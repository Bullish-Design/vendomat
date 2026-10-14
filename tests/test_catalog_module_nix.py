"""The catalog module on pinned Nixpkgs, with the real Nix parser (VMT-003, VMT-030 to VMT-035).

Each fixture writes YAML text into `vendomat.yaml`. The module reads it with `devenv/parse.nix`. The stub
options of `tests/nix/catalog.nix` stand in for devenv's own options. A real devenv runs the same module
in the opt-in `catalog-e2e` check. Opt in with `testee verify catalog-eval`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture, run

ROOT = Path(__file__).resolve().parents[1]

pytestmark = needs_nix_fixture


def nixpkgs_rev() -> str:
    lock = json.loads((ROOT / "flake.lock").read_text())
    return lock["nodes"]["nixpkgs"]["locked"]["rev"]


def evaluate(
    workspace: Path,
    text: str | None,
    read: str = "summary",
    *,
    files: tuple[str, ...] = (),
    contents: dict[str, str] | None = None,
    pythons: str = "",
    extra: str | None = None,
):
    """Evaluate the module for a workspace.

    ``text`` is the content of ``vendomat.yaml``, or None for no file. ``files`` are empty files to create
    in the workspace. ``contents`` maps more file names to their text.
    ``extra`` is the text of one more module, as the user's ``devenv.nix`` would be.
    """
    if text is not None:
        (workspace / "vendomat.yaml").write_text(text)
    for name in files:
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")
    for name, body in (contents or {}).items():
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    argv = ["nix-instantiate", "--extra-experimental-features", "flakes", "--eval", "--strict", "--json"]
    argv += [str(ROOT / "tests/nix/catalog.nix"), "--argstr", "root", str(workspace)]
    argv += ["--argstr", "repo", str(ROOT), "--argstr", "nixpkgs", nixpkgs_rev(), "--argstr", "read", read]
    argv += ["--argstr", "pythons", pythons]
    if extra is not None:
        module = workspace / "user.nix"
        module.write_text(extra)
        argv += ["--argstr", "extra", str(module)]
    return run(argv, workspace)


def summary(workspace: Path, text: str | None, **kwargs):
    result = evaluate(workspace, text, **kwargs)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


def fault_lines(stderr: str) -> list[str]:
    return [line.strip() for line in stderr.splitlines() if line.strip().startswith("vendomat.yaml:")]


def test_a_valid_file_maps_to_native_options(tmp_path: Path):
    text = """\
programs:
  - ripgrep
  - python3Packages.requests
languages:
  javascript:
    version: "22"
  python:
    enable: false
    version: "3.10"
services:
  postgres:
    enable: true
  redis:
    enable: false
env:
  VERSION: 3.10
  NAME: no
"""
    out = summary(tmp_path, text)
    assert out["packages"] == ["ripgrep", "requests"]
    # Text stays text: `3.10` is not a number and `no` is not a boolean.
    assert out["env"] == {"VERSION": "3.10", "NAME": "no"}
    # `enable: false` turns python off even with a version; its version is not mapped.
    assert out["python"]["enable"] is False
    assert out["python"]["version"] is None
    assert out["javascript"]["enable"] is True
    assert out["javascript"]["package"].startswith("nodejs-22")
    assert out["services"] == {"postgres": {"enable": True}, "redis": {"enable": False}}
    # A rust entry with a version selects the rust-overlay channel.
    rust = summary(tmp_path, 'languages:\n  rust:\n    version: "1.81.0"\n')["rust"]
    assert rust == {"channel": "stable", "enable": True, "version": "1.81.0"}
    # A rust entry with no version keeps the nixpkgs toolchain (VMT-044).
    bare = summary(tmp_path, "languages:\n  rust:\n    enable: true\n")["rust"]
    assert bare == {"channel": "nixpkgs", "enable": True, "version": "latest"}


def test_machine_programs_map_to_nixos_packages_separately_from_top_level_programs(tmp_path: Path):
    out = summary(
        tmp_path,
        "programs:\n  - jq\nmachines:\n  learner:\n    programs:\n      - ripgrep\n      - hello\n",
    )
    assert out["packages"] == ["jq"]
    assert out["machines"]["learner"]["programs"] == ["ripgrep", "hello"]


def test_machine_programs_resolve_with_the_package_set_of_the_machine(tmp_path: Path):
    # The stub gives a machine a `pkgs` where `jq` is `hello`. The workspace `pkgs` has the real `jq`.
    out = summary(tmp_path, "programs:\n  - jq\nmachines:\n  learner:\n    programs:\n      - jq\n")
    assert out["packages"] == ["jq"]
    assert out["machines"]["learner"]["programs"] == ["hello"]


def test_a_machine_program_is_still_checked_against_the_workspace_packages(tmp_path: Path):
    # The check reads the workspace `pkgs`, so a name that only the machine's set has is still a fault.
    result = evaluate(tmp_path, "machines:\n  learner:\n    programs:\n      - not-a-package-7319\n")
    assert result.returncode != 0 and "unknown program" in result.stderr


def test_machines_that_is_not_a_map_names_the_file_and_position(tmp_path: Path):
    # A raw Nix type error (`attrNames` on a string) once hid this message.
    result = evaluate(tmp_path, "machines: foo\n")
    assert result.returncode != 0
    assert fault_lines(result.stderr) == ['vendomat.yaml:1:11: machines must be a map, found "foo"']
    assert "expected a set" not in result.stderr


def test_an_unknown_machine_program_names_its_yaml_file_and_position(tmp_path: Path):
    result = evaluate(tmp_path, "machines:\n  learner:\n    programs:\n      - vendomat-no-such-package-7319\n")
    assert result.returncode != 0
    lines = fault_lines(result.stderr)
    assert len(lines) == 1
    assert lines[0].startswith("vendomat.yaml:4:")
    assert 'machines.learner.programs[0]: unknown program "vendomat-no-such-package-7319"' in lines[0]


@pytest.mark.parametrize("text", [None, ""], ids=["no-file", "empty-file"])
def test_a_missing_or_empty_file_is_an_empty_catalog(tmp_path: Path, text: str | None):
    out = summary(tmp_path, text)
    assert out["packages"] == [] and out["env"] == {}
    assert out["python"]["enable"] is False
    assert out["machines"] == {} and out["serve"] == {}


def test_a_tab_indented_file_reads_like_the_space_version(tmp_path: Path):
    spaces = summary(tmp_path, 'languages:\n  python:\n    version: "3.12"\nprograms:\n  - jq\n')
    tabs = summary(tmp_path, 'languages:\n\tpython:\n\t\tversion: "3.12"\nprograms:\n\t- jq\n')
    assert tabs == spaces
    assert tabs["python"]["version"] == "3.12"


def test_one_error_lists_every_bad_field_with_line_and_column(tmp_path: Path):
    # VMT-030 to VMT-032 and VMT-035: every fault names the file, a position, and the key path.
    text = """\
programs:
  - ripgrep
  - nosuchpkg
  - alsomissing
languages:
  python:
    enable: no
    enabled: true
  javascript:
    version: "99"
services:
  postgres:
    enable: maybe
env:
  GREETING:
    - hello
bogus: x
"""
    result = evaluate(tmp_path, text)
    assert result.returncode != 0
    lines = fault_lines(result.stderr)
    assert [line.split(" ", 2)[0] for line in lines] == [
        "vendomat.yaml:3:5:",
        "vendomat.yaml:4:5:",
        "vendomat.yaml:7:13:",
        "vendomat.yaml:8:5:",
        "vendomat.yaml:10:14:",
        "vendomat.yaml:13:13:",
        "vendomat.yaml:15:3:",
        "vendomat.yaml:17:1:",
    ], lines
    by_line = {line.split(":")[1]: line for line in lines}
    assert 'programs[1]: unknown program "nosuchpkg"' in by_line["3"]
    assert 'programs[2]: unknown program "alsomissing"' in by_line["4"]
    assert 'languages.python.enable must be "true" or "false", found "no"' in by_line["7"]
    assert "languages.python.enabled: unknown key (known: enable, uv, version)" in by_line["8"]
    assert "languages.javascript.version: nixpkgs has no Node.js 99" in by_line["10"]
    assert 'services.postgres.enable must be "true" or "false", found "maybe"' in by_line["13"]
    assert 'env.GREETING must be text, found a list ["hello"]' in by_line["15"]
    assert "bogus: unknown key (known: env, languages, machines, programs, services)" in by_line["17"]


def test_a_syntax_fault_reads_file_line_column_reason(tmp_path: Path):
    result = evaluate(tmp_path, 'languages:\n  python:\n    version: ["3.12"]\n')
    assert result.returncode != 0
    assert "vendomat.yaml:3:14: flow style is not accepted" in result.stderr


def test_a_nesting_fault_names_the_file(tmp_path: Path):
    # VMT-013: a file deeper than the limit fails with the file name, not with a Nix stack overflow.
    text = "".join("  " * i + f"k{i}:\n" for i in range(70)) + "  " * 70 + "leaf: x\n"
    result = evaluate(tmp_path, text)
    assert result.returncode != 0
    assert "vendomat.yaml:65:129: nesting deeper than 64 levels" in result.stderr
    assert "stack overflow" not in result.stderr


@pytest.mark.parametrize(
    "document",
    [
        "languages:\n  rust:\n    enable: false\n    version: not-a-version\n",  # a bad value in an unused field
        "languages:\n  gleam:\n    enable: true\n",  # an unknown key
    ],
)
def test_a_bad_file_stops_a_read_that_uses_no_catalog_value(tmp_path: Path, document: str):
    # `devenv.root` feeds from no catalog value. The module system still reads `_module.check` (VMT-031).
    result = evaluate(tmp_path, document, read="root")
    assert result.returncode != 0
    assert fault_lines(result.stderr)


def test_a_catalog_that_is_not_a_map_fails(tmp_path: Path):
    result = evaluate(tmp_path, "languages: python\nservices:\n  - redis\n")
    assert result.returncode != 0
    lines = fault_lines(result.stderr)
    assert any(line.startswith("vendomat.yaml:1:12: languages must be a map") for line in lines), lines
    assert any(line.startswith("vendomat.yaml:2:1: services must be a map") for line in lines), lines


def test_no_home_key_exists(tmp_path: Path):
    # R35, VMT-122: homes stay outside Vendomat. The key fails at the top level and inside a machine.
    top = evaluate(tmp_path, "home:\n  user: andrew\n")
    assert "vendomat.yaml:1:1: home: unknown key" in top.stderr
    inner = evaluate(tmp_path, "machines:\n  box:\n    home: andrew\n")
    assert (
        "vendomat.yaml:3:5: machines.box.home: unknown key (known: host, mode, programs, serve, virtual)"
        in inner.stderr
    )


# --- Python -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("uv_block", "pyproject", "enable", "sync"),
    [
        ("", False, True, False),  # uv on by default; sync stays off without pyproject.toml (VMT-041)
        ("", True, True, True),  # `auto` turns sync on with pyproject.toml
        ("    uv:\n      sync: auto\n", False, True, False),
        ("    uv:\n      sync: auto\n", True, True, True),
        ("    uv:\n      sync: true\n", False, True, True),  # forced on
        ("    uv:\n      sync: false\n", True, True, False),  # forced off
        ("    uv:\n      enable: false\n", True, False, True),
        ("    uv:\n      enable: true\n      sync: false\n", False, True, False),
    ],
)
def test_python_uv_keys_mirror_the_native_names(
    tmp_path: Path, uv_block: str, pyproject: bool, enable: bool, sync: bool
):
    text = 'languages:\n  python:\n    version: "3.12"\n' + uv_block
    out = summary(tmp_path, text, files=("pyproject.toml",) if pyproject else ())
    assert out["python"]["enable"] is True
    assert out["python"]["uv"] == {"enable": enable, "sync": {"enable": sync}}


def test_a_bad_uv_sync_value_fails_with_its_position(tmp_path: Path):
    result = evaluate(tmp_path, "languages:\n  python:\n    uv:\n      sync: sometimes\n")
    assert 'vendomat.yaml:4:13: languages.python.uv.sync must be "auto" or "true" or "false", found "sometimes"' in (
        result.stderr
    )


def test_a_python_version_that_nixpkgs_python_lacks_fails(tmp_path: Path):
    # VMT-045: the check runs when the workspace has the `nixpkgs-python` input.
    text = 'languages:\n  python:\n    version: "3.99"\n'
    ok = evaluate(tmp_path, text.replace("3.99", "3.12"), pythons="3.12,3.11")
    assert ok.returncode == 0, ok.stderr[-2000:]
    bad = evaluate(tmp_path, text, pythons="3.12,3.11")
    assert "vendomat.yaml:3:14: languages.python.version: nixpkgs-python has no Python 3.99" in bad.stderr
    # With no such input, the check cannot run, and the module accepts the version.
    assert evaluate(tmp_path, text).returncode == 0


# --- One value, one place ----------------------------------------------------------------------


def test_a_scalar_set_in_yaml_and_in_nix_conflicts_and_names_both_files(tmp_path: Path):
    # VMT-050 (R19): the inner module has `_file = "vendomat.yaml"`.
    nix = '{ languages.python.enable = true; languages.python.version = "3.11"; }'
    result = evaluate(tmp_path, 'languages:\n  python:\n    version: "3.12"\n', extra=nix)
    assert result.returncode != 0
    assert "vendomat.yaml" in result.stderr and "user.nix" in result.stderr
    assert "languages.python.version" in result.stderr


def test_a_catalog_default_yields_to_a_plain_nix_value(tmp_path: Path):
    # VMT-091 (R23): `uv.enable` is a default, so a plain Nix value wins with no conflict.
    nix = "{ languages.python.uv.enable = false; }"
    out = summary(tmp_path, 'languages:\n  python:\n    version: "3.12"\n', extra=nix)
    assert out["python"]["uv"]["enable"] is False


def test_lists_and_maps_merge_with_nix_definitions(tmp_path: Path):
    nix = '{ pkgs, ... }: { packages = [ pkgs.jq ]; env.OTHER = "x"; }'
    out = summary(tmp_path, "programs:\n  - ripgrep\nenv:\n  MINE: y\n", extra=nix)
    assert sorted(out["packages"]) == ["jq", "ripgrep"]
    assert out["env"] == {"MINE": "y", "OTHER": "x"}


# --- Machines -----------------------------------------------------------------------------------


def test_every_machine_gets_its_name_and_host(tmp_path: Path):
    # VMT-060 to VMT-062 (R21).
    out = summary(tmp_path, "machines:\n  laptop:\n    host: 10.0.0.2\n  server:\n    host: server.lan\n")
    assert out["machines"]["laptop"]["hostName"] == "laptop"
    assert out["machines"]["laptop"]["host"] == "10.0.0.2"
    assert out["machines"]["server"]["hostName"] == "server"
    # A different `networking.hostName` from the user conflicts and names both files; `mkForce` wins.
    nix = '{ machines.laptop.nixos.networking.hostName = "other"; }'
    clash = evaluate(tmp_path, "machines:\n  laptop:\n    host: h\n", extra=nix)
    assert clash.returncode != 0
    assert "vendomat.yaml" in clash.stderr and "user.nix" in clash.stderr
    forced = '{ lib, ... }: { machines.laptop.nixos.networking.hostName = lib.mkForce "other"; }'
    assert summary(tmp_path, "machines:\n  laptop:\n    host: h\n", extra=forced)["machines"]["laptop"]["hostName"] == (
        "other"
    )


def test_a_virtual_machine_has_no_hardware_report(tmp_path: Path):
    # VMT-063 (R23).
    out = summary(tmp_path, 'machines:\n  vm:\n    virtual: "true"\n  real:\n    host: h\n')["machines"]
    assert out["vm"]["facter"] is None
    assert out["real"]["facter"] == ".machines/real/facter.json"


@pytest.mark.parametrize(
    ("yaml_mode", "report", "expected"),
    [
        (None, False, None),  # neither: the catalog sets no mode
        (None, True, "adopt-existing"),  # a committed report marks the machine installed (R42)
        ("fresh-install", True, "fresh-install"),  # the key overrides the report: a deliberate reinstall
        ("adopt-existing", False, "adopt-existing"),  # the key works with no report too
        ("fresh-install", False, "fresh-install"),
    ],
)
def test_the_machine_mode_follows_the_hardware_report_and_the_key(
    tmp_path: Path, yaml_mode: str | None, report: bool, expected: str | None
):
    # VMT-099 (R42, D4). The report of another machine does not count.
    mode = f"    mode: {yaml_mode}\n" if yaml_mode else ""
    text = f"machines:\n  box:\n    host: h\n{mode}  other:\n    host: o\n"
    files = (".machines/box/facter.json",) if report else (".machines/other/facter.json",)
    out = summary(tmp_path, text, files=files)["machines"]
    assert out["box"]["mode"] == expected
    # `other` has the report exactly when `box` does not, and no key.
    assert out["other"]["mode"] == (None if report else "adopt-existing")


def test_the_facter_phase_case_marks_the_machine_installed(tmp_path: Path):
    # R42: `devenv machines install` writes `.machines/NAME/facter.json` in its `facter` phase, before the
    # remote install runs. From then on the machine reads as installed, and the host binary refuses the
    # install. The key `mode: fresh-install` allows a deliberate reinstall.
    text = "machines:\n  box:\n    host: 192.0.2.7\n"
    before = summary(tmp_path, text)["machines"]["box"]
    assert before["mode"] is None
    after = summary(tmp_path, text, files=(".machines/box/facter.json",))["machines"]["box"]
    assert after["mode"] == "adopt-existing"
    reinstall = text + "    mode: fresh-install\n"
    assert summary(tmp_path, reinstall, files=(".machines/box/facter.json",))["machines"]["box"]["mode"] == (
        "fresh-install"
    )


def test_the_derived_mode_is_a_default_and_a_plain_nix_value_wins(tmp_path: Path):
    nix = '{ machines.box.vendomat.mode = "fresh-install"; }'
    out = summary(tmp_path, "machines:\n  box:\n    host: h\n", files=(".machines/box/facter.json",), extra=nix)
    assert out["machines"]["box"]["mode"] == "fresh-install"
    # The key is a plain value, so a plain Nix value conflicts with it.
    clash = evaluate(tmp_path, "machines:\n  box:\n    mode: adopt-existing\n", extra=nix)
    assert clash.returncode != 0 and "vendomat.yaml" in clash.stderr


def test_a_bad_mode_fails_with_its_position(tmp_path: Path):
    result = evaluate(tmp_path, "machines:\n  box:\n    mode: reinstall\n")
    assert 'vendomat.yaml:3:11: machines.box.mode must be "fresh-install" or "adopt-existing"' in result.stderr


def test_serve_is_on_by_default_and_a_key_turns_it_off(tmp_path: Path):
    # R39: `serve` is a machine key, on by default. The catalog exposes it as `vendomat.serve`.
    text = 'machines:\n  a:\n    host: a\n  b:\n    serve: "false"\n  c:\n    serve: "true"\n'
    assert summary(tmp_path, text)["serve"] == {"a": True, "b": False, "c": True}


def test_a_bad_serve_value_fails_with_its_position(tmp_path: Path):
    result = evaluate(tmp_path, "machines:\n  a:\n    serve: nope\n")
    assert 'vendomat.yaml:3:12: machines.a.serve must be "true" or "false", found "nope"' in result.stderr


def test_serve_sets_no_other_option(tmp_path: Path):
    # `serve` feeds the sharing module only. The other machine options keep their values.
    out = summary(tmp_path, 'machines:\n  a:\n    serve: "false"\n')["machines"]["a"]
    assert out == {
        "hostName": "a",
        "host": None,
        "facter": ".machines/a/facter.json",
        "mode": None,
        "programs": [],
        "globalPorts": [],
        "trustedPorts": [],
    }


def test_a_machine_with_no_value_takes_every_default(tmp_path: Path):
    # R51, VMT-170: every machine key has a default, so `NAME:` alone declares a machine.
    out = summary(tmp_path, "machines:\n  laptop:\n  server: # all defaults\n")
    for name in ("laptop", "server"):
        assert out["machines"][name] == {
            "hostName": name,
            "host": None,
            "facter": f".machines/{name}/facter.json",
            "mode": None,
            "programs": [],
            "globalPorts": [],
            "trustedPorts": [],
        }
        assert out["sharing"][name]["serve"] is True
    assert out["serve"] == {"laptop": True, "server": True}


@pytest.mark.parametrize(
    ("text", "where"),
    [("machines:\n", "1:10"), ("env:\n  A:\n", "2:5"), ("languages:\n  python:\n", "2:10")],
    ids=["machines", "env", "language"],
)
def test_no_value_outside_a_machine_entry_still_fails(tmp_path: Path, text: str, where: str):
    result = evaluate(tmp_path, text)
    assert result.returncode != 0
    assert f'vendomat.yaml:{where}: no value; write "" for an empty text' in result.stderr


ALPHA_KEY = "alpha:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
GAMMA_KEY = "gamma:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="


def key_file(name: str) -> str:
    return f".machines/{name}/cache-key.pub"


def sharing(tmp_path: Path, text: str, **keys: str) -> dict:
    """The sharing facts of each machine, with a committed key file (and a trailing newline) per keyword."""
    contents = {key_file(name): key + "\n" for name, key in keys.items()}
    return summary(tmp_path, text, contents=contents)["sharing"]


TWO = "machines:\n  alpha:\n    host: alpha.lan\n  beta:\n    host: root@10.0.0.2\n"


def test_every_machine_imports_the_sharing_module_and_serves_by_default(tmp_path: Path):
    # R39, VMT-128. A machine without `serve` gets the module with serve on, and no peer.
    out = sharing(tmp_path, TWO)
    for name in ("alpha", "beta"):
        assert out[name]["serve"] is True
        assert out[name]["harmonia"] is True
        assert out[name]["keyUnit"] is True
        assert out[name]["peers"] == []
        assert out[name]["substituters"] == []


def test_serve_false_gives_the_module_with_serve_off(tmp_path: Path):
    text = 'machines:\n  alpha:\n    serve: "true"\n  beta:\n    serve: "false"\n'
    out = sharing(tmp_path, text)
    assert (out["alpha"]["serve"], out["alpha"]["harmonia"]) == (True, True)
    assert (out["beta"]["serve"], out["beta"]["harmonia"], out["beta"]["keyUnit"]) == (False, False, False)


def test_a_peer_needs_a_committed_key(tmp_path: Path):
    # Keyless at install: no key file, no peer. The key appears, and the peer follows.
    assert sharing(tmp_path, TWO)["beta"]["peers"] == []
    out = sharing(tmp_path, TWO, alpha=ALPHA_KEY)
    assert out["beta"]["peers"] == [{"url": "http://alpha.lan:5000", "publicKey": ALPHA_KEY}]
    assert out["beta"]["substituters"] == ["http://alpha.lan:5000"]
    assert out["beta"]["keys"] == [ALPHA_KEY]


def test_the_peer_url_drops_the_user_and_falls_back_to_the_name(tmp_path: Path):
    text = "machines:\n  alpha:\n    host: root@alpha.lan\n  beta:\n    host: b\n  gamma:\n    virtual: 'true'\n"
    out = sharing(tmp_path, text, alpha=ALPHA_KEY, gamma=GAMMA_KEY)
    assert out["beta"]["substituters"] == ["http://alpha.lan:5000", "http://gamma:5000"]
    assert out["beta"]["keys"] == [ALPHA_KEY, GAMMA_KEY]


def test_the_key_is_trimmed(tmp_path: Path):
    contents = {key_file("alpha"): f"  {ALPHA_KEY} \n\n"}
    out = summary(tmp_path, TWO, contents=contents)["sharing"]
    assert out["beta"]["keys"] == [ALPHA_KEY]


def test_a_machine_never_lists_itself(tmp_path: Path):
    out = sharing(tmp_path, TWO, alpha=ALPHA_KEY, beta="beta:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=")
    assert out["alpha"]["substituters"] == ["http://10.0.0.2:5000"]
    assert out["beta"]["substituters"] == ["http://alpha.lan:5000"]


def test_a_peer_with_serve_false_is_not_listed(tmp_path: Path):
    text = 'machines:\n  alpha:\n    host: alpha.lan\n    serve: "false"\n  beta:\n    host: b\n'
    out = sharing(tmp_path, text, alpha=ALPHA_KEY)
    assert out["beta"]["peers"] == []
    assert out["alpha"]["serve"] is False


def test_the_nix_files_can_override_the_sharing_values(tmp_path: Path):
    # R23: the YAML `serve` is a plain definition; the peers are a catalog default.
    peers = '[ { url = "http://x:5000"; publicKey = "x:AAAA="; } ]'
    nix = f"{{ machines.beta.nixos.vendomat.sharing.peers = {peers}; }}"
    text = TWO
    out = summary(tmp_path, text, contents={key_file("alpha"): ALPHA_KEY}, extra=nix)["sharing"]
    assert out["beta"]["substituters"] == ["http://x:5000"]
    clash = evaluate(
        tmp_path, 'machines:\n  a:\n    serve: "false"\n', extra="{ machines.a.nixos.vendomat.sharing.serve = true; }"
    )
    assert clash.returncode != 0
    assert "vendomat.sharing.serve" in clash.stderr


def test_sharing_defaults_closed_and_opens_only_a_marked_interface(tmp_path: Path):
    default = summary(tmp_path, 'machines:\n  alpha:\n    virtual: "false"\n')
    default_facts = default["sharing"]["alpha"]
    assert default_facts["globalPorts"] == []
    assert default_facts["trustedPorts"] == []

    marked = summary(
        tmp_path,
        'machines:\n  alpha:\n    virtual: "false"\n',
        extra='{ machines.alpha.nixos.vendomat.sharing.trustedInterfaces = [ "eth1" ]; }',
    )["sharing"]["alpha"]
    assert marked["globalPorts"] == []
    assert marked["trustedPorts"] == [5000]


def test_serve_false_keeps_port_closed_even_with_a_trust_marker(tmp_path: Path):
    facts = summary(
        tmp_path,
        'machines:\n  alpha:\n    serve: "false"\n',
        extra='{ machines.alpha.nixos.vendomat.sharing.trustedInterfaces = [ "eth1" ]; }',
    )["sharing"]["alpha"]
    assert facts["serve"] is False
    assert facts["harmonia"] is False
    assert facts["globalPorts"] == []
    assert facts["trustedPorts"] == []


def test_a_serving_machine_with_the_firewall_off_gets_a_warning(tmp_path: Path):
    # With `networking.firewall.enable = false`, port 5000 is open on every interface and the marker means nothing.
    text = 'machines:\n  alpha:\n    virtual: "false"\n  beta:\n    serve: "false"\n'
    off = (
        "{ machines.alpha.nixos.networking.firewall.enable = false;"
        " machines.beta.nixos.networking.firewall.enable = false; }"
    )
    facts = summary(tmp_path, text, extra=off)["sharing"]
    [warning] = facts["alpha"]["warnings"]
    assert "networking.firewall.enable is false" in warning and "TCP port 5000 on every interface" in warning
    assert "trustedInterfaces" in warning
    assert facts["beta"]["warnings"] == []  # serve = false: no Harmonia, nothing to warn about
    on = summary(tmp_path, text)["sharing"]
    assert on["alpha"]["warnings"] == [] and on["beta"]["warnings"] == []


def test_error_lines_come_first_and_match_one_pattern(tmp_path: Path):
    result = evaluate(tmp_path, "machines:\n  a:\n    serve: nope\nbogus: x\n")
    lines = fault_lines(result.stderr)
    assert len(lines) == 2
    for line in lines:
        assert re.match(r"^vendomat\.yaml:\d+:\d+: \S", line), line

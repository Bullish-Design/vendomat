"""The escape hatch in the catalog: the `advanced:` line and the data of `vendomat explain`.

(VMT-054 to VMT-057, VMT-093.) The stub options of `tests/nix/catalog.nix` stand in for devenv. The
workspace holds `devenv.nix` and `devenv.local.nix` as files, because the module reads them from the
workspace root. The same module runs on a real devenv in the opt-in `catalog-devenv` check. Opt in with
`testee verify catalog-eval`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture, run
from test_catalog_module_nix import ROOT, nixpkgs_rev

pytestmark = needs_nix_fixture


def read(
    workspace: Path,
    what: str,
    *,
    yaml: str = "",
    nix: str | None = None,
    local: str | None = None,
    load: bool = False,
):
    """Read `what` from the stub evaluation. `load` also loads the hatch files as modules, like devenv does."""
    (workspace / "vendomat.yaml").write_text(yaml)
    for name, text in (("devenv.nix", nix), ("devenv.local.nix", local)):
        if text is not None:
            (workspace / name).write_text(text)
    argv = ["nix-instantiate", "--extra-experimental-features", "flakes", "--eval", "--strict", "--json"]
    argv += [str(ROOT / "tests/nix/catalog.nix"), "--argstr", "root", str(workspace)]
    argv += ["--argstr", "repo", str(ROOT), "--argstr", "nixpkgs", nixpkgs_rev(), "--argstr", "read", what]
    if load:
        modules = [str(workspace / name) for name in ("devenv.nix", "devenv.local.nix") if (workspace / name).exists()]
        argv += ["--argstr", "extra", ",".join(modules)]
    result = run(argv, workspace)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


def line(workspace: Path, nix: str | None = None, local: str | None = None) -> str:
    """The `advanced:` line that the shell entry prints, or '' when it prints none."""
    shell = read(workspace, "shell", nix=nix, local=local)
    marker = "echo "
    if marker not in shell:
        return ""
    assert shell.startswith('[ "${VENDOMAT_HIDE_ADVANCED:-}" = 1 ] || echo '), shell
    return shell.split(marker, 1)[1].strip("'")


def test_stub_files_and_no_files_print_nothing(tmp_path: Path):
    # VMT-054: `{ }` and function stubs have no setting. A workspace with no hatch file has none either.
    assert line(tmp_path) == ""
    assert line(tmp_path, nix="{ }\n", local="{ pkgs, ... }: { }\n") == ""


def test_the_line_counts_the_settings_a_file_wrote(tmp_path: Path):
    # VMT-055: a leaf of the attribute tree is one setting; `packages` is one list; `mkForce` counts its content.
    nix = """\
{ lib, pkgs, ... }: {
  env.A = "a";
  env.B = lib.mkForce "b";
  packages = [ pkgs.jq pkgs.hello ];
  services.redis.enable = true;
}
"""
    assert line(tmp_path, nix=nix) == "advanced: devenv.nix sets 4 settings"
    assert line(tmp_path, nix='{ env.A = "a"; }\n') == "advanced: devenv.nix sets 1 setting"


def test_a_local_file_counts_apart_and_says_this_checkout_only(tmp_path: Path):
    # VMT-056.
    out = line(tmp_path, nix='{ env.A = "a"; }\n', local='{ env.L = "l"; env.M = "m"; }\n')
    assert out == "advanced: devenv.nix sets 1 setting; devenv.local.nix sets 2 settings (this checkout only)"
    assert line(tmp_path, nix="{ }\n", local='{ env.L = "l"; }\n') == (
        "advanced: devenv.local.nix sets 1 setting (this checkout only)"
    )


def test_the_line_counts_a_file_that_the_hatch_file_imports_from_the_workspace(tmp_path: Path):
    (tmp_path / "extra.nix").write_text('{ env.X = "x"; env.Y = "y"; }\n')
    out = line(tmp_path, nix='{ imports = [ ./extra.nix ]; env.A = "a"; }\n', local="{ }\n")
    assert out == "advanced: devenv.nix sets 3 settings"


def test_the_hide_switch_is_read_by_the_shell_not_by_nix(tmp_path: Path):
    # VMT-093, R45: the text tests the variable when the shell starts, so the evaluation is the same for both.
    shell = read(tmp_path, "shell", nix='{ env.A = "a"; }\n')
    assert shell.startswith('[ "${VENDOMAT_HIDE_ADVANCED:-}" = 1 ] || echo ')


def test_explain_lists_the_yaml_keys_in_file_order_with_option_value_and_file(tmp_path: Path):
    yaml = """\
programs:
  - jq
languages:
  python:
    version: "3.12"
env:
  GREETING: hello
machines:
  box:
    host: 192.0.2.7
  vm:
    virtual: "true"
    serve: "false"
    mode: fresh-install
"""
    report = read(tmp_path, "explain", yaml=yaml, nix="{ }\n", local="{ }\n")
    entries = {e["key"]: e for e in report["yaml"]}
    assert [e["key"] for e in report["yaml"]] == [
        "programs",
        "languages.python.version",
        "env.GREETING",
        "machines.box",
        "machines.box.host",
        "machines.vm",
        "machines.vm.virtual",
        "machines.vm.serve",
        "machines.vm.mode",
    ]
    assert (entries["languages.python.version"]["line"], entries["languages.python.version"]["column"]) == (5, 5)
    assert entries["programs"]["option"] == "packages" and entries["programs"]["value"] == ["jq"]
    assert entries["languages.python.version"]["option"] == "languages.python.version"
    assert entries["languages.python.version"]["value"] == "3.12"
    assert entries["env.GREETING"]["value"] == "hello"
    assert entries["machines.box.host"]["option"] == "machines.box.target.host"
    assert entries["machines.box"]["option"] == "machines.box.nixos"
    assert entries["machines.box"]["value"] == {"networking": {"hostName": "box"}}
    assert entries["machines.vm.virtual"]["option"] == "machines.vm.hardware.facter"
    assert entries["machines.vm.virtual"]["value"] is None
    assert entries["machines.vm.serve"]["option"] == "vendomat.serve.vm"
    assert entries["machines.vm.serve"]["value"] is False
    assert entries["machines.vm.mode"]["option"] == "machines.vm.vendomat.mode"
    assert entries["machines.vm.mode"]["value"] == "fresh-install"
    assert all(e["files"] == ["vendomat.yaml"] for e in report["yaml"])
    assert report["nix"] == []


def test_explain_names_the_file_that_wins_and_lists_the_options_only_nix_sets(tmp_path: Path):
    # R27: a `mkForce` in devenv.nix replaces vendomat.yaml as the source; a merged option lists both files.
    (tmp_path / "extra.nix").write_text('{ env.EXTRA = "e"; }\n')
    nix = """\
{ lib, pkgs, ... }: {
  imports = [ ./extra.nix ];
  env.GREETING = lib.mkForce "bye";
  packages = [ pkgs.hello ];
  languages.python.enable = true;
}
"""
    local = '{ env.LOCAL_ONLY = "1"; }\n'
    yaml = "programs:\n  - jq\nenv:\n  GREETING: hello\n"
    report = read(tmp_path, "explain", yaml=yaml, nix=nix, local=local, load=True)
    entries = {e["key"]: e for e in report["yaml"]}
    assert entries["env.GREETING"]["value"] == "bye"
    assert entries["env.GREETING"]["files"] == ["devenv.nix"]
    assert entries["programs"]["value"] == ["jq"]
    assert entries["programs"]["files"] == ["vendomat.yaml", "devenv.nix"]
    only_nix = {e["option"]: e for e in report["nix"]}
    assert set(only_nix) == {"env.EXTRA", "env.LOCAL_ONLY", "languages.python.enable"}
    assert only_nix["env.EXTRA"]["files"] == ["extra.nix"]
    assert only_nix["env.LOCAL_ONLY"]["files"] == ["devenv.local.nix"]
    assert only_nix["languages.python.enable"]["value"] is True


def test_explain_shows_every_source_whatever_the_hide_switch_says(tmp_path: Path):
    # R45: the switch lives in the shell text only. The report does not read it.
    nix = '{ env.A = "a"; }\n'
    report = read(tmp_path, "explain", nix=nix, load=True)
    assert [e["option"] for e in report["nix"]] == ["env.A"]


def test_explain_stops_with_the_yaml_fault_lines(tmp_path: Path):
    (tmp_path / "vendomat.yaml").write_text("languages:\n  python:\n    version: x\n")
    argv = ["nix-instantiate", "--extra-experimental-features", "flakes", "--eval", "--strict", "--json"]
    argv += [str(ROOT / "tests/nix/catalog.nix"), "--argstr", "root", str(tmp_path), "--argstr", "repo", str(ROOT)]
    argv += ["--argstr", "nixpkgs", nixpkgs_rev(), "--argstr", "read", "explain"]
    result = run(argv, tmp_path)
    assert result.returncode != 0
    assert "vendomat.yaml:3:14: languages.python.version must be a version" in result.stderr


@pytest.mark.parametrize("name", ["hatch.nix", "explain.nix"])
def test_the_module_files_exist(name: str):
    assert (ROOT / "devenv" / name).is_file()

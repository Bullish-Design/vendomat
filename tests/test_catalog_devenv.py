"""The hatch line, `vendomat explain`, the trimmed error, and `vendomat update` on a real devenv (S3 part 2).

These checks run stock devenv 2.4.0 from `PATH` on a workspace that imports the catalog of this repository
(`devenv/`, copied to a `path:` input) and the module source of the `devenv` input. Opt in with
`testee verify catalog-devenv`. The checks need `devenv`, `nix`, and the pinned Nixpkgs in the fetcher cache.

Environment:
    VENDOMAT_DEVENV_E2E=1         opt in.
    VENDOMAT_DEVENV_MODULES=DIR   a `src/modules` directory to use as a `path:` input. The default is the `devenv`
                                  input that `flake.lock` pins (the published S1 tag).
    VENDOMAT_DEVENV_LOGS=DIR      keep the command, status, and output of each run outside the repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from nixfixture import s1_devenv_input
from typer.testing import CliRunner

from vendomat import explain
from vendomat.cli import app

ROOT = Path(__file__).resolve().parents[1]
DEVENV_INPUT, DEVENV_LABEL = s1_devenv_input(os.environ.get("VENDOMAT_DEVENV_MODULES"))
LAUNCHER = ROOT / "launcher" / "vendomat"

pytestmark = pytest.mark.skipif(
    os.environ.get("VENDOMAT_DEVENV_E2E") != "1" or shutil.which("devenv") is None,
    reason="real devenv check; set VENDOMAT_DEVENV_E2E=1 and provide devenv to opt in",
)

_COUNTER = {"n": 0}


def clean_env(**extra: str) -> dict[str, str]:
    """The environment of a run: the caller's, without the variables of the repository's own venv."""
    env = {k: v for k, v in os.environ.items() if k not in ("UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV")}
    env.pop("VENDOMAT_HIDE_ADVANCED", None)
    env.update(extra)
    return env


def run(argv: list[str], cwd: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=clean_env(**extra), timeout=900)
    log_dir = os.environ.get("VENDOMAT_DEVENV_LOGS")
    if log_dir:
        _COUNTER["n"] += 1
        stem = Path(log_dir) / f"{os.getpid()}-{_COUNTER['n']:03d}"
        stem.parent.mkdir(parents=True, exist_ok=True)
        stem.with_suffix(".json").write_text(json.dumps({"argv": argv, "cwd": str(cwd), "rc": done.returncode}))
        stem.with_suffix(".stdout").write_text(done.stdout)
        stem.with_suffix(".stderr").write_text(done.stderr)
    return done


def nixpkgs_url() -> str:
    lock = json.loads((ROOT / "flake.lock").read_text())
    return f"github:NixOS/nixpkgs/{lock['nodes']['nixpkgs']['locked']['rev']}"


DISKO = "github:nix-community/disko/de5708739256238fb912c62f03988815db89ec9a"


def make_baseline(base: Path, extra_inputs: str = "") -> Path:
    """A locked workspace in ``base``, with ``extra_inputs`` (YAML lines of the `inputs` map) added."""
    log_dir = os.environ.get("VENDOMAT_DEVENV_LOGS")
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        (Path(log_dir) / "trees.txt").write_text(f"devenv input: {DEVENV_LABEL}\n")
    shutil.copytree(ROOT / "devenv", base / "modsrc" / "devenv")
    ws = base / "ws"
    ws.mkdir()
    (ws / "devenv.yaml").write_text(
        textwrap.dedent(
            f"""\
            inputs:
              vendomat:
                url: path:{base / "modsrc"}
                flake: false
              devenv:
                url: {DEVENV_INPUT}
              nixpkgs:
                url: {nixpkgs_url()}
            """
        )
        + extra_inputs
        + "imports:\n  - vendomat/devenv\n"
    )
    (ws / "devenv.nix").write_text("{ }\n")
    (ws / "vendomat.yaml").write_text("")
    done = run(["devenv", "eval", "devenv.root"], ws)
    assert done.returncode == 0, done.stderr[-3000:]
    assert (ws / "devenv.lock").is_file()
    return ws


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A locked workspace. Each test copies it."""
    return make_baseline(tmp_path_factory.mktemp("baseline"))


@pytest.fixture(scope="module")
def machines_baseline(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A locked workspace whose machines evaluate: `machines.nix` of the module tree needs `disko`."""
    disko = f"  disko:\n    url: {DISKO}\n    inputs:\n      nixpkgs:\n        follows: nixpkgs\n"
    return make_baseline(tmp_path_factory.mktemp("machines-baseline"), disko)


def copy_of(base: Path, tmp_path: Path) -> Path:
    target = tmp_path / "ws"
    shutil.copytree(base, target, ignore=shutil.ignore_patterns(".devenv"))
    return target


@pytest.fixture
def ws(baseline: Path, tmp_path: Path) -> Path:
    # The `vendomat` input is a path in the baseline; the lock names its hash, which the copy keeps.
    return copy_of(baseline, tmp_path)


@pytest.fixture
def mws(machines_baseline: Path, tmp_path: Path) -> Path:
    return copy_of(machines_baseline, tmp_path)


def shell_lines(ws: Path, **extra: str) -> list[str]:
    done = run(["devenv", "shell", "--", "true"], ws, **extra)
    assert done.returncode == 0, done.stderr[-3000:]
    return [line for line in (done.stdout + done.stderr).splitlines() if line.startswith("advanced:")]


def test_the_shell_prints_one_advanced_line_and_the_switch_hides_it(ws: Path):
    # VMT-054 to VMT-056, VMT-093, R45.
    (ws / "devenv.nix").write_text('{ pkgs, ... }: { env.A = "a"; env.B = "b"; packages = [ pkgs.jq ]; }\n')
    (ws / "devenv.local.nix").write_text('{ env.L = "l"; }\n')
    expected = "advanced: devenv.nix sets 3 settings; devenv.local.nix sets 1 setting (this checkout only)"
    assert shell_lines(ws) == [expected]
    assert shell_lines(ws, VENDOMAT_HIDE_ADVANCED="1") == []


def test_stub_hatch_files_print_nothing(ws: Path):
    (ws / "devenv.nix").write_text("{ }\n")
    (ws / "devenv.local.nix").write_text("{ pkgs, ... }: { }\n")
    assert shell_lines(ws) == []


def test_explain_reads_the_real_option_tree_and_names_the_files(ws: Path, monkeypatch: pytest.MonkeyPatch):
    # R27, VMT-057. The data comes from `devenv eval vendomat.explain` on the real module system.
    (ws / "vendomat.yaml").write_text(
        textwrap.dedent(
            """\
            programs:
              - jq
            env:
              GREETING: hello
              KEPT: kept
            services:
              redis:
                enable: true
            machines:
              box:
                host: 192.0.2.7
                mode: adopt-existing
            """
        )
    )
    (ws / "devenv.nix").write_text(
        '{ lib, ... }: { env.GREETING = lib.mkForce "bye"; env.ONLY_NIX = "n"; machines.box.nixos = { }; }\n'
    )
    (ws / "devenv.local.nix").write_text('{ env.LOCAL_ONLY = "1"; }\n')
    monkeypatch.setenv("VENDOMAT_DEVENV", shutil.which("devenv") or "devenv")
    report = explain.read_report(ws)
    entries = {e["key"]: e for e in report["yaml"]}
    assert (entries["env.GREETING"]["value"], entries["env.GREETING"]["files"]) == ("bye", ["devenv.nix"])
    assert (entries["env.KEPT"]["value"], entries["env.KEPT"]["files"]) == ("kept", ["vendomat.yaml"])
    assert entries["programs"]["option"] == "packages"
    assert entries["programs"]["files"] == ["vendomat.yaml"]
    assert entries["services.redis.enable"]["value"] is True
    assert entries["machines.box.host"]["option"] == "machines.box.target.host"
    assert entries["machines.box.host"]["value"] == "192.0.2.7"
    assert entries["machines.box.mode"]["value"] == "adopt-existing"
    assert entries["machines.box"]["files"] == ["vendomat.yaml", "devenv.nix"]
    assert sorted(e["option"] for e in report["nix"]) == ["env.LOCAL_ONLY", "env.ONLY_NIX"]
    assert [e["line"] for e in report["yaml"]] == sorted(e["line"] for e in report["yaml"])


def test_explain_marks_a_key_that_has_no_effect(ws: Path, monkeypatch: pytest.MonkeyPatch):
    # `languages.python.version` while Python is off: no file of the workspace sets the option.
    monkeypatch.setenv("VENDOMAT_DEVENV", shutil.which("devenv") or "devenv")
    (ws / "vendomat.yaml").write_text('languages:\n  python:\n    enable: "false"\n    version: "3.12"\n')
    entries = {e["key"]: e for e in explain.read_report(ws)["yaml"]}
    assert entries["languages.python.version"]["files"] == ["(devenv default)"]
    assert entries["languages.python.version"]["value"] is None


def test_explain_runs_as_a_command_and_hides_nothing_when_the_line_is_hidden(ws: Path, monkeypatch: pytest.MonkeyPatch):
    # R45.
    monkeypatch.setenv("VENDOMAT_DEVENV", shutil.which("devenv") or "devenv")
    monkeypatch.setenv("VENDOMAT_HIDE_ADVANCED", "1")
    (ws / "devenv.nix").write_text('{ env.ONLY_NIX = "n"; }\n')
    result = CliRunner().invoke(app, ["explain", "--root", str(ws), "--json"])
    assert result.exit_code == 0, result.output
    assert [e["option"] for e in json.loads(result.stdout)["nix"]] == ["env.ONLY_NIX"]


def test_a_bad_file_stops_the_launcher_with_the_yaml_lines_first(ws: Path, tmp_path: Path):
    # VMT-117 on the real devenv.
    (ws / "vendomat.yaml").write_text("programs:\n  - jq\n  - nosuchprog\nhome:\n  user: a\n")
    state = tmp_path / "state"
    done = run(
        ["bash", str(LAUNCHER)],
        ws,
        VENDOMAT_DEVENV_FORK=shutil.which("devenv") or "devenv",
        VENDOMAT_HOST_RELEASE="/nonexistent",
        XDG_STATE_HOME=str(state),
    )
    assert done.returncode == 2
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert lines[0].startswith("vendomat: the workspace does not evaluate")
    assert lines[1].startswith('vendomat.yaml:3:5: programs[1]: unknown program "nosuchprog"')
    assert lines[2].startswith("vendomat.yaml:4:1: home: unknown key")
    assert len(lines) == 4 and lines[3].startswith("vendomat: the full trace is in ")
    log = Path(lines[3].removeprefix("vendomat: the full trace is in "))
    assert log.parent == state / "vendomat" / "logs"
    assert len(log.read_text().splitlines()) > 100  # the whole trace stays in the log


def test_update_writes_the_lines_and_devenv_locks_them(ws: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # R25, VMT-094: the added lines are valid devenv.yaml, and `devenv update` accepts them. The template here
    # adds a path input, so no network is needed.
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "marker.txt").write_text("x\n")
    template = tmp_path / "template"
    template.mkdir()
    head, tail = (ws / "devenv.yaml").read_text().split("imports:\n")
    (template / "devenv.yaml").write_text(f"{head}  extra:\n    url: path:{extra}\n    flake: false\nimports:\n{tail}")
    monkeypatch.setenv("VENDOMAT_DEVENV", shutil.which("devenv") or "devenv")
    monkeypatch.setenv("VENDOMAT_TEMPLATE", str(template))
    result = CliRunner().invoke(app, ["update", "--check", "--root", str(ws)])
    assert result.exit_code == 1 and "inputs.extra.url" in result.output
    result = CliRunner().invoke(app, ["update", "extra", "--root", str(ws)])
    assert result.exit_code == 0, result.output
    assert "  inputs.extra.url: path:" in result.stdout
    assert "extra" in json.loads((ws / "devenv.lock").read_text())["nodes"]
    assert CliRunner().invoke(app, ["update", "--check", "--root", str(ws)]).exit_code == 0


# --- The sharing wiring (R39, VMT-127, VMT-128) -------------------------------------------------

ALPHA_KEY = "alpha:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
TWO_MACHINES = textwrap.dedent(
    """\
    machines:
      alpha:
        host: root@192.0.2.1
        virtual: "true"
      beta:
        host: 192.0.2.2
        virtual: "true"
        serve: "false"
    """
)


def nixos(machine: str, option: str) -> str:
    return f"machines.{machine}._nixosEval.config.{option}"


def test_alpha_serves_and_beta_with_serve_false_runs_no_harmonia(mws: Path):
    (mws / "vendomat.yaml").write_text(TWO_MACHINES)
    enable = "services.harmonia.cache.enable"
    done = run(["devenv", "eval", nixos("alpha", enable), nixos("beta", enable)], mws)
    assert done.returncode == 0, done.stderr[-3000:]
    values = json.loads(done.stdout)
    assert values == {nixos("alpha", enable): True, nixos("beta", enable): False}


def test_beta_substitutes_from_alpha_only_after_the_key_is_committed(mws: Path):
    (mws / "vendomat.yaml").write_text(TWO_MACHINES.replace('serve: "false"', 'serve: "true"'))
    settings = nixos("beta", "nix.settings")
    names = [f"{settings}.extra-substituters", f"{settings}.extra-trusted-public-keys", f"{settings}.fallback"]
    # No key file: no peer, and the evaluation works without a key (keyless at install).
    peers = nixos("beta", "vendomat.sharing.peers")
    keyless = run(["devenv", "eval", peers], mws)
    assert keyless.returncode == 0, keyless.stderr[-3000:]
    assert json.loads(keyless.stdout) == {peers: []}
    # The key is committed: the peer appears. The URL has the host without `root@`.
    key = mws / ".machines" / "alpha" / "cache-key.pub"
    key.parent.mkdir(parents=True)
    key.write_text(ALPHA_KEY + "\n")
    done = run(["devenv", "eval", *names], mws)
    assert done.returncode == 0, done.stderr[-3000:]
    values = json.loads(done.stdout)
    assert values[names[0]] == ["http://192.0.2.1:5000"]
    assert values[names[1]] == [ALPHA_KEY]
    assert values[names[2]] is True
    # Alpha lists no peer: beta serves too in this file, but it has no key.
    own = nixos("alpha", "vendomat.sharing.peers")
    done = run(["devenv", "eval", own], mws)
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout)[own] == []


def test_a_beta_that_does_not_serve_gives_no_peer_entry(mws: Path):
    # `beta` has `serve: "false"`. Its key file, if any, does not make it a peer of `alpha`.
    (mws / "vendomat.yaml").write_text(TWO_MACHINES)
    key = mws / ".machines" / "beta" / "cache-key.pub"
    key.parent.mkdir(parents=True)
    key.write_text("beta:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=\n")
    attribute = nixos("alpha", "vendomat.sharing.peers")
    done = run(["devenv", "eval", attribute], mws)
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout)[attribute] == []

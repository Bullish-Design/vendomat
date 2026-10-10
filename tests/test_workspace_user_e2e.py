"""A template-created workspace with two authored modules and no user Nix edits."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEVENV = os.environ.get("VENDOMAT_DEVENV") or shutil.which("devenv")
TEMPLATEER = (
    os.environ.get("VENDOMAT_TEMPLATEER")
    or shutil.which("templateer")
    or str(ROOT.parent / "templateer_v2/.venv/bin/templateer")
)
ENABLED = os.environ.get("VENDOMAT_E2E") == "1" and all(shutil.which(t) for t in ("nix", "git")) and bool(DEVENV)
pytestmark = pytest.mark.skipif(not ENABLED, reason="Nix, devenv, and Templateer fixture; set VENDOMAT_E2E=1")
GIT = ["git", "-c", "user.email=fixture@example.invalid", "-c", "user.name=fixture", "-c", "commit.gpgsign=false"]


def run(
    argv: list[str], cwd: Path, timeout: int = 900, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def record(name: str, result: subprocess.CompletedProcess[str]) -> None:
    directory = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if directory:
        path = Path(directory) / f"workspace-{name}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as stream:
            stream.write(f"argv: {result.args!r}\nexit: {result.returncode}\n{result.stdout}{result.stderr}\n")


def repo(root: Path, name: str, files: dict[str, str]) -> None:
    target = root / name
    target.mkdir(parents=True)
    for path, content in files.items():
        dest = target / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    commands = (
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "-A"],
        [*GIT, "commit", "-q", "-m", "v1"],
        [*GIT, "tag", "v1"],
    )
    for argv in commands:
        result = run(argv, target)
        assert result.returncode == 0, result.stderr


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_template_workspace_selects_authored_modules(tmp_path: Path) -> None:
    assert Path(TEMPLATEER).is_file(), f"Templateer is unavailable: {TEMPLATEER}"
    repos = tmp_path / "repos"
    repos.mkdir()
    number = port()
    forge = f"git://127.0.0.1:{number}"
    tagged = lambda name: f"{forge}/{name}?ref=refs/tags/v1"  # noqa: E731

    vendomat_files = {
        "flake.nix": "{ outputs = { self }: { devenvModules.default = import ./nix/devenv-module self; }; }\n"
    }
    for source in (ROOT / "nix/devenv-module").glob("*.nix"):
        vendomat_files[f"nix/devenv-module/{source.name}"] = source.read_text()
    repo(repos, "vendomat", vendomat_files)
    repo(repos, "alpha-dep", {"flake.nix": "{ outputs = { self }: { }; }\n"})
    repo(repos, "beta-dep", {"flake.nix": "{ outputs = { self }: { }; }\n"})
    for name, letter in (("alpha", "A"), ("beta", "B")):
        repo(
            repos,
            name,
            {
                "flake.nix": "{ outputs = { self }: { }; }\n",
                "devenv/devenv.yaml": f"inputs:\n  {name}-dep:\n    url: {tagged(f'{name}-dep')}\n",
                "devenv/devenv.nix": (
                    "{ config, lib, ... }: {\n"
                    f"  options.vendomat.settings.{name}.value = lib.mkOption {{\n"
                    f'    type = lib.types.str; default = "{letter}";\n'
                    "  };\n"
                    f"  config.env.{name.upper()}_VALUE = config.vendomat.settings.{name}.value;\n"
                    "}\n"
                ),
            },
        )
    repo(
        repos,
        "unused",
        {"flake.nix": "{ outputs = { self }: { }; }\n", "devenv/devenv.nix": 'throw "unused module loaded"\n'},
    )
    daemon = subprocess.Popen(
        [
            "git",
            "daemon",
            "--reuseaddr",
            "--export-all",
            f"--base-path={repos}",
            "--listen=127.0.0.1",
            f"--port={number}",
            str(repos),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            if run(["git", "ls-remote", f"{forge}/alpha"], tmp_path, timeout=10).returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise AssertionError("fixture Git daemon did not start")

        model = tmp_path / "model.json"
        model.write_text(json.dumps({"forge_url": forge, "vendomat_tag": "v1"}))
        workspace = tmp_path / "workspace"
        created = run(
            [str(ROOT / "templates/workspace/init"), str(model), str(workspace)],
            tmp_path,
            env={**os.environ, "VENDOMAT_TEMPLATEER": TEMPLATEER},
        )
        record("create", created)
        assert created.returncode == 0, created.stderr
        assert {p.name for p in workspace.iterdir()} == {"vendomat.toml", "devenv.nix", "devenv.yaml"}
        template_nix = (workspace / "devenv.nix").read_bytes()
        template_yaml = (workspace / "devenv.yaml").read_bytes()
        registry = workspace / "vendomat.toml"
        registry.write_text(
            registry.read_text()
            .replace(
                "[imports]\n\n[settings]",
                '[imports]\nalpha = "devenv"\nbeta = "devenv"\n\n'
                '[settings.alpha]\nvalue = "first"\n\n[settings.beta]\nvalue = "second"\n\n[settings]',
            )
            .replace(
                "[imports]",
                '[inputs.alpha]\nref = "refs/tags/v1"\n\n'
                '[inputs.beta]\nref = "refs/tags/v1"\n\n'
                '[inputs.unused]\nref = "refs/tags/v1"\n\n[imports]',
                1,
            )
        )

        def sync() -> subprocess.CompletedProcess[str]:
            result = run([sys.executable, "-m", "vendomat.cli", "sync", "--root", str(workspace)], workspace)
            record("sync", result)
            return result

        def evaluate(name: str) -> subprocess.CompletedProcess[str]:
            result = run([str(DEVENV), "--no-eval-cache", "eval", f"env.{name}"], workspace)
            record(f"eval-{name}", result)
            return result

        first = sync()
        assert first.returncode == 0, first.stdout + first.stderr
        assert "first" in evaluate("ALPHA_VALUE").stdout
        assert "second" in evaluate("BETA_VALUE").stdout
        shell = run([str(DEVENV), "--no-eval-cache", "shell", "--", "true"], workspace)
        record("shell", shell)
        assert shell.returncode == 0, shell.stderr[-3000:]
        lock = json.loads((workspace / "devenv.lock").read_text())
        for name in ("alpha", "alpha-dep", "beta", "beta-dep", "unused", "vendomat"):
            assert name in lock["nodes"]
        assert (workspace / "devenv.nix").read_bytes() == template_nix
        assert (workspace / "devenv.yaml").read_bytes() == template_yaml

        with_unused = run([str(DEVENV), "--no-eval-cache", "eval", "shell.drvPath"], workspace)
        record("shell-derivation", with_unused)
        assert with_unused.returncode == 0
        registry.write_text(registry.read_text().replace('[inputs.unused]\nref = "refs/tags/v1"\n\n', ""))
        assert sync().returncode == 0
        without_unused = run([str(DEVENV), "--no-eval-cache", "eval", "shell.drvPath"], workspace)
        record("shell-derivation", without_unused)
        assert without_unused.returncode == 0
        assert with_unused.stdout == without_unused.stdout

        registry.write_text(registry.read_text().replace('value = "first"', 'value = "changed"'))
        assert sync().returncode == 0
        assert "changed" in evaluate("ALPHA_VALUE").stdout
        assert (workspace / "devenv.nix").read_bytes() == template_nix

        registry.write_text(registry.read_text().replace('beta = "devenv"', 'missing = "devenv"'))
        unknown = sync()
        assert unknown.returncode != 0 and "missing" in unknown.stderr
        registry.write_text(registry.read_text().replace('missing = "devenv"', 'beta = "devenv"'))
        registry.write_text(registry.read_text().replace('value = "changed"', 'wrong = "changed"'))
        unsupported = evaluate("ALPHA_VALUE")
        assert unsupported.returncode != 0 and "wrong" in unsupported.stderr
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)

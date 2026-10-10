"""The host launcher against real Nix and real tags (Step 4). Opt in with `testee check e2e`.

Two tagged copies of this repository are served over `git://`. Two workspaces pin different tags.
The launcher, built from this tree, must run each workspace's own Vendomat, find it again with the
network off, and fall back to the host release only where the guide says.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEVENV = os.environ.get("VENDOMAT_DEVENV") or shutil.which("devenv")
ENABLED = os.environ.get("VENDOMAT_E2E") == "1" and all(shutil.which(t) for t in ("nix", "git", "jq")) and bool(DEVENV)
pytestmark = pytest.mark.skipif(not ENABLED, reason="Nix, devenv, and jq fixture; set VENDOMAT_E2E=1 to opt in")

GIT = ["git", "-c", "user.email=fixture@example.invalid", "-c", "user.name=fixture", "-c", "commit.gpgsign=false"]
COPY = ("flake.nix", "flake.lock", "pyproject.toml", "README.md")
COPY_DIRS = ("src", "nix", "direnv", "launcher", "preflight", "templates")


def sh(argv, cwd, env=None, timeout=1500):
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=full)


def copy_tree(dest: Path) -> None:
    dest.mkdir(parents=True)
    for name in COPY:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, dest / name)
    for name in COPY_DIRS:
        shutil.copytree(ROOT / name, dest / name, ignore=shutil.ignore_patterns("__pycache__"))


def set_version(repo: Path, version: str) -> None:
    path = repo / "pyproject.toml"
    path.write_text(re.sub(r'^version = ".*"$', f'version = "{version}"', path.read_text(), count=1, flags=re.M))


@pytest.fixture
def served(tmp_path):
    repos = tmp_path / "repos"
    repo = repos / "vendomat"
    copy_tree(repo)
    assert sh(["git", "init", "-q", "-b", "main"], repo).returncode == 0
    for version in ("0.6.0", "0.6.1"):
        set_version(repo, version)
        assert sh(["git", "add", "-A"], repo).returncode == 0
        assert sh([*GIT, "commit", "-q", "-m", f"release {version}"], repo).returncode == 0
        assert sh([*GIT, "tag", f"v{version}"], repo).returncode == 0
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    proc = subprocess.Popen(
        [
            "git",
            "daemon",
            "--reuseaddr",
            "--export-all",
            f"--base-path={repos}",
            "--listen=127.0.0.1",
            f"--port={port}",
            str(repos),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if sh(["git", "ls-remote", f"git://127.0.0.1:{port}/vendomat"], tmp_path).returncode == 0:
            break
        time.sleep(0.2)
    yield port, proc
    proc.terminate()


def workspace(tmp: Path, name: str, port: int, tag: str) -> Path:
    root = tmp / name
    root.mkdir()
    (root / "vendomat.toml").write_text(
        f'[forge]\nurl = "git://127.0.0.1:{port}"\n\n[targets]\ndevenv = true\n\n'
        f'[inputs]\nvendomat = {{ ref = "refs/tags/{tag}" }}\n'
    )
    (root / "devenv.yaml").write_text("imports:\n  - ./.vendomat\n")
    (root / "devenv.nix").write_text("{ ... }: { }\n")
    return root


def test_the_launcher_story(tmp_path, served):
    port, daemon = served
    # Build the launcher, and with it the host release, from this tree.
    built_from = tmp_path / "host-src"
    copy_tree(built_from)
    done = sh(
        ["nix", "build", "--no-link", "--print-out-paths", f"path:{built_from}#packages.x86_64-linux.launcher"],
        tmp_path,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    launcher = Path(done.stdout.strip().splitlines()[-1]) / "bin" / "vendomat"
    cache = tmp_path / "launcher-cache"
    env = {
        "VENDOMAT_DEVENV": str(DEVENV),
        "VENDOMAT_LAUNCHER_CACHE": str(cache),
        "PATH": os.environ["PATH"],
    }

    def run(cwd: Path, *args: str, extra: dict[str, str] | None = None):
        return sh([str(launcher), *args], cwd, {**env, **(extra or {})})

    # Outside a workspace: the host release, with no message.
    outside = tmp_path / "outside"
    outside.mkdir()
    host = run(outside, "--version")
    assert host.returncode == 0 and host.stdout.startswith("vendomat 0.6.0"), host.stderr
    assert host.stderr == ""

    # A new workspace has no lock: the host release bootstraps it, and says so.
    a = workspace(tmp_path, "a", port, "v0.6.0")
    b = workspace(tmp_path, "b", port, "v0.6.1")
    first_a = run(a, "sync")
    assert first_a.returncode == 0, first_a.stdout + first_a.stderr
    assert "bootstrap" in first_a.stderr
    assert run(b, "sync").returncode == 0
    assert (a / "devenv.lock").is_file() and (b / "devenv.lock").is_file()

    # Two workspaces on different tags each run their own build.
    va = run(a, "--version")
    vb = run(b, "--version")
    assert va.stdout.strip() == "vendomat 0.6.0", va.stderr
    assert vb.stdout.strip() == "vendomat 0.6.1", vb.stderr

    # With the network off and the cache empty, the pinned builds are found by NAR hash in the store.
    daemon.terminate()
    daemon.wait(timeout=10)
    shutil.rmtree(cache)
    again_a = run(a, "--version")
    again_b = run(b, "--version")
    assert again_a.stdout.strip() == "vendomat 0.6.0", again_a.stderr
    assert again_b.stdout.strip() == "vendomat 0.6.1", again_b.stderr
    assert "host release" not in again_a.stderr

    # `check` reaches the pinned build: a branch pin is named.
    checked = run(a, "check", "--no-version")
    assert checked.returncode == 0, checked.stderr

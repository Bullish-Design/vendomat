"""`vendomat sync` for a devenv workspace, against real Nix and a real `devenv` (Step 2).

Opt in with `testee check e2e`. The fixture builds four local Git repositories, each with a tag,
then runs the real `sync` and the real `devenv`. It proves that a three-level imported-input chain
locks one node per source, that every stale case is named, that an unchanged workspace does no
work, that a failed update keeps the prior lock, and that sources need not be reachable once the
fragment is current.

The host `devenv` must be 2.4.0 or later. The check uses `VENDOMAT_DEVENV` when set.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from vendomat.defaults import DEFAULT_NIXPKGS_URL

DEVENV = os.environ.get("VENDOMAT_DEVENV") or shutil.which("devenv")
ENABLED = os.environ.get("VENDOMAT_E2E") == "1" and all(shutil.which(t) for t in ("nix", "git")) and bool(DEVENV)

pytestmark = pytest.mark.skipif(not ENABLED, reason="Nix and devenv fixture; set VENDOMAT_E2E=1 to opt in")

GIT = ["git", "-c", "user.email=fixture@example.invalid", "-c", "user.name=fixture", "-c", "commit.gpgsign=false"]


def sh(argv: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 900):
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=full)


def make_repo(root: Path, name: str, files: dict[str, str]) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(text))
    assert sh(["git", "init", "-q", "-b", "main"], repo).returncode == 0
    assert sh(["git", "add", "-A"], repo).returncode == 0
    assert sh([*GIT, "commit", "-q", "-m", "release"], repo).returncode == 0
    assert sh([*GIT, "tag", "v1"], repo).returncode == 0
    return repo


def flake(shared_url: str) -> str:
    return f'{{ inputs.shared.url = "{shared_url}"; outputs = {{ self, shared }}: {{ }}; }}\n'


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Fixture:
    """Four tagged repositories served by `git daemon` on loopback: the production `git://` route."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.repos = tmp / "repos"
        self.port = free_port()
        self.daemon: subprocess.Popen[bytes] | None = None
        base = f"git://127.0.0.1:{self.port}"
        self.forge = base
        url = lambda name: f"{base}/{name}?ref=refs/tags/v1"  # noqa: E731
        make_repo(self.repos, "shared", {"flake.nix": "{ outputs = { self }: { }; }\n"})
        make_repo(self.repos, "leaf", {"marker.txt": "leaf\n"})
        for name, child in (("lib-c", "leaf"), ("lib-b", "lib-c"), ("lib-a", "lib-b")):
            flake_attrs = " flake: false" if child == "leaf" else ""
            make_repo(
                self.repos,
                name,
                {
                    "flake.nix": flake(url("shared")),
                    "devenv/devenv.nix": "{ ... }: { }\n",
                    "devenv/devenv.yaml": (
                        f'inputs:\n  {child}: {{ url: "{url(child)}",{flake_attrs} }}\n'.replace(",  }", " }")
                        + (f"imports:\n  - {child}/devenv\n" if child != "leaf" else "")
                    ),
                },
            )
        self.ws = tmp / "ws"
        self.ws.mkdir()
        (self.ws / "devenv.yaml").write_text("imports:\n  - ./.vendomat\n")
        (self.ws / "devenv.nix").write_text("{ ... }: { }\n")
        self.write_registry()
        self.env = {"VENDOMAT_DEVENV": str(DEVENV), "HOME": os.environ["HOME"]}
        self.start()

    def start(self) -> None:
        self.daemon = subprocess.Popen(
            [
                "git",
                "daemon",
                "--reuseaddr",
                "--export-all",
                f"--base-path={self.repos}",
                "--listen=127.0.0.1",
                f"--port={self.port}",
                str(self.repos),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            probe = subprocess.run(
                ["git", "ls-remote", f"{self.forge}/shared"], capture_output=True, text=True, timeout=10
            )
            if probe.returncode == 0:
                return
            time.sleep(0.2)
        raise AssertionError("git daemon did not start")

    def stop(self) -> None:
        if self.daemon is not None:
            self.daemon.terminate()
            self.daemon.wait(timeout=10)
            self.daemon = None

    def write_registry(self, extra: str = "", comment: str = "") -> None:
        (self.ws / "vendomat.toml").write_text(
            textwrap.dedent(
                f"""\
                {comment}
                [forge]
                url = "{self.forge}"

                [targets]
                devenv = true

                [inputs]
                lib-a = {{ ref = "refs/tags/v1" }}
                shared = {{ ref = "refs/tags/v1" }}
                {extra}

                [imports]
                lib-a = "devenv"
                """
            )
        )

    def sync(self, *extra: str):
        return sh([sys.executable, "-m", "vendomat.cli", "sync", "--root", str(self.ws), *extra], self.ws, self.env)

    def devenv(self, *args: str):
        return sh([str(DEVENV), "--no-eval-cache", *args], self.ws, self.env)

    def shell_true(self):
        """Enter the shell and leave. devenv evaluates assertions here, and not for `info` or `build`."""
        return self.devenv("shell", "--", "true")

    def lock(self) -> dict:
        return json.loads((self.ws / "devenv.lock").read_text())


def log(name: str, text: str) -> None:
    directory = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        (Path(directory) / f"{name}.txt").write_text(text)


def test_the_whole_sync_story(tmp_path):
    fx = Fixture(tmp_path)
    try:
        run_story(fx, tmp_path)
    finally:
        fx.stop()


def run_story(fx: Fixture, tmp_path: Path) -> None:

    # 1. A new workspace with no lock: sync writes the fragment and asks devenv to lock it.
    first = fx.sync()
    log("01-first-sync", first.stdout + first.stderr)
    assert first.returncode == 0, first.stdout + first.stderr
    assert "wrote .vendomat/" in first.stdout
    assert "devenv.lock updated" in first.stdout
    fragment = (fx.ws / ".vendomat" / "devenv.yaml").read_text()
    for name in ("lib-a", "lib-b", "lib-c", "leaf", "shared", "nixpkgs"):
        assert f"\n  {name}:\n" in fragment, name
    assert 'follows: "shared"' in fragment
    assert DEFAULT_NIXPKGS_URL in fragment

    # 2. The lock holds one node per source, though four flakes declare `shared`.
    nodes = fx.lock()["nodes"]
    sources = [n["original"]["url"] for k, n in nodes.items() if k != "root" and n.get("original", {}).get("url")]
    assert sum(1 for u in sources if u.endswith("/shared")) == 1, sources
    for key in ("lib-a", "lib-b", "lib-c", "leaf", "shared"):
        assert len(nodes[key]["locked"]["rev"]) == 40, key
    assert len(sources) == len(set(sources)), f"a source has two lock nodes: {sources}"

    # 3. The shell evaluates, including the module's assertions.
    entered = fx.devenv("info")
    log("03-devenv-info", entered.stdout + entered.stderr)
    assert entered.returncode == 0, entered.stderr[-2000:]

    # 4. Unchanged: no work, and no source needs to be reachable.
    fx.stop()
    try:
        before = {p.name: p.stat().st_mtime_ns for p in (fx.ws / ".vendomat").iterdir()}
        started = time.monotonic()
        warm = fx.sync()
        elapsed = time.monotonic() - started
        log("04-warm-sync", f"{elapsed:.3f} s\n{warm.stdout}{warm.stderr}")
        assert warm.returncode == 0, warm.stdout + warm.stderr
        assert "unchanged .vendomat/" in warm.stdout
        assert before == {p.name: p.stat().st_mtime_ns for p in (fx.ws / ".vendomat").iterdir()}
    finally:
        fx.start()

    # 5. A registry edit without a sync stops the shell and names the cause.
    fx.write_registry(comment="# edited")
    stale = fx.shell_true()
    assert stale.returncode != 0
    assert "STALE" in stale.stderr and "vendomat.toml" in stale.stderr
    resynced = fx.sync()
    assert resynced.returncode == 0, resynced.stdout + resynced.stderr
    assert fx.shell_true().returncode == 0

    # 6. A hand edit of the fragment is named, and sync repairs it.
    fragment_path = fx.ws / ".vendomat" / "devenv.yaml"
    fragment_path.write_text(fragment_path.read_text() + "# by hand\n")
    edited = fx.shell_true()
    assert edited.returncode != 0 and "edited by hand" in edited.stderr
    assert fx.sync().returncode == 0
    assert "by hand" not in fragment_path.read_text()

    # 7. A failed update (`devenv update` exits 0 on a fetch error) keeps the prior lock.
    prior_lock = (fx.ws / "devenv.lock").read_bytes()
    prior_fragment = fragment_path.read_bytes()
    fx.write_registry(extra='ghost = { ref = "refs/tags/v1", flake = false }')
    failed = fx.sync()
    log("07-failed-update", failed.stdout + failed.stderr)
    assert failed.returncode == 2, failed.stdout + failed.stderr
    assert "ghost" in failed.stderr
    assert (fx.ws / "devenv.lock").read_bytes() == prior_lock
    assert fragment_path.read_bytes() == prior_fragment
    again = fx.shell_true()
    assert again.returncode != 0 and "STALE" in again.stderr  # the registry moved; the fragment did not

    # 8. Restore the registry: the workspace is usable again.
    fx.write_registry(comment="# edited")
    assert fx.sync().returncode == 0
    assert fx.shell_true().returncode == 0

"""Helpers for the Nix fixtures.

The fixtures run pinned Nix against a disposable workspace. They need the network once to
fetch the pinned Nixpkgs, then use the local fetcher cache. They are opt-in:

    testee verify e2e

Set ``VENDOMAT_FIXTURE_LOGS`` to a directory outside the repository to keep every command,
its exit status, and its output. A fixture never writes a credential. The Testee shell drops host
variables, so the variable reaches the fixtures only if the `e2e` check in `devenv.nix` sets it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


def s1_devenv_input(override: str | None = None) -> tuple[str, str]:
    """The `devenv` input of the fixtures: ``(flake URL, label)``.

    The default is the input that `flake.lock` of this repository pins (the published S1 tag), so the default
    follows S1 releases. A non-empty ``override`` is a ``src/modules`` directory and gives a ``path:`` input.
    """
    if override:
        return f"path:{Path(override).resolve()}", f"path:{Path(override).resolve()} (override)"
    root = Path(__file__).resolve().parents[1]
    locked = json.loads((root / "flake.lock").read_text())["nodes"]["devenv"]["locked"]
    url = f"{locked['url']}?dir={locked['dir']}&ref={locked['ref']}&rev={locked['rev']}"
    return url, f"{locked['ref'].removeprefix('refs/tags/')} rev {locked['rev'][:8]} ({url})"


needs_nix_fixture = pytest.mark.skipif(
    os.environ.get("VENDOMAT_E2E") != "1" or shutil.which("nix") is None or shutil.which("git") is None,
    reason="Nix fixture; set VENDOMAT_E2E=1 and provide nix and git to opt in",
)

_LOG_COUNTER = {"n": 0}


@dataclass
class Result:
    argv: list[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    @property
    def warnings(self) -> list[str]:
        """Nix warnings, minus the expected notice that Nix created a lock file."""
        found = [ln for ln in self.stderr.splitlines() if ln.startswith("warning:")]
        return [ln for ln in found if "creating lock file" not in ln]

    @property
    def error_text(self) -> str:
        return self.stderr


def run(argv: list[str], cwd: Path, *, timeout: int = 900, env: dict[str, str] | None = None) -> Result:
    """Run a command and, when asked, keep its raw record outside the repository."""
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    result = Result(argv, cwd, proc.returncode, proc.stdout, proc.stderr)
    log_dir = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if log_dir:
        _LOG_COUNTER["n"] += 1
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        record = {"argv": argv, "cwd": str(cwd), "returncode": proc.returncode}
        stem = f"{os.getpid()}-{_LOG_COUNTER['n']:04d}"
        (directory / f"{stem}.json").write_text(json.dumps(record, indent=1) + "\n")
        (directory / f"{stem}.stdout").write_text(proc.stdout)
        (directory / f"{stem}.stderr").write_text(proc.stderr)
    return result


def nix(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> Result:
    return run(["nix", *args], cwd, env=env)

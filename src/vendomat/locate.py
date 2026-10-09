"""Find the store path of a locked direct input (``CLI-007``).

The path comes from Nix, not from ``flake.lock``: ``nix flake archive --json
--no-write-lock-file`` names the store path of every direct input, and it writes no lock file
(``CLI-004``, ``GEN-008``). This module never opens the lock or the registry.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

#: Seconds. Nix may have to fetch an input that is not in the store yet.
NIX_TIMEOUT = 600


class LocateError(Exception):
    """A refusal or a Nix failure. ``code`` is the CLI exit status."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def input_path(root: Path, name: str) -> str:
    """The store path of the locked source of the direct input ``name`` in the flake at ``root``."""

    if not (root / "flake.nix").is_file():
        raise LocateError(f"{root / 'flake.nix'}: no flake here; run `vendomat sync` first")
    inputs = _archive(root)
    if name not in inputs:
        known = ", ".join(sorted(inputs)) or "none"
        raise LocateError(f"unknown input '{name}'; known inputs: {known}", code=1)
    path = inputs[name].get("path")
    if not isinstance(path, str):
        raise LocateError(
            f"input '{name}' has no store path of its own; Nix keeps a path: input inside the project source", code=1
        )
    if not os.path.exists(path):
        raise LocateError(f"Nix named {path} for input '{name}', but it is not in the store")
    return path


def _archive(root: Path) -> dict[str, dict]:
    argv = ["nix", "flake", "archive", "--json", "--no-write-lock-file", "."]
    try:
        done = subprocess.run(
            argv, cwd=root, capture_output=True, text=True, timeout=NIX_TIMEOUT, stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired as exc:
        raise LocateError(f"nix flake archive timed out after {exc.timeout:.0f} s") from exc
    except OSError as exc:
        raise LocateError(f"cannot run nix: {exc.strerror or exc}") from exc
    if done.returncode != 0:
        tail = "\n".join(done.stderr.strip().splitlines()[-5:])
        raise LocateError(f"nix flake archive failed (status {done.returncode}):\n{tail}")
    try:
        data = json.loads(done.stdout)
        inputs = data["inputs"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LocateError("nix flake archive printed no input list") from exc
    if not isinstance(inputs, dict):
        raise LocateError("nix flake archive printed no input list")
    return inputs

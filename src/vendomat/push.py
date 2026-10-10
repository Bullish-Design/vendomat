"""``vendomat push``: check, build with devenv, then pipe the store paths to ``attic push`` (``VMOD-006``).

devenv runs nothing after ``devenv build``, so the push is an explicit command. The check runs
first, because ``devenv build`` does not evaluate assertions (``NAT-025``). A failed check pushes
nothing.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .check import Problem, check_workspace


class PushError(Exception):
    """A refusal or a fault. ``code`` is the CLI exit status: 1 needs a decision, 2 is a fault."""

    def __init__(self, message: str, code: int = 2, problems: list[Problem] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.problems = problems or []


@dataclass(frozen=True)
class PushResult:
    cache: str
    paths: tuple[str, ...]
    pushed: bool
    attic_output: str = ""


def parse_paths(output: str) -> list[str]:
    """Store paths from ``devenv build`` output: a JSON list or object, or one path per line."""

    text = output.strip()
    found: list[str] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, list):
        found = [item for item in data if isinstance(item, str)]
    elif isinstance(data, dict):
        found = [value for value in data.values() if isinstance(value, str)]
    else:
        found = [line.strip() for line in text.splitlines() if line.strip().startswith("/nix/store/")]
    return [p for p in found if p.startswith("/nix/store/")]


def build_attrs(machine: str | None, attrs: list[str]) -> list[str]:
    out = list(attrs)
    if machine:
        out.append(f"machines.{machine}.build.nixos")
    return out


def push(
    root: Path,
    cache: str,
    *,
    machine: str | None = None,
    attrs: list[str] | None = None,
    dry_run: bool = False,
    devenv_cmd: str | None = None,
    attic_cmd: str | None = None,
    check_version: bool = True,
) -> PushResult:
    devenv = devenv_cmd or os.environ.get("VENDOMAT_DEVENV", "devenv")
    attic = attic_cmd or os.environ.get("VENDOMAT_ATTIC", "attic")
    problems = check_workspace(root, devenv, check_version=check_version)
    if problems:
        raise PushError(
            "the workspace failed `vendomat check`; nothing was built or pushed:\n  "
            + "\n  ".join(p.line() for p in problems),
            code=1,
            problems=problems,
        )
    argv = [devenv, "build", *build_attrs(machine, attrs or [])]
    try:
        built = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=7200, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PushError(f"cannot run `{' '.join(argv)}`: {exc}") from exc
    if built.returncode != 0:
        tail = "\n".join(built.stderr.strip().splitlines()[-6:])
        raise PushError(f"`{' '.join(argv)}` failed (exit {built.returncode}); nothing was pushed:\n{tail}")
    paths = parse_paths(built.stdout)
    if not paths:
        raise PushError(f"`{' '.join(argv)}` printed no store path; nothing was pushed")
    if dry_run:
        return PushResult(cache, tuple(paths), pushed=False)
    try:
        sent = subprocess.run(
            [attic, "push", cache, "--stdin"],
            input="\n".join(paths) + "\n",
            capture_output=True,
            text=True,
            timeout=7200,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PushError(f"cannot run `{attic} push {cache} --stdin`: {exc}") from exc
    if sent.returncode != 0:
        tail = "\n".join((sent.stdout + sent.stderr).strip().splitlines()[-6:])
        raise PushError(f"`{attic} push {cache} --stdin` failed (exit {sent.returncode}):\n{tail}")
    return PushResult(cache, tuple(paths), pushed=True, attic_output=(sent.stdout + sent.stderr).strip())

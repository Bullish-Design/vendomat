"""``vendomat machine install``: a fresh install of one host, through the patched devenv (``MACH-008``).

The command is a second guard. The patched ``devenv machines install`` already refuses an adopted
host and runs the target-side preflight itself (``DVN-009``, ``MACH-021``). This module adds the
checks that only the controller can make, then runs exactly one command:

    devenv machines install <host> --phases disko,install

It offers no option for the phases or for the disko mode, so ``format`` and ``mount`` cannot be
selected through it. It never wraps ``plan``, ``apply``, ``deploy``, ``status``, or ``rollback``
(``MACH-005``). It does not reboot.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .check import Problem, check_workspace

PHASES = "disko,install"
DEVENV_TIMEOUT = 7200


class MachineError(Exception):
    """A refusal or a fault. ``code`` is the CLI exit status: 1 needs a decision, 2 is a fault."""

    def __init__(self, message: str, code: int = 1, problems: list[Problem] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.problems = problems or []


@dataclass
class InstallPlan:
    host: str
    mode: str
    argv: list[str]
    unmount: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _devenv_json(devenv: str, root: Path, attr: str) -> Any:
    """Evaluate one attribute with ``devenv eval`` and return its JSON value."""

    try:
        done = subprocess.run(
            [devenv, "eval", attr], cwd=root, capture_output=True, text=True, timeout=900, stdin=subprocess.DEVNULL
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MachineError(f"cannot run `{devenv} eval {attr}`: {exc}", code=2) from exc
    if done.returncode != 0:
        tail = "\n".join(done.stderr.strip().splitlines()[-6:])
        raise MachineError(f"`{devenv} eval {attr}` failed (exit {done.returncode}):\n{tail}", code=2)
    try:
        return json.loads(done.stdout)[attr]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise MachineError(f"`{devenv} eval {attr}` printed no value for {attr}", code=2) from exc


def facter_report(root: Path, host: str) -> Path:
    return root / ".machines" / host / "facter.json"


def _tracked(root: Path, path: Path) -> bool | None:
    """``True`` when version control tracks the file, ``False`` when it does not, ``None`` when unknown."""

    rel = str(path.relative_to(root))
    for argv in (["jj", "file", "list", rel], ["git", "ls-files", "--error-unmatch", rel]):
        try:
            done = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if argv[0] == "jj":
            if done.returncode == 0:
                return rel in done.stdout.split()
            continue
        if done.returncode == 0:
            return True
        # Exit 1 is "pathspec did not match": a repository that does not track the file.
        # Any other status (128: not a repository) says nothing about the file.
        return False if done.returncode == 1 else None
    return None


def plan_install(root: Path, host: str, devenv_cmd: str | None = None, check_version: bool = True) -> InstallPlan:
    """Run every controller-side check. Return the single command, or raise ``MachineError``."""

    devenv = devenv_cmd or os.environ.get("VENDOMAT_DEVENV", "devenv")
    problems = check_workspace(root, devenv, check_version=check_version)
    if problems:
        raise MachineError(
            "the workspace failed `vendomat check`; nothing ran:\n  " + "\n  ".join(p.line() for p in problems),
            code=1,
            problems=problems,
        )
    modes = _devenv_json(devenv, root, "vendomat.modes")
    if not isinstance(modes, dict) or host not in modes:
        known = ", ".join(sorted(modes)) if isinstance(modes, dict) else "none"
        raise MachineError(f"host '{host}' is not in vendomat.inventory; known hosts: {known or 'none'}")
    mode = modes[host]
    if mode != "fresh-install":
        raise MachineError(
            f"host '{host}' has mode '{mode}'. `machine install` runs only for a fresh-install host. "
            "Adopt an existing host with `devenv machines plan` and `apply`."
        )
    notes: list[str] = []
    report = facter_report(root, host)
    if not report.is_file():
        facter = _devenv_json(devenv, root, f"machines.{host}.hardware.facter")
        if facter is not None:
            raise MachineError(
                f"{report.relative_to(root)} is missing. Commit a nixos-facter report for {host}, "
                "or set hardware.facter = null and keep an explicit hardware module"
            )
        notes.append("hardware.facter is null; no facter report is needed")
    else:
        tracked = _tracked(root, report)
        if tracked is False:
            raise MachineError(f"{report.relative_to(root)} exists but is not committed; commit it first")
        if tracked is None:
            notes.append("could not tell whether the facter report is committed (no jj or git answered)")
    target = _devenv_json(devenv, root, f"machines.{host}.target.host")
    unmount: list[str] = []
    if isinstance(target, str) and target:
        unmount = ["ssh", "-o", "BatchMode=yes", target, "umount -R /mnt"]
    argv = [devenv, "machines", "install", host, "--phases", PHASES]
    return InstallPlan(host=host, mode=mode, argv=argv, unmount=unmount, notes=notes)


def run_install(plan: InstallPlan, root: Path) -> tuple[int, int | None]:
    """Run the install, then unmount ``/mnt`` on the target. Return ``(install exit, unmount exit)``."""

    done = subprocess.run(plan.argv, cwd=root, timeout=DEVENV_TIMEOUT, stdin=subprocess.DEVNULL)
    unmounted: int | None = None
    if plan.unmount:
        # Run it even when the install failed: a half-installed /mnt must not stay mounted.
        try:
            unmounted = subprocess.run(
                plan.unmount, cwd=root, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL
            ).returncode
        except (OSError, subprocess.TimeoutExpired):
            unmounted = 124
    return done.returncode, unmounted

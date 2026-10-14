#!/usr/bin/env python3
"""Delete the regenerable leftovers of this repository: Testee venvs, stale slots, and caches.

The default is a dry run. It prints each path it would delete, with its size, and the total.
Add `--yes` to delete. The script uses only the standard library.

What it deletes, for this repository only:

- A Testee slot whose workspace no longer exists. Testee recreates a slot on the next run.
- The venv and the caches inside each other idle Testee slot. The `setup:sync` task runs
  `uv sync --locked`, which rebuilds the venv on the next run.
- `__pycache__`, `.pytest_cache`, and `.ruff_cache` directories in the working copy.
- Dangling `result*` symlinks at the repository root.

Then it runs `testee gc` for this repository.

What it never deletes: `.worktrees/`, the venv of the working copy (`.devenv/`), tracked files,
verdicts, plans, attempts, a slot that Testee marks busy, the state of another repository, raw logs,
or the Nix store. It never runs a Nix or devenv garbage collection.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

CACHE_NAMES = ("__pycache__", ".pytest_cache", ".ruff_cache")
#: Directories the cache search never enters.
SKIP_DIRS = {".devenv", ".direnv", ".worktrees", ".git", ".jj", ".gitman", "node_modules"}


@dataclass
class Item:
    """One path to delete."""

    path: Path
    size: int
    why: str
    #: The Testee slot directory that owns the path. Its lock guards the delete.
    slot: Path | None = None


@dataclass
class Plan:
    items: list[Item] = field(default_factory=list)
    #: Slot directories that go away whole. Git keeps a worktree record for each.
    stale_slots: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Refusal(Exception):
    """The script cannot continue safely."""


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def tree_size(path: Path) -> int:
    """Return the disk use of a path. Count each inode once. Do not follow symlinks."""
    seen: set[tuple[int, int]] = set()
    total = 0

    def add(entry: Path) -> None:
        nonlocal total
        try:
            info = entry.lstat()
        except OSError:
            return
        key = (info.st_dev, info.st_ino)
        if key not in seen:
            seen.add(key)
            total += info.st_blocks * 512

    add(path)
    if path.is_dir() and not path.is_symlink():
        for base, dirs, files in os.walk(path):
            for name in (*dirs, *files):
                add(Path(base) / name)
    return total


def run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def git_common_dir(root: Path) -> Path:
    result = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root)
    if result.returncode:
        raise Refusal(f"{root} is not inside a Git repository: {result.stderr.strip()}")
    return Path(result.stdout.strip()).resolve()


def state_dir(explicit: str | None) -> Path:
    """Find the Testee state directory the way Testee does."""
    if explicit:
        return Path(explicit)
    if os.environ.get("TESTEE_STATE_DIR"):
        return Path(os.environ["TESTEE_STATE_DIR"])
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "testee"


def repo_state_dirs(state: Path, common: Path) -> list[Path]:
    """Return each Testee repository directory whose `repo.json` names this Git directory."""
    found: list[Path] = []
    for info in sorted((state / "repos").glob("*/repo.json")):
        try:
            recorded = Path(json.loads(info.read_text())["common_dir"]).resolve()
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if recorded == common:
            found.append(info.parent)
    return found


def jj_workspaces(root: Path) -> list[tuple[str, Path]] | None:
    """Return the jj workspaces as (name, root path). Return None when jj cannot answer."""
    base = ["jj", "--ignore-working-copy", "-R", str(root)]
    try:
        listing = run([*base, "workspace", "list", "-T", 'name ++ "\\n"'])
    except OSError:
        return None
    if listing.returncode:
        return None
    found: list[tuple[str, Path]] = []
    for name in listing.stdout.split():
        where = run([*base, "workspace", "root", "--name", name])
        if where.returncode:
            return None
        found.append((name, Path(where.stdout.strip())))
    return found


def slot_name(toplevel: Path) -> str:
    """Name the slot of a working copy. This matches Testee's rule in `testee.runner.repo`."""
    name = re.sub(r"[^A-Za-z0-9._-]", "-", toplevel.name)[:40] or "root"
    return f"{name}-{hashlib.sha256(str(toplevel).encode()).hexdigest()[:8]}"


def is_busy(slot_dir: Path) -> bool:
    """Return True when a process holds the slot lock, as `testee gc` tests it."""
    try:
        fd = os.open(slot_dir / "lock", os.O_RDONLY)
    except FileNotFoundError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(fd)
    return False


def tracked_paths(root: Path) -> set[str]:
    result = run(["git", "ls-files", "-z"], root)
    if result.returncode:
        raise Refusal(f"cannot list tracked files in {root}: {result.stderr.strip()}")
    return {name for name in result.stdout.split("\0") if name}


def find_caches(top: Path, tracked: set[str] | None) -> list[Path]:
    """List the cache directories under `top`. Skip `SKIP_DIRS` and any directory with a tracked file."""
    found: list[Path] = []
    for base, dirs, _files in os.walk(top):
        here = Path(base)
        keep: list[str] = []
        for name in sorted(dirs):
            path = here / name
            if name in SKIP_DIRS or path.is_symlink():
                continue
            if name in CACHE_NAMES:
                prefix = path.relative_to(top).as_posix() + "/"
                if tracked is None or not any(item.startswith(prefix) for item in tracked):
                    found.append(path)
                continue
            keep.append(name)
        dirs[:] = keep
    return found


def plan_slot(slot_dir: Path, live_roots: set[Path] | None, live_names: set[str], plan: Plan) -> None:
    ws = slot_dir / "ws"
    if is_busy(slot_dir):
        plan.notes.append(f"skip busy slot: {slot_dir}")
        return
    if ws.exists() and not (ws / ".git").is_file():
        plan.notes.append(f"skip slot with a workspace that is not a Testee worktree: {slot_dir}")
        return
    try:
        recorded = Path(json.loads((slot_dir / "slot.json").read_text())["toplevel"])
    except (OSError, ValueError, KeyError, TypeError):
        recorded = None
    if live_roots is None:
        # jj cannot answer. Only a missing working copy proves that a slot is stale.
        stale = recorded is not None and not recorded.exists()
    else:
        stale = slot_dir.name not in live_names and (recorded is None or recorded.resolve() not in live_roots)
    if stale:
        plan.items.append(Item(slot_dir, tree_size(slot_dir), "stale Testee slot (workspace gone)", slot_dir))
        plan.stale_slots.append(slot_dir)
        return
    venv = ws / ".devenv" / "state" / "venv"
    if venv.is_dir() and not venv.is_symlink():
        why = "venv in idle Testee slot (setup:sync rebuilds it)"
        plan.items.append(Item(venv, tree_size(venv), why, slot_dir))
    if ws.is_dir():
        for cache in find_caches(ws, None):
            plan.items.append(Item(cache, tree_size(cache), "cache in idle Testee slot", slot_dir))


def plan_root(root: Path, plan: Plan) -> None:
    tracked = tracked_paths(root)
    for cache in find_caches(root, tracked):
        plan.items.append(Item(cache, tree_size(cache), "cache in the working copy"))
    for link in sorted(root.glob("result*")):
        if link.is_symlink() and not link.exists():
            plan.items.append(Item(link, 0, "dangling result symlink"))


def report_worktrees(roots: list[Path], plan: Plan) -> None:
    for root in roots:
        base = root / ".worktrees"
        if not base.is_dir():
            continue
        for entry in sorted(path for path in base.iterdir() if path.is_dir()):
            plan.notes.append(
                f"keep {entry} ({human(tree_size(entry))}): a Git worktree that may hold unlanded work. "
                "Inspect it, then remove it by hand."
            )


def build_plan(args: argparse.Namespace, root: Path) -> Plan:
    plan = Plan()
    common = Path(args.common_dir).resolve() if args.common_dir else git_common_dir(root)
    if args.live_root is not None:
        workspaces: list[tuple[str, Path]] | None = [(path.name, path) for path in map(Path, args.live_root)]
    else:
        workspaces = jj_workspaces(root)
    live_roots: set[Path] | None
    if workspaces is None:
        live_roots = None
        plan.warnings.append("jj gave no workspace list. Only slots with a missing working copy count as stale.")
    else:
        live_roots = {root}
        for name, path in workspaces:
            if path.is_dir():
                live_roots.add(path.resolve())
            else:
                plan.notes.append(f"jj workspace {name!r} points to a missing directory: {path}")
    live_names = {slot_name(path) for path in live_roots or ()}

    state = state_dir(args.state_dir)
    state_dirs = repo_state_dirs(state, common)
    if not state_dirs:
        plan.notes.append(f"no Testee state for {common} under {state}")
    for repo_dir in state_dirs:
        for slot_dir in sorted((repo_dir / "slots").glob("*")):
            if slot_dir.is_dir() and not slot_dir.is_symlink():
                plan_slot(slot_dir, live_roots, live_names, plan)
    plan_root(root, plan)
    report_worktrees(sorted(live_roots or {root}), plan)
    return plan


def delete(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def remove_item(item: Item) -> str | None:
    """Delete one item. Return an error text, or None. Hold the slot lock while a slot goes."""
    fd = None
    try:
        if item.slot is not None and (item.slot / "lock").exists():
            fd = os.open(item.slot / "lock", os.O_RDONLY)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return f"skip busy slot: {item.slot}"
        delete(item.path)
    except OSError as exc:
        return f"error: {item.path}: {exc}"
    finally:
        if fd is not None:
            os.close(fd)
    return None


def prune_git(root: Path, slot_dirs: list[Path]) -> None:
    """Drop the Git worktree records and refs of the deleted slots, as `Slot.remove` does."""
    run(["git", "worktree", "prune"], root)
    for slot_dir in slot_dirs:
        run(["git", "update-ref", "-d", f"refs/testee/slots/{slot_dir.name}"], root)


def default_testee() -> str | None:
    host = Path.home() / ".nix-profile" / "bin" / "testee"
    return str(host) if host.exists() else shutil.which("testee")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cleanup",
        description="Delete Testee venvs, stale Testee slots, and caches of this repository. The default is a dry run.",
    )
    parser.add_argument("--yes", action="store_true", help="delete the paths (default: print them only)")
    parser.add_argument("--root", default=".", help="repository working copy (default: the current directory)")
    parser.add_argument("--state-dir", help="Testee state directory (default: Testee's own rule)")
    parser.add_argument("--common-dir", help="Git common directory of the repository (default: ask Git)")
    parser.add_argument(
        "--live-root",
        action="append",
        help="a live workspace root; repeat it. Skips jj. Meant for tests",
    )
    parser.add_argument("--testee", help="the testee command, or 'none' to skip `testee gc`")
    args = parser.parse_args(argv)

    try:
        root = Path(args.root).resolve(strict=True)
        plan = build_plan(args, root)
    except (Refusal, OSError) as exc:
        print(f"cleanup: refused: {exc}", file=sys.stderr)
        return 2

    mode = "delete" if args.yes else "dry run (add --yes to delete)"
    print(f"cleanup: {mode}")
    print(f"repository: {root}")
    for warning in plan.warnings:
        print(f"warning: {warning}")
    for item in plan.items:
        print(f"{'delete' if args.yes else 'would delete'}  {human(item.size):>10}  {item.path}  [{item.why}]")
    total = sum(item.size for item in plan.items)
    print(f"total: {human(total)} in {len(plan.items)} paths")
    for note in plan.notes:
        print(f"note: {note}")

    testee = args.testee or os.environ.get("TESTEE") or default_testee()
    gc = [] if testee in (None, "none") else [testee, "--root", str(root), "gc"]

    if not args.yes:
        if gc:
            print(f"would run: {' '.join(gc)}")
        return 0

    failed = 0
    for item in plan.items:
        message = remove_item(item)
        if message:
            print(message, file=sys.stderr)
            failed += message.startswith("error")
    prune_git(root, plan.stale_slots)
    if gc:
        result = run(gc)
        print((result.stdout + result.stderr).strip())
        failed += bool(result.returncode)
    print(f"cleanup: freed up to {human(total)}" + (f"; {failed} errors" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

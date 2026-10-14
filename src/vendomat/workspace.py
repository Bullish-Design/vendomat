"""The user's workspace, as ``vendomat apply`` and ``vendomat rollback`` see it.

A workspace made by ``vendomat new`` is a plain Git repository. These commands read and write it
with the ``git`` binary. A rollback ends in a commit, so Git gives the one history that every
machine and every clone shares (R30).

The watched files are the files that decide what a machine runs: ``vendomat.yaml``, ``devenv.lock``,
and the hatch files ``devenv.nix`` and ``devenv.local.nix``. A watched file that differs from the
commit counts as uncommitted. That covers an edit, a staged edit, a deleted file, an untracked
file, and an ignored file that exists, because none of them reaches another clone.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .record import RecordError

#: The files that decide what a machine runs. Extend this tuple when the catalog counts a new hatch file.
WATCHED = ("vendomat.yaml", "devenv.lock", "devenv.nix", "devenv.local.nix")

#: Root markers, strongest first.
ROOT_MARKERS = ("vendomat.yaml", "devenv.yaml")


class WorkspaceError(RecordError):
    """A fault or a refusal about the workspace. ``code`` is the CLI exit status."""


@dataclass(frozen=True)
class Change:
    """One watched file that differs from the commit, with the Git status code."""

    path: str
    status: str

    def text(self) -> str:
        return {
            "??": "untracked",
            "!!": "ignored",
            "D": "deleted",
            "A": "added",
            "M": "modified",
            "R": "renamed",
        }.get(self.status.strip() or "M", "modified") + f": {self.path}"


def find_root(start: Path) -> Path:
    """The nearest directory at or above ``start`` that holds ``vendomat.yaml`` or ``devenv.yaml``."""

    here = start.resolve()
    for marker in ROOT_MARKERS:
        for directory in (here, *here.parents):
            if (directory / marker).is_file():
                return directory
    raise WorkspaceError(f"no workspace here: {start} and its parents hold no vendomat.yaml or devenv.yaml", 3)


def git(root: Path, *args: str, check: bool = True, input: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``git`` in the workspace. A fault of Git is exit status 2."""

    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, input=input, check=False)
    except FileNotFoundError as exc:
        raise WorkspaceError("git is not on PATH", 2) from exc
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise WorkspaceError(f"git {' '.join(args)} failed: {detail}", 2)
    return proc


def head(root: Path) -> str:
    """The full id of the commit at HEAD."""

    proc = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", check=False)
    if proc.returncode != 0:
        raise WorkspaceError(f"{root} is not a Git repository with a commit; commit the workspace first", 2)
    return proc.stdout.strip()


def resolve(root: Path, rev: str) -> str:
    """The full id of a commit. An unknown name is a refusal."""

    proc = git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", check=False)
    if proc.returncode != 0:
        raise WorkspaceError(f"unknown commit {rev}: the repository does not hold it")
    return proc.stdout.strip()


def has_commit(root: Path, commit: str) -> bool:
    return git(root, "cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode == 0


def short(root: Path, commit: str) -> str:
    return git(root, "rev-parse", "--short=12", commit).stdout.strip()


def watched_changes(root: Path) -> list[Change]:
    """Watched files that differ from HEAD. An ignored file that exists counts."""

    proc = git(root, "status", "--porcelain", "--ignored=matching", "--untracked-files=all", "--", *WATCHED)
    changes: list[Change] = []
    for line in proc.stdout.splitlines():
        status, path = line[:2], line[3:].strip().strip('"')
        if path in WATCHED:
            changes.append(Change(path, status))
    return changes


def tree_changes(root: Path) -> list[str]:
    """Tracked files that differ from HEAD, as ``git status`` lines. Untracked files do not count."""

    return git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()


def diff_text(root: Path, rev: str, *, exact: bool) -> str:
    """The change that a restore from ``rev`` makes: the stat, then the patch."""

    paths = ["."] if exact else list(WATCHED)
    stat = git(root, "diff", "--no-color", "--stat", "HEAD", rev, "--", *paths).stdout
    patch = git(root, "diff", "--no-color", "HEAD", rev, "--", *paths).stdout
    return (stat + "\n" + patch).strip()


def restore(root: Path, rev: str, *, exact: bool) -> None:
    """Make the watched files (or every tracked file, for ``exact``) equal to ``rev``, in index and tree."""

    if exact:
        git(root, "restore", f"--source={rev}", "--staged", "--worktree", "--", ".")
        return
    for path in WATCHED:
        in_rev = git(root, "cat-file", "-e", f"{rev}:{path}", check=False).returncode == 0
        tracked = git(root, "ls-files", "--error-unmatch", "--", path, check=False).returncode == 0
        if in_rev:
            git(root, "restore", f"--source={rev}", "--staged", "--worktree", "--", path)
        elif tracked:
            git(root, "rm", "-q", "-f", "--", path)


def undo_restore(root: Path, *, exact: bool) -> None:
    """Return the index and the tree to HEAD after a failed rollback step."""

    if exact:
        git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", ".")
        return
    for path in WATCHED:
        in_head = git(root, "cat-file", "-e", f"HEAD:{path}", check=False).returncode == 0
        if in_head:
            git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", path)


def commit_restore(root: Path, message: str) -> str:
    """Commit the staged restore, even when it changes nothing, and return the new commit id."""

    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return head(root)

"""The user's workspace, as ``vendomat apply`` and ``vendomat rollback`` see it.

A workspace made by ``vendomat new`` is a plain Git repository. These commands read and write it
with the ``git`` binary. A rollback ends in a commit, so Git gives the one history that every
machine and every clone shares (R30).

The watched files are the files that decide what a machine runs: ``vendomat.yaml``, ``devenv.lock``,
and the hatch files ``devenv.nix`` and ``devenv.local.nix``. A watched file that differs from the
commit counts as a change. Apply commits those paths after a successful build; an ignored file must
be force-added first. ``--dirty`` skips that commit and marks the generation dirty.
"""

from __future__ import annotations

import hashlib
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


def _prefix(root: Path) -> str:
    """The path of ``root`` below the repository top, with a trailing slash. Empty at the top."""

    return git(root, "rev-parse", "--show-prefix").stdout.strip()


def watched_changes(root: Path) -> list[Change]:
    """Watched files that differ from HEAD. An ignored file that exists counts.

    ``git status`` names paths from the repository top, not from ``root``. A workspace may sit in a
    subdirectory, so the function strips the prefix of ``root``. A rename between watched files gives
    one change for each name.
    """

    proc = git(root, "status", "--porcelain", "-z", "--ignored=matching", "--untracked-files=all", "--", *WATCHED)
    prefix = _prefix(root)
    entries = proc.stdout.split("\0")
    changes: list[Change] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        names = [entry[3:]]
        if "R" in status or "C" in status:  # a rename or copy carries the old name next
            names.append(entries[index] if index < len(entries) else "")
            index += 1
        for name in names:
            if name.startswith(prefix) and name[len(prefix) :] in WATCHED:
                changes.append(Change(name[len(prefix) :], status))
    return changes


def fingerprint(root: Path) -> tuple[str, dict[str, str | None]]:
    """The commit at HEAD and the content hash of each watched file (``None`` for a missing file)."""

    hashes: dict[str, str | None] = {}
    for name in WATCHED:
        file = root / name
        hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
    return head(root), hashes


def require_commit_identity(root: Path) -> None:
    """Refuse when Git cannot name a committer, so that apply fails before the build and not after it.

    A detached HEAD is not a fault: a jj-colocated checkout is always detached. Git hooks stay on.
    """

    proc = git(root, "var", "GIT_COMMITTER_IDENT", check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise WorkspaceError(
            "git cannot name a committer, so apply cannot commit the configuration. "
            "Run `git config user.name NAME` and `git config user.email ADDRESS`, then apply again. "
            f"Nothing was built. Git said: {detail}"
        )


def refuse_ignored_watched(root: Path) -> None:
    """Ignored watched files must be explicitly force-added before they can be applied."""

    ignored = [change.path for change in watched_changes(root) if change.status == "!!"]
    if ignored:
        names = ", ".join(ignored)
        raise WorkspaceError(
            f"ignored configuration file(s) are present: {names}. Force-add them with `git add -f`, "
            "or remove them before applying."
        )


def _tracked(root: Path, path: str) -> bool:
    return git(root, "ls-files", "--error-unmatch", "--", path, check=False).returncode == 0


def _commit_paths(root: Path, changes: list[Change]) -> tuple[str, ...]:
    """Return changed watched paths, or one tracked path for an empty rollback commit."""

    paths = tuple(dict.fromkeys(change.path for change in changes))
    if paths:
        return paths
    for path in WATCHED:
        if _tracked(root, path):
            return (path,)
    raise WorkspaceError("the workspace has no tracked configuration path to commit")


def commit_watched(root: Path, message: str = "vendomat apply configuration") -> str:
    """Commit the current allowlisted workspace configuration without committing other staged files."""

    refuse_ignored_watched(root)
    changes = watched_changes(root)
    if not changes:
        return head(root)
    paths = _commit_paths(root, changes)
    # `git add` stops on a pathspec that matches nothing. The old name of a staged rename is such a path:
    # it is gone from the tree and the index, and the rename already staged its deletion.
    present = [path for path in paths if (root / path).exists() or _tracked(root, path)]
    if present:
        git(root, "add", "-A", "--", *present)
    # A staged change that the tree reverted (`MM`), or an added then deleted file (`AD`), leaves the
    # paths equal to HEAD. `git commit --only` would exit 1 then, so make no commit.
    differs = git(root, "diff", "--cached", "--quiet", "HEAD", "--", *paths, check=False)
    if differs.returncode == 0:
        return head(root)
    if differs.returncode != 1:
        raise WorkspaceError(f"git diff --cached failed: {(differs.stderr or differs.stdout).strip()}", 2)
    git(root, "commit", "--quiet", "--only", "-m", message, "--", *paths)
    return head(root)


def tree_changes(root: Path) -> list[str]:
    """Tracked files that differ from HEAD, as ``git status`` lines. Untracked files do not count."""

    # `-- .` limits the list to the workspace directory, the same scope as the `--exact` restore.
    return git(root, "status", "--porcelain", "--untracked-files=no", "--", ".").stdout.splitlines()


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
        tracked = _tracked(root, path)
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


def commit_restore(root: Path, message: str, *, exact: bool = False) -> str:
    """Commit a restore, keeping unrelated staged files out of a watched-file rollback."""

    if exact:
        git(root, "commit", "-q", "--allow-empty", "-m", message)
    else:
        paths = _commit_paths(root, watched_changes(root))
        git(root, "commit", "-q", "--allow-empty", "--only", "-m", message, "--", *paths)
    return head(root)

"""The user's workspace, as ``vendomat apply`` and ``vendomat rollback`` see it.

A workspace made by ``vendomat new`` is a plain Git repository. These commands read and write it
with the ``git`` binary. A rollback ends in a commit, so Git gives the one history that every
machine and every clone shares (R30).

A record is always a whole commit (R55, ``VMT-182``). The watched files are the four files that
apply commits: ``vendomat.yaml``, ``devenv.lock``, and the hatch files ``devenv.nix`` and
``devenv.local.nix``. A module can add more files with the option ``vendomat.watch`` (R62, ``VMT-280``).
Apply commits those paths after a successful build; an ignored one must be force-added first. Any
other uncommitted change under the workspace root, tracked or new, stops apply before the build.
Git-ignored files and the cache key file that apply writes do not count.
``--dirty`` skips the commit, allows other changes, and marks the generation dirty. Rollback
restores the whole workspace tree.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .record import RecordError

#: The files that decide what a machine runs. A module adds more with the option ``vendomat.watch`` (R62).
WATCHED = ("vendomat.yaml", "devenv.lock", "devenv.nix", "devenv.local.nix")

#: Root markers, strongest first.
ROOT_MARKERS = ("vendomat.yaml", "devenv.yaml")


class WorkspaceError(RecordError):
    """A fault or a refusal about the workspace. ``code`` is the CLI exit status."""


_BAD_CHARS = frozenset("*?[\\\n\r\0")


def check_watch_path(root: Path, path: str) -> str:
    """Return the normal form of one path of ``vendomat.watch``, or refuse it (R62).

    A path is relative to the workspace root. It has no leading ``/`` or ``:``, no empty, ``.``, ``..``, or
    ``.git`` part, and no glob character. A symlink must not lead out of the workspace. The Nix type in
    ``devenv/devenv.nix`` (``watchPathOk``) holds the same rule for the text. Keep the two in step.
    """

    parts = path.split("/")
    problem = None
    if not path:
        problem = "it is empty"
    elif path.startswith(("/", ":")):
        problem = "it must be relative to the workspace root"
    elif any(part in ("", ".", "..", ".git") for part in parts):
        problem = "it has an empty, `.`, `..`, or `.git` part"
    elif _BAD_CHARS & set(path):
        problem = "it has a glob or control character"
    else:
        base = root.resolve()
        target = (base / path).resolve()
        if target != base and base not in target.parents:
            problem = "it leads out of the workspace"
        elif target.is_dir():
            problem = "it is a directory; name the files"
    if problem is not None:
        raise WorkspaceError(f"vendomat.watch: {path!r} is not a file path below the workspace root: {problem}", 2)
    return path


def extend_watched(root: Path, extra: Sequence[str]) -> tuple[str, ...]:
    """The four fixed files, then the checked paths of ``vendomat.watch``, without repeats."""

    names = dict.fromkeys(WATCHED)
    for path in extra:
        names.setdefault(check_watch_path(root, path))
    return tuple(names)


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


def watched_changes(root: Path, watched: Sequence[str] = WATCHED) -> list[Change]:
    """Watched files that differ from HEAD. An ignored file that exists counts.

    ``git status`` names paths from the repository top, not from ``root``. A workspace may sit in a
    subdirectory, so the function strips the prefix of ``root``. A rename between watched files gives
    one change for each name.
    """

    proc = git(root, "status", "--porcelain", "-z", "--ignored=matching", "--untracked-files=all", "--", *watched)
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
            if name.startswith(prefix) and name[len(prefix) :] in watched:
                changes.append(Change(name[len(prefix) :], status))
    return changes


def _tree_paths(root: Path, watched: Sequence[str] = WATCHED) -> list[str]:
    """The files under ``root`` that a build can read: tracked files and new files that Git does not ignore.

    The names are relative to ``root`` (``git ls-files`` run in ``root`` does this). A watched file
    that exists counts even when Git ignores it.
    """

    proc = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".")
    names = {name for name in proc.stdout.split("\0") if name}
    names.update(name for name in watched if (root / name).exists() or (root / name).is_symlink())
    return sorted(names)


def _file_hash(file: Path) -> str | None:
    """The content hash of a file, of the target text of a symlink, or ``None`` for a missing path."""

    if file.is_symlink():
        return "link:" + hashlib.sha256(os.readlink(file).encode()).hexdigest()
    if not file.is_file():
        return None
    digest = hashlib.sha256()
    with file.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(root: Path, watched: Sequence[str] = WATCHED) -> tuple[str, dict[str, str | None]]:
    """The commit at HEAD and the content hash of every file of the tree under ``root``.

    The tree is the tracked files, the new files that Git does not ignore, and the watched
    files (``None`` for a missing watched file). A file that a build can read must not change during
    the build (R55).
    """

    hashes: dict[str, str | None] = {name: None for name in watched}
    for name in _tree_paths(root, watched):
        hashes[name] = _file_hash(root / name)
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


def refuse_ignored_watched(root: Path, watched: Sequence[str] = WATCHED) -> None:
    """Ignored watched files must be explicitly force-added before they can be applied."""

    ignored = [change.path for change in watched_changes(root, watched) if change.status == "!!"]
    if ignored:
        names = ", ".join(ignored)
        raise WorkspaceError(
            f"ignored configuration file(s) are present: {names}. Force-add them with `git add -f`, "
            "or remove them before applying."
        )


def _tracked(root: Path, path: str) -> bool:
    return git(root, "ls-files", "--error-unmatch", "--", path, check=False).returncode == 0


def _commit_paths(root: Path, changes: list[Change], watched: Sequence[str] = WATCHED) -> tuple[str, ...]:
    """Return changed watched paths, or one tracked path for an empty rollback commit."""

    paths = tuple(dict.fromkeys(change.path for change in changes))
    if paths:
        return paths
    for path in watched:
        if _tracked(root, path):
            return (path,)
    raise WorkspaceError("the workspace has no tracked configuration path to commit")


def commit_watched(root: Path, message: str = "vendomat apply configuration", watched: Sequence[str] = WATCHED) -> str:
    """Commit the current allowlisted workspace configuration without committing other staged files."""

    refuse_ignored_watched(root, watched)
    changes = watched_changes(root, watched)
    if not changes:
        return head(root)
    paths = _commit_paths(root, changes, watched)
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


def tree_changes(root: Path) -> list[Change]:
    """Every uncommitted change under ``root``: tracked files that differ from HEAD and new files.

    Files that Git ignores do not count. The names are relative to ``root``. Git reports a rename as a
    deletion and an addition (``--no-renames``), so each name appears once. A change outside ``root``
    does not count.
    """

    proc = git(root, "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", "--", ".")
    prefix = _prefix(root)
    changes: list[Change] = []
    for entry in proc.stdout.split("\0"):
        if len(entry) < 4:
            continue
        name = entry[3:]
        if name.startswith(prefix):
            changes.append(Change(name[len(prefix) :], entry[:2]))
    return changes


def cache_key_path(name: str) -> str:
    """The workspace path of the public cache key of machine ``name`` (``VMT-161``)."""

    return f".machines/{name}/cache-key.pub"


def written_key_file(root: Path, name: str, source: Path) -> str | None:
    """The path of the key file that apply writes for this machine, or ``None``.

    Apply copies the machine's public key from ``source`` into the workspace after each activation
    and never commits it. The file is apply's own output, so a change to it must not stop the next
    apply, whatever it holds: apply writes it again from ``source``. A machine with no ``source``
    (``serve: false``) has no such output, and its key file counts as a change of the user.
    """

    return cache_key_path(name) if source.is_file() else None


def uncommitted_changes(root: Path, *, skip: tuple[str, ...] = ()) -> list[Change]:
    """The uncommitted changes under ``root`` except the paths in ``skip``."""

    return [change for change in tree_changes(root) if change.path not in skip]


def diff_text(root: Path, rev: str) -> str:
    """The change that a restore of the workspace tree from ``rev`` makes: the stat, then the patch."""

    stat = git(root, "diff", "--no-color", "--stat", "HEAD", rev, "--", ".").stdout
    patch = git(root, "diff", "--no-color", "HEAD", rev, "--", ".").stdout
    return (stat + "\n" + patch).strip()


def restore(root: Path, rev: str) -> None:
    """Make every tracked file under ``root`` equal to ``rev``, in index and tree.

    ``git restore --source`` also removes a tracked file that ``rev`` lacks. New files that Git does
    not track stay. Paths outside ``root`` stay as they are.
    """

    git(root, "restore", f"--source={rev}", "--staged", "--worktree", "--", ".")


def undo_restore(root: Path) -> None:
    """Return the index and the tree under ``root`` to HEAD after a failed rollback step."""

    git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", ".")


def commit_restore(root: Path, message: str) -> str:
    """Commit a restore of the workspace tree. Staged files outside ``root`` stay out of the commit."""

    git(root, "commit", "-q", "--allow-empty", "--only", "-m", message, "--", ".")
    return head(root)

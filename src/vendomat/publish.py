"""Reversible local-to-GitHub source publishing for Vendomat consumers.

The manifest deliberately describes literal replacements rather than trying to rewrite TOML.
That keeps comments and a consumer's chosen dependency syntax intact, while making every
published transformation explicit and reviewable.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

MANIFEST = "vendomat.toml"


class PublishError(RuntimeError):
    """A manifest or Git state prevents a safe publication."""


@dataclass(frozen=True)
class Replacement:
    """One exact, repo-relative local source -> GitHub source substitution."""

    files: tuple[Path, ...]
    local: str
    github: str


def _safe_file(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise PublishError(f"manifest file must be repo-relative without '..': {raw!r}")
    return path


def read_manifest(repo_root: Path) -> list[Replacement]:
    """Read and validate ``vendomat.toml`` in a consumer repository."""

    path = repo_root / MANIFEST
    if not path.is_file():
        raise PublishError(f"{MANIFEST} is missing from {repo_root}")
    try:
        entries = tomllib.loads(path.read_text()).get("replacement", [])
    except tomllib.TOMLDecodeError as exc:
        raise PublishError(f"invalid {MANIFEST}: {exc}") from exc
    if not isinstance(entries, list) or not entries:
        raise PublishError(f"{MANIFEST} must contain at least one [[replacement]] table")

    replacements: list[Replacement] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise PublishError(f"replacement #{index} is not a table")
        files, local, github = entry.get("files"), entry.get("local"), entry.get("github")
        if not isinstance(files, list) or not files or not all(isinstance(f, str) for f in files):
            raise PublishError(f"replacement #{index}.files must be a non-empty list of paths")
        if not isinstance(local, str) or not local:
            raise PublishError(f"replacement #{index}.local must be a non-empty string")
        if not isinstance(github, str) or not github:
            raise PublishError(f"replacement #{index}.github must be a non-empty GitHub source spelling")
        relative_files = tuple(_safe_file(repo_root, cast(str, f)) for f in files)
        replacements.append(Replacement(relative_files, local, github))
    return replacements


def materialize(repo_root: Path, target: str) -> list[Path]:
    """Replace each declared source with its ``local`` or ``github`` spelling.

    Only files explicitly named in the manifest may change. A replacement whose source spelling
    is absent is harmless, making the operation idempotent.
    """

    if target not in {"local", "github"}:
        raise PublishError(f"unknown target {target!r}; expected 'local' or 'github'")
    changed: list[Path] = []
    for replacement in read_manifest(repo_root):
        source, destination = (
            (replacement.github, replacement.local) if target == "local" else (replacement.local, replacement.github)
        )
        for relative in replacement.files:
            path = repo_root / relative
            if not path.is_file():
                raise PublishError(f"manifest names a missing file: {relative}")
            before = path.read_text()
            after = before.replace(source, destination)
            if after != before:
                path.write_text(after)
                changed.append(path)
    return changed


def hook_script(executable: str) -> str:
    """The small tracked-by-Git hook trampoline installed into each consumer checkout."""

    return "#!/bin/sh\n# Installed by vendomat; do not edit.\nexec " + shlex.quote(executable) + ' pre-push "$@"\n'


def install_hook(repo_root: Path, executable: str | None = None) -> Path:
    """Install Vendomat's pre-push trampoline without overwriting another hook."""

    # A consumer opts into publication by committing a manifest. Importing the devenv module on
    # its own must not install a hook that would later reject every ordinary push.
    read_manifest(repo_root)
    common_dir = _git(repo_root, "rev-parse", "--git-common-dir").strip()
    hooks_dir = (
        (repo_root / common_dir / "hooks").resolve()
        if not Path(common_dir).is_absolute()
        else Path(common_dir) / "hooks"
    )
    hook = hooks_dir / "pre-push"
    script = hook_script(executable or str(Path(sys.argv[0]).resolve()))
    hooks_dir.mkdir(parents=True, exist_ok=True)
    if hook.exists() and hook.read_text() != script:
        raise PublishError(f"refusing to replace existing hook: {hook}")
    hook.write_text(script)
    hook.chmod(0o755)
    return hook


def _git(repo_root: Path, *args: str, input: str | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, input=input, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _lock_versions(text: str) -> dict[str, str]:
    """Return the resolved package versions from a uv.lock document."""

    try:
        packages = tomllib.loads(text).get("package", [])
    except tomllib.TOMLDecodeError as exc:
        raise PublishError(f"invalid uv.lock: {exc}") from exc
    return {
        str(package["name"]): str(package["version"])
        for package in packages
        if isinstance(package, dict) and "name" in package and "version" in package
    }


def lock_version_changes(before: str, after: str) -> list[str]:
    """Package names added, removed, or version-changed by a lock regeneration."""

    previous, regenerated = _lock_versions(before), _lock_versions(after)
    return sorted(name for name in previous.keys() | regenerated.keys() if previous.get(name) != regenerated.get(name))


def refresh_lock(repo_root: Path) -> list[Path]:
    """Regenerate an existing uv.lock and reject dependency graph churn.

    ``uv lock`` is intentionally run without an upgrade flag. It may update source metadata for
    an editable path becoming a Git dependency, but package additions/removals/version changes
    make publication ambiguous and must be reviewed outside the pre-push hook.
    """

    project, lock = repo_root / "pyproject.toml", repo_root / "uv.lock"
    if not project.is_file():
        return []
    if not lock.is_file():
        raise PublishError("pyproject.toml is present but uv.lock is missing; create and commit it before publishing")
    before = lock.read_text()
    result = subprocess.run(["uv", "lock"], cwd=repo_root, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"uv lock failed: {detail}")
    changed_versions = lock_version_changes(before, lock.read_text())
    if changed_versions:
        raise PublishError(
            "uv lock changed resolved package versions: "
            f"{', '.join(changed_versions)}; update and review the lock outside the publish hook"
        )
    return [lock] if lock.read_text() != before else []


def _rev_parse(repo_root: Path, ref: str) -> str | None:
    """Return the commit a ref points at, or ``None`` when the ref does not exist."""

    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() or None


def published_base_ref(remote: str, remote_ref: str) -> str:
    """The ref that records the local commit last published to ``remote_ref``."""

    branch = remote_ref.removeprefix("refs/heads/")
    return f"refs/vendomat/published/{remote}/{branch}"


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _vendomat_executable(executable: str | None = None) -> str:
    """Resolve the Vendomat CLI used by commands run inside the disposable worktree."""

    candidates: list[Path] = []
    if executable is not None:
        candidates.append(Path(executable).expanduser())

    on_path = shutil.which("vendomat")
    if on_path:
        candidates.append(Path(on_path))

    candidates.append(Path(sys.executable).resolve().parent / "vendomat")

    argv0 = Path(sys.argv[0])
    if argv0.name == "vendomat":
        candidates.append(argv0)

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    raise PublishError(
        "could not resolve the vendomat executable for publication; install the `vendomat` "
        "command or pass its path with executable=..."
    )


def _published_commit(
    repo_root: Path,
    local_sha: str,
    remote_sha: str,
    base: str | None,
    executable: str | None = None,
) -> str:
    """Replay outgoing commits in a disposable worktree, materializing GitHub sources per commit.

    ``base`` is the local commit last published to this remote branch. The published counterpart
    of that commit is ``remote_sha``, so replaying ``base..local_sha`` onto ``remote_sha`` gives
    the published counterpart of ``local_sha``. Publication rewrites commits, so ``remote_sha``
    is never part of the local history and cannot serve as the replay base itself.
    """

    with tempfile.TemporaryDirectory(prefix="vendomat-publish-") as temp:
        worktree = Path(temp) / "checkout"
        _git(repo_root, "worktree", "add", "--detach", str(worktree), local_sha)
        try:
            command_executable = shlex.quote(_vendomat_executable(executable))
            # A local-only source edit can disappear entirely after materialization. Keep an
            # empty commit in that case: it preserves the local branch's commit sequence and
            # gives the published ref a stable, transformed counterpart.
            command = (
                f"{command_executable} materialize github --repo-root . && "
                f"{command_executable} refresh-lock --repo-root . && "
                "git add -A && git commit --amend --no-edit --allow-empty"
            )
            if base is None:
                _git(worktree, "rebase", "--root", f"--exec={command}")
            else:
                _git(worktree, "rebase", "--onto", remote_sha, base, f"--exec={command}")
            return _git(worktree, "rev-parse", "HEAD").strip()
        finally:
            _git(repo_root, "worktree", "remove", "--force", str(worktree))


def pre_push(repo_root: Path, remote: str, updates: str, executable: str | None = None) -> None:
    """Publish rewritten temporary commits, then abort the original local-source push.

    Git has already selected the refs for the outer ``git push`` when this hook runs. We publish
    clean commits ourselves with ``--no-verify`` and intentionally fail the outer push so it
    cannot send the local-path commits afterwards. The developer's checkout is never modified.

    Every ref is published in one ``git push`` so a later failure cannot leave part of the set
    already sent. After that push succeeds, each branch's marker ref records the local commit
    that was published, which keeps the next push's replay range correct.
    """

    if os.environ.get("VENDOMAT_BYPASS_PRE_PUSH") == "1":
        return
    lines = [line.split() for line in updates.splitlines() if line.strip()]
    if not lines:
        return
    refspecs: list[str] = []
    markers: list[tuple[str, str]] = []
    for fields in lines:
        if len(fields) != 4:
            raise PublishError("malformed pre-push input")
        local_ref, local_sha, remote_ref, remote_sha = fields
        del local_ref
        if local_sha == "0" * 40 or remote_ref.startswith("refs/tags/"):
            raise PublishError("Vendomat publishes branches only; push tags separately with VENDOMAT_BYPASS_PRE_PUSH=1")
        marker = published_base_ref(remote, remote_ref)
        base = _rev_parse(repo_root, marker)
        if base is None and remote_sha != "0" * 40:
            # A branch published by plain Git before any marker existed: its remote commit is a
            # genuine ancestor of the local branch, so it is a valid replay base.
            base = remote_sha
        if base is not None and not _is_ancestor(repo_root, base, local_sha):
            raise PublishError(
                f"{remote_ref} diverged from the last publication: {base[:12]} is not an ancestor of "
                f"{local_sha[:12]}, so the outgoing range cannot be computed. Rebase the branch onto "
                f"{base[:12]}, or correct the marker with "
                f"'git update-ref {marker} <commit>', then push again"
            )
        published = _published_commit(repo_root, local_sha, remote_sha, base, executable)
        if remote_sha != "0" * 40:
            # Publication may amend already published commits, so the update is not always a
            # fast-forward. The lease keeps that from overwriting an unexpected remote state.
            refspecs.append(f"--force-with-lease={remote_ref}:{remote_sha}")
        refspecs.append(f"{published}:{remote_ref}")
        markers.append((marker, local_sha))
    _git(repo_root, "-c", "core.hooksPath=/dev/null", "push", remote, *refspecs)
    for marker, local_sha in markers:
        _git(repo_root, "update-ref", marker, local_sha)
    raise PublishError("published GitHub-source commit(s); local vendor-source branch was left unchanged")


def on_pre_push(
    remote: str,
    bookmarks: Sequence[str],
    repo_root: Path | None = None,
    executable: str | None = None,
    **_: object,
) -> None:
    """Pyjutsu ``pre-push`` hook entry point for pushes that cannot run a Git hook.

    Pyjutsu hooks get no standard input, so this resolves both sides of each update itself:
    the local bookmark and its remote-tracking ref. A successful publication raises, exactly as
    the Git hook does, because the outer push must not send the local-path commits.
    """

    root = Path(repo_root) if repo_root is not None else Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    updates = []
    for bookmark in bookmarks:
        local_sha = _rev_parse(root, f"refs/heads/{bookmark}")
        if local_sha is None:
            raise PublishError(f"pyjutsu pre-push names an unknown bookmark: {bookmark}")
        remote_sha = _rev_parse(root, f"refs/remotes/{remote}/{bookmark}") or "0" * 40
        updates.append(f"refs/heads/{bookmark} {local_sha} refs/heads/{bookmark} {remote_sha}")
    try:
        pre_push(root, remote, "\n".join(updates), executable=executable)
    except PublishError as exc:
        raise _hook_abort(str(exc)) from exc


def _hook_abort(message: str) -> BaseException:
    """Wrap a publication outcome in pyjutsu's abort type when pyjutsu is importable."""

    try:
        from pyjutsu.hooks import HookAbort  # ty: ignore[unresolved-import]
    except ImportError:
        return PublishError(message)
    return HookAbort(message)


def publish_preview(repo_root: Path) -> str:
    """Return the public manifest/lock diff for HEAD without changing the current checkout."""

    with tempfile.TemporaryDirectory(prefix="vendomat-publish-preview-") as temp:
        worktree = Path(temp) / "checkout"
        _git(repo_root, "worktree", "add", "--detach", str(worktree), "HEAD")
        try:
            materialize(worktree, "github")
            refresh_lock(worktree)
            result = subprocess.run(
                ["git", "diff", "--", "pyproject.toml", "uv.lock"],
                cwd=worktree,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode:
                raise PublishError(result.stderr.strip() or "could not produce publish preview")
            return result.stdout
        finally:
            _git(repo_root, "worktree", "remove", "--force", str(worktree))

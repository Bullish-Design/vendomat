"""Keep, mirror, and refresh source clones (``STORE-009``, ``STORE-013``).

``sync`` calls this module after it writes ``flake.nix``. A ``keep`` entry gets a persistent clone
on the machine that runs ``sync``. A ``mirror`` entry gets a reading copy on the collection host.
The collection host also moves each collection repository to its newest release tag.

Rules that hold everywhere in this module:

- Git runs as a subprocess with explicit arguments, ``GIT_TERMINAL_PROMPT=0``, and a timeout.
- A working tree with uncommitted changes is never touched (``STORE-003``). The entry is reported
  and the other entries continue.
- A clone shows the tag its entry pins, as a detached checkout, when its tree is clean.
- One failure never stops the other entries. Every entry yields one :class:`Outcome`.

Nothing here reads or writes ``flake.lock``, the registry, or the export marker and hook of a
collection repository. A mirror gets neither.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .registry import Registry, Source

#: The environment variable and the default for the directory that holds the clones (``STORE-001``).
SOURCE_ROOT_ENV = "VENDOMAT_SOURCE_ROOT"
DEFAULT_SOURCE_ROOT = "~/vendor"
#: Seconds. A network call (clone, fetch) gets longer than a local call.
NETWORK_TIMEOUT = 300
LOCAL_TIMEOUT = 60
#: A repository counts as part of the collection when it carries one of these (``STORE-014``, ``STORE-015``).
COLLECTION_HOOK = Path("hooks") / "pre-receive"
EXPORT_MARKER = Path("git-daemon-export-ok")
#: Schemes that ``git clone`` may use here. Anything else (``ext::``, ``fd::``) is refused.
CLONE_SCHEMES = frozenset({"git", "http", "https", "ssh", "file"})

#: Statuses. ``refused`` is a decision for the owner (exit 1). ``failed`` is a Git or network fault (exit 2).
OK_STATUSES = frozenset({"cloned", "updated", "unchanged", "skipped", "planned"})

_USERINFO_RE = re.compile(r"(?<=://)[^/@\s]+@")
_GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")


@dataclass(frozen=True)
class Outcome:
    """The result for one entry or one collection repository."""

    subject: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status in OK_STATUSES

    def line(self) -> str:
        return f"{self.subject}: {self.status}: {self.detail}"


def exit_code(outcomes: list[Outcome]) -> int:
    """0 when every outcome is fine, 2 when Git or the network failed, otherwise 1."""

    if any(o.status == "failed" for o in outcomes):
        return 2
    return 0 if all(o.ok for o in outcomes) else 1


def source_root(environ: dict[str, str] | None = None) -> Path:
    """``$VENDOMAT_SOURCE_ROOT`` when set and not empty, else ``~/vendor``."""

    env = os.environ if environ is None else environ
    return Path(env.get(SOURCE_ROOT_ENV) or DEFAULT_SOURCE_ROOT).expanduser()


def redact(text: str) -> str:
    """Remove credentials from a URL or a message, so no log can carry one."""

    return _USERINFO_RE.sub("", text)


def clone_url(url: str) -> str | None:
    """The URL for ``git clone``: no query, no ``git+`` prefix. ``None`` when Git cannot clone it."""

    bare = url.partition("?")[0]
    if bare.startswith("git+"):
        bare = bare[len("git+") :]
    scheme = bare.partition("://")[0]
    if "://" not in bare or scheme not in CLONE_SCHEMES:
        return None
    return bare


class _GitError(Exception):
    """A Git call failed or timed out. The message holds no credential."""


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROP}
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    env["LC_ALL"] = "C"
    return env


def _git(
    args: list[str], *, cwd: Path | None = None, network: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run ``git`` with explicit arguments. ``check`` raises :class:`_GitError` on a non-zero status."""

    argv = ["git", *args]
    try:
        done = subprocess.run(
            argv,
            cwd=cwd,
            env=_env(),
            capture_output=True,
            text=True,
            timeout=NETWORK_TIMEOUT if network else LOCAL_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise _GitError(f"git {args[0]} timed out after {exc.timeout:.0f} s") from exc
    except OSError as exc:
        raise _GitError(f"cannot run git: {exc.strerror or exc}") from exc
    if check and done.returncode != 0:
        lines = (done.stderr or done.stdout).strip().splitlines()
        detail = f": {redact(lines[-1])}" if lines else ""
        raise _GitError(f"git {args[0]} failed (status {done.returncode}){detail}")
    return done


def _is_repo(directory: Path) -> bool:
    return (directory / ".git").exists()


def _dirty(directory: Path) -> bool:
    return bool(_git(["--no-optional-locks", "status", "--porcelain"], cwd=directory).stdout.strip())


def _tag_commit(directory: Path, tag: str) -> str | None:
    done = _git(["rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}"], cwd=directory, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def _checkout_tag(directory: Path, tag: str, *, dry_run: bool) -> str:
    """Detach ``directory`` at ``tag``. Return a short description. The tree must be clean."""

    commit = _tag_commit(directory, tag)
    if commit is None:
        raise _GitError(f"tag {tag} is not in the clone")
    head = _git(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], cwd=directory, check=False)
    detached = _git(["symbolic-ref", "--quiet", "HEAD"], cwd=directory, check=False).returncode != 0
    short = commit[:7]
    if head.returncode == 0 and head.stdout.strip() == commit and detached:
        return f"at {tag} ({short})"
    if dry_run:
        return f"would check out {tag} ({short})"
    _git(["checkout", "--quiet", "--detach", commit], cwd=directory)
    return f"checked out {tag} ({short})"


def _tags(directory: Path) -> set[str]:
    return set(_git(["for-each-ref", "--format=%(refname)", "refs/tags"], cwd=directory).stdout.split())


def _newest_tag(directory: Path) -> str | None:
    """The newest tag by version order, or ``None`` when the repository has no tag."""

    out = _git(["for-each-ref", "--sort=-v:refname", "--count=1", "--format=%(refname)", "refs/tags"], cwd=directory)
    ref = out.stdout.strip()
    return ref.removeprefix("refs/tags/") if ref else None


def sync_store(registry: Registry, *, root: Path, collection: bool = False, dry_run: bool = False) -> list[Outcome]:
    """Act on every ``keep`` and ``mirror`` entry, then, on the collection host, refresh the collection."""

    outcomes: list[Outcome] = []
    for source in registry.sources:
        if not (source.keep or source.mirror):
            continue
        if source.mirror and not collection:
            outcomes.append(Outcome(source.name, "skipped", "mirror skipped: not the collection host"))
            if not source.keep:
                continue
        outcomes.append(_sync_clone(source, root, dry_run=dry_run))
    if collection:
        outcomes.extend(refresh_collection(root, dry_run=dry_run))
    return outcomes


def _sync_clone(source: Source, root: Path, *, dry_run: bool) -> Outcome:
    subject = source.name
    url = clone_url(source.url)
    if url is None:
        if source.url.startswith("path:"):
            return Outcome(subject, "skipped", "a path: input is local, so there is nothing to clone")
        return Outcome(
            subject, "refused", f"cannot clone {redact(source.url)}: Git needs a git, http(s), ssh, or file URL"
        )
    tag = source.tag
    if tag is None:
        return Outcome(subject, "refused", "the entry pins no tag, so there is nothing to check out")
    directory = root / source.repo
    try:
        if not os.path.lexists(directory):
            return _clone(subject, url, directory, tag, dry_run=dry_run)
        if not _is_repo(directory):
            return Outcome(subject, "refused", f"{directory} exists and is not a Git repository")
        origin = _git(["config", "--get", "remote.origin.url"], cwd=directory, check=False)
        if origin.returncode == 1:
            return Outcome(
                subject, "skipped", f"{directory} has no origin: it is the collection's own repository; left alone"
            )
        if origin.returncode != 0:
            raise _GitError(f"cannot read the origin of {directory}")
        if _dirty(directory):
            return Outcome(subject, "refused", f"{directory} has uncommitted changes; left alone")
        return _update(subject, directory, tag, dry_run=dry_run, origin=redact(origin.stdout.strip()), want=redact(url))
    except (_GitError, OSError) as exc:
        return Outcome(subject, "failed", str(exc))


def _clone(subject: str, url: str, directory: Path, tag: str, *, dry_run: bool) -> Outcome:
    shown = redact(url)
    if dry_run:
        return Outcome(subject, "planned", f"would clone {shown} to {directory}, then check out {tag}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    _git(["clone", "--quiet", "--", url, str(directory)], network=True)
    # A repository with tags and no branch can clone without them. Fetch only if the tag is missing.
    if _tag_commit(directory, tag) is None:
        _git(["fetch", "--quiet", "--tags", "origin"], cwd=directory, network=True)
    return Outcome(subject, "cloned", f"{shown} to {directory}; {_checkout_tag(directory, tag, dry_run=False)}")


def _update(subject: str, directory: Path, tag: str, *, dry_run: bool, origin: str, want: str) -> Outcome:
    note = "" if origin == want else f" (origin is {origin}, the entry names {want})"
    if dry_run:
        return Outcome(subject, "planned", f"would fetch tags in {directory}, then check out {tag}{note}")
    before = _tags(directory)
    _git(["fetch", "--quiet", "--tags", "origin"], cwd=directory, network=True)
    new = len(_tags(directory) - before)
    state = _checkout_tag(directory, tag, dry_run=False)
    changed = new > 0 or not state.startswith("at ")
    fetched = f"fetched {new} new tag(s)" if new else "no new tags"
    return Outcome(subject, "updated" if changed else "unchanged", f"{directory}: {fetched}; {state}{note}")


def refresh_collection(root: Path, *, dry_run: bool = False) -> list[Outcome]:
    """Check out the newest release tag in each collection repository (``STORE-013``).

    A repository belongs to the collection when it has the ``pre-receive`` hook or the export
    marker. Other directories under ``root`` are left alone.
    """

    if not root.is_dir():
        return []
    outcomes: list[Outcome] = []
    try:
        directories = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError as exc:
        return [Outcome("collection", "failed", f"cannot list {root}: {exc.strerror or exc}")]
    for directory in directories:
        git_dir = directory / ".git"
        if not (git_dir / COLLECTION_HOOK).exists() and not (git_dir / EXPORT_MARKER).exists():
            continue
        subject = f"collection:{directory.name}"
        try:
            if _dirty(directory):
                outcomes.append(Outcome(subject, "refused", f"{directory} has uncommitted changes; left alone"))
                continue
            tag = _newest_tag(directory)
            if tag is None:
                outcomes.append(Outcome(subject, "skipped", "no release tag yet"))
                continue
            state = _checkout_tag(directory, tag, dry_run=dry_run)
            if dry_run:
                status = "unchanged" if state.startswith("at ") else "planned"
            else:
                status = "unchanged" if state.startswith("at ") else "updated"
            outcomes.append(Outcome(subject, status, f"newest release {state}"))
        except (_GitError, OSError) as exc:
            outcomes.append(Outcome(subject, "failed", str(exc)))
    return outcomes

"""``vendomat rollback``: a lasting return to an earlier commit (R30, R43, ``VMT-072``, ``VMT-098``).

A lasting rollback changes the files, not only the machine. The command:

1. reads the generation record (``record.py``) and picks a target: the newest earlier clean entry
   with a different system path, or ``--to REV``, or ``--generation N``;
2. refuses uncommitted changes to the watched files, an unknown commit, and a recorded commit that
   the repository no longer holds;
3. shows the diff that the restore makes;
4. restores the watched files from the target commit (``--exact``: every tracked file);
5. builds, commits the restore as ``rollback to REV``, and activates.

A restore that stays in the working copy is not allowed: the next apply from another clone, or after
a reset, would silently roll forward (W9 R3). The commit is always made.

``--fast`` moves the profile to the recorded generation instead of building, and still commits.
``--boot-only`` only sets the next boot entry, for recovery. It changes no file and makes no commit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import workspace
from .apply import (
    PROFILE,
    Applied,
    Emit,
    Runner,
    activate,
    build_toplevel,
    current_toplevel,
    machine_name,
    run_command,
    sudo,
)
from .record import RECORD_PATH, Choice, RecordError, choose, read_entries

BOOT_ENTRIES = Path("/boot/loader/entries")
_VERSION = re.compile(r"^version\s+Generation\s+(\d+)\b", re.MULTILINE)


@dataclass
class RolledBack:
    commit: str
    target_commit: str
    applied: Applied | None
    boot_entry: str | None = None


def find_boot_entry(generation: int, entries: Path = BOOT_ENTRIES) -> str:
    """The file name of the systemd-boot entry for a generation."""

    try:
        files = sorted(entries.glob("*.conf"))
    except OSError as exc:
        raise RecordError(f"cannot read {entries}: {exc}", 2) from exc
    for file in files:
        try:
            match = _VERSION.search(file.read_text())
        except OSError:
            continue
        if match and int(match.group(1)) == generation:
            return file.name
    raise RecordError(f"no boot entry for generation {generation} in {entries}")


def pick(
    root: Path,
    current: str,
    *,
    to: str | None,
    generation: int | None,
    record: Path,
    fast_or_boot: bool,
) -> tuple[str, Choice | None]:
    """Return the target commit and, when the record names it, the chosen entry.

    ``--to REV`` needs no entry, except for ``--fast`` and ``--boot-only``, which need a generation.
    """

    entries = read_entries(record)
    if to is not None:
        target = workspace.resolve(root, to)
        chosen = choose(entries, current, commit=target) if fast_or_boot else None
        return target, chosen
    chosen = choose(entries, current, generation=generation)
    if not workspace.has_commit(root, chosen.entry.commit):
        raise RecordError(
            f"the record names commit {chosen.entry.commit[:12]} for generation {chosen.entry.generation}, "
            "but the repository does not hold it (was history rewritten?). Use --to REV with a commit you have."
        )
    return chosen.entry.commit, chosen


def rollback(
    root: Path,
    *,
    to: str | None = None,
    generation: int | None = None,
    exact: bool = False,
    fast: bool = False,
    boot_only: bool = False,
    dry_run: bool = False,
    run: Runner = run_command,
    emit: Emit = print,
    facts: Path | None = None,
    profile: Path | None = None,
    record: Path | None = None,
    boot_entries: Path | None = None,
) -> RolledBack | None:
    """Roll this machine back. Return ``None`` for ``--dry-run``."""

    profile = profile or PROFILE
    record = record or RECORD_PATH
    boot_entries = boot_entries or BOOT_ENTRIES
    if to is not None and generation is not None:
        raise RecordError("give --to or --generation, not both", 3)
    if exact and (fast or boot_only):
        raise RecordError("--exact cannot combine with --fast or --boot-only", 3)
    if fast and boot_only:
        raise RecordError("give --fast or --boot-only, not both", 3)

    name = machine_name(facts)
    changes = workspace.watched_changes(root)
    if exact and not changes:
        stray = workspace.tree_changes(root)
        if stray:
            raise RecordError("--exact replaces every tracked file, but the tree has changes:\n" + "\n".join(stray))
    if changes and not boot_only:
        listing = "; ".join(change.text() for change in changes)
        raise RecordError(f"uncommitted changes to watched files ({listing}). Commit or discard them first.")
    if changes and boot_only:
        pass  # --boot-only touches no file, so it needs no clean tree.

    current = current_toplevel(profile)
    head = workspace.head(root)
    target, chosen = pick(root, current, to=to, generation=generation, record=record, fast_or_boot=fast or boot_only)
    if chosen is not None:
        for entry in chosen.skipped_dirty:
            emit(f"skipped generation {entry.generation}: applied with uncommitted changes")
    target_short = workspace.short(root, target)
    if chosen is not None:
        emit(f"target: generation {chosen.entry.generation}, commit {target_short}, {chosen.entry.toplevel}")
    else:
        emit(f"target: commit {target_short}")

    if boot_only:
        if chosen is None:
            raise RecordError("--boot-only needs a recorded generation")
        entry_name = find_boot_entry(chosen.entry.generation, boot_entries)
        done = sudo(run, "bootctl", "set-oneshot", entry_name)
        if done.returncode != 0:
            raise RecordError(f"bootctl set-oneshot {entry_name} failed (exit {done.returncode})", 2)
        emit(f"next boot only: {entry_name} (generation {chosen.entry.generation}). No file changed; no commit made.")
        emit("This is for recovery. Restart to use it. The profile and the files stay as they are.")
        return RolledBack(head, target, None, entry_name)

    diff = workspace.diff_text(root, target, exact=exact)
    emit(diff if diff else "the files already equal the target commit; the rollback commit will be empty")
    if dry_run:
        emit("dry run: nothing changed")
        return None

    if fast:
        assert chosen is not None  # pick() guarantees an entry for --fast
        link = profile.parent / f"{profile.name}-{chosen.entry.generation}-link"
        if not link.is_symlink() or str(link.resolve()) != chosen.entry.toplevel:
            raise RecordError(
                f"generation {chosen.entry.generation} is gone from this machine, or no longer holds "
                f"{chosen.entry.toplevel}. Run the rollback without --fast."
            )

    workspace.restore(root, target, exact=exact)
    try:
        if fast:
            assert chosen is not None
            commit = workspace.commit_restore(root, f"rollback to {target_short}", exact=exact)
            applied = activate(
                run,
                chosen.entry.toplevel,
                commit,
                False,
                emit,
                profile=profile,
                record=record,
                generation=chosen.entry.generation,
            )
        else:
            top = build_toplevel(root, name, run)
            emit(f"built {top}")
            commit = workspace.commit_restore(root, f"rollback to {target_short}", exact=exact)
            applied = activate(run, top, commit, False, emit, profile=profile, record=record)
    except RecordError:
        # A restore that is neither committed nor applied must not stay in the tree.
        if workspace.head(root) == head:
            workspace.undo_restore(root, exact=exact)
        raise
    emit(f"committed {workspace.short(root, commit)}: rollback to {target_short}")
    return RolledBack(commit, target, applied)

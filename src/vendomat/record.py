"""The generation record of one machine (R43, ``VMT-098``).

Each machine keeps ``/var/lib/vendomat/generations.jsonl``. ``vendomat apply`` appends one JSON
line after a successful switch. The line links a system path to the workspace commit it came from:

    {"generation": 3, "toplevel": "/nix/store/...", "commit": "<40 hex>", "dirty": false, "time": "..."}

``system.configurationRevision`` stays unset (``VMT-110``), so this file is the only link from a
system path to a commit. The file is append-only. Root writes it. Everyone can read it.

This module holds the pure part: the line format, the reader, and the choice of a rollback target.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RECORD_PATH = Path("/var/lib/vendomat/generations.jsonl")


class RecordError(Exception):
    """A fault in the record or a refused choice. ``code`` is the CLI exit status."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Entry:
    """One apply: the generation it made current, its system path, and the commit it came from."""

    generation: int
    toplevel: str
    commit: str
    dirty: bool
    time: str

    def line(self) -> str:
        """The JSON line, with no newline."""

        return json.dumps(
            {
                "generation": self.generation,
                "toplevel": self.toplevel,
                "commit": self.commit,
                "dirty": self.dirty,
                "time": self.time,
            },
            separators=(",", ":"),
        )


def now() -> str:
    """The time in UTC, to the second."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_line(text: str) -> Entry:
    """Read one line. A missing key or a wrong type is a fault."""

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecordError(f"not JSON: {exc}", 2) from exc
    if not isinstance(raw, dict):
        raise RecordError("not a JSON object", 2)
    generation, toplevel, commit, dirty, when = (
        raw.get("generation"),
        raw.get("toplevel"),
        raw.get("commit"),
        raw.get("dirty"),
        raw.get("time"),
    )
    if not isinstance(generation, int) or isinstance(generation, bool):
        raise RecordError("key 'generation' must be an integer", 2)
    if not isinstance(toplevel, str) or not toplevel:
        raise RecordError("key 'toplevel' must be a non-empty string", 2)
    if not isinstance(commit, str) or not commit:
        raise RecordError("key 'commit' must be a non-empty string", 2)
    if not isinstance(dirty, bool):
        raise RecordError("key 'dirty' must be true or false", 2)
    if not isinstance(when, str):
        raise RecordError("key 'time' must be a string", 2)
    return Entry(generation, toplevel, commit, dirty, when)


def read_entries(path: Path = RECORD_PATH) -> list[Entry]:
    """All entries, oldest first. A missing file is an empty record. A bad line names its number."""

    try:
        text = path.read_text()
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise RecordError(f"cannot read {path}: {exc}", 2) from exc
    entries: list[Entry] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(parse_line(line))
        except RecordError as exc:
            raise RecordError(f"{path}:{number}: {exc}", 2) from exc
    return entries


@dataclass
class Choice:
    """The entry that a rollback targets, and the dirty entries that the search passed over."""

    entry: Entry
    skipped_dirty: list[Entry] = field(default_factory=list)


def choose(
    entries: list[Entry],
    current: str,
    *,
    generation: int | None = None,
    commit: str | None = None,
) -> Choice:
    """Pick the entry that a rollback restores.

    * ``generation``: the newest entry of that generation. It must be clean.
    * ``commit``: the newest clean entry of that commit.
    * neither: the newest clean entry whose system path differs from ``current``.

    A dirty entry never qualifies, because its commit does not hold the configuration that ran.
    """

    if generation is not None:
        found = [e for e in entries if e.generation == generation]
        if not found:
            raise RecordError(f"the record holds no entry for generation {generation}")
        entry = found[-1]
        if entry.dirty:
            raise RecordError(
                f"generation {generation} was applied with uncommitted changes; its commit "
                f"{entry.commit[:12]} does not hold that configuration"
            )
        if entry.toplevel == current:
            raise RecordError(f"generation {generation} is the running system; there is nothing to roll back to")
        return Choice(entry)
    if commit is not None:
        clean = [e for e in entries if e.commit == commit and not e.dirty]
        if not clean:
            raise RecordError(f"the record holds no clean entry for commit {commit[:12]}")
        return Choice(clean[-1])
    skipped: list[Entry] = []
    for entry in reversed(entries):
        if entry.toplevel == current:
            continue
        if entry.dirty:
            skipped.append(entry)
            continue
        return Choice(entry, skipped)
    if skipped:
        gens = ", ".join(str(e.generation) for e in skipped)
        raise RecordError(f"every earlier entry was applied with uncommitted changes (generation {gens})")
    raise RecordError("the record holds no earlier entry with a different system path")

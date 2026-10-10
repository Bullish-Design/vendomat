"""``vendomat bump``: move every workspace under a root to a Vendomat tag (``CLI-020``).

The default is a dry run that reads every workspace and changes nothing. With ``apply`` the command
edits the ``ref`` of the ``vendomat`` entry (and of the ``devenv`` entry when asked), runs ``sync``,
then runs each repository's verify gate. A failure stays in the report. The command never says the
fleet passed when one workspace failed.

``bump`` is the only command that writes a registry, and it writes only those two ``ref`` values
(``REG-025``). It edits an entry written as an inline table. Any other shape is reported, not edited.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .devenvgen import DevenvSyncError, sync_devenv
from .generate import tool_version
from .registry import RegistryError, parse_registry

TAG_RE = re.compile(r"[A-Za-z0-9._+-]+")
#: Directories that never hold a workspace.
SKIP_DIRS = frozenset({".git", ".jj", ".devenv", ".vendomat", ".testee", "node_modules", ".venv", "result"})
MAX_DEPTH = 4


@dataclass
class Entry:
    """The proposed or applied change for one workspace."""

    path: Path
    status: str = "pending"  # pending, current, would-change, changed, failed, skipped
    old: dict[str, str] = field(default_factory=dict)
    new: dict[str, str] = field(default_factory=dict)
    detail: str = ""
    gate: str = "not run"  # not run, passed, failed

    @property
    def ok(self) -> bool:
        return self.status in {"current", "would-change", "changed"} and self.gate in {"not run", "passed"}


def find_workspaces(fleet_root: Path) -> list[Path]:
    """Directories under ``fleet_root`` that hold a ``vendomat.toml`` with the devenv target."""

    found: list[Path] = []
    base_depth = len(fleet_root.parts)
    for current, dirs, files in os.walk(fleet_root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        if len(Path(current).parts) - base_depth >= MAX_DEPTH:
            dirs[:] = []
        if "vendomat.toml" in files:
            try:
                registry = parse_registry((Path(current) / "vendomat.toml").read_text(), current)
            except (OSError, RegistryError):
                found.append(Path(current))  # reported later with its error
                continue
            if registry.targets.devenv:
                found.append(Path(current))
    return found


_INLINE = r"^(?P<head>[ \t]*{name}[ \t]*=[ \t]*\{{)(?P<body>[^}}\n]*)(?P<tail>\}})"


def set_ref(text: str, entry: str, ref: str) -> tuple[str, str | None]:
    """Return ``(new text, old ref)`` for the inline-table entry ``entry``. Raise ``ValueError`` otherwise."""

    pattern = re.compile(_INLINE.format(name=re.escape(entry)), re.MULTILINE)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"entry '{entry}' is not a single inline table; edit it by hand")
    match = matches[0]
    body = match.group("body")
    ref_re = re.compile(r'(\bref[ \t]*=[ \t]*")([^"]*)(")')
    found = ref_re.search(body)
    if found is None:
        raise ValueError(f"entry '{entry}' has no ref key; edit it by hand")
    old = found.group(2)
    new_body = ref_re.sub(lambda m: f"{m.group(1)}{ref}{m.group(3)}", body, count=1)
    return text[: match.start("body")] + new_body + text[match.end("body") :], old


def plan_workspace(path: Path, tag: str, devenv_ref: str | None) -> tuple[Entry, str | None]:
    """Compute one workspace's change. The second value is the new registry text, or ``None``."""

    entry = Entry(path)
    try:
        text = (path / "vendomat.toml").read_text()
        parse_registry(text, str(path / "vendomat.toml"))
    except (OSError, RegistryError) as exc:
        entry.status, entry.detail = "failed", f"registry: {exc}"
        return entry, None
    wanted = {"vendomat": f"refs/tags/{tag}"}
    if devenv_ref is not None:
        wanted["devenv"] = devenv_ref if devenv_ref.startswith("refs/") else f"refs/tags/{devenv_ref}"
    new_text = text
    for name, ref in wanted.items():
        try:
            new_text, old = set_ref(new_text, name, ref)
        except ValueError as exc:
            if name == "devenv":
                entry.detail += f"{exc}; "
                continue
            entry.status, entry.detail = "skipped", str(exc)
            return entry, None
        entry.old[name], entry.new[name] = old or "", ref
    if new_text == text:
        entry.status = "current"
        return entry, None
    entry.status = "would-change"
    return entry, new_text


def bump(
    fleet_root: Path,
    tag: str,
    *,
    devenv_ref: str | None = None,
    apply: bool = False,
    gate: list[str] | None = None,
    only: list[str] | None = None,
    update_lock: bool = True,
) -> list[Entry]:
    if not TAG_RE.fullmatch(tag):
        raise ValueError(f"invalid tag {tag!r}")
    results: list[Entry] = []
    for path in find_workspaces(fleet_root):
        if only and path.name not in only:
            continue
        entry, new_text = plan_workspace(path, tag, devenv_ref)
        results.append(entry)
        if new_text is None or not apply:
            continue
        registry_path = path / "vendomat.toml"
        old_text = registry_path.read_text()
        registry_path.write_text(new_text)
        try:
            registry = parse_registry(new_text, str(registry_path))
            sync_devenv(path, registry, tool_version(), update_lock=update_lock)
        except (DevenvSyncError, RegistryError) as exc:
            registry_path.write_text(old_text)
            entry.status, entry.detail = "failed", f"sync: {exc}"
            continue
        entry.status = "changed"
        if gate:
            done = subprocess.run(
                gate, cwd=path, capture_output=True, text=True, timeout=7200, stdin=subprocess.DEVNULL
            )
            entry.gate = "passed" if done.returncode == 0 else "failed"
            if done.returncode != 0:
                entry.detail = f"gate `{' '.join(gate)}` exited {done.returncode}"
    return results


def summary(entries: list[Entry], applied: bool) -> tuple[str, bool]:
    """A one-line verdict and whether every workspace is fine. It never claims a pass over a failure."""

    bad = [e for e in entries if not e.ok]
    if not entries:
        return "no workspace found", False
    if bad:
        names = ", ".join(e.path.name for e in bad)
        return f"{len(bad)} of {len(entries)} workspace(s) incomplete: {names}", False
    verb = "bumped" if applied else "would change or are current"
    return f"all {len(entries)} workspace(s) {verb}", True

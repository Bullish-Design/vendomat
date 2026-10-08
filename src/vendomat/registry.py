"""Read and validate the V5 registry, ``vendomat.toml`` (``REG-*``).

The registry names the direct source inputs of one project. It selects no revision: Nix
resolves revisions and owns ``flake.lock``. This module only reads and validates. It never
writes the registry (``REG-009``) and never fetches an input.

Three tables exist. ``[inputs]`` and ``[passthrough]`` hold input entries. ``[follows]``
lists, per direct flake input, the child inputs that follow the root ``nixpkgs``.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ENTRY_KEYS = frozenset({"url", "ref", "rev", "flake"})
TABLES = frozenset({"inputs", "passthrough", "follows"})
#: The only root input a ``[follows]`` entry may name. A wider mapping needs its own fixture.
FOLLOWS_ROOT = "nixpkgs"

_URL_RE = re.compile(r"[^\s\x00-\x1f\x7f\"\\$#]+")
_REF_RE = re.compile(r"[A-Za-z0-9._/+-]+")
_REV_RE = re.compile(r"[0-9a-f]{40,64}")


class RegistryError(Exception):
    """A registry problem. The message names the file and the entry or key."""


@dataclass(frozen=True)
class Source:
    """One direct input. ``url`` already carries ``ref`` and ``rev`` as query parameters."""

    name: str
    url: str
    flake: bool
    follows: tuple[str, ...]


@dataclass(frozen=True)
class Registry:
    """A validated registry. ``sources`` is sorted by name, so output order never depends on the file."""

    sources: tuple[Source, ...]
    digest: str


def read_registry(path: Path) -> Registry:
    """Parse and validate the registry file."""

    try:
        text = path.read_text()
    except OSError as exc:
        raise RegistryError(f"{path}: cannot read the registry: {exc.strerror or exc}") from exc
    return parse_registry(text, str(path))


def parse_registry(text: str, where: str = "vendomat.toml") -> Registry:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise RegistryError(f"{where}: cannot parse the registry: {exc}") from exc

    unknown = sorted(set(data) - TABLES)
    if unknown:
        raise RegistryError(f"{where}: unknown table [{unknown[0]}]; expected [inputs], [passthrough], or [follows]")
    if "inputs" not in data:
        raise RegistryError(f"{where}: the registry needs an [inputs] table")

    entries: dict[str, tuple[str, bool]] = {}
    seen_in: dict[str, str] = {}
    for table in ("inputs", "passthrough"):
        raw = data.get(table, {})
        if not isinstance(raw, dict):
            raise RegistryError(f"{where}: [{table}] must be a table")
        for name, entry in raw.items():
            if name in seen_in:
                raise RegistryError(
                    f"{where}: input '{name}' appears in both [{seen_in[name]}] and [{table}]; keep it in one table"
                )
            seen_in[name] = table
            entries[name] = _entry(where, table, name, entry)

    follows = _follows(where, data.get("follows", {}), entries)
    sources = tuple(
        Source(name=name, url=entries[name][0], flake=entries[name][1], follows=follows.get(name, ()))
        for name in sorted(entries)
    )
    return Registry(sources=sources, digest=_digest(sources))


def _entry(where: str, table: str, name: str, entry: object) -> tuple[str, bool]:
    if not NAME_RE.fullmatch(name):
        raise RegistryError(f"{where}: input name '{name}' in [{table}] must match [a-z0-9][a-z0-9-]*")
    if not isinstance(entry, dict):
        raise RegistryError(f"{where}: [{table}] entry '{name}' must be a table with a 'url' key")
    for key in entry:
        if key not in ENTRY_KEYS:
            raise RegistryError(
                f"{where}: unknown key '{key}' in {table} entry '{name}'; allowed keys: {', '.join(sorted(ENTRY_KEYS))}"
            )
    url = _string(where, name, entry, "url", _URL_RE)
    if url is None:
        raise RegistryError(f"{where}: {table} entry '{name}' needs a 'url'; Vendomat does not guess a source")
    ref = _string(where, name, entry, "ref", _REF_RE)
    rev = _string(where, name, entry, "rev", _REV_RE)
    flake = entry.get("flake", True)
    if not isinstance(flake, bool):
        raise RegistryError(f"{where}: 'flake' in entry '{name}' must be true or false")
    return _with_query(where, name, url, ref, rev), flake


def _string(where: str, name: str, entry: dict, key: str, pattern: re.Pattern[str]) -> str | None:
    if key not in entry:
        return None
    value = entry[key]
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise RegistryError(f"{where}: '{key}' in entry '{name}' is not a valid {key}: {value!r}")
    return value


def _with_query(where: str, name: str, url: str, ref: str | None, rev: str | None) -> str:
    """Add ``ref`` and ``rev`` as URL query parameters.

    Nix 2.34.7 rejects them as separate input attributes next to ``url`` (PV-13).
    """

    query = url.partition("?")[2]
    present = {pair.partition("=")[0] for pair in query.split("&") if pair}
    pairs = [("ref", ref), ("rev", rev)]
    for key, value in pairs:
        if value is not None and key in present:
            raise RegistryError(f"{where}: entry '{name}' sets '{key}' and also carries '{key}=' in its url; use one")
    extra = "&".join(f"{key}={value}" for key, value in pairs if value is not None)
    if not extra:
        return url
    return f"{url}{'&' if '?' in url else '?'}{extra}"


def _follows(where: str, raw: object, entries: dict[str, tuple[str, bool]]) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, dict):
        raise RegistryError(f"{where}: [follows] must be a table")
    table = cast("dict[str, object]", raw)
    if table and FOLLOWS_ROOT not in entries:
        raise RegistryError(f"{where}: [follows] needs a '{FOLLOWS_ROOT}' entry in [inputs] or [passthrough]")
    out: dict[str, tuple[str, ...]] = {}
    for child, roots in table.items():
        if child not in entries:
            raise RegistryError(f"{where}: [follows] names '{child}', which is not a direct input")
        if child == FOLLOWS_ROOT:
            raise RegistryError(f"{where}: [follows] cannot make '{FOLLOWS_ROOT}' follow itself")
        if not entries[child][1]:
            raise RegistryError(
                f"{where}: [follows] names '{child}', which has flake = false; Nix ignores follows on a non-flake input"
            )
        if not isinstance(roots, list) or not roots or len(set(map(str, roots))) != len(roots):
            raise RegistryError(f"{where}: [follows] '{child}' must be a non-empty list of distinct names")
        names = tuple(str(root) for root in roots)
        for root in names:
            if root != FOLLOWS_ROOT:
                raise RegistryError(f"{where}: [follows] '{child}' names '{root}'; only '{FOLLOWS_ROOT}' is supported")
        out[child] = names
    return out


def _digest(sources: tuple[Source, ...]) -> str:
    """Hash the validated content, so comments and spacing in the file do not change it."""

    canonical = [{"name": s.name, "url": s.url, "flake": s.flake, "follows": list(s.follows)} for s in sources]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return "sha256-" + hashlib.sha256(payload).hexdigest()

"""Read and validate the V5 registry, ``vendomat.toml`` (``REG-*``).

The registry names the direct source inputs of one project. It selects no revision: Nix
resolves revisions and owns ``flake.lock``. This module only reads and validates. It never
writes the registry (``REG-009``) and never fetches an input.

Four tables exist. ``[forge]`` names the one source collection. ``[inputs]`` and
``[passthrough]`` hold input entries. ``[follows]`` lists, per direct flake input, the child
inputs that follow the root ``nixpkgs``.

An ``[inputs]`` entry without a ``url`` lives in the collection. Every ``[inputs]`` entry pins a
tag, so a lock never follows a moving branch (``REG-017``).
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
#: A repository name in the collection. It may hold dots, which an input name cannot.
REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
INPUT_KEYS = frozenset({"url", "repo", "ref", "rev", "flake", "mirror", "keep", "backup"})
PASSTHROUGH_KEYS = frozenset({"url", "ref", "rev", "flake", "backup"})
FORGE_KEYS = frozenset({"url"})
TABLES = frozenset({"forge", "inputs", "passthrough", "follows"})
#: The only root input a ``[follows]`` entry may name. A wider mapping needs its own fixture.
FOLLOWS_ROOT = "nixpkgs"
#: Inputs that are never copied into the collection or onto a machine. They are huge.
NEVER_LOCAL = frozenset({"nixpkgs", "devenv"})
TAG_PREFIX = "refs/tags/"

_URL_RE = re.compile(r"[^\s\x00-\x1f\x7f\"\\$#]+")
_REF_RE = re.compile(r"[A-Za-z0-9._/+-]+")
_REV_RE = re.compile(r"[0-9a-f]{40,64}")


class RegistryError(Exception):
    """A registry problem. The message names the file and the entry or key."""


@dataclass(frozen=True)
class Source:
    """One direct input. ``url`` already carries ``ref`` and ``rev`` as query parameters.

    ``mirror``, ``keep``, and ``backup`` never reach the generated flake. They steer the source
    collection and the owner's explicit fallback.
    """

    name: str
    url: str
    flake: bool
    follows: tuple[str, ...]
    in_forge: bool = False
    mirror: bool = False
    keep: bool = False
    backup: str | None = None


@dataclass(frozen=True)
class Registry:
    """A validated registry. ``sources`` is sorted by name, so output order never depends on the file."""

    sources: tuple[Source, ...]
    digest: str
    forge: str | None = None


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
        raise RegistryError(
            f"{where}: unknown table [{unknown[0]}]; expected [forge], [inputs], [passthrough], or [follows]"
        )
    if "inputs" not in data:
        raise RegistryError(f"{where}: the registry needs an [inputs] table")

    forge = _forge(where, data.get("forge"))
    entries: dict[str, Source] = {}
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
            entries[name] = _entry(where, table, name, entry, forge)

    follows = _follows(where, data.get("follows", {}), entries)
    sources = tuple(_with_follows(entries[name], follows.get(name, ())) for name in sorted(entries))
    return Registry(sources=sources, digest=_digest(sources), forge=forge)


def _with_follows(source: Source, follows: tuple[str, ...]) -> Source:
    return Source(
        name=source.name,
        url=source.url,
        flake=source.flake,
        follows=follows,
        in_forge=source.in_forge,
        mirror=source.mirror,
        keep=source.keep,
        backup=source.backup,
    )


def _forge(where: str, raw: object) -> str | None:
    """The base URL of the one source collection, without a trailing slash."""

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise RegistryError(f"{where}: [forge] must be a table")
    for key in raw:
        if key not in FORGE_KEYS:
            raise RegistryError(f"{where}: unknown key '{key}' in [forge]; the only key is 'url'")
    url = raw.get("url")
    if not isinstance(url, str) or not _URL_RE.fullmatch(url) or "?" in url:
        raise RegistryError(f"{where}: [forge] needs a 'url' without a query, such as \"git://server\": {url!r}")
    return url.rstrip("/")


def _entry(where: str, table: str, name: str, entry: object, forge: str | None) -> Source:
    if not NAME_RE.fullmatch(name):
        raise RegistryError(f"{where}: input name '{name}' in [{table}] must match [a-z0-9][a-z0-9-]*")
    if not isinstance(entry, dict):
        raise RegistryError(f"{where}: [{table}] entry '{name}' must be a table")
    allowed = INPUT_KEYS if table == "inputs" else PASSTHROUGH_KEYS
    for key in entry:
        if key not in allowed:
            hint = ""
            if key in INPUT_KEYS:
                hint = f"; '{key}' is not allowed in [{table}]" + (
                    ", because nixpkgs and devenv are never copied" if key in ("mirror", "keep") else ""
                )
            raise RegistryError(
                f"{where}: unknown key '{key}' in {table} entry '{name}'{hint}; allowed keys: "
                f"{', '.join(sorted(allowed))}"
            )

    own_url = _string(where, name, entry, "url", _URL_RE)
    repo = _string(where, name, entry, "repo", REPO_RE)
    if own_url is not None and repo is not None:
        raise RegistryError(f"{where}: entry '{name}' sets 'repo' and 'url'; 'repo' names a repository in the forge")
    if own_url is None:
        if table == "passthrough":
            raise RegistryError(f"{where}: [passthrough] entry '{name}' needs a 'url'")
        if forge is None:
            raise RegistryError(
                f"{where}: entry '{name}' has no 'url' and the registry has no [forge] table; "
                'add [forge] url = "git://server" or give the entry a url'
            )
        base = f"{forge}/{repo or name}"
    else:
        base = own_url

    ref = _string(where, name, entry, "ref", _REF_RE)
    rev = _string(where, name, entry, "rev", _REV_RE)
    if table == "inputs":
        _check_pin(where, name, base, ref, rev)
    flake = _boolean(where, name, entry, "flake", True)
    mirror = _boolean(where, name, entry, "mirror", False)
    keep = _boolean(where, name, entry, "keep", False)
    if (mirror or keep) and name in NEVER_LOCAL:
        raise RegistryError(f"{where}: entry '{name}' sets mirror or keep; nixpkgs and devenv are never copied locally")
    if mirror and own_url is None:
        raise RegistryError(
            f"{where}: entry '{name}' sets mirror but has no 'url'; "
            "mirror copies an upstream repository, and a forge repository is already in the collection"
        )
    backup = _string(where, name, entry, "backup", _URL_RE)
    return Source(
        name=name,
        url=_with_query(where, name, base, ref, rev),
        flake=flake,
        follows=(),
        in_forge=own_url is None,
        mirror=mirror,
        keep=keep,
        backup=backup,
    )


def _check_pin(where: str, name: str, url: str, ref: str | None, rev: str | None) -> None:
    """Every ``[inputs]`` entry follows a tag, never a branch or a moving default (``REG-017``).

    A ``path:`` URL is a local checkout or a fixture. It has no ref, so it is exempt.
    """

    if url.startswith("path:"):
        return
    pinned = ref if ref is not None else _query_value(url, "ref")
    if pinned is None or not pinned.startswith(TAG_PREFIX) or pinned == TAG_PREFIX:
        extra = " A rev alone is not enough; add the tag that names it." if rev is not None else ""
        raise RegistryError(
            f"{where}: entry '{name}' must pin a tag: set ref = \"{TAG_PREFIX}<tag>\" "
            f"(got {pinned!r}). A branch or no pin follows a moving target.{extra}"
        )


def _query_value(url: str, key: str) -> str | None:
    for pair in url.partition("?")[2].split("&"):
        name, _, value = pair.partition("=")
        if name == key:
            return value
    return None


def _string(where: str, name: str, entry: dict, key: str, pattern: re.Pattern[str]) -> str | None:
    if key not in entry:
        return None
    value = entry[key]
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise RegistryError(f"{where}: '{key}' in entry '{name}' is not a valid {key}: {value!r}")
    return value


def _boolean(where: str, name: str, entry: dict, key: str, default: bool) -> bool:
    value = entry.get(key, default)
    if not isinstance(value, bool):
        raise RegistryError(f"{where}: '{key}' in entry '{name}' must be true or false")
    return value


def _with_query(where: str, name: str, url: str, ref: str | None, rev: str | None) -> str:
    """Add ``ref`` and ``rev`` as URL query parameters.

    Nix 2.34.7 rejects them as separate input attributes next to ``url`` (PV-13).
    """

    present = {pair.partition("=")[0] for pair in url.partition("?")[2].split("&") if pair}
    pairs = [("ref", ref), ("rev", rev)]
    for key, value in pairs:
        if value is not None and key in present:
            raise RegistryError(f"{where}: entry '{name}' sets '{key}' and also carries '{key}=' in its url; use one")
    extra = "&".join(f"{key}={value}" for key, value in pairs if value is not None)
    if not extra:
        return url
    return f"{url}{'&' if '?' in url else '?'}{extra}"


def _follows(where: str, raw: object, entries: dict[str, Source]) -> dict[str, tuple[str, ...]]:
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
        if not entries[child].flake:
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
    """Hash what the generator writes, so comments, spacing, and collection flags do not change it."""

    canonical = [{"name": s.name, "url": s.url, "flake": s.flake, "follows": list(s.follows)} for s in sources]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return "sha256-" + hashlib.sha256(payload).hexdigest()

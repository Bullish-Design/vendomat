"""Read a consuming repo's dependency set — the usage gate for knowledge install.

`read_deps` resolves the set of distribution names a repo depends on, normalized for comparison.
It reads exactly one source, by **precedence — first that exists wins**:

    1. uv.lock        — the fully resolved set (every transitively-installed package)
    2. pyproject.toml — the declared direct deps (`[project.dependencies]` + groups + optionals)
    3. repoman.lock   — the pinned `*man` toolchain (each entry's `package` dist name)

uv.lock is preferred because it reflects what is actually installed; pyproject is the declared
fallback; repoman.lock is the coarsest (one entry per manager) but still meaningful once names are
normalized. All names are PEP 503-normalized on the way out so the caller can intersect against
`vendor/libs/<lib>` names without worrying about `_`/`-`/case spelling.

Pure functions over an explicit ``Path`` — the CLI and the devenv module supply the real location.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from pathlib import Path

# PEP 508 requirement strings start with the distribution name; grab that leading token.
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize(name: str) -> str:
    """PEP 503 normalized distribution name (`Foo_Bar.baz` -> `foo-bar-baz`)."""

    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(req: str) -> str | None:
    """Distribution name from a PEP 508 requirement string, or None if unparseable."""

    m = _NAME_RE.match(req)
    return m.group(1) if m else None


def _from_uv_lock(path: Path) -> set[str]:
    """Every resolved package in a uv.lock (`[[package]]` tables with a `name`)."""

    data = tomllib.loads(path.read_text())
    return {normalize(p["name"]) for p in data.get("package", []) if "name" in p}


def _from_pyproject(path: Path) -> set[str]:
    """Declared deps in a pyproject.toml: `[project.dependencies]`, its optionals, and PEP 735
    `[dependency-groups]`."""

    data = tomllib.loads(path.read_text())
    out: set[str] = set()

    project = data.get("project", {})
    reqs: list[str] = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        reqs.extend(group)

    # PEP 735 groups: entries are requirement strings or `{include-group = "..."}` tables.
    for group in data.get("dependency-groups", {}).values():
        reqs.extend(r for r in group if isinstance(r, str))

    for req in reqs:
        name = _requirement_name(req)
        if name:
            out.add(normalize(name))
    return out


def _from_repoman_lock(path: Path) -> set[str]:
    """The pinned `*man` toolchain: each entry's `package` dist name.

    Covers the `[repoman]` self entry and every `[managers.*]` entry, including pseudo-entries
    like `[managers.git-pyjutsu]` whose `package` is a native dist (`pyjutsu`). Coarser than
    uv.lock (one entry per manager), but normalization makes the intersection meaningful.
    """

    data = tomllib.loads(path.read_text())
    out: set[str] = set()

    repoman = data.get("repoman", {})
    if "package" in repoman:
        out.add(normalize(repoman["package"]))

    for entry in data.get("managers", {}).values():
        if isinstance(entry, dict) and "package" in entry:
            out.add(normalize(entry["package"]))

    return out


# Precedence order: first file that exists wins (see module docstring).
_SOURCES: tuple[tuple[str, Callable[[Path], set[str]]], ...] = (
    ("uv.lock", _from_uv_lock),
    ("pyproject.toml", _from_pyproject),
    ("repoman.lock", _from_repoman_lock),
)


def read_deps(repo_root: Path) -> set[str]:
    """Normalized distribution names the repo at ``repo_root`` depends on.

    Reads the first of uv.lock / pyproject.toml / repoman.lock that exists; returns an empty set
    if none do.
    """

    for filename, parser in _SOURCES:
        path = repo_root / filename
        if path.is_file():
            return parser(path)
    return set()


def read_resolved_versions(repo_root: Path) -> dict[str, str]:
    """Concrete resolved versions per normalized dist name — the input to review-on-bump (M4).

    Only ``uv.lock`` carries exact resolved versions (``[[package]]`` ``name`` + ``version``);
    pyproject/repoman only pin ranges or manager floors, from which no single "installed" version
    can be read. So this reads ``uv.lock`` when present and returns ``{}`` otherwise — meaning
    "resolved versions unknown", which ``vendomat doctor`` treats as *cannot judge staleness*
    (skills stay green) rather than a failure.
    """

    path = repo_root / "uv.lock"
    if not path.is_file():
        return {}
    data = tomllib.loads(path.read_text())
    return {normalize(p["name"]): str(p["version"]) for p in data.get("package", []) if "name" in p and "version" in p}

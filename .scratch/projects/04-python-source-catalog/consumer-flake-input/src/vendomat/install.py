"""Install per-dependency knowledge skills into a consumer repo + record a manifest.

Mirrors :mod:`repoman.devman.install` (copied, not imported — vendomat carries no `repoman`
dependency). The differences from devman are deliberate:

- skills are **usage-gated**: only libs the repo actually depends on are installed (the
  intersection of ``expected_libs`` with the repo's resolved dep set);
- each skill lands as a **flat sibling** ``<skills_dir>/dep-<lib>/SKILL.md`` (the ``dep-`` prefix
  keeps vendomat's skills from clobbering repoman/devman's ``<name>/SKILL.md`` — different names,
  they coexist);
- the manifest is ``.vendor-source`` and records, per installed skill, the **pin** the skill was
  written against (from each lib's ``meta.toml``) so M4 can flag staleness.

Pure functions over explicit ``Path`` args — fully unit-testable; the CLI and devenv module supply
the real ``vendor_root`` / ``skills_dir`` / ``repo_root``.
"""

from __future__ import annotations

import re
import shutil
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .deps import normalize

MANIFEST = ".vendor-source"
LIB_PREFIX = "dep-"

# A constraints entry is useful to M4 only when it unambiguously pins one bare distribution to
# one exact version. Deliberately do not accept extras, markers, ranges, URLs, or arbitrary
# ``===`` requirements: those do not answer the review-on-bump question safely.
_EXACT_CONSTRAINT_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s=;#]+)\s*$")


def _libs_dir(vendor_root: Path) -> Path:
    return vendor_root / "libs"


def expected_libs(vendor_root: Path) -> list[str]:
    """Lib names under ``vendor/libs/<lib>/`` that ship a ``SKILL.md`` (sorted)."""

    libs = _libs_dir(vendor_root)
    if not libs.is_dir():
        return []
    return sorted(p.name for p in libs.iterdir() if (p / "SKILL.md").is_file())


def lib_pin(vendor_root: Path, lib: str) -> str:
    """The version a lib's skill was written against.

    An exact ``<lib>==<version>`` entry in the shared ``constraints.txt`` takes precedence over
    the entry-local ``[lib].pin``. This keeps every installed manifest tied to the shared pin that
    consumer libraries reference, while preserving metadata-only entries during the incremental
    M2 → M4 rollout. Returns ``"unpinned"`` if neither source has a concrete pin.
    """

    constraint = _constraint_pin(vendor_root, lib)
    if constraint:
        return constraint

    meta = _libs_dir(vendor_root) / lib / "meta.toml"
    if not meta.is_file():
        return "unpinned"
    data = tomllib.loads(meta.read_text())
    pin = data.get("lib", {}).get("pin")
    return str(pin) if pin else "unpinned"


def _constraint_pin(vendor_root: Path, lib: str) -> str | None:
    """Return an exact pin for ``lib`` from ``vendor/constraints.txt``, if supplied.

    Constraints intentionally use pip/uv syntax. Only an exact ``==`` pin is usable for a
    review-on-bump comparison; ranges, editable requirements, and malformed lines are ignored.
    """

    constraints = vendor_root / "constraints.txt"
    if not constraints.is_file():
        return None
    normalized_lib = normalize(lib)
    for raw in constraints.read_text().splitlines():
        line = raw.split("#", 1)[0]
        match = _EXACT_CONSTRAINT_RE.fullmatch(line)
        if not match:
            continue
        name, pin = match.groups()
        if normalize(name) == normalized_lib:
            return pin
    return None


def _vendomat_version() -> str:
    try:
        return version("vendomat")
    except PackageNotFoundError:  # pragma: no cover - only when run uninstalled
        return "0+unknown"


def matched_libs(vendor_root: Path, deps: set[str]) -> list[str]:
    """Libs with a skill whose normalized name is in the repo's (normalized) dep set."""

    normalized_deps = {normalize(d) for d in deps}
    return [lib for lib in expected_libs(vendor_root) if normalize(lib) in normalized_deps]


def install_knowledge(vendor_root: Path, deps: set[str], skills_dir: str, repo_root: Path) -> list[Path]:
    """Install knowledge skills for the deps the repo actually uses; write ``.vendor-source``.

    Copies each matched ``vendor/libs/<lib>/SKILL.md`` to ``<repo>/<skills_dir>/dep-<lib>/SKILL.md``
    and writes the drift manifest. Idempotent: re-running with the same inputs overwrites in place
    and produces a byte-stable manifest (no duplicate entries).
    """

    libs = matched_libs(vendor_root, deps)
    skills_root = repo_root / skills_dir
    written: list[Path] = []

    for lib in libs:
        dest = skills_root / f"{LIB_PREFIX}{lib}"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_libs_dir(vendor_root) / lib / "SKILL.md", dest / "SKILL.md")
        written.append(dest / "SKILL.md")

    manifest = skills_root / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pins = "\n".join(f"  {LIB_PREFIX}{lib} @ {lib_pin(vendor_root, lib)}" for lib in libs)
    manifest.write_text(
        "Generated by vendomat (knowledge layer). Do not edit; re-run `vendomat sync`.\n"
        f"vendomat version: {_vendomat_version()}\n"
        f"skills: {', '.join(f'{LIB_PREFIX}{lib}' for lib in libs)}\n"
        "pins:\n" + (pins + "\n" if pins else "")
    )
    written.append(manifest)
    return written


def parse_manifest_pins(text: str) -> dict[str, str]:
    """Read the ``pins:`` block of a ``.vendor-source`` manifest back into ``{lib: pin}``.

    Each pin line is ``  dep-<lib> @ <pin>`` (see :func:`install_knowledge`); the ``dep-`` prefix is
    stripped so the key matches the ``vendor/libs/<lib>`` name. Lines without ``@`` or the prefix are
    skipped. Returns ``{}`` when there is no ``pins:`` section. This is what M4's review-on-bump
    compares against the consumer's resolved versions — the pin *the installed skill was written
    against*, not whatever the current vendor tree now says.
    """

    pins: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.rstrip() == "pins:":
            in_block = True
            continue
        if not in_block:
            continue
        entry = line.strip()
        if not entry.startswith(LIB_PREFIX) or " @ " not in entry:
            continue
        name, _, pin = entry.partition(" @ ")
        lib = name[len(LIB_PREFIX) :].strip()
        pin = pin.strip()
        if lib and pin:
            pins[lib] = pin
    return pins

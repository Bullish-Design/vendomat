"""Self-checks for `vendomat doctor` — the *man-family 0/1/2/3 exit-code contract.

This mirrors the *shape* of repoman's ``checks.SelfCheck`` / ``aggregate.worst_exit`` — copied,
not imported, so vendomat carries no dependency on the ``repoman`` package. The one deliberate
change: ``SelfCheck`` is a Pydantic model (not a dataclass) so doctor output is normalized like
the rest of the *man family, while keeping the identical level → exit-code mapping.

A check ``level`` contributes to the exit code: ``ok``/``warn`` are non-fatal (0); ``fail`` is
broken wiring → 2 (infra/config). Domain decisions (exit 1) and invalid usage (exit 3) are
raised by the commands themselves, not by self-checks.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .deps import normalize, resolved_versions
from .install import (
    LIB_PREFIX,
    MANIFEST,
    expected_libs,
    lib_pin,
    matched_libs,
    read_constraints,
    read_manifest_pins,
)
from .models import LibMeta, SkillFrontmatter, split_frontmatter

_LEVELS: dict[str, int] = {"ok": 0, "warn": 0, "fail": 2}


class SelfCheck(BaseModel):
    """One named self-check result under the shared exit-code contract."""

    name: str
    level: str  # "ok" | "warn" | "fail"
    detail: str = ""


def self_check_exit(checks: list[SelfCheck]) -> int:
    """Worst exit contribution across the self-checks (0 if there are none)."""

    return max((_LEVELS.get(c.level, 2) for c in checks), default=0)


def format_self_check(checks: list[SelfCheck]) -> str:
    """Render the checks as an aligned ``LEVEL name — detail`` report."""

    mark = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
    return "\n".join(f"{mark.get(c.level, '?')} {c.name}" + (f" — {c.detail}" if c.detail else "") for c in checks)


def vendor_checks(repo_root: Path, skills_dir: str, vendor_root: Path, deps: set[str]) -> list[SelfCheck]:
    """Knowledge-layer drift checks for ``vendomat doctor`` (mirrors devman's ``devman_checks``).

    Are the skills the repo's deps *should* have installed actually present, and is the manifest at
    the current vendomat version? **Warn-only** for now (like devman) — knowledge is advisory, not
    mandatory; flip to ``fail`` if it ever becomes required.
    """

    skills_root = repo_root / skills_dir
    manifest = skills_root / MANIFEST
    want = matched_libs(vendor_root, deps)
    # Authoring-side checks (frontmatter validity + constraints lockstep) only apply when a real vendor
    # tree is present; in a consumer this is the read-only nix-store knowledge source.
    out: list[SelfCheck] = (
        [_frontmatter_check(vendor_root), _constraints_check(vendor_root)] if (vendor_root / "libs").is_dir() else []
    )

    # Nothing expected and nothing installed → a clean repo, not a problem (keep any authoring checks).
    if not want and not manifest.exists():
        return out + [
            SelfCheck(name="vendor:manifest", level="ok", detail="no knowledge installed (run `vendomat sync`)")
        ]

    missing = [lib for lib in want if not (skills_root / f"{LIB_PREFIX}{lib}" / "SKILL.md").is_file()]
    missing_detail = f"missing {[LIB_PREFIX + m for m in missing]} — run `vendomat sync`"
    out.append(
        SelfCheck(
            name="vendor:skills",
            level="ok" if not missing else "warn",
            detail="all installed" if not missing else missing_detail,
        )
    )

    if manifest.exists():
        try:
            current = f"vendomat version: {version('vendomat')}"
        except PackageNotFoundError:  # pragma: no cover - only when run uninstalled
            current = "vendomat version: 0+unknown"
        fresh = current in manifest.read_text()
        out.append(
            SelfCheck(
                name="vendor:current",
                level="ok" if fresh else "warn",
                detail="up to date" if fresh else "manifest stale — re-run `vendomat sync`",
            )
        )
        out.append(_staleness_check(skills_root, repo_root))

    return out


def _staleness_check(skills_root: Path, repo_root: Path) -> SelfCheck:
    """Review-on-bump: flag a skill whose recorded pin no longer matches the resolved version (M4).

    For each ``dep-<lib> @ <pin>`` recorded in ``.vendor-source`` at sync time, compare ``<pin>`` to
    the version the repo currently resolves the lib to (``uv.lock``). A divergence means the skill was
    written for an older version and should be reviewed (DESIGN §7.5). **Warn-only** — a bump is a
    prompt to re-curate, not broken wiring.

    Skips judgement (counts as fine) for any skill that is ``unpinned`` or whose lib has no resolved
    version available (no ``uv.lock``, or the lib is no longer in the resolved set) — a bump it cannot
    see is not flagged rather than guessed.
    """

    pins = read_manifest_pins(skills_root)
    resolved = resolved_versions(repo_root)

    stale: list[str] = []
    for skill, pin in pins.items():
        if pin == "unpinned":
            continue
        lib = skill[len(LIB_PREFIX) :] if skill.startswith(LIB_PREFIX) else skill
        current = resolved.get(normalize(lib))
        if current is not None and current != pin:
            stale.append(f"{skill} (skill@{pin} → repo@{current})")

    return SelfCheck(
        name="vendor:staleness",
        level="ok" if not stale else "warn",
        detail="pins current" if not stale else f"review stale skill(s): {', '.join(stale)}",
    )


def _constraints_check(vendor_root: Path) -> SelfCheck:
    """Lockstep: every authored ``meta.toml`` pin must match ``vendor/constraints.txt`` (M4).

    ``constraints.txt`` is the single source of truth for external pins (DESIGN §7.3); each entry's
    ``[lib].pin`` is meant to track it. Warns when a pinned lib is missing from ``constraints.txt`` or
    its constraint disagrees with the entry's pin, so the two never silently drift. ``unpinned`` entries
    are skipped (nothing to reconcile). **Warn-only.**
    """

    constraints = read_constraints(vendor_root)
    mismatched: list[str] = []
    for lib in expected_libs(vendor_root):
        pin = lib_pin(vendor_root, lib)
        if pin == "unpinned":
            continue
        constraint = constraints.get(normalize(lib))
        if constraint is None:
            mismatched.append(f"{lib} (pinned {pin}, absent from constraints.txt)")
        elif constraint != pin:
            mismatched.append(f"{lib} (meta {pin} ≠ constraints {constraint})")

    return SelfCheck(
        name="vendor:constraints",
        level="ok" if not mismatched else "warn",
        detail="pins in lockstep" if not mismatched else f"drift: {'; '.join(mismatched)}",
    )


def _frontmatter_check(vendor_root: Path) -> SelfCheck:
    """Validate that every authored entry's SKILL.md frontmatter + meta.toml are structurally sound.

    Catches malformed *drafts* before they reach an agent (DESIGN §9: "Pydantic-validated frontmatter
    so drafts can't ship malformed"). Structural only — a DRAFT entry with TODO prose still validates;
    this flags genuinely broken frontmatter/meta, not unfinished curation. **Warn-only.**
    """

    libs_dir = vendor_root / "libs"
    invalid: list[str] = []
    for lib in expected_libs(vendor_root):
        entry = libs_dir / lib
        try:
            front, _ = split_frontmatter((entry / "SKILL.md").read_text())
            SkillFrontmatter.model_validate(front)
            LibMeta.from_toml((entry / "meta.toml").read_text())
        except (ValidationError, ValueError, OSError):
            invalid.append(lib)

    return SelfCheck(
        name="vendor:frontmatter",
        level="ok" if not invalid else "warn",
        detail="all entries valid" if not invalid else f"malformed entries: {invalid} — fix before publishing",
    )

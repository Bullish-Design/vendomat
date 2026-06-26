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

from pydantic import BaseModel

from .install import LIB_PREFIX, MANIFEST, matched_libs

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
    out: list[SelfCheck] = []

    # Nothing expected and nothing installed → a clean repo, not a problem.
    if not want and not manifest.exists():
        return [SelfCheck(name="vendor:manifest", level="ok", detail="no knowledge installed (run `vendomat sync`)")]

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

    return out

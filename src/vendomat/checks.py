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

from pydantic import BaseModel

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

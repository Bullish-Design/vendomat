"""Unit tests for the self-check exit-code contract (copied repoman SelfCheck shape)."""

from __future__ import annotations

from vendomat.checks import SelfCheck, format_self_check, self_check_exit


def test_empty_is_zero():
    assert self_check_exit([]) == 0


def test_ok_and_warn_are_non_fatal():
    checks = [
        SelfCheck(name="a", level="ok"),
        SelfCheck(name="b", level="warn", detail="heads up"),
    ]
    assert self_check_exit(checks) == 0


def test_fail_is_infra_config_two():
    checks = [
        SelfCheck(name="a", level="ok"),
        SelfCheck(name="b", level="fail", detail="broken"),
    ]
    assert self_check_exit(checks) == 2


def test_unknown_level_treated_as_fail():
    assert self_check_exit([SelfCheck(name="x", level="bogus")]) == 2


def test_format_renders_levels_and_detail():
    out = format_self_check([SelfCheck(name="x", level="warn", detail="why")])
    assert "WARN x — why" in out

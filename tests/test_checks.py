"""Unit tests for the self-check exit-code contract (copied repoman SelfCheck shape)."""

from __future__ import annotations

from pathlib import Path

from vendomat.checks import MANIFEST, SelfCheck, format_self_check, self_check_exit, vendor_checks
from vendomat.install import install_knowledge


def _seed_lib(vendor: Path, lib: str, pin: str = "0.12.5") -> None:
    d = vendor / "libs" / lib
    d.mkdir(parents=True)
    # A structurally-valid entry (real frontmatter + full meta) so the vendor:frontmatter check is ok.
    (d / "SKILL.md").write_text(f"---\nname: dep-{lib}\ndescription: use {lib}\n---\n\n# skill\n")
    (d / "meta.toml").write_text(
        f'[lib]\nname = "{lib}"\nversion = ">=0"\npin = "{pin}"\ndocs = "https://x"\n\n'
        '[curation]\nwhy = "y"\nrejected = "n"\n'
    )


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


# --- vendor_checks (doctor drift) -------------------------------------------------------------


def test_vendor_checks_clean_repo_is_ok(tmp_path):
    # No vendor root, no manifest → nothing expected, nothing installed.
    checks = vendor_checks(tmp_path, ".claude/skills", tmp_path / "nope", set())
    assert self_check_exit(checks) == 0
    assert any("no knowledge installed" in c.detail for c in checks)


def test_vendor_checks_up_to_date(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer")
    repo = tmp_path / "repo"
    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)

    checks = vendor_checks(repo, ".claude/skills", vendor, {"typer"})
    assert self_check_exit(checks) == 0
    assert {c.name for c in checks} == {"vendor:frontmatter", "vendor:skills", "vendor:current"}
    assert all(c.level == "ok" for c in checks)


def test_vendor_checks_missing_skill_warns(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer")
    repo = tmp_path / "repo"  # nothing installed

    checks = vendor_checks(repo, ".claude/skills", vendor, {"typer"})
    skills = next(c for c in checks if c.name == "vendor:skills")
    assert skills.level == "warn"
    assert "dep-typer" in skills.detail
    assert self_check_exit(checks) == 0  # warn-only for now


def test_vendor_checks_stale_manifest_warns(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer")
    repo = tmp_path / "repo"
    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)

    manifest = repo / ".claude/skills" / MANIFEST
    manifest.write_text(manifest.read_text().replace("vendomat version:", "vendomat version: 0.0.0-old #"))

    checks = vendor_checks(repo, ".claude/skills", vendor, {"typer"})
    current = next(c for c in checks if c.name == "vendor:current")
    assert current.level == "warn"
    assert "stale" in current.detail

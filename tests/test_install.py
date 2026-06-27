"""Unit tests for knowledge install: usage-gating, manifest, idempotency."""

from __future__ import annotations

from pathlib import Path

from vendomat.install import (
    MANIFEST,
    expected_libs,
    install_knowledge,
    matched_libs,
    read_constraints,
    read_manifest_pins,
)


def _seed_lib(vendor_root: Path, lib: str, pin: str = "1.2.3", skill: str = "# skill\n") -> None:
    d = vendor_root / "libs" / lib
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(skill)
    (d / "meta.toml").write_text(f'[lib]\nname = "{lib}"\npin = "{pin}"\n')


def test_expected_libs_lists_only_dirs_with_skill(tmp_path):
    _seed_lib(tmp_path, "typer")
    (tmp_path / "libs" / "no-skill").mkdir()
    assert expected_libs(tmp_path) == ["typer"]


def test_matched_libs_is_usage_gated_and_normalized(tmp_path):
    _seed_lib(tmp_path, "typer")
    # deps spelled differently (case / separators) still match via PEP 503.
    assert matched_libs(tmp_path, {"Typer", "click"}) == ["typer"]
    assert matched_libs(tmp_path, {"click"}) == []


def test_install_only_intersecting_skill(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    _seed_lib(vendor, "rich")  # present in the tree but NOT a dep → must not install
    repo = tmp_path / "repo"

    written = install_knowledge(vendor, {"typer"}, ".claude/skills", repo)

    installed = repo / ".claude/skills/dep-typer/SKILL.md"
    assert installed.is_file()
    assert not (repo / ".claude/skills/dep-rich").exists()
    assert installed in written


def test_unrelated_dep_installs_nothing_but_writes_manifest(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer")
    repo = tmp_path / "repo"

    install_knowledge(vendor, {"click"}, ".claude/skills", repo)

    assert not (repo / ".claude/skills/dep-typer").exists()
    manifest = repo / ".claude/skills" / MANIFEST
    assert manifest.is_file()
    assert "skills: \n" in manifest.read_text() or "skills:\n" in manifest.read_text()


def test_manifest_records_pin(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    repo = tmp_path / "repo"

    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)
    text = (repo / ".claude/skills" / MANIFEST).read_text()
    assert "dep-typer @ 0.12.5" in text


def test_idempotent_rerun(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    repo = tmp_path / "repo"

    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)
    manifest = repo / ".claude/skills" / MANIFEST
    first = manifest.read_text()
    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)
    second = manifest.read_text()

    # No dupes, byte-stable manifest.
    assert first == second
    skills = list((repo / ".claude/skills").glob("dep-*/SKILL.md"))
    assert len(skills) == 1


# --- read_manifest_pins (review-on-bump input) -------------------------------------------------


def test_read_manifest_pins_round_trips_the_writer(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    _seed_lib(vendor, "click", pin="8.1.7")
    repo = tmp_path / "repo"
    install_knowledge(vendor, {"typer", "click"}, ".claude/skills", repo)

    pins = read_manifest_pins(repo / ".claude/skills")
    assert pins == {"dep-typer": "0.12.5", "dep-click": "8.1.7"}


def test_read_manifest_pins_absent_manifest_is_empty(tmp_path):
    assert read_manifest_pins(tmp_path / "nope") == {}


# --- read_constraints --------------------------------------------------------------------------


def test_read_constraints_parses_pins_and_skips_noise(tmp_path):
    (tmp_path / "constraints.txt").write_text(
        "# a comment\n\ntyper==0.12.5\nPydantic == 2.12.0  # trailing comment\nnot-a-pin>=1\n"
    )
    assert read_constraints(tmp_path) == {"typer": "0.12.5", "pydantic": "2.12.0"}


def test_read_constraints_absent_file_is_empty(tmp_path):
    assert read_constraints(tmp_path) == {}

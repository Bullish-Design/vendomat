"""Unit tests for knowledge install: usage-gating, manifest, idempotency."""

from __future__ import annotations

from pathlib import Path

from vendomat.install import (
    MANIFEST,
    expected_libs,
    install_knowledge,
    lib_pin,
    matched_libs,
    parse_manifest_pins,
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


def test_shared_constraint_is_the_manifest_pin(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    (vendor / "constraints.txt").write_text("typer==0.13.0\n")
    repo = tmp_path / "repo"

    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)

    assert lib_pin(vendor, "typer") == "0.13.0"
    assert "dep-typer @ 0.13.0" in (repo / ".claude/skills" / MANIFEST).read_text()


def test_metadata_pin_is_used_without_an_applicable_exact_constraint(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    (vendor / "constraints.txt").write_text(
        "# Comments, ranges, markers, extras, and malformed exact requirements are ignored.\n"
        "typer>=0.13\n"
        "typer==0.13 ; python_version >= '3.13'\n"
        "typer[all]==0.13\n"
        "typer===0.13\n"
        "other==1.0\n"
    )
    repo = tmp_path / "repo"

    install_knowledge(vendor, {"typer"}, ".claude/skills", repo)

    assert lib_pin(vendor, "typer") == "0.12.5"
    assert "dep-typer @ 0.12.5" in (repo / ".claude/skills" / MANIFEST).read_text()


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


# --- parse_manifest_pins (M4 round-trip) ------------------------------------------------------


def test_manifest_pins_round_trip(tmp_path):
    vendor = tmp_path / "vendor"
    _seed_lib(vendor, "typer", pin="0.12.5")
    _seed_lib(vendor, "pydantic", pin="2.7.0")
    repo = tmp_path / "repo"
    install_knowledge(vendor, {"typer", "pydantic"}, ".claude/skills", repo)

    manifest = (repo / ".claude/skills" / MANIFEST).read_text()
    assert parse_manifest_pins(manifest) == {"typer": "0.12.5", "pydantic": "2.7.0"}


def test_manifest_pins_unpinned_lib(tmp_path):
    vendor = tmp_path / "vendor"
    d = vendor / "libs" / "bare"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# skill\n")  # no meta.toml → pin is "unpinned"
    repo = tmp_path / "repo"
    install_knowledge(vendor, {"bare"}, ".claude/skills", repo)

    manifest = (repo / ".claude/skills" / MANIFEST).read_text()
    assert parse_manifest_pins(manifest) == {"bare": "unpinned"}


def test_manifest_pins_no_block_is_empty():
    assert parse_manifest_pins("vendomat version: 1.0\nskills:\n") == {}

"""Unit tests for knowledge install: usage-gating, manifest, idempotency."""

from __future__ import annotations

from pathlib import Path

from vendomat.install import MANIFEST, expected_libs, install_knowledge, matched_libs


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

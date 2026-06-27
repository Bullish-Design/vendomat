"""Unit tests for the `vendor add` drafter — offline gather, render/validate, scaffold, no-clobber.

The metadata lookup is **injected** so every test is offline and deterministic; none target the
seeded ``typer`` entry (fresh names only), so the round-trip-into-M2 test exercises a clean entry.
"""

from __future__ import annotations

import pytest

from vendomat.add import (
    DistInfo,
    DraftMaterial,
    EntryExistsError,
    gather,
    render_meta,
    render_skill,
    scaffold,
)
from vendomat.checks import self_check_exit, vendor_checks
from vendomat.install import install_knowledge, lib_pin, matched_libs
from vendomat.models import LibMeta, SkillFrontmatter, split_frontmatter


def _full(name: str) -> DistInfo:
    return DistInfo(version="2.5.0", summary=f"{name} does things", docs=f"https://{name}.example/docs")


def _lookup(mapping):
    return lambda n: mapping.get(n)


# --- gather ------------------------------------------------------------------------------------


def test_gather_fills_from_metadata():
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    assert (m.lib, m.version_range, m.pin) == ("widgets", ">=2.5.0", "2.5.0")
    assert m.gathered and m.missing == []
    assert m.docs == "https://widgets.example/docs"


def test_gather_normalizes_lib_name():
    m = gather("Foo_Bar", lookup=_lookup({"foo-bar": _full("foo-bar")}))
    assert m.lib == "foo-bar"


def test_gather_records_partial_metadata():
    m = gather("widgets", lookup=_lookup({"widgets": DistInfo(version="1.0.0")}))
    assert m.gathered
    assert m.missing == ["docs", "summary"]
    assert m.docs.startswith("TODO") and m.summary.startswith("TODO")
    assert m.pin == "1.0.0"  # pin still derives from version


def test_gather_degrades_when_uninstalled():
    m = gather("ghost", lookup=_lookup({}))
    assert not m.gathered
    assert m.pin == "TODO" and m.version_range == "TODO"
    assert m.missing == ["version", "pin", "docs", "summary"]


# --- render / validate -------------------------------------------------------------------------


def test_rendered_skill_frontmatter_validates():
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    data, body = split_frontmatter(render_skill(m))
    front = SkillFrontmatter.model_validate(data)
    assert front.name == "dep-widgets"
    assert front.description  # non-empty trigger text (a TODO stub, but present)
    assert "DRAFT" in body


def test_rendered_meta_validates_even_when_degraded():
    m = gather("ghost", lookup=_lookup({}))
    meta = LibMeta.from_toml(render_meta(m))
    assert meta.lib.name == "ghost"
    assert meta.lib.pin == "TODO"
    assert meta.curation.why  # stubbed, but present and well-formed


# --- scaffold + no-clobber ---------------------------------------------------------------------


def test_scaffold_writes_three_files(tmp_path):
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    written = scaffold(tmp_path / "vendor", "widgets", m)
    names = {p.name for p in written}
    assert names == {"meta.toml", "notes.md", "SKILL.md"}
    assert all(p.is_file() for p in written)


def test_scaffold_refuses_existing_entry(tmp_path):
    vendor = tmp_path / "vendor"
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    scaffold(vendor, "widgets", m)
    sentinel = vendor / "libs" / "widgets" / "SKILL.md"
    sentinel.write_text("CURATED — do not clobber\n")

    with pytest.raises(EntryExistsError):
        scaffold(vendor, "widgets", m)
    assert sentinel.read_text() == "CURATED — do not clobber\n"  # untouched


def test_scaffold_force_overwrites(tmp_path):
    vendor = tmp_path / "vendor"
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    scaffold(vendor, "widgets", m)
    (vendor / "libs" / "widgets" / "SKILL.md").write_text("stale\n")

    scaffold(vendor, "widgets", m, force=True)
    assert "stale" not in (vendor / "libs" / "widgets" / "SKILL.md").read_text()


# --- round-trip into M2 ------------------------------------------------------------------------


def test_generated_entry_feeds_m2_pipeline(tmp_path):
    vendor = tmp_path / "vendor"
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    scaffold(vendor, "widgets", m)

    # M2 sees it as an installable, usage-gated entry.
    assert matched_libs(vendor, {"widgets"}) == ["widgets"]
    assert lib_pin(vendor, "widgets") == "2.5.0"

    repo = tmp_path / "repo"
    install_knowledge(vendor, {"widgets"}, ".claude/skills", repo)
    assert (repo / ".claude/skills/dep-widgets/SKILL.md").is_file()

    # doctor accepts it (warn-only frontmatter check passes; nothing missing/stale → exit 0).
    checks = vendor_checks(repo, ".claude/skills", vendor, {"widgets"})
    assert self_check_exit(checks) == 0
    assert any(c.name == "vendor:frontmatter" and c.level == "ok" for c in checks)


def test_doctor_flags_malformed_entry(tmp_path):
    vendor = tmp_path / "vendor"
    m = gather("widgets", lookup=_lookup({"widgets": _full("widgets")}))
    scaffold(vendor, "widgets", m)
    # Corrupt the frontmatter (drop the fence) — doctor should warn, not crash.
    (vendor / "libs" / "widgets" / "SKILL.md").write_text("no frontmatter\n")

    checks = vendor_checks(tmp_path / "repo", ".claude/skills", vendor, set())
    fm = next(c for c in checks if c.name == "vendor:frontmatter")
    assert fm.level == "warn" and "widgets" in fm.detail


def test_draftmaterial_is_constructible():
    # Guard the public shape the CLI depends on.
    m = DraftMaterial(lib="x", version_range=">=1", pin="1", docs="d", summary="s", gathered=True, missing=[])
    assert m.lib == "x"

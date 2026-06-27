"""Unit tests for the entry-format models — TOML/YAML round-trips and frontmatter validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from vendomat.models import (
    AutoTrigger,
    CurationSection,
    LibMeta,
    LibSection,
    SkillFrontmatter,
    split_frontmatter,
)


def _meta() -> LibMeta:
    return LibMeta(
        lib=LibSection(name="typer", version=">=0.12", pin="0.12.5", docs="https://typer.tiangolo.com"),
        curation=CurationSection(why="because", rejected="argparse"),
    )


def test_libmeta_round_trips_through_toml():
    meta = _meta()
    assert LibMeta.from_toml(meta.to_toml()) == meta


def test_skill_name_must_be_dep_prefixed():
    with pytest.raises(ValidationError):
        SkillFrontmatter(name="typer", description="x")
    with pytest.raises(ValidationError):
        SkillFrontmatter(name="dep-", description="x")
    assert SkillFrontmatter(name="dep-typer", description="x").name == "dep-typer"


def test_for_lib_normalizes_name():
    front = SkillFrontmatter.for_lib("Foo_Bar", description="x", keywords=["foo"])
    assert front.name == "dep-foo-bar"
    assert front.auto_trigger == AutoTrigger(keywords=["foo"])


def test_for_lib_without_keywords_omits_auto_trigger():
    front = SkillFrontmatter.for_lib("typer", description="x")
    assert front.auto_trigger is None
    # exclude_none → no empty auto_trigger key leaks into the rendered block.
    assert "auto_trigger" not in front.to_frontmatter_block()


def test_frontmatter_block_round_trips():
    front = SkillFrontmatter.for_lib("typer", description="use it: when building a CLI", keywords=["typer", "cli"])
    block = front.to_frontmatter_block()
    skill = block + "\n# body\n"
    data, body = split_frontmatter(skill)
    assert SkillFrontmatter.model_validate(data) == front
    assert body == "\n# body\n"


def test_split_frontmatter_parses_block_style_golden():
    # The seeded typer SKILL.md uses block-style YAML (nested auto_trigger.keywords) — must parse.
    golden = Path(__file__).resolve().parents[1] / "vendor" / "libs" / "typer" / "SKILL.md"
    data, body = split_frontmatter(golden.read_text())
    front = SkillFrontmatter.model_validate(data)
    assert front.name == "dep-typer"
    assert front.auto_trigger and "typer" in front.auto_trigger.keywords
    assert body.lstrip().startswith("#")


def test_split_frontmatter_requires_a_fence():
    with pytest.raises(ValueError):
        split_frontmatter("# no frontmatter here\n")
    with pytest.raises(ValueError):
        split_frontmatter("---\nname: dep-x\n")  # unterminated

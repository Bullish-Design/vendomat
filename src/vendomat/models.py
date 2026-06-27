"""Pydantic models for the two knowledge-entry formats — `meta.toml` and SKILL.md frontmatter.

These models are the **single source of truth** for the shapes M3 generates and M2 installs. A
draft that round-trips through them cannot ship malformed: ``vendor add`` builds the models first,
then renders, so every emitted ``meta.toml`` validates against :class:`LibMeta` and every SKILL.md
frontmatter validates against :class:`SkillFrontmatter` by construction (DESIGN §9, plan M3).

TOML is read with stdlib ``tomllib`` and written with ``tomli_w``; the SKILL.md frontmatter block
is YAML, handled with ``pyyaml``. Splitting/joining the ``---`` fence around the frontmatter is the
only hand-rolled bit (it is trivial and format-stable).
"""

from __future__ import annotations

import tomllib

import tomli_w
import yaml
from pydantic import BaseModel, field_validator

from .deps import normalize

FRONTMATTER_FENCE = "---"


# --- meta.toml ---------------------------------------------------------------------------------


class LibSection(BaseModel):
    """``[lib]`` — what the entry is about and the version its skill is written against."""

    name: str
    version: str
    pin: str
    docs: str


class CurationSection(BaseModel):
    """``[curation]`` — the human judgement: why this lib, and what was rejected."""

    why: str
    rejected: str


class LibMeta(BaseModel):
    """A full ``meta.toml``: ``[lib]`` + ``[curation]``. Round-trips to/from TOML."""

    lib: LibSection
    curation: CurationSection

    @classmethod
    def from_toml(cls, text: str) -> LibMeta:
        """Parse a ``meta.toml`` string into a validated :class:`LibMeta`."""

        return cls.model_validate(tomllib.loads(text))

    def to_toml(self) -> str:
        """Render this entry as ``meta.toml`` text (``tomli_w``)."""

        return tomli_w.dumps(self.model_dump())


# --- SKILL.md frontmatter ----------------------------------------------------------------------


class AutoTrigger(BaseModel):
    """``auto_trigger`` — devman-compatible keyword hints (discovery still rides ``description``)."""

    keywords: list[str] = []


class SkillFrontmatter(BaseModel):
    """The YAML frontmatter atop a SKILL.md: ``name`` / ``description`` / optional ``auto_trigger``.

    ``name`` must be ``dep-<lib>`` — the flat-sibling install name M2 writes to
    ``<skills_dir>/dep-<lib>/SKILL.md``. We enforce the ``dep-`` prefix here; the exact
    ``dep-<normalized-lib>`` value is guaranteed by the renderer that builds this model.
    """

    name: str
    description: str
    auto_trigger: AutoTrigger | None = None

    @field_validator("name")
    @classmethod
    def _name_is_dep_prefixed(cls, v: str) -> str:
        if not v.startswith("dep-") or v == "dep-":
            raise ValueError(f"skill name must be 'dep-<lib>', got {v!r}")
        return v

    @classmethod
    def for_lib(cls, lib: str, description: str, keywords: list[str] | None = None) -> SkillFrontmatter:
        """Build frontmatter for ``lib`` with the canonical ``dep-<normalized-lib>`` name."""

        return cls(
            name=f"dep-{normalize(lib)}",
            description=description,
            auto_trigger=AutoTrigger(keywords=keywords) if keywords else None,
        )

    def to_frontmatter_block(self) -> str:
        """Render the fenced YAML frontmatter block (``---`` … ``---``), trailing newline included."""

        body = yaml.safe_dump(
            self.model_dump(exclude_none=True),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
        return f"{FRONTMATTER_FENCE}\n{body}{FRONTMATTER_FENCE}\n"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a SKILL.md into ``(frontmatter_dict, body)``.

    Expects a leading ``---`` fenced YAML block (the format :meth:`SkillFrontmatter.to_frontmatter_block`
    emits and the devman/typer golden entry uses). Raises ``ValueError`` if the fence is missing or
    unterminated so a malformed entry is a loud failure, not a silent empty dict.
    """

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        raise ValueError("SKILL.md has no leading '---' frontmatter fence")

    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_FENCE:
            block = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            data = yaml.safe_load(block) or {}
            if not isinstance(data, dict):
                raise ValueError("SKILL.md frontmatter is not a mapping")
            return data, body

    raise ValueError("SKILL.md frontmatter fence is unterminated")

"""Draft a ``vendor/libs/<lib>/`` knowledge entry for human/agent curation (Face B tooling, M3).

``vendor add <lib>`` **scaffolds** the three-file entry M2 installs (``meta.toml`` + ``notes.md`` +
``SKILL.md``) and **mechanically pre-fills** every field it can derive offline from the installed
distribution's metadata (concrete ``version`` → ``pin``, ``docs`` URL, one-line summary). The prose
that needs judgement — ``[curation].why``/``rejected``, the SKILL.md how-to, the ``notes.md`` body —
is left as clearly-marked ``<!-- DRAFT -->`` / ``TODO`` stubs. The output is an *agent-curatable
draft*; a human or agent fills the prose, then it can be published and installed.

"Agent-assisted" means structured **for** an agent, not **calling** one: this module embeds no LLM
and never touches the network. Introspection is offline via ``importlib.metadata`` behind an
**injectable** lookup, so drafting is unit-testable without a real install and **degrades
gracefully** — when a dist is not importable in vendomat's own interpreter, fields become ``TODO``
placeholders and ``notes.md`` records what could not be gathered, rather than hard-failing.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path

from pydantic import BaseModel

from .deps import normalize
from .models import CurationSection, LibMeta, LibSection, SkillFrontmatter

DRAFT_MARK = "<!-- DRAFT — curate before publishing -->"


class EntryExistsError(Exception):
    """Raised by :func:`scaffold` when the entry already exists and ``force`` was not given."""

    def __init__(self, lib: str, path: Path) -> None:
        self.lib = lib
        self.path = path
        super().__init__(f"knowledge entry already exists: {path} (use --force to overwrite)")


class DistInfo(BaseModel):
    """What a metadata lookup can offer offline. ``summary``/``docs`` are best-effort (may be None)."""

    version: str
    summary: str | None = None
    docs: str | None = None


# A lookup maps a (normalized) dist name to its offline metadata, or None if not introspectable.
MetadataLookup = Callable[[str], "DistInfo | None"]


def _docs_url(meta) -> str | None:
    """Best-effort docs URL from dist metadata: a doc-ish ``Project-URL``, else ``Home-page``."""

    for entry in meta.get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if "doc" in label.strip().lower() and url.strip():
            return url.strip()
    home = meta.get("Home-page")
    return home.strip() if home else None


def default_lookup(lib: str) -> DistInfo | None:
    """Offline introspection via ``importlib.metadata`` (this interpreter only; None if absent)."""

    try:
        ver = version(lib)
    except PackageNotFoundError:
        return None
    summary: str | None = None
    docs: str | None = None
    try:
        meta = metadata(lib)
        summary = (meta.get("Summary") or "").strip() or None
        docs = _docs_url(meta)
    except PackageNotFoundError:  # pragma: no cover - version() succeeded, metadata() rarely won't
        pass
    return DistInfo(version=ver, summary=summary, docs=docs)


class DraftMaterial(BaseModel):
    """The resolved draft fields for one entry, plus what offline gathering could not supply."""

    lib: str  # PEP 503-normalized
    version_range: str
    pin: str
    docs: str
    summary: str
    gathered: bool
    missing: list[str]


def _docs_placeholder(lib: str) -> str:
    return f"TODO: docs URL for {lib}"


def _summary_placeholder(lib: str) -> str:
    return f"TODO: one-line summary of {lib}"


def gather(lib: str, *, lookup: MetadataLookup = default_lookup) -> DraftMaterial:
    """Assemble draft material for ``lib`` from offline metadata, degrading to TODO placeholders.

    Pure over the injectable ``lookup`` — pass a fake source to draft deterministically offline.
    """

    name = normalize(lib)
    info = lookup(name)

    if info is None:
        return DraftMaterial(
            lib=name,
            version_range="TODO",
            pin="TODO",
            docs=_docs_placeholder(name),
            summary=_summary_placeholder(name),
            gathered=False,
            missing=["version", "pin", "docs", "summary"],
        )

    missing: list[str] = []
    if not info.docs:
        missing.append("docs")
    if not info.summary:
        missing.append("summary")
    return DraftMaterial(
        lib=name,
        version_range=f">={info.version}",
        pin=info.version,
        docs=info.docs or _docs_placeholder(name),
        summary=info.summary or _summary_placeholder(name),
        gathered=True,
        missing=missing,
    )


def render_meta(material: DraftMaterial) -> str:
    """Render ``meta.toml`` from a validated :class:`LibMeta` (curation prose left as TODO stubs)."""

    meta = LibMeta(
        lib=LibSection(
            name=material.lib,
            version=material.version_range,
            pin=material.pin,
            docs=material.docs,
        ),
        curation=CurationSection(
            why=f"TODO (curation): why you use {material.lib} — what it buys the *man family and how it's used here.",
            rejected="TODO (curation): the alternatives you weighed and why you rejected them.",
        ),
    )
    header = (
        "# Curation metadata for the per-dependency knowledge entry (DRAFT — scaffolded by `vendor add`).\n"
        "# `version` is the range your libs target; `pin` is the concrete version SKILL.md is written\n"
        "# against. Fill the `[curation]` prose, then keep `pin` in lockstep with any SKILL.md rewrite.\n\n"
    )
    return header + meta.to_toml()


def render_notes(material: DraftMaterial) -> str:
    """Render ``notes.md`` — the raw curation material, with a gathered/missing report."""

    if material.gathered and not material.missing:
        report = "Offline metadata gathered cleanly (version, summary, docs)."
    elif material.gathered:
        report = f"Offline metadata partially gathered — could not derive: {', '.join(material.missing)}."
    else:
        report = (
            f"`{material.lib}` is not installed in vendomat's interpreter, so nothing could be gathered "
            "offline. `uv add` it (or fill these by hand) and re-run `vendor add --force` for richer pre-fill."
        )

    return (
        f"# {material.lib} — gotchas & patterns (raw curation material)\n\n"
        f"{DRAFT_MARK}\n\n"
        "Freeform notes that feed `SKILL.md`. Not installed into a consumer; the curated skill is.\n\n"
        f"Summary: {material.summary}\n\n"
        "## Scaffolding report\n\n"
        f"{report}\n\n"
        "## TODO — fill in\n\n"
        "- Gotchas you keep hitting with this lib.\n"
        "- Patterns / idioms worth standardizing across the *man family.\n"
        "- Anything an agent editing code that uses this lib must know.\n"
    )


def render_skill(material: DraftMaterial) -> str:
    """Render ``SKILL.md`` — validated devman-style frontmatter + a TODO-stubbed how-to body."""

    description = (
        f"TODO (curation): when should an agent reach for the {material.lib} skill? Replace this with "
        f"the real trigger text — it carries discovery. Drafted against {material.lib} {material.pin}."
    )
    front = SkillFrontmatter.for_lib(material.lib, description=description, keywords=[material.lib])
    return (
        front.to_frontmatter_block() + f"\n# {material.lib} — curated usage skill (DRAFT)\n\n"
        f"{DRAFT_MARK}\n\n"
        "A curated, usage-gated skill: installed into a repo only when that repo actually depends on "
        f"`{material.lib}`. Written against **{material.lib} {material.pin}**.\n\n"
        "## TODO — write the how-to\n\n"
        "- The handful of things to get right when using this lib here.\n"
        "- Concrete, copyable snippets over prose.\n"
        "- Replace the frontmatter `description` above with the real trigger text before publishing.\n\n"
        "Deeper curation material lives in this entry's `notes.md` (source, not installed).\n"
    )


def scaffold(vendor_root: Path, lib: str, material: DraftMaterial, *, force: bool = False) -> list[Path]:
    """Write ``vendor/libs/<lib>/{meta.toml,notes.md,SKILL.md}``; return the written paths.

    No-clobber: refuses with :class:`EntryExistsError` if the entry directory already exists unless
    ``force`` is set, so curated prose is never silently overwritten.
    """

    name = normalize(lib)
    entry = vendor_root / "libs" / name
    if entry.exists() and not force:
        raise EntryExistsError(name, entry)

    entry.mkdir(parents=True, exist_ok=True)
    meta_path = entry / "meta.toml"
    notes_path = entry / "notes.md"
    skill_path = entry / "SKILL.md"
    meta_path.write_text(render_meta(material))
    notes_path.write_text(render_notes(material))
    skill_path.write_text(render_skill(material))
    return [meta_path, notes_path, skill_path]

"""vendomat CLI — the vendor layer's command surface (artifacts + knowledge).

A thin Typer app following the *man-family contract: one CLI, Pydantic-normalized output, a
``doctor`` preflight, and the shared 0/1/2/3 exit-code contract (ok / domain-decision /
infra-config / invalid-usage). The knowledge commands ``sync`` and ``add`` are wired in later
milestones (Face B: M2 and M3); this milestone (M0) ships the package shape and a working
``doctor`` so the contract is real from day one.

The CLI is delivered to a *consumer* repo as a Nix-built package on PATH (DESIGN issue #3) — it
is never installed into the consumer's venv and has no ``repoman.lock`` entry.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from .add import EntryExistsError, gather, scaffold
from .catalog import CatalogError
from .checks import format_self_check, self_check_exit, vendor_checks
from .deps import read_deps, read_resolved_versions
from .install import LIB_PREFIX, install_knowledge
from .publish import PublishError, install_hook, pre_push, publish_preview, refresh_lock
from .publish import materialize as materialize_files
from .sources import SourceError, source_checks, source_status, sync_sources

app = typer.Typer(
    help="vendomat - the vendor layer for repoman's *man family (artifacts + knowledge).",
    no_args_is_help=True,
)
vendor_app = typer.Typer(help="Maintain pinned local Python sources for agent grounding.", no_args_is_help=True)
app.add_typer(vendor_app, name="vendor")


def _repo_root() -> str:
    """The repo vendomat acts on — the consumer's root inside its devenv shell."""

    return os.environ.get("DEVENV_ROOT", os.getcwd())


def _skills_dir() -> str:
    """Where per-dependency skills install — ``REPOMAN_SKILLS_DIR``-aware (flat siblings)."""

    return os.environ.get("REPOMAN_SKILLS_DIR", ".claude/skills")


def _vendor_root(flag: str | None) -> str | None:
    """The knowledge tree location: ``--vendor-root`` flag → ``VENDOMAT_VENDOR_ROOT`` env → None.

    The devenv module sets ``VENDOMAT_VENDOR_ROOT`` to ``${inputs.vendomat}/vendor`` (the flake
    source in the store); the flag is the unit-test / manual-override seam.
    """

    return flag or os.environ.get("VENDOMAT_VENDOR_ROOT")


def _catalog_root(flag: str | None) -> Path:
    """Vendomat checkout containing committed ``vendor/python`` catalog policy."""

    if flag:
        return Path(flag)
    if root := os.environ.get("VENDOMAT_CATALOG_ROOT"):
        return Path(root)
    if vendor_root := os.environ.get("VENDOMAT_VENDOR_ROOT"):
        return Path(vendor_root).parent
    return Path(__file__).resolve().parents[2]


def _global_source_root(flag: str | None) -> Path:
    """Machine-global third-party source cache, defaulting to ``~/vendor``."""

    return Path(flag or os.environ.get("VENDOMAT_SOURCE_ROOT", "~/vendor")).expanduser()


def _consumer_root(flag: str | None) -> Path:
    return Path(flag or _repo_root()).resolve()


def _source_roots(
    repo_root: str | None,
    vendomat_root: str | None,
    source_root: str | None,
) -> tuple[Path, Path, Path]:
    return (
        _catalog_root(vendomat_root).resolve(),
        _global_source_root(source_root).resolve(),
        _consumer_root(repo_root),
    )


@vendor_app.command("sync")
def vendor_sync(
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
    vendomat_root: str | None = typer.Option(
        None,
        "--vendomat-root",
        "--catalog-root",
        help="Vendomat checkout containing vendor/python catalog policy.",
    ),
    source_root: str | None = typer.Option(
        None,
        "--source-root",
        help="Global third-party source cache (defaults to $VENDOMAT_SOURCE_ROOT or ~/vendor).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report actions without cloning, fetching, or writing."),
) -> None:
    """Synchronize relevant pinned sources and the generated consumer source map."""

    catalog_root, sources, consumer = _source_roots(repo_root, vendomat_root, source_root)
    try:
        result = sync_sources(catalog_root, sources, consumer, dry_run=dry_run)
    except (CatalogError, SourceError, OSError) as exc:
        typer.echo(f"vendomat vendor sync: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    for action in result.actions:
        typer.echo(action)


@vendor_app.command("status")
def vendor_status(
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
    vendomat_root: str | None = typer.Option(
        None,
        "--vendomat-root",
        "--catalog-root",
        help="Vendomat checkout containing vendor/python catalog policy.",
    ),
    source_root: str | None = typer.Option(
        None,
        "--source-root",
        help="Global third-party source cache (defaults to $VENDOMAT_SOURCE_ROOT or ~/vendor).",
    ),
) -> None:
    """Show catalog, checkout, and installed-version identities without changing anything."""

    catalog_root, sources, consumer = _source_roots(repo_root, vendomat_root, source_root)
    try:
        lines = source_status(catalog_root, sources, consumer)
    except (CatalogError, SourceError, OSError) as exc:
        typer.echo(f"vendomat vendor status: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo("=== vendomat sources (status) ===")
    typer.echo("\n".join(lines) if lines else "no cataloged dependencies in this consumer")


@vendor_app.command("doctor")
def vendor_doctor(
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
    vendomat_root: str | None = typer.Option(
        None,
        "--vendomat-root",
        "--catalog-root",
        help="Vendomat checkout containing vendor/python catalog policy.",
    ),
    source_root: str | None = typer.Option(
        None,
        "--source-root",
        help="Global third-party source cache (defaults to $VENDOMAT_SOURCE_ROOT or ~/vendor).",
    ),
) -> None:
    """Diagnose Python source grounding under Vendomat's shared 0/1/2/3 contract."""

    catalog_root, sources, consumer = _source_roots(repo_root, vendomat_root, source_root)
    checks = source_checks(catalog_root, sources, consumer)
    typer.echo("=== vendomat sources (doctor) ===")
    typer.echo(format_self_check(checks))
    raise typer.Exit(code=self_check_exit(checks))


@app.command()
def sync(
    vendor_root: str | None = typer.Option(
        None, "--vendor-root", help="Knowledge tree (defaults to $VENDOMAT_VENDOR_ROOT)."
    ),
) -> None:
    """Install per-dependency knowledge skills, gated on the repo's actual deps.

    Reads the consuming repo's dependency set and installs a ``dep-<lib>`` skill for each lib it
    actually uses that the vendor tree carries. Idempotent.
    """

    vr = _vendor_root(vendor_root)
    if not vr:
        typer.echo("vendomat sync: VENDOMAT_VENDOR_ROOT is unset (set it or pass --vendor-root).", err=True)
        raise typer.Exit(code=2)  # infra/config

    repo_root = Path(_repo_root())
    deps = read_deps(repo_root)
    written = install_knowledge(Path(vr), deps, _skills_dir(), repo_root)

    installed = [p.parent.name for p in written if p.name == "SKILL.md"]
    if installed:
        typer.echo(f"vendomat sync: installed {len(installed)} skill(s): {', '.join(installed)}")
    else:
        typer.echo("vendomat sync: no matching dependency skills to install.")


def _add_vendor_root(flag: str | None) -> Path:
    """Where ``add`` *authors* the entry: ``--vendor-root`` flag → the local ``<repo>/vendor`` tree.

    Unlike ``sync``, ``add`` deliberately ignores ``VENDOMAT_VENDOR_ROOT``: the devenv module sets
    it to ``${inputs.vendomat}/vendor``, a **read-only nix store path** — wrong for writing. ``add``
    is a maintainer command run inside vendomat's own repo, so it writes the repo-local ``vendor/``.
    """

    if flag:
        return Path(flag)
    return Path(_repo_root()) / "vendor"


@app.command()
def add(
    lib: str,
    vendor_root: str | None = typer.Option(
        None, "--vendor-root", help="Vendor tree to author into (defaults to the repo's ./vendor)."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing entry (clobbers curated prose)."),
) -> None:
    """Draft a ``vendor/libs/<lib>/`` knowledge entry for human/agent curation.

    Scaffolds ``meta.toml`` + ``notes.md`` + ``SKILL.md``, mechanically pre-filling what it can
    derive offline from the installed dist (version → pin, docs, summary) and leaving the prose as
    clearly-marked DRAFT/TODO stubs. Never auto-published. No-clobber: refuses an existing entry
    (exit 1) unless ``--force``.
    """

    vr = _add_vendor_root(vendor_root)
    material = gather(lib)
    try:
        written = scaffold(vr, lib, material, force=force)
    except EntryExistsError as exc:
        typer.echo(f"vendomat add: {exc}", err=True)
        raise typer.Exit(code=1) from exc  # domain decision: refuse to clobber

    typer.echo(f"vendomat add {material.lib}: drafted {len(written)} file(s) under {written[0].parent}:")
    for p in written:
        typer.echo(f"  {p.name}")
    if not material.gathered:
        typer.echo(f"  (offline metadata for {material.lib} unavailable — fields stubbed as TODO)")
    elif material.missing:
        typer.echo(f"  (could not derive: {', '.join(material.missing)} — stubbed as TODO)")
    typer.echo("Now curate the DRAFT/TODO sections, then publish with `vendomat sync`.")


@app.command()
def doctor(
    vendor_root: str | None = typer.Option(
        None, "--vendor-root", help="Knowledge tree (defaults to $VENDOMAT_VENDOR_ROOT)."
    ),
) -> None:
    """Self-check vendomat's knowledge wiring under the shared 0/1/2/3 contract.

    Reads ``.vendor-source`` and the repo's deps, then reports whether the skills the repo *should*
    have are installed and current. Warn-only for now (knowledge is advisory) — a clean repo with
    nothing installed reports ``ok`` and exits 0.
    """

    repo_root = Path(_repo_root())
    skills_dir = _skills_dir()
    vr = _vendor_root(vendor_root)
    # Without a vendor root we can't enumerate expected libs; point at a path that won't exist so
    # `vendor_checks` still validates an already-written manifest but expects no new skills.
    vroot = Path(vr) if vr else repo_root / f".{LIB_PREFIX}no-vendor-root"

    deps = read_deps(repo_root)
    resolved = read_resolved_versions(repo_root)
    checks = vendor_checks(repo_root, skills_dir, vroot, deps, resolved)

    typer.echo("=== vendomat (self-check) ===")
    typer.echo(format_self_check(checks))
    raise typer.Exit(code=self_check_exit(checks))


@app.command()
def materialize(
    target: str = typer.Argument(..., help="Source spelling to write: local or github."),
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
) -> None:
    """Write the explicit local or GitHub source spellings declared in ``vendomat.toml``."""

    try:
        changed = materialize_files(Path(repo_root or _repo_root()), target)
    except PublishError as exc:
        typer.echo(f"vendomat materialize: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"vendomat materialize {target}: updated {len(changed)} file(s).")


@app.command("install-hook")
def install_hook_command(
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
) -> None:
    """Install Vendomat's non-clobbering pre-push hook into this Git checkout."""

    try:
        hook = install_hook(Path(repo_root or _repo_root()))
    except PublishError as exc:
        typer.echo(f"vendomat install-hook: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"vendomat install-hook: installed {hook}")


@app.command("refresh-lock", hidden=True)
def refresh_lock_command(
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
) -> None:
    """Hook-only lock refresh with version-churn protection."""

    try:
        changed = refresh_lock(Path(repo_root or _repo_root()))
    except PublishError as exc:
        typer.echo(f"vendomat refresh-lock: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"vendomat refresh-lock: updated {len(changed)} file(s).")


@app.command()
def publish(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the public manifest/lock diff without pushing."),
    repo_root: str | None = typer.Option(None, "--repo-root", help="Consumer repo root (defaults to $DEVENV_ROOT)."),
) -> None:
    """Preview Vendomat's publish-time GitHub-source and uv.lock transformation."""

    if not dry_run:
        typer.echo("vendomat publish: only --dry-run is supported; git push runs the publisher.", err=True)
        raise typer.Exit(code=3)
    try:
        diff = publish_preview(Path(repo_root or _repo_root()))
    except PublishError as exc:
        typer.echo(f"vendomat publish: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(diff or "vendomat publish: no public manifest or lock changes.", nl=not diff.endswith("\n"))


@app.command("pre-push", hidden=True)
def pre_push_command(remote_name: str = typer.Argument(...), remote_url: str = typer.Argument(...)) -> None:
    """Git hook entry point; reads ref updates from standard input."""

    del remote_url
    try:
        pre_push(Path(_repo_root()), remote_name, sys.stdin.read())
    except PublishError as exc:
        typer.echo(f"vendomat pre-push: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def main() -> None:
    """Entry point for the vendomat CLI."""

    app()


if __name__ == "__main__":
    main()

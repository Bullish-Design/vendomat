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

import typer

from .checks import SelfCheck, format_self_check, self_check_exit

app = typer.Typer(
    help="vendomat - the vendor layer for repoman's *man family (artifacts + knowledge).",
    no_args_is_help=True,
)

MANIFEST = ".vendor-source"


def _repo_root() -> str:
    """The repo vendomat acts on — the consumer's root inside its devenv shell."""

    return os.environ.get("DEVENV_ROOT", os.getcwd())


def _skills_dir() -> str:
    """Where per-dependency skills install — ``REPOMAN_SKILLS_DIR``-aware (flat siblings)."""

    return os.environ.get("REPOMAN_SKILLS_DIR", ".claude/skills")


@app.command()
def sync() -> None:
    """Install per-dependency knowledge skills, gated on the repo's actual deps.

    Wired in M2 (Face B slice 1). For now this is a no-op placeholder that keeps the
    command surface stable.
    """

    typer.echo("vendomat sync: knowledge install lands in M2 (not yet wired).")


@app.command()
def add(lib: str) -> None:
    """Draft a ``vendor/libs/<lib>/`` knowledge entry for human curation.

    Wired in M3 (Face B tooling). For now this is a no-op placeholder.
    """

    typer.echo(f"vendomat add {lib}: draft scaffolding lands in M3 (not yet wired).")


@app.command()
def doctor() -> None:
    """Self-check vendomat's knowledge wiring under the shared 0/1/2/3 contract.

    Reads the ``.vendor-source`` drift manifest (once M2 writes it) and reports
    missing/stale skills. On a repo with no knowledge installed there is nothing to flag,
    so the manifest's absence is reported (not an error) and the exit code is 0.
    """

    repo_root = _repo_root()
    skills_dir = _skills_dir()

    checks: list[SelfCheck] = []

    # M2 folds the real .vendor-source drift checks in here. Until then doctor has nothing
    # to validate, and the manifest's absence is informational, not a failure.
    manifest = os.path.join(repo_root, skills_dir, MANIFEST)
    if os.path.exists(manifest):
        checks.append(SelfCheck(name="vendor:manifest", level="ok", detail=manifest))
    else:
        checks.append(
            SelfCheck(
                name="vendor:manifest",
                level="ok",
                detail="no knowledge installed (run `vendomat sync`)",
            )
        )

    typer.echo("=== vendomat (self-check) ===")
    typer.echo(format_self_check(checks))
    raise typer.Exit(code=self_check_exit(checks))


def main() -> None:
    """Entry point for the vendomat CLI."""

    app()


if __name__ == "__main__":
    main()

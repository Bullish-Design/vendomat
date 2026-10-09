"""The ``vendomat`` command line (``CLI-*``).

A thin Typer app. Exit status: 0 ok, 1 a decision is needed (a refused entry, an unknown
input), 2 infrastructure or configuration (a Git, Nix, or registry fault), 3 invalid usage.

The command is installed on the host (``DEL-006``, ``DEL-007``). A project never imports it.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .generate import GenerateError, sync_flake
from .locate import LocateError, input_path
from .store import exit_code, source_root, sync_store

app = typer.Typer(
    help="vendomat - write a project flake from vendomat.toml, and keep source clones.",
    no_args_is_help=True,
)


@app.command()
def sync(
    root: str | None = typer.Option(None, "--root", help="Project directory (defaults to the current directory)."),
    collection: bool = typer.Option(
        False,
        "--collection",
        help="Run on the collection host: copy `mirror` entries and check out each repository's newest tag.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the planned actions and change nothing."),
) -> None:
    """Write the project ``flake.nix`` from ``vendomat.toml``, then keep and mirror sources.

    ``sync`` writes ``flake.nix`` first. A store failure never undoes it. ``keep`` entries get a
    clone under ``$VENDOMAT_SOURCE_ROOT`` (default ``~/vendor``) that shows the pinned tag. ``mirror``
    entries act only with ``--collection``. ``sync`` leaves ``flake.lock`` and ``flake-outputs.nix``
    alone: Nix owns the lock and the project owns its outputs. It refuses to overwrite a
    ``flake.nix`` that has no generated header, and it never touches a clone with uncommitted changes.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        result = sync_flake(project, dry_run=dry_run)
    except GenerateError as exc:
        typer.echo(f"vendomat sync: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    if result.changed:
        verb = "would write" if dry_run else "wrote"
    else:
        verb = "unchanged"
    typer.echo(f"vendomat sync: {verb} {result.path.name} ({result.inputs} direct input(s))")

    outcomes = sync_store(result.registry, root=source_root(), collection=collection, dry_run=dry_run)
    for outcome in outcomes:
        typer.echo(f"vendomat sync: {outcome.line()}", err=not outcome.ok)
    code = exit_code(outcomes)
    if code:
        failed = sum(1 for outcome in outcomes if not outcome.ok)
        typer.echo(f"vendomat sync: {failed} source problem(s); flake.nix is not affected", err=True)
        raise typer.Exit(code=code)


@app.command("path")
def path_command(
    name: str = typer.Argument(..., help="A direct input of the project flake."),
    root: str | None = typer.Option(None, "--root", help="Project directory (defaults to the current directory)."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Print the store path of the locked source of a direct input.

    Nix names the path (``nix flake archive``). The command writes neither ``flake.lock`` nor
    ``vendomat.toml``.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        found = input_path(project, name)
    except LocateError as exc:
        typer.echo(f"vendomat path: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    typer.echo(json.dumps({"name": name, "path": found}) if json_output else found)


def main() -> None:
    """Entry point for the vendomat CLI."""

    app()


if __name__ == "__main__":
    main()

"""The ``vendomat`` command line (``CLI-*``).

A thin Typer app. Exit status: 0 ok, 1 a decision is needed (a refused entry, an unknown
input), 2 infrastructure or configuration (a Git, Nix, or registry fault), 3 invalid usage.

The host launcher runs ``update``, ``explain``, ``apply``, ``rollback``, and ``push`` with the host release.
"""

from __future__ import annotations

import json
import os
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer

from .apply import apply as run_apply
from .apply import deploy_argv, machine_name
from .explain import ExplainError, read_report
from .explain import render as render_report
from .push import PushError
from .push import push as run_push
from .record import RecordError
from .rollback import rollback as run_rollback
from .update import UpdateError, check_lines, describe, devenv_command, run_update
from .workspace import find_root

app = typer.Typer(
    help="vendomat - explain and update vendomat.yaml workspaces, apply and roll back machines, push outputs.",
    no_args_is_help=True,
)


def tool_version() -> str:
    try:
        return version("vendomat")
    except PackageNotFoundError:
        return "0+unknown"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vendomat {tool_version()}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Print the version and exit."),
    ] = False,
) -> None:
    """Explain and update vendomat.yaml workspaces, apply and roll back machines, push outputs."""


@app.command("push")
def push_command(
    cache: str = typer.Option(..., "--cache", help="The Attic cache name."),
    machine: str | None = typer.Option(None, "--machine", help="Build machines.<name> instead of the outputs."),
    attr: Annotated[list[str] | None, typer.Option("--attr", help="A devenv attribute to build (repeatable).")] = None,
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Build, list the paths, push nothing."),
) -> None:
    """Build with ``devenv build`` and push the paths with ``attic push``.

    ``VENDOMAT_DEVENV`` and ``VENDOMAT_ATTIC`` name the commands.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        result = run_push(project, cache, machine=machine, attrs=list(attr or []), dry_run=dry_run)
    except PushError as exc:
        typer.echo(f"vendomat push: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    for path in result.paths:
        typer.echo(path)
    verb = "pushed" if result.pushed else "would push"
    typer.echo(f"vendomat push: {verb} {len(result.paths)} path(s) to {result.cache}", err=True)


@app.command("explain")
def explain_command(
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Show where each setting of the workspace comes from.

    For each key of vendomat.yaml it prints the native devenv option, the value, and the file that sets
    it. A second section lists the options that only a Nix file sets. It shows every source, also when
    VENDOMAT_HIDE_ADVANCED hides the line of the shell entry. It writes nothing.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        report = read_report(project)
    except ExplainError as exc:
        typer.echo(f"vendomat explain: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    typer.echo(json.dumps(report, indent=2, ensure_ascii=False) if json_output else render_report(report))


@app.command("update")
def update_command(
    inputs: Annotated[list[str] | None, typer.Argument(help="Inputs for `devenv update` (default: all).")] = None,
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    check: bool = typer.Option(False, "--check", help="Report the missing template lines and change nothing."),
) -> None:
    """Add the lines that the template needs to devenv.yaml, then run `devenv update`.

    A newer template can need a new input. This command adds each missing line and names it. It keeps
    every line that you wrote. Names after `update` pass to `devenv update`, so `vendomat update vendomat`
    moves only the vendomat input. With --check it only reports the missing lines and exits 1 when there are any.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        if check:
            missing = check_lines(project)
            if missing:
                typer.echo("vendomat update: devenv.yaml lacks these lines of the template:", err=True)
                for line in describe(missing):
                    typer.echo(line, err=True)
                typer.echo("vendomat update: run `vendomat update` to add them", err=True)
                raise typer.Exit(code=1)
            typer.echo("vendomat update: devenv.yaml has every line of the template")
            return
        added = run_update(project)
    except UpdateError as exc:
        typer.echo(f"vendomat update: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    if added:
        typer.echo("vendomat update: added to devenv.yaml:")
        for line in describe(added):
            typer.echo(line)
    else:
        typer.echo("vendomat update: devenv.yaml has every line of the template")
    try:
        result = subprocess.run([devenv_command(), "update", *(inputs or [])], cwd=project, check=False)
    except FileNotFoundError as exc:
        typer.echo("vendomat update: cannot run devenv (set VENDOMAT_DEVENV to the devenv command)", err=True)
        raise typer.Exit(code=2) from exc
    if result.returncode != 0:
        typer.echo(f"vendomat update: `devenv update` failed (exit {result.returncode})", err=True)
        raise typer.Exit(code=2)


def _echo(line: str) -> None:
    typer.echo(line)


def _workspace_root(root: str | None) -> Path:
    """The workspace directory: ``--root`` as given, else the nearest parent that holds the workspace files."""

    return find_root(Path(root) if root is not None else Path.cwd())


@app.command("apply")
def apply_command(
    name: str | None = typer.Argument(None, help="A machine name. Leave it out to apply this machine."),
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    dirty: bool = typer.Option(
        False,
        "--dirty",
        help="Apply uncommitted changes without a commit and record the generation as dirty. "
        "Ignored config files must still be force-added.",
    ),
) -> None:
    """Build this machine, commit watched config, then activate it. No SSH.

    A record is always a whole commit. Before the build, apply refuses any uncommitted change under
    the workspace root other than vendomat.yaml, devenv.lock, devenv.nix, and devenv.local.nix. This
    covers tracked and new files. Commit or remove them first. Files that Git ignores do not count.
    After a successful build, apply commits those four files before activation. --dirty skips that
    commit, allows other changes, and records the generation as dirty, so rollback skips it. An
    ignored watched file must be force-added or removed first.
    """

    try:
        own = machine_name()
        if name is not None and name != own:
            typer.echo(f"vendomat apply: {name} is not this machine ({own}); running devenv machines deploy {name}")
            argv = deploy_argv(name)
            os.execvp(argv[0], argv)
        run_apply(_workspace_root(root), dirty_ok=dirty, emit=_echo)
    except RecordError as exc:
        typer.echo(f"vendomat apply: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc


@app.command("rollback")
def rollback_command(
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    to: str | None = typer.Option(None, "--to", help="Roll back to this commit."),
    generation: int | None = typer.Option(None, "--generation", help="Roll back to the commit of this generation."),
    exact: bool = typer.Option(
        False, "--exact", help="Deprecated. The default now restores the whole workspace tree. Kept as an alias."
    ),
    fast: bool = typer.Option(
        False, "--fast", help="Move the profile to the recorded generation. Build nothing. Still commit the restore."
    ),
    boot_only: bool = typer.Option(
        False, "--boot-only", help="Set the next boot entry only. For recovery. No file, no commit."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the target and the diff. Change nothing."),
) -> None:
    """Return this machine to an earlier commit, with a lasting result.

    Without options: pick the newest earlier clean entry of the record with a different system path.
    Show the diff. Restore the whole workspace tree (every tracked file under the workspace root)
    from that commit. Build, commit the restore as `rollback to REV`, and activate. The command
    refuses uncommitted changes (tracked or new), an unknown commit, and a commit that the
    repository lacks.
    """

    try:
        run_rollback(
            _workspace_root(root),
            to=to,
            generation=generation,
            exact=exact,
            fast=fast,
            boot_only=boot_only,
            dry_run=dry_run,
            emit=_echo,
        )
    except RecordError as exc:
        typer.echo(f"vendomat rollback: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc


def main() -> None:
    """Entry point for the vendomat CLI."""

    app()


if __name__ == "__main__":
    main()

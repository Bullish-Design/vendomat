"""The ``vendomat`` command line (``CLI-*``).

A thin Typer app. Exit status: 0 ok, 1 a decision is needed (a refused entry, an unknown
input), 2 infrastructure or configuration (a Git, Nix, or registry fault), 3 invalid usage.

The command is installed on the host (``DEL-006``, ``DEL-007``). A project never imports it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .bump import bump as run_bump
from .bump import summary as bump_summary
from .check import check_workspace
from .devenvgen import DevenvSyncError, sync_devenv
from .generate import GenerateError, load_registry, sync_flake, tool_version
from .locate import LocateError, input_path
from .lockpath import LockPathError, input_path_from_lock
from .machine import MachineError, plan_install, run_install
from .push import PushError
from .push import push as run_push
from .registry import RegistryError, read_registry
from .store import exit_code, source_root, sync_store

app = typer.Typer(
    help="vendomat - write project inputs from vendomat.toml, check pins, push outputs, and keep source clones.",
    no_args_is_help=True,
)


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
    """Write project inputs from vendomat.toml, check pins, push outputs, and keep source clones."""


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
    """Write the project outputs from ``vendomat.toml``, then keep and mirror sources.

    ``[targets]`` selects the outputs. The flake target (the default) writes ``flake.nix``. The
    devenv target writes the ``.vendomat/`` fragment and asks ``devenv`` to lock its inputs.

    ``sync`` writes the outputs first. A store failure never undoes them. ``keep`` entries get a
    clone under ``$VENDOMAT_SOURCE_ROOT`` (default ``~/vendor``) that shows the pinned tag. ``mirror``
    entries act only with ``--collection``. ``sync`` leaves ``flake.lock`` and ``flake-outputs.nix``
    alone: Nix owns the lock and the project owns its outputs. It refuses to overwrite a
    ``flake.nix`` that has no generated header, and it never touches a clone with uncommitted changes.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        registry = load_registry(project)
        if registry.targets.flake:
            result = sync_flake(project, dry_run=dry_run)
            registry = result.registry
            verb = ("would write" if dry_run else "wrote") if result.changed else "unchanged"
            typer.echo(f"vendomat sync: {verb} {result.path.name} ({result.inputs} direct input(s))")
    except GenerateError as exc:
        typer.echo(f"vendomat sync: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc

    if registry.targets.devenv:
        try:
            outcome = sync_devenv(project, registry, tool_version(), dry_run=dry_run)
        except DevenvSyncError as exc:
            typer.echo(f"vendomat sync: {exc}", err=True)
            raise typer.Exit(code=exc.code) from exc
        for note in outcome.notes:
            typer.echo(f"vendomat sync: note: {note}")
        for warning in outcome.warnings:
            typer.echo(f"vendomat sync: warning: {warning}", err=True)
        if outcome.skipped:
            verb = "unchanged"
        else:
            verb = ("would write" if dry_run else "wrote") if outcome.changed else "unchanged"
        lock = "; devenv.lock updated" if outcome.lock_updated else ""
        typer.echo(f"vendomat sync: {verb} .vendomat/ ({outcome.inputs} input(s), {outcome.imports} import(s){lock})")

    outcomes = sync_store(registry, root=source_root(), collection=collection, dry_run=dry_run)
    for outcome_line in outcomes:
        typer.echo(f"vendomat sync: {outcome_line.line()}", err=not outcome_line.ok)
    code = exit_code(outcomes)
    if code:
        failed = sum(1 for item in outcomes if not item.ok)
        typer.echo(f"vendomat sync: {failed} source problem(s); the written outputs are not affected", err=True)
        raise typer.Exit(code=code)


def _uses_devenv_lock(project: Path) -> bool:
    """A workspace that selects the devenv target and holds a ``devenv.lock`` answers from that lock."""

    registry_path = project / "vendomat.toml"
    if not (project / "devenv.lock").is_file() or not registry_path.is_file():
        return False
    try:
        return read_registry(registry_path).targets.devenv
    except RegistryError:
        return False


@app.command("path")
def path_command(
    name: str = typer.Argument(..., help="A direct input of the project."),
    root: str | None = typer.Option(None, "--root", help="Project directory (defaults to the current directory)."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Print the store path of the locked source of a direct input.

    In a devenv workspace the path comes from ``devenv.lock`` and needs no network. In a flake
    project Nix names it (``nix flake archive``). The command writes neither lock nor registry.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        if _uses_devenv_lock(project):
            found = input_path_from_lock(project, name)
        else:
            found = input_path(project, name)
    except (LocateError, LockPathError) as exc:
        typer.echo(f"vendomat path: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    typer.echo(json.dumps({"name": name, "path": found}) if json_output else found)


@app.command("check")
def check_command(
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
    no_version: bool = typer.Option(False, "--no-version", help="Skip the devenv CLI and module version check."),
) -> None:
    """Check a devenv workspace: tag pins, the devenv version, and the generated fragment.

    Exit 0 when clean, 1 when it names a problem. It writes nothing.
    """

    project = Path(root) if root is not None else Path.cwd()
    problems = check_workspace(project, check_version=not no_version)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": not problems,
                    "problems": [{"kind": p.kind, "name": p.name, "message": p.message} for p in problems],
                }
            )
        )
    elif problems:
        for problem in problems:
            typer.echo(f"vendomat check: {problem.line()}", err=True)
    else:
        typer.echo("vendomat check: clean")
    if problems:
        raise typer.Exit(code=1)


@app.command("push")
def push_command(
    cache: str = typer.Option(..., "--cache", help="The Attic cache name."),
    machine: str | None = typer.Option(None, "--machine", help="Build machines.<name> instead of the outputs."),
    attr: Annotated[list[str] | None, typer.Option("--attr", help="A devenv attribute to build (repeatable).")] = None,
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Check and build, list the paths, push nothing."),
    no_version: bool = typer.Option(False, "--no-version", help="Skip the devenv version check."),
) -> None:
    """Check the workspace, build with ``devenv build``, and push the paths with ``attic push``.

    A failed check builds and pushes nothing. ``VENDOMAT_DEVENV`` and ``VENDOMAT_ATTIC`` name the commands.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        result = run_push(
            project, cache, machine=machine, attrs=list(attr or []), dry_run=dry_run, check_version=not no_version
        )
    except PushError as exc:
        typer.echo(f"vendomat push: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    for path in result.paths:
        typer.echo(path)
    verb = "pushed" if result.pushed else "would push"
    typer.echo(f"vendomat push: {verb} {len(result.paths)} path(s) to {result.cache}", err=True)


@app.command("bump")
def bump_command(
    tag: str = typer.Argument(..., help="The Vendomat release tag, such as v0.7.0."),
    root: str | None = typer.Option(None, "--root", help="Fleet root (defaults to the current directory)."),
    devenv_ref: str | None = typer.Option(None, "--devenv", help="Also set the devenv input's tag or ref."),
    apply: bool = typer.Option(False, "--apply", help="Write the registries and run each gate. Default: dry run."),
    gate: str = typer.Option(
        "testee verify --full", "--gate", help="The verify command that runs in each workspace after --apply."
    ),
    only: Annotated[
        list[str] | None, typer.Option("--only", help="Limit to a workspace directory name (repeatable).")
    ] = None,
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Move every workspace under a root to a Vendomat tag. A dry run is the default.

    ``--apply`` edits the ``ref`` of the ``vendomat`` entry, runs ``sync``, then runs each
    workspace's gate. The report names every failure. It never reports a fleet pass over one.
    """

    fleet = Path(root) if root is not None else Path.cwd()
    try:
        entries = run_bump(
            fleet,
            tag,
            devenv_ref=devenv_ref,
            apply=apply,
            gate=gate.split() if apply and gate else None,
            only=list(only or []) or None,
        )
    except ValueError as exc:
        typer.echo(f"vendomat bump: {exc}", err=True)
        raise typer.Exit(code=3) from exc
    verdict, good = bump_summary(entries, applied=apply)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "applied": apply,
                    "ok": good,
                    "workspaces": [
                        {
                            "path": str(e.path),
                            "status": e.status,
                            "old": e.old,
                            "new": e.new,
                            "gate": e.gate,
                            "detail": e.detail,
                        }
                        for e in entries
                    ],
                }
            )
        )
    else:
        for e in entries:
            change = ", ".join(f"{k} {e.old.get(k, '?')} -> {v}" for k, v in e.new.items())
            extra = f" ({e.detail})" if e.detail else ""
            typer.echo(f"{e.path}: {e.status}{' [gate ' + e.gate + ']' if apply else ''} {change}{extra}")
        typer.echo(f"vendomat bump: {'applied' if apply else 'dry run'}: {verdict}", err=not good)
    if not good:
        raise typer.Exit(code=1)


machine_app = typer.Typer(help="Machine commands. Only a fresh install lives here; devenv Machines does the rest.")
app.add_typer(machine_app, name="machine")


@machine_app.command("install")
def machine_install(
    host: str = typer.Argument(..., help="A fresh-install host of vendomat.inventory."),
    root: str | None = typer.Option(None, "--root", help="Workspace directory (defaults to the current directory)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run every check, print the command, and run nothing."),
    no_version: bool = typer.Option(False, "--no-version", help="Skip the devenv version check."),
) -> None:
    """Install a fresh-install host: check, then `devenv machines install <host> --phases disko,install`.

    The patched devenv runs the target-side preflight before it touches a disk. This command offers
    no phase or disko-mode option. It refuses an adopted host. It unmounts /mnt on the target after.
    Activation, status, and rollback stay with `devenv machines`.
    """

    project = Path(root) if root is not None else Path.cwd()
    try:
        plan = plan_install(project, host, check_version=not no_version)
    except MachineError as exc:
        typer.echo(f"vendomat machine install: {exc}", err=True)
        raise typer.Exit(code=exc.code) from exc
    for note in plan.notes:
        typer.echo(f"vendomat machine install: note: {note}", err=True)
    typer.echo("vendomat machine install: " + " ".join(plan.argv), err=dry_run)
    if dry_run:
        typer.echo("vendomat machine install: dry run; nothing ran", err=True)
        return
    installed, unmounted = run_install(plan, project)
    if unmounted not in (None, 0):
        typer.echo(
            f"vendomat machine install: could not unmount /mnt on the target (exit {unmounted}); unmount it by hand",
            err=True,
        )
    if installed != 0:
        typer.echo(f"vendomat machine install: the install failed (exit {installed})", err=True)
        raise typer.Exit(code=2)


def main() -> None:
    """Entry point for the vendomat CLI."""

    app()


if __name__ == "__main__":
    main()

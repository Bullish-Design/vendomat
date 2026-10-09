"""The command surface and the exit-status contract (CLI-001, CLI-002)."""

from __future__ import annotations

import typer.main
from typer.testing import CliRunner

from vendomat.cli import app

runner = CliRunner()

#: The commands `CLI-001` allows. A command appears here only when it is built.
BUILT = {"sync", "path"}


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vendomat" in result.stdout


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_the_surface_is_the_built_v5_commands_and_nothing_else():
    group = typer.main.get_command(app)
    assert set(getattr(group, "commands", {})) == BUILT


def test_an_unknown_command_is_invalid_usage():
    assert runner.invoke(app, ["plane", "show"]).exit_code == 2


def test_sync_without_a_registry_names_the_file_and_exits_two(tmp_path):
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "vendomat.toml" in result.output


def test_path_without_a_flake_asks_for_sync(tmp_path):
    result = runner.invoke(app, ["path", "lib-a", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "vendomat sync" in result.output

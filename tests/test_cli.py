"""Smoke tests for the vendomat CLI shape + the 0/1/2/3 exit-code contract (M0)."""

from __future__ import annotations

from typer.testing import CliRunner

from vendomat.cli import app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vendomat" in result.stdout


def test_no_args_shows_help():
    # no_args_is_help=True → Typer prints usage instead of erroring on a bare invocation.
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_doctor_clean_repo_exits_zero(tmp_path, monkeypatch):
    # An empty repo has no knowledge installed → nothing to flag → exit 0.
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "self-check" in result.stdout


def test_sync_and_add_stubs_run(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    assert runner.invoke(app, ["sync"]).exit_code == 0
    assert runner.invoke(app, ["add", "typer"]).exit_code == 0

"""`vendomat machine install` is a fresh-only second guard (`MACH-008`, `CLI-021`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import typer.main
from test_commands_v6 import stub, synced
from typer.testing import CliRunner

from vendomat.cli import app
from vendomat.machine import MachineError, plan_install

runner = CliRunner()


def fake_devenv(tmp: Path, *, modes: dict, facter: object = None, target: str | None = "root@localhost") -> str:
    """A `devenv` that answers `eval` from tables and records every other call."""

    log = tmp / "devenv-calls.log"
    answers = {
        "vendomat.modes": modes,
        "machines.server.hardware.facter": facter,
        "machines.server.target.host": target,
        "machines.framework.hardware.facter": facter,
        "machines.framework.target.host": target,
    }
    table = tmp / "answers.json"
    table.write_text(json.dumps(answers))
    return stub(
        tmp,
        "devenv",
        f"""
        if [ "$1" = "eval" ]; then
          {sys.executable} - "$2" <<'PY'
        import json, sys
        print(json.dumps({{sys.argv[1]: json.load(open("{table}")).get(sys.argv[1])}}))
        PY
          exit 0
        fi
        echo "$@" >> {log}
        exit ${{DEVENV_EXIT:-0}}
        """,
    )


def calls(tmp: Path) -> list[str]:
    log = tmp / "devenv-calls.log"
    return log.read_text().splitlines() if log.exists() else []


def prepare(tmp: Path, **kw) -> tuple[Path, str]:
    root = synced(tmp)
    return root, fake_devenv(tmp, **kw)


def test_a_fresh_host_gets_exactly_one_install_command(tmp_path):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter={"x": 1})
    report = root / ".machines" / "server" / "facter.json"
    report.parent.mkdir(parents=True)
    report.write_text("{}")
    plan = plan_install(root, "server", devenv, check_version=False)
    assert plan.argv == [devenv, "machines", "install", "server", "--phases", "disko,install"]
    assert plan.unmount == ["ssh", "-o", "BatchMode=yes", "root@localhost", "umount -R /mnt"]


def test_an_adopted_host_is_refused_before_any_install_call(tmp_path):
    root, devenv = prepare(tmp_path, modes={"framework": "adopt-existing"})
    with pytest.raises(MachineError, match="mode 'adopt-existing'") as info:
        plan_install(root, "framework", devenv, check_version=False)
    assert info.value.code == 1
    assert calls(tmp_path) == []


def test_an_unknown_host_names_the_known_ones(tmp_path):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"})
    with pytest.raises(MachineError, match="known hosts: server"):
        plan_install(root, "ghost", devenv, check_version=False)


def test_a_missing_facter_report_is_refused_unless_facter_is_null(tmp_path):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter={"x": 1})
    with pytest.raises(MachineError, match="facter.json is missing"):
        plan_install(root, "server", devenv, check_version=False)
    root2 = synced(tmp_path, name="ws2")
    devenv2 = fake_devenv(tmp_path, modes={"server": "fresh-install"}, facter=None)
    plan = plan_install(root2, "server", devenv2, check_version=False)
    assert any("hardware.facter is null" in n for n in plan.notes)


def test_a_failed_workspace_check_stops_before_the_install(tmp_path):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter=None)
    (root / "vendomat.toml").write_text((root / "vendomat.toml").read_text() + "# edit\n")
    with pytest.raises(MachineError, match="failed `vendomat check`"):
        plan_install(root, "server", devenv, check_version=False)
    assert calls(tmp_path) == []


def test_the_command_runs_the_install_then_unmounts(tmp_path, monkeypatch):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter=None)
    ssh_log = tmp_path / "ssh.log"
    ssh = stub(tmp_path, "ssh", f'echo "$@" >> {ssh_log}\n')
    monkeypatch.setenv("VENDOMAT_DEVENV", devenv)
    monkeypatch.setenv("PATH", f"{Path(ssh).parent}:/usr/bin:/bin:/run/current-system/sw/bin")
    result = runner.invoke(app, ["machine", "install", "server", "--root", str(root), "--no-version"])
    assert result.exit_code == 0, result.output
    assert calls(tmp_path) == ["machines install server --phases disko,install"]
    assert ssh_log.read_text().strip() == "-o BatchMode=yes root@localhost umount -R /mnt"


def test_a_failed_install_still_unmounts_and_exits_two(tmp_path, monkeypatch):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter=None)
    ssh_log = tmp_path / "ssh.log"
    ssh = stub(tmp_path, "ssh", f'echo "$@" >> {ssh_log}\n')
    monkeypatch.setenv("VENDOMAT_DEVENV", devenv)
    monkeypatch.setenv("DEVENV_EXIT", "7")
    monkeypatch.setenv("PATH", f"{Path(ssh).parent}:/usr/bin:/bin:/run/current-system/sw/bin")
    result = runner.invoke(app, ["machine", "install", "server", "--root", str(root), "--no-version"])
    assert result.exit_code == 2
    assert "install failed (exit 7)" in result.output
    assert ssh_log.exists()


def test_dry_run_prints_the_command_and_runs_nothing(tmp_path, monkeypatch):
    root, devenv = prepare(tmp_path, modes={"server": "fresh-install"}, facter=None)
    monkeypatch.setenv("VENDOMAT_DEVENV", devenv)
    result = runner.invoke(app, ["machine", "install", "server", "--root", str(root), "--no-version", "--dry-run"])
    assert result.exit_code == 0
    assert "machines install server --phases disko,install" in result.output
    assert calls(tmp_path) == []


def test_the_command_offers_no_phase_or_disko_mode_option():
    group: Any = typer.main.get_command(app)
    install = group.commands["machine"].commands["install"]
    options = {opt for param in install.params for opt in getattr(param, "opts", [])}
    assert {"--phases", "--disko-mode", "--stop-after-disko", "--no-reboot"}.isdisjoint(options)

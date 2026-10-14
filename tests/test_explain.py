"""`vendomat explain`: run `devenv eval vendomat.explain` and format the report (R27, VMT-057, VMT-093).

A fake devenv stands in for the real one. The catalog data itself is proved in `test_catalog_hatch_nix.py`
(Nix stubs) and `test_catalog_devenv.py` (real devenv).
"""

from __future__ import annotations

import json
import stat
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vendomat import explain
from vendomat.cli import app

runner = CliRunner()

REPORT = {
    "yaml": [
        {
            "key": "languages.python.version",
            "line": 5,
            "column": 5,
            "option": "languages.python.version",
            "value": "3.12",
            "files": ["vendomat.yaml"],
        },
        {
            "key": "env.GREETING",
            "line": 7,
            "column": 3,
            "option": "env.GREETING",
            "value": "bye",
            "files": ["devenv.nix"],
        },
        {
            "key": "languages.python.uv.sync",
            "line": 9,
            "column": 9,
            "option": "languages.python.uv.sync.enable",
            "value": False,
            "files": ["(devenv default)"],
        },
        {
            "key": "machines.vm.serve",
            "line": 13,
            "column": 5,
            "option": None,
            "value": "false",
            "files": ["vendomat.yaml"],
        },
    ],
    "nix": [{"option": "services.redis.enable", "value": True, "files": ["devenv.nix", "devenv.local.nix"]}],
}


def fake_devenv(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "devenv.yaml").write_text("inputs: {}\n")
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv(
        "VENDOMAT_DEVENV",
        str(
            fake_devenv(
                tmp_path / "devenv",
                f"""
                echo "$PWD $*" >> {tmp_path}/calls
                echo 'noise on stdout before the report'
                echo '{json.dumps({"vendomat.explain": REPORT})}'
                """,
            )
        ),
    )
    return root


def test_the_text_names_key_option_value_and_file(workspace: Path):
    result = runner.invoke(app, ["explain", "--root", str(workspace)])
    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines() == [
        "Keys of vendomat.yaml:",
        "  languages.python.version  (vendomat.yaml:5:5)",
        "    option  languages.python.version",
        '    value   "3.12"',
        "    from    vendomat.yaml",
        "  env.GREETING  (vendomat.yaml:7:3)",
        "    option  env.GREETING",
        '    value   "bye"',
        "    from    devenv.nix",
        "    note    another file overrides vendomat.yaml for this option",
        "  languages.python.uv.sync  (vendomat.yaml:9:9)",
        "    option  languages.python.uv.sync.enable",
        "    value   false",
        "    from    (devenv default)",
        "    note    the key has no effect here: devenv keeps its default",
        "  machines.vm.serve  (vendomat.yaml:13:5)",
        "    option  (read by the catalog, no native option)",
        '    value   "false"',
        "    from    vendomat.yaml",
        "",
        "Set only in Nix (not by a key of vendomat.yaml):",
        "  services.redis.enable",
        "    value   true",
        "    from    devenv.nix, devenv.local.nix",
    ]


def test_the_json_output_is_the_report(workspace: Path):
    result = runner.invoke(app, ["explain", "--root", str(workspace), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == REPORT


def test_the_command_runs_devenv_eval_in_the_workspace(workspace: Path, tmp_path: Path):
    runner.invoke(app, ["explain", "--root", str(workspace)])
    assert (tmp_path / "calls").read_text().strip() == f"{workspace} eval vendomat.explain"


def test_the_hide_switch_does_not_change_the_report(workspace: Path, monkeypatch: pytest.MonkeyPatch):
    # R45: the switch hides the line of the shell entry only. `explain` ignores it.
    monkeypatch.setenv("VENDOMAT_HIDE_ADVANCED", "1")
    result = runner.invoke(app, ["explain", "--root", str(workspace), "--json"])
    assert json.loads(result.stdout) == REPORT


def test_an_empty_report_says_none(workspace: Path):
    text = explain.render({"yaml": [], "nix": []})
    assert text.splitlines() == [
        "Keys of vendomat.yaml:",
        "  (none)",
        "",
        "Set only in Nix (not by a key of vendomat.yaml):",
        "  (none)",
    ]


def test_a_directory_without_devenv_yaml_is_not_a_workspace(tmp_path: Path):
    result = runner.invoke(app, ["explain", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "not a Vendomat workspace" in result.output


def test_a_failed_evaluation_prints_the_trimmed_error_and_keeps_the_trace(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    trace = (Path(__file__).parent / "fixtures" / "trim" / "yaml-faults.txt").read_text()
    (tmp_path / "trace.txt").write_text(trace)
    monkeypatch.setenv("VENDOMAT_DEVENV", str(fake_devenv(tmp_path / "bad", f"cat {tmp_path}/trace.txt >&2\nexit 1\n")))
    result = runner.invoke(app, ["explain", "--root", str(workspace)])
    assert result.exit_code == 2
    lines = result.output.splitlines()
    assert lines[0].startswith("vendomat explain: vendomat.yaml:3:5: programs[1]: unknown program")
    assert lines[1].startswith("vendomat.yaml:6:14:")
    assert len(lines) < 10
    log_line = lines[-1]
    assert log_line.startswith("the full trace is in ")
    log = Path(log_line.removeprefix("the full trace is in "))
    assert log.parent == tmp_path / "state" / "vendomat" / "logs"
    assert trace.strip() in log.read_text()


def test_a_missing_devenv_is_an_infrastructure_fault(workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_DEVENV", str(tmp_path / "none"))
    result = runner.invoke(app, ["explain", "--root", str(workspace)])
    assert result.exit_code == 2
    assert "VENDOMAT_DEVENV" in result.output


def test_output_without_a_report_is_an_error(workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_DEVENV", str(fake_devenv(tmp_path / "odd", "echo '{\"other\": 1}'\n")))
    result = runner.invoke(app, ["explain", "--root", str(workspace)])
    assert result.exit_code == 2
    assert "vendomat.explain" in result.output

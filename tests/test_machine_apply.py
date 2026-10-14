"""`vendomat apply`: the order of the steps, the refusals, and the record line (R15, R43, `VMT-075`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from machinesim import SUDO, Machine, commit_file, git, make_workspace
from typer.testing import CliRunner

from vendomat import apply as apply_module
from vendomat.apply import apply, deploy_argv, machine_name
from vendomat.cli import app
from vendomat.record import RecordError, read_entries


def lines(machine: Machine) -> list[dict]:
    return [json.loads(line) for line in machine.record.read_text().splitlines()]


def test_the_machine_name_comes_from_the_facts_file(tmp_path: Path):
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"hostname": "laptop", "version": 1}))
    assert machine_name(facts) == "laptop"


@pytest.mark.parametrize("text, code", [(None, 2), ("not json", 2), ("[]", 2), ('{"hostname": ""}', 2)])
def test_a_missing_or_bad_facts_file_is_a_fault(tmp_path: Path, text: str | None, code: int):
    facts = tmp_path / "facts.json"
    if text is not None:
        facts.write_text(text)
    with pytest.raises(RecordError) as info:
        machine_name(facts)
    assert info.value.code == code


def test_apply_builds_switches_and_records(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    said: list[str] = []
    result = apply(root, emit=said.append, **machine.kwargs())
    build = machine.calls[0]
    assert build[1:] == ["build", "machines.box.build.nixos"]
    top = machine.build_path(root)
    assert machine.calls[1][1:] == ["nix-env", "--profile", str(machine.profile), "--set", top]
    assert machine.calls[2][1:] == [f"{top}/bin/switch-to-configuration", "switch"]
    # The record is written after the switch, as root.
    assert machine.calls.index(machine.calls[2]) < next(i for i, c in enumerate(machine.calls) if c[1:2] == ["tee"])
    assert all(call[0] == SUDO for call in machine.calls if call[0] != "systemctl" and "devenv" not in call[0])
    [entry] = lines(machine)
    assert entry["generation"] == 1 and entry["toplevel"] == top
    assert entry["commit"] == git(root, "rev-parse", "HEAD") and entry["dirty"] is False
    assert entry["time"].endswith("Z")
    assert result.generation == 1 and result.failed_units == []
    assert any("generation 1 is active" in line for line in said)
    assert "failed units: none" in said


def test_apply_reports_the_failed_units(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", failed_units="foo.service loaded failed failed Foo\n")
    said: list[str] = []
    result = apply(root, emit=said.append, **machine.kwargs())
    assert result.failed_units == ["foo.service"] and "failed units: foo.service" in said


def test_apply_makes_a_new_generation_for_a_new_system_and_none_for_the_same_one(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    apply(root, emit=lambda _: None, **machine.kwargs())
    apply(root, emit=lambda _: None, **machine.kwargs())  # the same files, the same system path
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert [e["generation"] for e in lines(machine)] == [1, 1, 2]
    assert len({e["toplevel"] for e in lines(machine)}) == 2


@pytest.mark.parametrize("name", ["vendomat.yaml", "devenv.lock", "devenv.nix"])
def test_apply_refuses_an_uncommitted_change_and_runs_nothing(tmp_path: Path, name: str):
    root = make_workspace(tmp_path / "ws")
    (root / name).write_text("changed\n")
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match=f"modified: {name}") as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 1
    assert machine.calls == [] and not machine.record.exists()


def test_apply_refuses_an_untracked_and_an_ignored_hatch_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.local.nix").write_text("{ }\n")  # ignored by the workspace .gitignore
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match="ignored: devenv.local.nix"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == []


def test_apply_ignores_a_change_to_a_file_that_is_not_watched(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "notes.txt").write_text("two\n")
    machine = Machine(tmp_path / "m")
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert lines(machine)[0]["dirty"] is False


def test_apply_with_dirty_goes_on_and_marks_the_line(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ x = 3; }\n")
    machine = Machine(tmp_path / "m")
    said: list[str] = []
    apply(root, dirty_ok=True, emit=said.append, **machine.kwargs())
    [entry] = lines(machine)
    assert entry["dirty"] is True and entry["commit"] == git(root, "rev-parse", "HEAD")
    assert any(line.startswith("warning: applying uncommitted changes") for line in said)
    # The system is built from the edited file, not from the commit.
    assert entry["toplevel"] == machine.build_path(root)


def test_a_failed_build_changes_nothing(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", fail={"build"})
    with pytest.raises(RecordError, match="devenv build machines.box.build.nixos failed") as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 2
    assert not machine.record.exists() and not machine.profile.exists()


def test_a_failed_switch_writes_no_record_and_says_how_to_go_back(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", fail={"switch-to-configuration"})
    with pytest.raises(RecordError, match="switch-to-configuration failed .* No record line was written") as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 2
    assert not machine.record.exists()


def test_a_failed_profile_step_does_not_run_the_switch(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", fail={"nix-env"})
    with pytest.raises(RecordError, match="running system did not change"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert not any("switch-to-configuration" in call[1] for call in machine.calls if len(call) > 1)


def test_the_build_output_may_be_a_plain_path(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    plain = machine.build_path(root)
    original = machine.run

    def run(argv, **kw):
        if argv[0].endswith("devenv"):
            return apply_module.Result(0, f"building\n{plain}\n")
        return original(argv, **kw)

    machine.run = run  # ty: ignore[invalid-assignment]
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert lines(machine)[0]["toplevel"] == plain


def test_a_build_that_prints_no_path_is_a_fault(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.run = lambda argv, **kw: apply_module.Result(0, "nothing\n")  # ty: ignore[invalid-assignment]
    with pytest.raises(RecordError, match="printed no system path"):
        apply(root, emit=lambda _: None, **machine.kwargs())


def test_the_record_reads_back_through_the_reader(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    apply(root, emit=lambda _: None, **machine.kwargs())
    [entry] = read_entries(machine.record)
    assert entry.generation == 1 and entry.dirty is False


def test_apply_with_the_name_of_another_machine_runs_the_devenv_deploy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_DEVENV", "/x/devenv")
    assert deploy_argv("server") == ["/x/devenv", "machines", "deploy", "server"]
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    monkeypatch.setattr(apply_module, "FACTS_PATH", machine.facts)
    execs: list[list[str]] = []
    monkeypatch.setattr("os.execvp", lambda file, argv: execs.append(argv))
    monkeypatch.setattr("vendomat.cli.machine_name", lambda: "box")
    result = CliRunner().invoke(app, ["apply", "server", "--root", str(root)])
    assert execs == [["/x/devenv", "machines", "deploy", "server"]], result.output
    assert machine.calls == []


def test_the_cli_maps_a_refusal_to_exit_status_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("changed\n")
    machine = Machine(tmp_path / "m")
    monkeypatch.setattr("vendomat.cli.machine_name", lambda: "box")
    monkeypatch.setattr(apply_module, "FACTS_PATH", machine.facts)
    result = CliRunner().invoke(app, ["apply", "--root", str(root)])
    assert result.exit_code == 1
    assert "vendomat apply: uncommitted changes to watched files" in result.output


def test_the_cli_maps_a_missing_workspace_to_exit_status_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("vendomat.cli.machine_name", lambda: "box")
    (tmp_path / "empty").mkdir()
    result = CliRunner().invoke(app, ["apply", "--root", str(tmp_path / "empty")])
    assert result.exit_code == 3 and "no workspace here" in result.output


def test_apply_copies_the_cache_key_into_the_workspace_and_asks_for_a_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.cache_key.write_text("box:AAAA=\n")
    said: list[str] = []
    apply(root, emit=said.append, cache_key=machine.cache_key, **machine.kwargs())
    target = root / ".machines" / "box" / "cache-key.pub"
    assert target.read_text() == "box:AAAA=\n"
    assert said[-1] == "wrote .machines/box/cache-key.pub; commit it so that your other machines trust this one"
    # The command does not commit. The file is untracked, and it does not make the next apply dirty.
    assert git(root, "status", "--porcelain") == "?? .machines/"
    said.clear()
    apply(root, emit=said.append, cache_key=machine.cache_key, **machine.kwargs())
    assert not any("cache-key.pub" in line for line in said), "same content: no copy, no message"


def test_apply_copies_a_changed_cache_key_and_never_commits(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.cache_key.write_text("box:AAAA=\n")
    apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())
    git(root, "add", ".machines")
    git(root, "commit", "--quiet", "-m", "publish key")
    head = git(root, "rev-parse", "HEAD")
    machine.cache_key.write_text("box:BBBB=\n")
    said: list[str] = []
    apply(root, emit=said.append, cache_key=machine.cache_key, **machine.kwargs())
    assert (root / ".machines" / "box" / "cache-key.pub").read_text() == "box:BBBB=\n"
    assert any("commit it" in line for line in said)
    assert (
        git(root, "rev-parse", "HEAD") == head and git(root, "status", "--porcelain") == "M .machines/box/cache-key.pub"
    )


def test_apply_without_a_cache_key_writes_nothing(tmp_path: Path):
    # A machine with `serve: false` makes no key.
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())
    assert not (root / ".machines").exists()


def test_a_failed_switch_does_not_publish_the_key(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", fail={"switch-to-configuration"})
    machine.cache_key.write_text("box:AAAA=\n")
    with pytest.raises(RecordError):
        apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())
    assert not (root / ".machines").exists()


def test_a_switch_that_exits_4_is_active_with_a_warning_and_is_recorded(tmp_path: Path):
    # Exit 4: the new system is active, but some units failed. The record must still hold the generation.
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", codes={"switch-to-configuration": 4})
    said: list[str] = []
    result = apply(root, emit=said.append, **machine.kwargs())
    assert result.generation == 1 and len(lines(machine)) == 1
    assert any(line.startswith("warning: switch-to-configuration exited 4") for line in said)


def test_a_switch_that_exits_2_is_a_fault_with_no_record(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", codes={"switch-to-configuration": 2})
    with pytest.raises(RecordError, match="exit 2"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert not machine.record.exists()

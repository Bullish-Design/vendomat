"""`vendomat apply`: the order of the steps, the refusals, and the record line (R15, R43, `VMT-075`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from machinesim import SUDO, Machine, commit_file, fake_devenv, git, make_workspace
from typer.testing import CliRunner

from vendomat import apply as apply_module
from vendomat.apply import apply, deploy_argv, machine_name
from vendomat.cli import app
from vendomat.record import RecordError, read_entries


def no_committer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make Git unable to name a committer: no identity in the environment, and no guess from the host."""
    for name in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "EMAIL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "user.useConfigOnly")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")


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
def test_apply_commits_a_changed_watched_file_after_build(tmp_path: Path, name: str):
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / name).write_text("changed\n")
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.calls[0][1:] == ["build", "machines.box.build.nixos"]
    assert git(root, "rev-parse", "HEAD") != before
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == [name]
    assert git(root, "status", "--porcelain") == ""
    assert result.commit == git(root, "rev-parse", "HEAD")


def test_apply_builds_then_commits_configuration_then_activates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ changed = true; }\n")
    machine = Machine(tmp_path / "m")
    order: list[str] = []
    build = apply_module.build_toplevel
    commit = apply_module.workspace.commit_watched
    activate = apply_module.activate

    def ordered_build(*args, **kwargs):
        order.append("build")
        return build(*args, **kwargs)

    def ordered_commit(*args, **kwargs):
        order.append("commit")
        return commit(*args, **kwargs)

    def ordered_activate(*args, **kwargs):
        order.append("activate")
        return activate(*args, **kwargs)

    monkeypatch.setattr(apply_module, "build_toplevel", ordered_build)
    monkeypatch.setattr(apply_module.workspace, "commit_watched", ordered_commit)
    monkeypatch.setattr(apply_module, "activate", ordered_activate)
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert order == ["build", "commit", "activate"]


def test_apply_refuses_an_ignored_hatch_file_even_with_dirty(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.local.nix").write_text("{ }\n")  # ignored by the workspace .gitignore
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match="Force-add them with `git add -f`"):
        apply(root, dirty_ok=True, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == []


def test_apply_commits_a_force_added_ignored_hatch_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.local.nix").write_text("{ local = true; }\n")
    git(root, "add", "-f", "devenv.local.nix")
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == ["devenv.local.nix"]
    assert result.commit == git(root, "rev-parse", "HEAD")


def test_apply_commits_an_untracked_watched_file(tmp_path: Path):
    # R49: a new hatch file that Git does not ignore is part of the configuration.
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\n"})
    (root / "devenv.local.nix").write_text("{ local = true; }\n")
    assert git(root, "status", "--porcelain") == "?? devenv.local.nix"
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "show", "--format=", "--name-status", "HEAD").splitlines() == ["A\tdevenv.local.nix"]
    assert git(root, "status", "--porcelain") == "" and result.commit == git(root, "rev-parse", "HEAD")


def test_apply_commits_a_deleted_watched_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.lock").unlink()
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "show", "--format=", "--name-status", "HEAD").splitlines() == ["D\tdevenv.lock"]
    assert git(root, "status", "--porcelain") == "" and result.commit == git(root, "rev-parse", "HEAD")
    assert lines(machine)[0]["toplevel"] == machine.build_path(root)  # built without the file


def test_apply_from_a_subdirectory_workspace_commits_the_change(tmp_path: Path):
    # `git status` names paths from the repository top. Without the prefix strip, apply saw no change and
    # recorded the old commit for a state that it had built from the edited files (R43).
    top = make_workspace(tmp_path / "repo")
    sub = top / "proj"
    sub.mkdir()
    for name in ("vendomat.yaml", "devenv.lock", "devenv.nix"):
        (sub / name).write_text((top / name).read_text())
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", "workspace in a subdirectory")
    (sub / "devenv.nix").write_text("{ x = 5; }\n")
    machine = Machine(tmp_path / "m")
    result = apply(sub, emit=lambda _: None, **machine.kwargs())
    assert git(top, "show", "--format=", "--name-only", "HEAD").splitlines() == ["proj/devenv.nix"]
    assert result.commit == git(top, "rev-parse", "HEAD") == lines(machine)[0]["commit"]


def test_apply_makes_no_commit_when_the_staged_change_was_reverted(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    git(root, "add", "devenv.nix")
    (root / "devenv.nix").write_text("{ }\n")  # the status reads `MM`; the content equals HEAD
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "rev-parse", "HEAD") == before == result.commit
    assert lines(machine)[0]["commit"] == before


def test_apply_refuses_before_the_build_without_a_committer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    no_committer(monkeypatch)
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match="git cannot name a committer.*Nothing was built"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == [] and not machine.record.exists()


def test_apply_does_not_need_a_committer_when_it_commits_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = make_workspace(tmp_path / "ws")
    no_committer(monkeypatch)
    machine = Machine(tmp_path / "m")
    assert apply(root, emit=lambda _: None, **machine.kwargs()).generation == 1


def test_apply_works_on_a_detached_head(tmp_path: Path):
    # A jj-colocated checkout is always detached. Apply must not refuse it.
    root = make_workspace(tmp_path / "ws")
    git(root, "checkout", "--quiet", "--detach")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert result.commit == git(root, "rev-parse", "HEAD")
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == ["devenv.nix"]


@pytest.mark.parametrize("dirty", [False, True])
def test_a_watched_file_edited_during_the_build_is_not_committed_or_activated(tmp_path: Path, dirty: bool):
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    machine = Machine(tmp_path / "m")
    original = machine.run

    def run(argv, **kw):
        result = original(argv, **kw)
        if argv[0].endswith("devenv") and argv[1] == "build":
            (root / "devenv.nix").write_text("{ x = 2; }\n")  # the owner saves again while the build runs
        return result

    machine.run = run  # ty: ignore[invalid-assignment]
    with pytest.raises(RecordError, match="devenv.nix changed during the build.*Nothing was committed or activated"):
        apply(root, dirty_ok=dirty, emit=lambda _: None, **machine.kwargs())
    assert git(root, "rev-parse", "HEAD") == before
    assert [call[1] for call in machine.calls] == ["build"]
    assert not machine.record.exists() and not machine.profile.exists()


@pytest.mark.parametrize("dirty", [False, True])
@pytest.mark.parametrize("change", ["edit", "create"])
def test_a_file_that_is_not_watched_edited_during_the_build_is_refused(tmp_path: Path, dirty: bool, change: str):
    # R55: the check covers the whole tree under the root, not only the four watched files.
    root = make_workspace(tmp_path / "ws")
    (root / "nixos").mkdir()
    (root / "nixos" / "x.nix").write_text("{ }\n")
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "module")
    before = git(root, "rev-parse", "HEAD")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    machine = Machine(tmp_path / "m")
    original = machine.run

    def run(argv, **kw):
        result = original(argv, **kw)
        if argv[0].endswith("devenv") and argv[1] == "build":
            if change == "edit":
                (root / "nixos" / "x.nix").write_text("{ saved = true; }\n")
            else:
                (root / "nixos" / "new.nix").write_text("{ }\n")
        return result

    machine.run = run  # ty: ignore[invalid-assignment]
    name = "nixos/x.nix" if change == "edit" else "nixos/new.nix"
    with pytest.raises(RecordError, match=f"{name} changed during the build.*Nothing was committed or activated"):
        apply(root, dirty_ok=dirty, emit=lambda _: None, **machine.kwargs())
    assert git(root, "rev-parse", "HEAD") == before
    assert [call[1] for call in machine.calls] == ["build"]
    assert not machine.record.exists() and not machine.profile.exists()


def test_a_config_commit_stays_when_activation_fails_later(tmp_path: Path):
    # D9: the commit records the configuration that the owner asked for. A failed switch does not undo it.
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / "devenv.nix").write_text("{ x = 7; }\n")
    machine = Machine(tmp_path / "m", fail={"switch-to-configuration"})
    with pytest.raises(RecordError, match="The configuration commit stays; apply again to retry"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "rev-parse", "HEAD") != before
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == ["devenv.nix"]
    assert git(root, "status", "--porcelain") == "" and not machine.record.exists()


def test_apply_refuses_a_changed_tracked_file_that_is_not_watched(tmp_path: Path):
    # R55: a record is a whole commit. A change that apply would not commit stops it before the build.
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ x = 1; }\n")  # a watched change does not hide the other one
    (root / "notes.txt").write_text("two\n")
    machine = Machine(tmp_path / "m")
    with pytest.raises(
        RecordError, match=r"(?s)modified: notes\.txt.*Commit these paths or remove them.*Nothing was built"
    ) as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 1
    assert machine.calls == [] and not machine.record.exists()
    assert git(root, "rev-list", "--count", "HEAD") == "1"  # no commit, not even of the watched file


def test_apply_refuses_a_new_untracked_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "nixos").mkdir()
    (root / "nixos" / "x.nix").write_text("{ }\n")
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match=r"untracked: nixos/x\.nix"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == []


def test_apply_refuses_a_staged_file_and_names_every_path(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "notes.txt").write_text("staged\n")
    git(root, "add", "notes.txt")
    (root / "extra.txt").write_text("new\n")
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError) as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert "notes.txt" in str(info.value) and "extra.txt" in str(info.value)
    assert machine.calls == []


def test_apply_refuses_a_deleted_file_that_is_not_watched(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "notes.txt").unlink()
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError, match=r"deleted: notes\.txt"):
        apply(root, emit=lambda _: None, **machine.kwargs())


def test_apply_allows_a_file_that_git_ignores(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / ".devenv").mkdir()
    (root / ".devenv" / "state").write_text("cache\n")  # the workspace .gitignore holds `.devenv*`
    machine = Machine(tmp_path / "m")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert result.dirty is False and lines(machine)[0]["dirty"] is False
    assert git(root, "rev-list", "--count", "HEAD") == "1"


def test_apply_allows_a_clean_tree_and_commits_only_the_watched_files(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ x = 4; }\n")
    (root / "devenv.lock").write_text("{}\n")
    machine = Machine(tmp_path / "m")
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert sorted(git(root, "show", "--format=", "--name-only", "HEAD").splitlines()) == ["devenv.lock", "devenv.nix"]
    assert git(root, "status", "--porcelain") == ""


def test_the_key_file_that_a_previous_apply_wrote_does_not_block_the_next_apply(tmp_path: Path):
    # VMT-161: apply writes `.machines/NAME/cache-key.pub` and never commits it. R55 must not make
    # that output stop the next apply, whether the file is new or a tracked file that apply changed.
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.cache_key.write_text("box:AAAA=\n")
    apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())
    assert git(root, "status", "--porcelain") == "?? .machines/"
    result = apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())  # new file
    assert result.generation == 1 and len(lines(machine)) == 2
    git(root, "add", ".machines")
    git(root, "commit", "--quiet", "-m", "publish key")
    machine.cache_key.write_text("box:BBBB=\n")
    apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())  # writes a changed key
    assert git(root, "status", "--porcelain") == "M .machines/box/cache-key.pub"
    apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())  # tracked and modified
    assert len(lines(machine)) == 4
    assert all(line["dirty"] is False for line in lines(machine))


def test_the_key_file_of_another_machine_or_without_a_key_source_is_a_change(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.cache_key.write_text("box:AAAA=\n")
    other = root / ".machines" / "other"
    other.mkdir(parents=True)
    (other / "cache-key.pub").write_text("other:CCCC=\n")
    with pytest.raises(RecordError, match=r"untracked: \.machines/other/cache-key\.pub"):
        apply(root, emit=lambda _: None, cache_key=machine.cache_key, **machine.kwargs())
    (other / "cache-key.pub").unlink()
    own = root / ".machines" / "box"
    own.mkdir(parents=True)
    (own / "cache-key.pub").write_text("hand-made\n")
    absent = tmp_path / "no-such-key"  # a machine with `serve: false` has no key file
    with pytest.raises(RecordError, match=r"untracked: \.machines/box/cache-key\.pub"):
        apply(root, emit=lambda _: None, cache_key=absent, **machine.kwargs())
    assert machine.calls == []


def test_apply_with_dirty_allows_other_changes_and_records_dirty(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / "notes.txt").write_text("two\n")
    (root / "extra.txt").write_text("new\n")
    machine = Machine(tmp_path / "m")
    said: list[str] = []
    result = apply(root, dirty_ok=True, emit=said.append, **machine.kwargs())
    [entry] = lines(machine)
    assert result.dirty is True and entry["dirty"] is True and entry["commit"] == before
    assert git(root, "rev-parse", "HEAD") == before  # --dirty makes no commit
    assert any("notes.txt" in line and "extra.txt" in line for line in said if line.startswith("warning"))
    assert git(root, "status", "--porcelain").splitlines() == ["M notes.txt", "?? extra.txt"]


def test_apply_with_dirty_and_a_clean_tree_records_clean(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    apply(root, dirty_ok=True, emit=lambda _: None, **machine.kwargs())
    assert lines(machine)[0]["dirty"] is False


def test_a_subdirectory_workspace_ignores_a_change_outside_the_workspace_root(tmp_path: Path):
    top = make_workspace(tmp_path / "repo")
    sub = top / "proj"
    sub.mkdir()
    for name in ("vendomat.yaml", "devenv.lock", "devenv.nix"):
        (sub / name).write_text((top / name).read_text())
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", "workspace in a subdirectory")
    (top / "notes.txt").write_text("changed outside\n")  # tracked, outside the root
    (top / "elsewhere.txt").write_text("new outside\n")  # untracked, outside the root
    (sub / "devenv.nix").write_text("{ x = 5; }\n")
    machine = Machine(tmp_path / "m")
    result = apply(sub, emit=lambda _: None, **machine.kwargs())
    assert git(top, "show", "--format=", "--name-only", "HEAD").splitlines() == ["proj/devenv.nix"]
    assert result.commit == git(top, "rev-parse", "HEAD")
    assert git(top, "status", "--porcelain").splitlines() == ["M notes.txt", "?? elsewhere.txt"]


def test_a_subdirectory_workspace_refuses_a_change_inside_the_workspace_root(tmp_path: Path):
    top = make_workspace(tmp_path / "repo")
    sub = top / "proj"
    (sub / "nixos").mkdir(parents=True)
    for name in ("vendomat.yaml", "devenv.lock", "devenv.nix"):
        (sub / name).write_text((top / name).read_text())
    (sub / "nixos" / "x.nix").write_text("{ }\n")
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", "workspace in a subdirectory")
    (sub / "nixos" / "x.nix").write_text("{ changed = true; }\n")
    machine = Machine(tmp_path / "m")
    with pytest.raises(RecordError) as info:
        apply(sub, emit=lambda _: None, **machine.kwargs())
    assert "modified: nixos/x.nix" in str(info.value) and "proj/" not in str(info.value)
    assert machine.calls == []


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
    assert git(root, "status", "--porcelain") == "M devenv.nix"


def test_a_failed_build_changes_nothing(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = git(root, "rev-parse", "HEAD")
    (root / "devenv.nix").write_text("{ x = 9; }\n")
    machine = Machine(tmp_path / "m", fail={"build"})
    with pytest.raises(RecordError, match="devenv build machines.box.build.nixos failed") as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 2
    assert git(root, "rev-parse", "HEAD") == before
    assert git(root, "status", "--porcelain") == "M devenv.nix"
    assert not machine.record.exists() and not machine.profile.exists()


def test_apply_commits_only_watched_paths_and_keeps_a_staged_file_outside_the_root(tmp_path: Path):
    # A staged file inside the root now stops apply (R55). One outside the root stays staged and uncommitted.
    top = make_workspace(tmp_path / "repo")
    sub = top / "proj"
    sub.mkdir()
    for name in ("vendomat.yaml", "devenv.lock", "devenv.nix"):
        (sub / name).write_text((top / name).read_text())
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", "workspace in a subdirectory")
    (sub / "devenv.nix").write_text("{ x = 4; }\n")
    (top / "notes.txt").write_text("later\n")
    git(top, "add", "notes.txt")
    machine = Machine(tmp_path / "m")
    result = apply(sub, emit=lambda _: None, **machine.kwargs())
    assert git(top, "show", "--format=", "--name-only", "HEAD").splitlines() == ["proj/devenv.nix"]
    assert git(top, "status", "--porcelain") == "M  notes.txt"
    assert result.commit == git(top, "rev-parse", "HEAD")


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
        if argv[0].endswith("devenv") and argv[1] == "build":
            return apply_module.Result(0, f"building\n{plain}\n")
        return original(argv, **kw)

    machine.run = run  # ty: ignore[invalid-assignment]
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert lines(machine)[0]["toplevel"] == plain


def test_a_build_that_prints_no_path_is_a_fault(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    original = machine.run
    machine.run = lambda argv, **kw: (  # ty: ignore[invalid-assignment]
        apply_module.Result(0, "nothing\n") if argv[1] == "build" else original(argv, **kw)
    )
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


def test_the_cli_refuses_an_ignored_watched_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_DEVENV", fake_devenv(tmp_path))
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.local.nix").write_text("{ }\n")
    machine = Machine(tmp_path / "m")
    monkeypatch.setattr("vendomat.cli.machine_name", lambda: "box")
    monkeypatch.setattr(apply_module, "FACTS_PATH", machine.facts)
    result = CliRunner().invoke(app, ["apply", "--root", str(root)])
    assert result.exit_code == 1
    assert "vendomat apply: ignored configuration file(s) are present" in result.output


def test_apply_help_describes_configuration_commits_and_dirty_mode():
    result = CliRunner().invoke(app, ["apply", "--help"])
    assert result.exit_code == 0
    text = " ".join(result.output.replace("│", " ").split())
    assert "A record is always a whole commit" in text and "must still be force-added" in text
    assert "allows other changes" in text and "without a commit" in text


def test_the_cli_refuses_another_uncommitted_file_with_exit_status_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_DEVENV", fake_devenv(tmp_path))
    root = make_workspace(tmp_path / "ws")
    (root / "notes.txt").write_text("two\n")
    machine = Machine(tmp_path / "m")
    monkeypatch.setattr("vendomat.cli.machine_name", lambda: "box")
    monkeypatch.setattr(apply_module, "FACTS_PATH", machine.facts)
    result = CliRunner().invoke(app, ["apply", "--root", str(root)])
    assert result.exit_code == 1
    assert "vendomat apply: uncommitted changes outside" in result.output and "notes.txt" in result.output


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

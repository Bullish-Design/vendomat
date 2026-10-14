"""`vendomat rollback`: the choice of a target, the refusals, and the commit (R30, R43, `VMT-072`, `VMT-098`)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from machinesim import SUDO, Machine, commit_file, git, make_workspace
from typer.testing import CliRunner

from vendomat import apply as apply_module
from vendomat import workspace
from vendomat.apply import apply
from vendomat.cli import app
from vendomat.record import Entry, RecordError
from vendomat.rollback import find_boot_entry, rollback


@dataclass
class World:
    root: Path
    machine: Machine
    first: str  # commit of system A
    second: str  # commit of system A'

    def apply(self, **kw) -> None:
        apply(self.root, emit=lambda _: None, **self.machine.kwargs(), **kw)

    def rollback(self, said: list[str] | None = None, **kw):
        out = said if said is not None else []
        return rollback(self.root, emit=out.append, boot_entries=self.machine.boot, **self.machine.kwargs(), **kw)

    def lines(self) -> list[dict]:
        return [json.loads(x) for x in self.machine.record.read_text().splitlines()]


@pytest.fixture
def world(tmp_path: Path) -> World:
    """System A at commit one, then system A' at commit two. The machine runs A'."""

    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    first = git(root, "rev-parse", "HEAD")
    apply(root, emit=lambda _: None, **machine.kwargs())
    second = commit_file(root, "devenv.nix", '{ marker = "A-prime"; }\n', "A prime")
    apply(root, emit=lambda _: None, **machine.kwargs())
    return World(root, machine, first, second)


def names(machine: Machine) -> list[str]:
    return [" ".join(call[:3]) for call in machine.calls]


def test_the_default_rollback_restores_the_files_commits_and_applies(world: World):
    top_a = world.lines()[0]["toplevel"]
    assert world.machine.current() != top_a
    said: list[str] = []
    done = world.rollback(said)
    assert done is not None and done.applied is not None
    # The same files give the same system path (VMT-110: no commit inside the system).
    assert world.machine.current() == top_a
    assert done.applied.generation == 3
    assert (world.root / "devenv.nix").read_text() == "{ }\n"
    # The restore is a commit, named for its target.
    assert git(world.root, "log", "-1", "--format=%s") == f"rollback to {world.first[:12]}"
    assert git(world.root, "status", "--porcelain") == ""
    assert git(world.root, "diff", world.first, "HEAD", "--", "devenv.nix", "vendomat.yaml", "devenv.lock") == ""
    # The record gets a line with the new commit, and it is clean.
    last = world.lines()[-1]
    assert last["generation"] == 3 and last["toplevel"] == top_a and last["dirty"] is False
    assert last["commit"] == git(world.root, "rev-parse", "HEAD") != world.first
    assert any(line.startswith("committed ") for line in said)


def test_the_diff_is_shown_before_the_first_command_runs(world: World):
    seen: list[tuple[str, int]] = []
    world.machine.calls.clear()

    def emit(line: str) -> None:
        seen.append((line, len(world.machine.calls)))

    rollback(world.root, emit=emit, boot_entries=world.machine.boot, **world.machine.kwargs())
    diff_at = next(count for line, count in seen if line.startswith("devenv.nix |"))
    assert diff_at == 0
    assert any("-{ marker" in line or "marker" in line for line, _ in seen)


def test_a_second_rollback_goes_back_to_the_system_it_left(world: World):
    world.rollback()
    top_prime = world.lines()[1]["toplevel"]
    world.rollback()
    assert world.machine.current() == top_prime
    assert (world.root / "devenv.nix").read_text().startswith("{ marker")


def test_rollback_skips_a_dirty_entry_and_says_so(world: World):
    (world.root / "devenv.nix").write_text('{ marker = "dirty"; }\n')
    world.apply(dirty_ok=True)  # generation 3, dirty
    git(world.root, "checkout", "--", "devenv.nix")
    world.apply()  # A' again, generation 4, clean
    said: list[str] = []
    done = world.rollback(said)
    assert done is not None and done.applied is not None
    assert any("skipped generation 3: applied with uncommitted changes" in line for line in said)
    assert world.machine.current() == world.lines()[0]["toplevel"]  # system A, not the dirty one


def test_rollback_refuses_when_only_dirty_entries_remain(world: World):
    entries = [json.loads(x) for x in world.machine.record.read_text().splitlines()]
    entries[0]["dirty"] = True
    world.machine.record.write_text("".join(json.dumps(e) + "\n" for e in entries))
    with pytest.raises(RecordError, match="every earlier entry was applied with uncommitted changes"):
        world.rollback()


@pytest.mark.parametrize("name", ["vendomat.yaml", "devenv.lock", "devenv.nix"])
def test_rollback_refuses_an_uncommitted_change(world: World, name: str):
    (world.root / name).write_text("edit\n")
    calls = len(world.machine.calls)
    with pytest.raises(RecordError, match=f"uncommitted changes to watched files .*{name}") as info:
        world.rollback()
    assert info.value.code == 1
    assert len(world.machine.calls) == calls and (world.root / name).read_text() == "edit\n"


def test_a_working_copy_restore_is_refused_by_both_commands(world: World):
    # A restore that stays in the working copy leaves the tree dirty. Neither command goes on.
    git(world.root, "restore", f"--source={world.first}", "--", "devenv.nix")
    with pytest.raises(RecordError, match="uncommitted changes"):
        world.apply()
    with pytest.raises(RecordError, match="uncommitted changes"):
        world.rollback()


def test_rollback_refuses_an_unknown_commit(world: World):
    with pytest.raises(RecordError, match="unknown commit no-such-rev") as info:
        world.rollback(to="no-such-rev")
    assert info.value.code == 1


def test_rollback_refuses_a_recorded_commit_that_the_repository_lost(world: World):
    entries = [json.loads(x) for x in world.machine.record.read_text().splitlines()]
    entries[0]["commit"] = "f" * 40
    world.machine.record.write_text("".join(json.dumps(e) + "\n" for e in entries))
    with pytest.raises(RecordError, match="does not hold it") as info:
        world.rollback()
    assert info.value.code == 1


def test_rollback_to_a_commit_needs_no_record_entry(world: World):
    done = world.rollback(to=world.first)
    assert done is not None and done.target_commit == world.first
    assert (world.root / "devenv.nix").read_text() == "{ }\n"


def test_rollback_by_generation(world: World):
    commit_file(world.root, "devenv.nix", '{ marker = "third"; }\n', "third")
    world.apply()  # generation 3
    done = world.rollback(generation=2)
    assert done is not None and done.target_commit == world.second
    assert (world.root / "devenv.nix").read_text().startswith('{ marker = "A-prime"')


def test_usage_errors_exit_with_status_3(world: World):
    calls = (
        lambda: world.rollback(to="x", generation=1),
        lambda: world.rollback(exact=True, fast=True),
        lambda: world.rollback(fast=True, boot_only=True),
    )
    for call in calls:
        with pytest.raises(RecordError) as info:
            call()
        assert info.value.code == 3


def test_dry_run_shows_the_diff_and_changes_nothing(world: World):
    head = workspace.head(world.root)
    calls = len(world.machine.calls)
    said: list[str] = []
    assert world.rollback(said, dry_run=True) is None
    assert workspace.head(world.root) == head and len(world.machine.calls) == calls
    assert "dry run: nothing changed" in said and git(world.root, "status", "--porcelain") == ""


def test_exact_restores_every_tracked_file(world: World):
    commit_file(world.root, "notes.txt", "later\n", "notes")
    done = world.rollback(to=world.first, exact=True)
    assert done is not None
    assert (world.root / "notes.txt").read_text() == "one\n"
    assert git(world.root, "diff", world.first, "HEAD") == ""
    assert git(world.root, "log", "-1", "--format=%s") == f"rollback to {world.first[:12]}"


def test_exact_refuses_a_change_to_any_tracked_file(world: World):
    (world.root / "notes.txt").write_text("edit\n")
    with pytest.raises(RecordError, match="--exact replaces every tracked file"):
        world.rollback(to=world.first, exact=True)


def test_fast_moves_the_profile_builds_nothing_and_still_commits(world: World):
    top_a = world.lines()[0]["toplevel"]
    world.machine.calls.clear()
    done = world.rollback(fast=True)
    assert done is not None and done.applied is not None
    assert not any("devenv" in call[0] for call in world.machine.calls)
    switch = next(c for c in world.machine.calls if c[0] == SUDO and c[1] == "nix-env")
    assert switch[2:] == ["--profile", str(world.machine.profile), "--switch-generation", "1"]
    assert world.machine.current() == top_a and world.machine.number() == 1  # no new generation
    assert git(world.root, "log", "-1", "--format=%s") == f"rollback to {world.first[:12]}"
    assert world.lines()[-1]["generation"] == 1 and world.lines()[-1]["commit"] == workspace.head(world.root)


def test_fast_refuses_a_generation_that_left_the_machine(world: World):
    (world.machine.profiles / "system-1-link").unlink()
    head = workspace.head(world.root)
    with pytest.raises(RecordError, match="is gone from this machine"):
        world.rollback(fast=True)
    assert workspace.head(world.root) == head and git(world.root, "status", "--porcelain") == ""


def test_boot_only_sets_the_next_boot_and_changes_nothing_else(world: World):
    head = workspace.head(world.root)
    world.machine.calls.clear()
    said: list[str] = []
    done = world.rollback(said, boot_only=True)
    assert done is not None and done.boot_entry == "nixos-generation-1.conf"
    assert world.machine.calls == [[SUDO, "bootctl", "set-oneshot", "nixos-generation-1.conf"]]
    assert workspace.head(world.root) == head and git(world.root, "status", "--porcelain") == ""
    assert world.machine.number() == 2
    assert any("recovery" in line for line in said)


def test_boot_only_needs_a_boot_entry(world: World):
    (world.machine.boot / "nixos-generation-1.conf").unlink()
    with pytest.raises(RecordError, match="no boot entry for generation 1"):
        world.rollback(boot_only=True)


def test_boot_only_works_with_a_dirty_tree(world: World):
    (world.root / "devenv.nix").write_text("edit\n")
    done = world.rollback(boot_only=True)
    assert done is not None and done.boot_entry is not None


def test_find_boot_entry_reads_the_generation_from_the_version_line(tmp_path: Path):
    (tmp_path / "a.conf").write_text("title NixOS\nversion Generation 12 NixOS 26.11\n")
    (tmp_path / "b.conf").write_text("title NixOS\nversion Generation 2 NixOS 26.11\n")
    assert find_boot_entry(12, tmp_path) == "a.conf" and find_boot_entry(2, tmp_path) == "b.conf"
    with pytest.raises(RecordError):
        find_boot_entry(1, tmp_path)


def test_a_failed_build_leaves_the_tree_clean_and_makes_no_commit(world: World):
    head = workspace.head(world.root)
    world.machine.fail = {"build"}
    with pytest.raises(RecordError, match="devenv build"):
        world.rollback()
    assert workspace.head(world.root) == head
    assert git(world.root, "status", "--porcelain") == ""
    assert (world.root / "devenv.nix").read_text().startswith("{ marker")  # still A'


def test_a_failed_switch_keeps_the_commit_and_the_files_together(world: World):
    head = workspace.head(world.root)
    world.machine.fail = {"switch-to-configuration"}
    with pytest.raises(RecordError, match="switch-to-configuration failed"):
        world.rollback()
    assert workspace.head(world.root) != head  # the rollback commit stays
    assert git(world.root, "status", "--porcelain") == ""
    assert (world.root / "devenv.nix").read_text() == "{ }\n"


def test_a_rollback_with_no_record_is_refused(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.set_generation("/nix/store/aaa-system")
    with pytest.raises(RecordError, match="no earlier entry"):
        rollback(root, emit=lambda _: None, boot_entries=machine.boot, **machine.kwargs())


def test_an_empty_restore_still_commits(world: World):
    entries = [json.loads(x) for x in world.machine.record.read_text().splitlines()]
    entries[0]["commit"] = world.second  # the target commit equals the files now
    world.machine.record.write_text("".join(json.dumps(e) + "\n" for e in entries))
    before = workspace.head(world.root)
    said: list[str] = []
    world.rollback(said)
    assert workspace.head(world.root) != before
    assert "the files already equal the target commit; the rollback commit will be empty" in said


def test_the_cli_passes_the_options_and_maps_exit_status(world: World, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(apply_module, "FACTS_PATH", world.machine.facts)
    monkeypatch.setattr(apply_module, "PROFILE", world.machine.profile)
    monkeypatch.setattr("vendomat.rollback.PROFILE", world.machine.profile)
    monkeypatch.setattr("vendomat.rollback.RECORD_PATH", world.machine.record)
    monkeypatch.setattr("vendomat.rollback.BOOT_ENTRIES", world.machine.boot)
    monkeypatch.setattr(apply_module, "run_command", world.machine.run)
    monkeypatch.setattr("vendomat.rollback.run_command", world.machine.run)
    runner = CliRunner()
    bad = runner.invoke(app, ["rollback", "--root", str(world.root), "--to", "x", "--generation", "1"])
    assert bad.exit_code == 3 and "not both" in bad.output
    dry = runner.invoke(app, ["rollback", "--root", str(world.root), "--dry-run"])
    assert dry.exit_code == 0 and "dry run: nothing changed" in dry.output


def test_entries_are_plain_data():
    assert Entry(1, "/nix/store/a", "c", False, "t").line().startswith('{"generation":1,')

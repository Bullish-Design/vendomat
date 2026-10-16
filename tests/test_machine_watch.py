"""`vendomat.watch`: a module adds files to the watched set of `apply` and `rollback` (R62, `VMT-280`).

The first part uses a workspace whose module adds `extra.yaml`. The second part checks that `apply` and
`rollback` print the first fault line of a failed evaluation first (`VMT-281`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from machinesim import Machine, commit_file, git, make_workspace

from vendomat.apply import Result, apply, build_toplevel, devenv_binary, watch_paths
from vendomat.record import RecordError
from vendomat.rollback import rollback
from vendomat.workspace import WATCHED, WorkspaceError, check_watch_path, extend_watched

EXTRA = {"extra.yaml": "setting: one\n"}


def make(tmp_path: Path, **files: str) -> tuple[Path, Machine]:
    """A workspace that holds `extra.yaml`, and a machine whose module watches it."""
    root = make_workspace(tmp_path / "ws", {**EXTRA, **files})
    return root, Machine(tmp_path / "m", watch=["extra.yaml"])


def committed_names(root: Path, rev: str = "HEAD") -> list[str]:
    return git(root, "show", "--format=", "--name-only", rev).splitlines()


# --- apply ---------------------------------------------------------------------------------------------


def test_apply_reads_the_watch_list_with_devenv_eval(tmp_path: Path):
    root, machine = make(tmp_path)
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.evals == [[devenv_binary(), "eval", "vendomat.watch"]]
    assert machine.calls[0][1:] == ["build", "machines.box.build.nixos"]


def test_apply_commits_a_changed_extra_file(tmp_path: Path):
    root, machine = make(tmp_path)
    (root / "extra.yaml").write_text("setting: two\n")
    before = git(root, "rev-parse", "HEAD")
    result = apply(root, emit=lambda _: None, **machine.kwargs())
    assert git(root, "rev-parse", "HEAD") != before
    assert committed_names(root) == ["extra.yaml"]
    assert git(root, "status", "--porcelain") == ""
    assert result.commit == git(root, "rev-parse", "HEAD")


def test_apply_commits_a_new_extra_file_with_the_fixed_ones(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", watch=["extra.yaml"])
    (root / "extra.yaml").write_text("setting: new\n")
    (root / "devenv.nix").write_text("{ changed = true; }\n")
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert sorted(committed_names(root)) == ["devenv.nix", "extra.yaml"]


def test_without_the_watch_the_refusal_names_the_extra_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", EXTRA)
    machine = Machine(tmp_path / "m")  # no module watches extra.yaml
    (root / "extra.yaml").write_text("setting: two\n")
    with pytest.raises(RecordError, match=r"modified: extra\.yaml"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == []


def test_the_refusal_for_another_file_lists_the_watched_files(tmp_path: Path):
    root, machine = make(tmp_path)
    (root / "notes.txt").write_text("two\n")
    with pytest.raises(RecordError) as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert "notes.txt" in str(info.value)
    assert "vendomat.yaml, devenv.lock, devenv.nix, devenv.local.nix, extra.yaml" in str(info.value)
    assert machine.calls == []


def test_an_ignored_extra_file_needs_a_force_add_even_with_dirty(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\ndevenv.local.nix\nextra.yaml\n"})
    (root / "extra.yaml").write_text("setting: ignored\n")
    machine = Machine(tmp_path / "m", watch=["extra.yaml"])
    with pytest.raises(RecordError, match=r"ignored configuration file\(s\) are present: extra\.yaml"):
        apply(root, dirty_ok=True, emit=lambda _: None, **machine.kwargs())
    assert machine.calls == []
    git(root, "add", "-f", "extra.yaml")
    git(root, "commit", "--quiet", "-m", "track extra.yaml")
    (root / "extra.yaml").write_text("setting: two\n")
    apply(root, emit=lambda _: None, **machine.kwargs())
    assert committed_names(root) == ["extra.yaml"]


def test_a_change_to_the_extra_file_during_the_build_is_refused(tmp_path: Path):
    root, machine = make(tmp_path)
    run = machine.run

    def edit_during_build(argv, **kw):
        if list(argv)[1:2] == ["build"]:
            (root / "extra.yaml").write_text("setting: edited during the build\n")
        return run(argv, **kw)

    machine.run = edit_during_build  # ty: ignore[invalid-assignment]
    with pytest.raises(RecordError, match=r"extra\.yaml changed during the build"):
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert machine.record.exists() is False


def test_the_dirty_warning_names_the_extra_file(tmp_path: Path):
    root, machine = make(tmp_path)
    (root / "extra.yaml").write_text("setting: two\n")
    said: list[str] = []
    result = apply(root, dirty_ok=True, emit=said.append, **machine.kwargs())
    assert result.dirty
    assert any("modified: extra.yaml" in line for line in said)
    assert git(root, "status", "--short") == "M extra.yaml"  # the helper strips the leading space


# --- rollback ------------------------------------------------------------------------------------------


def test_rollback_restores_the_extra_file_and_the_system(tmp_path: Path):
    root, machine = make(tmp_path)
    apply(root, emit=lambda _: None, **machine.kwargs())  # system A: extra.yaml "one"
    system_a = machine.current()
    (root / "extra.yaml").write_text("setting: two\n")
    apply(root, emit=lambda _: None, **machine.kwargs())  # system B: the commit holds extra.yaml
    assert machine.current() != system_a
    said: list[str] = []
    rollback(root, emit=said.append, boot_entries=machine.boot, **machine.kwargs())
    assert (root / "extra.yaml").read_text() == "setting: one\n"
    assert machine.current() == system_a
    assert git(root, "status", "--porcelain") == ""
    assert git(root, "log", "-1", "--format=%s").startswith("rollback to ")
    assert committed_names(root) == ["extra.yaml"]


def test_rollback_refuses_an_uncommitted_extra_file_and_names_it(tmp_path: Path):
    root, machine = make(tmp_path)
    apply(root, emit=lambda _: None, **machine.kwargs())
    (root / "extra.yaml").write_text("setting: two\n")
    with pytest.raises(RecordError, match=r"modified: extra\.yaml"):
        rollback(root, emit=lambda _: None, boot_entries=machine.boot, **machine.kwargs())


def test_rollback_refuses_an_ignored_extra_file_and_names_it(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\ndevenv.local.nix\nextra.yaml\n"})
    machine = Machine(tmp_path / "m", watch=["extra.yaml"])
    apply(root, emit=lambda _: None, **machine.kwargs())
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    apply(root, emit=lambda _: None, **machine.kwargs())
    (root / "extra.yaml").write_text("setting: ignored\n")
    with pytest.raises(RecordError, match=r"ignored: extra\.yaml"):
        rollback(root, emit=lambda _: None, boot_entries=machine.boot, **machine.kwargs())


def test_rollback_still_runs_when_the_watch_list_cannot_be_read(tmp_path: Path):
    root, machine = make(tmp_path)
    apply(root, emit=lambda _: None, **machine.kwargs())
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    apply(root, emit=lambda _: None, **machine.kwargs())
    machine.eval_result = Result(2, "", "error: the workspace does not evaluate\n")
    said: list[str] = []
    rollback(root, emit=said.append, boot_entries=machine.boot, **machine.kwargs())
    assert any(line.startswith("warning: cannot read vendomat.watch") for line in said)
    assert git(root, "log", "-1", "--format=%s").startswith("rollback to ")


def test_boot_only_reads_no_watch_list(tmp_path: Path):
    root, machine = make(tmp_path)
    apply(root, emit=lambda _: None, **machine.kwargs())
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    apply(root, emit=lambda _: None, **machine.kwargs())
    machine.evals.clear()
    rollback(root, boot_only=True, emit=lambda _: None, boot_entries=machine.boot, **machine.kwargs())
    assert machine.evals == []


# --- the paths -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["", "/etc/passwd", "../outside.yaml", "a/../../outside.yaml", "a//b", "./extra.yaml", "a/", ".git/config",
     ":(top)extra.yaml", "*.yaml", "dir/?.yaml", "a[1].yaml", "back\\slash", "new\nline"],
)  # fmt: skip
def test_a_path_that_leaves_the_workspace_or_is_not_a_plain_file_is_refused(tmp_path: Path, path: str):
    with pytest.raises(WorkspaceError, match="not a file path below the workspace root"):
        check_watch_path(tmp_path, path)


def test_a_symlink_that_leaves_the_workspace_is_refused(tmp_path: Path):
    outside = tmp_path / "outside.yaml"
    outside.write_text("x\n")
    root = tmp_path / "ws"
    root.mkdir()
    (root / "link.yaml").symlink_to(outside)
    (root / "dir").mkdir()
    with pytest.raises(WorkspaceError, match="leads out of the workspace"):
        check_watch_path(root, "link.yaml")
    with pytest.raises(WorkspaceError, match="is a directory"):
        check_watch_path(root, "dir")


def test_good_paths_extend_the_fixed_four_without_repeats(tmp_path: Path):
    assert extend_watched(tmp_path, []) == WATCHED
    got = extend_watched(tmp_path, ["basix.yaml", "sub/dir/a b.yaml", "devenv.nix", "basix.yaml"])
    assert got == (*WATCHED, "basix.yaml", "sub/dir/a b.yaml")


def test_apply_refuses_a_path_outside_the_workspace_before_any_build(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m", watch=["../outside.yaml"])
    with pytest.raises(RecordError, match=r"'\.\./outside\.yaml' is not a file path below the workspace root") as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 2
    assert machine.calls == []


def test_a_bad_eval_output_is_a_fault(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.eval_result = Result(0, json.dumps({"vendomat.watch": "extra.yaml"}))
    with pytest.raises(RecordError, match="printed no list of paths"):
        watch_paths(root, machine.run)
    machine.eval_result = Result(0, "not json")
    with pytest.raises(RecordError, match="printed no JSON"):
        watch_paths(root, machine.run)


# --- the first fault line first (VMT-281) --------------------------------------------------------------

TRACE = """\
error:
       … while evaluating the attribute 'machines.basix.build.nixos'
         at /nix/store/aaa-source/devenv/machines.nix:41:7:
       … from call site
         at /nix/store/aaa-source/entry/devenv.nix:88:13:
       … while calling the 'throw' builtin
         at /nix/store/aaa-source/lib/basix.nix:7:3:

       error: basix.yaml:18:9: machines.basix.capabilities[0]: unknown capability "browsr" (known: remote-login)
"""


@pytest.fixture(autouse=True)
def _log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


def test_a_failed_build_prints_the_fault_line_first_and_keeps_the_full_trace(tmp_path: Path):
    machine = Machine(tmp_path / "m")
    run = machine.run

    def failing(argv, **kw):
        if list(argv)[1:2] == ["build"]:
            return Result(2, "", TRACE)
        return run(argv, **kw)

    root = make_workspace(tmp_path / "ws")
    with pytest.raises(RecordError) as info:
        build_toplevel(root, "box", failing)
    lines = str(info.value).splitlines()
    assert (
        lines[0] == 'basix.yaml:18:9: machines.basix.capabilities[0]: unknown capability "browsr" (known: remote-login)'
    )
    assert lines[-1].startswith("devenv build machines.box.build.nixos failed (exit 2)")
    log = Path(lines[-1].split("the full trace is in ")[1])
    assert log.read_text().count("\n") >= len(TRACE.splitlines())
    assert info.value.code == 2


def test_apply_stops_at_a_workspace_fault_with_its_first_line_first(tmp_path: Path):
    root, machine = make(tmp_path)
    machine.eval_result = Result(2, "", TRACE)
    with pytest.raises(RecordError) as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    first = str(info.value).splitlines()[0]
    assert first.startswith("basix.yaml:18:9: machines.basix.capabilities[0]: unknown capability")
    assert machine.calls == []
    assert git(root, "status", "--porcelain") == ""


def test_a_long_failure_without_a_fault_line_is_cut(tmp_path: Path):
    noise = "error: line 1\n" + "\n".join(f"detail {n}" for n in range(100))
    root = make_workspace(tmp_path / "ws")
    with pytest.raises(RecordError) as info:
        build_toplevel(root, "box", lambda argv, **kw: Result(1, "", noise))
    lines = str(info.value).splitlines()
    assert lines[0] == "line 1"
    assert any(line.startswith("... (") and "more lines)" in line for line in lines)
    assert len(lines) <= 42


# --- a module that predates R62 (v0.11.2) --------------------------------------------------------------

# The text is a recording of devenv 2.4.0 (the VM run 20261016T144016Z-503c03d7b4fe). The opt-in test
# `test_catalog_devenv.py::test_a_workspace_without_the_module_gives_the_error_that_apply_treats_as_missing`
# checks it against the pinned devenv, because `test:full` cannot run devenv (it needs the network).
MISSING = (
    "  × Failed to get attribute 'devenv.config.vendomat.watch': attribute `devenv.config.vendomat.watch` not found\n"
)
SYNTAX = "       at /ws/devenv.nix:1:13:\nerror: syntax error, unexpected end of file\n"


def test_a_missing_watch_attribute_means_the_four_fixed_files(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.eval_result = Result(1, "", MISSING)
    assert watch_paths(root, machine.run) == WATCHED
    (root / "devenv.nix").write_text("{ changed = true; }\n")
    said: list[str] = []
    apply(root, emit=said.append, **machine.kwargs())
    assert committed_names(root) == ["devenv.nix"]
    assert machine.calls[0][1:] == ["build", "machines.box.build.nixos"]
    assert said == [] or not any("watch" in line for line in said)


def test_a_syntax_error_stops_apply_with_the_first_line_first(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.eval_result = Result(1, "", SYNTAX)
    with pytest.raises(RecordError) as info:
        apply(root, emit=lambda _: None, **machine.kwargs())
    assert info.value.code == 2
    first = str(info.value).splitlines()
    assert first[0] == "syntax error, unexpected end of file"
    assert first[1].endswith("devenv.nix:1:13")
    assert machine.calls == []


def test_another_exit_code_with_the_missing_text_is_still_a_fault(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    machine = Machine(tmp_path / "m")
    machine.eval_result = Result(2, "", MISSING)
    with pytest.raises(RecordError):
        watch_paths(root, machine.run)

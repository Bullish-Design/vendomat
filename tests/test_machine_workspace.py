"""The workspace side of `apply` and `rollback`: dirty detection and the restore (R30, R43)."""

from __future__ import annotations

from pathlib import Path

import pytest
from machinesim import commit_file, git, make_workspace

from vendomat import workspace
from vendomat.record import RecordError


def statuses(root: Path) -> dict[str, str]:
    return {change.path: change.status.strip() for change in workspace.watched_changes(root)}


def make_subdirectory_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """A repository whose workspace is its subdirectory `proj`. The top holds a `devenv.nix` of its own."""
    top = make_workspace(tmp_path / "repo")
    sub = top / "proj"
    sub.mkdir()
    for name, text in {"vendomat.yaml": "machines:\n  box: {}\n", "devenv.lock": "{}\n", "devenv.nix": "{ }\n"}.items():
        (sub / name).write_text(text)
    git(top, "add", "-A")
    git(top, "commit", "--quiet", "-m", "workspace in a subdirectory")
    return top, sub


def test_a_clean_workspace_has_no_changes(tmp_path: Path):
    assert workspace.watched_changes(make_workspace(tmp_path / "ws")) == []


@pytest.mark.parametrize("name", ["vendomat.yaml", "devenv.lock", "devenv.nix"])
def test_an_edit_to_a_watched_file_is_a_change(tmp_path: Path, name: str):
    root = make_workspace(tmp_path / "ws")
    (root / name).write_text("changed\n")
    assert statuses(root) == {name: "M"}


def test_a_staged_edit_is_a_change(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    git(root, "add", "devenv.nix")
    assert statuses(root) == {"devenv.nix": "M"}


def test_a_deleted_watched_file_is_a_change(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "devenv.lock").unlink()
    assert statuses(root) == {"devenv.lock": "D"}


def test_an_untracked_hatch_file_is_a_change(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\n"})
    (root / "devenv.local.nix").write_text("{ }\n")
    assert statuses(root) == {"devenv.local.nix": "??"}


def test_an_ignored_hatch_file_that_exists_is_a_change(tmp_path: Path):
    # devenv.local.nix is ignored by the template. A copy on this machine reaches no other clone.
    root = make_workspace(tmp_path / "ws")
    assert workspace.watched_changes(root) == []
    (root / "devenv.local.nix").write_text("{ }\n")
    assert statuses(root) == {"devenv.local.nix": "!!"}
    assert workspace.watched_changes(root)[0].text() == "ignored: devenv.local.nix"


def test_an_edit_to_another_file_is_no_change(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "notes.txt").write_text("two\n")
    (root / "scratch.txt").write_text("new\n")
    assert workspace.watched_changes(root) == []


def test_head_and_resolve_give_full_ids_and_an_unknown_name_is_a_refusal(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    assert len(first) == 40 and workspace.resolve(root, "HEAD") == first
    second = commit_file(root, "notes.txt", "two\n", "second")
    assert workspace.resolve(root, second[:10]) == second
    with pytest.raises(RecordError, match="unknown commit nope") as info:
        workspace.resolve(root, "nope")
    assert info.value.code == 1
    assert workspace.has_commit(root, first) and not workspace.has_commit(root, "f" * 40)
    assert workspace.short(root, first) == first[:12]


def test_a_directory_that_is_not_a_repository_has_no_head(tmp_path: Path):
    (tmp_path / "plain").mkdir()
    with pytest.raises(RecordError, match="not a Git repository"):
        workspace.head(tmp_path / "plain")


def test_the_root_is_the_nearest_directory_with_a_workspace_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / "sub" / "deeper").mkdir(parents=True)
    assert workspace.find_root(root / "sub" / "deeper") == root.resolve()
    with pytest.raises(RecordError) as info:
        workspace.find_root(tmp_path / "elsewhere-that-does-not-exist")
    assert info.value.code == 3


def test_restore_returns_the_whole_tree_to_an_earlier_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(root, "notes.txt", "two\n", "notes")
    workspace.restore(root, first)
    assert (root / "devenv.nix").read_text() == "{ }\n"
    assert (root / "notes.txt").read_text() == "one\n"  # R55: not only the watched files
    commit = workspace.commit_restore(root, "rollback to x")
    assert git(root, "log", "-1", "--format=%s") == "rollback to x"
    assert commit == workspace.head(root)
    assert git(root, "status", "--porcelain") == ""
    assert git(root, "diff", first, "HEAD") == ""


def test_restore_removes_a_file_that_the_target_lacks(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\n"})
    first = workspace.head(root)
    commit_file(root, "devenv.local.nix", "{ }\n", "add local")
    (root / "nixos").mkdir()
    commit_file(root, "nixos/x.nix", "{ }\n", "add module")
    workspace.restore(root, first)
    assert not (root / "devenv.local.nix").exists() and not (root / "nixos" / "x.nix").exists()
    workspace.commit_restore(root, "rollback to x")
    assert git(root, "ls-files", "devenv.local.nix", "nixos") == ""
    assert git(root, "diff", first, "HEAD") == ""


def test_a_restore_that_changes_nothing_still_makes_a_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = workspace.head(root)
    workspace.restore(root, before)
    after = workspace.commit_restore(root, "rollback to x")
    assert after != before and git(root, "rev-list", "--count", "HEAD") == "2"


def test_a_restore_is_scoped_to_the_workspace_root(tmp_path: Path):
    # The workspace is the subdirectory `proj`. Files outside it keep their state, staged or not.
    top, sub = make_subdirectory_workspace(tmp_path)
    first = workspace.head(sub)
    commit_file(sub, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(sub, "extra.nix", "{ }\n", "extra")
    commit_file(top, "notes.txt", "two\n", "outside")
    (top / "notes.txt").write_text("staged outside\n")
    git(top, "add", "notes.txt")
    workspace.restore(sub, first)
    assert (sub / "devenv.nix").read_text() == "{ }\n" and not (sub / "extra.nix").exists()
    assert (top / "notes.txt").read_text() == "staged outside\n"
    workspace.commit_restore(sub, "rollback to first")
    assert sorted(git(top, "show", "--format=", "--name-only", "HEAD").splitlines()) == [
        "proj/devenv.nix",
        "proj/extra.nix",
    ]
    assert git(top, "status", "--porcelain") == "M  notes.txt"


def test_a_restore_does_not_commit_an_unrelated_staged_file_outside_the_root(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    first = workspace.head(sub)
    commit_file(sub, "devenv.nix", "{ x = 2; }\n", "second")
    (top / "notes.txt").write_text("staged elsewhere\n")
    git(top, "add", "notes.txt")
    workspace.restore(sub, first)
    workspace.commit_restore(sub, "rollback to first")
    assert git(top, "show", "--format=", "--name-only", "HEAD").splitlines() == ["proj/devenv.nix"]
    assert git(top, "status", "--porcelain") == "M  notes.txt"


def test_undo_restore_returns_to_head(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(root, "extra.txt", "x\n", "extra")
    workspace.restore(root, first)
    assert workspace.watched_changes(root) and not (root / "extra.txt").exists()
    workspace.undo_restore(root)
    assert workspace.tree_changes(root) == []
    assert (root / "devenv.nix").read_text() == "{ x = 2; }\n" and (root / "extra.txt").exists()


def test_the_diff_shows_the_change_to_the_whole_tree(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(root, "notes.txt", "two\n", "notes")
    text = workspace.diff_text(root, first)
    assert "devenv.nix" in text and "x = 2" in text and "notes.txt" in text


def test_a_workspace_in_a_subdirectory_sees_its_own_changes_and_not_those_of_the_top(tmp_path: Path):
    # `git status` names paths from the repository top. R43 needs the change of the workspace itself.
    top, sub = make_subdirectory_workspace(tmp_path)
    (sub / "devenv.nix").write_text("{ x = 1; }\n")
    assert statuses(sub) == {"devenv.nix": "M"}
    git(top, "checkout", "--", "proj/devenv.nix")
    (top / "devenv.nix").write_text("{ top = 1; }\n")  # a watched name outside the workspace
    assert statuses(sub) == {}


def test_a_subdirectory_workspace_commits_only_its_own_watched_files(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    (sub / "devenv.nix").write_text("{ x = 1; }\n")
    (top / "devenv.nix").write_text("{ top = 1; }\n")
    git(top, "add", "devenv.nix")
    commit = workspace.commit_watched(sub)
    assert commit == git(top, "rev-parse", "HEAD")
    assert git(top, "show", "--format=", "--name-only", "HEAD").splitlines() == ["proj/devenv.nix"]
    assert git(top, "status", "--porcelain") == "M  devenv.nix"


def test_a_staged_rename_between_watched_files_reports_both_names(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    git(root, "mv", "devenv.nix", "devenv.local.nix")
    assert git(root, "status", "--porcelain").startswith("R ")  # the case under test
    changes = workspace.watched_changes(root)
    found = {(change.path, change.status.strip()) for change in changes}
    assert found == {("devenv.local.nix", "R"), ("devenv.nix", "R")}
    commit = workspace.commit_watched(root)
    assert commit == git(root, "rev-parse", "HEAD")
    assert git(root, "status", "--porcelain") == ""


def test_a_subdirectory_rename_reports_both_names_without_the_prefix(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    git(top, "mv", "proj/devenv.nix", "proj/devenv.local.nix")
    assert {change.path for change in workspace.watched_changes(sub)} == {"devenv.nix", "devenv.local.nix"}
    commit = workspace.commit_watched(sub)
    assert commit == git(top, "rev-parse", "HEAD")
    shown = git(top, "show", "--format=", "--name-status", "HEAD")
    assert shown.startswith("R100\tproj/devenv.nix\tproj/devenv.local.nix")
    assert git(top, "status", "--porcelain") == ""


@pytest.mark.parametrize("case", ["staged-then-reverted", "added-then-deleted"])
def test_a_watched_path_that_equals_head_makes_no_commit(tmp_path: Path, case: str):
    # `git commit --only` exits 1 when nothing differs from HEAD. The build has run by then.
    root = make_workspace(tmp_path / "ws")
    before = workspace.head(root)
    if case == "staged-then-reverted":
        (root / "devenv.nix").write_text("{ x = 1; }\n")
        git(root, "add", "devenv.nix")
        (root / "devenv.nix").write_text("{ }\n")
        assert git(root, "status", "--porcelain") == "MM devenv.nix"
    else:
        (root / "devenv.local.nix").write_text("{ }\n")
        git(root, "add", "-f", "devenv.local.nix")
        (root / "devenv.local.nix").unlink()
        assert git(root, "status", "--porcelain") == "AD devenv.local.nix"
    assert workspace.watched_changes(root)  # the status lists the path
    assert workspace.commit_watched(root) == before
    assert workspace.head(root) == before


def test_the_fingerprint_changes_with_any_file_of_the_tree_and_with_head(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.fingerprint(root)
    (root / "notes.txt").write_text("changed\n")  # R55: a tracked file that is not watched counts
    assert workspace.fingerprint(root) != first
    (root / "notes.txt").write_text("one\n")
    assert workspace.fingerprint(root) == first
    (root / "new.txt").write_text("new\n")  # a new file counts
    assert workspace.fingerprint(root) != first
    (root / "new.txt").unlink()
    (root / ".devenv").mkdir()
    (root / ".devenv" / "state").write_text("cache\n")  # an ignored file does not count
    assert workspace.fingerprint(root) == first
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    assert workspace.fingerprint(root) != first
    (root / "devenv.nix").write_text("{ }\n")
    assert workspace.fingerprint(root) == first
    commit_file(root, "notes.txt", "two\n", "second")
    assert workspace.fingerprint(root)[0] != first[0]


def test_the_fingerprint_of_a_subdirectory_workspace_covers_only_its_own_files(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    first = workspace.fingerprint(sub)
    (top / "notes.txt").write_text("outside\n")
    assert workspace.fingerprint(sub) == first
    (sub / "devenv.lock").write_text("changed\n")
    assert workspace.fingerprint(sub) != first


def test_tree_changes_lists_only_the_changes_of_the_workspace_directory(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    (top / "notes.txt").write_text("changed outside\n")
    (top / "new-outside.txt").write_text("x\n")
    assert workspace.tree_changes(sub) == []
    (sub / "devenv.nix").write_text("{ x = 1; }\n")
    (sub / "new.nix").write_text("{ }\n")
    got = {change.path: change.status for change in workspace.tree_changes(sub)}
    assert got == {"devenv.nix": " M", "new.nix": "??"}


def test_tree_changes_skips_ignored_files_and_gives_a_rename_as_two_names(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / ".devenv").mkdir()
    (root / ".devenv" / "state").write_text("cache\n")
    assert workspace.tree_changes(root) == []
    git(root, "mv", "notes.txt", "moved.txt")
    got = {change.path: change.status for change in workspace.tree_changes(root)}
    assert got == {"notes.txt": "D ", "moved.txt": "A "}
    assert [c.path for c in workspace.uncommitted_changes(root, skip=("moved.txt",))] == ["notes.txt"]


def test_the_key_file_is_apply_output_only_with_a_key_source(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    source = tmp_path / "key.pub"
    assert workspace.written_key_file(root, "box", source) is None
    source.write_text("box:AAAA=\n")
    assert workspace.written_key_file(root, "box", source) == ".machines/box/cache-key.pub"


def test_commit_watched_takes_the_extra_paths_that_have_a_change_and_no_other_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    (root / ".machines" / "box").mkdir(parents=True)
    (root / ".machines" / "box" / "cache-key.pub").write_text("box:AAAA=\n")
    (root / "stray.txt").write_text("x\n")
    key = ".machines/box/cache-key.pub"
    commit = workspace.commit_watched(root, extra=(key,))
    assert commit == git(root, "rev-parse", "HEAD")
    assert git(root, "show", "--format=", "--name-only", "HEAD") == key
    assert git(root, "status", "--porcelain") == "?? stray.txt"
    assert workspace.commit_watched(root, extra=(key,)) == commit  # no change: no second commit


def test_restore_and_diff_text_leave_a_kept_path_alone(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = git(root, "rev-parse", "HEAD")
    (root / "notes.txt").write_text("two\n")
    (root / "keep.txt").write_text("kept\n")
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "second")
    assert "keep.txt" not in workspace.diff_text(root, first, ("keep.txt",))
    workspace.restore(root, first, ("keep.txt",))
    assert (root / "notes.txt").read_text() == "one\n"
    assert (root / "keep.txt").read_text() == "kept\n"
    assert git(root, "status", "--porcelain") == "M  notes.txt"

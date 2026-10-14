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


def test_restore_returns_the_watched_files_to_an_earlier_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(root, "notes.txt", "two\n", "notes")
    workspace.restore(root, first, exact=False)
    assert (root / "devenv.nix").read_text() == "{ }\n"
    assert (root / "notes.txt").read_text() == "two\n"  # not a watched file
    commit = workspace.commit_restore(root, "rollback to x")
    assert git(root, "log", "-1", "--format=%s") == "rollback to x"
    assert commit == workspace.head(root)
    assert git(root, "status", "--porcelain") == ""


def test_restore_removes_a_watched_file_that_the_target_lacks(tmp_path: Path):
    root = make_workspace(tmp_path / "ws", {".gitignore": ".devenv*\n"})
    first = workspace.head(root)
    commit_file(root, "devenv.local.nix", "{ }\n", "add local")
    workspace.restore(root, first, exact=False)
    assert not (root / "devenv.local.nix").exists()
    workspace.commit_restore(root, "rollback to x")
    assert git(root, "ls-files", "devenv.local.nix") == ""


def test_exact_restores_every_tracked_file_and_removes_added_ones(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "notes.txt", "two\n", "notes")
    commit_file(root, "extra.txt", "x\n", "extra")
    workspace.restore(root, first, exact=True)
    assert (root / "notes.txt").read_text() == "one\n"
    assert not (root / "extra.txt").exists()
    workspace.commit_restore(root, "rollback to x", exact=True)
    assert git(root, "diff", first, "HEAD") == ""


def test_a_restore_that_changes_nothing_still_makes_a_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = workspace.head(root)
    workspace.restore(root, before, exact=False)
    after = workspace.commit_restore(root, "rollback to x")
    assert after != before and git(root, "rev-list", "--count", "HEAD") == "2"


def test_a_watched_restore_does_not_commit_an_unrelated_staged_file(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    (root / "notes.txt").write_text("staged elsewhere\n")
    git(root, "add", "notes.txt")
    workspace.restore(root, first, exact=False)
    workspace.commit_restore(root, "rollback to first")
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == ["devenv.nix"]
    assert git(root, "status", "--porcelain") == "M  notes.txt"


def test_undo_restore_returns_to_head(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    workspace.restore(root, first, exact=False)
    assert workspace.watched_changes(root)
    workspace.undo_restore(root, exact=False)
    assert workspace.watched_changes(root) == [] and (root / "devenv.nix").read_text() == "{ x = 2; }\n"


def test_the_diff_shows_the_change_and_stays_off_the_other_files(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.head(root)
    commit_file(root, "devenv.nix", "{ x = 2; }\n", "second")
    commit_file(root, "notes.txt", "two\n", "notes")
    text = workspace.diff_text(root, first, exact=False)
    assert "devenv.nix" in text and "x = 2" in text and "notes.txt" not in text
    assert "notes.txt" in workspace.diff_text(root, first, exact=True)


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


def test_the_fingerprint_changes_with_a_watched_file_and_with_head(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    first = workspace.fingerprint(root)
    (root / "notes.txt").write_text("not watched\n")
    assert workspace.fingerprint(root) == first
    (root / "devenv.nix").write_text("{ x = 1; }\n")
    assert workspace.fingerprint(root) != first
    (root / "devenv.nix").write_text("{ }\n")
    assert workspace.fingerprint(root) == first
    commit_file(root, "notes.txt", "two\n", "second")
    assert workspace.fingerprint(root)[0] != first[0]


def test_exact_lists_only_the_tracked_changes_of_the_workspace_directory(tmp_path: Path):
    top, sub = make_subdirectory_workspace(tmp_path)
    (top / "notes.txt").write_text("changed outside\n")
    assert workspace.tree_changes(sub) == []
    (sub / "devenv.nix").write_text("{ x = 1; }\n")
    assert workspace.tree_changes(sub) == [" M proj/devenv.nix"]

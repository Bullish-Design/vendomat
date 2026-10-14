"""The workspace side of `apply` and `rollback`: dirty detection and the restore (R30, R43)."""

from __future__ import annotations

from pathlib import Path

import pytest
from machinesim import commit_file, git, make_workspace

from vendomat import workspace
from vendomat.record import RecordError


def statuses(root: Path) -> dict[str, str]:
    return {change.path: change.status.strip() for change in workspace.watched_changes(root)}


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
    workspace.commit_restore(root, "rollback to x")
    assert git(root, "diff", first, "HEAD") == ""


def test_a_restore_that_changes_nothing_still_makes_a_commit(tmp_path: Path):
    root = make_workspace(tmp_path / "ws")
    before = workspace.head(root)
    workspace.restore(root, before, exact=False)
    after = workspace.commit_restore(root, "rollback to x")
    assert after != before and git(root, "rev-list", "--count", "HEAD") == "2"


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

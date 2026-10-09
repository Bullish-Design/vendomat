"""The collection post-receive hook (STORE-023).

Each test pushes a tag into a real non-bare repository over `file://`, so Git runs the hooks the
way `git daemon`'s sibling, SSH `receive-pack`, does. No Nix, no network.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from vendomat.store import refresh_collection

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "collection-post-receive"

#: The rule that `scripts/collection-add` in nix-meta installs. The hook under test sits beside it.
PRE_RECEIVE = """#!/bin/sh
zero=0000000000000000000000000000000000000000
while read old new ref; do
  case "$ref" in
    refs/tags/*)
      [ "$old" = "$zero" ] || { echo "collection: $ref exists; releases are immutable" >&2; exit 1; } ;;
    *)
      echo "collection: only release tags are accepted, not $ref" >&2; exit 1 ;;
  esac
done
"""


@pytest.fixture(autouse=True)
def _git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture
def collection(tmp_path: Path) -> Path:
    """A collection repository as `collection-add` makes it, plus the post-receive hook."""
    repo = tmp_path / "vendor" / "devman"
    repo.mkdir(parents=True)
    git(repo, "init", "--quiet", "--initial-branch=main")
    hooks = repo / ".git" / "hooks"
    (hooks / "pre-receive").write_text(PRE_RECEIVE)
    shutil.copy(HOOK, hooks / "post-receive")
    for name in ("pre-receive", "post-receive"):
        (hooks / name).chmod(0o755)
    (repo / ".git" / "git-daemon-export-ok").write_text("")
    return repo


@pytest.fixture
def author(tmp_path: Path) -> Path:
    work = tmp_path / "author"
    work.mkdir()
    git(work, "init", "--quiet", "--initial-branch=main")
    return work


def release(author: Path, tag: str, text: str | None = None) -> None:
    (author / "README").write_text(text or f"{tag}\n")
    git(author, "add", "-A")
    git(author, "commit", "--quiet", "-m", tag)
    git(author, "tag", "-a", tag, "-m", tag)


def push(author: Path, collection: Path, *refs: str) -> subprocess.CompletedProcess[str]:
    return git(author, "push", f"file://{collection}", *refs, check=False)


def head_tag(repo: Path) -> str:
    return git(repo, "describe", "--tags", "--exact-match", "HEAD").stdout.strip()


def test_the_hook_file_is_executable_shell():
    assert HOOK.stat().st_mode & 0o111
    assert subprocess.run(["sh", "-n", str(HOOK)]).returncode == 0


def test_a_first_tag_push_fills_the_empty_unborn_repository(collection: Path, author: Path):
    release(author, "v0.7.0", "seven\n")

    done = push(author, collection, "refs/tags/v0.7.0")

    assert done.returncode == 0, done.stderr
    assert "working tree now shows v0.7.0" in done.stderr
    assert head_tag(collection) == "v0.7.0"
    assert (collection / "README").read_text() == "seven\n"
    assert git(collection, "status", "--porcelain").stdout == ""


def test_a_newer_tag_moves_the_tree_and_an_older_tag_does_not(collection: Path, author: Path):
    release(author, "v0.9.0", "nine\n")
    push(author, collection, "refs/tags/v0.9.0")
    release(author, "v0.10.0", "ten\n")
    assert push(author, collection, "refs/tags/v0.10.0").returncode == 0
    assert (collection / "README").read_text() == "ten\n"

    # Version order, not push order: v0.8.0 is older than v0.10.0, so the tree stays.
    git(author, "checkout", "--quiet", "-b", "side", "v0.9.0")
    release(author, "v0.8.0", "eight\n")
    assert push(author, collection, "refs/tags/v0.8.0").returncode == 0
    assert head_tag(collection) == "v0.10.0"
    assert (collection / "README").read_text() == "ten\n"


def test_a_dirty_tree_is_left_alone_and_the_push_still_succeeds(collection: Path, author: Path):
    release(author, "v1.0.0", "one\n")
    push(author, collection, "refs/tags/v1.0.0")
    (collection / "README").write_text("my edit\n")
    release(author, "v1.1.0", "two\n")

    done = push(author, collection, "refs/tags/v1.1.0")

    assert done.returncode == 0, done.stderr
    assert "uncommitted changes" in done.stderr
    assert (collection / "README").read_text() == "my edit\n"
    assert head_tag(collection) == "v1.0.0"
    assert "refs/tags/v1.1.0" in git(collection, "for-each-ref").stdout


def test_a_failed_checkout_never_fails_the_push(collection: Path, author: Path):
    release(author, "v1.0.0")
    push(author, collection, "refs/tags/v1.0.0")
    release(author, "v1.1.0")
    (collection / ".git" / "index.lock").write_text("")

    done = push(author, collection, "refs/tags/v1.1.0")

    assert done.returncode == 0, done.stderr
    assert "could not check out v1.1.0" in done.stderr
    assert "refs/tags/v1.1.0" in git(collection, "for-each-ref").stdout


def test_a_refused_branch_push_changes_neither_refs_nor_tree(collection: Path, author: Path):
    release(author, "v1.0.0", "one\n")
    push(author, collection, "refs/tags/v1.0.0")
    before = git(collection, "for-each-ref").stdout

    done = push(author, collection, "refs/heads/main")

    assert done.returncode != 0
    assert "only release tags are accepted" in done.stderr
    assert git(collection, "for-each-ref").stdout == before
    assert (collection / "README").read_text() == "one\n"


def test_the_hook_leaves_tags_alone_and_agrees_with_the_sync_refresh(collection: Path, author: Path):
    release(author, "v0.10.0")
    release(author, "v0.9.0")
    push(author, collection, "refs/tags/v0.9.0", "refs/tags/v0.10.0")
    tags_before = git(collection, "for-each-ref", "refs/tags").stdout

    [outcome] = refresh_collection(collection.parent)

    assert outcome.status == "unchanged"
    assert head_tag(collection) == "v0.10.0"
    assert git(collection, "for-each-ref", "refs/tags").stdout == tags_before


def test_a_bare_repository_is_ignored(tmp_path: Path, author: Path):
    bare = tmp_path / "bare.git"
    bare.mkdir()
    git(bare, "init", "--bare", "--quiet")
    shutil.copy(HOOK, bare / "hooks" / "post-receive")
    (bare / "hooks" / "post-receive").chmod(0o755)
    release(author, "v1.0.0")

    done = push(author, bare, "refs/tags/v1.0.0")

    assert done.returncode == 0, done.stderr
    assert "working tree" not in done.stderr

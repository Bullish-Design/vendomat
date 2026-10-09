"""`vendomat sync` store work: `keep`, `mirror`, and the collection refresh (STORE-009, STORE-013).

Every repository here is a local bare repository, and every URL is `file://`. No test needs
Nix, a network, or a daemon. The `git://` path is in `test_sync_nix.py`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vendomat import store
from vendomat.cli import app
from vendomat.registry import parse_registry
from vendomat.store import Outcome, exit_code, refresh_collection, sync_store

runner = CliRunner()


@pytest.fixture(autouse=True)
def _git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A fixed identity, and no user or system Git configuration."""
    for key, value in {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("VENDOMAT_SOURCE_ROOT", raising=False)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


class Upstream:
    """A bare repository with a work tree beside it. `release` commits, tags, and pushes the tag."""

    def __init__(self, base: Path, name: str, *, with_branch: bool = True) -> None:
        self.bare = base / name
        self.work = base / f"{name}-work"
        self.bare.mkdir(parents=True)
        git(self.bare, "init", "--bare", "--quiet", "--initial-branch=main")
        self.work.mkdir(parents=True)
        git(self.work, "init", "--quiet", "--initial-branch=main")
        git(self.work, "remote", "add", "origin", f"file://{self.bare}")
        self.with_branch = with_branch

    @property
    def url(self) -> str:
        return f"file://{self.bare}"

    def release(self, tag: str, text: str | None = None) -> None:
        (self.work / "README").write_text(text or f"{tag}\n")
        git(self.work, "add", "-A")
        git(self.work, "commit", "--quiet", "-m", f"release {tag}")
        git(self.work, "tag", "-a", tag, "-m", tag)
        refs = [f"refs/tags/{tag}"] + (["refs/heads/main"] if self.with_branch else [])
        git(self.work, "push", "--quiet", "origin", *refs)


def registry(text: str):
    return parse_registry(text, "vendomat.toml")


def forge_registry(forge: Path, entries: str) -> str:
    return f'[forge]\nurl = "file://{forge}"\n\n[inputs]\n{entries}\n'


def head_tag(clone: Path) -> str:
    return git(clone, "describe", "--tags", "--exact-match", "HEAD")


def detached(clone: Path) -> bool:
    return subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=clone, capture_output=True).returncode != 0


@pytest.fixture
def forge(tmp_path: Path) -> Path:
    return tmp_path / "forge"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "vendor"


# --- keep: first clone, fetch, rerun ---------------------------------------------------------


def test_keep_clones_a_forge_entry_and_shows_the_pinned_tag(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0", "one\n")
    up.release("v1.1.0", "two\n")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert (outcome.status, outcome.ok) == ("cloned", True)
    clone = root / "lib-a"
    assert head_tag(clone) == "v1.0.0"
    assert detached(clone)
    assert (clone / "README").read_text() == "one\n"
    assert git(clone, "remote", "get-url", "origin") == up.url


def test_keep_uses_the_repo_key_for_the_directory_and_the_url(forge: Path, root: Path):
    up = Upstream(forge, "loci.nvim")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'loci-nvim = { repo = "loci.nvim", ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.ok, outcome.line()
    assert (root / "loci.nvim" / "README").is_file()
    assert not (root / "loci-nvim").exists()


def test_keep_fetches_a_new_tag_and_moves_the_tree_to_it(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0", "one\n")
    sync_store(registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }')), root=root)
    up.release("v1.1.0", "two\n")

    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.1.0", keep = true }'))
    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "updated"
    assert "1 new tag" in outcome.detail
    assert head_tag(root / "lib-a") == "v1.1.0"
    assert (root / "lib-a" / "README").read_text() == "two\n"


def test_keep_rerun_changes_nothing(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))
    sync_store(reg, root=root)
    before = git(root / "lib-a", "rev-parse", "HEAD"), git(root / "lib-a", "for-each-ref")

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "unchanged"
    assert (git(root / "lib-a", "rev-parse", "HEAD"), git(root / "lib-a", "for-each-ref")) == before


def test_keep_leaves_a_branch_checkout_detached_at_the_tag_when_the_tree_is_clean(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))
    sync_store(reg, root=root)
    git(root / "lib-a", "checkout", "--quiet", "-b", "work")

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "updated"
    assert detached(root / "lib-a")
    assert head_tag(root / "lib-a") == "v1.0.0"


def test_keep_clones_a_remote_that_holds_tags_and_no_branch(forge: Path, root: Path):
    """The collection looks like this: `devman` has a tag and no branch."""
    up = Upstream(forge, "devman", with_branch=False)
    up.release("v0.7.0")
    reg = registry(forge_registry(forge, 'devman = { ref = "refs/tags/v0.7.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.ok, outcome.line()
    assert head_tag(root / "devman") == "v0.7.0"
    assert (root / "devman" / "README").is_file()


# --- keep: third-party entries ---------------------------------------------------------------


def test_keep_clones_a_third_party_entry_from_its_own_url(tmp_path: Path, root: Path):
    up = Upstream(tmp_path / "upstream", "telescope.nvim")
    up.release("v0.1.8")
    text = f'[inputs]\ntelescope = {{ url = "git+file://{up.bare}", ref = "refs/tags/v0.1.8", keep = true }}\n'

    [outcome] = sync_store(registry(text), root=root)

    assert outcome.ok, outcome.line()
    assert head_tag(root / "telescope") == "v0.1.8"
    assert git(root / "telescope", "remote", "get-url", "origin") == up.url


def test_an_entry_without_keep_or_mirror_gets_no_clone(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0" }'))

    assert sync_store(reg, root=root) == []
    assert not root.exists()


# --- mirror ----------------------------------------------------------------------------------


def _mirror_registry(up: Upstream) -> str:
    return f'[inputs]\ntelescope = {{ url = "git+file://{up.bare}", ref = "refs/tags/v0.1.8", mirror = true }}\n'


def test_mirror_is_skipped_away_from_the_collection_host(tmp_path: Path, root: Path):
    up = Upstream(tmp_path / "upstream", "telescope")
    up.release("v0.1.8")

    [outcome] = sync_store(registry(_mirror_registry(up)), root=root, collection=False)

    assert outcome.status == "skipped"
    assert "mirror skipped: not the collection host" in outcome.line()
    assert outcome.ok
    assert not root.exists()


def test_mirror_copies_on_the_collection_host_without_the_marker_or_the_hook(tmp_path: Path, root: Path):
    up = Upstream(tmp_path / "upstream", "telescope")
    up.release("v0.1.8")

    outcomes = sync_store(registry(_mirror_registry(up)), root=root, collection=True)

    assert [o.status for o in outcomes] == ["cloned"]
    mirror = root / "telescope"
    assert head_tag(mirror) == "v0.1.8"
    assert not (mirror / ".git" / "git-daemon-export-ok").exists()
    assert not (mirror / ".git" / "hooks" / "pre-receive").exists()


def test_keep_and_mirror_on_one_entry_clone_once_and_name_the_skipped_mirror(tmp_path: Path, root: Path):
    up = Upstream(tmp_path / "upstream", "telescope")
    up.release("v0.1.8")
    flags = "keep = true, mirror = true"
    text = f'[inputs]\ntelescope = {{ url = "git+file://{up.bare}", ref = "refs/tags/v0.1.8", {flags} }}\n'

    outcomes = sync_store(registry(text), root=root, collection=False)

    assert [o.status for o in outcomes] == ["skipped", "cloned"]
    assert "mirror skipped: not the collection host" in outcomes[0].line()


# --- refusals and failures -------------------------------------------------------------------


def test_a_dirty_tree_is_reported_and_left_alone(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0", "one\n")
    sync_store(registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }')), root=root)
    (root / "lib-a" / "README").write_text("my edit\n")
    up.release("v1.1.0", "two\n")

    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.1.0", keep = true }'))
    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "refused"
    assert "uncommitted changes" in outcome.detail
    assert exit_code([outcome]) == 1
    assert (root / "lib-a" / "README").read_text() == "my edit\n"
    assert head_tag(root / "lib-a") == "v1.0.0"
    # Nothing was fetched either: the tree and its refs stay exactly as they were.
    assert "refs/tags/v1.1.0" not in git(root / "lib-a", "for-each-ref")


def test_an_untracked_file_also_counts_as_uncommitted(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))
    sync_store(reg, root=root)
    (root / "lib-a" / "notes.txt").write_text("x\n")

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "refused"


def test_a_directory_that_is_not_a_git_repository_is_refused_and_untouched(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    (root / "lib-a").mkdir(parents=True)
    (root / "lib-a" / "keep.txt").write_text("mine\n")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "refused"
    assert "not a Git repository" in outcome.detail
    assert exit_code([outcome]) == 1
    assert [p.name for p in (root / "lib-a").iterdir()] == ["keep.txt"]


def test_a_repository_with_no_origin_is_the_collections_own_and_is_skipped(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    own = root / "lib-a"
    own.mkdir(parents=True)
    git(own, "init", "--quiet")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "skipped"
    assert outcome.ok
    assert "no origin" in outcome.detail
    assert git(own, "tag") == ""
    assert not (own / "README").exists()


def test_an_unreachable_remote_fails_and_leaves_no_directory(forge: Path, root: Path):
    reg = registry(forge_registry(forge, 'gone = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "failed"
    assert exit_code([outcome]) == 2
    assert not (root / "gone").exists()


def test_a_fetch_from_an_unreachable_remote_fails_and_keeps_the_clone(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))
    sync_store(reg, root=root)
    moved = up.bare.with_name("lib-a-moved")
    up.bare.rename(moved)

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "failed"
    assert head_tag(root / "lib-a") == "v1.0.0"


def test_a_pinned_tag_the_remote_lacks_fails_and_names_the_tag(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v9.9.9", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "failed"
    assert "v9.9.9" in outcome.detail


def test_a_remote_with_no_tags_fails_for_the_pinned_tag(forge: Path, root: Path):
    bare = forge / "lib-a"
    bare.mkdir(parents=True)
    git(bare, "init", "--bare", "--quiet")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root)

    assert outcome.status == "failed"
    assert "v1.0.0" in outcome.detail


def test_one_bad_entry_does_not_stop_the_others_and_the_exit_code_is_not_zero(forge: Path, root: Path):
    a, c = Upstream(forge, "lib-a"), Upstream(forge, "lib-c")
    a.release("v1.0.0")
    c.release("v3.0.0")
    entries = "\n".join(
        [
            'lib-a = { ref = "refs/tags/v1.0.0", keep = true }',
            'lib-b = { ref = "refs/tags/v2.0.0", keep = true }',
            'lib-c = { ref = "refs/tags/v3.0.0", keep = true }',
        ]
    )

    outcomes = sync_store(registry(forge_registry(forge, entries)), root=root)

    assert [(o.subject, o.status) for o in outcomes] == [("lib-a", "cloned"), ("lib-b", "failed"), ("lib-c", "cloned")]
    assert exit_code(outcomes) == 2
    assert head_tag(root / "lib-a") == "v1.0.0"
    assert head_tag(root / "lib-c") == "v3.0.0"


def test_a_path_input_with_keep_is_skipped(tmp_path: Path, root: Path):
    text = '[inputs]\nlocal = { url = "path:./inputs/local", keep = true }\n'

    [outcome] = sync_store(registry(text), root=root)

    assert outcome.status == "skipped"
    assert not root.exists()


def test_an_unsafe_url_scheme_is_refused_before_git_runs(root: Path):
    text = '[inputs]\nodd = { url = "ext::true", ref = "refs/tags/v1", keep = true }\n'

    [outcome] = sync_store(registry(text), root=root)

    assert outcome.status == "refused"
    assert not root.exists()


def test_credentials_in_a_url_never_reach_the_message(root: Path):
    text = '[inputs]\nsecret = { url = "https://user:hunter2@127.0.0.1:1/x", ref = "refs/tags/v1", keep = true }\n'

    [outcome] = sync_store(registry(text), root=root)

    assert outcome.status == "failed"
    assert "hunter2" not in outcome.line()


def test_a_slow_git_call_times_out_and_is_reported(forge: Path, root: Path, monkeypatch: pytest.MonkeyPatch):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    monkeypatch.setattr(store, "NETWORK_TIMEOUT", 0.0001)

    [outcome] = sync_store(
        registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }')), root=root
    )

    assert outcome.status == "failed"
    assert "timed out" in outcome.detail


def test_git_runs_without_a_terminal_prompt():
    assert store._env()["GIT_TERMINAL_PROMPT"] == "0"


# --- dry run ---------------------------------------------------------------------------------


def test_dry_run_plans_a_clone_and_changes_nothing(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    [outcome] = sync_store(reg, root=root, dry_run=True)

    assert outcome.status == "planned"
    assert "would clone" in outcome.detail
    assert not root.exists()


def test_dry_run_plans_a_fetch_and_reports_a_dirty_tree_without_touching_either(forge: Path, root: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    reg = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))
    sync_store(reg, root=root)
    up.release("v1.1.0")
    pin = registry(forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.1.0", keep = true }'))
    tags_before = git(root / "lib-a", "for-each-ref")

    [planned] = sync_store(pin, root=root, dry_run=True)
    assert planned.status == "planned"
    assert git(root / "lib-a", "for-each-ref") == tags_before
    assert head_tag(root / "lib-a") == "v1.0.0"

    (root / "lib-a" / "README").write_text("edit\n")
    [dirty] = sync_store(pin, root=root, dry_run=True)
    assert dirty.status == "refused"
    assert (root / "lib-a" / "README").read_text() == "edit\n"


# --- the collection refresh (STORE-013) -----------------------------------------------------


def _collection_repo(root: Path, name: str, tags: list[str], *, marker: bool = True, hook: bool = False) -> Path:
    """A collection repository like `devman`: tags, no branch, unborn HEAD, no files checked out."""
    seed = Upstream(root.parent / "seeds", name, with_branch=False)
    for tag in tags:
        seed.release(tag, f"{tag}\n")
    repo = root / name
    repo.mkdir(parents=True)
    git(repo, "init", "--quiet", "--initial-branch=main")
    if tags:
        git(repo, "fetch", "--quiet", f"file://{seed.bare}", "refs/tags/*:refs/tags/*")
    if marker:
        (repo / ".git" / "git-daemon-export-ok").write_text("")
    if hook:
        (repo / ".git" / "hooks" / "pre-receive").write_text("#!/bin/sh\nexit 0\n")
    return repo


def test_refresh_checks_out_the_newest_tag_in_an_unborn_repository(root: Path):
    repo = _collection_repo(root, "devman", ["v0.7.0"])
    assert not (repo / "README").exists()

    [outcome] = refresh_collection(root)

    assert outcome.subject == "collection:devman"
    assert outcome.status == "updated"
    assert head_tag(repo) == "v0.7.0"
    assert (repo / "README").read_text() == "v0.7.0\n"
    # The branch ref stays unborn and the tags stay as they were, so what `git://` serves holds.
    assert git(repo, "tag") == "v0.7.0"
    assert subprocess.run(["git", "rev-parse", "--verify", "-q", "refs/heads/main"], cwd=repo).returncode != 0


def test_refresh_picks_the_newest_tag_by_version_order_not_by_text(root: Path):
    repo = _collection_repo(root, "lib-a", ["v0.9.0", "v0.10.0", "v0.2.0"])

    refresh_collection(root)

    assert head_tag(repo) == "v0.10.0"


def test_refresh_follows_a_newer_tag_and_is_a_no_op_on_rerun(root: Path):
    repo = _collection_repo(root, "lib-a", ["v1.0.0"])
    refresh_collection(root)
    [again] = refresh_collection(root)
    assert again.status == "unchanged"

    newer = Upstream(root.parent / "seeds2", "lib-a", with_branch=False)
    newer.release("v1.1.0", "v1.1.0\n")
    git(repo, "fetch", "--quiet", f"file://{newer.bare}", "refs/tags/*:refs/tags/*")
    [moved] = refresh_collection(root)

    assert moved.status == "updated"
    assert head_tag(repo) == "v1.1.0"


def test_refresh_does_not_touch_a_dirty_tree(root: Path):
    repo = _collection_repo(root, "lib-a", ["v1.0.0"])
    refresh_collection(root)
    (repo / "README").write_text("edit\n")
    newer = Upstream(root.parent / "seeds2", "lib-a", with_branch=False)
    newer.release("v1.1.0")
    git(repo, "fetch", "--quiet", f"file://{newer.bare}", "refs/tags/*:refs/tags/*")

    [outcome] = refresh_collection(root)

    assert outcome.status == "refused"
    assert exit_code([outcome]) == 1
    assert (repo / "README").read_text() == "edit\n"
    assert head_tag(repo) == "v1.0.0"


def test_refresh_reports_a_collection_repository_with_no_tags(root: Path):
    _collection_repo(root, "lib-a", [])

    [outcome] = refresh_collection(root)

    assert (outcome.status, outcome.detail) == ("skipped", "no release tag yet")


def test_refresh_acts_on_a_repository_with_only_the_hook(root: Path):
    repo = _collection_repo(root, "lib-a", ["v1.0.0"], marker=False, hook=True)

    [outcome] = refresh_collection(root)

    assert outcome.status == "updated"
    assert head_tag(repo) == "v1.0.0"


def test_refresh_leaves_a_repository_with_neither_marker_nor_hook_alone(root: Path):
    repo = _collection_repo(root, "pydantic", ["v2.0.0"], marker=False)
    (root / "not-a-repo").mkdir()

    assert refresh_collection(root) == []
    assert not (repo / "README").exists()


def test_refresh_dry_run_changes_no_tree(root: Path):
    repo = _collection_repo(root, "devman", ["v0.7.0"])

    [outcome] = refresh_collection(root, dry_run=True)

    assert outcome.status == "planned"
    assert "would check out v0.7.0" in outcome.detail
    assert not (repo / "README").exists()


def test_refresh_runs_only_with_collection_and_after_the_entries(forge: Path, root: Path):
    _collection_repo(root, "devman", ["v0.7.0"])
    reg = registry(forge_registry(forge, 'devman = { ref = "refs/tags/v0.7.0" }'))

    assert sync_store(reg, root=root, collection=False) == []
    outcomes = sync_store(reg, root=root, collection=True)

    assert [o.subject for o in outcomes] == ["collection:devman"]


# --- the command -----------------------------------------------------------------------------


def _project(tmp_path: Path, text: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "vendomat.toml").write_text(text)
    (project / "flake-outputs.nix").write_text("inputs: { }\n")
    return project


def test_source_root_reads_the_environment_then_the_home_directory():
    assert store.source_root({"VENDOMAT_SOURCE_ROOT": "/srv/src"}) == Path("/srv/src")
    assert store.source_root({"VENDOMAT_SOURCE_ROOT": ""}) == Path("~/vendor").expanduser()
    assert store.source_root({}) == Path("~/vendor").expanduser()


def test_the_command_clones_into_vendomat_source_root(forge: Path, root: Path, tmp_path: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    project = _project(tmp_path, forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    result = runner.invoke(app, ["sync", "--root", str(project)], env={"VENDOMAT_SOURCE_ROOT": str(root)})

    assert result.exit_code == 0, result.output
    assert head_tag(root / "lib-a") == "v1.0.0"
    assert "cloned" in result.output
    assert (project / "flake.nix").is_file()


def test_a_store_failure_still_leaves_the_written_flake_and_exits_non_zero(forge: Path, root: Path, tmp_path: Path):
    project = _project(tmp_path, forge_registry(forge, 'gone = { ref = "refs/tags/v1.0.0", keep = true }'))

    result = runner.invoke(app, ["sync", "--root", str(project)], env={"VENDOMAT_SOURCE_ROOT": str(root)})

    assert result.exit_code == 2
    assert (project / "flake.nix").read_text().startswith("# GENERATED by vendomat")
    assert "gone: failed" in result.output


def test_the_command_exits_one_for_a_dirty_clone_and_still_syncs_the_rest(forge: Path, root: Path, tmp_path: Path):
    a, b = Upstream(forge, "lib-a"), Upstream(forge, "lib-b")
    a.release("v1.0.0")
    b.release("v1.0.0")
    entries = 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }\nlib-b = { ref = "refs/tags/v1.0.0", keep = true }'
    project = _project(tmp_path, forge_registry(forge, entries))
    env = {"VENDOMAT_SOURCE_ROOT": str(root)}
    assert runner.invoke(app, ["sync", "--root", str(project)], env=env).exit_code == 0
    (root / "lib-a" / "README").write_text("edit\n")
    git(root / "lib-b", "tag", "-d", "v1.0.0")

    result = runner.invoke(app, ["sync", "--root", str(project)], env=env)

    assert result.exit_code == 1
    assert "lib-a: refused" in result.output
    assert "lib-b: updated" in result.output
    assert head_tag(root / "lib-b") == "v1.0.0"


def test_dry_run_writes_no_flake_and_no_clone(forge: Path, root: Path, tmp_path: Path):
    up = Upstream(forge, "lib-a")
    up.release("v1.0.0")
    project = _project(tmp_path, forge_registry(forge, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }'))

    result = runner.invoke(app, ["sync", "--dry-run", "--root", str(project)], env={"VENDOMAT_SOURCE_ROOT": str(root)})

    assert result.exit_code == 0, result.output
    assert "would write flake.nix" in result.output
    assert "would clone" in result.output
    assert not (project / "flake.nix").exists()
    assert not root.exists()


def test_the_command_says_a_mirror_is_skipped_without_collection(tmp_path: Path, root: Path):
    up = Upstream(tmp_path / "upstream", "telescope")
    up.release("v0.1.8")
    project = _project(tmp_path, _mirror_registry(up))
    env = {"VENDOMAT_SOURCE_ROOT": str(root)}

    plain = runner.invoke(app, ["sync", "--root", str(project)], env=env)
    assert plain.exit_code == 0, plain.output
    assert "mirror skipped: not the collection host" in plain.output
    assert not root.exists()

    host = runner.invoke(app, ["sync", "--collection", "--root", str(project)], env=env)
    assert host.exit_code == 0, host.output
    assert head_tag(root / "telescope") == "v0.1.8"


def test_a_registry_error_stops_before_any_store_work(forge: Path, root: Path, tmp_path: Path):
    project = _project(tmp_path, forge_registry(forge, "lib-a = { keep = true }"))

    result = runner.invoke(app, ["sync", "--root", str(project)], env={"VENDOMAT_SOURCE_ROOT": str(root)})

    assert result.exit_code == 2
    assert not (project / "flake.nix").exists()
    assert not root.exists()


def test_outcome_lines_name_the_subject_and_status():
    assert Outcome("a", "cloned", "x").line() == "a: cloned: x"

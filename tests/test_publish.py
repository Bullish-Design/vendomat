from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from vendomat.publish import (
    PublishError,
    hook_script,
    lock_version_changes,
    materialize,
    on_pre_push,
    pre_push,
    publish_preview,
    read_manifest,
)


def _manifest(repo, files='["pyproject.toml"]'):
    (repo / "vendomat.toml").write_text(
        "[[replacement]]\n"
        f"files = {files}\n"
        'local = "path:vendor/pyjutsu"\n'
        'github = "git+https://github.com/acme/pyjutsu.git@v0.10.1"\n'
    )


def test_materialize_rewrites_only_manifest_files_and_is_reversible(tmp_path):
    _manifest(tmp_path)
    source = tmp_path / "pyproject.toml"
    source.write_text('source = "path:vendor/pyjutsu"\n')
    untouched = tmp_path / "notes.txt"
    untouched.write_text("path:vendor/pyjutsu\n")

    assert materialize(tmp_path, "github") == [source]
    assert "git+https://github.com/acme/pyjutsu.git@v0.10.1" in source.read_text()
    assert untouched.read_text() == "path:vendor/pyjutsu\n"
    assert materialize(tmp_path, "github") == []
    assert materialize(tmp_path, "local") == [source]
    assert source.read_text() == 'source = "path:vendor/pyjutsu"\n'


def test_manifest_rejects_unsafe_or_empty_github_replacements(tmp_path):
    _manifest(tmp_path, '["../pyproject.toml"]')
    with pytest.raises(PublishError, match="repo-relative"):
        read_manifest(tmp_path)

    _manifest(tmp_path)
    (tmp_path / "vendomat.toml").write_text(
        (tmp_path / "vendomat.toml").read_text().replace("git+https://github.com/acme/pyjutsu.git@v0.10.1", "")
    )
    with pytest.raises(PublishError, match="non-empty GitHub"):
        read_manifest(tmp_path)


def test_hook_trampoline_preserves_git_arguments():
    assert hook_script("/nix/store/example/bin/vendomat") == (
        '#!/bin/sh\n# Installed by vendomat; do not edit.\nexec /nix/store/example/bin/vendomat pre-push "$@"\n'
    )


def test_lock_version_changes_rejects_additions_removals_and_upgrades():
    before = '[[package]]\nname = "alpha"\nversion = "1.0"\n\n[[package]]\nname = "beta"\nversion = "2.0"\n'
    after = '[[package]]\nname = "alpha"\nversion = "1.1"\n\n[[package]]\nname = "gamma"\nversion = "3.0"\n'

    assert lock_version_changes(before, after) == ["alpha", "beta", "gamma"]


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()


def test_pre_push_publishes_github_sources_without_changing_local_checkout(tmp_path, monkeypatch):
    """The disposable-worktree publisher rewrites the outgoing commit, not the local branch."""

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    _manifest(repo)
    source = repo / "pyproject.toml"
    source.write_text('source = "git+https://github.com/acme/pyjutsu.git@v0.10.1"\n')
    (repo / "uv.lock").write_text('[[package]]\nname = "pyjutsu"\nversion = "0.10.1"\n')
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")
    remote_sha = _git(repo, "rev-parse", "HEAD")

    source.write_text('source = "path:vendor/pyjutsu"\n')
    _git(repo, "commit", "-am", "use local vendor")
    local_sha = _git(repo, "rev-parse", "HEAD")
    executable = shutil.which("vendomat")
    assert executable, "the test environment must expose the project console script"
    tools = tmp_path / "tools"
    tools.mkdir()
    fake_uv = tools / "uv"
    fake_uv.write_text("#!/bin/sh\nexit 0\n")
    fake_uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    monkeypatch.setattr("sys.argv", [executable])

    preview = publish_preview(repo)
    assert "git+https://github.com/acme/pyjutsu.git@v0.10.1" in preview

    update = f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"
    with pytest.raises(PublishError, match="published GitHub-source"):
        pre_push(repo, "origin", update)

    assert "path:vendor/pyjutsu" in source.read_text()  # original checkout was never touched
    published = _git(remote, "show", "main:pyproject.toml")
    assert "git+https://github.com/acme/pyjutsu.git@v0.10.1" in published


def _consumer_repo(tmp_path, monkeypatch):
    """A consumer repo whose first commit is already published GitHub-shape on origin."""

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    _manifest(repo)
    source = repo / "pyproject.toml"
    source.write_text('source = "git+https://github.com/acme/pyjutsu.git@v0.10.1"\n')
    (repo / "uv.lock").write_text('[[package]]\nname = "pyjutsu"\nversion = "0.10.1"\n')
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    executable = shutil.which("vendomat")
    assert executable, "the test environment must expose the project console script"
    tools = tmp_path / "tools"
    tools.mkdir()
    fake_uv = tools / "uv"
    fake_uv.write_text("#!/bin/sh\nexit 0\n")
    fake_uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    monkeypatch.setattr("sys.argv", [executable])
    return repo, remote, source


def _publish(repo, remote_ref="refs/heads/main"):
    local_sha = _git(repo, "rev-parse", "HEAD")
    remote_sha = _git(repo, "rev-parse", "refs/remotes/origin/main")
    update = f"{remote_ref} {local_sha} {remote_ref} {remote_sha}\n"
    with pytest.raises(PublishError, match="published GitHub-source"):
        pre_push(repo, "origin", update)


def test_pre_push_is_repeatable_across_the_published_divergence(tmp_path, monkeypatch):
    """A second push replays only the new commits onto the already published history."""

    repo, remote, source = _consumer_repo(tmp_path, monkeypatch)

    source.write_text('source = "path:vendor/pyjutsu"\n')
    _git(repo, "commit", "-am", "use local vendor")
    _publish(repo)

    (repo / "README.md").write_text("second\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "second")
    _publish(repo)

    assert "path:vendor/pyjutsu" in source.read_text()  # the local checkout stays vendor-shaped
    assert not (repo / "README.md").exists() or (repo / "README.md").read_text() == "second\n"
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "main")
    published = _git(remote, "show", "main:pyproject.toml")
    assert "git+https://github.com/acme/pyjutsu.git@v0.10.1" in published
    assert _git(remote, "show", "main:README.md") == "second"
    # Replay must not duplicate published history: base + two published commits, nothing more.
    assert _git(remote, "rev-list", "--count", "main") == "3"


def test_pre_push_reports_a_divergence_that_cannot_be_replayed(tmp_path, monkeypatch):
    """A branch rewritten after publication names the marker and the escape route."""

    repo, _remote, source = _consumer_repo(tmp_path, monkeypatch)
    source.write_text('source = "path:vendor/pyjutsu"\n')
    _git(repo, "commit", "-am", "use local vendor")
    _publish(repo)

    _git(repo, "reset", "--hard", "HEAD~1")
    (repo / "README.md").write_text("rewritten\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "rewritten")
    local_sha = _git(repo, "rev-parse", "HEAD")
    remote_sha = _git(repo, "rev-parse", "refs/remotes/origin/main")
    update = f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"
    with pytest.raises(PublishError, match="diverged from the last publication"):
        pre_push(repo, "origin", update)


def test_on_pre_push_resolves_both_shas_from_the_repository(tmp_path, monkeypatch):
    """The pyjutsu entry point needs no standard input; it reads the refs itself."""

    repo, remote, source = _consumer_repo(tmp_path, monkeypatch)
    source.write_text('source = "path:vendor/pyjutsu"\n')
    _git(repo, "commit", "-am", "use local vendor")

    with pytest.raises(PublishError, match="published GitHub-source"):
        on_pre_push("origin", ["main"], repo_root=repo)

    assert "path:vendor/pyjutsu" in source.read_text()
    assert "git+https://github.com/acme/pyjutsu.git@v0.10.1" in _git(remote, "show", "main:pyproject.toml")
    assert _git(repo, "rev-parse", "refs/vendomat/published/origin/main") == _git(repo, "rev-parse", "HEAD")

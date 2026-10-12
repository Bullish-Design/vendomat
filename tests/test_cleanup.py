"""The `cleanup` script deletes regenerable leftovers and nothing else.

Each test builds a fake Testee state directory and a small Git repository in a temporary directory.
The tests pass the live workspaces with `--live-root`, so no test calls jj or Testee.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cleanup.py"
_spec = importlib.util.spec_from_file_location("vendomat_cleanup", SCRIPT)
assert _spec is not None and _spec.loader is not None
cleanup = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cleanup
_spec.loader.exec_module(cleanup)


class World:
    """A repository, a live workspace, and a Testee state directory."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.live = base / "ws-live"
        self.live.mkdir()
        self.state = base / "state"
        self.state_repo = self.state / "repos" / "aaaa"
        self.state_repo.mkdir(parents=True)
        self._info(self.state_repo, self.repo / ".git")
        # Another repository, with a stale slot that cleanup must not touch.
        self.other_repo = base / "other"
        self.other_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.other_repo)], check=True)
        self.other_state = self.state / "repos" / "bbbb"
        self.other_state.mkdir(parents=True)
        self._info(self.other_state, self.other_repo / ".git")
        self.other_slot = self.slot(self.other_state, "gone-00000000", base / "missing-other")
        # Verdicts live outside the slots.
        self.verdict = self.state_repo / "verdicts" / "tree" / "key" / "ruff.json"
        self.verdict.parent.mkdir(parents=True)
        self.verdict.write_text("{}")

    @staticmethod
    def _info(directory: Path, common: Path) -> None:
        (directory / "repo.json").write_text(json.dumps({"common_dir": str(common), "kind": "git"}))

    @staticmethod
    def slot(state_repo: Path, name: str, toplevel: Path, *, worktree: bool = True) -> Path:
        slot = state_repo / "slots" / name
        ws = slot / "ws"
        (ws / ".devenv" / "state" / "venv" / "bin").mkdir(parents=True)
        (ws / ".devenv" / "state" / "venv" / "bin" / "python").write_text("venv")
        (ws / ".pytest_cache").mkdir()
        (ws / ".pytest_cache" / "x").write_text("cache")
        (ws / "marker.txt").write_text("source")
        if worktree:
            (ws / ".git").write_text("gitdir: /nowhere\n")
        (slot / "runs").mkdir()
        (slot / "lock").write_text("")
        (slot / "slot.json").write_text(json.dumps({"toplevel": str(toplevel)}))
        return slot

    def live_slot(self, name: str = "live") -> Path:
        return self.slot(self.state_repo, cleanup.slot_name(self.live), self.live)

    def stale_slot(self, name: str = "gone") -> Path:
        return self.slot(self.state_repo, f"{name}-12345678", self.base / f"missing-{name}")

    def args(self, *extra: str) -> list[str]:
        return [
            "--root",
            str(self.repo),
            "--state-dir",
            str(self.state),
            "--live-root",
            str(self.live),
            "--testee",
            "none",
            *extra,
        ]

    def litter(self) -> None:
        """Put regenerable files in the working copy, plus files that must stay."""
        for name in ("__pycache__", ".pytest_cache", ".ruff_cache"):
            (self.repo / "src" / name).mkdir(parents=True, exist_ok=True)
            (self.repo / "src" / name / "x.pyc").write_text("cache")
        (self.repo / "src" / "module.py").write_text("source")
        (self.repo / "result-old").symlink_to(self.base / "no-such-target")


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def test_dry_run_deletes_nothing(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    stale = world.stale_slot()
    live = world.live_slot()
    world.litter()
    before = sorted(p for p in world.base.rglob("*"))
    assert cleanup.main(world.args()) == 0
    out = capsys.readouterr().out
    assert sorted(world.base.rglob("*")) == before
    assert "dry run" in out
    assert "would delete" in out and str(stale) in out
    assert str(live / "ws" / ".devenv" / "state" / "venv") in out
    assert "total:" in out


def test_yes_deletes_stale_slots_and_caches(world: World) -> None:
    stale = world.stale_slot()
    live = world.live_slot()
    world.litter()
    assert cleanup.main(world.args("--yes")) == 0
    assert not stale.exists()
    # The idle live slot keeps its source tree and its record. It loses venv and caches.
    assert (live / "ws" / "marker.txt").exists()
    assert (live / "slot.json").exists()
    assert not (live / "ws" / ".devenv" / "state" / "venv").exists()
    assert not (live / "ws" / ".pytest_cache").exists()
    for name in ("__pycache__", ".pytest_cache", ".ruff_cache"):
        assert not (world.repo / "src" / name).exists()
    assert (world.repo / "src" / "module.py").read_text() == "source"
    assert not (world.repo / "result-old").is_symlink()
    # Verdicts live outside the slots.
    assert world.verdict.exists()


def test_a_busy_slot_is_skipped(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    stale = world.stale_slot()
    live = world.live_slot()
    held = [open(slot / "lock", "r+") for slot in (stale, live)]
    try:
        for handle in held:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert cleanup.main(world.args("--yes")) == 0
    finally:
        for handle in held:
            handle.close()
    assert "skip busy slot" in capsys.readouterr().out
    assert (stale / "ws" / "marker.txt").exists()
    assert (live / "ws" / ".devenv" / "state" / "venv" / "bin" / "python").exists()


def test_another_repository_is_untouched(world: World) -> None:
    world.stale_slot()
    assert cleanup.main(world.args("--yes")) == 0
    assert (world.other_slot / "ws" / ".devenv" / "state" / "venv" / "bin" / "python").exists()
    assert (world.other_slot / "slot.json").exists()


def test_worktrees_and_working_copy_venv_are_kept(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    old = world.repo / ".worktrees" / "old-branch"
    (old / ".devenv" / "state" / "venv").mkdir(parents=True)
    (old / "__pycache__").mkdir()
    (old / "work.txt").write_text("unlanded")
    venv = world.repo / ".devenv" / "state" / "venv"
    (venv / "__pycache__").mkdir(parents=True)
    world.litter()
    assert cleanup.main(world.args("--yes")) == 0
    out = capsys.readouterr().out
    assert (old / "work.txt").read_text() == "unlanded"
    assert (old / "__pycache__").exists()
    assert (old / ".devenv" / "state" / "venv").exists()
    assert venv.exists() and (venv / "__pycache__").exists()
    assert "old-branch" in out and "unlanded work" in out


def test_a_tracked_cache_directory_is_kept(world: World) -> None:
    tracked = world.repo / "pkg" / "__pycache__"
    tracked.mkdir(parents=True)
    (tracked / "keep.pyc").write_text("tracked")
    subprocess.run(["git", "add", "-f", "pkg/__pycache__/keep.pyc"], cwd=world.repo, check=True)
    assert cleanup.main(world.args("--yes")) == 0
    assert (tracked / "keep.pyc").read_text() == "tracked"


def test_a_slot_without_a_testee_worktree_is_kept(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    slot = world.slot(world.state_repo, "odd-11111111", world.base / "missing-odd", worktree=False)
    assert cleanup.main(world.args("--yes")) == 0
    assert (slot / "ws" / "marker.txt").exists()
    assert "not a Testee worktree" in capsys.readouterr().out


def test_a_directory_that_is_not_a_repository_is_refused(world: World, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    code = cleanup.main(["--root", str(plain), "--state-dir", str(world.state), "--live-root", str(plain)])
    assert code == 2

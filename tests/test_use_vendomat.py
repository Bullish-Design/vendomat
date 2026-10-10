"""`use_vendomat` re-syncs only when the digest is stale, then calls `use devenv` (`PRE-009`)."""

from __future__ import annotations

import hashlib
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "direnv" / "vendomat.sh"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_workspace(root: Path, *, current: bool = True) -> None:
    (root / ".vendomat").mkdir(parents=True)
    (root / "vendomat.toml").write_text("[inputs]\n")
    (root / ".vendomat" / "devenv.yaml").write_text("inputs: {}\n")
    (root / ".vendomat" / "devenv.nix").write_text("{ }\n")
    (root / "devenv.lock").write_text("{}\n")
    if current:
        digest = (
            f"digest x\nregistry {sha(root / 'vendomat.toml')}\n"
            f"fragment {sha(root / '.vendomat/devenv.yaml')}\nmodule {sha(root / '.vendomat/devenv.nix')}\n"
        )
        (root / ".vendomat" / "digest").write_text(digest)


def call(tmp_path: Path, root: Path, sync_status: int = 0) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "vendomat"
    stub.write_text(f'#!/bin/sh\necho "vendomat $*" >> {log}\nexit {sync_status}\n')
    stub.chmod(0o755)
    harness = textwrap.dedent(
        f"""
        watch_file() {{ :; }}
        log_status() {{ echo "status: $*"; }}
        log_error() {{ echo "error: $*" >&2; }}
        use() {{ echo "use $*" >> {log}; }}
        . {SCRIPT}
        use_vendomat {root}
        """
    )
    done = subprocess.run(
        ["bash", "-c", harness],
        capture_output=True,
        text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin:/run/current-system/sw/bin"},
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return done, calls


def test_a_current_workspace_runs_no_sync(tmp_path):
    root = tmp_path / "ws"
    make_workspace(root)
    done, calls = call(tmp_path, root)
    assert done.returncode == 0
    assert calls == ["use devenv"]


@pytest.mark.parametrize(
    "mutate, why",
    [
        (lambda r: (r / "vendomat.toml").write_text("[inputs]\nx = {}\n"), "registry changed"),
        (lambda r: (r / ".vendomat/devenv.yaml").write_text("inputs: {a: b}\n"), "fragment edited"),
        (lambda r: (r / ".vendomat/devenv.nix").write_text("{ a = 1; }\n"), "module edited"),
        (lambda r: (r / ".vendomat/digest").unlink(), "no digest"),
        (lambda r: (r / "devenv.lock").unlink(), "no lock"),
    ],
)
def test_each_stale_case_syncs_once_then_enters(tmp_path, mutate, why):
    root = tmp_path / "ws"
    make_workspace(root)
    mutate(root)
    done, calls = call(tmp_path, root)
    assert done.returncode == 0
    assert why in done.stdout
    assert calls == [f"vendomat sync --root {root}", "use devenv"]


def test_a_failed_sync_does_not_enter_the_shell(tmp_path):
    root = tmp_path / "ws"
    make_workspace(root, current=False)
    done, calls = call(tmp_path, root, sync_status=2)
    assert done.returncode == 1
    assert "use devenv" not in calls
    assert "sync failed" in done.stderr

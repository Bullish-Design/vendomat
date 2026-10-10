"""The host launcher runs each workspace's pinned Vendomat and the host release elsewhere (`DEL-017`)."""

from __future__ import annotations

import base64
import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "launcher" / "vendomat"
JQ = shutil.which("jq")
pytestmark = pytest.mark.skipif(JQ is None or shutil.which("bash") is None, reason="needs bash and jq")

ARCH = os.uname().machine + "-linux"


def script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class Env:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.store = tmp / "store"
        self.store.mkdir()
        self.bin = tmp / "bin"
        self.calls = tmp / "nix-calls.log"
        self.fail_build = tmp / "fail-build"
        script(tmp / "host" / "bin" / "vendomat", 'echo "HOST $*"\n')
        script(self.bin / "nix-store", f'echo "{self.store}/$(echo "$4" | cut -c1-8)-source"\n')
        # `nix build ... path:<store>#...` prints the output of a fake pinned build named after the source.
        script(
            self.bin / "nix",
            f"""
            echo "$*" >> {self.calls}
            [ -e {self.fail_build} ] && exit 1
            ref=""
            for a in "$@"; do ref="$a"; done
            case "$ref" in
              path:*) name="$(basename "${{ref%%#*}}" | cut -c1-8)" ;;
              *) name="fetched" ;;
            esac
            out="{tmp}/pinned/$name"
            mkdir -p "$out/bin"
            printf '#!/usr/bin/env bash\\necho "PINNED-%s $*"\\n' "$name" > "$out/bin/vendomat"
            chmod +x "$out/bin/vendomat"
            echo "$out"
            """,
        )
        self.env = {
            "PATH": f"{self.bin}:{Path(JQ or '/').parent}:/run/current-system/sw/bin:/usr/bin:/bin",
            "HOME": str(tmp / "home"),
            "VENDOMAT_HOST_RELEASE": str(tmp / "host" / "bin" / "vendomat"),
            "VENDOMAT_LAUNCHER_CACHE": str(tmp / "cache"),
        }

    def workspace(self, name: str, nar_hex: str | None, *, lock: bool = True) -> Path:
        root = self.tmp / name
        root.mkdir()
        (root / "vendomat.toml").write_text("[inputs]\n")
        if lock:
            nodes: dict = {"root": {"inputs": {}}}
            if nar_hex is not None:
                nar = "sha256-" + base64.b64encode(bytes.fromhex(nar_hex.ljust(64, "0"))).decode()
                nodes["vendomat"] = {
                    "locked": {"narHash": nar, "rev": "a" * 40, "type": "git", "url": "git://s/vendomat"},
                    "original": {"type": "git", "url": "git://s/vendomat", "ref": "refs/tags/v0.6.0"},
                }
            (root / "devenv.lock").write_text(json.dumps({"nodes": nodes, "root": "root"}))
        return root

    def source(self, nar_hex: str) -> Path:
        path = self.store / f"{nar_hex.ljust(64, '0')[:8]}-source"
        path.mkdir()
        return path

    def run(self, cwd: Path, *args: str, extra_env: dict[str, str] | None = None):
        return subprocess.run(
            ["bash", str(LAUNCHER), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**self.env, **(extra_env or {})},
        )

    def builds(self) -> list[str]:
        return self.calls.read_text().splitlines() if self.calls.exists() else []


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def test_outside_a_workspace_the_host_release_runs_without_a_message(env, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    done = env.run(elsewhere, "path", "x")
    assert done.stdout.strip() == "HOST path x"
    assert done.stderr == ""


def test_a_new_workspace_with_no_lock_bootstraps_with_the_host_release(env):
    root = env.workspace("new", None, lock=False)
    done = env.run(root, "sync")
    assert done.stdout.strip() == "HOST sync"
    assert "no devenv.lock" in done.stderr and "bootstrap" in done.stderr


def test_a_lock_without_a_vendomat_node_uses_the_host_release_and_says_so(env):
    root = env.workspace("nolock", None)
    done = env.run(root, "check")
    assert done.stdout.strip() == "HOST check"
    assert "pins no vendomat input" in done.stderr


def test_a_pinned_workspace_runs_its_own_build_found_by_nar_hash(env):
    env.source("aa")
    root = env.workspace("a", "aa")
    done = env.run(root, "sync")
    assert done.stdout.strip() == "PINNED-aa000000 sync"
    assert any(
        "--offline" in b and f"path:{env.store}/aa000000-source#packages.{ARCH}.vendomat" in b for b in env.builds()
    )


def test_the_build_is_cached_by_nar_hash_and_runs_without_nix(env):
    env.source("aa")
    root = env.workspace("a", "aa")
    env.run(root, "sync")
    before = len(env.builds())
    # With nix gone from PATH, the cached build still runs.
    (env.bin / "nix").unlink()
    done = env.run(root, "sync")
    assert done.stdout.strip() == "PINNED-aa000000 sync"
    assert len(env.builds()) == before


def test_two_workspaces_on_different_pins_each_run_their_own_build(env):
    env.source("aa")
    env.source("bb")
    one = env.workspace("one", "aa")
    two = env.workspace("two", "bb")
    assert env.run(one, "--version").stdout.strip() == "PINNED-aa000000 --version"
    assert env.run(two, "--version").stdout.strip() == "PINNED-bb000000 --version"


def test_root_option_selects_the_workspace_from_another_directory(env, tmp_path):
    env.source("aa")
    root = env.workspace("a", "aa")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    done = env.run(elsewhere, "sync", "--root", str(root))
    assert done.stdout.strip() == f"PINNED-aa000000 sync --root {root}"


def test_a_missing_pinned_build_falls_back_to_the_host_release_and_says_so(env):
    root = env.workspace("gone", "cc")  # the source is not in the store
    (env.tmp / "fail-build").write_text("")
    done = env.run(root, "sync")
    assert done.stdout.strip() == "HOST sync"
    assert "not in the store and cannot be fetched" in done.stderr
    assert "host release to repair" in done.stderr


def test_a_missing_source_is_fetched_from_the_locks_own_reference(env):
    root = env.workspace("fetch", "dd")  # not in the store; the fake nix can build the lock's ref
    done = env.run(root, "sync")
    assert done.stdout.strip() == "PINNED-fetched sync"
    assert any("git://s/vendomat?ref=refs/tags/v0.6.0&rev=" + "a" * 40 in b for b in env.builds())


def test_use_host_forces_the_host_release(env):
    env.source("aa")
    root = env.workspace("a", "aa")
    done = env.run(root, "sync", extra_env={"VENDOMAT_USE_HOST": "1"})
    assert done.stdout.strip() == "HOST sync"
    assert "VENDOMAT_USE_HOST=1" in done.stderr

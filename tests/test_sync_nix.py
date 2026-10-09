"""Actual `vendomat sync` output on pinned Nix (generator proof, V5 Step 8).

The generated flake must behave like the hand-written candidate in
`test_project_output_interface.py`. A pass here is not a pass for a private source host,
a cache, a cold store, or the host-installed command.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from nixfixture import (
    CANDIDATE_REGISTRY,
    NIXPKGS_URL,
    OUTPUTS_PACKAGES_ONLY,
    SYSTEM,
    candidate_flake,
    check_bridge,
    declared_inputs,
    init_repo,
    needs_nix_fixture,
    nix,
    nixpkgs_nodes,
    run,
    sanitized_env,
    save,
    tag_release,
    write,
    write_sources,
)

from vendomat.generate import tool_version
from vendomat.registry import parse_registry

pytestmark = needs_nix_fixture

_ENTRY = "from vendomat.cli import main; main()"


def vendomat(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the real CLI entry point in a fresh interpreter."""
    full_env = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, "-c", _ENTRY, *args], capture_output=True, text=True, env=full_env)


def vendomat_sync(root: Path) -> subprocess.CompletedProcess[str]:
    return vendomat(["sync", "--root", str(root)])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def seeded(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A tracked consumer with a registry and a project file, before the first sync."""
    root = tmp_path_factory.mktemp("sync-seed")
    write(root / "vendomat.toml", CANDIDATE_REGISTRY)
    write(root / "flake-outputs.nix", OUTPUTS_PACKAGES_ONLY)
    write_sources(root)
    init_repo(root, "sync fixture seed")
    return root


@pytest.fixture
def project(seeded: Path, tmp_path: Path) -> Path:
    target = tmp_path / "project"
    shutil.copytree(seeded, target, symlinks=True)
    return target


def synced(project: Path) -> None:
    result = vendomat_sync(project)
    assert result.returncode == 0, result.stderr + result.stdout
    save(project, "flake", "record the generated flake")


def test_sync_output_equals_the_candidate_that_passed(project: Path):
    synced(project)
    registry = parse_registry(CANDIDATE_REGISTRY)
    expected = candidate_flake(version=tool_version(), digest=registry.digest)
    assert (project / "flake.nix").read_text() == expected


def test_generated_flake_declares_only_direct_inputs_and_no_vendomat(project: Path):
    synced(project)
    inputs = declared_inputs(project / "flake.nix")
    assert sorted(inputs) == ["data", "mod-pkg", "nixpkgs", "plain"]
    assert inputs["data"] == {"url": "path:./inputs/data", "flake": False}
    assert inputs["nixpkgs"] == {"url": NIXPKGS_URL}


def test_generated_flake_passes_the_bridge_checks_with_vendomat_absent_and_no_cache(project: Path, tmp_path: Path):
    synced(project)
    check_bridge(project, env=sanitized_env(tmp_path), offline=True)


def test_sync_leaves_the_lock_and_project_file_byte_identical(project: Path):
    synced(project)
    assert nix(["flake", "lock"], project).returncode == 0
    save(project, "lock", "record the lock Nix wrote")
    lock, outputs, flake = project / "flake.lock", project / "flake-outputs.nix", project / "flake.nix"
    before = (sha(lock), sha(outputs), sha(flake))
    for _ in range(2):
        result = vendomat_sync(project)
        assert result.returncode == 0, result.stderr
    assert (sha(lock), sha(outputs), sha(flake)) == before
    assert "unchanged" in result.stdout


def test_registry_names_that_nix_reserves_still_parse(tmp_path: Path):
    write(tmp_path / "vendomat.toml", '[inputs]\n3d-lib = { url = "path:./a" }\nrec = { url = "path:./b" }\n')
    write(tmp_path / "flake-outputs.nix", "inputs: { }\n")
    result = vendomat_sync(tmp_path)
    assert result.returncode == 0, result.stderr
    assert sorted(declared_inputs(tmp_path / "flake.nix")) == ["3d-lib", "rec"]


def test_follows_edge_from_the_registry_gives_one_nixpkgs_node(project: Path):
    registry = CANDIDATE_REGISTRY + '\n[follows]\nmod-pkg = ["nixpkgs"]\nplain = ["nixpkgs"]\n'
    write(project / "vendomat.toml", registry)
    synced(project)
    lock = nix(["flake", "lock"], project)
    assert lock.returncode == 0, lock.stderr
    assert lock.warnings == []
    assert len(nixpkgs_nodes(json.loads((project / "flake.lock").read_text()))) == 1


def test_follows_on_a_child_without_nixpkgs_is_reported_by_nix_not_hidden(project: Path):
    write(project / "inputs/plain/flake.nix", "{ outputs = _: { packages.x86_64-linux.default = null; }; }\n")
    write(project / "vendomat.toml", CANDIDATE_REGISTRY + '\n[follows]\nplain = ["nixpkgs"]\n')
    synced(project)
    lock = nix(["flake", "lock"], project)
    assert lock.returncode == 0
    assert lock.warnings == ["warning: input 'plain' has an override for a non-existent input 'nixpkgs'"]


def test_sync_refuses_a_hand_authored_flake_and_leaves_it(project: Path):
    write(project / "flake.nix", "{ outputs = _: { }; }\n")
    result = vendomat_sync(project)
    assert result.returncode == 1
    assert "flake.nix" in result.stderr
    assert (project / "flake.nix").read_text() == "{ outputs = _: { }; }\n"


# --- explicit local override (REG-010, STORE-007) -----------------------------------------


def _source_repo(root: Path, marker: str) -> None:
    flake = f"""{{
  inputs.nixpkgs.url = "{NIXPKGS_URL}";
  outputs = {{ self, nixpkgs }}: {{
    packages.{SYSTEM}.default = nixpkgs.legacyPackages.{SYSTEM}.writeText "{marker}" "{marker}\\n";
  }};
}}
"""
    write(root / "flake.nix", flake)
    init_repo(root, f"source {marker}")
    tag_release(root, "1.0.0")


def test_local_override_selects_another_source_without_touching_the_lock(tmp_path: Path):
    remote = tmp_path / "remote/mod-pkg"
    local = tmp_path / "local/mod-pkg"
    _source_repo(remote, "remote-marker")
    _source_repo(local, "override-marker")

    project = tmp_path / "project"
    write(
        project / "vendomat.toml",
        f'[inputs]\nmod-pkg = {{ url = "git+file://{remote}", ref = "refs/tags/v1.0.0" }}\n\n'
        f'[passthrough]\nnixpkgs = {{ url = "{NIXPKGS_URL}" }}\n',
    )
    write(
        project / "flake-outputs.nix",
        "inputs: { packages.x86_64-linux.default = inputs.mod-pkg.packages.x86_64-linux.default; }\n",
    )
    init_repo(project, "override project")
    synced(project)
    assert nix(["flake", "lock"], project).returncode == 0
    save(project, "lock", "record the lock Nix wrote")

    flake_before, lock_before = sha(project / "flake.nix"), sha(project / "flake.lock")
    # The registry stays on the portable URL. Only this command selects the local checkout.
    attr = f".#packages.{SYSTEM}.default"
    override = ["--no-write-lock-file", "--override-input", "mod-pkg", f"git+file://{local}"]
    built = nix(["build", *override, "--no-link", "--print-out-paths", attr], project)
    assert built.returncode == 0, built.stderr
    assert Path(built.stdout.strip()).read_text() == "override-marker\n"
    assert (sha(project / "flake.nix"), sha(project / "flake.lock")) == (flake_before, lock_before)

    # An environment variable alone changes nothing (STORE-007).
    env = {**os.environ, "VENDOMAT_SOURCE_ROOT": str(local.parent)}
    env_only = nix(["build", "--no-link", "--print-out-paths", attr], project, env=env)
    assert env_only.returncode == 0, env_only.stderr
    assert Path(env_only.stdout.strip()).read_text() == "remote-marker\n"


# --- the source collection over git:// (STORE-008, REG-016, REG-017) ---------------------------


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def collection(tmp_path: Path) -> Iterator[tuple[Path, int, subprocess.Popen[bytes]]]:
    """A collection with one tagged repository, served read-only by `git daemon` on loopback."""
    base = tmp_path / "vendor"
    repo = base / "lib-a"
    write(repo / "flake.nix", '{ outputs = _: { marker = "lib-a-v1"; }; }\n')
    init_repo(repo, "lib-a release")
    tag_release(repo, "1.0.0")
    port = _free_port()
    daemon = subprocess.Popen(
        ["git", "daemon", "--reuseaddr", f"--base-path={base}", "--export-all", "--listen=127.0.0.1", f"--port={port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            pytest.fail("git daemon did not start")
        yield base, port, daemon
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)


def test_forge_entry_fetches_over_git_and_keeps_working_after_the_daemon_stops(
    collection: tuple[Path, int, subprocess.Popen[bytes]], tmp_path: Path
):
    base, port, daemon = collection
    project = tmp_path / "project"
    write(
        project / "vendomat.toml",
        f'[forge]\nurl = "git://127.0.0.1:{port}"\n\n[inputs]\nlib-a = {{ ref = "refs/tags/v1.0.0" }}\n',
    )
    write(project / "flake-outputs.nix", "inputs: { lib.marker = inputs.lib-a.marker; }\n")
    init_repo(project, "forge project")
    synced(project)
    assert f'lib-a.url = "git://127.0.0.1:{port}/lib-a?ref=refs/tags/v1.0.0";' in (project / "flake.nix").read_text()

    lock = nix(["flake", "lock"], project)
    assert lock.returncode == 0, lock.stderr
    assert lock.warnings == []
    save(project, "lock", "record the lock Nix wrote")
    locked = json.loads((project / "flake.lock").read_text())["nodes"]["lib-a"]["locked"]
    assert (locked["type"], locked["url"], locked["ref"]) == (
        "git",
        f"git://127.0.0.1:{port}/lib-a",
        "refs/tags/v1.0.0",
    )

    online = nix(["eval", "--raw", ".#lib.marker"], project)
    assert online.returncode == 0, online.stderr
    assert online.stdout == "lib-a-v1"
    assert online.warnings == []

    # The source path is the same whether Nix fetches by daemon URL or by local path, so the
    # builder may use a local clone and still produce the outputs that consumers substitute.
    def source_path(url: str) -> str:
        expr = f'(builtins.fetchTree {{ type = "git"; url = "{url}"; ref = "refs/tags/v1.0.0"; }}).outPath'
        result = nix(["eval", "--impure", "--raw", "--expr", expr], project)
        assert result.returncode == 0, result.stderr
        return result.stdout

    assert source_path(f"git://127.0.0.1:{port}/lib-a") == source_path(f"file://{base}/lib-a")

    # A revision that is already fetched needs no network (the laptop off the tailnet).
    daemon.terminate()
    daemon.wait(timeout=10)
    offline = nix(["eval", "--raw", ".#lib.marker"], project)
    assert offline.returncode == 0, offline.stderr
    assert offline.stdout == "lib-a-v1"


def _forge_project(tmp_path: Path, port: int, entry: str) -> Path:
    project = tmp_path / "project"
    write(project / "vendomat.toml", f'[forge]\nurl = "git://127.0.0.1:{port}"\n\n[inputs]\n{entry}\n')
    write(project / "flake-outputs.nix", "inputs: { lib.src = inputs.lib-a.outPath; }\n")
    init_repo(project, "forge project")
    return project


def test_keep_clones_over_git_and_the_clone_shows_the_pinned_tag(
    collection: tuple[Path, int, subprocess.Popen[bytes]], tmp_path: Path
):
    _base, port, _daemon = collection
    project = _forge_project(tmp_path, port, 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }')
    clones = tmp_path / "clones"

    first = vendomat(["sync", "--root", str(project)], {"VENDOMAT_SOURCE_ROOT": str(clones)})
    assert first.returncode == 0, first.stderr
    clone = clones / "lib-a"
    assert (clone / "flake.nix").read_text() == '{ outputs = _: { marker = "lib-a-v1"; }; }\n'
    assert run(["git", "describe", "--tags", "--exact-match", "HEAD"], clone).stdout.strip() == "v1.0.0"
    assert run(["git", "symbolic-ref", "-q", "HEAD"], clone).returncode != 0

    again = vendomat(["sync", "--root", str(project)], {"VENDOMAT_SOURCE_ROOT": str(clones)})
    assert again.returncode == 0, again.stderr
    assert "lib-a: unchanged" in again.stdout


def test_path_prints_the_locked_source_and_changes_neither_the_lock_nor_the_registry(
    collection: tuple[Path, int, subprocess.Popen[bytes]], tmp_path: Path
):
    _base, port, _daemon = collection
    project = _forge_project(tmp_path, port, 'lib-a = { ref = "refs/tags/v1.0.0" }')
    synced(project)

    # Before any lock exists: Nix resolves in memory and writes nothing.
    early = vendomat(["path", "lib-a", "--root", str(project)])
    assert early.returncode == 0, early.stderr
    assert not (project / "flake.lock").exists()

    assert nix(["flake", "lock"], project).returncode == 0
    save(project, "lock", "record the lock Nix wrote")
    before = {name: sha(project / name) for name in ("flake.lock", "vendomat.toml", "flake.nix", "flake-outputs.nix")}

    found = vendomat(["path", "lib-a", "--root", str(project)])
    assert found.returncode == 0, found.stderr
    path = found.stdout.strip()
    assert path == early.stdout.strip()
    assert (Path(path) / "flake.nix").read_text() == '{ outputs = _: { marker = "lib-a-v1"; }; }\n'
    locked = nix(["eval", "--raw", ".#lib.src"], project)
    assert locked.returncode == 0, locked.stderr
    assert path == locked.stdout

    as_json = vendomat(["path", "lib-a", "--json", "--root", str(project)])
    assert json.loads(as_json.stdout) == {"name": "lib-a", "path": path}
    assert {name: sha(project / name) for name in before} == before


def test_path_names_an_unknown_input_and_lists_the_known_ones(
    collection: tuple[Path, int, subprocess.Popen[bytes]], tmp_path: Path
):
    _base, port, _daemon = collection
    project = _forge_project(tmp_path, port, 'lib-a = { ref = "refs/tags/v1.0.0" }')
    synced(project)

    result = vendomat(["path", "lib-b", "--root", str(project)])

    assert result.returncode == 1
    assert "unknown input 'lib-b'" in result.stderr
    assert "known inputs: lib-a" in result.stderr


def test_path_reports_a_path_input_that_has_no_store_path_of_its_own(project: Path):
    synced(project)

    result = vendomat(["path", "plain", "--root", str(project)])

    assert result.returncode == 1
    assert "no store path of its own" in result.stderr
    assert not (project / "flake.lock").exists()


def test_path_asks_for_sync_when_there_is_no_flake(tmp_path: Path):
    result = vendomat(["path", "lib-a", "--root", str(tmp_path)])

    assert result.returncode == 2
    assert "vendomat sync" in result.stderr


def test_archive_dry_run_prints_the_same_paths_as_archive(
    collection: tuple[Path, int, subprocess.Popen[bytes]], tmp_path: Path
):
    """A fact about the pinned Nix that `path` relies on: `--dry-run` does not hide input paths (PV-20)."""
    _base, port, _daemon = collection
    project = _forge_project(tmp_path, port, 'lib-a = { ref = "refs/tags/v1.0.0" }')
    synced(project)
    base = ["flake", "archive", "--json", "--no-write-lock-file", "."]

    real = nix(base, project)
    dry = nix([*base, "--dry-run"], project)

    assert real.returncode == 0 and dry.returncode == 0, real.stderr + dry.stderr
    assert json.loads(dry.stdout)["inputs"]["lib-a"]["path"] == json.loads(real.stdout)["inputs"]["lib-a"]["path"]


def test_nix_version_is_the_pinned_one():
    assert run(["nix", "--version"], Path.cwd()).stdout.strip() == "nix (Nix) 2.34.7"

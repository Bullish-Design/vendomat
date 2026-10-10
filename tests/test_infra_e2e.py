"""Source, cache, and builder infrastructure in NixOS VMs (V6 Step 5). Opt in with `testee check e2e`.

Each test builds the Vendomat package from this repository, then runs one NixOS VM test under
`tests/nix/infra/`. The VM tests make every key and token inside the VM. The checks here read the
saved VM log for the proof lines, and they confirm that no credential reached the log. They need
`/dev/kvm` and the `nixos-test` system feature. They never touch the live collection, the live
Attic, or a real credential file.

Set ``VENDOMAT_FIXTURE_LOGS`` to keep each VM log outside the repository.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "tests" / "nix" / "infra"

# Every Attic token is a JWT: three base64url parts, and the first starts with `eyJ`.
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")


def _vm_ready() -> bool:
    if not os.access("/dev/kvm", os.R_OK | os.W_OK) or shutil.which("nix") is None:
        return False
    shown = subprocess.run(
        ["nix", "config", "show", "system-features"], capture_output=True, text=True, cwd=ROOT, check=False
    )
    features = shown.stdout.split()
    return "nixos-test" in features and "kvm" in features


needs_vm = pytest.mark.skipif(not _vm_ready(), reason="needs /dev/kvm and the nixos-test system feature")


@pytest.fixture(scope="module")
def vendomat_package() -> tuple[str, str]:
    """The Vendomat package built from this repository, and its NAR hash recorded at build."""
    built = subprocess.run(
        ["nix", "build", ".#packages.x86_64-linux.vendomat", "--no-link", "--print-out-paths"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=1800,
        check=False,
    )
    assert built.returncode == 0, built.stderr[-3000:]
    path = built.stdout.strip().splitlines()[-1]
    info = subprocess.run(
        ["nix", "path-info", "--json", "--json-format", "1", path], capture_output=True, text=True, check=True
    )
    data = json.loads(info.stdout)
    entry = data[path] if isinstance(data, dict) else data[0]
    return path, entry["narHash"]


def _run_vm_test(name: str, package: tuple[str, str], tmp_path: Path) -> str:
    """Build one VM test and return its log. A cached result still yields the stored log."""
    env = {**os.environ, "VENDOMAT_PACKAGE": package[0], "VENDOMAT_PACKAGE_NARHASH": package[1]}
    built = subprocess.run(
        ["nix", "build", "--impure", "--no-link", "-L", "--print-out-paths", "--file", str(INFRA / f"{name}.nix")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=3000,
        check=False,
    )
    log = built.stdout + built.stderr
    assert built.returncode == 0, log[-5000:]
    out_path = built.stdout.strip().splitlines()[-1]
    if "RESULT" not in log:
        # The VM result came from the store, so Nix printed no build log. Read the stored log.
        shown = subprocess.run(["nix", "log", out_path], capture_output=True, text=True, check=False)
        log = shown.stdout + shown.stderr
    keep = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if keep:
        directory = Path(keep)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"infra-{name}.log").write_text(log)
    return log


def _expect(log: str, *markers: str) -> None:
    for marker in markers:
        assert marker in log, f"the VM log lacks: {marker}"
    assert not JWT.search(log), "a token-shaped string reached the VM log"


def test_no_infra_file_holds_a_credential():
    """The fixtures make every secret at run time. A JWT or a private key in a fixture is a leak."""
    for path in sorted(INFRA.iterdir()):
        text = path.read_text()
        assert not JWT.search(text), f"{path.name} holds a token-shaped string"
        assert "BEGIN RSA PRIVATE KEY" not in text and "BEGIN PRIVATE KEY" not in text, path.name


@needs_nix_fixture
@needs_vm
def test_the_collection_serves_tags_only_and_rebuilds_from_release_tags(vendomat_package, tmp_path):
    log = _run_vm_test("collection", vendomat_package, tmp_path)
    _expect(
        log,
        "RESULT hook text: installed post-receive equals hooks/collection-post-receive",
        "RESULT tag push from framework over ssh: accepted; tree shows v1.0.0",
        "RESULT branch push refused; moved tag refused; tag delete refused",
        "RESULT unmarked repository not served; push over git:// fails from both VMs",
        "RESULT nix fetch over git:// on framework: lib-a-1.0.1",
        "RESULT nix fetch over git:// on server: lib-a-1.0.1",
        "RESULT mirror: skipped without --collection; copied with it; no marker; not served",
        "RESULT STORE-010: rebuilt refs, tree files, and selected tag equal the original",
        "RESULT idle cpu ns in 15 s: ",
    )
    # The hook messages (`only release tags are accepted`, `releases are immutable`) are asserted in
    # the VM script itself (`tests/nix/infra/collection.nix`). The driver log does not echo them.


@needs_nix_fixture
@needs_vm
def test_the_private_cache_takes_a_real_push_and_a_cold_vm_substitutes(vendomat_package, tmp_path):
    log = _run_vm_test("cache", vendomat_package, tmp_path)
    _expect(
        log,
        "RESULT narinfo of the never-pushed path: HTTP 404",
        "RESULT attic push of the Vendomat package closure:",
        "RESULT upstream-signed path: skipped by Attic, absent from the Vendomat cache, present upstream",
        "RESULT NAR hash of the Vendomat package: recorded ",
        "RESULT empty chroot store in the cold VM: all ",
        "RESULT upstream-sourced path substituted from http://server:8081; the Vendomat cache did not serve it",
        "RESULT no token or signing secret in /nix/store, /etc, /var/log, the journals, or the attic client config",
    )
    assert "User does not have permission to complete this action" in log
    assert "(0 already cached, 1 in upstream)" in log


@needs_nix_fixture
@needs_vm
def test_each_build_host_builds_per_tag_and_the_other_host_substitutes(vendomat_package, tmp_path):
    log = _run_vm_test("builder-vm", vendomat_package, tmp_path)
    _expect(
        log,
        "RESULT CACHE-006: vendomat-watch-store.service is active on server and framework",
        "RESULT BUILD-002: tag alpha:v1.0.0 built alpha only",
        "RESULT BUILD-005: no push command in the units or the script",
        "RESULT BUILD-008 A: server -> framework substituted with --max-jobs 0",
        "RESULT BUILD-003/BUILD-004: broken failed with status 1, charlie still built",
        "RESULT BUILD-008 B / BOOT-017: framework -> server substituted with --max-jobs 0",
        "RESULT CACHE-009: the build log reports the upstream-signed output",
    )

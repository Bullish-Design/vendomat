"""The source collection on two NixOS machines (Step 6.3, STORE-008 and STORE-011).

A disposable NixOS test boots a `server` with the git-daemon settings from nix-meta and a `client`.
The client pushes a release tag over SSH, is refused a branch push and a moved tag, and then fetches
the tag with Nix over the virtual network. The server's idle daemon must use no CPU. This needs
/dev/kvm and a Nix with the `nixos-test` system feature. It does not touch the real `server`.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture, nix, run

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "collection-vm"

pytestmark = needs_nix_fixture


def _can_run_vm_tests() -> bool:
    if not os.access("/dev/kvm", os.R_OK | os.W_OK) or shutil.which("nix") is None:
        return False
    features = run(["nix", "config", "show", "system-features"], Path.cwd()).stdout.split()
    return "nixos-test" in features and "kvm" in features


@pytest.mark.skipif(not _can_run_vm_tests(), reason="needs /dev/kvm and the nixos-test system feature")
def test_two_machines_push_a_tag_and_fetch_it_with_nix(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path / "vm")
    installable = f"path:{tmp_path / 'vm'}#checks.x86_64-linux.collection"
    built = nix(["build", installable, "--no-link"], tmp_path)
    assert built.returncode == 0, built.stderr[-3000:]
    # The log stays in the store, so a cached run still shows the refusals and the idle cost.
    shown = nix(["log", installable], tmp_path)
    assert shown.returncode == 0, shown.stderr
    log = shown.stdout + shown.stderr
    assert "collection: only release tags are accepted, not refs/heads/main" in log
    assert "collection: refs/tags/v1.0.0 exists; releases are immutable" in log
    assert re.search(r"RESULT idle cpu ns in 15 s: \d+", log)

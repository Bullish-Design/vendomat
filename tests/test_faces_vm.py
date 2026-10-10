"""The enabled faces run in a NixOS VM (Step 3). Opt in with `testee check e2e`.

The VM test boots a NixOS guest with the system unit and the Home Manager user unit of a described
library, and checks that each runs through the start script. It needs `/dev/kvm`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENABLED = os.environ.get("VENDOMAT_E2E") == "1" and shutil.which("nix") is not None and Path("/dev/kvm").exists()
pytestmark = pytest.mark.skipif(not ENABLED, reason="NixOS VM test; set VENDOMAT_E2E=1 and provide nix and /dev/kvm")


def test_the_enabled_faces_run_in_a_vm(tmp_path):
    done = subprocess.run(
        ["nix", "build", "--impure", "--no-link", "--print-out-paths", "--file", str(ROOT / "tests/nix/faces-vm.nix")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=3000,
    )
    assert done.returncode == 0, done.stderr[-4000:]

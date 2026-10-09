"""The V5-to-V6 requirement ledger stays in step with both specifications.

`LEDGER-V6.md` is generated. This check fails when an ID collides, a successor is missing, or the
file differs from the generator's output.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".scratch" / "projects" / "16-vendomat-devenv-layer" / "ledger" / "build_ledger.py"


def test_the_ledger_is_current_and_consistent():
    done = subprocess.run([sys.executable, "-I", str(TOOL), "--check"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr

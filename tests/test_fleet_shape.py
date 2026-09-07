import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PATH = re.compile(r"(?:file://)?/(?:home|Users)/[A-Za-z0-9._-]+/")


def test_committed_manifests_have_no_machine_paths():
    bad = {
        str(path.relative_to(ROOT)): lines
        for path in (ROOT / "flake.nix", ROOT / "flake.lock", ROOT / "devenv.yaml")
        if (lines := [line for line in path.read_text().splitlines() if LOCAL_PATH.search(line)])
    }
    assert not bad, f"committed fleet files name local checkouts: {bad}"


def test_flake_lock_first_party_inputs_use_published_tags():
    lock = json.loads((ROOT / "flake.lock").read_text())
    for name in ("pyjutsu", "repoman", "copyroom", "docman", "gitman"):
        locked = lock["nodes"][name]["locked"]
        assert locked["type"] == "git"
        assert locked["url"].startswith("https://github.com/Bullish-Design/")
        assert locked["ref"].startswith("refs/tags/")


def test_local_shellij_overlay_is_ignored():
    assert "devenv.local.yaml" in (ROOT / ".gitignore").read_text()

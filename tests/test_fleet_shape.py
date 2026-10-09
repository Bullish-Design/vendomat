"""Committed files must be PORTABLE: no file may name one machine's working trees.

Vendomat is the ROOT of the chain, so this guard has no transitive exemption. Every
node in `flake.lock` must be reachable from any machine, not only the declared ones.
Repos consume vendomat by published tag and inherit its whole lock; a `file:///home/...`
pin in here exists on exactly one machine and fails everywhere else.

For local iteration, override an input at the command line instead of editing the file:

    nix build .#vendomat --override-input nixpkgs git+file:///path/to/nixpkgs
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# An absolute path under a user's home directory, in a url or on its own.
LOCAL_PATH = re.compile(r"(?:file://)?/(?:home|Users)/[A-Za-z0-9._-]+/")


def test_the_flake_declares_no_local_checkout():
    bad = [line for line in (ROOT / "flake.nix").read_text().splitlines() if LOCAL_PATH.search(line)]
    assert not bad, "flake.nix names a local checkout — pin a published tag instead:\n" + "\n".join(bad)


def test_every_locked_input_is_reachable_from_any_machine():
    # No exemption: a consumer inherits every node of this lock, not just the ones
    # vendomat declares directly.
    lock = json.loads((ROOT / "flake.lock").read_text())
    bad = {}
    for name, node in lock["nodes"].items():
        locked = node.get("locked", {})
        target = str(locked.get("url") or locked.get("path") or "")
        if LOCAL_PATH.search(target):
            bad[name] = target
    assert not bad, (
        f"flake.lock was re-locked against local checkouts: {bad}\nRe-lock from the published tags: nix flake update"
    )


def test_every_first_party_input_is_pinned_to_a_tag():
    # A branch pin is portable but not reproducible: the same lock would resolve to
    # different source on a later fetch. Vendomat's flake.lock is authoritative for the
    # toolchain revision (CONCEPT 03 §8.2), so its inputs are pinned to release tags.
    lock = json.loads((ROOT / "flake.lock").read_text())
    for name, node in lock["nodes"].items():
        locked = node.get("locked", {})
        if locked.get("type") != "git":
            continue  # github: inputs (nixpkgs) pin a rev directly
        ref = locked.get("ref", "")
        assert ref.startswith("refs/tags/"), f"input {name!r} is pinned to {ref!r}, not a release tag"
        assert locked.get("rev"), f"input {name!r} has no locked rev"

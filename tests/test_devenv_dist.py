"""Fast offline checks for the Vendomat devenv distribution (DVN-003, DVN-005).

The recipe lives in `devenv-dist/`: the upstream pin, the ordered patch series, a hash manifest,
and the materialization tool. These checks need no network and no Nix. The runtime proofs (build,
version, offline shell, install VM) are fixtures that record raw logs outside the repository.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "devenv-dist"
PATCHES = DIST / "patches"


def read_lines(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def series() -> list[str]:
    return read_lines(DIST / "SERIES")


def manifest() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read_lines(DIST / "MANIFEST.sha256"):
        digest, _, name = line.partition("  ")
        out[name.strip()] = digest.strip()
    return out


def upstream() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read_lines(DIST / "UPSTREAM"):
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def header(name: str) -> str:
    """The commit message part of a format-patch file: everything before the diffstat."""
    text = (PATCHES / name).read_text()
    return text.split("\n---\n", 1)[0]


def test_the_upstream_pin_names_tag_and_commit():
    pin = upstream()
    assert pin["tag"] == "v2.4.0"
    assert pin["commit"] == "b904dcb51fe48c30db250038241507f60752f222"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
    assert pin["fork_tag"] == "v2.4.0-vendomat.1"
    assert pin["repo"].startswith("https://github.com/cachix/devenv")


def test_the_series_lists_every_patch_file_once_in_numeric_order():
    listed = series()
    assert listed == sorted(listed)
    assert len(set(listed)) == len(listed)
    assert listed == sorted(p.name for p in PATCHES.glob("*.patch"))
    numbers = [int(name.split("-", 1)[0]) for name in listed]
    assert numbers == list(range(1, len(listed) + 1))


def test_the_manifest_matches_the_patch_bytes():
    recorded = manifest()
    assert set(recorded) == set(series())
    for name, digest in recorded.items():
        assert hashlib.sha256((PATCHES / name).read_bytes()).hexdigest() == digest, name


def test_each_patch_names_an_upstream_reference_or_says_fork_only():
    for name in series():
        lines = [line for line in header(name).splitlines() if line.startswith("Upstream:")]
        assert len(lines) == 1, name
        value = lines[0].removeprefix("Upstream:").strip()
        assert value.startswith("fork-only") or re.search(r"cachix/devenv (PR #\d+|[0-9a-f]{8,40})", value), name


def test_each_patch_is_a_plain_format_patch_with_a_fixed_header():
    for name in series():
        text = (PATCHES / name).read_text()
        assert text.startswith("From 0000000000000000000000000000000000000000 "), name
        assert re.search(r"^From: .+ <.+>$", text, re.MULTILINE), name
        assert re.search(r"^Date: .+$", text, re.MULTILINE), name
        assert re.search(r"^Subject: \[PATCH \d+/\d+\] .+$", text, re.MULTILINE), name
        assert "\ndiff --git " in text, name


def test_the_series_keeps_the_agreed_order_of_the_project_15_patches():
    names = series()
    assert len(names) >= 4
    subjects = [re.search(r"^Subject: \[PATCH[^\]]*\] (.+)$", header(n), re.MULTILINE) for n in names[:4]]
    assert all(subjects)
    texts = [m.group(1) for m in subjects if m]
    assert "SSH connection handshake" in texts[0]
    assert "latest devenv version" in texts[1]
    assert "reuse locked inputs" in texts[2]
    assert "release" in texts[3]


def test_the_adopted_host_denial_and_fresh_host_rule_are_separate_patches():
    names = series()
    adopt = [n for n in names if "adopt" in n]
    fresh = [n for n in names if "preflight" in n or "fresh" in n]
    assert len(adopt) == 1
    assert len(fresh) == 1
    assert adopt != fresh


def test_materialize_refuses_a_directory_that_is_not_empty(tmp_path: Path):
    (tmp_path / "keep").write_text("x")
    run = subprocess.run(
        [sys.executable, "-I", str(DIST / "materialize"), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "not an empty directory" in run.stderr


def test_materialize_refuses_a_patch_that_differs_from_the_manifest(tmp_path: Path):
    # Copy the recipe, change one patch byte, and expect a refusal before any git call.
    dist = tmp_path / "dist"
    (dist / "patches").mkdir(parents=True)
    for name in ("UPSTREAM", "SERIES", "MANIFEST.sha256", "materialize"):
        (dist / name).write_bytes((DIST / name).read_bytes())
    for name in series():
        (dist / "patches" / name).write_bytes((PATCHES / name).read_bytes())
    first = dist / "patches" / series()[0]
    first.write_text(first.read_text() + "\n")
    run = subprocess.run(
        [sys.executable, "-I", str(dist / "materialize"), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "does not match MANIFEST.sha256" in run.stderr
    assert not (tmp_path / "out").exists()

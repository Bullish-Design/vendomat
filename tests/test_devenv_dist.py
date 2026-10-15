"""Fast offline checks for the Vendomat devenv distribution recipe (DVN-003, DVN-005).

The recipe lives in `devenv-dist/`: the upstream pin, the module-only patch series with its hash
manifest, the two patches of the host binary, and the materialization tool. S6 retired the older
binary series (fork tag `v2.4.0-vendomat.4`). These checks need no network and no Nix. The runtime
proofs are the opt-in checks `modules-e2e`, `modules-vm`, and `binary-e2e`.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "devenv-dist"
BINARY_PATCHES = DIST / "binary" / "patches"


def read_lines(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def upstream() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read_lines(DIST / "UPSTREAM"):
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def test_the_upstream_pin_names_tag_and_commit_and_no_fork_tag():
    pin = upstream()
    assert pin["tag"] == "v2.4.0"
    assert pin["commit"] == "b904dcb51fe48c30db250038241507f60752f222"
    assert re.fullmatch(r"[0-9a-f]{40}", pin["commit"])
    assert pin["repo"].startswith("https://github.com/cachix/devenv")
    # S6: the module series owns the only fork tag.
    assert "fork_tag" not in pin


def test_the_old_binary_series_is_gone():
    for name in ("SERIES", "MANIFEST.sha256", "RESULT", "patches", "fixtures"):
        assert not (DIST / name).exists(), name


def test_the_host_binary_keeps_exactly_patches_0003_and_0005():
    names = sorted(p.name for p in BINARY_PATCHES.iterdir())
    assert names == ["0003.patch", "0005.patch"]
    digests = {n: hashlib.sha256((BINARY_PATCHES / n).read_bytes()).hexdigest() for n in names}
    assert digests == {
        "0003.patch": "c4a121b9d237740e47243754a3ec6c6b9d7dc83e7fb05f019b6e769052aaa1c5",
        "0005.patch": "85eea6e22e52fdc3103381a69fa9765305433b4273d0e728e553123c0aedd2a3",
    }  # S2 evidence: a changed hash changes the host binary


def test_materialize_needs_the_series_argument(tmp_path: Path):
    run = subprocess.run(
        [sys.executable, "-I", str(DIST / "materialize"), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "--series" in run.stderr
    assert not (tmp_path / "out").exists()


def test_materialize_refuses_a_directory_that_is_not_empty(tmp_path: Path):
    (tmp_path / "keep").write_text("x")
    run = subprocess.run(
        [sys.executable, "-I", str(DIST / "materialize"), str(tmp_path), "--series", "modules"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "not an empty directory" in run.stderr


# The module-only series (`--series modules`): upstream plus module changes, no binary changes.
MODULES = DIST / "modules"
MODULE_PATCHES = MODULES / "patches"


def module_series() -> list[str]:
    return read_lines(MODULES / "SERIES")


def module_header(name: str) -> str:
    return (MODULE_PATCHES / name).read_text().split("\n---\n", 1)[0]


def module_patch(prefix: str) -> str:
    return (MODULE_PATCHES / next(n for n in module_series() if n.startswith(prefix))).read_text()


def key_values(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in read_lines(path):
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def test_the_module_series_numbers_are_contiguous_from_m0001():
    listed = module_series()
    assert len(listed) == 5
    assert listed == sorted(p.name for p in MODULE_PATCHES.glob("*.patch"))
    numbers = [re.fullmatch(r"m(\d{4})-.+\.patch", name) for name in listed]
    assert all(numbers)
    assert [int(m.group(1)) for m in numbers if m] == list(range(1, len(listed) + 1))


def test_the_module_manifest_matches_the_patch_bytes():
    recorded: dict[str, str] = {}
    for line in read_lines(MODULES / "MANIFEST.sha256"):
        digest, _, name = line.partition("  ")
        recorded[name.strip()] = digest.strip()
    assert set(recorded) == set(module_series())
    for name, digest in recorded.items():
        assert hashlib.sha256((MODULE_PATCHES / name).read_bytes()).hexdigest() == digest, name


def test_each_module_patch_has_the_fixed_header_and_says_no_upstream_pull_request():
    total = len(module_series())
    for index, name in enumerate(module_series(), start=1):
        text = (MODULE_PATCHES / name).read_text()
        assert text.startswith("From 0000000000000000000000000000000000000000 "), name
        assert "\nFrom: Vendomat Fork <vendomat-fork@users.noreply.invalid>\n" in text, name
        assert "\nDate: Fri, 9 Oct 2026 00:00:00 +0000\n" in text, name
        assert f"\nSubject: [PATCH {index}/{total}] vendomat: " in text, name
        lines = [line for line in module_header(name).splitlines() if line.startswith("Upstream:")]
        assert lines == ["Upstream: none (Vendomat module fork; R34: no upstream pull request)"], name
        assert "\ndiff --git " in text, name


def test_the_module_patches_touch_only_module_files():
    for name in module_series():
        text = (MODULE_PATCHES / name).read_text()
        paths = set(re.findall(r"^diff --git a/(\S+) b/", text, re.MULTILINE))
        assert paths, name
        assert all(path.startswith("src/modules/") for path in paths), (name, paths)


def test_m0001_changes_only_the_nixos_option_type():
    text = module_patch("m0001-")
    body = text.split("\ndiff --git ", 1)[1]
    changed = [line for line in body.splitlines()[4:] if line[:1] in "+-"]
    assert changed == [
        "-        type = lib.types.nullOr lib.types.unspecified;",
        "+        type = lib.types.nullOr lib.types.deferredModule;",
    ]
    assert "      nixos = lib.mkOption {" in body  # the hunk context is the nixos option
    # R35: the home-manager and nix-darwin option types stay as upstream has them.
    assert "home-manager" not in "\n".join(changed)
    assert "nix-darwin" not in "\n".join(changed)


def test_m0002_sets_the_latest_version_to_2_4_0_in_that_file_only():
    text = module_patch("m0002-")
    assert re.findall(r"^diff --git a/(\S+) b/", text, re.MULTILINE) == ["src/modules/latest-version"]
    assert "\n-2.3.1\n" in text
    assert "\n+2.4.0\n\\ No newline at end of file\n" in text


def test_m0003_and_m0004_keep_the_image_options_out_of_the_build_walker():
    build = module_patch("m0003-")
    assert build.count("type = lib.types.nullOr lib.types.package;") == 2
    assert "build.vm = lib.mkOption" in build
    assert "build.iso = lib.mkOption" in build
    assert "types.output" not in build
    iso = module_patch("m0004-")
    assert "extendModules" in iso
    assert "type = lib.types.listOf lib.types.deferredModule;" in iso
    assert iso.count("lib.mkImageMediaOverride") == 4  # priority 60: files, swap, LUKS, timeout
    assert "isoImage.makeEfiBootable = true;" in iso
    assert "isoImage.makeUsbBootable = true;" in iso


def test_m0005_adds_the_vendomat_mode_option_and_copies_it_into_the_meta():
    text = module_patch("m0005-")
    assert 'lib.types.enum [ "fresh-install" "adopt-existing" ]' in text
    assert "vendomat = { inherit (m.vendomat) mode; };" in text
    assert re.findall(r"^diff --git a/(\S+) b/", text, re.MULTILINE) == ["src/modules/machines.nix"]


def test_the_module_recipe_names_the_agreed_tag_on_the_same_upstream_pin():
    pin = upstream()
    own = key_values(MODULES / "UPSTREAM")
    assert own == {"fork_tag": "v2.4.0-vendomat-modules.1"}  # R44
    result = key_values(MODULES / "RESULT")
    assert result["fork_tag"] == own["fork_tag"]
    assert result["source_commit"] == pin["commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", result["fork_commit"])


def test_the_module_patches_stay_out_of_the_binary_patches():
    assert not list(BINARY_PATCHES.glob("m0*.patch"))


def test_materialize_refuses_a_module_patch_that_differs_from_the_manifest(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "modules" / "patches").mkdir(parents=True)
    for name in ("UPSTREAM", "materialize"):
        (dist / name).write_bytes((DIST / name).read_bytes())
    for name in ("UPSTREAM", "SERIES", "MANIFEST.sha256"):
        (dist / "modules" / name).write_bytes((MODULES / name).read_bytes())
    for name in module_series():
        (dist / "modules" / "patches" / name).write_bytes((MODULE_PATCHES / name).read_bytes())
    first = dist / "modules" / "patches" / module_series()[0]
    first.write_text(first.read_text() + "\n")
    run = subprocess.run(
        [sys.executable, "-I", str(dist / "materialize"), str(tmp_path / "out"), "--series", "modules"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode != 0
    assert "does not match MANIFEST.sha256" in run.stderr
    assert not (tmp_path / "out").exists()

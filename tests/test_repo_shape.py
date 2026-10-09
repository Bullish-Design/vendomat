"""The repository holds V5 and nothing else (DEL-012).

Nothing from V4 stays in the tree: no machine plane, no knowledge tree, no wheelhouse, no toolchain
closure, no consumer devenv module. These checks fail when one comes back.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The library modules that exist. Add a name here when a V5 module is built.
MODULES = {"__init__.py", "cli.py", "generate.py", "locate.py", "registry.py", "store.py"}


def test_the_library_holds_only_v5_modules():
    found = {p.name for p in (ROOT / "src" / "vendomat").glob("*.py")}
    assert found == MODULES


def test_no_v4_directory_remains():
    for name in ("vendor", "modules", "lib", "docs", "examples", "pkgs"):
        assert not (ROOT / name).exists(), f"{name}/ is V4 and must not return"


def test_the_flake_has_nixpkgs_as_its_only_input():
    lock = json.loads((ROOT / "flake.lock").read_text())
    assert set(lock["nodes"]["root"]["inputs"]) == {"nixpkgs"}


def test_the_package_needs_only_typer():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    names = {d.split(">")[0].split("=")[0].split("<")[0].strip() for d in project["dependencies"]}
    assert names == {"typer"}

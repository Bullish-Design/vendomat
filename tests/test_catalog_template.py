"""The fixed workspace template and the catalog module files (DOOR-074, DOOR-075).

These checks read files. They need neither Nix nor the devenv fork. `test_catalog_module_nix.py`
evaluates the module.
"""

from __future__ import annotations

from pathlib import Path

from vendomat.yamlsubset import parse

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace"
MODULE = ROOT / "devenv"


def test_the_template_holds_the_four_fixed_files():
    # `devenv.lock` is the fourth workspace file. devenv writes it on first use; no generated file ships.
    found = {p.name for p in TEMPLATE.iterdir()}
    assert found == {"vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore"}


def test_the_template_devenv_yaml_names_the_release_input_and_the_catalog_import():
    data = parse((TEMPLATE / "devenv.yaml").read_text())
    assert set(data) == {"inputs", "imports"}
    # A `git://` URL locks a `rev`; `git+file` does not (P2C).
    assert data["inputs"]["vendomat"] == {"url": "git://server/vendomat?ref=release"}
    assert data["inputs"]["nixpkgs"] == {"follows": "vendomat/nixpkgs"}
    assert set(data["inputs"]) == {"vendomat", "nixpkgs"}
    assert data["imports"] == ["vendomat/devenv"]


def test_the_template_devenv_nix_is_empty():
    assert (TEMPLATE / "devenv.nix").read_text().split() == ["{", "}"]


def test_the_template_vendomat_yaml_is_an_empty_catalog_with_comments():
    text = (TEMPLATE / "vendomat.yaml").read_text()
    assert parse(text) == {}
    # The example sits under a bare `#` line. Remove the leading `# ` and it is a valid catalog.
    lines = text.splitlines()
    example = "\n".join(line.removeprefix("# ").removeprefix("#") for line in lines[lines.index("#") + 1 :])
    assert set(parse(example)) == {"programs", "languages", "services", "env"}


def test_the_template_ignores_the_devenv_state():
    lines = (TEMPLATE / ".gitignore").read_text().split()
    assert ".devenv*" in lines


def test_the_module_directory_declares_only_the_language_inputs():
    data = parse((MODULE / "devenv.yaml").read_text())
    assert set(data) == {"inputs"}
    # The workspace sets `nixpkgs`; a module input of that name would be ignored.
    assert set(data["inputs"]) == {"nixpkgs-python", "rust-overlay"}
    for spec in data["inputs"].values():
        assert spec["inputs"]["nixpkgs"] == {"follows": "nixpkgs"}


def test_the_module_reads_the_file_with_the_primop_and_no_unsafe_setting():
    text = (MODULE / "devenv.nix").read_text()
    assert "vendomatFromYAML file (builtins.readFile path)" in text
    assert "builtins.pathExists path" in text
    for banned in ("allow-unsafe-native-code", "builtins.exec", "fromTOML", "getEnv", "--impure"):
        assert banned not in text


def test_the_old_template_files_moved_to_workspace_v6():
    old = ROOT / "templates" / "workspace-v6"
    assert {p.name for p in old.iterdir()} == {"devenv.nix", "devenv.yaml", "init"}
    init = (old / "init").read_text()
    assert "$templates/workspace-v6/devenv.nix" in init
    assert "$templates/workspace/" not in init
    flake = (ROOT / "flake.nix").read_text()
    assert "templates/workspace-v6/init" in flake

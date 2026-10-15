"""The fixed workspace template and the catalog module files (VMT-003, VMT-020, VMT-043).

These checks read files. They need neither Nix nor devenv. `test_catalog_module_nix.py` evaluates the
module and `test_catalog_parser_nix.py` runs the parser.
"""

from __future__ import annotations

import re
from pathlib import Path

from vendomat.yamlsubset import parse

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace"
MODULE = ROOT / "devenv"


def test_the_template_holds_the_four_fixed_files():
    # `devenv.lock` is the fourth workspace file. devenv writes it on first use; no generated file ships.
    found = {p.name for p in TEMPLATE.iterdir()}
    assert found == {"vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore"}


def test_the_template_devenv_yaml_lists_every_input_the_catalog_needs():
    # VMT-043, R11, R28, R41. Stock devenv ignores the `devenv.yaml` of an imported input, so the template
    # lists the inputs. `vendomat update` brings the lines to an older workspace (R25).
    data = parse((TEMPLATE / "devenv.yaml").read_text())
    assert set(data) == {"inputs", "imports"}
    # A `git://` URL locks a `rev`; `git+file` does not (P2C).
    assert data["inputs"]["vendomat"] == {"url": "git://server/vendomat?ref=release"}
    assert data["inputs"]["nixpkgs"] == {"follows": "vendomat/nixpkgs"}
    assert data["inputs"]["devenv"] == {"follows": "vendomat/devenv"}
    for name in ("nixpkgs-python", "rust-overlay"):
        assert data["inputs"][name]["url"].startswith("github:")
        assert data["inputs"][name]["inputs"] == {"nixpkgs": {"follows": "nixpkgs"}}
    assert set(data["inputs"]) == {"vendomat", "nixpkgs", "devenv", "nixpkgs-python", "rust-overlay"}
    assert data["imports"] == ["vendomat/devenv"]


def test_the_template_pins_no_devenv_version():
    # The host binary and the module input carry the version. `require_version` would only add a failure.
    assert "require_version" not in (TEMPLATE / "devenv.yaml").read_text()


def test_the_template_devenv_nix_is_empty():
    assert (TEMPLATE / "devenv.nix").read_text().split() == ["{", "}"]


def test_the_template_vendomat_yaml_is_an_empty_catalog_with_comments():
    text = (TEMPLATE / "vendomat.yaml").read_text()
    assert parse(text) == {}
    # The example sits under a bare `#` line. Remove the leading `# ` and it is a valid catalog.
    lines = text.splitlines()
    example = "\n".join(line.removeprefix("# ").removeprefix("#") for line in lines[lines.index("#") + 1 :])
    assert set(parse(example)) == {"programs", "languages", "services", "env", "machines", "settings"}


def test_the_template_ignores_the_devenv_state():
    lines = (TEMPLATE / ".gitignore").read_text().split()
    assert ".devenv*" in lines


def test_the_module_directory_declares_no_input():
    # It existed for fork patch 0007, which is gone. The template lists the inputs instead.
    names = sorted(p.name for p in MODULE.iterdir())
    assert names == ["devenv.nix", "explain.nix", "hatch.nix", "parse.nix", "sharing.nix"]


def test_the_module_reads_the_file_with_the_nix_parser_and_no_unsafe_setting():
    text = (MODULE / "devenv.nix").read_text()
    assert "import ./parse.nix" in text
    assert "builtins.pathExists path" in text
    assert "vendomatFromYAML" not in text and "devenvPrimops" not in text
    for banned in ("allow-unsafe-native-code", "builtins.exec", "fromTOML", "getEnv", "--impure"):
        assert banned not in text


def test_the_module_maps_no_home_key_and_builds_no_extension_point():
    # R35 (VMT-122) and R38: the keys of Basix live in `basix.yaml`.
    text = (MODULE / "devenv.nix").read_text()
    assert re.search(r"^\s*home(-manager)?\s*=", text, re.M) is None
    assert "options.vendomat.catalog" not in text and "extensions" not in text


def test_the_old_template_files_moved_to_workspace_v6():
    old = ROOT / "templates" / "workspace-v6"
    assert {p.name for p in old.iterdir()} == {"devenv.nix", "devenv.yaml", "init"}
    init = (old / "init").read_text()
    assert "$templates/workspace-v6/devenv.nix" in init
    assert "$templates/workspace/" not in init
    flake = (ROOT / "flake.nix").read_text()
    assert "templates/workspace-v6/init" in flake

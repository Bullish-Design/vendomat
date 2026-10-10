"""The V6 registry tables: `[imports]`, `[targets]`, and the `dir` key (`REG-022`, `PRE-001`)."""

from __future__ import annotations

import pytest

from vendomat.registry import RegistryError, parse_registry

BASE = """\
[forge]
url = "git://server"

[inputs]
lib-a = { ref = "refs/tags/v1.0.0" }
nixpkgs = { url = "github:NixOS/nixpkgs", rev = "e7439b6b14ad3cc35d05608ebca9bce01a25f5f8", ref = "refs/tags/x" }
"""


def test_a_registry_without_targets_selects_the_flake_target_only():
    registry = parse_registry(BASE)
    assert registry.targets.flake is True
    assert registry.targets.devenv is False
    assert registry.imports == ()


def test_targets_select_the_outputs():
    registry = parse_registry(BASE + "\n[targets]\ndevenv = true\n")
    assert (registry.targets.flake, registry.targets.devenv) == (False, True)
    both = parse_registry(BASE + "\n[targets]\ndevenv = true\nflake = true\n")
    assert (both.targets.flake, both.targets.devenv) == (True, True)


def test_a_targets_table_that_selects_nothing_is_an_error():
    with pytest.raises(RegistryError, match="selects no output"):
        parse_registry(BASE + "\n[targets]\ndevenv = false\n")


def test_an_unknown_target_key_is_an_error():
    with pytest.raises(RegistryError, match="unknown key 'nix'"):
        parse_registry(BASE + "\n[targets]\nnix = true\n")


def test_imports_normalize_to_input_and_directory():
    registry = parse_registry(BASE + '\n[imports]\nlib-a = ["devenv", "extra/sub", "."]\n')
    assert registry.imports == ("lib-a", "lib-a/devenv", "lib-a/extra/sub")


def test_an_import_of_an_unknown_input_is_an_error():
    with pytest.raises(RegistryError, match="not a direct input"):
        parse_registry(BASE + '\n[imports]\nghost = "devenv"\n')


@pytest.mark.parametrize("directory", ["../up", "/abs", "a/../b"])
def test_an_import_directory_must_stay_inside_the_input(directory):
    with pytest.raises(RegistryError, match="invalid directory"):
        parse_registry(BASE + f'\n[imports]\nlib-a = "{directory}"\n')


def test_the_dir_key_becomes_a_url_query_parameter():
    text = (
        BASE
        + '\ndevenv-src = { url = "git://server/devenv", ref = "refs/tags/v2.4.0-vendomat.2", dir = "src/modules" }\n'
    )
    registry = parse_registry(text)
    url = {s.name: s.url for s in registry.sources}["devenv-src"]
    assert url == "git://server/devenv?ref=refs/tags/v2.4.0-vendomat.2&dir=src/modules"


def test_an_unknown_table_names_the_allowed_tables():
    with pytest.raises(RegistryError, match=r"\[imports\], or \[targets\]"):
        parse_registry(BASE + "\n[other]\nx = 1\n")


def test_the_flake_digest_ignores_imports_and_targets():
    plain = parse_registry(BASE)
    extra = parse_registry(BASE + '\n[imports]\nlib-a = "devenv"\n\n[targets]\nflake = true\ndevenv = true\n')
    assert plain.digest == extra.digest

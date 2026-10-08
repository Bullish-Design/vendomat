"""The V5 registry reader (REG-001 to REG-015)."""

from __future__ import annotations

import json

import pytest

from vendomat.registry import RegistryError, parse_registry

VALID = """
[inputs]
mod-pkg = { url = "git+https://host.example/andrew/mod-pkg" }
data = { url = "path:./data", flake = false }

[passthrough]
nixpkgs = { url = "github:cachix/devenv-nixpkgs/rolling" }

[follows]
mod-pkg = ["nixpkgs"]
"""


def test_valid_registry_sorts_sources_by_name():
    registry = parse_registry(VALID)
    assert [s.name for s in registry.sources] == ["data", "mod-pkg", "nixpkgs"]
    assert registry.sources[0].flake is False
    assert registry.sources[1].follows == ("nixpkgs",)
    assert registry.digest.startswith("sha256-")


def test_digest_ignores_comments_spacing_and_order():
    reordered = """
# a comment
[follows]
mod-pkg = ["nixpkgs"]

[passthrough]
nixpkgs = {url="github:cachix/devenv-nixpkgs/rolling"}

[inputs]
data = { flake = false, url = "path:./data" }
mod-pkg = { url = "git+https://host.example/andrew/mod-pkg" }
"""
    assert parse_registry(reordered).digest == parse_registry(VALID).digest


def test_digest_changes_with_content():
    other = VALID.replace("andrew/mod-pkg", "andrew/other")
    assert parse_registry(other).digest != parse_registry(VALID).digest


def test_two_inputs_tables_are_a_parse_error():
    with pytest.raises(RegistryError, match="vendomat.toml: cannot parse"):
        parse_registry('[inputs]\na = { url = "x:y" }\n[inputs]\nb = { url = "x:y" }\n')


def test_missing_inputs_table_is_an_error():
    with pytest.raises(RegistryError, match=r"needs an \[inputs\] table"):
        parse_registry("[passthrough]\n")


def test_empty_inputs_table_is_valid():
    assert parse_registry("[inputs]\n").sources == ()


def test_unparseable_registry_names_file_and_line():
    with pytest.raises(RegistryError, match=r"my.toml: cannot parse the registry: .*line 2"):
        parse_registry("[inputs]\nthis is not toml\n", "my.toml")


def test_bad_name_is_rejected_and_named():
    with pytest.raises(RegistryError, match="Nvim_Review"):
        parse_registry('[inputs]\nNvim_Review = { url = "x:y" }\n')


def test_unknown_key_is_rejected_and_named():
    with pytest.raises(RegistryError, match="unknown key 'revision'"):
        parse_registry('[inputs]\na = { url = "x:y", revision = "abc" }\n')


def test_empty_entry_fails_because_vendomat_does_not_guess_a_source():
    with pytest.raises(RegistryError, match="needs a 'url'"):
        parse_registry("[inputs]\na = {}\n")


def test_unknown_top_level_table_is_rejected():
    with pytest.raises(RegistryError, match=r"unknown table \[follow\]"):
        parse_registry('[inputs]\na = { url = "x:y" }\n[follow]\n')


def test_name_in_both_tables_is_rejected():
    text = '[inputs]\nnixpkgs = { url = "x:y" }\n[passthrough]\nnixpkgs = { url = "x:z" }\n'
    with pytest.raises(RegistryError, match="'nixpkgs' appears in both"):
        parse_registry(text)


@pytest.mark.parametrize("bad", ["a b", 'a"b', "a\\b", "a$b", "a#frag", "a\x08b", "a\nb"])
def test_unsafe_url_characters_are_rejected(bad: str):
    # JSON string syntax is valid TOML, so json.dumps writes any value safely.
    with pytest.raises(RegistryError, match="not a valid url"):
        parse_registry(f"[inputs]\na = {{ url = {json.dumps('x:' + bad)} }}\n")


def test_ref_and_rev_become_url_query_parameters():
    rev = "a" * 40
    registry = parse_registry(f'[inputs]\na = {{ url = "git+https://h/a", ref = "refs/tags/v1.0.0", rev = "{rev}" }}\n')
    assert registry.sources[0].url == f"git+https://h/a?ref=refs/tags/v1.0.0&rev={rev}"


def test_ref_joins_an_existing_query_with_an_ampersand():
    registry = parse_registry('[inputs]\na = { url = "git+https://h/a?dir=sub", ref = "main" }\n')
    assert registry.sources[0].url == "git+https://h/a?dir=sub&ref=main"


def test_ref_set_twice_is_rejected():
    with pytest.raises(RegistryError, match="sets 'ref' and also carries 'ref='"):
        parse_registry('[inputs]\na = { url = "git+https://h/a?ref=main", ref = "dev" }\n')


@pytest.mark.parametrize("key,value", [("ref", "a b"), ("ref", "a&b"), ("rev", "xyz"), ("rev", "ABC" * 14)])
def test_bad_ref_or_rev_is_rejected(key: str, value: str):
    with pytest.raises(RegistryError, match=f"'{key}' in entry 'a'"):
        parse_registry(f'[inputs]\na = {{ url = "git+https://h/a", {key} = "{value}" }}\n')


def test_flake_must_be_boolean():
    with pytest.raises(RegistryError, match="'flake' in entry 'a'"):
        parse_registry('[inputs]\na = { url = "x:y", flake = "no" }\n')


@pytest.mark.parametrize(
    ("follows", "message"),
    [
        ('ghost = ["nixpkgs"]', "'ghost', which is not a direct input"),
        ('data = ["nixpkgs"]', "which has flake = false"),
        ('nixpkgs = ["nixpkgs"]', "cannot make 'nixpkgs' follow itself"),
        ('mod-pkg = ["other"]', "only 'nixpkgs' is supported"),
        ("mod-pkg = []", "non-empty list"),
        ('mod-pkg = ["nixpkgs", "nixpkgs"]', "distinct"),
        ('mod-pkg = "nixpkgs"', "non-empty list"),
    ],
)
def test_follows_validation(follows: str, message: str):
    text = VALID.replace('mod-pkg = ["nixpkgs"]', follows)
    with pytest.raises(RegistryError, match=message):
        parse_registry(text)


def test_follows_needs_a_root_nixpkgs():
    text = '[inputs]\na = { url = "x:y" }\n[follows]\na = ["nixpkgs"]\n'
    with pytest.raises(RegistryError, match="needs a 'nixpkgs' entry"):
        parse_registry(text)

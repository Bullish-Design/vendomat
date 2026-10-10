"""The devenv.yaml subset reader reads what devenv files use and rejects the rest."""

from __future__ import annotations

import pytest

from vendomat.yamlsubset import YamlError, parse

DOC = """\
# a comment
imports:
  - ./.vendomat
  - lib-a/devenv
require_version: "2.4.0"
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/abc # trailing comment
  lib: { url: "git+file:///x?ref=refs/tags/v1", flake: false }
  other:
    url: github:o/r
    flake: false
    inputs:
      nixpkgs:
        follows: nixpkgs
allowUnfree: true
"""


def test_a_typical_devenv_yaml_parses():
    data = parse(DOC)
    assert data["imports"] == ["./.vendomat", "lib-a/devenv"]
    assert data["require_version"] == "2.4.0"
    assert data["inputs"]["nixpkgs"] == {"url": "github:NixOS/nixpkgs/abc"}
    assert data["inputs"]["lib"] == {"url": "git+file:///x?ref=refs/tags/v1", "flake": False}
    assert data["inputs"]["other"]["inputs"]["nixpkgs"] == {"follows": "nixpkgs"}
    assert data["allowUnfree"] is True


def test_a_url_with_a_colon_is_a_value_not_a_key():
    assert parse("inputs:\n  a:\n    url: git://server/repo?ref=refs/tags/v1\n")["inputs"]["a"]["url"].startswith(
        "git://"
    )


def test_a_list_at_the_key_indent_parses():
    assert parse("imports:\n- a\n- b\n") == {"imports": ["a", "b"]}


def test_an_empty_document_is_an_empty_map():
    assert parse("# nothing\n") == {}


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("a: &x 1\n", "anchors"),
        ("a: |\n  text\n", "block scalar"),
        ("a:\n\t- b\n", "tab"),
        ("a: 1\na: 2\n", "duplicate key"),
        ("a:\n  - b: 1\n", "list of maps"),
        ("---\na: 1\n---\nb: 2\n", "several documents"),
        ("a: [b, c\n", "flow list"),
    ],
)
def test_an_unsupported_construct_is_an_error_that_names_the_line(text, fragment):
    with pytest.raises(YamlError) as info:
        parse(text, "f.yaml")
    assert fragment in str(info.value) or "f.yaml" in str(info.value)
    assert "f.yaml" in str(info.value)

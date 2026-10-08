"""The V5 registry reader (REG-001 to REG-020)."""

from __future__ import annotations

import json

import pytest

from vendomat.registry import RegistryError, parse_registry

VALID = """
[forge]
url = "git://server"

[inputs]
mod-pkg = { ref = "refs/tags/v1.0.0" }
data = { url = "path:./data", flake = false }

[passthrough]
nixpkgs = { url = "github:cachix/devenv-nixpkgs/rolling" }

[follows]
mod-pkg = ["nixpkgs"]
"""

REV = "a" * 40


def test_valid_registry_sorts_sources_by_name():
    registry = parse_registry(VALID)
    assert [s.name for s in registry.sources] == ["data", "mod-pkg", "nixpkgs"]
    assert registry.sources[0].flake is False
    assert registry.sources[1].follows == ("nixpkgs",)
    assert registry.digest.startswith("sha256-")
    assert registry.forge == "git://server"


def test_digest_ignores_comments_spacing_and_order():
    reordered = """
# a comment
[follows]
mod-pkg = ["nixpkgs"]

[passthrough]
nixpkgs = {url="github:cachix/devenv-nixpkgs/rolling"}

[inputs]
data = { flake = false, url = "path:./data" }
mod-pkg = { ref = "refs/tags/v1.0.0" }

[forge]
url = "git://server/"
"""
    assert parse_registry(reordered).digest == parse_registry(VALID).digest


def test_digest_changes_with_the_tag():
    assert parse_registry(VALID.replace("v1.0.0", "v1.1.0")).digest != parse_registry(VALID).digest


def test_two_inputs_tables_are_a_parse_error():
    with pytest.raises(RegistryError, match="vendomat.toml: cannot parse"):
        parse_registry('[inputs]\na = { url = "path:./a" }\n[inputs]\nb = { url = "path:./b" }\n')


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
        parse_registry('[inputs]\nNvim_Review = { url = "path:./a" }\n')


def test_unknown_key_is_rejected_and_named():
    with pytest.raises(RegistryError, match="unknown key 'revision'"):
        parse_registry('[inputs]\na = { url = "path:./a", revision = "abc" }\n')


def test_unknown_top_level_table_is_rejected():
    with pytest.raises(RegistryError, match=r"unknown table \[follow\]"):
        parse_registry('[inputs]\na = { url = "path:./a" }\n[follow]\n')


def test_name_in_both_tables_is_rejected():
    text = '[inputs]\nnixpkgs = { url = "path:./a" }\n[passthrough]\nnixpkgs = { url = "x:z" }\n'
    with pytest.raises(RegistryError, match="'nixpkgs' appears in both"):
        parse_registry(text)


@pytest.mark.parametrize("bad", ["a b", 'a"b', "a\\b", "a$b", "a#frag", "a\x08b", "a\nb"])
def test_unsafe_url_characters_are_rejected(bad: str):
    # JSON string syntax is valid TOML, so json.dumps writes any value safely.
    with pytest.raises(RegistryError, match="not a valid url"):
        parse_registry(f"[inputs]\na = {{ url = {json.dumps('x:' + bad)} }}\n")


# --- the collection (REG-016) ---------------------------------------------------------------


def test_forge_entry_resolves_to_the_collection_and_carries_its_tag():
    mod = parse_registry(VALID).sources[1]
    assert mod.url == "git://server/mod-pkg?ref=refs/tags/v1.0.0"
    assert mod.in_forge


def test_repo_names_a_forge_repository_that_an_input_name_cannot_spell():
    text = '[forge]\nurl = "git://server"\n[inputs]\nloci-nvim = { repo = "loci.nvim", ref = "refs/tags/v2" }\n'
    assert parse_registry(text).sources[0].url == "git://server/loci.nvim?ref=refs/tags/v2"


def test_repo_and_url_together_are_rejected():
    text = '[forge]\nurl = "git://s"\n[inputs]\na = { url = "path:./a", repo = "x" }\n'
    with pytest.raises(RegistryError, match="sets 'repo' and 'url'"):
        parse_registry(text)


def test_bad_repo_name_is_rejected():
    with pytest.raises(RegistryError, match="'repo' in entry 'a'"):
        parse_registry('[forge]\nurl = "git://s"\n[inputs]\na = { repo = "../x", ref = "refs/tags/v1" }\n')


def test_entry_without_url_needs_a_forge_table():
    with pytest.raises(RegistryError, match=r"no \[forge\] table"):
        parse_registry('[inputs]\na = { ref = "refs/tags/v1" }\n')


def test_passthrough_entry_always_needs_its_own_url():
    with pytest.raises(RegistryError, match=r"\[passthrough\] entry 'nixpkgs' needs a 'url'"):
        parse_registry('[forge]\nurl = "git://s"\n[inputs]\n[passthrough]\nnixpkgs = { ref = "main" }\n')


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[forge]\n[inputs]\n", "needs a 'url'"),
        ('[forge]\nurl = "git://s?x=1"\n[inputs]\n', "without a query"),
        ('[forge]\nurl = "git://s"\nhost = "x"\n[inputs]\n', "unknown key 'host' in \\[forge\\]"),
        ('forge = "git://s"\n[inputs]\n', "\\[forge\\] must be a table"),
    ],
)
def test_forge_table_errors(text: str, message: str):
    with pytest.raises(RegistryError, match=message):
        parse_registry(text)


# --- pinning (REG-017) ----------------------------------------------------------------------


def test_empty_entry_fails_because_vendomat_does_not_guess_a_source():
    with pytest.raises(RegistryError, match="must pin a tag"):
        parse_registry('[forge]\nurl = "git://s"\n[inputs]\na = {}\n')


@pytest.mark.parametrize(
    "pin",
    ["", ', ref = "main"', ', ref = "refs/heads/main"', ', ref = "refs/tags/"', f', rev = "{REV}"'],
)
def test_an_input_without_a_tag_is_rejected(pin: str):
    with pytest.raises(RegistryError, match="entry 'a' must pin a tag"):
        parse_registry(f'[inputs]\na = {{ url = "git+https://h/a"{pin} }}\n')


def test_a_rev_alone_gets_its_own_hint():
    with pytest.raises(RegistryError, match="A rev alone is not enough"):
        parse_registry(f'[inputs]\na = {{ url = "git+https://h/a", rev = "{REV}" }}\n')


def test_a_tag_may_carry_a_rev_as_a_second_guard():
    registry = parse_registry(f'[inputs]\na = {{ url = "git+https://h/a", ref = "refs/tags/v1.0.0", rev = "{REV}" }}\n')
    assert registry.sources[0].url == f"git+https://h/a?ref=refs/tags/v1.0.0&rev={REV}"


def test_a_tag_in_the_url_query_counts_as_a_pin():
    registry = parse_registry('[inputs]\na = { url = "git+https://h/a?ref=refs/tags/v1" }\n')
    assert registry.sources[0].url == "git+https://h/a?ref=refs/tags/v1"


def test_path_urls_and_passthrough_entries_need_no_tag():
    registry = parse_registry('[inputs]\na = { url = "path:./a" }\n[passthrough]\nnixpkgs = { url = "x:np/rolling" }\n')
    assert [s.url for s in registry.sources] == ["path:./a", "x:np/rolling"]


def test_ref_joins_an_existing_query_with_an_ampersand():
    registry = parse_registry('[inputs]\na = { url = "git+https://h/a?dir=sub", ref = "refs/tags/v1" }\n')
    assert registry.sources[0].url == "git+https://h/a?dir=sub&ref=refs/tags/v1"


def test_ref_set_twice_is_rejected():
    with pytest.raises(RegistryError, match="sets 'ref' and also carries 'ref='"):
        parse_registry('[inputs]\na = { url = "git+https://h/a?ref=refs/tags/v1", ref = "refs/tags/v2" }\n')


@pytest.mark.parametrize("key,value", [("ref", "a b"), ("ref", "a&b"), ("rev", "xyz"), ("rev", "ABC" * 14)])
def test_bad_ref_or_rev_is_rejected(key: str, value: str):
    with pytest.raises(RegistryError, match=f"'{key}' in entry 'a'"):
        parse_registry(f'[inputs]\na = {{ url = "git+https://h/a", {key} = "{value}" }}\n')


def test_flake_must_be_boolean():
    with pytest.raises(RegistryError, match="'flake' in entry 'a'"):
        parse_registry('[inputs]\na = { url = "path:./a", flake = "no" }\n')


# --- mirror, keep, backup (REG-018 to REG-020) ----------------------------------------------

THIRD_PARTY = 'url = "github:upstream/telescope.nvim", ref = "refs/tags/v0.1.8"'


def test_mirror_and_keep_are_flags_on_inputs_and_default_to_false():
    plain = parse_registry(f"[inputs]\nt = {{ {THIRD_PARTY} }}\n").sources[0]
    flagged = parse_registry(f"[inputs]\nt = {{ {THIRD_PARTY}, mirror = true, keep = true }}\n").sources[0]
    assert (plain.mirror, plain.keep) == (False, False)
    assert (flagged.mirror, flagged.keep) == (True, True)
    assert flagged.url == plain.url  # a reading copy never changes where Nix fetches


def test_mirror_needs_an_upstream_url():
    text = '[forge]\nurl = "git://s"\n[inputs]\na = { ref = "refs/tags/v1", mirror = true }\n'
    with pytest.raises(RegistryError, match="already in the collection"):
        parse_registry(text)


def test_a_forge_entry_may_be_kept():
    text = '[forge]\nurl = "git://s"\n[inputs]\na = { ref = "refs/tags/v1", keep = true }\n'
    assert parse_registry(text).sources[0].keep


@pytest.mark.parametrize("name", ["nixpkgs", "devenv"])
@pytest.mark.parametrize("flag", ["mirror", "keep"])
def test_nixpkgs_and_devenv_are_never_copied(name: str, flag: str):
    text = f'[inputs]\n{name} = {{ url = "github:o/{name}", ref = "refs/tags/v1", {flag} = true }}\n'
    with pytest.raises(RegistryError, match="never copied locally"):
        parse_registry(text)


@pytest.mark.parametrize("flag", ["mirror", "keep"])
def test_passthrough_entries_cannot_be_copied(flag: str):
    text = f'[inputs]\n[passthrough]\nother = {{ url = "x:o", {flag} = true }}\n'
    with pytest.raises(RegistryError, match=f"'{flag}' is not allowed in \\[passthrough\\]"):
        parse_registry(text)


def test_mirror_must_be_boolean():
    with pytest.raises(RegistryError, match="'mirror' in entry 't'"):
        parse_registry(f'[inputs]\nt = {{ {THIRD_PARTY}, mirror = "yes" }}\n')


def test_backup_is_kept_as_data_on_any_entry():
    text = (
        f'[inputs]\nt = {{ {THIRD_PARTY}, backup = "https://backup.example/t" }}\n'
        '[passthrough]\nnixpkgs = { url = "x:np", backup = "https://backup.example/np" }\n'
    )
    assert [s.backup for s in parse_registry(text).sources] == ["https://backup.example/np", "https://backup.example/t"]


def test_backup_must_be_a_safe_url():
    with pytest.raises(RegistryError, match="'backup' in entry 't'"):
        parse_registry(f'[inputs]\nt = {{ {THIRD_PARTY}, backup = "a b" }}\n')


# --- follows (REG-011, REG-014) -------------------------------------------------------------


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
    text = '[inputs]\na = { url = "path:./a" }\n[follows]\na = ["nixpkgs"]\n'
    with pytest.raises(RegistryError, match="needs a 'nixpkgs' entry"):
        parse_registry(text)

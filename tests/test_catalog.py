"""Validation tests for the committed Python source catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from vendomat.catalog import CatalogEntry, CatalogError, read_catalog

REV = "0123456789abcdef0123456789abcdef01234567"


def _entry(*, name: str = "pydantic", kind: str = "vendor", local: str = 'cache = "pydantic"') -> str:
    return (
        "[package]\n"
        f'name = "{name}"\n'
        f'kind = "{kind}"\n'
        'repository = "https://github.com/pydantic/pydantic"\n'
        f'rev = "{REV}"\n\n'
        "[local]\n"
        f"{local}\n"
    )


def test_catalog_entry_requires_normalized_distribution_name():
    with pytest.raises(ValueError, match="normalized"):
        CatalogEntry.from_toml(_entry(name="Pydantic"))


@pytest.mark.parametrize(
    "cache",
    ["/tmp/pydantic", "vendor/src/../pydantic", "../pydantic"],
)
def test_vendor_cache_must_be_safe_and_vendomat_relative(cache):
    with pytest.raises(ValueError, match="cache"):
        CatalogEntry.from_toml(_entry(local=f'cache = "{cache}"'))


def test_project_entry_requires_path_and_allows_parent_reference():
    entry = CatalogEntry.from_toml(_entry(name="knappy", kind="project", local='path = "../knappy"'))
    assert entry.package.name == "knappy"
    assert entry.local.path == Path("../knappy")
    assert entry.local.cache is None


def test_project_entry_rejects_absolute_path():
    with pytest.raises(ValueError, match="consumer-relative"):
        CatalogEntry.from_toml(_entry(name="knappy", kind="project", local='path = "/tmp/knappy"'))


def test_read_catalog_rejects_filename_name_mismatch_and_duplicate_names(tmp_path):
    catalog = tmp_path / "vendor/python"
    catalog.mkdir(parents=True)
    (catalog / "wrong.toml").write_text(_entry())
    with pytest.raises(CatalogError, match="filename"):
        read_catalog(tmp_path)

    (catalog / "wrong.toml").rename(catalog / "pydantic.toml")
    (catalog / "pydantic-copy.toml").write_text(_entry())
    with pytest.raises(CatalogError, match="filename|duplicate"):
        read_catalog(tmp_path)


def test_read_catalog_returns_entries_in_deterministic_name_order(tmp_path):
    catalog = tmp_path / "vendor/python"
    catalog.mkdir(parents=True)
    (catalog / "pydantic.toml").write_text(_entry())
    (catalog / "knappy.toml").write_text(_entry(name="knappy", kind="project", local='path = "../knappy"'))

    assert list(read_catalog(tmp_path)) == ["knappy", "pydantic"]

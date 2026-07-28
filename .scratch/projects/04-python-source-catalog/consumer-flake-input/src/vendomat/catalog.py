"""Validated, committed policy for Python source-grounding checkouts."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Literal, Self

import tomli_w
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from .deps import normalize

CATALOG_DIR = Path("vendor/python")
_FULL_REV = re.compile(r"^[0-9a-f]{40}$")


class CatalogError(RuntimeError):
    """Committed catalog policy is absent, malformed, or internally inconsistent."""


class PackageSpec(BaseModel):
    """The upstream identity and reviewed immutable revision for one distribution."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["project", "vendor"]
    repository: str
    rev: str

    @field_validator("name")
    @classmethod
    def _name_is_normalized(cls, value: str) -> str:
        if not value or normalize(value) != value:
            raise ValueError(f"package name must be PEP 503-normalized, got {value!r}")
        return value

    @field_validator("repository")
    @classmethod
    def _repository_is_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("repository must be non-empty")
        return value

    @field_validator("rev")
    @classmethod
    def _rev_is_full_commit(cls, value: str) -> str:
        if not _FULL_REV.fullmatch(value):
            raise ValueError("rev must be a full 40-character lowercase hexadecimal Git commit")
        return value


class LocalSpec(BaseModel):
    """The consumer-relative project path or global-source-root-relative vendor cache."""

    model_config = ConfigDict(extra="forbid")

    path: Path | None = None
    cache: Path | None = None


class CatalogEntry(BaseModel):
    """One ``vendor/python/<distribution>.toml`` document."""

    model_config = ConfigDict(extra="forbid")

    package: PackageSpec
    local: LocalSpec

    @model_validator(mode="after")
    def _local_shape_matches_kind(self) -> Self:
        if self.package.kind == "project":
            if self.local.path is None or self.local.cache is not None:
                raise ValueError("project entry requires local.path and forbids local.cache")
        elif self.local.cache is None or self.local.path is not None:
            raise ValueError("vendor entry requires local.cache and forbids local.path")

        project_path = self.local.path
        if project_path is not None and (project_path.is_absolute() or project_path == Path(".")):
            raise ValueError("project path must be a non-empty consumer-relative path")
        cache = self.local.cache
        if cache is not None and (cache.is_absolute() or cache == Path(".") or ".." in cache.parts):
            raise ValueError("vendor cache must be relative to the global source root without '..' traversal")
        return self

    @classmethod
    def from_toml(cls, text: str) -> CatalogEntry:
        """Parse and validate one catalog TOML document."""

        return cls.model_validate(tomllib.loads(text))

    def to_toml(self) -> str:
        """Render deterministic TOML, primarily for local-repository integration tests."""

        return tomli_w.dumps(self.model_dump(mode="json", exclude_none=True))


def read_catalog(vendomat_root: Path) -> dict[str, CatalogEntry]:
    """Read every committed catalog entry, keyed in deterministic normalized-name order."""

    catalog_dir = vendomat_root / CATALOG_DIR
    if not catalog_dir.is_dir():
        raise CatalogError(f"catalog directory is missing: {catalog_dir}")

    entries: dict[str, CatalogEntry] = {}
    for path in sorted(catalog_dir.glob("*.toml")):
        try:
            entry = CatalogEntry.from_toml(path.read_text())
        except (OSError, tomllib.TOMLDecodeError, ValidationError, ValueError) as exc:
            raise CatalogError(f"malformed catalog entry {path}: {exc}") from exc
        name = entry.package.name
        if path.stem != name:
            raise CatalogError(f"catalog filename {path.name!r} must match normalized package name {name!r}")
        if name in entries:
            raise CatalogError(f"duplicate catalog entry for {name!r}")
        entries[name] = entry
    return dict(sorted(entries.items()))

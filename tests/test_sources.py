"""Source synchronization tests; all Git remotes are local and disposable."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vendomat.catalog import CatalogEntry
from vendomat.sources import (
    SOURCE_MAP_HEADER,
    SourceError,
    relevant_entries,
    source_checks,
    source_map_text,
    source_path,
    sync_sources,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _working_repo(path: Path) -> tuple[Path, str]:
    path.mkdir(parents=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("first\n")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "first")
    return path, _git(path, "rev-parse", "HEAD")


def _bare_remote(tmp_path: Path) -> tuple[Path, str]:
    work, rev = _working_repo(tmp_path / "upstream-work")
    remote = tmp_path / "upstream.git"
    subprocess.run(["git", "clone", "--bare", str(work), str(remote)], check=True, capture_output=True)
    return remote, rev


def _entry(
    *,
    name: str,
    kind: str,
    repository: str,
    rev: str,
    path: str | None = None,
    cache: str | None = None,
) -> CatalogEntry:
    local = f'path = "{path}"' if path is not None else f'cache = "{cache}"'
    return CatalogEntry.from_toml(
        f'[package]\nname = "{name}"\nkind = "{kind}"\nrepository = "{repository}"\nrev = "{rev}"\n\n[local]\n{local}\n'
    )


def _write_catalog(vendomat_root: Path, *entries: CatalogEntry) -> None:
    catalog = vendomat_root / "vendor/python"
    catalog.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        (catalog / f"{entry.package.name}.toml").write_text(entry.to_toml())


def _consumer(path: Path, *dependencies: str, lock: str | None = None) -> Path:
    path.mkdir(parents=True)
    deps = ", ".join(f'"{dependency}"' for dependency in dependencies)
    (path / "pyproject.toml").write_text(f'[project]\nname = "consumer"\ndependencies = [{deps}]\n')
    if lock is not None:
        (path / "uv.lock").write_text(lock)
    return path


def test_relevant_entries_intersect_normalized_consumer_dependencies():
    project = _entry(
        name="knappy",
        kind="project",
        repository="https://github.com/Bullish-Design/knappy",
        rev="1" * 40,
        path="../knappy",
    )
    vendor = _entry(
        name="pydantic",
        kind="vendor",
        repository="https://github.com/pydantic/pydantic",
        rev="2" * 40,
        cache="pydantic",
    )
    catalog = {"pydantic": vendor, "knappy": project}

    assert [entry.package.name for entry in relevant_entries(catalog, {"Pydantic", "other"})] == ["pydantic"]


def test_source_map_is_deterministic_and_distinguishes_project_and_vendor_paths(tmp_path):
    source_root = tmp_path / "global-vendor"
    consumer = tmp_path / "consumer"
    project = _entry(
        name="knappy",
        kind="project",
        repository="https://example.test/knappy",
        rev="1" * 40,
        path="../knappy",
    )
    vendor = _entry(
        name="pydantic",
        kind="vendor",
        repository="https://example.test/pydantic",
        rev="2" * 40,
        cache="pydantic",
    )

    text = source_map_text([vendor, project], source_root, consumer)

    assert text.startswith(SOURCE_MAP_HEADER)
    assert text.index("knappy =") < text.index("pydantic =")
    assert 'knappy = "../knappy"' in text
    assert f'pydantic = "{source_root / "pydantic"}"' in text
    assert "[revisions]" in text
    assert f'knappy = "{project.package.rev}"' in text
    assert f'pydantic = "{vendor.package.rev}"' in text


def test_sync_managed_clone_is_detached_idempotent_and_never_mutates_packaging_files(tmp_path):
    remote, rev = _bare_remote(tmp_path)
    _project, project_rev = _working_repo(tmp_path / "knappy")
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    lock = (
        '[[package]]\nname = "knappy"\nversion = "0.1.0"\n\n'
        '[[package]]\nname = "pydantic"\nversion = "2.0.0"\n\n'
        '[[package]]\nname = "uncatalogued"\nversion = "1.0.0"\n'
    )
    consumer = _consumer(tmp_path / "consumer", "pydantic>=2", "knappy", lock=lock)
    project_entry = _entry(
        name="knappy",
        kind="project",
        repository="https://example.test/knappy",
        rev=project_rev,
        path="../knappy",
    )
    vendor_entry = _entry(
        name="pydantic",
        kind="vendor",
        repository=str(remote),
        rev=rev,
        cache="pydantic",
    )
    _write_catalog(catalog_root, project_entry, vendor_entry)
    pyproject_before = (consumer / "pyproject.toml").read_bytes()
    lock_before = (consumer / "uv.lock").read_bytes()

    first = sync_sources(catalog_root, source_root, consumer)
    clone = source_root / "pydantic"
    source_map = consumer / ".vendomat/sources.toml"
    first_map = source_map.read_bytes()
    first_mtime = source_map.stat().st_mtime_ns
    second = sync_sources(catalog_root, source_root, consumer)

    assert first.map_changed is True
    assert second.map_changed is False
    assert _git(clone, "rev-parse", "HEAD") == rev
    symbolic_ref = subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"],
        cwd=clone,
        check=False,
        capture_output=True,
        text=True,
    )
    assert symbolic_ref.returncode == 1
    assert symbolic_ref.stdout == ""
    assert source_map.read_bytes() == first_map
    assert source_map.stat().st_mtime_ns == first_mtime
    assert b'knappy = "../knappy"' in first_map
    assert f'knappy = "{project_rev}"'.encode() in first_map
    assert f'pydantic = "{rev}"'.encode() in first_map
    assert b"uncatalogued" not in first_map
    assert not (source_root / "knappy").exists()
    assert (consumer / "pyproject.toml").read_bytes() == pyproject_before
    assert (consumer / "uv.lock").read_bytes() == lock_before


def test_sync_refuses_dirty_managed_clone(tmp_path):
    remote, rev = _bare_remote(tmp_path)
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    consumer = _consumer(tmp_path / "consumer", "pydantic")
    entry = _entry(
        name="pydantic",
        kind="vendor",
        repository=str(remote),
        rev=rev,
        cache="pydantic",
    )
    _write_catalog(catalog_root, entry)
    sync_sources(catalog_root, source_root, consumer)
    (source_root / "pydantic/LOCAL-NOTES.md").write_text("investigating\n")

    with pytest.raises(SourceError, match="dirty"):
        sync_sources(catalog_root, source_root, consumer)


def test_dry_run_makes_no_clone_directory_or_source_map(tmp_path):
    remote, rev = _bare_remote(tmp_path)
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    consumer = _consumer(tmp_path / "consumer", "pydantic")
    entry = _entry(
        name="pydantic",
        kind="vendor",
        repository=str(remote),
        rev=rev,
        cache="pydantic",
    )
    _write_catalog(catalog_root, entry)

    result = sync_sources(catalog_root, source_root, consumer, dry_run=True)

    assert any("clone" in action for action in result.actions)
    assert not source_root.exists()
    assert not (consumer / ".vendomat").exists()


def test_managed_cache_cannot_escape_vendomat_through_symlink(tmp_path):
    source_root = tmp_path / "global-vendor"
    source_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (source_root / "pydantic").symlink_to(outside, target_is_directory=True)
    entry = _entry(
        name="pydantic",
        kind="vendor",
        repository="https://example.test/pydantic",
        rev="1" * 40,
        cache="pydantic",
    )

    with pytest.raises(SourceError, match="outside source root"):
        source_path(entry, source_root, tmp_path / "consumer")


def test_project_source_diagnostics_cover_missing_wrong_revision_and_dirty(tmp_path):
    consumer = _consumer(tmp_path / "consumer", "knappy")
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    missing = _entry(
        name="knappy",
        kind="project",
        repository="https://example.test/knappy",
        rev="1" * 40,
        path="../knappy",
    )
    _write_catalog(catalog_root, missing)

    checks = source_checks(catalog_root, source_root, consumer)
    assert any(check.level == "fail" and "missing" in check.detail for check in checks)

    project, initial = _working_repo(tmp_path / "knappy")
    current_entry = _entry(
        name="knappy",
        kind="project",
        repository="https://example.test/knappy",
        rev=initial,
        path="../knappy",
    )
    _write_catalog(catalog_root, current_entry)
    (project / "README.md").write_text("second\n")
    _git(project, "commit", "-am", "second")
    (project / "DIRTY.txt").write_text("dirty\n")

    checks = source_checks(catalog_root, source_root, consumer)
    assert any(check.level == "fail" and "wrong revision" in check.detail for check in checks)
    assert any(check.level == "warn" and "dirty" in check.detail for check in checks)


def test_doctor_detects_stale_map_and_reports_installed_version_separately(tmp_path):
    remote, rev = _bare_remote(tmp_path)
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    lock = '[[package]]\nname = "pydantic"\nversion = "9.9.9"\n'
    consumer = _consumer(tmp_path / "consumer", "ignored-because-lock-wins", lock=lock)
    entry = _entry(
        name="pydantic",
        kind="vendor",
        repository=str(remote),
        rev=rev,
        cache="pydantic",
    )
    _write_catalog(catalog_root, entry)
    sync_sources(catalog_root, source_root, consumer)
    source_map = consumer / ".vendomat/sources.toml"
    source_map.write_text(source_map.read_text().replace("pydantic =", "old-pydantic ="))

    checks = source_checks(catalog_root, source_root, consumer)

    assert any(check.level == "fail" and "stale" in check.detail for check in checks)
    state = next(check for check in checks if check.name == "source:pydantic")
    assert f"expected={rev}" in state.detail
    assert "installed=9.9.9" in state.detail


def test_uncatalogued_dependency_is_warn_only(tmp_path):
    catalog_root = tmp_path / "vendomat"
    source_root = tmp_path / "global-vendor"
    (catalog_root / "vendor/python").mkdir(parents=True)
    consumer = _consumer(tmp_path / "consumer", "mystery-lib")

    checks = source_checks(catalog_root, source_root, consumer)

    assert any(check.level == "warn" and "mystery-lib" in check.detail for check in checks)
    assert not any(check.level == "fail" for check in checks)

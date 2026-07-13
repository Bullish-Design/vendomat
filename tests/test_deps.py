"""Unit tests for the dep-reader: per-format parsing, precedence, and PEP 503 normalization."""

from __future__ import annotations

from pathlib import Path

from vendomat.deps import normalize, read_deps, read_resolved_versions


def test_normalize_pep503():
    assert normalize("Typer") == "typer"
    assert normalize("ruamel_yaml") == "ruamel-yaml"
    assert normalize("ruamel.yaml") == "ruamel-yaml"
    assert normalize("A__B--C") == "a-b-c"


def _write(p: Path, name: str, body: str) -> None:
    (p / name).write_text(body)


def test_reads_uv_lock(tmp_path):
    _write(
        tmp_path,
        "uv.lock",
        """
        [[package]]
        name = "Typer"
        version = "0.12.5"

        [[package]]
        name = "click"
        version = "8.1.7"
        """,
    )
    assert read_deps(tmp_path) == {"typer", "click"}


def test_reads_pyproject_deps_optionals_and_groups(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        """
        [project]
        name = "consumer"
        dependencies = ["typer>=0.12", "Pydantic>=2.12"]

        [project.optional-dependencies]
        extra = ["httpx>=0.27"]

        [dependency-groups]
        dev = ["pytest>=8", {include-group = "lint"}]
        """,
    )
    assert read_deps(tmp_path) == {"typer", "pydantic", "httpx", "pytest"}


def test_reads_repoman_lock_packages_incl_pseudo_entry(tmp_path):
    _write(
        tmp_path,
        "repoman.lock",
        """
        [repoman]
        package = "repoman"
        source = "path:/x"

        [managers.git]
        package = "gitman"
        source = "path:/x"

        [managers.git-pyjutsu]
        package = "pyjutsu"
        source = "wheel:pyjutsu>=0.8"
        """,
    )
    assert read_deps(tmp_path) == {"repoman", "gitman", "pyjutsu"}


def test_precedence_uv_lock_wins_over_pyproject_and_repoman(tmp_path):
    _write(tmp_path, "uv.lock", '[[package]]\nname = "typer"\nversion = "1"\n')
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies = ["click"]\n')
    _write(tmp_path, "repoman.lock", '[managers.git]\npackage = "gitman"\n')
    # uv.lock exists → only its set is returned.
    assert read_deps(tmp_path) == {"typer"}


def test_precedence_pyproject_wins_over_repoman(tmp_path):
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies = ["click"]\n')
    _write(tmp_path, "repoman.lock", '[managers.git]\npackage = "gitman"\n')
    assert read_deps(tmp_path) == {"click"}


def test_no_source_files_returns_empty(tmp_path):
    assert read_deps(tmp_path) == set()


# --- read_resolved_versions (M4 review-on-bump input) -----------------------------------------


def test_resolved_versions_from_uv_lock_normalizes_names(tmp_path):
    _write(
        tmp_path,
        "uv.lock",
        '[[package]]\nname = "Typer"\nversion = "0.13.0"\n\n[[package]]\nname = "click"\nversion = "8.1.7"\n',
    )
    assert read_resolved_versions(tmp_path) == {"typer": "0.13.0", "click": "8.1.7"}


def test_resolved_versions_no_uv_lock_is_empty(tmp_path):
    # pyproject/repoman carry no exact resolved version → unknown, not an error.
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies = ["typer>=0.12"]\n')
    assert read_resolved_versions(tmp_path) == {}

"""Smoke tests for the vendomat CLI shape + the 0/1/2/3 exit-code contract (M0)."""

from __future__ import annotations

from typer.testing import CliRunner

from vendomat.cli import _catalog_root, _global_source_root, app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vendomat" in result.stdout


def test_no_args_shows_help():
    # no_args_is_help=True → Typer prints usage instead of erroring on a bare invocation.
    result = runner.invoke(app, [])
    assert "Usage" in result.stdout


def test_doctor_clean_repo_exits_zero(tmp_path, monkeypatch):
    # An empty repo has no knowledge installed → nothing to flag → exit 0.
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "self-check" in result.stdout


def test_sync_without_vendor_root_is_infra_error(tmp_path, monkeypatch):
    # No VENDOMAT_VENDOR_ROOT and no --vendor-root → infra/config (exit 2).
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    monkeypatch.delenv("VENDOMAT_VENDOR_ROOT", raising=False)
    assert runner.invoke(app, ["sync"]).exit_code == 2


def test_sync_installs_gated_skill(tmp_path, monkeypatch):
    # Seed a vendor tree with a typer skill and a repo that depends on typer.
    vendor = tmp_path / "vendor"
    lib = vendor / "libs" / "typer"
    lib.mkdir(parents=True)
    (lib / "SKILL.md").write_text("# skill\n")
    (lib / "meta.toml").write_text('[lib]\nname = "typer"\npin = "0.12.5"\n')
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\ndependencies = ["typer>=0.12"]\n')

    monkeypatch.setenv("DEVENV_ROOT", str(repo))
    result = runner.invoke(app, ["sync", "--vendor-root", str(vendor)])
    assert result.exit_code == 0
    assert "dep-typer" in result.stdout
    assert (repo / ".claude/skills/dep-typer/SKILL.md").is_file()


def test_add_drafts_into_local_vendor(tmp_path, monkeypatch):
    # `add` authors into <repo>/vendor; ghost-lib isn't installed → degrades to TODO stubs, exit 0.
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    result = runner.invoke(app, ["add", "ghost-lib"])
    assert result.exit_code == 0
    assert "dep-ghost-lib" not in result.stdout  # entry name is the lib, not the dep- skill name
    entry = tmp_path / "vendor" / "libs" / "ghost-lib"
    assert (entry / "SKILL.md").is_file()
    assert (entry / "meta.toml").is_file()
    assert (entry / "notes.md").is_file()


def test_add_refuses_existing_entry_without_force(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))
    assert runner.invoke(app, ["add", "ghost-lib"]).exit_code == 0
    # Second run without --force is a domain refusal (exit 1); --force succeeds.
    assert runner.invoke(app, ["add", "ghost-lib"]).exit_code == 1
    assert runner.invoke(app, ["add", "ghost-lib", "--force"]).exit_code == 0


def test_add_respects_vendor_root_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path / "elsewhere"))
    target = tmp_path / "authored"
    result = runner.invoke(app, ["add", "ghost-lib", "--vendor-root", str(target)])
    assert result.exit_code == 0
    assert (target / "libs" / "ghost-lib" / "SKILL.md").is_file()


def test_materialize_rewrites_consumer_manifest_sources(tmp_path, monkeypatch):
    (tmp_path / "vendomat.toml").write_text(
        '[[replacement]]\nfiles = ["pyproject.toml"]\n'
        'local = "path:vendor/widgets"\n'
        'github = "git+https://github.com/acme/widgets.git@v1"\n'
    )
    (tmp_path / "pyproject.toml").write_text('source = "path:vendor/widgets"\n')
    monkeypatch.setenv("DEVENV_ROOT", str(tmp_path))

    result = runner.invoke(app, ["materialize", "github"])

    assert result.exit_code == 0
    assert "updated 1 file" in result.stdout
    assert "git+https://github.com/acme/widgets.git@v1" in (tmp_path / "pyproject.toml").read_text()


def test_vendor_group_help_exposes_required_commands():
    result = runner.invoke(app, ["vendor", "--help"])

    assert result.exit_code == 0
    assert "sync" in result.stdout
    assert "status" in result.stdout
    assert "doctor" in result.stdout


def test_vendor_source_root_defaults_to_home_vendor(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("VENDOMAT_SOURCE_ROOT", raising=False)

    assert _global_source_root(None) == tmp_path / "vendor"


def test_vendor_catalog_root_reuses_nix_vendor_root_environment(tmp_path, monkeypatch):
    vendor_root = tmp_path / "vendomat-store-source/vendor"
    monkeypatch.setenv("VENDOMAT_VENDOR_ROOT", str(vendor_root))
    monkeypatch.delenv("VENDOMAT_CATALOG_ROOT", raising=False)

    assert _catalog_root(None) == vendor_root.parent


def test_vendor_sync_help_exposes_global_source_root():
    result = runner.invoke(app, ["vendor", "sync", "--help"])

    assert result.exit_code == 0
    assert "--source-root" in result.stdout
    assert "~/vendor" in result.stdout


def test_vendor_doctor_uses_shared_exit_contract_for_missing_project(tmp_path):
    vendomat_root = tmp_path / "vendomat"
    catalog = vendomat_root / "vendor/python"
    catalog.mkdir(parents=True)
    (catalog / "knappy.toml").write_text(
        "[package]\n"
        'name = "knappy"\n'
        'kind = "project"\n'
        'repository = "https://github.com/Bullish-Design/knappy"\n'
        f'rev = "{"1" * 40}"\n\n'
        "[local]\n"
        'path = "../knappy"\n'
    )
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "pyproject.toml").write_text('[project]\ndependencies = ["knappy"]\n')

    result = runner.invoke(
        app,
        [
            "vendor",
            "doctor",
            "--repo-root",
            str(consumer),
            "--vendomat-root",
            str(vendomat_root),
            "--source-root",
            str(tmp_path / "global-vendor"),
        ],
    )

    assert result.exit_code == 2
    assert "missing" in result.stdout


def test_vendor_sync_malformed_catalog_is_infra_error(tmp_path):
    vendomat_root = tmp_path / "vendomat"
    catalog = vendomat_root / "vendor/python"
    catalog.mkdir(parents=True)
    (catalog / "broken.toml").write_text("not = [valid")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "pyproject.toml").write_text('[project]\ndependencies = ["pydantic"]\n')

    result = runner.invoke(
        app,
        [
            "vendor",
            "sync",
            "--repo-root",
            str(consumer),
            "--vendomat-root",
            str(vendomat_root),
            "--source-root",
            str(tmp_path / "global-vendor"),
        ],
    )

    assert result.exit_code == 2
    assert "catalog" in result.stderr.lower()

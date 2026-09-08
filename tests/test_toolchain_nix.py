"""Face D — the shared RepoMan command closure (CONCEPT 03).

Two layers of guard:

* grep-level checks on the nix sources, which are fast and run everywhere;
* real `nix` invocations, which are the only way to prove the acceptance criteria
  (a command resolves to /nix/store, the collision guard actually throws). Those are
  marked ``nix`` and skip when the binary is absent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
MODULE = ROOT / "modules" / "devenv.nix"

needs_nix = pytest.mark.skipif(shutil.which("nix") is None, reason="nix is not on PATH")


def _nix(*args: str, expect_fail: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["nix", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if expect_fail:
        assert result.returncode != 0, f"expected failure, got:\n{result.stdout}"
    else:
        assert result.returncode == 0, f"nix {' '.join(args)} failed:\n{result.stderr}"
    return result


# ------------------------------------------------------------------ source-level guards


def test_uv2nix_constructor_is_used_for_the_roster():
    text = (ROOT / "flake.nix").read_text()
    assert "mkUv2nixCli" in text
    assert "workspace.mkPyprojectOverlay" in text
    assert "uvVersions = lockVersions;" in text


def test_mk_toolchain_rejects_a_mixed_python_baseline():
    # CONCEPT 03 §8.3: one interpreter for the whole closure.
    text = (LIB / "mkToolchain.nix").read_text()
    assert "mixes Python versions" in text


def test_module_gives_tasks_an_absolute_bin_dir_not_a_path_lookup():
    # CONCEPT 03 §4.1: the resolver uses an absolute known path, so an unrelated venv on
    # PATH cannot shadow a selected shared tool.
    text = MODULE.read_text()
    assert 'env.REPOMAN_TOOLCHAIN_BIN = "${toolchain}/bin";' in text


def test_module_sets_the_repoman_provider_only_when_repoman_is_present():
    # A consumer may import vendomat without repoman; a definition for an undeclared
    # option fails a strict full-config eval.
    text = MODULE.read_text()
    assert "lib.optionalAttrs (options ? repoman)" in text
    assert 'repoman.cliProvider = "store";' in text


def test_module_keeps_the_toolchain_off_the_shell_entry_path():
    # gitman project 32 / G3: a broken `vendor-status` took loci-core's devenv shell down
    # entirely. Toolchain provenance is a TASK the user runs, never an enterShell hook.
    text = MODULE.read_text()
    face_d = text.split("--- Face D: the shared command closure")[1].split("This is independent of Face A")[0]
    # Comments may NAME enterShell (they explain why the hook is absent); only the
    # executable lines matter here.
    code = "\n".join(line for line in face_d.splitlines() if not line.lstrip().startswith("#"))
    assert "enterShell" not in code
    assert 'tasks."vendor:toolchain:status"' in face_d


# ------------------------------------------------------------------------- real nix runs


@needs_nix
def test_the_collision_guard_actually_throws(tmp_path):
    # CONCEPT 03 §3.2: the join must FAIL EVALUATION on a duplicate executable name rather
    # than silently shadow one. Silent shadowing by PATH order is the defect being removed,
    # so this guard is asserted against a real eval, not only against its source text.
    expr = tmp_path / "collide.nix"
    expr.write_text(
        f"""
        let
          flake = builtins.getFlake (toString {ROOT});
          pkgs = import flake.inputs.nixpkgs {{ system = "x86_64-linux"; }};
          mk = import "${{flake.outPath}}/lib/mkToolchain.nix" {{ inherit pkgs; python = pkgs.python313; }};
          tool = cmds: {{ version = "0"; passthru = {{ commands = cmds; pythonVersion = "3.13"; }}; }};
        in
        mk {{ name = "clash"; tools = {{ a = tool [ "x" "demo" ]; b = tool [ "y" "demo" ]; }}; }}
        """
    )
    result = _nix("eval", "--impure", "-f", str(expr), expect_fail=True)
    assert "duplicate command name(s)" in result.stderr
    assert "demo <- a, b" in result.stderr


@needs_nix
def test_the_core_roster_builds_and_reports_its_provenance():
    out = _nix("build", ".#repoman-toolchain-core", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    closure = Path(out)
    assert closure.is_relative_to("/nix/store")

    manifest = json.loads((closure / "share" / "vendomat" / "toolchain.json").read_text())
    assert manifest["roster"] == "core"
    assert manifest["python"] == "3.13"
    assert set(manifest["tools"]) == {"repoman", "copyroom", "docman", "gitman", "templateer"}
    for tool in manifest["tools"].values():
        # Acceptance: two consumers with identical locks resolve to the SAME store paths,
        # which is only meaningful if the manifest names them.
        assert tool["store"].startswith("/nix/store/")


@needs_nix
def test_every_roster_command_resolves_into_the_nix_store():
    out = _nix("build", ".#repoman-toolchain-core", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    # buildPythonApplication leaves `.<name>-wrapped` siblings; only the real commands
    # are on PATH, so only they can collide.
    expected = {"copyroom", "docman", "gitman", "repoman", "templateer"}
    binaries = sorted(p.name for p in (Path(out) / "bin").iterdir() if p.name in expected)
    # `demo` is copyroom's second console script. It is a generic name and no part of the
    # manager contract; left in, it would be the roster's first collision.
    assert set(binaries) == expected
    for name in binaries:
        assert (Path(out) / "bin" / name).resolve().is_relative_to("/nix/store")


@needs_nix
def test_the_closure_commands_run():
    # CONCEPT 03 §6 is explicit: do not mark a tool supported because its package
    # evaluates. Execute it.
    out = _nix("build", ".#repoman-toolchain-core", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    version = subprocess.run(
        [str(Path(out) / "bin" / "copyroom"), "--version"], capture_output=True, text=True, timeout=120
    )
    assert version.returncode == 0
    assert "copyroom" in version.stdout


@needs_nix
def test_gitman_pulls_no_rust_toolchain():
    # CONCEPT 03 §6 phase 3, and the acceptance criterion: a `git` consumer does zero
    # Cargo/Maturin work. The native compile happened once, when Vendomat built the
    # pyjutsu wheel; gitman's package only installs it. A Rust toolchain reappearing in
    # gitman's RUNTIME closure means someone made it build from source again.
    out = _nix("build", ".#gitman", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    closure = _nix("path-info", "-r", out).stdout
    for forbidden in ("cargo", "rustc", "maturin", "-mold-"):
        assert forbidden not in closure, f"{forbidden} is in gitman's runtime closure"


@needs_nix
def test_gitman_runs_and_imports_its_native_dependency():
    # `gitman --version` imports pyjutsu, so this exercises the vended wheel, not only
    # the fact that a file exists at bin/gitman.
    out = _nix("build", ".#gitman", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    result = subprocess.run([f"{out}/bin/gitman", "--version"], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "gitman" in result.stdout


# ------------------------------------------------- sub-phase 4: store mode is the default


def test_the_toolchain_is_on_by_default():
    # CONCEPT 03 §6 phase 4: importing Vendomat IS the opt-in. Only reached once every
    # roster tool has passed integration testing, which is why it lands last.
    text = MODULE.read_text()
    block = text.split("toolchain = {")[1].split("roster = lib.mkOption")[0]
    assert "default = true;" in block
    assert 'lib.types.enum [ "store" "editable" ]' in block
    assert 'default = "store";' in block


def test_editable_mode_delivers_no_package():
    # A tool author must be able to run uncommitted changes (acceptance criterion). In
    # gitman's own repo an older store build must not shadow the working tree, so
    # editable mode contributes no package and no env.
    text = MODULE.read_text()
    assert '(lib.mkIf (tcfg.enable && tcfg.mode == "store") (lib.mkMerge [' in text


def test_editable_mode_names_the_venv_provider():
    # It used to leave repoman.cliProvider alone, which was correct while that option
    # defaulted to "venv". repoman 0.7.6 moved the default to "store", so leaving it
    # alone would put a tagged build ahead of the tool author's own checkout — the one
    # thing editable mode exists to prevent. It must NAME the provider it wants.
    text = MODULE.read_text()
    assert '(lib.mkIf (tcfg.enable && tcfg.mode == "editable") (' in text
    block = text.split('tcfg.mode == "editable"')[1]
    assert 'repoman.cliProvider = "venv";' in block
    # Same guard as the store branch: a consumer may import vendomat without repoman.
    assert "options ? repoman" in block.split("repoman.cliProvider")[0]


def test_the_venv_escape_hatch_is_documented_as_short_lived():
    # `enable = false` returns a consumer to the machine venv. It stays available during
    # migration, but it must not read as an equal alternative to editable mode.
    text = MODULE.read_text()
    block = text.split("toolchain = {")[1].split("mode = lib.mkOption")[0]
    assert "escape hatch" in block
    assert "short-lived" in block


@needs_nix
def test_templateer_uses_uv_lock_and_no_other_tool_does():
    # The public templateer package must use the versions in its own uv.lock.
    out = _nix("build", ".#templateer", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    closure = _nix("path-info", "-r", out).stdout
    for package in (
        "click-8.4.2",
        "genai-prices-0.1.1",
        "httpcore2-2.9.1",
        "httpx2-2.9.1",
        "idna-3.18",
        "jiter-0.16.0",
        "minijinja-2.22.0",
        "openai-2.53.0",
        "pydantic-ai-slim-2.23.0",
        "pydantic-graph-2.23.0",
    ):
        assert package in closure

    gitman = _nix("build", ".#gitman", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    other = _nix("path-info", "-r", gitman).stdout
    assert "minijinja" not in other, "the templateer overlay reached a tool that does not need it"


@needs_nix
@pytest.mark.parametrize("tool", ["repoman", "copyroom", "docman", "gitman", "templateer"])
def test_uv2nix_closure_matches_each_tool_lockfile(tool: str):
    # Check every lockfile package that appears in the runtime closure. Dev-only packages
    # do not appear in the closure and are intentionally skipped by this boundary check.
    versions = json.loads(_nix("eval", f".#{tool}.uvVersions", "--json").stdout)
    out = _nix("build", f".#{tool}", "--no-link", "--print-out-paths").stdout.strip().splitlines()[-1]
    closure = _nix("path-info", "-r", out).stdout.splitlines()
    for name, version in versions.items():
        variants = {name, name.replace("-", "_"), name.replace("_", "-")}
        matching = [path for path in closure if any(f"-{variant}-" in path for variant in variants)]
        if matching:
            assert any(any(f"-{variant}-{version}" in path for variant in variants) for path in matching), (
                f"{tool} resolved {name} outside uv.lock version {version}: {matching}"
            )

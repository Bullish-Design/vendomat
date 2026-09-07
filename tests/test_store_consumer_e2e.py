"""End-to-end proof of Face D, in a real devenv (CONCEPT 03 §7).

Everything else about the shared closure is checked by evaluating nix or reading text.
That is not enough, and this suite exists because it was not: the store bin expression
was correct Nix, read correctly, and passed every grep-level test — then every
store-mode task died with `unexpected EOF while looking for matching`, because the
expression was only wrong once bash parsed it. The fixture caught it on its first run.

These tests enter a real shell and build a real closure, so they take minutes and need
the network. They are opt-in:

    VENDOMAT_E2E=1 devenv shell testee verify --mode ci

The fixture is `tests/fixtures/store-consumer`: a consumer that declares NO manager
anywhere — no repoman.lock, no `uv add`, nothing in pyproject.toml. That absence is the
thing under test.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "store-consumer"

needs_e2e = pytest.mark.skipif(
    os.environ.get("VENDOMAT_E2E") != "1" or shutil.which("devenv") is None,
    reason="end-to-end devenv run; set VENDOMAT_E2E=1 to opt in",
)


def _in_shell(script: str) -> subprocess.CompletedProcess:
    """Run `script` inside the fixture's devenv shell."""
    return subprocess.run(
        ["devenv", "shell", "--", "bash", "-c", script],
        cwd=FIXTURE,
        capture_output=True,
        text=True,
        timeout=3600,
    )


def _venv() -> Path:
    return FIXTURE / ".devenv" / "state" / "venv"


MANAGERS = ("repoman", "copyroom", "gitman", "docman", "testee", "pyjutsu")


@needs_e2e
def test_the_consumer_resolves_its_commands_from_the_nix_store():
    result = _in_shell(
        'echo "PROVIDER=$REPOMAN_CLI_PROVIDER"; '
        'echo "BIN=$REPOMAN_TOOLCHAIN_BIN"; '
        'echo "REPOMAN=$(command -v repoman)"; '
        'echo "COPYROOM=$(command -v copyroom)"'
    )
    assert result.returncode == 0, result.stderr
    out = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line and not line.startswith(" "))
    # Vendomat's module set repoman's provider; the two layers agree.
    assert out["PROVIDER"] == "store"
    assert out["BIN"].startswith("/nix/store/")
    for command in ("REPOMAN", "COPYROOM"):
        assert out[command].startswith("/nix/store/"), f"{command} resolved to {out[command]}"


@needs_e2e
def test_the_consumer_venv_holds_no_manager():
    """The acceptance criterion, checked directly rather than inferred.

    A consumer keeps a venv for its OWN dependencies. It must contain neither the
    manager distributions nor their console-script wrappers.
    """
    assert _venv().is_dir(), "run test_the_consumer_resolves_its_commands_from_the_nix_store first"

    wrappers = {p.name for p in (_venv() / "bin").iterdir()}
    assert not (wrappers & set(MANAGERS)), f"manager console scripts in the consumer venv: {wrappers & set(MANAGERS)}"

    site_packages = next(iter((_venv() / "lib").glob("python*/site-packages")), None)
    assert site_packages is not None, "no site-packages in the consumer venv"
    installed = [p.name.lower() for p in site_packages.iterdir()]
    leaked = [name for name in installed if any(m in name for m in MANAGERS)]
    assert not leaked, f"manager distributions in the consumer venv: {leaked}"


@needs_e2e
def test_a_venv_executable_cannot_shadow_the_shared_command():
    """Tasks must use the shared path even when a conflicting executable exists.

    This is what an absolute resolver buys over `command -v`. The impostor is installed
    where a stale pre-migration copy would sit, which is the case that motivated it.
    """
    assert _venv().is_dir(), "run test_the_consumer_resolves_its_commands_from_the_nix_store first"

    impostor = _venv() / "bin" / "copyroom"
    impostor.write_text('#!/usr/bin/env bash\necho "IMPOSTOR copyroom from the consumer venv"\nexit 0\n')
    impostor.chmod(0o755)
    try:
        result = subprocess.run(
            ["devenv", "tasks", "run", "repoman:template:status"],
            cwd=FIXTURE,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        combined = result.stdout + result.stderr
        assert "IMPOSTOR" not in combined, "the consumer venv shadowed the shared command"
        # The real copyroom ran and reported its own domain error: the fixture is not a
        # Copier project. A resolution failure would not get that far.
        assert ".copier-answers" in combined, combined
    finally:
        impostor.unlink()


def test_the_fixture_declares_no_manager():
    """Cheap, always runs. The fixture only proves an empty venv while it stays empty.

    If a manager is ever added to the fixture's pyproject.toml, the end-to-end tests
    above would still pass for the wrong reason.
    """
    import tomllib

    with open(FIXTURE / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    project = data.get("project", {})
    declared = list(project.get("dependencies") or [])
    for reqs in (project.get("optional-dependencies") or {}).values():
        declared += list(reqs or [])
    for reqs in (data.get("dependency-groups") or {}).values():
        declared += [r for r in (reqs or []) if isinstance(r, str)]
    # Read the DECLARATIONS, not the file text: the fixture's comments name the managers
    # precisely to explain why none is declared.
    for requirement in declared:
        for manager in MANAGERS:
            assert manager not in requirement.lower(), f"the fixture declares {requirement}"
    assert declared == [], f"the fixture must declare nothing at all, got {declared}"
    assert not (FIXTURE / "repoman.lock").exists(), "the fixture must not carry a repoman.lock"

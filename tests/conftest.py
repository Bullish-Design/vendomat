"""Isolate the suite from the shell it runs in.

`vendomat sync` reads `REPOMAN_SKILLS_DIR` to decide where per-dependency skills
install (`src/vendomat/cli.py:65`, defaulting to `.claude/skills`). A devenv
shell exports that variable, so a test that asserts the default path passed in a
bare shell and failed inside `devenv shell` — which is where the publish gate
runs. A suite must not depend on who invoked it.
"""

from __future__ import annotations

import pytest

#: Variables a devenv shell exports that would otherwise steer the code under test.
_AMBIENT = ("REPOMAN_SKILLS_DIR", "REPOMAN_MANAGERS", "VENDOMAT_VENDOR_ROOT")


@pytest.fixture(autouse=True)
def _no_ambient_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear the shell-provided variables before every test."""

    for name in _AMBIENT:
        monkeypatch.delenv(name, raising=False)

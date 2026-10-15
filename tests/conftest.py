"""Isolate the suite from the shell it runs in.

A devenv shell exports variables such as `REPOMAN_SKILLS_DIR`. A test that passes in a bare
shell can fail inside `devenv shell`. A suite must not depend on who invoked it.
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

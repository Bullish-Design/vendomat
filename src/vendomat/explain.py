"""``vendomat explain``: show where each setting of a workspace comes from (R27, ``VMT-057``).

The catalog module builds the data (``devenv/explain.nix``). ``devenv eval vendomat.explain`` prints it as
JSON. This module runs that command and formats the result. The report has two lists:

``yaml``
    One entry for each key of ``vendomat.yaml``, in file order: ``key``, ``line``, ``column``, the native
    ``option``, its ``value``, and the ``files`` that set the option.
``nix``
    One entry for each option that a hatch file sets and no key of ``vendomat.yaml`` covers.

``VENDOMAT_HIDE_ADVANCED`` hides only the line of the shell entry. ``explain`` always shows every source (R45).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .errortrim import save_log, trim

ATTRIBUTE = "vendomat.explain"
#: The file of an entry that no file of the workspace sets (see devenv/explain.nix).
NO_EFFECT = "(devenv default)"


class ExplainError(Exception):
    """A fault. ``code`` is the CLI exit status."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def devenv_command() -> str:
    """The devenv command: ``$VENDOMAT_DEVENV``, else ``devenv`` on ``PATH``."""

    return os.environ.get("VENDOMAT_DEVENV") or "devenv"


def read_report(root: Path) -> dict[str, Any]:
    """Run ``devenv eval vendomat.explain`` in the workspace and return the report."""

    if not (root / "devenv.yaml").is_file():
        raise ExplainError(f"{root} is not a Vendomat workspace: it has no devenv.yaml")
    argv = [devenv_command(), "eval", ATTRIBUTE]
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise ExplainError(f"cannot run {argv[0]!r}: not found (set VENDOMAT_DEVENV to the devenv command)") from exc
    if proc.returncode != 0:
        log = save_log("explain", f"$ {' '.join(argv)}\n(exit {proc.returncode})\n{proc.stderr}\n{proc.stdout}")
        where = f"\nthe full trace is in {log}" if log else ""
        raise ExplainError(f"{trim(proc.stderr) or 'devenv eval failed'}{where}")
    return parse_output(proc.stdout)


def parse_output(stdout: str) -> dict[str, Any]:
    """Read the JSON that ``devenv eval`` printed: ``{"vendomat.explain": {...}}``."""

    text = stdout.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("\n{")
        try:
            data = json.loads(text[start + 1 :] if start >= 0 else text)
        except json.JSONDecodeError as exc:
            raise ExplainError(f"devenv eval printed no JSON report: {text[:200]!r}") from exc
    report = data.get(ATTRIBUTE) if isinstance(data, dict) else None
    if not isinstance(report, dict) or "yaml" not in report or "nix" not in report:
        raise ExplainError(f"devenv eval printed no {ATTRIBUTE} report")
    return report


def _value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def render(report: dict[str, Any]) -> str:
    """Format the report as text."""

    out: list[str] = ["Keys of vendomat.yaml:"]
    entries = report["yaml"]
    if not entries:
        out.append("  (none)")
    for entry in entries:
        out.append(f"  {entry['key']}  (vendomat.yaml:{entry['line']}:{entry['column']})")
        out.append(f"    option  {entry['option'] or '(read by the catalog, no native option)'}")
        out.append(f"    value   {_value(entry['value'])}")
        out.append(f"    from    {', '.join(entry['files'])}")
        if entry["files"] == [NO_EFFECT]:
            out.append("    note    the key has no effect here: devenv keeps its default")
        elif "vendomat.yaml" not in entry["files"]:
            out.append("    note    another file overrides vendomat.yaml for this option")
    out.append("")
    out.append("Set only in Nix (not by a key of vendomat.yaml):")
    if not report["nix"]:
        out.append("  (none)")
    for entry in report["nix"]:
        out.append(f"  {entry['option']}")
        out.append(f"    value   {_value(entry['value'])}")
        out.append(f"    from    {', '.join(entry['files'])}")
    return "\n".join(out)

"""Trim a devenv failure to the part the user needs (``VMT-117``).

devenv prints about 300 lines of Nix trace before the message of a failed evaluation. The message
comes after the last ``error:`` line. The lines that name ``vendomat.yaml`` and a position come first, because
the user can act on them. The launcher does the same in Bash before it enters the shell. The full text goes
to ``~/.local/state/vendomat/logs/`` so nothing is lost.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

#: A fault line of the catalog or the parser: ``vendomat.yaml:LINE:COL: reason``.
FAULT = re.compile(r"^vendomat\.yaml:\d+:\d+:")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_ERROR = re.compile(r"^\s*error:(.*)$")
_AT = re.compile(r"^at (\S+:\d+:\d+):?$")


def plain(text: str) -> str:
    """Remove the color codes that devenv writes to a terminal."""

    return _ANSI.sub("", text)


def trim(text: str) -> str:
    """Return the fault lines of ``vendomat.yaml``, then the text after the last ``error:``.

    A message of one line, such as a syntax error, gets the last ``at FILE:LINE:COL`` place that came before it.
    When the text has no ``error:`` line and no fault line, the whole text comes back, so a failure of
    another kind is never hidden.
    """

    lines = plain(text).splitlines()
    faults: list[str] = []
    for line in lines:
        stripped = line.strip()
        if FAULT.match(stripped) and stripped not in faults:
            faults.append(stripped)
    last = None
    for index, line in enumerate(lines):
        if _ERROR.match(line):
            last = index
    if last is None:
        tail = [] if faults else [line.rstrip() for line in lines]
    else:
        first = _ERROR.match(lines[last])
        assert first is not None
        tail = [first.group(1).strip(), *(line.strip() for line in lines[last + 1 :])]
        tail = [line for line in tail if line not in faults]
        # A short message such as a syntax error names its place in the lines before it. Keep that place.
        if not faults and sum(1 for line in tail if line) <= 1:
            places = [m.group(1) for m in (_AT.match(line.strip()) for line in lines[:last]) if m]
            if places:
                tail = [*(line for line in tail if line), f"at {places[-1]}"]
    body = [*faults, *tail]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body)


def log_dir() -> Path:
    """The directory of the full traces: ``~/.local/state/vendomat/logs``."""

    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "vendomat" / "logs"


def save_log(kind: str, text: str) -> Path | None:
    """Write the full text to the log directory. Return the path, or None when the write fails."""

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir() / f"{kind}-{stamp}-{os.getpid()}.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    except OSError:
        return None
    return path

"""``vendomat update``: bring the lines of ``devenv.yaml`` up to the template, then run ``devenv update`` (R25).

A newer template can need a new input, for example the input of a new language. The user does not edit
``devenv.yaml`` by hand. This module compares the file with the template and adds what is missing:

- a top-level key of the template that the file lacks (``inputs``, ``imports``);
- an input of the template that the file lacks, with the lines the template writes for it;
- an import of the template that the file lacks.

It never changes or removes a line that the user wrote. An input that the user defines in any way is the
user's, even when its lines differ from the template. The edit works on the text, so the comments and the
order of the user's lines stay as they are. A flow style value (``inputs: {...}``, ``imports: [...]``)
cannot take an edit and is an error that names the key.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yamlsubset import YamlError, parse

_KEY = re.compile(r"^( *)([^\s#\-][^:]*?|\"[^\"]*\"|'[^']*'):(\s|$)")


class UpdateError(Exception):
    """A fault. ``code`` is the CLI exit status."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Addition:
    """One block of template lines that the file lacks. ``lines`` names each line for the user."""

    kind: str  # "key", "input", or "import"
    name: str
    lines: tuple[str, ...]


def template_dir() -> Path:
    """The workspace template: ``$VENDOMAT_TEMPLATE``, the install tree, or the source tree."""

    env = os.environ.get("VENDOMAT_TEMPLATE")
    candidates = [Path(env)] if env else []
    candidates.append(Path(sys.argv[0]).resolve().parent.parent / "share" / "vendomat" / "templates" / "workspace")
    candidates.append(Path(__file__).resolve().parents[2] / "templates" / "workspace")
    for path in candidates:
        if (path / "devenv.yaml").is_file():
            return path
    raise UpdateError("cannot find the workspace template (set VENDOMAT_TEMPLATE to its directory)")


# --- Text blocks ---------------------------------------------------------------------------------


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _children(lines: list[str], start: int, end: int, indent: int) -> list[tuple[str, int, int, int]]:
    """The keys at ``indent`` in ``lines[start:end]``: ``(key, first line, end line, key line)``.

    A comment block directly above a key belongs to that key. Trailing blank lines do not.
    """

    keys: list[tuple[str, int]] = []
    for index in range(start, end):
        match = _KEY.match(lines[index])
        if match and len(match.group(1)) == indent:
            keys.append((match.group(2).strip("\"'"), index))
    out: list[tuple[str, int, int, int]] = []
    firsts: list[int] = []
    for _key, index in keys:
        first = index
        while first - 1 >= start and _is_comment(lines[first - 1]) and _indent(lines[first - 1]) == indent:
            first -= 1
        firsts.append(first)
    for position, (key, index) in enumerate(keys):
        stop = firsts[position + 1] if position + 1 < len(keys) else end
        while stop - 1 > firsts[position] and not lines[stop - 1].strip():
            stop -= 1
        out.append((key, firsts[position], stop, index))
    return out


def _flat(prefix: str, value: Any) -> list[str]:
    """The lines of a parsed value as ``path: text``, for messages."""

    if isinstance(value, dict):
        return [line for key, item in value.items() for line in _flat(f"{prefix}.{key}" if prefix else str(key), item)]
    if isinstance(value, list):
        return [f"{prefix}: {item}" for item in value]
    return [f"{prefix}: {value}"]


def _read(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise UpdateError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        return text, parse(text, path.name)
    except YamlError as exc:
        raise UpdateError(str(exc)) from exc


def _reindent(block: list[str], delta: int) -> list[str]:
    if delta == 0:
        return block
    if delta > 0:
        return [(" " * delta + line) if line.strip() else line for line in block]
    return [line[-delta:] if line.strip() and line[:-delta].strip() == "" else line for line in block]


def _flow_error(name: str, key: str) -> UpdateError:
    return UpdateError(f"{name}: write `{key}` as a block, so that vendomat update can add lines to it")


# --- The plan ------------------------------------------------------------------------------------


def plan(workspace: Path, template: Path) -> tuple[str, list[Addition]]:
    """Return the new text of ``devenv.yaml`` and the additions. The text equals the old one when nothing is missing."""

    name = "devenv.yaml"
    text, user = _read(workspace / name)
    _tpl_text, tpl = _read(template / name)
    tpl_lines = (template / name).read_text().splitlines()
    lines = text.splitlines()
    additions: list[Addition] = []
    tpl_top = {key: (a, b, kl) for key, a, b, kl in _children(tpl_lines, 0, len(tpl_lines), 0)}

    for key, tpl_value in tpl.items():
        if key not in user:
            first, stop, _kl = tpl_top[key]
            while lines and not lines[-1].strip():
                lines.pop()
            lines.extend(tpl_lines[first:stop])
            additions.append(Addition("key", key, tuple(_flat(key, tpl_value))))
            continue
        user_value = user[key]
        if key == "inputs" and isinstance(tpl_value, dict):
            if not isinstance(user_value, dict):
                raise _flow_error(name, key)
            missing = [item for item in tpl_value if item not in user_value]
            if missing:
                _add_inputs(name, lines, tpl_lines, tpl_top["inputs"], tpl_value, missing, additions)
        elif key == "imports" and isinstance(tpl_value, list):
            if not isinstance(user_value, list):
                raise _flow_error(name, key)
            missing_imports = [item for item in tpl_value if item not in user_value]
            if missing_imports:
                _add_imports(name, lines, missing_imports, additions)
    new = "\n".join(lines) + "\n" if additions else text
    return new, additions


def _block_span(name: str, lines: list[str], key: str) -> tuple[int, int]:
    """The key line and the end of the block of a top-level key."""

    found = [(kl, b) for k, _a, b, kl in _children(lines, 0, len(lines), 0) if k == key]
    if not found:
        raise UpdateError(f"{name}: cannot find the `{key}` block to edit")
    first, stop = found[0]
    # The block of a key ends at its last line with content that is not a comment at indent 0.
    while stop - 1 > first:
        last = lines[stop - 1]
        if last.strip() and not (_is_comment(last) and _indent(last) == 0):
            break
        stop -= 1
    return first, stop


def _add_inputs(
    name: str,
    lines: list[str],
    tpl_lines: list[str],
    tpl_span: tuple[int, int, int],
    tpl_inputs: dict[str, Any],
    missing: list[str],
    additions: list[Addition],
) -> None:
    first, stop = _block_span(name, lines, "inputs")
    if lines[first].split("#")[0].rstrip().endswith(("{}", "{")):
        raise _flow_error(name, "inputs")
    user_indent = _first_child_indent(lines, first + 1, stop)
    tpl_children = {k: (a, b) for k, a, b, _kl in _children(tpl_lines, tpl_span[2] + 1, tpl_span[1], 2)}
    block: list[str] = []
    for item in missing:
        a, b = tpl_children[item]
        block.extend(_reindent(tpl_lines[a:b], user_indent - 2))
        additions.append(Addition("input", item, tuple(_flat(f"inputs.{item}", tpl_inputs[item]))))
    lines[stop:stop] = block


def _first_child_indent(lines: list[str], start: int, stop: int) -> int:
    for index in range(start, stop):
        if lines[index].strip() and not _is_comment(lines[index]):
            return _indent(lines[index])
    return 2


def _add_imports(name: str, lines: list[str], missing: list[str], additions: list[Addition]) -> None:
    first, stop = _block_span(name, lines, "imports")
    if "[" in lines[first]:
        raise _flow_error(name, "imports")
    prefix = "  - "
    for index in range(first + 1, stop):
        if lines[index].lstrip().startswith("- "):
            prefix = lines[index][: lines[index].index("-") + 2]
            break
    lines[stop:stop] = [f"{prefix}{item}" for item in missing]
    for item in missing:
        additions.append(Addition("import", item, (f"imports: {item}",)))


# --- The command ---------------------------------------------------------------------------------


def devenv_command() -> str:
    """The devenv command: ``$VENDOMAT_DEVENV``, else ``devenv`` on ``PATH``."""

    return os.environ.get("VENDOMAT_DEVENV") or "devenv"


def check_lines(workspace: Path, template: Path | None = None) -> list[Addition]:
    """List the template lines that ``devenv.yaml`` lacks. Write nothing."""

    return plan(workspace, template or template_dir())[1]


def run_update(workspace: Path, template: Path | None = None) -> list[Addition]:
    """Add the missing template lines to ``devenv.yaml`` and return them."""

    new, additions = plan(workspace, template or template_dir())
    if additions:
        target = workspace / "devenv.yaml"
        try:
            target.write_text(new)
        except OSError as exc:
            raise UpdateError(f"cannot write {target}: {exc.strerror or exc}") from exc
    return additions


def describe(additions: list[Addition]) -> list[str]:
    """One line for each missing template line."""

    return [f"  {line}" for item in additions for line in item.lines]

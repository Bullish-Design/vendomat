"""Read the small subset of YAML that ``devenv.yaml`` files use.

Vendomat depends on Typer only, so it has no YAML library. A ``devenv.yaml`` holds nested maps,
lists of scalars, and short flow collections. This reader accepts exactly that and rejects the
rest with a message that names the line. It never guesses: an unsupported construct is an error,
because a wrong read would write a wrong input into a fragment.

Supported: ``#`` comments, block maps, block lists of scalars, ``[a, b]`` and ``{a: b}`` flow
collections, single and double quoted scalars, ``true``, ``false``, and ``null``.
Rejected: tabs, anchors, aliases, tags, block scalars (``|`` and ``>``), several documents, and
block lists of maps.
"""

from __future__ import annotations

from typing import Any


class YamlError(Exception):
    """A construct the subset does not read. The message names the line."""


def parse(text: str, where: str = "devenv.yaml") -> dict[str, Any]:
    """Parse ``text`` into nested ``dict``, ``list``, ``str``, ``bool``, and ``None`` values."""

    lines = _lines(text, where)
    if not lines:
        return {}
    value, pos = _block(lines, 0, lines[0][1], where)
    if pos != len(lines):
        number = lines[pos][0]
        raise YamlError(f"{where}:{number}: unexpected indentation")
    if not isinstance(value, dict):
        raise YamlError(f"{where}: the document must be a map")
    return value


def _strip_comment(raw: str) -> str:
    quote = ""
    for index, char in enumerate(raw):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or raw[index - 1] in " \t"):
            return raw[:index]
    return raw


def _lines(text: str, where: str) -> list[tuple[int, int, str]]:
    """Return ``(line number, indent, content)`` for each meaningful line."""

    out: list[tuple[int, int, str]] = []
    documents = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        if raw.strip() == "---":
            documents += 1
            if documents > 1 or out:
                raise YamlError(f"{where}:{number}: several documents are not supported")
            continue
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        if "\t" in stripped[: len(stripped) - len(stripped.lstrip())]:
            raise YamlError(f"{where}:{number}: tab indentation is not supported")
        body = stripped.strip()
        if body[0] in "&*!" or body.startswith(("|", ">")):
            raise YamlError(f"{where}:{number}: anchors, aliases, tags, and block scalars are not supported")
        out.append((number, len(stripped) - len(stripped.lstrip(" ")), body))
    return out


def _block(lines: list[tuple[int, int, str]], pos: int, indent: int, where: str) -> tuple[Any, int]:
    if lines[pos][2].startswith("- ") or lines[pos][2] == "-":
        return _list(lines, pos, indent, where)
    return _map(lines, pos, indent, where)


def _list(lines: list[tuple[int, int, str]], pos: int, indent: int, where: str) -> tuple[list[Any], int]:
    out: list[Any] = []
    while pos < len(lines) and lines[pos][1] == indent and (lines[pos][2].startswith("- ") or lines[pos][2] == "-"):
        number, _indent, body = lines[pos]
        item = body[1:].strip()
        if not item:
            raise YamlError(f"{where}:{number}: an empty list item is not supported")
        if _is_map_item(item):
            raise YamlError(f"{where}:{number}: a list of maps is not supported")
        out.append(_scalar_or_flow(item, where, number))
        pos += 1
    return out, pos


def _is_map_item(item: str) -> bool:
    if item[0] in "\"'[{":
        return False
    key, sep, rest = item.partition(":")
    return bool(sep) and (not rest or rest.startswith(" ")) and bool(key)


def _map(lines: list[tuple[int, int, str]], pos: int, indent: int, where: str) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while pos < len(lines) and lines[pos][1] == indent:
        number, _indent, body = lines[pos]
        if body.startswith("- "):
            raise YamlError(f"{where}:{number}: a list item where a key was expected")
        key, sep, rest = _split_key(body)
        if not sep:
            raise YamlError(f"{where}:{number}: expected 'key: value', got {body!r}")
        if key in out:
            raise YamlError(f"{where}:{number}: duplicate key {key!r}")
        pos += 1
        rest = rest.strip()
        if rest:
            out[key] = _scalar_or_flow(rest, where, number)
        elif pos < len(lines) and lines[pos][1] > indent:
            out[key], pos = _block(lines, pos, lines[pos][1], where)
        elif pos < len(lines) and lines[pos][1] == indent and lines[pos][2].startswith("- "):
            out[key], pos = _list(lines, pos, indent, where)
        else:
            out[key] = None
    return out, pos


def _split_key(body: str) -> tuple[str, str, str]:
    if body[0] in "\"'":
        quote = body[0]
        end = body.find(quote, 1)
        if end < 0 or body[end + 1 : end + 2] != ":":
            return body, "", ""
        return body[1:end], ":", body[end + 2 :]
    key, sep, rest = body.partition(":")
    if sep and rest and not rest.startswith(" "):
        # A colon inside a scalar such as `github:owner/repo` is not a key separator.
        return body, "", ""
    return key.strip(), sep, rest


def _scalar_or_flow(text: str, where: str, number: int) -> Any:
    text = text.strip()
    if text[:1] in ("&", "*", "!", "|", ">"):
        raise YamlError(f"{where}:{number}: anchors, aliases, tags, and block scalars are not supported")
    if text.startswith("["):
        if not text.endswith("]"):
            raise YamlError(f"{where}:{number}: a flow list must close on the same line")
        return [_scalar_or_flow(part, where, number) for part in _split_flow(text[1:-1], where, number)]
    if text.startswith("{"):
        if not text.endswith("}"):
            raise YamlError(f"{where}:{number}: a flow map must close on the same line")
        out: dict[str, Any] = {}
        for part in _split_flow(text[1:-1], where, number):
            key, sep, rest = _split_key(part)
            if not sep:
                raise YamlError(f"{where}:{number}: expected 'key: value' in a flow map, got {part!r}")
            out[key] = _scalar_or_flow(rest, where, number)
        return out
    return _scalar(text)


def _split_flow(text: str, where: str, number: int) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote = ""
    current = ""
    for char in text:
        if quote:
            current += char
            if char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += char
    if quote or depth != 0:
        raise YamlError(f"{where}:{number}: unbalanced quote or bracket in a flow collection")
    if current.strip():
        parts.append(current.strip())
    return parts


def _scalar(text: str) -> Any:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "~", "Null"):
        return None
    return text

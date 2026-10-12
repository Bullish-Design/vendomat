# NON-PRODUCTION spike fixture (project 20, spike S1).
# Candidate (b): the same subset, enforced by walking the event stream of PyYAML or ruamel.yaml.
# The walk uses the library for tokenizing and structure. It re-reads the raw source slice for
# escapes, block-scalar headers, and flow-empty forms, because events hide those details.
from __future__ import annotations

import json
import re

import hand
from hand import LintError, IDENT, RESERVED_KEYS, INT_MIN, INT_MAX


def _backend(name):
    if name == "pyyaml":
        import yaml

        return yaml.parse, (yaml.YAMLError,)
    if name == "ruamel":
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        y = YAML(typ="rt")
        return (lambda text: y.parse(text)), (YAMLError,)
    raise ValueError(name)


class _Plain(hand.Parser):
    """Reuse only the plain-scalar classifier of the hand parser."""

    def __init__(self):
        pass


def _classify(text, ln_no, col, path):
    stub = _Plain()
    ln = hand.Line(ln_no, " " * (col - 1) + text)
    return stub.plain(ln, 0, text, path)


def load(data: bytes, backend: str):
    text = hand.precheck(data)
    parse, yerr = _backend(backend)
    lines = text.split("\n")
    stack: list = []  # entries: [container, key_pending, path, seen]
    root = None
    docs = 0

    def pos(ev, off=0):
        return ev.start_mark.line + 1, ev.start_mark.column + 1

    def place(value, ev):
        nonlocal root
        if not stack:
            root = value
            return
        top = stack[-1]
        if isinstance(top["c"], list):
            top["c"].append(value)
        else:
            top["c"][top["key"]] = value
            top["key"] = None

    def cur_path():
        return tuple(stack[-1]["path"]) if stack else ()

    try:
        events = list(parse(text))
    except yerr as exc:
        mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
        line, col = (mark.line + 1, mark.column + 1) if mark else (1, 1)
        raise LintError("syntax", line, col, (), f"YAML syntax fault: {getattr(exc, 'problem', None) or exc}") from None

    for idx, ev in enumerate(events):
        kind = type(ev).__name__
        if kind == "DocumentStartEvent":
            docs += 1
            line, col = pos(ev)
            if getattr(ev, "version", None) or getattr(ev, "tags", None):
                raise LintError("directive", line, col, (), "a directive is not accepted")
            if ev.explicit or docs > 1:
                raise LintError("document-marker", line, col, (), "document markers are not accepted; the file is one document")
        elif kind in ("MappingStartEvent", "SequenceStartEvent"):
            line, col = pos(ev)
            path = cur_path()
            if stack and isinstance(stack[-1]["c"], dict) and stack[-1]["key"] is not None:
                path = tuple(stack[-1]["path"]) + (stack[-1]["key"],)
            elif stack and isinstance(stack[-1]["c"], list):
                path = tuple(stack[-1]["path"]) + (len(stack[-1]["c"]),)
            if getattr(ev, "anchor", None):
                raise LintError("anchor", line, col, path, "anchors (&) are not accepted")
            if getattr(ev, "tag", None):
                raise LintError("tag", line, col, path, "tags (!) are not accepted")
            if getattr(ev, "flow_style", False):
                nxt = events[idx + 1] if idx + 1 < len(events) else None
                rawl = lines[line - 1]
                closing = "SequenceEndEvent" if kind == "SequenceStartEvent" else "MappingEndEvent"
                pair = "[]" if kind == "SequenceStartEvent" else "{}"
                if nxt is not None and type(nxt).__name__ == closing and rawl[col - 1 : col + 1] == pair:
                    pass
                else:
                    raise LintError("flow-collection", line, col, path, "flow collections are not accepted; only exactly [] and {} as a value")
            if kind == "SequenceStartEvent" and not stack:
                raise LintError("root-not-map", line, col, (), "the file must be a map of keys")
            container = {} if kind == "MappingStartEvent" else []
            place(container, ev)
            stack.append({"c": container, "key": None, "path": list(path), "seen": {}, "need_key": kind == "MappingStartEvent"})
        elif kind == "DocumentEndEvent":
            if ev.explicit:
                line, col = pos(ev)
                raise LintError("document-marker", line, col, (), "document markers are not accepted; the file is one document")
        elif kind in ("MappingEndEvent", "SequenceEndEvent"):
            stack.pop()
            if stack and isinstance(stack[-1]["c"], dict):
                stack[-1]["need_key"] = True
        elif kind == "AliasEvent":
            line, col = pos(ev)
            raise LintError("alias", line, col, cur_path(), "aliases (*) are not accepted")
        elif kind == "ScalarEvent":
            line, col = pos(ev)
            top = stack[-1] if stack else None
            is_key = top is not None and isinstance(top["c"], dict) and top["need_key"]
            path = tuple(top["path"]) if top else ()
            if top is not None and isinstance(top["c"], list):
                path += (len(top["c"]),)
            elif top is not None and not is_key:
                path += (top["key"],)
            if getattr(ev, "anchor", None):
                raise LintError("anchor", line, col, path, "anchors (&) are not accepted")
            if getattr(ev, "tag", None):
                raise LintError("tag", line, col, path, "tags (!) are not accepted")
            style = ev.style
            raw_line = lines[line - 1] if line - 1 < len(lines) else ""
            value = ev.value
            if style in ("'", '"'):
                end_line = ev.end_mark.line + 1
                if end_line != line:
                    raise LintError("unterminated-string", line, col, path, "quoted strings must end on the line where they start")
                span = raw_line[col - 1 : ev.end_mark.column]
                if style == '"':
                    for m in re.finditer(r"\\(.)", span):
                        if m.group(1) not in hand.ESCAPES and m.group(1) != "u":
                            raise LintError("bad-escape", line, col + m.start(), path, f"escape \\{m.group(1)} is not accepted")
                    for m in re.finditer(r"\\u([0-9a-fA-F]{4})", span):
                        cp = int(m.group(1), 16)
                        if cp < 0x20 or 0x7F <= cp <= 0x9F or 0xD800 <= cp <= 0xDFFF or cp in (0x2028, 0x2029, 0xFEFF, 0xFFFE, 0xFFFF):
                            raise LintError("bad-escape", line, col + m.start(), path, "escape is a control, surrogate, or reserved character")
                if "\t" in span:
                    raise LintError("tab", line, col + span.index("\t"), path, "a literal tab in a string is not accepted")
            elif style == ">":
                raise LintError("folded-scalar", line, col, path, "folded block scalars (>) are not accepted")
            elif style == "|":
                header = raw_line[col - 1 :]
                m = re.fullmatch(r"\|(-?)( +#.*)?", header.rstrip(" "))
                if not m:
                    raise LintError("block-scalar-form", line, col, path, "only | and |- are accepted")
            else:
                if is_key:
                    if value == "<<":
                        raise LintError("merge-key", line, col, path, "merge keys (<<) are not accepted")
                    if not IDENT.fullmatch(value):
                        raise LintError("bad-key", line, col, path, f"plain key {value!r} must match [A-Za-z_][A-Za-z0-9_-]*; quote it")
                    if value.lower() in RESERVED_KEYS:
                        raise LintError("reserved-key", line, col, path, "reserved word as plain key; quote it")
                else:
                    if value == "" and ev.start_mark.index == ev.end_mark.index:
                        raise LintError("empty-value", line, col, path, "the key has no value")
                    value = _classify(value, line, col, path)
            if is_key:
                if value == "" and style in ("'", '"'):
                    raise LintError("bad-key", line, col, path, "an empty key is not accepted")
                if value in top["seen"]:
                    raise LintError("duplicate-key", line, col, path, f"duplicate key {json.dumps(value)}; first defined on line {top['seen'][value]}")
                top["seen"][value] = line
                top["key"] = value
                top["need_key"] = False
                continue
            place(value, ev)
            if top is not None and isinstance(top["c"], dict):
                top["need_key"] = True
    # empty `[]` / `{}` come through as flow collections; allow them only when exactly empty.
    if root is not None and not isinstance(root, dict):
        raise LintError("root-not-map", 1, 1, (), "the file must be a map of keys")
    return root if root is not None else {}

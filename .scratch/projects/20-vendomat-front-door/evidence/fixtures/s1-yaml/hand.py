# NON-PRODUCTION spike fixture (project 20, spike S1).
# Candidate (d): a hand parser for the strict `vendomat.yaml` subset.
# Standard library only. It raises LintError on the first fault and never guesses.
"""Strict `vendomat.yaml` subset parser (spike).

Accepted: one block map; block maps and block lists; double- and single-quoted strings on one
line; decimal integers in the signed 64-bit range; `true`, `false`, `null`; literal block
scalars `|` and `|-`; exactly `[]` and `{}`; comments.
Plain keys match [A-Za-z_][A-Za-z0-9_-]*; any other key is quoted.
"""

from __future__ import annotations

import json
import re
import sys

INT_MIN, INT_MAX = -(2**63), 2**63 - 1
MAX_DEPTH = 64  # nesting levels of maps and lists

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
RESERVED_KEYS = {"true", "false", "null", "yes", "no", "on", "off"}
# A plain key ends at the first colon that a space or the line end follows.
PLAINKEY = re.compile(r"(\S*?):(?= |$)")
INT_STRICT = re.compile(r"-?(0|[1-9][0-9]*)")
INT_ODD = re.compile(r"[-+]?(0[xXoObB][0-9a-fA-F_]+|[0-9][0-9_]*)")
FLOAT = re.compile(
    r"[-+]?(\.[0-9]+|[0-9][0-9_]*\.[0-9_]*|[0-9][0-9_]*)([eE][-+]?[0-9]+)?"
    r"|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN)"
)
BOOLISH = {"yes", "no", "on", "off", "y", "n", "true", "false", "null", "~"}
BAD_CHARS = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f  ﻿￾￿]")
ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


class LintError(Exception):
    def __init__(self, code: str, line: int, col: int, path: tuple, reason: str):
        super().__init__(reason)
        self.code, self.line, self.col, self.path, self.reason = code, line, col, tuple(path), reason

    def format(self, name: str = "vendomat.yaml") -> str:
        return f"{name}:{self.line}:{self.col}: {fmt_path(self.path)}: {self.reason}"


def fmt_path(path) -> str:
    if not path:
        return "<root>"
    out = ""
    for part in path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            piece = part if IDENT.fullmatch(part) else json.dumps(part, ensure_ascii=False)
            out += ("." if out else "") + piece
    return out


class Line:
    __slots__ = ("no", "col0", "content", "raw")

    def __init__(self, no: int, raw: str):
        stripped = raw.lstrip(" ")
        self.no, self.raw = no, raw
        self.col0 = len(raw) - len(stripped)
        self.content = stripped.rstrip(" ")

    @property
    def blank(self) -> bool:
        return self.raw.strip(" ") == ""


def is_dash(c: str) -> bool:
    return c == "-" or c.startswith("- ")


def precheck(data: bytes) -> str:
    """Byte and character rules that hold everywhere in the file."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise LintError("bom", 1, 1, (), "a byte order mark is not accepted; save the file as UTF-8 without BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        line = data.count(b"\n", 0, exc.start) + 1
        col = exc.start - (data.rfind(b"\n", 0, exc.start) + 1) + 1
        raise LintError("not-utf8", line, col, (), f"byte {col} of the line is not valid UTF-8") from None
    for m in BAD_CHARS.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        col = m.start() - (text.rfind("\n", 0, m.start()) + 1) + 1
        ch = m.group()
        if ch == "\r":
            raise LintError("cr", line, col, (), "carriage return is not accepted; use LF line ends")
        raise LintError("control-char", line, col, (), f"character U+{ord(ch):04X} is not accepted; use an escape in a quoted string")
    if text and not text.endswith("\n"):
        line = text.count("\n") + 1
        raise LintError("no-final-newline", line, len(text) - (text.rfind("\n") + 1) + 1, (), "the file must end with a line feed")
    return text


class Parser:
    def __init__(self, text: str):
        raw = text.split("\n")
        if raw and raw[-1] == "":
            raw.pop()
        self.lines = [Line(i + 1, r) for i, r in enumerate(raw)]
        self.i = 0
        self.depth = 1  # the root map is level 1
        self.keylocs: dict[tuple, tuple[int, int]] = {}
        self.vlocs: dict[tuple, tuple[int, int]] = {}

    # ---- helpers
    def err(self, code, ln: Line, idx: int, path, reason):
        return LintError(code, ln.no, ln.col0 + idx + 1, path, reason)

    def sig(self, i: int):
        n = len(self.lines)
        while i < n:
            ln = self.lines[i]
            if not ln.blank and not ln.raw.lstrip(" ").startswith("#"):
                if ln.content.startswith("\t"):
                    raise self.err("tab", ln, 0, (), "a tab is not accepted; use spaces")
                return i
            i += 1
        return None

    def marker(self, ln: Line, path):
        c = ln.content
        if ln.col0 == 0:
            if c.startswith("%"):
                raise self.err("directive", ln, 0, path, "a directive is not accepted")
            if c in ("---", "...") or c.startswith(("--- ", "... ")):
                raise self.err("document-marker", ln, 0, path, "document markers are not accepted; the file is one document")

    # ---- entry
    def document(self):
        j = self.sig(0)
        if j is None:
            return {}
        ln = self.lines[j]
        self.marker(ln, ())
        if is_dash(ln.content):
            raise self.err("root-not-map", ln, 0, (), "the file must be a map of keys; found a list item")
        value = self.parse_map(ln.col0, ())
        k = self.sig(self.i)
        if k is not None:
            self.marker(self.lines[k], ())
            raise self.err("indent", self.lines[k], 0, (), "unexpected indentation")
        return value

    def parse_node(self, j: int, path):
        ln = self.lines[j]
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise self.err("too-deep", ln, 0, path, f"nesting is deeper than {MAX_DEPTH} levels")
        try:
            if is_dash(ln.content):
                return self.parse_seq(ln.col0, path)
            return self.parse_map(ln.col0, path)
        finally:
            self.depth -= 1

    # ---- maps
    def parse_map(self, indent: int, path):
        out: dict = {}
        first: dict = {}
        while True:
            j = self.sig(self.i)
            if j is None:
                break
            ln = self.lines[j]
            self.marker(ln, path)
            if ln.col0 < indent:
                break
            if ln.col0 > indent:
                raise self.err("indent", ln, 0, path, "unexpected indentation")
            if is_dash(ln.content):
                raise self.err("syntax", ln, 0, path, "a list item where a key was expected")
            key, kend = self.read_key(ln, path)
            if key in first:
                raise self.err("duplicate-key", ln, 0, path + (key,), f"duplicate key {json.dumps(key, ensure_ascii=False)}; first defined on line {first[key]}")
            first[key] = ln.no
            p = path + (key,)
            self.keylocs[p] = (ln.no, ln.col0 + 1)
            rest = ln.content[kend:]
            body = rest.lstrip(" ")
            self.i = j + 1
            if body == "" or body.startswith("#"):
                k = self.sig(self.i)
                if k is not None and self.lines[k].col0 > indent:
                    value = self.parse_node(k, p)
                elif k is not None and self.lines[k].col0 == indent and is_dash(self.lines[k].content):
                    value = self.parse_seq_deep(indent, p, ln)
                else:
                    raise self.err("empty-value", ln, kend, p, "the key has no value; write null, \"\", [], {}, or a nested block")
            else:
                value = self.parse_inline(j, kend + len(rest) - len(body), p, indent)
            out[key] = value
        return out

    def read_key(self, ln: Line, path):
        c = ln.content
        ch = c[0]
        if ch in "\"'":
            text, end = self.scan_quoted(ln, 0, path)
            if not (c[end : end + 1] == ":" and (end + 1 == len(c) or c[end + 1] == " ")):
                raise self.err("syntax", ln, end, path, "expected ':' and a space after a quoted key")
            if text == "":
                raise self.err("bad-key", ln, 0, path, "an empty key is not accepted")
            return text, end + 1
        self.indicator(ln, 0, path, as_key=True)
        m = PLAINKEY.match(c)
        if not m:
            tab = c.find("\t")
            if tab >= 0:
                raise self.err("tab", ln, tab, path, "a tab is not accepted; use spaces")
            raise self.err("syntax", ln, 0, path, "expected `key: value` (no space before the colon)")
        text = m.group(1)
        if text == "<<":
            raise self.err("merge-key", ln, 0, path, "merge keys (<<) are not accepted")
        if text == "":
            raise self.err("syntax", ln, 0, path, "a key is missing before the colon")
        if not IDENT.fullmatch(text):
            raise self.err("bad-key", ln, 0, path + (text,), f"plain key {text!r} must match [A-Za-z_][A-Za-z0-9_-]*; quote it")
        if text.lower() in RESERVED_KEYS:
            raise self.err("reserved-key", ln, 0, path + (text,), f"key {text!r} reads as a boolean or null in some YAML versions; quote it")
        return text, m.end()

    def indicator(self, ln: Line, idx: int, path, as_key=False):
        c = ln.content
        ch = c[idx]
        if ch == "&":
            raise self.err("anchor", ln, idx, path, "anchors (&) are not accepted")
        if ch == "*":
            raise self.err("alias", ln, idx, path, "aliases (*) are not accepted")
        if ch == "!":
            raise self.err("tag", ln, idx, path, "tags (!) are not accepted")
        if ch == "?" and (idx + 1 == len(c) or c[idx + 1] == " "):
            raise self.err("complex-key", ln, idx, path, "complex keys (?) are not accepted")
        if ch in "[{":
            raise self.err("flow-collection", ln, idx, path, "flow collections are not accepted; only [] and {} as a value")
        if ch == "%":
            raise self.err("directive" if ln.col0 + idx == 0 else "syntax", ln, idx, path, "a directive is not accepted" if ln.col0 + idx == 0 else "'%' cannot start a value")
        if ch in "@`,]}":
            raise self.err("syntax", ln, idx, path, f"{ch!r} is a reserved YAML indicator; quote the text")
        if as_key and ch in "|>":
            raise self.err("syntax", ln, idx, path, "a block scalar cannot be a key")

    # ---- sequences
    def parse_seq_deep(self, indent: int, path, ln: Line):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise self.err("too-deep", ln, 0, path, f"nesting is deeper than {MAX_DEPTH} levels")
        try:
            return self.parse_seq(indent, path)
        finally:
            self.depth -= 1

    def parse_seq(self, indent: int, path):
        out: list = []
        while True:
            j = self.sig(self.i)
            if j is None:
                break
            ln = self.lines[j]
            self.marker(ln, path)
            if ln.col0 < indent:
                break
            if ln.col0 > indent:
                raise self.err("indent", ln, 0, path, "unexpected indentation")
            if not is_dash(ln.content):
                break
            p = path + (len(out),)
            self.keylocs[p] = (ln.no, ln.col0 + 1)
            rest = ln.content[1:]
            body = rest.lstrip(" ")
            idx = 1 + len(rest) - len(body)
            self.i = j + 1
            if body == "" or body.startswith("#"):
                k = self.sig(self.i)
                if k is not None and self.lines[k].col0 > indent:
                    value = self.parse_node(k, p)
                else:
                    raise self.err("empty-value", ln, 1, p, "the list item has no value; write null or a nested block")
            elif is_dash(body) or self.has_key(body):
                ln.col0 += idx
                ln.content = body
                self.i = j
                value = self.parse_node(j, p)
            else:
                value = self.parse_inline(j, idx, p, indent)
            out.append(value)
        return out

    def has_key(self, body: str) -> bool:
        if body[0] in "\"'":
            q = body[0]
            k = 1
            while k < len(body):
                if body[k] == "\\" and q == '"':
                    k += 2
                    continue
                if body[k] == q:
                    if q == "'" and body[k + 1 : k + 2] == "'":
                        k += 2
                        continue
                    return body[k + 1 : k + 2] == ":" and (k + 2 == len(body) or body[k + 2] == " ")
                k += 1
            return False
        if body[0] in "&*!%@`,]}[{|>":
            return False
        return PLAINKEY.match(body) is not None

    # ---- values
    def scan_quoted(self, ln: Line, idx: int, path):
        c = ln.content
        q = c[idx]
        k = idx + 1
        buf: list[str] = []
        while k < len(c):
            ch = c[k]
            if ch == "\t":
                raise self.err("tab", ln, k, path, "a literal tab in a string is not accepted; use \\t")
            if q == "'":
                if ch == "'":
                    if c[k + 1 : k + 2] == "'":
                        buf.append("'")
                        k += 2
                        continue
                    return "".join(buf), k + 1
                buf.append(ch)
                k += 1
                continue
            if ch == '"':
                return "".join(buf), k + 1
            if ch == "\\":
                nxt = c[k + 1 : k + 2]
                if nxt in ESCAPES:
                    buf.append(ESCAPES[nxt])
                    k += 2
                    continue
                if nxt == "u":
                    hexs = c[k + 2 : k + 6]
                    if len(hexs) != 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hexs):
                        raise self.err("bad-escape", ln, k, path, "\\u needs four hex digits")
                    cp = int(hexs, 16)
                    if cp < 0x20 or 0x7F <= cp <= 0x9F or 0xD800 <= cp <= 0xDFFF or cp in (0x2028, 0x2029, 0xFEFF, 0xFFFE, 0xFFFF):
                        raise self.err("bad-escape", ln, k, path, f"escape \\u{hexs} is not accepted; it is a control, surrogate, or reserved character")
                    buf.append(chr(cp))
                    k += 6
                    continue
                raise self.err("bad-escape", ln, k, path, f"escape \\{nxt} is not accepted; allowed: \\\\ \\\" \\/ \\n \\t \\r \\b \\f \\uXXXX")
            buf.append(ch)
            k += 1
        raise self.err("unterminated-string", ln, idx, path, "the quoted string does not end on this line; quoted strings are one line (use a | block for several lines)")

    def after_value(self, ln: Line, idx: int, path):
        rest = ln.content[idx:]
        if rest == "":
            return
        if rest[0] == "\t":
            raise self.err("tab", ln, idx, path, "a tab is not accepted; use spaces")
        if rest[0] != " ":
            raise self.err("trailing-text", ln, idx, path, f"unexpected text {rest!r} after the value")
        s = rest.lstrip(" ")
        if s == "" or s[0] == "#":
            return
        pos = idx + len(rest) - len(s)
        if s[0] == "\t":
            raise self.err("tab", ln, pos, path, "a tab is not accepted; use spaces")
        raise self.err("trailing-text", ln, pos, path, f"unexpected text {s!r} after the value")

    def parse_inline(self, j: int, idx: int, path, parent_indent: int):
        ln = self.lines[j]
        c = ln.content
        self.vlocs[path] = (ln.no, ln.col0 + idx + 1)
        ch = c[idx]
        if ch in "\"'":
            text, end = self.scan_quoted(ln, idx, path)
            self.after_value(ln, end, path)
            return text
        if ch == "|":
            return self.block_scalar(j, idx, path, parent_indent)
        if ch == ">":
            raise self.err("folded-scalar", ln, idx, path, "folded block scalars (>) are not accepted; use | with one line per line")
        if ch in "[{":
            pair = "[]" if ch == "[" else "{}"
            if c[idx : idx + 2] == pair:
                self.after_value(ln, idx + 2, path)
                return [] if ch == "[" else {}
            raise self.err("flow-collection", ln, idx, path, "flow collections are not accepted; only exactly [] and {} (no inner space)")
        self.indicator(ln, idx, path)
        if ch == "-" and c[idx + 1 : idx + 2] == " ":
            raise self.err("syntax", ln, idx, path, "a list item cannot start on the line of a key")
        rest = c[idx:]
        cut = rest.find(" #")
        text = (rest if cut < 0 else rest[:cut]).rstrip(" ")
        tab = text.find("\t")
        if tab >= 0:
            raise self.err("tab", ln, idx + tab, path, "a tab is not accepted; use spaces")
        return self.plain(ln, idx, text, path)

    def plain(self, ln: Line, idx: int, text: str, path):
        if text == "true":
            return True
        if text == "false":
            return False
        if text == "null":
            return None
        if text == "~":
            raise self.err("null-form", ln, idx, path, "write null, not ~")
        if INT_STRICT.fullmatch(text):
            if text == "-0":
                raise self.err("int-form", ln, idx, path, "write 0, not -0")
            v = int(text)
            if not INT_MIN <= v <= INT_MAX:
                raise self.err("int-range", ln, idx, path, f"integer {text} is outside the signed 64-bit range")
            return v
        if FLOAT.fullmatch(text) and not INT_ODD.fullmatch(text):
            raise self.err("float", ln, idx, path, f"floats are not accepted ({text}); quote a version or text, or use native Nix for a float option")
        if INT_ODD.fullmatch(text):
            raise self.err("int-form", ln, idx, path, f"integer form {text!r} is not accepted; write a plain decimal integer such as 12")
        if text.lower() in BOOLISH:
            raise self.err("implicit-string", ln, idx, path, f"the word {text!r} reads as a boolean or null in some YAML versions; write true, false, or null, or quote it: \"{text}\"")
        raise self.err("implicit-string", ln, idx, path, f"unquoted text {text!r} is a string; quote it: \"{text}\"")

    def block_scalar(self, j: int, idx: int, path, parent_indent: int):
        ln = self.lines[j]
        c = ln.content
        head = c[idx + 1 :]
        chomp = ""
        if head.startswith("-"):
            chomp = "-"
            head = head[1:]
        if head[:1] in ("+", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
            raise self.err("block-scalar-form", ln, idx, path, "only | and |- are accepted (no + and no indentation digit)")
        if head != "" and not head.startswith(" "):
            raise self.err("trailing-text", ln, idx + 1, path, f"unexpected text {head!r} after the block header")
        hs = head.lstrip(" ")
        if hs and hs[0] != "#":
            raise self.err("trailing-text", ln, idx + len(c[idx:]) - len(hs), path, f"unexpected text {hs!r} after the block header")
        acc: list[str] = []
        m = None
        i = j + 1
        n = len(self.lines)
        while i < n:
            raw = self.lines[i].raw
            spaces = len(raw) - len(raw.lstrip(" "))
            if raw.strip(" ") == "":
                if m is not None:
                    acc.append(raw[m:] if len(raw) > m else "")
                else:
                    acc.append(raw)
                i += 1
                continue
            if m is None:
                if spaces <= parent_indent:
                    break
                if raw[spaces : spaces + 1] == "\t":
                    raise LintError("tab", self.lines[i].no, spaces + 1, path, "the first text line of a block scalar cannot start with a tab; use spaces")
                m = spaces
                for k, prev in enumerate(acc):
                    if len(prev) > m:
                        raise LintError("bad-indent", self.lines[j + 1 + k].no, m + 1, path, "a blank line before the text has more spaces than the first text line")
                    acc[k] = ""
            elif spaces < m:
                break
            acc.append(raw[m:])
            i += 1
        while acc and acc[-1] == "":
            acc.pop()
        self.i = i
        if m is None or not acc:
            return ""
        return "\n".join(acc) + ("" if chomp == "-" else "\n")


def load(data: bytes):
    """Return (tree, parser). Raise LintError on the first fault."""
    text = precheck(data)
    p = Parser(text)
    tree = p.document()
    return tree, p


# ---- DOOR-014 secret recognizer (syntax-time, key names and string values only)
SECRET_WORDS = {"password", "passwd", "passphrase", "secret", "token", "credential", "credentials"}
SECRET_PAIRS = {("api", "key"), ("private", "key"), ("secret", "key"), ("auth", "key"), ("signing", "key")}
SAFE_LAST = {"file", "path", "dir", "env", "name", "helper", "command", "cmd", "authentication", "policy", "length", "url"}
_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def words(key: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(key)]


def is_secret_key(key: str) -> bool:
    ws = words(key)
    if not ws or ws[-1] in SAFE_LAST:
        return False
    if any(w in SECRET_WORDS for w in ws):
        return True
    return any((a, b) in SECRET_PAIRS for a, b in zip(ws, ws[1:]))


def find_secrets(tree, parser: Parser):
    """Return LintError objects for non-empty string values under recognized secret keys."""
    found: list[LintError] = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                p = path + (k,)
                if isinstance(v, str) and v != "" and is_secret_key(k):
                    line, col = parser.vlocs.get(p, parser.keylocs.get(p, (0, 0)))
                    found.append(LintError("secret", line, col, p, "recognized secret field with a literal value; keep private values out of vendomat.yaml (use SecretSpec and a *File option)"))
                else:
                    walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + (i,))

    walk(tree, ())
    return found


def canonical(tree) -> bytes:
    return (json.dumps(tree, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def main(argv):
    name = argv[1]
    data = open(name, "rb").read()
    try:
        tree, parser = load(data)
        secrets = find_secrets(tree, parser)
        if secrets:
            raise secrets[0]
    except LintError as exc:
        print(exc.format(name), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(tree))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

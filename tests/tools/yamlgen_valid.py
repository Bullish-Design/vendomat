"""Generator for valid `vendomat.yaml` documents (the spike generator `gen2.py`). Standard library only.

Every document comes with the tree that the parser must return (`pNNNN.tree.json`) and a record of its
lines (`pNNNN.meta.json`) that `yamlgen_variants.py` uses to build tab variants and fault variants.

An indentation piece is `["free", width, id]` (a child block that a variant may render again) or
`["fixed", width]` (the spaces that a compact item `- ` puts before its continuation lines).

Use: `python yamlgen_valid.py OUTDIR COUNT SEED [nest] [tabtext]`

- `nest` raises the share of lists inside lists and of maps inside nested lists.
- `tabtext` puts tab characters into plain values.

The same seed gives the same files. The seeds of the project 21 spike corpora are in `tests/test_parser_fuzz.py`.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

PLAIN = [
    "a",
    "b",
    "ripgrep",
    "jq",
    "3.10",
    "no",
    "yes",
    "true",
    "false",
    "012",
    "~",
    "hello world",
    "x-y",
    "a.b",
    "http://h/p",
    "caf\u00e9",
    "\u65e5\u672c",
    "1e3",
    "-1",
    ".5",
    "it's",
    'say "hi"',
    "a:b",
    "x,y",
    "a#b",
    "k=v",
    "a  b",
    "100%",
    "/usr/bin/env",
    "$HOME",
    "x - y",
    "10.0.0.2",
    "a-b c",
    "\U0001f600 ok",
    "null",
    "0x1F",
]
TAB_PLAIN = ["a\tb", "x\t\ty", "tab\tend z"]
QUOTED_TOKENS = [
    "a",
    "b c",
    "x: y",
    " # not comment",
    "- dash",
    "[x]",
    "{y}",
    "&a",
    "*b",
    "!t",
    "|p",
    ">q",
    "@",
    "%",
    "  sp  ",
    "",
    "\u00e9",
    "\u65e5\u672c",
    "\U0001f600",
    "3.10",
    "back\\slash",
    'a"b',
    "it's",
    "tab\there",
    "line\nbreak",
    "#",
    ": ",
]
PLAIN_KEYS = [
    "a",
    "b",
    "c",
    "name",
    "version",
    "enable",
    "env",
    "GREETING",
    "a.b",
    "c-d",
    "e_f",
    "_g",
    "k1",
    "Z9",
    "x.y-z_1",
    "services",
    "address",
    "prefix",
    "gateway",
    "no",
    "on",
    "null",
    "y",
    "A",
]
QUOTED_KEYS = [
    "a b",
    "x: y",
    "3d",
    "-k",
    "\u00e9",
    "k # 1",
    "caf\u00e9 au lait",
    "\u65e5",
    "a",
    "name",
    "k:1",
    "[k]",
    "&k",
    "*",
]

Node = tuple[Any, ...]


class Generator:
    """One generator holds one random stream. The order of the calls to `rnd` fixes the output."""

    def __init__(self, seed: int, *, nest: bool = False, tabtext: bool = False) -> None:
        self.rnd = random.Random(seed)
        self.nest = nest
        self.tabtext = tabtext
        self.lines: list[dict[str, Any]] = []
        self.blocks: list[dict[str, Any]] = []
        self.next_id = 0

    # --- Text of values ---------------------------------------------------------------------

    def dq(self, v: str) -> str:
        escaped = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return '"' + escaped.replace("\t", self.rnd.choice(["\\t", "\t"])) + '"'

    @staticmethod
    def sq(v: str) -> str:
        return "'" + v.replace("'", "''") + "'"

    def quote_value(self) -> tuple[str, str]:
        v = "".join(self.rnd.choice(QUOTED_TOKENS) for _ in range(self.rnd.choice([1, 1, 1, 2, 3])))
        if self.rnd.random() < 0.5:
            return v, self.dq(v)
        v = v.replace("\n", " ")
        return v, self.sq(v)

    def scalar(self) -> tuple[str, str]:
        """A value and its text, for a value position."""
        if self.rnd.random() < 0.55:
            w = self.rnd.choice(PLAIN + (TAB_PLAIN * 6 if self.tabtext else []))
            return w, w
        return self.quote_value()

    def comment_tail(self, p: float = 0.2) -> str:
        if self.rnd.random() < p:
            return self.rnd.choice(["", " ", "  "]) + self.rnd.choice([" # c", " # note: x", " #", " # - a: b"])
        return ""

    # --- Lines and blocks -------------------------------------------------------------------

    def new_id(self) -> int:
        self.next_id += 1
        return self.next_id

    def free(self) -> list[Any]:
        return ["free", self.rnd.choice([1, 2, 2, 2, 3, 4]), self.new_id()]

    def noise(self) -> None:
        r = self.rnd.random()
        if r < 0.07:
            self.lines.append({"raw": self.rnd.choice(["", "", "   ", "  "]), "noise": True})
        elif r < 0.13:
            indent = " " * self.rnd.choice([0, 1, 2, 4, 6])
            self.lines.append({"raw": indent + self.rnd.choice(["# c", "#c", "# - x: y", "#"]), "noise": True})

    def line(self, pieces: list[Any], text: str, blk: int, idx: int) -> None:
        self.lines.append({"pieces": pieces, "text": text, "blk": blk, "idx": idx})

    def new_block(self, kind: str, path: list[Any], parent: int | None) -> dict[str, Any]:
        b: dict[str, Any] = {"id": len(self.blocks), "kind": kind, "path": path, "parent": parent, "entries": []}
        self.blocks.append(b)
        return b

    def child(self, node: Node, cpath: list[Any], parent: int) -> None:
        if node[0] == "map":
            self.emit_map(node[1], cpath, parent, None)
        else:
            self.emit_list(node[1], cpath, parent, None)

    def emit_map(
        self, entries: list[Any], path: list[Any], parent: int | None, head: tuple[list[Any], str] | None
    ) -> dict[str, Any]:
        """`head` is None, or the pieces and the prefix text of the first line (a compact item starts here)."""
        b = self.new_block("map", path, parent)
        for idx, (ktxt, v) in enumerate(entries):
            if idx > 0 or head is None:
                self.noise()
            first = idx == 0 and head is not None
            pieces = head[0] if first and head is not None else path
            pre = head[1] if first and head is not None else ""
            if v[0] == "s":
                sp = " " * self.rnd.choice([1, 1, 1, 2])
                self.line(pieces, pre + ktxt + ":" + sp + v[2] + self.comment_tail(), b["id"], idx)
            else:
                self.line(pieces, pre + ktxt + ":" + self.comment_tail(0.15), b["id"], idx)
            b["entries"].append({"line": len(self.lines) - 1, "pure": not first})
            if v[0] != "s":
                self.child(v, [*path, self.free()], b["id"])
        return b

    def emit_list(
        self, items: list[Any], path: list[Any], parent: int | None, head: tuple[list[Any], str] | None
    ) -> dict[str, Any]:
        b = self.new_block("list", path, parent)
        for idx, it in enumerate(items):
            if idx > 0 or head is None:
                self.noise()
            first = idx == 0 and head is not None
            pieces = head[0] if first and head is not None else path
            pre = head[1] if first and head is not None else ""
            sk = self.rnd.choice([1, 1, 1, 2, 3])
            dash = "-" + " " * sk
            if it[0] == "s":
                self.line(pieces, pre + dash + it[2] + self.comment_tail(), b["id"], idx)
                b["entries"].append({"line": len(self.lines) - 1, "pure": not first})
            elif self.rnd.random() < 0.65:
                # Compact: the inner block starts on this line.
                n0 = len(self.lines)
                inner = [*path, ["fixed", 1 + sk, self.new_id()]]
                hd = (pieces, pre + dash)
                if it[0] == "map":
                    self.emit_map(it[1], inner, b["id"], hd)
                else:
                    self.emit_list(it[1], inner, b["id"], hd)
                b["entries"].append({"line": n0, "pure": not first})
            else:
                # Bare: the dash stands alone and the block follows, indented.
                self.line(pieces, pre + "-" + self.comment_tail(0.3), b["id"], idx)
                b["entries"].append({"line": len(self.lines) - 1, "pure": not first})
                self.child(it, [*path, self.free()], b["id"])
        return b

    # --- Trees ------------------------------------------------------------------------------

    def mk_key(self, used: set[str]) -> tuple[str, str] | None:
        for _ in range(20):
            if self.rnd.random() < 0.82:
                k = self.rnd.choice(PLAIN_KEYS)
                t = k
            else:
                k = self.rnd.choice(QUOTED_KEYS)
                t = self.dq(k) if self.rnd.random() < 0.5 else self.sq(k)
            if k not in used:
                used.add(k)
                return k, t
        return None

    def mk_node(self, depth: int, kind: str, maxdepth: int) -> tuple[Node, Any]:
        """A node and its value. A node is ("map", [(keytext, node)]), ("list", [node]), or ("s", value, text)."""
        n = self.rnd.choice([1, 1, 2, 2, 3, 4])
        if kind == "map":
            used: set[str] = set()
            ents: list[tuple[str, Node]] = []
            val: dict[str, Any] = {}
            for _ in range(n):
                kt = self.mk_key(used)
                if kt is None:
                    break
                k, t = kt
                r = self.rnd.random()
                if depth < maxdepth and r < 0.18:
                    sub = self.mk_node(depth + 1, "map", maxdepth)
                elif depth < maxdepth and r < (0.55 if self.nest else 0.40):
                    sub = self.mk_node(depth + 1, "list", maxdepth)
                else:
                    v, st = self.scalar()
                    sub = (("s", v, st), v)
                ents.append((t, sub[0]))
                val[k] = sub[1]
            return ("map", ents), val
        items: list[Node] = []
        lval: list[Any] = []
        for _ in range(n):
            r = self.rnd.random()
            if depth < maxdepth and r < (0.30 if self.nest else 0.22):
                sub = self.mk_node(depth + 1, "map", maxdepth)
            elif depth < maxdepth and r < (0.70 if self.nest else 0.38):
                sub = self.mk_node(depth + 1, "list", maxdepth)
            else:
                v, st = self.scalar()
                sub = (("s", v, st), v)
            items.append(sub[0])
            lval.append(sub[1])
        return ("list", items), lval


def generate(out: Path, count: int, seed: int, *, nest: bool = False, tabtext: bool = False) -> None:
    """Write `count` documents (`pNNNN.yaml`, `.tree.json`, `.meta.json`) to `out`."""
    out.mkdir(parents=True, exist_ok=True)
    g = Generator(seed, nest=nest, tabtext=tabtext)
    for n in range(count):
        g.lines = []
        g.blocks = []
        g.next_id = 0
        node, val = g.mk_node(0, "map", g.rnd.choice([2, 3, 4, 5, 6]))
        g.emit_map(node[1], [], None, None)
        name = f"p{n:04d}"
        crlf = g.rnd.random() < 0.04
        texts = []
        for rec in g.lines:
            if rec.get("noise"):
                texts.append(rec["raw"])
            else:
                texts.append("".join(" " * p[1] for p in rec["pieces"]) + rec["text"])
        nl = "\r\n" if crlf else "\n"
        doc = nl.join(texts) + g.rnd.choice([nl, nl, nl, ""])
        (out / f"{name}.yaml").write_bytes(doc.encode("utf-8"))
        (out / f"{name}.tree.json").write_text(json.dumps(val, ensure_ascii=False), encoding="utf-8")
        meta = {"lines": g.lines, "blocks": g.blocks, "crlf": crlf, "final_nl": doc.endswith("\n")}
        (out / f"{name}.meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> None:
    out, count, seed = Path(argv[0]), int(argv[1]), int(argv[2])
    flags = argv[3:]
    generate(out, count, seed, nest="nest" in flags, tabtext="tabtext" in flags)
    print("wrote", count)


if __name__ == "__main__":
    main(sys.argv[1:])

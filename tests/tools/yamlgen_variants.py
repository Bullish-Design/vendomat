"""Generator for tab variants and indentation faults of valid documents (the spike generator `gen3.py`).

It reads the `pNNNN.meta.json` files that `yamlgen_valid.py` wrote and renders each document again with
tabs in the indentation.

- `OUTDIR/valid/pNNNN.vK.yaml`: valid variants. Each variant parses to the tree of its source document
  (`pNNNN.tree.json` in the source directory). `v1` and `v3` use tabs only. The others mix tabs and spaces.
  `v3` to `v6` also use the tab form for a compact item (item indentation plus one tab).
- `OUTDIR/invalid/pNNNN.F.yaml`: one indentation fault per fault kind F. The kinds are `a` (a sibling with
  a changed last character), `b` (a first row that is not under the parent), `c` (a block cut short), and `d`
  (a continuation of a compact item in the other form).
- `OUTDIR/invalid.json`: for each invalid file, the expected position (`line`, `col`), the fault kind, and
  whether the document has a tab.

Use: `python yamlgen_variants.py SRCDIR OUTDIR SEED`

The same seed gives the same files.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any

PIECES = ["\t", "\t", "\t\t", "  ", " ", " \t", "\t ", "\t  ", "   ", "    ", "\t\t "]
Meta = dict[str, Any]
Block = dict[str, Any]


def flip(s: str) -> str:
    """Change the last character between a tab and a space."""
    return s[:-1] + (" " if s[-1] == "\t" else "\t")


class Variants:
    def __init__(self, seed: int) -> None:
        self.rnd = random.Random(seed)
        # Fixed piece id -> "tab" (item indentation plus one tab). An id that is absent uses the dash spaces.
        self.forms: dict[int, str] = {}

    def mapping(self, meta: Meta, mode: str) -> dict[int, str]:
        """The indentation of each free piece.

        `mode` is `tabs` or `mixed`; a suffix `-t` makes every compact item use the tab form and a suffix `-r`
        makes a random half use it.
        """
        self.forms.clear()
        rows = [rec for rec in meta["lines"] if not rec.get("noise")]
        ids = {p[2] for rec in rows for p in rec["pieces"] if p[0] == "free"}
        fids = {p[2] for rec in rows for p in rec["pieces"] if p[0] == "fixed"}
        if mode.endswith("-t"):
            self.forms.update({i: "tab" for i in fids})
        if mode.endswith("-r"):
            self.forms.update({i: "tab" for i in fids if self.rnd.random() < 0.5})
        if mode.startswith("tabs"):
            return {i: "\t" for i in ids}
        return {i: self.rnd.choice(PIECES) for i in ids}

    def piece(self, p: list[Any], mp: dict[int, str]) -> str:
        if p[0] == "fixed":
            return "\t" if self.forms.get(p[2]) == "tab" else " " * p[1]
        return mp[p[2]]

    def ind(self, pieces: list[Any], mp: dict[int, str]) -> str:
        return "".join(self.piece(p, mp) for p in pieces)

    def noise_text(self, raw: str) -> str:
        """A comment or blank row, with random white space before the text."""
        body = raw.lstrip(" ")
        if body == "" and raw:
            return self.rnd.choice(["\t", " \t ", "\t\t", raw])
        return self.rnd.choice(["", "\t", "\t\t", " \t", "  ", raw[: len(raw) - len(body)]]) + body

    def render(self, meta: Meta, mp: dict[int, str], overrides: dict[int, str] | None = None) -> str:
        nl = "\r\n" if meta["crlf"] else "\n"
        rows = []
        for k, rec in enumerate(meta["lines"]):
            if rec.get("noise"):
                rows.append(self.noise_text(rec["raw"]))
                continue
            i = overrides[k] if overrides and k in overrides else self.ind(rec["pieces"], mp)
            rows.append(i + rec["text"])
        return nl.join(rows) + (nl if meta["final_nl"] else "")

    def fault_candidates(self, meta: Meta, mp: dict[int, str]) -> dict[str, list[tuple[Block, Any]]]:
        lines = meta["lines"]
        blocks = meta["blocks"]
        faults: dict[str, list[tuple[Block, Any]]] = {"a": [], "b": [], "c": [], "d": []}

        def bstr(b: Block) -> str:
            return self.ind(b["path"], mp)

        def has_child(b: Block) -> bool:
            # The first entry of b has a child block when the next row is deeper than b.
            k = b["entries"][0]["line"] + 1
            while k < len(lines) and lines[k].get("noise"):
                k += 1
            if k >= len(lines):
                return False
            pieces = lines[k]["pieces"]
            return len(pieces) > len(b["path"]) and pieces[: len(b["path"])] == b["path"]

        for b in blocks:
            s = bstr(b)
            p = blocks[b["parent"]] if b["parent"] is not None else None
            ps = bstr(p) if p else ""
            if s:
                for e in b["entries"][1:]:
                    if e["pure"]:
                        faults["a"].append((b, e))
            if p and b["entries"] and b["entries"][0]["pure"] and ps:
                faults["b"].append((b, b["entries"][0]))
            if b["path"] and b["path"][-1][0] == "fixed" and len(b["entries"]) >= 2:
                for j, e in enumerate(b["entries"]):
                    if (j >= 2 and e["pure"]) or (j == 1 and e["pure"] and has_child(b)):
                        faults["d"].append((b, e))
            if p and len(s) - len(ps) >= 2:
                for e in b["entries"][1:]:
                    if e["pure"]:
                        faults["c"].append((b, e))
        return faults

    def fault_indent(self, kind: str, meta: Meta, mp: dict[int, str], b: Block) -> str:
        blocks = meta["blocks"]
        s = self.ind(b["path"], mp)
        if kind == "d":
            cur = s
            par = self.ind(b["path"][:-1], mp)
            width = " " * b["path"][-1][1]
            return par + (width if cur != par + width else "\t")
        if kind == "a":
            return flip(s)
        if kind == "b":
            return flip(self.ind(blocks[b["parent"]]["path"], mp)) + "\t"
        ps = self.ind(blocks[b["parent"]]["path"], mp)
        return s[: self.rnd.randint(len(ps) + 1, len(s) - 1)]


def generate(src: Path, out: Path, seed: int) -> tuple[int, int]:
    """Write the variants of every document of `src`. Returns the number of valid and invalid files."""
    (out / "valid").mkdir(parents=True, exist_ok=True)
    (out / "invalid").mkdir(parents=True, exist_ok=True)
    v = Variants(seed)
    expect: dict[str, dict[str, Any]] = {}
    nv = 0
    names = sorted(f.name[:-10] for f in src.iterdir() if f.name.endswith(".meta.json"))
    for name in names:
        meta = json.loads((src / f"{name}.meta.json").read_text(encoding="utf-8"))
        has_fixed = any(p[0] == "fixed" for rec in meta["lines"] if not rec.get("noise") for p in rec["pieces"])
        modes = [("v1", "tabs"), ("v2", "mixed")]
        if has_fixed:
            modes += [("v3", "tabs-t"), ("v4", "mixed-t"), ("v5", "mixed-r"), ("v6", "mixed-r")]
        for tag, mode in modes:
            mp = v.mapping(meta, mode)
            (out / "valid" / f"{name}.{tag}.yaml").write_bytes(v.render(meta, mp).encode())
            nv += 1
        # Faults, on a mixed or tab rendering.
        mp = v.mapping(meta, v.rnd.choice(["tabs", "mixed", "mixed", "mixed-t", "mixed-r", "tabs-r"]))
        for kind, cands in v.fault_candidates(meta, mp).items():
            if not cands:
                continue
            b, e = v.rnd.choice(cands)
            x = v.fault_indent(kind, meta, mp, b)
            line = e["line"]
            text = v.render(meta, mp, {line: x})
            (out / "invalid" / f"{name}.{kind}.yaml").write_bytes(text.encode())
            expect[f"{name}.{kind}"] = {
                "line": line + 1,
                "col": len(x) + 1,
                "fault": kind,
                "indent": x,
                "block": v.ind(b["path"], mp),
                "tabs": "\t" in text,
            }
    (out / "invalid.json").write_text(json.dumps(expect), encoding="utf-8")
    return nv, len(expect)


def main(argv: list[str]) -> None:
    nv, ni = generate(Path(argv[0]), Path(argv[1]), int(argv[2]))
    print("valid", nv, "invalid", ni)


if __name__ == "__main__":
    main(sys.argv[1:])

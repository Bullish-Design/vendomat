"""Generator for fuzz input (the spike generator `fuzz_gen.py`). Standard library only.

The mix is 35 % valid files from a random tree, 50 % the same with one to three mutations, and 15 % rows chosen
at random from a list of fragments ("soup"). With `tame`, the files are mostly valid and faults are rare.

Use: `python yamlgen_fuzz.py OUTDIR COUNT SEED [tame]`

The files carry no expected result. A reference parser gives the oracle: the spike used the old Rust primop.
`tests/test_parser_fuzz.py` checks properties and a digest of the results instead.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

NASTY = [
    "\t",
    '"',
    "'",
    ":",
    "#",
    "-",
    " ",
    "  ",
    "*",
    "&",
    "!",
    "[",
    "]",
    "{",
    "}",
    "|",
    ">",
    "%",
    "@",
    "`",
    "?",
    ",",
    "\n",
    "\r",
    "\\",
    "é",
    " ",
    " ",
    "﻿",
    "\U0001f600",
    "---",
    "...",
    ": ",
    " #",
    "- ",
    "''",
    '\\"',
    "\\n",
    "\\q",
    "\x0b",
    "\x0c",
]
WORDS = [
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
    "café",
    "日本",
    "1e3",
    "-1",
    ".5",
    "it's",
    'say "hi"',
]
KEYWORDS = [
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
]
TAME_EXCLUDED = ("it's", 'say "hi"', "-1", "~", "http://h/p")
FRAGMENTS = [
    "a: 1",
    "b:",
    "  c: 2",
    "    d: 3",
    "- x",
    "  - y",
    "# c",
    "",
    'k: "v"',
    "k: 'v'",
    '  - "q"',
    "key: value # c",
    "---",
    "a: b: c",
    "x y",
    "  ",
    "a:  ",
    "-",
    "  -",
    '"k": v',
    "k: [a]",
    "k: *a",
    "k: &a v",
    "k: |",
    'e: "\\q"',
    "\tz: 1",
    "a: 1",
    "b: 2",
    "l:",
    "  - 1",
]


class Fuzz:
    def __init__(self, seed: int, *, tame: bool = False) -> None:
        self.rnd = random.Random(seed)
        self.tame = tame

    def key(self) -> str:
        k = self.rnd.choice(KEYWORDS)
        r = self.rnd.random()
        if self.tame:
            return k
        if r < 0.05:
            return '"' + k + ' z"'
        if r < 0.08:
            return "'" + k + "'"
        if r < 0.10:
            return self.rnd.choice(["3d", "-k", ".k", "café", ""])
        return k

    def scalar(self) -> str:
        r = self.rnd.random()
        w = self.rnd.choice(WORDS)
        if self.tame:
            if self.rnd.random() < 0.9:
                w = self.rnd.choice([x for x in WORDS if x not in TAME_EXCLUDED])
            r = min(r, 0.84) if self.rnd.random() < 0.95 else r
        if r < 0.55:
            return w
        if r < 0.70:
            return '"' + w.replace('"', '\\"') + '"'
        if r < 0.80:
            return "'" + w.replace("'", "''") + "'"
        if r < 0.85:
            tails = ["\\n", "\\t", "\\\\"] if self.tame else ["\\n", "\\t", "\\\\", "\\q", "\\", ""]
            return '"' + w + self.rnd.choice(tails) + '"'
        if r < 0.90:
            return w + self.rnd.choice([" # c", "  #c", "#c", " #"])
        if r < 0.93:
            return '"' + w + '"' + self.rnd.choice([" # c", "#c", " x", "  ", ""])
        return self.rnd.choice(NASTY) + w

    def ws(self) -> str:
        return self.rnd.choice(["", "", "", " ", "  "])

    def noise(self, ind: int) -> list[str]:
        r = self.rnd.random()
        if r < 0.08:
            return [""]
        if r < 0.14:
            return [" " * self.rnd.choice([0, ind, ind + 2]) + "# c"]
        if r < 0.16:
            return ["   "]
        return []

    def gen_map(self, depth: int, step: int, ind: int, lines: list[str]) -> None:
        used: set[str] = set()
        for _ in range(self.rnd.randint(1, 4)):
            lines.extend(self.noise(ind))
            k = self.key()
            while self.tame and k in used:
                k = self.key()
            used.add(k)
            r = self.rnd.random()
            if depth < 4 and r < 0.25:
                lines.append(" " * ind + k + ":" + self.ws() + self.rnd.choice(["", "", " # c"]))
                self.gen_map(depth + 1, step, ind + step, lines)
            elif depth < 4 and r < 0.40:
                lines.append(" " * ind + k + ":")
                self.gen_list(step, ind + step, lines)
            elif r < 0.45 and not self.tame:
                lines.append(" " * ind + k + ":")
            else:
                gaps = [1, 1, 1, 2] if self.tame else [1, 1, 1, 2, 0]
                lines.append(" " * ind + k + ":" + " " * self.rnd.choice(gaps) + self.scalar())

    def gen_list(self, step: int, ind: int, lines: list[str]) -> None:
        for _ in range(self.rnd.randint(1, 4)):
            lines.extend(self.noise(ind))
            r = self.rnd.random()
            if r < 0.05 and not self.tame:
                lines.append(" " * ind + "-")
            elif r < 0.08 and not self.tame:
                lines.append(" " * ind + "- " + self.key() + ": " + self.scalar())
            else:
                lines.append(" " * ind + "-" + " " * self.rnd.choice([1, 1, 1, 2]) + self.scalar())

    def mutate(self, text: str) -> str:
        for _ in range(1 if self.tame else self.rnd.randint(1, 3)):
            lines = text.split("\n")
            r = self.rnd.random()
            i = self.rnd.randrange(len(lines)) if lines else 0
            if r < 0.35 and text:
                p = self.rnd.randrange(len(text) + 1)
                text = text[:p] + self.rnd.choice(NASTY) + text[p:]
            elif r < 0.45 and text:
                p = self.rnd.randrange(len(text))
                text = text[:p] + text[p + 1 :]
            elif r < 0.55:
                lines.insert(i, lines[i])
                text = "\n".join(lines)
            elif r < 0.62 and len(lines) > 1:
                del lines[i]
                text = "\n".join(lines)
            elif r < 0.80:
                d = self.rnd.choice([-3, -2, -1, 1, 2, 3])
                row = lines[i]
                lines[i] = (" " * d + row) if d > 0 else row[min(-d, len(row) - len(row.lstrip(" "))) :]
                text = "\n".join(lines)
            elif r < 0.85 and len(lines) > 1:
                j = self.rnd.randrange(len(lines))
                lines[i], lines[j] = lines[j], lines[i]
                text = "\n".join(lines)
            elif r < 0.90 and text:
                text = text[: self.rnd.randrange(len(text))]
            elif r < 0.95:
                text = text.replace("\n", "\r\n")
            else:
                text = text.rstrip("\n")
        return text

    def soup(self) -> str:
        rows = "\n".join(self.rnd.choice(FRAGMENTS) for _ in range(self.rnd.randint(1, 8)))
        return rows + self.rnd.choice(["\n", ""])


def generate(out: Path, count: int, seed: int, *, tame: bool = False) -> None:
    """Write `count` files `fNNNN.yaml` to `out`."""
    out.mkdir(parents=True, exist_ok=True)
    g = Fuzz(seed, tame=tame)
    for n in range(count):
        r = g.rnd.random()
        if r < 0.15 and not tame:
            text = g.soup()
        else:
            lines: list[str] = []
            g.gen_map(0, g.rnd.choice([1, 2, 2, 2, 3, 4]), g.rnd.choice([0, 0, 0, 0, 1]), lines)
            text = "\n".join(lines) + g.rnd.choice(["\n", "\n", "\n", ""])
            if r < (0.4 if tame else 0.65):
                text = g.mutate(text)
        (out / f"f{n:04d}.yaml").write_bytes(text.encode("utf-8", errors="surrogatepass"))


def main(argv: list[str]) -> None:
    generate(Path(argv[0]), int(argv[1]), int(argv[2]), tame="tame" in argv[3:])
    print("wrote", argv[1])


if __name__ == "__main__":
    main(sys.argv[1:])

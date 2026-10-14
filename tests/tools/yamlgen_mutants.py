"""Generator for near-miss mutants of valid documents (the spike runner `p4_fuzz.py`, generator half).

Each mutant is a random valid document with one or two small changes: a stray character, a changed
indentation (also with a tab), a dropped or doubled row, a swapped row, a cut file, or a changed dash or
colon. Most mutants fail to parse at a position near the change. Some stay valid.

Use: `python yamlgen_mutants.py OUTDIR COUNT SEED SRCDIR[,SRCDIR...]`

The source directories hold the documents of `yamlgen_valid.py`. The files are `mNNNN.yaml`. The files carry
no expected result. The spike compared them with PyYAML (BaseLoader) as a loose oracle.
`tests/test_parser_fuzz.py` checks properties and a digest of the results instead.
"""

from __future__ import annotations

import random
import re
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
    "\\",
    "é",
    " ",
    "﻿",
    "---",
    "...",
    ": ",
    " #",
    "- ",
    "''",
    '\\"',
    "\\q",
    "- a: b",
    "- - ",
    "a: ",
    ":",
]
COMPACT_ITEM = re.compile(r"^( *)- (.*)$")


def mutate(rnd: random.Random, t: str) -> str:
    for _ in range(rnd.choice([1, 1, 1, 2])):
        rows = t.split("\n")
        r = rnd.random()
        i = rnd.randrange(len(rows))
        if r < 0.22 and t:
            p = rnd.randrange(len(t) + 1)
            t = t[:p] + rnd.choice(NASTY) + t[p:]
        elif r < 0.30 and t:
            p = rnd.randrange(len(t))
            t = t[:p] + t[p + 1 :]
        elif r < 0.37:
            rows.insert(i, rows[i])
            t = "\n".join(rows)
        elif r < 0.44 and len(rows) > 1:
            del rows[i]
            t = "\n".join(rows)
        elif r < 0.62:
            d = rnd.choice([-3, -2, -1, 1, 2, 3])
            row = rows[i]
            rows[i] = " " * d + row if d > 0 else row[min(-d, len(row) - len(row.lstrip(" "))) :]
            t = "\n".join(rows)
        elif r < 0.68 and len(rows) > 1:
            j = rnd.randrange(len(rows))
            rows[i], rows[j] = rows[j], rows[i]
            t = "\n".join(rows)
        elif r < 0.78:
            # A tab in the indentation, replacing a space or added.
            row = rows[i]
            k = len(row) - len(row.lstrip(" "))
            if k:
                p = rnd.randrange(k)
                rows[i] = row[:p] + "\t" + row[p + 1 :] if rnd.random() < 0.6 else row[:p] + "\t" + row[p:]
            else:
                rows[i] = "\t" + row
            t = "\n".join(rows)
        elif r < 0.84 and t:
            t = t[: rnd.randrange(len(t))]
        elif r < 0.92:
            # Make the first row of a block a compact item or a bare item.
            row = rows[i]
            m = COMPACT_ITEM.match(row)
            if m:
                if rnd.random() < 0.5:
                    rows[i] = m.group(1) + "-\n" + m.group(1) + "  " + m.group(2)
                else:
                    rows[i] = m.group(1) + "- - " + m.group(2)
            t = "\n".join(rows)
        else:
            rows[i] = rows[i].replace(": ", ":", 1) if rnd.random() < 0.5 else rows[i].replace("- ", "-", 1)
            t = "\n".join(rows)
    return t


def generate(out: Path, count: int, seed: int, sources: list[Path]) -> None:
    """Write `count` mutants `mNNNN.yaml` of the documents in `sources`."""
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(seed)
    docs = [s / f.name for s in sources for f in sorted(s.iterdir()) if f.name.endswith(".yaml")]
    for n in range(count):
        t = rnd.choice(docs).read_bytes().decode("utf-8").replace("\r\n", "\n")
        (out / f"m{n:04d}.yaml").write_bytes(mutate(rnd, t).encode("utf-8"))


def main(argv: list[str]) -> None:
    sources = [Path(s) for s in argv[3].split(",")]
    generate(Path(argv[0]), int(argv[1]), int(argv[2]), sources)
    print("wrote", argv[1])


if __name__ == "__main__":
    main(sys.argv[1:])

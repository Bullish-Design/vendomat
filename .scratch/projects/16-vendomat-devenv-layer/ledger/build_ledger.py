#!/usr/bin/env python3
"""Build the V5-to-V6 requirement ledger from the two specifications.

Run: python3 -I build_ledger.py [--check]

The V6 specification section 0 is the single source of every V5 disposition. This tool never
holds a second copy. It reads SPEC-V5.md and SPEC-V6.md, then writes LEDGER-V6.md. With
`--check` it writes nothing and exits 1 when the file differs or a rule fails.

Rules checked (exit 1 on any failure):
  1. No ID that SPEC-V6 defines is also defined in SPEC-V5.
  2. No ID is defined twice in one specification.
  3. Every successor named in section 0 or in a "Superseded by" note exists.
  4. Every V5 ID named in section 0 exists in SPEC-V5.
  5. An active V6 row does not name a superseded ID without naming its successor too.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
V5 = PROJECT.parent / "14-vendomat-local" / "SPEC-V5.md"
V6 = PROJECT / "SPEC-V6.md"
OUT = PROJECT / "LEDGER-V6.md"

ID = r"[A-Z]+-\d{3}"
ROW = re.compile(rf"^\| `({ID})` \| (.*)$", re.M)
#: IDs that project 15 drafted and the owner never adopted (SPEC-V6 "How to use this document").
PROJECT15_DRAFTS = {
    *(f"WS-00{n}" for n in range(1, 7)),
    "MOD-011",  # redefined by SPEC-V6 as a superseded row
    "BOOT-025",
    "CLI-018",
    "CLI-019",
}
#: Withdrawn V5 IDs that SPEC-V5 lists in prose ranges, not in table rows.
V5_PROSE_WITHDRAWN = (
    [f"PROJ-00{n}" for n in range(1, 7)]
    + [f"RES-{n:03d}" for n in range(1, 13)]
    + [f"EMIT-{n:03d}" for n in range(1, 8)]
)


def expand(cell: str) -> list[str]:
    """Expand "`A-001`, `A-003` to `A-005`" into IDs."""

    out: list[str] = []
    tokens = re.findall(rf"`({ID})`|\b(to)\b", cell)
    items: list[str | None] = [t[0] or None for t in tokens]
    flags = [bool(t[1]) for t in tokens]
    i = 0
    while i < len(tokens):
        if flags[i]:
            i += 1
            continue
        start = items[i]
        if i + 2 < len(tokens) + 1 and i + 1 < len(tokens) and flags[i + 1]:
            end = items[i + 2]
            fam, a = start.rsplit("-", 1)  # type: ignore[union-attr]
            fam2, b = end.rsplit("-", 1)  # type: ignore[union-attr]
            assert fam == fam2, f"range across families: {start} to {end}"
            out.extend(f"{fam}-{n:03d}" for n in range(int(a), int(b) + 1))
            i += 3
        else:
            out.append(start)  # type: ignore[arg-type]
            i += 1
    return out


def status_of(text: str) -> str:
    m = re.match(r"\s*\*(Superseded|Withdrawn|Narrowed|Decided|Proposed|To build)", text)
    if not m:
        return "active"
    return {"Decided": "decided", "To build": "to-build"}.get(m.group(1), m.group(1).lower())


def parse(path: Path) -> dict[str, tuple[str, str, str]]:
    """ID -> (status, requirement text, verify text). Rows of section 0 are not requirement rows."""

    rows: dict[str, tuple[str, str, str]] = {}
    dup: list[str] = []
    text = path.read_text()
    # Drop the section-0 table of SPEC-V6: it holds dispositions, not definitions.
    if path == V6:
        a = text.index("# 0. Relation to V5")
        b = text.index("# 1. One pinned devenv")
        text = text[:a] + text[b:]
    for m in ROW.finditer(text):
        ident, rest = m.group(1), m.group(2)
        cells = rest.rsplit(" | ", 1)
        req, ver = (cells[0], cells[1].rstrip(" |")) if len(cells) == 2 else (rest, "")
        if ident in rows:
            dup.append(ident)
        rows[ident] = (status_of(req), req, ver)
    if dup:
        raise SystemExit(f"{path.name}: duplicate ID row(s): {', '.join(sorted(set(dup)))}")
    return rows


def parse_section0() -> list[tuple[list[str], str, str]]:
    text = V6.read_text()
    a = text.index("# 0. Relation to V5")
    b = text.index("# 1. One pinned devenv")
    out = []
    for line in text[a:b].splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip("|").split(" | ")]
        if len(cells) < 3:
            continue
        out.append((expand(cells[0]), cells[1], " | ".join(cells[2:])))
    return out


def mentioned(text: str) -> list[str]:
    return re.findall(rf"`({ID})`", text)


def build() -> tuple[str, list[str]]:
    errors: list[str] = []
    v5 = parse(V5)
    v6 = parse(V6)
    v5_all = set(v5) | set(V5_PROSE_WITHDRAWN)
    sec0 = parse_section0()

    # Rule 1: collisions.
    for ident in sorted(set(v5) & set(v6)):
        errors.append(f"collision: {ident} is defined in SPEC-V5 and in SPEC-V6")

    # Rule 4 and the disposition map.
    disposition: dict[str, tuple[str, str]] = {}
    for ids, status, note in sec0:
        for ident in ids:
            if ident not in v5_all and ident not in v6:
                errors.append(f"section 0 names unknown ID {ident}")
            if ident in disposition:
                errors.append(f"section 0 names {ident} twice")
            disposition[ident] = (status, note)

    # Rule 3: successors exist.
    known = v5_all | set(v6)
    for ident, (status, note) in disposition.items():
        for succ in mentioned(note):
            if succ not in known:
                errors.append(f"section 0: {ident} names successor {succ}, which no specification defines")
    for ident, (status, req, _ver) in v6.items():
        if status in {"superseded", "decided"}:
            names = [n for n in mentioned(req) if n != ident]
            if not names:
                errors.append(f"{ident} is {status} and names no successor")
            for n in names:
                if n not in known and n not in PROJECT15_DRAFTS:
                    errors.append(f"{ident} names unknown ID {n}")

    # Rule 5: active V6 rows that cite a superseded ID.
    sup_of: dict[str, list[str]] = defaultdict(list)
    for ident, (status, note) in disposition.items():
        for succ in mentioned(note):
            sup_of[ident].append(succ)
    for ident, (status, req, _v) in v6.items():
        if status in {"superseded", "decided"}:
            sup_of[ident].extend(n for n in mentioned(req) if n != ident)
    closed = {i for i, (s, _r, _v) in v6.items() if s in {"superseded", "decided"}}
    closed |= {i for i, (s, _r, _v) in v5.items() if s in {"superseded", "withdrawn"}}
    closed |= {i for i, (s, _n) in disposition.items() if s.lower().startswith(("superseded", "withdrawn"))}
    stale: list[tuple[str, str]] = []
    for ident, (status, req, ver) in v6.items():
        if status in {"superseded", "decided"}:
            continue
        for n in sorted(set(mentioned(req + " " + ver))):
            if n in closed and n != ident and n not in {x for x, ss in sup_of.items() if ident in ss}:
                stale.append((ident, n))

    # Ledger body.
    lines: list[str] = []
    w = lines.append
    count5 = Counter(v5[i][0] for i in v5 if not i.startswith("NAT-"))
    nat5 = sum(1 for i in v5 if i.startswith("NAT-"))
    w("# Vendomat V5 to V6 requirement ledger")
    w("")
    w("**Generated** by `ledger/build_ledger.py` from `SPEC-V5.md` and `SPEC-V6.md`. Do not edit by hand.")
    w("Section 0 of `SPEC-V6.md` holds every V5 disposition. Change it there and regenerate.")
    w("`tests/test_v6_ledger.py` fails when this file differs from the tool's output.")
    w("")
    w("V6 stays a **draft**. V5 stays authoritative until the owner accepts V6.")
    w("")
    w("## Counts")
    w("")
    w("| Set | Count |")
    w("| --- | --- |")
    w(f"| V5 requirement IDs in tables (active {count5['active']}, superseded {count5['superseded']}, "
      f"withdrawn {count5['withdrawn']}, narrowed {count5['narrowed']}) | {sum(count5.values())} |")
    w(f"| V5 withdrawn IDs listed as ranges, not rows (`PROJ-*`, `RES-*`, `EMIT-*`) | "
      f"{len([i for i in V5_PROSE_WITHDRAWN if i not in v5])} |")
    w(f"| V5 `NAT-*` facts | {nat5} |")
    c6 = Counter(v6[i][0] for i in v6 if not i.startswith("NAT-"))
    nat6 = sum(1 for i in v6 if i.startswith("NAT-"))
    w(f"| V6 IDs defined (active {c6['active']}, proposed {c6['proposed']}, to build {c6['to-build']}, "
      f"superseded {c6['superseded']}, decided {c6['decided']}) | {sum(c6.values())} |")
    w(f"| V6 `NAT-*` facts | {nat6} |")
    w(f"| V5 IDs that section 0 names | {len(disposition)} |")
    w("")
    w("## Checks")
    w("")
    if errors:
        for e in errors:
            w(f"- **FAIL** {e}")
    else:
        w("- PASS: no V5/V6 collision, no duplicate row, every successor exists.")
    w("")
    w("### Active V6 rows that cite a closed ID")
    w("")
    if stale:
        w("Each pair names an active V6 row and the closed ID it cites. Repair the citation or name the")
        w("successor beside it.")
        w("")
        for a, b in stale:
            w(f"- `{a}` cites `{b}`")
    else:
        w("None.")
    w("")

    w("## V5 IDs and their V6 disposition")
    w("")
    w("`Kept` means the V5 text applies unchanged. `Closed in V5` means V5 already superseded or")
    w("withdrew it, and V6 adds nothing.")
    w("")
    w("| V5 ID | V5 status | V6 disposition | Successor or note |")
    w("| --- | --- | --- | --- |")
    for ident in sorted(v5_all, key=lambda i: (i.split("-")[0], i)):
        st = v5[ident][0] if ident in v5 else "withdrawn"
        if ident in disposition:
            d, note = disposition[ident]
        elif ident.startswith("NAT-"):
            d, note = "Fact", "Observation. It satisfies no requirement."
        elif st in {"superseded", "withdrawn"}:
            d, note = "Closed in V5", ""
        else:
            d, note = "Kept", "V5 text applies"
        w(f"| `{ident}` | {st} | {d} | {note} |")
    w("")
    w("## V6 IDs")
    w("")
    w("| V6 ID | Status | Supersedes (V5 or V6) | Note |")
    w("| --- | --- | --- | --- |")
    sup_by: dict[str, list[str]] = defaultdict(list)
    for ident, (status, note) in disposition.items():
        for succ in mentioned(note):
            sup_by[succ].append(ident)
    for ident in sorted(v6, key=lambda i: (i.split("-")[0], i)):
        status, req, _ver = v6[ident]
        if ident.startswith("NAT-"):
            status = "fact"
        replaces = ", ".join(f"`{i}`" for i in sorted(sup_by.get(ident, [])))
        note = ""
        if status in {"superseded", "decided"}:
            note = "by " + ", ".join(f"`{n}`" for n in mentioned(req) if n != ident)
        w(f"| `{ident}` | {status} | {replaces} | {note} |")
    w("")
    w("## Reserved and never adopted")
    w("")
    w("- Project 15 drafted `WS-001` to `WS-006`, `MOD-011`, `DISK-008`, `BOOT-025`, `CLI-017` to `CLI-019`,")
    w("  `GEN-023`, and `NAT-018` to `NAT-023`. The owner never adopted them. `SPEC-V6.md` defines its own")
    w("  text for each number it uses. `WS-*`, `BOOT-025`, and `CLI-018`/`CLI-019` are not V6 IDs unless the")
    w("  V6 table above lists them.")
    w("")
    return "\n".join(lines).rstrip() + "\n", errors


def main() -> int:
    text, errors = build()
    if "--check" in sys.argv:
        current = OUT.read_text() if OUT.exists() else ""
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        if current != text:
            print(f"{OUT.name} differs from the generated ledger; run build_ledger.py", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT} ({len(errors)} error(s))")
    for e in errors:
        print("  " + e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

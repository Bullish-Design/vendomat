<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-12/yaml-spike-2/REPORT.md. Raw logs, generators, and parse.nix (v3) stay in that directory. -->

# YAML parser spike 2: lists of maps, nested lists, tabs — 2026-10-12

Written by a Sonnet subagent; saved by the orchestrator because the subagent could not write files.
Final parser: `parse.nix` (248 lines; 197 without comments and blanks). Old parser: `parse.old.nix`.
Runners in `bin/`, logs in `logs/`. Old spike dir and the vendomat repo untouched.
Orchestrator spot-check: compact list of maps plus nested list parse; `\t- a` then `\t  b` parses;
`\t- a` then `\t\tb` fails with `inconsistent tabs and spaces`; `programs: - ripgrep` gives the
text `"- ripgrep"`.

## Grammar (observed)

- Indentation = leading run of spaces and tabs, compared as a string, no tab width. A child starts
  with the parent's string and is longer; siblings identical; a dedent lands on an open level.
- Errors: "unexpected indentation" for a deeper row or when only spaces are involved; otherwise
  "inconsistent tabs and spaces", LINE:COL at the row. A tab counts as 1 column. "tabs are not
  accepted" is gone.
- Compact items (`- key: v`, `- - x`) open a block at the item indentation plus the `-` and its
  trailing spaces, each counted as one space. Continuation lines must use exactly that string:
  `\t- a: 1` needs `\t  b: 2`. A tab in that position is an error.
- An item is a map entry when its rest is `key:` + space or end of line, or a quoted key + `:`.
  Otherwise a scalar. Bare form (`-` alone, then indented block) still works. Empty item fails with
  `no value`.
- Only spaces separate `-` and `:` from what follows. Tabs inside values stay text; a trailing tab
  on a plain value is trimmed.

## Proof

- P1 regression vs primop: 914 primop reruns matched stored results. Fuzz differences 126/2500
  (seed 20261012) and 14/2500 (seed 20261014): 88 tabs only, 29 compact lists of maps only, 22 both,
  1 changed value (`- - "x"`, formerly the text `- "x"`). Rust cases 25/27 (2 tab cases now
  accepted). Edge cases 154/163 (6 tab, 2 compact-map, `deep_1000` nesting limit).
- P2 vs PyYAML BaseLoader and the generator tree: 3200 + 1500 valid documents (seeds 20261101,
  20261103), 0 mismatches. 400 tab-in-value documents vs tree only: 0 mismatches.
- P3 tabs: 9400 valid variants (6460 with a tab) equal the space version. 6947 inconsistent variants
  all fail at the expected LINE:COL; 351 space-only dedent faults say "unexpected indentation".
- P4 rejects: 103 hand cases, 0 mismatches. 9000 near-miss mutants: 3935 accepted by both with equal
  values (except a trailing NBSP quirk and empty file = `{}`); 3380 rejected by both; 10 accepted by
  us only (`key: - x` as text); 266 accepted by us only for tabs in text; about 1400 rejected by us
  only, all in documented classes; 149 indented first row or deeper line after a scalar.
- P5 stock devenv: 1003 samples, 0 differences vs host Nix. Cost: `catalog_500` median 103 ms
  (old 83 ms); 500-line list-of-maps 51 ms, tab version 55 ms (process start 28 ms). `devenv eval`
  about 0.4 s with or without the parser.

## Remaining differences and unproved

- Nesting limit: nested lists pass at 800, fail at 850; chained list/map nesting passes at 800,
  fails at 1000.
- Quirks: `key: - x` accepted as text; bare `-` followed by a scalar on the next row is rejected.
- Not proved: a real consumer or machine entry point; other Nix or devenv versions; no Rust parity
  for the new grammar (the primop does not implement it).

## v3 (same day): tab continuation and dash values

`parse.nix` is now v3 (261 lines; 205 without comments and blanks); v2 is `parse.v2.nix`.
Summary also in `logs/REPORT-v3.txt`.

- Tab continuation: a compact item's block uses either item indent + dash and trailing spaces
  (space form) or item indent + one tab (tab form). The next code line after the item line fixes
  the form for every compact level on that line. A later line in the other form fails with
  `inconsistent tabs and spaces`. Same rule at each depth.
- Dash values: a plain map value that is `-` or starts with `- ` (also before a trailing tab or a
  ` #` comment) fails with `a list must start on the next line`, column at the `-`, also inside
  compact items. Quoted values and `-x`, `-1`, `--` stay text.
- P1: identical to v2 (140 intended differences). P2: 0 mismatches (4700 + 400). P3: 15616 valid
  (6216 tab form) and 8034 invalid (1185 mixed form), 0 wrong. P4: 131 hand cases, 0 mismatches;
  of 9000 mutants, 17 `key: - x` now rejected, 6 tab-indent mutants fail at a different row or
  message (3 checked, all intended), 8977 unchanged. P5: 1031 samples, 0 differences; costs
  unchanged within noise.
- Corrections to v2: of the 10 "accepted by us only, no tab" mutants, 9 were `key: - x`; the tenth
  is a no-break space before a comment (still accepted). Accepted-by-both count is 3965, not 3935.
- Orchestrator spot-check: tab form parses; a mix fails at 4:4; `programs: - ripgrep` fails at
  1:11; `note: "- x"` and `n: -1` stay text.

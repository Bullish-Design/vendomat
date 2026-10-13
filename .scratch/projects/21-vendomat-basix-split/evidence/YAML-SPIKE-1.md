<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-12/yaml-spike/REPORT.md. Raw logs, cases, and parse.nix stay in that directory. Preceded by a 92-line prototype in /home/andrew/.local/state/vendomat/p21/2026-10-12/pure-nix-yaml/ (16 cases). -->

# Pure-Nix YAML parser spike — 2026-10-12

Written by a Sonnet subagent; saved by the orchestrator because the subagent could not write files.
Raw logs, scripts, cases, and the final parser are in this directory (`parse.nix`, `bin/`,
`cases/`, `logs/`). The vendomat repository was not touched. Orchestrator spot-check: `parse.nix`
is 197 lines; `logs/q2-fuzz*.log` show 4 runs of 2500 inputs, every one SAME-OK or SAME-ERR.

**Recommendation:** patch 0009 can be dropped. The pure-Nix parser matches the primop on every
input tried and runs on stock devenv with no unsafe setting. "No fork" still needs patch 0007, or
two extra inputs in the template (Q3).

**Parser:** 197 lines (167 without comments and blanks), a faithful port of the Rust parser with the
same message text. Row loops use `genericClosure` chains; three regex-recursion overflows on long
lines were removed.

**Versions:** stock devenv 2.4.0+b904dcb, fork 2.4.0+c66ba87, host Nix 2.34.7, Testee 0.6.1,
direnv 2.37.1. Disk gate passed: 31 GiB unallocated, metadata 80 to 82 %.

## Verdicts

- **Q1 parity: PASS.** All 27 Rust unit-test cases identical to the primop and to the Rust
  expectations. 162 of 163 edge cases identical (CRLF, no trailing newline, BOM, non-ASCII columns,
  dotted and dashed keys, empty value then dedent, comments, trailing spaces, `#` handling). Same
  inside stock devenv's own Nix.
- **Q2 fuzz: PASS.** 0 mismatches in 5000 inputs (seeds 20261012 and 20261014; 1924 accepted,
  3076 rejected, all 20 message classes seen), on host Nix and again in stock devenv.
- **Q3 stock workspace: PASS.** Shell values correct; all 6 P2F edit steps seen (including
  same-size edit with restored mtime, delete, restore). Fresh clone, direnv, and Testee 0.6.1 work:
  GREEN, RED after an edit, GREEN again. `allow-unsafe-native-code-during-evaluation` stays false.
  The eval cache re-evaluates when `parse.nix` changes. Second fork dependency: stock devenv does
  not inherit the module's `nixpkgs-python` and `rust-overlay` inputs (patch 0007 does). With
  `languages.python.version` set, stock fails with "run devenv inputs add nixpkgs-python". Listing
  both inputs in the workspace `devenv.yaml` fixes it on stock (tested).
- **Q4 errors: PASS, cosmetic cost.** Stock + pure-Nix prints 442 to 846 lines for a syntax error;
  the primop route prints 338. Last non-blank line: `error: vendomat.yaml:7:12: flow style is not
  accepted` (primop route adds `Error from custom function:`). Testee prints one line on both
  routes. Type errors identical on both routes, no line number.
- **Q5 cost: PASS.** Parser only: +0 to 5 ms at 30 lines, about +30 ms at 500 lines (28 ms process
  start). End to end, cold `devenv shell` adds under 10 ms at 30 lines, about 100 ms at 500 lines;
  cached runs show no difference. No row limit: 10,000 rows take 1.3 s and 335 MB (the old
  recursive version failed at 4000 map rows). Nesting fails at about 1000 levels (900 passes); the
  primop passed 3000.

## Remaining differences (none matter for a 3-level catalog)

1. Nesting over about 1000 levels overflows in Nix.
2. Invalid UTF-8 is rejected on both routes with different message text.
3. A plain value ending in more than 5000 to 20000 Unicode-whitespace characters overflows in Nix;
   the primop accepts it.

## Grammar quirks in both parsers (decide in the spec)

- `-` followed by an indented block is accepted, so lists of maps and nested lists get in despite
  "lists of maps rejected".
- A tab anywhere in the file wins over an earlier syntax error.
- A BOM is an error.
- Keys must start with a letter or `_`.

## Unproved

A `git://` release input (a `path:` input was used); the repo's own `testee verify` suites; an
interactive direnv hook; a NixOS or machine entry point; patches 0001 to 0006 and 0008; other devenv
or Nix versions.

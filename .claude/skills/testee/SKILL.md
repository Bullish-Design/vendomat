---
name: testee
description: Use when verifying code changes in this repository — running tests, lint, formatting, or type checks, or checking whether a change is correct. This repo verifies through Testee, not by invoking pytest/ruff/ty directly.
---

# Testee verification

This repository uses **Testee** as its single verification interface. Do not run
`pytest`, `ruff`, `ty`, or other check commands directly. Run Testee instead — it
runs the configured checks, normalizes the results, and returns one compact report.

Use the `devenv shell testee …` forms: they stream Testee's report so you can read
the failures. (The `devenv tasks run testee:*` aliases are CI/exit-code gates — they
do not print the report.)

## Commands

- Verify (fast): `devenv shell testee verify --mode quick`
- Verify (thorough): `devenv shell testee verify --mode detailed`
- Auto-fix lint/format (modifies files): `devenv shell testee fix`
- Rerun previous failures: `devenv shell testee rerun-failures --last`
- Re-show last report: `devenv shell testee report --last`
- One target: `devenv shell testee verify --tool pytest --target tests/test_x.py::test_y --mode detailed`
- Diagnose: `devenv shell testee doctor`

## Workflow

1. Make your change.
2. Run `devenv shell testee verify --mode quick`.
3. On failure, read the report: each failure names its kind, location, and a rerun command.
4. Fix, then `devenv shell testee rerun-failures --last`.
5. `PASSED` means done. Exit 1 = fix the code; exit 2 = fix the environment.

`--changed` is an interactive convenience (CI gates should run a full mode). If it
skips every tool the report notes *"No checks ran (all tools skipped)"* — that is not
a verification pass.

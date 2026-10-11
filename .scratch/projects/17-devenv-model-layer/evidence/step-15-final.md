# Step 15 final record: the pilot and the supported set (GM9 PASS)

**Date:** 2026-10-11. **Status:** GM9 is met. This record closes [step-15.md](./step-15.md), which
holds the work up to commit `0dd939d802d2`. Read that record first for the history.
**Raw reports:** `~/.local/state/devenv-py/rt/<run-id>/report.md` (run ids below),
`~/.local/state/devenv-py/ident/REPORT.md`, `~/.local/state/devenv-py/gm9/`,
`~/.local/state/devenv-py/determ-work/`, and the author records under
`~/.local/state/devenv-py/devenv-py-author/`.

Labels: OBSERVATION means a report, a log, a commit, or a command output. INFERENCE means a
conclusion that the observations support. A fact marked "told" comes from the task brief, and the
cited commit or report confirms it.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` (devenv rev `b904dcb51fe48c30db250038241507f60752f222`) |
| Export hash | `sha256:a1126c7deb218be41121dc672fdb7b4b0ca58fafc482c787c9fd7ad66a07fc4e` (all runs below) |
| `devenv-py` `main` at record time | `4f3033bdaa9c` |
| Templateer | rev `ac02b48c015d`. `main` of Templateer has no release tag; `v0.4.2` is on `v6-flake`. |
| Testee | 0.6.1 (`~/.nix-profile/bin/testee`) |
| Final gate command | `env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV devenv shell -- uv run dpy rt ...` with all checks RT1 to RT8 and seeds 1 and 2, then `dpy report <run-id>` |

## The final gate runs (OBSERVATION)

| Run id | Subtrees | Candidates | Wall time | Gate | Note |
| --- | --- | --- | --- | --- | --- |
| `regate-1` | `languages.python`, `services.postgres`, `services.redis`, `languages.javascript` | 4619 | 103.4 s | PASS | cold cache; started 19:51Z after `2f3b57d568cb` (INFERENCE from the time stamps) |
| `regate-2` | the same four | 4619 | 13.2 s | not reported | warm cache; same command. No `report.md` exists for this run. |
| `rust-rebased-1` | `languages.rust` | 1183 | 5.9 s | PASS | started 20:45Z, after `b7848e630c83` (16:41 local) |
| `20261011T173553Z-rt-three` | `languages.python`, `services.postgres`, `services.redis` | 3377 | 65.3 s | PASS | earlier three-subtree gate, before `languages.javascript` and the seed fix |
| `20261011T195503Z-rt-pilot` | `languages.python`, `services.postgres` | 2429 | 63.2 s | PASS | the pilot pair, after `regate-1` |
| `rustcheck-1` | `languages.rust` | 1202 | 31.1 s | FAIL (RT7 1001 pass, 127 fail) | before the manifest rules; history only |

**Determinism check (OBSERVATION).** I compared `regate-1` and `regate-2` row by row on
(fixture, subtree, check, status). Both hold 4780 rows and the multisets are equal. The pass, fail,
and skip counts match for every subtree and check. The warm run took 13.2 s against 103.4 s cold.

Command used for the comparison: a short script that reads both `results.jsonl` files (scratch, not
committed). Expected: equal. Actual: equal.

## The supported set (OBSERVATION, reports `regate-1` and `rust-rebased-1`)

| Subtree | Status | Fixtures (real) | RT7 cases (seed 1 + seed 2) | RT8 | RT3 typed |
| --- | --- | --- | --- | --- | --- |
| `languages.python` | supported | 26 (24) | 1099 (541 + 558), 0 fail | 95 of 95 | 78 of 79 (98.7 %) |
| `services.postgres` | supported | 12 (10) | 1103 (561 + 542), 0 fail | 32 of 32 | 32 of 35 (91.4 %) |
| `services.redis` | supported (generated-only) | 2 (1) | 1059 (532 + 527), 0 fail | 11 of 11 | 2 of 2 |
| `languages.javascript` | supported | 7 (7) | 1061 (528 + 533), 0 fail | 38 of 38 | 22 of 22 |
| `languages.rust` | supported | 10 (10) | 1109 (542 + 567), 0 fail | 47 of 47 | 18 of 18 |

Per-check counts (pass / fail / skip):

| Subtree | RT1 | RT2 | RT3 | RT4 | RT5 | RT6 |
| --- | --- | --- | --- | --- | --- | --- |
| `languages.python` | 25/0/1 | 26/0/0 | 26/0/0 | 24/0/2 | 26/0/0 | 24/0/2 |
| `services.postgres` | 12/0/0 | 12/0/0 | 12/0/0 | 11/0/1 | 12/0/0 | 9/0/3 |
| `services.redis` | 2/0/0 | 2/0/0 | 2/0/0 | 1/0/1 | 2/0/0 | 2/0/0 |
| `languages.javascript` | 7/0/0 | 7/0/0 | 7/0/0 | 7/0/0 | 7/0/0 | 7/0/0 |
| `languages.rust` | 10/0/0 | 10/0/0 | 10/0/0 | 9/0/1 | 10/0/0 | 7/0/3 |

All RT7 fields occur in at least 20 cases for every subtree and seed (report row "RT7 size": 0
fields below 20). Truth stability: every corpus fixture of the five subtrees is stable
(`triage.toml`). Remaining `NixExpr` fields: `languages.python.import`, `languages.rust.import`
(function-typed), `services.postgres.extensions` (`NixExpr | FnMarker`).

### Skips and exclusions by subtree (OBSERVATION)

- `languages.python`: RT1 skips `python-with-packages` (`pkg-unresolved`; the package is
  `python3-3.14.7-env` from `withPackages`, with no attribute path). RT4 skips 2 (`has-imports` 1,
  `no-literal-fields` 1). Exclusion share: RT1 1 of 24 (4 %), RT4 1 of 24 (4 %).
- `services.postgres`: RT4 skips 1 (`has-imports`). Exclusion share 0 of 10 for every check.
- `services.redis`: RT4 skips 1 (`has-imports`, the golden fixture `d-priority`, which does not count
  as corpus).
- `languages.rust`: RT4 skips 1 (`no-literal-fields`). Exclusion share RT4 1 of 10 (10 %).
- Path-limit exceptions (listed in the reports, not counted in the share):

  | Subtree | Check and class | Fixtures |
  | --- | --- | --- |
  | `languages.python` | RT6 `pkg-unresolved` | `python-uv-sync`, `python-with-packages` |
  | `services.postgres` | RT6 `has-fn` | `postgres`, `postgres-timescale`, `postgres-customperdbinit` |
  | `languages.rust` | RT6 `pkg-unresolved` | `rust` (`rust_app`), `rust-wasm-cross` (`wasm-bindgen-cli`), `cli-options` (`devenv-test-existing-pkg`) |

### Earlier RT7 count differences (OBSERVATION)

The run `20261011T173553Z-rt-three` shows RT7 counts of 1021 (`languages.python`), 1059
(`services.postgres`), and 1058 (`services.redis`). `regate-1` shows 1099, 1103, and 1059. The seed
fix (MDL-034) landed between the two runs. INFERENCE: the counts changed because the same seed now
draws the same cases in any process. This record does not isolate the cause further.

## Owner decisions (told; the commits implement them)

1. **Two-tier corpus rule** (MDL-030). A non-pilot subtree with at least 5 real corpus fixtures is
   `supported`. With fewer, and with every other row passed, it is `supported (generated-only)`.
   Commit `87160a1e9a0c`; the constants are `SUPPORTED_MIN_CORPUS` and `CORPUS_METRIC_ROWS` in
   `report.py`. The pilots keep their own sizes: 10 for `languages.python` and 5 for
   `services.postgres`.
2. **Path-limit exceptions** (MDL-031). `PATH_LIMIT_EXCEPTIONS` names two: RT6 `has-fn` and RT6
   `pkg-unresolved`. Commit `0b722e4538e2`.
3. **A non-gate `pytest-focus` Testee check** for single-file iteration. Commit `daae98dcb09a`; the
   targets file moved to XDG state in `559964de7557`. No profile selects it and no verdict depends
   on it.
4. **Testee 0.6 migration.** `devenv-py`: owner commit `559964de7557`. Vendomat: owner commit
   `e1434bb28482` and the follow-up `9b1e6e247b07` (local `main`).

## Commits after `0dd939d802d2` (OBSERVATION, `jj log` of `devenv-py`)

| Commit | Subject |
| --- | --- |
| `4af72fe743ba` | feat: identify packages by derivation name; content-addressed case dirs; RT7 forces packages |
| `855d6c449894` | feat: bring services.redis to authored status with a narrowed model and tests |
| `d19458f4f736` | docs: fix the devenv-py skills from the GM10 trial feedback |
| `daae98dcb09a` | feat: add pytest-focus Testee check for single-test iteration |
| `87160a1e9a0c` | feat: close GM9 gaps: shell probe on, alone and function fixtures run, named exclusion classes, two-tier status |
| `0b722e4538e2` | feat: path-limit exceptions in the exclusion share |
| `737e0bc3f609` | feat: narrowed model of languages.rust with the rules of rust.nix (first trial, GM9 not met) |
| `559964de7557` | Migrate to the Testee 0.6 module and commit verdicts |
| `31213ed9e914` | docs: tighten the devenv-py skills and AGENTS.md after the languages.rust trial |
| `bb1087a287af` | Pin RepoMan v0.14.0 |
| `52d954221bf1` | chore: add rust-overlay to the pin inputs and re-triage the corpus |
| `0f810c24d60f` | feat: leave renamed options out of the generated models and record them as coverage |
| `cc21b91fe3fc` | feat: build RT8 bases from valid draws of the narrowed model |
| `c43ab0a66077` | feat: devenv.nix prints the ruff-format diff and finds the focus targets inside Testee 0.6 |
| `610905190c2f` | fix: accept option sub-paths in the probe, fold RT7 expectations, and splice fixture-local packages in RT2 |
| `4a3e45feef51` | feat: bring languages.javascript to supported status |
| `c8297c304c85` | fix: make an RT7 seed give the same cases in any process |
| `2f3b57d568cb` | docs: record the javascript trial lessons in the devenv-py skills |
| `0ff6e746d8c1` | docs: name the narrowed test file by the last segment of the subtree in AGENTS.md |
| `b7848e630c83` | feat: bring languages.rust to supported status with the rust-overlay manifest data of the pin |
| `4f3033bdaa9c` | docs: name the narrowed test by the last segment, and add lock-node, bulk-probe, list-field, and manifest-revision rules to the author skill |

## Harness changes after Step 16

Each change below has a requirement ID in [CONCEPT.md](../CONCEPT.md).

| Change | Commit | ID |
| --- | --- | --- |
| Package identity by the full `$name`; the normalizer keeps `$name`; `canonical_path` makes `./.` and `.` equal | `4af72fe743ba` | MDL-036 |
| Content-addressed requests and case directories (`cases/<sha256 of all files>/`) | `4af72fe743ba` | MDL-037 |
| RT7 forces `config.packages` names; the shell probe (`config.enterShell`) is on by default (`--no-probe-shell` turns it off) | `4af72fe743ba`, `87160a1e9a0c` | MDL-038 |
| Hybrid RT2 and RT5 render: splice the source span for a `$fn` option and for a fixture-local package | `87160a1e9a0c`, `610905190c2f` | MDL-039 |
| `alone` fixtures run in their own project; `$fn` fixtures run through the hybrid render | `87160a1e9a0c` | MDL-039 |
| Named exclusion classes; a skip outside them is a gate FAIL | `87160a1e9a0c` | MDL-032 |
| Golden fixtures leave the corpus metrics | `87160a1e9a0c` | MDL-033 |
| The syntax reader reads a root `let` constant (a plain literal bound once) | `87160a1e9a0c` | MDL-042 |
| Templateer integral-float fix (Templateer `main` `ac02b48c`) | `8c24fb61f028` | none; see [step-9.md](./step-9.md) |
| The generator rejects an invalid draw | `47def85602d1` | MDL-025 (existing) |
| Renamed and alias options leave the generated models | `0f810c24d60f` | MDL-035 |
| RT8 bases come from valid draws of the narrowed model | `cc21b91fe3fc` | MDL-040 |
| The probe accepts option sub-paths; RT7 expectations fold open submodules | `610905190c2f` | MDL-041 |
| An RT7 seed gives the same cases in any process | `c8297c304c85` | MDL-034 |

### Seed determinism (OBSERVATION and INFERENCE)

- OBSERVATION: the commit message of `c8297c304c85` states that Hypothesis mixes the constants of
  every local module in `sys.modules` into its draws. `languages.javascript` seed 2 gave 541 cases
  alone and 536 after `languages.python` loaded.
- OBSERVATION: the fix empties the local constants pool while the generator draws. A regression test
  compares runs across `PYTHONHASHSEED` values and loaded modules.
- OBSERVATION: `determ-work/` holds the scratch scripts (`canon.py`, `inproc.py`, `seq.py`) and the
  canonical case lists for three subtrees and two seeds under three modes (`standalone-h0`,
  `standalone-h12345`, `dpyrt-h777`). Testee run `20261011T194116Z-d81b1db1d3b3` (the verify log in
  `determ-work/verify2.log`) is GREEN 5 of 5 on commit `2f3b57d568`. An earlier run
  `20261011T193744Z-563deab02b50` was RED on ruff and was fixed.
- OBSERVATION: the `languages.javascript` author record shows seed 2 with 531 cases in the gate run
  and 541 in the coverage step. INFERENCE: this was the same defect, seen before the fix.

### Python version list (OBSERVATION)

With the shell probe on, RT7 failed 13 cases in the run `gm9-shell-1` (class `shell-error`). The
side probe `gm9/verprobe.log` lists 194 names tested and 8 bad: `3.3` and `3.3.1` to `3.3.7`.
Cause in the model comment: the series 3.3 builds with `gcc9`, which nixpkgs removed, so
`config.enterShell` throws. `narrowed/languages.python.py` now lists 186 names (series 3.4 to 3.14).
The earlier list of 194 passed the old probe because the old probe never forced `enterShell`.

## Resolution of the open items of [step-15.md](./step-15.md) (OBSERVATION)

| Item | Result |
| --- | --- |
| 1. Package identity (`python-packages`, `python-packages-no-venv`, `python-subprocess`, `python-uv-sync`, `postgres-timescale`) | Fixed by `4af72fe743ba`. `languages.python` RT2 is 26 of 26 and RT1 is 25 of 25 eligible. `python-with-packages` stays `pkg-unresolved` for RT1 (1 of 24, 4 %). |
| 2. `postgres-customdbuser` RT4 (`.` against `./.`) | Fixed by `canonical_path` in `4af72fe743ba` (`./.` is `.`). `services.postgres` RT4 is 11 of 11. |
| 3. `services.postgres` exclusion share 30 % | RT6 `has-fn` is a path-limit exception (MDL-031). Counted share is 0 of 10. |
| 4. `services.postgres` typed ratio 86.8 % | Now 32 of 35 (91.4 %). INFERENCE: golden fixtures left the metric (MDL-033) and the path fix changed the count. |
| 5. Truth stability | Reported PASS in every subtree section (`triage.toml`). |
| 6. `alone` fixtures skipped as `alone-needs-project` | The CLI passes `alone_project`. No `alone-needs-project` skip remains in `regate-1`. |
| 7. Run time needs a warm cache | Case directories are content-addressed. Cold 103.4 s, warm 13.2 s. |

## Limits (INFERENCE unless marked)

- The final four-subtree run `regate-1` used the direct `dpy rt` command. `testee check rt-pilot`
  covers `languages.python` and `services.postgres` only (run `20261011T195503Z-rt-pilot`, PASS).
- `PATH_LIMIT_EXCEPTIONS` removes 2 python, 3 postgres, and 3 rust skips from the share. The report
  lists them. A new exception needs a code change and a review.
- `services.redis` is `supported (generated-only)`: its corpus holds 1 real fixture. The tier says
  the harness proves the type mapping by RT7 and RT8, and proves the corpus path on one fixture only.
- Package narrowing and manifest rules (`CHOICES`, the `rust-overlay` tables) are semantic. RT8
  cannot test them. For `languages.rust`, `CHOICES` accepts only `str` or package fields, so RT7
  cannot draw real `targets` and `components` values (author record `rust2-gate-1`, gap 1).
  The unit tests and 2845 probes (0 disagreements) prove those rules.
- The rust data tables tie to `rust-overlay` `c1cfa7a2`. A re-lock of that root input needs a new
  extraction.

## Open items

1. Templateer `main` has no release tag. The harness pins `ac02b48c015d`. The owner decides the tag.
2. The `pytest-focus` targets file is one file in XDG state. Several checkouts share it.
3. The end-to-end default `VENDOMAT_TEMPLATEER` is specific to one machine.
4. The Devman push hook resolves `testee` from the session `PATH`. A session that started from an old
   Vendomat shell carries Testee 0.5.1.

## Gate GM9

PASS. See [GATES.md](./GATES.md).

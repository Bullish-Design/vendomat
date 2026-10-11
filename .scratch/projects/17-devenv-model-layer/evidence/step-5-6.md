# Steps 5 and 6 record: the oracle, the serializer, the normalizer, and the comparison

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`. The raw report is
`~/.local/state/devenv-py/step-2-6/REPORT.md`. The phase-A prototypes are in
[phase-a.md](./phase-a.md), section 2.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Commit | `4a79266083c7`: feat: add truth, the normalizer, the comparison, and the golden fixtures (Step 5 oracle files are in `4d6712d7a2cf`; see [step-2-3.md](./step-2-3.md)) |
| Files | `src/devenv_py/truth.py`, `normalize.py`, `compare.py`; `tests/test_golden.py`, `test_golden_match.py`, `golden_match.py`, `test_normalize.py`, `test_compare.py`; `tests/golden/<name>/{source/,expected.json,expected.normalized.json}` for `a-probe`, `b-scripts-tasks`, `c-imports`, `d-priority`, `e-paths` |
| Testee | `testee verify --full`, run `20261011T051232Z-101a43914d5c`, PASS (shared with Steps 2 and 3) |

## Results

| Check | Expected | Actual |
| --- | --- | --- |
| Raw truth against the hand-written `expected.json` (wildcards) | equal for five fixtures | equal |
| Two runs, cache on and `--no-eval-cache` | byte-identical | byte-identical |
| `scope = "all"` with `process.manager.command` denied, against `touched`, fixture `a-probe` | equal | equal |
| Twin test: five fixtures in two directories | equal after normalization | equal; raw truth of `e-paths` differs by the store hash, as designed |
| Batch of five fixtures at touched scope | about 1.6 s | about 1.6 s |
| Slowest test | (none stated) | `test_candidate_scope_all_equals_touched_for_a_simple_fixture`, 9.3 s (full option walk) |

## Departures from the guide

1. `expected.json` is hand-written raw truth with wildcards (from the oracle prototype).
   `expected.normalized.json` is the normalized truth. The agent generated the second file from the
   oracle output and read it against the first. Inference: it is a regression file, not independent
   proof.
2. The normalizer merge rule started as `DEFAULT_MERGE_RULES`, a table keyed by dotted option path.
   Step 4 replaced it with rules read from the export (see [step-4.md](./step-4.md)).
3. `normalized_truth` normalizes. `truth_for_fixtures` returns raw truth. No `dpy truth` command
   exists.
4. Later normalizer rules 7 and 8 (store hashes, runtime directory, project directories, checkout,
   home) came with `ad9476284450`. See [step-15.md](./step-15.md).

## Gate GM3

Met. All five golden fixtures match, touched scope equals `scope = "all"` with the deny list, truth
is stable, and the two-directory test shows no difference.

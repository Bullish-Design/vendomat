# V4 P4 record

**Run:** 2026-10-07. **Result:** The P4 gate passes on the pinned tools, with the gaps listed below.
No phase after P4 passed.

P4 binds declared checks to exact bytes and assembles the receipt. Vendomat added no code. Two
throwaway Python scripts stand in for the check runner and the receipt assembler: they are proof
harnesses, not Vendomat implementation. `nvim-review` got one real change: two module-owned
required-check tasks. Raw logs are in `~/.local/state/vendomat/v4-proof/2026-10-07/p4/`.

## Inputs and versions

| Item | Value |
| --- | --- |
| Nix | 2.34.7 |
| Module repository | `nvim-review` at `dc0b5190ca5c8628bc4a1197b08ff48b91854cea` (adds the two check tasks) |
| Consumer | `consumers/main`, a fresh devenv consumer, `nvimReview.enable = true` |
| Harness scripts | `run_required_checks.py`, `build_receipt.py`, `retry_proof.py` (throwaway, not committed) |

## Declared required checks

| Name | Owner | Declared when |
| --- | --- | --- |
| `nvimReview:known-input` | `module:nvim-review` | the module is enabled |
| `nvimReview:editor-smoke` | `module:nvim-review` | the module and its editor are enabled |
| `consumer:no-author-tool` | `consumer` | always, in this consumer |

## Checks

| Step | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| Declared set exists | `devenv tasks list --json` names each declared check before it runs | All 3 present | `tasklist-baseline.json` |
| Effective set follows enablement | Disabling the editor removes `nvimReview:editor-smoke` from the set | Present with editor on, absent with editor off, present again after revert | `tasklist-no-editor.json`, `tasklist-reverted.json` |
| `missing-required` | A declared name with no matching task reports `missing-required`, not a failure | `nvimReview:schema-check` (never implemented) reports `missing-required` | `results-baseline.json` |
| `failed-required` | A declared, existing check that fails reports `failed-required`, distinct from missing | Adding `shellcheck` to the consumer makes `consumer:no-author-tool` fail for real | `results-failed.json` |
| No `enterShell` gate | The harness never treats `devenv:enterShell` as a required check | Asserted in the harness; `devenv:enterShell` is not in any declared list | `run_required_checks.py` |
| Stage order | Pre-build gates the build; build realizes the output; artifact checks run against it | Pre-build (input declared) passed, then build, then both artifact checks passed against the realized path | `stages/` |
| Identity validation | An artifact check given a different output path is rejected | A real, different, valid build (`override-src`, `maxLength = 60`) does not equal the recorded path | `stages/wrong-path.txt` |
| Receipt: 4 native documents | `flake metadata`, `build`, `path-info --recursive`, `archive`, all present | All 4 present in `receipt.json` | `receipt-success/receipt.json` |
| Receipt: 6 Vendomat fields | required checks, upload result, closure availability, coverage statement, machine plan ID, tool versions | All 6 present | `receipt-success/receipt.json` |
| Canary scrub | A secret exported into the environment appears in no receipt and no log | Not found in any file under the run | grep over `p4/` |
| Broken derivation | The failure record names the stage. No success receipt exists | `failure.json` names `stage: "build"`. No `receipt.json` was written | `receipt-broken/failure.json` |
| Reuse on retry | Unchanged inputs are reused, not rerun | Run 2 reused all 3 checks | run 1 vs run 2 logs |
| Changed input reruns its check | Changing the consumer's `devenv.nix` reruns only `consumer:no-author-tool` | The other two checks were reused unchanged | run 3 log |
| Output path alone is not success | Clearing the check cache forces every check to rerun, even though the store output still exists | Run 4 reran all 3 checks against the same, still-present output path | run 4 log |

## Requirement IDs observed

| ID | Observation |
| --- | --- |
| `V4-CHK-001`, `002`, `004`, `006`, `007`, `010`, `011` | The declared list, its ownership, its enablement-dependent set, `missing-required` vs `failed-required`, and the `enterShell` exclusion are all demonstrated. |
| `V4-SEL-003`, `006`, `007`, `009` | The frozen revision re-evaluates to the same derivation path. Stage order and identity validation hold. |
| `V4-EVD-001`, `002`, `005`, `006` | The receipt stores all four native documents verbatim and compares cleanly against fresh queries. |
| `V4-EVD-012` | `tool_versions` records Nix 2.34.7 and `path_info_json_format: 2`. The spec's own `1\|2\|3` wording was wrong; this run corrected it to `1\|2`. |

## Gaps

- `V4-PROOF-005` and `V4-CHK-003`, P4's scenarios, have no text in the guide.
- The receipt's `upload_result` and `closure_availability` fields are honest placeholders. P5 has
  not run, so there is nothing to upload and nothing to verify yet.
- The receipt format itself is a proof harness output, not a Vendomat file format. It is proposed,
  not implemented.
- The retry cache is a flat JSON file in the harness, not a Vendomat-owned state class. Vendomat's
  own receipt-and-log storage is still proposed.

## Gate

Passed on 2026-10-07. A failed required check and a missing required check both block success, for
different, named reasons. The receipt lets a reader reconstruct the exact checked bytes: its
`out_path`, its closure, and its locked inputs are all in one file, with the tool version and JSON
format needed to read it again. P5 needs a reachable Attic cache with push and pull tokens. Neither
exists yet (`BLK-P5-01` to `BLK-P5-07`).

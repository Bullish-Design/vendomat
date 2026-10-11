# Step 16 final record: the skills trials (GM10 PASS)

**Date:** 2026-10-11. **Status:** GM10 is met. This record closes [step-16.md](./step-16.md), which
describes the skills as written in commit `028e7f774899` and holds no trial result.
**Raw records:** `~/.local/state/devenv-py/devenv-py-author/services.redis/redis-n-both.md`,
`.../languages.rust/20261011T175713Z-rust-final-s12.md`, `.../languages.rust/rust2-gate-1.md`,
`.../languages.javascript/js-final.md`.

Labels: OBSERVATION means a record, a log, a commit, or a command output. INFERENCE means a
conclusion from observations. A fact marked "told" comes from the task brief, and the cited commit
or record confirms it where it can.

## The gate and its rule

GM10 (guide Step 16): an agent brings a new subtree to the GM9 thresholds with the skills alone and
with no harness code change. The harness boundary is MDL-005 and the `AGENTS.md` list: no edit to
`nix/`, `pins/`, or `src/devenv_py/`. An author edits `narrowed/<subtree>.py`,
`tests/test_narrowed_<last segment>.py`, and the generated files only.

## Trial 1: `services.redis` (reached the gate after fixes it prompted)

OBSERVATION from `redis-n-both.md`:

- Base `4af72fe743ba`; change committed as `855d6c449894`. The commit adds the generated model, its
  schema, `narrowed/services.redis.py` (30 lines, no validator), and a 73-line test file. It touches
  no harness file.
- Module facts (`redis.nix`): no assertion, no `apply`, no `throw`. The record infers that no
  validator and no `CHOICES` list is justified.
- RT7: 538 pass (seed 1), 546 pass (seed 2); 1084 pass in one two-seed run. RT8: 11 of 11.
  `testee verify --full`: run `20261011T154402Z-ff6453184798` PASS.
- The agent reported the gate as BLOCKED, not passed. Reasons: one real fixture (corpus size), and
  RT3 typed 3 of 4 (75 %) because the golden fixture `d-priority` counts as a binding.
- DEVIATION (recorded by the agent): one direct `pytest` call through `devenv shell`. The rule
  forbids it. The Testee run covers the same file.

The agent also reported four harness issues: RT3 typed counts the golden `mkIf false true`
binding; RT4 skips the golden fixture as `has-imports` and marks the row REVIEW; the RT7 probe does
not force `processes.redis`; `dpy report` gives a gate FAIL for two runs of one seed each.

INFERENCE: the trial exposed gaps in the rules and the harness, not in the model. Each fixed gap
below came out of it. Commits: `d19458f4f736` (skills fixed from the trial feedback), `87160a1e9a0c`
(shell probe on, two tiers, named exclusion classes), and the golden-fixture rule (MDL-033).
After those commits `services.redis` reports `supported (generated-only)` in run `regate-1`
(see [step-15-final.md](./step-15-final.md)).

## Trial 2: `languages.rust`, first attempt (failed on harness gaps)

OBSERVATION from `20261011T175713Z-rust-final-s12.md`:

- Base `0b722e4538e2`; change commit `737e0bc3f609`. The agent wrote validators for the seven module
  assertions and for the conflict and default rules of `rust.nix`, with 11 tests. `testee verify --full` ran twice: run
  `20261011T175936Z-891922b42d9b` failed on ruff, and run `20261011T180233Z-44acfb1ee93b` passed.
- Result: GM9 FAIL for RT7, RT8, and the exclusion share. RT7 passed 14 of 516 cases (seed 1) and 2
  of 505 (seed 2). Every failure came from one cause: the probe answered `undeclared`.
- The agent named the harness gaps and did not change the harness. It used scratch runs with an
  in-memory patch as non-gate evidence only.

The six gaps, and where they are now:

| Gap | Fix |
| --- | --- |
| The probe rejects a sub-path of a submodule option as undeclared | `610905190c2f` (MDL-041) |
| An open submodule: RT7 expects leaf keys, truth keeps one attribute set | `610905190c2f` (MDL-041) |
| `packages` is a renamed option; the generated model treated it as a field | `0f810c24d60f` (MDL-035) |
| The pin has no `rust-overlay` input | `52d954221bf1` |
| RT8 base cases set `enable = true` and broke a cross-field rule | `cc21b91fe3fc` (MDL-040) |
| Fixture-local packages always skip RT2 and RT6 (30 percent share) | `610905190c2f` (MDL-039) and `0b722e4538e2` (MDL-031) |

The record names a seventh point: the report has no row for "every enum value and both integer
bounds occur". No commit in this list changes that. INFERENCE: coverage step 9 of the author skill
still computes it by hand.

**Independent confirmation (OBSERVATION).** Run `rustcheck-1` (19:08Z, main `61090519`) kept the
agent's narrowed model and ran with the fixes. RT1 to RT6 and RT8 passed: RT8 47 of 47, exclusion
share PASS. RT7 passed 1001 of 1128. The 127 failures (89 `type-error`, 38 `packages-error`) are
model gaps (see the next section), not harness gaps. INFERENCE: the six gaps are fixed.

## Trial 2b: `languages.rust`, second attempt (supported)

OBSERVATION from `rust2-gate-1.md`:

- Base `2f3b57d5`. Commit `e6f751af8197`; `main` holds it as `b7848e630c83`
  (INFERENCE: a rebase changed the commit id; the stat and the subject match). The diff holds `narrowed/` and
  `tests/` only (508 added lines, 8 removed). No harness file changed.
- Cause of the 127 failures: `version`, `targets`, and `components` were free strings. `rust.nix`
  throws when a value is not in the `rust-overlay` manifest. The agent encoded the manifest data of
  `rust-overlay` `c1cfa7a2` (the root input; the lock holds a second node, `860d7c83`, that the module
  does not use). Cross-check: 2845 probes, 0 disagreements. 22 stable versions (1.46.0 to 1.63.0) fail
  with the default `lsp`; the model carries that rule.
- Result: run `rust2-gate-1` gate PASS, status supported. RT7 1109 of 1109, RT8 47 of 47. Rerun after
  the rebase: `rust-rebased-1`, PASS. `testee verify`: run `20261011T203655Z-4bc7dbe797bc` GREEN 5 of 5.
- Skill gaps the agent named: the lock can hold two nodes for one input; no bulk-probe recipe;
  `CHOICES` takes only `str` and package fields. Commit `4f3033bdaa9c` adds the lock-node,
  bulk-probe, list-field, and manifest-revision rules to the author skill.
- INFERENCE: this attempt followed the skills and changed no harness code. It is a repeat on a
  subtree that earlier work had already shaped, so it is weaker evidence than the next trial.

## Trial 3: `languages.javascript` (GM10 PASS)

Told: a fresh agent, skills only, no help, no harness change.

OBSERVATION from `js-final.md` and the commit:

- Base `61090519` (main at the start). Change `ypvvvqul`, commit `4a3e45feef51`. The diff holds four
  files: the generated model, its schema, `narrowed/languages.javascript.py` (173 lines), and
  `tests/test_narrowed_javascript.py` (156 lines). No file under `src/`, `nix/`, or `pins/` changed.
  This confirms the "no harness change" condition.
- Rules found: nine assertions of `javascript.nix` (lines 384 to 421) and the package uses at
  lines 22, 41, 89, 170, 225, 348, 353, and 359. `CHOICES`: `nodejs`, `pnpm`, `yarn-berry`, `bun`,
  `vtsls`. Probes: all choices with all `install.enable` values evaluate `packages` and
  `enterShell`. `yarn.package = hello` fails (`called with unexpected argument 'nodejs'`).
  `npm.package = nodejs-slim` evaluates but has no `bin/npm`.
- Counts. Baseline `js-base1` (seed 1, no narrowing): 1138.8 s, RT7 278 pass and 261 fail
  (`assertion` 94, `other-error` 167), RT8 38 of 38. After narrowing `js-it1`: RT7 529 of 529, RT8
  38 of 38, 21.6 s. Final `js-final` (seeds 1 and 2): RT1 to RT6 7 of 7, RT7 1060 of 1060 (529 + 531),
  RT8 38 of 38, 25.5 s, status supported. Coverage: 30 of 30 fields in both seeds, none unmet. `NixExpr`
  fields left: 0. Real corpus fixtures: 7.
- `testee verify`: run `20261011T190830Z-9dc98b5f2868` GREEN on `4a3e45fe`.
- The gate re-run `regate-1` (after the seed fix) shows `languages.javascript` supported with RT7 1061
  of 1061 and RT8 38 of 38 ([step-15-final.md](./step-15-final.md)).
- The record shows seed 2 with 531 cases in the gate run and 541 in the coverage step. INFERENCE:
  this was the seed defect that `c8297c304c85` fixed (MDL-034). The agent reported the numbers and did
  not touch the harness.

Skill updates after the trial: `2f3b57d568cb` (the javascript lessons: use the absolute path of the
`testee` that the skill names; list `bin/` of each candidate before `CHOICES`; the
`builtins.deepSeq` rule for `tryEval`; run the baseline in the background; count only `corpus/`
fixtures) and `0ff6e746d8c1` and `4f3033bdaa9c` (name the narrowed test by the last segment).

## Verdict

GM10 PASS. The evidence is trial 3: a fresh agent used the three skills on a new subtree and
reached `supported` with a diff that holds no harness file. Trials 1 and 2 are the reason the skills
and the rules in their final form exist. Trial 1 reached the gate only after rule and harness fixes
that it prompted. Trial 2 failed on six harness gaps; the repeat (2b) passed after those fixes.

## Limits (INFERENCE)

- One fresh-agent pass on one subtree. The record has no second independent pass of trial 3.
- The skills name `~/.nix-profile/bin/testee` by absolute path because an inherited `PATH` can put an
  old Testee first. The Devman push hook resolves `testee` from the session `PATH` and has the same
  exposure (open item 4 in [step-15-final.md](./step-15-final.md)).
- The skills still ask the agent to compute the "every enum value and both bounds occur" check by hand.

## Gate GM10

PASS. See [GATES.md](./GATES.md).

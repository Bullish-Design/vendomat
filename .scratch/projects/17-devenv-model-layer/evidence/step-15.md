# Step 15 record: the pilot, `languages.python` and `services.postgres`

**Date:** 2026-10-11. **Status:** IN PROGRESS. GM9 is not met. This record holds the work done up to
the commit `0dd939d802d2`, and names the work in flight.
**Raw reports:** `~/.local/state/devenv-py/step-15-python/REPORT.md`,
`~/.local/state/devenv-py/harness-fix/REPORT.md`, `~/.local/state/devenv-py/widen/REPORT.md`,
and the run reports under `~/.local/state/devenv-py/rt/`. No `step-15-postgres/` report file exists.
The postgres facts below come from the orchestrator and from the repository source.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Export hash | `sha256:a1126c7deb218be41121dc672fdb7b4b0ca58fafc482c787c9fd7ad66a07fc4e` |
| `devenv-py` `main` | `0dd939d802d2` |
| Pilot command | `testee check rt-pilot` (runs `dpy rt --subtree languages.python,services.postgres --checks RT1,...,RT8 --seed 1 --seed 2`, then `dpy report`) |
| Templateer | rev `ac02b48c015d` (see [step-9.md](./step-9.md)) |

## Commits in order

| Commit | Subject |
| --- | --- |
| `47def85602d1` | fix: discard generated draws that fail narrowed model validation |
| `9a541b4bd8ed` | fix: make RT5 strict with one canonical dotted layout and path values |
| `308cf3e30afd` | feat: narrow services.postgres so pass requires user when enabled |
| `ab489dad7af5` | feat: narrow languages.python for RT7 and RT8 (package choices, version list, two cross-field rules) |
| `028e7f774899` | docs: add the three Step 16 agent skills (see [step-16.md](./step-16.md)) |
| `8c24fb61f028` | build: pin templateer to ac02b48c015d, the integral-float fix |
| `ad9476284450` | fix: scrub project and runtime paths in normalize; key the eval cache on a content-addressed request path |
| `0dd939d802d2` | fix: widen narrowed models to accept real corpus fixtures |

## `services.postgres` narrowing (`308cf3e30afd`)

Facts from the orchestrator; the narrowed file is `narrowed/services.postgres.py`.

- The module has one cross-field assertion: `pass` requires `user` for an entry of
  `initialDatabases` (`postgres.nix` lines 434 to 441). The validator runs only when `enable` is
  true, because the module sets its `config` under `lib.mkIf cfg.enable`. An empty string counts as
  set.
- `extensions` with no `withPackages` on `package` throws, but the model cannot see that.
  Inference: the rule is unmodelable. `extensions` stays `NixExpr` (and `FnMarker` after the
  widening).
- RT7 before the Templateer fix, with the new validator (reports `pg-after-s1`, `pg-after-s2`):

  | Seed | Cases | Pass | Fail |
  | --- | --- | --- | --- |
  | 1 | 554 | 532 | 22 `mismatch` |
  | 2 | 515 | 498 | 17 `mismatch` |

  RT8 passed 32 of 32 in both. The mismatches were a float such as `0.0` that came back as `0`
  (`services.postgres.settings`). Cause (orchestrator): MiniJinja 2.22 turns an integral float into
  an integer when a template reads a scalar. Templateer `ac02b48c` tags integral floats in `nix`
  templates. See [step-9.md](./step-9.md).
- RT7 after the pin `8c24fb61f028` (orchestrator): 554 of 554 pass (seed 1) and 515 of 515 pass
  (seed 2).
- The generator-reject fix `47def85602d1` made the validator usable: a draw that fails the narrowed
  validation is discarded. The orchestrator wrote it.

## `languages.python` narrowing (`ab489dad7af5`)

Raw report: `~/.local/state/devenv-py/step-15-python/REPORT.md`. Base `9a541b4b`, change
`mzrllzswxmvl` (commit `07c88e10` before the rebase). Testee run `20261011T132713Z-474aee178b0e`
PASS (full). Rules come from `src/modules/languages/python/default.nix` at `b904dcb5`.

Rules found (line numbers in that file):

- Lines 331 to 336: the `package` `apply` needs `.override`, `.buildEnv`, and `.pkgs`. Lines 96,
  108, and 754 need `.sitePackages` and `.interpreter`. Only an interpreter works. With
  `patches.buildEnv.enable = false`, `pkgs.jq` aborts with `attribute 'buildEnv' missing`.
- Lines 157 and 193: `uv.package` is used as `bin/uv`. Line 278: `poetry.package` as `bin/poetry`.
  Line 741: `lsp.package` is only installed.
- Lines 727 to 732: `version` picks `nixpkgs-python.packages.<system>.<version>` or throws. Lines
  330 and 727 both define `package`, so `version` with `package` fails when `enable` is true (the
  config sits under `mkIf` at line 655).
- Lines 777 to 782: the assertion forbids `poetry.install.enable` and `uv.sync.enable` together.
  Line 694: `poetry.enable = true` sets `install.enable` to true by default.

Constraints in `narrowed/languages.python.py`: `package` is `python3` only; `uv.package` is `uv`;
`poetry.package` is `poetry`; `lsp.package` is one of `pyright`, `basedpyright`,
`python3Packages.python-lsp-server`, `ty`. `version` is one of 194 names (CPython 3.3 to 3.14, minor
and patch) of `nixpkgs-python` `5821ac52`. All 194 evaluate. All 21 names of 2.7 abort
(`cpython/2.7/default.nix` is missing). Two validators run when `enable` is true: `version` and
`package` are exclusive, and the `poetry.install` and `uv.sync` assertion holds (effective install
is the explicit value, else `poetry.enable`). With `enable` false or unset, both rules pass in Nix
and in the model.

Generator change (`generate_cases.py`): a narrowed class may set
`CHOICES: ClassVar[dict[str, tuple[str, ...]]]`. RT7 draws that field only from the list. `_minimal`
uses the first choice. RT8 skips the string wrong-type mutation for a string field with choices,
because Nix accepts a string there and only the model rejects it.

Results (RT7 and RT8, before and after):

| Seed | RT7 before | RT7 after | RT8 |
| --- | --- | --- | --- |
| 1 | 540 cases: 251 pass, 175 `type-error`, 94 `assertion`, 20 `other-error` | 510 cases, 510 pass | 95 of 95 before and after |
| 2 | 534 cases: 327 pass, 123 `type-error`, 45 `assertion`, 39 `other-error` | 509 cases, 509 pass | 95 of 95 before and after |

Wall time of `dpy rt --subtree languages.python --checks RT7,RT8 --seed 1`: 151.5 s before (run
`step15-py-base-s1`), 9.1 s after (`step15-py-s1`). Seed 2 after: 8.3 s (`step15-py-s2`). Coverage
after: 48 of 48 fields in at least 20 cases (lowest 102 for seed 1, 106 for seed 2). All four
`verbosity` enum values occur (minimum 20). `languages.python.import` is skipped (`NixExpr`).

Harness limits the agent found:

1. A `$pkg` compares by `pname`. The `pname` of `python311` to `python315` is `python3`;
   `python3Minimal` is `python3-minimal`; `pypy27` is `pypy`. They evaluate, but RT7 reports
   `mismatch`. So `package` is limited to `python3`. A real source with `pkgs.python312` falls to
   `NixExpr` in the syntax reader. This is the package identity problem (below).
2. The RT7 probe forces only defined options. `version` alone never resolves, so RT7 does not prove
   that a version evaluates. The agent proved the 194 names with a side probe that also defined
   `packages = []` (scratch run `explore-vers-all-1791724586`). The list needs a new proof at a new
   pin.
3. Package narrowing (uv, poetry, lsp, `python3` only) is semantic. Nix accepts any package, so RT8
   cannot test it. `pypy` (Python 2.7) and `rustpython` pass the probe; both are excluded as
   unusable.
4. Scratch probe runs `explore-pkgs1`, `explore-pkgs2`, `explore-rules1`, and `explore-vers-*` sit
   under `~/.local/state/devenv-py/rt/`.

## Harness fix (`ad9476284450`)

Raw report: `~/.local/state/devenv-py/harness-fix/REPORT.md`. Change `wyzsmmll`, base `9a541b4b`.
Testee run `20261011T135340Z-8e4c8d819c28` PASS (two earlier runs failed on test and format fixes:
`20261011T134942Z-2b204d6889ca`, `20261011T135151Z-87f2edf2b3fc`).

- `normalize.py` rules 7 and 8: store hashes, `/tmp/devenv-<7hex>` and `/run/user/N/devenv-<7hex>`
  (to `<runtime>`), project directories and the fixture root (to `<root>`), the repository checkout
  (to `<checkout>`), and home (to `<home>`) in every string and object key. Signature:
  `normalize(raw, root, rules=None, project_dirs=None)`; the default project directory is the only
  pin directory. `truth.normalized_truth` takes `pin_dir`. `corpus.py` lost `scrub` and
  `path_replacements`.
- `driver.py`: `request_path` and `write_request` write
  `<state>/requests/<sha256 of canonical JSON>.json` once (atomic rename). `run_request` evaluates
  that path. The run directory still gets `request.json` and the logs. `cache=False` is unchanged.
- Corpus truth diff (public sources regenerated on `9a541b4b`; command
  `python -m devenv_py.corpus evaluate devenv-examples devenv-tests`): 0 unstable fixtures, and 0
  `/home/andrew` strings in `corpus/`. `caddy-php`, `python-django`, `wordpress`,
  `process-compose-interactive`, and `process-compose-merge` now show `<runtime>` for
  `/tmp/devenv-<hash>`. `process-watch-restart` shows `<root>/watch-target` in a message. `git`
  shows `<checkout>` for `git.root`. The error tails of `dotenv-nix`, `multiverse`, and
  `syntax-error` changed. No truth content changed.
- Cache timings: the same echo request three times took 0.33 s, 0.12 s, 0.12 s (the test needs warm
  below 0.6 times cold). `testee check rt-pilot` twice took 477.1 s (run
  `20261011T135525Z-689ab28677e4`) and 476.0 s (run `20261011T140323Z-b0f252d644d8`). No speedup.
- Cause of the missing speedup (inference from `roundtrip.py:990`): generated cases live in
  `rt/<run_id>/cases/gen-N-...`. Each run builds candidates with new module paths, so the requests
  differ and the cache cannot hit. The fix belongs in `roundtrip.py`: use case directories without
  the run id, for example a hash of the seed and the case content. That fix is in flight.

## Widening (`0dd939d802d2`)

Raw report: `~/.local/state/devenv-py/widen/REPORT.md`. Base `ad947628`. Change `rywzlzzl`. Testee
run `20261011T142118Z-dd913359ee02` PASS (`verify --full`). Source runs: pilot reports
`20261011T135526Z-rt-pilot` and `20261011T140324Z-rt-pilot`.

The pilot report listed five RT1 misses.

| Fixture | Field and value | Cause | Class |
| --- | --- | --- | --- |
| `postgres-customperdbinit`, `postgres`, `postgres-timescale` | `services.postgres.extensions` = `{"$fn": true}` | The fixture sets `extensions = extensions: [ ... ];`. The type is `nullOr (functionTo (listOf package))` (`postgres.nix` 226 to 228). The model typed it `NixExpr`, which needs source text. Eval truth holds `{"$fn": true}`. | model too tight; fixed |
| `python-uv-run` | `languages.python.libraries` = `[{"$pkg": "zlib"}]` | The fixture sets `libraries = [ pkgs.zlib ]`. The type is `listOf types.path` (`python/default.nix` 425 to 426). The model allowed `PathRef` only. `types.path` accepts a derivation. | model too tight; fixed |
| `python-uv-sync` | `languages.python.uv.package` = `{"$pkg": "uv", "$output": "out"}` | The model accepts `uv`. The reader fails before validation: `pname` `uv` fits both `uv` and `python3Packages.uv`. | reader and harness, package identity; not changed |

Changes: `values.py` has a new `FnMarker` (tag `$fn`, accepts only `{"$fn": true}`, holds no source).
`narrowed/services.postgres.py` types `extensions` as `NixExpr | FnMarker | None`.
`narrowed/languages.python.py` types `libraries` as `list[PathRef | PkgRef]`. No field was added
(the MDL-009 check passes). Tests: `test_values.py`, `test_narrowed_postgres.py`,
`test_narrowed_python.py`, `test_read_eval.py`.

Numbers after the widening (cache warm; runs `widen-fin-*`):

| Check | `languages.python` | `services.postgres` |
| --- | --- | --- |
| RT1 corpus | 23 pass, 1 fail (`python-uv-sync`) | 10 pass, 0 fail |
| RT7 seed 1 | 547 pass, 0 fail | 549 pass, 0 fail |
| RT7 seed 2 | 540 pass, 0 fail | 515 pass, 0 fail |
| RT8 seeds 1 and 2 | 95 pass, 0 fail | 32 pass, 0 fail |

RT7 now draws `PkgRef` elements into `libraries` (`jq`, `git`, `hello`, `python3Packages.requests`,
`python3Packages.pytest`). All pass.

The pilot runs before the widening show many RT7 failures (report `20261011T140324Z-rt-pilot`:
`languages.python` 578 pass and 496 fail; `services.postgres` 964 pass and 144 fail). The widen
agent did not reproduce them on current `main` plus the widening, and ran no before-run on
unchanged `main`. Inference: an earlier change removed them. The cause is not isolated.

## Pilot report `20261011T140324Z-rt-pilot` (observation, before the widening)

Run time 458.3 s for 2389 candidates in one batch. Gate: FAIL. The report is at
`~/.local/state/devenv-py/rt/20261011T140324Z-rt-pilot/report.md`. The run `20261011T135526Z-rt-pilot`
gave the same gate (460.5 s).

| Threshold row | `languages.python` | `services.postgres` |
| --- | --- | --- |
| Corpus size (10 and 5) | PASS, 24 real fixtures | PASS, 10 real fixtures |
| RT2 | FAIL, 18 of 21 eligible (3 `attribute 'requests' missing`) | REVIEW, 8 of 8 |
| RT3 | REVIEW, 21 of 21 | REVIEW, 10 of 10 |
| RT4 | REVIEW, 24 of 24 | FAIL, 9 of 11 (`postgresql_16` against `postgresql`; `.` against `./.`) |
| RT5 | PASS, 26 of 26 | PASS, 9 of 9 |
| RT6 | FAIL, 18 of 21 (same 3 fixtures) | REVIEW, 8 of 8 |
| RT7 | FAIL | FAIL |
| RT8 | PASS, 95 of 95 | PASS, 32 of 32 |
| RT1 coverage | FAIL, 24 of 26 | FAIL, 9 of 12 |
| RT3 typed ratio | PASS, 79 of 81 (97.5 percent) | FAIL, 33 of 38 (86.8 percent) |
| RT7 size and RT8 enumeration | PASS | PASS |
| Exclusion share (20 percent) | PASS, 0 of 24 | FAIL, 3 of 10 excluded by `has-fn` (30 percent) |
| Run time (15 minutes, warm) | PASS, 458 s (cache state not checked) | same |
| Truth stability | NOT-MEASURED | NOT-MEASURED |

"REVIEW" means the report found an eligible skip outside `has-fn`, `fails`, and `secret`
(`alone-needs-project`, `has-imports`, `no-literal-fields`).

## Open items for GM9 (observation unless marked)

1. Package identity. Three `languages.python` fixtures fail RT2 and RT6 (`python-packages`,
   `python-packages-no-venv`, `python-subprocess`): truth keeps the `pname` `requests`, the writer
   renders `pkgs.requests`, and the attribute is `python3Packages.requests`. `python-uv-sync` fails
   RT1 (`uv` fits `uv` and `python3Packages.uv`). `postgres-timescale` fails RT4 (`postgresql`
   against `postgresql_16`). Fix: IN PROGRESS (next section).
2. `postgres-customdbuser` RT4: the `$path` `.` against `./.`. Not examined. The cause is in path
   normalization in the reader or in truth.
3. `services.postgres` exclusion share: 3 of 10 fixtures are skipped as `has-fn` (30 percent against
   the 20 percent limit). Inference: the widening does not change this, because the writers still
   skip `$fn` values. Nobody re-measured it.
4. `services.postgres` RT3 typed ratio: 86.8 percent against the 90 percent threshold. Not
   re-measured after the path change in `9a541b4bd8ed`.
5. Truth stability is NOT-MEASURED by the report. Step 7 records it in each `triage.toml` (0 unstable).
6. `alone` fixtures skip the evaluating checks (`alone-needs-project`: 15 for `languages.python`, 6
   for `services.postgres`). The `alone_project` option is not wired in.
7. The run-time threshold needs a warm cache. The case directories carry the run id, so a rerun
   cannot hit the cache (see the harness fix section).

## In progress at the time of writing (no results claimed)

- Harness package identity by the full `$name` with attribute resolution, for RT2 and RT6. It
  supersedes the `pname` comparison. See MDL-020 in [CONCEPT.md](../CONCEPT.md).
- RT7 forcing of the `config.packages` names and of `enterShell`.
- Content-addressed case directories, for a warm cache.
- The final GM9 `rt-pilot` gate run.

## Gate GM9

IN PROGRESS. Not met. See [GATES.md](./GATES.md).

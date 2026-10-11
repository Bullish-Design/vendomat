# Steps 2 and 3 record: the evaluation driver, batch evaluation, and bisection

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`. The raw report is
`~/.local/state/devenv-py/step-2-6/REPORT.md` (shared with Steps 5 and 6). The Step 3 timing table
comes from `~/.local/state/devenv-py/step-7/REPORT.md`.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` (unchanged; `pin.toml` and `devenv.lock` untouched) |
| Base | `devenv-py` `main` at `ce250ec0` |
| Workspace | `~/Documents/Projects/gitman-workspaces/dpy-truth` |

## Commits on `devenv-py` `main`

| Commit | Subject |
| --- | --- |
| `4d6712d7a2cf` | feat: add the introspection module, oracle, and serializer |
| `3b6e48c20b09` | feat: add the evaluation driver with batch bisection |

Later changes to the driver: `ad9476284450` (content-addressed request path; see
[step-15.md](./step-15.md)).

## Files

`nix/introspect.nix`, `nix/oracle.nix`, `nix/serialize.nix`, `nix/touched.nix`,
`pins/devenv-2.4.0-b904dcb5-c2f38fe7/devenv.nix` (imports `../../nix/introspect.nix`),
`src/devenv_py/driver.py`, `tests/test_driver.py`, `tests/test_batch.py`, `tests/conftest.py`.
Every test that calls devenv carries the `nix` pytest marker.

## Commands and results

| Command | Expected | Actual |
| --- | --- | --- |
| `devenv eval -O introspect.request:path /tmp/dpy-req.json introspect.result` in the pin directory, with a dotted echo key | the payload returns | exit 0; result `"{\"a.b\":{\"c.d\":1}}"` |
| `testee verify --full`, first run | green | exit 1, run `20261011T051150Z-4279fb01939a`; one test bug (the glob `b*` also matched `bisect.log`) |
| `testee verify --full`, final | green | exit 0, run `20261011T051232Z-101a43914d5c`; ruff, ruff-format, ty, pytest PASS; 71 tests passed, 0 failed, 0 skipped; 22 s wall |

## Observations

- O1. The golden batch of five fixtures at touched scope took about 1.6 s.
- O2. `env."a.b" = "x"` evaluates in devenv. A dotted echo key round-trips because the result is a
  JSON string.
- O3. `builtins.abort` inside `env.MARK` aborts the whole batch. Bisection isolates the bad candidate
  and puts `dpy-bisect` in the error tail.
- O4. The cache follows a changed request file at one path (`test_cache_follows_a_changed_request_file`,
  0.68 s).

## Timing table for batches (Step 3 action 6)

The Step 7 bench measured this table on 181 `batch` corpus fixtures with truth, touched scope.
Source: `~/.local/state/devenv-py/step-7/REPORT.md`. Peak memory comes from
`resource.getrusage`, because the host has no `/usr/bin/time`.

| n candidates | cold wall (s) | cold per candidate (s) | peak RSS (MB) | warm wall (s) |
| --- | --- | --- | --- | --- |
| 1 | 0.33 | 0.33 | 84 | 0.11 |
| 10 | 1.27 | 0.127 | 211 | 0.07 |
| 50 | 3.54 | 0.071 | 436 | 0.11 |
| 100 | 5.37 | 0.054 | 628 | 0.12 |
| 181 | 12.13 | 0.067 | 751 | 0.13 |

The table has no row for 200: only 181 `batch` fixtures with truth exist. The phase-A whole-tree
oracle cost 2.8 s per candidate. Touched scope costs about 0.06 s per candidate at n of 50 or more.
Memory grows about 3.7 MB per candidate.

## Eval cache (observation, Step 7)

The phase-A claim "one cache entry per project" is refuted. Sequence A, A, B, A, B on the same request
files took: A 1.25 s, A again 0.12 s, B 0.52 s, A 0.12 s (hit), B 0.12 s (hit). The cache key holds
the request file path. A byte-identical copy of A at another path missed (1.26 s). The first driver
wrote `request.json` into a new run directory each time, so repeated runs never hit the cache.
`ad9476284450` fixed this (see [step-15.md](./step-15.md)).

## Departures from the guide

1. `introspect.result` is `types.str` that holds `builtins.toJSON` of the answer, for all kinds. The
   driver decodes twice.
2. `introspect.nix` takes `@moduleArgs` and passes `args`, `baseOptions`, `modules`, `scope`, and
   `deny` to the oracle. The `optionsDoc` option and the `options` kind came with Step 4.
3. `oracle.nix`, `serialize.nix`, and `touched.nix` replace the guide drafts. Roots end in `/`.
4. `run_request` takes an optional `run_dir`. The default is
   `~/.local/state/devenv-py/runs/<timestamp>-<kind>/` (override with `DEVENV_PY_STATE`). The
   subprocess gets `stdin=DEVNULL`. The driver appends the host `bin` directories to `PATH`, so it
   works in the Testee shell.
5. `run_batch` returns `dict[str, Outcome]` with `status` `ok` or `eval-error`, `result`, and
   `error`. It writes `bisect.log` and one subdirectory per call. A timeout is not bisected: it
   raises `DriverError(timed_out=True)`. A missing `devenv` binary raises `OSError`, not
   `DriverError`.
6. Step 3 action 3 is proved in part. An absolute module path keeps its file in
   `definitionsWithLocations` (tested). Pure evaluation reads candidates outside the base project
   (tested). The driver needs no `.candidates/` copy.
7. `truth_for_fixtures` labels candidates by the absolute fixture path. No `dpy truth` command
   exists. The corpus runner (`python -m devenv_py.corpus evaluate`) computes truth.
8. Not done: the cache versus no-cache wall time of Step 2 as a table. The cache test proves the
   behavior only.

## Incident: the shared virtual environment

The shell of the agent had `UV_PROJECT_ENVIRONMENT` and `VIRTUAL_ENV` set to Vendomat's venv. A bare
`uv sync` therefore overwrote that venv. The agent ran `uv sync` in the Vendomat root, which
restored `vendomat==0.7.0rc1` and its locked dependencies. It also moved `ty` to `0.0.54` and
removed the `devenv-py` install. The agents of Step 8 and Step 11 (syntax reader) also ran a bare
`uv` command. Each swapped the editable `devenv-py` install in that venv. Observation: the venv holds
Vendomat's own lock again, with no `devenv-py` install. All later briefs use
`env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV devenv shell -- uv ...`. The skills carry this rule.

## Gate GM1

Met. The echo, dotted-key, cache, bisection, and batch tests pass on the pin. The timing table
exists.

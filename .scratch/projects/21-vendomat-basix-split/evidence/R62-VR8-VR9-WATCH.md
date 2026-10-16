# R62: the option `vendomat.watch` (VR8) and trimmed errors in `apply` (VR9)

**Date:** 2026-10-15. **Ruling:** R62 ("Go for option 1", 2026-10-15, answer to the owner options for
request VR8 of Basix). Requests: VR8 and VR9 from Basix
(`basix/.scratch/projects/002-concept-review/VENDOMAT-REQUESTS.md`). Rows: `VMT-280`, `VMT-281`, `VMT-282`.
The ledger skips `VMT-185` to `VMT-279` because Basix reserves `BSX-240` to `BSX-279` on the shared number line.

## Status of the requests

| Request | State |
| --- | --- |
| VR8 (more watched files) | Resolved by R62 and `VMT-280`. On `main`. No release carries it. |
| VR9 (first error line first in `apply`) | Resolved by `VMT-281`. On `main`. No release carries it. |
| VR10 (the `cache-key.pub` commit message, `BSX-253`) | Resolved later by R63 (`VMT-282`, `VMT-283`). See [R63-VR10-KEY-COMMIT](R63-VR10-KEY-COMMIT.md). |

## The option (proposed name, now proved by the fixtures below)

`vendomat.watch`: `listOf` (a workspace-relative file path), default `[ ]`. Lists from several modules merge.
Declared in `devenv/devenv.nix`. The Nix type refuses a bad path at evaluation (`watchPathOk`).
`workspace.check_watch_path` repeats the rule in Python, and also refuses a directory and a symlink that
leaves the workspace.

## Code paths

| File | Change |
| --- | --- |
| `devenv/devenv.nix` | The option and its path type. |
| `src/vendomat/workspace.py` | `check_watch_path`, `extend_watched`. `watched_changes`, `fingerprint`, `refuse_ignored_watched`, `commit_watched` take a `watched` tuple (default: the four fixed files). |
| `src/vendomat/apply.py` | `watch_paths` (runs `devenv eval vendomat.watch`), `failure_text` (trim, 40 lines, log file). `dirty_apply`, `other_changes`, `refuse_changed_during_build`, and `apply` use the set. The refusal message names the watched files. `build_toplevel` uses `failure_text`. |
| `src/vendomat/rollback.py` | Reads the set (not for `--boot-only`). When the read fails, it warns and uses the four fixed files, so a broken workspace can still roll back. |
| `src/vendomat/cli.py` | Help text of `apply`. |
| `README.md` | The option. |

`explain` lists no watched files, so it did not change. The launcher prints no watched-file hint.

## Fixtures (observation)

| Check | Result |
| --- | --- |
| `tests/test_machine_watch.py` (unit; in `test:full`) | pass |
| `testee verify opt:catalog-eval`, run `20261016T013659Z-0919156df171` (Nix type: default, merge, 11 refused paths) | pass, 156 tests, 0 skipped |
| `testee verify opt:catalog-devenv`, run `20261016T013801Z-e821394f64ab` (real devenv 2.4.0: list read, `../outside.yaml` refused, a `basix.yaml:3:` fault first) | pass |

No VM check was added. The VM checks of `apply` and `rollback` (`opt:machines-vm`) use a workspace of the
catalog and need the watch list only through the same functions that the unit tests run. A VM proof with a
watched Basix file is the Basix check `opt:basix-undo`.

## What Basix sets

In `entry/devenv.nix`, in the config of the entry module: `vendomat.watch = [ "basix.yaml" ];`

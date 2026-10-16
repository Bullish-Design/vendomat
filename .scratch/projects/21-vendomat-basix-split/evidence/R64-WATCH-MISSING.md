# R64: a missing `vendomat.watch` option

**Date:** 2026-10-16. **Ruling:** R64. **Row:** `VMT-284`.

## Observation

The owner ran `testee verify opt:machines-vm` on `main` (tree `2925b24a17`, commit `fb168c8100`,
run `20261016T144016Z-503c03d7b4fe`). Result: 11 failed, 1 passed. Every `vendomat apply` in the VM
stopped at `devenv eval vendomat.watch` with exit 2:

```
× Failed to get attribute 'devenv.config.vendomat.watch': attribute `devenv.config.vendomat.watch` not found
devenv eval vendomat.watch failed (exit 1)
```

The fixture workspace `tests/fixtures/machines/workspace` does not import the catalog module, so the
option does not exist there. Since R62 (v0.11.0), `apply` treated every failure of that evaluation as
fatal. The VM check did not run before v0.11.0 and v0.11.1.

## Inference

A real workspace can meet the same failure. The host `vendomat` command comes from the machine layer,
not from the lock of each workspace. A newer command can evaluate a workspace that locks a catalog
module older than R62. Before this fix, `apply` could not run in that workspace.

## Fix

- `src/vendomat/apply.py`: `watch_attribute_missing` is true only for exit 1 with the exact text
  ``attribute `devenv.config.vendomat.watch` not found``. Then `watch_paths` returns the four fixed
  files and prints nothing. Any other failure raises exit 2 with the text of `VMT-281`.
- `rollback` calls `watch_paths`, so the missing case is silent there too.
- `tests/test_machines_vm.py`: a syntax error in `devenv.nix` now stops at the watch read. The test
  asserts exit 2, `devenv.nix:1:13` in the first three lines, and no build. Four assertions changed from
  the pre-R63 state (`?? .machines/` after apply and after rollback) to a clean working copy, with the
  owner's approval.

## Checks

| Check | Run | Result |
| --- | --- | --- |
| `opt:machines-vm` (after the fix) | `20261016T150342Z-e4c94a8a015c` | 12 passed, 375.67 s |
| `opt:catalog-devenv` (real devenv 2.4.0 gives the matched text) | `20261016T151008Z-ea493b63da88` | PASS |
| Unit fixtures in `tests/test_machine_watch.py` | in `test:full` | see the release evidence |

## Limits

- **Weak contract.** The command matches devenv's error text. A devenv release that rewords it breaks
  the match. The real-devenv test is opt-in (`opt:catalog-devenv`), because real devenv needs the
  network, so the normal gate does not catch a reworded text. A probe that evaluates the option with a
  default is cleaner. It is deferred, because `devenv eval` takes attribute paths only.
- **Refinement 1 deferred.** The VM fixture workspace still does not import the catalog module. An
  import adds the sharing module (Harmonia) to the fixture machine. The VM test assumes a machine
  without it (a stand-in cache key, the download counts), so the change needs a test redesign.

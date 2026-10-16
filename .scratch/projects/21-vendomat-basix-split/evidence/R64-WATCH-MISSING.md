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
- **Refinement 1 done** (see below). The no-module case stays covered by the unit fixtures in `tests/test_machine_watch.py` and by the opt-in real-devenv test `opt:catalog-devenv`.

## Refinement 1: the VM fixture imports the catalog

**Date:** 2026-10-16. **Rows:** `VMT-285`, `VMT-286`. **Owner approval (verbatim, in session):** "Great, agreed and approved. Permission granted for all changes. Kick off parallel background sonnet subagents to implement this." Recorded as an R64 follow-up.

### Change

- `devenv.yaml.in` adds the input `vendomat` (`path:`, `flake: false`, a copy of `devenv/` and `templates/workspace/`) and `imports: - vendomat/devenv`. A real workspace uses a flake `vendomat` and `follows` for `devenv` and `nixpkgs`. The fixture names `devenv` and `nixpkgs` as paths, because the machine is offline.
- `vendomat.yaml` keeps `machines: box:` (the empty entry of R51). The flow form `{}` is refused by the parser.
- The harness copies the catalog source to the work directory and to the machine at the same path, as it does for the module tree.

### Changed assertions

| Test | Old form | New form | Reason |
| --- | --- | --- | --- |
| `test_apply_a_gives_the_same_path_...` | The harness wrote the stand-in key `box:AAAA=` to `/var/lib/vendomat/cache-key.pub`; the test compared the copy with it; the harness then deleted the file. | The test reads the key that the sharing module made at first boot, checks its shape (`box:BASE64`), and compares the committed `.machines/box/cache-key.pub` with it. The file stays. | The stand-in existed because the fixture machine had no sharing module. |
| `test_apply_a_gives_the_same_path_...` | none | After apply, no failed unit, and `curl http://127.0.0.1:5000/nix-cache-info` answers. | New proof that Harmonia runs with the real key. |
| `test_the_machine_runs_system_a_before_any_command` | none | `vendomat-cache-key.service` and `harmonia.socket` are active; the key file starts with `box:`. | New proof of the sharing module at first boot. |

Every other assertion is unchanged. The download counts needed no new baseline: the harness cache counts only requests that reach it, and Harmonia's paths are in system A, which the image holds. The counts are 0 for the same-path apply and the rollbacks, and above 0 for `hello` (A-prime, and 11 after the garbage collection).

### Checks

| Check | Run | Result |
| --- | --- | --- |
| `testee verify` | tree `2875c64091` | GREEN |
| `opt:machines-vm` | `20261016T152444Z-32ec6cecc98f` | 12 passed, 436 s |

The first `opt:machines-vm` try (run `20261016T152411Z-e71495708282`) failed in setup: the fixture `vendomat.yaml` used `{}`, and the parser refuses flow style. Observation only; the next run fixed it.

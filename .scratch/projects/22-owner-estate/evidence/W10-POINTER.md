# W10: the pointer file on devenv 2.4.0 — 2026-10-13

<!-- Provenance: a subagent ran the fixtures on 2026-10-13. Outputs, traces, and scripts:
~/.local/state/vendomat/p22/w10-pointer/ (f2.out, f3.out, f4.out, f4b2.out, f5.out, pin-run1.out,
pin-run2.out, pin-neg.out, trace/, f2.sh to f5.sh, lib*.sh, pin-fixture.sh, neg-fixture.sh,
pin-fixture-files/). The subagent could not write a report file; the orchestrator wrote this record
from its report and did not rerun the fixtures. -->

This record backs owner rulings R12 and R14 (`ESTATE-035`, `ESTATE-036`, `ESTATE-037`).

## Inputs

- devenv 2.4.0+b904dcb; Nix 2.34.7.
- One scratch devenv project and one evaluation cache per case.
- The layer is a store directory with a real `default.nix` that sets `env.SPIKE_VAR`.
- The pointer is a real file outside the store: `import /nix/store/<hash>-layer`.
- A pointer rewrite writes a temporary file, then `mv`, after `sleep 1.2`: devenv stores
  modification times in whole seconds.
- Cache rows read with W9's `q.py`; checks named as in [W9](W9-EVAL-CACHE.md) (check 1: time, then
  hash; check 2: `inputs_changed`, hash only).

## Fixtures

| F | Claim | Result |
| --- | --- | --- |
| F1 | A pointer rewrite is seen with no flag; the pointer is tracked; store paths are not. | Pass. L1 became L2. `file_input` has the pointer row and no `/nix/store` row. |
| F2a | Check 1 alone catches a normal rewrite. | Pass. Trace: `file ... modified or removed, cache invalid`. |
| F2b | New content with the old modification time forced back (`touch -d`) is still caught. | Pass. Trace: `cache hit`, then `restore failed`: check 2 caught it. |
| F2c | The same test on the directory-symlink layout. | Not applicable: store files always have time 1. Only check 2 catches that layout; the trace matches F2b. |
| F3 | A rewrite with identical content forces a new evaluation. | Fail, as wanted. 8 cache hits, 0 invalidations. One extra hash, about 0.03 s. Hits stay about 0.3 s; a cold evaluation takes 4.4 s; a forced refresh 2.6 s. |
| F4a | A shared real file holds the pointer path; each project imports the shared file by relative path. | Pass. A pointer rewrite is caught. An edit of the shared file to name another pointer is caught. No flag. |
| F4b | `builtins.getEnv "DEVLAYER_POINTER"` with a default. | Works. Evaluation is impure, and devenv records the variable in `eval_env_input`. Every change of the variable forces a full evaluation (about 2.4 s). |
| F5 | The pointer file is missing. | Unguarded: exit 1 with a generic error; its last line is `error: path '<pointer>' does not exist`. Guarded with `builtins.pathExists`: a clean fallback, and the missing path gets a row with an empty hash. Create, rewrite, delete, and recreate were each caught with no flag. |
| F6 | `pin-fixture.sh` runs unattended and fails when the pointer case breaks. | Pass. Two runs: exit 0, 24 s each. A negative control (`neg-fixture.sh`, which skips the rewrites): exit 1 with `FAIL P1` and `WARN D1`. |

## Observations

- F4a chain: project `devenv.local.nix` (a symlink) to the central overlay file (real) to the shared
  file (real) to the pointer (real) to the store. Every real file in the chain has a row.
- **A relative import resolves against the directory of the symlink's target** (the central
  overlay file), not the project directory.
- F3: after an identical rewrite, the row keeps the old time, so later hits re-hash the small
  pointer each time. The cost is below timing noise.
- F4b: six alternating runs took 2.3 s to 2.6 s each; steady runs took 0.26 s and 0.36 s.

## Inference (not observed)

- A real Home Manager activation always moves the pointer's modification time, so check 1 catches
  it. If cachix/devenv#3154 adds a time shortcut to check 2, the pointer still works, and the
  directory-symlink layout breaks.
- A pointer that is a symlink (for example a Home Manager `home.file`) resolves into the store and
  goes untracked. The pointer must be a regular file. The same holds for the shared file of F4a.
- `getEnv` makes the cache depend on the caller's environment. A shell, direnv, a cron job, and
  Dagu could each select a different layer, and each change costs a full evaluation.

## The pin fixture

`pin-fixture.sh` (it needs `pin-fixture-files/` beside it):

| Check | Meaning | On failure |
| --- | --- | --- |
| P0 | A cache hit keeps the value | fail |
| P1 | A pointer rewrite is picked up | fail (exit 1) |
| P2 | A rewrite with the time forced back is picked up | warn |
| P3 | The pointer has a `file_input` row | fail |
| D1 | A directory-symlink repoint is picked up | warn; exit 3 with `STRICT_DIR=1` |

Exit codes: 0 pass, 1 pointer case failed, 2 fixture error, 3 directory case failed under
`STRICT_DIR=1`. It removes its temporary directory unless `KEEP=1`.

## Verdicts

- **R12 holds** on devenv 2.4.0. A real pointer file outside the store is caught with no flag. It
  does not depend on the re-hash accident; check 2 only backs it up (F2b).
- An activation with no layer change is harmless. Skipping the write is still better.
- **The pointer and the shared file must be regular files**, never symlinks.
- **The configurable path (R14) works through a shared real file (F4a).** `getEnv` works too, but
  ties the cache to the caller's environment; do not use it.
- **A `pathExists` guard** gives a clean fallback before the first switch, and it is tracked.

## Unproved

A real Home Manager activation; a symlinked pointer (expected untracked, by W9's rule); a future
devenv with a time shortcut; the relative import on devman's real overlay layout (tested at
`../../common/` in scratch only).

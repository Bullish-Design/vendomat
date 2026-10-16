# R63: apply commits the public cache key (VR10)

**Date:** 2026-10-16. **Ruling:** R63. **Owner words (verbatim):** "Great, do #1". Option 1: "Fix VR10 in Vendomat: apply writes the key before its commit and puts it in that commit. Then release Vendomat v0.11.1 to the local cache, bump the Basix pin, and tag `rc.3`."
**Request:** VR10 from Basix (`basix/.scratch/projects/002-concept-review/VENDOMAT-REQUESTS.md`, `BSX-253`). **Rows:** `VMT-282`, `VMT-283`.

## Observation

Basix run `20261016T130153Z-9d8544c5541c`, check `opt:basix-release`, Vendomat v0.11.0. `vendomat apply` printed `commit 17782c98abf2`, then `wrote .machines/basix/cache-key.pub; commit it so that your other machines trust this one`. The working copy kept `?? .machines/basix/cache-key.pub`. The learner needs a version-control command, which the common path forbids (`BSX-253`, `BSX-254`).

## Change

| File | Change |
| --- | --- |
| `src/vendomat/apply.py` | `pending_cache_key` and `write_cache_key` replace `publish_cache_key`. `apply` writes the key after the build and the change check, then commits it with the watched files, then activates. The identity check before the build also covers a commit that holds only the key. |
| `src/vendomat/workspace.py` | `commit_watched` takes `extra` paths. `restore` and `diff_text` take `keep` paths. |
| `src/vendomat/rollback.py` | The restore and the diff leave the key file out. |

## Ruling on the key path (watched or not)

The key path is not a watched file. A watched file is user configuration: a change to it makes the build and the commit, and the build reads it. The key is output of the machine. Three effects follow.

1. `apply` skips the key path in its dirty check. It writes the file again from the machine and commits it, so a stale or hand-edited copy cannot block it.
2. `rollback` skips the key path in its dirty check, because `apply --dirty` leaves the file uncommitted (no commit exists to hold it).
3. `rollback` keeps the key file as it is. Before this change, a rollback to a commit without the key deleted the tracked key in the rollback commit, and the other machines lost trust in this one. The key is the identity of the machine, not a past configuration.

The key is written after the build. The build of this machine does not read its own key, so the built system is the same. The fingerprint check runs before the write, so the write cannot fail it.

A failed switch leaves the key in the commit, as it leaves the configuration (the commit comes before the switch, R55).

## Fixtures (observation)

`testee verify` in the Gitman workspace `vr10`: GREEN 4/4 (run `20261016T132742Z-a5c937ca6b53`, tree `322457e722`, before the documents). New or changed cases: `tests/test_machine_apply.py` (new key with a configuration change; key only; same key; changed key; key left by an older version; `--dirty`; refusal of another machine's key file; identity check before the build; failed switch), `tests/test_machine_rollback.py` (key kept; key left by a dirty apply), `tests/test_machine_workspace.py` (`extra`, `keep`). The opt-in `opt:machines-vm` has updated assertions and did not run. A real two-machine proof is not done.

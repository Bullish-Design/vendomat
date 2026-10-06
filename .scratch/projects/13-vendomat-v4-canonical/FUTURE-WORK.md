# Vendomat future work

**Date:** 2026-10-06. **Status:** Canonical record of deferred capabilities. **No V4 phase gate.**

This file holds 17 requirement ID strings for capabilities V4 does not build. Each group names the
trigger that would open its design. No ID here gates a V4 phase. No ID here is reused or renumbered.

Opening any group needs its own review. A trigger permits a design session; it does not authorize an
implementation.

## Rules that apply to every group

1. Native declarations and locks stay the only selection authority.
2. A helper must leave native files authoritative for each dependency declaration.
3. Add a helper only after two real consumers hit the same repeated problem and a native-only trial
   leaves a concrete gap.
4. Test the failure path before enabling the capability.

## Group 1 — reviewed upgrades (`V4-UPG-001`–`009`)

**Trigger:** Two real consumers need the same dependency-update review, and `devenv update` in an
isolated checkout leaves a recorded gap.

**Native-only first option:** `devenv update [input]` in an isolated checkout, a devenv task to
validate the diff, and the owner's version-control workflow to record acceptance.

| ID | Deferred behaviour |
| --- | --- |
| `V4-UPG-001` | A proposal starts from a recorded consumer base in an isolated checkout, leaving the active tree unchanged. |
| `V4-UPG-002` | Native tooling produces the proposed declaration and lock diff. No Vendomat revision database exists. |
| `V4-UPG-003` | The proposal validates the exact changed composition. A changed diff invalidates its evidence. |
| `V4-UPG-004` | A failed proposal preserves its logs and leaves active files unchanged. |
| `V4-UPG-005` | A successful proposal may be cached without being accepted. |
| `V4-UPG-006` | Acceptance checks that the base files still match the validated base. |
| `V4-UPG-007` | Acceptance checks that the selected outputs remain available under the required policy. |
| `V4-UPG-008` | Acceptance applies only the validated native diff. It performs no rebuild, commit, merge, tag, or deployment. |
| `V4-UPG-009` | A managed hold records a reason and a date while native files stay the selection authority. |

## Group 2 — release and scheduled operations (`V4-OPT-001`–`004`)

**Trigger:** A project needs a release task that a native devenv task cannot already express, or a
repeated operation justifies a scheduled sweep.

**Native-only first option:** A devenv task for the release steps, and a systemd timer for
scheduling.

| ID | Deferred behaviour |
| --- | --- |
| `V4-OPT-001` | A release task cannot report success after a required gate failure. |
| `V4-OPT-002` | A retry never moves an already published immutable tag to another commit. |
| `V4-OPT-003` | A scheduled sweep may prepare proposals. It never accepts or deploys them automatically. |
| `V4-OPT-004` | A scaffold produces reviewable native source changes with no duplicate editable setting. |

## Group 3 — upgrade state reporting (`V4-EVD-008`)

**Trigger:** Group 1 opens.

| ID | Deferred behaviour |
| --- | --- |
| `V4-EVD-008` | Reports distinguish a prepared proposal, an accepted uncommitted change, and an activated configuration. |

## Group 4 — package source mapping (`V4-SRC-007`)

**Trigger:** A real inspection fails because a built package's source is unavailable, **and** a
fixture proves a native mapping on the pin.

**Why V4 defers it.** A built package's source is reachable only by evaluating the package set that
selected it. Patches apply during the build, not to `src`, so the result can never be labelled exact
selected source. `pkgs.srcOnly` produces the unpacked and patched tree as a store path. It runs
`unpackPhase` and `patchPhase` only, and it is undocumented in the Nixpkgs manual. Under V4 a built
package's source status is `unresolved`.

| ID | Deferred behaviour |
| --- | --- |
| `V4-SRC-007` | Packaging patches and known transformations appear beside the selected source, labelled selected source with packaging changes. |

**Design constraint for that session:** the label must distinguish the pristine fetched tree from the
patched tree. The derivation JSON separates them: `src` is the fetched tree, and `patches` are
separate store paths in the derivation environment. Do not compare an archive hash with a hash of its
unpacked tree.

## Group 5 — source indexing (`V4-SRC-013`)

**Trigger:** Real searches over retained source demonstrate value that reading store paths does not
already give.

| ID | Deferred behaviour |
| --- | --- |
| `V4-SRC-013` | An index or summary identifies the source identities used to create it, and reports stale data or regenerates. |

**Design constraint:** an index is derived state. It must be rebuildable and must never become a
selection authority. Keep generated summaries separate from source facts.

## Group 6 — retention and deletion (`V4-REC-007`)

**Trigger:** Measured storage growth from `P-STORAGE` justifies deletion.

**Why V4 defers it.** V4 deletes nothing automatically (`V4-REC-005`). Attic's native per-cache
retention period covers time-based collection, and the source cache's period is set to zero.

| ID | Deferred behaviour |
| --- | --- |
| `V4-REC-007` | An unreachable machine never counts as approval to delete its recovery paths. |

**Design constraint for that session:** compute and preview the protected set first. Binary retention
must account for active selections, saved plans, and machine recovery needs. Source retention must
account for explicit holds and for evidence that promises source availability. Destructive retention
needs its own inventory and recovery proof.

## Not in this file

The Jujutsu–btrfs–bubblewrap application and `V4-APP-001`–`031` are in
[LATER-APPLICATION.md](./LATER-APPLICATION.md).

Pre-V4 consumer migration is not deferred work for V4 to schedule. `V4-OWN-012` retired from V4
scope because a ground-up V4 owes nothing to the pre-V4 delivery paths. Migration is a separate
project, started after P6 passes, with its own before-and-after fixture per path.

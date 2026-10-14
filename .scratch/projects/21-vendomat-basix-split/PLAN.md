# Project 21: plan

**Status, 2026-10-14.** The design is final. W1 to W10 are historical spikes; implementation
slices S1 to S4 are complete on `main`, and Vendomat v0.8.0 is published. S2's host switch is also
complete under R48. S6 retired the old binary fork. The `p21-contracts` work is on `main`. It
records the VR1 to VR4, VR6, and VR7 contract work (VR5 is not done: Basix keeps its own hint); see
[its evidence](evidence/VR-CONTRACT-RESOLUTIONS-2026-10-14.md). Project 14 stays the implementation
contract until a release meets the project 21 gates. S5 steps 1 and 2 are done; S5 step 3 and S7 remain. Each spike has an evidence record under `evidence/`; raw logs go under
`~/.local/state/vendomat/p21/`. VM disk images, VM state, and VM scratch go under
`/mnt/shared/vendomat-p21/`. Disposable spike results do not prove real hardware or physical-disk writes.

## Spike phase (W1 to W10, done)

| # | Work | Result | Status |
| --- | --- | --- | --- |
| W1 | Review fork patches 0002, 0003, 0004, and 0008 against stock devenv v2.4.0 and upstream `main`. | A verdict on "no fork". | Done 2026-10-13: [W1](evidence/W1-FORK-REVIEW.md). Only 0003 needs a binary fork. |
| W2 | Machine fixtures in VMs: `deferredModule`, local apply, ISO and VM builds, local install. | Each mechanism proved or disproved. | Done 2026-10-13: [W2](evidence/W2-MACHINES.md). All four pass. |
| W3 | A Basix workspace with the follows topology of A1. | Proof that devenv resolves `basix/vendomat` and its import, with one lock. | Done 2026-10-13 as a spike: [W3](evidence/W3-TOPOLOGY.md). Works with a flake Basix and template `follows` lines. |
| W4 | The catalog with the Nix parser, the v3 grammar, the escape hatch rules, and the language mapping, in a stock-devenv workspace. | A requirement ledger draft for project 21 with successor IDs. | Done 2026-10-13 as a spike, before the rulings: [W4](evidence/W4-CATALOG.md), [ledger](REQUIREMENTS.md). 14 fixtures pass. |
| W5 | The disk guard as a disko pre-create hook in the Basix layout, in a VM: it refuses a used disk on the local and the remote install path. | A verdict on A5 option 3. | Done 2026-10-13: [W5](evidence/W5-DISK-GUARD.md). Backed with a change: replaces 0006, not 0005. |
| W6 | `pkgs.devenv` with patches 0003 and 0005 applied through `overrideAttrs`; the offline case of W1 Q2 and the 0005 refusal with it. | The A12 and A13 binary. | Done 2026-10-13: [W6](evidence/W6-HOST-BINARY.md). Backed. 0005 splits into a binary half and a 39-line module half in the module-only fork; the catalog sets `vendomat.mode`; 0008 not needed. |
| W9 | A lasting rollback: restore the files from an earlier commit, then apply; `configurationRevision`. | A verdict on A11 and a `vendomat rollback` design. | Done 2026-10-13: [W9](evidence/W9-ROLLBACK.md). Confirmed with changes. |
| W10 | A committed QEMU hardware report: what changes run to run and with the VM shape, and whether it changes the toplevel. | A verdict on A14. | Done 2026-10-13: [W10](evidence/W10-FACTER.md). Backed; one volatile field. |
| W7 | Public `machines.NAME.build.iso` and `build.vm` options in the module-only fork, over `_nixosEval`. | The A6 option 2 interface. | Done 2026-10-13: [W7](evidence/W7-BUILD-OPTIONS.md). D1 recommended; all eight fixtures pass. |
| W8 | Path D: an ISO of any machine through `extendModules`, with only required overrides, and policy in `iso.modules`. | The A6 interface and two patches for the module-only fork (no upstream pull request, R34). | Done 2026-10-13: [W8](evidence/W8-ISO-POLICY.md). Backed; six overrides required. |

Unproved after W1 to W4: real hardware; the `vendomat apply` command itself; an offline build on
the ISO; patch 0008's failure; why two `nixos-facter` runs differ; the catalog together with a
flake Basix; ISO and VM builds through the catalog; line numbers for schema faults (`VMT-035`).

The ledger is [REQUIREMENTS.md](REQUIREMENTS.md). Its rows for these gaps name what stays open.

## Implementation slices (S1 to S7)

The [implementation guide](IMPLEMENTATION-GUIDE.md) gives the step-by-step work for each slice, the
facts and spike artifacts it needs, and the open implementation decisions D1 to D8.

S1 is done, as of 2026-10-14: [S1-MODULE-FORK](evidence/S1-MODULE-FORK.md).
S2 and the host switch are done under R48, as of 2026-10-14: [S2-HOST-BINARY](evidence/S2-HOST-BINARY.md).
S3 is done, as of 2026-10-14. Vendomat v0.8.0 is published on `release` (`e5923a8f`):
[S3-CATALOG](evidence/S3-CATALOG.md). The catalog wiring of the sharing module landed in `79e46310ef30`.
S4 is done ([S4-APPLY-ROLLBACK](evidence/S4-APPLY-ROLLBACK.md)). Every new implementation slice
needs its own branch, its own verify, and evidence under `evidence/`. No slice plans an upstream pull
request (R34). The module-only fork and patched binary are long-lived.

| # | Work | Depends on | Ledger rows |
| --- | --- | --- | --- |
| S1 | The module-only `devenv` fork: `nixos` as `deferredModule`; `build.vm` and `build.iso` with `iso.modules`; the module half of patch 0005; the version file. **Done 2026-10-14**: tag `v2.4.0-vendomat-modules.1` published and locked as input `devenv`; see [S1-MODULE-FORK](evidence/S1-MODULE-FORK.md). | none | `VMT-064`, `VMT-082`, `VMT-095`, `VMT-106`, `VMT-107`, `VMT-108`, `VMT-118` |
| S2 (done; the host switched on 2026-10-14, R48; [evidence](evidence/S2-HOST-BINARY.md)) | The host binary overlay: `pkgs.devenv` with patches 0003 and 0005, built and kept under a GC root (R39: no Attic). | none | `VMT-074`, `VMT-099`, `VMT-126` |
| S3 (done; v0.8.0 released; [evidence](evidence/S3-CATALOG.md)) | The catalog rewrite in the repository: the Nix parser, the ruled keys, the hatch line, `explain`, error trimming, template `follows` lines, and `vendomat update`; and the Harmonia sharing module with its two-VM proof (R39). | S1 | `VMT-002`, `VMT-003`, `VMT-057`, `VMT-090` to `VMT-094`, `VMT-111`, `VMT-116`, `VMT-117` |
| S4 (done; [evidence](evidence/S4-APPLY-ROLLBACK.md)) | `vendomat apply` and `vendomat rollback` with the per-machine record, proved in a VM by `opt:machines-vm`. | S3 | `VMT-072`, `VMT-075`, `VMT-098`, `VMT-110` |
| S5 (steps 1 and 2 done 2026-10-14, [evidence](evidence/S5-BASIX.md); step 3, the Basix fixtures, runs in the Basix repository) | The Vendomat side of Basix: the collection hook change so any repository may fast-forward `release` (R37), and a parser that Basix imports for `basix.yaml` (R38). The Basix build is in `../basix/.scratch/projects/001-initial-concept/PLAN.md`. | S1 to S4 | `VMT-121` (with Basix), `VMT-171`; the `BSX-` rows are in the Basix ledger |
| S6 (done 2026-10-14; [evidence](evidence/S6-FORK-RETIRED.md)) | Retire the `v2.4.0-vendomat.4` fork and its other patches (0001, 0002, 0004, 0006 to 0009; see the fork table in the concept). | S1 and S2 | `VMT-080`, `VMT-081` |
| S7 | Real-machine gates: real hardware, and the two-machine Harmonia check. | S5 | `BSX-119`, `VMT-127` |

### Owner gates

The S2 host-switch gate was completed by the owner under R48 on 2026-10-14.

Any real disk write, including the S7 install on real hardware, still needs explicit owner approval.

### Remaining slices and gates

S5 steps 1 and 2 (the Vendomat side) are done. Step 3, the Basix fixtures, runs from the Basix
repository and needs a real Basix consumer. Basix
B2/B3 evidence is recorded in its own repository; it remains spike evidence until B5 integrates the
corrected disk guard and the product acceptance gate passes. S7's real-machine and two-machine
Harmonia checks remain outside this contract spike. Any physical-disk write requires owner approval.

The fresh-clone shell run also observed the `VMT-118` version-mismatch warning absent; its ledger
row records the run and the limit that this is not an explicit e2e assertion. Other current open
requirements remain identified by their IDs in the ledgers. The old list of pre-S3 gaps is
historical and is not an active blocker list.

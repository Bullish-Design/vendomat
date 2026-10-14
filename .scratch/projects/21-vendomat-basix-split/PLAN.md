# Project 21: plan

**Final, 2026-10-13.** The design is final. The plan has two phases: the spike phase (W1 to W10, done) and
the implementation slices (S1 to S7, not started). Each spike ends in an evidence record under `evidence/`. Raw logs go
under `~/.local/state/vendomat/p21/`. VM disk images, VM state, and VM scratch go under
`/mnt/shared/vendomat-p21/`. No spike changed production code or a real machine.

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

No slice has started. Every slice changes code, so it needs its own branch, its own verify, and
evidence under `evidence/`. No slice plans an upstream pull request (R34). The module-only fork and
the patched binary are long-lived.

| # | Work | Depends on | Ledger rows |
| --- | --- | --- | --- |
| S1 | The module-only `devenv` fork: `nixos` as `deferredModule`; `build.vm` and `build.iso` with `iso.modules`; the module half of patch 0005; the version file. | none | `VMT-064`, `VMT-082`, `VMT-095`, `VMT-106`, `VMT-107`, `VMT-108`, `VMT-118` |
| S2 | The host binary overlay: `pkgs.devenv` with patches 0003 and 0005, built and cached in Attic. | none | `VMT-074`, `VMT-099`, `VMT-105` |
| S3 | The catalog rewrite in the repository: the Nix parser, the ruled keys, the hatch line, `explain`, error trimming, template `follows` lines, and `vendomat update`. | S1 | `VMT-002`, `VMT-003`, `VMT-057`, `VMT-090` to `VMT-094`, `VMT-111`, `VMT-116`, `VMT-117` |
| S4 | `vendomat apply` and `vendomat rollback` with the per-machine record. | S3 | `VMT-072`, `VMT-075`, `VMT-098`, `VMT-110` |
| S5 | The Vendomat side of Basix: the collection hook change so any repository may fast-forward `release` (R37), and a parser that Basix imports for `basix.yaml` (R38). The Basix build is in `../basix/.scratch/projects/001-initial-concept/PLAN.md`. | S1 to S4 | `VMT-121` (with Basix); the `BSX-` rows are in the Basix ledger |
| S6 | Retire the `v2.4.0-vendomat.4` fork and its other patches (0001, 0002, 0004, 0006 to 0009; see the fork table in the concept). | S1 and S2 | `VMT-080`, `VMT-081` |
| S7 | Real-machine gates: real hardware, and the two-machine Harmonia check. | S5 | `BSX-119`, `VMT-120` |

### Owner gates

The owner must authorize each of these. No slice does them alone.

- Switching the host to the new binary of S2.
- Any real disk write, including the S7 install on real hardware.

### Open gaps with no ruling

Work or a ruling must settle these before S3 and S5 close: parser depth limit and line numbers
(`VMT-013`, `VMT-035`), trace trimming (`VMT-117`), the version warning (`VMT-118`), whether devenv
fetches unused inputs (`VMT-116`), and the disk guard gaps (`BSX-114`, `BSX-115`; Basix rows, now in the Basix ledger).

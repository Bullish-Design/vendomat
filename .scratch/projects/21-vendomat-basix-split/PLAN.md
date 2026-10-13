# Project 21: next work

**Draft, updated 2026-10-13 (W3, W4).** Each item ends in an evidence record under `evidence/`. Raw logs go
under `~/.local/state/vendomat/p21/`. VM disk images, VM state, and VM scratch go under
`/mnt/shared/vendomat-p21/`. No item changes production code or a real machine.

| # | Work | Result | Status |
| --- | --- | --- | --- |
| W1 | Review fork patches 0002, 0003, 0004, and 0008 against stock devenv v2.4.0 and upstream `main`. | A verdict on "no fork". | Done 2026-10-13: [W1](evidence/W1-FORK-REVIEW.md). Only 0003 needs a binary fork. |
| W2 | Machine fixtures in VMs: `deferredModule`, local apply, ISO and VM builds, local install. | Each mechanism proved or disproved. | Done 2026-10-13: [W2](evidence/W2-MACHINES.md). All four pass. |
| W3 | A Basix workspace with the follows topology of A1. | Proof that devenv resolves `basix/vendomat` and its import, with one lock. | Done 2026-10-13 as a spike: [W3](evidence/W3-TOPOLOGY.md). Works with a flake Basix and template `follows` lines. |
| W4 | The catalog with the Nix parser, the v3 grammar, the escape hatch rules, and the language mapping, in a stock-devenv workspace. | A requirement ledger draft for project 21 with successor IDs. | Done 2026-10-13 as a spike, before the rulings: [W4](evidence/W4-CATALOG.md), [ledger draft](REQUIREMENTS-DRAFT.md). 14 fixtures pass. |
| W5 | The disk guard as a disko pre-create hook in the Basix layout, in a VM: it refuses a used disk on the local and the remote install path. | A verdict on A5 option 3. | Done 2026-10-13: [W5](evidence/W5-DISK-GUARD.md). Backed with a change: replaces 0006, not 0005. |
| W6 | `pkgs.devenv` with patches 0003 and 0005 applied through `overrideAttrs`; the offline case of W1 Q2 and the 0005 refusal with it. | The A12 and A13 binary. | Proposed. |
| W7 | Public `machines.NAME.build.iso` and `build.vm` options in the module-only fork, over `_nixosEval`. | The A6 option 2 interface. | Done 2026-10-13: [W7](evidence/W7-BUILD-OPTIONS.md). D1 recommended; all eight fixtures pass. |
| W8 | Path D: an ISO of any machine through `extendModules`, with only required overrides, and policy in `iso.modules`. | The A6 interface and two upstream patches. | Done 2026-10-13: [W8](evidence/W8-ISO-POLICY.md). Backed; six overrides required. |

Unproved after W1 to W4: real hardware; the `vendomat apply` command itself; an offline build on
the ISO; patch 0008's failure; why two `nixos-facter` runs differ; the catalog together with a
flake Basix; ISO and VM builds through the catalog; line numbers for schema faults (`VMT-035`).

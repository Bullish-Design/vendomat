# Project 21: next work

**Draft, updated 2026-10-13.** Each item ends in an evidence record under `evidence/`. Raw logs go
under `~/.local/state/vendomat/p21/`. VM disk images, VM state, and VM scratch go under
`/mnt/shared/vendomat-p21/`. No item changes production code or a real machine.

| # | Work | Result | Status |
| --- | --- | --- | --- |
| W1 | Review fork patches 0002, 0003, 0004, and 0008 against stock devenv v2.4.0 and upstream `main`. | A verdict on "no fork". | Done 2026-10-13: [W1](evidence/W1-FORK-REVIEW.md). Only 0003 needs a binary fork. |
| W2 | Machine fixtures in VMs: `deferredModule`, local apply, ISO and VM builds, local install. | Each mechanism proved or disproved. | Done 2026-10-13: [W2](evidence/W2-MACHINES.md). All four pass. |
| W3 | A Basix workspace with the follows topology of A1. | Proof that devenv resolves `basix/vendomat` and its import, with one lock. | Open. Needs a Basix repository stub. |
| W4 | The catalog with the Nix parser, the v3 grammar, the escape hatch rules, and the language mapping, in a stock-devenv workspace. | A requirement ledger draft for project 21 with successor IDs. | Open. Follows the owner's rulings on A1 to A14. |

Unproved after W1 and W2: real hardware; the `vendomat apply` command itself; an offline build on
the ISO; patch 0008's failure; why two `nixos-facter` runs differ.

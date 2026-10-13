# Project 21: next work

**Draft, 2026-10-12.** Each item ends in an evidence record under `evidence/`. Raw logs go under
`~/.local/state/vendomat/p21/`. No item changes production code or a real machine.

| # | Work | Result |
| --- | --- | --- |
| W1 | Review fork patches 0002, 0003, 0004, and 0008 against stock devenv v2.4.0 and upstream `main`. | For each patch: what fails without it, whether upstream fixed it, and the smallest replacement. A verdict on "no fork". |
| W2 | Machine fixtures on the pinned devenv, in VMs: local `vendomat apply`, ISO and VM builds through `_nixosEval`, the six-step local install, and the `deferredModule` patch. | Each mechanism proved or disproved. |
| W3 | A Basix workspace with the follows topology of A1. | Proof that devenv resolves `basix/vendomat` and its import, with one lock. |
| W4 | The catalog with the Nix parser, the v3 grammar, the escape hatch rules, and the language mapping, in a stock-devenv workspace. | A requirement ledger draft for project 21 with successor IDs. |

Order: W1 and W2 can run in parallel. W3 needs a Basix repository stub. W4 follows the owner's
rulings on A1 to A9.

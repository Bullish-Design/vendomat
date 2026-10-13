# Project 22: next work

**Draft, 2026-10-13.** Each item ends in an evidence record under `evidence/`. Raw logs go under
`~/.local/state/vendomat/p22/`. No item changes production code, a real machine, or a project
repository. The migration phases of the concept start only after the owner rules on A1 to A4.

| # | Work | Result | Status |
| --- | --- | --- | --- |
| W1 | Import a module from an absolute, symlinked user path in `devenv.local.nix`; change the target; observe devenv's evaluation cache. | Whether a Home Manager path can replace `/run/current-system/sw/share/devman/`. | Done 2026-10-13: [W1](evidence/W1-DEVLAYER-PATH.md). A per-file link stays stale; a directory link is picked up. |
| W2 | A real standalone Home Manager generation in a scratch flake that links `~/.local/share/devlayer` as one directory. Switch twice; enter a scratch devenv shell after each switch. Also measure today's `/run/current-system/sw` path across a NixOS generation change, and `home-manager switch --override-input`. | A4 proved or disproved on real Home Manager; the development route of the concept proved. | Proposed. |
| W3 | devman `homeManagerModules.default`: shared options, a neutral service description, NixOS and Home Manager translators. Evaluate both in a scratch flake. Run the Dagu user unit in a VM or a throwaway user. | The devman port of the concept. | Proposed. |
| W4 | Testee task mode: run the five standard tasks by name in a clean checkout, one verdict per task, exit 78 reported as "not set up". Prove it in a scratch repository with placeholder, wired, and "not applicable" tasks and no Testee input. | `ESTATE-025` to `ESTATE-028` (R10). | Proposed. Supersedes the overlay-manifest form of W4. |
| W5 | The fleet doctor as a read-only prototype over the rules of the concept, run against all registered repositories. | A6; a baseline count per finding. | Proposed. |
| W6 | A nix-meta skeleton with `homeConfigurations."andrew@server"` that evaluates (no switch), a flake check for one node per family tool, and the atuin parity check on pytuin's package. | A2, A8; the shape of the home repository. | Proposed. |
| W7 | template-py and template-nix previews without tool pins, through CopyRoom's workshop. | The phase 1 change, reviewed before any release. | Proposed. |
| W9 | Read devenv 2.4.0's evaluation-cache source. Explain from the code why W1's directory-symlink change is noticed and the file-symlink change is not. Predict and simulate the real Home Manager layout, `/run/current-system/sw`, and `~/.nix-profile`. Say whether the behaviour is designed or incidental. Define the doctor's stale-module check. | The gate of R11 (`ESTATE-034`). | Running 2026-10-13. |
| W8 | The machine and home pairs (atuin, agentman, mnemonix, secrets) as shared packages or constants, each with a check that compares the two halves. | The cross-layer rule of the concept. | Proposed. |

Unproved after W1: the mechanism behind the directory result in W1; real Home Manager links;
`--override-input` on `home-manager`; Testee with an overlay-only manifest; the devman Home Manager
module; the fleet doctor; a standalone home with the current modules; the order and checks for the
machine and home pairs.

Survey records from 2026-10-13: [NIX-META-AUDIT](evidence/NIX-META-AUDIT.md),
[SUB-FLAKES](evidence/SUB-FLAKES.md), [NIX-SYSTEMS](evidence/NIX-SYSTEMS.md),
[FLEET-INVENTORY](evidence/FLEET-INVENTORY.md), [FAMILY-DELIVERY](evidence/FAMILY-DELIVERY.md),
[HOME-PORT](evidence/HOME-PORT.md), [TOOL-CLASSES](evidence/TOOL-CLASSES.md), and
[NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md). The raw inventory is under
`~/.local/state/vendomat/p22/inventory/`.

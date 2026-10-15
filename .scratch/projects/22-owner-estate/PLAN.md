# Project 22: next work

**Draft, 2026-10-13.** Each item ends in an evidence record under `evidence/`. Raw logs go under
`~/.local/state/vendomat/p22/`. No item changes production code, a real machine, or a project
repository. The migration phases of the concept start only after the owner rules on A1 to A4.

| # | Work | Result | Status |
| --- | --- | --- | --- |
| W1 | Import a module from an absolute, symlinked user path in `devenv.local.nix`; change the target; observe devenv's evaluation cache. | Whether a Home Manager path can replace `/run/current-system/sw/share/devman/`. | Done 2026-10-13: [W1](evidence/W1-DEVLAYER-PATH.md). A per-file link stays stale; a directory link is picked up. |
| W2 | A real standalone Home Manager generation in a scratch flake with the layer directory and the pointer-file activation step. Switch twice; enter a scratch devenv shell after each switch. Also prove `home-manager switch --override-input`. | R12 on real Home Manager; the development route of the concept proved. | Done 2026-10-15: [W2](evidence/W2-HOME-MANAGER-POINTER.md). Scratch HOME, real `home-manager switch`: two switches, `--override-input`, plain switch, and rollback each move the pointer and devenv sees it with no flag. A symlinked pointer is stale unless a `pathExists` guard tracks it. |
| W3 | devman `homeManagerModules.default`: shared options, a neutral service description, NixOS and Home Manager translators. Evaluate both in a scratch flake. Run the Dagu user unit in a VM or a throwaway user. | The devman port of the concept. | Done 2026-10-15: [W3](evidence/W3-DEVMAN-HOME-MODULE.md). The NixOS translator reproduces today's units byte for byte; the Home Manager translator runs Dagu, the watcher, a workflow, a restart, and the pointer step in a VM. Not committed to devman. |
| W4 | Testee task mode: run the five standard tasks by name in a clean checkout, one verdict per task, exit 78 reported as "not set up". Prove it in a scratch repository with placeholder, wired, and "not applicable" tasks and no Testee input. | `ESTATE-025` to `ESTATE-028` (R10). | Review and experiments done 2026-10-13 in Testee `.scratch/projects/10-task-mode/` (`REVIEW.md`, `DECISIONS-NEEDED.md`); R16 rules D1 to D4. Integrate hook change landed in devman-central `main` (`zmtzqqyy`). Testee 0.8.0 released 2026-10-14 (tag `v0.8.0`, `0c97f4bd`) and installed by nix-meta `zqzkrqok`. Next: the templates, then the 23 repository conversions. Supersedes the overlay-manifest form of W4. |
| W5 | The fleet doctor as a read-only prototype over the rules of the concept, run against all registered repositories. | A6; a baseline count per finding. | Done 2026-10-13: [W5](evidence/W5-FLEET-DOCTOR.md). Ten checks, 0.25 s, selftest 32 of 32. Testee is the remaining pin (22 repositories); every repository fails D05 and D06. |
| W6 | A nix-meta skeleton with `homeConfigurations."andrew@server"` that evaluates (no switch), a flake check for one node per family tool, and the atuin parity check on pytuin's package. | A2, A8; the shape of the home repository. | Done 2026-10-15: [W6](evidence/W6-HOME-SKELETON.md). The skeleton evaluates, builds, and passes its checks; the one-node check fails on nix-meta's lock today. Findings: pytuin's atuin 18.23 is untagged, pytuin and atuout must move together, and devman with devman-link collide in a Home Manager profile. |
| W7 | template-py and template-nix previews without tool pins, through CopyRoom's workshop. | The phase 1 change, reviewed before any release. | Done 2026-10-15: [W7](evidence/W7-TEMPLATE-PREVIEW.md). Both candidates render no pin and pass goldens and `release-check`; template-py `v0.9.0` still imports a machine-path Testee module. Not released. |
| W9 | Read devenv 2.4.0's evaluation-cache source. Explain from the code why W1's directory-symlink change is noticed and the file-symlink change is not. Predict and simulate the real Home Manager layout, `/run/current-system/sw`, and `~/.nix-profile`. Say whether the behaviour is designed or incidental. Define the doctor's stale-module check. | The gate of R11 (`ESTATE-034`). | Done 2026-10-13: [W9](evidence/W9-EVAL-CACHE.md). Directory case incidental; planned `linkFarm` layout and today's system-path import stale. |
| W10 | The pointer file on the pinned devenv: a real file outside the store that imports a store directory; change the store directory and rewrite the pointer; require the new value with no flag. Add the pin fixture of `ESTATE-036`. | R12 (`ESTATE-035`, `ESTATE-036`). | Done 2026-10-13: [W10](evidence/W10-POINTER.md). R12 holds; the shared-file mechanism works for R14; the pin fixture runs in 24 s. |
| W8 | The machine and home pairs (atuin, agentman, mnemonix, secrets) as shared packages or constants, each with a check that compares the two halves. | The cross-layer rule of the concept. | Done 2026-10-15: [W8](evidence/W8-PAIRS.md). Four pair checks pass on aligned halves and fail on eight kinds of drift; on nix-meta today they find one gap (the machine uid is null). Only pytuin exports a shared value; mnemonix and agentman need small exports first. |

Proved since W1 (2026-10-15): the mechanism behind the directory result (W9); real Home Manager
links, the pointer step, `--override-input`, and rollback, in a scratch home (W2); the devman Home
Manager module, run as a user unit in a VM (W3); a standalone home with the current modules, built,
with a one-node-per-tool lock check (W6); the template previews without tool pins (W7); the
machine and home pair checks (W8); the fleet doctor prototype (W5).

Unproved: a switch of the real `andrew@server` home; the tag rule for personal inputs (pytuin's
atuin 18.23 and atuout need tagged releases, and agentman has no flake package); the release of the
template candidates; moving the Dagu unit from the NixOS module to the home (ports 8080 and 50055
collide if both run); constants exported by mnemonix and agentman; the pair checks across two
repositories; a future devenv with the time shortcut of issue #3154; Testee with an overlay-only
manifest (superseded by R16).

Survey records from 2026-10-13: [NIX-META-AUDIT](evidence/NIX-META-AUDIT.md),
[SUB-FLAKES](evidence/SUB-FLAKES.md), [NIX-SYSTEMS](evidence/NIX-SYSTEMS.md),
[FLEET-INVENTORY](evidence/FLEET-INVENTORY.md), [FAMILY-DELIVERY](evidence/FAMILY-DELIVERY.md),
[HOME-PORT](evidence/HOME-PORT.md), [TOOL-CLASSES](evidence/TOOL-CLASSES.md), and
[NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md). The raw inventory is under
`~/.local/state/vendomat/p22/inventory/`.

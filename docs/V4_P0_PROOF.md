# Vendomat V4 P0 evidence

**Date:** 2026-10-06  
**Status:** Blocked. P0 is not complete, and P1 has not started.  
**Requirements:** `V4-OWN-009`, `V4-OWN-012`, `V4-MACH-001`, `V4-REC-009`  
**Repository base:** `34637a96d4bc8f1f93a57157c4e186c31bf3dc0a` (`main`, synchronized with
`origin` before the `v4-p0` Gitman lane began).

This record separates observed results from gaps. Raw command logs are stored outside the
repository in `/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/p0/`.

## Host and selected versions

| Item | Observed value |
| --- | --- |
| Host | `server`, Linux `6.18.38`, `x86_64-linux` |
| Nix | `2.34.7` |
| devenv executable | `2.4.0+b904dcb`, x86_64-linux; the adjacent `../../nix-meta/flake.lock` input revision is `b904dcb51fe48c30db250038241507f60752f222` |
| Vendomat devenv module | `cachix/devenv`, `src/modules`, revision `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`, nar hash `sha256-0FpLHIRDYiyo3EMTnMQSobZQknZaa3JuWo6vmMCK76o=` |
| Current host Vendomat selection | `/run/current-system/sw/share/vendomat/machine.json` names `/run/current-system/sw/bin/vendomat`, toolchain `/nix/store/iilwbhx0zmrzc33wm4vr1x2ib5f3f60a-repoman-toolchain-core`, vendor root `/nix/store/glz8awfy4m18xmqh7yvi8bdvbkrjlrl0-vendomat-vendor`, and wheelhouse `/nix/store/bpx4l868xry40zf4b0k9r1f125d7zhb2-vendomat-wheelhouse` |
| Current Vendomat input pin | The adjacent `../../nix-meta/flake.lock` selects Vendomat revision `bd26fea8a2124bb4b1bbd8721418d831b4c2bf13` |
| Installed module path | `/nix/store/p3dsyz9izp4zg8rgaifnabz1az67h8xj-vendomat-0.4.4/share/vendomat/consumer-module.nix` |
| Existing cache policy | `https://cache.nixos.org/` and `https://devenv.cachix.org`; `fallback=false`, `requireSigs=true`; no Attic substituter |

The repository's `devenv.lock` previously selected module revision
`37ecc72f1167655457851514507281310b3b1c3a`. `devenv --no-tui update devenv` changed it to the
Machines-capable module revision above. The current Vendomat input pin remains available in
`../../nix-meta/flake.lock`; this did not change a host or consumer selection.

The native fixture at `tests/fixtures/v4-p0-machines/` has its own lock:

| Input | Revision | nar hash |
| --- | --- | --- |
| `devenv` module (`cachix/devenv`, `src/modules`) | `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4` | `sha256-0FpLHIRDYiyo3EMTnMQSobZQknZaa3JuWo6vmMCK76o=` |
| `nixpkgs` | `c2f38fe7f9e04d9aadd354d380f2bd40531d9737` | `sha256-vNkJbtmqyBfFhn/HnzQo4ROuoyYWuy/allqTfJb4kMY=` |
| `disko` | `725ea35e410ad83be4931d1bff7e090eacaf3563` | `sha256-uZkBR7yHdIKUFB5SZdfgh1qkGfI3XmYmI/lTiquxbck=` |
| `home-manager` | `fae6e9e42c3b762ab47635cddcfaf6f52374a61b` | `sha256-KuLePuhwJM9NLt/gTLHzXaOoSZKGoB3m7NfXjiQ98HY=` |

The fixture declares a NixOS target `root@v4-p0.invalid`, one ext4 root filesystem, `hello`, and a
local Home Manager target for user `andrew`. The target hostname is intentionally unreachable;
the local Home Manager target tests native plan generation without activating it.

## Current delivery and consumer inventory

| Delivery path | Current use and evidence | P0 disposition |
| --- | --- | --- |
| Machine manifest | `../../nix-meta/machines/server.nix` imports `inputs.vendomat.nixosModules.default`. The active manifest is `/run/current-system/sw/share/vendomat/machine.json`. Vendomat's devenv module reads it before its flake-input fallback. | Preserve until a replacement passes its before-and-after fixture. |
| Installed central overlay | 11 active overlays import `/run/current-system/sw/share/vendomat/consumer-module.nix`: `argentic`, `eventic`, `flora-qc`, `flora`, `llgym`, `loci-core`, `loci.nvim`, `nix-secrets`, `poddantic`, `pyllij`, and `shellij`. The `loci-core` real shell resolved `repoman` and `agentman` from the selected Nix toolchain; `repoman --version=0.7.5`. | Preserve all 11. No migration has passed. |
| Local checkout overlay | 10 active overlays import `/home/andrew/Documents/Projects/vendomat/modules/devenv.nix`: `agentman`, `flora-core`, `forgelab`, `inferference`, `nix-desktop`, `nix-nvim`, `nix-paseo`, `repoman`, `talkee`, and `tyo3`. The RepoMan checkout shell resolved its editable `.devenv` command as configured. | Preserve all 10. No migration has passed. |
| Flake-input consumer | `tests/fixtures/store-consumer/devenv.yaml` declares Vendomat revision `bd26fea8a2124bb4b1bbd8721418d831b4c2bf13`; its `devenv.nix` enables `vendor.toolchain`. | Preserve its declared pin until a new-pin transition passes. The host manifest overrode it during the successful E2E run, so input fallback remains unproved. |
| Real consumer fixture | `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` passed the real store-consumer checks. Commands `repoman`, `copyroom`, and `agentman` resolved in the selected toolchain store path; supported version probes reported RepoMan `0.7.5` and CopyRoom `0.7.7`. | Preserve. E2E result proves the current host-manifest path, not the absent-manifest fallback. |

All 21 active central overlays remain on their current path. No current consumer was cut over.
Their `devenv.lock` transition fixtures on the proposed module revision remain a gap.

## Host, storage, and service inventory

| Area | Observation | Requirement result |
| --- | --- | --- |
| Publisher | `server` is a reachable x86_64 Nix build host candidate. No owner decision selected it as the desktop publisher. | Gap: `V4-OWN-009`. |
| Cold laptop | Tailnet peers include `framework` (Linux), `tower` (Windows), `samsung-book` (Windows), and offline `pinix` (Linux). None is confirmed as a cold Linux Nix consumer. `ssh -o BatchMode=yes -o ConnectTimeout=5 andrew@100.64.36.58 true` timed out; root SSH to `server` returned `Permission denied (publickey)`. Logs: `ssh-framework.log`, `ssh-server-root.log`. | Gap: `V4-OWN-009`, `V4-MACH-001`. |
| Attic | `attic --version` exited 127 because the client is absent; `systemctl is-active atticd.service` exited 4 with `inactive`; no Attic endpoint or credentials were configured. Logs: `attic-client.log`, `attic-service.log`. | Gap: `V4-OWN-009`, `V4-REC-009`. |
| Existing backup | Restic uses `/mnt/wd_green1/restic` on a locally mounted ext4 disk. The latest success marker was `2026-10-06T02:35:25-04:00`. This is same-host storage, not an off-host backup or a tested restore. | Gap: `V4-OWN-009`, `V4-REC-009`. |
| Durable state owners | No owner and restore destination are named for retained source, evidence and receipts, Attic objects and signing state, or application data. | Gap: `V4-REC-009`. |
| Native fallback | `nix show-config | rg '^(substituters|fallback|require-sigs) ='` reports `https://cache.nixos.org/ https://devenv.cachix.org`, `fallback=false`, and `require-sigs=true`. No Attic cache or cold-client fallback behavior was exercised. Log: `nix-cache-policy.log`. | Gap: `V4-OWN-009`. |
| First proof project and review module | No project owner or review-module repository was selected. `loci.nvim` is an active plugin consumer, but it has not been approved or proven as the V4 review application. | Gap: P0 selection. |

## Fixtures and results

### Machines pin and plan fixture

Fixture input files are `tests/fixtures/v4-p0-machines/devenv.yaml`, `devenv.nix`, and
`devenv.lock`. The module defines `v4P0` as a remote NixOS target and `v4P0User` as a local Home
Manager target. Commands in this section ran from `tests/fixtures/v4-p0-machines/`, except the
root module update, which ran from the repository root.

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| `devenv --no-tui update` | Resolve the fixture's declared native inputs into a lock. | Passed, exit 0. Lock records `devenv` module `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`, Nixpkgs `c2f38fe7f9e04d9aadd354d380f2bd40531d9737`, and Disko `725ea35e410ad83be4931d1bff7e090eacaf3563`. Log: `machines-input-update.log`. |
| `devenv --no-tui update home-manager` | Resolve the declared Home Manager input. | Passed, exit 0. Lock records Home Manager `fae6e9e42c3b762ab47635cddcfaf6f52374a61b`. Log: `home-manager-input-update.log`. |
| `devenv --no-tui update devenv` | Pin the repository's module source to the tested Machines revision. | Passed, exit 0. Root `devenv.lock` now selects module `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`, matching the fixture. Log: `devenv-module-update.log`. |
| `devenv --no-tui machines info` | List the declared machine targets and their systems. | Passed, exit 0. Output lists `v4P0` as `x86_64-linux`, target `root@v4-p0.invalid`, role `nixos`. It does not list local target `v4P0User`; the separate plan below proves that target. Log: `machines-info.log`. |
| `devenv --no-tui machines plan v4P0User` | Create a native local plan without activation. | Passed, exit 0. Plan `plan-LZ3GfpJgBO4WdYP5seGIwY3X` selected `/nix/store/2aaad3q3k6c470k69s0l8hkfcmnljkpa-devenv-home-manager-generation`; the native output says direct activation has no automatic rollback. Log: `machines-user-plan.log`; copied plan JSON: `home-manager-plan.json` in the preserved proof directory. |
| `devenv --no-tui machines plan v4P0` | Observe the target and create a native plan. | Gap, exit 1. Native SSH to `root@v4-p0.invalid` exited 255, so Machines could not observe target state. Log: `machines-plan.log`. This is not a passing NixOS plan. |
| `ssh -o BatchMode=yes -o ConnectTimeout=5 root@server true` | Confirm access to a real NixOS plan target. | Failed with public-key authentication. No target was modified. Log: `ssh-server-root.log`. |

This proves a local Home Manager Machines plan under the recorded CLI and module revisions. It
does not prove remote NixOS planning, activation, or consumer migration. `V4-MACH-001` is therefore
partial, not passed.

### Current consumer checks

| Command or fixture | Expected result | Actual result and artifact |
| --- | --- | --- |
| `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` | Pass the real consumer integration fixture without changing consumer selection. | Passed. The system manifest supplied the effective module, overriding the fixture's flake input. Logs: `testee-e2e-quick.log` (baseline), `testee-e2e-quick-final.log` (final). |
| Rootless user and mount namespace with the host manifest masked; then evaluate the store consumer | With no manifest, the declared Vendomat flake input supplies the module and toolchain. | Gap. The isolated run failed while opening SSH configuration and fetching the private `agentman` source, locked at tag `v0.0.3`, revision `601e10f84aa6b098f91228e9bbcf1398fa13ec84`. It did not establish whether the input fallback works. Log: `input-fallback.log`; the complete command was not retained in its header. |
| `devenv shell` in `loci-core` and `repoman` | Exercise one installed-module and one local-checkout overlay. | Both passed on the current host. Logs: `loci-core-installed-module.log`, `repoman-checkout-module.log`. These runs did not transition those consumers' native locks. |

The exploratory unsupported command `agentman --version` exited 3. This is not an integration
failure; the corrected path-resolution check passed and its record is `store-consumer-paths.log`.

### Repository gates

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| `devenv shell -- testee verify --mode quick` | Normal repository gate passes. | Passed, exit 0, 19.1 seconds. Ruff, Ruff-format, ty, and pytest passed. Log: `testee-quick-proof-final.log`; Testee report: `.testee/runs/2026-10-06T18-43-32Z-99bf30/testee-report.json`. |
| `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` | Existing real consumer integration passes. | Passed, exit 0, 22.7 seconds. Ruff, Ruff-format, ty, and pytest passed. Log: `testee-e2e-quick-final.log`; Testee report: `.testee/runs/2026-10-06T18-39-56Z-939be9/testee-report.json`. |
| `devenv shell -- nix build .#repoman-toolchain-core --no-link --print-out-paths` | Relevant shared toolchain build passes. | Passed, exit 0; output `/nix/store/iilwbhx0zmrzc33wm4vr1x2ib5f3f60a-repoman-toolchain-core`. Log: `repoman-toolchain-build.log`. |

## Requirement mapping and gate

| Requirement | Result | Evidence or missing proof |
| --- | --- | --- |
| `V4-OWN-009` | Gap | Publisher, cold laptop, endpoint access, durable-state owners, restore locations, and cold-client cache behavior are not established. |
| `V4-OWN-012` | Partial | All four delivery paths are inventoried and marked preserve. The current consumer locks have not passed before-and-after transition fixtures; no path is retired or migrated. |
| `V4-MACH-001` | Partial | CLI and matching module revisions are pinned. `machines info` and the local Home Manager plan pass; remote NixOS observation and current-consumer transition remain gaps. |
| `V4-REC-009` | Gap | Durable source, evidence, Attic, and application state have no named storage and backup owners or restore targets. The local Restic repository is not an off-host proof. |

**P0 gate: not passed.** Do not start P1. Continue only after an owner names the publisher, cold
laptop, first-proof project, review-module repository, Attic endpoint, native fallback policy,
durable-state owners and restore locations, and a reachable NixOS target. Then run the new pin
against every current delivery path before any cutover. Existing paths remain in service.

## Preserved logs

The dated directory above contains raw output for host and tool versions, cache policy, Attic and
SSH availability, fixture input updates, Machines info and both plan outcomes, the copied native
Home Manager plan, installed and checkout overlays, consumer command paths, input fallback
attempt, both Testee runs, and the toolchain build. Large and local-only logs are not checked into
the repository. Testee reports are under the local `.testee/runs/` directory and are ignored by
Gitman.

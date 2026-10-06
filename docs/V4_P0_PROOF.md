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
| Flake-input consumer | `tests/fixtures/store-consumer/devenv.yaml` declares Vendomat revision `bd26fea8a2124bb4b1bbd8721418d831b4c2bf13`; its `devenv.nix` enables `vendor.toolchain`. | Preserve its declared pin until a new-pin transition passes. The host-manifest path and, in the separate masked-manifest fixture below, the declared input path both pass. |
| Real consumer fixture | `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` passed the real store-consumer checks. Commands `repoman`, `copyroom`, and `agentman` resolved in the selected toolchain store path; supported version probes reported RepoMan `0.7.5` and CopyRoom `0.7.7`. | Preserve. E2E result proves the current host-manifest path, not the absent-manifest fallback. |

All 21 active central overlays remain on their current path. No current consumer was cut over.
Their `devenv.lock` transition fixtures on the proposed module revision remain a gap.

## Host, storage, and service inventory

| Area | Observation | Requirement result |
| --- | --- | --- |
| Publisher and cold laptop | The user selected `framework` for the publisher/cold-machine question. The answer did not assign the two roles separately. Tailscale reports `framework` online as Linux at `100.64.36.58`; `tailscale ping --c=1 framework` passed directly in 4 ms. `timeout 12s tailscale ssh andrew@framework ...` timed out with exit 124. Host versions and Nix access remain unknown. `pinix` is Linux but offline, last seen 242 days ago. No separate cold client is confirmed. Logs: `framework-reachability.log`, `tailscale-hosts.log`, `ssh-framework.log`. | Gap: `V4-OWN-009`, `V4-MACH-001`. |
| Attic | The user selected `server`. The service builds for `https://server.tail770f47.ts.net/attic`. Later on 2026-10-06, `atticd.service` ran from 16:19 (status 0), with the `/attic` route and port 8089 present; the 14:40 logs predate this. No Attic cache or client token exists. | Partial evidence; runtime and cold-client gaps remain: `V4-OWN-009`, `V4-REC-009`. |
| Existing backup | Restic uses `/mnt/wd_green1/restic` on `/dev/sdb1`, the same ext4 disk proposed for Attic data. Its source paths omit `/mnt/wd_green1/attic`. The latest success marker was `2026-10-06T02:35:25-04:00`. The host also has `/mnt/shared` on `/dev/sda2`, a separate local disk, but no off-host mount was found. Owner note, 2026-10-06: GitHub holds a secondary copy of the owner's local repositories (`D-REPO-BACKUP`). That copy is outside Vendomat. No independent restore is proven. Log: `attic-storage-devices.log`. | Gap: `V4-OWN-009`, `V4-REC-009`. |
| Durable state owners | Candidate Attic objects and its SQLite database live at `/mnt/wd_green1/attic`, owned by service account `atticd`. The SOPS store owns the encrypted server signing key. Attic objects are not backed up; selected source rebuilds them. Off-host copies of Vendomat state remain open. Pipeline scope per state class, and owners for retained source, evidence, and application data, remain open. | Gap: `V4-REC-009`. |
| Native fallback | `nix show-config | rg '^(substituters|fallback|require-sigs) ='` reports `https://cache.nixos.org/ https://devenv.cachix.org`, `fallback=false`, and `require-sigs=true`. No Attic cache or cold-client fallback behavior was exercised. Log: `nix-cache-policy.log`. | Gap: `V4-OWN-009`. |
| First proof project and review module | The user delegated the choice. Select `loci.nvim` as the first proof consumer at main revision `f0cca7c2e90a8a917fc52dc7bbcac3c6843805f0`. Its lock selects `loci-core` revision `4be325043194898b5a1ab8045ac84b75226e8744` and Nixpkgs revision `567a49d1913ce81ac6e9582e3553dd90a955875f`. Select `nix-nvim` as the review-module repository because it owns the existing Home Manager module and configured Neovim launcher. Its main revision is `edac5777c3f26940516d11628ede2d9efce2edce`; its flake lock selects Home Manager `5d320ab301cfaaca7d32514f13815d19d109f5f4`, `loci.nvim` `133dad16d062b6ff3a8218b26544d52e147c3315`, Nixpkgs `e73de5be04e0eff4190a1432b946d469c794e7b4`, and `nixpkgs-neovim` `d233902339c02a9c334e7e593de68855ad26c4cb`. `loci.nvim` exports packages, not option modules. The `nix-nvim` checkout has an active conflicted `stray-devenv` lane; `devenv shell -- gitman status` fails because conflict markers make `devenv.yaml` invalid. Do not change that lane. Logs: `loci-nvim-selection-status.log`, `nix-nvim-gitman-status.log`. | Selection recorded. The module fixture remains blocked until the active conflict is resolved safely. |

### Attic host selection and candidate build

The user selected `server` as the Attic host on 2026-10-06. The host runs NixOS 26.11,
kernel 6.18.38, Nix 2.34.7, devenv 2.4.0, and Tailscale 1.98.8. Its root filesystem has
13 GiB free at 98% use. `/mnt/wd_green1` is ext4, UUID
`21488349-01cb-4efe-9d21-a72f74a908e0`, with 1.7 TiB free.

The candidate uses the native NixOS `services.atticd` module from Nixpkgs revision
`256551e45f6303e142ab4a98be1bf243feb77dc0`. It selects `attic-server`
`0-unstable-2026-06-26`, listens on `127.0.0.1:8089`, and stores objects and SQLite data
under `/mnt/wd_green1/attic`. A root setup unit creates that directory after the disk mounts.
Attic runs as `atticd:atticd` and requires the mount. A Tailscale Serve unit adds `/attic`
on the existing HTTPS port 443. It removes only that route when stopped. The design follows
the [Attic local-storage tutorial](https://docs.attic.rs/tutorial.html) and the
[Tailscale Serve path interface](https://tailscale.com/docs/reference/tailscale-cli/serve).
A read-only port check found no listener on 8089. The storage directory was absent before
activation.

The `nix-secrets` input now selects tag `v0.1.4`, revision
`2d11ef47ba0c99f31a48af325e5b56d860f4a5da`. Its encrypted SOPS file contains the new
`attic-signing-key`. The host's derived age recipient matches `.sops.yaml`. The NixOS service
reads a rendered file under `/run/secrets`; the key does not enter the Nix store. Activation
has not tested decryption on this host.

The current Restic repository is also under `/mnt/wd_green1`. Its source paths omit the
proposed Attic directory. This repository shares the same disk and does not protect against
disk or host loss. It is a local copy only, not an off-host copy.

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| `ssh-to-age < /etc/ssh/ssh_host_ed25519_key.pub` | Match the server recipient in the encrypted store. | Passed. Output matched the `.sops.yaml` `tower` recipient. This proves public-key mapping, not runtime decryption. Log: `attic-host-age-recipient.log`. |
| `nix eval --json .#nixosConfigurations.server.config.services.atticd --apply 'x: { enable = x.enable; package = x.package.name; settings = x.settings; environmentFile = toString x.environmentFile; }'` | Evaluate the native server module and selected settings. | Passed. It selected loopback `127.0.0.1:8089`, local storage and SQLite under `/mnt/wd_green1/attic`, package `attic-0-unstable-2026-06-26`, and `/run/secrets/rendered/atticd.env`. Log: `attic-host-config-eval.log`. |
| `nix build .#nixosConfigurations.server.config.system.build.toplevel --no-link --print-out-paths` | Build the candidate generation and checked Attic config. | Passed, exit 0. Output `/nix/store/fmzw79hv8s04mzzd1b2midw7lqb73z7y-nixos-system-server-26.11.20260705.d407951`. Log: `nix-meta-server-build.log`. |
| `nix flake check` | Run the nix-meta flake check. | Passed, exit 0. The flake reported all checks passed. Log: `nix-meta-flake-check.log`. |
| `ss -H -ltn 'sport = :8089'` | Confirm the candidate loopback port is unused before activation. | Passed, exit 0; no listener was listed. The Attic storage directory was absent. Log: `attic-host-port-storage-check.log`. |
| `tailscale serve status --json` | Before activation, only current routes remain. | Passed. Port 443 has `/atuin` and `/notes`; `/attic` is absent. Log: `attic-host-serve-before.json`. |
| `systemctl show atticd.service -p LoadState -p ActiveState -p SubState` | Check whether the candidate service is active on the host. | `LoadState=not-found`, `ActiveState=inactive`, `SubState=dead`. The candidate generation is not active. Log: `attic-host-runtime-before.log`. |
| `ssh -oBatchMode=yes -oConnectTimeout=5 andrew@server true` | Confirm a real NixOS target accepts the available user key. | Failed: `Permission denied (publickey)`. No target was modified. Log: `ssh-server-user-hostname.log`. |
| `sudo -n true` | Check whether this session can activate the generation. | Failed, exit 1: `sudo: a password is required`. No activation or live Attic request ran. Log: `attic-host-runtime-before.log`. |

The candidate config is committed and pushed in nix-meta revision
`b757f494928ec61eb7d3b7a935f3c86ba85baa5c`. The secret tag is pushed; its value remains
encrypted. To run the runtime fixture, an operator with local root access must run
`sudo nixos-rebuild switch --flake /home/andrew/Documents/Projects/nix-meta#server`, then
check `atticd.service`, the `/attic` Tailscale route, and a real Attic client request.
The service and route have not passed those checks.

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

### Host, storage, and project selection fixture

The selected application project is `loci.nvim` at main revision
`f0cca7c2e90a8a917fc52dc7bbcac3c6843805f0`. Its `flake.lock` selects `loci-core`
`4be325043194898b5a1ab8045ac84b75226e8744` and Nixpkgs
`567a49d1913ce81ac6e9582e3553dd90a955875f`. The selected review-module repository is
`nix-nvim`, at main revision `edac5777c3f26940516d11628ede2d9efce2edce`. It owns the existing
Home Manager module and configured Neovim launcher. Its flake selects Home Manager
`5d320ab301cfaaca7d32514f13815d19d109f5f4`, `loci.nvim`
`133dad16d062b6ff3a8218b26544d52e147c3315`, Nixpkgs
`e73de5be04e0eff4190a1432b946d469c794e7b4`, and `nixpkgs-neovim`
`d233902339c02a9c334e7e593de68855ad26c4cb`. These are candidate input revisions, not V4
selection overrides.

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| `tailscale status` | Identify the selected publisher and an available cold Linux client. | `framework` is online Linux; `pinix` is offline, last seen 242 days ago. The user selected `framework`, but the response did not distinguish publisher from cold-client role. Log: `tailscale-hosts.log`. |
| `tailscale ping --c=1 framework` | Reach the selected Linux host over its intended private endpoint. | Passed, direct peer `192.168.68.123:41641`, 3 ms in the preserved run. This proves Tailscale reachability only. Log: `framework-reachability.log`. |
| `timeout 12s tailscale ssh andrew@framework 'uname -a; nix --version; devenv --version; hostnamectl --static'` | Read host and tool versions without changing the host. | Timed out, exit 124, with no shell output. Versions and cold-client access remain unproved. Log: `framework-reachability.log`. |
| `findmnt -T /mnt/wd_green1/restic -o TARGET,SOURCE,FSTYPE,OPTIONS` | Identify the current Restic repository's filesystem. | Passed. `/mnt/wd_green1` is `/dev/sdb1`, ext4. Log: `attic-storage-devices.log`. |
| `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL` | Inventory local disks and mounts relevant to backup placement. | Passed. `/mnt/shared` is `/dev/sda2`, a separate local NTFS disk on the same server. It is not an off-host destination. Log: `attic-storage-devices.log`. |
| `findmnt -t nfs,nfs4,cifs,sshfs -o TARGET,SOURCE,FSTYPE` | Find a mounted off-host backup target. | Passed with no matching mounts. No mounted off-host target is available. Log: `attic-storage-devices.log`. |
| `devenv shell -- gitman status` in `loci.nvim` | Confirm the selected first-proof base and preserve active work. | Passed. Main is `f0cca7c2e90a8a917fc52dc7bbcac3c6843805f0`, in sync with origin. The first status also reported an unbookmarked `devenv.lock`; the later recorded status did not. No changes were made in that repository. Log: `loci-nvim-selection-status.log`. |
| `gitman status` in `nix-nvim` | Confirm the review-module base and detect active work before edits. | Main is `edac5777c3f26940516d11628ede2d9efce2edce`, in sync with origin. A `stray-devenv` lane has one conflicted change. Log: `nix-nvim-gitman-status.log`. |
| `devenv shell -- gitman status` in `nix-nvim` | Run Gitman in its required project environment. | Failed, exit 1. Devenv cannot parse conflict markers in `devenv.yaml` at line 12. No lane was changed. Log: `nix-nvim-gitman-status.log`. |

### Current consumer checks

| Command or fixture | Expected result | Actual result and artifact |
| --- | --- | --- |
| `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` | Pass the real consumer integration fixture without changing consumer selection. | Passed. The system manifest supplied the effective module, overriding the fixture's flake input. Logs: `testee-e2e-quick.log` (baseline), `testee-e2e-quick-final.log` (final). |
| Rootless user and mount namespace with the host manifest masked; then evaluate the store consumer | With no manifest, the declared Vendomat flake input supplies the module and toolchain. | Gap. The isolated run failed while opening SSH configuration and fetching the private `agentman` source, locked at tag `v0.0.3`, revision `601e10f84aa6b098f91228e9bbcf1398fa13ec84`. It did not establish whether the input fallback works. Log: `input-fallback.log`; the complete command was not retained in its header. |
| `devenv shell` in `loci-core` and `repoman` | Exercise one installed-module and one local-checkout overlay. | Both passed on the current host. Logs: `loci-core-installed-module.log`, `repoman-checkout-module.log`. These runs did not transition those consumers' native locks. |

The exploratory unsupported command `agentman --version` exited 3. This is not an integration
failure; the corrected path-resolution check passed and its record is `store-consumer-paths.log`.

#### Declared Vendomat input fallback

The consumer fixture inputs are `tests/fixtures/store-consumer/devenv.yaml`, `devenv.nix`, and
`devenv.lock`. The lock selects Vendomat `bd26fea8a2124bb4b1bbd8721418d831b4c2bf13`, Nixpkgs
`c2f38fe7f9e04d9aadd354d380f2bd40531d9737`, and RepoMan
`7c5b79b995e1942a78dbce8b8677969d3ef11233`. Copies of those three files are in the preserved
proof directory.

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| Original rootless masked-manifest attempt, preserved as `input-fallback.log` | With the system manifest absent, evaluate the input-delivered module. | Failed before the module result. OpenSSH rejected a systemd SSH config include in the namespace, then the private `agentman` fetch failed. This did not disprove fallback behavior. |
| `run-input-fallback-e2e.sh` | Mask `machine.json`, use the declared Vendomat input, and pass the real consumer E2E check. | Passed, exit 0. Testee quick completed in 54.0 seconds; all 181 pytest cases passed, including the three opt-in consumer-shell checks. Log: `input-fallback-e2e-retry.log`. Harness: `/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/p0/run-input-fallback-e2e.sh`. Testee and pytest reports: `input-fallback-testee-report.json`, `input-fallback-pytest.json`. |
| `run-input-fallback-resolution.sh` | Print the command paths and versions from the consumer shell while `machine.json` is absent. | Passed. `repoman`, `copyroom`, and `agentman` resolved under `/nix/store/iilwbhx0zmrzc33wm4vr1x2ib5f3f60a-repoman-toolchain-core/bin`; RepoMan reported `0.7.5`, CopyRoom `0.7.7`. Log: `input-fallback-resolution.log`. Harness: `/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/p0/run-input-fallback-resolution.sh`. |

This proves the current declared Vendomat input pin without the host manifest. It does not prove
the proposed V4 module transition or the 21 active overlay transitions.

### Repository gates

| Command | Expected result | Actual result and artifact |
| --- | --- | --- |
| `devenv shell -- testee verify --mode quick` | Normal repository gate passes. | Passed, exit 0, 38.5 seconds after the fallback evidence update. Ruff, Ruff-format, ty, and pytest passed. Testee report: `.testee/runs/2026-10-06T20-25-37Z-20baa9/testee-report.json`; preserved copy: `testee-quick-after-fallback-doc-report.json`. Log: `testee-quick-after-fallback-doc.log`. |
| `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` | Existing real consumer integration passes. | Passed, exit 0, 22.7 seconds. Ruff, Ruff-format, ty, and pytest passed. Log: `testee-e2e-quick-final.log`; Testee report: `.testee/runs/2026-10-06T18-39-56Z-939be9/testee-report.json`. |
| `devenv shell -- nix build .#repoman-toolchain-core --no-link --print-out-paths` | Relevant shared toolchain build passes. | Passed, exit 0; output `/nix/store/iilwbhx0zmrzc33wm4vr1x2ib5f3f60a-repoman-toolchain-core`. Log: `repoman-toolchain-build.log`. |

## Requirement mapping and gate

| Requirement | Result | Evidence or missing proof |
| --- | --- | --- |
| `V4-OWN-009` | Gap | Attic host and candidate URL are selected, but the endpoint is inactive. `framework` was selected for the publisher/cold-machine question, but its roles and versions remain unproved. No Attic fallback policy has been exercised. |
| `V4-OWN-012` | Partial | All four delivery paths are inventoried and marked preserve. The current host-manifest and declared-input consumer fixtures pass. Before-and-after tests for the proposed V4 pin and the 21 active overlays remain gaps; no path is retired or migrated. |
| `V4-MACH-001` | Partial | CLI and matching module revisions are pinned. `machines info` and the local Home Manager plan pass; remote NixOS observation and current-consumer transition remain gaps. |
| `V4-REC-009` | Gap | Attic storage and service account are named. Selected source rebuilds Attic objects. Off-host copy routes for Vendomat state remain open. The same-disk Restic repository omits Attic data. `/mnt/shared` is another local disk, not an off-host copy. Pipeline scope and source, evidence, and application owners remain open. |

**P0 gate: not passed.** Do not start P1. The declared input fallback now passes, but it uses the
current Vendomat pin. The Attic service runs since 16:19 on 2026-10-06, but no cache or client
test exists. Off-host copy routes for Vendomat state remain open. `loci.nvim` and `nix-nvim` are selected for the first proof, but the latter has an active
conflict and cannot enter its devenv shell. P0 also needs distinct publisher and cold-client roles,
framework access, native fallback policy, the Attic runtime fixture, a reachable NixOS target, and
before-and-after tests for the proposed module pin. Resolve the module repository's active conflict
through its owner before editing it. Activate and test Attic with local root access. Existing
consumer paths remain in service until their replacements pass.

## Preserved logs

The dated directory above contains raw output for host and tool versions, cache policy, Attic and
SSH availability, fixture input updates, Machines info and both plan outcomes, the copied native
Home Manager plan, installed and checkout overlays, consumer command paths, input fallback
attempt, both Testee runs, the toolchain build, candidate Attic host evaluation and build, Tailscale
host discovery, framework reachability, repository selections, Gitman state, disk inventory, the
latest quick-gate report, and the masked-manifest E2E plus command-path proofs.
Large and local-only logs are not checked into the repository. Testee reports are under the
local `.testee/runs/` directory and are ignored by Gitman.

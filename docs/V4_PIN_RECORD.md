# Vendomat V4 pin record

**Date:** 2026-10-06. **Status:** Record. **Gate:** None. No V4 phase has passed.

This record satisfies `V4-OWN-009` and `V4-REC-009` as records. It does not pass a gate.
The [implementation guide](V4_IMPLEMENTATION_GUIDE.md) defines this record.

**Raw logs:** `/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/baseline/`. The file names in
this record refer to that directory. Earlier evidence: [V4_P0_PROOF.md](V4_P0_PROOF.md) and
`/home/andrew/.local/state/vendomat/v4-proof/2026-10-06/p0/`.

## 1. Tool versions

| Item | Observed value | Command and log |
| --- | --- | --- |
| Nix | `2.34.7` | `nix --version`; `versions-nix.txt` |
| devenv executable | `2.4.0+b904dcb` (x86_64-linux) | `devenv --version`; `versions-devenv.txt` |
| Host OS and kernel | NixOS 26.11, build `26.11.20260705.d407951`; Linux `6.18.38` | `uname -a`; `host-uname.txt`. `/etc/os-release` in `host-os.log` |
| devenv module (Machines pin) | `cachix/devenv`, `src/modules`, `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4` | `repo-devenv-lock.log`, repository `devenv.lock` |
| Nixpkgs (repository devenv input) | `cachix/devenv-nixpkgs`, `256551e45f6303e142ab4a98be1bf243feb77dc0` | `repo-devenv-lock.log` |
| Nixpkgs (P0 Machines fixture) | `cachix/devenv-nixpkgs`, `c2f38fe7f9e04d9aadd354d380f2bd40531d9737` | `fixture-locks.log` |
| Home Manager (P0 fixture only) | `nix-community/home-manager`, `fae6e9e42c3b762ab47635cddcfaf6f52374a61b` | `fixture-locks.log`. Host Home Manager version not observed |
| Disko (P0 fixture only) | `nix-community/disko`, `725ea35e410ad83be4931d1bff7e090eacaf3563` | `fixture-locks.log` |
| Attic server | `attic-0-unstable-2026-06-26` | `systemctl show atticd.service -p ExecStart`; `attic-server-unit-and-root.log`. Binaries: `atticd`, `atticadm` (`attic-server-bin-listing.log`) |
| Attic client | Not installed. `command -v attic` exits 1 | `attic-client.log` |

## 2. Target systems and hosts

| Role | Host | Observed state | Status |
| --- | --- | --- | --- |
| Publisher | `server` (x86_64-linux) | `hostname` returns `server`. `nix show-config` reports `system = x86_64-linux`. Build commands run here. | Owner has not confirmed the role. P0 did not separate roles. Blocker BLK-P5-05 |
| Cold consumer | `framework` (Tailscale, Linux) | Ping passes in 4 ms, direct path. SSH timed out with exit 124 in two runs. Nix and devenv versions not observed. | Blocker BLK-P5-04. Logs: `framework-reachability-baseline.log`, `tailscale-status.log` |
| NixOS target (Machines) | None reachable | Fixture target `root@v4-p0.invalid` does not resolve (P0 `machines-plan.log`). `andrew@server` and `root@server` refuse public-key login. `sudo -n` fails. | Blocker BLK-P7-01 and BLK-P7-02. Logs: `final-host-checks.log`, P0 `ssh-server-root.log` |
| Target systems for consumers | x86_64-linux | Only x86_64-linux observed. Extra platforms are x86_64 level variants. | Other systems are not claimed |

## 3. Attic endpoint

| Item | Observed value | Log |
| --- | --- | --- |
| Service | `atticd.service` active since 2026-10-06 20:30:54 EDT, as user `atticd` | `attic-service-state.log` |
| Local listener | `127.0.0.1:8089` | `attic-service-state.log` |
| Public route | `https://server.tail770f47.ts.net/attic`, Tailscale Serve, tailnet only, proxies to `127.0.0.1:8089` | `tailscale-serve-status.log` |
| Root response | HTTP 200 on the local port and on the public route | `attic-http-get.log` |
| Cache | None observed. `GET /nix-cache-info` without a cache name returns HTTP 404 | `attic-http-get.log` |
| Tokens | None created. `~/.config/attic` is absent | `attic-client.log` |
| Storage | `/mnt/wd_green1/attic`, owner `atticd`. Disk is ext4, UUID `21488349-01cb-4efe-9d21-a72f74a908e0`, now device `sda1` (P0 recorded `sdb1`; the UUID matches). Database `server.db` in the same directory | `attic-server-config.log`, `final-host-checks.log` |
| Signing key | Rendered at `/run/secrets/attic-signing-key` (root-only). Content not read | `final-host-checks.log` |
| Request logs | The last 60 journal lines show startup and stop only. No client request line appears | `attic-journal-tail.log` |

No client request is recorded as successful. The server journal cannot prove or disprove one.

## 4. Durable state classes

Vendomat owns exactly two classes: receipts with logs, and garbage-collection roots. Each other class
has a native owner.

| Class | Owner | Current location | Off-host copy | Restore route | Blocker |
| --- | --- | --- | --- | --- | --- |
| Retained source (store paths of locked inputs) | Nix store on the publisher. Attic holds the source cache copy | `/nix/store` on the btrfs volume `nvme1n1p3`. Nothing archived yet | None | Restore store paths from a backup, or run `nix flake archive` again from the lock. Neither is proved | BLK-P3-01, BLK-P6-01, BLK-P6-02 |
| Identity records of retained inputs | Vendomat. The records fall under the receipts class. Placement is not fixed by a fixture | Not created | None | Derive again from `nix flake metadata --json` and the lock. Not proved | BLK-P3-01 |
| Receipts and their logs | Vendomat | Not created. Raw baseline logs sit under the baseline directory | None | Restore from backup. Not proved | BLK-P6-01, BLK-P6-02 |
| Garbage-collection roots | Vendomat | No Vendomat root exists yet. Native plan links were observed in `fixtures/machines-hm` (MACH-003) | None | Recreate with `retain` from the identity records. Not proved | BLK-P3-01, BLK-P6-02 |
| Attic objects and database | NixOS and Attic | `/mnt/wd_green1/attic` | None. Not backed up by design (P0 and guide P6) | Rebuild from retained source (guide P6, step 3) | BLK-P6-02 |
| Attic server signing key | NixOS, through SOPS (`nix-secrets` tag `v0.1.4`) | `/run/secrets/attic-signing-key`. Encrypted copy in the `nix-secrets` repository | Encrypted copy in git only (GitHub is a secondary copy, outside Vendomat) | Decrypt on the host. Decryption on the host is not tested by restore | BLK-P6-03 |
| Attic push and pull tokens | NixOS and Attic | None created | None | Make with `atticadm make-token`. Make the pull token with `--pull` only. Not proved | BLK-P5-02 |
| Application data | The application | Not defined | None | Not defined | BLK-P7-04 |
| NixOS and Home Manager generations | NixOS and Home Manager | Profiles in the Nix store and user state | None | Native rollback for NixOS only. Home Manager has no automatic rollback (V4-SPEC §10) | BLK-P7-03 |
| Local restic repository | Host | `/mnt/wd_green1/restic`, on the same disk as Attic (`sda1` now). Its source paths omit `/mnt/wd_green1/attic` (P0) | None. Same disk as Attic | Not tested | BLK-P6-01 |

Source and binaries share one cache. They therefore share one loss domain (`V4-REC-009`).
No off-host mount exists (`findmnt -t nfs,nfs4,cifs,sshfs` returns no rows, `final-host-checks.log`).
`/mnt/shared` is a local NTFS disk on `sdb2`. It is not off-host.

## 5. Native cache fallback policy

**Declared order** (V4-SPEC §8): existing local output, then Attic, then configured public caches,
then a permitted local build. Set it with native Nix settings.

**Current host settings** (`nix-show-config-cache.log`):

| Setting | Value |
| --- | --- |
| `substituters` | `https://cache.nixos.org/ https://devenv.cachix.org` |
| `trusted-public-keys` | `cache.nixos.org-1` and `devenv.cachix.org-1` only. No Attic key |
| `fallback` | `false` |
| `require-sigs` | `true` |
| Trusted users | `root andrew`. `nix store info` reports `Trusted: 1` |

No Attic substituter is configured. The declared order is therefore not in effect.

**Observed priority rule** (`V4-CACHE-010.log`). Nix tries the substituter with the lower priority value first.
The public default is 40. The Attic default is 41. Without a change, the public cache is tried before Attic.
The declared order needs an Attic priority below 40. P5 must set it and test it. Blocker BLK-P5-06.

**Observed fallback rule** (`V4-CACHE-011.log`). With every substituter unreachable, the build ran under
`fallback=false`. A local build therefore ran in that case. The case where a substituter fails during
transfer is not yet tested. Blocker BLK-P5-07.

**Observed signature rule** (`V4-CACHE-012.log`). Nix accepts a path signed by a trusted key. It rejects a path
signed by another key. It accepts that path when `require-sigs` is false. The Attic key is not trusted yet.
Blocker BLK-P5-06.

**Owner decision.** Decide whether a consumer may build locally when Attic is unavailable. This sets `fallback`
and the last step of the order. Blocker BLK-P5-05.

## 6. Phase entry and blockers

A blocker names one missing item, its phase, and its evidence. A missing host blocks only the phase that needs it.

### Phase entry status

| Phase | Entry condition | Status |
| --- | --- | --- |
| P1 | devenv and Nix | Met. Versions observed in section 1 |
| P2 | devenv and Nix | Met. BLK-P2-01 cleared 2026-10-06 |
| P3 | P2 passed, and a writable store | P2 not passed. The store accepts writes through the daemon (`nix store info`). Direct writes are denied (`V4-SRC-012.log`) |
| P4 | P3 passed | Not met |
| P5 | P4 passed; Attic with push and pull tokens; cold machine with an empty store | Not met. Blockers BLK-P5-01 to BLK-P5-07 |
| P6 | P5 passed | Not met. Blockers BLK-P6-01 to BLK-P6-03 |
| P7 | NixOS target and Machines pin | Partly met. The Machines pin ran a Home Manager plan (`V4-MACH-003.log`). No NixOS target. Blockers BLK-P7-01 to BLK-P7-04 |

### Blockers

| ID | Phase | Missing item | Evidence |
| --- | --- | --- | --- |
| BLK-P2-01 | P2 | Cleared 2026-10-06. Owner approved raw git for a throwaway fixture. `V4-MOD-013` observed in `NATIVE-BASELINE.md` | `V4-MOD-013-run.log`, `V4-MOD-013-lock-nodes.txt` |
| BLK-P3-01 | P3 | No retained source, identity record, or Vendomat root yet. Depends on P2 | This record, section 4 |
| BLK-P5-01 | P5 | No Attic cache. A cache name is required before any check | `attic-http-get.log` |
| BLK-P5-02 | P5 | No push token and no pull token | `attic-client.log` |
| BLK-P5-03 | P5 | No Attic client on the publisher. Attic client flags and upload checks cannot run | `attic-client.log`, `attic-server-bin-listing.log` |
| BLK-P5-04 | P5 | No confirmed cold machine with an empty store. `framework` SSH timed out. Its Nix and devenv versions are unknown | `framework-reachability-baseline.log` |
| BLK-P5-05 | P5 | Owner decisions: publisher role, and local build when Attic is unavailable | P0 `framework` answer; section 5 |
| BLK-P5-06 | P5 | No Attic public key in `trusted-public-keys`. No Attic priority below 40 | `nix-show-config-cache.log`, `V4-CACHE-010.log` |
| BLK-P5-07 | P5 | Attic-side traces pending: the upload denial, the closure query, the mid-transfer fallback, and the signing check | `NATIVE-BASELINE.md` observation record |
| BLK-P6-01 | P6 | No off-host copy of any durable state class | `final-host-checks.log` |
| BLK-P6-02 | P6 | No restore route tested for source, receipts, or GC roots | This record, section 4 |
| BLK-P6-03 | P6 | Attic signing state restore not tested. The rendered key file exists on the server | `final-host-checks.log` |
| BLK-P7-01 | P7 | No reachable NixOS target. SSH to `root@server` and `andrew@server` is refused. The fixture target does not resolve | `final-host-checks.log`, P0 `ssh-server-root.log` |
| BLK-P7-02 | P7 | `andrew` has no passwordless sudo. The `sudo` binary is not setuid | `final-host-checks.log` |
| BLK-P7-03 | P7 | NixOS Machines plan, apply, status, and rollback not observed. Home Manager host version not observed | `NATIVE-BASELINE.md` observation record |
| BLK-P7-04 | P7 | Application data owner and restore route not defined | This record, section 4 |

## 7. Baseline facts

The 24 native baseline facts are in [NATIVE-BASELINE.md](../.scratch/projects/13-vendomat-v4-canonical/NATIVE-BASELINE.md).
Fourteen are observed on this pin, in whole or in part. Ten are pending. Observed facts are evidence, not gates.

## 8. Gate status

No V4 phase has passed. This record passes no gate.

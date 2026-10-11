# Host facts (Phase 1, read-only), 2026-10-11

Observed on `server` as `andrew` at 00:32-00:45 and 08:15 EDT. Raw: `~/.local/state/vendomat/v6/single-disk-cache/phase1/sizes.txt`.
Every fact below is an observation unless it says "inference".

## Disks and mounts

| Device | Model | Size | Rotational | Use now |
| --- | --- | --- | --- | --- |
| `nvme1n1` | NX-512 2280 | 476.9 GiB | no | `/` btrfs (subvolumes `@`, `@nix`, `@nix/store`, `@var`, `@home`, `@snapshots`); `/boot` vfat |
| `nvme0n1` | WD Blue SN5100 4TB | 3.6 TiB | no | blank install target; not touched |
| `sda` | WDC WD20EADS-00R6B0 | 1.8 TiB | yes | `/mnt/wd_green1` ext4: `attic/` (69 GB used on the filesystem), `restic/`, `restic-cache/`, `attic-investigation-andrew/` |
| `sdb` | TEAM TM8PS7002T | 1.9 TiB | no | `/mnt/shared` ntfs3, 195.8 GB used |

- Root btrfs: 443.9 GiB, 388.9 GiB used, 48.3 GiB free. Unallocated was 6.09 GiB at 00:32 and
  4.09 GiB at 08:15, then 8.09-9.09 GiB during the runs. Metadata 64-72 % used.
- `/mnt/wd_green1` also holds the **restic backup repository** of `nix-meta` (`profiles/backup.nix`,
  `nix-meta.backup.mountPoint = "/mnt/wd_green1"`). The `nix-systems` role on `main` (`fe848434`)
  has no backup module. The cache question does not decide where that repository goes.
- `nix-meta` also declares `/mnt/flex`, `/mnt/wd_re1`, and `/mnt/wd_re2` with `nofail`. They are not
  mounted now.

## Nix store and settings

| Fact | Value |
| --- | --- |
| Valid paths | 97,388 |
| Sum of NAR sizes | 127,780,402,144 bytes (about 119 GiB) |
| Paths with at least one signature | 11,012 (the rest were built here and carry none) |
| `/run/current-system` closure | 16.0 GiB (`nixos-system-server-26.11.20260705.d407951`) |
| Hard-link optimisation | "hard linking is currently saving 19.9 GiB" (from `nix store delete`) |
| `trusted-users` | `root andrew` |
| `substituters` on the running host | `https://cache.nixos.org/ https://devenv.cachix.org`. The running host does **not** substitute from its own Attic |
| `secret-key-files` | empty: locally built paths are unsigned |
| `require-sigs` | true |
| `nix.gc` in `nix-meta` | weekly, `--delete-older-than 14d` |
| `nix.gc` in `nix-systems` `main` | not set |

The `nix-systems` core (`nixos/core.nix`) sets the substituters `https://cache.nixos.org` and
`https://server.tail770f47.ts.net/attic/vendomat`, both public keys, `netrc-file = /etc/nix/netrc`,
and `fallback = true`.

## Attic today

- `nix-meta` `main` `2b08179b`, `machines/server.nix`: `services.atticd` with the patched package,
  SQLite at `/mnt/wd_green1/attic/server.db`, local storage at `/mnt/wd_green1/attic`, chunks
  16/64/256 KiB, `acquire-timeout = "1 minute"`, `max-connections = 4`, `busy-timeout = "30 seconds"`.
  Tailscale Serve publishes `/attic` to `http://127.0.0.1:8089`.
- The unit runs `/nix/store/yp3z60h1mwd8qiwrqn9r5ybmb191csai-attic-0-unstable-2026-06-26/bin/atticd`.
- `nix-systems` `main` `fe848434`, `nixos/server.nix`: stock Attic with no database keys, the same
  paths on `/mnt/wd_green1`, mounted by UUID with `nofail`, `RequiresMountsFor` on the unit.
- No retention period is configured (project 16 `evidence/live-cache.md`, "Limits").

## A fact in the brief that does not hold as written

The brief says one disk removes the `/mnt` conflict at cutover. The preflight (`MACH-016`, from
`MACH-010`) runs on the **running old system**. Its `/mnt/wd_green1` and `/mnt/shared` mounts come
from `nix-meta`, not from the new role. A one-disk new role does not unmount them. Inference: one
disk removes cutover step 11 (remount for the new system) and the new role's dependency on
`/mnt/wd_green1`. Step 8 (stop `atticd`, unmount both disks) stays, unless the old system first moves
its mount points out of `/mnt`.

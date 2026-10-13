# W5: the disk guard as a disko hook — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w5-disk-guard/REPORT.md (Sonnet subagent). Layout, hook, guard, and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w5-disk-guard/. VM images: /mnt/shared/vendomat-p21/w5/ (11 GB). Orchestrator spot-check: logs/G1-order.log shows disk-deactivate before the guard with destroy=true and the guard first with destroy=false; logs/G3-sha-before.txt and G3-sha-after.txt match; logs/G4b-install-default.log shows the kexec run on the running target. -->


VM fixtures only. No Vendomat repository change, no host disk, no host profile, no sudo, no GC.

## Verdict on A5 option 3: Backed with change

- The guard fits in the Basix disk layout and runs on the target before disko writes. It needs no devenv fork.
- It works only if the layout sets `destroy = false` on the disk. With disko's default `destroy = true`, the destroy step wipes the disk before the hook runs. The hook then sees a blank disk and passes (G3, naive case).
- The hook replaces fork patch 0006. It does NOT replace patch 0005 (G4b): stock `devenv machines install` kexecs the running machine before disko. Keep 0005, or accept that a mistaken install stops the machine until a power cycle.

## Inputs and versions

- Stock devenv: `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0/bin/devenv`. `devenv version`: `devenv 2.4.0 (x86_64-linux)`.
- Rust source read for devenv: `~/.local/state/vendomat/p21/2026-10-13/w2-machines/src/devenv-stock` (stock 2.4.0, no patch applied).
- nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`; disko `de5708739256238fb912c62f03988815db89ec9a` (store source `/nix/store/z2bsz1xw44k3gbkb4ks4ds8p0gyspvwb-source`); `devenv` input is W2's module-only path input.
- QEMU 11.1.1, OVMF 202608, KVM, disk-image files only. Images, VM state, and TMPDIR: `/mnt/shared/vendomat-p21/w5/` (11 GB; nothing removed).
- Work dir: `~/.local/state/vendomat/p21/2026-10-13/w5-disk-guard/`. Workspace `ws/`, scripts `bin/`, logs `logs/`. Reused from W2: SSH test key, QEMU and OVMF paths, the T3 ISO recipe.
- Fixture workspace files: `ws/basix-disk.nix` (layout and hook), `ws/basix-disk-guard.sh` (guard), `ws/target.nix`, `ws/devenv.nix`, `ws/installer.nix`.
- btrfs: every reading is in `logs/btrfs.log`. Metadata stayed 82.4 to 82.5 %. Unallocated fell from 33.87 to 30.87 GiB. Never near a stop condition.

## Hook option and source lines (disko de57087)

All paths are under `/nix/store/z2bsz1xw44k3gbkb4ks4ds8p0gyspvwb-source/`.

- `lib/default.nix:431-449` `mkSubType` adds `preCreateHook`, `postCreateHook`, `preMountHook`, and others to every disko device type. `:438` is `preCreateHook = diskoLib.mkHook "shell commands to run before create"`.
- `lib/default.nix:451-475` `mkCreateOption`. For a device the create text is: variable definitions (line 470), then `config.preCreateHook` (line 471), then the device's own create commands, then `postCreateHook`. The hook sees `$device`.
- `lib/default.nix:901-921` `_legacyDestroy`: `umount -Rv "/mnt" || :` (line 909), then `disk-deactivate` for each disk with `destroy = true`.
- `lib/default.nix:923-960` `_destroy` (same steps; `umount -Rv` at line 954).
- `lib/default.nix:1034-1046` `_disko` = `_legacyDestroy` + `_create` + `_mount`. This is what `diskoScript` runs (`lib/default.nix:852-857`).
- `lib/types/disk.nix:25-29` `destroy` option, default true: "If false, disko will not wipe or destroy this disk's contents during the destroy stage".
- `disk-deactivate/disk-deactivate.jq:` the `deactivate` function emits `wipefs --all -f` and `dd if=/dev/zero ... bs=440 count=1` for the disk and each partition.
- devenv roles: `src/modules/machines.nix:720-722` map `diskoScript` to `system.build.diskoScript`, `diskoFormatScript` to `formatScript`, `diskoMountScript` to `mountScript`. `devenv/src/devenv/machines.rs:1983-2003` runs the role; `--disko-mode` (`cli.rs:1401`) picks it.

Hook text used (`ws/basix-disk.nix`): `disko.devices.disk.main.preCreateHook = ''<guard> check "$device" [size]''` plus `destroy = false`.

## Fixtures

Disk use of all VM images: 11 GB under `/mnt/shared/vendomat-p21/w5/`. Two ISO builds added about 3 GiB each to the Nix store.

### G1. The hook exists and runs first: PASS with `destroy = false`; FAIL with `destroy = true`

- Command: `devenv build machines.target.build.diskoScript ...diskoFormatScript ...diskoMountScript`, then `grep -n` for guard, `umount`, `disk-deactivate`, `sgdisk`, `wipefs`, `mkfs`, `blkdiscard`, `dd`, `mount` (logs `G1-order.log`, `G1-naive-order.log`).
- Expected: guard line before every write line in every mode.
- Actual, `diskoScript` (`/nix/store/j31yd0xp...-disko`): line 3 `umount -Rv /mnt || :`; lines 5-9 `for dev in ;` (empty list, no `disk-deactivate` call); line 25 guard; line 33 first `sgdisk`; then `mkfs.vfat` and `mkfs.ext4`. `diskoFormatScript`: guard at line 16, first `sgdisk` at line 24. `diskoMountScript`: only `mount`, no write or guard (it creates nothing).
- Actual, `destroy = true` (`naive`, `/nix/store/f0kpmdms...-disko`): line 8 `disk-deactivate` (wipe) comes BEFORE line 25 guard. No `blkdiscard` line appears in any script.
- Verdict: the hook runs first in every create mode when `destroy = false`. The `umount -Rv /mnt` line always runs first (it unmounts only when `/mnt` is a mount point).

### G2. Local path, blank disk: PASS

- Command: boot the ISO (`/nix/store/sry7afw1...-nixos-minimal-...iso`, built by `devenv build outputs.iso`, 3:48) with a blank 4 GB qcow2 as `vd-target`, network blocked (`restrict=on`), 4 GB RAM. In the VM: run `/nix/store/j31yd0xp...-disko`, then `nixos-install --system TOP --no-root-password --no-channel-copy` (`logs/G2-steps.log`).
- Expected: guard OK, install succeeds, boots clean.
- Actual: `basix-disk-guard: OK /dev/disk/by-id/virtio-vd-target -> /dev/vda is blank, unused, and not a boot medium`; `disko-rc=0`; `install-rc=0`. Boot from the disk alone: hostname `target`, `running`, `systemctl --failed` empty, root on `/dev/vda2` (`G2-boot-check.log`).
- Note: the first attempt failed to boot (initrd had no `virtio_blk`) because `hardware.facter = null` gives no hardware modules. W2 had a real facter report. I added `boot.initrd.availableKernelModules` to the fixture target as a stand-in. The old logs are in `logs/attempt1-no-virtio-initrd/`. This is a fixture matter, not a guard matter.

### G3. Local path, used disk: PASS (and a FAIL for the naive layout)

- Command: make the target used (GPT, 1 GiB partition labelled `precious`, ext4 on it), shut down, hash. Boot the ISO with it. Run the `diskoScript` and the `diskoFormatScript` (`logs/G3-guard-run.log`).
- Expected: refusal; image unchanged; error names disk and reason.
- Actual: both scripts exit 1 with `basix-disk-guard: REFUSED /dev/disk/by-id/virtio-vd-target: has 1 partition(s): not blank`. Image sha256 before and after: `f2a6fcb2...52bc0f` (same; `G3-sha-before.txt`, `G3-sha-after.txt`).
- Naive layout (`destroy = true`, hook present), on a copy of the used image (`logs/G3-naive-run.log`): the script ran `wipefs --all -f /dev/vda1`, `wipefs --all -f /dev/vda`, `dd if=/dev/zero ... bs=440`, THEN the guard printed OK, and disko partitioned the disk. The copy's sha256 changed (`f2a6fcb2...` to `f6a586be...`), and `precious` was gone. Verdict: a hook on a `destroy = true` disk gives no protection.
- Verdict: PASS for the guarded layout.

### G4. Remote path, running machine: PASS for the disko hook; two side effects before it

- Setup: the G2-style install through G5 produced a bootable disk. Booted alone as `running` on port 2251: `running`, failed empty.
- Command: `env -u UV_PROJECT_ENVIRONMENT devenv machines install running --phases disko,install` (target `root@127.0.0.1:2251`) (`logs/G4-install-phases.log`).
- Expected: refusal before any write; VM still boots; image unchanged.
- Actual: `devenv rc=1`. Output: `basix-disk-guard: REFUSED ...: backs a mounted filesystem (/boot /nix/store /): boot medium, running root, or in use`, then `disko partitioning failed on machines.running`. The VM was not touched by disko. GPT header (first 1 MiB sha), last 1 MiB sha, and the partition and filesystem UUIDs are identical before and after (`G4-snap-before.txt`, `G4-snap-after.txt`). After a clean shutdown and reboot: `running`, failed empty, two partitions intact (`G4-boot-after.log`).
- Not as expected: before the guard, devenv ran `nix copy` of the disko script closure into the running machine's store: "copying 17 paths", store entries 588 to 605 (a write to the machine's disk). The whole-file sha256 of the qcow2 therefore differs, and it also differs when the VM only idles (host-file-sha changed between two idle snapshots 5 s apart). A whole-file hash is not a valid test on a running machine. The valid proof is the GPT and UUID comparison plus a clean reboot.
- Verdict: PASS for "disko did not run and the disk layout is intact". The "image sha256 unchanged" criterion does not hold, for a reason that is not the guard.

### G4b. Remote path, running machine, DEFAULT phases (extra fixture)

- Command: `devenv machines install running` (all phases) against the same running machine (`logs/G4b-install-default.log`, `G4b-*.txt`).
- Actual: the preflight passed (the NixOS box has `curl` and `tar`). devenv ran `curl --fail -L <nixos-images kexec tarball> | tar xzf - -C /root`, which wrote 451 MB to `/root/kexec` on the machine's disk. It then ran `/root/kexec/run`. The machine kexec'd into the installer: boot id changed, hostname `nixos-installer`, root on tmpfs, original sshd and services gone. The facter phase ran and wrote `.machines/running/facter.json` in the local workspace (I deleted it). devenv copied 104 paths. Then disko ran and the hook refused: `has 2 partition(s): not blank` (the mount-based reason is gone after kexec, but the partition check still holds). `devenv rc=1`.
- After a power cycle (QEMU killed): the original system booted, `running`, failed empty, `/root/kexec` (451 MB) left behind. No data loss.
- Verdict: the guard still saved the disk, but the machine was already stopped. A hook cannot protect a running machine's uptime.

### G5. Remote path, blank target: PASS

- Command: boot the ISO with a blank disk on port 2252 (`restrict=on`), then `devenv machines install target --phases disko,install` from the host (`logs/G5-install.log`).
- Expected: success through the guard.
- Actual: `devenv rc=0` in 1:50. The guard printed OK before the first `sgdisk`. `installation finished!`. The disk booted alone: `running`, failed empty (`G5-boot-check.log`). Image changed from the blank hash as expected.
- Not run: default phases against the ISO (kexec from the ISO). I covered kexec on the running machine in G4b instead.
- Verdict: PASS.

### G6. Boot medium and mounted target: PASS

- Boot medium as a disk: the ISO file copied to a raw image and attached as `virtio-vd-boot`, booted from it (`/iso` mounts from `vda1`). Scripts `bootmed` (diskoScript and diskoFormatScript) refuse: `REFUSED /dev/disk/by-id/virtio-vd-boot: backs a mounted filesystem (/iso ): boot medium, running root, or in use`. Image sha256 unchanged (`logs/G6-run.log`).
- Mounted target: blank disk `virtio-vd-mnt`, ext4 made and mounted at `/mnt/keep`. `diskoFormatScript` and `diskoScript` both refuse: `backs a mounted filesystem (/mnt/keep )`. `umount -Rv /mnt` did not unmount `/mnt/keep`: `/mnt` itself is not a mount point (`logs/G6-mnt.log`).
- Optical drives (`ata-QEMU_DVD-ROM_*`): `type is 'rom', not a disk`. Kernel name `/dev/vdb`: refused as not a by-id path. Missing path: refused.
- Verdict: PASS. All checks hold inside the hook.

### G7. Escape and gaps (no fix built)

- Deliberate bypass: `basix.disk.guard.enable = false` removes the hook text. The built script has 0 guard lines (`logs/G7-grep.log`). This is explicit, versioned, and visible in the layout.
- Natural bypass on the target: wipe the disk by hand (`wipefs -a`), then the guard sees a blank disk. This is the intended "I mean it" path.
- Gap 1, `destroy`: any layout with `destroy = true` (disko default) defeats the hook. A user can flip it with `lib.mkForce` (built script is identical to the naive script, `f0kpmdms...`). The module should assert `destroy = false` on every guarded disk. Not built.
- Gap 2, custom layout in `devenv.nix`: a user who defines another disk (`disko.devices.disk.extra`) gets no guard on it. The built script wipes `extra` (`for dev in /dev/disk/by-id/virtio-vd-extra`, line 6) with `disk-deactivate`, and creates `extra` (alphabetical order puts it before `main`). If the `main` guard then refuses, `extra` is already written. A user who replaces the Basix layout with their own disko config has no guard at all.
- Gap 3, scope: the guard sees only the disk named in the hook. Another disk mounted under `/mnt` is not checked (patch 0006 checked "nothing under /mnt"). A one-line `findmnt -R /mnt` check would add it. Not built or tested.
- Gap 4, wording: the refusal text says "disko wrote nothing in this step". The `umount -Rv /mnt` line has run before it. Change the text to "the guard stopped disko before it wrote to the disk".
- Gap 5, multi-disk: a hook on one disk cannot stop an earlier disk from being created. A multi-disk layout needs one guard call that checks all disks before the first create.

## Which patch 0006 checks fit the hook

| 0006 check | Fits? |
| --- | --- |
| by-id path resolves | Yes. Tested (missing path and kernel name refused). |
| Model and serial match | Not worth it. A real by-id name already holds model and serial (for example `nvme-<model>_<serial>`). Equal paths mean equal model and serial. A separate expected value adds nothing. |
| Size match | Yes, as an option. `basix.disk.guard.expectedSize` refused 12345 (`size is 4294967296 bytes, the layout expects 12345`) and accepted 4294967296 (`logs/G7-size.log`). Optional, cheap. |
| No signature | Yes. Tested (partition table and ext4 refused; zero-signature disk accepted). |
| Not the running root or /boot | Yes, through the mount, swap, and holder checks (tested G4, G6). Blind after kexec, but the partition check then holds. |
| Nothing under /mnt | Partly. The disk's own mounts are checked. Other disks under `/mnt` are not (Gap 3). |
| Committed facter report | No. This is not a target-side check. devenv already fails when `.machines/NAME/facter.json` is missing; "committed" is a workflow check. |

## What stock `devenv machines install` does to the target BEFORE disko

Source: `devenv/src/devenv/machines.rs:1583-1718` and `1872-1930`. Observed in G4, G4b, G5.

1. Local only: validates config; refuses a machine with no `target.host` before any contact (`machines.rs:1272-1276`). Reads local payload files.
2. Preflight (only when the kexec phase runs): one read-only SSH probe: `id -u`, `command -v tar`, `command -v curl`.
3. Kexec phase (in the DEFAULT phase set; skipped with `--phases disko,install`): writes a 451 MB tarball tree to `/root/kexec` on the target's disk, then runs `kexec`. The running OS stops and the machine becomes a RAM installer (observed).
4. Facter phase: runs `nixos-facter` on the target and writes `.machines/NAME/facter.json` locally.
5. Builds the toplevel locally; copies encryption keys if configured.
6. `nix copy` of the disko script closure to the target store (observed: 17 paths into a running machine's disk store).
7. Then disko (`ssh_run` of the script).

Answer to the 0005 question: a hook CANNOT replace patch 0005. With default phases, steps 3 and 6 happen before disko and stop and modify a running machine. The hook refuses afterwards and the disk stays safe, but the machine is down until a power cycle (and has 451 MB extra on its disk). A hook does replace the disk-safety half of 0005. Stock devenv has no option to disable kexec and no install-only flag. A machine with no `target.host` is refused, but `deploy` needs `target.host` for NixOS machines, so that route fails for adopt-existing machines.

## Observation versus inference

Observed in VMs (logs above): G1 script order; G2, G3, G5, G6 results; the naive wipe-first result; G4 and G4b behavior; size option.
Inferred, not run: a custom layout without `basix-disk.nix` has no guard (read from the built script, not installed); an assertion could enforce `destroy = false` (not built); `findmnt -R /mnt` fix; a real-hardware NVMe by-id name format; a naive layout on the boot medium would wipe it (not run); kexec with the Basix ISO as source (not run).

## Recommendation

1. Put the guard in the Basix layout with `destroy = false` and a build-time assertion for it. Drop patch 0006.
2. Keep patch 0005 (small, refuses before any SSH contact), or accept that a mistaken remote install of a running machine stops it. Do not claim the hook covers 0005.
3. Add the Gap 3 and Gap 5 checks and fix the Gap 4 text before this becomes the shipped guard.

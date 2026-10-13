# W8: an ISO of any machine, with policy in iso.modules — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w8-iso-policy/REPORT.md (Sonnet subagent). Patches: /home/andrew/.local/state/vendomat/p21/2026-10-13/w8-iso-policy/patches/patch1.diff (+21 -0) and patch2.diff (+46 -4). Workspaces and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w8-iso-policy/. Orchestrator spot-check: B1 shows the test services active without policy; B2, B3, B4 show state running, no failed units, both services inactive with policy; Q2-grubcfg.log shows timeout 10 vs 5. Between W7 and W8 the earlier unrooted ISO and disk-image store paths left the store (not removed by any agent); root unallocated was 41.87 GiB after W8. -->


Date: 2026-10-13. Fixture experiment only. No change to the Vendomat repository, a host disk, or a host profile.

## Inputs and versions

- devenv CLI `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0/bin/devenv`; `devenv version` prints `devenv 2.4.0 (x86_64-linux)` (logs/devenv-version.log). Run with `env -u UV_PROJECT_ENVIRONMENT`.
- Pins from W7/W2: nixpkgs e7439b6 (store `2010s04m...-source`), disko de57087, nixos-facter-modules 139dcef. Nothing downloaded.
- QEMU 11.1.1 with KVM, OVMF 202608, disk-image files only (no VM disk was needed: ISOs boot with no disk). Scratch under `/mnt/shared/vendomat-p21/w8/` (empty after cleanup; no qcow2 file was made).
- Module trees: `src/base` (v2.4.0 `src/modules` + the one-line `nixos` `deferredModule` change at line 302), `src/p1` (base + patch 1), `src/p2` (p1 + patch 2).
- Workspaces: `ws-q1` (override matrix, p1 modules), `ws-p2` (patch 2 fixtures). Machines in `ws-p2`: `box`, `iso`, `target` (as W7), `boxs`/`targets` (box/target + two test services, no policy), `boxp`/`targetp` (same + `iso.modules = [ ./policy.nix ]`), `boxq`/`boxf` (plain vs `mkForce` timeout), `isop` (ISO machine + `iso.modules`), `sl` (box + swap + LUKS).
- Scripts `bin-*.sh`; logs in `logs/`.

## Method note

`devenv eval q1.MACHINE.VARIANT` returns the ISO output path without building. A path is a hash of the whole derivation. Equal path = equal ISO; different path = different ISO. The Q1 matrix omits one of the nine W7 overrides at a time. The "none" variant gives W7's D2 box ISO path `4mvzi00d...` and target path `kgnfayfq...`, so the harness matches W7.

## Q1: required vs policy

| # | Override | Class | Evidence |
|---|---|---|---|
| 1 | `boot.loader.timeout = mkImageMediaOverride 10` | required (build) | Without it, eval fails on box and target: ``The option `boot.loader.timeout' has conflicting definition values: - In box.nix: 3 - In iso-image.nix: 10`` (logs/Q1-matrix.log). Source: `iso-image.nix:1029` sets a plain `boot.loader.timeout = 10`. Any machine that sets a timeout conflicts. The value 10 is not required; only the override is. |
| 2 | `isoImage.makeEfiBootable = true` | required (boot) | Source: `iso-image.nix:651` default false; `:994` adds `/boot/efi.img` and `/EFI` only when true. Eval: path differs (box `shizcdrf...` vs `4mvzi00d...`). W7 observed the ISO without it: OVMF "BdsDxe: No bootable option or device was found". Boot with it: B1 (CD and USB). Not re-booted without it in W8 (W7 result reused). |
| 3 | `isoImage.makeUsbBootable = true` | required for USB sticks, not for CD | Source: `make-iso9660-image.sh:45` makes `-isohybrid-mbr` from this flag only; `iso-image.nix:1048` passes it only with it. Eval: path differs. B1 ISO has the hybrid table (active partition 1 plus EFI partition 2, logs/Q1-usb-partition.log) and booted as a USB stick under OVMF (logs/B1-usb-check.log). The ISO without it was not built (budget), so "USB boot fails without it" is inference. |
| 4 | `fileSystems = mkImageMediaOverride isoFileSystems` | required (boot) | Eval: without it the ISO keeps the machine's `/boot` (box, sl: `/ /boot /iso /nix/...`); with it the list has no `/boot` (logs/Q1-extra.log). Boot: B5 (this override, swap, and LUKS removed) ends in emergency mode (logs/b5cd-serial.log). The 4/5/6 effects are not separated in B5. Source: `installation-cd-base.nix` sets the same override with the comment that a media "cannot tolerate a host config defined file system layout". |
| 5 | `swapDevices = mkImageMediaOverride [ ]` | required (boot) | Eval on `sl`: ISO has `/dev/disk/by-label/swap` without it, `[ ]` with it. B5 serial: "Expecting device /dev/disk/by-label/swap ... start job (1min 30s)". No effect on box or target (same path with and without). |
| 6 | `boot.initrd.luks.devices = mkImageMediaOverride { }` | required (boot) | Eval on `sl`: `cryptroot` present without it, empty with it. B5 serial: "Timed out waiting for device /dev/...0000", "Dependency failed for Cryptography Setup for cryptroot" (logs/B5-failures.log). No effect on box or target. |
| 7 | `hardware.enableAllHardware = true` | policy | B1 (box) and B3 (target) boot without it: running, zero failed units. Eval: the default initrd list already has `ahci ata_piix nvme sd_mod sr_mod xhci_pci ehci_pci uhci_hcd uas usbhid mmc_block`. The flag adds about 55 modules: legacy PATA/SATA, SCSI/RAID, VMware, Hyper-V. It matters for an installer that must boot on unknown hardware. That is distribution policy. |
| 8 | `boot.loader.systemd-boot.enable = mkImageMediaOverride false` | not needed | B1 and B3 boot without it. Eval: units, `/etc`, packages, kernel parameters, and activation scripts are identical with and without it. Only the `installBootLoader` text inside `switch-to-configuration` differs. The W7 claim "must be off" is not supported. |
| 9 | `disko.enableConfig = mkImageMediaOverride false` | not needed | Same ISO path with and without it on `target` (ext4+vfat layout) and on a ZFS disko layout `zt`. The `fileSystems` override already drops disko's file systems. Removing both brings `/boot` back (path differs), and the ZFS case then fails to eval (logs/Q1-zfs.log). Untested: LVM, disko LUKS layouts (the LUKS override covers `luks.devices`). |

Result: six overrides stay in devenv (1 to 6). Three leave (7 hw is policy; 8 and 9 are not needed). W7 listed nine.

Booted proof of the required set: B1 `boxs`, B3 `targetp`, B4 `sl` (has swap, LUKS, and `/boot`) all reach `running` with zero failed units, EFI boot, tmpfs root. B5 shows that without 4, 5, and 6 the `sl` ISO falls to emergency mode.

Priority finding (observation). The six overrides use priority 60. A plain `boot.loader.timeout = 5` in `iso.modules` is silently ignored: `boxq` has the same ISO path as `boxs` (`0grgf133...`). `lib.mkForce 5` works: `boxf` differs (`4rwrlwg9...`). The option text and the docs paragraph say "use `lib.mkForce`". Plain `isoImage.makeEfiBootable = false` would give a loud conflict error instead.

## Q2: patch 2 and a policy module

Policy (`ws-p2/policy.nix`): two services off, `boot.loader.timeout = lib.mkForce 5`, `pkgs.parted`.

| Check | Expected | Actual | Verdict |
|---|---|---|---|
| `build.nixos` of `boxs` (no policy) vs `boxp` (policy) | equal | both `30hxqg8gi0br4j9x1261gb9vkvw8jkw3` (logs/Q2-eval.log) | PASS |
| same for `targets` vs `targetp` | equal | both `0nl5xy7pgbjkl4pbx61zwh8rkzzlcmjf` | PASS |
| ISO path `boxs` vs `boxp` | differ | `0grgf133...` vs `8m0vwycb...` | PASS |
| GRUB timeout inside the ISO (`bsdtar -xOf ISO EFI/BOOT/grub.cfg`) | 10 vs 5 | `set timeout=10` vs `set timeout=5`; syslinux `TIMEOUT 100` vs `50` (logs/Q2-grubcfg.log) | PASS |
| `parted` on the booted ISO | absent vs present | absent in B1; `/run/current-system/sw/bin/parted` in B2, B3 | PASS |

## Q3: services on the live ISO

Test services in `svc.nix`: oneshot `make-host-key` (runs `ssh-keygen` into `/var/lib/hostkey`) and long-running `telemetry` (`sleep infinity`), both `wantedBy multi-user.target`.

- Without policy (B1, `boxs`): `make-host-key=active`, `telemetry=active`, `/var/lib/hostkey/id` and `id.pub` exist (logs/B1-cd-check.log, B1-usb-check.log). The services run on the live ISO. Root is tmpfs, so the key lives in RAM only. The harm is real for a service that uses a disk or the network.
- With policy (B2, `boxp`; B3, `targetp`): both `inactive`, `/var/lib/hostkey` absent, zero failed units.
- Simplest rule: `systemd.services.NAME.enable = lib.mkForce false`, one line per name, in a module in `iso.modules`. The unit file disappears from the ISO.

Rule proposed for Basix (the first is tested; the second is not):

1. Deny list. Basix ships `liveOff = names: { lib, ... }: { systemd.services = lib.genAttrs names (_: { enable = lib.mkForce false; }); }`. A machine adds `iso.modules = [ (basix.liveOff [ "make-host-key" "telemetry" ]) ]`. It needs no change in the machine's own modules. For a service from a NixOS module, use that module's `enable` option with `mkForce false`. Add `systemd.timers` and `systemd.sockets` the same way.
2. Live marker (untested). Basix declares `options.basix.live` and sets it true in the ISO policy. Machine modules read `config.basix.live or false`. This needs the machine author to write the check, so the deny list is the default.

Devenv should carry none of this. `iso.modules` is the whole devenv surface. Name lists, the marker, and the helper belong to Basix. Open point (inference, untested): another unit that `requires` a disabled service cannot start; the policy must disable the dependents too.

## Q4: facter + disko machine and plain machine

| ISO | Machine | Result | Verdict |
|---|---|---|---|
| B2 `8m0vwycb...` | `boxp` (plain box + services + policy) | running, failed list empty, EFI, tmpfs root, services inactive (logs/B2-cd-check.log) | PASS |
| B3 `7cpr3dbg...` | `targetp` (committed `facter.json` + disko layout + policy) | same (logs/B3-cd-check.log) | PASS |
| B4 `qjh1nv60...` | `sl` (swap + LUKS + `/boot`, no policy) | same (logs/B4-cd-check.log) | PASS (extra) |

## Q5: machine with its own ISO module

`devenv eval machines.iso.build.iso` with patch 2 gives `/nix/store/7qah8xsccpghd3h98xini5igrkwfzfqr-nixos-minimal-26.11.20261008.e7439b6-x86_64-linux.iso`. This is the W7 D1 and H4 path. Empty `iso.modules` leaves the path unchanged (`extendModules` with `[ ]` gives the same derivation). With `iso.modules` set (`isop`) the path changes (`5rf7538c...`): the policy applies, the devenv overrides do not. Verdict: PASS at eval level. The ISO file is no longer in the store, so I did not boot it; W7 booted this path (H4). The extra 1.3 GB build was not spent.

## Q6: `build.nixos` and `devenv build`

`devenv build machines.{box,iso,target}.build.nixos`: `fbp1k0vs...`, `sa86g98f...`, `6c1gfvkg...`. They equal W7 H1 (logs/Q6-nixos.log). PASS.

`devenv build machines.target` and `machines.targetp` return five outputs (nixos, deployer, diskoScript, diskoFormatScript, diskoMountScript) and no image (logs/Q6-walker.log). The options are `nullOr package`, so the walker skips them. PASS. `devenv build machines.iso` still fails as in stock: `expected a string, but got a AttrSet`. This is the W7 stock side issue (a machine with no disko disk); patch 2 does not change it.

## Q7: patches

Both apply in order on v2.4.0 `src/modules/machines.nix` with line 302 changed to `deferredModule` (`patch -p1`; final file equals `src/p2`). Patch 1 also applies without the one-line change.

| File | Lines in file | Added | Removed |
|---|---|---|---|
| `patches/patch1.diff` (W7 D1, `build.vm`, `build.iso` for machines with an ISO module) | 39 | 21 | 0 |
| `patches/patch2.diff` (extension + `iso.modules`, applies on patch 1) | 75 | 46 | 4 |
| both together | | 63 | 0 |

Compare W7 D2: +42 with nine overrides, no policy hook.

Docs paragraph for `docs/src/content/docs/machines.md`, under "Inspect and build":

> `devenv build machines.server.build.iso` builds a bootable ISO image of any machine. If the machine's `nixos` module imports an ISO module, devenv builds that image. Otherwise devenv adds the NixOS `iso-image` module for the image only. It sets the EFI and USB boot flags, and it replaces the machine's file systems, swap, LUKS devices, and boot menu timeout with the image's own. The machine's own `build.nixos` does not change.
>
> Use `iso.modules` for the rest of the image policy. It is a list of NixOS modules that apply to the ISO only:
>
> ```nix
> machines.server.iso.modules = [
>   ({ lib, pkgs, ... }: {
>     boot.loader.timeout = lib.mkForce 5;
>     environment.systemPackages = [ pkgs.parted ];
>     systemd.services.backup.enable = lib.mkForce false;
>   })
> ];
> ```
>
> To change an option that devenv sets (`boot.loader.timeout`, `fileSystems`, `swapDevices`, `boot.initrd.luks.devices`), use `lib.mkForce`. A plain value loses. `devenv build machines.server` does not build the image. Name `build.iso` to build it.

## Disk use

- ISOs built: 5 (B1 `boxs`, B2 `boxp`, B3 `targetp`, B4 `sl`, B5 `sl` negative). Sizes 534, 534, 706, 534, 535 MB.
- `/` unallocated 44.87 GiB at start, 41.87 GiB at end; metadata 80.8 % to 84.9 %, never above 90 % (logs/btrfs.log, 7 readings). `df` used 378 G to 383 G (about 5 GB: ISOs plus new toplevels and closures).
- No garbage collection, no sudo, no host disk or block device given to a VM. VM scratch under `/mnt/shared/vendomat-p21/w8/` is empty.

## Observation vs inference

Observations: every eval path, error text, boot result, serial log, and ISO file listing above.

Inferences:
- Without `makeUsbBootable` the ISO does not boot from a USB stick (source only; no ISO built).
- Without `makeEfiBootable`: W7 observation reused, not repeated.
- Each of overrides 4, 5, 6 is needed on its own: eval shows each effect; B5 boots with all three removed together.
- `disko.enableConfig = false` is redundant for ext4 and ZFS layouts only; LVM and disko-LUKS are untested.
- Real hardware: `enableAllHardware` matters only on hardware the default list misses; no real boot was tried.
- Dependents of a disabled service break (not tested).

## Verdict on Path D

Backed. An ISO of any machine needs six overrides, not nine. Machines with a `facter.json` and disko layout, plain machines, and machines with swap and LUKS all build ISOs that boot with zero failed units. `iso.modules` changes the ISO and leaves `build.nixos` untouched. A machine with its own ISO module keeps its path. Services turn off with a one-line `mkForce` rule in `iso.modules`. Three points to carry: policy must use `mkForce` to beat devenv's priority-60 overrides (plain values are silently ignored); `hw` goes to Basix; the USB flag has no negative proof.

## Gaps

- No ISO built without `makeUsbBootable` or `makeEfiBootable` in W8.
- Facter report is from a QEMU guest (W2). LVM, ZFS-on-boot, impermanence, and disko LUKS layouts untested for boot (ZFS and ext4 only at eval level).
- The own-ISO machine ISO was compared by path, not rebuilt or booted.
- Tested on v2.4.0 modules only, not upstream main. GitHub issues and pull requests not searched.
- Stock `devenv build machines.NAME` fails for machines without disko disks; unchanged.

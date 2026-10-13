# W7: public ISO and VM build options — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w7-build-options/REPORT.md (Sonnet subagent). Patches: /home/andrew/.local/state/vendomat/p21/2026-10-13/w7-build-options/patches/d1.diff (+21 lines) and d2.diff (+42 lines). Workspaces and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w7-build-options/. VM images were deleted; /mnt/shared/vendomat-p21/w7/ holds 2.1 MB. Orchestrator spot-check: H1 logs show identical build.nixos paths on stock, D1, and D2 (box fbp1k0vs..., target 6c1gfvkg...); H3 and H4 checks show running with no failed units; H6 shows the named error; btrfs at end 21.87 GiB unallocated, metadata 82.81 %. -->


Date: 2026-10-13. Fixture experiment only. No change to the Vendomat repository, a host disk, or a host profile.

## Inputs and versions

- devenv CLI: `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0/bin/devenv`, `devenv version` prints `devenv 2.4.0 (x86_64-linux)` (logs/devenv-version.log).
- Module source: copy of W2's `devenv-stock/src/modules` (devenv v2.4.0 `src/modules`, `latest-version` 2.3.1). Copies: `src/stock` (base), `src/d1`, `src/d2`, `src/d1o` (negative test).
- Pins reused from W2: nixpkgs e7439b6 (store `2010s04m...-source`), disko de57087, nixos-facter-modules 139dcef. Nothing downloaded.
- QEMU 11.1.1 with KVM, OVMF 202608. Disk-image files only. Images and scratch under `/mnt/shared/vendomat-p21/w7/` (2.1 MB left after cleanup; qcow2 files deleted).
- Workspaces: `ws-stock`, `ws-d1`, `ws-d2`, `ws-d1o`. Each has machines `box` (facter null, W2 T2 box), `iso` (facter null, installation-cd-minimal), `target` (W2 T3 `facter.json` from a QEMU guest, plus the W2 T3 disko layout).
- Scripts: `bin-*.sh`. Patches: `patches/d1.diff`, `patches/d2.diff`. Logs: `logs/`.

## Source lines (v2.4.0 `src/modules/machines.nix`)

- `nixosEval = machine: ...` builds the NixOS evaluation: line 126. It returns the full `nixosSystem` result, so it has `.config`, `.pkgs`, and `.extendModules`.
- `build.nixos = lib.mkOption { type = outputType; ... internal = true; }`: line 604. Siblings `build.deployer` 611, `build.nix-darwin` 646, `build.home-manager` 653, `build.diskoScript` 660, `build.diskoFormatScript` 667, `build.diskoMountScript` 674.
- `_nixosEval = lib.mkOption { type = unspecified; internal = true; visible = false; }`: line 684.
- `config._nixosEval = lib.mkIf (config.nixos != null) (nixosEval config);`: line 711.
- `config.build = { nixos = lib.mkIf (config.nixos != null) config._nixosEval.config.system.build.toplevel; ... }`: lines 714-724.
- `outputType = outerConfig.lib.types.output`: line 4. The `build` walker is `devenv-nix-backend/bootstrap/bootstrapLib.nix:488-533`. It collects only options whose type name is `output` or `outputOf`.
- `devenv build ATTR` is `devenv/src/devenv/mod.rs:2585`. It evaluates `build.ATTR`. If that evaluation fails, it builds `devenv.config.ATTR` directly.
- `nixos` option type: line 302 (`unspecified`; the deferredModule change is one line there, no overlap with this patch).

## Key finding: the option type must not be `output`

Observation. The `build` walker evaluates and builds every `output`-typed option of a machine. `devenv build` and `devenv build machines.NAME` would then build a VM and an ISO for every machine. A machine without an ISO module would also make D1 throw inside the walker.

Fixture: `ws-d1o` types `build.iso` as `outputType`. `devenv build machines.target` then fails: `Failed to build attribute: devenv.config.machines.target: expected a string, but got a AttrSet` (logs/H7-outputtype-negative.log). The walker forced the D1 throw, the CLI swallowed it, and the fallback failed.

With `lib.types.nullOr lib.types.package` the walker skips the options. `devenv build machines.target` returns the same five outputs as stock (nixos, deployer, diskoScript, diskoFormatScript, diskoMountScript; logs/H7-*-build-machines-target.log). `devenv build machines.NAME.build.vm` still works because the CLI falls back to the direct attribute. This is the design in both diffs.

Side observation (stock, not from the patch): `devenv build machines.box` fails for any machine without a disko disk (`No disks defined, did you forget to import your disko config?`), because `build.diskoScript` throws in the walker.

## The two designs

### D1: read `system.build.vm` and `system.build.isoImage` directly

Diff: `patches/d1.diff`, 21 lines added, 0 removed, 2 hunks.

```nix
build.vm  = mkOption { type = nullOr package; default = null; description = ...; };
build.iso = mkOption { type = nullOr package; default = null; description = ...; };
...
vm  = lib.mkIf (config.nixos != null) config._nixosEval.config.system.build.vm;
iso = lib.mkIf (config.nixos != null) (
  config._nixosEval.config.system.build.isoImage or (throw
    "machines.${name}.build.iso: the NixOS configuration of machine '${name}' has no ISO image. Import an ISO module in machines.${name}.nixos, for example (modulesPath + \"/installer/cd-dvd/installation-cd-minimal.nix\")."));
```

### D2: extend the evaluation with the NixOS `iso-image` module

Diff: `patches/d2.diff`, 42 lines added, 0 removed, 4 hunks. `build.vm` is the same as D1. `build.iso` uses the machine's own image when it has one, and otherwise `isoEval`:

```nix
isoEval = eval: eval.extendModules { modules = [ ({ config, lib, modulesPath, ... }: {
  imports = [ (modulesPath + "/installer/cd-dvd/iso-image.nix") ];
  hardware.enableAllHardware = true;
  isoImage.makeEfiBootable = true;
  isoImage.makeUsbBootable = true;
  swapDevices = lib.mkImageMediaOverride [ ];
  fileSystems = lib.mkImageMediaOverride config.lib.isoFileSystems;
  boot.initrd.luks.devices = lib.mkImageMediaOverride { };
  boot.loader.systemd-boot.enable = lib.mkImageMediaOverride false;
  boot.loader.timeout = lib.mkImageMediaOverride 10;
  disko.enableConfig = lib.mkImageMediaOverride false;
}) ]; };
iso = lib.mkIf (config.nixos != null) (
  config._nixosEval.config.system.build.isoImage or (isoEval config._nixosEval).config.system.build.isoImage);
```

What the ISO needs, found by failure (observations):

1. `boot.loader.timeout`: iso-image sets a plain 10, `box.nix` sets 3. Evaluation fails with "conflicting definition values". A machine that sets a loader timeout needs an override. Fixed with `mkImageMediaOverride 10`.
2. `isoImage.makeEfiBootable` defaults to false. The first ISO built but did not boot under OVMF ("BdsDxe: No bootable option or device was found"). Fixed with `makeEfiBootable` and `makeUsbBootable`, as `installation-cd-base.nix` does.
3. `fileSystems`, `swapDevices`, `boot.initrd.luks.devices`: the image must drop the machine's own. `installation-cd-base.nix` uses `mkImageMediaOverride` for all three; D2 copies that. `disko.enableConfig = false` stops disko from adding file systems and loader devices. `hardware.enableAllHardware` gives the initrd storage drivers.
4. `systemd-boot` must be off for the image (iso-image already turns GRUB off).
5. `hardware.facter`: no override needed. The facter modules only add kernel modules; the ISO with a real `facter.json` built and booted.
6. First D2 version applied the extension to a machine that already imports `installation-cd-minimal`. That ISO failed to boot: `Failed to mount /sysroot/nix/store` and emergency mode (logs/H4-d2-first-try-emergency-serial.log). Cause (inference): two priority-60 `fileSystems` definitions duplicate mount options. Fix: the `or` in the diff. A machine with an ISO module keeps its own image, and its store path equals the D1 path (`7qah8xsc...`).

`build.vm` needs no override in either design: nixpkgs `build-vm.nix` builds `system.build.vm` through `vmVariant`, and `qemu-vm.nix` replaces `fileSystems` with `mkVMOverride`. The disko file systems and the facter report do not block it.

## Fixtures

Disk: unallocated 30.87 GiB at start, 21.87 GiB at end (about 9 GiB of new store paths: ISOs 1.3 to 1.5 GiB each, VMs). Metadata 82.5 % to 82.8 %, never above 90 % (logs/btrfs.log, 25 readings). No garbage collection. No sudo.

| # | Command | Expected | Actual | Verdict |
|---|---|---|---|---|
| H1 | `devenv build machines.{box,iso,target}.build.nixos` on stock, D1, D2 | same store path | box `fbp1k0vs...`, iso `sa86g98f...`, target `6c1gfvkg...` in all three (target equals W2 T3) | PASS |
| H2 | D1 `devenv build machines.box.build.vm`, boot | multi-user, zero failed units | `x6vb0nsw...-nixos-vm`; `systemctl is-system-running` = running, failed list empty (logs/H2-d1-vm-check.log). D2 gives the same path, so the boot result holds for D2 | PASS |
| H3 | D1 `devenv build machines.target.build.vm` (facter.json + disko), boot | same, no extra setting | `ydcv04py...-nixos-vm`; running, failed list empty, `/` is `/dev/vda` ext4, `/boot` not mounted. D2 same path. No override needed (qemu-vm.nix drops the disko file systems) | PASS |
| H4 | D1 `devenv build machines.iso.build.iso`, OVMF boot, no disk | boots | `7qah8xsc...iso`; ssh ok, running, failed list empty, EFI boot, root on tmpfs (logs/H4-d1-iso-check.log). D2 returns the same path | PASS |
| H5 | D2 `devenv build machines.box.build.iso` (box: systemd-boot, label file systems) | builds, boots | `4mvzi00d...iso`; running, failed empty, EFI, tmpfs root (logs/H5-d2-box-iso-check.log). Needed timeout and EFI fixes first (see D2 list) | PASS |
| H5b | D2 `devenv build machines.target.build.iso` (facter.json + disko) | builds, boots | `kgnfayfq...iso`; running, failed empty, EFI, tmpfs root (logs/H5-d2-target-iso-check.log) | PASS |
| H6 | D1 `devenv build machines.box.build.iso` and `machines.target.build.iso` | clear error | `error: machines.box.build.iso: the NixOS configuration of machine 'box' has no ISO image. Import an ISO module in machines.box.nixos, for example (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix").` Same text for `target` (logs/H6-*.log) | PASS |
| H7a | `devenv info` and `devenv eval` with each patch | works | `devenv info` rc 0 in stock, D1, D2; `devenv eval machines.target.hardware.facter` works | PASS |
| H7b | `build.nixos` eval time, `--refresh-eval-cache`, 3 rounds | no cost | box: stock 9.74 s, D1 9.90 s, D2 9.54 s. target: stock 10.04 s, D1 9.66 s, D2 10.02 s. `info`: 1.21, 1.09, 1.31 s. All inside the run-to-run spread (logs/H7-timing.log) | PASS |
| H7c | on-demand cost (`devenv eval`, no cache) | small | box vm 10.9 s (D1) and 11.3 s (D2); box iso 9.7 s (D2); iso-machine iso 22.1 s (D1), 19.7 s (D2); stock box nixos 9.5 s (logs/H7-ondemand-eval.log) | INFO |
| H7d | `devenv build machines.target` (walker) | still 5 outputs, no image | stock and D2 return the same five outputs; images skipped | PASS |
| H8 | patch composes with the one-line `deferredModule` change | applies | `patch --dry-run` of d1.diff and d2.diff on a v2.4.0 copy with line 302 changed: both apply | PASS |

Not built or booted: the D2 hybrid ISO for the `iso` machine (same path as D1, so the D1 boot covers it); D1 for `box`/`target` ISO (it throws by design).

## H8: upstream fit

Recommended patch: `patches/d1.diff` (unified diff against v2.4.0 `src/modules/machines.nix`, headers `a/src/modules/machines.nix`). D2: `patches/d2.diff`.

Search of the local devenv source tree (CHANGELOG.md, `docs/src/content/docs/machines.md`, `docs/src/data/options.json`): no entry for an ISO or VM build, `build.vm`, `build.iso`, or `isoImage`. The only `virtiofs/9p VM` text in the CHANGELOG is an unrelated SQLite fix. I did not search GitHub issues or pull requests (no network search was asked for). Nothing was posted.

Docs paragraph for `docs/src/content/docs/machines.md`, under "Inspect and build", after the `build.nixos` example (D1 wording):

> To try a machine without installing it, build a virtual machine or an ISO image from the same `nixos` module:
>
> ```sh
> devenv build machines.server.build.vm   # a script that runs the machine in QEMU
> devenv build machines.server.build.iso  # a bootable ISO image
> ```
>
> `devenv build machines.server` does not build these images. Name one to build it. The `build.vm` image needs no extra setting. The `build.iso` image needs a `nixos` module that imports an ISO module, for example `modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix"`. Without one, devenv stops with an error that names the machine.

Changelog line: "Added `machines.<name>.build.vm` and `machines.<name>.build.iso` to build a QEMU script and an ISO image of a machine."

## Comparison

| | D1 | D2 (with machine-own-ISO rule) |
|---|---|---|
| Diff | +21 lines | +42 lines |
| Facter + disko machine builds VM with no setting | yes | yes (same VM path) |
| Facter + disko machine builds ISO with no setting | no, throws with a clear error | yes (verified for target) |
| `build.nixos` store path | unchanged | unchanged |
| Eval cost without use | none measurable | none measurable |
| ISO-specific settings (`storeContents`, volume ID, keys) | yes, on a dedicated ISO machine | only on a dedicated ISO machine (the option does not exist on a normal machine) |
| Policy owned by devenv | none | nine ISO choices copied from `installation-cd-base`; they can drift with nixpkgs |

## Verdict on A6 option 2

Backed with two changes: (1) type the options `nullOr package`, not `output`; (2) choose D1 or D2 for `build.iso`.

Recommendation: D1 (+21 lines). Reasons:

1. The smaller patch is the easier upstream offer, and it adds no installer policy.
2. Vendomat's Basix ISO already needs its own machine (A7 puts `storeContents` on it), and that machine imports an ISO module. D1 serves it exactly.
3. `build.vm` is identical in D1 and D2 and works for facter + disko machines with no setting.
4. D2 only adds an ISO of an installed-style machine. If wanted later, add it as a second patch; the hybrid rule keeps ISO machines unchanged.

## Gaps

- The facter report is from a QEMU guest (W2 T3). `nixos-facter` refuses to run without root, and sudo was out of scope, so a real-hardware report was not tried. Inference: the VM drops host-specific file systems, but a report with host-only initrd modules may add modules the VM kernel lacks.
- The ISO check proves boot and no failed units under OVMF, not a booted install. VM and ISO networking and ssh worked.
- Machines with LUKS, ZFS, or an impermanence layout are untested for both `build.vm` and the D2 ISO.
- Tested against the v2.4.0 modules only, not upstream main.
- The stock `devenv build machines.NAME` failure for machines without disko disks is unchanged by the patch.
- GitHub issues and pull requests were not searched.

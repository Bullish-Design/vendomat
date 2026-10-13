# W10: a stable QEMU hardware report (A14) — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w10-facter/REPORT.md (Sonnet subagent). Reports, filters (bin/drop.jq, bin/allow.jq), and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w10-facter/. Overlays deleted; W2 and W5 images unchanged. Orchestrator spot-check: data/f2 holds five reports with five raw hashes and one hash after del(.hardware.cpu[].tlb_size); logs/F4-results.txt shows 6c1gfvkg for the baked, RAM, CPU-count, MAC, and second-disk reports, 2f0a8lba for named -cpu models, 2l8s1piy for -machine pc. -->


VM fixture experiment only. No change to the Vendomat repository, a host disk, a host profile, or the W2 and W5 images.

## Inputs and versions

- nixos-facter 0.4.4 (`/nix/store/vriblh78visrrsfp6d3k8q1x61vikk0y-nixos-facter-0.4.4`, nixpkgs e7439b6, fetched from cache.nixos.org, 94 MB closure). hwinfo 25.5 (source read from the same nixpkgs).
- nixos-facter-modules 139dcef (`/nix/store/4v4gqlpwx3vlp9l104rcgj5632ljr2dd-source`), disko de57087, devenv 2.4.0 stock modules (W2 pins, copy of W2 `ws-t3`, in `ws-f4/`).
- QEMU 11.1.1 with KVM, OVMF 202608. Guest: W2 T1 `box.qcow2` (NixOS 26.11, kernel 6.18.55) through a qcow2 overlay. Host CPU: Xeon W-2125 (Skylake-W).
- Scripts in `bin/`, reports in `data/`, logs in `logs/` (`btrfs.log`, `F4-results.txt`, `F4-nixdiff-*.txt`).
- Overlays, `vars.fd` copies, and the extra 1 GiB disk image were deleted at the end. The W2 and W5 images were not changed.
- btrfs readings are in `logs/btrfs.log`. Metadata stayed at 80 to 83 %, unallocated at 40.87 GiB or more. My own store growth is about 0.5 GiB (facter, hwinfo source, nix-diff, a few 316 KB toplevels). The 3 GiB drop in unallocated space came from the other spikes.

## F1. Explain the W2 difference

- Command: copy the baked `ws-t3/.machines/target/facter.json` (QEMU probe) and the re-run copy `/root/workspace/.machines/target/facter.ISO-RUN.json`. I read the re-run copy by booting an overlay of W2 `vd-target.qcow2`. Then `diff` of `jq -S` output.
- Expected: a small set of differing paths.
- Actual: the re-run copy comes from the 8 GiB slim run, not from the 4 GiB pre run that gave byte 9737. The 4 GiB pre-run file no longer exists. Five paths differ:
  - `.hardware.cpu[0].tlb_size`: 4982 vs 15479. This sits on line 434, the line W2 reported.
  - RAM size: `.hardware.memory[].resources[].range`, `.smbios.memory_array[].max_size`, `.smbios.memory_array_mapped_address[].end_address`, `.smbios.memory_device[].size`.
- Cause of `tlb_size`: a bug in hwinfo 25.5. `src/hd/cpu.c:442` reads `tlb_size = clflush_size = address_size_physical, address_size_virtual = 0;`. The comma makes `tlb_size` take an uninitialised stack value. Line 468 sets it only when `/proc/cpuinfo` has a "TLB size" line. Line 500 copies it into the report. The guest `/proc/cpuinfo` has no such line (`grep -ic tlb` gives 0).
- Verdict: explained. The W2 byte-9737 difference is `tlb_size` (observation: same line; inference: same cause, because the 4 GiB pair is gone).

## F2. Two runs in one boot, then after a reboot

- Command: `nixos-facter` three times in boot 1, reboot, twice in boot 2, same VM shape (2 GiB, 2 CPUs, `-cpu host`, q35). Diff with `jq -S`.
- Expected: no difference if the report is stable.
- Actual: the five raw files have five different hashes. `jq -S` diff shows only `.hardware.cpu[0].tlb_size` (7855, 14346, 1590, 10937, 862). After `del(.hardware.cpu[].tlb_size)` all five files are byte identical.
- Verdict: one volatile field, nothing else. Reboot has no effect.

## F3. Change the VM shape

Each shape ran once on the same guest disk. I compared the leaf paths after removing `tlb_size` and the handle numbers (`index`, `attached_to`, `handle`, `array_handle`), and after sorting the arrays (`bin/canon.jq`).

| Shape (change from base: 2 GiB, 2 CPUs, `-cpu host`, q35, virtio NIC, MAC 52:54:00:12:34:56) | Paths that differ | Class |
| --- | --- | --- |
| Second run of the same shape | `.hardware.cpu[].tlb_size` | volatile |
| RAM 4096 | `.hardware.memory[].resources[].range`, `.smbios.memory_array[].max_size`, `.smbios.memory_device[].size`, `.smbios.memory_array_mapped_address[]` (an extra entry above 4 GiB) | configuration |
| 4 CPUs | `.hardware.cpu[].cores`, `.siblings`, `.units` (plus handle renumbering) | configuration |
| Other MAC | none in the content. Only the order of `.hardware.network_interface[]` changed (loopback moved) and the handle numbers. The report never holds the MAC: both `hwaddr` entries read `53`. | none (order only) |
| Second 1 GiB disk (new image file) | new `.hardware.disk[]`, `.storage_controller[]`, `.pci[]` entries, new `unix_device_names`, `sysfs_id`, `slot.number`, PCI `resources[].base` | configuration |
| `-cpu max` | none | none (same as `host` here) |
| `-cpu Skylake-Server-v4` | `.hardware.cpu[].features` (22 entries, `vmx` missing), `.bugs`, `.model_name`, `.cpuid_level`, `.address_sizes.physical` | configuration |
| `-cpu Haswell-v4` | the same fields, plus `.model`, `.stepping` | configuration |
| `-cpu qemu64` | the same fields, plus `.family`, `.cache_alignment` (63 `features` entries differ) | configuration |
| `-machine pc` (i440fx) | `.hardware.bridge[]`, `.storage_controller[]` (IDE), `.cdrom[]`, `.disk[]`, `.pci[]`, `unix_device_names`, `sysfs_id`; NIC name `ens3` instead of `enp0s2` | configuration |
| `-nic model=e1000` | `.hardware.network_controller[]` and `.network_interface[]` driver and device fields | configuration |

Verdict: one volatile field. All other differences follow the VM shape. A report is stable for a fixed shape. The `-cpu host` and `-cpu max` reports depend on the host CPU (inference: not tested on a second host).

## F4. Does the toplevel store path change?

- Command: `env -u UV_PROJECT_ENVIRONMENT devenv build machines.target.build.nixos` in `ws-f4` (copy of W2 `ws-t3`) with each report copied to `.machines/target/facter.json`. Raw results are in `logs/F4-results.txt`.
- Expected: no change for volatile and RAM fields. Possible change for CPU, machine type, and device fields.
- Actual:

| Report | Toplevel |
| --- | --- |
| W2 baked, W2 re-run (8 GiB, other `tlb_size`), F2 runs 1 and 3 (box VM, other hardware) | `6c1gfvkg...` (same as W2 T3) |
| F3 base, RAM 4096, 4 CPUs, other MAC, second disk, `-cpu max`, `e1000` | `6c1gfvkg...` |
| F3 `-cpu Skylake-Server-v4`, `Haswell-v4`, `qemu64`, and the combined shape | `2f0a8lba...` |
| F3 `-machine pc` | `2l8s1piy...` |
| Control: report `{"system":"x86_64-linux"}` | `d7kmlmrh...` |
| Control: baked report with `virtualisation = "none"` | `gmf3abk4...` |

- `nix-diff` (`logs/F4-nixdiff-A-B.txt`, `F4-nixdiff-A-C.txt`) for `6c1gfvkg` against `2f0a8lba`: only `nixos.conf` changes (`/etc/modules-load.d`). `6c1gfvkg` loads `atkbd kvm-intel loop`. `2f0a8lba` loads `atkbd loop`. Cause: `vmx` is missing from the named CPU models.
- For `6c1gfvkg` against `2l8s1piy`: the interface name `enp0s2` becomes `ens3` (`40-ens3.link`, `network-addresses-ens3.service`, `networking.interfaces`), and the initrd changes (319 KiB larger, from the IDE storage drivers). `nix store diff-closures` agrees.
- The controls show the report does reach the toplevel. A different QEMU box VM (2 GiB, 2 CPUs, one disk) and the W2 ISO VM (4 CPUs, two disks, other RAM) give the same toplevel.
- Verdict: the volatile field and the RAM, CPU-count, MAC, disk-count, NIC-model fields never change the store path. The CPU `vmx` or `svm` feature, the machine type, and the device drivers do.

## F5. Filters

Fields the modules read (nixos-facter-modules 139dcef):

- `.system`: `modules/nixos/system.nix:9-10`.
- `.virtualisation`: `modules/nixos/virtualisation.nix:28,32,36,44,49`.
- `.uefi.supported`: `modules/nixos/boot.nix:8`.
- `.hardware.cpu[].features`: `virtualisation.nix:60` (`vmx` gives `kvm-intel`, `svm` gives `kvm-amd`).
- `.hardware.cpu[].vendor_name`: `lib/lib.nix:19-23`. `.family`, `.model`: `modules/nixos/camera/ipu6.nix:9-11`.
- `.hardware.{disk,storage_controller,firewire_controller}[].driver_modules`: `modules/nixos/disk.nix:13-16`, through `collectDrivers` (`lib/lib.nix:26`).
- `.hardware.network_controller[].driver_modules`: `modules/nixos/networking/initrd.nix:11`. `.vendor.value`, `.device.value`: `networking/intel.nix:15-26,35-46`.
- `.hardware.network_interface[].sub_class.name`, `.unix_device_names`: `modules/nixos/networking/default.nix:21-25`.
- `.hardware.usb_controller[].driver_modules`: `modules/nixos/keyboard.nix:10`. `.graphics_card[].driver_modules`: `graphics/default.nix:20`, `graphics/amd.nix:10`.
- `.hardware.scsi[].vendor.value`, `.device.value`: `virtualisation.nix:15-24`.
- Array length only: `.hardware.bluetooth` (`bluetooth.nix:6`), `.hardware.monitor` (`graphics/default.nix:12`).
- PCI and USB identity: `.hardware.{pci,unknown}[]` (`camera/ipu6.nix:76-77`), `.hardware.{unknown,fingerprint,usb}[]` (`fingerprint/default.nix:26-28`).
- Nothing reads `tlb_size`, `.smbios`, `.hardware.memory`, `hwaddr`, `index`, or `attached_to`.

Filters (both in `bin/`):

1. `bin/drop.jq`: `del(.hardware.cpu[].tlb_size)`. This is enough. It removes the only volatile field.
2. `bin/allow.jq`: keeps only the fields above and sorts each array. It makes a 6 KB report instead of 36 KB, and it hides RAM, CPU-count, MAC, and extra-disk churn. It breaks when a module update reads a new field.

Proof (`logs/F4-results.txt`, labels `F5-*` and `F5s-*`): raw, `drop`, and `allow` reports give the same toplevel for the baked report, the re-run, the second-disk, RAM 4096, `e1000`, `Skylake-Server-v4` (`2f0a8lba`), and `-machine pc` (`2l8s1piy`). After `allow`, the shapes base, mac, smp4, mem4096, and cpu-max are byte identical (hash 640018fc). W2 baked, W2 re-run, and the second-disk shape are identical too (ab6b173f).

## F6. Recommendation and verdict on A14 option 2

A committed QEMU report is stable enough. The run-to-run noise is one field, `tlb_size`, and no module reads it. Option 2 stands, with these conditions:

1. Commit one report per test-VM shape, taken with `nixos-facter` from a guest of that shape. Pin the shape in the VM definition: machine type (`q35`), disk bus and count, NIC model, and a named `-cpu`.
2. Pin the CPU with a named model, not `-cpu host`. `host` reports the host CPU feature list, so `vmx` or `svm` follows the host and its nested-virtualisation setting. A named model fixes `kvm-intel` or `kvm-amd` in the toplevel. Choose with intent: `Skylake-Server-v4` has no `vmx`, so the guest loads no `kvm-intel`.
3. RAM size, CPU count, and MAC need no pinning. They never change the toplevel.
4. Run the drop filter (`del(.hardware.cpu[].tlb_size)`) when `install` or the report command writes the file. The committed file is then byte stable across runs, and a regenerate gives an empty diff.

Cost of option 2: one 30 KB file per shape, a regenerate step when the shape changes, and a pinned QEMU command line. Benefit: VM tests run the real facter module path (`kvm`, virtio initrd modules, DHCP interface names).

Cost of option 1 (`hardware.facter = null`): no file, no pin, and W7 H3 shows it builds and boots. VM tests then skip the facter modules. Interface names, initrd drivers, and `virtualisation`-driven settings come from other config, so the test covers less of the real path.

Real hardware: `install` should apply the drop filter too. On real hardware `tlb_size` is probably also garbage on Intel (inference: the kernel prints "TLB size" only when it knows the value; I did not run facter on real hardware). I advise against the allow filter on real reports: a module update that reads a new field would silently see no data. Prefer the drop filter, and optionally also drop `.smbios` and `.hardware.memory` for smaller diffs (not tested as a drop; the allow filter proves they are unread today).

## Observation vs inference

Observation: all diffs, hashes, toplevel paths, and source lines above. Inference: that the W2 4 GiB pair differed only in `tlb_size`; that real Intel hardware also yields a random `tlb_size`; that a different host CPU changes `-cpu host` reports.

## Gaps

- One host only. No second CPU model or an AMD host.
- Not tested: the real test-VM path (`build.vm` with a committed report), only the toplevel. W7 H3 covers the VM boot with a QEMU report.
- Not tested: UEFI versus BIOS boot (`.uefi.supported` is `true` in all reports), virtio-scsi, and a USB controller.
- Not tested: whether a future nixos-facter release changes the volatile set.

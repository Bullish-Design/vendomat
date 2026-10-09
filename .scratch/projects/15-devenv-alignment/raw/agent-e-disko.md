<!-- Raw final report of Agent E (disko by VM fixture, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Model output: an observation here is the agent's claim, backed by the raw logs it names under ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

AGENT E REPORT. disko, devenv Machines, a second ESP and the 4 TB NVMe. Raw log dir: ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-e/ (log.txt, q*-final.txt, q*-raw.txt, src/ holds the flake and VM tests, README.txt). Temp dirs are removed. I ran no sudo and touched no real block device. Every disk write happened inside a disposable NixOS VM test.

PINS
- disko v1.13.0 = de5708739256238fb912c62f03988815db89ec9a (also the floating tag `latest`). It is the newest tag, from 2026-01-20. Master is 725ea35e (2026-09-18, 82 commits later); I read it only for the Q7 diff.
- nixpkgs nixos-unstable = e7439b6b14ad3cc35d05608ebca9bce01a25f5f8. systemd there is 261.3.
- devenv v2.4.0 = b904dcb51fe48c30db250038241507f60752f222.
- Source line numbers below are at the pinned revs.

Q1. GENERATED MOUNTS, UUID OVERRIDE, PRESET UUIDS
ANSWER
- For a GPT layout the generated device is `/dev/disk/by-partlabel/disk-<diskAttr>-<partName>`, not by-uuid.
- `lib.mkForce` on `fileSystems.<m>.device` to by-uuid works. The booted system's fstab carries it and the VM mounts correctly.
- Disko can fix UUIDs before formatting. A partition `uuid` option sets the GPT partition GUID (by-partuuid). `extraArgs = ["-U" uuid]` sets the ext4 UUID. `extraArgs = ["-i" "A1B2C3D4"]` sets the vfat volume ID.
- If a partition `uuid` is set, disko's own default device switches to `/dev/disk/by-partuuid/<uuid>` (gpt.nix:83-84).
EVIDENCE
- `nix eval` of `config.fileSystems` for disk attr `newsys`: `{"/":{"device":"/dev/disk/by-partlabel/disk-newsys-root","fsType":"ext4","options":["x-initrd.mount","defaults"]},"/boot":{"device":"/dev/disk/by-partlabel/disk-newsys-ESP","fsType":"vfat","options":["umask=0077"]}}`.
- Source: gpt.nix:90 (default device is by-partlabel), filesystem.nix:90-91 (`fileSystems.${mountpoint}.device = config.device`), filesystem.nix:23 and 57-58 (`mkfs.<fmt> ${extraArgs} "<device>"`), gpt.nix:289-291 (`--partition-guid=<n>:<uuid or R>`).
- VM test `makeDiskoTest` (q1-final.txt) with `fileSystems."/".device = mkForce "/dev/disk/by-uuid/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02"` and `/boot` = `by-uuid/A1B2-C3D4`. The disko destroy,format,mount step ran with mkfs `-U` and `-i`. The system then booted from the formatted disk.
- Booted `/etc/fstab`: `/dev/disk/by-uuid/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02 / ext4 x-initrd.mount,defaults 0 1` and `/dev/disk/by-uuid/A1B2-C3D4 /boot vfat umask=0077 0 2`.
- Booted `lsblk`: vda1 `disk-newsys-ESP` PARTUUID 11111111-...-501 UUID A1B2-C3D4 vfat /boot; vda2 `disk-newsys-root` PARTUUID ...-502 UUID aaaaaaaa-...-02 ext4 /.
- The harness replaced the by-id device with /dev/vdb, so by-id was not tested here. Q3 and Q4 do test it, with virtio serials as by-id.
STATUS: PROVEN.

Q2. PARTLABEL COLLISION
ANSWER
- The partlabel is `<disk type>-<disk attr name>-<partition name>`, so it comes from the attribute name. `disk.newsys` gives `disk-newsys-root`.
- If two disks carry the same label, `/dev/disk/by-partlabel/X` points at one of them. Which one depends on udev event order, and it was the old disk after one reboot.
EVIDENCE
- Source: gpt.nix:146 `label = "${config._parent.type}-${config._parent.name}-${partition.config.name}"`. A name over 36 characters is replaced by a sha256 prefix (gpt.nix:141-151).
- Disk attr `name` is the attribute name (disk.nix:10-14). `device` is a separate option (disk.nix:21).
- Collision VM test (q2a-raw.txt):
  - Disk A (vdb) was a GPT disk labelled `disk-main-ESP` and `disk-main-root`, holding a marker file.
  - Disko config named its disk `main` and pointed at disk B (vdc).
  - After destroy,format,mount, `by-partlabel` pointed at vdc and B was formatted. A's raw sha256 was unchanged.
  - `udevadm trigger --action=add` on vdb* made `disk-main-root -> ../../vdb2`.
  - The same trigger on vdc* flipped it to `vdc2`.
  - After a VM reboot `readlink -f /dev/disk/by-partlabel/disk-main-root` printed `/dev/vdb2`, which is the old disk.
  - Mounts by this label are therefore not safe when labels collide.
- Control (q2b-raw.txt): disk attr `newsys` gave `disk-newsys-*` on vdc and `disk-main-*` stayed on vdb. No collision.
STATUS: PROVEN. The order that wins is non-deterministic, shown here by trigger and reboot only.

Q3. MODES, DRY RUN, CONFIRMATION, SCOPE
ANSWER
- The `disko` CLI accepts `destroy`, `format`, `mount`, `unmount`, `format,mount` and `destroy,format,mount`. It also accepts the legacy `disko`, `create` and `zap_create_mount`.
- `--dry-run` only builds the script and prints its path. It runs nothing.
- Destroy,format,mount and destroy ask you to type `yes`, unless you pass `--yes-wipe-all-disks`. The legacy `diskoScript` does not ask.
- Destroy touches only disks listed in the config (with `destroy = true`, the default). A disk not listed kept its bytes exactly.
EVIDENCE
- Modes: `disko` lines 28-34 (help text); the accepted-mode check is lines 138-146. Line 10 sets `mode=mount` as the default.
  - Quirk: the `abort` message lists only 5 modes, but `unmount` is accepted.
  - Quirk: `--yes-wipe-all-disks` is forwarded only when mode is `destroy,format,mount` (`disko` lines 180-182). With `--mode destroy` the CLI wrapper does not forward it, so the prompt still appears.
- Mode actions (lib/default.nix):
  - `destroy` = `_destroy` (lines 927-957).
  - `format` = `_create`.
  - `mount` = `_mount`.
  - `unmount` = `_unmount`.
  - The combined modes chain these.
- Prompt: lib/default.nix:935 `if [ "$1" != "--yes-wipe-all-disks" ]`, then `read -rp ... Type 'yes'`.
- Scope: lib/default.nix:931 `disksToWipe = filterAttrs (disk.destroy) devices.disk`. Each disk runs `disk-deactivate "$dev"` (lib/default.nix:955-956). `disk-deactivate.jq` `init` returns `[]` for every disk that does not match the target. It matches by /dev name, by-id link or wwn.
- Side effect: `umount -Rv "${rootMountPoint}"` (default `/mnt`) runs before the wipe (lib/default.nix:909, 954). Anything mounted under `/mnt` on the host gets unmounted.
- Dry run on the host, evaluation only, against a FAKE nonexistent device `/dev/disk/by-id/FAKE-DISKO-DRYRUN-NONEXISTENT` (log.txt): `disko --dry-run --mode X` printed `/nix/store/...-disko-<mode>/bin/disko-<mode>` for all six modes. `--mode bogus` printed `aborted: mode must be one of ...`. This host run is the only disko CLI use outside a VM, and no disk was involved.
- Two-disk VM test (q3-final.txt, by-id `virtio-DISKA` and `virtio-DISKB`):
  - Config lists only DISKB. Disk A is whole-disk ext4 with a marker file.
  - `sha256sum` of A before: `60b5a2a8c4e9bf5c...`.
  - Ran: `echo no | destroy-format-mount` (printed `WARNING: ... - /dev/disk/by-id/virtio-DISKB ... Aborted.`, exit 1), then `--yes-wipe-all-disks`, unmount, mount, format (B's `/mnt/keep` file survived), `echo no | destroy` (aborted), `echo yes | destroy` (wipefs only on vdc, vdc1, vdc2), and the legacy `diskoScript` (no prompt).
  - Sha256 of A after everything: identical, `60b5a2a8c4e9bf5c...`. The marker was readable by a read-only mount afterwards. Test assertion `h0 == h1` passed.
- The VM test needs `-o ro` for the final mount. A normal mount of A changes its raw hash (superblock), which I saw in an earlier run.
STATUS: PROVEN. Not covered: LVM, mdadm and ZFS member cases on non-listed disks. The jq filter limits scope by source reading only.

Q4. DISKO-INSTALL
ANSWER
- Yes, v1.13.0 ships `disko-install` (package.nix:31-39 installs it, except on Darwin).
- It formats, mounts, copies the closure and runs `nixos-install` into `/mnt/disko-install-root` (default).
- Run from a live system, it needs no reboot. It touches only disks you map with `--disk NAME DEVICE`.
- It does NOT write EFI NVRAM entries by default. Only `--write-efi-boot-entries` does.
- The default `--mode format` wipes the mapped disk without any prompt.
EVIDENCE
- Flags (disko-install lines 5-25 and the parser at 56-157): `--mode format|mount`, `-f/--flake`, `--disk NAME DEV`, `--dry-run`, `--show-trace`, `--extra-files SRC DEST`, `--option`, `--write-efi-boot-entries`, `--system-config JSON`, `--mount-point` (default /mnt/disko-install-root). It requires root unless `--dry-run` (line 191).
- Flow: build (235-247), run the disko script (273), `--extra-files` (275-279), xcp the store (284-290), then `nixos-install --no-channel-copy --no-root-password --system ... --root` (292).
- Mode: line 49 `diskoAttr=diskoScript` (default) = `_disko` = `_legacyDestroy` + `_create` + `_mount`, with no confirmation (lib/default.nix:1034-1045). `--mode mount` uses `mountScript`, which only mounts.
- The default NVRAM behaviour comes from install-cli.nix:51 `boot.loader.efi.canTouchEfiVariables = lib.mkVMOverride writeEfiBootEntries` (default false). Line 41 maps `--disk` names over the config's `disk.<name>.device`, and install-cli.nix:18 throws if a disk name has no `--disk`.
- Parity: I checked on the host (evaluation only) that the toplevel, closureInfo and disko script `.drv` paths I prebuilt match what the real install-cli.nix produces. The VM re-computation matched too (q4-final.txt `PARITY`).
- VM test (q4-final.txt):
  - VM "machine" runs NixOS from disk A: OVMF/UEFI, systemd-boot, canTouch=true. B is an empty 12 GB disk with by-id `virtio-DISKB`.
  - The `disko-install` flake config uses the REAL by-id `nvme-eui.e8238fa6...` for the disk, remapped with `--disk newsys /dev/disk/by-id/virtio-DISKB`.
  - `--dry-run` printed `Would run: mkdir -p /mnt/disko-install-root`, ..., `Would run: nixos-install --system ... --root '/mnt/disko-install-root'`.
  - The real run (default flags, A kept running) ended with `installation finished!` and `disko-install succeeded`.
  - After the default run, A's ESP tree hash and A's partition table were unchanged, and `efibootmgr -v` was identical to baseline (`EFI unchanged by default run: True`).
  - B's ESP then held `EFI/BOOT/BOOTX64.EFI`, `EFI/systemd/systemd-bootx64.efi`, `EFI/nixos/*-bzImage.efi`, `loader/entries/nixos-*.conf`, and `lsblk` showed `disk-newsys-ESP` and `disk-newsys-root`.
  - Boot of B alone: a second VM got only B (bootindex=1) and fresh OVMF NVRAM. Firmware: `BdsDxe: starting Boot0002 "UEFI Misc Device"`. The guest printed `newsys`, root `/dev/vda2 ext4`, `/boot` `/dev/vda1 vfat`, `efi-booted`, `Current Boot Loader: systemd-boot 261.3`.
  - Booting A+B again with the saved NVRAM: it booted A (`machine`), BootOrder `0002,0004,0000,0001,0005` unchanged.
- Caveats:
  - `--dry-run` creates nothing, yet the script calls `realpath /mnt/disko-install-root`. On a host where `/mnt` is missing, the VM run failed to find the matching derivation. Create `/mnt` first.
  - The VM had no network, so I prebuilt the closure. The real server needs substitutes or network.
  - Read-only A: `disko-install` never mounted A.
STATUS: PROVEN for the VM scenario, including the default NVRAM behaviour. UNPROVEN: a real NVMe and a real firmware menu. The real root-disk contents of A were not hashed, because that disk is live. I hashed A's ESP and partition table.

Q5. EFI BOOT ENTRIES WITH TWO ESPs
ANSWER
- With `canTouchEfiVariables = true`, the installer creates NVRAM boot entries for the NEW ESP and puts them FIRST in BootOrder.
- It does not write to the old drive's ESP. It only touches the ESP that is mounted at `/boot` in the target root.
- With `canTouchEfiVariables = false`, the builder passes `--variables=no`. NVRAM stays unchanged. The new ESP still gets `\EFI\BOOT\BOOTX64.EFI`.
- `efiInstallAsRemovable` does not exist for systemd-boot. Only grub, limine and refind have it.
EVIDENCE
- nixpkgs systemd-boot-builder.py (nixos/modules/system/boot/loader/systemd-boot/):
  - line 35: `CAN_TOUCH_EFI_VARIABLES = "@canTouchEfiVariables@" == "1"`.
  - lines 498-499: `if not CAN_TOUCH_EFI_VARIABLES: bootctl_flags.append("--variables=no")`.
  - lines 508-511: `bootctl --esp-path=<ESP> <flags> install`.
  - lines 517-519: the update path sets `params["touchVariables"] = False` when canTouch is false.
  - The builder uses only `EFI_SYS_MOUNT_POINT` / `BOOT_MOUNT_POINT`.
- systemd 261.3 `bootctl-install.c`:
  - lines 239-249: `should_touch_install_variables` returns the explicit setting if given.
  - lines 1284-1345: `insert_into_order` puts a new slot at the top of BootOrder when the operation is `INSTALL_NEW`.
  - lines 1475-1497: creates the entry and inserts it.
  - lines 1615-1650: `install_variables` registers `\EFI\systemd\systemd-bootx64.efi` and a "Fallback ..." entry.
  - Slots are looked up per ESP partition UUID, so each ESP gets its own entry.
  - `--variables` is parsed in `bootctl.c:523-535`.
- nixpkgs efi.nix:5: `canTouchEfiVariables` default is false.
- `grep efiInstallAsRemovable` in nixos/modules: matches only install-grub.pl, grub.nix, limine-install.py, refind.nix, refind-install.py, azure/gce images, nixos-generate-config.pl.
- VM test (q4-final.txt) with `disko-install --mode mount --write-efi-boot-entries` on the running A:
  - Output: `Created EFI boot entry "Linux Boot Manager".` and `Created EFI boot entry "Fallback Linux Boot Manager".`
  - `efibootmgr -v` before: `BootOrder: 0002,0004,0000,0001,0005`.
  - `efibootmgr -v` after: `BootOrder: 0003,0006,0002,0004,0000,0001,0005`. Boot0003 = `HD(1,GPT,5d7a1592-...,0x800,0x100000)/\EFI\systemd\systemd-bootx64.efi` (B's ESP). Boot0006 = `Fallback Linux Boot Manager` on B's ESP.
  - Boot0002 (A's ESP) stayed as it was. A's ESP tree hash and partition table were unchanged by this run (`A ESP unchanged by run 2: True`). The NVRAM file sha256 changed.
  - The default run (no flag) printed the same bootctl lines but no "Created EFI boot entry" lines, and NVRAM stayed identical.
- Not proven: that the next boot goes to B. After a warm reboot in this harness the new entries were gone (`BootOrder: 0002,0004,0000,0001,0005`). A control test (q5nv-raw.txt) shows the cause is the VM, not disko or bootctl. A plain `efibootmgr -c` entry (Boot0003 DUMMYENTRY, BootOrder `0003,...`) also disappeared after a warm reboot and after shutdown+start. I did not find why the OVMF/QEMU setup drops guest-written entries. Persistence of guest-written NVRAM entries is UNPROVEN in this harness.
STATUS: PROVEN for what the tools write and which ESP they touch. UNPROVEN on real hardware. UNPROVEN: that the firmware boots B first because of BootOrder.

Q6. disko MODULE WITH devenv Machines
ANSWER
- devenv imports `disko.nixosModules.disko` for every NixOS machine. With empty `disko.devices` it is inert for the system closure: same `system.build.toplevel.drvPath`, same `fileSystems`.
- devenv also adds its own modules (`recovery.nix`, `facts.nix`). Those, not disko, make a devenv machine differ from a plain NixOS config.
EVIDENCE
- devenv `src/modules/machines.nix:145` `disko.nixosModules.disko`, the next lines list `./machines/recovery.nix` and `./machines/facts.nix`. `recovery.nix` adds the `devenv-machines-recover` systemd service.
- Eval (log.txt, Q6): a minimal nixosSystem with a root `fileSystems`, with and without the module, gives the same drvPath `/nix/store/cmllsbgssflm7v2icrbbr5vcbv7i13lr-nixos-system-server-26.11.20261008.e7439b6.drv`. Both give `{"/":{"device":"/dev/disk/by-label/x","fsType":"ext4","options":["x-initrd.mount"]}}`.
- The module only adds `system.build.*` attributes (format, mount, destroyFormatMount, diskoScript, vmWithDisko, ...). `enableConfig` is true, but `fileSystems` and `boot` are `mkIf`-ed to `cfg.devices._config.*`, which is empty (module.nix:307-309). With no disk, `system.build.format` throws `No disks defined, did you forget to import your disko config?`.
- devenv install flow (devenv/src/devenv/machines.rs:1982-2002, cli.rs:1098-1105): `diskoScript` (default) = destroy+create+mount with no prompt, `format` and `mount` modes available. The install first kexecs into an installer on the target host (machines.rs:346, 676-688). This is built for a fresh remote host, not a side-by-side install on a running machine.
STATUS: PROVEN for a minimal config. I did not eval the full devenv machine config. Bare configs with no root `fileSystems` fail with the usual root-filesystem assertion, so I used a root `fileSystems` in both variants.

Q7. VM TESTING OF A LAYOUT
ANSWER
- Disko provides `lib.testLib.makeDiskoTest`, `config.system.build.vmWithDisko`, `config.system.build.diskoImages` / `diskoImagesScript` and `config.system.build.installTest`.
- `makeDiskoTest` and `vmWithDisko` both booted my layout. `diskoImages` needs the locked nixpkgs of disko v1.13.0. On nixos-unstable e7439b6 it fails.
EVIDENCE
- `makeDiskoTest`: used in Q1. It formats, mounts, installs a systemd-boot system and boots it. The booted VM saw the by-uuid root and boot. lib/tests.nix:72 defines it, and module.nix:291-299 wires `installTest`.
- `diskoImages` / `vmWithDisko` on nixos-unstable e7439b6 with disko v1.13.0 (q7-build.txt): evaluation error `vmTools: the kernel argument (kernel-modules) has no target attribute, so the kernel image filename cannot be determined.` lib/make-disk-image.nix:44 builds `kernel` with `pkgs.aggregateModules`. Master has the same kernel code (the diff between v1.13.0 and master for make-disk-image.nix does not touch it). I did not build master.
- With disko's own locked nixpkgs 3327b113f2ef698d380df83fbccefad7e83d7769:
  - First attempt failed with `No space left on device`: default `imageSize` 2G was too small (q7-diskoimages-log.txt). The log also shows `mkfs.vfat -i A1B2C3D4 /dev/disk/by-partuuid/11111111-...-501` and `mkfs.ext4 -U aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02 /dev/disk/by-partuuid/...-502`. So preset UUIDs and by-partuuid work in disko's own image build.
  - With `disko.devices.disk.newsys.imageSize = "6G"` the build passed. `run-imgvm-vm` (headless, `virtualisation.vmVariantWithDisko.virtualisation.graphics = false`) printed `DISKO-VM-BOOTED root=/dev/vda2 aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02 boot=/dev/vda1 A1B2-C3D4` (q7-run.txt).
STATUS: PROVEN with the locked nixpkgs. A version mismatch with current nixos-unstable breaks `diskoImages` and `vmWithDisko` (cause confirmed in nixpkgs vmTools, fix not tried).

WHAT THIS MEANS FOR THE 4 TB DRIVE WITH THE 512 GB DRIVE AS FALLBACK
Facts, proven above:
1. Use a unique disk attribute name (for example `newsys`). Then the partlabels are `disk-newsys-*`. The default `main` can collide with any other disko-made disk on the host. A collision silently mounts or skips formatting depending on udev order (Q2).
2. Disko accepts the by-id path as `device`. The mounts it generates use partlabels, not the by-id path (Q1). You can pin by-partuuid with `partitions.<n>.uuid`, and ext4/vfat UUIDs with `extraArgs` (Q1). Set `fileSystems` to by-uuid with `mkForce` if you want that.
3. The wipe is limited to the disks in the config (`destroy` defaults to true). A disk not in the config keeps its bytes (Q3). The `/mnt` unmount side effect is a risk if the 512 GB drive is mounted under `/mnt`. Use `--root-mountpoint` or `disko.rootMountPoint` for a different path.
4. `disko-install` can run from the live 512 GB system and install onto the mapped 4 TB disk without a reboot. Its default mode wipes the mapped disk with no prompt (Q4).
5. By default `disko-install` forces `canTouchEfiVariables = false`, so NVRAM does not change. The 4 TB ESP is still bootable through `\EFI\BOOT\BOOTX64.EFI` (Q4 VM boot of B alone).
6. With `canTouchEfiVariables = true` the new install adds NVRAM entries ahead of the old ones in BootOrder. The 512 GB ESP is not modified (Q5). So the firmware may boot the 4 TB drive first. `--write-efi-boot-entries` is the only disko-install path that does this.
7. devenv's `diskoScript` has no prompt. `devenv machines install` first kexecs into an installer on the target host. Disko's module itself is inert with no disks (Q6).
8. disko v1.13.0 `diskoImages` / `vmWithDisko` do not work against nixos-unstable e7439b6. Use `makeDiskoTest` there (Q7).

Inferences, not proven:
- On the real server, `canTouchEfiVariables = true` on the new system would put the 4 TB drive first in BootOrder. The firmware menu choice then still selects the 512 GB drive. I could not test the firmware ordering or the reboot (VM NVRAM does not persist guest entries).
- The old system's ESP stays intact if its root is not mounted at the install's `/boot`. The old fstab is not read by the install.
- Real NVMe device names and the `nvme-eui.*` by-id link behave like the virtio serial links in the VM. Check `ls -l /dev/disk/by-id/` first.
- Recommended order: set `canTouchEfiVariables = false` for the first 4 TB install, keep the 512 GB entry first in BootOrder, then pick the 4 TB drive in the firmware menu. Flip the setting and rebuild after the first successful boot.

NOT DONE
- No test on a real NVMe or real firmware.
- Did not build disko master (725ea35) for Q7.
- Did not eval a full devenv machine config (only the disko-module-inert comparison).
- LVM/mdadm/ZFS cases for Q3 scope.

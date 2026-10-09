<!-- Raw final report of Agent F (install routes for the 4 TB drive, sonnet), 2026-10-09. Extracted unedited from the agent transcript (longest hand-back). Model output: an observation here is the agent's claim, backed by the raw logs it names under ~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/. -->

# Agent F report: devenv Machines install for the 4 TB NVMe, 512 GB kept as fallback

Raw log, repro files and scripts: `/home/andrew/.local/state/vendomat/v5/2026-10-09/devenv-alignment/agent-f/`. Versions are in `versions.txt`. Each result below names its log file. Temp dirs are removed.

Pins:
- devenv 2.4.0, rev b904dcb51fe48c30db250038241507f60752f222.
- nixpkgs nixos-unstable rev e7439b6b14ad3cc35d05608ebca9bce01a25f5f8.
- disko v1.13.0 (de5708739256238fb912c62f03988815db89ec9a). Latest tag, 2026-01-20.
- disko master 725ea35. Its `disko-install` is identical to v1.13.0.
- systemd 261.3, QEMU 11.1.1, OVMF 202608, nixos-facter 0.4.4.

The host I ran on is `server` itself (`hostname` = server). I used no sudo and opened no block device. I only read `/dev/disk/by-id` symlinks and EFI variables. All writes went to the QEMU VM.

## Real server facts (read-only)
- `nvme-eui.e8238fa6…` and `nvme-WD_Blue_SN5100_4TB_25459R800917` both point to `nvme0n1`. No `-part` links exist, so the 4 TB drive has no partitions.
- The 512 GB drive is `nvme-NX-512_2280_0040141310300` → `nvme1n1`, with 3 partitions. `/nix` is on `nvme1n1p3` with 65 G free.
- NVRAM now: `BootOrder: 0005,0000,0001,0002`.
  - Boot0005 "Linux Boot Manager" is on ESP partuuid 08b493db-8918-44f5-8796-204e3426e132.
  - Boot0000 "Windows Boot Manager" is on a different ESP, partuuid 24b0b0a5-….
  - Boot0001 and Boot0002 are Onboard NIC (IPv4 and IPv6) entries.
- `/mnt` is an empty directory and is not a mountpoint. `findmnt /mnt` printed nothing.
- sshd has `PermitRootLogin prohibit-password` and `PasswordAuthentication no`.
- `/etc/ssh/authorized_keys.d/` holds only `andrew`. A root key login is therefore not set through NixOS. UNPROVEN whether `/root/.ssh/authorized_keys` exists, because the directory is unreadable to me.

Logs: `q1-env.log`, `q2-server-facts.log`.

## Test rig
The VM runs NixOS from disk A, on NVMe serial `NX512A0001`. It has an empty disk B (40 GB, serial `WD4TBB0001`) and OVMF with persistent NVRAM.
- I seeded A's NVRAM with `bootctl install`, as on the real server. That gives "Linux Boot Manager" as first boot entry.
- The by-id name `nvme-eui.…` could not be reproduced. The kernel ignored the QEMU NGUID. I used `/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_WD4TBB0001`.
- The controller is this host, using devenv 2.4.0 against `root@127.0.0.1:22822`.
- The first A image was 6 GB and too small for `disko-install`. I rebuilt it at 20 GB. Only the first install run used the 6 GB image.

---

## Q1. What each phase runs (machines.rs at b904dcb)

ANSWER:
- **No confirmation prompt.** `install` requires machine names (`cli.rs:1396-1404`).
- **Preflight** runs only when the `kexec` phase is selected (`machines.rs:1617`). It checks `id -u` is 0 and that `tar` and `curl` exist (`:1850`).
- **kexec** (`:1899-1900`) runs `curl --fail -L <url> | tar xzf - -C /root && /root/kexec/run`.
  - The default URL is the nixos-images `nixos-unstable` `nixos-kexec-installer-noninteractive-<arch>.tar.gz` (`:677-690`).
  - The tarball's `/root/kexec/run` copies root's `authorized_keys`, the SSH host keys and the network config into the installer initrd.
  - It then runs `kexec --load`. After 6 s a background `kexec -e` fires. The script does not call `systemctl kexec`.
  - The `kexec -e` help text reads "Execute a currently loaded kernel".
  - The old OS gets no clean service stop (from this script and help text; I did not capture a shutdown trace).
- **facter** runs the bare command `nixos-facter` over SSH (`:74`, `:1942`).
  - It writes `.machines/<name>/facter.json` locally and runs `git add --intent-to-add` (`:1959`). A git failure is non-fatal.
- **Order and checks:**
  - After facter, devenv refuses to install if no root authentication is declared (`:1664`).
  - It builds the toplevel before any disk change (`:1681`).
- **disko** (`:1991-1993`): the mode picks the script.

  | Mode | Script | What it does |
  |---|---|---|
  | `disko` | `diskoScript` | destroy, format, mount |
  | `format` | `diskoFormatScript` | `_create` only, no mount (disko `lib/default.nix:842-846`) |
  | `mount` | `diskoMountScript` | `_mount` only |

  - devenv runs `nix copy` of the script to the target, then runs it with no arguments (`:1996-2001`).
  - In disko v1.13.0, `diskoScript` is `_legacyDestroy` + `_create` + `_mount` (`lib/default.nix:852-856`, `:1042`). It has no confirmation.
  - `_legacyDestroy` runs `umount -Rv "/mnt" || :`. It then runs `disk-deactivate` on each disko disk with `destroy = true` (`:909-914`).
  - The mount root defaults to `/mnt` (`lib/default.nix:3`). devenv never overrides it.
- **install** (`:2019`) runs `nixos-install --system <toplevel> --no-root-password --no-channel-copy`.
  - There is no `--root`, so the root is `/mnt` (`nixos-install.sh:16`).
  - There is no `--no-bootloader`, so the bootloader installs. `NIXOS_INSTALL_BOOTLOADER=1 nixos-enter --root … switch-to-configuration boot` (`nixos-install.sh:310`) does it.
  - `nixos-enter` rbind-mounts `/sys` (`nixos-enter.sh:64`). The chroot can therefore reach efivarfs.
  - NVRAM writes follow `boot.loader.efi.canTouchEfiVariables`. `systemd-boot-builder.py:35` reads it and `:498-499` appends `--variables=no` when it is false.
  - devenv has no NVRAM code. The NVRAM write comes from nixos-install.
- **After install:** optional `copyHostKeys` runs `cp /etc/ssh/ssh_host_* /mnt/etc/ssh/` (`:2259`).
- **reboot:** plain `ssh … reboot`, then it waits up to 30 s for a boot-ID change (`:2271`, `:2286`).

EVIDENCE: the file:line citations above, plus VM logs `q2-run2-install.log` and `q4-novars-install.log`.

STATUS: PROVEN (source plus VM runs).

---

## Q2. `--phases facter,disko,install` on a host already running NixOS from disk A

ANSWER: yes. It worked in the VM with these caveats:

1. **`nixos-facter` is not on the target PATH by default.** The `facter` phase failed before any disk change, and `.machines/` was not created.
   - Raw output from `q2-run1-nofacter.log`:
     - devenv: `newsys: nixos-facter failed on machines.newsys — is the NixOS installer running?`
     - SSH: `bash: line 1: nixos-facter: command not found`, exit 127.
   - `nix profile add <path>` works. `/root/.nix-profile/bin` is on the non-interactive SSH PATH.
   - Skipping the `facter` phase also works when `.machines/<name>/facter.json` already exists. I ran `--phases disko` and `--phases disko,install` on a VM without `nixos-facter` and they succeeded.
   - On the real server, `nixos-facter` was not on PATH in my shell. UNPROVEN for root's SSH PATH.
2. **disko scope.**
   - The script ran `realpath /dev/disk/by-id/nvme-QEMU…WD4TBB0001` → `/dev/nvme1n1`. Only that disk was walked, though `lsblk -a` listed A too.
   - `umount -Rv /mnt || :` unmounts anything at `/mnt`. Test: a tmpfs mounted at `/mnt` was unmounted by the disko phase (`q2-mnt-disko.log`: `umount: /mnt unmounted`).
   - The server's `/mnt` is not a mountpoint now. UNPROVEN whether it has submounts; `findmnt /mnt` showed nothing.
3. **`--disko-mode format` is hazardous on a live host.** It does not mount, so `nixos-install` targets the running system's `/mnt` directory.
   - Run: `--phases disko,install --disko-mode format` with `/mnt` absent failed with `mount point /mnt doesn't exist`.
   - Run: `--phases install` with `/mnt` present wrote a 2.6 GB system tree into A's root. Disk use went 3.2 G → 5.8 G.
   - The bootloader step then failed with `efiSysMountPoint = '/boot' is not a mounted partition`. NVRAM was unchanged.
   - Logs: `q2-format-mode*.log`, `q2-format-mode-install-unmounted-effect.txt`.
   - Use `--disko-mode disko` (default). Do not use `format` or `mount` unless you mount first.
4. **Mounts stay.** After the run, B stays mounted at `/mnt` and `/mnt/boot` (`q2-state-B-after-install.txt`). Unmount before any other work.
5. **NVRAM.** With `canTouchEfiVariables = true`, devenv/nixos-install created two new entries and put them first in BootOrder:
   - Before: `BootOrder: 0007,0008,0000,…`
   - After: `BootOrder: 0009,000A,0007,0008,0000,…`
   - Boot0009 and Boot000A sit on B's ESP.
6. **Root check.** The uid-0 preflight only runs with the `kexec` phase. Without it, a non-root SSH user fails later in `nixos-install`. I did not test a non-root user.

Controller on the target itself (the real server's case):
- A non-root user `ctl` with `target.host = "root@localhost"` completed `--phases facter,disko,install` in 87 s (`q2-local-after.txt`).
- Root as controller on NixOS fails with `Failed to open Nix store … cannot remount "/nix/store" writable: not in a private mount namespace`. Setting `NIX_REMOTE=daemon` fixes it (`q5-selfdeploy.log`, `q5-selfdeploy-daemon.log`). Run devenv as `andrew`, not root.

Disk A untouched (`q2-state-A-before.txt`, `q2-state-A-after-install.txt`, `diskA-hash-*.txt`, `diskA-esp-diff-after-q2.txt`):
- GPT dump sha is identical before and after.
- The `/boot` file tree sha (excluding `random-seed`) is identical.
- The raw first-1MiB and last-1MiB sha256 match the baseline. The ESP file tree diff shows only `loader/random-seed`, which systemd-boot rewrites on every boot.
- The marker file is intact.
- A's NVRAM entries 0007 and 0008 are unchanged.
- A's root filesystem changes during normal running, so I give no whole-disk checksum. Install also copies the toplevel into A's store.

Disk B boots (`q2-bootB.log`): booted with only B attached. `hostname` = newsys, `/etc/newsys-marker` = NEWSYS-GENERATION-1, `BootCurrent: 0009`.

STATUS: PROVEN in the VM. UNPROVEN on real firmware and real hardware.

---

## Q3. Routes

Common to a, b and c: the server stays up and its services keep running during the install. Downtime is only the final reboot or one-time boot into the new system.

### a. Manual partition + `nixos-install --root /mnt --system <prebuilt toplevel>`
- Ran in the VM: `sfdisk`, `mkfs`, mount, then `nixos-install --root /mnt --system <novars toplevel> --no-root-passwd --no-channel-copy`. It succeeded (`q3a-nixos-install.log`).
- **Pitfall.** A disko-derived toplevel's fstab uses `/dev/disk/by-partlabel/disk-main-root` and `disk-main-ESP` (`q3a-fstab.txt`).
  - With plain `sfdisk` and no partlabels, B failed to boot. The serial log shows `Timed out waiting for device /dev/disk/by-partlabel/disk-main-root` and "root account is locked" (`q3a-boot-manual-partition-fail.txt`).
  - Labelling the partitions `disk-main-root` and `disk-main-ESP` should fix it. UNPROVEN, not tested.
- Needs: root on the server, the toplevel built (`devenv build machines.<n>.build.nixos`) and copied, and partitions made by hand or by the disko script.
- NVRAM: follows the toplevel's `canTouchEfiVariables`. It was false in the test, so there was no NVRAM change.

### b. `disko-install` (v1.13.0)
- Flags (`disko-install`): `--flake URI#ATTR`, `--disk NAME DEVICE`, `--mode format|mount`, `--write-efi-boot-entries`, `--mount-point` (default `/mnt/disko-install-root`), `--extra-files`, `--system-config`, `--dry-run`.
- It builds its own toplevel with `canTouchEfiVariables = writeEfiBootEntries` (default false; `install-cli.nix:6`, `:51`). Its generation 1 therefore differs from the `devenv build` toplevel.
- It requires a flake with `nixosConfigurations.<name>`. That is not native Machines.
- **Failed as shipped in the VM.** The step `Copying store paths` died with `[ERROR] Error copying … nix-2.34.8-doc/…/favicon-de23e50b.svg … Read-only file system (os error 30)`. Then the bootloader step failed (`q3b-disko-install-noefi.log`).
  - Standalone `xcp 0.24.2` reproduces it on that path (`q3b-xcp-repro.log`). `cp -a` of the same path works.
  - Root cause UNPROVEN. It may depend on the closure contents.
- After I patched `xargs xcp --recursive` to `xargs cp -a` in a copy of the wrapper:
  - Without `--write-efi-boot-entries`: success, no "Created EFI boot entry", BootOrder unchanged (`q3b-A-after-noefi.txt`).
  - With `--write-efi-boot-entries`: success, new entries first (`BootOrder: 0009,000A,0007,…`; `q3b-A-after-efi.txt`).
  - A's GPT and `/boot` hashes were unchanged in both runs.
- It needs network (`nix run github:…`) unless the disko package is pre-fetched.

### c. `devenv machines install --phases facter,disko,install` against `root@localhost` or the tailnet name
- Proven in Q2, including controller = target as non-root user `ctl` → `root@localhost`.
- Time in the VM: 68 s total, with an 18.9 s build.
- Needs: `nixos-facter` on the target PATH, or a pre-generated `facter.json` plus skipping the `facter` phase. Also root SSH key login to the server, which is not configured now (see the server facts).

### d. Boot `server` from an installer USB, then run `--phases facter,disko,install,reboot`
- I booted a minimal ISO built from nixpkgs e7439b6 with my root SSH key. Disk A was visible but unmounted.
- From the host controller, the run took 46 s. `hostname` = nixos afterwards. B booted alone as newsys (`q3d-B-boot.txt`).
- A's GPT was unchanged. NVRAM changes in that run cannot be judged. Plain booting the ISO under QEMU/OVMF with a bootindex rewrote BootOrder and dropped A's entries (`q3d-control-iso-boot-nvram.txt`). This is a QEMU/OVMF artefact, not devenv.
- **Stock ISO gaps.**
  - The nixpkgs installer modules do not mention `nixos-facter`, so the `facter` phase fails on a stock ISO. My ISO added it. Alternatively skip the phase with a pre-generated report.
  - `nix-command` is disabled in the ISO.
- **Controller on the USB itself** works, with two tweaks (`q3d-iso-hosted-controller.log`):
  - `NIX_REMOTE=daemon` is needed for the "cannot remount /nix/store" error.
  - `NIX_CONFIG="experimental-features = nix-command flakes"` is needed. Without it the step fails with `Failed to copy disko script to target`.
- After the `reboot` phase, the VM returned to the ISO because the ISO was first in boot order. Remove the USB before that phase.
- `framework` is not required if the controller runs on the USB. If `framework` is the controller, it must reach the ISO over LAN with the root key. Its availability is unknown to me.

### e. Full `devenv machines install` with kexec from another controller (VM run: controller = host, target = A)
- Timeline (`q3e-availability.log`): A up until 14:01:41. The kexec installer answered SSH at 14:01:43. DOWN at 14:02:38. A back up at 14:02:52. That is about 71 s of A's services down from kexec to return, in the VM. devenv's own wall time was 77 s.
- The old kernel is replaced by a direct `kexec -e`, with no service stop or unmount (from the script source).
- A's disk: the GPT hashes match, and the ESP tree differs only in `random-seed`. The installer does not mount A.
- It returned to A (novars config, no NVRAM change), BootCurrent 0007.
- Real-hardware numbers differ: BIOS POST, a 471 MB tarball download, closure copy, and 457 MB of installer RAM. The docs say about 1 GB free RAM is needed.
- The kexec installer image comes from GitHub, so the server needs internet at that moment.

### f. Move the 4 TB drive to another machine, install there, move it back
- VM emulation (`q3f-moved-drive-fresh-nvram.txt`): B installed with `canTouchEfiVariables = false`, then booted alone on a VM with fresh OVMF NVRAM. It booted via the firmware's automatic entry for `\EFI\BOOT\BOOTX64.EFI` (`BootCurrent: 0002`, hostname newsys).
- If `canTouchEfiVariables = true` on the other machine, its NVRAM entries do not travel with the disk. Use the firmware menu or `efibootmgr -C` on the server.
- The facter report must come from `server` (the real hardware), not the other machine. The initrd modules for the server's controller must be in the config.
- Real-firmware behaviour is UNPROVEN.

### Route summary

| Route | Downtime | Controller | Risk to 512 GB drive | Laptop | Proven in VM | Blockers |
|---|---|---|---|---|---|---|
| a | none until cutover | server (root shell) | `/mnt` use, store growth; NVRAM only if toplevel allows | no | yes (install). Boot only after labelling partitions (not tested) | partlabel pitfall; root shell |
| b | none until cutover | server | `/mnt/disko-install-root` (not `/mnt`); NVRAM only with the flag | no | partly (needed an xcp patch) | `xcp` EROFS; needs a flake, not Machines |
| c | none until cutover | server or other host (root@localhost works) | `umount -R /mnt`; `format` mode writes into A's root; NVRAM if canTouch=true | no | yes | `nixos-facter` on PATH; root SSH key; `NIX_REMOTE=daemon` if root |
| d | whole install, services offline | other host or USB-hosted | low: A unmounted; reboot phase returns to the USB if it stays first | no if USB-hosted | yes (VM ISO, B boots) | ISO lacks `nixos-facter`/nix-command; USB wiring |
| e | ~71 s in VM, longer on real hardware | other host | unclean stop of A's services (no unmount); A's disk untouched in VM | other host needed | yes | internet for tarball; RAM; physical access if it fails |
| f | none for server; drive is out | other machine | none, if the 512 GB drive stays | optional | partly (fresh-NVRAM boot) | facter report from `server`; NVRAM entries lost |

STATUS: a, c, d, e PROVEN in VM. b PARTLY (patched). f PARTLY.

---

## Q4. EFI and fallback (nixpkgs e7439b6, `systemd-boot-builder.py`)

ANSWER:
- **Every route that runs `nixos-install` also installs the bootloader.** NVRAM changes only when the installed config has `boot.loader.efi.canTouchEfiVariables = true`.
  - For routes a, c, d, e and f this is the toplevel's own value.
  - For `disko-install` it is the flag `--write-efi-boot-entries` (default false; `install-cli.nix:51`).
- **With `canTouchEfiVariables = false`:**
  - The builder passes `--variables=no` (`systemd-boot-builder.py:498-499`). The option name is `--variables=no`, not `--no-variables`.
  - B still gets `EFI/systemd/systemd-bootx64.efi` and `EFI/BOOT/BOOTX64.EFI`, so the firmware boot menu can pick it.
  - Proven in the VM: no "Created EFI boot entry" in the log, BootOrder unchanged (`q4-novars-A-after.txt`).
- **With `canTouchEfiVariables = true`:** new "Linux Boot Manager" and "Fallback Linux Boot Manager" entries go to the front of BootOrder. The new disk becomes the default (`q2-state-A-after-install.txt`).
- **`efiInstallAsRemovable` is not available for systemd-boot at this rev.** It exists only for grub (`grub.nix:709`) and limine. systemd-boot always writes the `EFI/BOOT/BOOTX64.EFI` fallback.
- **Boot B once, keep A the default.** Both parts proven in the VM:
  - `efibootmgr -n <B firmware entry>` plus `reboot` booted B once. The next boot returned to A as default (`q4-novars-T3-bootnext.txt`).
  - `efibootmgr -C -d /dev/disk/by-id/<4TB> -p 1 -L newsys-trial -l '\EFI\systemd\systemd-bootx64.efi'` creates an entry outside BootOrder. `efibootmgr -n` then boots it once (`q4-efibootmgr-C-bootnext.txt`).
- **The new disk alone boots by the firmware entry** (`q4-novars-T2.txt`). The OVMF boot was slow here because of PXE timeouts.
- **Plan.** Install first with `canTouchEfiVariables = false` (or without `--write-efi-boot-entries`). Boot with `-C` plus `-n`, or the firmware menu. After the new system is proven, set `canTouchEfiVariables = true` and run `bootctl install` once on the new system.
  - UNPROVEN: whether a later deploy writes the entry by itself. The builder runs `bootctl update` on non-install runs and may create nothing.
  - UNPROVEN: `efibootmgr -o` to restore order after an accidental reorder. It is standard but I did not run it.
- **OVMF caveat.** QEMU `bootindex` rewrites BootOrder and can drop entries (control test above). Real firmware may differ.

STATUS: PROVEN in VM for the false/true/BootNext cases and for the source flag. UNPROVEN on the server's firmware.

---

## Q5. Management after install

ANSWER: proven in the VM on the installed B system. `sshd`: `PermitRootLogin prohibit-password`, key-only.
- `devenv machines status newsys` before the first deploy:
  ```
  { "newsys": { "version": 1, "phase": "uninitialized" } }
  ```
- `devenv machines deploy newsys --yes` (generation 2). The log shows a plan with Running/Profile/Requested/Executor store paths and `Closure: +3 / -3 store paths`. It saved plan `plan-qzZZupl3…`, copied 3 + 2 paths and printed `newsys: deployed`. Total 20.6 s. `/etc/newsys-marker` became NEWSYS-GENERATION-2 (`q5-deploy.log`).
- Recorded state on the target, `/var/lib/devenv-machines/current.json`, and `status`:
  - `operation: deploy`, `phase: succeeded`, `previousSystem` / `requestedSystem` store paths, a `deployment-…` id and `unit: devenv-machine-deployment-….service`.
  - Also present: `/var/lib/devenv-machines/lock`, gcroots `/nix/var/nix/gcroots/devenv-machines/deployment-*/{previous,requested,executor}`, a recover service, and a watchdog service and timer.
- `devenv machines rollback newsys` restored generation 1. `status` then showed `operation: rollback`, `phase: succeeded`, and the marker returned to NEWSYS-GENERATION-1 (`q5-rollback.log`).
- **Self-deploy.**
  - As non-root `ctl` with `target.host = "root@localhost"`: `newsys: deployed` (generation 4; `q5-selfdeploy-nonroot.log`).
  - As root: first attempt failed with the mount-namespace error; with `NIX_REMOTE=daemon` it succeeded (generation 3; `q5-selfdeploy-daemon.log`).
  - Self-deploy works. The controller user should be non-root.
- **Requirement for the real server.** `server` must accept root SSH key login from the controller user. Currently only `andrew` has a key file in `authorized_keys.d`. Set `users.users.root.openssh.authorizedKeys.keys` in the new config. devenv refuses to install without root auth declared (`machines.rs:1664`).

STATUS: PROVEN in VM.

---

## Recommended route (my reading, not a proven requirement)
Route c from the running server, run as `andrew`:
1. Pre-generate the facter report with `nix run nixpkgs#nixos-facter` on the server, or put the tool on PATH for root. Commit `.machines/<n>/facter.json`.
2. Set `canTouchEfiVariables = false` for the first install.
3. Use `--disko-mode disko` (the default). Confirm that `/mnt` has no submounts, and use the by-id path in the disko config.
4. Unmount `/mnt` after the run.
5. Boot the new disk once with `efibootmgr -C` plus `-n`.
6. After proof, enable `canTouchEfiVariables` and run `bootctl install`.

If anything about the host needs offline work, route d with the controller on the USB is the next best.

## Caveats
- All timings come from the VM. Real hardware adds firmware POST, closure copy time and disk speed.
- `disko-install` v1.13.0 worked in the VM only after my `xcp` → `cp -a` patch.
- Raw logs hold the full command output. Large devenv logs contain noise: filter with `scripts/filt.sh` in `repro/scripts/`.

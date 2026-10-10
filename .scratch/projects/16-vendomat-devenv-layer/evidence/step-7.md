# Step 7 — the fresh server disk route in a two-disk VM

**Date:** 2026-10-10. **Gate:** G7. **Status:** PASS for every refusal and for the install route.
One item of the gate FAILS in the VM: `systemctl --failed` is not empty on the new system. The
cause is a unit of the server role that needs a secret (finding N1). The route itself is proven in
QEMU. The real firmware and the real 4 TB drive are still unproven.

An earlier pass (2026-10-09) found defects D1 to D5, W1 to W3, G1, C1, and C2, and stopped on a
DISK blocker. Those fixes are in vendomat `main`. This record is the rerun with the repository
program, the repository wrapper, and the fork CLI `v2.4.0-vendomat.2`. No patched scratch copy of
any program ran. The earlier pass keeps its logs under `run1/`.

## Pins and tools

| Item | Value |
| --- | --- |
| Patched devenv CLI | `/nix/store/3mfmgg65mf08h7rhwd7w4f2vvcr9ia9i-devenv-wrapped-2.4.0/bin/devenv`, `devenv 2.4.0+e2acb5b`, tag `v2.4.0-vendomat.2` |
| Wrapper and preflight | vendomat `main` `90f4f3ab` (the Step 7 fixes are in `f09ee323`): `src/vendomat/machine.py`, `preflight/vendomat-preflight` |
| nix-systems | `main` `53000247`, copied to a scratch workspace; only `inventory/default.nix`, the VM target, and the install payload differ |
| Collection | `git daemon` on `127.0.0.1:19477`, tags `v0.7.0` (vendomat tree) and `v2.4.0-vendomat.2` (fork mirror) |
| Nix, nixpkgs, disko | 2.34.7, `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, v1.13.0 |
| QEMU, OVMF | 11.1.1 `qemu-host-cpu-only`, OVMF 202608, KVM, q35, persistent `OVMF_VARS` copy |
| Guest tools | util-linux 2.42.3, kernel 6.18.55 (old and new system) |
| Server closure | `nixos-system-server-26.11.20261008.e7439b6`, 3.4 GiB (Home Manager and services included) |

VM identities: old disk `…nvme-QEMU_NVMe_Ctrl_VMOLD0000000001`, 17179869184 bytes, role `keep`.
New disk `…nvme-QEMU_NVMe_Ctrl_VMNEW0000000001`, 42949672960 bytes, role `install-target`. Model of
both is `QEMU NVMe Ctrl`. The preset PARTUUIDs and UUIDs are the repository's `ids` block.

Raw logs: `~/.local/state/vendomat/v6/2026-10-09/07-disk-vm/run2/` (`matrix/`, `direct/`,
`success/`, `matrix-table.md`). Harness: nix-systems `tests/disk/` (`README.md` lists the order).

## Gate table

| Gate | Result | Raw log (under `run2/`) |
| --- | --- | --- |
| Layout: preset PARTUUIDs and UUIDs, own ESP, mount by UUID after boot of the new disk alone | PASS | `success/new-alone-facts.txt`, `success/new-disk-layout-from-old.txt` |
| Baseline of old disk and blank disk | PASS | `success/baseline-capture.txt`, `success/baseline-hashes.json` |
| Injection matrix: 25 cases through the wrapper | PASS (25 of 25) | `matrix/`, `matrix-table.md` |
| Direct patched CLI: 10 cases | PASS (10 of 10) | `direct/` |
| Success path: wrapper install with payload | PASS | `success/wrapper-install.log` |
| Old disk, ESP hashes, `efibootmgr -v` equal baseline after the install | PASS | `success/post-capture.txt` |
| New disk alone boots; UUIDs, key-only SSH, payload, no secret in store | PASS | `success/new-alone-facts.txt` |
| `systemctl --failed` empty on the new system | FAIL (N1) | `success/new-alone-facts.txt` section `failed-units` |
| One-time entry, `BootNext`, reboot into new system, reboot back | PASS | `success/both-*.txt` |

## Success path

Command: `python -m vendomat.cli machine install server --root <ws> --no-version` with
`VENDOMAT_DEVENV` set. The workspace sets `install.secrets` (a run-time random value, from a tmpfs
file), `install.extraFiles`, and `install.copyHostKeys = true`. Expected: exit 0. Actual: exit 0
in 69 to 71 s. No SSH shim and no patched program.

| Step | Expected | Observed |
| --- | --- | --- |
| Baseline, old disk | first MiB `bea9c45a…`, last MiB `b4e3b0b5…`; blank disk zero in first and last 16 MiB | as expected |
| Wrapper output | no secret value | none (the check ran before the log was written; the log is redacted) |
| After the wrapper | `/mnt` unmounted, no swap on the new disk | `findmnt /mnt` empty, `/mnt` empty; `/proc/swaps` empty |
| Old disk after the install (same boot) | `sfdisk --dump`, `lsblk`, 8 ESP file hashes, `efibootmgr -v`, first and last MiB equal | all equal |
| New disk layout | PARTUUIDs `…4e5300000001/2/3`, filesystem UUIDs `4E53-0001`, `…12`, `…13`, ESP type `C12A7328-…`, no PARTUUID in common with the old disk | all equal |
| Boot of the new disk alone (persistent OVMF vars, no NVRAM write by the system) | SSH up | up after 143 s; `BootCurrent` `0002`, the firmware's auto-created NVMe entry; the old `Boot0007` entry could not match; the ESP holds `EFI/BOOT/BOOTX64.EFI` (inference: the auto entry used that removable path) |
| Root and boot mounts | by UUID | `/` `…4e5300000013` ext4, `/boot` `4E53-0001` vfat; `/etc/fstab` by-uuid |
| SSH | key only | `PasswordAuthentication no`, `PermitRootLogin prohibit-password`; a password attempt gave `Permission denied (publickey)`; the old pinned host key verified (`copyHostKeys`) |
| Payload | `token` 400 `root:root`, `extra` 640 `root:root`, sha256 equal | equal |
| Secret in a store path | none | `grep -rlF` of the new system's `/nix/store`: none. 0 new store paths on the controller held it |
| `systemctl --failed` | empty | 1 unit: `tailscaled-autoconnect.service` (N1) |

### One-time boot and fallback (OVMF 202608)

1. Both disks, default boot: `hostname` `oldserver`, `BootCurrent` `0007` (`Old NixOS`).
2. `efibootmgr -C -d <new disk> -p 1 -L vendomat-new -l '\EFI\systemd\systemd-bootx64.efi'`
   created `Boot0008`. `BootOrder` did not change (`-C` is create-only).
3. `efibootmgr -n 0008` set `BootNext: 0008`; `systemctl reboot`.
4. Booted `server` (the new system); `BootCurrent` `0008`; `BootNext` gone.
5. `systemctl reboot` again: `oldserver` returned (BootNext is one-shot).

After those three boots the old disk differed from the baseline in exactly these ways:
`loader/random-seed` (systemd-boot rewrites it at each boot of the old system), the added
`Boot0008`, and `BootOrder` (OVMF moved its two auto-created NVMe entries `0002`, `0003` behind
the PXE entries after the boot of the new disk alone). The first entry `0007` stayed first.
`sfdisk --dump` and the other ESP files were equal.

What real firmware may do differently (unproven): keep or drop a created entry across power
cycles; write NVRAM on a failed entry; not honour `BootNext`; reorder or remove entries; show a
boot menu; treat the `HD(1,GPT,…)` path or the removable path with other rules; Secure Boot,
a TPM measurement, or a vendor default can pick another loader; the new NVMe disk and its
by-id name may differ in model, serial, and Intel VMD behavior. These stay open (Step 9).

## Injection matrix (wrapper, one fresh copy-on-write overlay per case)

Every case: exit non-zero; the output names the failed check; new-disk content hash equal
before and after; old-disk first and last MiB, `sfdisk --dump`, ESP hashes, `efibootmgr -v` equal;
`/mnt`, swap, and device-mapper state equal. `matrix-table.md` holds the full refusal texts.

| Case | Injection | Exit | Failed check named | Result |
| --- | --- | --- | --- | --- |
| a | inventory model `QEMU NVMe Ctrl X` | 2 | `identity` | PASS |
| b | inventory serial `VMNEW0000000002` | 2 | `identity` | PASS |
| c | overlay virtual size 41 GiB | 2 | `identity` | PASS |
| d | ext4 signature | 2 | `no-signature-wipefs`, `no-signature-blkid` | PASS |
| e | empty GPT | 2 | `no-signature-wipefs`, `no-signature-blkid` | PASS |
| e2 | GPT with one partition, no filesystem | 2 | `no-partitions`, signatures | PASS |
| f | mounted ext4 partition | 2 | `not-mounted`, `no-partitions`, signatures | PASS |
| g | active swap on a partition | 2 | `not-mounted`, `no-partitions`, signatures | PASS |
| h | device-mapper linear map | 2 | `no-holders` (`dm-0`) | PASS |
| i | install-target is the running disk, no `keep` entry | 2 | `not-mounted`, `no-partitions` (disk A) | PASS |
| i2 | install-target and `keep` share A's by-id path | 2 | module guard: "an install-target has the same by-id path as a keep or existing-system disk" (G1 closed) | PASS |
| j | by-id path absent | 2 | `resolve:` (C2 closed: the CLI prints it first) | PASS |
| k | file in `/mnt` | 2 | `mnt-clear` | PASS |
| l | tmpfs at `/mnt/sub` | 2 | `mnt-clear` ("mounted at or under /mnt", D5 closed) | PASS |
| l2 | tmpfs at `/mnt` | 2 | `mnt-clear`; the mount stayed (W2 closed) | PASS |
| m | `wipefs` absent from PATH | 2 | `tools` (missing wipefs), result `unknown` | PASS |
| m2 | `grep` absent | 2 | `tools` (missing grep) | PASS |
| m3 | `awk` absent | 2 | `tools` (missing awk) | PASS |
| m4 | `wipefs` present, not executable | 2 | `tools` | PASS |
| m5 | `grep` not executable, partition mounted | 2 | `tools` | PASS |
| m6 | `awk` not executable, swap active | 2 | `tools` | PASS |
| x1 | `grep` not executable, blank disk | 2 | `tools` | PASS |
| x2 | `awk` not executable, blank disk | 2 | `tools` | PASS |
| o | `keep` by-id path absent, blank disk | 2 | `protected-resolves` (`unknown`) | PASS |
| n | program replaced by one that prints pass with nonce `000…0` | 2 | CLI: "carries a different nonce" | PASS |

Notes: after a refusal the wrapper prints "Nothing was unmounted. Inspect the target before you
unmount /mnt or run the install again". Case i2 stops at module evaluation, before any target
contact. Cases m to x2 hid the tool inside the guest by a bind mount over the `system-path/bin`
directory (absent) or over the binary (not executable).

## Direct patched CLI

Command: `devenv machines install server …`, program from the Vendomat module unless noted.

| Case | Arguments | Exit | Observation | Result |
| --- | --- | --- | --- | --- |
| direct-no-program | `--phases disko,install`, program unset | 1 | "Refusing to install … set no `vendomat.preflight.program` … made no connection to the target" | PASS |
| direct-failing-program | program exits 1 | 1 | "the preflight did not pass" | PASS |
| direct-wrong-nonce-program | wrong nonce | 1 | "carries a different nonce" | PASS |
| direct-mode-format | `--phases disko --disko-mode format` | 1 | program: `phases` and `disko-mode` failed; new disk unchanged | PASS |
| direct-mode-mount | `--phases disko --disko-mode mount` | 1 | program: `disko-mode` failed | PASS |
| direct-install-only | `--phases install` | 1 | program: `phases` failed | PASS |
| direct-disko-only | `--phases disko` | 1 | program: `phases` failed | PASS |
| direct-default-phases | none (`kexec,facter,disko,install,reboot`) | 1 | CLI: "joins kexec or reboot with disko or install, or is empty … made no connection" (C1 closed) | PASS |
| direct-kexec-disko | `--phases kexec,disko` | 1 | same CLI refusal | PASS |
| direct-disko-install-reboot | `--phases disko,install,reboot` | 1 | same CLI refusal | PASS |

## Earlier defects

| ID | Defect | State | Proof in this run |
| --- | --- | --- | --- |
| D1 | `wipefs --parse` | closed | a blank disk passes: success path |
| D2 | incomplete tool list, `command -v` accepts a non-executable file | closed | m, m2, m3, m4, m5, m6, x1, x2 |
| D3 | `--phases` and `--disko-mode` unchecked | closed | direct-mode-format, -mode-mount, -install-only, -disko-only |
| D4 | missing protected path skipped | closed | o |
| D5 | `findmnt -R /mnt` misses submounts | closed | l |
| W1 | unmount without `sshOpts` and port | closed | success: `/mnt` unmounted with `root@127.0.0.1:PORT` and no shim |
| W2 | unmount after a refusal | closed | l2 |
| W3 | swap stays active | closed | success: `/proc/swaps` empty |
| G1 | guard accepts `keep` equal to `install-target` | closed | i2 |
| C1 | `kexec` before the preflight | closed | three direct cases |
| C2 | CLI hides failed checks | closed | j, m |

## New findings

### N1. `tailscaled-autoconnect.service` fails on the first boot (gate item `systemctl --failed` empty)

Observed in the new system alone: state `degraded`, one failed unit. The journal says
`cat: /run/secrets/tailscale-auth-key: No such file or directory`, then the unit prints a login
URL and times out after 90 s. No sops age key is on the new system in this fixture (only the
bootstrap token and one extra file). Inference: on the real server the same unit fails until the
age key and the auth key are placed. Reproduction: boot the installed disk alone and run
`systemctl status tailscaled-autoconnect`. Proposed patch (the server role): add
`systemd.services.tailscaled-autoconnect.unitConfig.ConditionPathExists =
"/run/secrets/tailscale-auth-key";`, or place the age key through `install.secrets` so the secret
exists on the first boot.

### N2. The new system has no `efibootmgr`

`command -v efibootmgr` failed on the installed system. `MACH-009` and Step 9 create the one-time
entry from the old system, but a recovery from the new system needs the tool. Proposed patch: add
`pkgs.efibootmgr` to `environment.systemPackages` in `nixos/core.nix`.

### N3. ESP hashes are equal only within one boot of the old system

`loader/random-seed` changes at each boot of the old system. The Step 9 comparison of the old ESP
must exclude that file or state "no file differs but `random-seed`". The install itself left the
old ESP equal (same boot).

### N4. OVMF reorders its own entries

After the boot of the new disk alone, `BootOrder` moved `0002`, `0003` behind the PXE entries.
The entry `0007` (the old system) stayed first. Step 9's "default boot order equals baseline"
check should compare the first entry and the set of entries, not the full list.

### Harness faults found and fixed in this run (not product defects)

`qemu-img dd skip=` is ignored (the last MiB hashed as empty). The first pass of the earlier run
used it. The capture script used `grep` and `awk`, which the tool-hiding cases disabled; it uses
`sed` and `find` now. `findmnt` takes one path argument. The own-ESP check read the by-uuid
listing of both disks. The matrix verdicts above are from the corrected harness.

## Image and base hashes

Base images (unchanged by every case): `A-base.qcow2` `1d225816…c69b`, `B-blank.qcow2`
`04082b5e…b225e`, `vars-baseline.fd` `53c05b08…98cef`. Success run after the last boot:
`A.qcow2` `6cbfee9a…55b3`, `B.qcow2` `a3603192…6e0e`, `vars.fd` `935291dd…db2b`. All images,
the collection, the scratch workspace, and the token file were deleted. No GC ran.

## Not covered

- Real firmware, the real 4 TB drive, the kexec route, Intel VMD, PV-02 (Step 9).
- A boot of the new system with the age key and the Tailscale auth key (N1).
- A sops decryption of a payload secret on the new system. The payload here is a plain file.
- Machines `plan`, `apply`, `status`, `rollback` on the installed VM (Step 6 owns them).

## Proposed document changes

IDs are proposals. Check them against the ledger.

### SPEC-V6.md

- `MACH-016`: Verify now names the VM matrix (25 cases) and the direct cases (10). Mark Open for
  the real hardware only.
- `MACH-008`, `MACH-009`: Verify gains the success path of this record. Keep **Open** for the real
  firmware. Add the one-shot `BootNext` and the removable-path boot as VM-proven.
- `DISK-009`: Verify gains the boot of the new disk alone with preset PARTUUIDs and UUIDs.
- New `BOOT-023` (proposal): the shared core MUST include `efibootmgr` (N2).
- New `MACH-024` (proposal): a first boot MUST finish with `systemctl --failed` empty without the
  operator's secrets, or the unit MUST wait for its secret by a condition (N1).

### GUIDE-V6.md Step 7

- Item 5: add that the ESP comparison excludes `loader/random-seed` and the entry comparison does
  not use the full `BootOrder` (N3, N4).
- **Gate**: mark done for the VM except `systemctl --failed` (N1).

### GATES.md

- G7: `PARTIAL`: VM route proven, N1 open, real firmware open.

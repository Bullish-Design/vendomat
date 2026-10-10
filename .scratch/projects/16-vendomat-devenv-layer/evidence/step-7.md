# Step 7 — the fresh server disk route in a two-disk VM

**Date:** 2026-10-09 to 2026-10-10. **Gate:** G7. **Status:** PARTIAL, stopped on a DISK blocker.
The injection matrix and the direct patched CLI cases ran. The success path (install with payload,
boot of the new disk alone, one-time boot, fallback) did NOT run. Gate G7 stays OPEN.

**Blocker (DISK).** The root btrfs reached 1.00 MiB unallocated (17 MiB a minute later) with
metadata at 80%. The lead's rule says stop at 0.
The lane stopped, killed its VMs, and removed its scratch images from `/mnt/shared`. This lane's
own root writes: a 2.4 GiB disk image and a 1.2 GiB old-system closure in `/nix/store` (the
`build-old-image.sh` build, no GC root, not collected because GC is forbidden), a 4.6 MB workspace
in `/tmp`, and small preflight derivations. The server closure was already in the store. Other
processes also wrote to the root; the split is not measured.

## Pins and tools

| Item | Value |
| --- | --- |
| Patched devenv CLI | `/nix/store/6djw5w3sil4c0s8z0dvaqcq832y4cfvb-devenv-wrapped-2.4.0/bin/devenv`, fork `972624027d5788c0590e4b9f09bd3c3fbc53adb4` |
| Wrapper | `src/vendomat/machine.py` at the Step 4 checkout `gitman-workspaces/v6-implementation` (main `b30100b7`), run as `python -m vendomat.cli machine install server --root <ws> --no-version` |
| Preflight program | `preflight/vendomat-preflight` of that checkout, built by `nix/devenv-module/preflight.nix` |
| nix-systems | main `b60b2f1a`, copied to a scratch workspace; its `inventory/default.nix` replaced, `ids` kept verbatim |
| Collection | `git daemon` on `127.0.0.1:19477`, tags `v0.7.0` (vendomat tree) and `v2.4.0-vendomat.1` (fork) |
| Nix, nixpkgs, disko | 2.34.7, `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, v1.13.0 |
| QEMU, OVMF | 11.1.1 `qemu-host-cpu-only`, OVMF 202608; KVM, q35, UEFI, persistent `OVMF_VARS` copy per VM |
| Guest tools | util-linux 2.42.3 (`wipefs`, `blkid`, `lsblk`, `findmnt`), kernel 6.18.55 |
| Server closure | `nixos-system-server-26.11.20261008.e7439b6`, 2.3 GiB |

## VM identities

| Disk | By-id path | Model | Serial | Size (qcow2 virtual) | Role |
| --- | --- | --- | --- | --- | --- |
| old (disk A) | `/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_VMOLD0000000001` | `QEMU NVMe Ctrl` | `VMOLD0000000001` | 17179869184 | `keep` |
| new (disk B) | `/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_VMNEW0000000001` | `QEMU NVMe Ctrl` | `VMNEW0000000001` | 42949672960 | `install-target` |

Observed in the guest: sysfs `device/model` and `device/serial` give the same strings; the by-id
link `nvme-QEMU_NVMe_Ctrl_<serial>` exists. The preset PARTUUIDs and UUIDs are those of the
repository (`6f1c2a0e-5b7d-4c0e-9a31-4e53000000{01,02,03,12,13}`, ESP `4E53-0001`).

## What was built

All in nix-systems, workspace `v6-vm-disk`, `tests/disk/`:

| File | Purpose |
| --- | --- |
| `old-system.nix`, `build-old-image.sh` | Old system as a UEFI qcow2 (GPT, ESP, ext4 root, key-only root SSH, `efibootmgr`, `lvm2`, nix) |
| `base_vm.py` | First boot of the old system, one NVRAM entry `Old NixOS`, power off |
| `prepare_ws.py`, `vmids.py` | Scratch workspace: VM inventory, VM target, install payload, forge URL |
| `vmlib.py`, `capture.py` | QEMU control, raw-disk hashes, in-guest state capture and comparison |
| `matrix.py`, `direct.py` | Injection matrix (wrapper) and direct patched CLI cases |
| `success.py` | Success path and firmware test. Written, syntax checked, NOT RUN |
| `preflight_fixes.py` | The program fixes below, applied to a scratch copy only |
| `summarize.py`, `devvm.py` | Result table; throw-away VM for hand tests |

## Gate table

| Gate | Result | Raw log (under `07-disk-vm/run1/`) |
| --- | --- | --- |
| 1 Layout: preset PARTUUIDs, UUIDs, own ESP, installed by the wrapper | PARTIAL | `matrix-pass1-lastmib-bug/m3-tool-missing-awk/` (see run notes) |
| 1 Layout: mounts by UUID after boot of the new disk alone | NOT RUN | DISK blocker |
| 2 Baseline for the old and the blank disk | PASS | `matrix/*/capture-pre.txt`, `matrix/*/result.json` |
| 3 Matrix (a) to (n) | PASS for every refusal case; 3 cases FAIL (see defects) | `matrix/`, `matrix-pass1-lastmib-bug/` |
| 3 Direct CLI: no valid preflight refuses | PASS | `direct-pass1-lastmib-bug/direct-no-program/` etc. |
| 3 Direct CLI: `format` and `mount` | FINDING: `format` passes the preflight and formats | `direct-pass1-lastmib-bug/direct-mode-format-then-mount/` |
| 4 Success path, payload, boot alone, BootNext, fallback | NOT RUN (DISK blocker) | none |
| `testee verify --full` | not applicable (no repository code changed) | |

## Runs

The harness had a defect in its own last-MiB hash (`qemu-img dd skip=` is not honoured, so the
last MiB hashed as the empty string). Pass 1 therefore proved the first MiB, the whole new disk
(every non-zero 1 MiB chunk with its offset), `sfdisk --dump`, `lsblk`, every ESP file hash, and
`efibootmgr -v`. After the fix (`qemu-img convert --image-opts driver=raw,offset=...`), pass 2
reran 17 cases with the last MiB included. The DISK blocker stopped pass 2 before its last 8 cases.
Both passes keep their raw logs. Pass 2 matches pass 1 for every case it covers.

Base images, unchanged by every run (sha256 before and after):
`A-base.qcow2` `95a6212b…bd8351`, `B-blank.qcow2` `04082b5e…cb225e`, `vars-baseline.fd`
`3c811edf…625cf1b`.

### Baseline (deliverable 2)

Old disk, captured inside the booted old system (identical in every case):

- `sfdisk --dump`: GPT label-id `97FD5997-F390-0B4A-A3F8-D106C1723AEA`, ESP `C12A7328-…` uuid
  `1C06F03B-704E-…`, root `0FC63DAF-…` uuid `F222513B-DED1-…`.
- `lsblk -b -o NAME,PTTYPE,PARTUUID,UUID,FSTYPE`: vfat `12CE-A600`, ext4 `f222513b-…`.
- ESP files (8): `EFI/BOOT/BOOTX64.EFI` `91bccf4a…`, `EFI/systemd/systemd-bootx64.efi` `91bccf4a…`,
  kernel, initrd, one loader entry, `loader.conf`, `loader/random-seed` `5e212d20…`.
- `efibootmgr -v`: `BootOrder: 0007,0000,0001,0002,0003,0004,0005,0006`; `Boot0007 Old NixOS` on
  `HD(1,GPT,1c06f03b-…)\EFI\systemd\systemd-bootx64.efi`; OVMF auto-created `Boot0002` and `Boot0003`
  for the two NVMe disks.
- Host side, first MiB `bea9c45a169d9c22…`, last MiB `b4e3b0b52726bfbb…` (guest-visible bytes).

New disk: all zero in the first and last 16 MiB; content hash is the empty set (no non-zero chunk);
`wipefs --no-act` prints nothing; `blkid -p` exits 2.

### Injection matrix (wrapper `machine install server`, one fresh overlay per case)

"Equal" means: new-disk content hash equal before and after; old-disk first and last MiB,
`sfdisk --dump`, ESP hashes, and `efibootmgr -v` equal; `/mnt`, swap, and device-mapper state
equal. Every case ran `devenv machines install server --phases disko,install` through the wrapper.

| Case | Injection | Exit | Where the refusal came from and what it named | Equal | Result |
| --- | --- | --- | --- | --- | --- |
| a | inventory model `QEMU NVMe Ctrl X` | 2 | program: `identity:` got model vs inventory model | yes | PASS |
| b | inventory serial `VMNEW0000000002` | 2 | program: `identity:` serial | yes | PASS |
| c | overlay virtual size 41 GiB | 2 | program: `identity:` size 44023414784 | yes | PASS |
| d | ext4 signature on B | 2 | program: `no-signature-wipefs`, `no-signature-blkid` | yes | PASS |
| e | empty GPT on B | 2 | program: `no-signature-wipefs` (gpt, PMBR), `no-signature-blkid` | yes | PASS |
| e2 | GPT with one partition, no filesystem | 2 | program: `no-partitions`, signatures | yes | PASS |
| f | mounted ext4 partition of B | 2 | program: `not-mounted`, `no-partitions`, signatures | yes | PASS |
| g | active swap on a partition of B | 2 | program: `not-mounted`, `no-partitions`, signatures | yes | PASS |
| h | device-mapper linear map of B | 2 | program: `no-holders` (`dm-0`) | yes | PASS |
| i | install-target is A, no `keep` entry | 2 | program: `no-partitions`, `not-mounted`, signatures | yes | PASS |
| i2 | install-target and `keep` share A's by-id path | 2 | program: `not-protected`, `not-mounted`. The module guard did NOT stop it (finding G1) | yes | PASS (guard gap) |
| j | inventory by-id path absent in the guest | 2 | CLI: "preflight result covers disks {}, but the disko layout names {…}". The program's `resolve:` failure is not shown | yes | PASS |
| k | file in `/mnt` | 2 | program: `mnt-clear` ("/mnt holds files") | yes | PASS |
| l | tmpfs at `/mnt/sub` | 2 | program: `mnt-clear` (found by `ls -A`; `findmnt -R /mnt` was empty) | yes | PASS |
| l2 | tmpfs at `/mnt` itself | 2 | program: `mnt-clear`. The wrapper then ran `umount -R /mnt` and removed the operator mount (finding W2) | NO: mount gone | refused; wrapper changed state |
| m | `wipefs` absent from PATH | 2 | program: `tools` unknown, report has `disks: []`; CLI named "covers disks {}" | yes | PASS |
| m4 | `wipefs` present but not executable | 2 | program: `no-signature-wipefs` unknown | yes | PASS |
| m5 | `grep` not executable, B partition mounted | 2 | refused by `no-partitions` and signatures. `not-mounted` reported PASS (false pass, D2) | yes (harness `grep` also broken) | refused; check wrong |
| m6 | `awk` not executable, swap active on B | 2 | refused by other checks. `not-mounted` reported PASS (swap unread, D2) | yes | refused; check wrong |
| m2 | `grep` absent from PATH, blank B | 0 | no refusal; install ran to the end on the overlay (D2) | n/a | FAIL (expected unknown) |
| m3 | `awk` absent from PATH, blank B | 0 | no refusal; install ran (D2) | n/a | FAIL (expected unknown) |
| o | `keep` by-id path absent in the guest, blank B | 0 | no refusal; install ran (D4) | n/a | FAIL (expected unknown) |
| n | program replaced by one that prints pass with nonce `000…0` | 2 | CLI: "carries a different nonce: it is not an answer to this run" | yes | PASS |
| p0 | unmodified program, blank B | 2 | program: `no-signature-wipefs` unknown, `wipefs: unrecognized option '--parse'` (D1) | yes | refused; blocks every install |

Pass 2 (last MiB included) covers a to m and p0. Cases m2 to o and n rest on pass 1 (first MiB and
the whole new disk only). Cases m2, m3, and o produced complete installs on disposable overlays; the
disko output printed the preset UUIDs, the layout showed PARTUUIDs `6f1c2a0e-…{01,02,03}`, and the
wrapper's unmount succeeded (`findmnt /mnt` empty).

### Direct patched CLI (`devenv machines install server …`)

| Case | Program | Arguments | Exit | Observation |
| --- | --- | --- | --- | --- |
| direct-no-program | none | `--phases disko,install` | 1 | "Refusing to install: … set no `vendomat.preflight.program` … made no connection to the target" (0.3 s) |
| direct-failing-program | exits 1 | `--phases disko,install` | 1 | "the preflight did not pass … exit status 1 and printed no report" |
| direct-wrong-nonce-program | wrong nonce | `--phases disko,install` | 1 | "carries a different nonce" |
| direct-mode-format-then-mount | D1-fixed real | `--phases disko --disko-mode format` | 0 | preflight passed on the blank disk; disko formatted B (content hash changed) |
| (same VM, next run) | D1-fixed real | `--phases disko --disko-mode mount` | 1 | preflight refused: signatures and partitions now present, so `mount` can never pass on a formatted disk |
| direct-mode-mount-blank-disk | D1-fixed real | `--phases disko --disko-mode mount` | 1 | preflight passed; disko mount failed ("Can't lookup blockdev"); B unchanged |
| direct-phases-install-only-blank-disk | D1-fixed real | `--phases install` | 1 | preflight passed; `nixos-install` failed only because `/mnt` does not exist in this guest |
| direct-fullpatch-format-mode | full fix | `--phases disko --disko-mode format` | 1 | `disko-mode` check failed; B unchanged |
| direct-fullpatch-mount-mode | full fix | `--phases disko,install --disko-mode mount` | 1 | `disko-mode` check failed; B unchanged |
| direct-fullpatch-install-only | full fix | `--phases install` | 1 | `phases` check failed; B unchanged |
| direct-fullpatch-default-phases | full fix | (none: `kexec,facter,disko,install,reboot`) | 1 | the CLI ran `kexec` BEFORE the preflight (finding C1); then the `phases` check refused |

## Findings

Each has a minimal reproduction. None was applied to the vendomat repository.

### D1. `wipefs --no-act --parse` is not an option (blocks every install)

`preflight/vendomat-preflight` line 227. Reproduction in the guest:
`wipefs --no-act --parse -- /dev/nvme1n1` prints `unrecognized option '--parse'`, exit 1. The
check becomes `unknown`, so no blank disk ever passes. Observed: case p0. Fix: `--parsable`
(`wipefs --no-act --parsable` prints nothing and exits 0 on a blank disk).

### D2. The tool list is incomplete; a failed tool turns a check into a false pass

The `tools` check lists `lsblk wipefs blkid readlink findmnt`. The script also needs `awk`, `cat`,
`grep`, `head`, `id`, `ls`, `sort`, and `tr`. `printf … | grep -Fxq` returns 127 when `grep` is
missing, and the `else` branch reports `not-mounted` as PASS. The swap list comes from
`awk … /proc/swaps` in a process substitution, so a missing `awk` drops swap silently. Also,
`command -v` succeeds for a file that is not executable (bash falls back to the first match).
Reproduction: hide `grep` or `awk` (cases m2, m3, m5, m6). On a blank disk the program passes and
the install runs. With a mounted partition or active swap, `not-mounted` reports pass.
Fix: list every tool, and test it with `[ -x "$(type -P "$t")" ]`. The list part is in the
patch below and ran in direct cases; the `type -P` part is proposed and not run.

### D3. `--phases` and `--disko-mode` are read and never checked

`format`, `mount`, `--phases install`, and the default phase list all pass on a blank disk.
Reproduction: direct case `direct-mode-format-then-mount` (formats the disk). `MACH-008` requires
`disko,install` in the default mode. Fix: the `phases` and `disko-mode` checks in the patch.

### D4. A protected disk that does not resolve is skipped

`if [ -e "$p" ]` has no `else`. A stale `keep` by-id path gives no `not-protected` evidence and the
run passes. Reproduction: case o (exit 0, full install). Fix: a `protected-resolves:` check with
status `unknown` (in the patch, direct-tested only by hand in the guest; the wrapper run of the
patched copy was not repeated).

### D5. `findmnt -rn -R /mnt` misses submounts when `/mnt` is not a mount point (minor)

Case l: `findmnt` printed nothing; only `ls -A /mnt` caught the mount point directory. The outcome
is the same. A direct fix is `findmnt -rn -o TARGET | grep -E '^/mnt(/|$)'`.

### W1. The wrapper's unmount ignores `target.sshOpts` and the port

`machine.py` runs `ssh -o BatchMode=yes <target.host> umount -R /mnt`. With `target.host =
root@127.0.0.1:19822` (the form devenv accepts) `ssh` cannot resolve `127.0.0.1:19822`. With
`root@localhost` it uses the default ssh identity and known hosts, not `sshOpts`. The fixture put a
test `ssh` shim first on PATH that rewrites exactly `user@ip:port`. Without the shim the wrapper
prints "could not unmount /mnt on the target". Fix: read `machines.<host>.target.sshOpts`, split
`:port` into `-p`, and pass both to `ssh`.

### W2. The wrapper unmounts `/mnt` after a refused preflight

`run_install` unmounts "even when the install failed". Case l2: an operator tmpfs at `/mnt` was
removed after the preflight refused. Fix: unmount only when the install exit is 0, and otherwise
print the instruction. (A refused run has mounted nothing.)

### W3. Swap of the new disk stays active after the wrapper

Observed in m3: after the wrapper, `/proc/swaps` lists the new swap partition (the disko mount
script runs `swapon`). `umount -R /mnt` does not turn it off. On the real server the running system
holds swap on the new disk until reboot. Fix: `swapoff` the partition of the new disk by PARTUUID
after the unmount.

### G1. The module guard accepts an `install-target` that equals a `keep` disk

Case i2: both entries have the same `byId`; the evaluation passed and only the runtime
`not-protected` check refused. `VMOD-016` says no `keep` disk may be a disko device. Fix in
`nix/devenv-module/guard.nix`: fail when any `keep` or `existing-system` `byId` equals an
`install-target` `byId`.

### C1. The default phase list reaches `kexec` before the preflight

Direct case `direct-fullpatch-default-phases`: the log shows `kexec --load …` and "machine will
boot into nixos in 6s" before the CLI copied and ran the preflight. The patched CLI gates only
`disko` and `install`. A direct `devenv machines install server` on the running server would
replace its kernel first. Fix, in the fork: for a `fresh-install` machine refuse any phase set
that contains `kexec` or `reboot` together with `disko`, `install`, or an empty list, or run the
preflight before the first phase.

### C2. The CLI message hides which program check failed in two cases

When the report lists no disk (`resolve:` failed, or `tools` unknown) the CLI compares the disk
set first and prints "covers disks {}". The program's own failed check is in the report but not in
the message (cases j and m). Fix: print the failed checks before the disk-set comparison.

## Proposed patch to `preflight/vendomat-preflight`

```diff
@@ tools
-for tool in lsblk wipefs blkid readlink findmnt; do
-  command -v "$tool" >/dev/null 2>&1 || missing+=" $tool"
+for tool in lsblk wipefs blkid readlink findmnt awk cat grep head id ls sort tr; do
+  [ -x "$(type -P "$tool" 2>/dev/null)" ] || missing+=" $tool"
@@ after the --disk check
+if [ "$phases" = "disko,install" ]; then add_check phases pass "disko,install"
+else add_check phases fail "phases '$phases'; only 'disko,install' is supported"; fi
+if [ "$disko_mode" = "disko" ]; then add_check disko-mode pass "disko"
+else add_check disko-mode fail "disko mode '$disko_mode'; only 'disko' is supported"; fi
@@ protected disks
   if [ -e "$p" ]; then
     protected_dev["$(readlink -f -- "$p")"]=1
+  else
+    add_check "protected-resolves:$p" unknown "the protected disk path does not resolve"
   fi
@@ signatures
-  if wipe="$(wipefs --no-act --parse -- "$dev" 2>&1)"; then
+  if wipe="$(wipefs --no-act --parsable -- "$dev" 2>&1)"; then
```

`tests/disk/preflight_fixes.py` holds the exact replacements that ran (without the `type -P`
line). The scratch copy of the program, not the repository file, ran in every matrix case except p0.

## Observations of OVMF 202608 behavior (partial)

- OVMF creates a boot entry for each NVMe disk and each network device on first boot, marked
  `{auto_created_boot_option}`, and `efibootmgr -c` puts the new entry first in `BootOrder`.
- A one-time entry and `BootNext`, the new-disk-alone boot, and the fallback did NOT run.
  Everything about real firmware stays unproven.

## Not covered

- Success path: wrapper install with `install.secrets`, `install.extraFiles`, and
  `install.copyHostKeys`; compare of the old disk after it; boot of the new disk alone with
  persistent OVMF variables; key-only SSH; payload modes and hashes; `systemctl --failed`;
  secret grep of the store; one-time boot entry, `BootNext`, reboot, and return. `tests/disk/success.py`
  has these steps. It has not run.
- Pass 2 cases m2 to o and n (last MiB of the old disk). Pass 1 covers them without it.
- Layout by booting the new disk alone (mount sources by UUID in `/etc/fstab`).
- The `type -P` tools check of the patch.
- Real firmware, the real 4 TB drive, the kexec route, PV-02.

## Proposed document changes

IDs are proposals. Check them against the ledger.

### SPEC-V6.md

- `MACH-016` Verify: add D1 to D4 (the unmodified program passes no blank disk; `format`, `mount`,
  `install`-only, and a missing protected path passed). Mark the check "fixture ran; defects open".
- `MACH-008`: add that the program refuses any phase set other than `disko,install` and any disko
  mode other than `disko` (new ID `MACH-022`), because the patched CLI does not refuse them.
- New `MACH-023`: `vendomat machine install` MUST pass `target.sshOpts` and the port to the unmount
  and MUST NOT unmount after a refusal. MUST `swapoff` the new swap partition (W1 to W3).
- `VMOD-016` Verify: add the `keep` equals `install-target` by-id fixture (G1).
- New `DVN-011`: the patched CLI MUST run the preflight before `kexec` when the phase set can reach
  `disko` or `install`, and MUST show the failed checks of the report (C1, C2).
- `MACH-021`: its fixture list gains "wrong nonce" (done, direct) and "no program" (done).

### GUIDE-V6.md Step 7

- Item 2: add the tool-completeness and phase checks. Item 3: name the DISK blocker and the
  resume point (success path). Item 4: record that the direct `--disko-mode format` passes the
  preflight today.
- **Stop if**: add "a program defect makes an install impossible" (D1).

### GATES.md

- G7: `PARTIAL`. Matrix and direct CLI evidence in `step-7.md`. Success path and firmware: `OPEN`.

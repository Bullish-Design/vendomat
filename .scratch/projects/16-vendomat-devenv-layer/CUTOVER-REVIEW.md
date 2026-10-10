# Server cutover review package (Step 9)

**Date:** 2026-10-10. **Status:** DRAFT for owner review. **Nothing in this document has run.**
Every command in sections 8 to 11 is marked NOT RUN. No real disk, firmware entry, boot order, or
service was changed while this package was prepared.

**Read with:** [GUIDE-V6.md](./GUIDE-V6.md) Step 9, [evidence/GATES.md](./evidence/GATES.md), and the
evidence records it links.

## 1. Verdict

`server` is **not ready for the cutover**. The package lists what blocks it. The first block is a
privileged read-only scan that the owner must run (section 3).

| Item | State |
| --- | --- |
| Target identity (model, serial, size, by-id) | Matches the committed inventory (unprivileged observation) |
| Target blank: partition table and signatures | **BLOCKED**: `wipefs` and `blkid -p` need root (PV-02) |
| Old disk, ESP, and firmware baseline | Recorded without privilege (section 4) |
| `nixos-facter` report | **BLOCKED**: needs root. The role uses an explicit hardware module instead |
| Installed closure | Built and listed (section 6). No V4 module or toolchain manifest |
| Live source, cache, and Dagu routes | Not changed. See section 7 and the blockers |

## 2. What the install does, in one paragraph

`vendomat machine install server` runs the controller-side checks. It then runs
`devenv machines install server --phases disko,install` against `root@localhost`. The patched
devenv builds the closure, copies it, and runs the target-side preflight program with a fresh nonce.
Only a definite pass lets disko partition the blank 4 TB drive and lets `nixos-install` write it. The
old 512 GB drive and its ESP are never written. The owner then creates a one-time firmware entry and
boots the new disk once.

## 3. Privileged facts the owner must collect (PV-02)

`sudo` asks for a password in the agent session, so the scan did not run. The script is read-only:
it opens no block device for writing, mounts nothing, and calls `efibootmgr` only with `-v`.

```bash
sudo bash ~/.local/state/vendomat/v6/tools/pv02-scan.sh \
  ~/.local/state/vendomat/v6/2026-10-09/09-cutover-review/privileged-001      # NOT RUN
```

Accept the result only if all of these hold. Any other result stops the cutover.

| File | Required result |
| --- | --- |
| `10-new-wipefs.txt` | no signature line, `# exit=0` |
| `11-new-blkid.txt` | no output, `# exit=2` |
| `12-new-sfdisk.txt` | empty (no partition table) |
| `13-…`, `14-…` | both print `0` (first and last 16 MiB are zero) |
| `15-new-size.txt` | `4000787030016` |
| `16-new-holders.txt` | empty |
| `22-old-sfdisk.txt`, `42-esp-files.txt`, `40-efibootmgr.txt` | equal to the unprivileged baseline in section 4 |
| `facter.json` | exists; compare with `nixos/hardware/server.nix` (section 6) |

## 4. Facts observed without privilege

Raw: `~/.local/state/vendomat/v6/2026-10-09/09-cutover-review/unprivileged-001/` (observed
2026-10-09T23:51Z and 2026-10-10T03:02Z, user `andrew`, host `server`, kernel 6.18.38).

### Inventory against observation

| Fact | Committed (`nix-systems/inventory/default.nix`) | Observed | Match |
| --- | --- | --- | --- |
| Target by-id | `nvme-eui.e8238fa6bf530001001b448b4fbe837d` | udev `DEVLINKS` holds it, for `/dev/nvme0n1` | yes |
| Target model | `WD Blue SN5100 4TB` | sysfs `model` (trailing spaces trimmed) | yes |
| Target serial | `25459R800917` | sysfs `serial` | yes |
| Target size | `4000787030016` | `7814037168` sectors × 512 | yes |
| Target partitions | none expected | `lsblk`: none; sysfs: none; udev: no `ID_PART_TABLE_TYPE`, no `ID_FS_TYPE` | consistent (not proof) |
| Target mounted, swap, holders | none | none in `/proc/mounts`, `/proc/swaps`, `holders/` | yes |
| Old by-id | `nvme-NX-512_2280_0040141310300` | links to `/dev/nvme1n1` | yes |
| Old model, serial, size | `NX-512 2280`, `0040141310300`, `512110190592` | same | yes |
| Old role | `keep` | holds `/` (btrfs `e6b180fa-534a-4b71-aff8-f9fe2e6d0834`), `/boot` (vfat `0086-EC69`), swap | consistent |

### Old ESP and firmware baseline

- Old ESP: `/dev/nvme1n1p1`, vfat `0086-EC69`, PARTUUID `08b493db-8918-44f5-8796-204e3426e132`,
  mounted at `/boot`. 21 files; hashes in `old-esp-sha256.txt`. It holds `EFI/systemd/systemd-bootx64.efi`,
  `EFI/BOOT/BOOTX64.EFI`, `EFI/nixos/*`, 10 loader entries, and `EFI/Dell/logs/diags_previous.xml`.
- Firmware: `BootCurrent: 0005`, `BootOrder: 0005,0000,0001,0002`. `0005` is "Linux Boot Manager" on the
  old ESP. `0000` is "Windows Boot Manager" on a partition (`24b0b0a5-…`) that no attached disk has.
  `0001` and `0002` are onboard NIC entries. Secure Boot: disabled. Firmware: AMI 5.15, UEFI 2.70.
- Other mounts: `/mnt/wd_green1` (ext4, 1.8 TB `sda1`, holds Attic) and `/mnt/shared` (ntfs `sdb2`).

### A finding that changes the plan

Both data disks mount **under `/mnt`**. disko installs to `/mnt`, and its `disko` mode begins with
`umount -Rv /mnt`. The preflight program refuses while anything is mounted under `/mnt`
(`MACH-010`). A real install would stop at that check, and a bypass would unmount the Attic
storage under the running `atticd`. Section 8 therefore includes an operator step that stops
`atticd`, unmounts both disks, and mounts them again after the install. The
alternative is to move both mountpoints out of `/mnt` in the running system first.

## 5. Pins

| Item | Value |
| --- | --- |
| Patched devenv fork | commit `972624027d5788c0590e4b9f09bd3c3fbc53adb4`, tag `v2.4.0-vendomat.1`, upstream `v2.4.0` = `b904dcb51fe48c30db250038241507f60752f222` |
| Patched CLI | `devenv 2.4.0+9726240`, `/nix/store/6djw5w3sil4c0s8z0dvaqcq832y4cfvb-devenv-wrapped-2.4.0` |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| disko | `de5708739256238fb912c62f03988815db89ec9a` (v1.13.0) |
| Home Manager | `6b88c12cc6d234de4888f5d21076fb11199d0844` |
| sops-nix | `dcd241ba97088c22569d1573286e1b9daad340c0` |
| Vendomat | `main` of `Bullish-Design/vendomat`; **no release tag yet** (the registry names `v0.7.0`) |
| nix-systems | `main` of `Bullish-Design/nix-systems` (private); **no release tag yet** |
| Deploy key (public) | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMLhWJRKm9Z0TH+uYXt2LUUYNohKZBYHbkD79eUUuuF+ nix-systems-deploy@server`, SHA256:2yBw9eeg4lE57cQesFH8OUF8XdydFFSnRHhheJD6peI. The private key is `~/.ssh/nix-systems-deploy`, created 2026-10-09 for this work |
| Server host key (public) | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEuCv60g0lkc64dHXAk0pSqU9UGFqLAgtm67j9bMG3K8`, SHA256:yB8P5Uga/SPYxzrKHL+FT9i+Uu3XqZ2w+FRoKWL6Y0g. The first install copies it into the new system |
| Cache | `vendomat`, public key `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=` (matches `attic cache info`) |

The lock in the review run came from a **disposable** loopback collection, because the live
collection holds only `devman`. The closure's store paths depend on source hashes and not on the
URL, so the lock that `vendomat sync` writes after the collection holds the tags must give the same
toplevel. Verify that equality (section 8, step 4).

## 6. The built closure

- Toplevel: `/nix/store/vg74gb57xbp64fvdrj1jmp4bzjy92awr-nixos-system-server-26.11.20261008.e7439b6`
  (3.1 GiB, 810 paths). Built with the patched CLI: `devenv build machines.server.build.nixos`.
- Contains: `devenv-wrapped-2.4.0` (the patched CLI), `vendomat-launcher-0.6.0`, `vendomat-0.6.0` (host
  release), `repoman-0.12.0`, `python3.13-gitman-0.12.1`, `jujutsu-bin-0.46.0`, `testee-0.5.0`, `atticd`,
  `sops-install-secrets`.
- Does not contain: the V4 `vendomat` module, `repoman-toolchain-core`, `toolchain.json`, or
  `REPOMAN_TOOLCHAIN_BIN`.
- `nix.conf` holds the Attic substituter, its public key, and `netrc-file = /etc/nix/netrc`.
- Hardware: `nixos/hardware/server.nix` (Dell Precision 5820, Intel Xeon W-2125, Intel VMD, `vmd` in the
  initrd). It stands in for a facter report.

## 7. Routes and services

| Route | In the new system | State |
| --- | --- | --- |
| SSH | `services.openssh`, key-only; root accepts the deploy key; `andrew` accepts the two framework keys | built; VM check in Step 6 |
| Secrets | sops-nix; host key is the age identity; `secrets/secrets.yaml` is the old ciphertext | built; the first recipient equals the server's host key (`ssh-to-age`) |
| Tailnet | `services.tailscale` with `tailscale-auth-key` | built |
| Source collection | `services.gitDaemon` over `/home/andrew/vendor`, port 9418 on `tailscale0` | built; data must be copied (section 8) |
| Attic | `services.atticd` on loopback; Tailscale Serve publishes `/attic`; data on `/mnt/wd_green1` | built |
| Dagu | pending the `devman` registry function (Step 8, lane `v6-devman`) | see GATES G8 |
| Library services | pending a real library description | see GATES G6, G8 |
| Pull credential for a cold installer (PV-09) | `/etc/nix/netrc` has no source | **owner decision** |

## 8. Proposed commands (NOT RUN)

Run each from `~/Documents/Projects/nix-systems` as `andrew`, in order, only after the owner has
reviewed this package. Stop at the first unexpected output.

**Before the install**

1. Collect the privileged facts (section 3). `# NOT RUN`
2. Publish the tags the lock needs to the collection, from a checkout of each repository:
   `git push git://server/… `is read-only; use the owner's collection route (SSH, the post-receive hook):
   `vendomat` `v0.7.0`, and `devenv` `v2.4.0-vendomat.1` (the materialized fork). `# NOT RUN`
3. Tag `nix-systems` and re-lock against the collection: `vendomat sync && vendomat check`. `# NOT RUN`
4. Build and compare: `devenv build machines.server.build.nixos`. Its path must equal the toplevel
   in section 6. `# NOT RUN`
5. Push the closure to Attic with the owner's push credential:
   `vendomat push --cache vendomat --machine server`. `# NOT RUN` (the agent session was not
   permitted to push to the live cache).
6. Decide the pull-credential route for the new system (PV-09), and place `/etc/nix/netrc` through
   `install.extraFiles` or by hand after the first boot. `# NOT RUN`
7. Copy the data that the new `/home` needs (the collection under `~/vendor`, `~/Documents/Projects`,
   dotfiles) from the old root, read-only, after the install and before the first boot. `# NOT RUN`

**The install**

8. Stop what uses the data disks, then unmount them:
   `systemctl stop atticd atticd-tailscale-serve && umount /mnt/wd_green1 /mnt/shared`, after the owner has stopped every other user of those two disks (`fuser -m`). `# NOT RUN`
9. Dry run: `vendomat machine install server --dry-run`. It must print
   `devenv machines install server --phases disko,install`. `# NOT RUN`
10. Install: `vendomat machine install server`. The patched CLI runs the preflight program, and only a
    definite pass reaches disko. `# NOT RUN`
11. Mount the data disks again: `mount /mnt/wd_green1 /mnt/shared`; start the stopped units. `# NOT RUN`

**One-time boot**

12. Find the new ESP: `/dev/disk/by-partuuid/6f1c2a0e-5b7d-4c0e-9a31-4e5300000001`. `# NOT RUN`
13. `sudo efibootmgr -c -d /dev/disk/by-id/nvme-eui.e8238fa6bf530001001b448b4fbe837d -p 1 -L "NixOS new" -l '\EFI\systemd\systemd-bootx64.efi'`;
    note the new `Boot000N`; leave `BootOrder` alone. `# NOT RUN`
14. `sudo efibootmgr -n 000N` (BootNext). `# NOT RUN`
15. `sudo systemctl reboot`. `# NOT RUN`

**Verify the new system**

16. `findmnt -no SOURCE,UUID /` must show UUID `6f1c2a0e-5b7d-4c0e-9a31-4e5300000013`. `# NOT RUN`
17. `findmnt -no UUID /boot` must show `4E53-0001`. `# NOT RUN`
18. `systemctl --failed` is empty; `ssh -o BatchMode=yes root@server true` works; password login is refused. `# NOT RUN`
19. `sudo cat /run/secrets/tailscale-auth-key >/dev/null` succeeds; no secret value is in `/nix/store`. `# NOT RUN`
20. `tailscale status`; `git ls-remote git://server/devman`; `curl -sI https://server.tail770f47.ts.net/attic/vendomat/nix-cache-info`. `# NOT RUN`
21. `vendomat --version`; `devenv version` prints `2.4.0+9726240`; `devenv machines status server`. `# NOT RUN`

## 9. Health checks

`machines.server.deploy.healthCheck` fails the deploy when any unit is failed. After the first boot
the owner also checks: `systemctl --failed`, `atticd`, `tailscaled`, the git daemon socket,
`sops-nix` units, and the `/mnt/wd_green1` mount.

## 10. Fallback and recovery (NOT RUN)

| Situation | Action |
| --- | --- |
| The new system does not boot | Power-cycle. `BootNext` is one-shot, so the firmware returns to `BootOrder` (`0005`, the old Linux entry) |
| The new entry is missing or wrong | From the firmware menu, choose the old "Linux Boot Manager". The old ESP was not written |
| The old ESP is damaged | Boot a NixOS installer from USB, mount old `nvme1n1p3` and `p1` by UUID, and `nixos-enter` |
| Services fail on the new system | Boot the old system; its generations are intact. The data disks mount there as before |
| The preflight refuses | Stop. Do not edit the program to pass. Compare the failing check with the facts in section 4 |

Do not run `bootctl install` against the new ESP while the old ESP is mounted (`/boot` is the old
one). Promote the new entry to default only after repeated good boots (`MACH-009`).

## 11. Deferred or owner-decided

1. PV-09: how the new system receives a pull credential for the private cache.
2. Collection population: only `devman` is served today. The tags in section 8 step 2 are the
   owner's push.
3. `agentman` and its PostgreSQL unit are not in the new role (deferred; see the Step 8 record).
4. A `nixos-facter` report: optional replacement for the hardware module.
5. A live push to the production Attic: not run in this work.

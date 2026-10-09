# Vendomat V6 adoption VM acceptance plan (not executed)

**Status:** TEST DESIGN; all NixOS VM gates UNPROVEN here. Never point this suite at Framework or server. **Pins:** devenv `b904dcb51fe48c30db250038241507f60752f222` + V6 patch series `devenv-v2.4.0-vendomat.1.patch`; nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` is the **reference server pin**, not a permitted substitute for the unknown Framework pin; disko `de5708739256238fb912c62f03988815db89ec9a` only for the fresh-install comparison. From project 15: Nix 2.34.7, QEMU 11.1.1, OVMF 202608. Pin Home Manager and sops-nix to explicit revisions in the test lock and record them before claiming a gate.

## Workspace and guest shape

Create an isolated temporary controller workspace using the pinned patched devenv; `require_version: "2.4.0"`; a plain pinned nixpkgs input; a disko input (Machines evaluation requires it even for adopted hosts); a pinned Home Manager input; a pinned sops-nix input; and exactly one `machines.adopt-vm` NixOS role. Use `hardware.facter = null` with a manually captured, real baseline `hardware-configuration.nix` from the VM. No `disko.devices` stanza in the adopted machine module. Do **not** give it a separate `machines.adopt-vm.home-manager` role. Configure `target.host` to root SSH on the disposable VM, known host key and isolated controller deploy key. Pre-create a copy of the original VM's root deploy key policy, sops age key and encrypted fixture secret; do not put private values into the Nix store.

Create QEMU disk A as a persistent qcow2 (e.g. 24 GiB), with GPT, ESP, root ext4, optional swap and a NixOS system booting from disk A. Include NixOS and standalone Home Manager from pinned baseline inputs. Populate `/var/lib/adoption-fixture/document.bin`, `/home/tester/adoption-fixture.txt`, a chosen mutable service-data fixture and an unmanaged `~/.config/fixture/config` file. Put `/etc/vendomat-vm-adoption-marker` in this **VM only**. Keep its original boot entry and two generations. A second qcow2 snapshot/copy of disk A is the offline disaster-recovery backup. Keep persistent OVMF variables. Use `-snapshot` or copied disks for destructive injections and preserve the baseline qcow2.

### Suggested command sequence (controller unless indicated)

```bash
# Record tool/flake revisions and every command verbatim under ~/.local/state/vendomat/v6/<date>/vm-adoption/
# QEMU guest, using the supplied marker-protected read-only collection script:
VENDOMAT_VM_GUEST=1 bash capture-guest-state.sh > before.txt
# Controller: fail if any disko device is present; use only the adopted NixOS role
# All plan/apply and target SSH addresses must be the disposable VM's address.
devenv machines info
devenv build machines.adopt-vm.build.nixos
devenv machines check adopt-vm
devenv machines plan adopt-vm
# Record plan.json, target system generation/boot facts; manually review plan.
devenv machines apply plan-<reviewed-ID>
# VM guest:
VENDOMAT_VM_GUEST=1 bash capture-guest-state.sh > after-switch.txt
# VM only: reboot the guest (never the real host).
# VM guest after reboot:
VENDOMAT_VM_GUEST=1 bash capture-guest-state.sh > after-reboot.txt
# Controller:
devenv machines status adopt-vm
devenv machines rollback adopt-vm
# VM guest:
VENDOMAT_VM_GUEST=1 bash capture-guest-state.sh > after-rollback.txt
```

Use an approved Gitman command for any repository VCS operation. Save raw logs outside the repository. For snapshot comparison, collect **both** GPT partition GUIDs and filesystem UUIDs plus filesystem types, mount points, block sizes, root and ESP sources, user/group numeric IDs, system and Home Manager generation links, EFI NVRAM entries, encrypted key public identities (not private contents), and selected data-file sizes, owner/mode and hashes. Compare both old and new ESP trees; boot files are intentionally allowed to change and must be reviewed, not ignored. **Do not claim a whole-disk hash is unchanged while the operating system is running**: logs, `/nix/store`, profiles and boot files normally change.

## Gates and fault injection

| Gate | Injection | Expected observation | What a pass proves / does not prove |
|---|---|---|---|
| A1 | Baseline, no changes | Plan builds and doesn't contact target to write; apply creates generation, reboot succeeds | Adopted path works without disko on pinned VM, not real hardware |
| A2 | Wrong root/ESP UUID in proposed config | Adoption preflight fails before apply | Guard catches known disk mapping mismatch; does not prove old config safe when unchecked |
| A3 | Add `install-target` or any `disko.devices.disk` to adopted host | Nix evaluation/assertion fails and new CLI `install` gate denies | Role topology enforced; requires fork patch fixture |
| A4 | Call raw pinned fork `devenv machines install adopt-vm` with **every** phase combination (`kexec`, `facter`, `disko`, `install`, `reboot`, `--stop-after-disko`, `--disko-mode mount|format|disko`) | Rejected BEFORE network, payload staging or target filesystem changes | Direct Machines route blocked; upstream stock 2.4.0 will *not* pass this |
| A5 | Health check exits nonzero after switch | Watchdog returns system profile and running system to previous path | Recovery on running VM; cannot restore arbitrary service-data mutations |
| A6 | SSH connectivity lost before confirmation | Watchdog rollback after timeout; inspect target state | Doesn't imply recovery if PID1/systemd fails or VM fails to boot |
| A7 | Missing owner root deploy key | Check/apply refuse or fail before activation; keys remain unchanged | Initial key bootstrapping must precede Machines; no SSH bypass |
| A8 | Missing sops age key / wrong SOPS recipient | Test service can't decrypt, health check fails; profile rolls back | Decryption contract enforced; old key must be retained |
| A9 | Unit already failed before deployment | Read-only gate refuses deploy; verify failing unit can make native rollback fail if bypassed | Why `systemctl --failed` baseline gate is required |
| A10 | `~/.config/fixture/config` occupied by unmanaged file | First embedded Home Manager activation refuses or uses a reviewed unique backup suffix; never overwrites user content | Collision handling, not all files in home |
| A11 | Embedded HM config changes, then Machines rollback | Old HM-managed symlink and NixOS system generation reappear; unmanaged and mutable files stay | Configuration rollback, not user state backup |
| A12 | New VM boot fails (wrong initrd/root) | Firmware boot menu can select old generation; offline rescue can mount and restore previous profile/boot files | Recovery independent of new networking and boot success; must test physical console/OVMF |
| S1 | Fresh server-style two disks: new blank + protected old | Strict blank signature scan and disko only on new; old GPT/ESP/NVRAM stable | Fresh-install guard intact; uses distinct existing project 15 fixture |

Every gate must record **exact commands, exit codes, UTC timestamp, pins, before/after metadata, file hashes, screenshot or serial log for boot, and a clear PASS/FAIL/BLOCKED**. Never infer a gate pass from documentation alone.

## Home Manager cutover verification

A VM must start with *actual standalone Home Manager* at its original pin and profile. Capture `~/.local/state/nix/profiles/home-manager*` or other actual profile links, ownership, managed symlinks, package list and active user services. Stage an embedded NixOS Home Manager module with the same `home.stateVersion`, user ID, home directory and HM revision. Set `home-manager.backupFileExtension` to a unique audited suffix only if collisions are expected; leave `home-manager.overwriteBackup = false`, avoid `force = true`. Verify initial activation and boot on this state. Run Machines rollback and prove prior managed symlinks return; then prove the standalone activation path can be run from a separately retained old user profile after restoring old NixOS generation if necessary. Verify without deleting standalone generations until the transition is accepted.

## Recovery drill

Use the VM's OVMF boot manager first to select an older NixOS generation. If the old entry is absent or the ESP is broken, boot a pinned NixOS rescue ISO with **the disposable qcow2 only**, unlock the root volume using the VM key, mount the original filesystems by UUID without disko, verify `/nix/var/nix/profiles/system-<old>-link`, inspect `/boot`, and restore bootloader entries from the known-good old generation. Verify boot into baseline, SSH optional. This is a recovery path design; exact rescue steps must be written and exercised for Framework's actual bootloader/filesystem layout once recorded.

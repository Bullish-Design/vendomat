# W2: devenv Machines fixtures in VMs — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w2-machines/logs/REPORT.txt (Sonnet subagent). Scripts, workspaces, and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w2-machines/. VM images: /mnt/shared/vendomat-p21/w2/ (6.5 GB). Orchestrator spot-check: Generation 2 and the A-prime marker appear in the logs; btrfs after the run: 23.87 GiB unallocated, metadata 82.5 %. -->

W2 REPORT (project 21, machines fixtures). Stock devenv 2.4.0 CLI (/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0). QEMU 11.1.1 + OVMF 202608, KVM, VM image files only. nixpkgs e7439b6. No GC, no sudo, no host block device.
Work dir: ~/.local/state/vendomat/p21/2026-10-13/w2-machines/ (bin/ scripts, ws-* workspaces, logs/). Images: /mnt/shared/vendomat-p21/w2/{t1,t2,t3} (6.5 GB).

T4 deferredModule: PASS
 Patch: src/modules/machines.nix line 302 `unspecified` -> `deferredModule` (nixos only). Diff: logs/T4-patch.diff. Copy: src/devenv-patched; unpatched copy: src/devenv-stock (inputs.devenv = path:.../src/modules).
 Workspace (m1.nix attrset, m2.nix function, defaults.nix re-declaring options.machines = attrsOf (submodule { nixos = {pkgs,...}: ...; })).
 Patched: `devenv build machines.box.build.nixos` rc 0 -> /nix/store/f3mx2yp3blrpysx1mv1kbbsc35w5m8ii-nixos-system-nixos-26.11.20261008.e7439b6. /etc has t4-m1, t4-m2, t4-default; hello (m2) and jq (default) in system-path.
 Stock, same workspace: rc 1 `Cannot merge definitions of `machines.box.nixos'` (defaults.nix function, m1 attrset, m2 function).
 Stock, two attrsets (m1, m3): rc 0, but /etc has only t4-m3; t4-m1 silently lost (shallow merge replaces whole `environment`). fileSystems/boot from m1 kept.
 Side finding: /etc/devenv/machine-facts.json names `hostname` (networking.hostName, default "nixos"), NOT the devenv machine name. Vendomat must set networking.hostName = machine name.
T1 local apply: PASS (logs/T1-apply.log)
 Disk image from `outputs.t1-disk` = nixpkgs make-disk-image over machines.box._nixosEval (efi, systemd-boot). A toplevel j7p826jd..., A' toplevel h7rxzs79... (both from `devenv build machines.box.build.nixos`). A' copied with `nix copy --no-check-sigs --to ssh-ng://root@127.0.0.1`.
 In VM: `nix-env --profile /nix/var/nix/profiles/system --set A'` rc 0; `A'/bin/switch-to-configuration switch` rc 0. system-2-link created; boot entry Generation 2 added (default in loader.conf); /etc/t1-marker = A-prime; `hello` runs; systemctl --failed empty. Reboot: A' boots, failed empty.
 Rollback: `bootctl set-oneshot nixos-a341...conf` rc 0 + reboot -> /run/current-system = A (j7p826jd), marker A, no hello, failed empty. Profile `system` still points to gen 2 after boot-menu rollback.
 Facts file exists, hostname "box" (set in config).
T2 ISO and VM via _nixosEval: PASS (with hardware.facter = null)
 `outputs.vm = config.machines.box._nixosEval.config.system.build.vm`, `outputs.iso = config.machines.iso._nixosEval.config.system.build.isoImage`; `devenv build outputs.vm` / `outputs.iso` rc 0 (ISO 3:06, 1.5 GB). VM boots: running, failed empty (needs QEMU_OPTS="-display none -serial file:..", stdin kept open). ISO boots under OVMF with no disk: autologin shell on ttyS0, ssh ok, running, failed empty.
 Disko module: no problem. Facter: default (non-null) requires .machines/NAME/facter.json: `error: path '.../.machines/iso/facter.json' does not exist`. Needed hardware.facter = null for ISO/VM until a report exists. A real report (T3) with facter on the installed target machine worked.
T3 local install: PASS (logs/T3-pre-steps.log, T3-slim-steps.log, T3-slim4g-steps.log, T3-usb-steps.log)
 Facter: nixos-facter (copied into live store with nix copy for the probe; later in ISO systemPackages) rc 0, 36 KB JSON, 0.4 s. Re-run in ISO differs from baked report (byte 9737), not analysed.
 Guard (vendomat-disk-guard, guard.sh): refuses virtio-vd-used ("has 1 partition(s): not blank"), refuses ata-QEMU_DVD-ROM boot medium ("type is rom"), refuses boot medium as a rw virtio disk ("backs a mounted filesystem"), refuses the target once mounted; lists virtio-vd-target OK. With both disks used: no OK candidate. vd-used.img sha256 unchanged.
 Prebuilt ISO (iso-pre, storeContents = toplevel + disko script, 1.7 GB, ISO build 3:55), 4 GB guest, network blocked (restrict=on): disko script 3.8 s; nixos-install --system TOP --no-root-password --no-channel-copy 105.9 s, rc 0; workspace copied to /root/workspace; peak guest used ~720 MB (MemAvailable min 3,268,224 kB of 3911 MB); host qemu VmHWM 4.2 GB (page cache).
 Installed system from the virtual disk alone: running, failed empty, hostname target, facts ok, root workspace present, no secretspec/sops/age, only first-boot ssh host keys on disk, default cache config.
 In-ISO build (iso-slim: devenv + modules + workspace only, 1.6 GB), 8 GB guest, network on: `NIX_REMOTE=daemon devenv build machines.target.build.nixos machines.target.build.diskoScript` 70 s (substituted ~1.7 GB from cache.nixos.org), same store paths as host build (6c1gfvkg..., cnkd8mscw...). Without NIX_REMOTE=daemon devenv fails: "cannot remount /nix/store writable". Install then 31 s. Peak guest used ~3.8 GB. At 4 GB: build rc 0 in 61 s but overlay store 2.0 GB 86 % full, min available 380 MB (borderline). Installed system boots clean (same checks).
Disk/metadata: unallocated 38.87 GiB at start, 23.87 GiB at end; metadata 87.0 % at start (peak 87.3 %), 82.5 % at end. Never above 90 %.
Unproved: real hardware, kexec, offline in-ISO build, ssh-to-self deploy watchdog, facter report difference cause, nested-input follow (A1), `vendomat apply` command itself.

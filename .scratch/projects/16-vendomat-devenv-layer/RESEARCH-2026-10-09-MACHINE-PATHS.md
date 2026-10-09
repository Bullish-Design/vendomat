# Vendomat V6 — two machine paths: fresh install vs existing-system adoption

**Date:** 2026-10-09  
**Status:** Research and proposed requirements only; **no production changes**.  
**Intended repository destination:** `.scratch/projects/16-vendomat-devenv-layer/RESEARCH-2026-10-09-MACHINE-PATHS.md`  
**Scope:** Investigate `server` fresh-drive installation and `framework` in-place adoption. No disk, deployment, NVRAM, key, or real-machine write was made.

## Recommendation

**Accept two explicit, mutually exclusive machine modes.** `server` is `fresh-install`: retain V6's strong blank-drive check, protected old drive, disko, and controlled firmware cutover. `framework` is `adopt-existing`: preserve its *actual* disk and boot configuration, retain the old management tool and recovery generation, and use `devenv machines plan` + `apply` (or `deploy`) without running `machines install`. The only common part is the NixOS Machines deployment engine, not the disk lifecycle.

**Critical design consequence:** No-disko-layout plus `VMOD-012` is **not** a sufficient safety gate. Stock devenv accepts `machines install --phases install` for a NixOS role, and `nixos-install` may write to `/mnt` or install a bootloader. Introduce a **fork-level machine install policy check** that blocks *all* `machines install` phases for adoption, including when commands bypass Vendomat. Keep the same protections on a fresh-install target; the upstream CLI does not implement V6's blank-drive preflight. This can prevent mistakes through the supported pinned CLI, not arbitrary privileged commands or an operator using an unpatched binary.

**Do not promote source review to a passed VM gate.** A real adoption VM, initial Home Manager transition, offline rescue, and real Framework disk inventory remain open.

## Inputs and evidence grade

**Repository instructions read:** [AGENTS.md](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/AGENTS.md), [.scratch/CURRENT.md](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/CURRENT.md), [V6 concept](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/16-vendomat-devenv-layer/CONCEPT-V6.md), [V6 spec](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/16-vendomat-devenv-layer/SPEC-V6.md), [active V5 spec](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/14-vendomat-local/SPEC-V5.md), [project 15 report](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/REPORT.md), [project 15 follow-up](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/FOLLOWUP-2026-10-09.md), and relevant [agent D](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-d-devenv-source.md), [E](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-e-disko.md), [F](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-f-install-routes.md), [G](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-g-machines-pinning.md), [K](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-k-vendomat-module.md).

**Pinned upstream:** devenv `v2.4.0` = [`b904dcb51fe48c30db250038241507f60752f222`](https://github.com/cachix/devenv/tree/b904dcb51fe48c30db250038241507f60752f222); V6 fork patch proposal [`devenv-v2.4.0-vendomat.1.patch`](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/prototypes/devenv-v2.4.0-vendomat.1.patch), based on upstream commits `a5fd551a` and `a5c34429`, plus PR #3244 and release-build change. This patch **does not contain the proposed adoption install prohibition**. Project 15 pins: Nix 2.34.7, nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, disko v1.13.0 `de5708739256238fb912c62f03988815db89ec9a`, QEMU 11.1.1, OVMF 202608. The project 15 raw VM logs live on the original host under `~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/`; this research could read the repository reports, **not those host-local logs**.

**Current research environment:** Python 3.13.5, Pydantic 2.13.5, Bash 5.2.37; no `nix`, QEMU, Testee or Gitman. Therefore no Nix builds, Machines target commands, source builds, NixOS guest boots, real disk reads or repository Gitman writes were possible here. Static sources and the reported prior fixtures are evidence, not newly passed gates. New policy prototype: 11/11 *synthetic contract cases* passed; capture script passed `bash -n`. Results are in `fixtures/` and the raw research log directory `~/.local/state/vendomat/v6/2026-10-09/research/`.

**Evidence keys:** **S** = directly inspected pinned code; **D** = official upstream documentation; **P15** = earlier project-15 fixture report, not reproduced here; **L** = new synthetic model; **I** = inference/proposal; **OPEN** = acceptance test needed.

## 1. Execution-path map: native Machines

Source: [CLI/Rust Machines implementation](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/devenv/src/devenv/machines.rs), [Machines module](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines.nix), [target executor](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines/deploy.py), [official guide at pinned revision](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/docs/src/content/docs/machines.md). The current website is live and may have newer behavior; pinned implementation is authority for V6.

| Command / phase | Build or local write | Remote read/copy/write | Disk/boot risk | Evidence |
|---|---|---|---|---|
| `devenv machines info` | Evaluates machine metadata; may update normal evaluation cache | No host contacted | No target writes | S, D |
| `devenv build machines.H.build.nixos` | Builds NixOS derivation/store closure on builder | None | No target writes; local Nix store changes | S, D |
| `devenv build machines.H.build.diskoScript` | Builds an **executable** disko script | None until explicitly run | Script is destructive if later invoked | S |
| `devenv machines check H` | Evaluates access facts | Reads SSH/target access facts | No deploy; not proof of disk identities or reachability after switch | S, D |
| `devenv machines plan H` | Builds closure(s), records `.devenv/machine-plans/<ID>/plan.json` and GC roots | Queries current NixOS generation/access facts; no closure copy, activation or disko | Read-only **to target**, but writes local plan and Nix store | S, D |
| `devenv machines apply plan-ID` | Reuses reviewed build paths, tests staleness | `nix copy --to ssh://...`; target starts deployment executor | **Writes** target store, system profile, `/run/current-system`, `/etc`/services and EFI boot files during switch | S |
| `devenv machines deploy H` | Plans, displays, optionally prompts, then applies; `--yes` skips question | Same as apply | Same target writes; with no names can select every remote machine | S |
| `devenv machines status H` | Metadata evaluation | Reads target transaction record/status over root SSH | No activation | S |
| `devenv machines rollback H` | No rebuild required | Root SSH executor selects recorded `previousSystem`, changes `/nix/var/nix/profiles/system`, calls `switch-to-configuration switch` | May rewrite ESP boot entries and restart services; cannot restore arbitrary mutable files | S |
| `machines install` phase `kexec` | Prepares installer | SSH: downloads/extracts installer into `/root`, invokes kexec | Replaces running kernel/environment, disrupts services | S, P15 |
| `machines install` phase `facter` | Writes `.machines/H/facter.json` in project; upstream directly invokes `git add --intent-to-add` | Executes `nixos-facter` on target | Hardware read plus **local repository file and VCS staging write**, not a disk wipe | S |
| `machines install` phase `disko` (default mode) | Builds/copies disk script | Executes disko `destroy + format + mount`; starts with recursive `/mnt` unmount | **Partitions and formats** listed target disks without confirmation | S, P15 |
| `machines install --disko-mode format` | Builds format-only script | Creates storage without mounting | May leave `/mnt` pointing to wrong place for subsequent install | S, P15 |
| `machines install --disko-mode mount` | Builds mount-only script | Mounts existing layout, doesn't format by itself | Can mount wrong filesystem or reuse unsafe `/mnt`; does **not** turn entire install into an adoption action | S, I |
| `machines install` phase `install` | Builds/copies replacement top-level | Runs `nixos-install --system <out> --no-root-password --no-channel-copy` targeting `/mnt`; then can copy host keys, extra files and secrets | **Writes installed system and bootloader; can alter NVRAM depending on bootloader config** even if disko skipped | S, P15 |
| `machines install` phase `reboot` | None | Runs remote reboot | Reboots target, possible selection of wrong generation | S |

**More exact effects:** `machines.rs:1579–~1760` sequences phases; `:1681` builds replacement before disko; `:1983–2001` selects/copies/executes disko script; `:2019` uses `nixos-install` (no explicit `--root`, default `/mnt`). `machines.rs:2845–~2980` applies a plan, `:3031–~3205` starts transaction/copies paths. `deploy.py` sets Nix profile and calls `switch-to-configuration switch`; watchdog retains previous closure as a GC root and can restore it. The `machines.install` check for root authentication is **not** an install-mode check. [Project 15 agent F](https://github.com/Bullish-Design/vendomat/blob/406a9a4e3a9ba57c28a5e55de7fbe8704faf2add/.scratch/projects/15-devenv-alignment/raw/agent-f-install-routes.md) observed an install-only run writing gigabytes into the running machine's `/mnt` directory. There is **no native install dry run**. An omitted disko phase does not imply harmlessness. [Official install documentation](https://devenv.sh/machines/) specifically distinguishes fresh install from existing-host deployment.

`machines.nix:127–145` requires an **input named `disko` for every NixOS role**, even adoption, because it always imports `disko.nixosModules.disko`. It does **not** require a nonempty `disko.devices.disk`. `hardware.facter = null` removes facter input/report requirements; alternatively a real, committed per-host report may be used. `machines.<H>.nixos`, `system`, `target.host`, `target.sshOpts`, `deploy.healthCheck` and `deploy.rollbackTimeout` are the relevant deployment inputs; a **separate** `machines.<H>.home-manager` role is not needed if HM is inside NixOS.

### Bypass / accident paths

1. Raw upstream or fork `devenv machines install framework` default phases: kexec and disko can destroy the running installation (S).
2. Explicit `--phases disko`, any disko mode: `diskoScript` destroys/formats when a layout exists; `mount`/`format` still create dangerous `/mnt` state (S).
3. Explicit `--phases install` or `--phases facter,install` *without disko*: `nixos-install` writes to `/mnt`, can rewrite boot and install payloads (S, P15).
4. Explicit `--phases reboot` can interrupt an adopted host, even without disk format (S).
5. An adopted host whose module accidentally inherits a fresh disko device; or a legacy disk setup with colliding `by-partlabel` names (P15).
6. Direct execution of a built `build.diskoScript`, `nixos-install`, `disko`, a second NixOS builder, or an unpatched devenv binary by a privileged operator: beyond what a module assertion can block (I).
7. `apply` of a stale or modified plan file, `deploy --yes` with no host names, or activation scripts with custom arbitrary writes. The native plan checks recorded role/host/generation and pinned outputs, **not an inventory hash or live disk topology** (S).
8. A normal NixOS `switch` may update bootloader files and services; an empty disko layout **does not guarantee a no-write deployment** (S).

**Practical guard design:** extend the patched devenv fork with a machine-level `install.allowed` (name **proposed**, not an upstream option) exposed in machine metadata; default to a restrictive policy for Vendomat-managed hosts. Its check must run at `machines_install` entry, *before* phase-dependent actions, including when disko is omitted, and must reject an adopted host. Do not represent a Vendomat-only wrapper or an Nix assertion as sufficient against a direct CLI bypass. For the fresh host, the patched CLI must either perform or verify a just-issued host/disk-specific preflight attestation before disk-mutating phases; alternatively make native `install` always refuse for a Vendomat-managed host and expose a dedicated, tested internal invocation from `vendomat machine install`. Implement the attestation safely (bound to host, disk identities, signatures, plan revision and short TTL); a plain environment variable or a `--yes` flag is not a meaningful safeguard. Because the proposed metadata/attestation API is **not implemented or proven**, list this as an acceptance blocker. Root shell actions cannot be sandboxed by these software checks.

## 2. Machine inventory, decision table and layers of checks

**Proposed shape (not yet implemented):**

```nix
vendomat.inventory.server = {
  mode = "fresh-install";
  nixos.imports = [ ./nixos/core.nix ./nixos/server.nix ];
  disks.newsys = {
    byId = "/dev/disk/by-id/<new-drive>";
    role = "install-target";
    # model, serial, sizeBytes: required runtime hardware expectations
  };
  disks.oldsys = { byId = "/dev/disk/by-id/<old-drive>"; role = "keep"; };
};
vendomat.inventory.framework = {
  mode = "adopt-existing";
  nixos.imports = [ ./nixos/core.nix ./nixos/framework.nix
                   ./nixos/framework-existing-hardware.nix ];
  disks.system = {
    byId = "/dev/disk/by-id/<measured-existing-system-disk>";
    role = "existing-system";
  };
  # NO disko.devices.disk for this machine
};
```

**Two orthogonal meanings:** host `mode` determines lifecycle; a disk `role` protects individual block devices. `keep` is a protected auxiliary or fallback disk on *either* host; `existing-system` means a protected disk which already contains the adopted root or boot filesystem. `install-target` is exclusive to a `fresh-install` host. Never infer mode from an empty disko attrset or filesystem signatures. A `disk` existing in inventory is not authorization to format it.

| Operation | Fresh server mode | Adopted Framework mode | Barrier |
|---|---|---|---|
| `info`, `check`, `status` | Allow | Allow | Target identity/access checks; `status` needs deployed executor for detail |
| `devenv build`, `plan` | Allow | Allow | Nix module assertions; record all planned generation/service/boot changes |
| `apply` of reviewed plan; `deploy <host>` | Allow after system is installed | Allow only after baseline key, state/pin, data/boot inventory gates | Native plan staleness and SSH-access checks; Testee/read-only local preflight; explicit host name |
| `rollback <host>` | Allow after a deployment | Allow after a deployment | Previous closure must exist; SSH/systemd must work. Offline boot rescue independently verified |
| `vendomat machine install server` | Allow only after strict fresh-drive preflight and explicit operator approval | **Deny** | Vendomat preflight + fork-level CLI install gate |
| Raw `devenv machines install` (all phases/modes) | **Deny by default** unless validated preflight authorization in patched CLI | **Always deny before contacting target** | Fork-level command policy; module checks alone insufficient |
| Direct disko script, `nixos-install`, manual format | Unsupported; admin can execute externally | Unsupported; admin can execute externally | Documented privilege boundary, cannot be prevented by Vendomat evaluation |

**Build/evaluation assertion (`VMOD-016` proposal):** (1) the inventory owns `machines.H.nixos` uniquely; (2) explicit mode exists; (3) no adopted machine has *any* `disko.devices.disk` or `install-target`; (4) adopted machine has at least one `existing-system`; (5) every fresh disko device is one of its exact `install-target` paths and no `keep`/`existing-system`; (6) every filesystem source is an explicitly mapped stable UUID/PARTUUID (unless a declared virtual/temporary filesystem) and no `by-partlabel`/kernel disk name; (7) disko and NixOS disks cannot share a duplicate ID or label; (8) adopted config retains selected boot/fstab properties from approved baseline manifest. For a NixOS role `disko` input is still present, *not necessarily a disk layout*.

**Vendomat command:** Only `machine install` for fresh. Refuse install for adopted, `--disko-mode format|mount`, unsanctioned `--phases`, wrong target/root, missing inventory and stale lock/facter, and preflight failures. It must not act as a deploy engine. All `plan/deploy/apply/status/rollback` remain native Machines (`MACH-005`).

**Target read-only preflight:** On fresh target, check `by-id` path, disk model/serial/size, blank `wipefs --no-act` **and** `blkid -p`, live root/boot ancestry, nothing mounted from target, nothing below `/mnt`, committed facter and root authentication, protected old drive/ESP, baseline EFI NVRAM; stop on unknown. **Never weaken `MACH-010` to allow signatures.** On adoption, collect current `lsblk`/`findmnt`/fstab/crypttab/swap/LUKS mapping/ESP/firmware/bootloader, compare with declared UUID/PARTUUID, confirm baseline hashes, users, services, keys, profile links and **no disko layout**. Refuse deployment on unexplained mismatch; never call disko. A read-only preflight is evidence at an instant, not a guarantee that future state cannot change. For normal deploy, record reviewable writes to system generation, boot entries/ESP and service changes from the plan and config diff.

## 3. Framework facts needed before adoption

No direct read-only access to the running Framework was available to this research. A 2026-10-07 [Framework cutover report](https://github.com/Bullish-Design/nix-meta/blob/main/.scratch/projects/03-framework-cutover-readiness/REPORT.md) states that the **then-active** `~/.dotfiles` flake was its authority, that the intended `system.stateVersion` and `home.stateVersion` were both `23.11`, and that a separate `nix-meta` Framework output was *not yet ready*. These are **historical static findings**, not proof of the live system now. The present disk and encryption topology, exact bootloader and actual user IDs remain unknown. No credential values should enter research logs.

Collect *locally on Framework, read only* before writing a target module:

| Category | Required baseline and comparison source |
|---|---|
| Disk identity/layout | `lsblk -J -b -o NAME,PATH,TYPE,SIZE,MODEL,SERIAL,WWN,FSTYPE,UUID,PARTUUID,PARTTYPE,PTTYPE,MOUNTPOINTS`, `blkid`, `sfdisk --dump` **read only**; map `/dev/disk/by-id/` to physical root, boot and any additional volumes; geometry and ESP partition GUID |
| Mounts and persistence | `findmnt --json`, `/etc/fstab` if present, NixOS `fileSystems`, Btrfs subvolumes/flags if used, bind mounts, ZFS datasets/import paths, `neededForBoot`, `boot.initrd.*`, swap via `swapon --show`; verify partitions by UUID/PARTUUID |
| Encryption | `/etc/crypttab` if used, `lsblk`, `cryptsetup status <mapped-name>` and `cryptsetup luksDump <volume>` **only metadata** (do not capture salts/master keys), initrd unlock/keyfile paths, TPM/FIDO2 enrollment and network-unlock dependencies; never print key material |
| Boot | `bootctl status` or appropriate loader, `efibootmgr -v` (UEFI only), `/boot`/`/boot/efi` mount, selected ESP by PARTUUID, systemd-boot/GRUB/Limine details, Secure Boot keys if relevant, boot menu generation retention; read-only tree and path manifest for ESP |
| NixOS inputs/state | Live `/run/current-system`, `/nix/var/nix/profiles/system*`, exact deployed flake lock/input revisions and local overrides, `system.stateVersion`, hardware modules, CPU/GPU/storage/network kernel modules, microcode, filesystems, persist settings, systemd version, custom activation scripts |
| Users, homes and services | `getent passwd/group` for numeric UID/GID, home directory/shell and ownership, NixOS `users.mutableUsers`, group membership; systemd failed units; user services; service state and data-directory paths; **do not capture shadow, keys or tokens** |
| Home Manager | Live standalone flake/lock, `home.stateVersion`, generated HM profile links and active symlinks, home file conflict list, HM packages, session-variable sourcing, user systemd units and out-of-store links |
| Credentials | Existence, owner, mode and **public identity only** of root deploy authorized key(s), SSH host public keys, sops age public recipient, SOPS file recipient coverage, `sops.age.keyFile`/`sshKeyPaths` decision; no secret values |

The missing report must include the **current** Framework's root/boot UUIDs, PARTUUIDs, ESP ID, actual disk by-id, FS types and mount options, encryption/unlock/swap, bootloader path, HM source and pinned revs, users' UIDs/GIDs, deployed generation and system state versions, and age key path. Only the then-static `23.11` state-version intention is known; do not infer any layout from it.

## 4. Adoption procedure (no disko, no format)

0. **Backup and rescue first.** With the old system still in control, record the full baseline and create a restorable, verified backup of home/service data, the original generation and boot files plus an offline rescue route. Capture a physical/VM boot choice for the previous generation; do not delete old generations or garbage collect the rescue closure. A Btrfs snapshot alone is not a substitute for a test restore; match the actual filesystem.
1. **Keep the old NixOS module content unchanged at first.** Transcribe/import its `hardware-configuration.nix`, filesystem and partition UUIDs, ESP, initrd LUKS, swap, boot loader, `users.users` and numeric IDs, hardware modules, boot options, networking, service state choices, `system.stateVersion` and current Home Manager state. Use the actual active `~/.dotfiles` flake or other authoritative source. Compare evaluated old/new NixOS declarations or output derivations and explain every difference. Do **not** generate disko devices for it.
2. **Pin matching inputs for baseline.** The first cutover must use the same *effective* nixpkgs revision, overlays, Home Manager source and service-specific pinned dependencies as Framework's working system. `nixos-unstable` tag name is not equivalence. Machines NixOS evaluator uses `inputs.nixpkgs` for the whole machine, so a different rev is a real system update. If `server` and `framework` require different revs, use a temporary separately locked devenv Machines workspace (still importing Vendomat's module) for Framework adoption, not simultaneous cross-host nixpkgs upgrade; merge workspaces when deliberate migration gates pass. Pin controller devenv separately as intended. **This requires `MACH-002`/`MACH-013` exceptions or successors.**
3. **Bootstrap root SSH in the existing system's management path, not by Machines install.** Add the owner's dedicated public deploy key to root's declared authorized keys using the current working NixOS mechanism; keep root login key-only, disable password login, constrain network/key options if verified. Test `ssh -o BatchMode=yes` using a pinned known host key and current target. Use an out-of-band local sudo transition only if needed and record/revert it through the original system config; do not place the private key in Nix/store or logs. If the root key is absent, *stop before first Machines apply*. Existing home-user SSH does not automatically imply root access.
4. **Preserve/provision sops age identity without `install.secrets`.** Determine whether sops-nix currently uses `sops.age.keyFile` or derives an age identity from `/etc/ssh/ssh_host_ed25519_key`; use the same existing private identity in place if present, or securely provision an age key locally through the old managed system and update encrypted file recipients first. In the adopted NixOS module set `sops.age.keyFile = "/var/lib/sops-nix/key.txt"` **only if that is the actual key path**; for existing key choose `sops.age.generateKey = false`, and verify public recipient matches before activation. Never make a fresh unrelated key silently by setting `generateKey = true` when encrypted files rely on a prior identity. Confirm decrypt/secret service under a throwaway VM with no plaintext in store. [sops-nix primary documentation](https://github.com/Mic92/sops-nix/blob/master/README.md).
5. **Stage standalone Home Manager carefully.** Initially retain the existing standalone HM source and profile untouched. Reuse its exact revision, `home.stateVersion`, owned files, usernames/UIDs and user services in `home-manager.users.<user>` and import `home-manager.nixosModules.home-manager` into the same NixOS role. Disable a duplicate `machines.<host>.home-manager` role. Audit managed symlinks/collisions; allow no `force = true` or backup overwrite by default. If a file is not already an HM-managed symlink, fail or use an **audited unique** `home-manager.backupFileExtension`. Retain standalone generations and a manual rollback path until the integrated HM activation has survived a reboot and rollback. [HM collision behavior](https://nix-community.github.io/home-manager/usage/dotfiles.html), [NixOS HM options](https://nix-community.github.io/home-manager/options/nixos/home-manager.html).
6. **Prove exact route in an already-bootable, populated VM.** Use the fixture plan in `fixtures/VM-TEST-PLAN.md`; gate both preservation and boot recovery. Fix pinned-fork install prohibition before allowing the adopted machine into shared inventory.
7. **Plan, inspect, apply (first cutover only).** `devenv machines check framework`; `devenv build machines.framework.build.nixos`; `devenv machines plan framework`; archive plan ID/JSON and inspect exact closure, access, kernel/initrd/boot settings, changed services and user HM activation; `devenv machines apply plan-<ID>` only after acceptance, from authorized operator. Not `install`, not `disko`, not `--yes` in first cutover. Set a health check that verifies network, key-only root SSH reachability, required mount/service availability and critical HM outcomes without restarting or modifying services. Native watchdog protects an activation that fails; do not rely on it for an unbootable generation.
8. **After switch and reboot** compare disk identity, GPT, partition/filesystem UUID, mounts and selected hashes, root and ESP, users, HM-managed symlinks, services, actual key recipients and installed generation. Expect `/nix/store`, logs, `/etc`, EFI files and service state to change. Record and approve changes; test `devenv machines status` and rollback of a later disposable generation. Do **not** delete the original NixOS/HM profiles yet.
9. **Only then** separately upgrade nixpkgs, HM, devenv release, service data schemas or refactor module architecture, each with an independent plan, verification and rollback/backup.

**Minimal shape (illustrative; options not a substitute for hardware inventory):**

```nix
# nix-systems/adoption workspace; actual inputs and hardware sourced from live Framework
{ inputs, ... }: {
  imports = [ inputs.vendomat.devenvModules.default ];
  vendomat.inventory.framework = {
    mode = "adopt-existing";  # PROPOSED, not yet implemented
    disks.system = { role = "existing-system"; byId = "/dev/disk/by-id/<ACTUAL>"; };
    nixos.imports = [ ./nixos/framework-existing-hardware.nix
                      ./nixos/framework-existing-system.nix ];
  };
  machines.framework = {
    system = "x86_64-linux";
    target.host = "root@<ACTUAL-FRAMEWORK-TAILNET-HOST>";
    hardware.facter = null; # first cutover; existing hardware module retained
    deploy.rollbackTimeout = 300;
    deploy.healthCheck = ''
      /run/current-system/sw/bin/systemctl is-system-running --quiet
    ''; # refine based on actual baseline; pre-existing failed units must be cleared first
    # NO separate home-manager role
  };
}
```

## 5. Fresh server install remains its own procedure

1. Keep the 512 GB old drive in role `keep`, its ESP and BootOrder as fallback; new 4 TB is `install-target`. Existing project 15 read-only evidence identified the new by-id path, but signature checks were blocked by lack of privilege: **PV-02 still open**.
2. Build the fresh `server` NixOS role with disko target **only** the approved new drive. Preassign partition GUIDs/filesystem UUIDs, mount by UUID or PARTUUID, use a unique disko disk attribute, and set `boot.loader.efi.canTouchEfiVariables = false` initially. Capture and commit valid `.machines/server/facter.json` without running upstream's `facter` phase in the operational installation path (its built-in VCS staging bypasses Gitman).
3. Pass runtime target preflight with `wipefs --no-act`, `blkid -p`, model/serial/size, currently mounted roots/boot, and every `/mnt` submount. Reject unknowns and existing filesystem signatures. Inspect second drive partition/ESP/NVRAM state before/after.
4. Run **only** `vendomat machine install server`, using the pinned fork and its validated internal `--phases disko,install` route, while the old host is running. Refuse `--disko-mode format` and `mount` and all unreviewed phases. The source VM reported that the new drive booted independently and that the old disk's GPT/ESP stayed intact; this is **P15**, not production proof.
5. Unmount `/mnt` safely. Try the new OS once via a deliberately chosen firmware boot entry and `BootNext` (the original BootOrder remains old first). Verify cold boot, mounts, services, Attic/cache, and fallback. Promote new boot default only after stable real-machine operation. NVRAM behavior of real firmware is still an open gate.

Do not reuse these steps or disko metadata rules for Framework adoption. Disk roles are authorization controls, not system-wide promises that `switch-to-configuration` never writes the ESP.

## 6. Rollback and recovery limits

Source: pinned [`deploy.py`](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines/deploy.py) `start/worker/watchdog/recover/restore`, pinned [`recovery.nix`](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines/recovery.nix), [NixOS manual on rollback](https://nixos.org/manual/nixos/stable/).

- **What native Machines can recover:** it retains previous/requested NixOS closures and an executor GC root; transaction state under `/var/lib/devenv-machines`; `rollback` sets the system profile to `previousSystem` then invokes the old `switch-to-configuration switch`. Health failures, lost confirmation and activation failures can invoke the watchdog if target systemd remains functional. A boot recovery service exists for an unconfirmed deployment that reaches a later working boot.
- **What it cannot guarantee:** it cannot reverse arbitrary writes to `/home`, `/var/lib`, databases, `nix store` GC, or migrations already applied; cannot rescue a machine where initrd, disk unlock, root mount, systemd, SSH, or bootloader cannot operate; cannot guarantee a previously failed unit permits `switch-to-configuration` rollback (project 15 observed systemd exit 4 and rollback failure). A standalone HM role is activated separately **after** NixOS transaction and has no atomic combined rollback. Move HM into NixOS if shared rollback is required, but that restores declarative managed paths only, **not mutable home content**.
- **Bootloader/ESP single-drive risk:** on an adopted single-drive host the new `switch` can update `/boot`/EFI entries on the *same* ESP as the working system; no second disk acts as fallback. `canTouchEfiVariables = false` concerns EFI variable modification, not all ESP file changes. Booted old generations may be pruned by configuration limits or GC. Baseline must retain an old boot entry and working initrd/root/unlock. Review ESP free space, bootloader type and generation limit.
- **Offline fallback:** firmware/boot manager chooses known-good old generation; if its ESP entry is missing, boot external pinned NixOS rescue media, unlock actual LUKS/Btrfs/etc, mount *existing* UUIDs (never disko), inspect old `/nix/var/nix/profiles/system-N-link`, repair/restore old boot files, and boot it without depending on the new OS networking. Prove this in an isolated VM with persistent OVMF and a rescue ISO *before* adoption. Filesystem-/loader-specific commands can only be finalized after live read-only inventory.

## 7. Acceptance matrix, observations vs inference

| Case | What was actually observed so far | Required test / interpretation |
|---|---|---|
| P15 server fresh install | Two-disk QEMU VM in agent F; old drive GPT/ESP stable, new drive booted | Server still needs PV-02, production firmware/boot proof |
| P15 Machines deploy/rollback | Project-15 agent G tested `plan/deploy/status/rollback`, health failure and self-deploy in NixOS VM | **Not adoption**; does not prove preservation of an existing populated installation |
| Standalone HM -> embedded HM | Official HM collision/backup and NixOS module behavior documented | **OPEN:** populated same-user VM transition, then reboot and rollback |
| Adoption without disko | Native code's input/evaluation logic and official guide permit it | **OPEN:** proof on a *previously installed* VM with unchanged partition table/UUIDs |
| Existing machine running installer by accident | Source shows default disko wipes; project 15 observed bad phase effects | **OPEN:** fork-level install policy and every raw CLI phase denial fixture |
| Missing root deploy key | Target requires root SSH for NixOS deploy | **OPEN:** before/after transition from old management, key-only auth and loss of key failure |
| Existing age key retained | sops-nix documents non-store key file and host SSH identity modes | **OPEN:** decrypt/health check before/after without `install.secrets` |
| nixpkgs pin preservation | Native Machines evaluates NixOS from `inputs.nixpkgs` | **OPEN:** compare effective old/new pinned package paths and service versions |
| Bad UUID / role / health / unit | P15 shows a failed unit can cause rollback failure; synthetic role predicate suite 11/11 | **OPEN:** real VM failures with before/after disk metadata and exact logs |
| Failed reboot or networking | Pinned executor code includes boot recovery path | **OPEN:** rescue from firmware/offline media with a broken new generation |

The supplied `fixtures/policy_contract.py` is a **synthetic** role checker and was executed here (11/11). It does not prove the actual Vendomat module or patched devenv Rust guard. `fixtures/capture-guest-state.sh` passed Bash syntax validation here. `fixtures/VM-TEST-PLAN.md` lists 13 acceptance scenarios and captures the required evidence. There are **no newly executed NixOS VM results**, so the deliverable explicitly **does not mark VM gates passed**.

## 8. Proposed V6 requirement changes (new IDs only)

**Do not edit existing requirement text in place.** In V6 draft, mark each changed requirement superseded and add the successor. Existing V5 requirements remain authoritative until V6 acceptance. These are **proposals**, not accepted norms. Keep the V6 concept, V6 spec, and future implementation aligned after testing.

| Existing ID | Proposed disposition | New ID / proposed normative text and verification |
|---|---|---|
| `MACH-011` | Supersede; direct `install` on Framework is unsafe | **`MACH-014`**: Adopt an already-bootable Framework using `plan`/`apply` or `deploy` with **no install/kexec/facter/disko/nixos-install/reboot phase**. VM: old data + disk IDs before/after + boot and rollback |
| `MACH-003` | Supersede to separate input requirement from layout | **`MACH-015`**: Both NixOS modes pin a `disko` input for Machines evaluation; an adopted host MUST have no disko disk declarations; committed facter report or `hardware.facter=null`; preserve existing hardware module as baseline. Nix build fixture both modes |
| `MACH-010` | Supersede to scope blank-drive guards precisely | **`MACH-016`**: Before fresh disko, require every existing blank-drive preflight; adoption MUST instead compare current hardware/layout/key/boot/hashes read-only and MUST never test for a blank disk as a precondition. Fail-closed fixture for both |
| `MACH-012` | Supersede to require staged standalone migration | **`MACH-017`**: HM inside NixOS only **after** a lossless standalone-to-embedded VM cutover; keep exact HM revision, stateVersion, unmanaged files, standalone recovery generations until gate passes. VM collision/rollback proof |
| `MACH-013` | Supersede to isolate initial adoption from release-default upgrades | **`MACH-018`**: Vendomat may supply a tested nixpkgs default to new workspaces, but Framework's baseline adoption MUST pin the current effective rev and postpone every migration until later. Prove equal locked rev and no unapproved package/service drift |
| `MACH-002` | Supersede its unconditional nixos-unstable requirement for adoption | **`MACH-019`**: Use plain pinned `github:NixOS/nixpkgs/<rev>`; fresh systems use release-tested default, adoption cutover may use an exact legacy pin in a separately locked temporary `nix-systems` adoption workspace because Machines uses one `inputs.nixpkgs` per workspace. Merge only after independent upgrade |
| `MACH-004` | Retain; add bootstrap detail | **`MACH-020`**: First adoption MUST bootstrap/test the root deploy public key through the **existing** configuration route, key-only with known-host pin; refuse apply without verified root SSH. VM missing-key/working-key test |
| `MACH-005` | Retain native commands; no Vendomat deployment wrapper | Additional gate in `MACH-014/016`: prefer a reviewed, named `plan` + `apply`, with recorded target identity and no `deploy` without explicit host during first cutover |
| `MACH-006` | Retain failed-unit rule, strengthen verification | **`MACH-022`**: Baseline `systemctl --failed` and critical user-service health MUST be clean or explicitly resolved **before** deploy; VM pre-existing failed-unit injection and rollback-failed result |
| `MACH-008`, `MACH-009` | Retain **fresh server only** | Explicitly out of scope for adopted Framework |
| `VMOD-012` | Supersede; original is incomplete for adoption | **`VMOD-016`**: Host-mode-sensitive inventory/NixOS evaluation assertions with *zero* adopted disko disks and stable existing mount devices; fresh disko paths only to declared install-target. Test direct `devenv build` with bad roles/layout |
| `DISK-008` | Supersede to avoid requiring disko/UUID *creation* during adoption | **`DISK-009`**: Preset and test new GPT/filesystem UUIDs only when creating fresh server disks. Adopted host MUST preserve existing observed UUID/PARTUUID, partition table, filesystem types, ESP and unlock/mount paths. Before/after VM comparisons |
| `SEC-001` | Supersede unconditional install.secrets | **`SEC-003`**: Fresh installs may use `install.secrets` for age key with pinned fork; adopted host MUST retain its existing age/host identity or provision securely under its current NixOS mechanism, with *no install phase*, then prove sops-nix decrypt after deploy and reboot; no plaintext in store |
| `DVN-003`, `DVN-007` | Retain; add a fork-patch acceptance requirement | **`DVN-009`**: Pinned patched Machines CLI MUST deny all `install` phases for an adopted host before contacting target and enforce attested fresh-host preflight for fresh install even on direct CLI calls. All phase combinations and bypass attempts in VM |
| `VMOD-011` | Retain module ownership | Mode policy must flow to native `machinesMeta` without allowing a second `machines.H.nixos` definition |
| `BOOT-019` (V5) | Review its now-invalid 'laptop install' wording when accepting V6 | **`BOOT-026`**: Cold-substitution / no local builds for Framework **first deploy** and subsequent deploys; no laptop formatting/install step. Verify target closure copy and builder logs, separately from adoption preservation |

**ID reservation note:** `MACH-021` is intentionally reserved in this draft for the direct-install policy schema if the proven implementation needs an extra requirement. Do not adopt or silently fill it until interface testing. Follow active ID ledger; if another branch has since allocated a proposed ID, allocate a new unused ID rather than reusing it. `MACH-022` is the new failed-unit gate. No existing ID has been overwritten in this research.

**Duplicate-claim search required before integration:** V6 spec and concept references to `framework ... install` (`MACH-011`, concept Build order step 6), `MACH-003` disko requirement, `MACH-010` blank-target preflight, `MACH-012` HM rollback, `MACH-013` global nixos-unstable, `VMOD-012` all disko, `DISK-008` UUID formatting, `SEC-001` install.secrets. Also search V5 `BOOT-019`, `BOOT-021..024`, `DISK-002..007`, `CLI-011..013`, and project-15 proposal `BOOT-025`. Historical project 15 proposals are **not normative**. Re-scope or supersede conflicting legacy claims **without renumbering** and search for matching wording across guide and future implementation. A source string search of the two attached V6 docs confirms each named conflict; a full repository search should be performed with Gitman/Testee in the native development environment before merging.

## 9. Implementation sequence and acceptance gates

**Shared prerequisites (no production writes):**

1. Implement schema for host mode and disk roles; decide exact field names by pinned prototype. Add valid/invalid evaluation fixtures and Testee verification. **Gate:** all wrong-command/role claims fail closed, no lax fallback.
2. Add the smallest fork patch for install prohibition/attested fresh-install path, adjust patch ledger and bump checklist, pin a new test tag. **Gate:** direct raw Machines `install`, with phase subsets and disk modes, cannot contact or write an adopted VM; fresh route only runs after binding runtime preflight. Code inspection alone not a pass.
3. Add separate read-only preflight specifications and on-disk evidence manifest, plus reviewed plan display for changes to ESP/bootloader, filesystem mappings, services and Home Manager. **Gate:** identical baseline reproducible, injected errors refuse execution before writes.

**Needed before SERVER fresh install (independent of Framework):**

4. Preserve `MACH-008/009`, blank `MACH-010` behavior and `DISK-008` fresh UUID policy (successor IDs later). Run existing project-15 two-disk QEMU test with the **actual new fork CLI**, strict by-id check and old-drive/NVRAM snapshot. **Gate:** protected old-drive GPT/ESP and default boot order unchanged; new disk boots alone; format/mount bypass refused.
5. Clear blockers PV-02 (privileged real server target signatures), facter report, install payload fix on fork, actual root SSH deploy access, cache cold-substitution, and firmware BootNext behavior. **Gate:** only then consider real fresh install. No production action under this research assignment.

**Needed before FRAMEWORK adoption (separate later lane):**

6. Obtain actual read-only Framework hardware/system/HM/encryption/boot/UID/key inventory from working OS. **Gate:** every persistence and identity item resolved and privately logged, no guessed disk layout.
7. Preserve current nixpkgs/HM/service pins; bootstrap tested root SSH key and age identity with the old management route. **Gate:** initial plan shows no unapproved upgrade/migration, sops decrypt works, standalone rollback survives.
8. Build and boot an already-populated NixOS VM with *no disko layout* and embedded Home Manager transition. Run all acceptance cases in `fixtures/VM-TEST-PLAN.md`: normal generation, reboot, rollback, bad UUID, wrong role, failed health, absent key, failed unit, user-file conflict, and offline recovery. **Gate:** saved before/after hashes/UUIDs and actual guest outputs; successful offline old-generation boot.
9. Plan and review real Framework deploy separately from any OS/library/service upgrade; apply only after operator authorization, retain previous boot generation and backups. **Gate:** post-reboot health, mount/UUID/UID invariants, authorized ESP changes, no unexplained user/service data changes; then exercise a non-destructive second-generation rollback.
10. After both lanes are accepted, separately update the shared pin/architecture, test service migration and HM cleanup, and retire legacy config only after restoration exercises pass.

## 10. Blockers, risk register and source links

| Priority | Risk / blocker | Condition to close |
|---|---|---|
| **P0** | Adopted machine vulnerable to raw `machines install` and `--phases install` without upstream/fork role check | Fork command guard implemented, source reviewed and raw-phase VM negative suite passes |
| **P0** | Framework live filesystem, encryption, ESP, UID, state and HM pin data unavailable | Read-only live inventory and approved baseline captured |
| **P0** | No VM execution in current sandbox (Nix/QEMU/Testee unavailable) | Run prepared VM acceptance suite in Nix-capable isolated host and attach logs |
| **P0** | First Framework root deploy SSH key may not yet exist | Bootstrap under old config and verify locked host key/key-only login |
| **P0** | Framework first cutover could upgrade nixpkgs, HM and services | Exact baseline pin comparison and staged workspace proof |
| **P1** | Initial embedded HM may replace unmanaged symlinks or create two conflicting managers | VM file-collision and rollback proof, old standalone profile retained |
| **P1** | Existing SOPS identity may be absent or incompatible with encrypted recipients | Existing key/public recipient/permission test and VM decrypt check |
| **P1** | Nix rollback cannot undo database or home mutations, failed unit may defeat rollback | Backup+restore rehearsal, pre-existing failed-unit gate |
| **P1** | Single-drive ESP or bootloader entries can be modified by normal switch | Old boot entry preservation, reviewed `/boot` diff and offline OVMF recovery drill |
| **P1** | Server real blank-drive scan and firmware are unproven | PV-02 and hardware BootNext test, separate from adoption |
| **P2** | Native `machines install` facter phase invokes raw `git add`, violating Gitman policy | Pre-generate and commit facter through Gitman; omit facter phase in controlled install |
| **P2** | Patch fork release and V6 command metadata may drift | Pinned commit and patches with exact version + Testee regression |

**Primary documentation:** [devenv Machines](https://devenv.sh/machines/), [pinned Rust Machines](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/devenv/src/devenv/machines.rs), [pinned Nix Machines](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines.nix), [pinned executor](https://github.com/cachix/devenv/blob/b904dcb51fe48c30db250038241507f60752f222/src/modules/machines/deploy.py), [pinned disk script](https://github.com/nix-community/disko/blob/de5708739256238fb912c62f03988815db89ec9a/lib/default.nix), [sops-nix](https://github.com/Mic92/sops-nix/blob/master/README.md), [Home Manager NixOS](https://nix-community.github.io/home-manager/options/nixos/home-manager.html), [Home Manager collision rules](https://nix-community.github.io/home-manager/usage/dotfiles.html), [NixOS rollback manual](https://nixos.org/manual/nixos/stable/).

**Final evidence status:** design recommendation **SUPPORTED**; native paths **SOURCE-CONFIRMED**; fresh server VM route **PREVIOUSLY REPORTED (P15)**; 11/11 synthetic policy model **PASSED**; capture script syntax **PASSED**; adopted NixOS VM, disko bypass patch, Home Manager migration, failed reboot/offline rescue and real hardware **NOT TESTED / OPEN**. Do not deploy based on this document alone.

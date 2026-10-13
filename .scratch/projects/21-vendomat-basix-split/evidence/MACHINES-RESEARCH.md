<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-12/machines-research/REPORT.md. The devenv v2.4.0 source clone is in /home/andrew/.local/state/vendomat/p21/2026-10-12/devenv-src/. -->

# devenv Machines research (devenv v2.4.0, b904dcb) — 2026-10-12

Written by a read-only Sonnet subagent; saved by the orchestrator because the subagent could not
write files. Source clone: `~/.local/state/vendomat/p21/2026-10-12/devenv-src/` (tag v2.4.0).

Notation: SRC = the clone. N = SRC/src/modules/machines.nix. R = SRC/devenv/src/devenv/machines.rs.
D = SRC/src/modules/machines/deploy.py. DOC = SRC/docs/src/content/docs/machines.md.
P20 = vendomat/.scratch/projects/20-vendomat-front-door/evidence. FORK = vendomat/devenv-dist/patches.
Fact = read in source, docs, or --help. Inference = reasoning. Unproved = no fixture ran it.
The old "machines.rs:1704" is fork numbering; stock is R:1274.

## Summary

1. Eval and build are local and need no target. `devenv build machines.NAME.build.nixos` and
   `.build.diskoScript` work with no `target.host` and no SSH.
2. Every NixOS or nix-darwin step touches a target over root SSH plus `nix copy --to ssh://`. No
   local target. `localhost` still uses SSH. Only home-manager activates in process.
3. Install = kexec, facter, disko, install, reboot, all over SSH. DOC: boot an installer yourself
   and use `--phases facter,disko,install,reboot` when kexec is unavailable. Fork patch 0006
   refuses a phase set that joins kexec or reboot with disko or install.
4. A local ISO install is a hand-run sequence: build toplevel and disko script, run disko, then
   `nixos-install --system TOP --no-root-password --no-channel-copy`. devenv has no CLI for it and
   no ISO builder. The only image is the nixos-images kexec tarball.
5. Deploy uses real NixOS generations (`nix-env --profile /nix/var/nix/profiles/system --set`,
   then `switch-to-configuration switch`). A target-side watchdog adds rollback. State lives in
   /var/lib/devenv-machines.
6. SecretSpec is optional and install-only. A keyless install needs only a root login method
   (SSH key or password hash) in the NixOS config.
7. No hooks around deploy or install, no shared default modules, no cache wiring. `nixos` is one
   `unspecified` module value.
8. Patch 0001 is merged upstream (PR #3255, a5fd551) but in no release; latest tag v2.4.0.
   Patches 0005 and 0006 are fork-only.
9. No upstream issue or PR asks for local deploy, ISO install, or deploy-to-self.

## 1. Nix side

Options of `machines.<name>` (N:757-761, N:285-749): `system` (N:287); `target.host` nullOr str
(N:257-267); `target.sshOpts` (N:269); `nixos`, `home-manager`, `nix-darwin`, each
`nullOr unspecified` (N:301, 568, 581); `hardware.facter`, default ".machines/${name}/facter.json",
null opts out (N:314-339); `install.{kexec.{image,postSshPort}, extraFiles, secrets, secretspec,
encryptionKeys, copyHostKeys}` (N:341-566); `deploy.healthCheck` (default "true") and
`deploy.rollbackTimeout` (30-600, default 300) (N:625-644); internal outputs `build.{nixos,
deployer, nix-darwin, home-manager, diskoScript, diskoFormatScript, diskoMountScript}`
(N:604-679); `installCheck.hasRootAuth` (N:692). No machine-level `disko` option; disko is always
required for a NixOS machine (N:127-129); facter required unless `hardware.facter = null`
(N:131-135). Fork adds `vendomat.mode`, `vendomat.preflight.{program,ttlSeconds}`,
`build.vendomatPreflight`, `installCheck.diskoDevices`.

NixOS config (`nixosEval`, N:126-182): `(nixosSystemFor system) { specialArgs = { inherit inputs
self; }; modules = [...]; }`. Module order: hostPlatform, disko module, `machines/recovery.nix`,
`machines/facts.nix` (writes /etc/devenv/machine-facts.json), `machine.nixos`, optional
secretspec launcher, facter modules. Toplevel = `_nixosEval.config.system.build.toplevel` (N:719).
`_nixosEval` is an internal option (N:684, set at N:711), so a module can read any
`system.build.*` attribute from it (orchestrator check; unproved by build).
CLI builds `machines.{name}.build.{role}` (R:3172-3179) and reads `machinesMeta` (R:2483-2487).
P2D F1: `devenv eval machines.box.build.nixos` gives the same path with or without target.host.
Inference (tested by subagent): two definitions of `machines.X.nixos` merge shallowly; attrset plus
function conflicts. Set `nixos` once as `{ imports = [ ... ]; }`.

## 2. Targets

No local target for NixOS or nix-darwin (N:261-264: "Leave unset to activate in process on the
current host; this is only valid for `home-manager`. ... "localhost" still routes through SSH.";
DOC line 47; R:2530; install "always operates over SSH" R:1274-1275; P20 F-install rc 1).
Deploy: controller builds `build.nixos` and `build.deployer`, observes target over SSH
(R:2587-2645), saves a plan, confirms (R:2452), `nix copy --to ssh://` (R:2893-2899,
R:3181-3209), runs `<deployer>/bin/devenv-machine-deploy start ID TOPLEVEL --expected-system ..
--expected-profile ..` (R:3055-3100). Target: writes /var/lib/devenv-machines/current.json and
gcroots (D:235-254), arms watchdog via `systemd-run --on-active` (D:326-345), starts
devenv-machine-ID.service (D:346-362); worker runs `nix-env --profile .. --set TOP` then
`TOP/bin/switch-to-configuration switch` (D:404-410), checks, runs health check, waits for
`confirm`. No reboot or repartition. Home-manager `activate` follows (R:2958-2982).

## 3. Install

Phases (cli.rs:1088-1096): kexec, facter, disko, install, reboot. Preflight SSH probe (R:1816).
kexec (R:1877-1925, default URL R:677-692, override `install.kexec.image`). facter (R:1935-1982)
writes .machines/NAME/facter.json. Root-auth check (R:1656-1674). Build toplevel first (R:1682).
encryptionKeys before disko (R:2028). disko (R:1983-2005). install (R:2007-2025): `nix copy`, then
`nixos-install --system TOP --no-root-password --no-channel-copy`. extraFiles, secrets, host keys
(R:1733 on, R:1798, R:2255). reboot (R:2267-2292).
Fork 0006 forces split phases and a target-side preflight program. Local ISO route (inference):
build `build.diskoScript` and `build.nixos`, run the script, run nixos-install; extraFiles,
secrets, encryptionKeys, copyHostKeys must be redone by hand (P2D Q2 agrees). Alternative: fork
CLI on the ISO with `root@localhost` (unproved). No ISO builder in devenv.

## 4. Plan / apply / status / rollback

Transactional (D:1-4): activation as a systemd unit, under a lock, with watchdog rollback on
failure, failed health check, or missing confirm. Phases D:21, D:96-105. Target state
/var/lib/devenv-machines/{current.json,lock}; gcroots /nix/var/nix/gcroots/devenv-machines/ID/.
Controller state .devenv/machine-plans/ID/ and .machines/NAME/facter.json. Boot recovery unit
devenv-machines-recover (recovery.nix:5-21). Rollback = `nix-env --set PREVIOUS` + switch
(D:540-555); native boot menu still works. NixOS only.

## 5. Secrets

Optional; `install.secrets` only (N:475-531), plus opportunistic CACHIX_AUTH_TOKEN (R:1384). Local
mode needs secretspec enabled (R:1404). Sending files forces strict SSH (R:50-72). Bootstrap files
are install-only (upstream #3232). Keyless install and boot: yes, given root auth in config
(R:1656, N:730-748).

## 6. Fleet

`--use-machines-as-builders` (cli.rs:1370, 1433; R:566-616; backend.rs:1741-1756; issue #3262,
PR #3263). `--max-concurrent`: install all at once (R:1513); deploy 1 at a time by default.
`plan`/`apply ID`/`plan --json`. No substituter or cache wiring anywhere; deploy pushes with
`nix copy --to ssh://` and the target must trust paths.

## 7. Extension points

machines.nix imported by top-level.nix:326, so any module can set `machines.<n>.*`. No
`machines.defaults`, no extra-modules list, no hooks or tasks around deploy or install. User hooks:
`deploy.healthCheck`, `install.*` files, fork preflight.

## 8. Fork patches

0001: `-o PermitLocalCommand=yes -o LocalCommand=echo started` for nix SSH; merged upstream as
PR #3255 (a5fd551a, 2026-10-08), not released. 0005: `vendomat.mode` fresh-install |
adopt-existing; refuses install for adopt-existing. 0006: mode required; preflight program before
disk phases; split phase sets; preflight report schema vendomat.preflight/v1 with nonce, machine-id,
boot-id, exact disk set, TTL. Both guard only the remote door.

## 9. Upstream

No request for local deploy, ISO install, or deploy-to-self. Related: #3073 (Machines added),
#3226 (use existing nixosConfigurations), #3242 (non-root SSH), #3232 (deploy-time secrets),
#3262/#3263 (builder SSH identity), #3254/#3255 (0001 hang).

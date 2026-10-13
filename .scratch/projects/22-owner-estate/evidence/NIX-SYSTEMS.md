# nix-systems and vendomat-demo as Vendomat consumers — 2026-10-13

<!-- Provenance: a read-only subagent study on 2026-10-13 of ~/Documents/Projects/nix-systems,
~/Documents/Projects/vendomat-demo, and the v6-* workspaces under gitman-workspaces. The subagent did
not read Vendomat's concept documents; Vendomat behaviour here is inferred from the consumers. The
subagent could not write this file (permission refusal); the orchestrator wrote it from the
subagent's report, with the owner's permission. -->

Read-only. Nothing was built, switched, or changed.

## Structure

nix-systems: first commit 2026-10-09, last 2026-10-12, 12 commits. jj-managed.

- **Not a flake.** It is a devenv project. `devenv.yaml` holds `require_version: 2.4.0` and
  `imports: [./.vendomat]`. `devenv.nix` imports `inputs.vendomat.devenvModules.default`. Vendomat's
  module owns `machines.<host>.nixos`.
- **Inventory.** `inventory/default.nix` (59 lines) is plain data: the deploy key, the server host
  key, login public keys, per-host `mode` (`fresh-install` or `adopt-existing`), disks by
  `/dev/disk/by-id` with model, serial, and size, and preset partition and filesystem UUIDs.
  `AGENTS.md` says it is the only place that names a disk, key, or host fact. `devenv.nix` declares
  each host in `vendomat.inventory.<host>` (mode, disks, `nixos.imports`) and `machines.<host>`
  (system, `target.host`, `sshOpts`, a pinned `known_hosts`, `deploy.rollbackTimeout = 300`, and a
  `healthCheck` that fails, and so rolls back, when any systemd unit has failed).
- **nixos/.** `core.nix` (65 lines) is the shared core: systemd-boot, Nix settings with the Attic
  substituter, key-only SSH, user `andrew`, timezone. It must boot and accept SSH with no Vendomat
  service. `server.nix` (202 lines) adds sops, Tailscale, a git-daemon source collection, Attic,
  Dagu through `inputs.devman.nixosModules.default` with a `mkRegistry`, and the docman library
  face. It also installs gitman, repoman, testee, copyroom, gh, uv, and the patched devenv CLI.
  `hardware/server.nix` and `server-disk.nix` (disko) describe the server. `framework.nix` is a
  provisional laptop role with all-zero placeholder UUIDs and a warning not to deploy.
- **Home Manager runs as a NixOS module** (`nixos/home.nix`: `useGlobalPkgs`, `useUserPackages`,
  `users.andrew = import ../home/andrew.nix`). The stated reason: a system rollback also rolls back
  Home Manager state. `home/andrew.nix` is 15 lines: user name, home directory, `stateVersion`, and
  one marker file that the VM tests read. Its comment says to add a program only when a VM check
  covers it.
- **Secrets.** sops-nix, pinned by rev. `secrets/secrets.yaml` is ciphertext copied from
  nix-secrets. `secrets/.sops.yaml` has two age recipients; its header still says "SCAFFOLD ONLY".
  The age identity is the host SSH key. Two secrets are declared: `tailscale-auth-key` and
  `attic-signing-key`.
- **Tests.** `tests/run` needs `/dev/kvm`. It serves a disposable collection, locks and builds a
  copy of the repository, boots the core in a VM, then runs the Machines flow (check, plan, apply,
  status, rollback, a failing health check, key refusal, the failed-unit gate, a library face, Home
  Manager, a framework tripwire). `tests/services/services-vm` boots the production `server.nix`
  with a test overlay. `tests/disk/` is a two-disk QEMU harness for the fresh-install route.

## How Vendomat is used

`vendomat.toml` is the registry. It is the V5/V6 format; project 21 replaces it with
`vendomat.yaml`.

- `[forge] url = "git://server"`: the collection, served by git-daemon over the tailnet.
- `[targets] devenv = true`.
- `[inputs]`: the devenv fork (`v2.4.0-vendomat.2`, `dir = src/modules`) and its CLI from the
  collection; Vendomat `v0.7.0-rc.1`, repoman `v0.12.1`, gitman `v0.13.0`, testee `v0.5.0`, docman
  `v0.3.1`, copyroom `v0.8.6`, and devman `v0.8.0` from GitHub tags. A comment calls the GitHub
  route interim.
- `[passthrough]`: sops-nix, disko, nixpkgs, and home-manager, pinned by rev.
- `[follows]`: each input follows nixpkgs.
- `vendomat sync` writes `.vendomat/devenv.yaml` ("Do not edit"), `.vendomat/devenv.nix`, and
  `.vendomat/digest`; `vendomat check` verifies the digest. devenv writes `devenv.lock`. Both are
  committed.
- `nixos/core.nix` sets the Attic substituter
  `https://server.tail770f47.ts.net/attic/vendomat`. atticd runs on loopback port 8089 behind
  Tailscale Serve.

## Built and scaffold

Built and VM-tested (per commits and README): the core role, the server role (services VM, disk
harness), Home Manager inside the server role, and the Machines flow with health-check rollback.

Not done: the framework laptop (placeholder); the install on the real 4 TB disk; the collection
route for several inputs; `home/andrew.nix` beyond a stub; real secret decryption on the new
system; a README section that `server.nix` cites ("Decisions that wait") does not exist.

## Comparison with nix-meta

nix-systems is stronger on reproducible pins (tags and revs only, no local paths), hardware safety
(by-id disks, serial and size checks, a mode gate), deployment (plan, apply, health-check rollback,
host-key pins), VM tests of the production role, and generated, digested registry data.

nix-systems is weaker or different on scope (only a server role; no terminal, agent, mnemonix,
backup, or GPU equivalents), reuse (no profile layer yet), coupling (a patched devenv fork and a
Vendomat release candidate), flake outputs (none; deploys go through `devenv machines`), and the
cache (Attic is a hard dependency of the core role).

## Where user configuration and the personal tools sit

- The personal tools are system packages in `nixos/server.nix`. Dagu comes from devman's NixOS
  module, with a project list hardcoded in `server.nix`.
- `home/andrew.nix` could host user configuration structurally, but it holds none today.
- **Inference:** project 22's standalone home (recommendation A1) removes `nixos/home.nix` and the
  personal tools from `server.nix`. It keeps Dagu's `linger` on the machine.

## Integration observations

- Moving nix-meta's machine content here means porting its profiles into `nixos/` modules, adding
  inventory entries, and replacing local inputs with tagged ones.
- Blockers: no flake outputs; no profile composition; a different lock model (`devenv.lock` and a
  digest against `flake.lock`); collection tag discipline; unproved hardware and secrets; a
  Vendomat release candidate and a fork tag (`.2` here, `.3` in vendomat-demo).
- **Inference:** confirm that nix-meta's `server` and nix-systems' `server` are the same machine
  before merging content. nix-meta's server carries AMD GPU tuning; nix-systems names a Xeon W-2125.

## vendomat-demo

Six commits from 2026-10-10. A small proof of the no-Nix user flow. Its `vendomat.toml` adds
`[imports]` (select a module) and `[settings.<module>]` (values that devenv evaluates as
environment variables), which nix-systems does not use. `EVALUATION.md` records live runs and found
two Vendomat bugs. It does not prove Attic substitution or machine activation.

## The V6 workspaces

Under `~/Documents/Projects/gitman-workspaces/`: `v6-server-role`, `v6-services-rerun`,
`v6-services-vm`, `v6-vm-core`, and `v6-vm-disk` carry nix-systems history (Steps 6 to 8).
`v6-devman` carries devman's store-path registry and the linkman exclude work. `v6-pyjutsu` is a
Rust jj binding. `devman-testee-audit` is not a jj repository. **Inference:** V6 is the
devenv-module registry design with a patched devenv fork, a tag-pinned collection, Attic, and
`devenv machines`. No workspace was checked for work that `main` lacks.

## Unproved

Real hardware install; real sops decryption on the new system; Attic substitution in
vendomat-demo; whether the two `server` names are one machine.

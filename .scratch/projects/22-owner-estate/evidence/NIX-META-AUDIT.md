# nix-meta audit — 2026-10-13

<!-- Provenance: a read-only subagent audit of ~/Documents/Projects/nix-meta on 2026-10-13 at HEAD
f173fd0 ("Stop installing RepoMan machine-wide"), clean tree at that time. The subagent could not
write this file (permission refusal); the orchestrator wrote it from the subagent's report, with
the owner's permission. The orchestrator re-checked HEAD and the lock node counts of the committed
flake.lock afterwards: unchanged (77 nodes). Later the same day the working tree held uncommitted
edits to flake.lock, flake.nix, machines/server.nix, and profiles/developer.nix, and a deleted
gitman.toml, made by another session. The working-tree lock had 81 nodes, 3 repoman nodes
(v0.7.5, v0.14.1, v0.10.0), and new root inputs linkman, mancore, testee, and repoman.
Figures below are for the committed HEAD. -->

Read-only. Nothing was built, switched, or changed. 265 commits, 74 tracked files.

## Inputs

`flake.nix:4-280` declares 21 top-level inputs.

- **Upstream:** `nixpkgs` (nixos-unstable), `pi-nixpkgs` (a second pinned nixpkgs for Pi),
  `home-manager` (`?ref=master`), `devenv` (v2.4.0; keeps its own nixpkgs on purpose, with a
  20-line comment), `claude-code` and `codex-cli` (`?ref=main`), `atuin` (tag v18.23.0).
- **Personal flakes over the network:** `nixos-core` (`?ref=main`, no `follows`),
  `silverbullet-server` (git+ssh, `main`), `inferference` (git+ssh, `main`, `flake = false`),
  `vendomat` (raw rev `d5a90f0`, nested overrides), `devman` (tag v0.7.0).
- **Personal tools:** `gitman` (tag v0.13.1); `vendomat`, which supplies repoman, copyroom,
  templateer, docman, and agentman through `repoman-toolchain-core`; copyroom and templateer as
  `flake = false` sub-inputs of vendomat (`:59-66`). Testee and linkman appear nowhere. The direct
  repoman input went in `f173fd0`.
- **Local `git+file:///home/andrew/...` (7):** nix-paseo (`?ref=main`), nix-secrets (tag v0.1.4),
  nix-terminal (`?ref=main`), mnemonix (tag v0.2.7), atuout (no ref), pytuin (no ref), argentic
  (no ref).
- **Local `path:` (1):** fornix-host. It is locked and imported, but `services.fornix-host.enable =
  false` (`machines/server.nix:464`).
- **Commented out:** zelligate, shellij, structured-agents.

## Machines and profiles

`mkMachine` (`flake.nix:292-295`) is `lib.nixosSystem` with `specialArgs = { inherit inputs; }`
and `[ ./machines/<name>.nix ] ++ profileModules`. Profiles use a curried `inputs:` form; machine
files read `inputs` from `specialArgs`. Two injection styles exist.

One machine: `server` (`flake.nix:306`), a Dell Precision 5820 with two V620 GPUs and an ARCTIC fan
controller. Profiles: minimal, terminal, developer, gpu-compute, agent, secrets, backup, devman,
mnemonix.

Left from the retired hosts: `machines/wsl.nix` (24 lines), `machines/desktop.nix` (18 lines),
`profiles/gui.nix` (15 lines), none referenced; `AGENTS.md`, which still describes them; the
`nix-meta.developer.repoman.*` options (`developer.nix:67-113`); about 150 lines of commented
zelligate, structured-agents, and snapper blocks in `server.nix`.

## Per-file classification

Columns: (a) system infrastructure, (b) Home Manager user configuration, (c) personal tool
delivery, (d) services.

| File (lines) | (a) | (b) | (c) | (d) |
| --- | --- | --- | --- | --- |
| `machines/server.nix` (773) | boot, mounts (`:705-761`), users, linger, SSH, firewall, udev, zram, GC | none | Vendomat NixOS module (`:71`); an inferference user unit (`:117`) | inferference, Paseo, SilverBullet, argentic, atuin server, atticd with Tailscale Serve, Postgres, git-daemon, coolercontrol |
| `machines/hardware/arctic-fan-controller.nix` (669) | kernel module, udev | | | fan watchdog units |
| `machines/hardware/amdgpu-power-profile.nix` (317) | power profile and verify units | | | |
| `profiles/terminal.nix` (228) | Home Manager bootstrap, a UID lookup (`:22`) | nearly all: zsh, atuin, atuout, aliases | pytuin package, nix-terminal | |
| `profiles/developer.nix` (243) | substituters (`:131`) | packages, user units, nixbuild | devenv, gitman and jj, the toolchain on `PATH` (`:178`), agentman units | agentman daemon |
| `profiles/agent.nix` (187) | `environment.systemPackages`: claude-code, codex, zellij | Pi, an atuin-codex hook, a zsh secret export | the agent CLIs | |
| `profiles/secrets.nix` (107) | sops secrets and templates | | | `restartUnits` for Paseo and atticd |
| `profiles/devman.nix` (52) | `lingerUsers` | | devman NixOS module | Dagu user service |
| `profiles/mnemonix.nix` (68) | | `programs.mnemonix` | mnemonix | Hindsight service |
| `profiles/backup.nix` (736) | all | | | restic units, preflight, health timers |
| `profiles/gpu-compute.nix` (170) | all | | | |

`server.nix`, `developer.nix`, `agent.nix`, and `mnemonix.nix` mix concerns. `backup.nix` is one
self-contained module. `machines/hardware/` holds two large reusable modules beside one generated
file.

## Lock graph problems

`flake.lock` at HEAD: 77 nodes.

- **nixpkgs:** 7 real trees: the root, `pi-nixpkgs`, devenv's own, devenv's again through
  Vendomat, nixos-core's (no `follows`), Vendomat's devman's, and nix-nvim's `nixpkgs-neovim`.
- **home-manager:** 2 (the root, and nix-nvim's).
- **devman:** 3 (root v0.7.0; nix-terminal's `main`; Vendomat's v0.5.2).
- **gitman:** 2 (root v0.13.1; Vendomat's v0.9.1).
- **repoman:** 2 (nix-terminal's v0.7.5; Vendomat's v0.10.0).
- Also duplicated: `uv2nix` ×2, `flake-utils` ×3, `flake-compat` ×3, `systems` ×4, `flake-parts` ×2.
- Floating refs: nixos-core, nix-paseo, nix-terminal, silverbullet-server, inferference,
  claude-code, codex-cli (`main`); home-manager (`master`); atuout, pytuin, argentic (no ref).
- `git+file:` inputs fail on a machine without the checkouts. `server.nix:538-564` exists so that
  `sudo nixos-rebuild` can fetch the private git+ssh inputs as root.
- Vendomat is pinned by raw rev, and its nested copyroom and templateer overrides must move
  together.

## Hygiene

- `.worktrees/`: 23 directories, about 13 MB, dated 2026-10-02 to 2026-10-09: `032-fan-lease`,
  `collection-post-receive`, 13 `phase-0-*`, `retire-kickoff-instructions`,
  `retire-personal-layer`, `source-collection`, 4 `v620-*`, `vendomat-0-5-0`. Not judged for
  unlanded work.
- `.gitman/workspaces/`: `mnemonix-memprojects` (2026-10-12).
- `artifacts/`: 17 directories, ignored, untracked. `result`: ignored symlink to a system build.
- `RESEARCH_REPORT.md` (tracked, 2026-09-04 content) duplicates a file in `.scratch/projects/02-*`.
- `devenv.lock` is tracked, but no `devenv.yaml` or `devenv.nix` exists.

## Checks

One flake check, `atuin-server-runtime` (`flake.nix:309-332`). It reads
`serverConfig.home-manager.users.andrew.programs.atuin.package` and the server package, and
compares versions with the literal `18.23.0`. The version appears in four places. No evaluation
check of the machine itself; no CI. `scripts/` (1,291 lines of shell) are manual acceptance
scripts.

## Coupling that blocks standalone Home Manager

1. The check at `flake.nix:309-332` reads the Home Manager NixOS module path.
2. `terminal.nix:22` reads `config.users.users.<user>.uid`.
3. The atuin client (`terminal.nix:197-200`) and server (`server.nix:315-334`) share
   `nix/atuin-18.23.0.nix`.
4. `mnemonix.nix:12,60-65` reads `config.services.mnemonix.hindsight.*` from the NixOS side.
5. `agent.nix:88-95,171` reads `/run/secrets/*` at run time.
6. The agentman user units (`developer.nix:184-211`) need the Postgres role in
   `server.nix:419-439`.
7. `devman.nix:19` uses devman's NixOS module, which installs a user service.
8. `server.nix:71` installs `/run/current-system/sw/share/vendomat/...` for devenv consumers.
9. `developer.nix:131-136` sets substituters, a NixOS-only option.
10. `useGlobalPkgs = true` gives Home Manager the system's overlays and `nixpkgs.config`.
11. `server.nix:117-131` declares the inferference user unit through a NixOS module.
12. `secrets.nix:55-70` restarts system units.
13. `agent.nix:39-47` installs the agent CLIs system-wide.

## Restructuring sketch (subagent proposal)

```
flake.nix          inputs and outputs only
lib/               mkHost, mkHome, constants (user, tailnet host, paths)
overlays/          one atuin, silverbullet, pi
packages/          atuin, arctic-fan-controller, silverbullet, attic-server
modules/nixos/     one module per concern
modules/home/      terminal, developer, agent, mnemonix
hosts/server/      identity, hardware, storage, services, networking
homes/andrew/      shared and per-host
checks/            evaluation, atuin parity, module tests
```

Value order proposed: split the personal tools first; add one constants file; replace local inputs
with tagged ones; deduplicate the lock; decide the devenv module path before moving devman or
Vendomat delivery; delete dead code and rewrite `AGENTS.md`.

## Unproved

Whether the 23 worktrees hold unlanded work; whether root still fetches Home Manager-only private
inputs after the split; a standalone home that evaluates with the current modules.

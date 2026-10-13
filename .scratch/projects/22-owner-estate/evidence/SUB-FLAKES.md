# Composed flakes around nix-meta — 2026-10-13

<!-- Provenance: a read-only subagent survey on 2026-10-13 of each repository's flake.nix,
flake.lock, AGENTS.md, git log, and modules/, and of nix-meta's flake.nix, profiles/, and
machines/. Commit counts from `git rev-list --count HEAD`. The subagent could not write this file
(permission refusal); the orchestrator wrote it from the subagent's report, with the owner's
permission. -->

Read-only. Nothing was built or changed.

## The flakes

| Flake | Purpose | Kind | Consumed by nix-meta (pin) | Last commit, count | Status |
| --- | --- | --- | --- | --- | --- |
| nixos-core | Base system modules (user, Nix, SSH, Tailscale), desktop, nvidia-compute, kanata, cross-compile, WSL | NixOS | Yes, `?ref=main` | 2026-10-02, 21 | Active |
| nix-terminal | Terminal environment (zsh, atuin, tmux, starship, nvim, development, scripts) plus `nixbuild` and `repoman` modules | Home Manager | Yes, `git+file://`, `?ref=main` | 2026-10-02, 80 | Active; stale pins |
| nix-nvim | Neovim module; supersedes nixvim | Home Manager | Through nix-terminal (`github:`, `main`) | 2026-10-13, 70 | Active |
| nixvim | Older Neovim module | Home Manager | No ("the retired, broken nixvim input") | 2026-10-03, 73 | Superseded |
| nix-desktop | niri, noctalia, walker, workspace groups, kitty | Home Manager | No | 2026-10-13, 52 | Dormant |
| nix-paseo | Paseo agent server | NixOS | Yes, `git+file://`, `?ref=main` | 2026-10-13, 91 | Active |
| nix-secrets | sops-nix wrapper and operator scripts | NixOS | Yes, `git+file://`, tag v0.1.4 | 2026-10-13, 63 | Active |
| mnemonix | Hindsight memory service and coding-agent wiring | Both, plus a package | Yes, `git+file://`, tag v0.2.7 | 2026-10-12, 53 | Active |
| atuout | Atuin output archiver | Home Manager, package | Yes, `git+file://`, no ref | 2026-10-03, 53 | Active |
| pytuin | Atuin SDK, server module, client module | Both, package | Yes, `git+file://`, no ref | 2026-10-12, 59 | Active |
| nix-meta-channel4 | A git worktree of nix-meta on `v620-channel4-fan` | none | No | no commits | Stale scratch copy |
| nixbuild | `nixos-rebuild-test` CLI, NixOS module, VM-test helper | package, NixOS | Through nix-terminal | 2026-10-02, 72 | Low value |
| fornix | Agent sandbox tool; no top-level flake | product | `fornix-host` as `path:` | 2026-10-11, 57 | Active product |
| template-nix | CopyRoom template workshop; no flake | template | No | 2026-10-12, 20 | Tooling |
| vendomat-demo | Vendomat V6 demo; no flake | demo | No | 2026-10-11, 6 | Demo |

## Overlap and duplicate lock nodes

- nix-terminal pins `devman = github:Bullish-Design/devman/main` and `repoman` at v0.7.5. These are
  nix-meta's `devman_2` and repoman v0.7.5 nodes. The 2026-10-13 commits that removed RepoMan from
  nix-meta, nix-nvim, nix-desktop, and nix-paseo did not touch nix-terminal. It still ships
  `homeManagerModules.repoman` and a `programs.devman` option built on devman's 0.2.0-era
  `lib.mkDevmanEnv`. nix-meta sets `devman.enable = false` (`profiles/terminal.nix:71-90`), and
  `profiles/developer.nix:148` still imports the repoman module.
- nix-terminal pins nixbuild and nix-nvim on `main`.
- nix-terminal's README (lines 14, 105, 288, 374, 441) still names nixvim.
- **Atuin is defined three times plus an input:** pytuin's `atuin-18.23.0.nix`, nix-meta's
  `nix/atuin-18.23.0.nix`, and the `atuinsh/atuin` input. pytuin also vendors
  `atuout-0.2.0.nix`. pytuin's client module conflicts with nix-terminal's `programs.atuin`, so
  nix-meta leaves it off (`profiles/terminal.nix:57-66`). About 200 lines of atuin wiring sit in
  `profiles/terminal.nix`.

## Interface quality

- **Clean, works in standalone Home Manager:** nix-terminal (monolithic; dead `repoman` and
  `devman` options), nix-nvim, nix-desktop, atuout (assumes nix-terminal's zsh order).
- **Hardcoded user facts:**
  - mnemonix `coding-agents.nix`: `/home/andrew/.local/bin/atuin-codex-hook` (lines 65, 72);
    `projectsRoot` and `.memprojects` default to `/home/andrew/Documents/Projects/...` (lines 154,
    160).
  - nixos-core `base.nix`: `username = "andrew"` default (line 16). Every nix-meta profile reads
    `config.nixos-core.base.username`.
  - nix-paseo `paseo.nix`: user `andrew` (255), `/home/andrew/Documents/Projects` (267),
    `/home/andrew/.paseo` (273), `/home/andrew/.paseo/worktrees` (279), example host
    `server.tail770f47.ts.net` (456).
- **NixOS-only by design:** nix-secrets, fornix-host, nixbuild's system module.

## Classification

- **Personal layer (home):** nix-terminal (reshaped), nix-nvim, atuout, mnemonix's Home Manager
  half, pytuin's client and package, nixbuild's CLI.
- **Machine:** nixos-core, nix-secrets, nix-paseo, fornix-host, mnemonix's NixOS half, pytuin's
  server module.
- **Applications:** fornix, pytuin, atuout, nixbuild export packages.
- **Dead or superseded:** nixvim, nix-meta-channel4, nix-terminal's repoman and devman parts.
  nix-desktop is dormant.

## Recommendations (subagent)

1. Archive nixvim; delete the nix-meta-channel4 worktree; fix nix-terminal's README.
2. Remove nix-terminal's repoman and devman inputs and modules and the import at
   `developer.nix:148`. Pin its inputs by tag. Split `terminal` into modules with `enable`.
3. One atuin package, in pytuin; move the atuin wiring into a home module.
4. Remove hardcoded paths from mnemonix's Home Manager module.
5. Remove `andrew` from nixos-core and nix-paseo defaults; stop reading
   `nixos-core.base.username` from profiles.
6. Tag every local input, or pin by rev.
7. Keep nix-desktop for a future laptop home, or archive it.
8. Make nixbuild a plain package flake.
9. Keep fornix-host separate; it is disabled today because of a boot-order cycle
   (`machines/server.nix:455-465`).
10. Target: the machine composes nixos-core, nix-secrets, nix-paseo, fornix-host, and the mnemonix
    and pytuin server modules; the home composes nix-terminal, nix-nvim, atuout, mnemonix's home
    module, and the personal tools.

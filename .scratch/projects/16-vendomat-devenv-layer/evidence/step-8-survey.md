# Step 8 survey — what ties `server` to Vendomat V4

**Date:** 2026-10-09. **Kind:** read-only survey by a subagent. `[O]` = observed, `[I]` = inference.
Revisions are each repository's `main`. The survey changed no file by hand. It did let `jj status`
snapshot the working copy of `~/.config/devman`.

## Corrections to the backlog in `.scratch/CURRENT.md`

- `[O]` Item 3 (the critical path) is done in `repoman`. v0.11.0 (`806f31f0`) and v0.12.0
  (`58832be2`) run managers by name from `PATH`. They read no `REPOMAN_TOOLCHAIN_BIN` and no
  `toolchain.json`.
- `[O]` Item 6 (`linkman`) is done on `main`. It declares no `vendomat` input.
- `[O]` The running login-shell `repoman` is still 0.10.0 from the V4 closure.
- `[O]` The running system carries `vendomat` 0.5.0 and `devman` 0.6.0. `nix-meta` `main`
  (`8b91868f`, one commit ahead of origin) pins newer `devman`, `repoman`, and `gitman`.

## What makes `server` depend on V4

| # | Location | Fact |
| --- | --- | --- |
| 1 | `nix-meta/flake.nix:52`, `flake.lock:1588-1616` | `vendomat` input at V4 commit `d5a90f0`; pulls uv2nix and a private `repoman` v0.10.0 node |
| 2 | `nix-meta/machines/server.nix:63-68` | Imports `inputs.vendomat.nixosModules.default` (CLI, consumer module, `machine.json`) |
| 3 | `nix-meta/profiles/developer.nix:21-22,178-180` | `repoman-toolchain-core` on the login-shell `PATH` |
| 4 | `nix-meta/profiles/developer.nix:184-211` | The `agentman` user socket and service run from the toolchain closure |
| 5 | `nix-meta/profiles/devman.nix:40` | `registryDir = "$HOME/.local/state/vendomat/devman/active"` (generation 4, immutable) |
| 6 | `nix-meta/scripts/repoman-toolchain-test`, `AGENTS.md:136`, `profiles/terminal.nix:134-136` | Read `share/vendomat/toolchain.json`; aliases call retired `repoman sync` |
| 7 | `~/.config/devman/projects/*/devenv.local.nix` | 13 central overlays import `/run/current-system/sw/share/vendomat/consumer-module.nix`; 4 import a vendomat checkout path |
| 8 | `mnemonix/devenv.nix:13`, `nix-nvim/devenv.yaml:54`, `mancore/devenv.yaml:59` | Import the consumer module or `vendomat/modules` |

## Inputs the new `server` role can use as they are

| Input | Tag | Output |
| --- | --- | --- |
| `repoman` | v0.12.0 | `packages.default`, `nixosModules.default` |
| `gitman` | v0.12.1 | `packages.gitman`, `packages.jujutsu-bin` |
| `testee` | v0.5.0 | `packages.default` (today only in an imperative profile) |
| `devman` | v0.7.0 | `nixosModules.default` (`services.devman-dagu`) |
| `linkman` | v0.1.0 | `packages.linkman` |
| `nix-secrets` | v0.1.4 | `nixosModules.secrets` (sops-nix; age key = host SSH key) |
| `nixos-core` | none (rev `5b13f985`) | `nixosModules.base` |
| `vendomat` | none after V4's v0.4.6 | `packages.x86_64-linux.vendomat`; needs a tag |

## Repositories that need a change, in dependency order

1. A Python core repository with a uv2nix `lib` (backlog item 2). `[I]`
2. `pyjutsu`: no `flake.nix`. Needs `packages.default` (wheel or maturin build).
3. `docman`: no `flake.nix`. Pure Python (`pydantic`, `typer`); plain nixpkgs builder suffices.
4. `templateer_v2`: no `flake.nix`. `[I]` Likely needs the Python core.
5. `copyroom`: no `flake.nix`. Needs `pyjutsu` and `templateer`.
6. `agentman`: no `flake.nix`. Heavy dependencies; needs the core and `inferference`.
7. `devman`: no Nix function renders a registry from project inputs. `[I]` The module must not
   `mkdir` or watch a store-path `registryDir`.
8. Central overlays: delete the consumer-module import line. Depends on the host `PATH` tools.

## Repository state (do not touch an OPEN repository)

OPEN with uncommitted work: `eventic`, `argentic`, `flora`, `flora-qc`, `loci.nvim`, `nix-nvim`,
and the central overlay repository `~/.config/devman`. Parked work: `loci-core`, `poddantic`.
`[I]` Another session is editing `eventic`, `argentic`, `flora`, and `flora-qc` today.
Clean and required: `repoman`, `gitman`, `devman`, `linkman`, `testee`, `nix-secrets`, `nixos-core`,
`pyjutsu`, `copyroom`, `docman`, `templateer_v2`, `agentman`, `nix-meta`.

## Services the old `server` runs

| Need | Option | Location |
| --- | --- | --- |
| SSH | `services.openssh` key-only | `nixos-core` `modules/base.nix:109-112` |
| Tailnet | `services.tailscale` | `nixos-core` `modules/base.nix:114-116` |
| Source collection | `services.gitDaemon` over `/home/andrew/vendor` | `nix-meta/machines/server.nix:174-180` |
| Attic | `services.atticd`, sqlite, storage under `/mnt/wd_green1/attic` | `server.nix:341-398` |
| Secrets | `nix-secrets.secrets`, template `atticd.env` | `profiles/secrets.nix` |
| Dagu | `services.devman-dagu`, user service, ports 8080/50055 | `profiles/devman.nix:19-51` |
| `agentman` | user socket and service plus PostgreSQL 17 | `developer.nix:184-211`, `server.nix:410-430` |

`[O]` No Attic client substituter or trusted key exists in `nix-meta`. Step 5 and the host core
must add them (`CACHE-010`).

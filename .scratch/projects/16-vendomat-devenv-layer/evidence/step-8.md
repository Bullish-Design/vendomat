# Step 8 — the server role without V4

**Date:** 2026-10-10. **Gate:** G8. **Status:** OPEN. The closure passes. The VM run of the services,
the V4 removal from repositories that hold open work, and `agentman` remain.

Tool flakes, the `devman` registry function, and the `repoman` check are in
[step-8a.md](step-8a.md). This record covers the role that consumes them.

## What the role is

`nix-systems` `main` (private repository `Bullish-Design/nix-systems`) builds `machines.server`
from `nixos/core.nix` and `nixos/server.nix`. Inputs are plain flakes at tags:

| Input | Pin | Use |
| --- | --- | --- |
| `repoman` | v0.12.1 | manager commands by name from `PATH` |
| `gitman` | v0.12.1 | `gitman`, `jujutsu-bin` |
| `testee` | v0.5.0 | the host wrapper |
| `docman` | v0.3.1 | the command, and its `vendomat` description (the library face) |
| `copyroom` | v0.8.1 | the command; brings `pyjutsu` 0.23.1 and `templateer` 0.4.2 |
| `devman` | v0.8.0 | `services.devman-dagu` and `lib.<system>.mkRegistry` |
| `sops-nix` | `dcd241ba…` | runtime secrets |
| `devenv` fork | `v2.4.0-vendomat.1` | modules (`dir=src/modules`) and the CLI |
| `vendomat` | `main`, no tag | launcher and host release |

## Observations

Closure `/nix/store/p5b2c7z6vqcmzvc9201bl3xlqmqxjcpj-nixos-system-server-26.11.20261008.e7439b6`
(3.4 GiB, 879 paths), built with the patched CLI: `devenv build machines.server.build.nixos`.
Raw log: `~/.local/state/vendomat/v6/2026-10-09/08-legacy/server-closure-build-3.log`.

1. **No V4 path.** `nix-store -qR` lists no `toolchain`, `consumer-module`, or `REPOMAN_TOOLCHAIN`
   path, and no file under `etc/` names `REPOMAN_TOOLCHAIN_BIN`.
2. **Tools come from their own flakes.** `repoman-0.12.1`, `gitman-0.12.1`, `jujutsu-bin`, `testee`,
   `docman`, `copyroom-0.8.1`, `devman-0.8.0`, `dagu-2.15.0`, and the patched `devenv-wrapped-2.4.0`.
3. **Dagu reads a store registry.** The unit `dagu.service` and `devman-watch.service` exist, and
   the registry is one store path rendered by `mkRegistry` from a project list.
4. **The library face works through the module.** `vendomat.libs.docman.enable = true` puts the
   command in the closure. `docman` carries a `vendomat` description and no Vendomat input.
5. **`vendomat check` is clean** for the workspace with the patched CLI (pins, fragment, lock, and the
   CLI/module revision).

## Findings

- A flake that exports `nixosModules.default` is not a Vendomat face. The first server role
  imported `nix-secrets`, and the module imported it again. `VMOD-018` fixes the rule.
- `nix-secrets` v0.1.4 pins an older `sops-nix` whose `sops-install-secrets` needs
  `buildGo125Module`, which this nixpkgs removed. The role pins `sops-nix` itself and copies the
  ciphertext (`secrets/secrets.yaml`), which the server's host key decrypts (`ssh-to-age`).
- `linkman` `main` does not build under Nix: its `mancore` dependency is a private repository with
  no flake. **`linkman` v0.1.1 (tagged 2026-10-10 in this work) is broken. Do not use it.** The
  library face moved to `docman` v0.3.1.
- `devenv-cli` brings its own nixpkgs. The sync note names it: `its 'nixpkgs' differs`.

## Open

- A VM that runs the final role's services (source, cache, SSH, secrets, Dagu, library). Step 6
  runs the Machines flow with a stand-in role. The services run as a unit only on hardware.
- V4 removal inside repositories that hold open work: the central overlays under `~/.config/devman`
  and `eventic`, `argentic`, `flora`, `flora-qc`, `loci.nvim`, `nix-nvim`. Another session edits them
  today. `nix-meta` stays unchanged as the recovery reference (`.scratch/CURRENT.md` backlog 4, 5).
- `agentman` is deferred (step-8a.md): its dependencies are not in this nixpkgs.
- A `nix-meta` repin is not needed: the new role does not read it.

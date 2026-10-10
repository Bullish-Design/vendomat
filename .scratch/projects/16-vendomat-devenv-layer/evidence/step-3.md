# Step 3 — the Vendomat module and library faces

**Date:** 2026-10-09. **Gate:** G3. **Status:** PASS for evaluation, direct NixOS builds, and a NixOS VM.
The real `/etc/vendomat/paths.json` and the machine plan paths are Step 6.

## Pins and tools

| Tool | Version |
| --- | --- |
| Nix | 2.34.7 (host) |
| devenv | 2.4.0+b904dcb (host, stock; the patched CLI is Step 1) |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the release default) |
| disko | `de5708739256238fb912c62f03988815db89ec9a` (v1.13.0) |
| Home Manager | `6b88c12cc6d234de4888f5d21076fb11199d0844` (master on 2026-10-09) |
| QEMU | the NixOS test driver of the pinned nixpkgs, `/dev/kvm` |

## What was built

- `nix/devenv-module/` holds the module: `default.nix` (options, composition), `builder.nix` (the
  face builder), `guard.nix` (per-host assertions), and `lock-pin.nix` (the tag check).
- `flake.nix` exports `devenvModules.default` beside `packages.<system>.vendomat`. It has one input,
  `nixpkgs`, now the plain release revision (`DEL-019`, `MACH-018`).

## Runs

| Run | Command | Result |
| --- | --- | --- |
| M1 | `testee check e2e`, run `20261010T022850Z-82b3e6de8adb`, exit 0 | PASS. Includes 30 module cases, the VM test, and the Step 2 story |
| M2 | `nix build --impure --file tests/nix/faces-vm.nix` | PASS. A KVM guest ran the system unit and the user unit |
| M3 | `testee verify --full`, run `20261010T023502Z-94168b9fa588`, exit 0 | PASS |

Raw logs: `~/.local/state/vendomat/v6/2026-10-09/03-module/`.

## Observations

1. **Inertness.** With a described library imported and disabled, the shell, the NixOS toplevel,
   and the Home Manager activation derivation paths equal those of the same workspace without the
   library input (same directory, same lock otherwise).
2. **Enabled faces.** devenv: package in the shell, `processes.knappy`, `KNAPPY_EXTRA`, and a
   process that ran under `devenv up -d`. NixOS: `systemd.services.knappy` runs `…-knappy-start`, the
   firewall port opens. Home Manager: the user unit and the session variable. In the VM both units
   ran `knappy serve`, though the unit PATH holds no `systemPackages`: the start script supplied it.
3. **Hand-written faces** import beside described ones. A description plus a hand-written face is
   an error naming the input.
4. **Machine guard.** Twelve bad layouts fail a direct NixOS evaluation with a named message in both
   modes. A good fresh host (disko disk named `main`, by-id device, preset UUIDs, by-uuid mounts) and
   a good adopted host (no disko disk, `existing-system` disk, by-uuid mounts) evaluate.
   `vendomat.check.enable = false` does not reach the guard.
5. **Pin assertion.** A `refs/heads/main` git node stopped `devenv shell -- true` and named the
   node. A `refs/tags/v1` node passed.

### Findings that changed the design

- A module function that reads `options` at its top level recurses forever. The Home Manager rider
  now sits under `config`.
- Home Manager gives `systemd.user.services.<name>.Service.ExecStart` as a list.
- A `path:` input is a live directory, not a store path. `inputPaths` interpolates, which copies it.
- The disko default mounts use `by-partlabel`. The guard rejects them, so a layout overrides each
  mount with a `by-uuid` device (`DISK-009`).
- `vendomat.inventory.<host>.mode` has no default. A host without a mode fails evaluation.

## Not covered

- `machines.<host>.vendomat.mode` in the patched devenv metadata (`DVN-009`) waits for Step 1.
- The module's `vendomat-push` script is covered by `vendomat push` (Step 4); only its task is
  evaluated here.
- Real `/etc/vendomat/paths.json` and the units on the production system are Step 6 and Step 9.

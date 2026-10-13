# How `machines.NAME.nixos` merges several definitions — 2026-10-12

Fixture files: `~/.local/state/vendomat/p21/2026-10-12/nixos-merge/` (`demo.nix`, `defaults.nix`).

## Inputs

- Nix 2.34.7, `nix-instantiate --eval --strict --json`.
- nixpkgs `lib` from the Vendomat flake lock revision (store path
  `/nix/store/2010s04mqpq7q1kch0ddc9b429s2vh9v-source`).
- devenv v2.4.0 declares `machines.<name>.nixos` as `lib.types.nullOr lib.types.unspecified`
  (`src/modules/machines.nix:301-312`) and passes the value to NixOS as one module
  (`machines.nix:148`).
- The fixture copies that declaration into a plain `lib.evalModules` call, then evaluates the
  resulting value as a module of a two-option stand-in for NixOS (`services.openssh.enable`,
  `environment.systemPackages`). It does not run devenv.

## Cases and results

| Type of `nixos` | Definitions | Expected | Actual |
| --- | --- | --- | --- |
| `nullOr unspecified` | two attrsets: `{ openssh on; packages [git] }` and `{ packages [ripgrep] }` | both packages | `{"pkgs":["ripgrep"],"ssh":true}`; `git` is lost with no error |
| `nullOr unspecified` | an attrset and a function `{ pkgs, ... }: { … }` | merge | `error: Cannot merge definitions of 'machines.laptop.nixos'` |
| `deferredModule` | two attrsets | both packages | `{"pkgs":["ripgrep","git"],"ssh":true}` |
| `deferredModule` | an attrset and a function | merge | `{"pkgs":["ripgrep"],"ssh":true}` |
| `deferredModule` | a second module re-declares `machines` as `attrsOf (submodule { nixos.environment.systemPackages = [ "basix-core" ]; })`; the user sets `firefox` on `laptop` and SSH on `server` | defaults for every machine | `laptop`: `["firefox","basix-core"]`; `server`: `["basix-core"]`, SSH on |

## Observation and inference

- Observed: with the devenv type, two definitions either lose settings silently or fail.
- Observed: with `deferredModule`, definitions merge as module imports, and one module can add a
  default to every machine.
- Inference: a one-line devenv patch (`nullOr deferredModule`) gives the same behaviour in devenv.
  It must keep `null` as "not a NixOS machine". Unproved on the pinned devenv.

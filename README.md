# Vendomat

Vendomat composes one owner's development workspaces and NixOS machines from native devenv,
NixOS, and Home Manager modules. This `0.7.0-rc.1` release candidate exercises the V6 workspace
flow. V6 remains a draft until its machine and cache gates pass and the owner accepts it.

## Workspaces

A workspace lists tagged sources, selected modules, and supported settings in `vendomat.toml`.
`vendomat sync` writes `.vendomat/` and asks devenv to update `devenv.lock`. Nix owns the lock.
The template supplies stable `devenv.nix` and `devenv.yaml` files. A workspace user changes
module selections and settings in TOML without editing Nix. Module authors write native devenv
modules and declare inherited inputs in their own `devenv.yaml`.

The package includes `vendomat-workspace-init`. It needs Templateer on `PATH` and a JSON model
with `forge_url`, `vendomat_tag`, and optional `devenv_tag`:

```sh
vendomat-workspace-init model.json workspace
cd workspace
vendomat sync
devenv shell
```

The private `vendomat-demo` repository is the live consumer for the no-Nix workspace flow.

## Other targets

The flake target writes `flake.nix` for a project that publishes its own flake outputs. Its
project-owned `flake-outputs.nix` defines those outputs. Vendomat also provides `check`, `path`,
`push`, `bump`, and a guarded fresh-machine install command. NixOS and Home Manager own machine
activation. The source collection holds tagged source; Attic holds cached build outputs.

## Verify

Run `testee verify --full` from the repository root. Run `testee check e2e` after a change to the
module, toolchain, or consumer path. Testee opens a clean devenv shell for the checks.

The V6 concept, specification, guide, and gate records are under
`.scratch/projects/16-vendomat-devenv-layer/`. Read `.scratch/CURRENT.md` for the current authority
and open gates.

# Vendomat

Vendomat composes one owner's development workspaces and NixOS machines from native devenv,
NixOS, and Home Manager modules. Release `0.9.0` adds the machine key `trustedInterfaces`, an empty
machine entry in `vendomat.yaml`, machine `programs`, the `release` branch in the collection hook, and
the Basix contracts. It retires the old binary fork. Release `0.8.0` added the `vendomat.yaml` catalog.
The design is
project 21 (`.scratch/projects/21-vendomat-basix-split/`). The older V6 flow stays until the owner
accepts the new one.

## Workspaces

A workspace lists its routine settings in `vendomat.yaml`: `programs`, `env`, `languages` (Python,
JavaScript, Rust), `services` (`postgres`, `redis`), `machines`, and `settings`. A Nix function in the Vendomat
source (`devenv/parse.nix`) reads the file. The catalog module (`devenv/devenv.nix`) maps each key to
a native devenv option. No devenv fork binary and no unsafe Nix setting is involved. An edit of
`vendomat.yaml` shows in the next shell with no other step.

```sh
vendomat new my-workspace
cd my-workspace
vendomat                # enter the shell
vendomat explain        # each key, its native option, its value, and the file that set it
vendomat update         # add the lines a newer template needs, then run devenv update
```

- One error lists every bad field. Each line starts with `vendomat.yaml:LINE:COL:` and the key path.
  The launcher prints those lines first and keeps the full trace under `~/.local/state/vendomat/logs/`.
  The launcher lifts a fault line from any YAML file of the workspace in the same way: it starts with
  `FILE.yaml:LINE:COL:`.
- `machines.NAME.programs` lists nixpkgs package names for that machine only. The machine's own NixOS
  evaluation resolves them into `environment.systemPackages`. Top-level `programs` stays the shell's list.
- `settings: MODULE: FIELD: text` sets the option `vendomat.settings.MODULE.FIELD` of an authored module
  (R60, `VMT-183`). The catalog declares no such option: the authored module declares its own with
  `mkOption`. A module name and a field name each match `[A-Za-z_][A-Za-z0-9_-]*`. Every value is text.
  The catalog converts nothing, so an option of another type must accept text. Declare `types.str`, or a
  conversion such as `types.coercedTo types.str (s: s == "true") types.bool`. A plain `types.bool` gives a
  type error that names `vendomat.yaml`. A field with no declared option gives
  `vendomat.yaml:LINE:COL: settings.MODULE.FIELD: no module declares the option ...`. A plain value of
  `devenv.nix` for the same option conflicts, and the error names both files. `vendomat explain` maps each
  key to its option.
- Inside the pinned shell, `VENDOMAT_TEMPLATE` names the template of the imported Vendomat source.
  `vendomat new` and `vendomat update` use it there. Outside the shell, the bundled template applies.
- The template supplies `devenv.yaml`. The user MAY edit `devenv.nix` and `devenv.local.nix`. Shell
  entry prints one `advanced:` line when either file sets a value. `VENDOMAT_HIDE_ADVANCED=1` hides it.
- The module `devenv/sharing.nix` runs Harmonia on a machine, with a signing key that the machine makes at
  first boot. Other machines of the workspace substitute from it. `serve: false` turns it off. The
  new system configures no Attic. The module opens TCP port 5000 only on the interfaces in the NixOS
  option `vendomat.sharing.trustedInterfaces` (default: none). The machine key `trustedInterfaces`
  in `vendomat.yaml` sets it (R52, `VMT-173`): a list of interface names, for example `eth1`. A Nix file
  can add more. `serve: false` opens nothing, even with a list.
  With `networking.firewall.enable = false` the port is open on every interface, and the module warns.

## The older flow

The `vendomat.toml` flow (V6) still works until the consumers move: `vendomat sync` writes `.vendomat/`
and asks devenv to update `devenv.lock`. The flake target writes `flake.nix` for a project that
publishes its own flake outputs. Vendomat also provides `check`, `path`, `push`, `bump`, and a guarded
fresh-machine install command. NixOS and Home Manager own machine activation. The source collection
holds tagged source.

The package includes `vendomat-workspace-init`. It needs Templateer on `PATH` and a JSON model
with `forge_url`, `vendomat_tag`, and optional `devenv_tag`.

## Verify

Run `testee verify` from the repository root. Testee runs the devenv tasks of `nix/tasks.nix` on the
commit in its own workspace. Run the opt-in tasks after a change to the area they cover:
`testee verify opt:catalog-e2e`, `opt:parser-fuzz`, `opt:front-door-e2e`, `opt:sharing-vm` (three VMs),
or `opt:e2e`.

Read `.scratch/CURRENT.md` for the current authority and open gates. The evidence for the catalog
slice is `.scratch/projects/21-vendomat-basix-split/evidence/S3-CATALOG.md`.

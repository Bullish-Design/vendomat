# Vendomat

Vendomat composes one owner's development workspaces and NixOS machines from native devenv,
NixOS, and Home Manager modules. Release `0.11.1` makes `apply` commit the public cache key, so the user runs no version-control command for it (`VMT-282`). Release `0.11.0` added the list option `vendomat.watch`. `apply` and `rollback` print the first fault line of a workspace file first. Release `0.10.0` added the catalog key `settings`, whole-commit `apply` and `rollback`, and `push` without
its pre-push check. It removes the `vendomat.toml` flow: the old verbs now exit 3. Release `0.9.0` added the machine key `trustedInterfaces`, an empty
machine entry in `vendomat.yaml`, machine `programs`, the `release` branch in the collection hook, and
the Basix contracts. It retires the old binary fork. Release `0.8.0` added the `vendomat.yaml` catalog.
The design and the implementation contract is
project 21 (`.scratch/projects/21-vendomat-basix-split/`). The `vendomat.toml` flow is gone (S8).

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
- A module can add workspace files to the files that `vendomat apply` and `vendomat rollback` watch (R62,
  `VMT-280`). It sets the list option `vendomat.watch`, for example `vendomat.watch = [ "extra.yaml" ];`.
  Each path is relative to the workspace root, with no leading `/`, no `..` part, no glob character, and no
  symlink that leaves the workspace. The default is empty, so the four fixed files stay watched
  (`vendomat.yaml`, `devenv.lock`, `devenv.nix`, `devenv.local.nix`). Apply commits a watched file after the
  build. Apply and rollback refuse an uncommitted or ignored watched file by name. The commands read the
  list with `devenv eval vendomat.watch`. A failed evaluation prints the first fault line of a workspace
  file first (`VMT-281`), then the rest of the trimmed text.
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

## Removed: the `vendomat.toml` flow

S8 step 3 removed the `vendomat.toml` flow: the commands `sync`, `path`, `check`, `bump`, and
`machine`, the `.vendomat/` fragment, the V6 devenv module, and `vendomat-workspace-init`. Both
consumers use `vendomat.yaml`. `vendomat push` stays until a two-machine Harmonia check passes on real
machines (`VMT-120`, `VMT-127`). The source collection holds tagged source (`hooks/`).

## Verify

Run `testee verify` from the repository root. Testee runs the devenv tasks of `nix/tasks.nix` on the
commit in its own workspace. Run the opt-in tasks after a change to the area they cover:
`testee verify opt:catalog-e2e`, `opt:parser-fuzz`, `opt:front-door-e2e`, `opt:sharing-vm` (three VMs),
or `opt:infra-vm` (collection, cache, and build-host VMs).

Read `.scratch/CURRENT.md` for the current authority and open gates. The evidence for the catalog
slice is `.scratch/projects/21-vendomat-basix-split/evidence/S3-CATALOG.md`.

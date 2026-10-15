# W2: a real standalone Home Manager generation with the layer and the pointer step — 2026-10-15

<!-- Provenance: a subagent ran the commands on 2026-10-15. Raw logs (switch-N.log, shell-N.log,
generations.log, rollback.log, cache-rows.log), the module (devlayer.nix), and a tarball of the whole
scratch tree (w2-scratch.tar.gz): ~/.local/state/vendomat/p22/w2/. Live scratch tree:
/tmp/p22-proofs/w2/ (flake/, central/, project/, project2/, project3/, tool-*/, bin/scratch) and the
scratch home /tmp/p22-proofs/w2-home/. The orchestrator did not rerun the commands. -->

This record backs R12 and R14 on real Home Manager (`ESTATE-035`, `ESTATE-037`) and the
development route of the concept (`--override-input`).

## Question

Does a real standalone `home-manager switch` write the pointer file as the concept needs? Does a
devenv shell see each new layer with no flag? Does `home-manager switch --override-input` select a
development build, and does a plain switch restore the release?

## Isolation method

**Scratch HOME on the real machine, with no VM.** Every command ran through `bin/scratch`:

```bash
env -u DBUS_SESSION_BUS_ADDRESS -u XDG_CONFIG_HOME -u XDG_DATA_HOME -u XDG_STATE_HOME ... \
  HOME=/tmp/p22-proofs/w2-home USER=p22user LOGNAME=p22user \
  XDG_RUNTIME_DIR=/tmp/p22-proofs/w2-home/run XDG_CACHE_HOME=/home/andrew/.cache  "$@"
```

- The configuration sets `home.homeDirectory = "/tmp/p22-proofs/w2-home"`, `home.username =
  "p22user"`, and `systemd.user.startServices = false`. It defines no unit, and the scratch run
  directory holds no user manager. Activation printed `User systemd daemon not running. Skipping
  reload.`
- Nix put the user profile in the scratch home (`.nix-profile ->
  /tmp/p22-proofs/w2-home/.local/state/nix/profiles/profile`). No `/nix/var/nix/profiles/per-user`
  directory was created.
- After the run the real `~/.local/state/nix/profiles/home-manager` still pointed at generation 2
  (1 October), and the real `~/.local/state/devlayer/current.nix` still named devman-link 0.6.0.
- Reason for this method: the question needs a real `devenv` shell and the real `home-manager`
  command. A VM test cannot run devenv against the host store as cheaply. W3 uses a VM for the
  user unit, which a scratch HOME cannot start.
- The shared cache `~/.cache` stayed in use for Nix fetches. This is the one write outside the
  scratch tree.

## Inputs

- Home Manager CLI `26.11-pre`, input `git+https://github.com/nix-community/home-manager.git`
  at `5a9d300b`. nixpkgs `55bfb4d7`. Nix 2.34.7. devenv 2.4.0.
- The scratch flake has a Home Manager module `modules/devlayer.nix` with these options:
  `devlayer.enable`, `devlayer.pointerPath` (default
  `${config.home.homeDirectory}/.local/state/devlayer/current.nix`, the R14 option),
  `devlayer.package` (the layer), and `devlayer.homeFilePointer` (a negative control).
- The layer is one store directory, `runCommand "devlayer"`, with `default.nix` copied from the
  `tool` input. `tool` is a `path:` input with `flake = false`; it stands for a personal tool.
  `tool-v1`, `tool-v2`, and `tool-dev` each set `env.DEVLAYER_VERSION` to their name.
- The activation step `home.activation.devlayerPointer` (after `writeBoundary`) builds the wanted
  two-line text, refuses a symlink or a non-regular file (warning, left alone), compares with
  `$(< file)`, writes to a `mktemp` file in the same directory, and `mv -f`s it. It writes nothing
  when the content is the same. It honours `$DRY_RUN`.
- `home.sessionVariables.DEVLAYER_POINTER` carries the option's value for the doctor (OI-02). The
  devenv evaluation never reads it.
- The overlay is a scratch copy of the production layout. `project/devenv.local.nix` is a symlink
  to `central/projects/p/devenv.local.nix`. That file imports `../../common/devlayer.nix`, a regular
  file with `if builtins.pathExists pointer then [ pointer ] else [ ]`. This matches
  `~/.config/devman/common/devlayer.nix`.

## Method and results

Each row is one command and its result. A "shell" is `devenv shell -- printenv DEVLAYER_VERSION` in
the scratch project, with no flag.

| # | Action | Pointer afterwards | Shell prints | Verdict |
| --- | --- | --- | --- | --- |
| S1 | `home-manager switch --flake '.#p22user@scratch'` (tool v1) | regular file, `import /nix/store/mizgzbsp...-devlayer` | `v1` | pass |
| S2 | `nix flake update tool` after pointing the input at `tool-v2`, then `switch` | new regular file, `import /nix/store/68hrnkw3...-devlayer`, mtime moved | `v2` | pass |
| S3 | `switch --override-input tool path:/tmp/p22-proofs/w2/tool-dev` | `import /nix/store/z1kxq74c...-devlayer` | `dev` | pass |
| S3b | `sha256sum -c` of `flake.lock` taken before S3 | n/a | n/a | `flake.lock: OK`; the override changed no file |
| S4 | plain `switch` (no override) | `import /nix/store/68hrnkw3...` (the S2 layer again) | `v2` | pass |
| S5 | the same plain `switch` again | `stat` mtime and name identical; the step printed nothing | n/a | pass: no rewrite |
| R | `home-manager generations`, then run `<generation 1>/activate` | `import /nix/store/mizgzbsp...` (the S1 layer) | `v1` | pass: rollback restores the layer |

- Generation ids: 1 (v1), 2 (v2), 3 (dev), 4 (v2 again; its store path equals generation 2).
  The rollback made id 5. S5 made no new generation.
- S1 took 11.6 s with the nixpkgs build cache warm. A devenv shell took 4.1 s on the first run.
- The override flag reached `nix build` through `home-manager`: the command accepts
  `--override-input` unchanged and the generation changed. This proves the development route
  `home-manager switch --flake .#andrew@server --override-input linkman path:...` of the concept
  for an input that is not a flake. (The input here has `flake = false`; a flake input follows the
  same flag.)

### Negative controls: a pointer that is a Home Manager `home.file`

Home Manager writes a `home.file` as a symlink into the store. The pointer must not be one (R12).
W10 named this "expected untracked" and left it unproved. S6 to S8 test it with three projects:

| Project | Pointer | Shared file | After S7 (`dev`) | After S8 (back to `v2`) |
| --- | --- | --- | --- | --- |
| `project` | regular file `current.nix` | `pathExists` guard | `dev` | `v2` |
| `project2` | symlink `link.nix` (a `home.file`) | `pathExists` guard | `dev` | `v2` |
| `project3` | symlink `link.nix` | **no guard**: `imports = [ <link.nix> ]` | `dev` | **`dev` (stale)** |

`project3` printed the old value after S8, and `devenv --refresh-eval-cache shell` printed `v2`. The
cache rows (`cache-rows.log`) show why:

- `project`: a row for `current.nix` with a real modification time, and one for the shared file.
- `project2`: a row for `link.nix` with `modified_at = 1`, and one for its shared file. The row
  exists because `builtins.pathExists` reports the path as written, before any symlink is
  followed. devenv re-hashes the target of that row on every cache hit.
- `project3`: no row for `link.nix`, because Nix reports the store path for an import whose final
  component is a symlink and devenv drops store paths.

## Findings

1. **R12 holds on real Home Manager.** One activation step writes the pointer. Two switches, a
   development override, a plain switch, and a rollback each moved the pointer, and each devenv
   shell saw the right layer with no flag. An unchanged layer leaves the pointer untouched.
2. **`--override-input` works on the installed `home-manager`,** leaves `flake.lock` unchanged,
   and a plain `switch` restores the release.
3. **The `pathExists` guard of the shared file (R14) also tracks a symlinked pointer.** Both
   `project` and `project2` followed every change. For `project2` this rests on devenv's re-hash
   check (check 2), the same incidental path as W1's directory case. Issue cachix/devenv#3154
   could remove it. The regular-file pointer does not depend on it (W10 F2a). Keep the pointer a
   regular file and keep the guard.
4. **An unguarded import of a symlinked pointer is stale.** This confirms W9's rule with a real
   Home Manager `home.file`.
5. **Rollback is free.** The `activate` script of an old generation rewrites the pointer, so a
   bad tool release rolls back for devenv shells too.

## Verdict

**Holds.** R12, the option of R14, `--override-input`, and rollback all work on a real standalone
Home Manager generation with a scratch HOME. Nothing real changed.

## Unproved

- A switch of the real `andrew@server` home (this record used a scratch user).
- A systemd user unit under Home Manager (W3 runs one in a VM).
- The real production overlay layout and the 62 overlay imports. The scratch overlay has three.
- `home-manager switch` with `git://server` inputs and a tag. The `tool` input is a `path:` input.
- A future devenv with the time shortcut of #3154.
- The doctor's comparison of `DEVLAYER_POINTER` with the shared file.

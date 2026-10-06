# P-PUB-FORM spike

Date: 2026-10-06. Gate: `P-PUB-FORM` (V4-SPEC.md §12, P2 step 1). Requirement: `V4-SEL-010`.

This spike observes native behavior. It does not design an interface. No option or command name is fixed here.

## Environment

- Host system: `x86_64-linux` (`nix eval --impure --raw --expr builtins.currentSystem`).
- Nix: `nix --version` gives `nix (Nix) 2.34.7`.
- devenv: `devenv --version` gives `devenv 2.4.0+b904dcb`.
- nixpkgs pin: `151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4` (nixos-unstable, from the fixture `flake.lock`).
- Throwaway fixture (outside the repository): `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/flake-fixture/`
- Throwaway devenv project (outside the repository): `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/devenv-project/`
- Log directory: `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/`
- No file in the repository changed except this report. No fixture or code was added to the repository. No VCS action ran. P1 did not start.

The fixture exports, under `packages.x86_64-linux`:

- `plugin`: `pkgs.vimUtils.buildVimPlugin` over a local `runCommand` source tree.
- `editor`: `pkgs.wrapNeovimUnstable pkgs.neovim-unwrapped { wrapRc = true; luaRcContent; plugins = [ { plugin; optional = false; } ]; }`.
- `default`: same as `editor`.

Network use: `nix flake lock` fetched nixpkgs. Nix fetched binaries from the default substituter (`cache.nixos.org`). `devenv build` fetched its own inputs (`cachix/devenv`, nixpkgs) from GitHub. No other network use occurred.

## Q1. One flake exports a plugin and a wrapped editor that uses it

Command:

```
cd flake-fixture && nix build .#plugin --no-link --print-out-paths
cd flake-fixture && nix build .#editor --no-link --print-out-paths
```

Observed:

- `/nix/store/inzh854rjmdi60ccdcsvm1sfk0i16jgq-vimplugin-pubform-hello-0.0.1`
- `/nix/store/fr0j455g0m2pypf5z5218p7yhmig810n-neovim-0.12.5`
- The editor wrapper `bin/nvim` runs with `--cmd "set packpath^=...vim-pack-dir"`. The plugin is in that pack dir.
- Headless probe: `vim.g.pubform_marker` is `plugin-loaded`. The plugin file `plugin/hello.lua` ran.

Verdict: **CONFIRMED**.

## Q2. `nix build --json` returns drvPath and output paths

Command:

```
nix build --json --no-link .#editor
nix build --json --no-link .#plugin
```

Observed:

- editor: `[{"drvPath":"/nix/store/vafnj7zq5pzsvw7fa2ah2p10w7mym0f5-neovim-0.12.5.drv","outputs":{"out":"/nix/store/fr0j455g0m2pypf5z5218p7yhmig810n-neovim-0.12.5"}}]`
- plugin: `[{"drvPath":"/nix/store/z8qsj0gdxcpyqayf3jj9wi47n4j5gx6a-vimplugin-pubform-hello-0.0.1.drv","outputs":{"out":"/nix/store/inzh854rjmdi60ccdcsvm1sfk0i16jgq-vimplugin-pubform-hello-0.0.1"}}]`
- Both derivations have one output, `out`. A multi-output case was not tested.

Verdict: **CONFIRMED** (single-output derivations only).

## Q3. `nix flake metadata --json` returns the complete locks graph

Command:

```
nix flake metadata --json  (in flake-fixture)
```

Observed:

- Top-level keys include `locks`, `locked`, `resolved`, `path`.
- `locks.nodes` keys: `nixpkgs`, `root`.
- Keys in `flake.lock` `nodes`: `nixpkgs`, `root`. The two sets match.
- `locks.nodes.nixpkgs.locked.rev` equals the rev in `flake.lock`.

Limit: the fixture has one locked input. A graph with several inputs or `follows` was not tested.

Verdict: **CONFIRMED** for a one-input graph. Multi-input graphs: **UNCONFIRMED**.

## Q4. `nix flake archive --json` lists one store path per locked input

Command:

```
nix flake archive --json --dry-run   (in flake-fixture)
nix flake archive --json             (in flake-fixture)
```

Observed (both runs equal):

```
{"inputs":{"nixpkgs":{"inputs":{},"path":"/nix/store/0r7xswpqa49y26bl05lydybpw86sywmq-source"}},"path":"/nix/store/rggr7i7hs5sc7yhincahb6hjxgdivqx7-source"}
```

- The output lists the root flake source path, plus one entry under `inputs` for each locked input.
- Count: one locked input (`nixpkgs`) gives one input path. The root source adds one more path.
- `nix path-info` confirms both paths exist in the store.

Verdict: **CONFIRMED** for a one-input graph. The count matches the locks graph.

## Q5. `devenv build outputs.<name>` and any `nix build` route

Command:

```
cd devenv-project && devenv build outputs.pubform-hello
```

`devenv.nix` declares `outputs = { pubform-hello = pkgs.hello; };`.

Observed:

```
{
  "outputs.pubform-hello": "/nix/store/5z2yp3ysx8476c8g5w25b0smlgkjvaq3-hello-2.12.3"
}
```

- `devenv build` returns a JSON map from attribute name to store path. It returns no drvPath.
- The project has no `flake.nix`. devenv evaluates `devenv.nix` through its own bootstrap, not a flake.
- Comparison: `nix build --no-link --print-out-paths --inputs-from ../flake-fixture nixpkgs#hello` gives the same path. This shows only that the derivation is the same plain nixpkgs derivation. It does not show a `nix build` route to the devenv output attribute.
- A `nix eval --impure` import of `.devenv/bootstrap` reached the module system. It failed with a module error (`Module imports can't be nested lists`). I time-boxed this probe and did not resolve it. It is not a supported route.

Verdicts:

- `devenv build` returns a path map: **CONFIRMED**.
- A `nix build` route to the devenv output attribute: **NOT CONFIRMED**. No supported route was found.

## Q6. `wrapRc` isolation through `VIMINIT`, and PATH shadowing

The wrapper script `bin/nvim` (store path `fr0j455g0m2pypf5z5218p7yhmig810n-neovim-0.12.5`) contains:

```
export VIMINIT=${VIMINIT-'lua dofile('\''/nix/store/...-init.lua'\'')'}
```

The wrapper uses `${VIMINIT-...}`. It keeps a `VIMINIT` value that the caller sets. It does not force one.

Probes. A user config `XDG_CONFIG_HOME/nvim/init.lua` sets `vim.g.host_leak`. Headless runs write the probe values to a file.

| Case | Env | `pubform_init` | `pubform_marker` | `host_leak` |
|---|---|---|---|---|
| A | `VIMINIT` unset | `init-loaded` | `plugin-loaded` | nil (user config not loaded) |
| B | `VIMINIT` set by caller | nil (wrapper config not loaded) | `plugin-loaded` | nil |

Command for case A: `env -u VIMINIT XDG_CONFIG_HOME=... HOME=... nvim --headless -c "lua ..." -c 'qa!'`

Command for case B: same, with `VIMINIT='lua vim.g.caller_viminit=1'`.

PATH shadowing:

- A fake `nvim` script sits first on `PATH`.
- `command -v nvim` returns the fake script.
- Bare `nvim` runs the fake script. It printed `FAKE-NVIM`.
- The absolute store path `/nix/store/fr0j.../bin/nvim` runs the real wrapper. The probe shows `init-loaded` and `plugin-loaded`.

PATH suffix:

- The wrapper sets `PATH=${PATH:+':'$PATH':'}`, then appends `/nix/store/fw0x...-wl-clipboard-2.3.0/bin`. This is a suffix for the `PATH` that the wrapper hands to child processes.
- The wrapper does not change how the shell finds `nvim`. The shell lookup uses the caller's `PATH`. A prefix entry wins that lookup.
- The premise that a suffix stops the shadowing is not correct. Only an absolute path avoids shadowing.

Verdicts:

- `wrapRc` isolates the user config when the caller leaves `VIMINIT` unset: **CONFIRMED** (case A).
- `wrapRc` isolates against a caller-set `VIMINIT`: **NOT CONFIRMED**. The caller value replaces the generated config (case B).
- An absolute store path avoids `PATH` shadowing: **CONFIRMED**.

## Recommendation

The flake output attribute form can express the P1 Neovim outputs. Q1, Q2, and Q4 hold on the pin. Q3 holds for a one-input graph. Use the flake output attribute as the publication form for `V4-SEL-010`. Record `devenv build` as a different handle. It returns a path map and no drvPath. It is not an equivalent handle.

Before P3, revise these points in V4-SPEC.md. Do not change the structure:

1. State that `wrapRc` isolates only when the caller leaves `VIMINIT` unset. Also state that the wrapper keeps a caller `VIMINIT`.
2. Require the editor to run by absolute store path. Do not rely on `PATH` lookup.
3. State that `devenv build` is not a flake attribute and gives no `nix build` route. Record it as evidence only.

Still open. Test a multi-input lock graph in Q3 and Q4. Test a multi-output derivation in Q2.

## Verdict table

| Q | Question | Verdict |
|---|---|---|
| 1 | One flake exports plugin and wrapped editor | CONFIRMED |
| 2 | `nix build --json` returns drvPath and outputs | CONFIRMED (single output) |
| 3 | `flake metadata --json` returns the full locks graph | CONFIRMED (one input) |
| 4 | `flake archive --json` lists one path per locked input | CONFIRMED (one input) |
| 5 | `devenv build` handle; `nix build` route to it | `devenv` path map CONFIRMED; `nix build` route NOT CONFIRMED |
| 6 | `wrapRc` isolates via `VIMINIT`; absolute path beats PATH shadow | isolation (unset) CONFIRMED; against caller `VIMINIT` NOT CONFIRMED; absolute path CONFIRMED |

## Artifacts

- Fixture: `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/flake-fixture/`
- devenv project: `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/devenv-project/`
- Logs: `~/.local/state/vendomat/v4-proof/2026-10-06/pub-form/` (`q1-*.out`, `q2-*.json`, `q3-metadata.json`, `q4-archive*.json`, `q5-devenv-build.log`, `q6/`)

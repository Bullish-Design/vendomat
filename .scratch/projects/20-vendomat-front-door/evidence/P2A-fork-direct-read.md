# Spike A: fork direct read of vendomat.toml (project 20, 2026-10-12)

Spike dir: `~/.local/state/vendomat/p20/2026-10-12/A-fork-direct-read/`.
Nothing inside the Vendomat repository changed.

## Common inputs

| Item | Value |
| --- | --- |
| Host | `server`, x86_64-linux, Nix 2.34.7 |
| devenv | fork `devenv 2.4.0+fb5d382` (tag `v2.4.0-vendomat.3`), `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv` |
| Disk before start | unallocated 37.09 GiB, metadata 71 percent (limit: 2 GiB, 90 percent) |
| Disk after end | unallocated 34.09 GiB, metadata 74 percent |
| nixpkgs | the fork default `cachix/devenv-nixpkgs` `rolling` locked at `760b8522...`; pin `256551e4...` where named |
| Runner | `bin/dv.sh LOG DIR ARGS...`. It prints `devenv version` first, strips `DEVENV_*`, `IN_NIX_SHELL`, `VIRTUAL_ENV` from the environment, and writes the exit code. |
| Fixtures | `fx/` (path inputs) and `q5/` (loopback `git daemon`, tag-pinned `git://` source) |
| Logs | `logs/` (46 files; names are quoted per question) |

The first attempts ran without the `DEVENV_*` strip. The parent shell leaked `DEVENV_ROOT` (the
Vendomat repo). The leak showed up only in `builtins.getEnv "DEVENV_ROOT"` (probe log
`q2-probe.log` was rerun clean). All results below come from, or were re-confirmed with, the clean
runner, except the Q3 steps `q3-0` to `q3-13`, which ran with the leak. Those steps used
`config.devenv.root`, which the leak did not change (Q2). Steps `q3-14`, `q3-15`, all Q4, Q5, and
`q1-ws-v*` ran clean.

Shell aliases bit twice: `ls` is `eza` and `cat` is `bat`. Two early commands hung. All later steps
use `bash` scripts in `bin/`.

Catalog module under test (`fx/catalog/devenv/devenv.nix`, the form that works):

```nix
{ pkgs, lib, config, ... }:
let
  file = config.devenv.root + "/vendomat.toml";
  data = builtins.fromTOML (builtins.readFile file);
in
{
  env.VENDOMAT_MESSAGE = data.message;
  packages = map (n: pkgs.${n}) (data.packages or [ ]);
}
```

Workspace `devenv.yaml` (the fork resolves the module as `<input>/devenv/devenv.nix`):

```yaml
inputs:
  vendomat:
    url: path:/.../fx/catalog        # or git://...?ref=refs/tags/v1
    flake: false
imports:
  - vendomat/devenv
```

## Q1. Minimal files

- Hypotheses: H1 `devenv.nix` may be absent. H2 an empty `devenv.nix` works. H3 the workspace may omit
  `nixpkgs` and the catalog's pin applies. H4 the workspace may omit `nixpkgs` and the fork default
  applies. H5 `flake: false` is optional for a data-only catalog.
- Inputs: fixtures `fx/ws1`, `fx/ws-v1` to `ws-v4`, catalogs `fx/catalog`, `catalog-inh`, `catalog-fol`.
  The catalogs declare `nixpkgs` pinned to `256551e4...` in their own `devenv/devenv.yaml`.
- Commands: `devenv shell -- sh -c 'echo MSG=$VENDOMAT_MESSAGE'` in each workspace.
- Expected: H3 or H4 work. Others unknown.
- Actual:
  - H1 false. With no `devenv.nix`: `File devenv.nix does not exist. To get started, run: $ devenv init`
    (`logs/q1-first.log`).
  - H2 false for a 0-byte file: `error: syntax error, unexpected end of file` at `devenv.nix:1:1`
    (`logs/q1-ws-v1.log`). A file with `{ }` works (`logs/q1-second.log`, `logs/q1-ws-v1-b.log`,
    `MSG=one`, `Hello, world!`).
  - `devenv.yaml` with only the catalog input plus `imports` works. Exit 0.
  - H3 false, H4 true. The lock of `ws-v1` holds `nixpkgs` with `ref: rolling` (rev `760b8522...`).
    The catalog's pin `256551e4...` is not in the lock. The workspace with its own `nixpkgs` line
    (`ws-v2`) locks `256551e4...`. So the consumer's implicit default wins over the inherited entry.
  - Inheritance does work for other names. `ws-v1` and `ws-v2` locks hold `extra`, declared only in the
    catalog yaml (`logs/q1-ws-v1-b.log`; lock node `extra`, type `path`).
  - `follows` does not rescue H3. `ws-v4` (`nixpkgs: {follows: vendomat-nixpkgs}`, where the catalog
    declares `vendomat-nixpkgs`) fails: `input 'nixpkgs' follows a non-existent input 'vendomat-nixpkgs'`
    (`logs/q1-ws-v4-b.log`). This matches S9 c3b: a `follows` target must be a top-level input of the
    workspace yaml.
  - H5 false. `ws-v3` (no `flake: false`): `Failed to lock inputs for import inheritance: ...
    path '/nix/store/...-source/flake.nix' does not exist` (`logs/q1-ws-v3.log`).
- Files devenv creates in the workspace: `.devenv/` (directory, includes `nix-eval-cache.db`, `bootstrap/`,
  `state/`) and `devenv.lock`. It created no `.gitignore`, no `.env`, no `devenv.local.*`.
  Files it requires: `devenv.nix` (valid Nix) and `devenv.yaml`.
- Smallest working set: `devenv.yaml`, `devenv.nix` (`{ }`), `vendomat.toml`; plus the generated
  `devenv.lock` to commit; plus a `.gitignore` entry for `.devenv*`.
- Proves: the list above on this fork, for local `path:` and git sources.
- Inference: a workspace with no `nixpkgs` line gets `rolling` as of the first lock, not the Vendomat
  release pin. The native lock then fixes it per workspace. The Vendomat pin reaches the workspace
  only through a `nixpkgs.url` line in the workspace yaml.
- Unproved: whether a future fork patch could let an imported input override the implicit default.
  Flake-style catalogs (`flake: true`) were not tried.

## Q2. Direct read path

- Hypotheses: H1 `config.devenv.root` points to the workspace. H2 `inputs.self` does. H3 `builtins.getEnv
  "DEVENV_ROOT"` does. H4 the fork evaluates purely, so the read fails.
- Inputs: probe module `fx/catalog-probe/devenv/devenv.nix`, workspace `fx/ws-probe`. The probe sets one
  env var per candidate.
- Command: `bin/q2.sh` (`devenv shell -- env`), then the same with `--no-impure --no-eval-cache`.
- Actual (`logs/q2-probe.log`, clean run):
  - `P_ROOT=.../fx/ws-probe` (type string). `P_DOTFILE=.../ws-probe/.devenv`.
  - `P_SELF=.../fx/ws-probe`. `inputs` attrs: `devenv nixpkgs self vendomat`. So `inputs.self.outPath`
    is the workspace directory too.
  - `P_EXISTS=1`; `P_READ=message = "probe"`; also OK through `builtins.toPath`.
  - `P_GETENV_DEVENV_ROOT=` (empty in the clean run). In the leaked run it held the parent's root
    (`/home/andrew/Documents/Projects/vendomat`). So H3 is unsafe.
  - `P_THISFILE=.../fx/catalog-probe/devenv`: a `path:` module source is read in place, not copied.
    A git source is copied to the store (Q5).
  - `P_CURSYS=x86_64-linux`: `builtins.currentSystem` exists, so evaluation is impure.
- `--no-impure --no-eval-cache` (`logs/q2-probe-no-impure.log`, `logs/q2-no-impure-nocache.log`): same
  values, `P_CURSYS` still set, read still works. The flag does not change the evaluation. (With the
  cache on, `--no-impure` only replayed a cached result, so the first test said nothing.)
- `devenv eval devenv.root` returns `".../fx/ws1"` (`logs/q2-root-eval.log`).
- Proves: `config.devenv.root + "/vendomat.toml"` reads the workspace file on the fork, with no flag.
  Also from a subdirectory (Q5 step E: root is still the workspace).
- Inference: `inputs.self.outPath` is an equal alternative. Do not use `getEnv`.
- Unproved: behavior of a future fork that turns on real pure evaluation.

## Q3. Eval cache

- Hypotheses: H1 the cache tracks `vendomat.toml` and invalidates on edit. H2 it keys on mtime only and
  goes stale on a same-mtime edit. H3 it misses edits made by another tool.
- Inputs: `fx/ws1` and the strict catalog. Cache is on (default). `.devenv/nix-eval-cache.db` holds
  tables `file_input` (path, `content_hash`, `modified_at`), `eval_input_path`, `eval_env_input`,
  `cached_eval`.
- Evidence the cache is active: `devenv --verbose shell -- true` on unchanged files prints
  `Evaluating shell in 4.35ms (cached)` (`logs/q3-7-verbose-unchanged.log`). After an edit it prints
  `Evaluating shell in 3.66s`, no `(cached)` (`logs/q3-13-verbose-after-edit.log`).
  `.devenv/input-paths.txt` lists `.../ws1/vendomat.toml`.
- Steps and results (each is one `devenv shell`, no extra command in between):

| Step | Edit | Result | Log |
| --- | --- | --- | --- |
| 0 | none | `MSG=one` | `q3-0` |
| 1 | `message` one to two | `MSG=two` | `q3-1` |
| 2 | add `cowsay` to `packages` | `cowsay` on PATH | `q3-2` |
| 3-4 | `aaa` to `bbb`, same size (37 bytes), mtime restored with `touch -d` | `MSG=bbb` | `q3-3`, `q3-4` |
| 5-6 | two edits and runs in the same second | `MSG=ccc`, then `MSG=ddd` | `q3-5`, `q3-6` |
| 14 | `devenv test` after edit n1 to n2 | `test-out.txt` shows `TEST_MSG=n1`, then `TEST_MSG=n2` | `q3-14-test-n1`, `q3-14-test-n2` |
| 15 | `devenv tasks run vendomat:show` after the same edit | `task-out.txt` shows `TASK_MSG=n1`, then `TASK_MSG=n2` | `q3-15-task-n1`, `q3-15-task-n2` |

Steps `q3-8` to `q3-13` ran the same flow, but `devenv test` and `tasks run` print no module
output, so they proved nothing. Steps 14 and 15 write a file and read it back.

- Actual: no stale result in any step. Content hash decides, not only mtime (step 4).
- Also tested (Q4): file created and deleted between runs. The cache sees both (`pathExists` is tracked).
- Proves: on this fork, a direct read of `vendomat.toml` needs no extra step for `shell`, `test`,
  `tasks run`, for edits, same-size edits, same-mtime edits, creation, deletion.
- Inference: `git checkout` and `git pull` change content, so they invalidate too.
- Unproved: `devenv up`, direnv reload, and a long-lived shell. `input-paths.txt` lists the file, so a
  watcher can see it. No watcher ran here. Staleness condition not found. One related fact: the
  cache key does not include the `DEVENV_*` environment, but `getEnv` reads are tracked in
  `eval_env_input`, so a module that used `getEnv` would depend on the caller environment.

## Q4. Missing vendomat.toml

- Hypotheses: H1 the strict read fails with a clear error. H2 `pathExists` lets the module treat a
  missing file as an empty catalog. H3 the cache misses creation of the file.
- Inputs: `fx/ws-miss-strict` (strict catalog), `fx/ws-miss-lenient` with `fx/catalog-lenient`:
  `data = if builtins.pathExists file then builtins.fromTOML (builtins.readFile file) else { };`
  and `env.VENDOMAT_MESSAGE = data.message or "empty-catalog"`.
- Command: `bin/q4.sh`.
- Actual (`logs/q4-*.log`):
  - Strict, missing: exit 1, `error: path '.../ws-miss-strict/vendomat.toml' does not exist`, with a
    trace to `catalog/devenv/devenv.nix:4:29`.
  - Lenient, missing: exit 0, `MSG=empty-catalog`.
  - Lenient, then file created: `MSG=created`. Then deleted: `MSG=empty-catalog`. Empty file (0 bytes):
    `MSG=empty-catalog` (`fromTOML ""` is `{ }`). The cache followed all three.
- Proves: a missing file can mean an empty catalog, and the cache does not go stale on create or delete.
- Unproved: whether an empty catalog is the right product behavior; that is a design choice.

## Q5. Commit and clone

- Hypotheses: H1 a fresh clone of committed files enters the shell with no step. H2 an untracked
  `vendomat.toml` is invisible (flake-style git filtering). H3 the clone needs the network.
- Inputs: `q5/ws-src` (git repo), catalog `q5/repos/vendomat-catalog` tag `v1` served by a loopback
  `git daemon` on port 55655. The catalog pin is `ref=refs/tags/v1`, locked to rev `e0b7f0b3...` with a
  `narHash`. Workspace yaml has no `nixpkgs` line.
- Command: `bin/q5.sh` (driver log `logs/q5-driver.log`).
- Actual:
  - A. Untracked, uncommitted `vendomat.toml` in a git repo: `MSG=from-git-ws`, `hello` found, exit 0
    (`logs/q5-1-untracked.log`). H2 false. The fork reads the working directory, not a git snapshot.
  - Committed files (`git ls-files`): `.gitignore devenv.lock devenv.nix devenv.yaml vendomat.toml`.
    `.gitignore` held `.devenv*`, `devenv.local.nix`, `devenv.local.yaml`, `.env`.
    `git status` after first entry listed only `.devenv/` and `devenv.lock` as new; the ignore rule
    removes `.devenv/`.
  - B. `git clone` into `q5/ws-clone`, daemon up: `MSG=from-git-ws`, `hello` found, exit 0
    (`logs/q5-2-clone-daemon-up.log`). The lock hash stayed `2464c812...`; `git status` stayed clean.
  - C. Fresh clone `ws-clone2`, daemon stopped: same result, exit 0 (`logs/q5-3-clone-daemon-down.log`).
    The catalog source was already in the store. H3 is true only for a cold store.
  - D. Edit of `vendomat.toml` in the clone: `MSG=edited-in-clone` (`logs/q5-4-clone-edit.log`).
  - E. Run from `sub/dir` in the clone: `MSG=edited-in-clone` (`logs/q5-5-subdir.log`). Root is found.
- Proves: H1 on a warm store. The shell needs no sync, no prepare, no generated tree.
- Unproved: a cold store with an unreachable source (fork-3 patch 0008 covers the cold path with the
  network up; not rerun). GitHub sources. A direnv flow.

## Surprises

1. The catalog's `nixpkgs` pin does not reach the workspace. The fork default `rolling` wins, and
   `follows` to an inherited name fails. A workspace that wants the Vendomat pin needs a `nixpkgs`
   URL line in `devenv.yaml`.
2. `devenv.nix` is mandatory and must be valid Nix. A 0-byte file fails. `{ }` is the minimum.
3. `--no-impure` is a no-op for evaluation on this fork. The direct read works regardless.
4. The eval cache is content-hash based and tracks `pathExists`. No stale case found.
5. `builtins.getEnv "DEVENV_ROOT"` leaks the caller's value. Use `config.devenv.root`.
6. A `path:` catalog is read in place and is not hashed in the lock. Use a git source for a release.

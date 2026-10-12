# Slice 1, lanes B and C: the catalog module and the fixed workspace template

Date: 2026-10-12. Serves `DOOR-074` and `DOOR-075`. This record is fixture-level evidence. No slice
gate has run; lane F writes the gates.

## Inputs and versions

| Item | Value |
| --- | --- |
| Repository | `/home/andrew/Documents/Projects/gitman-workspaces/p20-catalog`, based on `main` after lanes A and D |
| Release fork (final evidence) | `/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin/devenv`, `devenv 2.4.0+c66ba87` |
| Prototype fork (development) | P2G binary, `devenv 2.4.0+febee12`. Logs in `logs-prototype-febee12/` |
| Stock devenv (control) | `devenv 2.4.0+b904dcb` |
| Nix | host 2.34.7. `NIX_CONFIG`, `NIX_USER_CONF_FILES`, `XDG_CONFIG_HOME` unset in every run |
| Pinned nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the `flake.lock` of this repository) |
| Disk gate | before the runs: unallocated 25 GiB, metadata 74 percent |
| Log directory | `~/.local/state/vendomat/p20/2026-10-12/slice-1/B-catalog/` (`logs/`, `logs-prototype-febee12/`, `bin/`, `cases/`, `ws/`) |

Every log in `logs/` starts with `devenv version`. Driver scripts: `bin/snap.sh` (copy the checkout to
`vsrc/`, the `path:` input), `bin/mkws.sh` (fresh workspace from `templates/workspace/`), `bin/dv.sh`
(run the fork, log with version), `bin/matrix.sh`, `bin/seq.sh`. Case files are in `cases/`.

## What changed in the repository

| Path | Change |
| --- | --- |
| `devenv/devenv.nix`, `devenv/devenv.yaml` | New. The catalog module and the inputs that a workspace inherits |
| `templates/workspace/` | Rewritten: `vendomat.yaml`, `devenv.yaml`, `devenv.nix` (`{ }`), `.gitignore` |
| `templates/workspace-v6/` | **Moved** from `templates/workspace/`: `devenv.nix`, `devenv.yaml`, `init` (the V6 files) |
| `templates/workspace-v6/init` | Two copy paths now read `$templates/workspace-v6/...` |
| `flake.nix` | `postInstall` copies `workspace-v6` too and installs `workspace-v6/init` as `vendomat-workspace-init` |
| `tests/test_workspace_user_e2e.py` | One path: `templates/workspace-v6/init` |
| `tests/test_catalog_template.py`, `tests/test_catalog_module_nix.py`, `tests/nix/catalog.nix` | New |

The old verbs (`sync`, `vendomat-workspace-init`) keep their files (`DOOR-063`). The flake keeps one input
(`nixpkgs`). `tests/test_repo_shape.py` needed no change.

## Layout check (import path and inheritance)

The workspace `devenv.yaml` imports `vendomat/devenv`. The fork resolves it to `<input>/devenv/devenv.nix`
and reads `<input>/devenv/devenv.yaml` (patch 0007). The Vendomat input has a `flake.nix`, so it is a
flake input (P2C fixture lesson 1).

- Final lock of a fresh workspace (`ws/gitd/devenv.lock`): root inputs
  `devenv, nixpkgs -> [vendomat, nixpkgs], nixpkgs-python, rust-overlay, vendomat`. `nixpkgs` locks to
  `e7439b6b` (the Vendomat pin). `nixpkgs-python` and `rust-overlay` came from `devenv/devenv.yaml`: the
  workspace declares neither. **Inheritance works.**
- Template URL form: a loopback `git daemon` served a copy of the checkout as branch `release`. The
  workspace used `git://127.0.0.1:39611/vendomat?ref=release`. The lock node holds `rev`
  (`9ba459fe...`), `ref: release`. The shell entered. A `git clone` of that workspace (lock committed)
  entered the shell with an unchanged lock (`git status` empty). Logs `gitd-shell.log`, `clone-shell.log`.
- Not tested: the real `git://server/vendomat` URL. The `release` branch does not exist yet.

## The catalog

Options (`vendomat.catalog.*`; one namespace, so it cannot clash with the V6 module's `vendomat.*` options):

| Key | Type | Mapping |
| --- | --- | --- |
| `programs` | list of text | `packages`, each name looked up as a nixpkgs attribute path (dots allowed) |
| `languages.python.{enable,version}` | `"true"`/`"false"`; `N.N` or `N.N.N` | `languages.python.enable`, `.version` (needs `nixpkgs-python`) |
| `languages.javascript.{enable,version}` | switch; major number | `languages.javascript.enable`, `.package = pkgs.nodejs_<major>` |
| `languages.rust.{enable,version}` | switch; `latest`, `N.N.N`, or a date | `languages.rust.enable`; a version sets `channel = "stable"` and `version` (needs `rust-overlay`) |
| `services.postgres.enable`, `services.redis.enable` | switch | `services.<name>.enable` |
| `env` | map of text | `env` |

A present entry is on unless it says `enable: false`. A native option gets a definition only when its item
is on (`mkIf`), so a definition in `devenv.nix` merges natively. The module sets `channel = "stable"` as a
plain definition, so a `devenv.nix` that sets another channel needs `lib.mkForce`.

Mechanism (all in `devenv/devenv.nix`):

1. `raw` = `devenvPrimops.vendomatFromYAML "vendomat.yaml" (builtins.readFile path)` if the file exists, else
   `{ }`. One parse. If `devenvPrimops ? vendomatFromYAML` is false it throws one line: `vendomat.yaml: this devenv
   has no vendomatFromYAML primop. Put the Vendomat devenv fork first on PATH.`
2. Unknown keys are found by walking `raw` against the declared option tree (`options.vendomat.catalog`), and
   `prune` drops them before the module system sees the data. So the module system never raises its separate
   "option does not exist" error: **unknown keys join the one listing.**
3. Type faults: `tryEval (deepSeq option.value)` over every option, described with the option type.
   Semantic faults (each only when the field passed its type check): an unknown program, a Node.js major
   that nixpkgs lacks, a Python version that `nixpkgs-python` lacks.
4. `guard v` throws all faults as one error, else returns `v`. Every mapped value passes through `guard` or
   `mkIf (guard ...)`, and the mapping reads values from `options.*.value`, not from raw data.
5. `_module.check = guard true`. See "Unmapped read" below.

## Observations

All runs: the release fork, fresh workspace from `templates/workspace/` with only the URL changed to `path:`.
Expected result and actual result agree unless noted. Summary file: `logs/summary.txt`.

### Good file and mapped values (logs `f-good-*`, `good-shell.log` in the prototype directory)

Case `cases/good.yaml` (programs `ripgrep`, `jq`, `python3Packages.requests`; javascript `22`; postgres on; redis
`enable: false`; env `GREETING`, `PYV: 3.10`, `NAME: no`). The shell saw `GREETING=hello PYV=3.10 NAME=no`, found
`rg`, `jq`, `node` (22.23.3), `pg_ctl` (postgres 18.6), and no `redis-server`. Proves programs, JavaScript,
a service, an off switch, and `3.10` and `no` as text.

Python and Rust versions, evaluated not built (`heavy-eval.log`): `version: 3.10` (unquoted) and `1.81.0` gave
`languages.python.package = ...python3-3.10.20-env`, `languages.rust.toolchainPackage = ...rust-stable-1.81.0`,
`channel = stable`. Proves the inherited inputs resolve. A shell build of these toolchains did not run.

The commented example in `templates/workspace/vendomat.yaml`, uncommented, evaluates (`example-eval.log`). The
template file itself, all comments, entered the shell on the prototype fork (`t0-first.log`).

### Missing file, create, edit, delete (`seq-*.log`)

| Step | Actual |
| --- | --- |
| no file | rc 0, `GREETING=unset`, no figlet |
| create (env + program) | `GREETING=one`, figlet present |
| edit | `GREETING=two`, figlet gone |
| delete | `GREETING=unset` |

No other step ran between the shells.

### Faults (`f-<case>-*.log`)

Six commands per case: `shell -- touch`, `test`, `build shell`, `build outputs.hello` (a `devenv.nix` output that
reads no catalog value), `eval devenv.root`, `tasks run`. Cases `unknown-key`, `unknown-top`, `bad-used`,
`bad-unused` (`rust.enable: false` with `version: not-a-version`), `unknown-program`, `two-faults`, `enable-no`,
`syntax`, `structure`, `bad-js`, `bad-py`. **All 66 runs: rc 1, no work marker, error names `vendomat.yaml`.**
Good file and missing file: rc 0 on all six (markers appear where the command runs user work).

Two faults and more in one run (`f-two-faults-shell.log`):

    error:
    vendomat.yaml: languages.python.enabled: unknown key (known: enable, version)
    vendomat.yaml: env must be a map of text values, found a map {"GREETING":["hello"]}
    vendomat.yaml: languages.python.enable must be "true" or "false", found "no"
    vendomat.yaml: services.postgres.enable must be "true" or "false", found "maybe"
    vendomat.yaml: programs: unknown program "nosuchpkg" (nixpkgs has no package with this name)

Syntax fault, a tab on line 4 (`f-syntax-shell.log`), from the primop:

    error: Error from custom function: vendomat.yaml:4:1: tabs are not accepted; use spaces

Structure fault (`f-structure-shell.log`):

    vendomat.yaml: languages must be a map, found "python"
    vendomat.yaml: services must be a map, found a list ["redis"]
    vendomat.yaml: programs must be a list of nixpkgs attribute names, found "ripgrep"

`enable: no` fails (`vendomat.yaml: services.redis.enable must be "true" or "false", found "no"`).

Stock devenv control (`stock-control.log`, `devenv 2.4.0+b904dcb`): `error: vendomat.yaml: this devenv has no
vendomatFromYAML primop. Put the Vendomat devenv fork first on PATH.`

### Unmapped read (the P2B open question)

The `_module.check = guard true` line makes every read of the final config run the checks: the module system
forces `config._module.check` in `checkUnmatched` on each read of the evaluated config, and a module sees an
unchecked `config`, so the hook creates no cycle. Prototype-fork runs, `bad-unused` case, six commands each:

| Variant | Result |
| --- | --- |
| no guard at all | rc 0 on all six (the bad unused value passes; the harness can see a miss) |
| guards on mapped values, no `_module.check` | rc 1 on all six |
| `_module.check` only, mapped values unguarded | rc 1 on all six |
| both (final module) | rc 1 on all six |

Logs: `logs-prototype-febee12/m-noguard-bad-unused-*`, `m-nocheck-bad-unused-*`, `m-checkonly-bad-unused-*`,
`m-bad-unused-*`. Observation: devenv reads at least one mapped value (`packages` or `env`) for every command
that I tried, so the guards alone already stopped `build outputs.hello` and `eval devenv.root`. Inference: the
`_module.check` hook is the universal part, because it needs no mapped read. The Nix test below tests it
without devenv.

### Repository checks

`tests/test_catalog_template.py` reads files (no Nix, no fork). `tests/test_catalog_module_nix.py` and
`tests/nix/catalog.nix` evaluate the module on pinned nixpkgs with stub options and a stub primop that reads
JSON. They run under `testee verify e2e` only. They cover the mapping, the missing file, the one listing of
eight faults, a bad unused value and an unknown key on a read of `devenv.root`, and the not-a-map case.
Testee verdicts: see the end of this file.

## What this proves

- The module, the template, and the inheritance of `nixpkgs-python` and `rust-overlay` work on the release
  fork `c66ba87` and the prototype `febee12`, at fixture level, with a `path:` input and a `git://` input.
- `DOOR-075` mechanism: one parse, one error with every bad field, unknown keys in the same listing, a syntax
  fault with `vendomat.yaml:LINE:COL`, text-typed `3.10` and `no`, a failing `enable: no`, and a stop on all
  six commands, including two that read no mapped value.
- `DOOR-074` mechanism: four fixed files, direct read, missing file is an empty catalog, an edit, a create, and
  a delete show in the next shell, a fresh clone enters, and no unsafe Nix setting is set.

## What stays inference or open

- No slice gate has run. Direnv, Testee with the fork first on `PATH`, and `vendomat new` are lane E and F work.
- The real `git://server/vendomat?ref=release` URL has not been tried. A force-pushed branch and a cold store are
  untested (P2C).
- A full shell build of Python 3.12 or Rust from the inherited inputs was not run; only evaluation was.
- Rust and Python version validity is checked by `nixpkgs-python` (Python) and by `rust-overlay` natively (Rust).
  A Rust version that does not exist fails natively, not in the one listing.
- The Python reader in `src/vendomat/yamlsubset.py` is the V6 reader and accepts flow style that the primop
  rejects. The repository tests use it only on files that the primop also accepts.
- Not tested: integer-like fields, very large files, a symlinked `vendomat.yaml`, `devenv up` with the services.
- `AGENTS.md` "Repository layout" does not list `devenv/` or `templates/`. It was already out of date; not edited.

## Testee verdicts

Run on commit `2f93706237` (tree `e124dfc768`), `testee 0.6.1`, after the rebase onto `main` (lanes A and D):

- `testee verify`: GREEN, 4/4 checks (pytest, ruff, ruff-format, ty). `testee verify --profile full`: GREEN (cached on
  the same tree).
- `testee verify e2e`: PASS (run `20261012T200520Z-0323bc84cfe6`). It includes `tests/test_catalog_module_nix.py`.

This record was added after those runs, and it changes no code. The final tree has a fresh `testee verify` verdict;
the e2e verdict belongs to the tree above.

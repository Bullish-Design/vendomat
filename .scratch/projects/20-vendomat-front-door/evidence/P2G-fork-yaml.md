# P2G (spike G): can the devenv fork read `vendomat.yaml` itself?

Date: 2026-10-12. Nothing inside the Vendomat repository changed. No fork repository changed.
All files are under `~/.local/state/vendomat/p20/2026-10-12/G-fork-yaml/` (`$D` below).

## Question

Can our devenv fork parse a strict-subset YAML user file, so that every entry point sees current data,
with no stored copy and no unsafe Nix setting?

## Verdict

Viable. A Rust primop `vendomatFromYAML name text` in the fork gives the correct result on every entry point
tested. It needs no wrapper, no generated file, and no `allow-unsafe-native-code-during-evaluation`.
Condition: the process that evaluates (a direct call, direnv, or Testee) must run the fork, not stock devenv.

## Inputs and versions

| Item | Value |
| --- | --- |
| Base fork | `v2.4.0-vendomat.3`, commit `fb5d382b822f6ecf58365a77f2f872ba6f7ce79d` (upstream `cachix/devenv` `v2.4.0` `b904dcb5` plus patches 0001 to 0008) |
| Source copy | `$D/src` (copy of `~/.local/state/vendomat/v7/2026-10-11/devenv-v2.4.0-vendomat.3`); two spike commits `2efaeb12`, `febee126` on top |
| Patched CLI | `devenv 2.4.0+febee12`, `/nix/store/406jjk64bw8mxk849fcydckrvdy64x72-devenv-wrapped-2.4.0` (`$D/result-devenv`) |
| First (broken) build | `devenv 2.4.0+2efaeb1`: `error: Implementation error in custom function: return value must not be a thunk` (seen in the terminal; the log was overwritten by the fixed run). Fixed by forcing the value (see Patch). |
| Stock CLI (control) | `devenv 2.4.0+b904dcb`, first on the default PATH |
| Nix | host 2.34.7; the fork links Nix 2.35.2 (C API) |
| Testee | 0.6.1, `~/.nix-profile/bin/testee` |
| direnv | 2.37.1 |
| Disk gate | before: unallocated 31 GiB, metadata 75 %. After the builds: unallocated 21 GiB, metadata 77.7 %. Gate passed. |
| Raw logs | `$D/logs/` |

## Designs considered

- D1, primop. The fork evaluates Nix in process through the Nix C API (`nix-bindings-expr`, git dependency
  `cachix/nix-bindings-rust` branch 2.35). It already has a primop registry: `devenv-nix-backend/src/primops.rs`
  registers `loadDotenv` and `allocatePort`. The bootstrap passes the set to modules as the module argument
  `devenvPrimops` (`devenv-nix-backend/bootstrap/bootstrapLib.nix`, line 173) and as a special argument `primops`.
  So a new primop needs no change to Nix code in the fork. CHOSEN.
- D2, injection into the bootstrap. Not built. It needs the Rust side to find the file, parse it, and register a cache
  input by hand (`EvalInputTracker`, as `load_dotenv_tracked` does). This is more code than D1, and D1 gets the
  tracking free from `builtins.readFile`.
- D3, anything simpler. `serde_yaml 0.9` is in the dependency tree (`devenv-core`). Rejected as the parser: it
  resolves scalars by YAML rules, so `3.10` would become a float and `no` a boolean. The subset must keep text.
  A hand parser is about 240 lines of code, and the same rules as the P2F Python parser.

## Chosen design

1. `vendomatFromYAML name text` is a pure function of two strings. It returns Nix maps, lists, and strings.
2. The catalog module reads the file with `builtins.readFile` and passes the text in:
   `devenvPrimops.vendomatFromYAML "vendomat.yaml" (builtins.readFile p)`, guarded by `builtins.pathExists p`.
   The eval cache already tracks `readFile` (content hash) and `pathExists` (P2A, and Q1 below). The primop does no
   I/O, so it adds no hidden input.
3. The primop name and a parser version number (`VENDOMAT_YAML_VERSION = 1`) go into the primop cache-key fragment.
   A change of the parser makes old cache entries invalid.
4. The parser rules mirror P2F: maps, lists, string scalars; it rejects tabs, anchors, aliases, tags, flow style, block
   scalars, document markers, duplicate keys, unknown escapes, and lists of maps. Errors read `NAME:LINE:COL: reason`.

Catalog fixture: `$D/tmpl/catalog.nix`. It is the P2F catalog with the `@@DATA@@` line replaced and `devenvPrimops`
added to the argument list:

    config.vendomat = let p = config.devenv.root + "/vendomat.yaml"; in
      if builtins.pathExists p
      then devenvPrimops.vendomatFromYAML "vendomat.yaml" (builtins.readFile p)
      else {};

## Patch

File: `$D/0009-vendomat-add-the-vendomatFromYAML-primop.patch`, 403 lines (`git diff fb5d382b..HEAD`).
Repository copy: `fixtures/p2g/0009-vendomat-add-the-vendomatFromYAML-primop.patch` (this directory).
It applies on top of patch 0008.

| File | Change |
| --- | --- |
| `devenv-nix-backend/src/yaml_subset.rs` | new, 299 lines (about 235 code, 64 test lines) |
| `devenv-nix-backend/src/primops.rs` | +58 lines: `VendomatYamlPlugin`, `VendomatYamlPrimop` |
| `devenv-nix-backend/src/lib.rs` | +3 lines: `pub mod yaml_subset;` and exports |
| `devenv/src/devenv/mod.rs` | +1 line: `.install(devenv_nix_backend::VendomatYamlPlugin)` |

The primop turns the parsed tree into a JSON string, evaluates `builtins.fromJSON` with `eval_from_string`, applies
it with `new_value_apply`, and calls `force` before it returns. The first build did not force and failed with
"return value must not be a thunk". The Rust Nix bindings have no safe call to build a list, so the JSON round trip
avoids a change to `nix-bindings-rust`.

## Build recipe

    cd $D/src                     # a git copy of the materialized tree; new files must be committed or `git add -N`
    nix build .#devenv -o ../result-devenv --print-build-logs

Same recipe as fork-3 (`nix build .#devenv` in the materialized tree). Logs: `logs/build.log` (first build, with
crate downloads from `devenv.cachix.org`; exit 0) and `logs/build2.log` (fixed build, exit 0). The incremental
build rebuilds only `devenv-nix-backend`, `devenv`, `devenv-run-tests`, `xtask`, and the wrapper. The
`devenv-core` unit tests were not re-run (see Unproved).

To make a release: add the patch to `devenv-dist/SERIES`, rerun `materialize`, retag (`v2.4.0-vendomat.4`). Not done.

## Tests

Fixtures: `$D/ws` (workspace), `$D/repo` and `$D/clone*` (git), `$D/testee-fx/t-g` (Testee), `$D/diff-ws`
(parser comparison). Data: `$D/cases/base.yaml` (`version: 3.10`, `name: no`, `postgres enable: "false"`,
`python enable: true`). Probe: `bin/probe.sh` runs `ENTRY -v --no-tui shell -- sh -c 'echo SEEN ...'`.
Every run used `$FORK`, the patched binary by absolute path, except where noted. `NIX_CONFIG`,
`NIX_USER_CONF_FILES`, and `XDG_CONFIG_HOME` were unset (Q8).

### T1. Edit detection

Command: `cd ws; sh bin/q1.sh $FORK`. Log: `logs/q1.log` (first line `devenv 2.4.0+febee12`).
Expected: every edit seen; an unchanged rerun cached.

| Step | Actual |
| --- | --- |
| baseline, then unchanged rerun | `✓ Evaluating shell in 38.1ms (cached)`, `PYV=3.10` |
| value 3.10 to 3.11 | re-eval 3.97 s, `PYV=3.11` |
| same size, mtime restored (size 159, mtime identical before and after) | re-eval 3.98 s, `PYV=3.12` |
| add key `env.EXTRA: yes` | re-eval, `EXTRA=yes` |
| delete the file | re-eval, `PYV=unset EN=false NAME=unset PROG=` |
| restore the file | re-eval, `PYV=3.10` |

Proves: the eval cache sees the file through `readFile` and `pathExists`, including a same-size edit with a restored
mtime, delete, and restore. The primop result never goes stale in this sequence.
Inference: other commands that read `config` behave the same (only `shell` and `test` ran).
Unproved: very large files, a concurrent edit during a run, a symlinked `vendomat.yaml`.

### T2. Direct `devenv shell` and `devenv test`

Command: `devenv -v --no-tui test`, with `enterTest = echo "TESTSAW PYV=$VM_PY_VERSION"`. Log: `logs/q2-test.log`.
Actual: baseline `TESTSAW PYV=3.10` (`Evaluating devenv.config.test ... (cached)`); after the edit to 3.14,
`TESTSAW PYV=3.14` with a re-evaluation (34.9 ms); after the restore, `TESTSAW PYV=3.10`; "Tests passed" each time.
`devenv shell` is covered by T1. Proves: `test` sees the current data. (Note: without `-v` the test output is hidden.)

### T3. Fresh git clone

Command: `git clone repo clone; cd clone; env -u NIX_CONFIG probe.sh $FORK`, then `devenv -v --no-tui test`.
Log: `logs/q3-clone.log`. The clone holds the committed `vendomat.yaml`, `catalog.nix`, `devenv.*`, no `.devenv`.
Actual: cold shell 8.39 s, `PYV=3.10 EN=true NAME=no PROG=ripgrep,jq`; `test` printed `TESTSAW PYV=3.10`.
Proves: a fresh checkout works with a direct call, no wrapper, no generated file.

### T4. direnv `use devenv`

Command: `bin/q-direnv.sh $D/clone-dr` with `$D/forkbin` first on PATH and isolated `XDG_DATA_HOME`
(`.envrc`: `eval "$(devenv direnvrc)"`, `use devenv`). Log: `logs/q4-direnv.log`.
Actual: initial `SEEN PYV=3.10 NAME=no`; after the edit, `SEEN PYV=3.11 NAME=no`.
Proves: direnv is non-interactive here and sees an edit. Unproved: a real interactive shell hook with `cd`.

### T5. Testee 0.6.1

Fixture `testee-fx/t-g`: git repo; `devenv.yaml` with `nixpkgs`, `nixpkgs-python`, `testee` v0.6.1, imports
`testee/nix/testee.nix` and `./catalog.nix`; one check `seen` passes only if `$VM_PY_VERSION` is `3.10`.
PATH: `$D/forkbin` first. Logs: `logs/q5-testee.log`, `q5-testee-edit.log`, `q5-testee-stock.log`.

| Step | Actual |
| --- | --- |
| commit with 3.10 | `PASS seen`, `GREEN tree def793eda3` |
| commit with 3.11 | `FAIL seen`, `RED ... failed: seen`; `seen.txt`: `SEEN PYV=3.11 NAME=no` |
| commit with 3.10 again | `GREEN tree def793eda3` |
| control: stock devenv first on PATH | `testee: eval_failed: devenv eval failed: attribute 'vendomatFromYAML' missing` |

Proves: Testee sees the committed data and gives no false green. P2F's plain-`exec` failure mode does not occur.
The control proves the fork binary did the evaluation. Important: the default PATH puts stock devenv first.
The Vendomat host must put the fork first on the PATH that Testee inherits (testee-path-shadowing memory).
Unproved: `testee verify` with the real Vendomat catalog.

### T6. Errors

Commands: `CASES="..." bin/q4.sh $FORK` (log `logs/q6-errors.log`), full output `logs/q6-tab-full.log`,
Testee `logs/q6-testee-errors.log`.

Subset faults, direct call (`devenv shell`): the message is the LAST line of 238 lines of trace, and it names
file, line, and column:

    error: Error from custom function: vendomat.yaml:4:1: tabs are not accepted; use spaces
    error: Error from custom function: vendomat.yaml:3:6: anchors (&) are not accepted
    error: Error from custom function: vendomat.yaml:4:1: duplicate key 'name'; first on line 3
    error: Error from custom function: vendomat.yaml:1:11: flow style is not accepted
    error: Error from custom function: vendomat.yaml:3:1: document markers are not accepted; one document per file

The P2F exec route put the parser line first and a generic "program failed" line last. Here the real message is last
(the line a terminal shows).

Under Testee, the line survives:

    testee: eval_failed: devenv eval failed: Error from custom function: vendomat.yaml:4:1: tabs are not accepted; use spaces

Type error ("maybe" in a bool field), direct and under Testee:

    vendomat.yaml: `services.postgres.enable' must be boolean or (one of "true", "false") convertible to it, found string "maybe"
    testee: eval_failed: devenv eval failed: vendomat.yaml: `services.postgres.enable' must be boolean or (one of "true", "false") convertible to it, found string "maybe"

Unknown key (`enabled`): `error: The option `vendomat.languages.python.enabled' does not exist. Definition values:`
(the file name is on the lines after it; same as P2F).
Remaining noise: 237 lines of Nix trace before the message on a direct call (no flag cuts it). The type error has no
line number; only the parser knows it. The prefix "Error from custom function:" is added by Nix.

### T7. Traps

Input `err-traps.yaml` (`name: no`, `version: 3.10`, `enable: "true"`): shell saw `PYV=3.10 EN=true NAME=no`
(`logs/q6-errors.log`, last case). `enable: no` and `enable: yes` in a bool field are rejected with the type error
above (`err-no`, `err-yes`). `name: no` stays text. Proves: all-string input plus the `coercedTo` bool type
prevents these traps on this catalog. Unproved: integer fields (no `int` type coercion tried).

### T8. No unsafe Nix setting

Command: `nix config show | grep ...`. Log: `logs/q8-nix-config.log`. Actual: `NIX_CONFIG`, `NIX_USER_CONF_FILES`,
and `XDG_CONFIG_HOME` unset; `allow-unsafe-native-code-during-evaluation = false`; `pure-eval = true`;
`/etc/nix/nix.conf` has no match; `~/.config/nix/nix.conf` does not exist; `nix eval --impure 'builtins ? exec'`
gave `false`. Every test above ran under this configuration. The fixture `devenv.yaml` has no Nix option keys.
Proves: no unsafe setting was in effect. Unproved: nothing found; the fork's in-process Nix reads the same
`nix.conf` files (inference).

### T9. Parser equivalence

Command: `sh bin/difftest.sh`, log `logs/q9-difftest.log`. It runs the Rust primop and the P2F `vyaml.py` on each of
the 27 files in `cases/` and compares the JSON tree or the `file:line:col: reason` text.
Actual: 27 of 27 identical (13 trees, 14 errors, including tab, anchor, alias, tag, flow, duplicate key,
document marker, bad indent, empty value, unterminated quote).
Proves: the Rust parser matches the Python reference on these 27 inputs. Unproved: fuzz or an independent oracle.
The Rust unit tests in `yaml_subset.rs` did not run: a bare `rustc` could not load the store `serde_json` rlib
(`can't find crate`), so I used T9 instead. `cargo test` for the crate (a Nix build with `runTests`) is the fix.

## Maintenance note

- Size: 4 files, 1 changed upstream line plus 3 export lines; the rest is new code in a new file and one new block
  in `primops.rs`. 361 insertions, 1 deletion.
- Conflict risk: low to medium. The new file cannot conflict. The `primops.rs` block sits before `LoadDotenvPrimop`
  and copies the existing registration pattern; a rewrite of that pattern upstream would need a rebase. The
  `mod.rs` line sits in the plugin chain `NixEvalSetup::install(...)`; a new upstream plugin on the next line gives a
  textual conflict that takes one minute to fix. The primop API (`PrimOp::new`, `eval_from_string`,
  `new_value_apply`, `force`) belongs to `nix-bindings-rust` branch 2.35, which moves with each Nix bump; a Nix
  upgrade could need a small change.
- The catalog module depends on `devenvPrimops`, a module argument that upstream also uses (`dotenv.nix`,
  `processes.nix`). A rename upstream would break the catalog and the fork build together.
- Optional hardening (not built): in the catalog, check `devenvPrimops ? vendomatFromYAML` and throw
  "run with the Vendomat devenv fork". Stock devenv now says `attribute 'vendomatFromYAML' missing`.
- Upstreaming: a generic `fromYAML` primop is a plausible PR; the strict subset is Vendomat-specific.

## Unproved

- A release build with `devenv-core` and `devenv-nix-backend` unit tests (`runTests`).
- Real Vendomat catalog, `vendomat sync` interplay, and a machine-level (NixOS) entry point.
- Very large files, non-UTF-8 files, a symlinked file, a concurrent edit.
- A real interactive direnv session.
- A GitHub or `git://` collection delivery of the new tag.

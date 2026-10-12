# S3: option schema export, storage, refresh, offline use, and invalidation

**Date:** 2026-10-11. **Status:** observation record. Nothing here is a passed project 20 gate.
The fixtures are spike code, not production code.

## 1. Questions and hypotheses

| Q | Question | Hypothesis before the run |
| --- | --- | --- |
| Q1 | Can Vendomat export the full option schema with neutral data, before validated user values exist? | H1: yes. A module can expose `options` as a config value, as `devenv-py` does. |
| Q2 | Can imports or declarations depend on config values, so the schema needs user data? | H2: yes, in some authoring forms. A rule can make the export data-independent. |
| Q3 | When a tag changes and a new option is set in one edit, does the sequence work? | H3: devenv does not lock a changed input by itself, so Vendomat must run `devenv update <input>`. |
| Q4 | Where does the schema live, and what key is enough? | H4: a cache outside the workspace, keyed by the lock and the module sources, beats a store derivation. |
| Q5 | Does export work offline from a warm store? What does `--offline` do? | H5: yes with a warm store. `--offline` stops fetches. |
| Q6 | Size and time? Can a subtree export cut the time? | H6: a subtree export is much faster than the full tree. |
| Q7 | Does devenv emit options itself? | H7: `devenv search` or an `optionsJSON` output gives a usable list. |

H3 and H5 were wrong in part. See sections 4 and 6.

## 2. Exact inputs

| Item | Value |
| --- | --- |
| devenv CLI (all real runs) | `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`, `devenv 2.4.0+fb5d382 (x86_64-linux)`. Every row in `timings.tsv` prints the version. One run (`q2-inherit-v3`) lost its version column; the rerun `q2-inherit-v3-rerun` has it. The host PATH devenv is stock and was not used. |
| Nix | 2.34.7 |
| nixpkgs input | `github:cachix/devenv-nixpkgs/256551e45f6303e142ab4a98be1bf243feb77dc0` (the rev in the Vendomat `devenv.lock`). The lock also holds `nixpkgs-src` `c8f90650`. |
| devenv module input | Not declared. The fork added it and locked `cachix/devenv` `a73c5b84c9527760f009232988466763068f9f61` (`src/modules`). The Vendomat repository lock holds `fe20b5cb`. See finding F9. |
| Library input | Loopback `git daemon`, repository `lib`, tags `v1` (`c35eb3e5`), `v2` (`7eda676a`, adds `demo.newOption`), `v3` (adds `devenv/devenv.yaml` that declares input `extra`), `v4`, `v5` (empty commits). Input name `demolib`, `flake: false`, URL `git://127.0.0.1:38989/lib?ref=refs/tags/<tag>`. |
| Workspace shape | `devenv.yaml` holds `imports: [./.vendomat]`. `.vendomat/devenv.yaml` holds the generated inputs and `imports: [demolib/devenv]`. `.vendomat/devenv.nix` is the generated data module. `.vendomat/config.json` is the data. This mirrors the current `devenvgen.py` shape. |
| Export method | Reused from `devenv-py` (project 17): a module reads `options` and writes a read-only config value. `nix/options.nix` of `devenv-py` is copied unchanged into `fixtures/s3-schema/options-tree.nix`. `fixtures/s3-schema/schema.nix` exposes `vendomat.schema.json`. A new option `vendomat.schema.keys` (JSON list of top-level keys) filters the tree. Stock `devenv eval` reads the value. No fork patch is needed. |
| Host | 8 CPUs. Load average was 13 to 15 in the first half of the session (other agents) and 5.8 later. This affects the timings (section 5). Btrfs: metadata 85 to 86 percent, unallocated 6.1 down to 4.1 GiB. No heavy build ran. |
| Fixtures | `evidence/fixtures/s3-schema/` (see section 9) |
| Raw logs and workspaces | `~/.local/state/vendomat/p20/2026-10-11/S3/` (`logs/`, `ws-a` to `ws-j`, `cache/`, `cache-offline/`, `repos/`). `logs/timings.tsv` has 63 timed commands. |

The data module in the fixture:

```nix
{ lib, config, ... }: {
  imports = [ ./schema.nix ];
  options.vendomat.neutral = lib.mkOption { type = lib.types.bool; default = false; ... };
  config = lib.mkIf (!config.vendomat.neutral) (builtins.fromJSON (builtins.readFile ./config.json));
}
```

## 3. Q1: neutral export

**Command** (workspace `ws-a`, tag `v1`, `.vendomat/config.json` is `{}`):
`devenv eval vendomat.schema.json`. Later runs add `-O _module.check:bool false -O vendomat.neutral:bool true`.

**Expected:** the export holds every devenv option and every `demo.*` option of the library.

**Actual:**

- Exit 0. The output is a JSON object with one key; its value is the schema as a JSON string. A caller decodes twice.
- 853 records, 76 top-level keys (`services` 327, `languages` 306, `process` 55, `demo` 8). Zero `depthCut` nodes.
- The 8 `demo` records show: `str` with default `"hello"`; `enum` with `payload.values = ["fast","slow"]`; `nullOr` with `elemType int`; `bool`; `listOf str`; `attrsOf` with a `submodule` element type whose children `demo.users.<name>.uid` and `.shell` sit under `nested.elemType.options`; a `submodule` with `freeformType` (`nested.freeformType`) and child `demo.settings.level`; a `package`.
- Default presence (`hasDefault`), nullable (`nullOr` node), enum values, submodule children, and freeform type are all in the structure. The `package` default is `null` because the option has `defaultText`; the exporter skips such defaults (a `devenv-py` rule).
- With the lock at `v2` the export holds 854 records (`demo.newOption`). With `v3` it holds 855 (`demo.fromExtra` from the inherited input).
- Output is byte-identical across 10 runs (cached, uncached, no lock, lock kept): SHA-256 prefix `42676fa6503d`.
- A minimal validator (`validate.py`, about 80 lines) used this schema. A good data file passes. A bad file gives 7 faults with the right paths: bad enum value, wrong scalar types, an unknown child of an `attrsOf` submodule, an undeclared option, a wrong freeform value type, an unknown top-level key.

**Proves:** a full structured schema exports at the pins with neutral data, and a validator can use it.

**Stale or bad data does not matter when the export uses the two switches** (`-O _module.check:bool false`, `-O vendomat.neutral:bool true`):

| Run | Data in `config.json` | Result |
| --- | --- | --- |
| `q3-e5` | unknown option `demo.newOption`, bad types, `nonexistent` key; no switch | exit 1: ``The option `demo.newOption' does not exist`` |
| `q3-e1` | unknown option; only `vendomat.neutral` | exit 1, same error. The module system reports an unmatched definition even for `mkIf false` (`condition = false` in the message). |
| `q3-e3`, `q3-e4` | unknown option, bad types; only `_module.check=false` | exit 0, same bytes as the neutral export |
| `q3-e6` | bad data, both switches | exit 0, byte-identical to the empty-data export `q1-first` at `v1` |

So `_module.check=false` is the switch that removes the data dependency. `vendomat.neutral` adds a second guard: no stale value reaches a default. A case with `default = "${config.demo.greeting}!"` and `greeting = 5` exported with exit 0 either way (the exporter catches a failed default with `tryEval`, `defaultError`).

## 4. Q2: evaluation cycles

**Method.** `cycles/run.sh` copies each case module into `devenv.nix` and runs the export with neutral data and with user data
(`demo.enable=true, mode=slow, greeting=hi, users.bob`), with `--no-eval-cache`. Log: `logs/q2-run.log`.

| Case | Module form | Neutral | With user data | Result |
| --- | --- | --- | --- | --- |
| C1 | `imports = optional config.demo.enable ...` | exit 1 | exit 1 | `error: infinite recursion encountered`; Nix hint: "you probably reference `config` in `imports`" |
| C4 | `imports = optional (pkgs ? hello) ...` (module argument `pkgs`) | exit 1 | exit 1 | infinite recursion. `pkgs` depends on config in devenv. |
| C5 | `imports = optional (inputs ? demolib) ...` (module argument `inputs`) | exit 0 | exit 0 | Works. Identical bytes in both runs. |
| C3 | `imports` read `.vendomat/config.json` with `fromJSON`, not `config` | exit 0, no `demo.gated` | exit 0, `demo.gated` present | **Schema differs with data.** No cycle. |
| C2 | option `type` chosen by `config.demo.mode` | `str`, default `"x"` | `int`, default `0` | **Schema differs with data.** No cycle. |
| C9 | `enum (attrNames config.demo.users)` | `values: []` | `values: ["bob"]` | **Schema differs with data.** |
| C11 | `default` reads `config.demo.greeting` | default `"hello!"` | default `"hi!"` | Only the default differs. Structure is equal. |
| C10 | `options = mkIf config.demo.enable {...}` | exit 1 | exit 1 | Not a valid module form (`An option declaration for _type`). It is my test error, not a finding about cycles. |

**devenv's own modules.** A full export with heavy user data (python, rust, javascript, postgres, redis, nginx, a
container, `process.manager`, `packages`, `env`, `git-hooks`) and no switch gave 854 records. A full neutral export of the same
workspace gave 854 records. The key sets are equal. Zero records differ outside the default fields. One default differs
(`task.package`). So the pinned devenv modules do not make the structure depend on data (`q2-userdata-full-nocheckflag`,
`q2-neutral-full-same-ws`).

**Fork import inheritance (patch 0007).** Tag `v3` of the library has `devenv/devenv.yaml` with input `extra`, and its
module imports `${inputs.extra}/mod.nix`. The neutral export (`q2-inherit-v3-rerun`, 3.65 s) holds `demo.fromExtra`. The lock holds
`demolib`, `extra`, `devenv`, `nixpkgs`, `nixpkgs-src`. Inheritance reads `devenv.yaml` files before Nix evaluates any module. A
YAML file cannot name a config value. So inheritance cannot create a data cycle. (Inference from the mechanism plus this one fixture.)

**Observation outside the question.** An input named `lib` breaks the project: `attribute 'mkRenamedOptionModule' missing` in
devenv's own `processes.nix`. The same input named `demolib` works. The generator should reject input names that equal a module
argument (`lib` observed; `pkgs`, `config`, `options` not tested).

**Authoring rule that makes the export data-independent** (proposed):

1. `imports` of every module that Vendomat loads MUST NOT read `config`, `pkgs`, or `.vendomat/config.json`. They MAY read `inputs`, `lib`, and constants.
2. An option's declaration (name, `type`, enum values, submodule options, `freeformType`, `visible`, `internal`, `readOnly`) MUST NOT read `config`.
3. A condition on a value goes in `config = mkIf ...`, never in `imports` or in a declaration.
4. A `default` MAY read `config`. Vendomat MUST NOT validate against a default, and MUST treat a default in the schema as the value under neutral data.

Rule 1 is enforced by Nix (infinite recursion, C1 and C4) for `config` and `pkgs`. Nix does not enforce the file read of C3, and does
not enforce rule 2 (C2, C9). A module author needs a test: export with neutral data and with sample data, compare the records
without the default fields. The full-tree run above did this for devenv itself (0 differences).

## 5. Timings and sizes (Q1, Q6)

Load matters. Rows marked L ran at load average 13 to 15; rows marked I ran at load 5.8.

| Case | Time | Log label |
| --- | --- | --- |
| First export: no lock, no `.devenv`, tag fetch, lock written | 13.4 s (L) | `q1-first` |
| No lock, `.devenv` removed, store and git cache warm | 8.2 s (L) | `q6-nolock-warmstore` |
| Lock kept, `.devenv` removed (cold eval cache) | 13.5 s, 9.2 s (L) | `q6-nocache-lockkept-*` |
| `--no-eval-cache`, full tree, warm store | 9.4, 12.5, 9.9 s (L); 3.9, 3.9, 3.9, 3.8, 4.3 s (I) | `q6-noevalcache-*`, `q6b-full-noevalcache-*` |
| devenv eval-cache hit, full tree | 0.21, 0.19, 0.18 s | `q6-cached-*` |
| Trivial `devenv eval env.DEVENV_ROOT` (base cost of one devenv start) | 0.18 to 0.39 s | `q6-trivial-*`, `q6b-trivial-noevalcache` |
| Subtree `["demo"]`, `--no-eval-cache` | 0.16 to 0.19 s (I) | `q6b-demo-noevalcache-*` |
| Subtree `["demo","scripts","packages","tasks"]` | 0.16 s (I) | `q6b-fresh-keys-1` |
| Subtree `["languages"]` / `["services"]` | 1.03 s / 1.37 s (I) | `q6b-fresh-keys-lang`, `-svc` |
| Vendomat cache hit (Python start, read and hash the workspace Nix, YAML, and lock files) | 0.09 to 0.11 s, no devenv call | `schema_cache.py` runs 2, 3, 4, 6, 8, 10 |
| `devenv update demolib` | 1.49 s | `q3-f1-update-demolib` |
| Export after a lock change (eval cache miss), full tree | 4.24 s | `q3-f2-export-v2` |

| Size | Bytes |
| --- | --- |
| `devenv eval` output, full tree (JSON object, schema as a string) | 935,099 |
| Schema JSON, full tree | 839,680 (canonical 839,760) |
| Same, without `description`, `declarations`, `defaultText` | 456,046 |
| Same, gzip | 66,571 |
| `demo` only | 6,099 (output), 5.9 KB (cache file) |
| `packages` only | 652 |
| `languages` only / `services` only | 188,129 / 283,446 (output) |

**Subtree export (Q6).** `vendomat.schema.keys` filters the tree before the walk. A slice of a full export equals a subtree export
(`demo`: 9 of 9 records equal; `packages`: 1 of 1). The cost is in the walk of each option's type tree, not in module loading: the base
`devenv eval` start is 0.16 to 0.4 s and the full walk adds about 3.7 s. So the keys named in `vendomat.yaml` cut the cost from about
4 s to 0.2 to 1.4 s on an idle host. A top-level key that the tree does not hold gives an empty list, which the validator reports as `no such option`.

## 6. Q3: changed tag and a new option in one edit

State before: `ws-f`, fragment tag `v1`, lock `demolib` at `c35eb3e5`, schema cached at `v1`. The user edit sets tag `v2` and
`demo.newOption`. Candidate data: `{"demo":{"enable":true,"newOption":"from-v2"}}`. Log labels `q3-f*`.

| Step | Command | Result |
| --- | --- | --- |
| 1. Lint | (Python, no Nix) | not run in this spike |
| 2. Generate fragment | `ws-gen.sh ... v2 '{}'`; candidate data kept aside; `config.json` stays `{}` | `.vendomat/devenv.yaml` names `refs/tags/v2` |
| 2b. Validate against the old schema | `validate.py` | `FAULT demo.newOption: no such option`, exit 1. This is the expected stale-schema result; do not report it as the user's fault. |
| 3. Resolve the lock | `devenv update demolib` | 1.49 s, exit 0. Only node `demolib` changed (`7eda676a`); `devenv`, `nixpkgs`, `nixpkgs-src`, `root` equal. |
| 4. Export, neutral data | `devenv eval -O _module.check:bool false -O vendomat.neutral:bool true vendomat.schema.json` | 4.24 s, 854 records, `demo.newOption` present |
| 5. Validate | `validate.py` with the new schema | exit 0 |
| 6. Write data | copy candidate to `.vendomat/config.json` | |
| 7. Run | `devenv shell -- sh -c 'echo DEMO_NEW=$DEMO_NEW'` | `DEMO_NEW=from-v2`, exit 0 |

The sequence works. Other observations:

- **devenv locks a changed or new input by itself.** With the fragment at `v2` and the lock at `v1`, `devenv eval` rewrote only the `demolib` node (`q3-a`, 18 s under load). `devenv shell` did the same (`q3-g1`). A new input added to the fragment was locked on the next `devenv eval` (`q3-g2`). H3 was wrong: the explicit `devenv update` is not required for correctness. It is still useful, for three reasons. It gives a clear error. It finishes the lock before the cache key is computed. It keeps the export from relocking as a hidden side effect.
- **Data written before the schema fails, and so does the export.** With the lock at `v1`, fragment at `v1`, and `newOption` in `config.json`: the export, `devenv eval env.DEMO_GREETING`, and `devenv shell` all exit 1 with ``The option `demo.newOption' does not exist`` in 0.14 to 0.17 s (`q3-c1`, `q3-c2`, `q3-c3`). A workspace in this state cannot refresh its own schema unless the export uses `_module.check=false`. With that switch the export succeeds (`q3-e3`).
- **The same data works once the pin is right.** Fragment `v2`, same data: export 4.41 s, `devenv eval env.DEMO_NEW` gives `"hello-new"` (`q3-d1`, `q3-d2`).
- **Key before lock is wrong.** `schema_cache.py` computes the key before it calls the export. If devenv relocks inside the export, the schema is stored under the key of the old lock. Vendomat must finish the lock first (the existing `lock_problems` check in `nixio.py` compares lock nodes with the fragment in Python and makes no Nix call), then compute the key, then export.

## 7. Q4: storage and key

**Options measured:**

| Option | Result |
| --- | --- |
| A. `.vendomat/schema.json` in the workspace | Not measured as a file. It needs a key sidecar. If committed, it adds 0.8 MB (or 6 to 200 KB with subtrees) of churn per pin change. If ignored, a fresh clone has none. An offline fresh clone still needs the sources in the store, so a committed schema does not make the build offline. |
| B. Cache under `$XDG_CACHE_HOME/vendomat/schema/<key>/<top-key>.json` | Implemented in `schema_cache.py`. Hit: 0.09 to 0.11 s, no devenv call (shim log shows none). Shared by workspaces with equal pins. |
| C. Store derivation (`pkgs.writeText` of the JSON) | `devenv build vendomat.schema.drv` printed `/nix/store/8yvh1giq...-vendomat-schema.json` in 4.84 s, then 0.93 s on the second run. `devenv build` did not add a GC root for it (`.devenv/gc/` holds `shell`, task config, changelog only). To find the path, Nix must evaluate the module first, so the derivation does not remove the evaluation. It adds a GC root problem and no cache hit without Nix. Rejected. |
| D. `nixosOptionsDoc` JSON (`devenv`'s own `optionsJSON`) | See Q7. Types are English strings. Not used. |

**Key** (`compute_key`, SHA-256, first 32 hex characters), over:

1. the real path of the devenv CLI (the store path names its content, so no process starts),
2. the system,
3. the export flags and depth,
4. the SHA-256 of every `.nix`, `.yaml`, `.yml` file, and `devenv.lock`, under the workspace root, except `.devenv`, `.git`, `.jj`, `.direnv`, `node_modules`, and `.vendomat/config.json`.

The data file is outside the key. File 4 covers the lock, the generated fragment, the data module, the Vendomat module copy, and the
user's `devenv.nix` with any local import. In production the Vendomat module arrives through an input, so the lock covers its version.
Every file under a key directory is one top-level option key (`demo.json`, `packages.json`, `ALL.json`).

**Invalidation run** (`logs/shim-q4.log` counts devenv calls; `$S3/cache/`):

| Step | Action | Result | devenv calls |
| --- | --- | --- | --- |
| 1 | miss, full tree | exported, 9.3 s (L) | 1 |
| 2, 3 | same input | HIT, 0.09 and 0.11 s | 1 |
| 4 | change `config.json` | HIT, 0.10 s | 1 |
| 5 | `--keys demo` (file missing) | MISS, 0.39 s | 2 |
| 6 | `--keys demo` | HIT | 2 |
| 7 | `--keys demo,packages` | exports only `packages`, 0.39 s | 3 |
| 8 | same | HIT | 3 |
| 9 | fragment and lock back to `v1` | new key `2317...`, MISS, 0.37 s | 5 (one `update`, one `eval`) |
| 10 | fragment and lock back to `v2` | original key `99f0...`, HIT | 5 |
| 11 | append a comment to `devenv.nix` | new key `206d...`, MISS | 6 |
| CLI | key with the stock CLI path versus the fork path | `c8c520d1...` versus `5bc172e8...` (`q4-cli-key.log`) | |

The slice check: `demo.json` and `packages.json` equal the same records in `ALL.json` (`True`, `True`).

## 8. Q5: offline

Tools: `unshare -rn` works unprivileged on this host. Inside it, only `lo` exists and it is down; `git ls-remote` of the daemon
fails with `Network is unreachable`. The Nix daemon socket still works.

| Run | Setup | Result |
| --- | --- | --- |
| `q5-a` | `ws-f` (`v2`, locked), `--no-eval-cache`, `["demo"]` | exit 0, 0.24 s |
| `q5-b` | same, full tree | exit 0, 5.76 s, byte-identical to the online export `q3-f2` |
| `q5-c` | `devenv shell -- echo OK` | exit 0, 4.95 s, prints `OK` |
| `q5-f` | `schema_cache.py`, empty cache, offline, `["demo","packages"]` | MISS, regenerated, exit 0, 0.37 s |
| `q5-g` | same cache again, offline | HIT, 0.11 s |
| `q5-g` (D) | HIT with an unusable devenv path (`REAL_DEVENV` names the identity) | HIT, 0.10 s, no process started |
| `q5-d` | new tag `v4` never locked, offline, fragment changed | exit 1: `Failed to lock inputs for import inheritance ... Failed to fetch git repository 'git://127.0.0.1:38989/lib'`. The lock kept `refs/tags/v2`. |
| `q5-h` | new tag `v5`, never fetched, empty cache, offline, through `schema_cache.py` | exit 2 with the Vendomat message below. Lock kept `v2`. |

The missing-schema message the fixture prints (the Nix tail comes from devenv):

```text
vendomat: no option schema for pin 392b96b23a988794379bf4ab75b8a60a and the export failed (exit 1).
  The schema cache has no entry, and Nix could not read the locked sources.
  Connect to the network, or restore the sources, then run the command again.
  Nix said:
  ... while fetching the input 'git://127.0.0.1:38989/lib?ref=refs/tags/v5'
  error: Failed to fetch git repository 'git://127.0.0.1:38989/lib'
```

A production message should name the input and the tag, not the key. (Proposed text; the fixture message is a draft.)

**A first v4 test was invalid.** In the first attempt (`ws-h3`) the tag `v4` had already been fetched by an online `--offline` run, so Nix's git cache served it and the offline relock succeeded. That shows a new tag works offline when Nix fetched it before. The v5 run is the valid missing case.

**`devenv --offline` on 2.4.0.** The flag exists. Its help text: "Disable substituters and consider all previously downloaded files up-to-date." With the daemon reachable, `devenv --offline eval ...` on a never-fetched tag still fetched the tag and rewrote the lock (`q5-e`, 0.5 s, "From git://... * [new tag] v4"). So `--offline` does not stop git input fetches. H5 was wrong on this point. It is not a gate for offline entry; a network namespace or an unreachable source is.

## 9. Q7: can devenv emit options?

| Route | Result |
| --- | --- |
| `devenv eval options.demo.greeting.type.name` | exit 1: ``attribute `devenv.config.options.demo.greeting.type.name` not found``. The `eval` command reaches `devenv.config.*` only (same as probe O2 of project 17). |
| `devenv info` | prints inputs, env, packages, tasks. No options. |
| `devenv search <name>` | Builds `optionsJSON` and prints a text table for packages and options. It found the library option `demo.greeting` (type `string`, default `"hello"`) and `demo.mode` (type `one of "fast", "slow"`). Output is a text table only; no JSON flag. 47 to 49 s per call. Not usable as an export. |
| `devenv build optionsJSON` | exit 1: ``attribute `devenv.config.optionsJSON` not found``. `optionsJSON` is a project attribute, not a config attribute; only `devenv search` and `devenv mcp` reach it (`search.rs`, `mcp.rs` call `build_devenv(["optionsJSON"])`). |
| Module-exposed `nixosOptionsDoc` (`vendomat.schema.doc`, then `devenv build vendomat.schema.doc`) | 2.45 s. `/nix/store/gb0laraay7nhbbidkn5imibyy3vy771y-options.json`: 504 KB, 1156 entries, children flattened (`demo.users.<name>.uid`). Types are English strings: `null or signed integer`, `one of "fast", "slow"`, `attribute set of (submodule)`, `open submodule of attribute set of string`. Defaults are `literalExpression` text. |

**Comparison.** `nixosOptionsDoc` gives a smaller file in a store path and a Nix build output. The direct export gives a structure:
enum values as a list, `nullOr` and `listOf` nesting as typed nodes, submodule children inside the type, `freeformType`, `hasDefault`,
default as JSON. A reader of the doc must parse 104 or more English type strings (project 17 probe O5). The direct export needs no new
derivation. Both need a Nix evaluation of the whole module set. The direct export is the better source for a validator.

## 10. Proves, inference, unproved

**Proves** (on the pinned fork CLI, Nix 2.34.7, the nixpkgs rev above, devenv modules at `a73c5b84`):

- P1. A full structured option schema exports with neutral data, through stock `devenv eval` and a module that reads `options`. 853 records, byte-stable.
- P2. `-O _module.check:bool false` removes the data dependency, including stale, unknown, and wrongly typed data. The module system reports unmatched options even under `mkIf false`.
- P3. The pinned devenv modules do not make the option structure depend on data (854 against 854 records, 0 structural differences, with a heavy data file).
- P4. `imports` that read `config` or `pkgs` fail with infinite recursion. A declaration that reads `config`, or an `imports` that reads the data file, does not fail; it makes the schema differ.
- P5. A changed tag plus a new option works: update, export, validate, write, run. `devenv` also relocks a changed or new input in `eval` and `shell` without `update`.
- P6. Data written before the schema fails every `devenv` command, including the export, unless the export uses `_module.check=false`.
- P7. A cache outside the workspace gives a hit with no devenv call, a new key on a lock change, a new key on a `devenv.nix` change, the old key after a revert, and no change on a data edit.
- P8. Export and shell run offline in a network namespace from a warm store. A miss with a warm store regenerates offline. A miss with a missing source fails with a Nix fetch error and leaves the lock as it was.
- P9. A subtree export cuts the walk from about 4 s to 0.16 to 1.4 s on an idle host and equals a slice of the full export.
- P10. `devenv --offline` does not stop git input fetches on 2.4.0.

**Inference:**

- I1. Import inheritance (patch 0007) cannot create a data cycle, because it reads YAML before evaluation. One fixture (`v3`) shows it works with neutral data.
- I2. A cache key of the file hashes is sufficient for modules under the workspace root. A local import that points outside the root is not covered. The Vendomat module in production arrives through an input, so the lock covers it.
- I3. A committed schema file would not make an offline fresh clone work, because the build needs the sources in the store anyway.
- I4. The schema validates in advance only. Nix remains the authority on the final merge and types. A module that breaks rule 2 can make the schema wrong for that module; Nix still rejects a wrong value in the real run.

**Unproved:**

- U1. Lint (step 1) and a production Python implementation. The validator covers `str`, `int`, `bool`, `enum`, `nullOr`, `listOf`, `attrsOf`, `submodule`, freeform. Other type names (`package`, `path`, `either`, JSON value types) were not checked.
- U2. The effect of `--profile` or other `-O` flags on the structure. The key does not include extra CLI flags.
- U3. A local nix file imported from outside the workspace root, or an environment variable that changes the evaluation.
- U4. A GC root or any retention for the cache. The cache is a derived file; a loss costs one export.
- U5. Cross-machine reuse of the cache (copying `$XDG_CACHE_HOME/vendomat/schema`).
- U6. A hosted flake input (`github:`) with `flake: true` as the library source. Only `flake: false` git tags were tested.
- U7. Behavior with a non-loopback network that is slow or half available.
- U8. Whether the first lock of the auto-added `devenv` input should be pinned in the generated fragment (finding F9).

## 11. Findings that change the plan

- F1. The reliable neutral switch is `-O _module.check:bool false`. Keep `vendomat.neutral` as a second guard.
- F2. Step 2 of section 4 needs an exact order: generate, finish the lock, compute the key, load or export, validate, write data, run.
- F3. Exports the whole tree cost about 4 s idle; the subtree export costs 0.2 to 1.4 s. Export per top-level key and cache per key.
- F4. The data file must stay outside the key and outside the stale-schema path.
- F5. `devenv --offline` is not an offline guard. The offline proof is a network namespace.
- F6. The module author rule (section 4) must reach the author docs. Nix enforces only the `config` and `pkgs` part.
- F7. The generator must reject input names that shadow module arguments (`lib` breaks devenv).
- F8. `devenv build` leaves no GC root for an arbitrary attribute. A store-derivation schema would need an explicit root.
- F9. The fork does not pin its own module input. A fresh lock took `a73c5b84`; the Vendomat repository lock holds `fe20b5cb`. The generated fragment should name the `devenv` input and its revision or tag, so the schema key and the shell use the same devenv modules on every machine.

## 12. Recommended command sequence (replaces section 4, steps 1 to 4 of CONCEPT.md if the owner accepts)

1. **Parse and lint** `vendomat.yaml`. No Nix. Stop on an invalid YAML form or input shape. Reject input names that equal a module argument.
2. **Generate** the fragment (`.vendomat/devenv.yaml`, the data module) in memory. Write a file only when its content changes.
3. **Finish the lock.** Compare `devenv.lock` nodes with the fragment inputs in Python. When a node is missing or its `original` differs, run `devenv update <input>` (or `devenv update` for a new lock). Compare again. On failure, keep the old lock and the old fragment, and stop. When the lock is complete, no Nix call runs.
4. **Compute the schema key** from the finished lock, the fragment, the Vendomat module, the user's workspace Nix files, the devenv CLI path, and the system. The data file is not in the key.
5. **Load the schema** for the top-level keys that `vendomat.yaml` names (plus `inputs`/`imports` handled separately). For a key with no cache file, run one `devenv eval -O _module.check:bool false -O vendomat.neutral:bool true -O vendomat.schema.keys:string '[...]' vendomat.schema.json`. Split the result by top-level key and write each file atomically.
6. **Validate** the data against the schema. Name the file, line, key, and reason. A fault stops the command here.
7. **Write** `.vendomat/config.json` and the content hashes only when content changes. Then run the requested devenv command.

Offline: step 3 makes no Nix call on a complete lock. Step 5 hits the cache or regenerates from the local store. Without the cache and
without the locked source in the store, the command stops at step 5 with the missing-schema error. A new tag that Nix never fetched
fails at step 3; the old lock and fragment stay.

**Storage.** `${XDG_CACHE_HOME:-~/.cache}/vendomat/schema/<key>/<top-key>.json`. Not committed, not in the workspace, not a store
derivation. No GC root; a deleted entry costs one export.

**Command exit codes proposed:** 1 for a lint or validation fault; 2 for a missing schema or a failed lock.

## 13. `NEW:` claim text (no ID allocation)

- NEW: Vendomat MUST export the option schema for a workspace's locked inputs with neutral data. It MUST run the export with `_module.check` false and its data switch on, so a stale, unknown, or wrongly typed value in `.vendomat/config.json` cannot stop the export.
- NEW: A module that Vendomat loads MUST NOT read `config`, `pkgs`, or the data file in `imports`, and MUST NOT read `config` in an option's type, enum values, submodule options, `freeformType`, `visible`, `internal`, or `readOnly`. A condition on a value MUST sit in `config` under `mkIf`.
- NEW: Vendomat MUST finish the lock for the generated inputs before it computes the schema key. It MUST compare the lock with the fragment without a Nix call, and MUST run `devenv update <input>` only on a mismatch. A failed update MUST leave the previous lock and fragment in place.
- NEW: Vendomat MUST store each exported schema outside the workspace, under a key over the finished lock, the generated fragment, the Vendomat module, the workspace Nix and YAML files, the devenv CLI identity, and the system. The key MUST NOT include `.vendomat/config.json`. A cache hit MUST start no Nix or devenv process.
- NEW: Vendomat MUST export and cache the schema per top-level option key, and MUST export only the keys that `vendomat.yaml` names when a cache file is missing.
- NEW: When the schema cache has no entry and Nix cannot read a locked source, Vendomat MUST stop before the requested operation. The message MUST name the input and its tag, say that no schema is available, and leave the lock and the generated files unchanged.
- NEW: Vendomat MUST NOT rely on `devenv --offline` to prevent a fetch. The offline proof MUST use a network namespace or an unreachable source.
- NEW: The generated fragment MUST pin the `devenv` module input, so the schema and the shell use the same devenv modules on every machine.
- NEW: The generator MUST reject an input name that equals a module argument name (`lib` is known to break devenv).

## 14. Fixture files

All under `.scratch/projects/20-vendomat-front-door/evidence/fixtures/s3-schema/`. Each file has a non-production header.

| File | Purpose |
| --- | --- |
| `lib-setup.sh` | Builds the `lib` repository with tags `v1` and `v2` |
| `ws-gen.sh` | Writes a workspace and its `.vendomat/` fragment for a tag and a data file |
| `schema.nix` | Exposes `vendomat.schema.json` (and `drv`, `doc` for comparison) |
| `options-tree.nix` | Copy of `devenv-py` `nix/options.nix` |
| `validate.py` | Minimal data validator over the exported schema |
| `schema_cache.py` | Key, lookup, export, and store |
| `devenv-shim.sh` | Counts devenv calls |
| `timeit.sh` | Times one command |
| `cycles/` | Cases C1 to C11 and `run.sh` |

The tags `v3`, `v4`, `v5` and the `extra` repository were made by commands in this record, not by `lib-setup.sh` (it makes `v1` and `v2`).

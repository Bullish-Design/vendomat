# Phase A record: five prototype experiments

**Date:** 2026-10-11. **Status:** Observed in prototypes outside the repository. Steps 2 to 6, 8, and
11 are "prototype proved, in-repo port in progress". No step gate passes until the code lives in
`devenv-py` with its tests. Step 7 has a static survey only.

Raw work directories and reports are under `~/.local/state/devenv-py/phase-a/` (outside the
repository, MDL-012). Each section links its report.

## Pin used by all experiments

| Item | Value |
| --- | --- |
| Pin identifier | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| devenv CLI | `devenv 2.4.0+b904dcb (x86_64-linux)` |
| Nix | `nix (Nix) 2.34.7` |
| `devenv` input | `cachix/devenv` `b904dcb51fe48c30db250038241507f60752f222` (lock node `devenv`) |
| `nixpkgs` input | `cachix/devenv-nixpkgs` `c2f38fe7f9e04d9aadd354d380f2bd40531d9737` (lock node `nixpkgs_2`) |
| `nixpkgs-python` | `cachix/nixpkgs-python` `5821ac5267b0dc89e48705407206e3c88ee3e0ad` |
| `nixpkgs-src_2` (supplies `lib`) | `NixOS/nixpkgs` `c7def046b9a883d46974757852106483d741586f` |
| devenv module source | `/nix/store/n1zz8rrfw0sx39dizqj4a6468lxga71q-source` |

The root of `devenv.lock` maps `nixpkgs` to the node `nixpkgs_2`. The node named `nixpkgs` holds
`256551e45f6303e142ab4a98be1bf243feb77dc0`, which is a different revision. A pin reader must follow
`nodes.root.inputs`.

## Status by guide step

| Guide step | Phase A result | State |
| --- | --- | --- |
| 1 | not part of phase A | done ([step-1.md](./step-1.md)) |
| 2 driver | echo, unknown kind, cache, dotted-key failure | prototype proved, in-repo port in progress |
| 3 batch | TODO: no driver report yet (section 3) | prototype proved for the oracle batch only; port in progress |
| 4 options export | exporter, completeness, census, hash | prototype proved, in-repo port in progress |
| 5 oracle | touched scope, five golden fixtures | prototype proved, in-repo port in progress |
| 6 normalizer | rules, tests, two-directory test | prototype proved, in-repo port in progress |
| 7 corpus | static survey only; nothing evaluated | not started (survey done) |
| 8 generator | facts from the export census | prototype proved for inputs only, port in progress |
| 9 `nix` language | done on `templateer_v2` `main` | done ([step-9.md](./step-9.md)) |
| 11 syntax reader | prototype and fleet run | prototype proved, in-repo port in progress |

"Prototype proved" means a script outside the repository met the expected result on the pin. It is
not a passed harness gate.

---

## 1. Options export (Steps 2, 4)

**Raw report:** `~/.local/state/devenv-py/phase-a/options/REPORT.md`. Files in that directory:
`options.nix`, `introspect.nix`, `export.json`, `export.sha256`, `scripts/`, `logs/`.
The orchestrator saved the report from the subagent's returned text.

**Inputs.** The pin above. Request `{"kind":"options","maxDepth":8}`. Command:
`devenv eval -O introspect.request:path <file> introspect.result`.

**Expected.** The Step 4 draft exports every option with a structured type tree.

**Actual.** The draft failed. Eleven changes made it work (table). The final version exits 0 with
1330 option records and 833,807 canonical bytes.

| # | Failure or change | Cause (observed) | Fix |
| --- | --- | --- | --- |
| F1 | `cannot convert the built-in function 'isString' to JSON` | `functor.payload` holds types; `toJSON` fails and `tryEval` does not catch it | A hand-written walk `ser`: type to `{"$type":name}`, function to `{"$fn":true}`, derivation to `{"$pkg":name}`, path to `{"$path":..}`. Drop the payload keys `modules`, `staticModules`, `specialArgs`. `tryEval (deepSeq ..)` guards `throw`. |
| F2 | `Failed to get attribute 'mcp.devenv.sh'`; the echo key `d.e` fails too | `devenv eval` fails when the result holds an attribute name with a dot | `introspect.result` is a JSON string for every kind. The driver decodes twice. |
| F3 | stack overflow | recursive types (JSON, YAML, TOML values) expand without end | Cut a node whose `description` repeats an ancestor's: `{name, description, recursive:true}`. Depth limit 12 as a safety net (`truncated:true`); it never fired. |
| F4 | wrong sub-option `loc` | a `listOf` submodule needs `*`; an `attrsOf` submodule needs its placeholder | Carry `loc`. `elemLoc` reads `functor.payload.placeholder`. Use `*` for `listOf` and `<function body>` for `functionTo`. |
| F5 | 10 duplicate `loc` | `getSubOptions` adds `_freeformOptions` | `removeAttrs [ "_freeformOptions" ]`. Freeform options stay under `nested.freeformType`. |
| F6 | 9 options missing at `maxDepth` 3 | the deepest chain has 5 submodule levels | Default `maxDepth = 8`. Each cut marks `depthCut:true`. 0 cuts at 8. |
| F7 | defaults can be functions, derivations, or `throw` (`containers.<name>.derivation`) | `toJSON` fails or forces packages | A `safe` walk in `tryEval`. A failure gives `default:null, defaultError:true` (1 option). |
| F8 | the eval cache never hit for `maxDepth` of 1 or more | the default of `containers.<name>.copyToRoot` is `self`, which copies the changing project directory | Skip `default` when the option has `defaultText` (226 options): `defaultSkipped:true`. |
| F9 | the export held store hashes, the project path, and `/tmp/devenv-<hash>` | config-dependent defaults | `norm` rewrites `/nix/store/<32>-` to `<store>/`. `introspect.nix` passes `config.devenv.root` (`<root>`) and `config.devenv.runtime` (`<runtime>`). |
| F10 | `devenv build introspect.optionsDoc` failed on a synthetic option with no description | `nixosOptionsDoc` defaults to `warningsAreErrors = true` | Set `warningsAreErrors = false`. |
| F11 | not a failure: `lib.mdDoc` is gone | none | `text` handles string, `literalExpression`, `literalMD`, and null, then applies `norm`. |

`visible` is exported raw. No option at the pin uses `shallow` or `transparent`. The `attrTag`
branch is untested.

### Completeness (Step 4 action 3)

`optionsDoc` lists 1144 keys under 45 top-level names. The export holds 1330 records, 845 of them
outside any submodule.

| Rule | Listed | Difference | Result |
| --- | --- | --- | --- |
| Naive: `visible` and not `internal` | 1199 | 55 extra | FAIL |
| Doc rule (from `optionAttrSetToDocList'`) | 1144 | 0 | PASS |

The doc rule: list an option when `visible` is `true` or `"shallow"` and it is not `internal`. Walk
sub-options only when `visible` is `true` or `"transparent"`. `internal` does not stop the walk. A
synthetic module with all `visible` forms also matched (1152 keys, 0 differences).

The 55 extra keys: `configurations.<name>.*` 31, `machinesMeta.<name>.*` 17,
`languages.rust.packages.*` 5, `machines.<name>.installCheck.hasRootAuth` 1, one under
`pre-commit`. Each has a hidden ancestor.

### Type census (26 distinct names)

| `type.name` | at root | anywhere | nodes |
| --- | --- | --- | --- |
| bool | 357 | 391 | 394 |
| str | 152 | 380 | 386 |
| package | 178 | 220 | 220 |
| nullOr | 183 | 191 | 239 |
| listOf | 129 | 163 | 164 |
| submodule | 68 | 108 | 111 |
| attrsOf | 55 | 91 | 97 |
| path | 14 | 67 | 73 |
| int | 18 | 61 | 64 |
| enum | 42 | 48 | 48 |
| separatedString | 33 | 48 | 48 |
| either | 10 | 47 | 191 |
| unsignedInt16 | 36 | 40 | 40 |
| float | 0 | 26 | 26 |
| attrs | 11 | 19 | 19 |
| anything | 6 | 17 | 17 |
| unspecified | 6 | 15 | 15 |
| output | 14 | 14 | 14 |
| lazyAttrsOf | 3 | 8 | 9 |
| functionTo | 4 | 6 | 9 |
| unsignedInt | 2 | 6 | 6 |
| intBetween | 4 | 4 | 4 |
| deferredModule | 3 | 3 | 3 |
| strMatching "<pattern>" | 1 | 1 | 1 |
| coercedTo | 0 | 1 | 1 |
| outputOf | 1 | 1 | 1 |

- Only `strMatching "<pattern>"` carries a payload in its name (`changelogs.*.date`). The raw
  pattern is in `payload.pattern`.
- Payload shapes: `attrsOf` and `lazyAttrsOf` `{elemType, lazy, placeholder}`; `listOf`, `nullOr`,
  and `functionTo` `{elemType}`; `either` `{elemType=[l,r]}`; `enum` `{values}`; `path`
  `{absolute, inStore}`; `separatedString` `{sep}`; `strMatching` `{pattern}`; `submodule`
  `{class, description, shorthandOnlyDefinesConfig}`; `deferredModule` `{}`; others null.
- `nested` keys: `elemType`, `freeformType`, `left` and `right`, `coercedType` and `finalType`.
- `output` and `outputOf` are devenv types (`src/modules/outputs.nix`). The concept table lacked them.
- Rows of the concept table with no name at this pin: `number` is `either int float`. Format types
  appear as `nullOr` or `either` with a JSON, YAML, or TOML description and a `recursive` marker
  (28 options). `oneOf` folds into `either`. `pathInStore` and `externalPath` appear as `path`
  with a payload.
- Not observed: `nonEmptyStr`, `singleLineStr`, `signedInt*`, `positiveInt`, `raw`, `module`.
- Enum payload is `{ values = [...]; }` (48 nodes, 165 string values). `unsignedInt` and
  `unsignedInt16` carry their bounds in the name. `intBetween` carries them only in the description
  ("integer between 30 and 600", "1 and 31"). A bound added with `addCheck` on `int` is invisible.

### Spot checks (all pass)

`services.postgres.port` is `unsignedInt16`, default 5432. `packages` is `listOf package`, default
`[]`. `env` is a `submodule` ("open submodule of lazy attribute set of anything") with
`nested.freeformType = lazyAttrsOf anything`, empty own options, default `{}`.
`languages.python.version` is `nullOr str`, default null. `scripts` is `attrsOf submodule` (binary,
description, exec, package, packages, scriptPackage). `tasks` is `attrsOf submodule` with many
sub-options and no default.

### Hash and timing

Canonical form: `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)`. Four
calls (two with `--no-eval-cache`, one with `--refresh-eval-cache`, one cache hit) and a run from
another directory give SHA-256 `a1126c7deb218be41121dc672fdb7b4b0ca58fafc482c787c9fd7ad66a07fc4e`
(833,807 bytes). Echo with no cache 0.32 s; echo cache hit 0.06 s; unknown kind 0.33 s (exit 1);
`options` uncached 4.0 to 4.2 s; `options` cache hit 0.11 s; `devenv build introspect.optionsDoc`
1.7 to 2.7 s.

### Inferences (not proved)

- I1. Cheap repeat exports depend on F8.
- I2. F2 likely comes from devenv splitting result names on dots. Nobody read the Rust source.
- I3. F8 was found by bisection over top-level names. A clean checkout may behave differently.
- I4. The counts 1144 and 45 equal the Step 0 probe counts at `a73c5b84`. Nobody diffed the sets.
- I5. A future default with `abort` or a type error would break the whole export. Bisection cannot
  help.
- I6. The `recursive` rule keys on descriptions. Two different types with one description would be
  cut wrongly.
- I7. The `attrTag` branch is untested.

---

## 2. Oracle, golden fixtures, normalizer (Steps 2, 5, 6)

**Raw report:** `~/.local/state/devenv-py/phase-a/oracle/REPORT.md`. Files: `base/` (pinned base
project with `nix/introspect.nix`, `serialize.nix`, `oracle.nix`, `touched.nix`), `driver.py`,
`compare_golden.py`, `normalize.py`, `test_normalize.py`, `twin_test.py`, `stability.py`,
`fixtures/`, `logs/`.

**Request route.** From `base/`:
`devenv eval [--no-eval-cache] -O introspect.request:path <request.json> introspect.result`.
Request: `{"kind":"truth","candidates":{"<label>":{"modules":["/abs/devenv.nix"],"roots":["/abs/source/"]}}}`.
Optional keys per candidate: `scope` (`touched` default, or `all`) and `deny` (option paths, for
`all`). Expected: an echo request returns its payload. Actual: yes, exit 0, 0.30 s. Candidate modules
read by absolute path from outside the base project work under pure evaluation. No copy is needed.

### The unmodified Step 5 draft failed

| Observation | Detail |
| --- | --- |
| O1 | Probe fixture: exit 0 in 11.1 s (cold). Four options returned `error: true`: `languages.purescript.package`, `.lsp.package`, `.spago.package`, `languages.solidity.foundry.package`. |
| O2 | Fixtures b, c, e (no processes): exit 1 after 4 to 5 s. Error `cannot coerce null to a string: null` at `src/modules/process-managers/native.nix:77`. Fixtures a and d enable postgres, so `processes != {}`, and did not fail. |
| O3 | A fixture with `env.GATED = mkIf false` is invalid in devenv. Reading `config.env` throws `The option env.GATED was accessed but has no value defined`. |

Causes, read from nixpkgs `lib/modules.nix` lines 1231 to 1265 and 1458: `definitionsWithLocations`
is `defsFinal`. Building it forces each surviving definition to weak head normal form. The option
default is a definition (`mkOptionDefault opt.default`) and survives when no fixture file defines
the option. In O1 the default is a `throw`, and `tryEval` catches it. In O2 the winning definition
is devenv's own `mkDefault ''${config.task.package}/...''`. `task.package` is null with no
processes. The string coercion is a type error, and `tryEval` does not catch it. The whole
evaluation aborts. A fixture definition that wins on priority hides the default.

### Fixes

| # | File | Fix | Why |
| --- | --- | --- | --- |
| F1 | `oracle.nix` | Query only the options that the fixture files mention (new `touched.nix`). Keep the full walk as `scope = "all"` with a `deny` list. | O2 is uncatchable. The full walk cannot be safe for every fixture state. Touched scope also cuts time. |
| F2 | `touched.nix` (new) | Load each fixture module, and its `imports` under `roots`, with the module arguments. Walk the module `config` text. Stop at the first declared option. Ignore `mkIf` conditions, so the set is a superset. Read no option value and no default. | Gives option paths without forcing other files' definitions. Handles `config =` form, shorthand form, `mkMerge`, `mkIf`, `mkOverride`, inline attrset, and function imports. |
| F3 | `oracle.nix` | On a catchable error, compare with the base option set. If the base option throws too, return no entry. Otherwise return `error = "definition-throws"`. | A throwing default means "no fixture definition" (O1). A throwing definition is a fixture error. Limit: a fixture definition that throws on an option whose default also throws is dropped silently. |
| F4 | `oracle.nix` | The `error` field is a string. The draft had `true`. | Name the cause. |
| F5 | `introspect.nix` | Take `@moduleArgs`. Pass `args`, `baseOptions`, `modules`, `scope`, `deny` to the oracle. | Needed by F2 and F3. The harness never reports `introspect`. |
| F6 | `serialize.nix` | Peel property wrappers inside attribute-set and list values: a false `mkIf` drops the element; a true `mkIf`, `mkOverride`, and `mkOrder` keep the content; `mkMerge` becomes `{"$merge": [...]}`. | `definitionsWithLocations` strips wrappers only at the top. Inside a freeform `env` or an `attrsOf submodule` they stay. The draft printed `{"FORCED": {"$type": "override"}, "GATED": {"$type": "if"}}`. |
| F7 | request | `roots` entries end in `/`. | Without it, `.../source` also matches `.../source-other`. |

`scope = "touched"` equals `scope = "all"` (with `process.manager.command` denied) for fixtures a, b,
c, d, e, and x-edge2. For x-edge they differ only by `process.manager.command`, which the deny list
removes. `scope = "all"` with the deny list walks the whole tree without error on all seven
fixtures. Cold time of the full walk: 4.5 s (b, c, e), 8.5 s (a), 4.5 s (x-edge, x-edge2). Touched
scope: 0.3 to 1.7 s.

An undeclared option in a fixture (`foo.bar = 1`) makes `extended.options` fail (module check) and
aborts the whole call. The `undeclared` entry in `oracle.nix` is unreachable. Bisection (Step 3)
handles it.

### Five golden fixtures

Commands: `python3 run_truth.py logs/final fixtures/{a,b,c,d,e}-*/`, then
`python3 compare_golden.py logs/final/run.stdout fixtures/{a,b,c,d,e}-*/`. Compare rules: `file` is
relative to `source/`. Wildcards in expected strings: `{FIXTURE}`, `<hash>`, `<version>`.

| Fixture | Content | Result |
| --- | --- | --- |
| a-probe | python enable, `env.GREETING`, packages jq, postgres enable, `enterShell` | equal to the 5-row table |
| b-scripts-tasks | `scripts.hello`, `scripts.greet`, `tasks."app:build"`, `tasks."app:test"` | equal; one definition each for `scripts` and `tasks` |
| c-imports | `imports = [ ./extra.nix ]`; env, packages, `enterShell` set in both files | equal; two definitions each; `extra.nix` first |
| d-priority | `mkForce`, `mkDefault`, `mkIf false`, `mkIf true`; second file `loser.nix` | equal |
| e-paths | `env.DATA_FILE = ./data.txt`; `"${pkgs.jq}/bin/jq"`; plain string; `scripts.show.exec = "cat ${./data.txt}"` | equal under wildcards |

Fixture d, expected and observed:

- `services.postgres.enable = mkForce true` beats plain `false` in `loser.nix`. Truth: `true`, file
  `devenv.nix`.
- `services.postgres.port = mkDefault 5433` loses to plain `5434` in `loser.nix`. Truth `5434`. The
  loser is absent. `services.redis.port` (`mkDefault 7000` against `7001`) has the same shape.
- `services.redis.enable = mkIf false true`: no entry.
- `env.FORCED = mkForce "forced"` and `env.DEFAULTED = mkDefault "defaulted"`: value
  `{"FORCED":"forced","DEFAULTED":"defaulted"}`, no priority.
- `scripts.gated = mkIf false {...}`: `scripts` has the value `{}`. The option has a definition with
  no element.
- `languages.python.enable = mkIf true true`: `true`.

Differences between actual and expected: the absolute `file` path (the comparison strips the prefix);
the store hash in two strings of e (`<hash>` matches 32 characters); the `$path` absolute path in e
(`{FIXTURE}`); `$name` `git-2.55.0` in c (`<version>`). The draft serializer printed `$type` for
nested `mkForce`, `mkDefault`, and `mkIf` in d (F6).

Honesty note from the report: the author wrote the expected files after seeing the first raw output.
The author derived the values from the fixture source and the module rules. Only the nested-wrapper
case disagreed, and the serializer changed, not the expectation. Fixture d changed once, because
`env.GATED = mkIf false` is invalid in devenv (O3). `scripts.gated` replaced it.

### Confirmations

| Claim | Evidence | Result |
| --- | --- | --- |
| `mkIf false` definitions are absent | d, x-edge | confirmed |
| `mkForce` and `mkDefault` values appear without priority | d (top level and, after F6, nested) | confirmed |
| A definition that loses on priority is absent | d: `loser.nix` `enable = false`, `5433`, `7000` | confirmed |
| Derivations serialize as `$pkg`, `$name`, `$output` | a: `{"$pkg":"jq","$name":"jq-1.8.2","$output":"bin"}` | confirmed |
| A path value is a `$path` tag | e: `DATA_FILE` | confirmed. A path inside a string is copied to the store at once. |
| A candidate path outside the base project is readable | all fixtures | confirmed |
| The eval cache tracks fixture and imported files | edited `extra.nix`, then `devenv.nix`, under one request path | confirmed |

### Stability (`python3 stability.py`)

For each fixture alone and for the batch of five: two runs with `--no-eval-cache`, one cold run and
one warm run with the cache. Byte comparison of the output. All six rows are byte-identical over
four runs, return code 0.

| Run | no-cache 1 | no-cache 2 | cache cold | cache warm |
| --- | --- | --- | --- | --- |
| a-probe | 1.20 s | 1.25 s | 1.19 s | 0.10 s |
| b-scripts-tasks | 0.31 s | 0.36 s | 0.31 s | 0.08 s |
| c-imports | 1.17 s | 1.13 s | 1.28 s | 0.09 s |
| d-priority | 0.30 s | 0.30 s | 0.37 s | 0.08 s |
| e-paths | 1.44 s | 1.45 s | 1.38 s | 0.08 s |
| batch of 5 | 1.60 s | 1.58 s | 1.48 s | 0.10 s |

The batch of five costs about the same as the slowest single call. The fixed start is about 0.3 s.
Other times: truth, `scope = "all"`, one fixture, cold: 4.5 to 8.5 s. Unmodified draft, probe
fixture: 11.1 s.

### Normalizer (`normalize.py`)

Rules: sorted keys; `/nix/store/<32 chars>-` to `<store>/`; `$path` under the root to `./rel`;
`file` dropped after a root check (a definition outside the root raises); `$name` dropped; folding
by a hard-coded table (`enterShell` lines joined by a newline; `env`, `scripts`, `tasks` recursive
union; `packages` concatenation; any other option with more than one definition becomes
`{"$multi-def": [...]}`; a clash inside a union also becomes `$multi-def`). A record with `error`
becomes `{"$error": <error>}`.

`python3 test_normalize.py`: all assertions pass. `python3 twin_test.py` copies the five fixtures to
`twin/A/deeper/` and `twin/B/deeper/`. Side B also changes `data.txt`, so the store hash differs.
One batch call. All five normalize equal. Raw truth is equal after swapping the directory prefix for
four fixtures. For e it differs in the store hash only.

### Inferences (not proved)

- I1. The extra cost of the full walk (3 to 8 s) is the forcing of every default. Nobody profiled it.
- I2. Other option states can hit uncatchable errors like `process.manager.command`. Touched scope
  avoids the class, not only this case.
- I3. Module forms not tested (`disabledModules`, a `specialArgs`-only argument, `imports` of a
  non-path key) may make `touched.nix` differ from the module system. The superset rule limits the
  harm. `scope = "all"` is the cross-check.
- I4. The oracle does not force `config`, so it cannot tell whether a fixture evaluates. The
  `env.GATED` fixture produced a truth although devenv rejects it. Step 7 needs a separate validity
  check for the `fails` class.
- I5. The cache key includes the request file path or its stamp. A new request path gave a cold run,
  and a repeat gave a warm run. The cause was not isolated.
- I6. Priority between two definitions inside one freeform attribute set (`env.X = mkDefault "a"`
  in one file, `env.X = "b"` in another) is not visible in truth. The normalizer would report
  `$multi-def` at `env.X`. Not tested.

---

## 3. Driver and batching (Steps 2, 3)

**Raw report:** none. TODO: `~/.local/state/devenv-py/phase-a/driver/REPORT.md` did not exist when
this record was written. Add the driver facts, the bisection log, and the timing table when the
report arrives.

What exists in the work directory (`~/.local/state/devenv-py/phase-a/driver/`, not yet reviewed
for this record): `driver.py`, the scripts `t1_echo_cache.py`, `t4_5_6.py`, `t4b_cache_edit.py`,
`t7_timing.py`, and logs under `runs/` (`t1.log`, `t4b.log`, `t456.log`, `t7-*.log`).

The oracle experiment gives partial evidence for Step 3: one `truth` request with five candidates
works (1.5 to 1.7 s), a candidate path outside the base project is readable (Step 3 action 3), and
a failing candidate aborts the whole call. The bisection test (Step 3 action 5) has no record yet.

---

## 4. Syntax reader (Step 11)

**Raw report:** `~/.local/state/devenv-py/phase-a/syntax/REPORT.md`. Files: `read_syntax.py`,
`selftest.py`, `literal_diff.py`, `probe_kinds.py`, `run_fleet.py`, `node-schema.json`, `.venv/`.

**Inputs.**

| Input | Value |
| --- | --- |
| pydantree | `~/Documents/Projects/pydantree`, git `c0ccabc`, clean |
| Vendored schema | copy of `examples/devenv-extract/node-schema.json`, sha256 `d34e9bdf2acd…`, 84 entries, 83 kind names (`inherit` is both a named node and a keyword token) |
| Python | 3.13.14 (uv venv) |
| tree-sitter | 0.26.0 |
| Grammar A | PyPI `tree-sitter-nix` 0.1.0, ABI 14, 108 kinds |
| Grammar B | nixpkgs `python3Packages.tree-sitter-grammars.tree-sitter-nix` 0.3.0 (2025-12-03), ABI 13, 108 kinds |
| pydantic | 2.14.0 |
| Fleet | 59 files `~/Documents/Projects/*/devenv.nix` |

### Loading the grammar

- Route 1 fails: `devenv shell -- python examples/devenv-extract/extract.py` in pydantree stops with
  `Failed to evaluate dotenv configuration` and `The option 'dotenv.resolved' was accessed but has no
  value defined`. The cause is in the pydantree devenv setup with devenv 2.4.0. Nobody investigated.
- Route 2 works: a uv venv with `tree-sitter>=0.26,<0.27`, `tree-sitter-nix`, `pydantic`, and the
  pydantree `src` on `PYTHONPATH`. The schema loads and `Grammar.load` passes its conformance check.
- Route 3 works: the nixpkgs grammar (Grammar B) needs a two-line stub for `tree_sitter_config` and
  `pydantic[email]`. The fleet run on Grammar B gives the same counts as Grammar A on every row.

### Real node kinds

| Construct | Real kind | Fields and children |
| --- | --- | --- |
| root | `source_code` | `expression` (opt, one) |
| function head | `function_expression` | `formals` (opt), `universal` (opt; the `args@` name, also a bare `x:` parameter), `body` (req) |
| formals | `formals` | `formal` (opt, many), `ellipses` (opt) |
| one formal | `formal` | `name` (req, `identifier`), `default` (opt) |
| attrset | `attrset_expression` | child `binding_set` (opt) |
| recursive attrset | `rec_attrset_expression` | same |
| binding set | `binding_set` | `binding` (req, many): `binding`, `inherit`, or `inherit_from` |
| binding | `binding` | `attrpath` (req), `expression` (req) |
| attrpath | `attrpath` | `attr` (req, many): `identifier`, `string_expression`, or `interpolation` |
| `inherit a;` | `inherit` | `attrs` (req, `inherited_attrs`) |
| `inherit (a) b;` | `inherit_from` | `attrs` (req), `expression` (req) |
| string | `string_expression` | children (opt, many): `string_fragment`, `escape_sequence`, `dollar_escape`, `interpolation` |
| interpolation | `interpolation` | `expression` (req) |
| indented string | `indented_string_expression` | same children. No indented fragment kind. |
| integer | `integer_expression` | none; the text is the value |
| float | `float_expression` | none |
| negative number | `unary_expression` | `operator` (`-` or `!`), `argument`. A literal `-1` is a unary node. |
| `true`, `false`, `null`, other variable | `variable_expression` | `name` (req, `identifier`). No boolean or null kind. |
| list | `list_expression` | `element` (opt, many) |
| select (`pkgs.jq`) | `select_expression` | `expression`, `attrpath`, `default` (opt; the `or` form) |
| with | `with_expression` | `environment`, `body` |
| apply | `apply_expression` | `function`, `argument`. Curried: `lib.mkOverride 5 v` is apply(apply(`lib.mkOverride`, 5), v). |
| let | `let_expression` | child `binding_set` (opt), `body` |
| if | `if_expression` | `condition`, `consequence`, `alternative` |
| parentheses | `parenthesized_expression` | `expression` |
| binary | `binary_expression` | `left`, `operator`, `right` |
| path | `path_expression` | children `path_fragment`, `interpolation` |

pydantree names the attrset content `content`. A `\$` or `''$` in a string gives a `dollar_escape`
node with only the marker; the next `string_fragment` holds the `$`. A `comment` node is not in the
`binding` field. In this grammar `a or 1` outside a select parses as an apply of `a` to a variable
named `or`. It does not occur in the fleet.

### The prototype `read_syntax.py`

- Typed nodes: `Fn` narrows `function_expression`; `Root` narrows `source_code`. Other nodes are
  generated pydantree classes. The reader dispatches with `isinstance`.
- `read_syntax(src)` returns the nested dict and raises `SyntaxReadError` on a grammar parse error.
  `read_syntax_full(src)` also returns every `$nix` record with its byte span, every typed literal
  with its span, the function head, and a shadow read of a root `let` body.
- Value forms: `mkDefault` gives priority 1000. `mkForce` gives 50. `mkOverride n` gives `n` when
  `n` is an integer literal. Parentheses are removed. A `-` before a number reads as a negative
  number. `pkgs.x.y` reads as `$pkg` only when every attribute is a plain name and there is no `or`
  default. Inside `with pkgs; [ ... ]` a bare name reads as `$pkg`, unless the function head binds
  it (`lib`, `config`); then it becomes `$nix`. `true`, `false`, `null` stay literals.
- Strings: a double-quoted string decodes `\n`, `\r`, `\t`, and `\X`. An interpolation makes the
  whole string `$nix`. An indented string removes the common indent as Nix does. An interpolation or
  any `''\` escape makes it `$nix`. The `'''` escape decodes.
- A binding with a dynamic attribute name, an `inherit`, an `inherit (x)`, or a path collision goes
  in a list under the key `$nix-binding`. Each entry is `{"$nix": <binding text>}`, with the `;`.
- A function head is read and removed. A curried head is read in a loop.
- A root body that is a `let` becomes `{"$nix": <whole let text>}`. Any other non-attrset root body
  becomes one `$nix`. `rec { }` and legacy `let { }` become `$nix`.
- Counting: a leaf is the lowest value in the tree (a scalar, a list, a priority wrapper, `$pkg`,
  `$nix`, or an empty attrset). A leaf is `typed` when it holds no `$nix`, `nix` when it is itself a
  `$nix`, and `partial` otherwise (a list with some `$nix` elements).

Tests: `selftest.py` has 18 synthetic cases with exact trees, all pass. `literal_diff.py` compares 44
synthetic literal snippets with Nix evaluation: 0 mismatches (3 snippets fall back to `$nix` by
design).

### Fleet run

Command: `PYTHONPATH=~/Documents/Projects/pydantree/src .venv/bin/python run_fleet.py`. The glob
matched 60 files. The run skips paths with `.devenv` or `gitman-workspaces`, never reads
`devenv.local.nix`, and skips `devenv-py/devenv.nix`. That leaves 59 files. Expected: most files
read, a high share of bindings typed.

| Measure | Value |
| --- | --- |
| Files parsed | 58 of 59. `nix-nvim` holds conflict markers (`<<<<<<<`); `nix-instantiate --parse` rejects it too. |
| Leaves, 58 valid files | 423: typed 358, partial 6, nix 59 |
| Typed ratio | 84.6 percent (86.0 percent with partial). Inflated. |
| Root `let` | 28 of 58 files; each counts as one `nix` leaf |
| 30 files without a root `let` | 395 leaves, 358 typed, 90.6 percent. 10 of the 30 have no `$nix`. |
| All 58 with `let` bodies followed (shadow read) | 1131 leaves, 894 typed, 112 partial, 125 nix. Typed 79.1 percent (88.9 with partial). A lower bound. |
| Value forms | 107 `$pkg`, 64 lists, 3 `$priority`, 65 `$nix` |
| Typed scalars | 172 double-quoted strings, 76 indented strings, 89 booleans, 2 integers. No floats, no `null`, no `mkOverride`. |
| Time | 1.0 s for 58 files; the largest file 43 ms |
| Non-ASCII | 48 of 59 files; spans stay exact |

Reasons for `$nix` (65 values): root `let` 28 (43 percent); indented string with interpolation 19
(29 percent); string with interpolation 11 (17 percent); path in a list 4; apply of something other
than `lib.mkDefault`, `lib.mkForce`, or `lib.mkOverride` 2; select whose root is not `pkgs` 1. Without
the root `let`, interpolation causes 30 of the 37 remaining (81 percent). All 6 partial leaves are
lists. Inside `let` bodies (213 `$nix` values): string interpolation 89, select with a non-`pkgs`
root 38, indented interpolation 35, unknown variable 21, `lib.mkOption` 8, other apply 8, `++` 4,
`lib.mkIf` 4, path 3, `+` 2, `lib.optional` 1.

The per-file table is in the raw report.

### Span exactness and literal values

Over 58 valid files and 65 `$nix` values: the source slice at the span equals the stored text; the
tree value equals the stored text; the text parses by itself as one expression (or one binding in
`{ }`); the tree values and records match one to one. 0 failures on each check, including
non-ASCII files. Extra check: `nix-instantiate` evaluated the source slice of 339 typed scalar
literals and compared type and value: 0 mismatches, 0 evaluation errors. The check found three bugs in
the first indented-string decoder (an escaped line break `''\n` is not an indent break; a
single-line string of spaces reads as the empty string; a wrong slice offset). All three are fixed.

### Inferences (not proved)

1. A root `let` is the main cost. Under the guide rule ("keep the whole body as one NixExpr"), half of
   the files give no typed field.
2. Interpolation is the next cost. A fragment list with `$nix` holes would keep literal parts typed.
   The run did not inspect what the interpolations hold.
3. `lib.mkIf`, `lib.mkMerge`, and function calls are rare at the top level of a fleet `devenv.nix`.
4. The reader needs the function head's bound names, or `with pkgs; [ lib.x ]` reads `lib.x` as a
   package. A `let` or a nested lambda also binds names. The prototype is safe only because it makes
   those values `$nix`.
5. pydantree narrowing works one level at a time. The prototype narrows two levels and uses
   `isinstance` below.
6. A module that defines node subclasses must not use `from __future__ import annotations`. With it,
   `Fn.formals: N.Formals | None` raised `SchemaCheckError: optionality disagrees`. The cause is
   likely annotation strings evaluated in the class namespace. Not confirmed in the pydantree source.
7. A bare-number `$priority` loses the function name: `lib.mkDefault 1` and `lib.mkOverride 1000 1`
   read the same. This matters for RT5.
8. The devenv failure in pydantree is a local environment fault. It does not touch the reader.

---

## 5. Corpus survey (Step 7)

**Raw report:** `~/.local/state/devenv-py/phase-a/corpus/REPORT.md`. Data: `fixtures.json`,
`survey.json`. Tools: `~/.local/state/devenv-py/phase-a/tools/` (`survey.py`, `aggregate.py`,
`report.py`).

This is a static survey. No fixture was evaluated. Classes are predictions. The option paths come
from a small Nix tokenizer and a binding parser, not from evaluation. Options set only in imported
files are not counted. The `devenv.yaml` reader is a line-based subset parser. `secret` means a
`secretspec.toml`, a `secretspec` key or word in `devenv.yaml`, or a `secretspec` token in
`devenv.nix`. Other secret tools are not detected.

License: devenv at the pin is Apache-2.0. Vendoring examples and tests needs the license text and a
NOTICE of origin.

| Source | `devenv.nix` files | batch | alone | secret | broken |
| --- | --- | --- | --- | --- | --- |
| devenv-examples | 72 | 47 | 25 | 0 | 0 |
| devenv-tests | 159 | 124 | 31 | 4 | 0 |
| fleet | 407 | 99 | 289 | 18 | 1 |

- Examples: 69 top-level directories hold a `devenv.nix`; 3 nested files add to 72
  (`compose/projectA`, `compose/projectB`, `imports/folder`).
- Tests: 150 entries in `tests/`; 159 `devenv.nix` files because some entries nest.
- Fleet: 407 files, all private. 266 sit under `.archive/` or `.worktrees/` (copies and old
  checkouts). 140 are primary paths. Unique content: 157 across all paths, 104 across primary paths.
  One file is a broken symlink (`.archive/paloma-story-generation-20261003`).
- `devenv.local.nix` exists in 71 fleet directories; 69 are symlinks. Contents never read.
- The fleet `alone` count is high because fleet projects set `imports:` in `devenv.yaml` and add
  inputs such as `repoman`, `vendomat`, `git-hooks`, `shellij`.
- `fails` cannot be predicted statically. Fixtures such as `tests/syntax-error` and
  `tests/missing-input-error` are probably `fails`.

### Pilot coverage (gate: 10 python, 5 postgres, at most 20 percent excluded)

| Group | python (unique) | python excluded | postgres (unique) | postgres excluded |
| --- | --- | --- | --- | --- |
| devenv-examples | 7 (7) | 0 | 5 (5) | 0 |
| devenv-tests | 16 (16) | 0 | 5 (5) | 0 |
| fleet, all paths | 282 (103) | 16 (5.7 percent) | 114 (11) | 1 (0.9 percent) |
| fleet, primary, unique | 64 (64) | 8 (12.5 percent) | 3 (3) | 0 |
| public only (examples + tests) | 23 (23) | 0 | 10 (10) | 0 |
| all, deduplicated | 87 (87) | 8 (9.2 percent) | 13 (13) | 0 |

The raw fleet count of 114 postgres fixtures is one `.archive` file copied about 95 times. By
prediction the corpus meets the pilot gate, and the public sources alone meet it. The prediction
holds only if the public fixtures evaluate. Re-check after the evaluation run reports `fails`.

Top option-path prefixes by deduplicated fixture count: `packages` 121, `languages.python` 87,
`env.*` 83, `enterTest` 79, `tasks.*` 72, `enterShell` 65, `scripts.*` 42, `processes.*` 32,
`repoman.enable` 26, `testee.package` 23, `testee.checks` 23, `languages.rust` 13, `process.manager` 13,
`services.postgres` 13, `git-hooks.hooks` 10. The prefixes `repoman`, `testee`, `docman`, and
`zelligate` are fleet-module options. A stock model does not have them. The per-fixture tables are in
the raw report.

### Inferences (not proved)

- I1. Deduplication by content hash removes the copies. Excluding `.archive/` and `.worktrees/` also
  drops old unique files: 157 unique contents over all paths, 104 over primary paths. The owner
  decision (D7) accepts that loss.
- I2. Fleet-module options need those modules in a pin's options export (a later pin variant).

---

## 6. Orchestrator decisions taken from phase A

| # | Decision | Source |
| --- | --- | --- |
| D1 | The oracle uses `touched` scope by default. `scope = "all"` with a `deny` list is the cross-check. | section 2, F1 |
| D2 | `introspect.result` is a JSON string for every kind. The driver decodes twice. | section 1, F2 |
| D3 | The syntax reader keeps a root `let` header as a verbatim prefix text. | section 4, inference 1 |
| D4 | `inherit`, dynamic names, and collisions go in `extra_bindings`. | section 4 |
| D5 | The syntax reader keeps an interpolated string as one `$nix`. | section 4 |
| D6 | The syntax reader records the priority function name. | section 4, inference 7 |
| D7 | The corpus harvest excludes `.archive/` and `.worktrees/` and deduplicates by content hash. | section 5 |
| D8 | Models for fleet-module options (`testee`, `repoman`, `docman`) need those modules in a pin's options export. Add them as a later pin variant. | section 5 |

## 7. GM0 on the new pin

Step 0 says GM0 must pass again for the pin that Step 1 selects. Phase A used `b904dcb5`. These
Step 0 surfaces worked in the experiments: stock `devenv eval` with `-O` and a request file (O10 to
O12), `extendModules` for batches (O8), option types with `type.name`, `nestedTypes`, and
`definitionsWithLocations` (O6, O7), and the nixpkgs tree-sitter Nix grammar (O9, Route 3). Nobody
reran the Step 0 probe commands one by one. GM0 for this pin is therefore not recorded as passed.

## 8. Findings with no home yet

- The options report notes that the Step 8 rule "freeform options under `nested.freeformType`" and
  "`loc` is a list whose elements can hold dots" bind the generator. Both appear in the guide's
  Step 8 now. The generator must also read `recursive`, `truncated`, `depthCut`, `defaultSkipped`,
  and `defaultError`.
- The two `introspect.nix` prototypes differ. The options prototype returns a JSON string and adds
  `optionsDoc` and `normalize`. The oracle prototype returns a plain attribute set and takes
  `@moduleArgs`, `scope`, and `deny`. No prototype has both. The port merges them under decision D2.
- The pydantree `devenv shell` fault (`dotenv.resolved`) is not in project 17 scope. The owner may
  want it fixed. It blocks the example `extract.py` on Route 1.
- The fleet file `nix-nvim` holds version-control conflict markers in `devenv.nix`.

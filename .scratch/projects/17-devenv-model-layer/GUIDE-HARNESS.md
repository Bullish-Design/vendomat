# Guide: the round-trip harness for typed devenv models

**Date:** 2026-10-10. **Status:** Draft for owner review. **Concept:** [CONCEPT.md](./CONCEPT.md).

This guide builds the harness in order. Each step names its goal, its actions, the expected result,
the record to write, and its gate. Do not start a step before the gate of the step before it passes.

Every command, file name, option name, and Nix node kind here is proposed until the step's fixture
proves it on the pinned tools. When a fixture disproves an interface, update this guide, the concept,
and the code together.

## Conventions

- **Repository.** The harness lives in a new repository, `devenv-py` (owner decision, 2026-10-11). Paths below
  are relative to its root unless they start with `~` or `/`.
- **Version control.** Use a Gitman workspace for each step: `gitman work dpy-step-N`.
- **Verification.** The harness repository verifies through Testee, like Vendomat. Step 14 adds the
  checks. Before Step 14, run the step's commands inside `devenv shell`.
- **Raw logs.** Write raw logs under `~/.local/state/devenv-py/` (MDL-012). Never commit them.
- **Records.** Write one record per step in this project directory:
  `evidence/step-N.md`. Record the pin, the exact commands, the expected results, and the actual
  results. Keep observation apart from inference.
- **Pin.** A pin is the devenv CLI version, the `devenv` input revision, and the `nixpkgs` input
  revision. Its identifier is `devenv-<cli>-<devenv-rev:8>-<nixpkgs-rev:8>`. Every output file
  carries the pin identifier.

## Repository layout (target)

```text
devenv-py/
  devenv.nix  devenv.yaml  devenv.lock      harness toolchain and Testee checks
  pyproject.toml  uv.lock
  pins/<pin-id>/                             base project for one pin
    devenv.nix  devenv.yaml  devenv.lock  pin.toml
  nix/
    introspect.nix                           the request module that the base imports
    options.nix                              options export
    serialize.nix                            tagged JSON values
    oracle.nix                               per-file contributions
  reader-module/default.nix                  Path T fixed reader
  src/devenv_py/
    pin.py  driver.py  options.py  truth.py  normalize.py  compare.py
    corpus.py  values.py  generator.py  writer_nix.py  writer_toml.py
    read_eval.py  read_syntax.py  roundtrip.py  generate_cases.py  report.py  cli.py
  templates/devenv-module/                   Templateer template for Path N
  exports/<pin-id>/options.json
  generated/<pin-id>/<subtree>.py
  narrowed/<subtree>.py
  corpus/<source>/<name>/
    source/  provenance.toml  truth/<pin-id>.json  triage.toml
  tests/
  .agents/skills/                            Step 16
```

The command-line tool is `dpy` (proposed). Its subcommands appear in the steps that add them.

---

## Step 0. Confirm the evaluation surfaces

**Goal.** Know which devenv interfaces expose typed options and per-file definitions.

**Status.** Done on 2026-10-10. See [evidence/step-0-probe.md](./evidence/step-0-probe.md).

**Facts the later steps rely on.**

- `devenv eval` reaches only `devenv.config.*` (O2). A module can still expose options there.
- An introspection module with the `options` and `extendModules` arguments works through stock
  `devenv eval`. A request file reaches it through `-O`. The evaluation cache tracks changed files
  (O10 to O12).
- `devenv repl` reads commands from standard input (O4). It is the fallback route.
- `devenv.project` is the `lib.evalModules` result. Its `options` carry `type.name`,
  `nestedTypes`, and `definitionsWithLocations` (O6, O7).
- `devenv.project.extendModules` evaluates added modules in the same process (O8).
- nixpkgs ships `python3Packages.tree-sitter-grammars.tree-sitter-nix` (O9).

**Repeat on each pin bump.** Run the probe commands in the record against the new pin. If any fact
fails, stop and update the concept before you continue.

**Gate GM0.** Passed for the probe pin. It must pass again for the pin that Step 1 selects.

---

## Step 1. Create the repository, the toolchain, and the first pin

**Goal.** A repository with a working shell and one base project per pin.

**Actions.**

1. Create the `devenv-py` repository with the owner's usual repository tooling. Use Gitman
   workspaces for every later change.
2. Write `devenv.nix` with Python 3.13, uv, Nix tools (`nix-instantiate`), and the Testee module.
   Copy the Testee import pattern from Vendomat's `devenv.nix`.
3. Write `pyproject.toml` with these dependencies: `pydantic`, `hypothesis`, `tomli-w`,
   `pydantree-sitter`, `tree-sitter`, `tree-sitter-nix`, and `templateer`. Point `pydantree-sitter`
   and `templateer` at their pinned tags. Use the `devenv-extract` pattern from pydantree for the
   Nix grammar.
4. Create the first base project at `pins/<pin-id>/`:

   ```nix
   # pins/<pin-id>/devenv.nix: the empty base that candidates extend.
   { }
   ```

   ```yaml
   # pins/<pin-id>/devenv.yaml
   inputs:
     devenv:
       url: github:cachix/devenv/<rev>      # pin the module source (probe I5)
     nixpkgs:
       url: github:cachix/devenv-nixpkgs/rolling
     nixpkgs-python:
       url: github:cachix/nixpkgs-python
       inputs:
         nixpkgs:
           follows: nixpkgs
   ```

   For the owner's machines, pin `devenv` to the fork revision instead. For Basix learners, pin it to
   the upstream release.
5. Run `devenv shell -- true` inside `pins/<pin-id>/`. This writes `devenv.lock`.
6. Write `pin.toml` from the lock and the CLI:

   ```toml
   id = "devenv-2.4.0-a73c5b84-c2f38fe7"
   cli = "2.4.0+b904dcb"
   devenv_rev = "a73c5b84c9527760f009232988466763068f9f61"
   nixpkgs_rev = "c2f38fe7f9e04d9aadd354d380f2bd40531d9737"
   inputs = ["devenv", "nixpkgs", "nixpkgs-python"]
   ```

7. Write `src/devenv_py/pin.py`. It reads `pin.toml`, checks it against `devenv.lock` and
   `devenv --version`, and fails on any difference.

**Expected result.** `devenv shell -- python -c "import pydantree_sitter, templateer, tree_sitter_nix"`
exits 0. `pin.py` accepts the pin.

**Record.** `evidence/step-1.md`: the tag of each dependency, the pin, and the commands.

**Gate.** The shell imports all three libraries, and the pin check passes.

---

## Step 2. The evaluation driver

**Goal.** One Python function sends a request to stock `devenv eval` and returns parsed JSON.

The base project imports an introspection module. The module takes the `options` and
`extendModules` module arguments. It reads a request file and puts its answer in a read-only config
value. `devenv eval` then reads that value like any other config attribute (probe O10 to O12).
No fork patch and no repl are needed.

**Actions.**

1. Write `nix/introspect.nix`:

   ```nix
   # nix/introspect.nix: answer one harness request as a config value.
   { lib, pkgs, options, extendModules, config, ... }:
   let
     cfg = config.introspect;
     req = builtins.fromJSON (builtins.readFile cfg.request);
     # The harness never reports on its own options.
     own = opts: removeAttrs opts [ "introspect" ];
     truthOf = c:
       let extended = extendModules { modules = map (f: /. + f) c.modules; };
       in import ./oracle.nix { inherit lib; options = own extended.options; roots = c.roots; };
   in
   {
     options.introspect = {
       request = lib.mkOption {
         type = lib.types.nullOr lib.types.path;
         default = null;
         description = "The harness request file.";
       };
       result = lib.mkOption {
         type = lib.types.raw;
         readOnly = true;
         description = "The answer to the harness request.";
       };
       optionsDoc = lib.mkOption {
         type = lib.types.package;
         readOnly = true;
         description = "nixosOptionsDoc JSON for the completeness check of Step 4.";
       };
     };
     config.introspect = {
       result =
         if cfg.request == null then null
         else if req.kind == "echo" then req.payload
         else if req.kind == "options" then
           import ./options.nix { inherit lib; options = own options; maxDepth = req.maxDepth; }
         else if req.kind == "truth" then lib.mapAttrs (_: truthOf) req.candidates
         else throw "unknown request kind: ${req.kind}";
       optionsDoc =
         (pkgs.nixosOptionsDoc { options = removeAttrs (own options) [ "_module" ]; }).optionsJSON;
     };
   }
   ```

2. Make the base project import it. Replace `pins/<pin-id>/devenv.nix` with:

   ```nix
   # pins/<pin-id>/devenv.nix: the base that candidates extend.
   { imports = [ ../../nix/introspect.nix ]; }
   ```

3. Write `src/devenv_py/driver.py`:

   ```python
   class DriverError(RuntimeError):
       """devenv eval failed. The message holds the tail of its error output."""


   def run_request(
       pin_dir: Path, request: dict, run_dir: Path, timeout: int = 900, cache: bool = True
   ) -> Any:
       run_dir.mkdir(parents=True, exist_ok=True)
       request_file = run_dir / "request.json"
       request_file.write_text(json.dumps(request))
       argv = ["devenv", "eval"]
       if not cache:
           argv.append("--no-eval-cache")
       argv += ["-O", "introspect.request:path", str(request_file), "introspect.result"]
       proc = subprocess.run(
           argv, cwd=pin_dir, text=True, capture_output=True, timeout=timeout,
           env={**os.environ, "NO_COLOR": "1"},
       )
       (run_dir / "eval.stdout").write_text(proc.stdout)
       (run_dir / "eval.stderr").write_text(proc.stderr)
       if proc.returncode != 0:
           raise DriverError(proc.stderr[-4000:])
       return json.loads(proc.stdout)["introspect.result"]
   ```

   `run_dir` is `~/.local/state/devenv-py/runs/<timestamp>-<kind>/`.
4. Write `tests/test_driver.py`. Send an `echo` request with a payload that holds a double quote, a
   backslash, a newline, `${`, a non-ASCII character, and a nested list. Assert that the result
   equals the payload.
5. Send an unknown request kind. Assert that `DriverError` holds the text `unknown request kind`.
6. Test the cache. Send two different requests through the same file path. Assert two different
   results (probe O12 saw this once). Keep `cache=False` as the switch if it ever fails.

**Expected result.** The echo test passes, and the cache test gives two different results.

**Fallback.** If a later pin breaks this route, use `devenv repl`. Pipe
`:p import <nix-dir>/entry.nix { inherit devenv; requestFile = <file>; }` on standard input. Let the
entry wrap `builtins.toJSON` of the answer in fixed sentinel strings, and parse the text between
them (probe O4). Use `devenv.project.options` and `devenv.project.extendModules` in place of the
module arguments.

**Record.** `evidence/step-2.md`: the echo payload, the cache result, and the wall time of one
request with and without the cache.

**Gate GM1 (part 1).** The echo and cache tests pass on the pin.

---

## Step 3. Batch evaluation and bisection

**Goal.** Evaluate many candidate modules in one `devenv eval` call. Find the bad one when a batch
fails.

**Actions.**

1. Write a temporary `oracle.nix` that returns the `env` definitions for each candidate. Step 5
   replaces it.
2. Write three candidate modules under a temporary directory. Each one sets a different
   `env.MARK` value. Send one `truth` request with all three. Assert three different results.
3. Confirm that a module given as an absolute path keeps its path in `definitionsWithLocations`.
   Probe O8 saw `<unknown-file>` only for an inline module, and probe O12 used a relative path.
   Also confirm that pure evaluation lets the module read candidate files outside the base project.
   If it does not, let the driver copy each batch into `pins/<pin-id>/.candidates/<batch-id>/`.
4. Write `driver.run_batch(candidates)`. On `DriverError`, split the batch in two halves and retry
   each half. A single candidate that still fails gets the status `eval-error` and keeps its error
   tail (MDL-013).
5. Write a test with five good candidates and one candidate that sets
   `env.MARK = builtins.abort "dm-bisect";`. `tryEval` does not catch `abort`, so the whole batch
   fails. Assert five results and one `eval-error` whose tail holds `dm-bisect`.
6. Measure wall time for batches of 1, 10, 50, and 200 candidates that each enable one service.

**Expected result.** Batch evaluation works. Bisection isolates the bad candidate. The time per
candidate falls as the batch grows.

**Record.** `evidence/step-3.md`: the timing table, the bisection log, and the answer to action 3.

**Gate GM1.** Batch and bisection tests pass. The timing table exists.

---

## Step 4. The options export

**Goal.** A complete, structured JSON export of the option tree for the pin.

**Actions.**

1. Write `nix/options.nix`:

   ```nix
   # nix/options.nix: export the option tree with structured types.
   { lib, options, maxDepth }:
   let
     json = v:
       let r = builtins.tryEval (builtins.toJSON v);
       in if r.success then builtins.fromJSON r.value else null;
     text = d: if d == null then null else if builtins.isString d then d else d.text or null;
     typeTree = depth: t: {
       name = t.name;
       description = t.description or null;
       payload = json (t.functor.payload or null);
       nested = lib.mapAttrs (_: typeTree depth) (t.nestedTypes or { });
       options =
         if t.name == "submodule" && depth < maxDepth
         then walk (depth + 1) (t.getSubOptions [ "<name>" ])
         else null;
     };
     leaf = depth: o: {
       loc = o.loc;
       type = typeTree depth o.type;
       hasDefault = o ? default;
       default = if o ? default then json o.default else null;
       defaultText = text (o.defaultText or null);
       description = text (o.description or null);
       readOnly = o.readOnly or false;
       internal = o.internal or false;
       visible = o.visible or true;
       declarations = map toString (o.declarations or [ ]);
     };
     walk = depth: attrs:
       lib.concatLists (lib.mapAttrsToList (_: v:
         if lib.isOption v then [ (leaf depth v) ]
         else if builtins.isAttrs v then walk depth v
         else [ ]) (removeAttrs attrs [ "_module" ]));
   in walk 0 options
   ```

2. Write `src/devenv_py/options.py` with `dpy export`. It sends an `options` request with
   `maxDepth = 3`, adds the pin, adds a SHA-256 of the canonical JSON, and writes
   `exports/<pin-id>/options.json`.
3. Write the completeness check. Run `devenv build introspect.optionsDoc` and read
   `share/doc/nixos/options.json`. Take its keys.
   Take the joined `loc` of every exported option that is visible and not internal, including
   sub-options. The two sets must be equal. List every difference. `optionsJSON` writes `<name>`
   for an attribute-set element and `*` for a list element; map the export's names the same way.
4. Write a type census: count options per `type.name`, including nested names. Some names carry a
   payload in the name itself, such as `strMatching <pattern>`. Record each such form.
5. Spot-check three options by hand: `services.postgres.port` (`unsignedInt16`), `packages`
   (`listOf` of `package`), and `env` (freeform `submodule`).
6. Check `enum` payloads. Record whether the payload is `{ values = [...]; }` or a bare list at this
   nixpkgs revision.

**Expected result.** About 1144 top-level visible options at the probe pin (probe O5). The two key
sets are equal, or every difference has a named cause. The spot checks match.

**Record.** `evidence/step-4.md`: the export hash, the census, the completeness result, and the
enum payload form.

**Gate GM2.** The export is complete, or each gap is named, and the hash is stable over two runs.

---

## Step 5. The oracle and the serializer

**Goal.** Truth: the definitions that a fixture's files give to each option, as tagged JSON.

**Actions.**

1. Write `nix/serialize.nix`:

   ```nix
   # nix/serialize.nix: turn a Nix value into JSON data with tagged forms.
   { lib }:
   let
     tag = v:
       if lib.isDerivation v then {
         "$pkg" = v.pname or (lib.getName v);
         "$name" = v.name;
         "$output" = v.outputName or "out";
       }
       else if builtins.isFunction v then { "$fn" = true; }
       else if builtins.isPath v then { "$path" = toString v; }
       else null;
     go = depth: v:
       let t = tag v; in
       if depth > 64 then { "$deep" = true; }
       else if t != null then t
       else if builtins.isAttrs v then
         (if v ? _type then { "$type" = v._type; } else lib.mapAttrs (_: go (depth + 1)) v)
       else if builtins.isList v then map (go (depth + 1)) v
       else v;
   in v:
     let r = builtins.tryEval (let s = go 0 v; in builtins.deepSeq s s);
     in if r.success then r.value else { "$error" = "throw or assert"; }
   ```

   `tryEval` does not return the message. The driver's bisection gives the message for other
   errors.
2. Write `nix/oracle.nix`:

   ```nix
   # nix/oracle.nix: the definitions that files under `roots` give to each option.
   { lib, options, roots }:
   let
     serialize = import ./serialize.nix { inherit lib; };
     mine = d: lib.any (root: lib.hasPrefix root (toString d.file)) roots;
     leaf = opt:
       let r = builtins.tryEval (builtins.filter mine opt.definitionsWithLocations);
       in if !r.success then [ { loc = opt.loc; error = true; } ]
          else if r.value == [ ] then [ ]
          else [ {
            loc = opt.loc;
            defs = map (d: { file = toString d.file; value = serialize d.value; }) r.value;
          } ];
     walk = attrs:
       lib.concatLists (lib.mapAttrsToList (_: v:
         if lib.isOption v then leaf v
         else if builtins.isAttrs v then walk v
         else [ ]) (removeAttrs attrs [ "_module" ]));
   in walk options
   ```

3. Write `src/devenv_py/truth.py` with `dpy truth <fixture>...`. It builds a batch request. Each
   candidate's `modules` is the fixture's `source/devenv.nix`. Its `roots` is the fixture's
   `source/` directory.
4. Write five golden fixtures under `tests/golden/`. Write each expected truth by hand. Use the
   probe fixture as the first one. Its expected truth, before normalization:

   | `loc` | `defs[].value` |
   | --- | --- |
   | `languages.python.enable` | `true` |
   | `env` | `{"GREETING": "hi"}` |
   | `packages` | `[{"$pkg": "jq", "$name": "jq-1.8.2", "$output": "bin"}]` |
   | `services.postgres.enable` | `true` |
   | `enterShell` | `"echo hi"` |

   The other four golden fixtures: a `scripts` and `tasks` fixture; a fixture with `imports` of a
   second file; a fixture with `lib.mkForce`, `lib.mkDefault`, and a false `lib.mkIf`; and a fixture
   with a path value and a string that holds a store path.
5. Run each golden fixture twice. Compare the two runs byte for byte.

**Expected result.** The truth equals the golden values. The `mkIf false` definition is absent.
`mkForce` and `mkDefault` values appear without their priority (concept: Truth). Two runs are equal.

**Record.** `evidence/step-5.md`: the five truths, the run times, and each observed difference from
the golden values with its cause.

**Gate GM3 (part 1).** All five golden fixtures match, and truth is stable.

---

## Step 6. The normalizer and the comparison

**Goal.** Compare truths without false differences from store hashes, paths, or definition counts.

**Actions.**

1. Write `src/devenv_py/normalize.py`:
   - Sort object keys.
   - Replace `/nix/store/<32 chars>-` with `<store>/` in every string.
   - Rewrite `$path` values under the fixture root as relative paths that start with `./`.
   - Drop the `file` field of each definition after the root check.
   - Fold the definitions of one option with the option's merge rule from the export:
     `listOf` concatenates, `attrsOf` and `submodule` take a recursive union, and
     `separatedString` joins with its separator. Mark any other option with more than one
     definition as `multi-def`.
   - Drop `$name` from `$pkg` values, because it carries a version. Keep `$pkg` and `$output`.
2. Write `src/devenv_py/compare.py`. It returns a list of differences. Each difference holds
   the option path, the JSON path inside the value, the expected value, and the actual value.
3. Write unit tests for each rule in action 1, and for a comparison with zero, one, and many
   differences.

**Expected result.** Two truths of the same source in two directories compare equal.

**Record.** `evidence/step-6.md`: the rules, the test count, and the result of the two-directory
test.

**Gate GM3.** The normalizer tests pass, and the two-directory test shows no difference.

---

## Step 7. Harvest and triage the corpus

**Goal.** A corpus of real fixtures, each with provenance, triage, and truth.

**Actions.**

1. Write `src/devenv_py/corpus.py` with `dpy harvest <source>`. Each fixture gets this layout:

   ```text
   corpus/<source>/<name>/
     source/devenv.nix   source/devenv.yaml   (and any imported files)
     provenance.toml     origin, revision, path, license, private flag
     triage.toml         class and reason
     truth/<pin-id>.json
   ```

2. Harvest `devenv-examples` from the pinned `devenv` input's `examples/` directory. Read the source
   path from the export's `declarations` or from the lock. Record the license from the source.
3. Harvest `devenv-tests` from the input's `tests/` directory. Keep only entries with a `devenv.nix`.
4. Harvest `fleet`: every `devenv.nix` under `~/Documents/Projects`, excluding `.devenv/`,
   `gitman-workspaces/`, and `node_modules/`. Set `private = true`. Never copy a
   `devenv.local.nix`. Fleet fixtures stay in a private repository or in local state.
5. Triage each fixture into one class:

   | Class | Rule |
   | --- | --- |
   | `batch` | Its inputs are a subset of the pin's inputs, and its `devenv.yaml` sets nothing else |
   | `alone` | It needs other inputs or settings. Copy it to a temporary project with its own `devenv.yaml` and evaluate it alone |
   | `secret` | It needs SecretSpec or other secrets |
   | `fails` | It does not evaluate at the pin; keep the error tail |

6. Compute truth for every `batch` and `alone` fixture. Compute it twice, and compare.

**Expected result.** Most devenv examples are `batch` or `alone`. Every `fails` entry has a reason.

**Record.** `evidence/step-7.md`: counts per source and class, the `fails` reasons, and the run
time.

**Gate GM4.** Every fixture has a class. Every `batch` and `alone` fixture has a stable truth.

---

## Step 8. The model generator

**Goal.** Generated Pydantic models for any subtree, stamped with the pin.

**Actions.**

1. Write `src/devenv_py/values.py` with the shared value types: `PkgRef`, `PathRef`,
   `NixExpr`, `Priority[T]`, `Lines`, and `JsonValue`. Each has a `to_tagged()` method that
   returns the tagged JSON form of Step 5.
2. Write `src/devenv_py/generator.py` with `dpy gen <subtree>`. It reads the export, selects
   options whose `loc` starts with the subtree, and maps each type tree with the concept's table.
   - Match parameterized names by prefix, such as `strMatching <pattern>`.
   - Read integer bounds by name for fixed types (`unsignedInt16`: 0 to 65535). For `intBetween`,
     read the bounds from the description through the fixed patterns that MDL-007 allows.
   - Generate a nested class for each submodule. Allow extra keys for a freeform submodule, with
     the freeform type.
   - Map any unknown name to `NixExpr` and add it to a coverage list (MDL-008).
   - Make every field optional with no value set (MDL-003). Put the option default and the
     description in the field description.
3. Write the module header:

   ```python
   # Generated by devenv-py. Do not edit.
   # pin: devenv-2.4.0-a73c5b84-c2f38fe7
   # export: sha256:<hash>
   # subtree: services.postgres
   ```

4. Write `dpy schema <subtree>`. It writes JSON Schema from the generated model.
5. Write the narrowing loader. It imports `narrowed/<subtree>.py` and checks that each class adds no
   field that the option tree lacks (MDL-009).
6. Write unit tests for each row of the type table, from small synthetic export entries. Write a
   golden test for `services.postgres`.
7. Write the drift check: `dpy drift <old-pin> <new-pin>`. It lists added, removed, and retyped
   options per subtree.

**Expected result.** `dpy gen languages.python` and `dpy gen services.postgres` write importable
modules. The coverage list names every `NixExpr` field.

**Record.** `evidence/step-8.md`: the coverage for both pilot subtrees and the census of unmapped
type names across the whole export.

**Gate GM5.** The type tests pass, the golden test passes, and both pilot modules import.

---

## Step 9. The `nix` output language in Templateer

**Goal.** Templateer renders Nix text with safe escaping and a parse check.

Make this change in the `templateer_v2` repository, in its own Gitman workspace, with its own
tests and release tag. The harness then pins that tag.

**Actions.**

1. In `models.py`, add `nix` to the language set. Put it in a new class: parsed, but not in
   `STRUCTURED_LANGUAGES`, because a module is a function and does not round-trip as data.
2. In `escaping.py`, add `escape_nix_string`. Nix double-quoted strings do not share JSON's escape
   grammar. Nix has no `\uXXXX` escape. Use these rules:

   | Character | Output |
   | --- | --- |
   | `\` | `\\` |
   | `"` | `\"` |
   | `${` | `\${` |
   | newline | `\n` |
   | carriage return | `\r` |
   | tab | `\t` |
   | U+0000 | raise `EscapeError`; a Nix string cannot hold it |
   | any other character | unchanged |

   Booleans render as `true` and `false`. A `None` value raises, as for other languages.
   Keep `nix` out of `_QUOTED_STRING_LANGUAGES`. The finalizer then passes strings unchanged, so it
   does not escape the Nix text that the `nix` filter returns. Every value must therefore go
   through the `nix` filter. Add an audit rule that flags an interpolation without it.
3. Add a `nix` filter for `nix` templates. It renders a tagged JSON value as a Nix expression:
   strings through `escape_nix_string`; numbers and booleans as literals; lists as `[ a b ]`;
   objects as `{ "key" = value; }` with every key quoted; `$pkg` as `pkgs.<attr>` and its output;
   `$path` as a relative path; `$nix` (from `NixExpr`) as its source in parentheses; `$priority` as
   `lib.mkDefault`, `lib.mkForce`, or `lib.mkOverride n`.
4. Add the built-in parse validator. Pipe the artifact into `nix-instantiate --parse -`. Confirm
   that `-` reads standard input on the pinned Nix before you rely on it.
5. Write an exhaustive escape test like `test_escape_string_round_trips_every_codepoint`. Put every
   codepoint in U+0001 to U+011F, plus U+2028, U+2029, U+FEFF, one astral character, and the text
   `${x}`, into one Nix list. Evaluate it once with `nix-instantiate --eval --strict --json -`.
   Compare the result with the input.
6. Write filter tests for each tagged form. Parse each output with the validator.

**Expected result.** The escape test passes in one Nix call. The filter output parses.

**Record.** `evidence/step-9.md`: the Templateer tag, the test counts, and the Nix version.

**Gate GM6.** The Templateer suite passes with the `nix` language, and the tag exists.

---

## Step 10. The writers

**Goal.** Turn a model instance into a module, by Path N and by Path T.

**Actions.**

1. Write `templates/devenv-module/` for Templateer. `metadata.yml` declares `language: nix`. The
   schema is a generic `ModuleContribution`: a `head` with the function arguments, and a list of
   `(loc, value)` pairs in tagged JSON. The template renders:

   ```nix
   { pkgs, lib, ... }:
   {
     {% for d in definitions %}
     {{ d.loc | join(".") }} = {{ d.value | nix }};
     {% endfor %}
   }
   ```

   Quote any `loc` segment that is not a plain Nix identifier. Add that rule to the `nix` filter
   tests.
2. Write `src/devenv_py/writer_nix.py`. It takes a model, or a normalized truth, and produces
   the `ModuleContribution`. It renders through Templateer's Python interface. An option without a
   model uses the generic tagged value. A `$fn` value makes the fixture `has-fn`; RT2 skips it with
   that reason.
3. Write `reader-module/default.nix` for Path T:

   ```nix
   # reader-module/default.nix: set options from contribution.toml beside this file.
   { pkgs, lib, ... }:
   let
     data = builtins.fromTOML (builtins.readFile ./contribution.toml);
     decode = v:
       if builtins.isAttrs v && v ? "$pkg" then
         let p = lib.getAttrFromPath (lib.splitString "." v."$pkg") pkgs;
         in if (v."$output" or "out") == "out" then p else p.${v."$output"}
       else if builtins.isAttrs v && v ? "$path" then ./. + "/${lib.removePrefix "./" v."$path"}"
       else if builtins.isAttrs v then lib.mapAttrs (_: decode) v
       else if builtins.isList v then map decode v
       else v;
   in decode data
   ```

   Path T does not carry `$nix` or `$priority`. A model with those values uses Path N only.
4. Write `src/devenv_py/writer_toml.py`. It writes the nested option tree as TOML with
   `tomli-w`, beside a copy of the reader module.
5. Test both writers on the five golden fixtures. Evaluate the output. Compare its truth with the
   golden truth.

**Expected result.** Both writers reproduce the golden truths, except where a golden fixture holds a
value that its path cannot carry.

**Record.** `evidence/step-10.md`: the results per fixture and per path.

**Gate GM7 (part 1).** Both writers pass on the golden fixtures within their stated limits.

---

## Step 11. The readers

**Goal.** Turn truth or source text into a model instance.

**Actions.**

1. Write `src/devenv_py/read_eval.py`. It takes a normalized truth and validates the subtree
   with the generated or narrowed model.
   - Resolve each `$pkg` to an attribute path. Try the candidates `pname` and
     `pname.<output>` in one batch evaluation, and keep the one whose `outPath` matches. Record an
     ambiguous or missing result as a miss (concept open question 3).
2. Write `src/devenv_py/read_syntax.py` with pydantree. Load the grammar from
   `tree_sitter_nix` and the vendored `node-schema.json`, as in pydantree's `devenv-extract`
   example. Read node kinds from the vendored schema. Do not trust the names in this guide.
   - Accept a function head such as `{ pkgs, lib, ... }:` and read its body.
   - Read `binding` nodes. Expand dotted attribute paths and nested attribute sets into one tree.
   - Read literals: strings without interpolation, integers, floats, `true`, `false`, `null`, and
     lists and attribute sets of literals.
   - Read `pkgs.x.y` as `PkgRef`. Read `with pkgs; [ a b ]` as a list of `PkgRef`.
   - Read `lib.mkDefault v`, `lib.mkForce v`, and `lib.mkOverride n v` as `Priority`.
   - Keep every other value as `NixExpr` with its exact source span (MDL-010). This includes
     `lib.mkIf`, interpolated strings, and function calls.
   - If the body is a `let ... in` expression, keep the whole body as one `NixExpr` in this version.
3. Test the syntax reader on the five golden fixtures. Assert the literal fields and the `NixExpr`
   spans.

**Expected result.** Both readers produce valid instances for the golden fixtures.

**Record.** `evidence/step-11.md`: the node kinds that the pinned grammar uses, and the number of
`NixExpr` values per golden fixture.

**Gate GM7.** Both readers pass their tests.

---

## Step 12. The round-trip runner: RT1 to RT6

**Goal.** One command runs the corpus checks and writes results.

**Actions.**

1. Write `src/devenv_py/roundtrip.py` with `dpy rt --subtree <s> --checks RT1,...`. For each
   `batch` or `alone` fixture:

   | Check | Steps |
   | --- | --- |
   | RT1 | Validate truth with `read_eval`. Count `NixExpr` fields in the subtree. |
   | RT2 | Render the full truth with `writer_nix`. Evaluate. Compare with truth. |
   | RT3 | Read the source with `read_syntax`. Render with `writer_nix`. Evaluate. Compare with truth. |
   | RT4 | Compare each literal field of the syntax reader's instance with the eval reader's field. |
   | RT5 | Render, read with `read_syntax`, render again. Compare the two texts. |
   | RT6 | For a data-only instance: write TOML with `writer_toml`. Evaluate. Compare with truth. |

2. Evaluate every rendered candidate of one run in one batch (Step 3).
3. Write each case result as one JSON line under `~/.local/state/devenv-py/rt/<run-id>/`:
   fixture, subtree, check, status (`pass`, `fail`, `skip`), reason, and differences.

**Expected result.** RT2 passes on most `batch` fixtures before any narrowing, because it renders
the truth back as data. Its failures show writer and serializer gaps.

**Record.** `evidence/step-12.md`: pass counts per check for the pilot subtrees.

**Gate GM8 (part 1).** The runner produces results for every fixture and check, with no crash.

---

## Step 13. Generated cases: RT7 and RT8

**Goal.** Test the type mapping itself with many generated instances.

**Actions.**

1. Write `src/devenv_py/generate_cases.py`. Build Hypothesis strategies from each generated
   model. Use custom strategies for the value types:
   - `PkgRef` from a short vetted list of attribute paths that evaluate at the pin.
   - `PathRef` from files that the case creates in its candidate directory.
   - `Lines` from short strings, including `${`, quotes, and newlines.
   - Integers inside their bounds, with the bounds themselves included.
2. RT7: for each instance, render with `writer_nix`, evaluate in a batch, and compare the truth with
   the instance's tagged form. Classify each failure:

   | Class | Meaning | Action |
   | --- | --- | --- |
   | `type-error` | Nix rejected a value that Pydantic accepted | The model is too loose; fix the generator or narrow the model |
   | `assertion` | A module assertion failed, such as a version that needs an input | A cross-field rule; add a validator to the narrowed model |
   | `mismatch` | Nix accepted, but the truth differs | A writer or serializer error |

3. RT8: take a valid instance. Change one field to a value outside its type: a wrong type, an
   integer outside its bounds, or an unknown enum value. Build it with `model_construct` so that
   Pydantic does not stop it. Render and evaluate. Nix must reject it with a type error. If Nix
   accepts it, the model is too tight.
4. Use a fixed Hypothesis seed per run. Record the seed. Cap the cases per subtree with an argument.

**Expected result.** RT7 finds the cross-field rules of each pilot subtree. RT8 finds no
too-tight field.

**Record.** `evidence/step-13.md`: the seed, the case counts, each failure class with examples, and
the time per case.

**Gate GM8.** RT7 and RT8 run, and each failure has a class.

---

## Step 14. The report and the Testee checks

**Goal.** One readable report per run. The normal gate runs the fast checks.

**Actions.**

1. Write `src/devenv_py/report.py` with `dpy report <run-id>`. It writes Markdown and JSON with:
   - a table per subtree: options, mapped options, `NixExpr` misses, fixtures, and pass counts for
     RT1 to RT8,
   - each failure: fixture, check, class, the first differences, and the log path,
   - the pin and the export hash.
2. Add Testee checks to `devenv.nix`, in the form that Vendomat uses:

   | Check | Profiles | Runs |
   | --- | --- | --- |
   | `ruff`, `ruff-format`, `ty` | quick, full | static checks |
   | `unit` | full | pytest without the `nix` marker |
   | `harness-smoke` | full | the driver, the five golden fixtures, and both writers |
   | `rt-pilot` | `rt` (opt-in) | RT1 to RT8 for the pilot subtrees |

**Expected result.** `testee verify --full` passes. `testee check rt-pilot` writes a report.

**Record.** `evidence/step-14.md`: the Testee run identifiers and the first report.

**Gate.** `testee verify --full` passes.

---

## Step 15. The pilot: `languages.python` and `services.postgres`

**Goal.** Two subtrees reach supported status (MDL-011).

**Actions.**

1. Run `dpy rt` with all checks for both subtrees. Read the report.
2. Fix each failure in the right place:
   - Generator, writer, serializer, or normalizer errors: fix the code, with a unit test.
   - Cross-field rules from RT7: add validators in `narrowed/<subtree>.py`.
   - Syntax reader gaps: add a node rule, or accept the `NixExpr` and count it.
3. Run again until the thresholds hold.

**Thresholds** (owner decision, 2026-10-11; concept open question 5). The thresholds fall into
four groups.

*Correctness. Any failure blocks the gate.*

| Check | Threshold |
| --- | --- |
| RT2, RT3, RT4, RT5, RT6 | 100 percent of eligible cases |
| Exclusions | Only by a named class: `has-fn`, `fails`, or `secret`. The report lists each excluded fixture. |
| RT7 | No `type-error` and no `mismatch`. An `assertion` failure counts only after it becomes a validator in the narrowed model, so the rerun has none. |
| RT8 | No invalid value that Nix accepts |
| Truth stability | Two runs give byte-identical truth |

*Coverage. Measure it; after the gate, it must not fall.*

| Check | Threshold |
| --- | --- |
| RT1 | 100 percent of fixtures validate. The pilot models have no `NixExpr` field, except for options whose type is a function. The record lists each one. |
| RT3 | At least 90 percent of the pilot-subtree bindings in the corpus are typed fields. The rest are `NixExpr` values. |

*Generated cases. Size them by coverage, not by count.*

| Check | Threshold |
| --- | --- |
| RT7 | Every field is set in at least 20 cases. Every enum value, and both ends of every integer bound, occur at least once. At least 500 cases per subtree. Run under two seeds. |
| RT8 | One case per field for each mutation that applies to it: wrong type, out of bounds, unknown enum value, and null where null is not allowed. Enumerate the cases; do not sample them. |

*Corpus and time.*

| Check | Threshold |
| --- | --- |
| Corpus size | At least 10 real fixtures that use `languages.python`, and at least 5 that use `services.postgres` |
| Exclusion share | At most 20 percent of those fixtures are excluded |
| Small corpus | If the corpus is below these sizes, record GM9 as BLOCKED, not passed |
| Run time | `testee check rt-pilot` finishes in 15 minutes or less with a warm evaluation cache |

**Record.** `evidence/step-15.md`: the final report, both seeds, the RT7 coverage counts, the
excluded fixtures, and every remaining `NixExpr` field.

**Gate GM9.** Both subtrees meet every threshold above.

---

## Step 16. The agent skills

**Goal.** Agents run the authoring loop without changes to the harness code.

**Actions.**

1. Write `.agents/skills/devenv-py-harvest/SKILL.md`. Inputs: a source. Steps: `dpy harvest`,
   triage, `dpy truth` twice. Done when every fixture has a class and a stable truth.
2. Write `.agents/skills/devenv-py-author/SKILL.md`. Inputs: a subtree. Steps: `dpy gen`, read the
   coverage list and the fixtures, write `narrowed/<subtree>.py`, add syntax reader rules if needed,
   run `dpy rt`. Done when GM9's thresholds hold for the subtree. Point to the
   `copyroom-template-edit` skill for template changes.
3. Write `.agents/skills/devenv-py-roundtrip/SKILL.md`. Inputs: a report. Steps: pick one
   failure, find its class, fix it in the right place, rerun the failing case and then the subtree.
   Done when the case passes and no other case fails.
4. Put these rules in all three skills (MDL-005):
   - Do not edit `nix/`, `normalize.py`, `compare.py`, or `driver.py`. Report a suspected harness
     error to the owner instead.
   - Do not change a golden fixture or a truth file to make a check pass.
   - Record each run in the subtree's record.
5. Trial: give an agent the author skill for `services.redis`. Do not help it. Record the run.

**Expected result.** The agent brings `services.redis` to the thresholds with no harness code
change.

**Record.** `evidence/step-16.md`: the agent's run, its changes, the report, and any harness change
it asked for.

**Gate GM10.** The trial subtree passes with no harness code change.

---

## After the gates

- Choose the next subtrees from the fleet census: the options that the fleet fixtures set most.
- Generate JSON Schema for `vendomat.toml` and wire it into the V6 workspace template.
- Repeat Steps 4 to 15 for the NixOS and Home Manager option trees, for Machines.
- Start the Basix curated layer as Nix modules, and run them through the same harness.

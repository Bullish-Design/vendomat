# Guide: the round-trip harness for typed devenv models

**Date:** 2026-10-10. **Updated:** 2026-10-11 with the findings of phase A and Steps 1 and 9.
**Status:** Draft for owner review. **Concept:** [CONCEPT.md](./CONCEPT.md).

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
  carries the pin identifier. The first pin is `devenv-2.4.0-b904dcb5-c2f38fe7`. Read each revision
  through `nodes.root.inputs` in `devenv.lock`: the root `nixpkgs` points at the node `nixpkgs_2`.
- **Step states.** Phase A proved prototypes outside the repository
  ([evidence/phase-a.md](./evidence/phase-a.md)). A step marked "prototype proved, in-repo port in
  progress" passes its gate only after the code and tests live in `devenv-py`.

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
    touched.nix                              option paths that a fixture mentions
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

**Gate GM0.** Passed for the probe pin. It must pass again for the pin that Step 1 selects. Phase A
used that pin (`b904dcb5`) and the surfaces worked, but nobody reran the probe commands one by one.
See [evidence/phase-a.md](./evidence/phase-a.md), section 7. Record GM0 as passed only after that rerun.

---

## Step 1. Create the repository, the toolchain, and the first pin

**Goal.** A repository with a working shell and one base project per pin.

**Status.** Done on 2026-10-11. See [evidence/step-1.md](./evidence/step-1.md). The repository is
`~/Documents/Projects/devenv-py`, with the private GitHub copy `Bullish-Design/devenv-py`.

**Facts the later steps rely on.**

- The first pin is `devenv-2.4.0-b904dcb5-c2f38fe7`. The `devenv` input is `b904dcb5…`, the
  `nixpkgs` input is `c2f38fe7…`, and `nixpkgs-python` is `5821ac52…`. Full revisions are in the
  record.
- The `devenv.lock` root maps `nixpkgs` to the node `nixpkgs_2`. A node named `nixpkgs` exists with
  another revision. `pin.py` must follow `nodes.root.inputs` to find each input. It must not look up a
  node by its name.
- The shell Python is 3.14.7. The repository sets no Python version pin. The dependencies import in
  that version.
- Dependencies come from HTTPS git tags, except `tree-sitter-nix`:

  | Dependency | Source |
  | --- | --- |
  | `pydantree-sitter` | tag `v0.4.0`, subdirectory `src/pydantree_sitter` |
  | `templateer` | tag `v0.4.2`. The tag is on the `v6-flake` branch of `templateer_v2`, not on `main`. Step 9 landed on `main`; a new tag must follow. |
  | `loci-core` | tag `v0.4.5`, with `mancore` `v0.1.0` source |
  | `tree-sitter-nix` | PyPI `0.1.0`, wheel `cp310-abi3` |

- Testee is `v0.5.1`. The pytest check appends the host `PATH`.
- The host profile lacks `repoman` and `copyroom`. `devenv.nix` pins the CLIs `repoman` `v0.13.0` and
  `copyroom` `v0.8.1` in `packages`.
- `copyroom new` with `template-py` does not work under copyroom `0.8.x`. The repository was built by
  hand, with `talkee` and `agentman` as models.

**Actions (as done).**

1. Create the repository. Use Gitman workspaces for every later change.
2. Write `devenv.nix` with uv, Nix tools (`nix-instantiate`), the pinned CLIs above, and the Testee
   module. Set no Python version.
3. Write `pyproject.toml` with `pydantic`, `hypothesis`, `tomli-w`, `pydantree-sitter`, `tree-sitter`,
   `tree-sitter-nix`, and `templateer`. Use the pins in the table above. Use the `devenv-extract`
   pattern from pydantree for the Nix grammar. Phase A found that the pydantree shell does not start
   under devenv 2.4.0, so load the grammar from the project venv (Step 11).
4. Create the first base project at `pins/<pin-id>/`. `devenv.nix` is `{ imports = [ ../../nix/introspect.nix ]; }`
   once Step 2 lands. `devenv.yaml` pins `devenv`, `nixpkgs` (`github:cachix/devenv-nixpkgs/rolling`),
   and `nixpkgs-python` (which follows `nixpkgs`):

   ```yaml
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
   id = "devenv-2.4.0-b904dcb5-c2f38fe7"
   cli = "2.4.0+b904dcb"
   devenv_rev = "b904dcb51fe48c30db250038241507f60752f222"
   nixpkgs_rev = "c2f38fe7f9e04d9aadd354d380f2bd40531d9737"
   inputs = ["devenv", "nixpkgs", "nixpkgs-python"]
   ```

7. Write `src/devenv_py/pin.py`. It reads `pin.toml`, checks it against `devenv.lock` (through
   `nodes.root.inputs`) and `devenv --version`, and fails on any difference.

**Expected result.** `devenv shell -- python -c "import pydantree_sitter, templateer, tree_sitter_nix"`
exits 0. `pin.py` accepts the pin.

**Record.** [evidence/step-1.md](./evidence/step-1.md): the tag of each dependency, the pin, and the
commands. Testee run `20261011T044545Z-8570615c953a` passed.

**Gate.** The shell imports all three libraries, and the pin check passes. Met.

---

## Step 2. The evaluation driver

**Goal.** One Python function sends a request to stock `devenv eval` and returns parsed JSON.

**Status.** Prototype proved, in-repo port in progress. See
[evidence/phase-a.md](./evidence/phase-a.md), sections 1 and 2. The two prototypes of
`introspect.nix` differ (the options prototype returns a JSON string, the oracle prototype returns
an attribute set). The port merges them under the rules below.

The base project imports an introspection module. The module takes the module arguments as
`@moduleArgs`. It reads a request file and puts its answer in a read-only config value. `devenv eval`
reads that value like any other config attribute (probe O10 to O12). No fork patch and no repl are
needed.

**Interface of `nix/introspect.nix`.** The repository file is the authority once ported. The
prototypes are in `~/.local/state/devenv-py/phase-a/options/introspect.nix` and
`~/.local/state/devenv-py/phase-a/oracle/base/nix/introspect.nix`.

- Arguments: `{ lib, pkgs, options, extendModules, config, ... }@moduleArgs`. The oracle needs
  `moduleArgs` (Step 5).
- Option `introspect.request`: `nullOr path`, default `null`.
- Option `introspect.result`: read-only. Its value is **a JSON string for every request kind**.
  `devenv eval` fails with `Failed to get attribute 'mcp.devenv.sh'` when the result holds an
  attribute name with a dot. A string hides the names. A key such as `d.e` in the `echo` payload
  fails the same way if the result is not a string.
- Option `introspect.optionsDoc`: read-only package. It is `nixosOptionsDoc` over the option tree
  without `introspect`, with `warningsAreErrors = false`. The default `true` fails on a synthetic
  option that has no description.
- Request kinds: `echo` (returns `payload`), `options` (field `maxDepth`; Step 4), and `truth`
  (field `candidates`; Step 5). Any other kind throws `unknown request kind: <kind>`.
- The module passes `normalize` to the export: `config.devenv.root` becomes `<root>` and
  `config.devenv.runtime` becomes `<runtime>` (Step 4).
- The harness never reports on `introspect` itself: it removes that attribute from the option sets.

**Actions.**

1. Write `nix/introspect.nix` to the interface above.
2. Make the base project import it: `pins/<pin-id>/devenv.nix` is
   `{ imports = [ ../../nix/introspect.nix ]; }`.
3. Write `src/devenv_py/driver.py`. The function below shows the required behavior:

   ```python
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
           stdin=subprocess.DEVNULL,
           env={**os.environ, "NO_COLOR": "1"},
       )
       (run_dir / "eval.stdout").write_text(proc.stdout)
       (run_dir / "eval.stderr").write_text(proc.stderr)
       if proc.returncode != 0:
           raise DriverError(proc.stderr[-4000:])
       # Decode twice: devenv prints {"introspect.result": "<json string>"}.
       return json.loads(json.loads(proc.stdout)["introspect.result"])
   ```

   `DriverError` carries the tail of the error output. `run_dir` is
   `~/.local/state/devenv-py/runs/<timestamp>-<kind>/`.
4. Write `tests/test_driver.py`. Send an `echo` request with a payload that holds a double quote, a
   backslash, a newline, `${`, a non-ASCII character, and a nested list. Assert that the result
   equals the payload.
5. Add a dotted-key echo test. Send a payload with the keys `d.e` and `mcp.devenv.sh`. Assert that
   the result equals the payload. This test fails if the result stops being a JSON string.
6. Send an unknown request kind. Assert that `DriverError` holds the text `unknown request kind`.
7. Test the cache. Send two different requests through the same file path. Assert two different
   results (probe O12 saw this once). Keep `cache=False` as the switch if it ever fails. Phase A saw
   that a new request path gave a cold run and a repeat gave a warm run; the cause is not isolated
   (inference I5).

**Expected result.** The echo tests pass, and the cache test gives two different results.
Phase A times: echo with no cache 0.30 to 0.32 s, echo with a cache hit 0.06 s, unknown kind 0.33 s
with exit 1.

**Fallback.** If a later pin breaks this route, use `devenv repl`. Pipe
`:p import <nix-dir>/entry.nix { inherit devenv; requestFile = <file>; }` on standard input. Let the
entry wrap `builtins.toJSON` of the answer in fixed sentinel strings, and parse the text between
them (probe O4). Use `devenv.project.options` and `devenv.project.extendModules` in place of the
module arguments.

**Record.** `evidence/step-2.md`: the echo payloads, the cache result, and the wall time of one
request with and without the cache.

**Gate GM1 (part 1).** The echo, dotted-key, and cache tests pass on the pin.

---

## Step 3. Batch evaluation and bisection

**Goal.** Evaluate many candidate modules in one `devenv eval` call. Find the bad one when a batch
fails.

**Status.** Prototype proved for the oracle batch, in-repo port in progress. The driver experiment
has no report yet. TODO: add the driver facts (bisection log, timing table for 1, 10, 50, and 200
candidates) from `~/.local/state/devenv-py/phase-a/driver/REPORT.md` when it exists. Until then, the
actions below stay as the plan.

**Facts from phase A** ([evidence/phase-a.md](./evidence/phase-a.md), section 2).

- A `truth` request with five candidates costs 1.5 to 1.7 s, about the slowest single call. The
  fixed start is about 0.3 s.
- A candidate module given as an absolute path outside the base project is readable under pure
  evaluation. Its path stays absolute in `definitionsWithLocations`. No copy is needed (action 3).
- An undeclared option in a candidate (`foo.bar = 1`) makes the module check fail and aborts the
  whole call. Bisection handles it.

**Actions.**

1. Use the Step 5 oracle with `scope = "touched"` as the batch workload. (The phase-A driver
   experiment used its own temporary oracle.)
2. Write three candidate modules under a temporary directory. Each one sets a different
   `env.MARK` value. Send one `truth` request with all three. Assert three different results.
3. Confirm again, in the port, that a module given as an absolute path keeps its path and that pure
   evaluation reads candidate files outside the base project. If it does not, let the driver copy
   each batch into `pins/<pin-id>/.candidates/<batch-id>/`.
4. Write `driver.run_batch(candidates)`. On `DriverError`, split the batch in two halves and retry
   each half. A single candidate that still fails gets the status `eval-error` and keeps its error
   tail (MDL-013).
5. Write a test with five good candidates and one candidate that sets
   `env.MARK = builtins.abort "dm-bisect";`. `tryEval` does not catch `abort`, so the whole batch
   fails. Assert five results and one `eval-error` whose tail holds `dm-bisect`. Add a second bad
   candidate that sets an undeclared option.
6. Measure wall time for batches of 1, 10, 50, and 200 candidates that each enable one service.

**Expected result.** Batch evaluation works. Bisection isolates the bad candidate. The time per
candidate falls as the batch grows.

**Record.** `evidence/step-3.md`: the timing table, the bisection log, and the answer to action 3.
The phase-A record line for this step is a TODO until the driver report exists.

**Gate GM1.** Batch and bisection tests pass. The timing table exists.

---

## Step 4. The options export

**Goal.** A complete, structured JSON export of the option tree for the pin.

**Status.** Prototype proved, in-repo port in progress. The first draft failed in eleven places. The
proven exporter replaces the draft. Evidence: [evidence/phase-a.md](./evidence/phase-a.md), section 1.

**The exporter.** The repository file `nix/options.nix` is the authority once ported. The prototype is
`~/.local/state/devenv-py/phase-a/options/options.nix`. Its arguments are `options` (the tree without
`introspect`), `maxDepth`, and `normalize` (a list of `{ from; to; }` replacements). The result is a
list of option records, one per option outside any submodule. Sub-options appear inside
`type.options`. Rules the port keeps:

- **Type nodes.** Each node holds `name`, `description`, `payload`, `nested`, `options`, and
  `depthCut`. A hand-written walk converts payloads: a type becomes `{"$type": name}`, a function
  `{"$fn": true}`, a derivation `{"$pkg": name}`, and a path `{"$path": ...}`. The payload keys
  `modules`, `staticModules`, and `specialArgs` are dropped. `builtins.toJSON` on a payload fails and
  `tryEval` does not catch the failure.
- **Locations.** `loc` is a list. A `listOf` submodule adds `*`. An `attrsOf` submodule adds the
  placeholder from `functor.payload.placeholder`. A `functionTo` adds `<function body>`.
  Elements of `loc` can hold dots.
- **Freeform.** `getSubOptions` adds `_freeformOptions`. The exporter removes it. Freeform options
  stay under `nested.freeformType`.
- **Depth.** `maxDepth` defaults to 8. The deepest chain at the pin has 5 submodule levels. A cut
  node sets `depthCut: true`. The driver must fail the export when any node has `depthCut`.
- **Recursive types.** JSON, YAML, and TOML value types expand without end. A node whose
  `description` repeats an ancestor's becomes `{name, description, recursive: true}`. A safety limit
  of 12 sets `truncated: true`. It did not fire at the pin.
- **Defaults.** A default can be a function, a derivation, or a `throw`. A `safe` walk guards it. A
  failure gives `default: null, defaultError: true`. An option that has `defaultText` skips
  `default` and sets `defaultSkipped: true` (226 options at the pin). This keeps the export out of
  the project directory and keeps the evaluation cache usable.
- **Text.** `description` and `defaultText` pass through `text`: a string, `literalExpression`,
  `literalMD`, or null. `lib.mdDoc` no longer exists.
- **Normalization.** `/nix/store/<32 characters>-` becomes `<store>/`. The project root becomes
  `<root>`. The runtime directory becomes `<runtime>`. Without this the hash depends on the checkout.
- **Record fields.** `loc`, `type`, `hasDefault`, `default`, `defaultError`, `defaultSkipped`,
  `defaultText`, `description`, `readOnly`, `internal`, `visible` (raw), and `declarations`.
- **Markers.** `recursive`, `truncated`, `depthCut` (on type nodes). `defaultSkipped` and
  `defaultError` (on options).

**Actions.**

1. Port `nix/options.nix` and the `options` request kind of `nix/introspect.nix`.
2. Write `src/devenv_py/options.py` with `dpy export`. It sends an `options` request with
   `maxDepth = 8`, fails when any node has `depthCut`, adds the pin, adds a SHA-256 of the canonical
   JSON, and writes `exports/<pin-id>/options.json`. Canonical form:
   `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
3. Write the completeness check. Run `devenv build introspect.optionsDoc` and read
   `share/doc/nixos/options.json`. Take its keys. Take the joined `loc` of every exported option
   that the **doc rule** lists, including sub-options. The two sets must be equal. Map names as
   `optionsJSON` does: `<name>` for an attribute-set element and `*` for a list element.

   **The doc rule** (from `optionAttrSetToDocList'`). List an option when `visible` is `true` or
   `"shallow"` and it is not `internal`. Walk its sub-options only when `visible` is `true` or
   `"transparent"`. `internal` does not stop the walk. The naive rule "visible and not internal" lists
   1199 options at the pin and fails by 55: each has a hidden ancestor. Test the rule on a synthetic
   module that uses every `visible` form.
4. Write a type census: count options per `type.name`, including nested names. Record each name that
   carries a payload in the name, such as `strMatching "<pattern>"`.
5. Spot-check by hand: `services.postgres.port` (`unsignedInt16`, default 5432), `packages` (`listOf`
   of `package`, default `[]`), `env` (freeform `submodule`: `nested.freeformType` is
   `lazyAttrsOf anything`, own options empty, default `{}`), `languages.python.version` (`nullOr
   str`, default null), `scripts` and `tasks` (`attrsOf submodule`).
6. Check `enum` payloads. At the pin the payload is `{ values = [...]; }`, not a bare list.
7. Hash stability: call the export four times (two with `--no-eval-cache`, one with
   `--refresh-eval-cache`, one cache hit) and once from another directory. All hashes must match.

**Expected result at the pin.** `optionsDoc` lists 1144 keys under 45 top-level names. The export
holds 1330 records, 845 of them outside any submodule. The doc rule gives 1144 with 0 differences.
The type census has 26 distinct names (see the record). The canonical export is 833,807 bytes with
SHA-256 `a1126c7d…7fc4e` (full value in the record). Time: about 4 s uncached, 0.11 s on a cache
hit. These are values for one pin. The test asserts the equalities, not the byte count.

**Known limits.** A future default that fails with `abort` or a type error breaks the whole export,
and bisection cannot help. The `recursive` rule keys on descriptions, so two different types with one
description would be cut wrongly. The `attrTag` branch is untested.

**Record.** `evidence/step-4.md`: the export hash, the census, the completeness result, the enum
payload form, and the timings. The prototype values are in `evidence/phase-a.md`.

**Gate GM2.** The export is complete, or each gap is named. The hash is stable over repeated runs.
The export has no `depthCut`.

---

## Step 5. The oracle and the serializer

**Goal.** Truth: the definitions that a fixture's files give to each option, as tagged JSON.

**Status.** Prototype proved, in-repo port in progress. The first draft aborted on some fixtures.
Evidence: [evidence/phase-a.md](./evidence/phase-a.md), section 2.

**Why the draft failed, and the scope rule.** `definitionsWithLocations` forces each definition that
survives the priority filter to weak head normal form. When no fixture file defines an option, its
default survives, and the call forces the default. A default that throws is catchable. A default or
`mkDefault` value with a type error aborts the whole evaluation, and `tryEval` does not catch it.
Phase A saw this: devenv's own default for `process.manager.command` coerces `null` to a string
when the fixture has no processes. The full walk therefore cannot be safe for every fixture.

The oracle now queries **only the options that the fixture files mention** (`scope = "touched"`, the
default). `scope = "all"` walks every option and takes a `deny` list. It is the cross-check, not the
normal mode. Touched scope also cuts time: 0.3 to 1.7 s, against 4.5 to 8.5 s for the full walk.

**The files.** The repository files are the authority once ported. The prototypes are in
`~/.local/state/devenv-py/phase-a/oracle/base/nix/`.

- `nix/touched.nix`. It loads each fixture module, and the `imports` that lie under `roots`, with the
  module arguments. It walks the module `config` text and stops at the first declared option. It
  ignores `mkIf` conditions, so the set is a superset. It reads no option value and no default. It
  handles `config =` form, shorthand form, `mkMerge`, `mkIf`, `mkOverride`, inline attribute sets,
  and function imports. Untested forms: `disabledModules`, a `specialArgs`-only argument, `imports`
  of a non-path key. Use `scope = "all"` as the cross-check for them.
- `nix/oracle.nix`. For each option path, it keeps the definitions whose `file` lies under a root.
  On a catchable error it compares with the base option set: if the base option throws too, it
  returns no entry (a throwing default means no fixture definition); otherwise it returns
  `error = "definition-throws"`. The `error` field is a string. A definition that throws on an
  option whose default also throws is dropped silently. The `undeclared` entry is unreachable,
  because an undeclared option aborts the call earlier (Step 3).
- `nix/serialize.nix`. It writes the tagged forms below.

**Request.** `{"kind": "truth", "candidates": {"<label>": {"modules": ["/abs/devenv.nix"],
"roots": ["/abs/source/"], "scope": "touched", "deny": []}}}`. `scope` and `deny` are optional.
**Every `roots` entry ends in `/`.** Without it `.../source` also matches `.../source-other`.

**Tagged forms.**

| Nix value | Serialized form |
| --- | --- |
| Derivation | `{"$pkg": pname, "$name": name, "$output": outputName}` |
| Path | `{"$path": "<absolute path>"}`; a path inside a string is copied to the store at once |
| Function | `{"$fn": true}` |
| Attribute set with `_type` | `{"$type": "<_type>"}`, except `merge` |
| `mkMerge` inside a value | `{"$merge": [...]}` |
| A `throw` or `assert` failure | `{"$error": "throw or assert"}`: a fixed marker with no message |
| Depth over 64 | `{"$deep": true}` |

`definitionsWithLocations` strips property wrappers only at the top of a definition. Inside a
freeform `env` or an `attrsOf submodule` they stay. The serializer therefore peels them inside
attribute sets and lists: a false `mkIf` drops the element; a true `mkIf`, `mkOverride`, and
`mkOrder` keep the content. A wrapper never reaches the output.

**Actions.**

1. Port `nix/serialize.nix`, `nix/touched.nix`, and `nix/oracle.nix`. Extend `nix/introspect.nix`
   with the `truth` kind, `@moduleArgs`, and the candidate keys `scope` and `deny` (Step 2).
2. Write `src/devenv_py/truth.py` with `dpy truth <fixture>...`. It builds a batch request. Each
   candidate's `modules` is the fixture's `source/devenv.nix`. Its `roots` is the fixture's
   `source/` directory with a trailing `/`.
3. Write five golden fixtures under `tests/golden/`. Each has `source/`, a hand-written
   `expected.json`, and the raw and normalized truth. The prototypes are in
   `~/.local/state/devenv-py/phase-a/oracle/fixtures/`.

   | Fixture | Content |
   | --- | --- |
   | `a-probe` | python enable, `env.GREETING`, `packages = [ pkgs.jq ]`, postgres enable, `enterShell` |
   | `b-scripts-tasks` | `scripts.hello`, `scripts.greet` (multi-line `exec`, description), `tasks."app:build"`, `tasks."app:test"` |
   | `c-imports` | `imports = [ ./extra.nix ]`; `env`, `packages`, `enterShell` set in both files |
   | `d-priority` | `mkForce`, `mkDefault`, `mkIf false`, `mkIf true`; a second file `loser.nix` with plain definitions |
   | `e-paths` | `env.DATA_FILE = ./data.txt`; `"${pkgs.jq}/bin/jq"`; a plain string; `scripts.show.exec = "cat ${./data.txt}"` |

   Do not put `env.<name> = mkIf false ...` in a fixture. Devenv rejects it: reading `config.env`
   throws `The option env.GATED was accessed but has no value defined`. Use `scripts.<name> = mkIf
   false {...}` instead.
4. Compare with wildcards in the expected strings: `{FIXTURE}` for the fixture directory, `<hash>`
   for 32 store-hash characters, `<version>` for a version. `file` compares relative to `source/`.
5. Run each golden fixture twice, and the batch of five. Compare the runs byte for byte, with and
   without the evaluation cache.
6. Run each golden fixture with `scope = "all"` and the deny list `["process.manager.command"]`.
   The result must equal the touched scope.

**Expected result.**

- `a-probe` gives this table before normalization:

  | `loc` | `defs[].value` |
  | --- | --- |
  | `languages.python.enable` | `true` |
  | `env` | `{"GREETING": "hi"}` |
  | `packages` | `[{"$pkg": "jq", "$name": "jq-1.8.2", "$output": "bin"}]` |
  | `services.postgres.enable` | `true` |
  | `enterShell` | `"echo hi"` |

- A `mkIf false` definition is absent. `mkForce` and `mkDefault` values appear without their
  priority (concept: Truth), at the top and inside freeform values.
- **Loser rule.** A definition that loses on priority is absent. In `d-priority`,
  `services.postgres.enable = mkForce true` beats plain `false` in `loser.nix`; the truth is `true`
  from `devenv.nix`. `services.postgres.port = mkDefault 5433` loses to plain `5434` in `loser.nix`;
  the truth is `5434` from `loser.nix`.
- **Nested wrapper rule.** `env.FORCED = mkForce "forced"` and `env.DEFAULTED = mkDefault "defaulted"`
  give the value `{"FORCED": "forced", "DEFAULTED": "defaulted"}`.
- **Empty value.** `scripts.gated = mkIf false {...}` gives `scripts` the value `{}`. The option has
  a definition with no element.
- **Imports.** `c-imports` gives two definitions each for `enterShell`, `env`, and `packages`, with
  `extra.nix` first.
- **Error.** An option that fails on a catchable error gives a record with an `error` string, not a
  value. Normalization makes it `{"$error": <string>}`.
- Two runs are byte-identical, with and without the cache. The batch of five costs about as much as
  the slowest single call (1.5 to 1.7 s).

**Limits.** The oracle does not force `config`, so it cannot tell whether a fixture evaluates. The
`env.GATED` fixture produced a truth although devenv rejects it. Step 7 needs its own validity check
for the `fails` class. The oracle cannot see priority between two definitions inside one freeform
attribute set (inference I6, untested).

**Record.** `evidence/step-5.md`: the five truths, the run times, the touched-against-all comparison,
and each observed difference from the golden values with its cause. Phase A found four causes:
absolute `file` paths, store hashes in e, `$path` absolute in e, and `$name` versions in c.

**Gate GM3 (part 1).** All five golden fixtures match, touched scope equals `scope = "all"` with the
deny list, and truth is stable.

---

## Step 6. The normalizer and the comparison

**Goal.** Compare truths without false differences from store hashes, paths, or definition counts.

**Status.** Prototype proved, in-repo port in progress. The prototype is
`~/.local/state/devenv-py/phase-a/oracle/normalize.py` with `test_normalize.py` and `twin_test.py`.

**Actions.**

1. Write `src/devenv_py/normalize.py`:
   - Sort object keys.
   - Replace `/nix/store/<32 chars>-` with `<store>/` in every string.
   - Rewrite `$path` values under the fixture root as relative paths that start with `./`.
   - Drop the `file` field of each definition after the root check. A definition outside the root
     raises.
   - Drop `$name` from `$pkg` values, because it carries a version. Keep `$pkg` and `$output`.
   - Turn a record that has `error` into `{"$error": <error>}`.
   - Fold the definitions of one option with the merge rule of its type. Read the rule from the
     options export. The merge table:

     | Option type (from the export) | Rule |
     | --- | --- |
     | `listOf` | concatenate, in definition order |
     | `attrsOf`, `lazyAttrsOf`, freeform or ordinary `submodule` | recursive union |
     | `separatedString` | join with `payload.sep` |
     | any other type, with more than one definition | `{"$multi-def": [...]}` |

     A key clash inside a union also becomes `$multi-def`. The prototype used a hard-coded table
     (`enterShell` joined by newline; `env`, `scripts`, `tasks` recursive union; `packages`
     concatenation). The port derives the same rules from the export, and a test checks that the
     derived rules equal the hard-coded ones for these four options.
2. Write `src/devenv_py/compare.py`. It returns a list of differences. Each difference holds
   the option path, the JSON path inside the value, the expected value, and the actual value.
3. Write unit tests for each rule in action 1, and for a comparison with zero, one, and many
   differences.
4. Write the two-directory test. Copy the five golden fixtures to two directories at the same depth
   (`A/deeper/`, `B/deeper/`). Change `data.txt` on side B, so the store hash differs. Send one
   batch. All five normalized truths must be equal.

**Expected result.** Two truths of the same source in two directories compare equal. Phase A: the
prototype passed all assertions, and the two-directory test passed for all five fixtures. Raw truth
differed only by the directory prefix, and by the store hash for `e-paths`.

**Limit.** Priority between two definitions inside one freeform attribute set is invisible in truth.
The normalizer would report `$multi-def` at `env.X`.

**Record.** `evidence/step-6.md`: the rules, the test count, and the result of the two-directory
test.

**Gate GM3.** The normalizer tests pass, and the two-directory test shows no difference.

---

## Step 7. Harvest and triage the corpus

**Goal.** A corpus of real fixtures, each with provenance, triage, and truth.

**Status.** Not started. A static survey ran in phase A. It evaluated no fixture. See
[evidence/phase-a.md](./evidence/phase-a.md), section 5.

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
   path from the export's `declarations` or from the lock. Record the license from the source: Apache
   License 2.0 at the pin. Vendoring needs the license text and a NOTICE of origin. Phase A counts:
   69 top-level directories and 72 `devenv.nix` files, because 3 nested files exist
   (`compose/projectA`, `compose/projectB`, `imports/folder`).
3. Harvest `devenv-tests` from the input's `tests/` directory. Keep only entries with a `devenv.nix`.
   Phase A counts: 150 entries and 159 `devenv.nix` files, because some entries nest.
4. Harvest `fleet`: every `devenv.nix` under `~/Documents/Projects`. Exclude `.devenv/`,
   `gitman-workspaces/`, `node_modules/`, **`.archive/`, and `.worktrees/`**. Then **deduplicate by
   content hash**. Set `private = true`. Never copy a `devenv.local.nix` (71 fleet directories hold
   one; 69 are symlinks). Handle a broken symlink as `broken` and leave it out of the counts. Fleet
   fixtures stay in a private repository or in local state.

   Phase A counts for the fleet: 407 files with the spec exclusions only. 266 sit under `.archive/`
   or `.worktrees/`. 140 are primary paths. Unique content: 157 over all paths, 104 over primary
   paths. The exclusion drops old unique files; the owner accepted that (decision D7).
5. Triage each fixture into one class:

   | Class | Rule |
   | --- | --- |
   | `batch` | Its `devenv.yaml` inputs are a subset of {`devenv`, `nixpkgs`, `nixpkgs-python`}, and `devenv.yaml` has no other key (no `imports`, `allowUnfree`, `nixpkgs` block) |
   | `alone` | It needs other inputs or settings. Copy it to a temporary project with its own `devenv.yaml` and evaluate it alone |
   | `secret` | It needs SecretSpec or other secrets: a `secretspec.toml`, a `secretspec` key or word in `devenv.yaml`, or a `secretspec` token in `devenv.nix` |
   | `fails` | It does not evaluate at the pin; keep the error tail |

   The `batch` test checks input names only. It does not check a changed `url` on an allowed input.
   Add that check. The phase A survey did not detect other secret tools (sops, agenix, vault).
6. Write a **validity check** for the `fails` class. The oracle does not force `config`, so a truth
   can exist for a fixture that devenv rejects (`env.GATED = mkIf false` is an example). Proposed:
   force a config value of the candidate with `tryEval`, and treat a failure as `fails`. Use
   bisection for failures that `tryEval` misses. Design and prove this check with a fixture before
   use.
7. Compute truth for every `batch` and `alone` fixture. Compute it twice, and compare.

**Fleet-module options.** Fleet fixtures set options from modules that a stock pin lacks:
`repoman.*`, `testee.*`, `docman.*`, `zelligate.*`. A model for those needs those modules in the
options export. Add them as a later pin variant (decision D8). Until then those options are outside
the stock pilot.

**Expected result.** Most devenv examples are `batch` or `alone`. Every `fails` entry has a reason.
The static survey predicts, for the pilot gate: 87 deduplicated `languages.python` fixtures (8
excluded, 9.2 percent) and 13 `services.postgres` fixtures (0 excluded). The public sources alone
give 23 and 10. The prediction holds only if the public fixtures evaluate. Check it after the
evaluation run reports `fails`.

**Record.** `evidence/step-7.md`: counts per source and class, the `fails` reasons, and the run
time.

**Gate GM4.** Every fixture has a class. Every `batch` and `alone` fixture has a stable truth.

---

## Step 8. The model generator

**Goal.** Generated Pydantic models for any subtree, stamped with the pin.

**Status.** Not started. The type facts from the phase A export are folded into the actions below.

**Actions.**

1. Write `src/devenv_py/values.py` with the shared value types: `PkgRef`, `PathRef`,
   `NixExpr`, `Priority[T]`, `Lines`, and `JsonValue`. Each has a `to_tagged()` method that
   returns the tagged JSON form of Step 5.
2. Write `src/devenv_py/generator.py` with `dpy gen <subtree>`. It reads the export, selects
   options whose `loc` starts with the subtree, and maps each type tree with the concept's table.
   - Match parameterized names by prefix, such as `strMatching "<pattern>"`. Read the raw pattern
     from `payload.pattern`.
   - Read `output` and `outputOf` (devenv types from `src/modules/outputs.nix`).
   - Fold `either int float` (the type of `number`) to `float`. `oneOf` already folds into `either`.
   - Recognise a format type (JSON, YAML, TOML value) by the `recursive` marker and the description
     of its node. These are `nullOr` or `either` nodes (28 options at the pin).
   - Read `path` from its payload `{absolute, inStore}`. `pathInStore` and `externalPath` appear as
     `path`.
   - Types never seen at the pin (`nonEmptyStr`, `singleLineStr`, `signedInt*`, `positiveInt`,
     `raw`, `module`, `attrTag`) need synthetic export entries in the unit tests.
   - Read freeform options from `nested.freeformType`. A `loc` is a list; its elements can hold
     dots, so never join and split it on dots.
   - Read the export markers: `recursive`, `truncated`, `depthCut`, `defaultSkipped`, and
     `defaultError`. A `defaultSkipped` or `defaultError` option has no usable default value; use
     `defaultText` in the field description.
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
   # pin: devenv-2.4.0-b904dcb5-c2f38fe7
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

**Status.** Done on 2026-10-11. The change landed on `templateer_v2` `main` at `d3304db4` and was
pushed. No release tag exists yet. See [evidence/step-9.md](./evidence/step-9.md). The harness pins a
tag, and the pinned tag `v0.4.2` is on the `v6-flake` branch, so it lacks the `nix` language.
A new tag on `main` is an open item for the owner.

**What exists.**

- `nix` is a parsed language. It is not in `STRUCTURED_LANGUAGES` or `_QUOTED_STRING_LANGUAGES`.
  The finalizer passes strings unchanged and writes `true` and `false`. A `None` value raises.
- `escape_nix_string` follows the table below. A lone surrogate raises too.

  | Character | Output |
  | --- | --- |
  | `\` | `\\` |
  | `"` | `\"` |
  | `${` | `\${` |
  | newline | `\n` |
  | carriage return | `\r` |
  | tab | `\t` |
  | U+0000 | raise `EscapeError` |
  | any other character | unchanged |

- Filters `nix` and `nix_attr` (in `src/templateer/nix_render.py`). The `nix` filter renders tagged
  JSON: strings, numbers, booleans, lists, objects, `$pkg` (with `$output`), `$path` (safe relative
  paths only), `$nix` (raw source; the caller owns it), and `$priority`. A tagged object with extra
  keys raises. `nix_attr` takes a string, or a list of strings joined with dots. It writes a bare
  identifier when valid, and a quoted name for other names and for keywords.
- The parse validator pipes the artifact into `nix-instantiate --parse -`. A missing program and a
  NUL byte are errors.
- The lint requires the last filter of every `{{ }}` site to be `nix` or `nix_attr`. `indent` may
  follow. A loose operator outside the filter is a finding.
- `templateer check` renders each fixture and parses it with Nix. It runs no injection probe.

**Facts that change this guide.**

1. `-` reads standard input on Nix 2.34.7 for `--parse` and for `--eval --strict --json`. The guide
   claim holds.
2. `--parse` also binds variables. A fragment such as `pkgs.git` fails with "undefined variable".
   **A module must start with `{ pkgs, lib, ... }:`** for `--parse`. The validator tests wrap fragments
   in that head.
3. **Atom parenthesis rules.** A list element or a function argument must be one atom.
   - `[ -1 ]` is a syntax error. The filter writes `[ (-1) ]`.
   - `[ lib.mkForce 1 ]` is two elements. The filter writes `[ (lib.mkForce 1) ]`.
   - `lib.mkDefault (lib.mkForce 1)` and `lib.mkOverride (-5) (-1)` need parentheses.
   - At the top level and as an attribute value, the filter writes none: `lib.mkDefault 1`.
4. **Float exponent.** `1e20` and `1e+20` are not Nix floats. Nix needs a decimal point. The filter
   writes `1.0e+20`. `1.5e-07` is already valid.
5. **Integer range.** Nix cannot write `-9223372036854775808` as a literal, and `9223372036854775808`
   is invalid. The filter accepts -(2^63-1) to 2^63-1 and raises outside it.
6. The earlier guide text wrote `$nix` "in parentheses". The filter writes `$nix` source raw. The
   record does not say whether it adds parentheses in an atom position. Check this in Step 10.

**Tests.** 213 tests in `tests/test_nix_language.py` pass; 58 carry the `needs_nix` marker and skip
without `nix-instantiate`. One exhaustive escape test covers U+0001 to U+011F, U+2028, U+2029,
U+FEFF, one astral character, and `${x}` in one `nix-instantiate --eval --strict --json -` call. The
whole suite passes: `659 passed, 9 skipped`.

**Record.** [evidence/step-9.md](./evidence/step-9.md).

**Gate GM6.** The Templateer suite passes with the `nix` language. The tag part is open.

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
     {{ d.loc | nix_attr }} = {{ d.value | nix }};
     {% endfor %}
   }
   ```

   The `nix_attr` filter of Step 9 takes a list and writes a bare identifier or a quoted name for
   each segment. It already quotes names that are not plain identifiers and keywords.
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

**Status.** Prototype proved for the syntax reader, in-repo port in progress. The eval reader has no
prototype. Evidence: [evidence/phase-a.md](./evidence/phase-a.md), section 4. The prototype is
`~/.local/state/devenv-py/phase-a/syntax/read_syntax.py`.

**Actions.**

1. Write `src/devenv_py/read_eval.py`. It takes a normalized truth and validates the subtree
   with the generated or narrowed model.
   - Resolve each `$pkg` to an attribute path. Try the candidates `pname` and
     `pname.<output>` in one batch evaluation, and keep the one whose `outPath` matches. Record an
     ambiguous or missing result as a miss (concept open question 3).
2. Write `src/devenv_py/read_syntax.py` with pydantree.

   **Load route.** `devenv shell` in pydantree fails today (`dotenv.resolved` has no value). Load the
   grammar from the `devenv-py` project venv: `tree-sitter>=0.26,<0.27`, `tree-sitter-nix`, `pydantic`,
   and `pydantree-sitter` at its pinned tag. Pin the vendored `node-schema.json` by hash (phase A:
   sha256 `d34e9bdf2acd…`, 84 entries, from pydantree `c0ccabc`). `Grammar.load` runs a conformance
   check against the schema; the PyPI grammar (ABI 14) and the nixpkgs grammar (ABI 13) both pass.

   **Node kinds.** Read kinds from the vendored schema. These are the real kinds, observed at the
   pin. The earlier guesses were wrong in several places.

   | Construct | Real kind | Fields and children |
   | --- | --- | --- |
   | root | `source_code` | `expression` |
   | function head | `function_expression` | `formals`, `universal` (`args@` name, or a bare `x:`), `body` |
   | formals, one formal | `formals`, `formal` | `formal` (many), `ellipses`; `name`, `default` |
   | attrset | `attrset_expression`, `rec_attrset_expression` | child `binding_set` |
   | binding set | `binding_set` | `binding`, `inherit`, or `inherit_from` (many) |
   | binding | `binding` | `attrpath`, `expression` |
   | attrpath | `attrpath` | `attr` (many): `identifier`, `string_expression`, or `interpolation` |
   | `inherit a;`, `inherit (a) b;` | `inherit`, `inherit_from` | `attrs`; `attrs`, `expression` |
   | string | `string_expression` | `string_fragment`, `escape_sequence`, `dollar_escape`, `interpolation` |
   | indented string | `indented_string_expression` | the same children; no indented fragment kind |
   | integer, float | `integer_expression`, `float_expression` | none; the text is the value |
   | negative number, `!` | `unary_expression` | `operator`, `argument` |
   | `true`, `false`, `null`, any name | `variable_expression` | `name`; no boolean or null kind |
   | list | `list_expression` | `element` (many) |
   | select | `select_expression` | `expression`, `attrpath`, `default` (the `or` form) |
   | with | `with_expression` | `environment`, `body` |
   | apply | `apply_expression` | `function`, `argument`; curried |
   | let | `let_expression` | child `binding_set`, `body` |
   | if, parentheses, binary | `if_expression`, `parenthesized_expression`, `binary_expression` | |
   | path | `path_expression` | `path_fragment`, `interpolation` |

   `comment` nodes appear between bindings and are not in the `binding` field. A `dollar_escape`
   node holds only the marker; the next `string_fragment` holds the `$`. `a or 1` outside a select
   parses as an apply to a variable named `or`.

   **Reader rules (decisions D3 to D6, and prototype behavior).**
   - **Parse errors.** Refuse a file that the grammar reports as having an error (for example
     version-control conflict markers). Raise `SyntaxReadError`.
   - **Function head.** Accept a head such as `{ pkgs, lib, ... }:`, including a curried head, and
     read its body. Keep the names the head binds.
   - **Root `let`.** Keep the `let` header as **verbatim prefix text**. Read the attribute set in
     the `in` body, and write the prefix back unchanged. (The earlier rule, "keep the whole body as
     one `NixExpr`", gives no typed field for half the fleet: 28 of 58 files.) Names bound in the
     header are unknown to the reader, so any value that uses them stays `NixExpr`.
   - **Bindings.** Expand dotted attribute paths and nested attribute sets into one tree. A binding
     with a dynamic attribute name, an `inherit`, an `inherit (x)`, or a path collision goes in
     `extra_bindings`, as a `NixExpr` of the binding text including the `;`. (The prototype used the
     list key `$nix-binding`.)
   - **Literals.** Read strings without interpolation, integers, floats, `true`, `false`, `null`,
     and lists and attribute sets of literals. Remove parentheses. Read `-` before a number
     literal as a negative number.
   - **Strings.** Decode `\n`, `\r`, `\t`, and `\X` in a double-quoted string. Remove the common
     indent of an indented string, as Nix does. Keep a string with an interpolation as **one
     `NixExpr`** (decision D5). Any `''\` escape in an indented string makes it `NixExpr`. The
     `'''` escape decodes.
   - **Packages.** Read `pkgs.x.y` as `PkgRef` only when every attribute is a plain name and there is
     no `or` default. Read a bare name in `with pkgs; [ a b ]` as `PkgRef`. A name that the function
     head binds (`lib`, `config`) shadows the `with` scope, so it is not a package: keep it
     `NixExpr`.
   - **Priority.** `lib.mkDefault v` is priority 1000. `lib.mkForce v` is 50. `lib.mkOverride n v`
     is `n` when `n` is an integer literal. **Record the function name** as well as the number
     (decision D6): `lib.mkDefault 1` and `lib.mkOverride 1000 1` must stay apart, or RT5 cannot
     be idempotent.
   - **Everything else** is `NixExpr` with its exact source span (MDL-010). This includes
     `lib.mkIf`, other function calls, paths in a list, selects whose root is not `pkgs`, `rec { }`,
     and legacy `let { }`.
   - **Leaf counts.** Report, for each file, leaves as `typed` (no `NixExpr` inside), `nix` (the
     leaf is a `NixExpr`), or `partial` (a list with some `NixExpr` elements).

   **Implementation notes.** pydantree narrowing works one level at a time: a subclass is used for a
   child only when the parent class redeclares the field. Narrow two levels and use `isinstance`
   below. Do not use `from __future__ import annotations` in the module that declares node
   subclasses; it caused `SchemaCheckError: optionality disagrees`.
3. Test the syntax reader on the five golden fixtures. Assert the literal fields and the `NixExpr`
   spans.
4. **Span check.** For every `NixExpr`, assert that the source slice at its span equals its text,
   that the text parses alone as one expression (or one binding in `{ }`), and that the tree and the
   records match one to one. Run it on non-ASCII files.
5. **Value check.** Evaluate the source slice of every typed scalar literal with `nix-instantiate`.
   Compare type and value. Add synthetic snippets for indented strings. Phase A found three decoder
   bugs only this way.
6. **Fleet run.** Run the reader over the fleet `devenv.nix` files (Step 7 selection) and record the
   counts per file, the typed ratio, and the reasons for `NixExpr`. The golden fixtures cannot show
   the root `let` cost.

**Expected result.** Both readers produce valid instances for the golden fixtures. Phase A, for the
prototype with the old `let` rule: 58 of 59 fleet files parse (one has conflict markers); 423
leaves, 358 typed, 6 partial, 59 nix (84.6 percent typed, inflated by the root `let`); 90.6 percent
for the 30 files without a root `let`; 79.1 percent typed when `let` bodies are followed (a lower
bound). Interpolation causes 81 percent of the remaining `NixExpr` values. The span check passed for
65 values, and the value check for 339 literals, with 0 failures. Time: 1.0 s for 58 files. The
`let` prefix rule should lift the file-level ratio. Measure it in the port.

**Record.** `evidence/step-11.md`: the node kinds that the pinned grammar uses, the number of
`NixExpr` values per golden fixture, and the fleet counts.

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

# Guide: the round-trip harness for typed devenv models

**Date:** 2026-10-10. **Updated:** 2026-10-11 with the implementation of Steps 2 to 14, the pilot
work of Step 15, and the Step 16 skills. **Status:** Draft for owner review. Steps 1 to 14 are done.
Step 15 and Step 16 are IN PROGRESS. **Concept:** [CONCEPT.md](./CONCEPT.md).
**Gates:** [evidence/GATES.md](./evidence/GATES.md).

This guide builds the harness in order. Each step names its goal, its actions, the expected result,
the record to write, and its gate. Do not start a step before the gate of the step before it passes.

Every command, file name, option name, and Nix node kind here is proposed until the step's fixture
proves it on the pinned tools. When a fixture disproves an interface, update this guide, the concept,
and the code together. Where a step says "as built", the text follows the code in `devenv-py` at
`main` `0dd939d802d2`, and the code wins on any disagreement.

## Conventions

- **Repository.** The harness lives in a new repository, `devenv-py` (owner decision, 2026-10-11). Paths below
  are relative to its root unless they start with `~` or `/`.
- **Version control.** Use a Gitman workspace for each step: `gitman work dpy-step-N`.
- **Verification.** The harness repository verifies through Testee, like Vendomat. Run
  `testee verify --full` from the repository root. Run other commands inside `devenv shell`:
  `devenv shell -- dpy ...`. Do not call pytest, ruff, or ty directly.
- **No bare `uv`.** The shell of an agent can inherit `UV_PROJECT_ENVIRONMENT` and `VIRTUAL_ENV` from
  Vendomat. A bare `uv sync` then overwrites the Vendomat venv (this happened; see
  [evidence/step-2-3.md](./evidence/step-2-3.md)). Run
  `env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV devenv shell -- uv ...`.
- **Raw logs.** Write raw logs under `~/.local/state/devenv-py/` (MDL-012). Never commit them.
- **Records.** Write the records in this project directory under `evidence/`. Record the pin, the
  exact commands, the expected results, and the actual results. Keep observation apart from
  inference. Some records cover several steps: `step-2-3.md`, `step-5-6.md`, `step-12-14.md`.
  `evidence/GATES.md` holds the status of each gate.
- **Pin.** A pin is the devenv CLI version, the `devenv` input revision, and the `nixpkgs` input
  revision. Its identifier is `devenv-<cli>-<devenv-rev:8>-<nixpkgs-rev:8>`. Every output file
  carries the pin identifier. The first pin is `devenv-2.4.0-b904dcb5-c2f38fe7`. Read each revision
  through `nodes.root.inputs` in `devenv.lock`: the root `nixpkgs` points at the node `nixpkgs_2`.
- **Step states.** Phase A proved prototypes outside the repository
  ([evidence/phase-a.md](./evidence/phase-a.md)). The in-repo port of every step from 2 to 14 is
  done, with tests. Each step names its commit on `devenv-py` `main`. Step 15 and Step 16 are IN
  PROGRESS.

## Repository layout (as built)

```text
devenv-py/
  AGENTS.md  CLAUDE.md (symlink)             project instructions
  devenv.nix  devenv.yaml  devenv.lock       harness toolchain and Testee checks
  pyproject.toml  uv.lock
  pins/<pin-id>/                             base project for one pin
    devenv.nix  devenv.yaml  devenv.lock  pin.toml
  nix/
    introspect.nix                           the request module that the base imports
    options.nix                              options export
    serialize.nix                            tagged JSON values
    touched.nix                              option paths that a fixture mentions
    oracle.nix                               per-file contributions
    validity.nix                             triage probe (Step 7)
  reader-module/default.nix                  Path T fixed reader
  src/devenv_py/
    pin.py  driver.py  options.py  truth.py  normalize.py  compare.py  corpus.py
    values.py  generator.py  writer_common.py  writer_nix.py  writer_toml.py
    read_eval.py  read_syntax.py  syntax_stats.py  grammar/
    roundtrip.py  generate_cases.py  report.py  cli.py
  templates/devenv-module/                   Templateer template for Path N
  exports/<pin-id>/options.json  options.meta.json
  generated/<pin-id>/<subtree>.py  <subtree>.schema.json
  narrowed/<subtree>.py
  corpus/<source>/<name>/
    source/  provenance.toml  truth/<pin-id>.json  triage.toml
  skills/<name>/SKILL.md                     Step 16 skill sources (Devman links them into .agents/skills/)
  tests/  (golden fixtures under tests/golden/)
```

The fleet corpus is private. It lives under `~/.local/state/devenv-py/corpus/`, not in the
repository. Raw runs live under `~/.local/state/devenv-py/` (`runs/`, `requests/`, `rt/`, `cases/`).

### Commands (as built)

Two kinds of entry point exist: `dpy` subcommands and `python -m` modules. The guide text of earlier drafts proposed `dpy export`, `dpy harvest`, and
`dpy truth`. Those subcommands do not exist.

| Command | Purpose | Step |
| --- | --- | --- |
| `python -m devenv_py.options {export,check,census}` | write and check the options export; count the types | 4 |
| `python -m devenv_py.corpus {harvest SOURCE, evaluate [SOURCES], all, bench}` | harvest, triage, compute truth, time batches | 7 |
| `python -m devenv_py.syntax_stats` | fleet counts of the syntax reader (counts only) | 11 |
| `dpy gen SUBTREE`, `dpy schema SUBTREE`, `dpy drift OLD NEW` | generate models and schema; compare exports | 8 |
| `dpy render TRUTH.json [--path nix\|toml] [--out DIR]` | write a normalized truth as a module | 10 |
| `dpy rt ...` | run RT1 to RT8 | 12, 13 |
| `dpy report RUN_ID [--strict] [--json]` | write the report and the gate | 14 |

Truth has no command. `truth.truth_for_fixtures` computes it, and `corpus evaluate` calls it.
Exit codes: 0 ok, 1 act on findings, 2 the tool could not run.

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
  | `templateer` | First tag `v0.4.2`, which is on the `v6-flake` branch of `templateer_v2` and lacks the `nix` language. Since Step 10 the harness pins a revision on `main`, now `ac02b48c015d` (see Step 9). A tag on `main` is still open. |
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

**Status.** Done. Commits `4d6712d7a2cf` (introspection module) and `3b6e48c20b09` (driver). Record:
[evidence/step-2-3.md](./evidence/step-2-3.md).

The base project imports an introspection module. The module takes the module arguments as
`@moduleArgs`. It reads a request file and puts its answer in a read-only config value. `devenv eval`
reads that value like any other config attribute (probe O10 to O12). No fork patch and no repl are
needed.

**Interface of `nix/introspect.nix` (as built).** The repository file is the authority.

- Arguments: `{ lib, pkgs, options, extendModules, config, ... }@moduleArgs`.
- Option `introspect.request`: `nullOr path`, default `null`.
- Option `introspect.result`: read-only `types.str`. Its value is **a JSON string for every request
  kind**. `devenv eval` fails with `Failed to get attribute 'mcp.devenv.sh'` when the result holds
  an attribute name with a dot. A string hides the names.
- Option `introspect.optionsDoc`: read-only package. It is `nixosOptionsDoc` over the option tree
  without `introspect`, with `warningsAreErrors = false` (Step 4).
- Request kinds: `echo` (returns `payload`), `options` (field `maxDepth`; Step 4), and `truth`
  (field `candidates`; Step 5). Any other kind throws `unknown request kind: <kind>`.
- The harness never reports on `introspect` itself: it removes that attribute from the option sets.
- The triage probe is a separate request path, `-O dpyValidity.request:path`, in `nix/validity.nix`
  (Step 7). It leaves `introspect.nix` unchanged.

**Driver behavior (as built).** Read `src/devenv_py/driver.py` for the code. The behavior:

- `run_request` evaluates `devenv eval [--no-eval-cache] -O introspect.request:path <file>
  introspect.result` in the pin directory. It sets `NO_COLOR=1`, `stdin=DEVNULL`, and appends the
  host `bin` directories to `PATH`. It decodes the output twice.
- The request file is **content-addressed**: `request_path` and `write_request` write
  `~/.local/state/devenv-py/requests/<sha256 of the canonical JSON>.json` once, by atomic rename.
  The evaluation cache keys on the request path, so a new path per run never hits the cache
  (Step 7 observation). The run directory (`~/.local/state/devenv-py/runs/<timestamp>-<kind>/`,
  override with `DEVENV_PY_STATE`) still gets `request.json` and the logs.
- `DriverError` carries the tail of the error output. A missing `devenv` binary raises `OSError`. A
  timeout raises `DriverError(timed_out=True)`.

**Actions (as done).**

1. `nix/introspect.nix` follows the interface above.
2. `pins/<pin-id>/devenv.nix` is `{ imports = [ ../../nix/introspect.nix ]; }`.
3. `tests/test_driver.py` sends an `echo` request with a payload that holds a double quote, a
   backslash, a newline, `${`, a non-ASCII character, and a nested list. The result equals the
   payload.
4. A dotted-key echo test sends the keys `d.e` and `mcp.devenv.sh`. It fails if the result stops
   being a JSON string.
5. An unknown request kind raises `DriverError` with the text `unknown request kind`.
6. Cache tests: a changed request file at one path gives a new result; the same request three times
   gives 0.33 s, 0.12 s, and 0.12 s (warm below 0.6 times cold, in `nix`-marked tests).

**Expected result.** The echo tests pass, and the cache test gives two different results. Observed:
echo with no cache 0.30 to 0.33 s, echo with a cache hit 0.06 to 0.12 s, unknown kind 0.33 s with
exit 1.

**Fallback.** If a later pin breaks this route, use `devenv repl`. Pipe
`:p import <nix-dir>/entry.nix { inherit devenv; requestFile = <file>; }` on standard input. Let the
entry wrap `builtins.toJSON` of the answer in fixed sentinel strings, and parse the text between
them (probe O4). Use `devenv.project.options` and `devenv.project.extendModules` in place of the
module arguments. The fallback is untested.

**Gate GM1 (part 1).** Met. The echo, dotted-key, and cache tests pass on the pin.

---

## Step 3. Batch evaluation and bisection

**Goal.** Evaluate many candidate modules in one `devenv eval` call. Find the bad one when a batch
fails.

**Status.** Done. Commit `3b6e48c20b09` (`driver.run_batch`). Records:
[evidence/step-2-3.md](./evidence/step-2-3.md) and the timing table measured in Step 7.

**Facts.**

- A `truth` request with five candidates costs 1.5 to 1.7 s. The fixed start is about 0.3 s.
- A candidate module given as an absolute path outside the base project is readable under pure
  evaluation. Its path stays absolute in `definitionsWithLocations`. The driver needs no copy into
  `.candidates/` (action 3).
- An undeclared option in a candidate (`foo.bar = 1`) makes the module check fail and aborts the
  whole call. Bisection handles it.
- `builtins.abort` in a candidate aborts the batch. `tryEval` does not catch it. Bisection isolates
  the candidate and writes `dpy-bisect` in the error tail.

**Actions (as done).**

1. The Step 5 oracle with `scope = "touched"` is the batch workload.
2. Three candidates with different `env.MARK` values give three different results (`test_batch.py`).
3. A module given as an absolute path keeps its path (tested).
4. `driver.run_batch(candidates)` returns `dict[str, Outcome]` with `status` `ok` or `eval-error`,
   `result`, and `error`. On `DriverError` it splits the batch in two halves and retries each half.
   A single candidate that still fails keeps its error tail (MDL-013). It writes `bisect.log`. A
   timeout is not bisected.
5. A test with five good candidates and one `builtins.abort "dm-bisect"` candidate asserts five
   results and one `eval-error` whose tail holds `dm-bisect`. A second bad candidate sets an
   undeclared option.
6. The timing table (Step 7, 181 `batch` fixtures, touched scope):

   | n | cold wall (s) | cold per candidate (s) | peak RSS (MB) | warm wall (s) |
   | --- | --- | --- | --- | --- |
   | 1 | 0.33 | 0.33 | 84 | 0.11 |
   | 10 | 1.27 | 0.127 | 211 | 0.07 |
   | 50 | 3.54 | 0.071 | 436 | 0.11 |
   | 100 | 5.37 | 0.054 | 628 | 0.12 |
   | 181 | 12.13 | 0.067 | 751 | 0.13 |

   The table has no row for 200: only 181 fixtures qualify. Touched scope costs about 0.06 s per
   candidate at n of 50 or more. The phase-A whole-tree oracle cost 2.8 s per candidate. Memory
   grows about 3.7 MB per candidate.

**Expected result.** Batch evaluation works. Bisection isolates the bad candidate. The time per
candidate falls as the batch grows. All three hold.

**Gate GM1.** Met. Batch and bisection tests pass. The timing table exists.

---

## Step 4. The options export

**Goal.** A complete, structured JSON export of the option tree for the pin.

**Status.** Done. Commit `4052991b1b8a`. Record: [evidence/step-4.md](./evidence/step-4.md). The first
draft failed in eleven places; the proven exporter replaced it ([evidence/phase-a.md](./evidence/phase-a.md),
section 1). The step has no report file; the record holds the orchestrator's facts.

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
2. Write `src/devenv_py/options.py`. The command is `python -m devenv_py.options export` (the draft
   name `dpy export` does not exist). It sends an `options` request with `maxDepth = 8`, fails when
   any node has `depthCut`, and writes `exports/<pin-id>/options.json` with the sidecar
   `options.meta.json` (pin, SHA-256, `records`, `top_level_records`). Canonical form:
   `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
3. Write the completeness check. Run `devenv build introspect.optionsDoc` and read
   `share/doc/nixos/options.json`. Take its keys. Take the joined `loc` of every exported option
   that the **doc rule** lists, including sub-options. The two sets must be equal. Map names as
   `optionsJSON` does: `<name>` for an attribute-set element and `*` for a list element. The command
   is `python -m devenv_py.options check`.

   **The doc rule** (from `optionAttrSetToDocList'`). List an option when `visible` is `true` or
   `"shallow"` and it is not `internal`. Walk its sub-options only when `visible` is `true` or
   `"transparent"`. `internal` does not stop the walk. The naive rule "visible and not internal" lists
   1199 options at the pin and fails by 55: each has a hidden ancestor. Test the rule on a synthetic
   module that uses every `visible` form.
4. Write a type census (`python -m devenv_py.options census`): count options per `type.name`,
   including nested names. Record each name that carries a payload in the name, such as
   `strMatching "<pattern>"`.
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
hit. These are values for one pin. The test asserts the equalities, not the byte count. **Observed
in the port:** the export hash equals the phase-A hash byte for byte, and the counts above hold.

**Known limits.** A future default that fails with `abort` or a type error breaks the whole export,
and bisection cannot help. The `recursive` rule keys on descriptions, so two different types with one
description would be cut wrongly. The `attrTag` branch is untested.

**Record.** [evidence/step-4.md](./evidence/step-4.md). The prototype values are in
[evidence/phase-a.md](./evidence/phase-a.md).

**Gate GM2.** Met. The export is complete, the hash equals the phase-A hash, and the export has no
`depthCut`.

---

## Step 5. The oracle and the serializer

**Goal.** Truth: the definitions that a fixture's files give to each option, as tagged JSON.

**Status.** Done. Commits `4d6712d7a2cf` (Nix files) and `4a79266083c7` (truth, golden fixtures).
Record: [evidence/step-5-6.md](./evidence/step-5-6.md). The first draft aborted on some fixtures
([evidence/phase-a.md](./evidence/phase-a.md), section 2).

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
2. Write `src/devenv_py/truth.py`. No `dpy truth` command exists. `truth_for_fixtures` builds a batch
   request and returns raw truth. `normalized_truth` normalizes it. Each candidate's `modules` is
   the fixture's `source/devenv.nix`. Its `roots` is the fixture's `source/` directory with a
   trailing `/`. The candidate label is the absolute fixture path.
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

**Record.** [evidence/step-5-6.md](./evidence/step-5-6.md). Phase A found four causes of difference
from the golden values: absolute `file` paths, store hashes in e, `$path` absolute in e, and `$name`
versions in c.

**Gate GM3 (part 1).** Met. All five golden fixtures match, touched scope equals `scope = "all"` with
the deny list, and truth is stable. The golden `expected.normalized.json` files are regression
files, not independent proof (the agent generated them from the oracle output and read them against
the hand-written `expected.json`).

---

## Step 6. The normalizer and the comparison

**Goal.** Compare truths without false differences from store hashes, paths, or definition counts.

**Status.** Done. Commit `4a79266083c7`; merge rules from the export in `4052991b1b8a`; path
scrubbing in `ad9476284450`. Record: [evidence/step-5-6.md](./evidence/step-5-6.md).

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
     concatenation). The port first kept that table (`DEFAULT_MERGE_RULES`), then derived the rules
     from the export (`normalize.default_rules`, Step 4). A `nullOr X` option takes the rule of `X`.
   - Two more rules (rules 7 and 8 in `normalize.py`; added with `ad9476284450`): rewrite store hashes, `/tmp/devenv-<7hex>` and
     `/run/user/N/devenv-<7hex>` (to `<runtime>`), project directories and the fixture root (to
     `<root>`), the repository checkout (to `<checkout>`), and home (to `<home>`) in every string
     and object key. Signature: `normalize(raw, root, rules=None, project_dirs=None)`.
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

**Record.** [evidence/step-5-6.md](./evidence/step-5-6.md): the rules, the test count (71 tests in
the first gate run), and the result of the two-directory test.

**Gate GM3.** Met. The normalizer tests pass, and the two-directory test shows no difference.

---

## Step 7. Harvest and triage the corpus

**Goal.** A corpus of real fixtures, each with provenance, triage, and truth.

**Status.** Done. Commit `18ad476966a8`. Record: [evidence/step-7.md](./evidence/step-7.md). The
phase-A static survey is in [evidence/phase-a.md](./evidence/phase-a.md), section 5.

**Actions.**

1. Write `src/devenv_py/corpus.py`. The commands are `python -m devenv_py.corpus harvest SOURCE
   [--dest DIR] [--devenv-src DIR] [--limit N]`, `evaluate [SOURCES] [--corpus-dir DIR]
   [--names ...] [--summary FILE]`, `all`, and `bench [--sizes ...]`. The sources are
   `devenv-examples`, `devenv-tests`, and `fleet`. `evaluate` triages, computes truth twice, runs
   the validity check, and writes the results. The full run is manual; the default tests are small.
   Each fixture gets this layout:

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

   As built, the `batch` test compares input name and `url`. An extra key other than `url` or
   `inputs` makes a fixture `alone`; `follows` differences are ignored. A fixture with
   `devenv: github:cachix/devenv` is `alone`, because the pin yaml holds a revision. The `secret`
   test also detects `sops`, `agenix`, and `vault` (only as `vault-agent`, `vault secrets`,
   `VAULT_TOKEN`, or `config.vault`).
6. The **validity check** for the `fails` class is `nix/validity.nix` (request
   `-O dpyValidity.request:path`). The oracle does not force `config`, so a truth can exist for a
   fixture that devenv rejects (`env.GATED = mkIf false` is an example). The probe runs three
   checks: an undeclared option; each touched option forced to shallow depth (names and weak-head
   children; a submodule with declared options only to weak head, because `git-hooks.src` has no
   default); and a probe of `config.enterShell`, which exposes a missing integration input
   (`missing-input-error`). Bisection isolates errors that `tryEval` misses. Limit: the probe is not
   a full `devenv shell` build. It misses a failure inside a nested value, such as a script `exec`
   that throws. Fixtures proved: `syntax-error`, `missing-input-error`, `env.GATED`.
7. Compute truth for every `batch` and `alone` fixture. Compute it twice, and compare.

**Fleet-module options.** Fleet fixtures set options from modules that a stock pin lacks:
`repoman.*`, `testee.*`, `docman.*`, `zelligate.*`. A model for those needs those modules in the
options export. Add them as a later pin variant (decision D8). Until then those options are outside
the stock pilot.

**Expected result.** Most devenv examples are `batch` or `alone`. Every `fails` entry has a reason.
The static survey predicted 23 public `languages.python` fixtures and 10 `services.postgres`
fixtures. **Observed:** 24 and 10 evaluate. Counts per class: examples 45 `batch`, 24 `alone`, 0
`secret`, 3 `fails` (72); tests 119, 21, 4, 15 (159); fleet 17, 48, 11, 35 (111 after 31 duplicates).
0 fixtures have an unstable truth. The run took 978 s.

**Record.** [evidence/step-7.md](./evidence/step-7.md): counts per source and class, the `fails`
reasons, and the run time.

**Gate GM4.** Met. Every fixture has a class. Every `batch` and `alone` fixture has a stable truth.

---

## Step 8. The model generator

**Goal.** Generated Pydantic models for any subtree, stamped with the pin.

**Status.** Done. Commit `7579a9e18315`. Record: [evidence/step-8.md](./evidence/step-8.md). The
type facts from the phase A export are folded into the actions below. Departures that change the
design are marked "as built".

**Actions.**

1. Write `src/devenv_py/values.py` with the shared value types: `PkgRef`, `PathRef`,
   `NixExpr`, `Priority[T]`, `Lines`, and `JsonValue`. Each has a `to_tagged()` method that
   returns the tagged JSON form of Step 5; `JsonValue` is a type alias, so `to_tagged(value)` is a
   module function. Later, Step 15 added `FnMarker` (tag `$fn`, accepts only `{"$fn": true}`, holds
   no source) for a function-typed option whose value comes from truth.
2. Write `src/devenv_py/generator.py` with `dpy gen <subtree>`. It reads the export, selects
   options whose `loc` starts with the subtree, and maps each type tree with the concept's table.
   - Match parameterized names by prefix, such as `strMatching "<pattern>"`. Read the raw pattern
     from `payload.pattern`.
   - Read `output` and `outputOf` (devenv types from `src/modules/outputs.nix`).
   - Fold `either int float` (the type of `number`) to a number type. As built: `StrictInt |
     StrictFloat`, not `float`, because Nix `number` accepts ints. `oneOf` already folds into
     `either`.
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
   - As built: scalar fields use `StrictBool`, `StrictInt`, and `StrictFloat`, because lax Pydantic
     accepts `"yes"` as a bool and turns ints into floats, and Nix rejects both. An intermediate
     option path becomes a module-level group class (`LanguagesPythonUvSync`), children before
     parents. Read-only options are left out. A `strMatching` pattern is wrapped as `^(?:pat)$`.
     `intBetween` bounds come from two fixed description patterns. A fourth coverage kind,
     `bounds-lost`, flags a lost pattern, separator, or bound.
3. Write the module header:

   ```python
   # Generated by devenv-py. Do not edit.
   # pin: devenv-2.4.0-b904dcb5-c2f38fe7
   # export: sha256:<hash>
   # subtree: services.postgres
   ```

4. Write `dpy schema <subtree>`. It writes JSON Schema from the generated model.
5. Write the narrowing loader. It imports `narrowed/<subtree>.py` and checks that each class adds no
   field that the option tree lacks (MDL-009). It also rejects a different `extra` rule and a class
   that extends no generated class. A narrowed file imports the generated one as
   `devenv_py_generated.<subtree with _>`. A narrowed class may hold a `CHOICES` class variable
   (Step 13).
6. Write unit tests for each row of the type table, from small synthetic export entries. Write a
   golden test for `services.postgres`.
7. Write the drift check: `dpy drift <old> <new>`. Each argument is an export file, a directory, or
   a pin id under `exports/`. It lists added, removed, and retyped options per subtree. It exits 1
   on drift and 0 on none.

**Expected result.** `dpy gen languages.python` and `dpy gen services.postgres` write importable
modules. The coverage list names every `NixExpr` field.

**Record.** [evidence/step-8.md](./evidence/step-8.md): the coverage for both pilot subtrees (16
fields with 1 `NixExpr` for `services.postgres`; 39 with 1 for `languages.python`) and the census of
unmapped type names across the whole export.

**Gate GM5.** Met. The type tests pass, the golden test passes, and both pilot modules import.

---

## Step 9. The `nix` output language in Templateer

**Goal.** Templateer renders Nix text with safe escaping and a parse check.

**Status.** Done on 2026-10-11. The change landed on `templateer_v2` `main` at `d3304db4` and was
pushed. No release tag exists. See [evidence/step-9.md](./evidence/step-9.md). The tag `v0.4.2` is on
the `v6-flake` branch and lacks the `nix` language. **Since Step 10 the harness pins Templateer by
revision.** The pin is now `ac02b48c015d` (`main`), which keeps an integral float as a Nix float.
The tag on `main` is an open item for the owner.

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
6. The earlier guide text wrote `$nix` "in parentheses". Step 10 answered this: the filter writes
   `$nix` source in parentheses at an atom position (the writer renders null as `(null)`). The
   syntax reader never keeps outer parentheses in a `$nix` value.
7. **Integral floats.** MiniJinja 2.22 turns an integral float into an integer when a template reads a
   scalar. RT7 on `services.postgres` showed this as `mismatch` (`0.0` came back as `0`). Templateer
   `ac02b48c` tags integral floats in `nix` templates. After the fix, RT7 passes 554 of 554 and
   515 of 515 on `services.postgres`.

**Tests.** 213 tests in `tests/test_nix_language.py` pass; 58 carry the `needs_nix` marker and skip
without `nix-instantiate`. One exhaustive escape test covers U+0001 to U+011F, U+2028, U+2029,
U+FEFF, one astral character, and `${x}` in one `nix-instantiate --eval --strict --json -` call. The
whole suite passes: `659 passed, 9 skipped`.

**Record.** [evidence/step-9.md](./evidence/step-9.md).

**Gate GM6.** The Templateer suite passes with the `nix` language. The tag part is open; the harness
pins a revision.

---

## Step 10. The writers

**Goal.** Turn a model instance into a module, by Path N and by Path T.

**Status.** Done. Commit `74826b8d99b9`. Record: [evidence/step-10.md](./evidence/step-10.md).

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

   **As built.** The template schema holds `definitions` only (`[{loc, value}]`). The lint needs the
   `nix` filter on every site, and that filter quotes strings and wraps `$nix` in parentheses. So
   `head`, `let_prefix`, and `extra_bindings` cannot pass through the template as verbatim text.
   `writer_nix.ModuleContribution` carries those three fields and splices them with
   `read_syntax.assemble_module`. The template file is `templates/devenv-module/template.j2`.
2. Write `src/devenv_py/writer_nix.py`. It takes a model, or a normalized truth, and produces
   the `ModuleContribution`. It renders through Templateer's Python interface. An option without a
   model uses the generic tagged value. A `$fn` value makes the fixture `has-fn`; RT2 skips it with
   that reason. As built:
   - The model path uses `OptionModel.to_tagged()`, which keeps set fields, aliases, and tags. Plain
     `model_dump` turns a `PkgRef` into `{"attr": ...}`.
   - **Null.** The `nix` filter refuses null. The writer passes null as `{"$nix": "null"}`, which
     renders as `(null)`.
   - **`$path` forms.** Path N accepts relative paths only. A `$path` of `.` or `..` renders as `./.`
     or `../.`, because a bare `.` is not a Nix path.
   - **Canonical layout.** `render` merges all definitions into one tree (reader insert rules,
     first-seen order) and writes one dotted binding per leaf. A set inside a list or a tagged value
     stays a set. `{}` is a leaf. This is what makes RT5 strict (Step 12).
   - **`WriterSkip` reasons** (stable strings in `writer_common.py`): `has-fn`, `marker`
     (`$multi-def`, `$error`, `$merge`, `$type`, `$deep`), `path-outside-root`, `toml-nix`,
     `toml-priority`, and `toml-null`.
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

   Path T does not carry `$nix`, `$priority`, or null. A model with those values uses Path N only.
   The file above is the file in `reader-module/default.nix`.
4. Write `src/devenv_py/writer_toml.py`. It writes the nested option tree as TOML with
   `tomli-w`, beside a copy of the reader module. As built, the reader module is copied as
   `source/devenv.nix` next to `contribution.toml`, because the driver needs `source/devenv.nix`. A
   truth key splits at dots, so an option path segment cannot hold a dot.
5. Test both writers on the five golden fixtures. Evaluate the output. Compare its truth with the
   golden truth.

**Expected result.** Both writers reproduce the golden truths, except where a golden fixture holds a
value that its path cannot carry.

**Record.** [evidence/step-10.md](./evidence/step-10.md): 10 of 10 golden comparisons equal (five
fixtures by two paths). `dpy render TRUTH.json [--path nix|toml] [--out DIR]` writes a module from a
normalized truth.

**Gate GM7 (part 1).** Met. Both writers pass on the golden fixtures within their stated limits.

---

## Step 11. The readers

**Goal.** Turn truth or source text into a model instance.

**Status.** Done. The eval reader is commit `5684ace508ea`. The syntax reader is commit
`549e25ba517e`. Record: [evidence/step-11.md](./evidence/step-11.md). The syntax reader prototype is
in [evidence/phase-a.md](./evidence/phase-a.md), section 4.

**Actions.**

1. Write `src/devenv_py/read_eval.py`. It takes a normalized truth and validates the subtree
   with the generated or narrowed model.
   - Resolve each `$pkg` to an attribute path. **As built:** truth keeps no `outPath`, so the reader
     tries the candidates `pname` and `<set>.<pname>` (the set comes from a hint table, for example
     `python3Packages` for `languages.python`) in one batch evaluation. It keeps the candidate
     whose `pname` and output match. `PkgRef.output` is `None` when the truth output is the default
     output. An ambiguous or missing result is a miss. A `pname` that differs from the attribute
     name (`gcc` gives `gcc-wrapper`) is a miss. **This `pname` rule is the source of the package
     identity problem of Step 15** (concept MDL-020, in progress).
   - API: `read_eval(truth, subtree, *, model=None, resolver=None, ...) -> (OptionModel,
     list[Miss])`. A `ValidationError` maps each error to its option, drops it, records a `Miss`
     (kinds `unreadable`, `invalid`, `not-in-model`, `package`, `conflict`, `model`), and retries.
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
     be idempotent. As built: the value carries the name (`"default"`, `"force"`) or an integer
     for `mkOverride`. Only `lib.`-qualified calls read.
   - **Paths.** A plain `./x` or `../x` path literal (no `${`) reads as a typed `{"$path": ...}`
     value. `<x>`, `/abs`, `~/x`, and an interpolated path stay `$nix` (`9a541b4bd8ed`).
   - **No outer parentheses.** A `$nix` value never carries outer parentheses. `x = (a b);` reads as
     `a b`.
   - **Errors.** A parse error raises `SyntaxParseError` (a `SyntaxReadError` and `ValueError`)
     with the byte offset. The message never echoes source.
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

**Observed in the port (60 fleet files; 59 parse, 1 has conflict markers; 29 have a root `let`).**
With the `let` prefix rule: 1152 leaves, 903 typed, 118 partial, 131 nix (78.4 percent typed; 88.6
percent typed or partial). 264 `$nix` values remain; interpolation causes 159 (60.2 percent). The
earlier rule (root `let` as one `$nix`) gave 84.4 percent on 424 leaves, which overstates typing
because it counts 29 whole files as one leaf each. The ratios predate the path-literal change.

**Expected result.** Both readers produce valid instances for the golden fixtures. Phase A, for the
prototype with the old `let` rule: 58 of 59 fleet files parse (one has conflict markers); 423
leaves, 358 typed, 6 partial, 59 nix (84.6 percent typed, inflated by the root `let`); 90.6 percent
for the 30 files without a root `let`; 79.1 percent typed when `let` bodies are followed (a lower
bound). Interpolation causes 81 percent of the remaining `NixExpr` values. The span check passed for
65 values, and the value check for 339 literals, with 0 failures. Time: 1.0 s for 58 files. The
`let` prefix rule should lift the file-level ratio. Measure it in the port.

**Record.** [evidence/step-11.md](./evidence/step-11.md): the node kinds that the pinned grammar
uses, the reader rules as built, and the fleet counts. The vendored schema is checked by hash at load
(`grammar/node-schema.json`, sha256 `d34e9bdf...`).

**Gate GM7.** Met. Both readers pass their tests.

---

## Step 12. The round-trip runner: RT1 to RT6

**Goal.** One command runs the corpus checks and writes results.

**Status.** Done. Commit `70d7419f5ac1`. Strict RT5 in `9a541b4bd8ed`. Record:
[evidence/step-12-14.md](./evidence/step-12-14.md).

**Actions.**

1. Write `src/devenv_py/roundtrip.py` with `dpy rt`. Flags (as built): `--subtree` (repeat or
   separate by commas; `*` for all), `--checks` (default `RT1,...,RT6`), `--fixtures DIR...`
   (default golden and corpus), `--run-id`, `--pin-dir`, `--seed` (repeat; default 1),
   `--min-cases` (500), `--max-cases` (5000), `--no-cache`, and `--smoke` (driver echo, then the five
   golden fixtures through RT1 to RT6). For each `batch` or `alone` fixture:

   | Check | Steps |
   | --- | --- |
   | RT1 | Validate truth with `read_eval`. Count `NixExpr` fields in the subtree. |
   | RT2 | Render the full truth with `writer_nix`. Evaluate. Compare with truth. |
   | RT3 | Read the source with `read_syntax`. Render with `writer_nix`. Evaluate. Compare with truth. |
   | RT4 | Compare each literal field of the syntax reader's instance with the eval reader's field. |
   | RT5 | Render, read the render with `read_syntax`, render again. **Strict:** the first render equals the second. Both use the canonical dotted layout (Step 10). |
   | RT6 | For a data-only instance: write TOML with `writer_toml`. Evaluate. Compare with truth. |

2. Evaluate every rendered candidate of one run in one batch (Step 3).
3. Write each case result as one JSON line in `~/.local/state/devenv-py/rt/<run-id>/results.jsonl`:
   fixture, subtree, check, status (`pass`, `fail`, `skip`), reason, and differences. The run also
   writes `run.json`, `report.md`, `report.json`, and `cases/`.

   **Skip reasons (as built).** RT4 skips a fixture with `imports` (`has-imports`: the syntax reader
   sees only `devenv.nix`; truth merges all files) and a fixture with `no-literal-fields`. RT1 and
   RT4 skip for subtree `*` (`no-subtree`). An `alone` fixture skips the evaluating checks
   (`alone-needs-project`) because the runner does not receive `alone_project`. A writer skip
   (Step 10) shows as `has-fn` and the other `WriterSkip` reasons.

**Expected result.** RT2 passes on most `batch` fixtures before any narrowing, because it renders
the truth back as data. Its failures show writer and serializer gaps.

**Record.** [evidence/step-12-14.md](./evidence/step-12-14.md). Observed on the five golden
fixtures (`dpy rt --smoke`): RT2, RT3, RT5, RT6 pass 9 of 9; RT4 passes 2 and skips 7; RT1 passes 4
and skips 5. Wall time 2.2 s (first run).

**Gate GM8 (part 1).** Met. The runner produces results for every fixture and check, with no crash.

---

## Step 13. Generated cases: RT7 and RT8

**Goal.** Test the type mapping itself with many generated instances.

**Status.** Done. Commit `cb5cf22e03c4`; the reject fix is `47def85602d1`. Record:
[evidence/step-12-14.md](./evidence/step-12-14.md).

**Actions.**

1. Write `src/devenv_py/generate_cases.py`. Build Hypothesis strategies from each generated
   model. Use custom strategies for the value types:
   - `PkgRef` from a short vetted list of attribute paths that evaluate at the pin (`PKG_ATTRS`).
     A narrowed class overrides a field through its `CHOICES` class variable (see below).
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
   | `other-error` | The batch aborted with an error that `tryEval` does not catch, such as `attribute 'buildEnv' missing` | Often a wrong package kind; add a `CHOICES` list |

   **The probe.** `definitionsWithLocations` never merges a value, so a plain `truth` request
   rejects nothing. The runner adds an own option `dpyRtProbe` to each generated module. The probe
   forces the defined values and `config.assertions` under `tryEval` and answers a string. The class
   `type-error` therefore means "forcing the values threw". It also covers a throwing `apply`. The
   probe forces only defined options, so an option that only affects another one (such as
   `languages.python.version`) never evaluates in RT7. In flight: forcing the `config.packages` names
   and `enterShell` (Step 15). The runner classifies an uncatchable error from stderr with the ANSI
   codes stripped (`NO_COLOR` does not remove color from Nix errors).

   **`CHOICES`.** A narrowed class (MDL-009) may set `CHOICES: ClassVar[dict[str, tuple[str, ...]]]`.
   RT7 draws that field only from the list. `_minimal` uses the first choice. RT8 skips the string
   wrong-type mutation for such a field, because Nix accepts a string there and only the model
   rejects it. A choice adds no RT8 mutation and no enum coverage target.

   **Rejecting draws.** RT7 discards a Hypothesis draw that fails the narrowed model validation
   (`reject()`). A drop in the case count can mean a validator that is too wide.

3. RT8: take a valid instance. Change one field to a value outside its type: a wrong type, an
   integer outside its bounds, an unknown enum value, null where null is not allowed, a string that
   misses its pattern, or an empty string for a `nonEmptyStr`. Build it with `model_construct` so
   that Pydantic does not stop it. Render and evaluate. **The pass rule is a type error only:** Nix
   must reject the value with a `type-error`. If Nix accepts it (`accepted`), the model is too
   tight. Another kind of rejection is its own failure class: `rejected-assertion`,
   `rejected-unknown-option`, or `rejected-other`.
4. Use a fixed Hypothesis seed per run. Record the seed. Cap the cases per subtree with an argument.

**Expected result.** RT7 finds the cross-field rules of each pilot subtree. RT8 finds no
too-tight field.

**Record.** [evidence/step-12-14.md](./evidence/step-12-14.md). Observed: RT7 cases per seed 523 to
548, every field in at least 20 cases; RT8 cases 32 (`services.postgres`) and 95
(`languages.python`).

**Gate GM8.** Met. RT7 and RT8 run, and each failure has a class.

---

## Step 14. The report and the Testee checks

**Goal.** One readable report per run. The normal gate runs the fast checks.

**Status.** Done. Commit `70d7419f5ac1`. Record: [evidence/step-12-14.md](./evidence/step-12-14.md).

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
   | `pytest` | full | the whole suite (the check is named `pytest`, not `unit`) |
   | `harness-smoke` | full | `dpy rt --smoke`: the driver echo and the five golden fixtures through RT1 to RT6 |
   | `rt-pilot` | `rt` (opt-in, not required) | RT1 to RT8 for the pilot subtrees under seeds 1 and 2, then `dpy report`; timeout 1800 s |

   `dpy report <run-id>` exits 1 only for gate FAIL (`--strict` also for BLOCKED and INCOMPLETE).
   The report cannot measure truth stability (Step 7 records it) or the warm-cache state of the
   run time.

**Expected result.** `testee verify --full` passes. `testee check rt-pilot` writes a report.

**Record.** [evidence/step-12-14.md](./evidence/step-12-14.md). `testee verify --full`: run
`20261011T125749Z-5cc9d147cc4f`, green, 2 min 12 s. `testee check rt-pilot`: run
`20261011T130004Z-0841a0d0988c`, exit 1 by design (RT7 findings). First full pilot: 2315
candidates, 426.8 s.

**Gate.** Met. `testee verify --full` passes.

---

## Step 15. The pilot: `languages.python` and `services.postgres`

**Goal.** Two subtrees reach supported status (MDL-011).

**Status.** IN PROGRESS. GM9 is not met. Record: [evidence/step-15.md](./evidence/step-15.md). Done so
far: both subtrees have narrowed models (`narrowed/services.postgres.py`, `308cf3e30afd`;
`narrowed/languages.python.py`, `ab489dad7af5`); the harness fix (`ad9476284450`); the widening
(`0dd939d802d2`). RT7 and RT8 pass for both subtrees under seeds 1 and 2 after the widening. The last
full pilot report (`20261011T140324Z-rt-pilot`, before the widening) has gate FAIL. In progress (no
result claimed): package identity by the full `$name` with attribute resolution (RT2, RT6); RT7
forcing of `config.packages` names and `enterShell`; content-addressed case directories for a warm
cache; then the final gate run.

**Lessons so far (as built).**

- A narrowed model restricts, validates, or lists choices. It adds no field (MDL-009). A
  cross-field rule is a `model_validator(mode="after")`, gated on `enable` when the module sets its
  config under `mkIf cfg.enable`.
- A package or string field with a confirmed list uses `CHOICES` (Step 13). Prove each entry with a
  probe. Package narrowing is semantic: Nix accepts any package, so RT8 cannot test it.
- A narrowed type can be too tight. `FnMarker` and `list[PathRef | PkgRef]` widened two fields so
  that real fixtures validate. The generator could make these widenings for every `functionTo` and
  `path` option; that is a concept decision, so the widenings stay in `narrowed/`.
- The comparison of a package by `pname` limits `package` choices to attributes whose `pname`
  equals the attribute name (`python3` only). This blocks wider interpreter lists until the
  identity fix lands.

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

**Record.** [evidence/step-15.md](./evidence/step-15.md): the report runs, both seeds, the RT7
coverage counts, the excluded fixtures, and every remaining `NixExpr` field
(`languages.python.import`; `services.postgres.extensions` as `NixExpr | FnMarker`). The final
report is not yet written.

**Gate GM9.** Both subtrees meet every threshold above. IN PROGRESS. The open items are in
[evidence/GATES.md](./evidence/GATES.md).

---

## Step 16. The agent skills

**Goal.** Agents run the authoring loop without changes to the harness code.

**Status.** The skills exist (commit `028e7f774899`). The trial is IN PROGRESS. Record:
[evidence/step-16.md](./evidence/step-16.md). The skill sources are `skills/<name>/SKILL.md` in
`devenv-py`. Devman links them into `.agents/skills/<name>` on a machine; edit the source only.

**Actions.**

1. Write `skills/devenv-py-harvest/SKILL.md`. Inputs: a source. Steps:
   `python -m devenv_py.corpus harvest <source>`, then `evaluate <source>` (triage, truth twice, and
   the validity check). Done when every fixture has a class and a stable truth.
2. Write `skills/devenv-py-author/SKILL.md`. Inputs: a subtree. Steps: `dpy gen`, read the
   coverage list and the fixtures, write `narrowed/<subtree>.py`, add syntax reader rules if needed,
   run `dpy rt`. Done when GM9's thresholds hold for the subtree. Point to the
   `copyroom-template-edit` skill for template changes.
3. Write `skills/devenv-py-roundtrip/SKILL.md`. Inputs: a report. Steps: pick one
   failure, find its class, fix it in the right place, rerun the failing case and then the subtree.
   Done when the case passes and no other case fails.
4. Put these rules in all three skills (MDL-005):
   - Do not edit `nix/`, `normalize.py`, `compare.py`, or `driver.py`. Report a suspected harness
     error to the owner instead.
   - Do not change a golden fixture or a truth file to make a check pass.
   - Never run a bare `uv`.
   - Record each run in the subtree's record, under
     `~/.local/state/devenv-py/<skill>/<subtree or source>/<run-id>.md`, with each line labeled
     OBSERVATION or INFERENCE.
5. Trial: give an agent the author skill for `services.redis`. Do not help it. Record the run.

**Expected result.** The agent brings `services.redis` to the thresholds with no harness code
change.

**Record.** [evidence/step-16.md](./evidence/step-16.md). It holds no trial result yet.

**Gate GM10.** The trial subtree passes with no harness code change. IN PROGRESS.

---

## After the gates

- Choose the next subtrees from the fleet census: the options that the fleet fixtures set most.
- Generate JSON Schema for `vendomat.toml` and wire it into the V6 workspace template.
- Repeat Steps 4 to 15 for the NixOS and Home Manager option trees, for Machines.
- Start the Basix curated layer as Nix modules, and run them through the same harness.

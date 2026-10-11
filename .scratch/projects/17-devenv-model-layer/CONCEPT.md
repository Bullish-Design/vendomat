# Concept: typed models for devenv modules

**Date:** 2026-10-10. **Updated:** 2026-10-11 with the findings of phase A and Steps 1 and 9.
**Status:** Draft for owner review. Every option name, command, file format,
and repository name here is proposed until a fixture proves it on the pinned tools.
**Guide:** [GUIDE-HARNESS.md](./GUIDE-HARNESS.md). **Evidence:** [evidence/step-0-probe.md](./evidence/step-0-probe.md),
[evidence/step-1.md](./evidence/step-1.md), [evidence/phase-a.md](./evidence/phase-a.md),
[evidence/step-9.md](./evidence/step-9.md).
**Builds on:** [project 16](../16-vendomat-devenv-layer/CONCEPT-V6.md) and its
[2026-10-10 update](../16-vendomat-devenv-layer/CONCEPT-UPDATE-2026-10-10.md).
**Uses:** `pydantree` (`../../../../pydantree`) and `templateer_v2` (`../../../../templateer_v2`).

## Purpose

Let a person or an agent treat a modular devenv configuration as a set of Pydantic models. The
models must stay correct as devenv changes. A mechanical test harness must prove that correctness.
Agent skills then do most of the authoring work, and the harness checks each result.

The first deliverable is the harness. The models, templates, and readers come after it, and the
harness judges them.

## The layering analogy

devenv is a curated layer over nixpkgs and the Nix module system. Its `services.postgres` is not the
NixOS `services.postgresql`. devenv reimplements the service and maps it onto nixpkgs packages by
hand. That mapping can drift from NixOS. devenv accepts the cost because a simpler vocabulary is its
product.

A Pydantic layer over devenv is the same move, one level up. The design question is not "should a
second type system exist". It is "where is the seam, and who pays to keep it in step".

Two differences from devenv shape this concept:

1. **Language.** devenv's layer is Nix modules on the same evaluator, so a broken mapping fails at
   evaluation. A Pydantic layer is in another language. Drift goes unseen unless the models are
   generated or tested. This concept does both.
2. **Who pays.** A community maintains devenv's mapping. Vendomat has one owner. The 2026-10-10
   update retired the description builder for this reason: it added "a second module language and a
   central compatibility duty". This concept must not bring that duty back.

## Decisions

1. **The seam is always a Nix `options` declaration.** Pydantic models, JSON Schema, and TOML
   shapes are generated from option declarations. Nothing flows the other way.
2. **Native modules stay the authoring contract.** Module authors keep writing native devenv, NixOS,
   and Home Manager modules. The models are tooling around those modules.
3. **A model is one module's contribution, not the merged config.** Nix keeps the merge. A model
   field that is unset means "this module defines nothing here".
4. **The test oracle is independent of the agent's work.** The ground truth for a fixture is what
   Nix evaluates from the original file. It is never the output of a reader or writer under test.
5. **The harness is code. The authoring is skills.** Code owns evaluation, normalization,
   comparison, the Nix output language, and generation of the type mapping. Agent skills own
   fixture harvest, model narrowing, templates, and repair of failures.
6. **A curated layer exists only where an audience needs it.** Basix learners are that audience.
   A curated layer is written as Nix modules with its own options. Its models are generated through
   the same pipeline.
7. **The harness lives in its own repository, `devenv-py`** (owner decision, 2026-10-11). Vendomat and Basix
   consume its outputs. Reason: it depends on `pydantree` and `templateer`, and it is useful outside
   Vendomat.

## Terms

| Term | Meaning |
| --- | --- |
| Option tree | The `options` attribute set of a `lib.evalModules` result. devenv exposes it as `devenv.project.options` (probe O6). |
| Options export | A JSON file that the harness writes from the option tree. It holds a structured type tree for each option. |
| Contribution | The definitions that a set of files gives to each option. The harness reads them from `definitionsWithLocations` (probe O7). |
| Truth | The normalized contribution of a fixture's original files. It is the test oracle. |
| Model | A generated Pydantic class for one option subtree, such as `languages.python`. |
| Writer | Code or a template that turns a model instance into a module. Path N writes Nix text. Path T writes TOML for a fixed reader module. |
| Reader | Code that turns a module into a model instance. The eval reader uses truth. The syntax reader uses pydantree over source text. |
| Escape value | A model value that holds raw Nix: `NixExpr`. Each one is a coverage miss. |
| Pin | The devenv CLI version, the `devenv` input revision, and the `nixpkgs` input revision used for one run. |

## Architecture

```text
native modules (devenv, Vendomat, Basix, workspace)
        |
        v
  devenv eval + introspect.nix --------------> options export (JSON, per pin)
        |                                               |
        |                                               v
        |                                   model generator (Python)
        |                                               |
        v                                               v
corpus fixtures --> oracle.nix --> truth      generated models + narrowed subclasses
                                    |                   |
                                    |      +------------+------------+
                                    |      v                         v
                                    |   writers                   readers
                                    |   Path N: Templateer, nix    eval reader (truth -> model)
                                    |   Path T: TOML + fixed module syntax reader (pydantree)
                                    |      |                         |
                                    v      v                         v
                              round-trip runner: RT1 to RT8 --> report
```

### Evaluation driver

`devenv eval` reaches only `devenv.config.*` (probe O2). The typed options and per-file definitions
are not config values. A module can still reach them: the module system passes `options` and
`extendModules` to every module. The harness base project therefore imports an introspection
module. The module reads a request file and writes its answer to a read-only config value,
`introspect.result`. Stock `devenv eval` reads that value (probe O10 to O12). This route needs no
fork patch, and it uses devenv's evaluation cache. The result is a JSON string for every request
kind, because `devenv eval` fails on a result that holds an attribute name with a dot. The driver
decodes the output twice (phase A, options F2). The driver is the only part of the harness that
talks to devenv. `devenv repl` is the fallback route (probe O4).

One `devenv eval` call can evaluate many candidate modules through `extendModules` (probe O8, O12).
Batch evaluation is the normal mode. Single-project evaluation is the fallback for fixtures that need
their own inputs or settings.

### Options export

The exporter walks the option tree and writes one record for each option outside a submodule. It
nests sub-options of submodule types inside the type tree, to a bounded depth. Each record holds:

- the location (`loc`), a list whose elements can hold dots; a `listOf` submodule adds `*`, and an
  `attrsOf` submodule adds its placeholder,
- the type tree. Each node holds `name`, `description`, `payload` (data only: a type becomes
  `{"$type": name}`, a function `{"$fn": true}`, a derivation `{"$pkg": name}`), `nested` types
  (`elemType`, `freeformType`, `left` and `right`, `coercedType` and `finalType`), `options` for a
  submodule, and `depthCut`,
- `hasDefault` and `default` as JSON when it serializes; `defaultText` otherwise,
- `defaultError` (the default threw or failed to serialize) and `defaultSkipped` (the option has
  `defaultText`, so the exporter does not evaluate the default),
- `readOnly`, `internal`, `visible` (raw), `description`, and `declarations`.

Three markers on type nodes keep the walk finite and honest. `recursive: true` cuts a recursive type
(JSON, YAML, TOML values): the node repeats an ancestor's description. `truncated: true` is a safety
limit that did not fire at the pin. `depthCut: true` marks a submodule that the depth limit cut. The
default depth is 8, and the export fails when any node has `depthCut`. Store hashes, the project
root, and the runtime directory are rewritten to `<store>/`, `<root>`, and `<runtime>`, so the hash
does not depend on the checkout.

The export is complete when its option set equals the set that `nixosOptionsDoc` lists. The rule
that gives that equality: list an option when `visible` is `true` or `"shallow"` and it is not
`internal`; walk its sub-options only when `visible` is `true` or `"transparent"`. At the pin the
export holds 1330 records and the doc lists 1144.

The generator reads `type.name`, `nested`, and `payload`. It does not parse the description strings
in `optionsJSON` (probe O5: 104 distinct strings at one pin). Two exceptions apply. `intBetween`
carries its bounds only in its description, so the generator reads integer bounds through a fixed
list of patterns. A format type (JSON, YAML, or TOML value) shows as `nullOr` or `either` with a
`recursive` marker, so the generator recognises it by the marker and its description (MDL-015). Each
export carries the pin and a hash of its content. A changed hash on a pin bump is the drift signal.

### Truth

The oracle keeps, for each option that a fixture mentions, the definitions whose file lies under the
fixture's directory. It does not walk the whole option tree by default. `definitionsWithLocations`
forces each surviving definition, including a default, and an uncatchable error in one default or
`mkDefault` value aborts the whole evaluation. Phase A saw this with `process.manager.command`. The
default scope is therefore `touched`: a Nix pass over the fixture's module text finds the option
paths that the fixture mentions, without reading any value. The scope `all`, with a deny list, walks
every option and serves as the cross-check. With `process.manager.command` denied, both scopes agreed
on seven fixtures.

The oracle serializes each value with tagged forms for values that JSON cannot carry:

| Nix value | Serialized form |
| --- | --- |
| Derivation | `{"$pkg": pname, "$name": name, "$output": outputName}` |
| Path | `{"$path": "<path>"}` |
| Function | `{"$fn": true}` |
| Attribute set with `_type` | `{"$type": "<_type>"}` |
| `mkMerge` inside a value | `{"$merge": [...]}` |
| A `throw` or `assert` failure | `{"$error": "throw or assert"}`, a fixed marker with no message |

The serializer discharges property wrappers inside attribute sets and lists: a false `mkIf` drops
the element, and a true `mkIf`, `mkOverride`, or `mkOrder` keeps its content. A wrapper never
reaches the output. A definition that throws on a catchable error becomes a record with an `error`
string, and the normalizer turns it into `$error`.

A Python normalizer then sorts keys, replaces `/nix/store/<hash>-` with `<store>/`, makes `$path`
values relative, drops `file` and `$name`, and folds several definitions from one fixture into one
value with the option's merge rule from the options export. It folds `listOf` by concatenation,
`attrsOf` and submodules by recursive union, and `separatedString` by joining with its separator.
It writes any other multi-definition as `{"$multi-def": [...]}`.

`definitionsWithLocations` drops definitions that lose on priority, so a losing definition vanishes
from truth. A false `mkIf` leaves no definition, or an empty element inside a freeform value. The
priority of the winning definition is not visible: a `mkForce` or `mkDefault` value appears as the
plain value. The truth therefore cannot see `mkDefault`, `mkForce`, or a false `mkIf`. The syntax
reader covers those forms (RT3, RT4). Priority between two definitions inside one freeform
attribute set is also invisible.

The oracle does not force `config`. It cannot tell whether a fixture evaluates, so the corpus needs
a separate validity check for the `fails` class.

### Model generator

The generator maps type names to Python types. It emits one module per subtree, with a pin stamp.

| Nix `type.name` | Python type |
| --- | --- |
| `bool` | `bool` |
| `str`, `nonEmptyStr`, `singleLineStr`, `strMatching "<pattern>"` | `str`, with a pattern where the type has one; the name carries the pattern and `payload.pattern` holds it raw |
| `separatedString` (`lines`, `commas`) | `Lines`, a `str` subtype that records its separator |
| `int`, `signedInt*`, `unsignedInt*`, `positiveInt`, `intBetween` | `int` with `ge` and `le` |
| `float`, `number` | `float`. `number` has no name at the pin: it is `either int float`, and the generator folds that pair to `float` |
| `enum` | `Literal[...]` |
| `nullOr` | `T \| None` |
| `listOf` | `list[T]` |
| `attrsOf`, `lazyAttrsOf` | `dict[str, T]` |
| `submodule` | A nested `BaseModel`; a freeform submodule allows extra keys of its freeform type |
| `either`, `oneOf` | `T1 \| T2`, except `either int float` |
| `coercedTo` | the final type |
| `package` | `PkgRef` |
| `path`, `pathInStore`, `externalPath` | `PathRef`. At the pin all three appear as `path`; the payload `{absolute, inStore}` tells them apart |
| `anything`, `unspecified`, `raw`, `attrs` | `JsonValue`, with a coverage warning |
| format types (JSON, YAML, TOML value) | `JsonValue`, with a coverage warning. The export shows them as `nullOr` or `either` with a `recursive` marker (28 options at the pin); the generator recognises them by that marker and the description |
| `output`, `outputOf` | `NixExpr`, a coverage miss. They are devenv types (`src/modules/outputs.nix`) and have no Python shape yet |
| `functionTo`, `deferredModule`, `module`, any unknown name | `NixExpr`, a coverage miss |

The pinned export holds 26 distinct type names (census in
[evidence/phase-a.md](./evidence/phase-a.md)). The names `nonEmptyStr`, `singleLineStr`,
`signedInt*`, `positiveInt`, `raw`, `module`, and `attrTag` do not occur at the pin. Their rows are
untested against a real export. The generator tests use synthetic export entries for them. An
`enum` payload is `{ values = [...]; }`. `unsignedInt` and `unsignedInt16` carry their bounds in the
name, and `intBetween` carries them only in its description. A bound added with `addCheck` on `int`
is invisible.

Every field of a generated model defaults to unset. Writers render with `exclude_unset=True`. Option
defaults appear in field descriptions, not as values (decision 3).

Shared value types:

| Type | Holds | Renders as |
| --- | --- | --- |
| `PkgRef` | an attribute path, such as `jq` or `python3Packages.ruff`, and an optional output | `pkgs.jq`, `pkgs.jq.bin` |
| `PathRef` | a path relative to the module file | `./relative/path` |
| `NixExpr` | raw Nix source | the source, unchanged |
| `Priority[T]` | a value and `default`, `force`, or an integer | `lib.mkDefault v`, `lib.mkForce v`, `lib.mkOverride n v` |
| `Lines` | a string and its separator | a Nix string |

A truth value `{"$pkg": "jq", "$output": "bin"}` does not name its attribute path. The eval reader
looks up candidates in a package index for the pin. An ambiguous lookup is a recorded miss.

Agents narrow generated classes by subclassing, as pydantree narrows node classes. A narrowed class
may add validators and tighter types. It may not add fields that the option tree lacks. The generator
checks this rule when it loads a narrowed class.

### Writers

**Path N (Nix text).** A Templateer template renders a model instance as a devenv module. Templateer
needs a `nix` output language for this: string escaping, a parse validator, and a data round-trip
check. The template set is small and generic: one template for a module and recursive macros for
values. Narrowed subtrees may add their own templates.

**Path T (TOML data).** A writer emits TOML. A fixed reader module reads it with `builtins.fromTOML`
and maps keys to option paths one to one. Path T fits only data. A model with `PkgRef`, `PathRef`,
`Priority`, or `NixExpr` values needs Path N, or a tagged TOML form that the fixed module decodes.
V6 `vendomat.toml` is a Path T surface today.

### Readers

**Eval reader.** It validates truth against the model. It sees the true value of every option,
including values from `let`, functions, and imports. It cannot see priorities or a false `mkIf`, and
it sees a package only as a name.

**Syntax reader.** It parses source with pydantree and the tree-sitter Nix grammar (probe O9). It
reads literal bindings into model fields. It keeps every non-literal value as a `NixExpr` that holds
the exact source span. So it can read every file in full: literal parts become typed fields, and the
rest passes through unchanged. It also sees `lib.mkDefault`, `lib.mkForce`, `lib.mkIf`, and
`with pkgs;` forms. It refuses a file that the grammar reports as having a parse error.

Phase A ran a prototype over 59 fleet files and set these rules:

- **Root `let`.** Half of the fleet files (28 of 58) start with a root `let`. The earlier rule kept
  the whole body as one `NixExpr`, which gives such a file no typed field. The reader now keeps the
  `let` header as verbatim prefix text, reads the attribute set in the body, and writes the prefix
  back unchanged. A value that uses a name from the header stays `NixExpr`.
- **Extra bindings.** An `inherit`, an `inherit (x)`, a dynamic attribute name, and an attribute
  collision go into the model field `extra_bindings`, as `NixExpr` values of the binding text.
- **Strings.** A string with an interpolation stays one `NixExpr`. Interpolation causes 81 percent of
  the `NixExpr` values outside the root `let`. A parts list may replace this rule later.
- **Priority.** The reader keeps the function name with the number (`mkDefault` 1000, `mkForce` 50,
  `mkOverride n`), so that `lib.mkDefault 1` and `lib.mkOverride 1000 1` stay apart (RT5).
- **Scope of names.** A name that the function head binds shadows `with pkgs;`, so it is not a
  package.
- **Node kinds.** The real kinds differ from the first guess: `true`, `false`, and `null` are
  `variable_expression` nodes, a negative number is a `unary_expression`, and an attribute set holds a
  `binding_set` of `binding`, `inherit`, and `inherit_from` nodes. Guide Step 11 lists them.

### Round-trip checks

| Check | Input | Pass condition |
| --- | --- | --- |
| RT1 schema | truth | truth validates against the model; count the escape values |
| RT2 eval round trip | truth | truth -> model -> Path N -> evaluate -> equals truth |
| RT3 syntax round trip | source | source -> syntax reader -> model -> Path N -> evaluate -> equals truth |
| RT4 reader agreement | source and truth | each literal field that the syntax reader sets equals the eval reader's field |
| RT5 idempotence | model | render(read_syntax(render(m))) is the same text as render(m) |
| RT6 TOML path | data-only model | model -> TOML -> fixed module -> evaluate -> equals the model's own truth |
| RT7 generated acceptance | model instances from Hypothesis | Nix accepts each instance, and its truth equals the instance |
| RT8 rejection agreement | invalid instances from mutation | Pydantic rejects the value, and Nix also rejects it |

RT7 and RT8 test the type mapping itself. A value that Pydantic accepts and Nix rejects means the
model is too loose. A value that Pydantic rejects and Nix accepts means the model is too tight.

### Corpus

| Source | Count at the probe pin | Use |
| --- | --- | --- |
| devenv `examples/` | 69 directories, 72 `devenv.nix` files (3 nested) | RT1 to RT5 |
| devenv `tests/` | 150 entries, 159 `devenv.nix` files (some nest) | RT1 to RT5, after triage |
| The owner's fleet: every `devenv.nix` under `~/Documents/Projects`, without `.archive/` and `.worktrees/`, deduplicated by content | 407 files in all; 266 sit under `.archive/` or `.worktrees/`; 104 unique contents over primary paths | RT1 to RT5; the realistic set. Fleet-module options (`repoman`, `testee`, `docman`, `zelligate`) need those modules in a later pin variant |
| Public repositories that hold a `devenv.nix` | not counted | RT1 to RT5; check licenses before vendoring |
| Generated by Hypothesis from each model | unbounded | RT7, RT8 |

Each fixture keeps its source, its inputs, a provenance record, and its truth for one pin. The counts
are from the phase A static survey at pin `devenv-2.4.0-b904dcb5-c2f38fe7`. The survey predicts that
the pilot gate holds (87 deduplicated `languages.python` fixtures and 13 `services.postgres`
fixtures, and 23 and 10 from the public sources alone). It evaluated no fixture. A fixture
is batchable when its inputs are a subset of the base project's inputs and it sets no project
settings. Other fixtures are evaluated alone.

## Bootstrap through agent skills

The harness turns authoring into a loop with a mechanical verdict. Three skills run that loop.

| Skill | Input | Output | Verdict |
| --- | --- | --- | --- |
| `devenv-py-harvest` | a source of examples | fixtures with provenance and truth | the fixture evaluates and its truth is stable across two runs |
| `devenv-py-author` | one subtree, its options export, and its fixtures | a narrowed model, templates, and syntax-reader rules | RT1 to RT8 for that subtree |
| `devenv-py-roundtrip` | a failing report | a fix to the model, template, or reader | the failing case passes and no passing case fails |

The existing `copyroom-template-edit` skill covers Templateer source edits. The author skill uses it.

The skills never edit the oracle, the normalizer, or the comparison. A change to those parts is a
code change with its own review.

## Curated layer for Basix

A curated layer gives learners a smaller vocabulary than devenv's. It is written as Nix modules
that declare their own options and set devenv options. The harness treats it as one more module set:
the same options export, the same generated models, and the same checks. Because the mapping is in
Nix, evaluation catches a broken mapping.

Templateer's generation pipeline then lets a large language model (LLM) fill a curated model from a
learner's request. The model is validated before any Nix is written.

## Relation to Vendomat V6

- The project 16 update asks: "Which registry table carries supported values, and which value types
  does it allow?" This concept answers: the module's own `options`. The supported value types are
  the types that the generator maps without an escape value.
- `vendomat sync` can validate `vendomat.toml` against generated models before it writes the
  fragment.
- Generated JSON Schema gives editor completion and checks for `vendomat.toml` and `devenv.yaml`.
- The input-layer wall stays. A model does not change evaluation order. A step before shell entry is
  still needed.
- The workspace templates stay Templateer templates. Path N adds a `nix` output language to the same
  tool.

## Opportunities

- Editor support from generated JSON Schema.
- LLM-generated configurations that pass validation before any Nix exists.
- Project rules as validators, such as a disko model that rejects `/dev/sdX` names.
- Typed fleet queries, such as "which workspaces enable postgres".
- A readable change plan from a comparison of two models before a render.
- Codemods for option renames on a devenv bump, through the syntax reader.
- The same pipeline for NixOS and Home Manager option trees, for Machines.

## Risks and controls

| Risk | Control |
| --- | --- |
| The models drift from devenv | Generate from the options export; compare export hashes on each pin bump; rerun the corpus |
| A reader and a writer share an error and still agree | The oracle is Nix evaluation of the original source (decision 4) |
| The introspection route breaks on a later pin | One driver module owns it; the repl route is the fallback |
| Batch evaluation hides a failure in one candidate | `tryEval` catches only `throw` and `assert`; on any other batch error, bisect the batch |
| One option's default aborts the whole evaluation | The oracle reads only the options that a fixture mentions (touched scope); `scope = "all"` is a cross-check with a deny list |
| A fixture has a truth although devenv rejects it | A validity check for the `fails` class (guide Step 7) |
| Evaluation cost limits generated cases | Batch through `extendModules`; cap cases per subtree; measure first |
| Nix string escaping errors | The `nix` language in Templateer owns escaping, with its own tests |
| A curated layer becomes a central duty again | Build one only for a named audience; write it in Nix |
| The models become the authoring contract by habit | Requirement MDL-002 |

## Requirements (proposed)

| ID | Requirement |
| --- | --- |
| MDL-001 | Every model, JSON Schema, and TOML shape is generated from a Nix option declaration at a recorded pin. |
| MDL-002 | Native Nix modules remain the authoring contract. No module author is required to write a model. |
| MDL-003 | A model represents one module's contribution. Unset fields render nothing. |
| MDL-004 | Truth comes from Nix evaluation of the original fixture source through `definitionsWithLocations`. |
| MDL-005 | The oracle, normalizer, and comparison are code with their own tests. Skills do not edit them. |
| MDL-006 | Every options export records the devenv CLI version, the `devenv` input revision, the `nixpkgs` input revision, and a content hash. |
| MDL-007 | **Superseded by MDL-015.** The generator reads `type.name`, `nestedTypes`, and functor payloads. It parses a type description string only for integer bounds, through a fixed list of patterns that its tests name. |
| MDL-008 | An unmapped type becomes `NixExpr`, and the report counts it as a coverage miss. |
| MDL-009 | A narrowed model class adds no field that the option tree lacks. |
| MDL-010 | The syntax reader keeps every non-literal value as a `NixExpr` with its exact source span. |
| MDL-011 | A subtree is supported only when RT1 to RT8 pass for it at the current pin. |
| MDL-012 | The harness keeps raw logs outside the repository, under `~/.local/state/devenv-py/`. |
| MDL-013 | A batch failure that `tryEval` does not catch leads to bisection, not to a failed batch. |
| MDL-014 | A curated layer is written as Nix modules with their own options. |
| MDL-015 | The generator reads `type.name`, `nested` types, payloads, and the export markers. It parses a type description string for two uses only: integer bounds of `intBetween`, and recognition of a format type that carries the `recursive` marker. Each use goes through a fixed list of patterns that its tests name. Supersedes MDL-007. |
| MDL-016 | The options export fails when any node carries `depthCut`. Its option set equals the set that `nixosOptionsDoc` lists under the doc rule. |
| MDL-017 | The oracle reads only the options that a fixture mentions (`scope = "touched"`) by default. The scope `all`, with a deny list, is the cross-check. |
| MDL-018 | The syntax reader refuses a file with a parse error. It keeps a root `let` header as verbatim prefix text. |
| MDL-019 | Every typed literal that the syntax reader sets equals the Nix evaluation of its source slice. |

## Gates

| Gate | Proves | Guide step |
| --- | --- | --- |
| GM0 | The evaluation surfaces exist at a pin | Step 0 (observed; see evidence) |
| GM1 | The driver evaluates a batch and returns parsed JSON | Steps 2, 3 |
| GM2 | The options export is complete and structured | Step 4 |
| GM3 | Truth is stable and correct on hand-checked fixtures | Steps 5, 6 |
| GM4 | The corpus is harvested and triaged | Step 7 |
| GM5 | The generator maps types and stamps the pin | Step 8 |
| GM6 | Templateer has a `nix` output language | Step 9 (landed; tag open) |
| GM7 | Writers and readers exist | Steps 10, 11 |
| GM8 | The round-trip runner reports RT1 to RT8 | Steps 12, 13 |
| GM9 | The pilot subtrees pass | Step 15 |
| GM10 | The three skills run the loop on a new subtree | Step 16 |

## Open questions

1. Resolved 2026-10-11: the repository is `devenv-py`.
2. Resolved 2026-10-11: no fork patch. The introspection module works with stock `devenv eval`
   (probe O10 to O12). Revisit only if a later pin breaks that route and the repl fallback.
3. How should the eval reader name packages: a package index per pin, or a rule that prefers the
   syntax reader for `packages`?
4. Which subtrees come after the pilot (`languages.python`, `services.postgres`)?
5. Resolved 2026-10-11: GM9 uses the thresholds in Step 15 of the guide. Correctness checks
   must be perfect, coverage must not fall, generated cases are sized by coverage, and a small
   corpus blocks the gate.
6. Should Path T support tagged values (`{"$pkg": ...}`) in TOML, or should such models use Path N
   only?
7. Which `templateer` tag carries the `nix` language? Step 9 landed on `main` at `d3304db4` with no
   tag. The pinned tag `v0.4.2` is on the `v6-flake` branch.
8. Should a string with an interpolation read as a parts list (literal text plus `NixExpr` holes)
   instead of one `NixExpr`? The fleet run shows interpolation as the main cost after the root `let`.

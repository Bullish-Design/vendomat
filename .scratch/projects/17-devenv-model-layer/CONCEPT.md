# Concept: typed models for devenv modules

**Date:** 2026-10-10. **Status:** Draft for owner review. Every option name, command, file format,
and repository name here is proposed until a fixture proves it on the pinned tools.
**Guide:** [GUIDE-HARNESS.md](./GUIDE-HARNESS.md). **Evidence:** [evidence/step-0-probe.md](./evidence/step-0-probe.md).
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
7. **The harness lives in its own repository.** Proposed name: `devenv-models`. Vendomat and Basix
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
  devenv repl + options.nix ------------------> options export (JSON, per pin)
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
sit under `devenv.project` (probe O6, O7). The driver therefore runs `devenv repl`, feeds it a short
script on standard input, and reads the JSON result (probe O4). The driver is the only part of the
harness that talks to devenv. A later fork patch can add a direct command, such as
`devenv eval --root project`, without a change to the rest of the harness.

One repl process can evaluate many candidate modules through `extendModules` (probe O8). Batch
evaluation is the normal mode. Single-project evaluation is the fallback for fixtures that need
their own inputs or settings.

### Options export

The exporter walks the option tree and writes, for each option:

- the location (`loc`),
- the type tree: `type.name`, enum values, bounds, and nested types, recursively,
- sub-options of submodule types, to a bounded depth,
- the default, as JSON when it serializes, and as `defaultText` otherwise,
- `readOnly`, `internal`, `visible`, `description`, and `declarations`.

The generator reads `type.name`, `nestedTypes`, and functor payloads. It does not parse the
description strings in `optionsJSON` (probe O5: 104 distinct strings at one pin). One exception
applies: `ints.between` carries its bounds only in its description, so the generator reads integer
bounds through a fixed list of patterns (MDL-007). Each export carries the pin and a hash of
its content. A changed hash on a pin bump is the drift signal.

### Truth

The oracle walks the option tree. For each option it keeps the definitions whose file lies under the
fixture's directory. It serializes each value with tagged forms for values that JSON cannot carry:

| Nix value | Serialized form |
| --- | --- |
| Derivation | `{"$pkg": pname, "$name": name, "$output": outputName}` |
| Path | `{"$path": "<relative or store-normalized path>"}` |
| Function | `{"$fn": true}` |
| Attribute set with `_type` | `{"$type": "<_type>"}` |
| A `throw` or `assert` failure | `{"$error": "<message>"}` |

A Python normalizer then sorts keys, replaces `/nix/store/<hash>-` with `<store>/`, and folds several
definitions from one fixture into one value with the option's merge rule. It folds `listOf` by
concatenation, `attrsOf` by recursive union, and `lines` by joining with a newline. It flags any
other multi-definition as `multi-def`.

`definitionsWithLocations` drops definitions that lose on priority and removes `mkIf` wrappers. The
truth therefore cannot see `mkDefault`, `mkForce`, or a false `mkIf`. The syntax reader covers those
forms (RT3, RT4).

### Model generator

The generator maps type names to Python types. It emits one module per subtree, with a pin stamp.

| Nix `type.name` | Python type |
| --- | --- |
| `bool` | `bool` |
| `str`, `nonEmptyStr`, `singleLineStr`, `strMatching` | `str`, with a pattern where the type has one |
| `separatedString` (`lines`, `commas`) | `Lines`, a `str` subtype that records its separator |
| `int`, `signedInt*`, `unsignedInt*`, `positiveInt`, `intBetween` | `int` with `ge` and `le` |
| `float`, `number` | `float` |
| `enum` | `Literal[...]` |
| `nullOr` | `T \| None` |
| `listOf` | `list[T]` |
| `attrsOf`, `lazyAttrsOf` | `dict[str, T]` |
| `submodule` | A nested `BaseModel`; a freeform submodule allows extra keys of its freeform type |
| `either`, `oneOf` | `T1 \| T2` |
| `coercedTo` | the final type |
| `package` | `PkgRef` |
| `path`, `pathInStore`, `externalPath` | `PathRef` |
| `anything`, `unspecified`, `raw`, `attrs`, format types (`YAML 1.1 value`) | `JsonValue`, with a coverage warning |
| `functionTo`, `deferredModule`, `module`, any unknown name | `NixExpr`, a coverage miss |

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
`with pkgs;` forms.

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
| devenv `examples/` | 69 directories | RT1 to RT5 |
| devenv `tests/` | 156 entries | RT1 to RT5, after triage |
| The owner's fleet: every `devenv.nix` under `~/Documents/Projects` | not counted | RT1 to RT5; the realistic set |
| Public repositories that hold a `devenv.nix` | not counted | RT1 to RT5; check licenses before vendoring |
| Generated by Hypothesis from each model | unbounded | RT7, RT8 |

Each fixture keeps its source, its inputs, a provenance record, and its truth for one pin. A fixture
is batchable when its inputs are a subset of the base project's inputs and it sets no project
settings. Other fixtures are evaluated alone.

## Bootstrap through agent skills

The harness turns authoring into a loop with a mechanical verdict. Three skills run that loop.

| Skill | Input | Output | Verdict |
| --- | --- | --- | --- |
| `devenv-models-harvest` | a source of examples | fixtures with provenance and truth | the fixture evaluates and its truth is stable across two runs |
| `devenv-models-author` | one subtree, its options export, and its fixtures | a narrowed model, templates, and syntax-reader rules | RT1 to RT8 for that subtree |
| `devenv-models-roundtrip` | a failing report | a fix to the model, template, or reader | the failing case passes and no passing case fails |

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
| The repl interface changes | One driver module owns it; a fork patch can replace it |
| Batch evaluation hides a failure in one candidate | `tryEval` catches only `throw` and `assert`; on any other batch error, bisect the batch |
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
| MDL-007 | The generator reads `type.name`, `nestedTypes`, and functor payloads. It parses a type description string only for integer bounds, through a fixed list of patterns that its tests name. |
| MDL-008 | An unmapped type becomes `NixExpr`, and the report counts it as a coverage miss. |
| MDL-009 | A narrowed model class adds no field that the option tree lacks. |
| MDL-010 | The syntax reader keeps every non-literal value as a `NixExpr` with its exact source span. |
| MDL-011 | A subtree is supported only when RT1 to RT8 pass for it at the current pin. |
| MDL-012 | The harness keeps raw logs outside the repository, under `~/.local/state/devenv-models/`. |
| MDL-013 | A batch failure that `tryEval` does not catch leads to bisection, not to a failed batch. |
| MDL-014 | A curated layer is written as Nix modules with their own options. |

## Gates

| Gate | Proves | Guide step |
| --- | --- | --- |
| GM0 | The evaluation surfaces exist at a pin | Step 0 (observed; see evidence) |
| GM1 | The driver evaluates a batch and returns parsed JSON | Steps 2, 3 |
| GM2 | The options export is complete and structured | Step 4 |
| GM3 | Truth is stable and correct on hand-checked fixtures | Steps 5, 6 |
| GM4 | The corpus is harvested and triaged | Step 7 |
| GM5 | The generator maps types and stamps the pin | Step 8 |
| GM6 | Templateer has a `nix` output language | Step 9 |
| GM7 | Writers and readers exist | Steps 10, 11 |
| GM8 | The round-trip runner reports RT1 to RT8 | Steps 12, 13 |
| GM9 | The pilot subtrees pass | Step 15 |
| GM10 | The three skills run the loop on a new subtree | Step 16 |

## Open questions

1. Is `devenv-models` the right repository name and home?
2. Should the fork carry a patch for direct project evaluation, so that the driver does not need the
   repl?
3. How should the eval reader name packages: a package index per pin, or a rule that prefers the
   syntax reader for `packages`?
4. Which subtrees come after the pilot (`languages.python`, `services.postgres`)?
5. What pass thresholds should GM9 use? The guide proposes 100 percent of evaluable fixtures for
   RT2, and 500 generated cases without a mismatch for RT7.
6. Should Path T support tagged values (`{"$pkg": ...}`) in TOML, or should such models use Path N
   only?

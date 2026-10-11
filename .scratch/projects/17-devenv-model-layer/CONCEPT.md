# Concept: typed models for devenv modules

**Date:** 2026-10-10. **Updated:** 2026-10-11 with the implementation of Steps 2 to 14, the pilot
work of Step 15, the Step 16 skills, and the final records of gates GM9 and GM10.
**Status:** Draft for owner review. The harness exists in `devenv-py` (Steps 1 to 16 done; gates GM0
to GM10 pass, with named open items in [evidence/GATES.md](./evidence/GATES.md)). Five subtrees are
supported at the pin: `languages.python`, `services.postgres`, `services.redis` (generated-only),
`languages.javascript`, and `languages.rust`. A design item marked "proposed" stays proposed until
its fixture passes. Every other new option name, command, and file format is proposed until a
fixture proves it on the pinned tools.
**Guide:** [GUIDE-HARNESS.md](./GUIDE-HARNESS.md). **Evidence:** [evidence/GATES.md](./evidence/GATES.md),
[step-0-probe.md](./evidence/step-0-probe.md), [step-1.md](./evidence/step-1.md),
[phase-a.md](./evidence/phase-a.md), [step-2-3.md](./evidence/step-2-3.md),
[step-4.md](./evidence/step-4.md), [step-5-6.md](./evidence/step-5-6.md),
[step-7.md](./evidence/step-7.md), [step-8.md](./evidence/step-8.md),
[step-9.md](./evidence/step-9.md), [step-10.md](./evidence/step-10.md),
[step-11.md](./evidence/step-11.md), [step-12-14.md](./evidence/step-12-14.md),
[step-15.md](./evidence/step-15.md), [step-15-final.md](./evidence/step-15-final.md),
[step-16.md](./evidence/step-16.md), [step-16-final.md](./evidence/step-16-final.md).
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
their own inputs or settings. Measured at the pin: about 0.06 s per candidate at 50 candidates or
more, against 2.8 s for the whole-tree oracle of phase A ([step-2-3.md](./evidence/step-2-3.md)).

**The evaluation cache keys on the request file path** ([step-7.md](./evidence/step-7.md),
refuting the phase-A claim of one entry per project). The driver therefore writes each request to a
content-addressed path, `requests/<sha256 of the canonical JSON>.json` (MDL-026, superseded by
MDL-037). Generated cases also use content-addressed directories, `cases/<sha256 of all files>/`
(MDL-037, done). A rerun of the same request therefore hits the cache: the four-subtree gate took
103.4 s cold and 13.2 s warm ([step-15-final.md](./evidence/step-15-final.md)).

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
values relative, drops `file`, keeps `$name` (MDL-036; the earlier rule that dropped `$name` is
superseded), and folds several definitions from one fixture into one
value with the option's merge rule from the options export. It folds `listOf` by concatenation,
`attrsOf` and submodules by recursive union, and `separatedString` by joining with its separator. A
`nullOr X` option takes the rule of `X`. It writes any other multi-definition as
`{"$multi-def": [...]}`. It also rewrites `/tmp/devenv-<7hex>` and `/run/user/N/devenv-<7hex>` to
`<runtime>`, the project directories and the fixture root to `<root>`, the repository checkout to
`<checkout>`, and the home directory to `<home>`, in every string and object key (MDL-027). A path
canonicalizer makes `./.` and `.` equal (MDL-036).

`definitionsWithLocations` drops definitions that lose on priority, so a losing definition vanishes
from truth. A false `mkIf` leaves no definition, or an empty element inside a freeform value. The
priority of the winning definition is not visible: a `mkForce` or `mkDefault` value appears as the
plain value. The truth therefore cannot see `mkDefault`, `mkForce`, or a false `mkIf`. The syntax
reader covers those forms (RT3, RT4). Priority between two definitions inside one freeform
attribute set is also invisible.

The oracle does not force `config`. It cannot tell whether a fixture evaluates, so the corpus needs
a separate validity check for the `fails` class. That check is `nix/validity.nix`, a triage probe
that tests undeclared options, forces each touched option to shallow depth, and probes
`config.enterShell`. It is not a full shell build, so it misses a failure inside a nested value
([step-7.md](./evidence/step-7.md)).

### Model generator

The generator maps type names to Python types. It emits one module per subtree, with a pin stamp.

| Nix `type.name` | Python type |
| --- | --- |
| `bool` | `StrictBool` |
| `str`, `nonEmptyStr`, `singleLineStr`, `strMatching "<pattern>"` | `str`, with a pattern where the type has one; the name carries the pattern and `payload.pattern` holds it raw |
| `separatedString` (`lines`, `commas`) | `Lines`, a `str` subtype that records its separator |
| `int`, `signedInt*`, `unsignedInt*`, `positiveInt`, `intBetween` | `StrictInt` with `ge` and `le` |
| `float`, `number` | `StrictFloat` for `float`. `number` has no name at the pin: it is `either int float`, and the generator maps that pair to `StrictInt \| StrictFloat`, because Nix `number` accepts an integer (MDL-029) |
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
| `functionTo`, `deferredModule`, `module`, any unknown name | `NixExpr`, a coverage miss. A narrowed model may widen a function-typed field to `NixExpr \| FnMarker` (MDL-021) |

The pinned export holds 26 distinct type names (census in
[evidence/phase-a.md](./evidence/phase-a.md)). The names `nonEmptyStr`, `singleLineStr`,
`signedInt*`, `positiveInt`, `raw`, `module`, and `attrTag` do not occur at the pin. Their rows are
untested against a real export. The generator tests use synthetic export entries for them. An
`enum` payload is `{ values = [...]; }`. `unsignedInt` and `unsignedInt16` carry their bounds in the
name, and `intBetween` carries them only in its description. A bound added with `addCheck` on `int`
is invisible.

Every field of a generated model defaults to unset. Writers render with `exclude_unset=True`. Option
defaults appear in field descriptions, not as values (decision 3).

The generator is stricter than lax Pydantic. Lax mode accepts `"yes"` for a bool and turns an integer
into a float, and Nix rejects both. A scalar field therefore uses `StrictBool`, `StrictInt`, or
`StrictFloat` (MDL-029). An intermediate option path becomes a group class named by its path, at
module level, children before parents. A read-only option is left out of the model. A renamed or alias option
(`mkRenamedOptionModule`, `mkAliasOptionModule`) is left out too (MDL-035): a value written to it
lands in the target option, which has its own field. A coverage entry
has one of four kinds: `nix-expr` (an MDL-008 miss), `json-value` (loosened), `bounds-lost` (a
pattern, separator, or `intBetween` bound that the export does not carry), and `renamed` (the reason
reads `renamed -> <target>`). At the pin the pilot
models cover 15 of 16 fields (`services.postgres`) and 38 of 39 (`languages.python`); the whole
export gives 1242 fields in 45 subtrees, 24 with `NixExpr` and 68 with `JsonValue`
([step-8.md](./evidence/step-8.md)).

Shared value types:

| Type | Holds | Renders as |
| --- | --- | --- |
| `PkgRef` | an attribute path, such as `jq` or `python3Packages.ruff`, and an optional output | `pkgs.jq`, `pkgs.jq.bin` |
| `PathRef` | a path relative to the module file | `./relative/path` |
| `NixExpr` | raw Nix source | the source, unchanged |
| `Priority[T]` | a value and `default`, `force`, or an integer | `lib.mkDefault v`, `lib.mkForce v`, `lib.mkOverride n v` |
| `Lines` | a string and its separator | a Nix string |
| `FnMarker` | the eval marker `{"$fn": true}`; it holds no source | nothing: no writer renders it (the fixture is `has-fn`) |

A truth value `{"$pkg": "jq", "$output": "bin"}` does not name its attribute path. The eval reader
looks up candidates in a package index for the pin. An ambiguous lookup is a recorded miss.

Agents narrow generated classes by subclassing, as pydantree narrows node classes. A narrowed class
may add validators and tighter types. It may not add fields that the option tree lacks. The generator
checks this rule when it loads a narrowed class.

A narrowed class may also set a class variable `CHOICES`, a map from a package or string field to the
only values that Nix accepts for it (MDL-022). Example: `languages.python.uv.package` takes `uv`
only, because the module runs `${cfg.uv.package}/bin/uv`. RT7 draws such a field only from its
choices. A cross-field rule is a validator, gated on `enable` when the module sets its `config`
under `mkIf cfg.enable`. The generator discards a draw that fails the narrowed validation
(MDL-025). A narrowed type can also be too tight for real input: a function-typed option holds
`{"$fn": true}` in truth, and `listOf types.path` accepts a derivation. The pilot widened both
(`FnMarker`, `list[PathRef | PkgRef]`). The generator could apply the same widening to every
`functionTo` and `path` option. That is a decision for later.

### Writers

**Path N (Nix text).** A Templateer template renders a model instance as a devenv module. Templateer
needs a `nix` output language for this: string escaping, a parse validator, and a data round-trip
check. The template set is small and generic: one template for a module (a loop over
`{loc, value}` definitions). Narrowed subtrees may add their own templates. Three rules came from
the build:

- The template cannot carry the function head, the root `let` header, or extra bindings, because the
  lint forces the `nix` filter on every site. The writer splices those three parts around the
  rendered definitions.
- `render` writes one canonical layout: all definitions merge into one tree, and each leaf becomes
  one dotted binding (MDL-023). A set inside a list or a tagged value stays a set.
- The `nix` filter refuses null. The writer writes null as `{"$nix": "null"}`, which renders as
  `(null)`. The filter wraps a `$nix` value in parentheses at an atom position. A `$path` of `.`
  renders as `./.`.

A writer skips a value that it cannot carry. The skip has a stable reason: `has-fn`, `marker`,
`path-outside-root`, `toml-nix`, `toml-priority`, or `toml-null`. A skip is not a failure.

**Path T (TOML data).** A writer emits TOML. A fixed reader module reads it with `builtins.fromTOML`
and maps keys to option paths one to one. Path T fits only data. A model with `PkgRef`, `PathRef`,
`Priority`, or `NixExpr` values needs Path N, or a tagged TOML form that the fixed module decodes.
V6 `vendomat.toml` is a Path T surface today.

### Readers

**Eval reader.** It validates truth against the model. It sees the true value of every option,
including values from `let`, functions, and imports. It cannot see priorities or a false `mkIf`, and
it sees a package only as a name. **Superseded by MDL-036:** the first build resolved a `$pkg` by
evaluating candidate attributes (`pname` and `<set>.<pname>`) and matching `pname` and output. A
`pname` that differs from the attribute name (`gcc` gives `gcc-wrapper`) was a miss. The rule in
force is under "Package identity" below. The reader sets `PkgRef.output` to `None` for the default
output.

**Package identity (done; MDL-036, which supersedes MDL-020).** The `pname` rule failed on real
fixtures. Truth kept the `pname` `requests`, the writer rendered `pkgs.requests`, and the attribute
was `python3Packages.requests`. The `pname` `uv` fits both `uv` and `python3Packages.uv`. The `pname`
`python3` fits `python311` to `python315`. The rule now: the normalizer keeps the full `$name`; the
reader keys a package by `(pname, output, name)` and resolves a name to an attribute by evaluation in
one batch (candidates: the `pname`; a versioned name such as `python3-3.12.x` gives `python312`;
sets from the name prefix, then the subtree hint; several attributes with one name: the first wins).
RT2 and RT6 resolve truth packages in one batch. A package with no attribute path gives the skip
`pkg-unresolved`. Commit `4af72fe743ba`; result in
[step-15-final.md](./evidence/step-15-final.md). One limit stays: Templateer drops `.out`, so a
`pkgs.x.out` whose default output is not `out` renders as `pkgs.x`. No fixture hits it.

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
  the `NixExpr` values outside the root `let` in phase A, and 60.2 percent of all `NixExpr` values in
  the port (159 of 264). A parts list may replace this rule later.
- **Root `let` constants (MDL-042).** A name that the root `let` binds once to a plain literal
  (string without interpolation, number, or boolean) reads as that literal, and `${name}` inside a
  string reads as its text. A name bound twice, or by `inherit`, is not a constant. A function,
  `rec`, a nested `let`, and `with` stay one `NixExpr`.
- **Paths.** A plain `./x` or `../x` literal (no interpolation) reads as a typed `$path` value
  (MDL-028). `<x>`, `/abs`, `~/x`, and an interpolated path stay `NixExpr`.
- **No outer parentheses.** A `NixExpr` never carries outer parentheses: `x = (a b);` reads as `a b`.
  The writer adds parentheses where an atom needs them.
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
| RT5 idempotence | model | render(read_syntax(render(m))) is the same text as render(m). Strict: both renders use the canonical dotted layout (MDL-023). |
| RT6 TOML path | data-only model | model -> TOML -> fixed module -> evaluate -> equals the model's own truth |
| RT7 generated acceptance | model instances from Hypothesis | Nix accepts each instance, and its truth equals the instance |
| RT8 rejection agreement | invalid instances from mutation | Pydantic rejects the value, and Nix also rejects it |

RT7 and RT8 test the type mapping itself. A value that Pydantic accepts and Nix rejects means the
model is too loose. A value that Pydantic rejects and Nix accepts means the model is too tight.

A plain `truth` request rejects nothing, because `definitionsWithLocations` never merges a value. The
runner therefore adds a probe option to each generated module. The probe forces the defined values
and `config.assertions` under `tryEval`. It also forces the `config.packages` names and, by default,
`config.enterShell` (MDL-038; `--no-probe-shell` turns the shell force off). Without those forces,
an option that only affects another option never evaluates (for example `languages.python.version`).
The probe accepts a path as declared when a prefix of the path is an option, so a sub-option of a
submodule is not `unknown-option` (MDL-041). The class `type-error` means that forcing threw.
The shell force found eight broken Python versions (series 3.3: `gcc9` is gone from nixpkgs), which
the older probe could not see.

RT8 builds its base case from a valid draw of the narrowed model, so the base satisfies the
cross-field rules (MDL-040). RT8 passes only when Nix rejects the mutated value with a type error
(MDL-024). Any other rejection
is its own failure class: `rejected-assertion`, `rejected-unknown-option`, or `rejected-other`.
RT7 classes: `type-error`, `assertion`, `mismatch`, and `other-error` (an error that `tryEval` does
not catch, such as a wrong package kind). The probe also answers `packages-error` and `shell-error`
when forcing the package names or `enterShell` throws. RT7 folds its expected values for an open
submodule into the shape that truth keeps (one attribute set, not leaf keys; MDL-041).

**Seeds (MDL-034).** An RT7 seed gives the same cases in any process. Hypothesis mixes the constants
of every local module in `sys.modules` into its draws, so a process that loaded other models drew
other cases (`languages.javascript` seed 2: 541 cases alone, 536 after `languages.python`). The
generator empties that constants pool while it draws. A regression test compares runs across
`PYTHONHASHSEED` values and loaded modules.

**Hybrid render (MDL-039).** Some options have no data form: a `$fn` option and a fixture-local
package. RT2 and RT5 write the truth, and for such an option they splice the exact source span that
the syntax reader found in the fixture's own source. Without a span the case skips with `has-fn`.
RT6 (TOML) cannot carry either value and skips (see the path-limit exceptions below).

### Corpus

| Source | Count at the probe pin | Use |
| --- | --- | --- |
| devenv `examples/` | 69 directories, 72 `devenv.nix` files (3 nested) | RT1 to RT5 |
| devenv `tests/` | 150 entries, 159 `devenv.nix` files (some nest) | RT1 to RT5, after triage |
| The owner's fleet: every `devenv.nix` under `~/Documents/Projects`, without `.archive/` and `.worktrees/`, deduplicated by content | 407 files in all; 266 sit under `.archive/` or `.worktrees/`; 104 unique contents over primary paths | RT1 to RT5; the realistic set. Fleet-module options (`repoman`, `testee`, `docman`, `zelligate`) need those modules in a later pin variant |
| Public repositories that hold a `devenv.nix` | not counted | RT1 to RT5; check licenses before vendoring |
| Generated by Hypothesis from each model | unbounded | RT7, RT8 |

Each fixture keeps its source, its inputs, a provenance record, and its truth for one pin. The counts
in the table are from the phase A static survey at pin `devenv-2.4.0-b904dcb5-c2f38fe7`. The
harvest of Step 7 measured the corpus ([step-7.md](./evidence/step-7.md)):

| Source | batch | alone | secret | fails | total |
| --- | --- | --- | --- | --- | --- |
| devenv-examples | 45 | 24 | 0 | 3 | 72 |
| devenv-tests | 119 | 21 | 4 | 15 | 159 |
| fleet (private) | 17 | 48 | 11 | 35 | 111 (31 duplicates) |

No `batch` or `alone` fixture has an unstable truth. The pilot subtrees have 24 public
`languages.python` fixtures and 10 public `services.postgres` fixtures that evaluate (the survey
predicted 23 and 10). A fixture is `batch` when its inputs match the base project's inputs by name
and `url` and `devenv.yaml` holds no other key. Other fixtures are `alone`. A `fails` fixture keeps
its error tail. Most fleet failures are limits of the harvest, not devenv failures.

**Corpus rules (final).** The report applies these rules to every subtree.

- **Two tiers (MDL-030).** The pilots keep their own sizes: 10 real fixtures for
  `languages.python` and 5 for `services.postgres`. Any other subtree is `supported` with at least 5
  real fixtures and every row passed. With fewer real fixtures and every other row passed (RT2 to
  RT8, and the RT7 size row with 2 seeds), it is `supported (generated-only)`. A generated-only
  status says that RT7 and RT8 prove the type mapping and the corpus proves little.
- **Exclusion share.** At most 20 percent of the real fixtures of a subtree, measured for each
  check, are skipped.
- **Named exclusion classes (MDL-032).** Each skip and each excluded fixture has one class:
  `has-imports`, `no-literal-fields`, `pkg-unresolved`, `has-fn`, `no-subtree`, `secret`, or
  `fails`. A class outside the list is a gate FAIL. `secret` and `fails` are triage classes, listed
  apart from the share.
- **Path-limit exceptions (MDL-031).** `PATH_LIMIT_EXCEPTIONS` names the skips that come from a
  documented limit of a writer: RT6 `has-fn` (TOML cannot carry a function) and RT6
  `pkg-unresolved` (the TOML reader module addresses a package only by its attribute path in
  `pkgs`). The report lists each such skip and does not count it in the share. A new exception
  needs a code change and a review.
- **Golden fixtures are not corpus (MDL-033).** The fixtures in `tests/golden/` run every check for
  correctness. The corpus metrics (RT3 typed share, exclusion share, corpus size) count only the
  `corpus/` fixtures.

## Bootstrap through agent skills

The harness turns authoring into a loop with a mechanical verdict. Three skills run that loop.

| Skill | Input | Output | Verdict |
| --- | --- | --- | --- |
| `devenv-py-harvest` | a source of examples | fixtures with provenance and truth | the fixture evaluates and its truth is stable across two runs |
| `devenv-py-author` | one subtree, its options export, and its fixtures | a narrowed model, templates, and syntax-reader rules | RT1 to RT8 for that subtree |
| `devenv-py-roundtrip` | a failing report | a fix to the model, template, or reader | the failing case passes and no passing case fails |

The existing `copyroom-template-edit` skill covers Templateer source edits. The author skill uses it.

The skill sources are `skills/<name>/SKILL.md` in `devenv-py`. Devman links them into
`.agents/skills/`. All three skills forbid a bare `uv`. The shell of an agent can inherit Vendomat's
`UV_PROJECT_ENVIRONMENT`, and a bare `uv sync` then overwrote Vendomat's venv (twice during the
build). The skills exist and the trials are done (GM10). The first trial, `services.redis`, reached
the gate only after rule and harness fixes that it prompted. The second, `languages.rust`, failed
on six harness gaps, which were fixed. The third, `languages.javascript`, passed with a fresh agent,
the skills alone, and no harness change ([step-16-final.md](./evidence/step-16-final.md)).

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
| A package compares by `pname`, which many attributes share | Done: identity by the full `$name` (MDL-036, superseding MDL-020). `CHOICES` lists are no longer limited to attributes whose `pname` equals the attribute name. |
| A rerun never hits the evaluation cache | Done: the cache keys on the request path, and requests and case directories are content-addressed (MDL-037, superseding MDL-026). |
| An RT7 seed gives other cases in another process | Done: the generator isolates the Hypothesis constants pool (MDL-034), with a regression test. |
| A skip rule hides a real gap | Named classes only (MDL-032); two path-limit exceptions, listed in every report (MDL-031); golden fixtures do not inflate the corpus metrics (MDL-033). |
| An agent shell overwrites another project's venv | Run `uv` only as `env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV devenv shell -- uv ...` |
| A narrowed type rejects a real fixture | RT1 on the corpus. The pilot found two such cases and widened them (MDL-021). |
| A narrowed model encodes data that goes stale (for example the `rust-overlay` manifests) | The data names the revision it came from (`rust-overlay` `c1cfa7a2`). A re-lock of that input needs a new extraction. RT8 cannot test such rules; unit tests and probes do. |

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
| MDL-020 | **Superseded by MDL-036.** *(Was: IN PROGRESS, proposed.)* The harness identifies a package by its full `$name` and resolves a name to an attribute path by evaluation. It no longer compares a package by `pname`. When it lands, it replaces the `pname` rule of the eval reader and the rule that the normalizer drops `$name` (neither rule has an ID). |
| MDL-021 | A narrowed model may type a function-typed option as `NixExpr \| FnMarker`. `FnMarker` accepts only `{"$fn": true}` and holds no source. A fixture with a `$fn` value is `has-fn`: the writers skip it. |
| MDL-022 | A narrowed class may set a `CHOICES` class variable that limits a package or string field to a listed set. Each entry has a probe that shows it evaluates at the pin. `CHOICES` adds no field, so MDL-009 holds. |
| MDL-023 | `render` writes one canonical layout: all definitions merge into one tree and each leaf is one dotted binding. RT5 is strict: the first render equals the render of the read of the first render. |
| MDL-024 | RT8 passes only when Nix rejects the mutated value with a type error. Any other rejection is a separate failure class. |
| MDL-025 | RT7 discards a generated draw that fails the narrowed model validation. |
| MDL-026 | **Superseded by MDL-037.** The driver evaluates a request from a content-addressed path, `requests/<sha256 of the canonical JSON>.json`, because the evaluation cache keys on the request path. Generated cases use paths that do not depend on the run id (in progress). |
| MDL-027 | The normalizer rewrites store hashes, the runtime directory, project directories, the fixture root, the checkout, and the home directory in every string and object key. |
| MDL-028 | The syntax reader reads a plain relative path literal (`./x`, `../x`, no interpolation) as a typed `$path` value. Other path forms stay `NixExpr`. |
| MDL-029 | A generated scalar field uses a strict Pydantic type. `number` maps to `StrictInt \| StrictFloat`. This replaces the table row that mapped `number` to `float`. |
| MDL-030 | A subtree other than the two pilots is `supported` with at least 5 real corpus fixtures and every row passed. With fewer real fixtures and every other row passed (RT2 to RT8, and the RT7 size row with 2 seeds), it is `supported (generated-only)`. The pilots keep 10 (`languages.python`) and 5 (`services.postgres`). Owner decision, 2026-10-11. |
| MDL-031 | A skip that comes from a documented path limit of a writer does not count toward the exclusion share. `PATH_LIMIT_EXCEPTIONS` names each such skip, and the report lists each one. The two exceptions are RT6 `has-fn` and RT6 `pkg-unresolved`. A new exception needs a code change and a review. Owner decision, 2026-10-11. |
| MDL-032 | Every skip and every excluded fixture has a named class: `has-imports`, `no-literal-fields`, `pkg-unresolved`, `has-fn`, `no-subtree`, `secret`, or `fails`. A skip with another reason is a gate FAIL. The exclusion share is measured for each of RT1 to RT6 and is at most 20 percent. |
| MDL-033 | The golden fixtures (`tests/golden/`) run every check for correctness. The corpus metrics (RT3 typed share, exclusion share, corpus size) count only the `corpus/` fixtures. |
| MDL-034 | An RT7 seed gives the same cases in any process, with any `PYTHONHASHSEED` and any set of loaded models. The generator isolates the Hypothesis constants pool while it draws. |
| MDL-035 | A renamed or alias option (`mkRenamedOptionModule`, `mkAliasOptionModule`) has no field in a generated model. The generator records it as a `renamed` coverage entry with the target path. |
| MDL-036 | The harness identifies a package by its full `$name`. The normalizer keeps `$name`; the eval reader keys a package by `(pname, output, name)` and resolves a name to an attribute path by evaluation; RT2, RT6, and RT7 compare by `$name` and output; a canonical path makes `./.` and `.` equal. A package with no attribute path gives the skip `pkg-unresolved`. Supersedes MDL-020. |
| MDL-037 | The driver evaluates a request from a content-addressed path, `requests/<sha256 of the canonical JSON>.json`. The runner writes a generated case to `cases/<sha256 of all files>/`, written once. A repeat run sends identical requests and hits the evaluation cache. Supersedes MDL-026. |
| MDL-038 | The RT7 probe forces the `config.packages` names. It also forces `config.enterShell` by default; `--no-probe-shell` turns that off. A failure has the class `packages-error` or `shell-error`. |
| MDL-039 | RT2 and RT5 render a fixture with a hybrid writer. For a `$fn` option and a fixture-local package, the writer splices the exact source span from the syntax reader. Without a span the case skips with `has-fn`. `alone` fixtures run in their own project. |
| MDL-040 | RT8 builds its base case from a valid draw of the narrowed model, so the base satisfies the cross-field rules. |
| MDL-041 | The RT7 and RT8 probe treats a path as declared when a prefix of the path is an option. RT7 folds the expected value of an open submodule into the shape that truth keeps. |
| MDL-042 | The syntax reader reads a root `let` name that is bound once to a plain literal as that literal, and reads `${name}` of such a name as its text. A name bound twice or by `inherit` is not a constant. |

## Gates

GM9 covers five subtrees: `languages.python`, `services.postgres`, `services.redis`
(generated-only), `languages.javascript`, and `languages.rust`.

| Gate | Proves | Guide step | Status (2026-10-11) |
| --- | --- | --- | --- |
| GM0 | The evaluation surfaces exist at a pin | Step 0 | PASS at the probe pin; formal rerun on the first pin not done |
| GM1 | The driver evaluates a batch and returns parsed JSON | Steps 2, 3 | PASS |
| GM2 | The options export is complete and structured | Step 4 | PASS |
| GM3 | Truth is stable and correct on hand-checked fixtures | Steps 5, 6 | PASS |
| GM4 | The corpus is harvested and triaged | Step 7 | PASS |
| GM5 | The generator maps types and stamps the pin | Step 8 | PASS |
| GM6 | Templateer has a `nix` output language | Step 9 | PASS for the suite; tag open (the harness pins a revision) |
| GM7 | Writers and readers exist | Steps 10, 11 | PASS |
| GM8 | The round-trip runner reports RT1 to RT8 | Steps 12, 13, 14 | PASS |
| GM9 | The pilot subtrees pass; the supported set passes | Step 15 | PASS |
| GM10 | The three skills run the loop on a new subtree | Step 16 | PASS |

The evidence for each status is in [evidence/GATES.md](./evidence/GATES.md).

## Open questions

1. Resolved 2026-10-11: the repository is `devenv-py`.
2. Resolved 2026-10-11: no fork patch. The introspection module works with stock `devenv eval`
   (probe O10 to O12). Revisit only if a later pin breaks that route and the repl fallback.
3. Resolved 2026-10-11: the eval reader names packages by the full `$name` and resolves a name to an
   attribute by evaluation, with no package index (MDL-036).
4. Which subtrees come after the five supported ones? The trials used `services.redis`,
   `languages.rust`, and `languages.javascript`. The next choice comes from the fleet census.
5. Resolved 2026-10-11: GM9 uses the thresholds in Step 15 of the guide. Correctness checks
   must be perfect, coverage must not fall, generated cases are sized by coverage, and a small
   corpus blocks the gate.
6. Should Path T support tagged values (`{"$pkg": ...}`) in TOML, or should such models use Path N
   only?
7. Which `templateer` tag carries the `nix` language? Step 9 landed on `main` at `d3304db4` with no
   tag. The tag `v0.4.2` is on the `v6-flake` branch. The harness pins revision `ac02b48c015d`
   (the integral-float fix). A tag on `main` is still open. The owner decides.
10. How should the report show "every enum value and both integer bounds occur"? Today an author
    computes it by hand (author skill, step 9).
11. Should `testee check rt-pilot` cover all five supported subtrees? Today it covers the two pilots.
    The gate runs for the other three used `dpy rt` directly.
9. Should the generator widen every `functionTo` and `path` option as the pilot did by hand
   (`NixExpr | FnMarker`, `list[PathRef | PkgRef]`)?
8. Should a string with an interpolation read as a parts list (literal text plus `NixExpr` holes)
   instead of one `NixExpr`? The fleet run shows interpolation as the main cost after the root `let`.

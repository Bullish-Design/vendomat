# Step 8 record: the model generator

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`.
**Raw report:** `~/.local/state/devenv-py/step-8/REPORT.md`.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Commit | `7579a9e18315` (change `nwylqwop`), parent `ce250ec0` |
| Workspace | `~/Documents/Projects/gitman-workspaces/dpy-gen` |
| Testee | `testee verify --full`, run `20261011T051752Z-5a6f9bd2a573`, PASS (pytest, ruff, ruff-format, ty) |
| Tests | 137 in the run: 95 new in `test_generator.py`, 25 in `test_values.py`, 4 in `test_cli.py`, 13 old in `test_pin.py` |

## Files

`exports/<pin>/options.json` (the phase-A export, byte for byte) and `options.meta.json`;
`src/devenv_py/values.py` (`PkgRef`, `PathRef`, `NixExpr`, `Priority[T]`, `Lines`, `Separator`,
`JsonValue`, `OptionModel`, `to_tagged()`); `src/devenv_py/generator.py`; `src/devenv_py/cli.py`
(`dpy gen`, `dpy schema`, `dpy drift`; the script entry is `dpy = "devenv_py.cli:main"`);
`generated/<pin>/{services.postgres,languages.python}.py` and `.schema.json`.

## Pilot coverage (leaf options in all classes, read-only options left out)

| Subtree | Fields | Typed | `NixExpr` | `JsonValue` | The `NixExpr` field |
| --- | --- | --- | --- | --- | --- |
| `services.postgres` | 16 | 15 | 1 | 0 | `services.postgres.extensions` (`nullOr functionTo`) |
| `languages.python` | 39 | 38 | 1 | 0 | `languages.python.import` (`functionTo` of `functionTo`) |

Each generated module holds the constants `COVERAGE` and `STATS`.

## Whole-export census (1330 records)

- Unmapped, become `NixExpr`: `functionTo` 9, `output` 14, `deferredModule` 3, `outputOf` 1.
- Loosened to `JsonValue`: recursion markers 43 (format types and Traffic Server records), `attrs`
  19, `anything` 17, `unspecified` 15.
- All 45 top-level subtrees generate and import (one test checks this).
- Summed over the 45 subtrees: 1242 fields, 1218 typed, 24 with `NixExpr`, 68 with `JsonValue`, and
  32 read-only options left out.
- Open observation: 1330 records against 1242 + 32 fields leaves 56 unexplained. Inference: options
  under the `coercedType` branch and similar side branches are not walked. Nobody investigated.

## Departures from the guide and the brief

1. Every field uses a strict scalar type (`StrictBool`, `StrictInt`, `StrictFloat`). Lax Pydantic
   accepts `"yes"` for a bool and turns ints into floats. Nix rejects both. `str` stays lax
   because Pydantic does not coerce numbers to `str`.
2. `number` maps to `StrictInt | StrictFloat`, not `float`. Nix `number` accepts ints.
3. Fields are not wrapped in `Priority[T]`. The type exists. The syntax reader decides how a field
   holds a priority (Step 11).
4. `JsonValue` is a recursive type alias, not a class. The module function `to_tagged(value)`
   handles it.
5. `Lines` is a `str` subclass with `.separator`. `Annotated[Lines, Separator(",")]` fixes the
   separator per field. A `separatedString` without `payload.sep` gets a `bounds-lost` entry.
6. A fourth coverage kind, `bounds-lost`, flags a lost pattern, separator, or `intBetween` bound.
   The kinds are `nix-expr` (an MDL-008 miss), `json-value` (loosened), and `bounds-lost`.
7. A `strMatching` pattern is wrapped as `^(?:pat)$` unless it already starts with `^` and ends
   with `$`. Nix `strMatching` is a full match. Pydantic search is not.
8. `intBetween` bounds come from two description patterns: "integer between A and B (both
   inclusive)" and "integer between A and B". The "1 and 31" form in the phase-A report is not
   matched; the real description holds the full text.
9. `int` has no 64-bit bounds.
10. A node is a format-type root (`JsonValue`) when a descendant recursion marker repeats its
    description. The test compares strings for equality. It parses nothing.
11. An intermediate option path (`languages.python.uv.sync.enable`) becomes a group class
    (`LanguagesPythonUvSync`). All classes sit at module level, children before parents, named by
    path. The brief said "nested classes".
12. Read-only options are left out of models. Internal options stay in, with a flag in the
    description.
13. `PkgRef`, `PathRef`, `NixExpr`, and `Priority` also validate from their tagged dict form.
    `PathRef` uses the Templateer `$path` grammar (relative paths only). `PkgRef` ignores `$name`.
    A truth `$pkg` holds a `pname`, not an attribute path. The eval reader resolves it (Step 11).
14. Output files keep the dots: `generated/<pin>/services.postgres.py`. Tests and the narrowing
    loader import by file path. A narrowed file imports the generated one as
    `devenv_py_generated.<subtree with _>` (for example `devenv_py_generated.services_postgres`).
15. `dpy gen` writes the module and the schema. `dpy schema` rewrites the schema. It refuses when the
    module is missing or stale.
16. `dpy drift` takes export files, directories, or pin ids under `exports/`. Exit code 1 means
    drift, 0 means none. It compares type signatures (name, enum values, bounds, pattern,
    separator, nested types), including options inside submodules. The guide form
    `dpy drift <old-pin> <new-pin>` works too.
17. The committed generated modules are the golden files. The test regenerates them and compares
    byte for byte. A structure test covers `services.postgres`.
18. The narrowing loader also rejects a narrowed class with a different `extra` rule, and a model
    class that extends no generated class.
19. The sidecar `options.meta.json` holds the pin, the hash, and the counts. The export file stays
    canonical.

## Incident

The agent ran a bare `uv sync` and a bare `uv run` in the workspace. The inherited
`UV_PROJECT_ENVIRONMENT` pointed at Vendomat's venv. The sync changed one thing: `devenv-py` was
reinstalled (editable) from the `dpy-gen` path. The agent did not repair it. See the incident in
[step-2-3.md](./step-2-3.md).

## Gate GM5

Met. The type tests pass, the golden test passes, and both pilot modules import.

# R60: the catalog key `settings` (VMT-183)

**Date:** 2026-10-15. **Ruling:** R60 ("Great, recommendations approved.", 2026-10-15, answer to the
recommendations for the S8 nix-systems proposal). It closes the gap `VMT-181`.

## What changed

| File | Change |
| --- | --- |
| `devenv/devenv.nix` | The schema gets `settings` (a map of module names to maps of field names to text). The mapping defines `vendomat.settings` from it. A new check reports a field with no option. |
| `devenv/explain.nix` | `settings.MODULE.FIELD` maps to `vendomat.settings.MODULE.FIELD`. The "file is the YAML file" shortcut now covers only `vendomat.serve`, so a `mkForce` in `devenv.nix` shows as the winner. |
| `templates/workspace/vendomat.yaml` | A commented `settings` example. |
| `README.md` | The key, its rules, and the type rule below. |
| `tests/` | See "Tests". |

## Behavior (observation)

- A module name and a field name each match `[A-Za-z_][A-Za-z0-9_-]*`. A bad name gives
  `vendomat.yaml:LINE:COL: settings.X: the name is not a module name (or a field name)`.
- A non-text value gives `settings.M.F must be text, found a list ...` (or `a map`). A non-map module entry
  gives `settings.M must be a map`.
- The values are plain definitions inside the inner module with `_file = "vendomat.yaml"`. The catalog
  declares no option.
- A catalog default is not used: R60 says plain definitions. A `devenv.nix` default (`mkDefault`) yields.
  A plain `devenv.nix` value conflicts, and the module system names both files:
  `The option 'vendomat.settings.greeting.text' has conflicting definition values` with
  `In 'vendomat.yaml'` and `In '.../devenv.nix'`.

## The error for an undeclared field

The module system rejects a definition with no option. Its text names the file and the option
(`The option 'vendomat.settings.X.Y' does not exist. Definition values: - In 'vendomat.yaml': ...`) but gives no
line. I added a catalog check instead (the instruction allowed this when the module system's text is not
enough). The check reads the `options` tree. A field counts as declared when an option sits on the path
`vendomat.settings.MODULE.FIELD` at any depth, so an author who declares `settings.MODULE` as a `submodule`
option passes. The error reads:

```
vendomat.yaml:4:5: settings.greeting.colour: no module declares the option vendomat.settings.greeting.colour (an authored module declares it with mkOption)
```

The check skips a path whose name or shape is already a fault, so one mistake gives one line.

## Two facts that bite (observation, nixpkgs `2010s04mqpq7q1kch0ddc9b429s2vh9v` module system)

1. The module system rejects a definition of `vendomat.settings` when no module declares it, even for an empty
   map and even under `mkIf false` or `mkMerge []`. So the catalog defines the option path only when the file
   has the key.
2. The top-level names of `mapping` cannot depend on the parsed file: the file path needs `config.devenv.root`,
   and a condition on the top level gave infinite recursion (the W4 problem). The condition therefore sits one
   level lower: `vendomat = optionalAttrs (raw ? settings) { settings = guard raw.settings; }`.

## Choice: text for a bool or int option

**Choice.** The catalog converts nothing. The authored module declares `types.str`, or declares its own
conversion, for example `types.coercedTo types.str (s: s == "true") types.bool` (or `lib.toInt` for an int).
A plain `types.bool` option given `"true"` fails with the module system's type error, which names
`vendomat.yaml`:
`A definition for option 'vendomat.settings.flags.on' is not of type 'boolean'` with `In 'vendomat.yaml'`.

**Why this one (inference).**
- It needs no code. The other choice needs the catalog to read the type of every option at the path
  (`options.vendomat.settings.M.F.type`), including options below a `submodule` or `attrsOf`, which the catalog
  cannot see.
- A hidden conversion has rules to define: `"yes"`, `"True"`, `"08"`, and a text that is a number for a `str`
  option. Each rule is a new interface. `VMT-010` already says the type gives the text its meaning. Here the
  module's option type gives it, and `coercedTo` is the module system's own tool for it.
- Parse, do not validate: the author states the conversion once, next to the option.
- The failure is clear and names the file.

## Tests

| Level | Test | Proves |
| --- | --- | --- |
| Eval | `test_settings_map_to_the_options_of_the_authored_module` | a good map; str, bool (coerced), int (coerced); default without the key |
| Eval | `test_a_setting_text_stays_text_for_a_string_option` | `3.10` stays text |
| Eval | `test_a_bad_module_name_...`, `test_a_bad_field_name_...`, `test_names_with_underscore_and_dash_are_good` | name rule, with line, column, and path |
| Eval | `test_a_setting_that_is_not_text_fails_with_its_position`, `test_settings_that_is_not_a_map_fails` | list and map values, non-map entries |
| Eval | `test_a_field_that_no_module_declares_...`, `test_a_submodule_option_above_the_field_counts_as_a_declaration` | the undeclared-field error; the submodule case |
| Eval | `test_a_setting_and_a_nix_definition_conflict_...`, `test_a_nix_default_yields_to_the_setting` | R23: the conflict names both files; a default yields |
| Eval | `test_text_for_a_bool_option_without_a_conversion_is_a_type_error_that_names_the_file` | the type rule |
| Eval | `test_explain_maps_each_setting_to_its_module_option` | explain: option, value, file, line; `mkForce` wins; Nix-only list |
| Real devenv | `test_settings_in_vendomat_yaml_reach_an_authored_module_on_real_devenv` | a module with two options (str and coerced bool); explain on the real option tree |
| Real devenv | the undeclared field, the conflict, and the plain-bool type error on real devenv | the same errors with the real devenv text |
| Template | `test_the_template_vendomat_yaml_is_an_empty_catalog_with_comments` | the commented example parses as a catalog |

## Runs

Tree `34d00b1d95` (commit `86309545d4`; later commits change `.scratch` text only). Logs under
`~/.local/state/vendomat/p21/2026-10-15/r60/`.

| Command | Run | Verdict |
| --- | --- | --- |
| `testee verify` | `20261015T150546Z-0ca5a519f41d` | GREEN 4/4 |
| `testee verify opt:catalog-eval` | `20261015T150650Z-579e7ef1b768` | PASS, 144 passed |
| `testee verify opt:catalog-devenv` | `20261015T150753Z-c398dbb27f9d` | PASS, 21 passed |
| `testee verify opt:catalog-e2e` | `20261015T150838Z-34a900057d54` | PASS, 21 passed |

Failed runs on the way (history): `20261015T145349Z-bed3cfc571a2` (an empty `vendomat.settings` map is a module
system error when no module declares it) and `20261015T150046Z-56837331fdb1` (format and line length).

## Limits

- A `settings` key works only with an authored module that declares the option. The catalog gives no typed or
  line-numbered error for a wrong value of a declared option; the module system's error names the file only.
- No per-machine form (`machines.NAME.settings`). The proposal left it open.
- The demo move is a separate record (see the end of [S8-CONSUMERS](S8-CONSUMERS.md)).

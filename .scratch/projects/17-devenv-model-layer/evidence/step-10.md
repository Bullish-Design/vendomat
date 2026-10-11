# Step 10 record: the writers

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`.
**Raw report:** `~/.local/state/devenv-py/step-10/REPORT.md`.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Commit | `74826b8d99b9` (change `zwyyysos`) on `5684ace5` |
| Workspace | `~/Documents/Projects/gitman-workspaces/dpy-writers` |
| Testee | `testee verify --full`, run `20261011T121708Z-3fd530e67e44`, PASS (after the rebase onto `5684ace5`) |
| Templateer | rev `d3304db4bbcf44008d5af1906ddd774d990dbac8` at that time; now `ac02b48c015d` (see [step-9.md](./step-9.md)) |

## Files

`templates/devenv-module/` (`metadata.yml`, `schema.py`, `template.j2`, `prompt.md`, three
examples), `reader-module/default.nix`, `src/devenv_py/writer_common.py`, `writer_nix.py`,
`writer_toml.py`, `cli.py` (`dpy render`), `tests/test_writers.py`, `pyproject.toml`, `uv.lock`.

## Results

| Check | Expected | Actual |
| --- | --- | --- |
| Golden truth, candidate, driver batch, normalized compare, Path N and Path T, five fixtures | 10 of 10 equal | 10 of 10 equal |
| Path T skips on the five fixtures | (none stated) | none: a truth holds final values only (no `$priority`, no `$nix`), so Path T carries them |
| Skip reasons on synthetic truths | asserted | `toml-nix`, `toml-priority`, `toml-null`, `has-fn`, `marker` |
| RT5 on `plain`, `head-let`, `curried-nonascii`, `not-attrset` | same tree, head, `let_prefix`, `extra_bindings` | equal (this RT5 form is the old one; see [step-15.md](./step-15.md) for the strict form) |
| Renders parse with `nix-instantiate` | yes | yes (`plain.nix` excluded: its source is invalid Nix) |
| `templateer check devenv-module -p templates` | clean | 3 fixtures, 2 sites linted, 0 findings |

## `WriterSkip` reasons (stable strings)

| Reason | Meaning |
| --- | --- |
| `has-fn` | the value holds `{"$fn": true}`; a function has no data form |
| `marker` | the value holds `$multi-def`, `$error`, `$merge`, `$type`, or `$deep` |
| `path-outside-root` | a `$path` value is not relative to the module file |
| `toml-nix`, `toml-priority` | Path T carries neither `$nix` nor `$priority` |
| `toml-null` | TOML has no null |

## Departures from the guide

1. The template schema holds `definitions` only. The Nix lint needs the `nix` filter on every
   site. That filter quotes strings and wraps `$nix` in parentheses, so `head`, `let_prefix`, and
   `extra_bindings` cannot pass as verbatim text. `writer_nix.ModuleContribution` adds those three
   fields and splices them with `read_syntax.assemble_module`. The `definitions: [{loc, value}]`
   shape is unchanged.
2. The `nix` filter refuses null. The writer writes null as `{"$nix": "null"}`, which renders as
   `(null)`.
3. The model path uses `OptionModel.to_tagged()` (set fields, aliases, tags kept). Plain
   `model_dump` turns a `PkgRef` into `{"attr": ...}`.
4. A `$path` of `.` or `..` renders as `./.` or `../.` in Path N, because a bare `.` is not a Nix
   path.
5. Path T copies the reader module as `source/devenv.nix` beside `contribution.toml`, because the
   driver needs `source/devenv.nix`. A truth key splits at dots, so an option path segment cannot
   hold a dot.
6. `writer_common.py` holds the typed `WriterSkip`.
7. The agent ran `git ls-remote` once, read-only, to confirm the Templateer revision.

## Answer to the Step 9 open item

Step 9 asked whether the `$nix` filter adds parentheses in an atom position. Observation: yes. The
filter renders `$nix` source in parentheses at an atom position. The syntax reader therefore never
keeps outer parentheses in a `$nix` value (rule 10 of [step-11.md](./step-11.md)).

## Gate GM7 (part 1)

Met. Both writers pass on the golden fixtures within their stated limits.

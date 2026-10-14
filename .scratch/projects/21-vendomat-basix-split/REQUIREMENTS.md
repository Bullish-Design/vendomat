# Project 21 requirement ledger

**Date:** 2026-10-13. The design is final as of this date. The W4 spike drafted the ledger, and the owner
rulings R1 to R34 settled it. A requirement here is not an implementation gate until the named
evidence is a pass on the pinned tools. Evidence names refer to the W4 fixtures (F1 to F14, [W4](evidence/W4-CATALOG.md)) or to earlier records. "Unproved" means no
fixture exists. Do not reuse or renumber an ID. Project 20 text stays unchanged. The ledger came from
`REQUIREMENTS-DRAFT.md`, which this file replaces.

## ID scheme

Each product has its own prefix (owner ruling R24, 2026-10-13): `VMT-` for Vendomat and `BSX-` for
Basix, three digits each. The W4 draft used one prefix, `SPLIT-`. It was renamed before any ruling,
and each ID kept its number: `SPLIT-004` became `BSX-004`, `SPLIT-030` became `VMT-030`. A number
is used under one prefix only. A successor row names the project 20 item it supersedes. Project 20
`S` numbers are decisions in its `DECISIONS.md`, not ledger IDs; a successor names them the same way.
The Basix repository exists since 2026-10-13 (`../basix`), and the 13 `BSX-` rows moved there (`.scratch/projects/001-initial-concept/REQUIREMENTS.md` in that repository, with the exact text, status, and evidence). Each moved row stays here as a stub with its ID, so no ID is lost. The Basix repository adds new rows; its next number follows the highest number used under either prefix.

Status words: **Proposed** (no fixture yet), **Fixture pass** (a spike fixture proved it; not an
implementation gate), **Observed gap** (a fixture shows a shortfall), **Ruled** (an owner ruling in
`DECISIONS.md` settles the choice; proof may still be open), **Unproved** (no fixture exists),
**Superseded** (a newer row replaces the claim), **Moved** (the row lives in the Basix repository). No row awaits an owner ruling now. Rows marked
"open, no ruling covers it" need work or a ruling. Numbers continue across prefixes, so the highest
number is `BSX-100` before the section "Added at the design freeze".

## Successors to project 20 items

| ID | Claim | Supersedes | Evidence | Status |
| --- | --- | --- | --- | --- |
| `VMT-001` | Basix MUST have its own repository and release, and Vendomat MUST NOT import, test, or name Basix. | Decision S34 (machine catalog in the Vendomat release); owner ruling R1 | R1 only | Ruled (R1); implementation unproved |
| `VMT-002` | A workspace MUST hold `vendomat.yaml`, template-owned `devenv.yaml`, `devenv.lock`, and a `devenv.nix` that the user MAY edit; the catalog module MUST read `vendomat.yaml` with `builtins.readFile` and parse it with a Nix function from the Vendomat source, with no primop and no unsafe Nix setting. | `DOOR-074` (primop; `devenv.nix` must be `{ }`) | F2, F13 (stock devenv 2.4.0, no primop); S3: `opt:catalog-eval`, `opt:catalog-e2e` (F2, F13); `test_the_module_reads_the_file_with_the_nix_parser_and_no_unsafe_setting` | Ruled (R2, R7); fixture pass (W4 and S3 repository) |
| `VMT-003` | The catalog MUST be a bounded set of named, typed entries; the grammar MUST allow maps, lists of text, lists of maps, nested lists, and tab indentation, and MUST reject `key: - x`; syntax errors MUST read `vendomat.yaml:LINE:COL: reason`. | `DOOR-075` (tabs and lists of maps rejected) | F1, F3, F13; YAML-SPIKE-2 (P1 to P5); S3: `opt:catalog-eval`, `opt:parser-fuzz`, `opt:catalog-e2e` (F1, F3, F13) | Ruled (R2, R8 to R10); fixture pass for programs, env, languages, services, machines (S3); `services` also under `VMT-090` |
| `BSX-004` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | — | Moved |
| `VMT-005` | Native `devenv.nix` and `devenv.local.nix` MUST stay available as an optional, visible escape hatch; no rule MAY say that Vendomat owns every other file. | Concept line "Vendomat owns every other file" (project 20 `CONCEPT.md`, no ID); the `{ }` clause of `DOOR-074` | F6, F8, F11 | Ruled (R12); fixture pass |
| `VMT-006` | The verbs `apply` and `install`, and the "pinned devenv fork" wording, MUST follow the rulings on A2 and A12. | `DOOR-071` (verbs and pass-through), in part | none | Ruled (R13, R22); wording unproved |

## Grammar

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-010` | Every value in the file MUST be text; the catalog types MUST give the text its meaning; the file MUST have no null. | F1; F3 (`"three"` rejected as a version); S3: `opt:catalog-eval` (`test_the_parser_matches_every_expectation_of_the_group`), `opt:parser-fuzz` | Fixture pass (grammar basis R2, R7); repeated in S3 |
| `VMT-011` | The parser MUST compare indentation as text with no tab width; a child MUST extend its parent; siblings MUST match; a mix MUST fail with `inconsistent tabs and spaces`. | F13 (`vendomat.yaml:3:3`); YAML-SPIKE-2 P3; S3: `opt:parser-fuzz` (`test_indentation_faults_fail_at_the_computed_position`), `opt:catalog-e2e` F13 | Ruled (R9, R10); fixture pass (W4 and S3) |
| `VMT-012` | The parser MUST reject anchors, aliases, merge keys, tags, flow style, block scalars, document markers, empty values, duplicate keys, a colon-space in plain text, a list on the key's line, special first characters, unknown escapes, bad plain keys, and a byte order mark. | F1 (131 hand cases through the catalog); YAML-SPIKE-2 P4; S3: curated corpus (321 files), `opt:parser-fuzz` fuzz and mutant corpora | Fixture pass (grammar basis R7 to R10); repeated in S3 |
| `VMT-013` | A file deeper than the parser limit MUST fail with an error that names the file. | F1 (`deep_1000` fails with Nix `stack overflow; max-call-depth exceeded`, no `vendomat.yaml` prefix); S3: limit 64 (`test_a_file_at_the_limit_parses_and_one_level_more_fails`; chains to 1500 levels and dash runs to 3000 fail with the file name) | Fixture pass (S3 choice of the limit, see `VMT-158`; was Observed gap) |

## Reader

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-020` | The parser MUST be plain Nix over builtins only and MUST live in the Vendomat source, pinned by the workspace lock. | F1, F2; `parse.nix` is a byte copy of v3; S3: `test_the_parser_is_plain_nix_over_builtins`; `devenv/parse.nix` is no longer a byte copy of v3 (depth limit, side table, file-name parameter); S3 release smoke on `git://server/vendomat?ref=release` at `e5923a8f` (v0.8.0): the lock pins `vendomat` and `devenv`, `~/.local/state/vendomat/p21/2026-10-14/s3/release-smoke/RESULT.md` | Ruled (R7); pass (fixtures and the real-channel smoke, 2026-10-14) |
| `VMT-021` | The catalog MUST parse the file once; a missing or empty file MUST mean an empty catalog. | F2 (no file, empty file, one key); S3: `test_a_missing_or_empty_file_is_an_empty_catalog`, `opt:catalog-e2e` F2 | Fixture pass (W4 and S3) |
| `VMT-022` | An edit, create, or delete of `vendomat.yaml` MUST show in the next shell with no other step. | F2 (one workspace: no file, then an empty file, then a one-key file, each seen by the next shell); F4b (the cache follows `pyproject.toml`); S3: `opt:catalog-e2e` `test_edit_create_delete_of_vendomat_yaml_show_in_the_next_shell` (create, edit, delete, create again), `opt:front-door-e2e` | Fixture pass for create, edit, and delete (S3) |

## Catalog

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-030` | The catalog MUST report every bad field in one error before any work, and every line MUST name `vendomat.yaml` and the key path. | F3, F3b; S3: `test_one_error_lists_every_bad_field_with_line_and_column`, `opt:catalog-e2e` F3, F3b | Fixture pass (W4 and S3) |
| `VMT-031` | The error MUST stop every read of the configuration, including `devenv eval` of an unrelated option. | F3 (`dv eval languages.python.enable` gives the same error); S3: `test_a_bad_file_stops_a_read_that_uses_no_catalog_value`, `opt:front-door-e2e` (shell, test, builds, tasks) | Fixture pass (W4 and S3) |
| `VMT-032` | An unknown key MUST fail and MUST list the known keys; an unknown program name MUST fail even when other fields are bad. | F3, F3b; S3: `opt:catalog-eval`, `opt:catalog-e2e` F3b | Fixture pass (W4 and S3) |
| `VMT-033` | `programs` MUST map to `packages`, and `env` MUST map to `env`. | F2, F8; S3: `test_a_valid_file_maps_to_native_options`, `opt:catalog-e2e` F2, F8 | Fixture pass (W4 and S3) |
| `VMT-034` | The catalog MUST use the native option names, and MUST add only checks and Vendomat defaults. | F4, F5, F9; S3: `opt:catalog-eval`, `opt:catalog-e2e` F4, F5, F9 | Fixture pass (W4 and S3) |
| `VMT-035` | A fault of a schema-checked field MUST carry line and column. | F3 (key path only; the parser returns no line for a value); S3: the parser side table `at`; `test_the_side_table_gives_line_and_column_of_keys_and_values`, `test_one_error_lists_every_bad_field_with_line_and_column`, `opt:catalog-e2e` F3b | Fixture pass (S3; was Observed gap) |
| `VMT-036` | The catalog MUST NOT cost more than noise on shell entry. | `logs/timing.log`; S3: `opt:catalog-e2e` `test_the_catalog_costs_only_noise_on_shell_entry`: warm median of 7, bare 0.46 s and catalog 0.39 s in one run, bare 0.48 s and catalog 0.46 s in another | Fixture pass (W4 and S3) |

## Languages

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-040` | A `languages.python` entry MUST turn on `languages.python.enable`, map `version`, and turn on `uv.enable` by default (priority `mkDefault`). | F4, F4d; S3: `test_python_uv_keys_mirror_the_native_names`, `opt:catalog-e2e` F4 | Ruled (R11); fixture pass (W4 and S3) |
| `VMT-041` | The catalog MUST turn on `uv.sync.enable` only when `pyproject.toml` exists in the workspace root, and shell entry MUST print no warning without the file. | F4, F4c (control), F4b; S3: `opt:catalog-e2e` F4, F4c | Ruled (R20); fixture pass (A9, S3) |
| `VMT-042` | A created or deleted `pyproject.toml` MUST change `uv.sync.enable` in the next shell with no other step. | F4b (6 steps, no stale result); S3: `opt:catalog-e2e` F4b | Fixture pass (W4 and S3) |
| `VMT-043` | The template MUST list `nixpkgs-python` and `rust-overlay`, each following `nixpkgs`; no fork patch MAY inherit inputs. | F4, F5; S3: `test_the_template_devenv_yaml_lists_every_input_the_catalog_needs`, `opt:catalog-e2e` F4, F5 | Ruled (R11, R28); fixture pass (retires patch 0007; S3) |
| `VMT-044` | A `languages.rust` entry without `version` MUST use the nixpkgs toolchain; with `version` it MUST set `channel = "stable"` and `version`. | F5 (`rustc 1.97.1`, then `rustc 1.81.0`); S3: `opt:catalog-e2e` F5 on nixpkgs `e7439b6b` | Ruled (R11); fixture pass (W4 and S3) |
| `VMT-045` | The catalog MUST report a Python version that `nixpkgs-python` lacks. | Code path exists; no fixture; S3: `test_a_python_version_that_nixpkgs_python_lacks_fails` with a stub `nixpkgs-python` input list | Fixture pass with a stub input only; the real input is unproved |
| `VMT-046` | A new language MUST be addable to existing workspaces without a template change. | none (project 21 Open question 3) | Superseded in part by `VMT-094` (R25): the template gains the line and `vendomat update` brings it to existing workspaces; unproved |

## Escape hatch

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-050` | The catalog MUST put its mappings in an inner module with `_file = "vendomat.yaml"`, so a conflict error names `vendomat.yaml` and the other file. | F6, F10; S3: `opt:catalog-eval`, `opt:catalog-e2e` F6, F10 | Ruled (R19); fixture pass (A8, S3) |
| `VMT-051` | A value from the YAML MUST be a plain definition; a scalar set in both places MUST stop with a conflict error that names both files. | F6, F4d; S3: `test_a_scalar_set_in_yaml_and_in_nix_conflicts_and_names_both_files`, `opt:catalog-e2e` F6 | Ruled (R12); fixture pass (W4 and S3) |
| `VMT-052` | Lists and maps from the YAML and from Nix MUST merge. | F8; S3: `test_lists_and_maps_merge_with_nix_definitions`, `opt:catalog-e2e` F8 | Ruled (R12); fixture pass (W4 and S3) |
| `VMT-053` | `lib.mkForce` in `devenv.nix` MUST win over the YAML. | F7; S3: `opt:catalog-e2e` F7 | Ruled (R12); fixture pass (W4 and S3) |
| `VMT-054` | Shell entry MUST print one `advanced:` line when `devenv.nix` or `devenv.local.nix` sets a value, and MUST print nothing for `{ }` stubs or empty files. | F11; S3: `devenv/hatch.nix`; `test_catalog_hatch_nix` (in `opt:catalog-eval`), `opt:catalog-devenv`, `opt:catalog-e2e` F11 | Ruled (R19); fixture pass (A8, S3) |
| `VMT-055` | The count in the line MUST be the number of settings the file wrote (each leaf of its attribute tree), and MUST NOT claim to be the number of options devenv merged. | F11; `definitionsWithLocations` fails for counting (REPORT, Surprise 1); S3: `test_the_line_counts_the_settings_a_file_wrote`, `opt:catalog-e2e` F11 | Fixture pass for the leaf count (W4 and S3); the wording "settings" replaces "options" |
| `VMT-056` | `devenv.local.nix` MUST count separately and the line MUST say it applies to this checkout only. | F11; S3: `test_a_local_file_counts_apart_and_says_this_checkout_only`, `opt:catalog-e2e` F11 | Fixture pass (W4 and S3) |
| `VMT-057` | `vendomat explain` MUST print the user's YAML keys, each with its native option, value, and source file, then a section for options set only in Nix; `--json` MUST print the same data. | F12 (prototype prints value and file); S3: `devenv/explain.nix`, `src/vendomat/explain.py`; `test_explain`, `test_catalog_hatch_nix`, `opt:catalog-devenv`, `opt:catalog-e2e` F12 | Ruled (R27); fixture pass (S3); the format is now what the fixtures define |
| `VMT-058` | Vendomat MUST check its own lines in `devenv.yaml`. | S3: `vendomat update --check` reports each missing template line and exits 1 (`test_update`); it does not check a changed or wrong value | Unproved beyond the missing-line check; no ruling covers it |
| `BSX-059` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |

## Machines

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-060` | A `machines.NAME.host` entry MUST map to `machines.NAME.target.host`. | F9, F12; S3: `test_every_machine_gets_its_name_and_host`, `opt:catalog-e2e` F9 | Fixture pass (W4 and S3) |
| `VMT-061` | The catalog MUST set `networking.hostName` to the machine name. | F9, F10 (A10); S3: `opt:catalog-e2e` F10 | Ruled (R21); fixture pass (A10, S3) |
| `VMT-062` | A different `networking.hostName` from another file MUST fail with a conflict that names both files, unless it uses `lib.mkForce`. | F10; S3: `opt:catalog-e2e` F10 | Ruled (R21); fixture pass (W4 and S3) |
| `VMT-063` | A machine marked `virtual` MUST set `hardware.facter = null`, and a machine without a report MUST NOT evaluate. | F14 (A14); S3: `test_a_virtual_machine_has_no_hardware_report`, `opt:catalog-e2e` F14 | Fixture pass at evaluation level (A14, S3); key name ruled (R23) |
| `VMT-064` | `machines.NAME.nixos` from the YAML, from `devenv.nix`, and from an imported file MUST merge, whether each is an attribute set or a function. | F9 on the module-only fork input; W2 T4; [S1](evidence/S1-MODULE-FORK.md) E1 (stock fails, fork merges) | Ruled (R14, R22, R34); fixture pass; S1 partial: an attribute set, a function, and a default module merge on the published fork; the YAML source needs S3 |
| `BSX-065` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved; superseded by `BSX-124` in the Basix ledger (R38) |

## Items that awaited an owner ruling (all ruled)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `BSX-070` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-071` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-072` | A lasting rollback MUST be: restore `vendomat.yaml` and `devenv.lock`, then apply. The boot menu MUST be for recovery only. | W2 T1 (boot-menu rollback does not move the profile); [S4](evidence/S4-APPLY-ROLLBACK.md): `opt:machines-vm` run `20261014T184833Z-df3bd2858db6` (rollback reboot, `--boot-only`, `--fast` steps) | Ruled (R30); S4: fixture pass in a VM; the watched files are in `VMT-163` |
| `VMT-073` | Hosts and the ISO MUST install `pkgs.devenv` from Vendomat's pinned nixpkgs; the workspace `devenv` input MUST be a module-only fork; the template MUST omit `require_version`. | F2 to F14 ran on stock 2.4.0 with the module-only input; the line `devenv 2.4.0 is newer than devenv input (2.3.1)` shows each entry until `devenv.warnOnNewVersion = false` | Ruled (R22); D2 ruled (R41) |
| `VMT-074` | Vendomat MUST keep a devenv binary with patch 0003, or accept that a fresh machine cannot enter a workspace while the remote is down. | W1 Q2; [S2](evidence/S2-HOST-BINARY.md) B2 | Ruled (R31); W6; S2: fixture pass on the binary built from the flake (stock fails with `Failed to fetch git repository`, patched enters; `opt:binary-e2e` run `20261014T182736Z-e8b7d16bba14`) |
| `VMT-075` | The `vendomat apply` command MUST read the machine name from the facts file and run the two activation commands. | W2 T1 (commands, not the command); S4: `opt:machines-vm` run `20261014T184833Z-df3bd2858db6` (apply A, apply A', dirty apply) and the unit tests of `tests/test_machine_apply.py` | Ruled (R13, R15); S4: fixture pass in a VM; `apply NAME` for another machine has a unit test only |

## Fork retirement (carried by the rows above)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-080` | Patch 0009 (`vendomatFromYAML`) MUST be dropped. | `VMT-002`, `VMT-003` (F1 to F13) | Ruled (R7); fixture pass |
| `VMT-081` | Patch 0007 (inherit an imported source's inputs) MUST be dropped. | `VMT-043` | Ruled (R11); fixture pass |
| `VMT-082` | The `nixos = deferredModule` change MUST ship in a module-only `devenv` input; Vendomat MUST NOT open an upstream pull request for it (R34). | `VMT-064`; [S1](evidence/S1-MODULE-FORK.md) (tag published, locked as flake input `devenv`) | Ruled (R14, R22, R34); fixture pass; tag name ruled (R44); S1 proved: `v2.4.0-vendomat-modules.1` (061c2184) published, input locked |

## Added by the owner rulings of 2026-10-13

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-090` | The catalog MUST map `services.postgres` and `services.redis` as typed keys, as slice 1 did. | Slice 1 catalog (`devenv/devenv.nix`); not in the W4 catalog; S3: `test_a_valid_file_maps_to_native_options` (`services.postgres` and `services.redis` on the Nix parser) | Ruled (R23); fixture pass at module level (S3) |
| `VMT-091` | Catalog defaults MUST use `lib.mkDefault`; YAML values MUST stay plain definitions. | F4d, F6; S3: `test_a_catalog_default_yields_to_a_plain_nix_value`, `opt:catalog-e2e` F4 | Ruled (R23); fixture pass (W4 and S3) |
| `VMT-092` | A `languages.python` entry MUST accept `uv` and `uv.sync`; `uv.sync` MUST accept `auto`, `true`, and `false`, and `auto` MUST turn sync on only when `pyproject.toml` exists. | F4, F4b (the `auto` behaviour); S3: `test_python_uv_keys_mirror_the_native_names`, `test_a_bad_uv_sync_value_fails_with_its_position`, `opt:catalog-e2e` F4, F4b | Ruled (R20); fixture pass (S3) |
| `VMT-093` | A personal setting outside `vendomat.yaml` MUST hide the shell `advanced:` line; `explain` MUST still show every source. | S3: `VENDOMAT_HIDE_ADVANCED=1` hides the line (`opt:catalog-devenv`, `opt:catalog-e2e` F11); `test_explain_shows_every_source_whatever_the_hide_switch_says` | Ruled (R19, R45); fixture pass (S3) |
| `VMT-094` | `vendomat update` MUST add missing template lines to `devenv.yaml`, and an error for a missing line MUST name the exact line. | S3: `src/vendomat/update.py`; `test_update`, `opt:catalog-devenv` (`test_update_writes_the_lines_and_devenv_locks_them`), `opt:front-door-e2e` | Ruled (R25); fixture pass for `update` and `update --check`; an error at shell entry that names the exact missing line is unproved (devenv prints its own text); `update` edits block-style files only |
| `VMT-095` | The module-only `devenv` input MUST give every machine `build.vm` and `build.iso` (typed `nullOr package`), and `build.iso` MUST extend the machine with the ISO module, the six required overrides, and `machines.NAME.iso.modules`. | W7, W8; [S1](evidence/S1-MODULE-FORK.md) E3, E4, V1, V2 | Ruled (R17); fixture pass; S1 proved on the published fork (evaluation and two boots); the six settings are four priority-60 overrides plus two normal-priority flags |
| `BSX-096` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-097` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-098` | `vendomat rollback` MUST restore the configuration files from an earlier commit, MUST end in a new commit, and MUST refuse uncommitted changes; each machine MUST keep a record from system path to workspace commit. | W9 R2, R3; S4: `opt:machines-vm` run `20261014T184833Z-df3bd2858db6` (rollback, working-copy restore, dirty skip, path left the store, `--exact`) and `tests/test_machine_rollback.py` | Ruled (R30); record ruled (R43); S4: fixture pass in a VM, including the record line per apply; refusal of an unknown or lost commit has unit tests only |
| `VMT-099` | The catalog MUST set `machines.NAME.vendomat.mode` to `adopt-existing` for an installed machine, and the host binary MUST refuse `machines install` for it before any contact. | W6 B5; [S2](evidence/S2-HOST-BINARY.md) B5, B6; S3: `test_the_machine_mode_follows_the_hardware_report_and_the_key`, `test_the_facter_phase_case_marks_the_machine_installed`, `test_the_derived_mode_is_a_default_and_a_plain_nix_value_wins` | Ruled (R31); fixture pass (catalog half re-proved in S3); S2: binary half proved on the binary built from the flake (B5 refusal against a running VM, B6 catalog workspace; `opt:binary-e2e` run `20261014T182736Z-e8b7d16bba14`); install marker ruled (R42) |
| `BSX-100` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |

## Added at the design freeze, 2026-10-13

Rows for ruled behaviour that had no row, and for the open gaps. The numbers continue after
`BSX-100`.

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-101` | Machines MUST be devenv Machines on a pinned devenv version; plain NixOS flakes MUST NOT be the machine path. | W2 (all four fixtures on stock devenv 2.4.0) | Ruled (R4); fixture pass |
| `VMT-102` | Vendomat MUST NOT offer an `eject` command until a clear need appears; `vendomat explain` is the read-only window into Nix. | none | Ruled (R5) |
| `VMT-103` | Routine use MUST need no Nix file; the catalog MUST cover routine needs. | F1 to F14 for programs, env, languages, and machines; S3: `opt:catalog-e2e` F2 to F14, `opt:front-door-e2e` (programs, env, languages, services, machines) | Ruled (R6); fixture pass for those keys (S3) |
| `BSX-104` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-105` | The host and ISO binary MUST be `pkgs.devenv` from Vendomat's pinned nixpkgs with patches 0003 and 0005 applied through an overlay, MUST NOT carry patch 0008, and MUST be built and cached in Attic. The overlay MUST drop the `CHANGELOG.md` hunk of 0003, because that hunk needs patch 0001. A nixpkgs bump MUST recheck PR #3244. | [W6](evidence/W6-HOST-BINARY.md) (build 23 to 49 min, one new 218 MiB path, stock closure kept) | Ruled (R16, R22, R31); fixture pass for the build; the Attic cache is unproved; superseded by `VMT-126` (R39) |
| `VMT-106` | Patch 0005 MUST split: the Rust half (`machines.rs`) MUST ship in the host binary, and the module half (`machines.nix`, 39 lines) MUST ship in the module-only fork. | W6 B5; [S1](evidence/S1-MODULE-FORK.md) E5 (module half); [S2](evidence/S2-HOST-BINARY.md) B5 (binary half) | Ruled (R31); fixture pass; S1 partial: the module half ships in the fork (option and `machinesMeta` copy proved); S2: the Rust half ships in the host binary (patch 0005 built from the flake; the refusal proved in B5); the owner gate (host switch) is open |
| `VMT-107` | A module in `machines.NAME.iso.modules` that changes an option which `build.iso` overrides MUST use `lib.mkForce`, because devenv's six overrides use priority 60 and a plain value loses without a message. | [W8](evidence/W8-ISO-POLICY.md) (`boot.loader.timeout`: plain value ignored, `mkForce` works); [S1](evidence/S1-MODULE-FORK.md) E4 | Ruled (R17); fixture pass; S1 proved on the published fork |
| `VMT-108` | A machine that imports its own ISO module MUST keep its own image; `build.iso` MUST NOT add the ISO module twice. | [W7](evidence/W7-BUILD-OPTIONS.md) (first try failed to boot), [W8](evidence/W8-ISO-POLICY.md) Q5; [S1](evidence/S1-MODULE-FORK.md) E4 | Ruled (R17); fixture pass; S1 proved on the published fork |
| `BSX-109` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-110` | `system.configurationRevision` MUST NOT hold the workspace commit; the per-machine record of `VMT-098` is the only link from a system path to a commit. | [W9](evidence/W9-ROLLBACK.md) (each commit gives a new generation); S4: the rollback step of `opt:machines-vm` run `20261014T184833Z-df3bd2858db6` gave the identical path of A with no `configurationRevision` | Ruled (R30); record ruled (R43); S4: fixture pass in a VM |
| `VMT-111` | One `vendomat update` MUST move the Basix and Vendomat pair together, and it MUST keep the `follows` lines of `BSX-070` current. | [W3](evidence/W3-TOPOLOGY.md) (one `devenv update` moved the pair); S3: `vendomat update` adds missing `follows` lines (`test_update`); the Basix pair is S5 | Ruled (R28); fixture pass with stubs; D2 ruled (R41); the Basix half waits for S5 |
| `VMT-112` | A workspace that builds with `vendomat.yaml` MUST pin Vendomat in its own `devenv.lock`; a personal tool MUST NOT enter a workspace lock. | W3; project 22 clone test; S3: `opt:front-door-e2e` (clone and direnv use the workspace's own release lock; a scratch copy of the repository is the `vendomat` input) | Ruled (R33); fixture pass for the first clause; the published lock waits for S3 step 14 |
| `VMT-113` | Vendomat MUST NOT open an upstream pull request for a devenv patch. The module-only fork and the patched binary are long-lived. Vendomat MAY watch upstream (PR #3244, releases). The owner MAY revisit after months of use. | none | Ruled (R34) |
| `BSX-114` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-115` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-116` | Template inputs that a workspace does not use MUST NOT cost a fetch on shell entry. | S3 spike: answer NO (devenv resolves lock nodes lazily; blocked Python-only entries succeed; positive controls fail on the used input); logs `~/.local/state/vendomat/p21/2026-10-14/s3/vmt116/` | Fixture pass (S3 spike, scripts outside the repository; no repository test) |
| `VMT-117` | The wrapper MUST trim devenv's Nix trace so the `vendomat.yaml:` lines come first. | [W4](evidence/W4-CATALOG.md) (about 300 lines of trace print before the message); S3: `src/vendomat/errortrim.py`, launcher trim (exit 2, trace under `~/.local/state/vendomat/logs/`); `test_errortrim`, `test_a_bad_file_stops_the_launcher_with_the_yaml_lines_first`, `opt:front-door-e2e` | Fixture pass (S3; was Observed gap) |
| `VMT-118` | Shell entry MUST print no devenv version warning. | [W1](evidence/W1-FORK-REVIEW.md) Q1 (`devenv 2.4.0 is newer than devenv input (2.3.1)`); [S1](evidence/S1-MODULE-FORK.md) E6 | Fixture pass at module level (S1): the fork version file (m0002) removes the warning, and stock prints it. Partial: shell entry through the catalog is not proved. Open, no ruling covers it |
| `BSX-119` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-120` | Attic MUST stay until a two-machine Harmonia check passes on real machines; a serving machine MUST make its own signing key, and a client MUST substitute from it. | project 20 S6 (two VMs only) | Unproved; superseded by `VMT-127` (R39) |
| `VMT-121` | The catalog together with a flake Basix, and ISO and VM builds through the catalog, MUST work. | none | Unproved |
| `VMT-122` | The catalog MUST map no home key; homes MUST stay outside Vendomat, and devenv's native `machines.NAME.home-manager` MUST be reachable only through the escape hatch. | S3: `test_no_home_key_exists`, `test_the_module_maps_no_home_key_and_builds_no_extension_point` | Ruled (R35); fixture pass (S3) |
| `VMT-123` | Vendomat MUST ship no host-side module; a workspace MUST get Vendomat only through its own lock, and the project 14 `share/vendomat/consumer-module.nix` and `machine.json` MUST be removed with the project 14 code. | Project 22 [HOME-PORT](../22-owner-estate/evidence/HOME-PORT.md) (0 readers) | Ruled (R36) |
| `VMT-126` | The host and ISO binary MUST be `pkgs.devenv` from Vendomat's pinned nixpkgs with patches 0003 and 0005 applied through an overlay, MUST NOT carry patch 0008, and MUST be kept in the building machine's store under a GC root; no slice MAY push it to Attic. The overlay MUST drop the `CHANGELOG.md` hunk of 0003. A nixpkgs bump MUST recheck PR #3244. Supersedes `VMT-105`. | [W6](evidence/W6-HOST-BINARY.md); [S2](evidence/S2-HOST-BINARY.md) | Ruled (R39); fixture pass for the build; S2: built from the Vendomat flake (`packages.<system>.devenv`, `overlays.devenv`), store path `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0`, kept under a GC root, no Attic; host switch not applied (owner gate) |
| `VMT-127` | The new system MUST configure no Attic. A machine MUST share build outputs through Harmonia with a signing key it makes at first boot, and a client MUST substitute from it with `fallback = true` and a short timeout. Supersedes `VMT-120`. | project 20 S6 (two VMs only); S3: `opt:sharing-vm` PASS, 10 tests: key made at first boot, secret in no store path, B substitutes A's path with the signature checked (5.2 s), an untrusted key is refused, `serve = false` runs no Harmonia, A off gives fallback (25.1 s); plain nixpkgs VMs, not through the catalog | Ruled (R39); fixture pass for two VMs (S3, module level); real machines unproved (S7) |
| `VMT-128` | The catalog MUST map the machine key `serve` (default on; `serve: false` turns it off) to Vendomat's sharing module: Harmonia on the machine and the substituter and key on the other machines of the workspace. | S3: the key `serve` is parsed and defaults on (`test_serve_is_on_by_default_and_a_key_turns_it_off`); the module is proved by `opt:sharing-vm`; the catalog wiring landed in `79e46310ef30` (stub tests in `test_catalog_module_nix.py` and real-devenv tests `test_alpha_serves_and_beta_with_serve_false_runs_no_harmonia`, `test_beta_substitutes_from_alpha_only_after_the_key_is_committed`, `test_a_beta_that_does_not_serve_gives_no_peer_entry` in `opt:catalog-devenv`; `opt:catalog-eval` PASS 93, `opt:catalog-e2e` PASS) | Ruled (R39); fixture pass at evaluation level (S3); no VM boots a machine built through the catalog |

## Added by slice S3, 2026-10-14

The numbers continue after `BSX-156`, the highest number across both ledgers on 2026-10-14. The
kickoff of project 24 said to start at 130; that was out of date ([S3](evidence/S3-CATALOG.md)).
Basix may add rows later, so check both ledgers before you add one. Slice S4 adds `VMT-161` to `VMT-163` at the end of this table ([S4](evidence/S4-APPLY-ROLLBACK.md)).

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-157` | A machine MUST make its cache signing key at first boot. The owner MUST publish the public key by committing it as `.machines/NAME/cache-key.pub`. The catalog MUST give another machine of the workspace a peer entry only when that file exists. A peer key that does not read `NAME:BASE64` MUST fail evaluation. An install MUST need no key. | S3: `opt:sharing-vm` (`test_a_key_that_is_not_committed_gives_no_peer_entry`, `test_a_malformed_public_key_is_refused`); the fixture `tests/fixtures/sharing/default.nix` applies the rule in the VM harness; the catalog applies it too (`test_a_peer_needs_a_committed_key`, `test_the_key_is_trimmed`, `test_beta_substitutes_from_alpha_only_after_the_key_is_committed`) | Proposed by the main agent in S3 (the kickoff asked for a design); no owner ruling; fixture pass for the module, the harness, and the catalog (evaluation level); the catalog applies the rule since `79e46310ef30` (evaluation-level tests); a VM built through the catalog is unproved; ruled (R47) |
| `VMT-158` | The parser MUST fail a file nested deeper than 64 levels with `vendomat.yaml:LINE:COL: nesting deeper than 64 levels`, and MUST parse a file at 64 levels. Sets the limit for `VMT-013`. | S3: `test_a_file_at_the_limit_parses_and_one_level_more_fails`, `test_chains_far_past_the_old_stack_limit_fail_with_the_file_name`, `test_dash_runs_far_past_the_old_stack_limit_fail_with_the_file_name`; the spike overflow was between 800 and 850 levels | S3 choice; no owner ruling; fixture pass |
| `VMT-159` | The required checks MUST be the devenv tasks `check:lint`, `check:format`, `check:types`, and `test:full`. An opt-in check MUST be a task named `opt:NAME` and MUST NOT count for green. | S3: `nix/tasks.nix`; `testee status -r 845172f0768f` (GREEN 4/4, epoch 2, Testee 0.8.0); devenv rejects a task name without a namespace | Ruled (project 22 R18 for the conversion); the name `opt:` is an S3 choice; fixture pass |
| `VMT-160` | A machine entry in `vendomat.yaml` needs at least one key, because the grammar rejects an empty value (`VMT-012`). No ruling says how to declare a machine with no key. | S3: observed during the catalog rewrite; no fixture | Observed gap; open, no ruling covers it |
| `VMT-161` | After a successful bare `vendomat apply`, the command MUST copy `/var/lib/vendomat/cache-key.pub` to `.machines/NAME/cache-key.pub` in the workspace when the file is missing or differs, MUST tell the user to commit it, and MUST NOT commit it. A machine with no key file (`serve: false`) MUST get no copy. | S4: `tests/test_machine_apply.py` (four cases); one assertion in `opt:machines-vm` run `20261014T184833Z-df3bd2858db6` with a stand-in key file | Ruled (R47; it completes `VMT-157`); fixture pass; a real key from the sharing module is unproved |
| `VMT-162` | An exit status 4 of `switch-to-configuration` MUST be a warning: `vendomat apply` and `vendomat rollback` write the record line and print `warning: switch-to-configuration exited 4: the new system is active, but some units failed`. Any other non-zero exit MUST be a fault with no record line. | S4: `test_a_switch_that_exits_4_is_active_with_a_warning_and_is_recorded`; run 3 of `opt:machines-vm` saw exit 4 on an active system (user-manager race) | Ruled (R46); unit test pass |
| `VMT-163` | `apply` and `rollback` MUST watch `vendomat.yaml`, `devenv.lock`, `devenv.nix`, and `devenv.local.nix`. A watched file counts as uncommitted when it is modified, staged, deleted, untracked, or ignored but present. Files that a hatch file imports are not watched. | S4: `tests/test_machine_workspace.py`; the refusal step of `opt:machines-vm` (modified `devenv.nix` and ignored `devenv.local.nix`) | S4 choice from R43; no owner ruling; the import gap is open; fixture pass |

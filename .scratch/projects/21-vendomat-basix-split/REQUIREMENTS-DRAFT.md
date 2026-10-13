# Project 21 requirement ledger (draft)

**Date:** 2026-10-13. Draft from spike W4. A requirement here is proposed until the named evidence
is a pass on the pinned tools. Evidence names refer to the W4 fixtures (F1 to F14, [W4](evidence/W4-CATALOG.md)) or to earlier records. "Unproved" means no
fixture exists. Do not reuse or renumber an ID. Project 20 text stays unchanged.

## ID scheme

Project 20 uses the prefix `DOOR-`. Project 21 uses the prefix `SPLIT-` (Vendomat and Basix, split)
and three digits that start at `001`. A new prefix has two effects. It cannot collide with a project 20
number. It shows the source project at a glance. A successor row names the project 20 item it
supersedes. Project 20 `S` numbers are decisions in its `DECISIONS.md`, not ledger IDs; a successor
names them the same way.

Status words: **Proposed** (no fixture yet), **Fixture pass** (a spike fixture proved it; not an
implementation gate), **Observed gap** (a fixture shows a shortfall), **Awaits owner ruling**
(depends on A1, A2, A11, A12, or A13 of `DECISIONS.md`).

## Successors to project 20 items

| ID | Claim | Supersedes | Evidence | Status |
| --- | --- | --- | --- | --- |
| `SPLIT-001` | Basix MUST have its own repository and release, and Vendomat MUST NOT import, test, or name Basix. | Decision S34 (machine catalog in the Vendomat release); owner ruling R1 | R1 only | Proposed; implementation unproved |
| `SPLIT-002` | A workspace MUST hold `vendomat.yaml`, template-owned `devenv.yaml`, `devenv.lock`, and a `devenv.nix` that the user MAY edit; the catalog module MUST read `vendomat.yaml` with `builtins.readFile` and parse it with a Nix function from the Vendomat source, with no primop and no unsafe Nix setting. | `DOOR-074` (primop; `devenv.nix` must be `{ }`) | F2, F13 (stock devenv 2.4.0, no primop) | Fixture pass |
| `SPLIT-003` | The catalog MUST be a bounded set of named, typed entries; the grammar MUST allow maps, lists of text, lists of maps, nested lists, and tab indentation, and MUST reject `key: - x`; syntax errors MUST read `vendomat.yaml:LINE:COL: reason`. | `DOOR-075` (tabs and lists of maps rejected) | F1, F3, F13; YAML-SPIKE-2 (P1 to P5) | Fixture pass for programs, env, languages, machines; `services` unproved |
| `SPLIT-004` | The Basix ISO MUST install the machine locally with the six steps of the concept; the owner of the command is open. | `DOOR-072` (`vendomat install`) | W2 T3 (VM only); no command exists | Awaits owner ruling (A2) |
| `SPLIT-005` | Native `devenv.nix` and `devenv.local.nix` MUST stay available as an optional, visible escape hatch; no rule MAY say that Vendomat owns every other file. | Concept line "Vendomat owns every other file" (project 20 `CONCEPT.md`, no ID); the `{ }` clause of `DOOR-074` | F6, F8, F11 | Fixture pass |
| `SPLIT-006` | The verbs `apply` and `install`, and the "pinned devenv fork" wording, MUST follow the rulings on A2 and A12. | `DOOR-071` (verbs and pass-through), in part | none | Awaits owner ruling (A2, A12) |

## Grammar

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-010` | Every value in the file MUST be text; the catalog types MUST give the text its meaning; the file MUST have no null. | F1; F3 (`"three"` rejected as a version) | Fixture pass |
| `SPLIT-011` | The parser MUST compare indentation as text with no tab width; a child MUST extend its parent; siblings MUST match; a mix MUST fail with `inconsistent tabs and spaces`. | F13 (`vendomat.yaml:3:3`); YAML-SPIKE-2 P3 | Fixture pass |
| `SPLIT-012` | The parser MUST reject anchors, aliases, merge keys, tags, flow style, block scalars, document markers, empty values, duplicate keys, a colon-space in plain text, a list on the key's line, special first characters, unknown escapes, bad plain keys, and a byte order mark. | F1 (131 hand cases through the catalog); YAML-SPIKE-2 P4 | Fixture pass |
| `SPLIT-013` | A file deeper than the parser limit MUST fail with an error that names the file. | F1 (`deep_1000` fails with Nix `stack overflow; max-call-depth exceeded`, no `vendomat.yaml` prefix) | Observed gap (limit about 800 levels; the message has no file) |

## Reader

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-020` | The parser MUST be plain Nix over builtins only and MUST live in the Vendomat source, pinned by the workspace lock. | F1, F2; `parse.nix` is a byte copy of v3 | Fixture pass (the pin through a published lock is unproved) |
| `SPLIT-021` | The catalog MUST parse the file once; a missing or empty file MUST mean an empty catalog. | F2 (no file, empty file, one key) | Fixture pass |
| `SPLIT-022` | An edit, create, or delete of `vendomat.yaml` MUST show in the next shell with no other step. | F2 (one workspace: no file, then an empty file, then a one-key file, each seen by the next shell); F4b (the cache follows `pyproject.toml`) | Fixture pass for create and edit; delete of `vendomat.yaml` is unproved |

## Catalog

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-030` | The catalog MUST report every bad field in one error before any work, and every line MUST name `vendomat.yaml` and the key path. | F3, F3b | Fixture pass |
| `SPLIT-031` | The error MUST stop every read of the configuration, including `devenv eval` of an unrelated option. | F3 (`dv eval languages.python.enable` gives the same error) | Fixture pass |
| `SPLIT-032` | An unknown key MUST fail and MUST list the known keys; an unknown program name MUST fail even when other fields are bad. | F3, F3b | Fixture pass |
| `SPLIT-033` | `programs` MUST map to `packages`, and `env` MUST map to `env`. | F2, F8 | Fixture pass |
| `SPLIT-034` | The catalog MUST use the native option names, and MUST add only checks and Vendomat defaults. | F4, F5, F9 | Fixture pass |
| `SPLIT-035` | A fault of a schema-checked field MUST carry line and column. | F3 (key path only; the parser returns no line for a value) | Observed gap |
| `SPLIT-036` | The catalog MUST NOT cost more than noise on shell entry. | `logs/timing.log` | Fixture pass |

## Languages

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-040` | A `languages.python` entry MUST turn on `languages.python.enable`, map `version`, and turn on `uv.enable` by default (priority `mkDefault`). | F4, F4d | Fixture pass |
| `SPLIT-041` | The catalog MUST turn on `uv.sync.enable` only when `pyproject.toml` exists in the workspace root, and shell entry MUST print no warning without the file. | F4, F4c (control), F4b | Fixture pass (A9) |
| `SPLIT-042` | A created or deleted `pyproject.toml` MUST change `uv.sync.enable` in the next shell with no other step. | F4b (6 steps, no stale result) | Fixture pass |
| `SPLIT-043` | The template MUST list `nixpkgs-python` and `rust-overlay`, each following `nixpkgs`; no fork patch MAY inherit inputs. | F4, F5 | Fixture pass (retires patch 0007) |
| `SPLIT-044` | A `languages.rust` entry without `version` MUST use the nixpkgs toolchain; with `version` it MUST set `channel = "stable"` and `version`. | F5 (`rustc 1.97.1`, then `rustc 1.81.0`) | Fixture pass |
| `SPLIT-045` | The catalog MUST report a Python version that `nixpkgs-python` lacks. | Code path exists; no fixture | Unproved |
| `SPLIT-046` | A new language MUST be addable to existing workspaces without a template change. | none (project 21 Open question 3) | Unproved |

## Escape hatch

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-050` | The catalog MUST put its mappings in an inner module with `_file = "vendomat.yaml"`, so a conflict error names `vendomat.yaml` and the other file. | F6, F10 | Fixture pass (A8) |
| `SPLIT-051` | A value from the YAML MUST be a plain definition; a scalar set in both places MUST stop with a conflict error that names both files. | F6, F4d | Fixture pass |
| `SPLIT-052` | Lists and maps from the YAML and from Nix MUST merge. | F8 | Fixture pass |
| `SPLIT-053` | `lib.mkForce` in `devenv.nix` MUST win over the YAML. | F7 | Fixture pass |
| `SPLIT-054` | Shell entry MUST print one `advanced:` line when `devenv.nix` or `devenv.local.nix` sets a value, and MUST print nothing for `{ }` stubs or empty files. | F11 | Fixture pass (A8) |
| `SPLIT-055` | The count in the line MUST be the number of settings the file wrote (each leaf of its attribute tree), and MUST NOT claim to be the number of options devenv merged. | F11; `definitionsWithLocations` fails for counting (REPORT, Surprise 1) | Fixture pass for the leaf count; the wording "settings" replaces "options" |
| `SPLIT-056` | `devenv.local.nix` MUST count separately and the line MUST say it applies to this checkout only. | F11 | Fixture pass |
| `SPLIT-057` | An `explain` command MUST print an option's value and the files that set it, from evaluation only. | F12 (`vendomat-explain PATH`); keys inside map options use the key's priority | Fixture pass (prototype; the output format is project 21 Open question 5) |
| `SPLIT-058` | Vendomat MUST check its own lines in `devenv.yaml`. | none | Unproved |
| `SPLIT-059` | A Basix workspace MAY turn the hatch off with one setting. | none | Proposed; not ruled |

## Machines

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-060` | A `machines.NAME.host` entry MUST map to `machines.NAME.target.host`. | F9, F12 | Fixture pass |
| `SPLIT-061` | The catalog MUST set `networking.hostName` to the machine name. | F9, F10 (A10) | Fixture pass |
| `SPLIT-062` | A different `networking.hostName` from another file MUST fail with a conflict that names both files, unless it uses `lib.mkForce`. | F10 | Fixture pass |
| `SPLIT-063` | A machine marked `virtual` MUST set `hardware.facter = null`, and a machine without a report MUST NOT evaluate. | F14 (A14); the key name `virtual` is a proposal | Fixture pass at evaluation level |
| `SPLIT-064` | `machines.NAME.nixos` from the YAML, from `devenv.nix`, and from an imported file MUST merge, whether each is an attribute set or a function. | F9 on the module-only fork input; W2 T4 | Fixture pass; shipping the fork awaits A12 |
| `SPLIT-065` | The YAML machine table MUST map `profile`, `capabilities`, `serve`, and `disk` to Basix modules, the cache module, and one disk layout. | none | Unproved; depends on A1 and A2 |

## Items that await an owner ruling

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-070` | Basix MUST be a flake that lists its inputs and commits its `flake.lock`; a Basix workspace MUST name `basix` and get `vendomat`, `nixpkgs`, the `devenv` input, and the language inputs through `follows` lines that the template writes. | [W3](evidence/W3-TOPOLOGY.md) Q1 to Q6 (stub repositories); naming only `basix` fails with `attribute 'vendomat' missing` | Fixture pass with stubs; awaits owner ruling (A1) |
| `SPLIT-071` | Basix MUST own `install` and the disk guard; Vendomat MUST own `apply`. | W2 T3 (guard) | Awaits owner ruling (A2) |
| `SPLIT-072` | A lasting rollback MUST be: restore `vendomat.yaml` and `devenv.lock`, then apply. The boot menu MUST be for recovery only. | W2 T1 (boot-menu rollback does not move the profile) | Awaits owner ruling (A11) |
| `SPLIT-073` | Hosts and the ISO MUST install `pkgs.devenv` from Vendomat's pinned nixpkgs; the workspace `devenv` input MUST be a module-only fork; the template MUST omit `require_version`. | F2 to F14 ran on stock 2.4.0 with the module-only input; the line `devenv 2.4.0 is newer than devenv input (2.3.1)` shows each entry until `devenv.warnOnNewVersion = false` | Awaits owner ruling (A12) |
| `SPLIT-074` | Vendomat MUST keep a devenv binary with patch 0003, or accept that a fresh machine cannot enter a workspace while the remote is down. | W1 Q2 | Awaits owner ruling (A13) |
| `SPLIT-075` | The `vendomat apply` command MUST read the machine name from the facts file and run the two activation commands. | W2 T1 (commands, not the command) | Awaits owner ruling (A2); unproved |

## Fork retirement (carried by the rows above)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `SPLIT-080` | Patch 0009 (`vendomatFromYAML`) MUST be dropped. | `SPLIT-002`, `SPLIT-003` (F1 to F13) | Fixture pass |
| `SPLIT-081` | Patch 0007 (inherit an imported source's inputs) MUST be dropped. | `SPLIT-043` | Fixture pass |
| `SPLIT-082` | The `nixos = deferredModule` change MUST ship in a module-only `devenv` input and be offered upstream. | `SPLIT-064` | Fixture pass; shipping awaits A12 |

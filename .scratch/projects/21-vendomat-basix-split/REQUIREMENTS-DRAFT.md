# Project 21 requirement ledger (draft)

**Date:** 2026-10-13. Draft from spike W4. A requirement here is proposed until the named evidence
is a pass on the pinned tools. Evidence names refer to the W4 fixtures (F1 to F14, [W4](evidence/W4-CATALOG.md)) or to earlier records. "Unproved" means no
fixture exists. Do not reuse or renumber an ID. Project 20 text stays unchanged.

## ID scheme

Each product has its own prefix (owner ruling R24, 2026-10-13): `VMT-` for Vendomat and `BSX-` for
Basix, three digits each. The W4 draft used one prefix, `SPLIT-`. It was renamed before any ruling,
and each ID kept its number: `BSX-004` became `BSX-004`, `VMT-030` became `VMT-030`. A number
is used under one prefix only. A successor row names the project 20 item it supersedes. Project 20
`S` numbers are decisions in its `DECISIONS.md`, not ledger IDs; a successor names them the same way.
When the Basix repository exists, the `BSX-` rows move there.

Status words: **Proposed** (no fixture yet), **Fixture pass** (a spike fixture proved it; not an
implementation gate), **Observed gap** (a fixture shows a shortfall), **Ruled** (an owner ruling in
`DECISIONS.md` settles the choice; proof may still be open), **Awaits owner ruling**.

## Successors to project 20 items

| ID | Claim | Supersedes | Evidence | Status |
| --- | --- | --- | --- | --- |
| `VMT-001` | Basix MUST have its own repository and release, and Vendomat MUST NOT import, test, or name Basix. | Decision S34 (machine catalog in the Vendomat release); owner ruling R1 | R1 only | Proposed; implementation unproved |
| `VMT-002` | A workspace MUST hold `vendomat.yaml`, template-owned `devenv.yaml`, `devenv.lock`, and a `devenv.nix` that the user MAY edit; the catalog module MUST read `vendomat.yaml` with `builtins.readFile` and parse it with a Nix function from the Vendomat source, with no primop and no unsafe Nix setting. | `DOOR-074` (primop; `devenv.nix` must be `{ }`) | F2, F13 (stock devenv 2.4.0, no primop) | Fixture pass |
| `VMT-003` | The catalog MUST be a bounded set of named, typed entries; the grammar MUST allow maps, lists of text, lists of maps, nested lists, and tab indentation, and MUST reject `key: - x`; syntax errors MUST read `vendomat.yaml:LINE:COL: reason`. | `DOOR-075` (tabs and lists of maps rejected) | F1, F3, F13; YAML-SPIKE-2 (P1 to P5) | Fixture pass for programs, env, languages, machines; `services` unproved |
| `BSX-004` | The Basix ISO MUST install the machine locally with the six steps of the concept; the owner of the command is open. | `DOOR-072` (`vendomat install`) | W2 T3 (VM only); no command exists | Ruled (R13): Basix owns the command; unproved |
| `VMT-005` | Native `devenv.nix` and `devenv.local.nix` MUST stay available as an optional, visible escape hatch; no rule MAY say that Vendomat owns every other file. | Concept line "Vendomat owns every other file" (project 20 `CONCEPT.md`, no ID); the `{ }` clause of `DOOR-074` | F6, F8, F11 | Fixture pass |
| `VMT-006` | The verbs `apply` and `install`, and the "pinned devenv fork" wording, MUST follow the rulings on A2 and A12. | `DOOR-071` (verbs and pass-through), in part | none | Ruled (R13, R22); wording unproved |

## Grammar

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-010` | Every value in the file MUST be text; the catalog types MUST give the text its meaning; the file MUST have no null. | F1; F3 (`"three"` rejected as a version) | Fixture pass |
| `VMT-011` | The parser MUST compare indentation as text with no tab width; a child MUST extend its parent; siblings MUST match; a mix MUST fail with `inconsistent tabs and spaces`. | F13 (`vendomat.yaml:3:3`); YAML-SPIKE-2 P3 | Fixture pass |
| `VMT-012` | The parser MUST reject anchors, aliases, merge keys, tags, flow style, block scalars, document markers, empty values, duplicate keys, a colon-space in plain text, a list on the key's line, special first characters, unknown escapes, bad plain keys, and a byte order mark. | F1 (131 hand cases through the catalog); YAML-SPIKE-2 P4 | Fixture pass |
| `VMT-013` | A file deeper than the parser limit MUST fail with an error that names the file. | F1 (`deep_1000` fails with Nix `stack overflow; max-call-depth exceeded`, no `vendomat.yaml` prefix) | Observed gap (limit about 800 levels; the message has no file) |

## Reader

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-020` | The parser MUST be plain Nix over builtins only and MUST live in the Vendomat source, pinned by the workspace lock. | F1, F2; `parse.nix` is a byte copy of v3 | Fixture pass (the pin through a published lock is unproved) |
| `VMT-021` | The catalog MUST parse the file once; a missing or empty file MUST mean an empty catalog. | F2 (no file, empty file, one key) | Fixture pass |
| `VMT-022` | An edit, create, or delete of `vendomat.yaml` MUST show in the next shell with no other step. | F2 (one workspace: no file, then an empty file, then a one-key file, each seen by the next shell); F4b (the cache follows `pyproject.toml`) | Fixture pass for create and edit; delete of `vendomat.yaml` is unproved |

## Catalog

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-030` | The catalog MUST report every bad field in one error before any work, and every line MUST name `vendomat.yaml` and the key path. | F3, F3b | Fixture pass |
| `VMT-031` | The error MUST stop every read of the configuration, including `devenv eval` of an unrelated option. | F3 (`dv eval languages.python.enable` gives the same error) | Fixture pass |
| `VMT-032` | An unknown key MUST fail and MUST list the known keys; an unknown program name MUST fail even when other fields are bad. | F3, F3b | Fixture pass |
| `VMT-033` | `programs` MUST map to `packages`, and `env` MUST map to `env`. | F2, F8 | Fixture pass |
| `VMT-034` | The catalog MUST use the native option names, and MUST add only checks and Vendomat defaults. | F4, F5, F9 | Fixture pass |
| `VMT-035` | A fault of a schema-checked field MUST carry line and column. | F3 (key path only; the parser returns no line for a value) | Observed gap |
| `VMT-036` | The catalog MUST NOT cost more than noise on shell entry. | `logs/timing.log` | Fixture pass |

## Languages

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-040` | A `languages.python` entry MUST turn on `languages.python.enable`, map `version`, and turn on `uv.enable` by default (priority `mkDefault`). | F4, F4d | Fixture pass |
| `VMT-041` | The catalog MUST turn on `uv.sync.enable` only when `pyproject.toml` exists in the workspace root, and shell entry MUST print no warning without the file. | F4, F4c (control), F4b | Fixture pass (A9) |
| `VMT-042` | A created or deleted `pyproject.toml` MUST change `uv.sync.enable` in the next shell with no other step. | F4b (6 steps, no stale result) | Fixture pass |
| `VMT-043` | The template MUST list `nixpkgs-python` and `rust-overlay`, each following `nixpkgs`; no fork patch MAY inherit inputs. | F4, F5 | Fixture pass (retires patch 0007) |
| `VMT-044` | A `languages.rust` entry without `version` MUST use the nixpkgs toolchain; with `version` it MUST set `channel = "stable"` and `version`. | F5 (`rustc 1.97.1`, then `rustc 1.81.0`) | Fixture pass |
| `VMT-045` | The catalog MUST report a Python version that `nixpkgs-python` lacks. | Code path exists; no fixture | Unproved |
| `VMT-046` | A new language MUST be addable to existing workspaces without a template change. | none (project 21 Open question 3) | Unproved |

## Escape hatch

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-050` | The catalog MUST put its mappings in an inner module with `_file = "vendomat.yaml"`, so a conflict error names `vendomat.yaml` and the other file. | F6, F10 | Fixture pass (A8) |
| `VMT-051` | A value from the YAML MUST be a plain definition; a scalar set in both places MUST stop with a conflict error that names both files. | F6, F4d | Fixture pass |
| `VMT-052` | Lists and maps from the YAML and from Nix MUST merge. | F8 | Fixture pass |
| `VMT-053` | `lib.mkForce` in `devenv.nix` MUST win over the YAML. | F7 | Fixture pass |
| `VMT-054` | Shell entry MUST print one `advanced:` line when `devenv.nix` or `devenv.local.nix` sets a value, and MUST print nothing for `{ }` stubs or empty files. | F11 | Fixture pass (A8) |
| `VMT-055` | The count in the line MUST be the number of settings the file wrote (each leaf of its attribute tree), and MUST NOT claim to be the number of options devenv merged. | F11; `definitionsWithLocations` fails for counting (REPORT, Surprise 1) | Fixture pass for the leaf count; the wording "settings" replaces "options" |
| `VMT-056` | `devenv.local.nix` MUST count separately and the line MUST say it applies to this checkout only. | F11 | Fixture pass |
| `VMT-057` | `vendomat explain` MUST print the user's YAML keys, each with its native option, value, and source file, then a section for options set only in Nix; `--json` MUST print the same data. | F12 (prototype prints value and file) | Ruled (R27); format unproved |
| `VMT-058` | Vendomat MUST check its own lines in `devenv.yaml`. | none | Unproved |
| `BSX-059` | A Basix workspace MUST keep hatch files working and MUST make the shell line and `explain` point to the lesson that introduces Nix (a soft lock). | none | Ruled (R26); unproved |

## Machines

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-060` | A `machines.NAME.host` entry MUST map to `machines.NAME.target.host`. | F9, F12 | Fixture pass |
| `VMT-061` | The catalog MUST set `networking.hostName` to the machine name. | F9, F10 (A10) | Fixture pass |
| `VMT-062` | A different `networking.hostName` from another file MUST fail with a conflict that names both files, unless it uses `lib.mkForce`. | F10 | Fixture pass |
| `VMT-063` | A machine marked `virtual` MUST set `hardware.facter = null`, and a machine without a report MUST NOT evaluate. | F14 (A14) | Fixture pass at evaluation level; key name ruled (R23) |
| `VMT-064` | `machines.NAME.nixos` from the YAML, from `devenv.nix`, and from an imported file MUST merge, whether each is an attribute set or a function. | F9 on the module-only fork input; W2 T4 | Fixture pass; shipping the fork awaits A12 |
| `BSX-065` | The YAML machine table MUST map `profile`, `capabilities`, `serve`, and `disk` to Basix modules, the cache module, and one disk layout. | none | Unproved; depends on A1 and A2 |

## Items that await an owner ruling

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `BSX-070` | Basix MUST be a flake that lists its inputs and commits its `flake.lock`; a Basix workspace MUST name `basix` and get `vendomat`, `nixpkgs`, the `devenv` input, and the language inputs through `follows` lines that the template writes. | [W3](evidence/W3-TOPOLOGY.md) Q1 to Q6 (stub repositories); naming only `basix` fails with `attribute 'vendomat' missing` | Fixture pass with stubs; awaits owner ruling (A1) |
| `BSX-071` | Basix MUST own `install` and the disk guard; Vendomat MUST own `apply`. | W2 T3 (guard); W5 (hook) | Ruled (R13, R16) |
| `VMT-072` | A lasting rollback MUST be: restore `vendomat.yaml` and `devenv.lock`, then apply. The boot menu MUST be for recovery only. | W2 T1 (boot-menu rollback does not move the profile) | Awaits owner ruling (A11) |
| `VMT-073` | Hosts and the ISO MUST install `pkgs.devenv` from Vendomat's pinned nixpkgs; the workspace `devenv` input MUST be a module-only fork; the template MUST omit `require_version`. | F2 to F14 ran on stock 2.4.0 with the module-only input; the line `devenv 2.4.0 is newer than devenv input (2.3.1)` shows each entry until `devenv.warnOnNewVersion = false` | Ruled (R22) |
| `VMT-074` | Vendomat MUST keep a devenv binary with patch 0003, or accept that a fresh machine cannot enter a workspace while the remote is down. | W1 Q2 | Awaits owner ruling (A13) |
| `VMT-075` | The `vendomat apply` command MUST read the machine name from the facts file and run the two activation commands. | W2 T1 (commands, not the command) | Ruled (R13, R15); unproved |

## Fork retirement (carried by the rows above)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-080` | Patch 0009 (`vendomatFromYAML`) MUST be dropped. | `VMT-002`, `VMT-003` (F1 to F13) | Fixture pass |
| `VMT-081` | Patch 0007 (inherit an imported source's inputs) MUST be dropped. | `VMT-043` | Fixture pass |
| `VMT-082` | The `nixos = deferredModule` change MUST ship in a module-only `devenv` input and be offered upstream. | `VMT-064` | Fixture pass; shipping awaits A12 |

## Added by the owner rulings of 2026-10-13

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-090` | The catalog MUST map `services.postgres` and `services.redis` as typed keys, as slice 1 did. | Slice 1 catalog (`devenv/devenv.nix`); not in the W4 catalog | Ruled (R23); unproved on the Nix parser |
| `VMT-091` | Catalog defaults MUST use `lib.mkDefault`; YAML values MUST stay plain definitions. | F4d, F6 | Ruled (R23); fixture pass |
| `VMT-092` | A `languages.python` entry MUST accept `uv` and `uv.sync`; `uv.sync` MUST accept `auto`, `true`, and `false`, and `auto` MUST turn sync on only when `pyproject.toml` exists. | F4, F4b (the `auto` behaviour) | Ruled (R20); key names unproved |
| `VMT-093` | A personal setting outside `vendomat.yaml` MUST hide the shell `advanced:` line; `explain` MUST still show every source. | none | Ruled (R19); unproved |
| `VMT-094` | `vendomat update` MUST add missing template lines to `devenv.yaml`, and an error for a missing line MUST name the exact line. | none; whether devenv fetches unused inputs is unmeasured | Ruled (R25); unproved |
| `VMT-095` | The module-only `devenv` input MUST give every machine `build.vm` and `build.iso` (typed `nullOr package`), and `build.iso` MUST extend the machine with the ISO module, the six required overrides, and `machines.NAME.iso.modules`. | W7, W8 | Ruled (R17); fixture pass |
| `BSX-096` | The Basix disk layout MUST run the blank-disk guard as a disko `preCreateHook`, and every guarded disk MUST keep `destroy = false`, checked at build time. | W5 (hook); the build-time check is not built | Ruled (R16); check unproved |

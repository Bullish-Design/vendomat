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
| `VMT-002` | A workspace MUST hold `vendomat.yaml`, template-owned `devenv.yaml`, `devenv.lock`, and a `devenv.nix` that the user MAY edit; the catalog module MUST read `vendomat.yaml` with `builtins.readFile` and parse it with a Nix function from the Vendomat source, with no primop and no unsafe Nix setting. | `DOOR-074` (primop; `devenv.nix` must be `{ }`) | F2, F13 (stock devenv 2.4.0, no primop) | Ruled (R2, R7); fixture pass |
| `VMT-003` | The catalog MUST be a bounded set of named, typed entries; the grammar MUST allow maps, lists of text, lists of maps, nested lists, and tab indentation, and MUST reject `key: - x`; syntax errors MUST read `vendomat.yaml:LINE:COL: reason`. | `DOOR-075` (tabs and lists of maps rejected) | F1, F3, F13; YAML-SPIKE-2 (P1 to P5) | Ruled (R2, R8 to R10); fixture pass for programs, env, languages, machines; `services` is covered by `VMT-090` |
| `BSX-004` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | — | Moved |
| `VMT-005` | Native `devenv.nix` and `devenv.local.nix` MUST stay available as an optional, visible escape hatch; no rule MAY say that Vendomat owns every other file. | Concept line "Vendomat owns every other file" (project 20 `CONCEPT.md`, no ID); the `{ }` clause of `DOOR-074` | F6, F8, F11 | Ruled (R12); fixture pass |
| `VMT-006` | The verbs `apply` and `install`, and the "pinned devenv fork" wording, MUST follow the rulings on A2 and A12. | `DOOR-071` (verbs and pass-through), in part | none | Ruled (R13, R22); wording unproved |

## Grammar

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-010` | Every value in the file MUST be text; the catalog types MUST give the text its meaning; the file MUST have no null. | F1; F3 (`"three"` rejected as a version) | Fixture pass (grammar basis R2, R7) |
| `VMT-011` | The parser MUST compare indentation as text with no tab width; a child MUST extend its parent; siblings MUST match; a mix MUST fail with `inconsistent tabs and spaces`. | F13 (`vendomat.yaml:3:3`); YAML-SPIKE-2 P3 | Ruled (R9, R10); fixture pass |
| `VMT-012` | The parser MUST reject anchors, aliases, merge keys, tags, flow style, block scalars, document markers, empty values, duplicate keys, a colon-space in plain text, a list on the key's line, special first characters, unknown escapes, bad plain keys, and a byte order mark. | F1 (131 hand cases through the catalog); YAML-SPIKE-2 P4 | Fixture pass (grammar basis R7 to R10) |
| `VMT-013` | A file deeper than the parser limit MUST fail with an error that names the file. | F1 (`deep_1000` fails with Nix `stack overflow; max-call-depth exceeded`, no `vendomat.yaml` prefix) | Observed gap (limit about 800 levels; the message has no file); open, no ruling covers it |

## Reader

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-020` | The parser MUST be plain Nix over builtins only and MUST live in the Vendomat source, pinned by the workspace lock. | F1, F2; `parse.nix` is a byte copy of v3 | Ruled (R7); fixture pass (the pin through a published lock is unproved) |
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
| `VMT-035` | A fault of a schema-checked field MUST carry line and column. | F3 (key path only; the parser returns no line for a value) | Observed gap; open, no ruling covers it |
| `VMT-036` | The catalog MUST NOT cost more than noise on shell entry. | `logs/timing.log` | Fixture pass |

## Languages

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-040` | A `languages.python` entry MUST turn on `languages.python.enable`, map `version`, and turn on `uv.enable` by default (priority `mkDefault`). | F4, F4d | Ruled (R11); fixture pass |
| `VMT-041` | The catalog MUST turn on `uv.sync.enable` only when `pyproject.toml` exists in the workspace root, and shell entry MUST print no warning without the file. | F4, F4c (control), F4b | Ruled (R20); fixture pass (A9) |
| `VMT-042` | A created or deleted `pyproject.toml` MUST change `uv.sync.enable` in the next shell with no other step. | F4b (6 steps, no stale result) | Fixture pass |
| `VMT-043` | The template MUST list `nixpkgs-python` and `rust-overlay`, each following `nixpkgs`; no fork patch MAY inherit inputs. | F4, F5 | Ruled (R11, R28); fixture pass (retires patch 0007) |
| `VMT-044` | A `languages.rust` entry without `version` MUST use the nixpkgs toolchain; with `version` it MUST set `channel = "stable"` and `version`. | F5 (`rustc 1.97.1`, then `rustc 1.81.0`) | Ruled (R11); fixture pass |
| `VMT-045` | The catalog MUST report a Python version that `nixpkgs-python` lacks. | Code path exists; no fixture | Unproved |
| `VMT-046` | A new language MUST be addable to existing workspaces without a template change. | none (project 21 Open question 3) | Superseded in part by `VMT-094` (R25): the template gains the line and `vendomat update` brings it to existing workspaces; unproved |

## Escape hatch

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-050` | The catalog MUST put its mappings in an inner module with `_file = "vendomat.yaml"`, so a conflict error names `vendomat.yaml` and the other file. | F6, F10 | Ruled (R19); fixture pass (A8) |
| `VMT-051` | A value from the YAML MUST be a plain definition; a scalar set in both places MUST stop with a conflict error that names both files. | F6, F4d | Ruled (R12); fixture pass |
| `VMT-052` | Lists and maps from the YAML and from Nix MUST merge. | F8 | Ruled (R12); fixture pass |
| `VMT-053` | `lib.mkForce` in `devenv.nix` MUST win over the YAML. | F7 | Ruled (R12); fixture pass |
| `VMT-054` | Shell entry MUST print one `advanced:` line when `devenv.nix` or `devenv.local.nix` sets a value, and MUST print nothing for `{ }` stubs or empty files. | F11 | Ruled (R19); fixture pass (A8) |
| `VMT-055` | The count in the line MUST be the number of settings the file wrote (each leaf of its attribute tree), and MUST NOT claim to be the number of options devenv merged. | F11; `definitionsWithLocations` fails for counting (REPORT, Surprise 1) | Fixture pass for the leaf count; the wording "settings" replaces "options" |
| `VMT-056` | `devenv.local.nix` MUST count separately and the line MUST say it applies to this checkout only. | F11 | Fixture pass |
| `VMT-057` | `vendomat explain` MUST print the user's YAML keys, each with its native option, value, and source file, then a section for options set only in Nix; `--json` MUST print the same data. | F12 (prototype prints value and file) | Ruled (R27); format unproved |
| `VMT-058` | Vendomat MUST check its own lines in `devenv.yaml`. | none | Unproved; no ruling covers it |
| `BSX-059` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |

## Machines

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-060` | A `machines.NAME.host` entry MUST map to `machines.NAME.target.host`. | F9, F12 | Fixture pass |
| `VMT-061` | The catalog MUST set `networking.hostName` to the machine name. | F9, F10 (A10) | Ruled (R21); fixture pass |
| `VMT-062` | A different `networking.hostName` from another file MUST fail with a conflict that names both files, unless it uses `lib.mkForce`. | F10 | Ruled (R21); fixture pass |
| `VMT-063` | A machine marked `virtual` MUST set `hardware.facter = null`, and a machine without a report MUST NOT evaluate. | F14 (A14) | Fixture pass at evaluation level; key name ruled (R23) |
| `VMT-064` | `machines.NAME.nixos` from the YAML, from `devenv.nix`, and from an imported file MUST merge, whether each is an attribute set or a function. | F9 on the module-only fork input; W2 T4 | Ruled (R14, R22, R34); fixture pass |
| `BSX-065` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved; superseded by `BSX-124` in the Basix ledger (R38) |

## Items that awaited an owner ruling (all ruled)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `BSX-070` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-071` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-072` | A lasting rollback MUST be: restore `vendomat.yaml` and `devenv.lock`, then apply. The boot menu MUST be for recovery only. | W2 T1 (boot-menu rollback does not move the profile) | Ruled (R30); the commit record is unproved |
| `VMT-073` | Hosts and the ISO MUST install `pkgs.devenv` from Vendomat's pinned nixpkgs; the workspace `devenv` input MUST be a module-only fork; the template MUST omit `require_version`. | F2 to F14 ran on stock 2.4.0 with the module-only input; the line `devenv 2.4.0 is newer than devenv input (2.3.1)` shows each entry until `devenv.warnOnNewVersion = false` | Ruled (R22); D2 ruled (R41) |
| `VMT-074` | Vendomat MUST keep a devenv binary with patch 0003, or accept that a fresh machine cannot enter a workspace while the remote is down. | W1 Q2 | Ruled (R31); W6 |
| `VMT-075` | The `vendomat apply` command MUST read the machine name from the facts file and run the two activation commands. | W2 T1 (commands, not the command) | Ruled (R13, R15); unproved |

## Fork retirement (carried by the rows above)

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-080` | Patch 0009 (`vendomatFromYAML`) MUST be dropped. | `VMT-002`, `VMT-003` (F1 to F13) | Ruled (R7); fixture pass |
| `VMT-081` | Patch 0007 (inherit an imported source's inputs) MUST be dropped. | `VMT-043` | Ruled (R11); fixture pass |
| `VMT-082` | The `nixos = deferredModule` change MUST ship in a module-only `devenv` input; Vendomat MUST NOT open an upstream pull request for it (R34). | `VMT-064` | Ruled (R14, R22, R34); fixture pass; tag name ruled (R44) |

## Added by the owner rulings of 2026-10-13

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-090` | The catalog MUST map `services.postgres` and `services.redis` as typed keys, as slice 1 did. | Slice 1 catalog (`devenv/devenv.nix`); not in the W4 catalog | Ruled (R23); unproved on the Nix parser |
| `VMT-091` | Catalog defaults MUST use `lib.mkDefault`; YAML values MUST stay plain definitions. | F4d, F6 | Ruled (R23); fixture pass |
| `VMT-092` | A `languages.python` entry MUST accept `uv` and `uv.sync`; `uv.sync` MUST accept `auto`, `true`, and `false`, and `auto` MUST turn sync on only when `pyproject.toml` exists. | F4, F4b (the `auto` behaviour) | Ruled (R20); key names unproved |
| `VMT-093` | A personal setting outside `vendomat.yaml` MUST hide the shell `advanced:` line; `explain` MUST still show every source. | none | Ruled (R19); unproved; setting ruled (R45) |
| `VMT-094` | `vendomat update` MUST add missing template lines to `devenv.yaml`, and an error for a missing line MUST name the exact line. | none; whether devenv fetches unused inputs is unmeasured | Ruled (R25); unproved |
| `VMT-095` | The module-only `devenv` input MUST give every machine `build.vm` and `build.iso` (typed `nullOr package`), and `build.iso` MUST extend the machine with the ISO module, the six required overrides, and `machines.NAME.iso.modules`. | W7, W8 | Ruled (R17); fixture pass |
| `BSX-096` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-097` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-098` | `vendomat rollback` MUST restore the configuration files from an earlier commit, MUST end in a new commit, and MUST refuse uncommitted changes; each machine MUST keep a record from system path to workspace commit. | W9 R2, R3 (the record is not built) | Ruled (R30); record unproved; record ruled (R43) |
| `VMT-099` | The catalog MUST set `machines.NAME.vendomat.mode` to `adopt-existing` for an installed machine, and the host binary MUST refuse `machines install` for it before any contact. | W6 B5 | Ruled (R31); fixture pass; install marker ruled (R42) |
| `BSX-100` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |

## Added at the design freeze, 2026-10-13

Rows for ruled behaviour that had no row, and for the open gaps. The numbers continue after
`BSX-100`.

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `VMT-101` | Machines MUST be devenv Machines on a pinned devenv version; plain NixOS flakes MUST NOT be the machine path. | W2 (all four fixtures on stock devenv 2.4.0) | Ruled (R4); fixture pass |
| `VMT-102` | Vendomat MUST NOT offer an `eject` command until a clear need appears; `vendomat explain` is the read-only window into Nix. | none | Ruled (R5) |
| `VMT-103` | Routine use MUST need no Nix file; the catalog MUST cover routine needs. | F1 to F14 for programs, env, languages, and machines | Ruled (R6); fixture pass for those keys |
| `BSX-104` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-105` | The host and ISO binary MUST be `pkgs.devenv` from Vendomat's pinned nixpkgs with patches 0003 and 0005 applied through an overlay, MUST NOT carry patch 0008, and MUST be built and cached in Attic. The overlay MUST drop the `CHANGELOG.md` hunk of 0003, because that hunk needs patch 0001. A nixpkgs bump MUST recheck PR #3244. | [W6](evidence/W6-HOST-BINARY.md) (build 23 to 49 min, one new 218 MiB path, stock closure kept) | Ruled (R16, R22, R31); fixture pass for the build; the Attic cache is unproved; superseded by `VMT-126` (R39) |
| `VMT-106` | Patch 0005 MUST split: the Rust half (`machines.rs`) MUST ship in the host binary, and the module half (`machines.nix`, 39 lines) MUST ship in the module-only fork. | W6 B5 | Ruled (R31); fixture pass |
| `VMT-107` | A module in `machines.NAME.iso.modules` that changes an option which `build.iso` overrides MUST use `lib.mkForce`, because devenv's six overrides use priority 60 and a plain value loses without a message. | [W8](evidence/W8-ISO-POLICY.md) (`boot.loader.timeout`: plain value ignored, `mkForce` works) | Ruled (R17); fixture pass |
| `VMT-108` | A machine that imports its own ISO module MUST keep its own image; `build.iso` MUST NOT add the ISO module twice. | [W7](evidence/W7-BUILD-OPTIONS.md) (first try failed to boot), [W8](evidence/W8-ISO-POLICY.md) Q5 | Ruled (R17); fixture pass |
| `BSX-109` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-110` | `system.configurationRevision` MUST NOT hold the workspace commit; the per-machine record of `VMT-098` is the only link from a system path to a commit. | [W9](evidence/W9-ROLLBACK.md) (each commit gives a new generation) | Ruled (R30); fixture observation; record ruled (R43) |
| `VMT-111` | One `vendomat update` MUST move the Basix and Vendomat pair together, and it MUST keep the `follows` lines of `BSX-070` current. | [W3](evidence/W3-TOPOLOGY.md) (one `devenv update` moved the pair) | Ruled (R28); fixture pass with stubs; D2 ruled (R41) |
| `VMT-112` | A workspace that builds with `vendomat.yaml` MUST pin Vendomat in its own `devenv.lock`; a personal tool MUST NOT enter a workspace lock. | W3; project 22 clone test | Ruled (R33); fixture pass for the first clause |
| `VMT-113` | Vendomat MUST NOT open an upstream pull request for a devenv patch. The module-only fork and the patched binary are long-lived. Vendomat MAY watch upstream (PR #3244, releases). The owner MAY revisit after months of use. | none | Ruled (R34) |
| `BSX-114` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `BSX-115` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-116` | Template inputs that a workspace does not use MUST NOT cost a fetch on shell entry. | none; devenv may fetch unused inputs (R25 asks for a spike) | Unproved |
| `VMT-117` | The wrapper MUST trim devenv's Nix trace so the `vendomat.yaml:` lines come first. | [W4](evidence/W4-CATALOG.md) (about 300 lines of trace print before the message) | Observed gap; open, no ruling covers it |
| `VMT-118` | Shell entry MUST print no devenv version warning. | [W1](evidence/W1-FORK-REVIEW.md) Q1 (`devenv 2.4.0 is newer than devenv input (2.3.1)`) | Observed gap; the version file of the module-only fork or `devenv.warnOnNewVersion = false` would silence it; neither is proved through the catalog; open, no ruling covers it |
| `BSX-119` | Moved to the Basix repository, `.scratch/projects/001-initial-concept/REQUIREMENTS.md`. | — | Moved |
| `VMT-120` | Attic MUST stay until a two-machine Harmonia check passes on real machines; a serving machine MUST make its own signing key, and a client MUST substitute from it. | project 20 S6 (two VMs only) | Unproved; superseded by `VMT-127` (R39) |
| `VMT-121` | The catalog together with a flake Basix, and ISO and VM builds through the catalog, MUST work. | none | Unproved |
| `VMT-122` | The catalog MUST map no home key; homes MUST stay outside Vendomat, and devenv's native `machines.NAME.home-manager` MUST be reachable only through the escape hatch. | none | Ruled (R35) |
| `VMT-123` | Vendomat MUST ship no host-side module; a workspace MUST get Vendomat only through its own lock, and the project 14 `share/vendomat/consumer-module.nix` and `machine.json` MUST be removed with the project 14 code. | Project 22 [HOME-PORT](../22-owner-estate/evidence/HOME-PORT.md) (0 readers) | Ruled (R36) |
| `VMT-126` | The host and ISO binary MUST be `pkgs.devenv` from Vendomat's pinned nixpkgs with patches 0003 and 0005 applied through an overlay, MUST NOT carry patch 0008, and MUST be kept in the building machine's store under a GC root; no slice MAY push it to Attic. The overlay MUST drop the `CHANGELOG.md` hunk of 0003. A nixpkgs bump MUST recheck PR #3244. Supersedes `VMT-105`. | [W6](evidence/W6-HOST-BINARY.md) | Ruled (R39); fixture pass for the build |
| `VMT-127` | The new system MUST configure no Attic. A machine MUST share build outputs through Harmonia with a signing key it makes at first boot, and a client MUST substitute from it with `fallback = true` and a short timeout. Supersedes `VMT-120`. | project 20 S6 (two VMs only) | Ruled (R39); unproved (S3 two VMs, S7 real machines) |
| `VMT-128` | The catalog MUST map the machine key `serve` (default on; `serve: false` turns it off) to Vendomat's sharing module: Harmonia on the machine and the substituter and key on the other machines of the workspace. | none | Ruled (R39); unproved |

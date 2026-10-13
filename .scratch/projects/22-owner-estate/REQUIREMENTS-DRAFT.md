# Project 22 requirement ledger (draft)

**Date:** 2026-10-13. Draft from the concept and W1. A requirement here is proposed until the named
evidence is a pass on the pinned tools. Do not reuse or renumber an ID. Project 21 text stays
unchanged.

## ID scheme

Project 20 uses `DOOR-`, project 21 uses `SPLIT-`. Project 22 uses `ESTATE-` and three digits that
start at `001`. The new prefix cannot collide with an earlier number, and it shows the source
project at a glance.

Status words: **Proposed** (no fixture yet), **Fixture pass** (a spike fixture proved it; not an
implementation gate), **Observed gap** (a fixture shows a shortfall), **Awaits owner ruling**
(depends on a recommendation in `DECISIONS.md`).

## Layers

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-001` | The estate MUST have four layers: machine, home, overlay, project. Each layer MUST have one source of truth. | R7 | Proposed |
| `ESTATE-002` | The machine layer MUST come from nix-systems as devenv Machines. | R4; project 21 R4 | Proposed |
| `ESTATE-003` | The home layer MUST be standalone Home Manager, one `homeConfigurations."<user>@<machine>"` per user and machine. No machine MAY run Home Manager as a NixOS module. | R3, R8 | Proposed (ruled; implementation unproved) |
| `ESTATE-004` | nix-meta MUST hold the homes; nix-systems MUST hold the machines. | R2, R4, R9 | Proposed (ruled; implementation unproved) |
| `ESTATE-005` | The machine layer MUST NOT install or pin a personal tool. | Concept rule 2 | Proposed |

## Pins

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-010` | A personal tool MUST appear in exactly one lock: the home lock. A flake check MUST fail on a second node for a family tool. | Concept rule 1; nix-meta lock holds 3 devman, 2 gitman, 2 repoman nodes today | Proposed |
| `ESTATE-011` | A project repository MUST NOT declare a personal-tool input, import, or option. | R1; [TOOL-CLASSES](evidence/TOOL-CLASSES.md) | Awaits owner ruling (A3) |
| `ESTATE-012` | A personal input MUST come from the collection at a release tag. No input MAY use `git+file://`, `path:`, or a branch ref. | Project 21 collection rule | Awaits owner ruling (A5) |
| `ESTATE-013` | A tool under development MUST reach the repositories through `--override-input` on the home switch, never through a repository file. | Concept | Proposed; W2 |
| `ESTATE-014` | A project dependency (for example mancore in linkman) MAY be pinned in the repository. | Clone test | Proposed |

## Project configuration

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-020` | Each repository manifest that a personal tool reads MUST carry a schema number. A tool MUST refuse an unknown schema with an error that names the file. | Concept rule 5 | Proposed |
| `ESTATE-021` | A tool that reads configuration MUST resolve keys in this order: flag, repository manifest, project overlay, owner default, built-in default. The repository layer MUST accept a closed key set. | Concept; agentman's current behaviour | Proposed |
| `ESTATE-022` | Tools MUST call fixed task names (`base:check`, `base:test`). The repository MUST own the task bodies, and they MUST run without a personal tool. | devman `groups/base/README.md` | Proposed |
| `ESTATE-023` | The owner's Testee manifest MUST live in the project overlay, and its checks MUST call the base tasks. | [TOOL-CLASSES](evidence/TOOL-CLASSES.md) | Superseded by `ESTATE-025` to `ESTATE-028` (R10) |
| `ESTATE-024` | A repository MUST NOT hold a copy of personal content (skills, tool configuration, generated skills). | Concept rule 7 | Proposed |
| `ESTATE-025` | Each repository MUST define the tasks `check:lint`, `check:format`, `check:types`, `test:quick`, and `test:full`; `base:check` MUST chain to the `check:*` tasks and `base:test` to `test:full`. | R10 | Proposed |
| `ESTATE-026` | A template MUST write each standard task as a placeholder that prints how to configure it and exits 78. A placeholder MUST NOT exit 0. | R10 | Proposed |
| `ESTATE-027` | A repository MAY replace a standard task with an explicit exit 0 and a one-line reason ("not applicable"). | R10 | Proposed |
| `ESTATE-028` | Testee MUST run the standard tasks by name, with no devenv module and no per-repository configuration, and MUST report exit 78 as "not set up", apart from pass and fail. | R10 | Proposed; W4 |

## Eval-time modules

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-030` | The home MUST install the eval-time devenv modules under one user directory, outside `~/.local/share/devman/`. | R11 | Proposed (ruled; name open) |
| `ESTATE-031` | The home MUST link that directory as one directory symlink, never file by file. Superseded by `ESTATE-035` (R12; W9 found the directory behaviour incidental). | [W1](evidence/W1-DEVLAYER-PATH.md) F4 (directory link picked up); F3 and F5 (file links stale) | Fixture pass (simulated tree); W2 for real Home Manager |
| `ESTATE-032` | A per-file symlink to a store file MUST be treated as stale after a switch. | [W1](evidence/W1-DEVLAYER-PATH.md) F3, F5 | Observed gap (devenv 2.4.0 evaluation cache) |
| `ESTATE-034` | No repository MAY import from the devlayer directory before a record explains, from devenv's source, why a directory-symlink change invalidates the evaluation cache and a file-symlink change does not. | R11; [W9](evidence/W9-EVAL-CACHE.md) | Met by W9 (record exists) |
| `ESTATE-035` | Home Manager activation MUST write one real file outside the store (the pointer) that names the layer's store path, and MUST rewrite it only when that path changes. Overlay `devenv.local.nix` files MUST import the pointer, never a store path or a symlink. | R12; [W9](evidence/W9-EVAL-CACHE.md) | Proposed; W10 |
| `ESTATE-036` | A fixture MUST fail when the pinned devenv stops catching a changed pointer file, or a changed directory symlink. | W9 | Proposed; W10 |
| `ESTATE-033` | A module in the directory MUST name its commands by store path, not by a system profile path. | [HOME-PORT](evidence/HOME-PORT.md) (`modules/link.nix:71`) | Proposed |

## Fleet doctor

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-040` | One command MUST check every registered repository against `ESTATE-011`, `ESTATE-020`, and `ESTATE-024`, and exit 1 on a finding. | Concept | Awaits owner ruling (A6); W5 |
| `ESTATE-041` | The command MUST fail when a repository's evaluation cache holds a devenv module store path that differs from the live one. | `ESTATE-032` | Superseded by `ESTATE-043` (W9: an untracked import leaves no row) |
| `ESTATE-043` | The command MUST fail on an overlay import whose final path component is a symlink, and on an import with no row in the repository's evaluation cache. | [W9](evidence/W9-EVAL-CACHE.md); prototype `doctor_check.py` | Proposed; W5 |
| `ESTATE-042` | The command MUST fail when a personal tool resolves on `PATH` from a second source. | [FAMILY-DELIVERY](evidence/FAMILY-DELIVERY.md) | Proposed |

## Machine and home pairs

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-050` | A pair with a machine half and a home half MUST take its shared package or constants from one flake, and both halves MUST pin the same tag. | Concept | Proposed; W8 |
| `ESTATE-051` | A check MUST compare the running versions of each pair. | Concept | Proposed; W8 |
| `ESTATE-052` | A home module MUST NOT read the machine's configuration (`osConfig`, `config.users.users`, `config.services.*`). | [HOME-PORT](evidence/HOME-PORT.md) | Proposed |

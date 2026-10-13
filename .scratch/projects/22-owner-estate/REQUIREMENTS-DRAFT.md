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
| `ESTATE-023` | The owner's Testee manifest MUST live in the project overlay, and its checks MUST call the base tasks. | [TOOL-CLASSES](evidence/TOOL-CLASSES.md) | Proposed; W4 |
| `ESTATE-024` | A repository MUST NOT hold a copy of personal content (skills, tool configuration, generated skills). | Concept rule 7 | Proposed |

## Eval-time modules

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-030` | The home MUST install the eval-time devenv modules under one user directory, outside `~/.local/share/devman/`. | Concept | Awaits owner ruling (A4) |
| `ESTATE-031` | The home MUST link that directory as one directory symlink, never file by file. | [W1](evidence/W1-DEVLAYER-PATH.md) F4 (directory link picked up); F3 and F5 (file links stale) | Fixture pass (simulated tree); W2 for real Home Manager |
| `ESTATE-032` | A per-file symlink to a store file MUST be treated as stale after a switch. | [W1](evidence/W1-DEVLAYER-PATH.md) F3, F5 | Observed gap (devenv 2.4.0 evaluation cache) |
| `ESTATE-033` | A module in the directory MUST name its commands by store path, not by a system profile path. | [HOME-PORT](evidence/HOME-PORT.md) (`modules/link.nix:71`) | Proposed |

## Fleet doctor

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-040` | One command MUST check every registered repository against `ESTATE-011`, `ESTATE-020`, and `ESTATE-024`, and exit 1 on a finding. | Concept | Awaits owner ruling (A6); W5 |
| `ESTATE-041` | The command MUST fail when a repository's evaluation cache holds a devenv module store path that differs from the live one. | `ESTATE-032` | Proposed; W5 |
| `ESTATE-042` | The command MUST fail when a personal tool resolves on `PATH` from a second source. | [FAMILY-DELIVERY](evidence/FAMILY-DELIVERY.md) | Proposed |

## Machine and home pairs

| ID | Claim | Evidence | Status |
| --- | --- | --- | --- |
| `ESTATE-050` | A pair with a machine half and a home half MUST take its shared package or constants from one flake, and both halves MUST pin the same tag. | Concept | Proposed; W8 |
| `ESTATE-051` | A check MUST compare the running versions of each pair. | Concept | Proposed; W8 |
| `ESTATE-052` | A home module MUST NOT read the machine's configuration (`osConfig`, `config.users.users`, `config.services.*`). | [HOME-PORT](evidence/HOME-PORT.md) | Proposed |

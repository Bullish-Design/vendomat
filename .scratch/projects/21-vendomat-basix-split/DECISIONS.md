# Project 21 decisions

**Date:** 2026-10-12. The owner opened a clean-slate review: "Ignore all previous
requirements/specs/decisions. Our only goal is to have the best, cleanest, most elegant concept
and architecture possible." The rulings below come from that session. They change concept only.
No production code, consumer, or machine changed.

## Owner rulings

| # | Ruling | Owner words (2026-10-12) | Effect |
| --- | --- | --- | --- |
| R1 | Basix moves to its own repository. Vendomat does not depend on Basix. | "I want to split out the Basix concept into its own separate repo." | Replaces project 20 S34. |
| R2 | YAML stays the user format. | "I like yaml for this. It'll be cleaner and easier for newcomers to grasp." | The parser moves into Nix (R7). |
| R3 | Two names: Vendomat is the tool, Basix the distribution. | "Two names" | `vendomat` and `vendomat.yaml` stay in Basix workspaces. |
| R4 | Machines use devenv Machines on a pinned devenv. | "I want devenv machines." "We'll pin a devenv version." | Plain NixOS flakes are not the machine path. |
| R5 | No `eject` command until a clear need appears. | "Agreed on dropping eject until we have a clear need." | A read-only `explain` is the preferred window into Nix. |
| R6 | `vendomat.yaml` is the primary interface. Routine use needs no Nix file. | "The whole point of vendomat is that the user doesn't need to interact with .nix files." | The catalog must cover routine needs. |
| R7 | The YAML parser is written in Nix; the fork's primop is not needed. | Approved the spike ("Do a more thorough spike"), then the grammar work. | Fork patch 0009 can go. |
| R8 | Lists of maps in the normal `- key: value` form, and nested lists, are allowed. | "Allow them." | Supersedes the "lists of maps rejected" rule of `DOOR-075`. |
| R9 | Tabs are allowed for indentation. | "Tabs for indentation need to be allowed." | The file is no longer strict YAML. |
| R10 | A compact item may continue with one tab; `key: - x` is rejected. | "Yes, agreed for both." | Parser v3. |
| R11 | Languages use standard devenv language management. uv is the Python default. | "We should utilize standard devenv language management when possible, with UV the standard/default for Python." | The template lists `nixpkgs-python` and `rust-overlay`; fork patch 0007 is not needed. |
| R12 | Native devenv files stay as an escape hatch for advanced settings. | Asked how to enable "a devenv.nix or devenv.local.nix escape hatch for any advanced or not-provided configuration". | Refines R6: YAML is primary; Nix files are optional and visible. |

R6 and R12 together: routine use needs only `vendomat.yaml`. Native files remain for settings the
catalog does not cover.

## Recommendations awaiting a ruling

| # | Recommendation | Basis |
| --- | --- | --- |
| A1 | A Basix workspace names only `basix`; `vendomat` and `nixpkgs` follow through it. | Removes the compatibility matrix. Unproved. |
| A2 | Basix owns `install` and the disk guard; Vendomat owns `apply`. | `install` has one consumer, the Basix ISO. |
| A3 | Add a devenv patch that types `machines.NAME.nixos` as `deferredModule`, and offer it upstream. | [NIXOS-MERGE](evidence/NIXOS-MERGE.md) |
| A4 | Local `vendomat apply` runs the two activation commands of devenv's deploy worker. The deployer with its watchdog comes later. | [MACHINES-RESEARCH](evidence/MACHINES-RESEARCH.md) |
| A5 | Drop fork patches 0005 and 0006. Remote install becomes the native door. | They guard only the remote path. |
| A6 | Expose ISO and VM builds through `machines.NAME._nixosEval`. | `machines.nix:684`. Unproved. |
| A7 | The Basix ISO carries the core closure for an offline install. | Inference. |
| A8 | Show hatch use on shell entry and in `vendomat explain`; name `vendomat.yaml` in conflict errors through `_file`. | Concept, escape hatch section. |
| A9 | The catalog enables `uv.sync` only when `pyproject.toml` exists. | devenv warns on every shell entry otherwise (`python/default.nix:253-255`). |

## Ideas recorded, not pursued now

Catalog keys as an allow list of native option paths with one generic type converter; a JSON
Schema for editor completion; a commit per `apply`; machines that pull their own branch; one estate
repository whose machine keys define cache trust; capability directories with a module, a lesson,
and a check; an assistant that edits only the intent file.

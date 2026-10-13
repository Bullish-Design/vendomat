# Project 22 decisions

**Date:** 2026-10-13. The owner asked for a canonical way to use the personal tool family and said
the goal is "the best, cleanest, most elegant concept and architecture possible". The rulings below
come from that session. They change concept only. No production code, consumer, or machine
changed.

## Owner rulings

| # | Ruling | Owner words (2026-10-13) | Effect |
| --- | --- | --- | --- |
| R1 | The personal tools form one personal development layer. No repository bundles them or pins their version. Each repository still configures them and customizes its scripts. | "these libraries will serve as a personal development layer that can be configured for personal development, but won't get bundled into/tied to a version in the repo I'm working on. I'll still want to be able to configure their interaction capabilities and customize scripts/etc from the individual project repos where they're used though." | The goal of this project. Rules 1, 5, and 7 of the concept. |
| R2 | nix-meta is the entry point of the owner's Nix configurations, which are modular and composable. | "my nix configuration is modular and composable. Nix-meta is the entrypoint for my family of configs, I just choose the specific machine flake to rebuild-switch to." | nix-meta stays the owner's entry point. A2 proposes what it holds. |
| R3 | The personal layer lives in Home Manager, so a change needs no system rebuild. | "I'd want this to be in home manager so we dont need a full system rebuild on each change." | The home layer. A1 states the consequence for Home Manager as a NixOS module. |
| R4 | nix-systems is work in progress. It will hold each machine's system-level configuration and later join nix-meta. | "Ignore nix systems, its in-process work. It will define my individual machines systems level config (hardware, etc) and eventually be integrated with nix-meta." | The machine layer is nix-systems. |
| R5 | nix-meta's current structure is not fixed. | "we're not stuck with our current nix-meta config. It has grown and evolved over time, but never really been planned out. If there's a better way to structure things, please let me know." | The restructure in the concept. |
| R6 | Align with the Vendomat and Basix concept of project 21 in the near term. | "the latest Vendomat+Basix concept ... which we'll want to align with in the near term future" | The concept section "Relation to project 21". |
| R7 | The four-layer design, with the machine and the home switched separately, is the direction. | "That approach sounds much better." (after a comparison of ten update scenarios, today against the proposal) | This concept. The specific choices below stay recommendations until ruled. |
| R8 | The home is standalone Home Manager. No machine runs Home Manager as a NixOS module. | "A1 and A2 are confirmed." | Rules A1. nix-systems drops `nixos/home.nix`. `ESTATE-003`. |
| R9 | nix-meta holds the homes. nix-systems holds the machines. | "A1 and A2 are confirmed." | Rules A2. nix-meta's `nixosConfigurations` ends as nix-systems takes over each machine. `ESTATE-004`. |

## Recommendations awaiting a ruling

| # | Recommendation | Basis |
| --- | --- | --- |
| A1 | **Ruled (R8).** The home is standalone Home Manager. No machine runs Home Manager as a NixOS module. nix-systems drops `nixos/home.nix`. | R3. One user can have only one Home Manager ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)). Rule 2 of the concept removes the risk that a shared rollback guards against. Reverses a deliberate nix-systems choice. |
| A2 | **Ruled (R9).** nix-meta holds the homes. nix-systems holds the machines. nix-meta's `nixosConfigurations` ends when nix-systems takes over each machine. | R2, R4, project 21 ruling R4 ("Plain NixOS flakes are not the machine path"). One repository per activation unit. Keeps R2: nix-meta stays the owner's entry point for everything personal. |
| A3 | The clone test classifies every tool. Testee splits: the check commands go into the repository's `base:*` tasks, and the runner and its manifest are personal. repoman, devman, linkman, gitman, and copyroom are personal. mancore is a project dependency. | [TOOL-CLASSES](evidence/TOOL-CLASSES.md). |
| A4 | The home installs the eval-time devenv modules under one directory, `~/.local/share/devlayer/`, linked as one directory symlink. The fleet doctor checks for a stale module in each evaluation cache. | [W1](evidence/W1-DEVLAYER-PATH.md): a per-file link stays stale; a directory link is picked up. Path name proposed. |
| A5 | Personal inputs come from the collection by tag. No `git+file://`, `path:`, or branch ref. Development uses `--override-input`. | Project 21 collection rule. Today nix-meta has 7 `git+file://` inputs, 1 `path:` input, and 7 floating refs. |
| A6 | The fleet doctor is a devman doctor mode, `devman doctor --fleet`. | devman doctor is already the one check of the whole plane. |
| A7 | Offer three proposals to project 21: the clone test answers its A1; a standalone home is a native target or outside Vendomat; host-side modules use the devlayer directory. | Concept section "Relation to project 21". |
| A8 | nix-meta is a plain flake, or a light flake-parts flake. Not the dendritic pattern, not snowfall-lib. | [NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md). |
| A9 | repoman's remaining work (roster wiring and one generated skill) becomes part of the overlay and devman. repoman stops being a separate tool. | Its module adds two variables, one script, two packages, and one task; nothing in any project's build or test depends on it ([TOOL-CLASSES](evidence/TOOL-CLASSES.md)). |
| A10 | Remove devman's `agent` group, or port it to agentman's current commands. It targets `agentman run --request` and the `agentman.devman/v1` contract, which agentman deleted on 2026-09-18. | Commit `072aed0` in agentman. |
| A11 | Remove the old Vendomat NixOS module and its `share/vendomat` files from nix-meta. | No file reads them ([HOME-PORT](evidence/HOME-PORT.md)). |

## Ideas recorded, not pursued now

- A Nix registry entry per personal tool. The system and user registries do not resolve flake
  inputs in `flake.nix`, so they cannot replace a pin; they only serve `nix run` and `nix shell`
  ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)).
- `nix profile` for the personal tools. It conflicts with Home Manager on the same user. Testee is
  installed this way today; the home replaces it.
- One monorepo for all personal tools. Each tool keeps its own repository and release; the home
  lock is the one place that selects versions.

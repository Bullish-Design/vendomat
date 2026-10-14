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
| R10 | The clone test classifies every tool. Testee becomes fully personal: it runs a fixed set of standard devenv tasks that each repository defines. Templates write the tasks as placeholders. A placeholder prints how to configure it and exits 78; Testee reports that as "not set up". A repository may mark a task "not applicable" with an explicit exit 0 and a reason. `base:check` and `base:test` chain to the standard tasks. | "A3: Agreed, lets move to this approach." "How about testee just pre-populates with a few different test and check tasks (test:full, test:quick, check:lint, check:format, etc) that are template generated as placeholders that just print an instructional "how to configure this" message, and its up to the user to wire them up how they want? No programmatic requirements, just make it clear to the user if its set up or not. Simple and flexible is the goal." "Agreed on the A3 refinements." | Rules A3, refined. Supersedes the overlay Testee manifest (`ESTATE-023`). Concept section "Per-project configuration". |
| R11 | The home links the devenv modules as one directory (option 3 of four). Amended by R12. The reason it works must be found and recorded before the design relies on it. | "A4: Agreed on option 3, though we should investigate how/why it actually works rather than just assume we'll be good to continue using it." | Rules A4. W9 is a gate on migration phase 5. The directory name `devlayer` stays proposed. |
| R12 | Amends R11. The home builds the layer as one store directory, and Home Manager activation writes one real pointer file outside the store that names the layer's store path. Overlay `devenv.local.nix` files import the pointer. | "Yes, agreed on the R11 change." (after W9 found the directory link incidental and the planned `linkFarm` layout stale) | Supersedes the directory-link form of R11. W10 proves it before phase 5. [W9](evidence/W9-EVAL-CACHE.md). |
| R13 | The patched devenv binary and the `vendomat` launcher belong to the machine layer. They are the platform, not personal tools. | "Yes, please make those updates" (after the summary of project 21's final rulings, 2026-10-13) | Follows project 21 R22 and R31. Corrects the concept, which listed devenv under the home. |
| R14 | The pointer file is `~/.local/state/devlayer/current.nix` by default, and its path is a configurable option. | "Pointer name and location approved. Lets make this an configurable option though in case we change our mind." (2026-10-13) | `ESTATE-037`. The mechanism that keeps the overlay imports in step with the option is open item OI-02; W10 measures the candidates. |
| R15 | Retire RepoMan (OI-05 option c). The central overlay stops importing its host module, and no repository keeps RepoMan settings. | "Excellent, go with option 1." (2026-10-13; option 1 was: land the overlay commits, then remove the 19 RepoMan host-module imports, retiring RepoMan as A9 recommends) | Rules A9 in part. Overlay commit `da3a4f58`; mnemonix commit `9af72666`. The RepoMan repository, its generated skill, and the template-nix seed of `.repoman/project.toml` remain. |

## Recommendations awaiting a ruling

| # | Recommendation | Basis |
| --- | --- | --- |
| A1 | **Ruled (R8).** The home is standalone Home Manager. No machine runs Home Manager as a NixOS module. nix-systems drops `nixos/home.nix`. | R3. One user can have only one Home Manager ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)). Rule 2 of the concept removes the risk that a shared rollback guards against. Reverses a deliberate nix-systems choice. |
| A2 | **Ruled (R9).** nix-meta holds the homes. nix-systems holds the machines. nix-meta's `nixosConfigurations` ends when nix-systems takes over each machine. | R2, R4, project 21 ruling R4 ("Plain NixOS flakes are not the machine path"). One repository per activation unit. Keeps R2: nix-meta stays the owner's entry point for everything personal. |
| A3 | **Ruled (R10), refined.** The clone test classifies every tool. Testee splits: the check commands go into the repository's `base:*` tasks, and the runner and its manifest are personal. repoman, devman, linkman, gitman, and copyroom are personal. mancore is a project dependency. | [TOOL-CLASSES](evidence/TOOL-CLASSES.md). |
| A4 | **Ruled (R11, amended by R12).** The home installs the eval-time devenv modules under one directory, `~/.local/share/devlayer/`, linked as one directory symlink. The fleet doctor checks for a stale module in each evaluation cache. | [W1](evidence/W1-DEVLAYER-PATH.md): a per-file link stays stale; a directory link is picked up. Path name proposed. |
| A5 | Personal inputs come from the collection by tag. No `git+file://`, `path:`, or branch ref. Development uses `--override-input`. | Project 21 collection rule. Today nix-meta has 7 `git+file://` inputs, 1 `path:` input, and 7 floating refs. |
| A6 | The fleet doctor is a devman doctor mode, `devman doctor --fleet`. | devman doctor is already the one check of the whole plane. |
| A7 | **Answered by project 21 R33, R35, and R36 (2026-10-13).** Offer three proposals to project 21: the clone test answers its A1; a standalone home is a native target or outside Vendomat; host-side modules use the devlayer directory. | Concept section "Relation to project 21". |
| A8 | Project 21 R35 rules out a Vendomat workspace for homes. nix-meta is a plain flake, or a light flake-parts flake. Not the dendritic pattern, not snowfall-lib. | [NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md). |
| A9 | **Ruled in part (R15).** repoman's remaining work (roster wiring and one generated skill) becomes part of the overlay and devman. repoman stops being a separate tool. | Its module adds two variables, one script, two packages, and one task; nothing in any project's build or test depends on it ([TOOL-CLASSES](evidence/TOOL-CLASSES.md)). |
| A10 | Remove devman's `agent` group, or port it to agentman's current commands. It targets `agentman run --request` and the `agentman.devman/v1` contract, which agentman deleted on 2026-09-18. | Commit `072aed0` in agentman. |
| A11 | Confirmed in direction by project 21 R36 (`VMT-123`). Remove the old Vendomat NixOS module and its `share/vendomat` files from nix-meta. | No file reads them ([HOME-PORT](evidence/HOME-PORT.md)). |

## Ideas recorded, not pursued now

- A Nix registry entry per personal tool. The system and user registries do not resolve flake
  inputs in `flake.nix`, so they cannot replace a pin; they only serve `nix run` and `nix shell`
  ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)).
- `nix profile` for the personal tools. It conflicts with Home Manager on the same user. Testee is
  installed this way today; the home replaces it.
- A curated `release` branch per personal tool, fast-forward only, as Vendomat uses for itself
  (project 21, carried from project 20). `nix flake update` would then take each tool's newest
  release. Recorded as the alternative to A5's tags; tags name the version, so A5 keeps them.
- A third devenv binary patch that tracks a symlinked import by its path as written (W9). The
  pointer file makes it unnecessary; it needs a project 21 ruling (`VMT-105`).
- One monorepo for all personal tools. Each tool keeps its own repository and release; the home
  lock is the one place that selects versions.

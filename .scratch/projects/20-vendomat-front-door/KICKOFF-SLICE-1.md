# Kickoff prompt: project 20, slice 1 (the Vendomat workspace)

**Date:** 2026-10-12. Paste everything below the line into a fresh session that starts in
`/home/andrew/Documents/Projects/vendomat`.

---

Work in /home/andrew/Documents/Projects/vendomat. This session implements slice 1 of project 20:
the Vendomat workspace. The owner accepted the design on 2026-10-12 (`DECISIONS.md`, R1 to R4).
Do not reopen the design. If a fixture disproves part of it, stop that part, update the concept,
the requirements, and the plan together, and report it.

## Your role

You are the orchestrator. Do the high-level planning, the orchestration, the analysis, the
review of results, and the landing. Delegate **all** investigation, exploration, implementation,
testing, and documentation edits to parallel **background Sonnet subagents** (Agent tool,
`model: "sonnet"`, `run_in_background: true`). Do not write production code yourself. Read only
what you need to plan, brief, and review.

Give each subagent a complete brief: the goal, the exact paths, the rules below, the requirement
IDs it serves, the record format, what it must not touch, and the length and shape of its final
reply. Launch independent lanes in one message. Review each result before you act on it. A
subagent report is a claim; check its key evidence (a diff, a log line, a Testee verdict) before
you land.

## Read first, in order

1. `AGENTS.md`, then `.scratch/CURRENT.md`.
2. `.scratch/projects/20-vendomat-front-door/`: `CONCEPT.md` (five minutes), `PLAN.md`,
   `DECISIONS.md` (from "Second simplification pass" onward), and `REQUIREMENTS.md` (from
   "Second simplification pass" onward). The active IDs are `DOOR-036`, `DOOR-038`, `DOOR-063`,
   and `DOOR-071` to `DOOR-075`. Slice 1 serves `DOOR-071`, `DOOR-074`, and `DOOR-075`.
3. `evidence/SIMPLIFY-REVIEW-2026-10-12-PASS2.md`, then the spike records it cites, as needed:
   P2A (direct read, eval cache), P2B (parse once, all faults in one error), P2C (update by a
   `release` branch), P2F (why a hand-off fails under Testee), and P2G (the fork primop).
4. Repository fixtures: `evidence/fixtures/p2g/` (prototype catalog module and workspace, 27
   strict-subset case files, patch 0009), `evidence/fixtures/p2b/` (parse-once catalog and cases).
   Raw logs and larger fixtures: `~/.local/state/vendomat/p20/2026-10-12/` (the P2G build output
   is `G-fork-yaml/result-devenv`, the patched fork `devenv 2.4.0+febee12`).

Use `rg --hidden`, because rg skips `.scratch` otherwise.

## Ask the owner first, as one group

Ask these before the lanes that need them start. Start the other lanes at once.

1. **Release branch host.** The template's Vendomat input follows a `release` branch. Which URL?
   The P2C spike needs a URL form that locks a `rev` (`git://`, `git+ssh://`, or `github:`; not
   `git+file`). The project 14 collection serves `git://server/<repo>`. GitHub is only a
   secondary copy of local repositories, never part of the Vendomat pipeline. Recommend
   `git://server/vendomat?ref=release` for slice 1, and leave the public Basix URL to slice 2.
2. **Publishing.** Slice 1 needs a new fork tag (`v2.4.0-vendomat.4` with patch 0009) in the
   collection and a `release` branch on the Vendomat repository. Both are release actions. Ask
   for authorization to publish them after the gates pass.
3. **First catalog entries.** Recommend: `programs` (nixpkgs attribute names); `languages` with
   `python`, `javascript`, and `rust` (enable and version); `services` with `postgres` and
   `redis` (enable); and `env` (text values). Project 17 proved these subtrees in `devenv-py`.

## Lanes

Each lane is one Gitman workspace and one or more background subagents. Respect the order on
the critical path. Lanes without a dependency start at once.

| Lane | Work | Depends on |
| --- | --- | --- |
| A. Fork patch | Add patch 0009 to `devenv-dist/patches` and `SERIES`. Turn the 27 case files into Rust unit tests for `yaml_subset.rs`. Run `devenv-dist/materialize` and its `--verify`; update `RESULT` and `MANIFEST.sha256`. Build the fork. Do not tag or publish until the owner authorizes it. | none |
| B. Catalog module | Write the production catalog module at the import path the template uses (P2C used `vendomat/devenv`; confirm against the flake). Named, typed entries from owner question 3. Parse once with the primop on `builtins.readFile`; a missing file is an empty catalog; one error lists every bad field and every unknown program as `vendomat.yaml: <field> ...`; every mapping reads only the parsed values; an unknown key fails. Start from `evidence/fixtures/p2g/workspace/catalog.nix`. Develop against the P2G binary until lane A's build exists. | A for the final gate |
| C. Template | Rewrite `templates/workspace/`: `vendomat.yaml` (an empty or example catalog), `devenv.yaml` (the Vendomat flake input on `release`, `nixpkgs.follows: vendomat/nixpkgs`, the catalog import), `devenv.nix` as `{ }`, and `.gitignore` for `.devenv*`. | B; owner question 1 |
| D. Host command | Change the host `vendomat`: no argument enters the pinned fork's shell; `new` copies the template; every unknown argument runs the pinned fork with `exec`, keeping exit status, signals, and the terminal. Keep `sync`, `push`, and the other old verbs until the release (`DOOR-063`). Study `src/vendomat/cli.py`, `launcher/vendomat`, `nix/devenv-module/`, and `flake.nix` first. The host release must carry the patched fork. | A for the fork pin |
| E. Testee and PATH | Make Testee evaluate with the patched fork, not the stock `devenv` that comes first on the inherited PATH (P2G found this; see the memory note on Testee PATH shadowing). Find the narrowest fix: Testee configuration, the `devenv.nix` Testee settings, or the host profile. | A |
| F. Gates | Write the checks for `DOOR-071`, `DOOR-074`, and `DOOR-075` as Testee checks (`testee.checks` in `devenv.nix`; add a named opt-in check, as `e2e` is). The matrix: a fresh workspace from `vendomat new` enters the shell; edits, a create, and a delete of `vendomat.yaml` show in the next shell; a fresh clone enters the shell; an unknown key, a bad used value, a bad unused value, and an unknown program stop `shell`, `test`, `build`, and `tasks run` before work; one run lists every bad field; a syntax fault gives `vendomat.yaml:LINE:COL`; `3.10` and `name: no` stay text, and `enable: no` fails; `vendomat update` moves a `release` branch and a restored lock restores the old shell; pass-through keeps the exit status; Testee goes RED on a bad file and GREEN again. Also test a `build` of an attribute that reads no mapped value (P2B left it open). | B, C, D, E |
| G. Records | Write `evidence/slice-1/` gate records (one file per gate) and update `CURRENT.md`, `PLAN.md`, and the requirement statuses as gates pass. Update `tests/test_repo_shape.py` if the new paths need it. | each gate |

Critical path: **A → B → C → F**, with D and E in parallel after A.

## Rules for every subagent

- Each lane works in its own Gitman workspace:
  `gitman work NAME --path /home/andrew/Documents/Projects/gitman-workspaces/NAME`. List the
  existing workspaces first (`jj workspace list`) and report any work that `main` lacks. Use
  native jj for status, describe, and diff. Never run raw `git` in a real repository; throwaway
  fixtures may use git.
- Subagents do not move `main`, push, forget, or delete a workspace. They report the change id,
  the commit id, and the Testee verdicts. You land.
- Verify with `~/.nix-profile/bin/testee verify`, `testee verify --profile full`, and
  `testee verify e2e` for module, toolchain, or consumer changes. Do not call pytest, ruff, or ty.
  Do not wrap testee in `devenv shell`. During edits, use `testee verify --profile quick`.
- The pinned fork today is `2.4.0+fb5d382` at
  `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`. The `devenv` on
  PATH is stock. Print `devenv version` at the top of every devenv log.
- Never run `devenv gc`, `nix-collect-garbage`, or `nix store gc`. Before a heavy build, run
  `btrfs filesystem usage /`; stop below 2 GiB unallocated or above 90 % metadata. Run one VM or
  fork build at a time.
- Subagents inherit `UV_PROJECT_ENVIRONMENT`. In another repository, run uv only as
  `devenv shell -- uv ...` or with `env -u UV_PROJECT_ENVIRONMENT`.
- Shell aliases: `ls` is eza and `cat` is bat; use `command ls` and `command cat` in scripts.
- `sudo` is `/run/wrappers/bin/sudo`, and the agent has no sudo password. No machine
  activation, no real disk write.
- Keep raw logs under `~/.local/state/vendomat/p20/<date>/slice-1/`. Record each observation:
  inputs, versions, command, expected result, actual result, log path, what it proves, what
  stays inference.
- Requirement IDs: never reuse or renumber one. Supersede instead of editing a claim. Mint a new
  ID only when the owner accepts a design or a fixture proves an interface.
- Write in Simplified Technical English (`.claude/skills/writing/SKILL.md`): short sentences,
  active voice, one word for one meaning.

## Landing

For each lane, after the subagent reports: check the diff summary and the Testee status of the
exact revision (`testee status -r REV`). Move `main` and push as two separate commands. Run
`jj new main` in the main checkout when its working copy is empty. Forget the workspace and
remove its directory. Ask the owner before you land anything that touches CI configuration,
secrets, or a release branch, or that publishes a tag.

## Done when

- Patch 0009 is in the fork series with passing unit tests, and the fork builds.
- The catalog module, the template, and the host command are on `main`.
- The `DOOR-071`, `DOOR-074`, and `DOOR-075` gates pass on the patched fork as Testee checks,
  with records in `evidence/slice-1/`.
- The requirement statuses, `PLAN.md`, and `CURRENT.md` say what passed and what did not.
- No workspace holds unlanded work, or the owner knows which one does and why.
- A short handoff names the next step: publish the fork tag and the `release` branch (with the
  owner's authorization), then slice 2.

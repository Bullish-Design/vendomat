# Kickoff prompt: simplify the project 20 concept and plan

**Date:** 2026-10-12. Paste everything below the line into a fresh session that starts in
`/home/andrew/Documents/Projects/vendomat`.

---

Work in /home/andrew/Documents/Projects/vendomat.

This session is a design review of project 20 (Vendomat as the front door to Basix and devenv). Find
where the concept and the plan are over-engineered or over-specified. Then propose and record a simpler
design. Do not implement the runtime, change production code, migrate consumers, deploy machines, or
write real disks.

## The goal

**A simple mental model beats every other property.** The owner accepts lost functionality and lost
capability to get it. Optimize the 90 % path so it is as smooth and as simple as possible. Push the other
10 % to native Nix, to a later release, or out of scope.

Vendomat is our own interaction layer over Nix, devenv, NixOS, and Home Manager. Because we own the layer,
we may constrain the workflows it supports. A constraint that removes a concept, a file, a command, a
mode, an option, or a failure state is a gain. Prefer "this cannot happen" over "we detect it when it
happens".

Basix users learn general computing, not Nix. Nix is the hidden engine with an opt-in door. Design the
surface around programs, services, files, settings, versions, and machines.

## Review principle: parse, don't validate

Apply Alexis King's "parse, don't validate" throughout:

- Turn untrusted input into a precise type once, at the boundary. After that, no code re-checks it.
- Make illegal states unrepresentable. If two fields cannot both be set, use two types, not a check.
- A guard, a digest, a staleness check, a refusal, or a cross-field assertion is a smell. Each one says
  that a derived state can drift or that a wide type admits a bad value. First ask whether the derived
  state or the wide type can go away. Keep a check only when no simpler shape removes its cause.
- Prefer one source of truth that the engine reads directly over a generated copy plus a guard.
- Count concepts, not lines. A design with fewer things the user must hold in mind wins, even if the
  code is larger.

## Read first, in order

1. `AGENTS.md`, then `.scratch/CURRENT.md`.
2. `.scratch/projects/20-vendomat-front-door/`: `CONCEPT.md`, `DECISIONS.md`, `REQUIREMENTS.md`,
   `PLAN.md`.
3. `.scratch/projects/20-vendomat-front-door/evidence/RESEARCH-2026-10-11.md` (decision matrix, gate
   matrix, journeys, migration inventory, handoff).
4. The spike records in the same `evidence/` directory, as needed: S1 (YAML grammar), S2 (merge
   priority), S3 (schema export), S4 (machine inventory), S5 (front door, guard, launcher), S6 (Harmonia
   two-VM), S7 (keyless install and secrets), S9 (native follows). R3 is the migration inventory. R4 is
   the user journeys. The requirement disposition map is `REQUIREMENT-DISPOSITION-2026-10-11.md`.
5. Background only: projects 16 to 19 under `.scratch/projects/`. They are evidence, not direction.

Treat every spike result as evidence about the tools. Do not treat a spike's design as settled because
it passed. A passing spike proves a mechanism works; it does not prove the mechanism is needed.

## Define the 90 % first

Before you judge any feature, write down the few journeys that make up the 90 %. Start from these and
correct them from the evidence:

1. A learner installs Basix on one machine, boots it, and adds programs, services, and settings.
2. A developer creates a workspace, adds a language and tools, enters the shell, and runs tests.
3. A user updates: moves a pinned release forward, and rolls back if it breaks.
4. A user adds a second machine and shares built outputs.

Name what each journey needs and nothing more. Everything else is a candidate for the 10 %. Examples of
likely 10 % items: adoption of a foreign NixOS configuration, source mirrors and keep clones, offline
first use with unfetched sources, multiple imported libraries that disagree on a shared input, custom
disk layouts, and direct `devenv` use without Vendomat.

## Questions to answer

Answer each with evidence, not taste. For each, say what the simplest shape is, what it removes, and what
capability is lost.

1. **The user file and the generated state.** The present design parses `vendomat.yaml`, writes a
   committed `.vendomat/` copy, guards it with a digest, adds `prepare`, `prepare --check`, and an
   escape variable. Can the engine read the user's source of truth directly, so no derived copy exists?
   Consider: a format Nix reads natively (`builtins.fromJSON`, `builtins.fromTOML`); keeping inputs and
   imports in native `devenv.yaml`; or whether a separate Vendomat file is needed at all. State the
   trade against the owner's earlier choice of YAML. The owner said functionality may be sacrificed.
2. **Validation.** The design exports an option schema, caches it under a key, validates in Python, and
   has exit codes for schema faults and a missing schema. Could Nix's own types be the only validator,
   with every set value forced eagerly and errors located at the user file (S2 showed `_file` works)?
   What does the user lose in error quality, and is it worth the removed machinery?
3. **The YAML grammar.** S1 built a 168-case grammar with quoted keys, block scalars, and a secret
   recognizer. Which rules does the 90 % need? Could a much smaller, stricter form serve, and the rest
   go to `devenv.nix`?
4. **Merge rules.** YAML values are plain definitions, and a conflict with a library's plain definition
   is an error (S2). Is there a constraint that makes conflicts rare or impossible for the 90 % (for
   example, libraries may only use `mkDefault`, or user data may only set options that no library sets)?
5. **The command surface and the launcher.** The plan has ten named commands, a pass-through, nine exit
   codes, a launcher protocol, a transition launcher that reads two markers, and a pinned-devenv lookup.
   What is the smallest surface? Could `vendomat` be a single verb plus pass-through, or could the shell
   carry everything so the host needs only a bootstrap?
6. **Machines.** The inventory has two modes, many fields, guards, an admin key and an installer key, a
   host-key re-pin, and a secret receiver. What does one-machine Basix need on day one? Can fresh install
   and adoption be one flow, or can adoption be dropped from the first release? Can types make a bad
   inventory unrepresentable instead of asserted?
7. **Secrets and the cache.** Could the cache host simply not exist until the user turns it on after the
   key is delivered, instead of a path-unit activation dance? Does the first release need the secret
   route at all?
8. **Source, store, collection.** Release tags, collection mirrors, keep clones, release GC roots, and a
   collection builder. Which of these does the 90 % need in the first release?
9. **Requirement and process weight.** Project 20 carries 56 DOOR IDs plus 195 V5 and 122 V6 IDs with
   dispositions. Propose a lighter structure if it helps. `AGENTS.md` forbids reusing or renumbering an
   ID, so supersede; never edit a claim in place. A proposal to close the V5 and V6 ledgers as history
   needs the owner's ruling; ask for it, do not assume it.
10. **The ten owner decisions (O1 to O10).** For each, say whether a simplification makes the question
    disappear.

## How to work

- Use parallel background Sonnet subagents for all exploration, evidence reading, and spikes. Do the
  high-level planning, orchestration, and analysis yourself. Give each subagent a complete brief: paths,
  rules, the record format, and the final reply length.
- A spike is welcome when it settles whether a simpler shape works on the pinned tools. Keep spikes
  small and isolated. Do not modify `src/vendomat`, `nix/`, `launcher/`, or `templates/`. Keep raw logs
  under `~/.local/state/vendomat/p20/<date>/`. Record each spike: question, competing hypotheses, exact
  inputs and versions, command, expected result, actual result, log path, what it proves, what stays
  inference, what stays unproved.
- Run one VM build at a time. Check `btrfs filesystem usage /` first; stop when unallocated space is
  under 2 GiB or metadata use is over 90 %.
- Challenge the concept when evidence disagrees. Do not keep a mechanism because a document or a spike
  already describes it.
- Ask the owner only for a decision that evidence cannot settle and that blocks useful work. Group such
  questions; do not ask one at a time.

## Deliverables

1. A dated review record, `evidence/SIMPLIFY-REVIEW-<date>.md`:
   - the 90 % journeys you defined;
   - a table of every mechanism in the current concept and plan, with the reason it exists, the
     simplest alternative, what the alternative removes, what capability is lost, the evidence, and a
     verdict: keep, simplify, cut, or defer;
   - the new mental model in five sentences or fewer;
   - a before-and-after count of user-facing concepts, files, commands, and modes.
2. A revised `CONCEPT.md`, short enough to read in five minutes. Move detail to a spec or to evidence.
3. Updated `REQUIREMENTS.md`: supersede or withdraw IDs that the simplification removes; add few new IDs.
   Never reuse or renumber an ID.
4. Updated `DECISIONS.md`: record each simplification and which earlier decisions or O-questions it
   closes.
5. A revised `PLAN.md` with fewer slices, the critical path, and the first slice.
6. A handoff: what changed, what was cut, which owner rulings are still needed, and what the next
   session does first.

## Facts that bite

- Pinned devenv is the fork `2.4.0+fb5d382` (tag `v2.4.0-vendomat.3`) at
  `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`. The `devenv` on `PATH`
  is stock `2.4.0+b904dcb`. Print `devenv version` in every spike log.
- Never run `devenv gc`, `nix-collect-garbage`, or `nix store gc`.
- Verify with Testee: `testee verify` and `testee verify --profile full` (there is no `--full` flag).
  Use `~/.nix-profile/bin/testee` (0.6.1). Do not call pytest, ruff, or ty.
- `devenv shell -- cleanup` lists Testee venvs, stale slots, and caches; `--yes` deletes them.
- Subagents inherit `UV_PROJECT_ENVIRONMENT`. In another repository, run uv only as
  `devenv shell -- uv ...` or with `env -u UV_PROJECT_ENVIRONMENT`.
- `rg` skips `.scratch` unless you pass `--hidden`.
- `sudo` is `/run/wrappers/bin/sudo`; the agent has no sudo password.
- `server` and `framework` are the owner's machines. Use them as fixtures only, never as defaults.

## Version control

Use Gitman to open the workspace (`gitman work NAME --path
/home/andrew/Documents/Projects/gitman-workspaces/NAME`). List existing workspaces first and report any
work that `main` lacks. Native jj is authorized for status, commit, rebase, and push. Do not use raw
`git`. Run `testee verify` and `testee verify --profile full` before landing. Land on `main`, push, run
`jj new main` in the main checkout when its working copy is empty, and remove the workspace. Write in
Simplified Technical English (see `.claude/skills/writing/SKILL.md`).

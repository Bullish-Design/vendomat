# Current project

**Updated:** 2026-10-08. This file names the active project. `AGENTS.md` holds durable rules and
points here. When the active project changes, change this file and not `AGENTS.md`.

## Active: project 14 — Vendomat V5

Authority, in reading order, all in `.scratch/projects/14-vendomat-local/`:

1. `CONCEPT-V5.md` — the shape and the worked examples.
2. `SPEC-V5.md` — normative. 153 requirement IDs in its tables, 126 active; 19 withdrawn resolver and emitter IDs are preserved.
3. `GUIDE-V5.md` — the commands. Steps 0 to 10.
4. `REFINEMENT-2026-10-08.md` — named paths and drive identity.

`KICKOFF-V5.md` in the same directory is the prompt for starting an implementation session.

### State

Updated 2026-10-08 after the V5 preliminary verification. No V5 implementation step has run.
Step 0 is blocked: PV-02 could not read the 4 TB target's partition table or signatures. PV-09 also
blocked installer cache access. Do not start implementation or disk work until the relevant P0
blockers are resolved. See [preliminary results](projects/14-vendomat-local/prelim-verification/RESULTS.md).

The Nix-only core booted in a disposable PV-11 VM without the Vendomat CLI. That fixture did not
prove production boot or tailnet reachability. The CLI belongs in a later host delta. The generator
and consumer contract remain proposed until the tracked fixtures pass.

## Superseded

`.scratch/projects/09-*` through `13-*` and the `docs/V4_*.md` records are closed history. They
hold observations that the active documents cite by name. Do not read them for direction, and do
not follow any programme, gate, or requirement ID defined in them. Each closed directory carries
its own terminal note.

## Inherited facts that still hold

- The code at version 0.4.4 serves the current surface: the wheel build, the dependency knowledge
  commands, and the toolchain in `src/vendomat/`, `vendor/`, `lib/`, and `modules/devenv.nix`.
  V5 treats it as **provenance, not a base.** The git history stays.
- Eleven central overlays, ten local-checkout overlays, and one flake-input consumer use the
  current paths. Every machine is reconfigured, so those paths are replaced. `BOOT-010` carries the
  one obligation: a converted input must produce the same result as the tree it replaces, or name
  the difference.
- `tests/fixtures/store-consumer/` is a real consumer fixture for the current pin.
- V5 logs go in `~/.local/state/vendomat/v5/<date>/`. Older logs sit beside it.

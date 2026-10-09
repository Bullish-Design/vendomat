# Current project

**Updated:** 2026-10-08. This file names the active project. `AGENTS.md` holds durable rules and
points here. When the active project changes, change this file and not `AGENTS.md`.

## Active: project 14 — Vendomat V5

Authority, in reading order, all in `.scratch/projects/14-vendomat-local/`:

1. `CONCEPT-V5.md` — the shape and the worked examples.
2. `SPEC-V5.md` — normative. 185 requirement IDs in its tables, 142 active, 32 superseded, 10 withdrawn, 1 narrowed; 19 withdrawn resolver and emitter IDs are preserved.
3. `GUIDE-V5.md` — the commands. Steps 0 to 10.
4. `REFINEMENT-2026-10-08.md` — named paths and drive identity.

`KICKOFF-V5.md` in the same directory is the prompt for starting an implementation session.

### State

Updated 2026-10-08, second session. The V5 machine steps have not run. Step 8, the registry and
generator, ran in isolation under the owner's authorization, and its fixtures pass: the project-output
interface on pinned Nix ([PV-13](projects/14-vendomat-local/prelim-verification/results/PV-13.md)) and
the real `vendomat sync` output ([PV-14](projects/14-vendomat-local/prelim-verification/results/PV-14.md)).
This is not fleet acceptance.

Owner decisions of 2026-10-08: Vendomat is a system-installed command, added by a host delta at
`packages.<system>.vendomat`. It generates no development shell and no `devenv` input. A generated
`flake.nix` bridges to a project-owned `flake-outputs.nix`. The laptop is `framework`. Nix owns
`flake.lock`. Vendomat tracks two things: build outputs, which Attic holds, and source, which one
collection on `server` holds. Nix reads personal inputs from that collection over `git://`, CI pushes
release tags to it, and every input pins a tag. Attic never needs to hold source. The library is
being rewritten from scratch around the V5 concept; old code is provenance. See
[DECISIONS.md](projects/14-vendomat-local/prelim-verification/DECISIONS.md). PV-05 stays as history.

Still blocked, each by evidence:

- **Step 0 and Step 7 (PV-02):** the 4 TB target's identity matches, but its partition table and
  signatures cannot be read without privilege. The owner runs the scan.
- **Step 2, 3, and 10 (PV-09):** a cold VM reaches the private route and meets HTTP 401 without a
  credential. The owner chooses how the installer gets the pull credential.
- **Step 8 acceptance:** Step 6.3 is done. The daemon settings were proved on two NixOS test machines
  (PV-18), landed in `nix-meta` (`6cfcba5`, not pushed to origin), and switched on `server`. The
  collection holds `devman` at `v0.7.0`, and the owner reports `git ls-remote git://server/devman`
  works from `framework` (PV-19). A Nix lock and build on `framework`, and key login from `framework`
  to `server` for release pushes, are untested.
- **`DEL-010`:** no fixture yet shows the host-installed CLI reachable from a project shell.

The Nix-only core booted in a disposable PV-11 VM without the Vendomat CLI. That fixture did not
prove production boot or tailnet reachability. See
[results](projects/14-vendomat-local/prelim-verification/RESULTS.md).

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

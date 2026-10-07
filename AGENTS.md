# AGENTS.md — project instructions

## What this project is

Vendomat is the V4 integration layer for composable devenv modules. It helps one owner compose
personal NixOS machines, development projects, and reusable applications from native devenv,
NixOS, and Home Manager configuration. It adds two core capabilities:

- Retained source for the inputs a selection chose.
- A durable record that binds declared checks to exact output bytes, with verified cache
  availability.

Two named operations provide them: `retain` and `publish`.

Vendomat is not a dependency resolver, second lock, daemon, general runtime, action registry,
deployment engine, workspace orchestrator, index, retention engine, or cache protocol. Native
declarations and locks select dependencies. Machines, NixOS, and Home Manager own plans and
activation. RepoMan, `repoman.lock`, and the surrounding `*man` tools keep their own roles.

## Current state

- The V4 contract is defined in project 13. The implementation is not. P1 to P3 have passed ([P1](docs/V4_P1_RECORD.md), [P2](docs/V4_P2_RECORD.md), [P3](docs/V4_P3_RECORD.md) records). P4 to P7 have not.
- There is no P0 and no combined preflight gate. A pin record and per-phase entry conditions
  replace them. P1 and P2 need only a pinned devenv and Nix.
- The code at version 0.4.4 still serves the pre-V4 surface: the wheel build, the dependency
  knowledge commands, and the shared toolchain in `src/vendomat/`, `vendor/`, `lib/`, and
  `modules/devenv.nix`. Treat it as a preserved surface. It does not define V4.
- Eleven central overlays, ten local-checkout overlays, and one flake-input consumer use these
  paths. Do not retire or migrate a path until its replacement passes a before-and-after fixture.
  That migration is a separate project. Start it after P6 passes. It is not a V4 phase or gate.
  No V4 requirement covers it. `V4-OWN-012` is retired from V4 scope.

## Authority

Read these documents in `.scratch/projects/13-vendomat-v4-canonical/` in this order when you start
V4 work:

1. [README.md](.scratch/projects/13-vendomat-v4-canonical/README.md): the index.
2. [CONCEPT-V4.md](.scratch/projects/13-vendomat-v4-canonical/CONCEPT-V4.md): goals and boundary.
3. [V4-SPEC.md](.scratch/projects/13-vendomat-v4-canonical/V4-SPEC.md): the only normative contract.
4. [V4-REQUIREMENTS.md](.scratch/projects/13-vendomat-v4-canonical/V4-REQUIREMENTS.md): stable
   requirement IDs.
5. [NATIVE-BASELINE.md](.scratch/projects/13-vendomat-v4-canonical/NATIVE-BASELINE.md): upstream
   facts the design assumes.

Then read the two supporting notes. Neither defines V4. [LATER-APPLICATION.md](.scratch/projects/13-vendomat-v4-canonical/LATER-APPLICATION.md)
covers a later application outside V4. [FUTURE-WORK.md](.scratch/projects/13-vendomat-v4-canonical/FUTURE-WORK.md)
covers deferred capabilities and their triggers.

Last, read the [V4 implementation guide](docs/V4_IMPLEMENTATION_GUIDE.md) for phase order and gates.

The project-09, project-10, and project-11 documents are history. They do not define V4. Project
10's review and requirement audit remain as provenance. Preserve each requirement ID when you change
a document. Never reuse or renumber an ID.

## Rules for V4 work

- Keep native declarations and locks as the only selection authority.
- Vendomat owns exactly two durable state classes: receipts with their logs, and
  garbage-collection roots.
- Evaluate a publishable selection with no access to undeclared host state.
- Retain the source of every locked native input. There is no capture list. A built package's
  source status is `unresolved`.
- Treat every new option name, command, and file format as proposed. Mark it as implemented
  only after a fixture proves it on the pinned tools.
- Use the native behavior of devenv, Nix, NixOS, Home Manager, and Attic at their own boundaries.
- Run the phases in order. Check each phase entry condition against the pin record. Record the exact
  inputs, versions, commands, expected results, actual results, and preserved logs. Do not advance
  past a failed gate.
- 24 requirement IDs assert upstream tool behavior. They live in `NATIVE-BASELINE.md`. Observe each
  one once on the pin and record it there. None of them is a gate.
- Record a documented upstream fact as evidence about the upstream tool. Never record it as a
  passed gate.
- A unit test does not replace a required real consumer, Attic, restore, or Machines proof.
- If a fixture disproves an interface, update the specification, guide, implementation, and tests
  together.
- Record unavailable infrastructure as a named blocker with evidence. Do not report it as passed.

## Working here

```bash
devenv shell -- testee verify --mode quick
VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick
devenv shell -- nix build .#repoman-toolchain-core --no-link --print-out-paths
```

Run the first command as the normal gate. Run the second command when a change affects the Nix
module, toolchain, or consumer integration. A pull request needs a green Testee verification.
The end-to-end test remains opt-in because it builds a real consumer shell.

Use Gitman for every version-control action. Do not run raw `git` or `jj`.

## Where things live

- `.scratch/projects/13-vendomat-v4-canonical/`: the canonical V4 documents. Seven files:
  `README.md`, `CONCEPT-V4.md`, `V4-SPEC.md`, `V4-REQUIREMENTS.md`, `NATIVE-BASELINE.md`,
  `LATER-APPLICATION.md`, and `FUTURE-WORK.md`.
- `.scratch/projects/09-*` to `12-*`: history and provenance. They are not V4 authority.
- `docs/V4_IMPLEMENTATION_GUIDE.md`: the V4 phase sequence.
- `docs/V4_P0_PROOF.md`: an observed record from 2026-10-06. The pin record supersedes its gate
  framing. Its observations remain valid.
- `tests/fixtures/store-consumer/`: the real consumer fixture for the current pin.
- `tests/fixtures/v4-p0-machines/`: the Machines fixture from the earlier P0 observation.
- `flake.nix`, `lib/`, `modules/`, `src/vendomat/`, `vendor/`: the preserved pre-V4 surface.
- `tests/`: Python checks, Nix checks, and consumer fixtures.
- Raw proof logs stay outside the repository in `~/.local/state/vendomat/v4-proof/`.

Read `README.md` for the current consumer configuration. It describes the preserved surface.

## Shared instructions

Follow your active user and machine instructions for rules that apply across
repositories. Keep this file focused on Vendomat.

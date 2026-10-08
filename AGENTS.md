# AGENTS.md — project instructions

Durable rules only. Project state, authority documents, and current work live in
[`.scratch/CURRENT.md`](.scratch/CURRENT.md). Read that file next.

Do not add project state here. A fact that changes when the active project changes belongs in
`.scratch/CURRENT.md`.

## What this project is

Vendomat composes one owner's NixOS machines, development projects, and reusable applications from
native devenv, NixOS, and Home Manager configuration.

It is not a dependency resolver's replacement, a second lock, a daemon, a general runtime, a
deployment engine, a workspace orchestrator, or a cache protocol. Native declarations and locks
select dependencies. NixOS and Home Manager own activation. Attic owns cached objects.

## Working here

```bash
devenv shell -- testee verify --mode quick
VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick
```

Run the first command as the normal gate. Run the second when a change affects the Nix module,
toolchain, or consumer integration. A pull request needs a green Testee verification. The
end-to-end test stays opt-in because it builds a real consumer shell.

Do not call pytest, ruff, or ty directly. This repository verifies through Testee.

Use Gitman for every version-control action. Do not run raw `git` or `jj`.

## How work is recorded

- Record the exact inputs, versions, commands, expected results, and actual results for any
  observation. Separate observation from inference.
- Keep raw logs outside the repository, under `~/.local/state/vendomat/`.
- Preserve every requirement ID. Never reuse or renumber one. Mark a changed requirement as
  superseded by a new ID rather than editing it in place. When you supersede one, search for
  duplicates of the same claim.
- Treat every new option name, command, and file format as proposed until a fixture proves it on
  the pinned tools.
- Record a documented upstream fact as evidence about the upstream tool, never as a passed gate.
- Record unavailable infrastructure as a named blocker with evidence. Do not report it as passed.
- A unit test does not replace a required real-consumer, cache, restore, or machine proof.
- If a fixture disproves an interface, update the specification, the guide, and the implementation
  together. Do not leave them disagreeing.

## Repository layout

- `.scratch/CURRENT.md`: the active project and its authority documents.
- `.scratch/projects/`: numbered project directories. Older numbers are history and provenance,
  never current authority.
- `flake.nix`, `lib/`, `modules/`, `src/vendomat/`, `vendor/`: the existing code surface.
- `tests/`: Python checks, Nix checks, and consumer fixtures.
- `docs/`: records and guides. Check `.scratch/CURRENT.md` before treating any of them as current.

## Host facts

`sudo` is at `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid and fails with a
misleading ownership message. The system is not broken.

Never select a disk by kernel device name. Kernel names move between boots. Use
`/dev/disk/by-id/` to select hardware, `/dev/disk/by-partuuid/` for a partition, and
`/dev/disk/by-uuid/` to mount a filesystem.

## Shared instructions

Follow your active user and machine instructions for rules that apply across repositories. Keep
this file focused on Vendomat.

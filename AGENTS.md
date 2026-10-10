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
testee verify --full
testee check e2e
```

Run the first command from the repository root as the normal gate. Run `testee verify` for a quick
check. Run the second command when a change affects the Nix module, toolchain, or consumer
integration. A pull request needs a green `testee verify --full`. The end-to-end check stays
opt-in because it builds a real consumer shell. The checks live in `devenv.nix` as
`testee.checks`.

The `testee` wrapper is the host program `~/.nix-profile/bin/testee`. It starts before devenv and
opens its own clean devenv shell. Do not wrap it in `devenv shell`. The uv dependency graph and the
venv do not carry Testee.

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
- `.scratch/projects/`: numbered project directories. Older numbers are closed history.
- `flake.nix`: one input (`nixpkgs`), one output (`packages.<system>.vendomat`).
- `src/vendomat/`: `registry.py`, `generate.py`, `store.py`, `locate.py`, `cli.py`.
- `hooks/`: the collection `post-receive` hook.
- `tests/`: Python checks, Nix checks, and fixtures.

The repository holds V5 and nothing else. `tests/test_repo_shape.py` fails when V4 code, a V4
directory, or a second flake input comes back.

## Host facts

`sudo` is at `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid and fails with a
misleading ownership message. The system is not broken.

Never select a disk by kernel device name. Kernel names move between boots. Use
`/dev/disk/by-id/` to select hardware, `/dev/disk/by-partuuid/` for a partition, and
`/dev/disk/by-uuid/` to mount a filesystem.

## Shared instructions

Follow your active user and machine instructions for rules that apply across repositories. Keep
this file focused on Vendomat.

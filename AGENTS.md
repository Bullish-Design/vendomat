# AGENTS.md — project instructions

Durable rules only. Project state, authority documents, and current work live in
[`.scratch/CURRENT.md`](.scratch/CURRENT.md). Read that file next.

Do not add project state here. A fact that changes when the active project changes belongs in
`.scratch/CURRENT.md`.

## What this project is

Vendomat composes one owner's NixOS machines, development projects, and reusable applications from
native devenv, NixOS, and Home Manager configuration.

Basix is a separate product in `../basix`, and this repository never names it in code (R1).

It is not a dependency resolver's replacement, a second lock, a daemon, a general runtime, a
deployment engine, a workspace orchestrator, or a cache protocol. Native declarations and locks
select dependencies. NixOS and Home Manager own activation. Attic owns cached objects.

## Working here

```bash
testee verify
testee verify opt:e2e
```

Run the first command from the repository root as the normal gate. Add named tasks (for example
`testee verify opt:e2e`) when a change affects the Nix module, toolchain, or consumer
integration. A pull request needs a green `testee verify` (or `testee status -r REV` for the exact
revision). The end-to-end task stays opt-in because it builds a real consumer shell.

Testee 0.8 runs devenv tasks. The project defines them in `nix/tasks.nix`. The required tasks are
`check:lint`, `check:format`, `check:types`, and `test:full`. `test:quick` is "n/a" (no quick
subset). During an edit, run `testee verify --profile quick` for `check:lint` and `check:format`
only. The opt-in tasks (`opt:e2e`, `opt:workspace-e2e`, `opt:front-door-e2e`, `opt:catalog-eval`,
`opt:catalog-devenv`, `opt:catalog-e2e`, `opt:parser-fuzz`, `opt:sharing-vm`, `opt:live-cache`,
`opt:live-cache-load`) never count for green. Each carries its own time limit in `input.testee.timeout_s`.
Run `opt:catalog-e2e`, `opt:front-door-e2e`, and `opt:parser-fuzz` after a change to the parser, the
catalog, the template, or the launcher. Run `opt:sharing-vm` after a change to `devenv/sharing.nix`.

The `testee` command is the host program (see the nix profile). It checks the commit in its own
workspace. The `setup:sync` task fills the venv before the checks. Do not wrap `testee` in
`devenv shell`. The uv dependency graph and the venv do not carry Testee.

Run `devenv shell -- cleanup` to list the regenerable leftovers (Testee venvs, stale Testee slots,
caches) with their sizes. Add `--yes` to delete them. It never deletes `.worktrees/`.

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
- `flake.nix`: one input (`nixpkgs`). Outputs: `packages.<system>.vendomat`,
  `packages.<system>.launcher`, `lib.<system>.mkLauncher`, and `devenvModules.default`.
- `devenv/`: the catalog that a workspace imports as `vendomat/devenv`. `parse.nix` is the
  `vendomat.yaml` parser (plain Nix, builtins only). `devenv.nix` is the catalog. `hatch.nix` counts
  the settings of `devenv.nix` and `devenv.local.nix` for the `advanced:` line. `explain.nix` builds
  the data of `vendomat explain`. `sharing.nix` is the Harmonia module of a machine.
- `templates/workspace/`: the `vendomat.yaml` workspace template. `workspace-v6/` and
  `workspace-registry/` serve the older flow, which stays until S8.
- `launcher/vendomat`: the host launcher. It enters the shell, trims errors, and dispatches
  `new`, `update`, `explain`, and the older verbs.
- `src/vendomat/`: the Python command line, `cli.py`, with `explain.py`, `update.py`, `errortrim.py`, and
  the older modules (`registry.py`, `generate.py`, `store.py`, `locate.py`, and others).
- `nix/`: `tasks.nix` (the Testee tasks) and `devenv-module/`.
- `devenv-dist/`: the recipe of the current devenv fork.
- `hooks/`: the collection `post-receive` and `pre-receive` hooks. `direnv/`: the direnv function.
- `tests/`: Python checks, Nix checks, and fixtures (`fixtures/yaml/` is the parser corpus;
  `tools/` holds the corpus generators).

`tests/test_repo_shape.py` fixes the set of `src/vendomat/` modules (a new module and its `MODULES`
entry land in one commit), forbids V4 directories, and allows one flake input and one dependency
(`typer`).

## Host facts

`sudo` is at `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid and fails with a
misleading ownership message. The system is not broken.

Never select a disk by kernel device name. Kernel names move between boots. Use
`/dev/disk/by-id/` to select hardware, `/dev/disk/by-partuuid/` for a partition, and
`/dev/disk/by-uuid/` to mount a filesystem.

## Shared instructions

Follow your active user and machine instructions for rules that apply across repositories. Keep
this file focused on Vendomat.

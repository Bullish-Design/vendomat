# AGENTS.md — project instructions

> **Seed.** The `my-ai` personal layer wrote this file because this repo had
> none. It is now **the repo's** file: edit it freely, and no `my-ai` update will
> ever overwrite it (`_skip_if_exists`). Every agent tool reads it through the
> `CLAUDE.md` symlink.

## What this project is

Vendomat is the vendor layer for the `*man` family. It builds native Python wheels once in the
Nix store, installs usage-gated dependency knowledge, and provides a shared `*man` command
toolchain. It is not the composition framework, manifest owner, or workspace orchestrator; those
roles belong to RepoMan, `repoman.lock`, and the surrounding fleet tools.

## Working here

```bash
devenv shell -- testee verify --mode quick
VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick
devenv shell -- nix build .#repoman-toolchain-core --no-link --print-out-paths
```

Run the first command as the normal gate. Run the second command when a change affects the Nix
module, toolchain, or consumer integration. A pull request needs a green Testee verification.
The end-to-end test remains opt-in because it builds a real consumer shell.

## Where things live

- `flake.nix`, `lib/`, and `modules/` define native artifacts and the shared command toolchain.
- `src/vendomat/` and `vendor/` implement dependency knowledge and publishing.
- `tests/` contains Python checks, Nix checks, and the real consumer fixture.

Read `README.md` for consumer configuration and `docs/` for design and implementation records.

## The standing configuration

The user's cross-repo law — devenv discipline, the exit-code contract, manager
routing, the agent-files convention — lives in
[`.agents/skills/my-ai/SKILL.md`](.agents/skills/my-ai/SKILL.md), delivered by
the `my-ai` personal layer. **Read it first.** Keep this file for what is true of
*this* project only.

```bash
copyroom layer list              # which template layers manage this repo
copyroom update --layer my-ai    # converge the personal layer
copyroom agent-files check       # conformance report
```

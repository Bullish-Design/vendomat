# Project 20: implementation plan

**Proposal, 2026-10-12 (second simplification pass).** [CONCEPT.md](CONCEPT.md) states the
user path. [REQUIREMENTS.md](REQUIREMENTS.md) holds the active IDs `DOOR-071` to `DOOR-075`
(`DOOR-074` and `DOOR-075` supersede `DOOR-069` and `DOOR-070`), with `DOOR-036`, `DOOR-038`,
and `DOOR-063`. The
[second review](evidence/SIMPLIFY-REVIEW-2026-10-12-PASS2.md) records the lost capability and
the owner questions. No project 20 runtime gate has passed. Spikes P2A to P2G are fixture
evidence only.

## Before slice 1

The owner rules on the review's questions Q1 to Q4 as one group. Slice 1 needs Q1. Slice 2
needs Q2. The release needs Q3 and Q4.

## Slices and gates

| Slice | Result | Gate | Rollback |
| --- | --- | --- | --- |
| 1. Workspace | The catalog module in the Vendomat release (`devenv/`), its parse step, the fixed template, a `release` branch, and the host `vendomat` with `new` and pass-through. The fork series in `devenv-dist/` gains patch 0009 (`vendomatFromYAML`) with its Rust unit tests. The host puts the fork first on the PATH that Testee inherits. | `DOOR-074`, `DOOR-075`, `DOOR-071` gates on the pinned fork. `testee verify`, `testee verify --profile full`, and `testee verify e2e` pass. | Revert the slice; the current runtime stays. |
| 2. Basix machine | The machine catalog table, `vendomat apply`, and then the Basix ISO with `vendomat install` and a local preflight mode. | `DOOR-072` in a VM: install to a blank virtual disk, refuse the boot medium and a used disk, zero failed units, apply, boot-menu rollback. | Revert the Basix module. No real disk. |
| 3. Sharing | `serve = true` with a self-made key, and derived client settings. | `DOOR-073` with two VMs, then a real two-machine check. | Revert the cache module. Attic stays. |
| Release | Hand-move the two live consumers to the new `vendomat.yaml`, release the host command, remove old paths after the real cache check. | `DOOR-063`. Consumer checks pass. The host keeps a rollback generation. | Switch to the earlier host generation. |

The critical path is **workspace → Basix machine → sharing → release**. Slice 3 may start on
fixture VMs when slice 2 has the machine table and `vendomat apply`; it does not need the ISO.

## First slice

Start from the P2A, P2B, P2C, and P2G fixtures under `~/.local/state/vendomat/p20/2026-10-12/`.

1. Add patch 0009 (`vendomatFromYAML`, from `evidence/fixtures/p2g/`) to the fork series in
   `devenv-dist/`. Run its Rust unit tests with `cargo test` or a Nix build with `runTests`.
   Build a release (`v2.4.0-vendomat.4`). Put the fork first on the PATH that Testee inherits.
2. Write the catalog module with four kinds: programs, languages, services, environment values.
   Name each entry. Read `vendomat.yaml` with `builtins.readFile` and parse it with
   `devenvPrimops.vendomatFromYAML`. Parse once with `tryEval` and list all faults; map only
   parsed values.
3. Write the fixed template and the `release` branch convention. Use a URL form that locks a
   `rev`.
4. Change the host `vendomat`: bare entry opens the shell, `new` copies the template, and every
   other argument runs the pinned fork with `exec`. Keep `sync` and Attic push until the release.
5. Prove the three gates on the pinned fork. Test a `build` of an attribute that reads no
   mapped value; P2B did not.

If a fixture disproves the surface, revise the concept, the requirements, and the plan together.

## Hardware gate

Prepare a read-only package with stable disk identity, a partition and signature scan, a
hardware report, the planned commands, the expected results, and the undo steps. Mark every real
write **NOT RUN**. The owner has not authorized a real disk write. No gate grants it.

## Working rules

- Treat every name and interface as proposed until a fixture passes on the pinned tools. Print
  `devenv version` in each devenv log. Keep raw logs under `~/.local/state/vendomat/p20/<date>/`.
- Use the host `~/.nix-profile/bin/testee`. Do not call pytest, ruff, or ty.
- Use Gitman for the workspace and jj for its lifecycle. Land verified work on `main`.
- Before a VM build, run `btrfs filesystem usage /`. Stop below 2 GiB unallocated or above 90 %
  metadata. Run one VM build at a time. Never run Nix store garbage collection.
- Mint a requirement ID only when the owner accepts a design or a fixture proves its interface.

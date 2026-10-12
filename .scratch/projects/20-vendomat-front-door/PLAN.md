# Project 20: implementation plan

**Proposal, 2026-10-12 (second simplification pass).** [CONCEPT.md](CONCEPT.md) states the
user path. [REQUIREMENTS.md](REQUIREMENTS.md) holds the active IDs `DOOR-071` to `DOOR-076`
(`DOOR-074` and `DOOR-075` supersede `DOOR-069` and `DOOR-070`), with `DOOR-036`, `DOOR-038`,
and `DOOR-063`. The
[second review](evidence/SIMPLIFY-REVIEW-2026-10-12-PASS2.md) records the lost capability and
the owner questions. The owner accepted R1 to R5. Slice 1 is complete. The Testee profile, front-door
gate, full end-to-end gate, two-VM hook test, and published-channel smoke pass. The `.4` tag and
`release` branch are published. No Basix machine gate has passed.

## Before slice 1

The owner accepted Q1 to Q4 and the collection rule on 2026-10-12 (`DECISIONS.md`, R1 to R5).
Slice 1 may start.

## Slices and gates

| Slice | Result | Gate | Rollback |
| --- | --- | --- | --- |
| 1. Workspace | The catalog module, parser, fixed template, host `vendomat` with `new` and pass-through, fork patch 0009, and Vendomat-only fast-forward release branch rule are implemented. The `.4` fork and `release` branch are published. | `DOOR-071`, `DOOR-074`, and `DOOR-075` pass. The `DOOR-076` NixOS hook test and published-channel smoke pass. Testee is GREEN on the current tree. | Revert the slice; the current runtime stays. |
| 2. Basix machine | The machine catalog table, `vendomat apply`, and then the Basix ISO with `vendomat install` and a local preflight mode. | `DOOR-072` in a VM: install to a blank virtual disk, refuse the boot medium and a used disk, zero failed units, apply, boot-menu rollback. | Revert the Basix module. No real disk. |
| 3. Sharing | `serve = true` with a self-made key, and derived client settings. | `DOOR-073` with two VMs, then a real two-machine check. | Revert the cache module. Attic stays. |
| Release | Hand-move the two live consumers to the new `vendomat.yaml`, release the host command, remove old paths after the real cache check. | `DOOR-063`. Consumer checks pass. The host keeps a rollback generation. | Switch to the earlier host generation. |

The critical path is **workspace → Basix machine → sharing → release**. Slice 3 may start on
fixture VMs when slice 2 has the machine table and `vendomat apply`; it does not need the ISO.

## First slice

Start from the P2A, P2B, P2C, and P2G fixtures under `~/.local/state/vendomat/p20/2026-10-12/`.

**Status, 2026-10-12.** The catalog, template, host command, patch series, and local front-door
gate are implemented. See [slice 1 gate records](evidence/slice-1/). Testee is GREEN on the current
tree. The full profile passes all four required checks. The front-door gate passes one consumer test.
The end-to-end profile passes 395 tests and skips two. See [Testee evidence](evidence/slice-1/TESTEE-2026-10-12.md).
The Testee gate refuses an
invalid catalog during evaluation with exit 2; it does not mark that commit RED. A valid catalog
change can make a consumer check RED, and restoring the file returns GREEN. This matches the
observed Testee 0.6.1 interface. The actual collection read-side smoke later passed; see
[published-channel evidence](evidence/slice-1/PUBLISHED-CHANNEL-2026-10-12.md).

1. Add patch 0009 (`vendomatFromYAML`, from `evidence/fixtures/p2g/`) to the fork series in
   `devenv-dist/`. Run its Rust unit tests with `cargo test` or a Nix build with `runTests`.
   **Done:** 27 Rust unit tests pass, the fork builds as `2.4.0+c66ba87`, and Testee ran with the
   fork first on its inherited PATH. Publish the release tag after the repository gates pass.
2. Write the catalog module with four kinds: programs, languages, services, environment values.
   Name each entry. Read `vendomat.yaml` with `builtins.readFile` and parse it with
   `devenvPrimops.vendomatFromYAML`. Parse once with `tryEval` and list all faults; map only
   parsed values.
3. Write the fixed template and the `release` branch convention. Use a URL form that locks a
   `rev`.
4. Change the host `vendomat`: bare entry opens the shell, `new` copies the template, and every
   other argument runs the pinned fork with `exec`. Keep `sync` and Attic push until the release.
5. **Done on the local fixture channel:** prove the three gates on the patched fork. The gate also
   builds an attribute that reads no mapped value.

The initial slice 1 gate used a loopback Git server. After publication, a fresh workspace used the
template URL and entered the shell through the actual collection. See the
[published-channel record](evidence/slice-1/PUBLISHED-CHANNEL-2026-10-12.md).

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

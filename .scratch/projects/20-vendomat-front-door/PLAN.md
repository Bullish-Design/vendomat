# Project 20: smaller implementation plan

**Proposal, 2026-10-12.** [CONCEPT.md](CONCEPT.md) states the proposed user path.
[REQUIREMENTS.md](REQUIREMENTS.md) preserves old claims and gives seven proposed
successor IDs. The [review](evidence/SIMPLIFY-REVIEW-2026-10-12.md) records the
lost capability. No project 20 runtime gate has passed. The direct-TOML
`lib.evalModules` fixture is evidence only.

The first release covers four journeys: one fresh Basix machine, a development
workspace, explicit update and rollback, and optional output sharing with a
second machine. Adoption, collection mirrors, automatic secret delivery, and
custom disk layouts wait for a later decision.

## Slices and gates

| Slice | Result | Needs | Gate and rollback |
| --- | --- | --- | --- |
| 1. Direct workspace | A fixed module reads `vendomat.toml` directly. Native `devenv.yaml` owns inputs and imports. The host command opens a shell or passes through to pinned devenv. | Owner ruling on TOML before runtime wiring. `DOOR-057` to `DOOR-059`, `DOOR-062`. | On the pinned fork, a fresh workspace adds a program, language, service, and tagged input. Used and unused bad values fail before shell, test, and build. Type errors name the user file. A changed ref updates the native lock; version control restores the old result. `testee verify`, `testee verify --profile full`, and `testee verify e2e` pass. Revert the slice to restore the old runtime. |
| 2. Fresh Basix | One typed fresh-install record, keyless core, installer ISO route, and real disk preflight. The controller uses separate installer and admin keys. | Slice 1; Basix repository placement; installer ISO fixture. `DOOR-060`. | A fresh virtual machine boots with zero failed units and no user key or cache. A wrong target and a protected disk fail before a write. Re-pin the host key. Test native generation rollback. `testee verify` and the named virtual-machine check pass. Revert the Basix module; do not touch real disks. |
| 3. Optional sharing | A second fresh machine can substitute signed output from a configured Harmonia host. Clients use explicit trust and fallback. | Slice 2. `DOOR-061`. | One two-VM run proves cold substitution, bad-signature refusal, absent-path fallback, down-cache fallback with bounded timeout, and selected-root survival. A real two-machine check then proves the network route. Keep Attic until that check passes. Revert the new cache module if it fails. |
| Release and migration | Hand-migrate the two live consumers, release the host command, and remove old paths after gates pass. | Slices 1 to 3; `DOOR-063`. | Each migration records source-to-destination mapping and activates no machine. Consumer checks pass. The host release has an explicit rollback generation. A repository-shape check finds no old parser, `sync`, Attic push, or two-marker launcher after the live cache gate. |

The critical path is **direct workspace → fresh Basix → two-machine sharing → release**.
The first implementation slice is the direct workspace. Start it with a small
fixture on the pinned devenv fork that extends the isolated direct-TOML probe:
program mapping, native input, module source location, and eager invalid-value
failure. If the fixture disproves the direct surface, revise the concept,
requirements, and plan together before production wiring.

## Hardware gate

Prepare a read-only package with stable disk identity, partition and signature
scan, hardware report, planned commands, expected results, and undo steps.
Mark every real write **NOT RUN**. The owner has not authorized a real disk
write. No release gate, unit test, or virtual-machine result grants that
authorization. Run only the named commands the owner later authorizes.

## Working rules

- Treat every proposed name and interface as unproved until a fixture passes on
  the pinned tools. Print `devenv version` in each devenv fixture log.
- Record exact inputs, versions, commands, expected results, actual results,
  inference, limits, and raw log path. Keep raw logs under
  `~/.local/state/vendomat/p20/<date>/`.
- Use the host `~/.nix-profile/bin/testee`. Run `testee verify --profile quick`
  during edits. Run `testee verify` and `testee verify --profile full` before
  landing. Add `testee verify e2e` for module, toolchain, and consumer changes.
  Check `testee status -r REV` on the exact revision. Do not run pytest,
  ruff, or ty directly.
- Use Gitman for the workspace and native jj for its lifecycle. Keep existing
  production paths until the successor passes its gate. Land verified work
  on `main` and push it.
- Before any virtual-machine build, run `btrfs filesystem usage /`. Stop if
  unallocated space is below 2 GiB or metadata use exceeds 90 %. Run one
  virtual-machine build at a time. Never run Nix store garbage collection.

## Decisions and next session

The owner must rule on direct TOML with native input edits before slice 1
changes the runtime. The owner must separately rule on closing the V5 and V6
ledgers as history. Basix repository placement (O2), a real installer ISO (O9),
Attic removal after the live cache gate (O5), and real disk authorization (O7)
remain later decisions. O6 was resolved on 2026-10-12. Adoption and its O8
comparison are deferred.

The next session first runs the pinned-fork direct-read fixture. It then records
the owner's format ruling and implements slice 1. Do not copy the S1 YAML parser
into production. The new design has no generated data or YAML grammar.

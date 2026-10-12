# Project 20 simplification review, second pass

**Date:** 2026-10-12. This is a design proposal, not an implementation result. It follows
[the first pass](SIMPLIFY-REVIEW-2026-10-12.md) of the same day. The first pass left its key
claims unproved and kept several mechanisms marked "no safe reduction found". This pass tested
those claims on the pinned tools and audited the revised documents. No production code,
consumer, machine, or real disk changed.

## Evidence

Five spikes and one audit ran in isolation. Each spike record holds the question, the hypotheses,
the exact inputs, the commands, the expected and actual results, and the limits. Raw logs stay
under `~/.local/state/vendomat/p20/2026-10-12/` (`A-fork-direct-read/` to `F-audit/`).

| Record | Question | Result on the pinned fork `devenv 2.4.0+fb5d382` |
| --- | --- | --- |
| [P2A](P2A-fork-direct-read.md) | Can a fixed module read the workspace's TOML directly? Does the eval cache go stale? | Yes. `builtins.fromTOML (builtins.readFile (config.devenv.root + "/vendomat.toml"))` works with no flag. The eval cache saw every edit, create, and delete, including a same-size edit with the old mtime. `pathExists` makes a missing file an empty catalog. A fresh clone enters the shell with no extra step. `devenv.nix` must exist (`{ }` is enough). |
| [P2B](P2B-eager-checks.md) | Can Nix types be the only validator, with eager failure and usable errors? | Yes, with one parse step. An unknown key fails every command with no extra code and names `vendomat.toml`. A bad unused value passes until forced. A `deepSeq` of the catalog at each mapped value stopped all five tested commands before work. A `throw` at module `config` level gave infinite recursion. A short `tryEval` step lists every type error at once with the file and field. TOML gives no line numbers. The fork prints a 300-line trace around the useful line. |
| [P2C](P2C-update-channel.md) | Can "update" be a native lock update with no edit protocol? | Yes. The workspace names the Vendomat input on a `release` branch. `devenv update` moved the lock to the newest release commit and never to `main`. A restored `devenv.lock` gave the old shell back. Two conditions: a fixed `nixpkgs.follows: vendomat/nixpkgs` line, and a `git://`, `git+ssh://`, or `github:` URL (a `git+file` lock holds no `rev`). A failed fetch leaves the lock intact but exits 0. |
| [P2D](P2D-machine-path.md) | What is the simplest first install for one machine? | The fork's Machines install works only over SSH from a controller (`machines.rs:1704`); it has no local mode. A local install from a Basix ISO removes the controller, the target address, the installer key, the admin key as a required field, and the host-key re-pin from the learner path. Native `switch-to-configuration` already exits non-zero on a failed unit. |
| [P2E](P2E-cache-key.md) | Must an administrator place the cache signing key? | No. In one NixOS VM test, a oneshot made the key on first start, Harmonia started after it, and a client verified the signature. A wrong client key refused the path. Nix refused an unsigned path unless `require-sigs = false`, so unsigned sharing is rejected. Harmonia serves and signs any path in its store, built there or not. |
| F audit | What did the first pass keep by habit, miss, or contradict? | It counted 21 learner concepts, not 7. It found eleven contradictions, for example `DECISIONS.md` S18 against S24 and two validators in `CONCEPT.md`. It proposed cuts for `test`, `build`, the `vendomat devenv` prefix, the failed-unit gate, and the update protocol. |

P2A and P2C disagree on `follows`. P2A used a catalog input with `flake: false`, so
`follows: vendomat/nixpkgs` failed. P2C used a flake input, so the same line worked. The
Vendomat release is a flake. The design uses the P2C form.

## The 90 % journeys

| Journey | Needs | Moves to the 10 % |
| --- | --- | --- |
| 1. Install Basix on one machine and change it | A Basix ISO, one install command on the machine, a disk choice by typed by-id, a console password, `vendomat.toml`, `vendomat apply`, the boot menu for rollback | Remote and headless install, adoption, used-disk erase, custom layouts, reviewed plans |
| 2. Create a workspace and run tests | `vendomat new`, `vendomat.toml`, `vendomat`, `vendomat test` | Inputs or modules outside the catalog, arbitrary option paths |
| 3. Update and roll back | `vendomat update`; version control restores `devenv.lock` | Pinning an older release, holding back one dependency |
| 4. Add a second machine and share outputs | Repeat journey 1; one `serve` switch on one machine; one host name and public key line on the others | Several cache hosts, key backup and rotation, a build host workflow |

## Mechanism review

The table covers every mechanism that the first pass's revised documents still carried.
"Lost" names the capability that leaves the routine path. Most lost items stay reachable
through native Nix.

| Mechanism | Why it exists | Simpler shape | Removes | Lost | Evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `vendomat.toml` read directly by a fixed module | One routine file without Nix | Keep. Read `config.devenv.root + "/vendomat.toml"`; a missing file is an empty catalog | A "missing file" failure | None | P2A | keep |
| Template-owned `devenv.yaml`, `devenv.nix`, `devenv.lock` | Native devenv needs them | Fixed content: one input, one `follows` line, one import; `devenv.nix` is `{ }` | Routine edits of native files | None | P2A, P2C | keep |
| Two validators: Vendomat checks before devenv, then Nix types | Early errors | One parse step inside the catalog module. Every mapping reads only the parsed value, so no command can skip it | Release skew between host and pinned catalog; a second validator | Precise TOML line and column | P2B | simplify |
| Per-leaf `deepSeq` guard | Force unused values | Fold into the parse step: the module maps from one parsed value | A rule that each mapping must remember | None | P2B | simplify |
| Unbounded "settings" catalog kind | Cover the long tail | Named entries only; the rest uses `devenv.nix` | Arbitrary option paths as data | Long-tail options as data | F audit | cut |
| Program name lookup | Map names to packages | Parse step resolves each name and lists every unknown name | Raw `attribute missing` with no file | None | P2B | keep |
| Trace noise around errors | The fork always prints a trace | Vendomat's own verbs print from the last `error:` line; pass-through keeps native output | A 300-line trace on Vendomat verbs | Full trace without `--show-trace` on those verbs | P2B | simplify |
| Named `test` and `build` | Routine intents | Pass-through to the pinned fork: `vendomat test` runs `devenv test` | Two Vendomat verbs | None | F audit | cut |
| `vendomat devenv ...` prefix | Explicit advanced door | Pass-through of every unnamed argument | One prefix concept | None | F audit | cut |
| `update` edit protocol | Move a release ref and lock together | Release branch; `vendomat update` passes through to `devenv update` | The edit protocol, "supported release" refs | Choosing an older release on the routine path | P2C | cut |
| Failed-unit gate before apply and deploy (O10) | Do not activate onto a degraded host | Local `vendomat apply` reports the native switch status and failed units | A wrapper refusal; O10 | Refusal to activate onto an already degraded host | P2D | cut |
| Remote install by controller | Install from another machine | Local install from the Basix ISO; remote install through native Machines is the advanced door | Controller, target address, installer key, required admin key, host-key re-pin | Headless and unattended install | P2D | defer |
| Disk preflight | Prevent a wrong disk write | Keep, run on the target: list blank non-boot by-id disks, refuse the boot medium, partitions, and signatures, require the typed full by-id | Remote preflight copy and nonce | Install onto a used disk | P2D, S4 | keep |
| Typed fresh-install record | Make a bad inventory unrepresentable | The installer writes the record from the disk the user confirmed; the user never types system facts | Model, serial, size, target, keys as user fields | None on the routine path | P2D | simplify |
| Cache key placement and start condition | Keep the key out of the store | The host makes its own key on first start, before Harmonia | Key placement, path unit, `ConditionPathExists`, delivery route | Key survival across a reinstall without a backup | P2E | cut |
| Cache client settings | Trust and fallback | Derive URL, trust, `fallback = true`, and a short connect timeout from one host name and one public key line | Per-client settings | Several cache hosts | P2E | keep |
| "Build shared outputs on the cache host" | Make shared outputs exist | Advice only. The host serves what its store holds; clients build the rest | A build host workflow | Guaranteed warm cache | P2E | cut |
| Native roots for shared outputs | Keep outputs alive | Defer. Generations already root what each machine runs | A root management task | Retained old releases | P2E, S6 | defer |
| Hand migration record | Audit the format change | Version control history of the two consumers is the record | A table per consumer | A separate audit table | F audit | simplify |
| Attic overlap until the Harmonia live gate | Keep the current cache | Keep. It is temporary and is not a user concept | Nothing | Nothing | S6 | keep |
| Collection, source modes, keep clones | Private source store | Defer from the first release | Source modes and the collection builder | Offline source mirror | R3 | defer (owner ruling) |
| Separate Basix repository and input | Ownership split (O2) | Ship the machine catalog in the Vendomat release for the first release | One input, one release channel, O2 | Independent Basix releases | Inference | simplify (owner ruling) |

## New mental model

1. You describe a workspace or a machine in one file, `vendomat.toml`; Vendomat owns every other file.
2. `vendomat` opens the shell, and any other command runs in the pinned devenv.
3. `vendomat update` moves to the newest Vendomat release; version control or the boot menu takes you back.
4. You install a machine from the Basix USB stick, then `vendomat apply` switches it to your file.
5. One machine can serve what it builds; the others name it and copy its public key line.

## Before and after

"Before" is the first pass's revised documents, counted by the audit. "After" is this proposal.

| Measure | First pass | This pass |
| --- | --- | --- |
| Learner concepts | 21: fresh-machine record, admin key, controller and target roles, installer key, host-key re-pin, disk preflight, `vendomat.toml`, catalog kinds, `new`, template-owned native files, bare shell, `test`, `build`, `update` and release refs, `devenv.lock`, version-control restore, `machine` workflow, failed-unit gate, generation rollback, cache record with key placement and roots, advanced door | 9: `vendomat.toml`, catalog entries, `vendomat` shell and pass-through, `new`, `update` with version-control restore, Basix USB install with disk confirmation, `apply` with boot-menu rollback, sharing (serve, or host plus key line), native files as the advanced door |
| Files the user edits | 1 routine, 3 more by the update and machine flows | 1: `vendomat.toml` |
| Files in a workspace | 4 | 4: `vendomat.toml`, `devenv.yaml`, `devenv.nix`, `devenv.lock` |
| Vendomat verbs | 5 plus `vendomat devenv` | 3: `new`, `apply`, and `install` (on the ISO only); bare entry; pass-through |
| Machine modes | 1 | 1 |
| Failure states owned by Vendomat | Catalog fault, stale protocol, failed-unit refusal, disk refusal, update edit fault | Catalog fault, disk refusal |

## Owner questions

These four rulings block implementation. Evidence cannot settle them, because each one trades a
capability the owner may value.

| # | Question | Recommendation |
| --- | --- | --- |
| Q1 | Accept direct TOML with a bounded catalog in place of the 2026-10-11 YAML decision? (Open since the first pass.) | Yes. |
| Q2 | Make the learner install local from a Basix ISO, and move remote install to the native door? The owner's `server` install would use the native door. | Yes. |
| Q3 | Defer the source collection, mirrors, and keep clones from the first release? This touches the "two tracked things" rule from project 14. | Yes. |
| Q4 | Close the V5 and V6 ledgers as history at cutover, and replace the 521-row map with the rows that cite live IDs? (Open since the first pass.) | Yes, at cutover, not before, because V5 code still runs. |

O2 (Basix placement) becomes part of Q2's package: the first release ships the machine catalog in
the Vendomat release. O10 disappears: no failed-unit refusal remains. O5, O7, and O9 stay as
recorded in [DECISIONS.md](../DECISIONS.md).

## Process weight

The first pass minted five IDs and superseded them the same day. This pass supersedes the six
proposed IDs with five (`DOOR-069` to `DOOR-073`). From now on, mint an ID only when the owner
accepts a design or a fixture proves its interface. Keep drafts ID-free in the review.

## Handoff

- **Changed.** `CONCEPT.md` is rewritten around the five-sentence model. `REQUIREMENTS.md`
  supersedes `DOOR-060` and `DOOR-064` to `DOOR-068` with `DOOR-069` to `DOOR-073`.
  `DECISIONS.md` adds S27 to S35. `PLAN.md` has three slices and a release.
- **Cut.** Named `test` and `build`, the `vendomat devenv` prefix, the update edit protocol, the
  Vendomat-side catalog check, the failed-unit refusal, cache key placement and its path unit,
  the "settings" catalog kind, and the hand-migration table.
- **Moved to the advanced door.** Remote install and deploy, the installer and admin keys, and
  the host-key re-pin.
- **Owner rulings needed.** Q1 to Q4 above. O5, O7, and O9 stay open.
- **Next session.** Record the owner's rulings. Then start slice 1 in [PLAN.md](../PLAN.md) from
  the P2A, P2B, and P2C fixtures.

## Limits

- No implementation, consumer, Basix ISO, local apply, or two-machine run exists.
- P2B tested five commands. A `build` of an attribute that reads no mapped value was not tested.
- P2C did not test a bumped nixpkgs inside the release, a cold store, or a force-pushed branch.
- P2D is reading plus an eval-only fixture. The local installer and `nixos-rebuild --store-path`
  with the fork's machine output are unproved.
- P2E ran one VM. It did not prove a second machine, a real network, a reboot, or the timeout.

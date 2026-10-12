# Project 20 simplification review, second pass

**Date:** 2026-10-12. This is a design proposal, not an implementation result. It follows
[the first pass](SIMPLIFY-REVIEW-2026-10-12.md) of the same day. The first pass left its key
claims unproved and kept several mechanisms marked "no safe reduction found". This pass tested
those claims on the pinned tools and audited the revised documents. No production code,
consumer, machine, or real disk changed.

## Evidence

Five spikes and one audit ran in isolation. Two more spikes (P2F and P2G) ran later the same day. Each spike record holds the question, the hypotheses,
the exact inputs, the commands, the expected and actual results, and the limits. Raw logs stay
under `~/.local/state/vendomat/p20/2026-10-12/` (`A-fork-direct-read/` to `F-audit/`, `F2-yaml-handoff/`, and `G-fork-yaml/`).

| Record | Question | Result on the pinned fork `devenv 2.4.0+fb5d382` |
| --- | --- | --- |
| [P2A](P2A-fork-direct-read.md) | Can a fixed module read the workspace's TOML directly? Does the eval cache go stale? | Yes. `builtins.fromTOML (builtins.readFile (config.devenv.root + "/vendomat.toml"))` works with no flag. The eval cache saw every edit, create, and delete, including a same-size edit with the old mtime. `pathExists` makes a missing file an empty catalog. A fresh clone enters the shell with no extra step. `devenv.nix` must exist (`{ }` is enough). |
| [P2B](P2B-eager-checks.md) | Can Nix types be the only validator, with eager failure and usable errors? | Yes, with one parse step. An unknown key fails every command with no extra code and names `vendomat.toml`. A bad unused value passes until forced. A `deepSeq` of the catalog at each mapped value stopped all five tested commands before work. A `throw` at module `config` level gave infinite recursion. A short `tryEval` step lists every type error at once with the file and field. TOML gives no line numbers. The fork prints a 300-line trace around the useful line. |
| [P2C](P2C-update-channel.md) | Can "update" be a native lock update with no edit protocol? | Yes. The workspace names the Vendomat input on a `release` branch. `devenv update` moved the lock to the newest release commit and never to `main`. A restored `devenv.lock` gave the old shell back. Two conditions: a fixed `nixpkgs.follows: vendomat/nixpkgs` line, and a `git://`, `git+ssh://`, or `github:` URL (a `git+file` lock holds no `rev`). A failed fetch leaves the lock intact but exits 0. |
| [P2D](P2D-machine-path.md) | What is the simplest first install for one machine? | The fork's Machines install works only over SSH from a controller (`machines.rs:1704`); it has no local mode. A local install from a Basix ISO removes the controller, the target address, the installer key, the admin key as a required field, and the host-key re-pin from the learner path. Native `switch-to-configuration` already exits non-zero on a failed unit. |
| [P2E](P2E-cache-key.md) | Must an administrator place the cache signing key? | No. In one NixOS VM test, a oneshot made the key on first start, Harmonia started after it, and a client verified the signature. A wrong client key refused the path. Nix refused an unsigned path unless `require-sigs = false`, so unsigned sharing is rejected. Harmonia serves and signs any path in its store, built there or not. |
| F audit | What did the first pass keep by habit, miss, or contradict? | It counted 21 learner concepts, not 7. It found eleven contradictions, for example `DECISIONS.md` S18 against S24 and two validators in `CONCEPT.md`. It proposed cuts for `test`, `build`, the `vendomat devenv` prefix, the failed-unit gate, and the update protocol. |
| [P2F](P2F-yaml-handoff.md) | Can the user file be YAML, parsed by our own strict-subset parser, with no stored copy? | Parsing works: 173 lines of stdlib Python, 39 ms, every scalar a string, and Nix types give the meaning. The hand-off to Nix does not work on every entry point. Only plain `builtins.exec` with `readFile` (H3b) works on a fresh clone, direct devenv, direnv, and Testee. It needs the machine-wide `allow-unsafe-native-code-during-evaluation = true`. Plain `exec` without `readFile` (H3) gives a silent stale eval and a false GREEN under Testee. |
| [P2G](P2G-fork-yaml.md) | Can our devenv fork parse `vendomat.yaml` itself, with no stored copy and no unsafe Nix setting? | Yes. A Rust primop `vendomatFromYAML name text` (patch 0009, 403 lines) parses a strict subset. The catalog passes it the text of `builtins.readFile`, so the eval cache tracks every edit. Edit detection, direct `shell` and `test`, a fresh clone, direnv, and Testee 0.6.1 all passed with no unsafe setting. The Rust parser matched the P2F Python parser on 27 of 27 case files. Syntax errors give `vendomat.yaml:LINE:COL: reason`. Condition: the process that evaluates must run the fork, not stock devenv. |

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
| `vendomat.toml` read directly by a fixed module | One routine file without Nix | Keep, now as `vendomat.yaml`. Read `config.devenv.root + "/vendomat.yaml"` with `builtins.readFile` and parse it with the fork primop; a missing file is an empty catalog | A "missing file" failure | None | P2A, P2G | keep |
| Template-owned `devenv.yaml`, `devenv.nix`, `devenv.lock` | Native devenv needs them | Fixed content: one input, one `follows` line, one import; `devenv.nix` is `{ }` | Routine edits of native files | None | P2A, P2C | keep |
| Two validators: Vendomat checks before devenv, then Nix types | Early errors | One parse step inside the catalog module. Every mapping reads only the parsed value, so no command can skip it | Release skew between host and pinned catalog; a second validator | Line and column of a type error (a syntax error keeps its line) | P2B, P2G | simplify |
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

**Note (P2G).** Rows above that name `vendomat.toml` or TOML now read `vendomat.yaml`. The fork primop reads it (P2G) in place of `builtins.fromTOML` (P2A). The parse step still lists type errors by field without a line number. A syntax error now carries `vendomat.yaml:LINE:COL`. The same swap applies to the journeys table and the "Before and after" table.

## New mental model

1. You describe a workspace or a machine in one file, `vendomat.yaml`; Vendomat owns every other file.
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
| Q1 | Confirm YAML through the fork primop (`vendomat.yaml`) in place of TOML. (Open since the first pass; restated after P2G.) | Yes. P2G passed the entry-point table with no unsafe setting. It keeps the 2026-10-11 YAML decision. |
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

## YAML hand-off (P2F)

**Question.** Can the user file be `vendomat.yaml`, parsed by our own strict-subset parser,
with no stored copy of the data? The spike used the pinned fork `devenv 2.4.0+fb5d382`. The
parser is 173 lines of stdlib Python and runs in 39 ms. Every scalar stays a string, and the
catalog module's Nix types give the meaning. `version: 3.10` and `name: no` stay text.
`enable: no` is rejected with the file and field. Unit checks gave `vendomat.yaml:LINE:COL` on
15 inputs. No fuzz or oracle test ran.

Four candidates moved the parsed data into the Nix evaluation.

| Candidate | Edit detection | Direct devenv, no wrapper | Fresh clone | direnv | Testee | Error line | Traps | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1: wrapper passes JSON in an env var | All 5 edits seen. The eval cache keys on `getEnv`. | Fails with a JSON parse error. Silent stale if the variable leaks from a wrapper shell. | Wrapper only | Fails | Fails: Testee drops the variable | One line `vendomat.yaml:LINE:COL`, before devenv starts | Stale when the variable leaks | None measured |
| H2: wrapper writes an ignored `.devenv/` file | All 5 edits seen through the wrapper | Silent stale. The old file stays. | Fails | Fails | Fails with a misleading `module_missing` | One line, before devenv starts | Silent stale; wrong error text | None measured |
| H3: plain `builtins.exec` of the parser on the file | None seen. Silent stale. | Stale after an edit | Works with the setting | Stale after an edit | False GREEN | Parser line first, then 237 lines of trace | Silent stale | Machine-wide unsafe setting |
| H3b: Nix `readFile`, text passed to the parser by `builtins.exec` | All 5 edits seen | Works with the setting | Works with the setting | Works | Works, if `nix.conf` holds the setting | Parser line first, then 237 lines of trace. Lost under Testee. | Needs the setting on every machine | Machine-wide unsafe setting |

**Surprise: a false GREEN.** H3 passed under Testee at version 3.10. After the file changed to
3.11, Testee passed again, and the check file still said 3.10. The eval cache does not track what
`builtins.exec` reads, so the change stayed hidden. H3b fixes this: Nix reads the file, so the
cache tracks it.

**Why H3b has a cost.** `builtins.exec` exists only when the Nix setting
`allow-unsafe-native-code-during-evaluation` is `true`. No per-project switch exists in the
fork. `nixConfig:` and `nix_options:` keys in `devenv.yaml` had no effect. A flag or `NIX_CONFIG`
works, but Testee drops `NIX_CONFIG`. With the setting, any evaluated Nix code can run any
program as the user, including third-party flakes and every `nix eval` on the machine. A test
printed `"ran as andrew"` with the setting and `attribute 'exec' missing` without it. No
hostile `devenv.nix` ran.

**Conclusion.**

1. Only H1 and H2 give a good error line, and neither survives direct devenv, direnv, or Testee.
2. Only H3b works on every entry point, and it needs a machine-wide unsafe setting. Reject it.
3. TOML needs no hand-off step. The fork reads it directly (P2A). Keep TOML for the first release.
4. A fork patch that lets devenv read `vendomat.yaml` itself would give YAML the TOML behavior.
   A spike for that patch is running. YAML returns only if the patch passes the same
   entry-point table.

Limits: very large files, a concurrent edit, a symlinked file, integer fields, and a Testee hook
that runs a data step first are unproved.

P2G (next section) ran that spike. Its result replaces conclusion items 3 and 4.

## YAML through a fork primop (P2G)

**Question.** Can our devenv fork parse `vendomat.yaml` itself, so that every entry point sees
current data, with no stored copy and no unsafe Nix setting? The fork (`devenv 2.4.0+fb5d382`)
evaluates Nix in process through the Nix C API. It already has a primop registry
(`devenv-nix-backend/src/primops.rs`, with `loadDotenv` and `allocatePort`). Modules receive the
registry as the `devenvPrimops` argument.

**Design.** Patch 0009 adds the pure primop `vendomatFromYAML name text`. It has 403 lines:
a new `yaml_subset.rs` of 299 lines, 58 lines in `primops.rs`, 3 in `lib.rs`, and 1 in
`devenv/src/devenv/mod.rs`. It applies on top of patch 0008. A hand-written Rust parser accepts
maps, lists, and string scalars only. The catalog calls
`devenvPrimops.vendomatFromYAML "vendomat.yaml" (builtins.readFile p)`, guarded by
`builtins.pathExists p`. The eval cache tracks `readFile` and `pathExists`, and the primop reads
no file, so no input is hidden. The patch is in
[fixtures/p2g/](fixtures/p2g/0009-vendomat-add-the-vendomatFromYAML-primop.patch).

| Check | Result with no unsafe Nix setting |
| --- | --- |
| Edit detection | Passed: value, same size with restored mtime, added key, delete, restore |
| Direct `devenv shell` and `devenv test` | Passed |
| Fresh git clone | Passed |
| direnv `use devenv` | Passed (an interactive hook was not tested) |
| Testee 0.6.1 | Passed: GREEN, RED, GREEN, no false green |
| Traps | `3.10` and `name: no` stay text; `enable: no` and `enable: yes` are rejected |
| Parser match | The Rust parser matched the P2F Python parser on 27 of 27 case files |
| Unsafe setting | `allow-unsafe-native-code-during-evaluation = false` in every run |

**Errors.** A syntax error is the last line of a trace of about 238 lines, for example
`vendomat.yaml:4:1: tabs are not accepted; use spaces`. Testee shows that line on one line. A
type error names the file and field and has no line number.

**Catch.** The PATH that Testee inherits on this host puts stock devenv first. Stock devenv fails
with `attribute 'vendomatFromYAML' missing`. The host must put the fork first on that PATH.

**Cost.** Maintenance is low to medium. The new file cannot conflict. The `primops.rs` block and
the plugin line in `mod.rs` may need a rebase. The Nix bindings API can move with a Nix bump.

**Conclusion.** YAML through the fork primop works on every entry point that P2F tested, and it
needs no unsafe setting. It replaces TOML, supersedes S36, and returns the user file to the
2026-10-11 name `vendomat.yaml`. Slice 1 must carry patch 0009 in the fork series.

Not proved: Rust unit tests, a release build, the real catalog, a NixOS machine entry,
interactive direnv, very large or symlinked files, and a concurrent edit.

## Format discussion and repository fixtures

The first pass assumed that a YAML parser outside Nix needs a committed parsed copy and a guard.
The owner disagreed. The owner was right: a parser does not cause drift; a *stored* parsed copy
does. Vendomat may constrain its workflow, so the parser may live anywhere if no parsed copy is
stored. P2F then showed that a hand-off by environment variable or by file fails under Testee,
direnv, or a direct devenv call. P2G moved the parser into the fork as a pure function on text
that Nix reads itself. The owner accepted that shape (R1).

Small fixtures from this pass are in the repository under `fixtures/`: `p2g/workspace/` (the
prototype catalog module and workspace files), `p2g/cases/` (27 strict-subset case files), the
patch `p2g/0009-...patch`, `p2b/` (the parse-once catalog and its TOML cases), and `p2e/test.nix`
(the self-keyed cache VM test). Raw logs and larger fixtures stay under
`~/.local/state/vendomat/p20/2026-10-12/`.

## Handoff

- **Changed.** `CONCEPT.md` is rewritten around the five-sentence model. `REQUIREMENTS.md`
  supersedes `DOOR-060` and `DOOR-064` to `DOOR-068` with `DOOR-069` to `DOOR-073`.
  `DECISIONS.md` adds S27 to S35. `PLAN.md` has three slices and a release.
- **Cut.** Named `test` and `build`, the `vendomat devenv` prefix, the update edit protocol, the
  Vendomat-side catalog check, the failed-unit refusal, cache key placement and its path unit,
  the "settings" catalog kind, and the hand-migration table.
- **Moved to the advanced door.** Remote install and deploy, the installer and admin keys, and
  the host-key re-pin.
- **Owner rulings needed.** Q1 to Q4 above (Q1 restated after P2G). O5, O7, and O9 stay open.
- **Next session.** Record the owner's rulings. Then start slice 1 in [PLAN.md](../PLAN.md) from
  the P2A, P2B, and P2C fixtures.

## Limits

- No implementation, consumer, Basix ISO, local apply, or two-machine run exists.
- P2B tested five commands. A `build` of an attribute that reads no mapped value was not tested.
- P2C did not test a bumped nixpkgs inside the release, a cold store, or a force-pushed branch.
- P2D is reading plus an eval-only fixture. The local installer and `nixos-rebuild --store-path`
  with the fork's machine output are unproved.
- P2E ran one VM. It did not prove a second machine, a real network, a reboot, or the timeout.

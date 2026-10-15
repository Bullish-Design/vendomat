# Current project

**Updated:** 2026-10-14. This file names the active project. `AGENTS.md` holds durable rules and
points here. When the active project changes, change this file and not `AGENTS.md`.

## Active estate design draft: project 22 — the owner's estate

On 2026-10-13 the owner asked for a canonical way to use the personal tool family and for the best
structure of nix-meta, aligned with project 21. The [concept](projects/22-owner-estate/CONCEPT.md)
divides the estate into four layers: machine (nix-systems, devenv Machines), home (nix-meta,
standalone Home Manager, which carries the personal tools), overlay (`~/.config/devman`), and
project (tracked facts only). No project repository pins a personal tool. The
[decisions](projects/22-owner-estate/DECISIONS.md) hold owner rulings R1 to R14 (R8 to R12 rule A1
to A4) and recommendations A1 to A11. The [open items](projects/22-owner-estate/OPEN-ITEMS.md)
list every question that still needs a ruling. The [plan](projects/22-owner-estate/PLAN.md) names the next work (W2 to W8). A draft
[ledger](projects/22-owner-estate/REQUIREMENTS-DRAFT.md) uses the prefix `ESTATE-`.

Spikes W1 and W9 found that devenv 2.4.0's evaluation cache does not track an import whose final
path component is a symlink into the store. Today's system-path import of devman's link module is
such an import, so it can stay stale. A changed directory symlink is caught only by accident. Owner
ruling R12 therefore imports the home's devenv modules through one real pointer file that Home
Manager activation rewrites. W10 proved the pointer on devenv 2.4.0, and owner ruling R14 makes its
path an option, reached through one shared overlay file. W5 built a read-only fleet doctor prototype
and a baseline: Testee is the remaining repository pin (22 repositories), and every repository
still imports devman's link module in the form devenv cannot track.

No production code, consumer, or machine changed. Project 22 states where each part of the estate
lives. Project 21 stays the authority for the Vendomat and Basix products. Project 21 answered
project 22's three proposals with R33 (pin layout), R35 (homes outside Vendomat), and R36 (no
host-side module). Project 22 ruling R13 puts the patched devenv binary and the `vendomat` launcher
in the machine layer.

## Implementation: projects 23 and 24 (run in parallel)

Two sessions implement the project 21 design. Each starts from its kickoff file. Project 21 stays
the design authority and holds the slice evidence.

- [Project 23](projects/23-vendomat-fork-and-binary/KICKOFF.md): S1, the module-only devenv fork
  (tag `v2.4.0-vendomat-modules.1`, R44), and S2, the host devenv binary (no Attic, R39). Both are
  complete; the owner switched the host on 2026-10-14 (R48).
- [Project 24](projects/24-vendomat-catalog-and-machines/KICKOFF.md): S3, the catalog, template,
  commands, and Harmonia sharing module, and S4, `vendomat apply` and `vendomat rollback`, proved
  in VMs. Done; v0.8.0 is published. See [REPORT](projects/24-vendomat-catalog-and-machines/REPORT.md).

Each kickoff lists the files its session owns.

**Project 24 state, 2026-10-14.** S3 and S4 are done and on `main`. Vendomat v0.8.0 is published on
`release` at `e5923a8f` (tag `v0.8.0`; owner approval in session). The repository runs Testee 0.8 tasks
since `bd7baeb06b1a`. The fixtures ran on the published S1 tag. Report:
[REPORT](projects/24-vendomat-catalog-and-machines/REPORT.md). Evidence:
[S3-CATALOG](projects/21-vendomat-basix-split/evidence/S3-CATALOG.md) and
[S4-APPLY-ROLLBACK](projects/21-vendomat-basix-split/evidence/S4-APPLY-ROLLBACK.md). The opt-in
checks are `opt:NAME` tasks in `nix/tasks.nix`.

**Release v0.9.0, 2026-10-15.** Vendomat v0.9.0 is published: tag `v0.9.0` and `release` are at `9b8885e3`
(owner approval in session). It adds the catalog key `trustedInterfaces` (R52, `VMT-173`) and the project 21
contracts (R49 to R51). Evidence: [RELEASE-0.9.0](projects/21-vendomat-basix-split/evidence/RELEASE-0.9.0.md).

**R60, 2026-10-15.** The catalog key `settings: MODULE: FIELD: text` (R60, `VMT-183`) is in release v0.10.0 (below).
It maps to `vendomat.settings.MODULE.FIELD`. The authored module declares its options and converts text itself.
Evidence: [R60-SETTINGS](projects/21-vendomat-basix-split/evidence/R60-SETTINGS.md).

**Release v0.10.0, 2026-10-15.** Vendomat v0.10.0 is published: tag `v0.10.0` and `release` are at `c6b36c1e` (owner approval in session). It adds R55 (whole-commit `apply` and `rollback`), R60 (`settings`), and the end of the `vendomat.toml` flow (S8 step 3). vendomat-demo pins it (`bb6bad05`). Evidence: [RELEASE-0.10.0](projects/21-vendomat-basix-split/evidence/RELEASE-0.10.0.md).

**Patch 0003 fix, 2026-10-15.** The offline entry failed when the store lacked a locked input's path and two inputs shared one source (`VMT-184`). The fix is in `0003.patch`; new binary `s3x37wa0x8y3c9wkkzjbgpk44z2sgbx5-devenv-2.4.0`. Evidence: [P0003-MISSING-PATH](projects/21-vendomat-basix-split/evidence/P0003-MISSING-PATH.md).

## Final design: project 21 — Vendomat and Basix, separated

**Current status, 2026-10-14.** R39 (2026-10-13): the new system configures no Attic;
every installed machine runs Harmonia from first boot. R40 to R45 settle the implementation
decisions D1, D2, D4, D6, D7, and D8. Project 21 is the design authority for Vendomat and Basix.
S1 to S4 are complete on Vendomat `main`; v0.8.0 is published on `release` at `e5923a8f`, and the
S2 host switch is complete under R48. S6 retired the old binary fork. Do not restart those slices.
Project 21 is the implementation contract (2026-10-15, S8 step 4). Project 14 is history.
The `p21-contracts` work is on `main`. It resolves the Basix requests VR1 to VR4, VR6, and VR7 and
adds rulings R49 to R51. VR5 is not done: Basix keeps its own hint. No release carries this work yet.
Its evidence is [VR contract resolutions](projects/21-vendomat-basix-split/evidence/VR-CONTRACT-RESOLUTIONS-2026-10-14.md).

S1 is done (2026-10-14): tag `v2.4.0-vendomat-modules.1` (commit 061c2184) is published at `git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules`, and Vendomat's flake has it as input `devenv` ([evidence](projects/21-vendomat-basix-split/evidence/S1-MODULE-FORK.md)).

S2 is built (2026-10-14): Vendomat's flake output `packages.x86_64-linux.devenv` is `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0` (NAR hash `sha256-ef9WVFzW+JIst6xnUUi+42MCv1ePgF2/ksi7juhWmn4=`), kept under a GC root in `~/.local/state/vendomat/roots/`. The host runs it since 2026-10-14 (R48): nix-meta `main` `cf8ef3cc` installs it, and the owner switched `server` ([evidence](projects/21-vendomat-basix-split/evidence/S2-HOST-BINARY.md)).

S8 step 1 is done (2026-10-15): vendomat-demo (`main` `85e6c725`) and nix-systems (`main` `9419924d`) run on `vendomat.yaml` and the S3 template; the VM checks of nix-systems pass. Step 3 is done (below); step 2 waits for project 22 and the V4 backlog; see [S8-CONSUMERS](projects/21-vendomat-basix-split/evidence/S8-CONSUMERS.md).

S8 steps 3 and 4 are done (2026-10-15). `main` no longer holds the `vendomat.toml` flow: the commands `sync`, `path`, `check`, `bump`, and `machine`, their modules, `direnv/`, `preflight/`, the V6 devenv module and its output `devenvModules.default`, and two templates. `VMT-123` is done: no host-side module output exists. R40's condition is met and its effect is done, except `push`: `push.py` stays until `VMT-120` passes. Step 2 (nix-meta's old module import) waits for project 22 and the V4 backlog. Evidence: [S8-REMOVAL](projects/21-vendomat-basix-split/evidence/S8-REMOVAL.md).

S5, the Vendomat side: steps 1 and 2 are done (2026-10-14). The collection hook accepts the `release` branch in every repository (R37, `VMT-171`), and `devenv/parse.nix` imports with a plain file name (R38, `VMT-164`). Step 3, the Basix fixtures, runs from the Basix repository. The live hooks under `~/vendor/` are not updated, and `~/vendor/basix` does not exist (owner gate). The evidence is [S5-BASIX](projects/21-vendomat-basix-split/evidence/S5-BASIX.md).

S6 is done (2026-10-14): the `v2.4.0-vendomat.4` binary fork series, its fixtures, and patches 0001, 0002, 0004, and 0006 to 0009 are gone from `devenv-dist/`; the S1 module series and the S2 binary patches stay ([evidence](projects/21-vendomat-basix-split/evidence/S6-FORK-RETIRED.md)).

**Basix now lives in `~/Documents/Projects/basix`** (moved 2026-10-13). Its design, the `BSX-` ledger, and
its plan are in that repository, under `.scratch/projects/001-initial-concept/`. The project 21 files here keep
stub rows and pointers.

On 2026-10-12 the owner opened a clean-slate review of the project 20 design and asked for Basix in
its own repository. The [concept](projects/21-vendomat-basix-split/CONCEPT.md) states the result.
The [decisions](projects/21-vendomat-basix-split/DECISIONS.md) hold owner rulings R1 to R36. Every
recommendation A1 to A14 has a ruling. The
[requirement ledger](projects/21-vendomat-basix-split/REQUIREMENTS.md) uses the prefixes `VMT-` and
`BSX-`. Its rows carry their rulings and mark the open gaps.

Main changes from project 20: Basix gets its own repository; `vendomat.yaml` is parsed by a parser
written in Nix (no fork primop); the grammar allows tabs, lists of maps, and nested lists; languages
use standard devenv modules with uv for Python; native devenv files stay as a visible escape hatch;
machines use devenv Machines with a local `apply` and a local install from the Basix ISO. Vendomat
opens no upstream pull request for its devenv patches (R34), so the module-only fork and the patched
host binary are long-lived.

The Basix B2 and B3 console-install and disk-guard spike evidence is committed on a Basix feature
branch. Those disposable VM results are not B5 product integration or S7 hardware proof. The next
product work is S5/B5 integration; S7 and any physical-disk write still require the applicable
owner approval. W1 to W10 are historical design spikes, not the current implementation status. S3
resolved the catalog issues recorded in its evidence, and S4 implemented apply and rollback. Current
contract spikes and their limits are recorded separately; fixtures and disposable VMs do not
establish a real-machine or physical-disk proof. Remaining ledger gaps are listed by ID in the ledger.

Where project 21 and project 20 disagree, project 21 states the future design. Project 20 stays the
record of slice 1. One owner gate stands: any real disk write. The host switch is done (R48). Real
hardware and the two-machine Harmonia check are unproved (S7).

## Earlier future design: project 20 — Vendomat as the front door

The owner chose [project 20](projects/20-vendomat-front-door/CONCEPT.md) on 2026-10-11 as the
future design. The [decision log](projects/20-vendomat-front-door/DECISIONS.md) records the switch.
Its [requirement ledger](projects/20-vendomat-front-door/REQUIREMENTS.md) preserves the first
draft's IDs. Its [plan](projects/20-vendomat-front-door/PLAN.md) names the proof gates.
Vendomat becomes the user command. The 2026-10-12 second simplification
pass proposes one user file (`vendomat.yaml`, read by a catalog module through a fork primop),
three verbs plus pass-through to the pinned fork, a local Basix install from an
ISO, and a serving machine that makes its own signing key. Native devenv remains
the advanced door. The owner accepted the four grouped questions on 2026-10-12.
A fresh Basix core still must boot without keys.

The current CLI and live consumers still use the project 14 workflow. Project 14 remains the
current implementation contract, but no longer directs future design. Slice 1 is complete: the
required Testee profile, front-door consumer gate, full end-to-end gate, and published-channel
smoke pass. The collection serves fork tag `v2.4.0-vendomat.4` and Vendomat branch `release`.
A fresh workspace locked the branch to Vendomat `d3c279e0` and entered the catalog shell. The host
PATH still puts stock devenv first, so the smoke used the `.4` fork explicitly. No host profile
switch or Basix machine gate has run. The owner has not authorized real disk writes.

**Authority split.** The project 20 documents are the future design authority, except where project
21 revises them. Project 14 stays the
current implementation contract until a release supports the project 20 gates.

**State on 2026-10-11 (research session).** Spikes ran on the pinned tools (fork devenv
`v2.4.0-vendomat.3`). Each passed at fixture level only; see the
[research report](projects/20-vendomat-front-door/evidence/RESEARCH-2026-10-11.md).

- S1: a strict YAML grammar and canonical JSON passed the 53 accept and 115 reject corpus.
- S2: the native merge matrix passed on the fork; generated data stay plain definitions.
- S3: a neutral schema export, a cache key, and a warm offline store passed.
- S4: the Basix machine inventory evaluated, and the disk guards fired. No machine was activated.
- S5: the guard, committed `.vendomat/`, launcher protocol, pass-through, and direnv hook passed in prototypes.
- S6: a two-VM Harmonia run passed a keyless boot, a cold substitution, and release roots. It also
  showed that a down cache blocks a build under default Nix settings.
- S7: a keyless core, a post-boot secret route, a fresh install to a separate VM, and an adoption
  without disk writes passed on fixtures.
- S9: native `follows` passed 19 cases and 2 stock-devenv control runs.

No implementation, consumer migration, machine deployment, or real disk write happened.
The VM spikes drove btrfs unallocated space on `/` to 93 MiB. On 2026-10-12 the owner cleaned and
balanced the disk (23.09 GiB unallocated, metadata 71.6 %), so VM work may resume.

**Simplification review (2026-10-12).** The
[review](projects/20-vendomat-front-door/evidence/SIMPLIFY-REVIEW-2026-10-12.md)
proposes direct data (first TOML, now YAML), a bounded Vendomat catalog, no generated
`.vendomat/`, one fresh Basix machine type, and optional signed output sharing.
Vendomat owns the routine workflow; native devenv files are an advanced door. The
[concept](projects/20-vendomat-front-door/CONCEPT.md),
[requirements](projects/20-vendomat-front-door/REQUIREMENTS.md),
[decisions](projects/20-vendomat-front-door/DECISIONS.md), and
[plan](projects/20-vendomat-front-door/PLAN.md) record the proposal. An isolated
Nix fixture proved direct file reading and file-level type errors. It did not
prove eager validation or a pinned-devenv workspace. No production code or
consumer changed. The owner still needs to rule on the user file format (now Q1, YAML) and on closing the V5 and V6 ledgers as history. The next session starts
with the pinned-fork direct-read fixture, not the strict YAML reader.

**Owner rulings (2026-10-12).** The owner accepted Q1 to Q4: YAML through the fork primop,
a local Basix install from the ISO, deferral of user source modes and mirrors, and closing the V5
and V6 ledgers as history at cutover. R5 permits the existing collection to serve the Vendomat
`release` branch. The [decision log](projects/20-vendomat-front-door/DECISIONS.md) records R1 to R5.
No gate had passed when these rulings were recorded. The next session starts slice 1 of the
[plan](projects/20-vendomat-front-door/PLAN.md) with the prompt
[KICKOFF-SLICE-1.md](projects/20-vendomat-front-door/KICKOFF-SLICE-1.md). The sentences below that say the owner must
still rule are history.

**Second simplification pass (2026-10-12).** The
[second review](projects/20-vendomat-front-door/evidence/SIMPLIFY-REVIEW-2026-10-12-PASS2.md)
ran five spikes (P2A to P2E; P2F followed) on the pinned fork and one VM, and audited the
documents. It proved, at fixture level: a direct read with no stale eval cache,
one parse step that stops every tested command, update as a native lock update
of a `release` branch, and a self-made cache signing key. It found that the fork
installs only over SSH, so the learner path becomes a local ISO install. It
supersedes `DOOR-060` and `DOOR-064` to `DOOR-068` with `DOOR-069` to `DOOR-073`
and adds decisions S27 to S35. The owner must rule on Q1 to Q4: YAML through the fork
primop, local install, deferring the source collection, and closing the V5 and V6
ledgers at cutover. The next session records those rulings, then starts slice 1. A sixth spike
([P2F](projects/20-vendomat-front-door/evidence/P2F-yaml-handoff.md)) showed that no
hand-off of parsed YAML to Nix works on every entry point without a machine-wide unsafe Nix
setting. Decision S36 kept TOML for the first release, pending a fork patch.

**YAML through a fork primop (2026-10-12).** The seventh spike
([P2G](projects/20-vendomat-front-door/evidence/P2G-fork-yaml.md)) tested that patch. Patch 0009
adds the primop `vendomatFromYAML` to the fork. The catalog reads `vendomat.yaml` with
`builtins.readFile` and parses it with the primop. It passed edit detection, direct devenv, a
fresh clone, direnv, and Testee with no unsafe Nix setting. Decision S37 supersedes S36, and
`DOOR-074` and `DOOR-075` supersede `DOOR-069` and `DOOR-070`. Q1 now reads: confirm YAML through
the fork primop (`vendomat.yaml`) in place of TOML. The host must put the fork first on the PATH
that Testee inherits. Slice 1 later passed the Rust unit tests, built the fork, and ran the real
catalog module through a host-created workspace, a local Git release channel, direnv, and Testee.
The final published-channel smoke also passed against `git://server/vendomat?ref=release`. The fork
tag and release branch are published. No Basix machine gate has passed. The later slice 1 tests are
recorded in `projects/20-vendomat-front-door/evidence/slice-1/`.

## Earlier draft and evidence: project 16 — Vendomat V6, the devenv layer

`.scratch/projects/16-vendomat-devenv-layer/`: `CONCEPT-V6.md`, `SPEC-V6.md`, `GUIDE-V6.md`,
`CONCEPT-UPDATE-2026-10-10.md`, `LEDGER-V6.md` (generated),
`CUTOVER-REVIEW.md` (the Step 9 package, DRAFT), and
`RESEARCH-2026-10-09-MACHINE-PATHS.md`. Gate records: `evidence/GATES.md`.

Every workspace imports a pinned Vendomat devenv module. `vendomat sync` writes a `.vendomat/`
fragment. One patched devenv (`devenv-dist/`) runs everywhere. The `nix-systems` repository
(`Bullish-Design/nix-systems`, private) holds the machine roles: `server` is installed fresh on the
4 TB drive, then `framework` is adopted in place without a disk install.

**State on 2026-10-10.** Gates G0 to G4, G6, and G7 pass for their recorded interfaces (G7 in
QEMU). The revised no-Nix workspace gate G3A passes in a template-created local consumer
([evidence](projects/16-vendomat-devenv-layer/evidence/step-3a.md)). G1, G5, G8, and G9 are
BLOCKED by named items: cold substitution on another host or VM (the same-host live Attic proof
passed; see [evidence](projects/16-vendomat-devenv-layer/evidence/live-release-2026-10-10.md)), PV-09 (the
installer's pull credential), V4 removal in repositories that hold open work, `agentman`, and the
privileged scan with the `nixos-facter` report (they need root). S7 of project 20 found that G7 is not a keyless proof (it carried `install.secrets`, `extraFiles`, `copyHostKeys`, and one failed unit). No real disk, firmware entry, or boot
order changed. `CUTOVER-REVIEW.md` holds the verdict, the read-only facts, the built closure, and every
proposed command marked NOT RUN. The patched devenv is the fork `v2.4.0-vendomat.3`, published to the collection on 2026-10-11 (the review above still names `.2`).

The live cache checks `testee check live-cache` and `live-cache-load` (`CACHE-012`) pass on
`server`. The original 64 MiB runs needed a second push attempt and showed server pool timeouts.
After an approved Attic chunk change, one small and three 64 MiB checks passed with zero retries.
The owner then restored the original chunks and applied a patched Attic with configurable database
pool keys and a 60 s wait, then four database connections. The same four checks passed again each
time with zero retries. The timeouts' cause remains not established
([evidence](projects/16-vendomat-devenv-layer/evidence/live-cache.md)).

The 2026-10-10 concept revision makes no-Nix workspace use the first user goal. Module authors
may write native Nix. The existing description builder remains fixture evidence, but the revised
draft no longer requires it. Machine operator coverage follows this workspace proof.

The private `Bullish-Design/vendomat-demo` repository is the reusable live consumer. Its first
run passed two selected modules, inherited inputs, TOML setting changes, shell entry, and the
unselected-source check ([evidence](projects/16-vendomat-devenv-layer/evidence/demo-consumer.md)).
It found and led to fixes for `dir=` source discovery and a lock update with two changed inputs.
It uses stock devenv and a Vendomat module snapshot; it does not close the patched-fork or fleet
gate.

**Vendomat inside devenv (2026-10-10).** Spikes showed that `vendomat sync` must stay the one step
before shell entry ([evidence](projects/16-vendomat-devenv-layer/evidence/wrapper-spikes-2026-10-10.md)).
The shell now carries the pinned `vendomat` and runs `check` and `push` as tasks; the host launcher
serves `sync` only inside a workspace (`DEL-020`, `VMOD-020`, `VMOD-021`). Upstream PR
cachix/devenv#3055 does not cover the need on 2.4.0, so the fork carries it. Fork `v2.4.0-vendomat.3`
(published in the collection) adds input inheritance (patch 0007, `DVN-011`) and fixes a cold first
entry that fails on `.2` (patch 0008, `DVN-012`)
([evidence](projects/16-vendomat-devenv-layer/evidence/fork-3-inheritance.md)).

Project 20 replaces this draft as the future design. The V6 records remain evidence. V5 and V6
requirement IDs still need dispositions in the project 20 successor specification. Do not edit or
renumber their original claims.

## Draft concept: project 17 — typed models for devenv modules

`.scratch/projects/17-devenv-model-layer/`: `CONCEPT.md`, `GUIDE-HARNESS.md`, and `evidence/`
(`GATES.md` and one record per step). Pydantic models are generated from native option
declarations and checked by a round-trip harness against Nix evaluation. The harness exists in
`devenv-py` (private, `Bullish-Design/devenv-py`, pin `devenv-2.4.0-b904dcb5-c2f38fe7`, `main`
`4f3033bdaa9c`). Steps 1 to 16 are done, and gates GM0 to GM10 pass (GM0 and GM6 keep named open
items). Final record on 2026-10-11: GM9 passes for five supported subtrees under two seeds
(`languages.python` 24 real fixtures, `services.postgres` 10, `languages.javascript` 7,
`languages.rust` 10, and `services.redis` as supported generated-only with 1). GM10 passes on
`languages.javascript`: a fresh agent used the skills alone and changed no harness file. The records
are `evidence/step-15-final.md` and `evidence/step-16-final.md`; the requirements MDL-030 to
MDL-042 hold the new rules (two-tier corpus, path-limit exceptions, named exclusion classes, golden
fixtures outside the corpus metrics, seed determinism, renamed options, package identity by
`$name`). Open items: Templateer `main` has no release tag; the `pytest-focus` targets file is
shared across checkouts; the end-to-end `VENDOMAT_TEMPLATEER` default is machine-specific; the
Devman push hook resolves `testee` from the session `PATH`, so a session from an old shell carries
Testee 0.5.1. The project does not change the authority of project 14 or project 16.

## History: project 14 — Vendomat V5 (and project 16, V6)

Project 14 was the implementation contract until 2026-10-15. Project 21 replaced it (S8 step 4).
The V5 and V6 ledgers (`SPEC-V5.md`, the project 16 ledger) are now history: the rows stay as
written, and project 20 R4 already ruled that they do not bind new work. The code of the
`vendomat.toml` flow is gone from `main` (S8 step 3, 2026-10-15); it stays in Git history. Project
14's long state of 2026-10-08, with its owner decisions and blockers, is in
[STATE-2026-10-08](projects/14-vendomat-local/STATE-2026-10-08.md). Its authority documents stay in
`.scratch/projects/14-vendomat-local/`.

## V4 removal backlog (outside the `vendomat` repository)

The owner ruled on 2026-10-09: V4 stays nowhere, V5 gives no backward compatibility, and the rest of
the system is aligned to V5. `vendomat` `main` is purged ([PV-26](projects/14-vendomat-local/prelim-verification/results/PV-26.md)).
The `nix-meta` pin keeps the old code alive on the machine until the items below are done. Each item
names its V5 answer. None keeps V4 behavior.

| # | V4 leftover | V5 answer | Needs first |
| --- | --- | --- | --- |
| 1 | `nix-meta` pins `vendomat` at `d5a90f0`. `profiles/developer.nix:16` takes the login-shell tools from `repoman-toolchain-core`. `machines/server.nix:68` imports `nixosModules.default`, which installs the CLI and the V4 consumer module | Each tool is its own flake input of `nix-meta`, listed in its registry and enabled in the host TOML. A host delta installs `packages.<system>.vendomat` only. Repin to 0.6.0 or later | Items 2 and 3 |
| 2 | `gitman`, `copyroom`, `docman`, `templateer`, `agentman`, `pyjutsu` have no `flake.nix`. The old `vendomat` flake built them with a shared uv2nix builder | Each tool authors its own flake (`packages.<system>.default`, and a module through `mkModules` when it has one). The uv2nix builder becomes a Python core input that exports `lib` (the `nvim-core` pattern), outside `vendomat`. Compare each build with today's (`BOOT-010`). `pyjutsu` exports its own wheel. Only `copyroom` depends on `pyjutsu` (checked in `pyproject.toml` and `uv.lock` of 17 repositories), so the wheelhouse is nearly unused | The Python core |
| 3 | **The critical path.** `repoman`'s module requires `REPOMAN_TOOLCHAIN_BIN` (`modules/devenv.nix` fails with "import the vendomat toolchain module"). Its manager modules (`gitman`, `docman`, `copyroom`, and others) run `"${cfg.toolchainBin}"/<tool>`. `repoman-sync.sh` reads the toolchain manifest at `$REPOMAN_TOOLCHAIN_BIN/../share/vendomat/toolchain.json`. Only the V4 module sets these | `repoman` runs its managers by name from the host `PATH`, and needs no Vendomat manifest. The host puts the tools on `PATH` (item 1 today; item 2 later). The login shell has them on `PATH` now | A `repoman` change, tagged and repinned in `nix-meta`, then the owner switches |
| 4 | Eleven central overlays import the V4 consumer module: `eventic`, `llgym`, `loci-core`, `argentic`, `poddantic`, `flora`, `loci.nvim`, `flora-qc`, `shellij`, `nix-secrets`, `pyllij`. Removing the import now breaks every `repoman` task in these repositories (item 3) | Remove the import line. Keep the `devman` link lines. A project that needs a native wheel lists the owning repository as an input | **Item 3** |
| 5 | V4-format `vendomat.toml` files. **Done 2026-10-09 in four clean repositories:** `argentic`, `eventic`, `shellij`, `flora` (they held only `[vendor.publish] enable = false`, so the shell is unchanged; the no-file path of the V4 module was tested in a throwaway project). **Left:** `flora-core` and `nix-nvim` (`[toolchain] enable = false` opts out of the closure, so deleting the file turns it on until item 4), `repoman` (a stale `[vendor] libs = ["pyjutsu"]` and `mode = "editable"`), and `loci-core`, `loci.nvim`, `poddantic`, `pyllij`, which hold other work in progress (open lanes, unbookmarked work, or an unpushed commit) | Delete each. A repository gets a V5 `vendomat.toml` only when it becomes a flake-backed project or author | The owners of the open work, and item 4 for `flora-core` and `nix-nvim` |
| 6 | `linkman` declares `vendomat` as a devenv input at `v0.4.3`, and its `devenv.nix` takes `REPOMAN_TOOLCHAIN_BIN` from `inputs.vendomat.packages.<system>.repoman-toolchain-core` | Remove the input and the `vendomat/modules` import | **Item 3** |
| 7 | The machine plane. The Dagu service on `server` reads its registry from `~/.local/state/vendomat/devman/active` (generation 4), set in `nix-meta` `profiles/devman.nix` | Not part of V5. NixOS generations give the atomic switch and the rollback. `devman`'s flake supplies the renderer, Dagu, and the runtime, and already validates workflows in a Nix check. `devman` exports a function that renders a registry from project inputs; `nix-meta` sets `registryDir` to that store path. Workflows then follow released tags. A local checkout uses an explicit input override. Until then the live Dagu keeps reading generation 4, which is immutable | A `devman` change |
| 8 | Documents that name V4 commands: `repoman` README and changelog, `devman/USER.md` section 2.7, `mancore/CONCEPT.md`, `pyjutsu/nix/pyjutsu.nix` | Rewrite to V5 | Items 1 and 7 |
| 9 | `.scratch/projects/09-*` to `13-*`, which the V5 documents cite by name | Remove after the citations are inlined or dropped | Last |

Item 2 has no requirement IDs yet: the V5 documents name a Python core and do not specify it.

## Superseded

`.scratch/projects/09-*` through `13-*` and the `docs/V4_*.md` records are closed history. They
hold observations that the active documents cite by name. Do not read them for direction, and do
not follow any programme, gate, or requirement ID defined in them. Each closed directory carries
its own terminal note.

## Inherited facts that still hold

- `vendomat` `main` holds the project 21 code only (S8). The V4 and V5 code is in Git history and in the
  revision `nix-meta` still pins (`d5a90f0`). Nothing reads it for direction.
- Eleven central overlays, ten local-checkout overlays, and one flake-input consumer use the
  current paths. Every machine is reconfigured, so those paths are replaced. `BOOT-010` carries the
  one obligation: a converted input must produce the same result as the tree it replaces, or name
  the difference.
- `tests/fixtures/store-consumer/` is a real consumer fixture for the current pin.
- V5 logs go in `~/.local/state/vendomat/v5/<date>/`. Older logs sit beside it.

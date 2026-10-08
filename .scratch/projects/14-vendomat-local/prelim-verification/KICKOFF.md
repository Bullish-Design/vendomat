# V5 preliminary verification session record

**State:** run completed on 2026-10-08; V5 implementation remains blocked. Do not use this file as a new-session green light. Read [RESULTS.md](RESULTS.md) and [`../KICKOFF-V5.md`](../KICKOFF-V5.md) for current status.

Paste the text below the line into a new working session.

---

Perform the Vendomat V5 preliminary verification in
`/home/andrew/Documents/Projects/vendomat`.

## Objective

Resolve the design risks before V5 implementation begins. Run the spikes in
`.scratch/projects/14-vendomat-local/prelim-verification/SPIKES.md`. Record exact evidence for
each result. Repair the active design documents when evidence supports a change. End with a
clear implementation readiness decision and a list of remaining blockers.

Do not treat a design claim, an upstream document, or a unit test as a passed real-consumer,
cache, restore, installer, or machine proof.

## Read first

1. `AGENTS.md` and `.scratch/CURRENT.md`.
2. `.scratch/projects/14-vendomat-local/CONCEPT-V5.md`.
3. `.scratch/projects/14-vendomat-local/SPEC-V5.md`.
4. `.scratch/projects/14-vendomat-local/GUIDE-V5.md`.
5. `.scratch/projects/14-vendomat-local/REFINEMENT-2026-10-08.md`.
6. This directory's `README.md`, `SPIKES.md`, `EVIDENCE.md`, and `DECISIONS.md`.

The four parent documents are current authority. This directory proposes checks. Closed
projects and V4 documents are history, except where current authority cites an observation.

## Starting observations

As recorded on 2026-10-08, no V5 step has run. `server` is the active build host. The 4 TB
WD Blue target is a proposed new boot drive. Its stable hardware ID is
`nvme-eui.e8238fa6bf530001001b448b4fbe837d`. The current 512 GB system must remain bootable.
Kernel device names changed between observations, so never select hardware by `/dev/nvme*`.
Confirm every host fact again before using it.

The existing V5 guide is marked superseded for server bootstrap. Its Step 0 script does not
prove every `DISK-*` claim. Treat its commands as proposals. Do not use a `PREFLIGHT PASS` from
that script to justify a disk write.

## Work sequence

1. Inspect Gitman status and the active worktree. Start a named lane for the verification work.
   Include relevant active worktree changes under the repository working agreement.
2. Make an audit table for the active requirement IDs and the stale claims named in `SPIKES.md`.
   Preserve every ID. Mark a changed claim as superseded by a new ID.
3. Run independent, reversible spikes first. Use disposable fixtures under the raw-log directory
   or tracked fixture sources in this directory. Record all inputs and commands.
4. Run read-only checks on `server` for disk identity and cache access. A read-only result is
   evidence about the observed machine, not authorization for later disk work.
5. Use a virtual machine or disposable image for cold-store and installer tests. Name the exact
   image before writing it. Keep all physical disks untouched.
6. For each spike, write a result using `EVIDENCE.md`. Record failures and unavailable
   infrastructure as named blockers. Do not mark them passed.
7. Decide each open design question from the evidence. Ask the owner only for choices that the
   evidence cannot settle. Continue independent work while a choice is pending.
8. Update `CONCEPT-V5.md`, `SPEC-V5.md`, `GUIDE-V5.md`, `REFINEMENT-2026-10-08.md`,
   `.scratch/CURRENT.md`, and `KICKOFF-V5.md` where the final decisions require it. Search for
   duplicate claims before superseding an ID. Keep the documents consistent.
9. Run `devenv shell -- testee verify --mode quick`. Run the opt-in end-to-end command when a
   changed fixture affects the Nix module, toolchain, or consumer integration.
10. Record the final readiness result. Commit and push relevant work through Gitman.

## Hard limits

- Do not start V5 implementation steps 0 to 10 in this session.
- Do not partition or format a physical disk, switch a live system, install a machine, move
  Attic data, or change production cache retention.
- Do not run raw `git` or `jj`. Use Gitman for temporary repositories too.
- Do not call pytest, ruff, or ty directly. Use Testee for repository verification.
- Do not write a second dependency resolver or lock as part of a spike.
- Do not silently relax a requirement. Preserve its ID and add a new ID when superseding it.
- Do not claim that a warm store proves a cold consumer or installer path.

## Required final report

Report each spike as passed, failed, or blocked. Link its evidence record and raw log path.
List every changed requirement ID and the fixture that supports the new claim. State the
remaining limits for local source paths, transitive `nixpkgs`, private cache startup, and
retention. Say whether Step 0 can safely begin. Say whether any later implementation step
still needs a design decision.

## Continuation

Read [RESULTS.md](RESULTS.md) first. The main unresolved blockers are the target signature and
partition-table scan (PV-02) and the cold installer cache route (PV-09). No V5 implementation step
has run. Do not begin Step 0 until the physical scan passes and the guide has a reviewed
fail-closed preflight.

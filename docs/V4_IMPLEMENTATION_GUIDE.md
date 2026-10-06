# Vendomat V4 implementation guide

**Status:** P0 evidence recorded, gate blocked, 2026-10-06. No V4 phase gate has passed.
See the [P0 evidence record](V4_P0_PROOF.md). Do not start P1 until its listed host,
storage, and consumer-transition gaps are closed.

The reviewed [V4 concept](../.scratch/projects/10-vendomat-v4-adversarial-review/CONCEPT-V4.md),
[specification](../.scratch/projects/10-vendomat-v4-adversarial-review/V4-SPEC.md), and
[requirements](../.scratch/projects/10-vendomat-v4-adversarial-review/V4-REQUIREMENTS.md)
define the contract. The [adversarial review](../.scratch/projects/10-vendomat-v4-adversarial-review/V4-REVIEW.md)
names the proof risks. This guide orders the work and gives each step an observable check.
If a fixture disproves a proposed interface, revise the specification and this guide before
implementing a different interface. Preserve stable requirement IDs.

V4 keeps native declarations and locks as the selection authority. Vendomat adds source
inspection and evidence for checked publication. The first complete application proof is a
Neovim review command and editor interface. P1–P6 prove that application path. P7 separately
proves machine integration. P8 is one reviewed upgrade. P9–P10 require measured demand.

## How to run this guide

1. Create one Gitman lane for each reviewable phase or smaller contract. Record its base revision.
   **Verify:** `devenv shell -- gitman status` shows the intended lane and no unrelated work.
2. Before implementation, write the fixture inputs and the expected pass, failure, and gap results.
   **Verify:** Another reader can run each check without guessing a version, host, or selection.
3. For each step, save the native command, exit status, relevant output, selected revisions, and
   observed identities in a dated proof record. Keep large raw logs outside tracked documentation.
   **Verify:** The record links to preserved logs and separates observation from inference.
4. Run `devenv shell -- testee verify --mode quick` after repository code or documentation changes.
   Run `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` when the module, toolchain,
   or consumer integration changes. Run the relevant Nix build and real host fixture for affected
   native behavior. **Verify:** The phase record contains the results and names any skipped gate.
5. Do not advance past a failed phase gate. Fix the implementation or revise the contract with a
   recorded decision. **Verify:** The next phase cites a passing prior gate and the exact fixture.

The proof record for each step must name its requirement IDs, environment, commands, expected
result, actual result, artifacts, and conclusion. A test that only asserts implementation
details does not replace the named user-visible behavior. Proposed names and commands in the
V4 specification become instructions only after their fixture proves them.

## P0 — pin the environment and preserve current consumers

**Requirements:** `V4-OWN-009`, `V4-OWN-012`, `V4-MACH-001`, `V4-REC-009`.

1. Inventory the current Vendomat module, machine manifest, central overlay, input-based
   consumer, and real active consumers. Mark each path for preserve, migrate, or retire.
   **Verify:** Evaluate the current consumer fixture and at least one active example of each
   used delivery path. Record its effective Vendomat input, store paths, and working commands.
2. Select one desktop publisher, one cold laptop, one first-proof project, and one review-module
   repository. Record system architectures, Nix versions, network access, Attic endpoint,
   storage owners, backup destinations, and native cache fallback policy.
   **Verify:** Each host can reach only its intended endpoints. Each durable state class has a
   named owner and restore location. Record unavailable infrastructure as a P0 blocker.
3. Pin a devenv executable and matching module revision with Machines support. Keep the old
   consumer pin available during migration.
   **Verify:** Record both identities. On the new pin, evaluate a minimal machine fixture and
   create a native plan. A successful version query alone does not pass this step.
4. Re-run every current delivery fixture on the proposed pin. Record any changed option,
   module path, generated output, or host-delivered input. Choose and test a migration for
   each affected active consumer before retiring a path.
   **Verify:** Before and after results match the intended behavior. A failing consumer has a
   named migration and rollback path. No host store path affecting selection is hidden.
5. Run the current Testee gate and the existing opt-in consumer integration fixture. Save the
   baseline without changing V4 code.
   **Verify:** Record pass or failure for each check. A pre-existing failure has a reproducible
   command and does not get reported as a V4 regression.

**Gate:** A tested Machines pin and a complete consumer transition inventory exist. Host,
storage, backup, and fallback policies are explicit. Do not use current devenv 2.2 behavior
as evidence for Machines.

## P1 — prove one focused native module

**Requirements:** `V4-OWN-001–008`, `V4-OWN-010`, `V4-MOD-001–010`, `V4-CHK-013`,
`V4-MACH-002`, `V4-PROOF-001–002`.

1. Put one review implementation and a command with a documented result format in its owning
repository. Export project, NixOS, and Home Manager contributions as distinct native targets.
   **Verify:** Run the command on known input and parse the expected result. Evaluate each
   target alone. Confirm that project import does not activate system or user configuration.
2. Define typed options, enabled defaults, supported targets, required inputs, and default
   command and editor checks in the module contract.
   **Verify:** Evaluate defaults, invalid types, a missing required input, and an unsupported
   target. Each invalid case must fail with a diagnostic naming the cause.
3. Export a normal Neovim plugin contribution and a dedicated configured Neovim output. Both
   must invoke the same packaged review command by its selected path.
   **Verify:** Run the representative editor command in both forms. Put a conflicting binary
   first on `PATH`; both forms must still invoke the selected package.
4. Test independent overrides and composition conflicts. Disable the editor while retaining
   the command. Change one supported option. Compose a documented incompatible setting.
   **Verify:** The command still runs without the editor. The override changes only its intended
   output. The conflict fails with a named native diagnostic.
5. Run the module locally without a Vendomat service or Attic. Keep a normal editor profile
   active beside the dedicated output.
   **Verify:** Both editors keep their own settings. The command produces its expected result
   while Vendomat and Attic are unavailable.

**Gate:** The command and both editor forms work from one implementation. Native target,
default, override, conflict, and required-check contracts pass. This gate makes no machine
activation or publication claim.

## P2 — prove delivery and fresh local use

**Requirements:** `V4-OWN-013`, `V4-MOD-011–014`, `V4-SEL-001–002`, `V4-PROOF-003`.

1. Build two clean consumers: an ordinary devenv repository and a flake-backed repository.
   Export only the focused module, not the author's development shell.
   **Verify:** Evaluate and build both consumers. Add an author-only tool or process to the
   author shell; confirm neither consumer inherits it.
2. Determine the minimum native input contract for the ordinary consumer. Remove one required
   input and test the resulting diagnostic. Record the exact import path proven by the fixture.
   **Verify:** The complete consumer works. The incomplete consumer identifies the missing
   input. It does not rely on recursive import of the author's `devenv.yaml`.
3. Prove how a flake-backed export carries or explicitly passes its transitive inputs. Test the
   selected revision in a fresh consumer and record its effective lock graph.
   **Verify:** The consumer builds without undeclared local paths. Changing its lock changes
   only the native selection. A lock entry alone does not enable the module.
4. Test active profiles and a reversible local checkout override through both delivery paths.
   Compare two independent consumers before and after the override.
   **Verify:** The selection report names each effective path, profile, and override. Reverting
   the override restores the prior result. Consumer B's accepted lock does not change.
5. Deny Vendomat and Attic to a fresh local consumer. Permit only the native sources, public
   caches, and local builds allowed by the P0 fallback policy. Realize and run the command.
   **Verify:** A clean consumer obtains its needed native inputs and runs the selected command.
   Record any external source or cache used. Do not call this a fully offline rebuild.
6. Compare explicit native declarations with a small delivery helper only if repeated manual
   declarations cause a concrete failure in both consumers.
   **Verify:** A helper, if added, leaves native files and locks as the only selection authority.
   If it adds no measurable value, keep the explicit declarations.

**Gate:** Both delivery forms and a fresh local realization pass on the P0 pin. The tested
export, input, profile, and override behavior replaces proposed syntax in the specification.

## P3 — retain and inspect selected source

**Requirements:** `V4-SRC-001–009`, `V4-SRC-011–012`, `V4-SRC-014–017`,
`V4-SRC-019–025`, `V4-PROOF-004`.

1. Evaluate the first consumer's selected native inputs and selected output's direct package
   dependencies. Choose one identifiable entry from each graph. Add both to a reviewable
   consumer capture list, with the graph named for each entry.
   **Verify:** Resolve each entry to the native selected revision or archive hash. An unlisted
   dependency stays discoverable. A stale or unmatched entry reports a policy gap and cannot
   change the native lock. If either graph cannot be resolved, stop P3 and revise the proof.
2. Capture the selected owned module and the listed direct dependencies into durable storage.
   Keep one retained object and a small identity record for each selected source.
   **Verify:** Compare the declared revision or archive hash, content hash, and stored bytes.
   Record original locator, selecting context, storage path, and capture result.
3. Inspect native package metadata for patches, generated source, or other transformations.
   Label each view as exact selected source, selected source with packaging changes, upstream
   reference, or unresolved.
   **Verify:** Use one patched fixture and one unresolved fixture. A retained upstream tree
   cannot receive an exact installed-source label without matching evidence.
4. Expose a read-only tree and provenance record from project context. Keep lookup separate
   from native input selection and package execution.
   **Verify:** Open a selected file, inspect its source relationship, and compare consumer
   locks and output paths before and after lookup. They must remain unchanged.
5. Exercise missing, unavailable, disconnected, and mismatched inspection source cases.
   **Verify:** Reports distinguish identified but uncaptured, unavailable, unidentified, and
   client-unreachable states. A disconnected lookup does not mark retained source as lost.
   An inspection gap does not turn a valid artifact check into a failed check.
6. Test source durability independently of derived read views. Remove a view, run local Nix
   garbage collection in the fixture, and recreate the view from retained bytes.
   **Verify:** Hashes and identity records still match. The project and accepted command run
   without a mounted inspection tree. Measure retained bytes for the P6 storage report.

**Gate:** Both direct-dependency graphs resolve under the pinned tools. The first consumer can
read retained source with honest correspondence labels and explicit gaps. Source lookup never
changes native selection.

## P4 — bind checks to one frozen output

**Requirements:** `V4-SEL-003–009`, `V4-CHK-001–012`, `V4-CHK-014–016`, `V4-SRC-010`,
`V4-EVD-001–002`, `V4-EVD-004–006`, `V4-EVD-011`, `V4-PROOF-005`.

1. Freeze one immutable consumer revision, or one exact proposed diff against a recorded base.
   Record declarations, locks, output attribute, target system, active profiles, overrides,
   module sources, and effective host-delivered inputs.
   **Verify:** Re-evaluate the selection and compare every recorded input. A mutable path or
   changed host manifest prevents an immutable success claim unless its exact bytes were frozen.
2. Evaluate the selected derivation and required-check set. Merge default checks from enabled
   modules with consumer-added checks. Record each check's owner and input.
   **Verify:** Enable and disable one component and add one consumer check. The effective set
   changes as declared. An enabled module without its required-check declaration cannot pass.
3. Run declared pre-build checks, realize the exact output, and run artifact and integration
   checks against that output. Use devenv tasks for order and narrow helpers for validation.
   **Verify:** Instrument stage order. A failed pre-build check prevents build success. An
   artifact check supplied with a different output path fails identity validation.
4. Query and record the realized output path, derivation, Nix Archive (NAR) hash, references,
   and check logs. Recheck the frozen inputs before any upload.
   **Verify:** Change a lock, derivation, output path, host input, or output bytes after checks.
   Each drift fixture must reject publication success or require the affected check again.
   Supply wrong fixed-output source bytes; native validation must fail before publication.
5. Run three distinct check outcomes: a required check that runs and fails, a declared required
   check that is missing or unavailable, and an absent documented nonrequired check.
   **Verify:** The first two block success with different reasons. The third remains a visible
   coverage gap and may accompany success. A build failure has its own reason.
6. Preserve a receipt for the exact selection and useful failure logs for each failed stage.
   Link source coverage without making inspection gaps artifact failures.
   **Verify:** Compare receipt fields to native evaluation and check inputs. Inject a canary
   secret in the environment; neither receipt nor preserved logs may expose it.
7. Retry the same selection after partial work, then change one check input and retry again.
   **Verify:** Reuse requires matching recorded inputs and validated side effects. A changed
   input reruns its affected check. An existing output path alone cannot count as success.

**Gate:** Failed and missing required checks block publication success. A nonrequired gap
remains visible. The exact checked bytes and their selection can be reconstructed from evidence.

## P5 — publish and prove Attic consumption

**Requirements:** `V4-CACHE-001–015`, `V4-EVD-003`, `V4-EVD-007`, `V4-PROOF-006`.

1. Configure Attic, credentials, trusted key, and the consumer's native fallback policy on the
   P0 hosts. Keep push credentials outside tracked files, Nix outputs, and receipts.
   **Verify:** A read-only client cannot push. The publisher can push only under its intended
   scope. Record the effective substituter order and key accepted by the cold laptop.
2. Derive the selected application's runtime closure from the P4 output. Include at least one
   dependency that the build host first obtained from a public cache.
   **Verify:** Save the native closure path list and NAR metadata. Confirm that the public-cache
   dependency is in the expected list before testing Attic publication.
3. Push the selected output and its full runtime closure. Account for Attic's upstream filter
   when selecting push policy.
   **Verify:** A partial upload reports partial progress. A failed upload leaves the local output
   usable and produces no complete-publication receipt. A successful push command alone does
   not pass the closure gate.
4. In an isolated store, disable other substituters and builds. Obtain every required runtime
   path from Attic alone, including the public-cache dependency.
   **Verify:** Record a successful substitution for every path. Compare the served selected
   output's NAR hash with P4 and record closure-member metadata. Any absent member fails P5.
5. On the cold laptop, select the same immutable output and run the command and editor. Trace
   normal cache priority separately from the Attic-only proof.
   **Verify:** The laptop starts without the selected output, obtains the expected path from
   Attic, performs no build, and runs both interfaces. Logs identify the source of transfers.
6. Test local-store preference, Attic outage, public-cache fallback, and allowed local-build
   fallback as separate fixtures. Remove one published object after a passing check.
   **Verify:** Each case follows the P0 native policy without changing the consumer lock.
   Current availability changes in the report, while historical check results remain intact.

**Gate:** Attic alone serves every required runtime path with the checked output bytes. The
cold laptop runs the selected application, and normal fallback follows the declared policy.
This gate does not claim that a whole machine generation is cached.

## P6 — restore evidence and complete the application proof

**Requirements:** `V4-EVD-009–010`, `V4-REC-001–006`, `V4-REC-008`,
`V4-REC-010–012`, and the combined `V4-PROOF-001–006` gates.

1. Back up source objects and identity records, Attic objects and signing state, and receipts
   and failure logs as separate state classes.
   **Verify:** Record backup time, owner, restore target, and hashes or native identities for
   each class. A snapshot alone does not count as an off-host backup.
2. Restore source into a clean location and rebuild any derived view. Look up the selected
   module and dependency again.
   **Verify:** Restored bytes match their recorded hashes, provenance stays readable, and a
   damaged source backup fails only the source restore claim.
3. Restore Attic objects and signing state into a clean fixture. Use an existing trusted
   consumer to substitute the expected selected output.
   **Verify:** The consumer accepts the restored object under its existing trust policy. A
   missing signing state fails the cache restore claim without changing source status.
4. Restore receipts and failure logs. Recreate the P4 and P5 reports from preserved evidence.
   **Verify:** Prior check and upload outcomes remain explainable. A signed cache object does
   not set an independent-rebuild proof field. Cache availability and source correspondence
   remain distinct results.
5. Measure source storage growth, selected closure size, and transfer bytes with native
   queries. Confirm mutable application data stays outside immutable Nix outputs.
   **Verify:** Reported sizes match the native measurements. Writing application data leaves
   the selected output path and hash unchanged. No initial V4 operation deletes source or
   Attic objects automatically.
6. Run the whole P1–P5 path again from the recorded revisions. Run the normal Testee gate and
   the opt-in consumer fixture if Vendomat's integration code changed.
   **Verify:** The first-proof result includes command, editor, source, checks, Attic-only
   closure, cold laptop, and restore evidence. List each passed requirement and any gap.

**Gate:** P1–P6 establish the Neovim application, inspection, publication, and recovery path.
Do not claim machine readiness from this gate.

## P7 — prove native machine integration separately

**Requirements:** `V4-OWN-011`, `V4-MACH-003–015`, `V4-REC-013`, `V4-PROOF-009`.

1. Compose a native workstation fixture with one persistent NixOS service and a separate Home
   Manager role on the tested P0 Machines pin. Name its activation driver.
   **Verify:** Evaluate each native contribution. A system service candidate passes a native
   activation or virtual-machine check, including its declared health result.
2. Create a native plan and compare its selected outputs with the P4 checked paths. Link the
   plan ID and paths to Vendomat evidence without creating another plan or apply interface.
   **Verify:** Every linked path matches the native plan. A change in effective selection
   requires new evidence or a check whose recorded inputs still match.
3. Save a valid plan, block new builds, and apply it. Trace target transfers and native status.
   **Verify:** Apply uses saved outputs. Label direct build-host copy and Attic substitution
   from observed traffic; neither is inferred from a successful activation.
4. Make the plan stale by changing target state, then attempt apply. Prepare a new plan and
   alter one check input before retry.
   **Verify:** Machines rejects the stale plan. The changed check runs again. Inspect unknown
   or pending native status before another deployment attempt.
5. Inject a NixOS health failure after an application write. Separately fail Home Manager
   activation after NixOS succeeds. Exercise the native recovery paths.
   **Verify:** Report system, user, and application outcomes separately. A NixOS rollback does
   not claim to restore user files or application data. Record the driver-specific user result.
6. Inspect source, Attic, and evidence status after machine failures. Check the publication
   report for its scope.
   **Verify:** A cached application output does not imply a cached machine generation. The
   report keeps system, user, application, source, cache, and evidence outcomes distinct.

**Gate:** The pinned Machines fixture proves plan, transfer, activation, status, and recovery
limits. Only then may V4 documentation claim machine readiness.

## Release and current-consumer cutover

1. Compare the P0 inventory with every active consumer. Migrate one delivery path at a time
   and retain a tested rollback until its consumer passes on the new path.
   **Verify:** Re-run the before and after fixture for each path. Effective locks, host inputs,
   packages, and commands match the recorded intended selection.
2. Update public README, module examples, and project instructions to describe only proven
   interfaces. Mark any surviving old face and its support boundary explicitly.
   **Verify:** Every shown command runs on the selected pin. No text presents P8–P10, the later
   application, or a proposed option name as an implemented V4 interface.
3. Run Testee, the affected Nix builds, the opt-in consumer fixture, and the real P1–P6 proof.
   Include P7 when releasing machine claims. Land and push through Gitman.
   **Verify:** All required gates pass on the release revision. Gitman reports the completed
   trunk in sync with origin and no relevant active work left behind.

## P8 — validate one reviewed upgrade

**Requirements:** `V4-UPG-001–008`, `V4-EVD-008`. Start after P1–P6. A machine upgrade
claim also requires P7.

1. Prepare one candidate from a recorded consumer base in an isolated checkout. Let native
   update tooling produce the declaration and lock diff.
   **Verify:** The active checkout stays unchanged. The diff and update trace show no second
   Vendomat revision database.
2. Validate the exact diff against P4 and P5 gates. Save checks, selected paths, and any
   publication receipt without accepting the candidate.
   **Verify:** Changing the diff invalidates its evidence. A failed check preserves logs and
   leaves active files unchanged. A cached candidate does not change the accepted selection.
3. Before acceptance, compare base files with the recorded base and recheck selected output
   availability under the required policy.
   **Verify:** A changed base or missing output rejects acceptance or requires revalidation.
4. Apply only the validated native diff through the project's version-control flow.
   **Verify:** Compare the applied diff byte for byte. Acceptance performs no rebuild,
   automatic commit, or deployment. Reports distinguish prepared, accepted, and activated.

**Gate:** One real candidate advances through prepare, validate, and explicit acceptance with
no selection drift or hidden activation.

## P9–P10 and the later application

P9 adds scaffolds, release tasks, or cross-repository reports only after two real consumers
show the same repeated problem. P10 adds scheduled proposals, broader capture, or full machine
caching only after measured use justifies them. These phases have no automatic start date.

1. Record the repeated user operation, native-only trial, failure, and proposed helper.
   **Verify:** A second consumer reproduces the same problem. A helper leaves native files and
   locks authoritative. Apply `V4-OPT-001–004` whenever the corresponding feature is offered.
2. Test each optional operation's failure path before enabling it. A scheduled sweep may
   prepare proposals but must not accept or deploy them.
   **Verify:** Failed release gates cannot report success or move an immutable tag. A scaffold
   yields a reviewable native patch. A timer leaves accepted files and targets unchanged.
3. Treat the Jujutsu–btrfs–bubblewrap application as a separate later module. Resolve its
   queue, state-retention, network, image, and sandbox choices from its own fixtures.
   **Verify:** Apply conditional `V4-APP-001–031` to that module. Its results do not retroactively
   gate the P1–P6 application proof or create a Vendomat runtime.
4. Apply optional source and retention requirements only if their features are offered.
   **Verify:** An index identifies its source and refreshes or reports stale data
   (`V4-SRC-013`). Remote reads deny writes (`V4-SRC-018`). A managed hold records reason and
   date (`V4-UPG-009`). An unreachable machine cannot authorize deletion (`V4-REC-007`).

## Final acceptance checklist

- P0 names tested pins, hosts, delivery paths, durable-state owners, and fallback policy.
- P1–P2 prove focused native modules, both delivery forms, and fresh local use.
- P3 retains selected source from both accepted direct-dependency graphs with honest labels.
- P4 binds required checks and NAR hashes to one frozen native selection.
- P5 proves every required runtime path from Attic alone and runs a cold laptop consumer.
- P6 restores source, Attic trust, and evidence as separate domains.
- P7 separately proves machine plan, transfer, activation, and recovery claims.
- The release revision passes its Testee, consumer, Nix, and real-host gates.

An incomplete item stays an explicit gap. The [requirement audit](../.scratch/projects/10-vendomat-v4-adversarial-review/V4-REQUIREMENT-AUDIT.md)
retains retired IDs and the disposition of inherited requirements.

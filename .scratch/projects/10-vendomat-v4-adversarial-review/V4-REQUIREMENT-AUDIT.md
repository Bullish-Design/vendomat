# V4 requirement audit

**Baseline:** The copied [V4-REQUIREMENTS.md](../09-vendomat-nixos-devenv-rewrite/V4-REQUIREMENTS.md) has 172 distinct IDs. [BASELINE.md](./BASELINE.md) identifies its exact bytes. This audit assigns one disposition to each baseline ID. The [revised requirements](./V4-REQUIREMENTS.md) retain every ID.  
**Rule:** Keep means the baseline behavior is atomic, observable, correctly owned, and traceable. Clarify means the revised row narrows its behavior or verification. Split narrows a mixed-owner row and routes its second concern to an existing ID. Move changes a phase or offer condition. Merge retires a duplicate ID while retaining its history. Conditional means the baseline row stays outside initial V4 through D-APP-SCOPE or an explicit later offer. No existing ID was reused or renumbered.

The audit treats native documentation as boundary evidence. It does not treat unrun fixtures as passed. The [review](./V4-REVIEW.md) gives failure scenarios and primary sources for material findings.

## Ownership and local independence

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-OWN-001 | Keep | Native lock selection has one owner; the lock-change evaluation observes it. |
| V4-OWN-002 | Keep | A negative resolver-state check protects that ownership; inspect generated files and update trace. |
| V4-OWN-003 | Keep | Shell entry without a Vendomat process is observable; fresh realization needs new `V4-OWN-013`. |
| V4-OWN-004 | Keep | The local-store test proves already-realized execution only; new `V4-OWN-013` covers first use. |
| V4-OWN-005 | Keep | Hash and selected-path comparison detects lookup side effects. |
| V4-OWN-006 | Clarify | Narrow the devenv-owned gate to evaluation side effects; activation remains native. |
| V4-OWN-007 | Keep | Native evaluation refresh proves the report has no selection database. |
| V4-OWN-008 | Keep | A new unregistered consumer tests ordinary module use directly. |
| V4-OWN-009 | Keep | P0 host, storage, backup, and fallback record is needed before deployment tests. |
| V4-OWN-010 | Keep | Task trace can show stage order; Testee remains the current verification interface. |
| V4-OWN-011 | Keep | Native plan and apply trace can detect a second deployment path. |

## Module contracts and delivery

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-MOD-001 | Keep | Compare documented target exports with evaluated native contributions; no new registry is required. |
| V4-MOD-002 | Keep | Import isolation is essential; author-only processes must remain absent. |
| V4-MOD-003 | Keep | Native type failure is a direct option-contract test. |
| V4-MOD-004 | Keep | Defaults apply only after explicit target enablement; evaluate that boundary. |
| V4-MOD-005 | Keep | Disabling editor while running command tests independent overrides. |
| V4-MOD-006 | Clarify | Only declared settings and documented bindings can yield named conflicts without a global binding registry. |
| V4-MOD-007 | Clarify | Native missing-export failure suffices; a custom Vendomat diagnostic is unnecessary. |
| V4-MOD-008 | Keep | Compare implementation identity across the two editor forms, then run both. |
| V4-MOD-009 | Keep | A conflicting `PATH` command makes package-path selection observable. |
| V4-MOD-010 | Keep | Two editor processes with distinct configuration test isolation. |
| V4-MOD-011 | Keep | The plain export must state consumer inputs; exact syntax remains P2 evidence. |
| V4-MOD-012 | Keep | The flake route's transitive input outcome is testable; export convention remains provisional. |
| V4-MOD-013 | Keep | The remote YAML counterexample follows devenv's documented polyrepo limit. |
| V4-MOD-014 | Keep | A profile and override matrix tests each supported path without assuming propagation. |

## Exact selections

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-SEL-001 | Clarify | An override need not change the output; inspect its path and native evaluation. |
| V4-SEL-002 | Keep | A second consumer gives a direct noninterference test. |
| V4-SEL-003 | Clarify | Revision or diff alone is insufficient when host or path inputs vary; `V4-SEL-009` closes that gap. |
| V4-SEL-004 | Keep | Digest comparison ties receipt to native declarations and locks. |
| V4-SEL-005 | Keep | Varying each selection field tests observability; names remain proposed. |
| V4-SEL-006 | Clarify | Record NAR hashes as well as derivation and paths; Nix output paths do not alone identify bytes. |
| V4-SEL-007 | Clarify | Include checked NAR hash in drift injection, not only locks and paths. |
| V4-SEL-008 | Keep | A composed output is the publication unit for a configuration-only module. |

## Required checks and coverage

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-CHK-001 | Keep | A check classified as pre-build must pass before build; instrument stage order. |
| V4-CHK-002 | Keep | Artifact checks must bind to the realized selected output path and bytes. |
| V4-CHK-003 | Clarify | The first-proof consumer declares its integration gates; consumers may add gates by choice. |
| V4-CHK-004 | Keep | A failed required gate blocks success; the injected failure is decisive. |
| V4-CHK-005 | Clarify | The old editor example conflicted with `V4-CHK-013`; use documented nonrequired behavior. |
| V4-CHK-006 | Keep | A failed native build and retained log have separate observable outcomes. |
| V4-CHK-007 | Keep | A stale reused path cannot replace check evidence; rerun with changed inputs. |
| V4-CHK-008 | Keep | Enabled module defaults are an accepted owner decision; inspect the effective set. |
| V4-CHK-009 | Keep | A consumer-added native check is an accepted extension point. |
| V4-CHK-010 | Keep | The union is observable with one gate from each owner. |
| V4-CHK-011 | Clarify | Classify absent or unavailable declared gates as missing-required, separate from a run failure. |
| V4-CHK-012 | Keep | The accepted nonrequired-gap policy permits success while the gap remains visible. |
| V4-CHK-013 | Keep | Command and editor checks are required for the enabled first-proof contributions. |
| V4-CHK-014 | Keep | Gate provenance is needed to reconstruct the effective required set. |
| V4-CHK-015 | Clarify | Report documented optional behavior; Vendomat cannot infer every unlisted test automatically. |

## Inspection source

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-SRC-001 | Clarify | Discovery can report unresolved candidates; it cannot promise a complete source map. |
| V4-SRC-002 | Keep | Deleting a read view distinguishes durable retained bytes from derived state. |
| V4-SRC-003 | Keep | The first-proof listed dependency directly tests accepted automatic capture. |
| V4-SRC-004 | Keep | Native identity and consumer selection give a minimum useful record. |
| V4-SRC-005 | Keep | Archive algorithm and representation prevent false raw-versus-unpacked hash comparisons. |
| V4-SRC-006 | Keep | Retention and correspondence are independent observed fields. |
| V4-SRC-007 | Keep | A patched package is a necessary false-exact-source counterexample. |
| V4-SRC-008 | Keep | A source gap must not alter an otherwise valid artifact result. |
| V4-SRC-009 | Keep | Corrupt retained bytes test correspondence failure without changing the native lock. |
| V4-SRC-010 | Keep | A bad fixed-output input fails native build validation; inspection status is separate. |
| V4-SRC-011 | Keep | Readable file plus provenance meets the first inspection need. |
| V4-SRC-012 | Keep | Read-only view and unchanged lock test lookup authority. |
| V4-SRC-013 | Move | Indexing is optional in the concept; its identity gate applies when an index or summary is offered. |
| V4-SRC-014 | Clarify | P3 needs a rebuildable read view; an optional index need not exist. |
| V4-SRC-015 | Keep | Capture evidence must not claim a rebuild that was never attempted. |
| V4-SRC-016 | Keep | Evaluation during source-host outage tests no remote mount dependency. |
| V4-SRC-017 | Keep | Startup during source-host outage tests application independence. |
| V4-SRC-018 | Move | Remote read is conditional on offering it; the central host shape is not yet required. |
| V4-SRC-019 | Keep | The consumer owns the capture list; `Q-CAPTURE-GRAPH` still defines its native target. |
| V4-SRC-020 | Keep | Capture each listed obtainable selection; P3 must prove resolution and identity. |
| V4-SRC-021 | Keep | A list-only edit must not change native dependency selection. |
| V4-SRC-022 | Keep | An unlisted source remains discoverable without automatic capture. |
| V4-SRC-023 | Keep | A stale list entry is a policy gap, not an update command. |

## Attic and cold consumption

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-CACHE-001 | Keep | Path equality binds push target to the checked selection; NAR identity adds `V4-CACHE-015`. |
| V4-CACHE-002 | Keep | Enumerating and querying the output closure tests the stated cache unit. |
| V4-CACHE-003 | Keep | A public-cache-seeded dependency exposes Attic's upstream filter. |
| V4-CACHE-004 | Keep | Test configured filter behavior; do not assume the push command included skipped paths. |
| V4-CACHE-005 | Keep | Remove one member after push to reject a false complete claim. |
| V4-CACHE-006 | Keep | Interrupt and retry the same selection to test partial side effects. |
| V4-CACHE-007 | Keep | Local execution after upload failure tests cache independence. |
| V4-CACHE-008 | Keep | Compare native files before and after candidate publication. |
| V4-CACHE-009 | Keep | Cold substitution with builds disabled tests the selected output path. |
| V4-CACHE-010 | Keep | Separate traces test priority and public-cache fallback; Attic defaults to priority 41. |
| V4-CACHE-011 | Keep | Fallback is native Nix policy; test allowed and denied builds separately. |
| V4-CACHE-012 | Clarify | Nix trust has content-addressed and trusted-store exceptions; test input-addressed signed paths. |
| V4-CACHE-013 | Split | Narrow NixOS ownership to secret placement; receipt redaction already belongs to `V4-EVD-006`. |
| V4-CACHE-014 | Keep | Re-query after removal distinguishes current availability from history. |

## Evidence and restore

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-EVD-001 | Keep | Compare receipt to frozen selection and native output metadata. |
| V4-EVD-002 | Keep | Check name, input, result, and log reference explain past validation. |
| V4-EVD-003 | Keep | Upload and verification time belong to historical evidence. |
| V4-EVD-004 | Move | A publication receipt first exists in P4; P3 can produce a source report alone. |
| V4-EVD-005 | Keep | Separate failure injections test stage and side-effect logging. |
| V4-EVD-006 | Keep | A canary secret makes redaction testable. |
| V4-EVD-007 | Keep | Cache expiry changes availability but not past check result. |
| V4-EVD-008 | Keep | Proposal, acceptance, and activation are distinct P8 states. |
| V4-EVD-009 | Keep | Restored receipts and logs must explain earlier outcomes. |
| V4-EVD-010 | Keep | Signed substitution does not establish independent rebuild proof. |
| V4-REC-001 | Keep | Restore and hash check prove inspection recovery. |
| V4-REC-002 | Keep | Restore and clean trusted substitution prove cache recovery. |
| V4-REC-003 | Keep | A source-only fault tests recovery-result independence. |
| V4-REC-004 | Keep | A cache-only fault tests recovery-result independence. |
| V4-REC-005 | Clarify | No initial deletion operation exists; exercise offered operations, not a speculative timer. |
| V4-REC-006 | Keep | Native size queries can check reported source and closure measurements. |
| V4-REC-007 | Move | No initial deletion engine exists; unreachable-target protection gates any later deletion offer. |
| V4-REC-008 | Keep | Deleting derived data must leave archive identity intact. |
| V4-REC-009 | Keep | P0 needs a named backup owner for every durable state class. |
| V4-REC-010 | Keep | Source retention and binary availability must have separate fields. |
| V4-REC-011 | Keep | A signed cached output can coexist with unresolved source correspondence. |
| V4-REC-012 | Keep | Application writes outside Nix outputs protect immutable package state. |

## Machine composition and native recovery

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-MACH-001 | Clarify | Current devenv 2.2.2 lacks documented Machines 2.4; run evaluation and plan on the new matched pin. |
| V4-MACH-002 | Keep | Separate target evaluation catches project-option leakage into NixOS or Home Manager. |
| V4-MACH-003 | Keep | Native plan paths are observable and remain Machines-owned. |
| V4-MACH-004 | Keep | Compare evidence link to native plan ID and selected paths. |
| V4-MACH-005 | Keep | Saved-plan apply without a build tests native plan identity. |
| V4-MACH-006 | Clarify | Machines owns stale-plan rejection; `V4-OWN-011` forbids a second Vendomat apply path. |
| V4-MACH-007 | Keep | A changed check input forces revalidation after replanning. |
| V4-MACH-008 | Keep | Transfer trace separates Attic substitution from direct copy. |
| V4-MACH-009 | Keep | Home Manager can fail after system success; statuses must remain separate. |
| V4-MACH-010 | Keep | Native pending or unknown status must be read before a retry. |
| V4-MACH-011 | Keep | Application writes survive system rollback; report that limit. |
| V4-MACH-012 | Clarify | Test actual service or activation behavior with native activation or a VM, not a generic build. |
| V4-MACH-013 | Keep | System rollback does not assert Home Manager file recovery. |

## Reviewed upgrades and optional work

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-UPG-001 | Keep | Isolated checkout and recorded base protect accepted files. |
| V4-UPG-002 | Keep | Native update trace preserves lock ownership. |
| V4-UPG-003 | Keep | Diff mutation after checks tests exact candidate binding. |
| V4-UPG-004 | Keep | A failed proposal leaves active files unchanged and retains logs. |
| V4-UPG-005 | Keep | Candidate cache presence must not select the candidate. |
| V4-UPG-006 | Keep | Base-file recheck prevents stale-diff acceptance. |
| V4-UPG-007 | Keep | Output availability follows declared acceptance policy, not receipt history alone. |
| V4-UPG-008 | Keep | Compare applied diff and absence of rebuild, commit, or deployment. |
| V4-UPG-009 | Conditional | A managed hold exists only when offered; native files still select the revision. |
| V4-OPT-001 | Conditional | An offered release task must fail when a required gate fails. |
| V4-OPT-002 | Conditional | Retry must preserve an existing immutable tag identity. |
| V4-OPT-003 | Clarify | Vendomat owns proposal-only behavior when offered; a native timer merely triggers it. |
| V4-OPT-004 | Conditional | Scaffolding must leave one editable source for each setting. |

## Proof acceptance IDs

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-PROOF-001 | Keep | Known findings test the command's useful result. |
| V4-PROOF-002 | Keep | A live editor command tests integration beyond command parsing. |
| V4-PROOF-003 | Keep | Clean plain and flake consumers test both delivery forms. |
| V4-PROOF-004 | Keep | The full lookup tests module and listed dependency correspondence together. |
| V4-PROOF-005 | Keep | Full-pipeline failure injection is an acceptance scenario beyond `V4-CHK-004`. |
| V4-PROOF-006 | Keep | Cold laptop run combines exact selection, closure, and application behavior. |
| V4-PROOF-007 | Merge | It exactly repeats `V4-REC-001`; retire the ID and use that P6 restore gate. |
| V4-PROOF-008 | Merge | It exactly repeats `V4-REC-002`; retire the ID and use that P6 restore gate. |

## Conditional later application

All `V4-APP-*` rows remain conditional under accepted D-APP-SCOPE. Their verification methods describe a later module fixture, not initial V4 work.

| Baseline ID | Disposition | Reason and verification judgment |
| --- | --- | --- |
| V4-APP-001 | Clarify | Require the three behaviors, not three separate exported submodules. |
| V4-APP-002 | Conditional | Local devenv run is the later module's development entry. |
| V4-APP-003 | Conditional | Native NixOS contribution owns persistent host service and storage. |
| V4-APP-004 | Conditional | Zero and multiple revset results must fail before admission. |
| V4-APP-005 | Conditional | Change-ID movement cannot change a queued commit ID. |
| V4-APP-006 | Clarify | Verified btrfs image is the contract; a staging subvolume is only one method. |
| V4-APP-007 | Conditional | Failure injection tests reader-visible atomicity and read-only status. |
| V4-APP-008 | Conditional | Two images of one commit test logical versus physical identity. |
| V4-APP-009 | Conditional | Conflicts and unsupported entries must fail exact materialization. |
| V4-APP-010 | Conditional | Tampered mapping or image mode must prevent reuse. |
| V4-APP-011 | Conditional | Old commit after runtime update tests matched native lock and output. |
| V4-APP-012 | Conditional | Missing runtime path must fail before process launch. |
| V4-APP-013 | Conditional | Write probes distinguish read-only image and instance state. |
| V4-APP-014 | Conditional | Cross-instance read probe tests default isolation. |
| V4-APP-015 | Conditional | Host-path probes test archive and credential hiding. |
| V4-APP-016 | Conditional | Namespace setup failure must not fall back to unsandboxed launch. |
| V4-APP-017 | Conditional | Same-commit instances must have unique IDs and state. |
| V4-APP-018 | Conditional | Different commits running together test revision coexistence. |
| V4-APP-019 | Conditional | Same commit running twice tests instance independence. |
| V4-APP-020 | Conditional | Mixed-revision capacity test awaits later queue policy. |
| V4-APP-021 | Conditional | Excess request must receive capacity result without a process. |
| V4-APP-022 | Conditional | A queued request must keep commit and runtime identities. |
| V4-APP-023 | Conditional | Concurrent race test verifies admission limits. |
| V4-APP-024 | Conditional | Supervisor restart must not double launch an accepted request. |
| V4-APP-025 | Conditional | Instance data retention differs from source, image, Nix, and system state. |
| V4-APP-026 | Conditional | Later local run needs neither Vendomat service nor Attic push. |
| V4-APP-027 | Conditional | Attic receipt must cover runtime Nix paths only. |
| V4-APP-028 | Conditional | Whole-system change needs native activation or VM evidence. |
| V4-APP-029 | Conditional | Invalid capacity settings must fail native configuration. |
| V4-APP-030 | Conditional | Running instance must protect its image from cleanup. |
| V4-APP-031 | Conditional | Rematerialization claim needs retained exact commit or verified source copy. |

## Missing requirements and proposed new IDs

These IDs are new. They do not replace any baseline ID. Their rows are present in the revised requirements.

| New ID | Missing contract, owner, and proof |
| --- | --- |
| V4-OWN-012 | Vendomat records preserve, migrate, or retire outcomes for current consumer delivery; test before and after the pin transition. |
| V4-OWN-013 | A fresh consumer realizes and runs under native policy with Vendomat and Attic unavailable; no offline-build promise. |
| V4-SEL-009 | Vendomat freezes or rejects host-delivered and local-path inputs outside the consumer lock; inject drift. |
| V4-CHK-016 | Vendomat blocks publication when an enabled module omits its default required-check declaration; classify missing-required. |
| V4-SRC-024 | Source store records immutable bytes for captured local source; change the working tree after capture. |
| V4-CACHE-015 | Vendomat compares checked NAR hash with Attic-only cold substitution; record closure-member metadata. |
| V4-EVD-011 | Vendomat reports failed-required, missing-required, and nonrequired-gap outcomes separately. |
| V4-REC-013 | Vendomat reports each recovery domain separately in the P7 fixture. |
| V4-MACH-014 | NixOS proves one persistent fixture service and health result after native apply. |
| V4-MACH-015 | Vendomat keeps application cache proof separate from a full machine-generation claim. |
| V4-PROOF-009 | Consumer runs an end-to-end pinned Machines fixture with plan, transfer, system/user outcome, and recovery status. |

## Open choices and technical gates

`Q-CAPTURE-GRAPH`, `Q-PROOF-GATE`, and `Q-OFFLINE-SOURCE` await the owner's answers. They are not new requirement IDs. `P-CURRENT-CONSUMERS` and `P-NAR-IDENTITY` are prototype gates, not commands or options. The revised [specification](./V4-SPEC.md) keeps these distinct from accepted D-CHECK-OWNER, D-CHECK-GAP, D-CAPTURE, D-NAMES, and D-APP-SCOPE.

**Consistency result:** 172 baseline IDs have one disposition each. Two duplicate IDs are retired without reuse. Eleven new IDs close missing observable contracts. P1–P6 prove application, inspection, and distribution. P7 proves machine claims. Conditional application IDs stay outside initial V4.

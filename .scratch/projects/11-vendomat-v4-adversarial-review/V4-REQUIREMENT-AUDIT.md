# Vendomat V4 requirement audit

**Date:** 2026-10-04.
**Input:** `V4-REQUIREMENTS.md` at the hash recorded in [BASELINE.md](./BASELINE.md).
**Rule honored:** every existing ID keeps its number. No ID is reused or renumbered.
**Findings referenced:** F-nn in [V4-REVIEW.md](./V4-REVIEW.md).

Existing IDs audited: **172**. Dispositions: keep 128, clarify 34, split 2, defer 3,
conditional 2, delete 0, merge 0.

| Disposition | Meaning |
| --- | --- |
| Keep | Atomic, observable, correct owner, traced, verifiable. No change. |
| Clarify | The requirement stands. Its wording, owner, or verification method changes. |
| Split | Two or more observations in one ID. The ID keeps one; a new ID takes the rest. |
| Defer | Correct, but premature for its stated phase. Moved to a later phase or "when offered". |
| Conditional | Correct only under a stated assumption that the P0 record must fix. |
| Delete | Removed. |

No existing requirement was deleted. Every one states a real, observable fact. The defects
are carrier, owner, phase, and scope — not invention.

## Ownership and local independence

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-OWN-001 | Keep | Atomic, native-owned, observable through one lock change. |
| V4-OWN-002 | Keep | The negative invariant that holds the whole design together. |
| V4-OWN-003 | Keep | Directly observable. The strongest requirement in the set. |
| V4-OWN-004 | Keep | Observable by denying Attic access. |
| V4-OWN-005 | Keep | Already true of the shipped `vendomat vendor sync`. |
| V4-OWN-006 | Keep | One observation: evaluation starts nothing. |
| V4-OWN-007 | Clarify | Must name the native source per reported field. Under F-01 the report attributes composition to RepoMan and `repoman.lock`, not to Vendomat. |
| V4-OWN-008 | Keep | Observable in a fresh consumer. |
| V4-OWN-009 | Clarify | Owner is the owner-operator, not "Consumer"; a P0 record has no consumer repository. Add `fallback = true` and cache-advertised priority to the recorded policy (F-06, F-07). |
| V4-OWN-010 | Clarify | Name devenv tasks as the stage and gate carrier (F-02), matching `nix/testee.nix`. |
| V4-OWN-011 | Conditional | Correct, but it conflicts with the shipped `vendomat plane` lifecycle until F-04 is decided. |

## Module contracts and delivery

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-MOD-001 | Keep | Atomic and inspectable. |
| V4-MOD-002 | Keep | Observable by absence of author-only processes. |
| V4-MOD-003 | Keep | Native type failure is the observation. |
| V4-MOD-004 | Keep | Paired with the new V4-MOD-015 cost requirement. |
| V4-MOD-005 | Keep | Independent override is the core module claim. |
| V4-MOD-006 | Keep | Covers both options and editor bindings in one observation. |
| V4-MOD-007 | Keep | Named unsupported contribution is observable. |
| V4-MOD-008 | Keep | Carried by the Neovim fixture under D-PROOF-SPLIT. |
| V4-MOD-009 | Keep | The `PATH`-shadowing method is a good adversarial test. |
| V4-MOD-010 | Keep | Observable with two distinct configurations. |
| V4-MOD-011 | Keep | Now also exercised by the `*man` toolchain fixture. |
| V4-MOD-012 | Keep | The P2 core question. |
| V4-MOD-013 | Keep | Confirms a documented limit: "devenv.yaml from imported projects is not evaluated." |
| V4-MOD-014 | Clarify | Profiles are already documented as unsupported for cross-project references (F-11). The matrix covers supported paths and records the documented limit instead of discovering it. |

## Exact selections and checks

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-SEL-001 | Keep | Observable report field. |
| V4-SEL-002 | Keep | The isolation claim that makes local overrides safe. |
| V4-SEL-003 | Keep | The immutability gate. |
| V4-SEL-004 | Keep | Digest comparison is observable. |
| V4-SEL-005 | Split | Four fields with "vary each field separately" is four observations. V4-SEL-005 keeps requested attribute and target system. New V4-SEL-009 takes profiles and overrides, with the F-11 limitation recorded. |
| V4-SEL-006 | Keep | Comparable against native Nix queries. |
| V4-SEL-007 | Keep | The drift gate. Essential. |
| V4-SEL-008 | Keep | Covers the configuration-only module case. |
| V4-CHK-001 | Clarify | Name the devenv task carrier (F-02). Order alone is not the observation; the task result is. |
| V4-CHK-002 | Clarify | Owner moves from "Module repository" to Vendomat. The module supplies the check; the gate performs the rejection. |
| V4-CHK-003 | Keep | Consumer-owned integration check. Correct owner. |
| V4-CHK-004 | Keep | The primary blocking gate. |
| V4-CHK-005 | Clarify | Scope to report content only. V4-CHK-012 owns the publication outcome. Both observations are real; the wording overlapped. |
| V4-CHK-006 | Keep | Failed build retains logs and claims nothing. |
| V4-CHK-007 | Clarify | "Changed check evidence" presumes a record. Name it: the recorded gate-task result set for the frozen selection. |
| V4-CHK-008 | Clarify | D-CHECK-OWNER needs a carrier. Name declared devenv gate-task names (F-02). |
| V4-CHK-009 | Clarify | Same carrier, consumer side. |
| V4-CHK-010 | Clarify | The union is a union of task names, not of an undefined check object. |
| V4-CHK-011 | Keep | "Declared but cannot run" is the subtlest and most valuable gate in the set. |
| V4-CHK-012 | Clarify | Scope to the publication outcome. See V4-CHK-005. |
| V4-CHK-013 | Keep | First-proof module gate declaration. |
| V4-CHK-014 | Keep | Gate origin attribution. Needed for D-CHECK-OWNER to be auditable. |
| V4-CHK-015 | Clarify | Mark `[PROTOTYPE]`. It depends on P-CHECK-COVERAGE, which F-02 shows has no native mechanism yet. |

## Inspection source

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-SRC-001 | Keep | Discovery without capture is the right separation. |
| V4-SRC-002 | Keep | Retained bytes survive read-view deletion. |
| V4-SRC-003 | Keep | Traces to D-CAPTURE. |
| V4-SRC-004 | Keep | Identity plus selection context. |
| V4-SRC-005 | Keep | Algorithm and hashed representation. Prevents the archive-versus-tree hash error. |
| V4-SRC-006 | Keep | Two separate fields. The design's best source requirement. |
| V4-SRC-007 | Keep | Patch visibility beside source. |
| V4-SRC-008 | Keep | Gap does not invalidate an artifact check. |
| V4-SRC-009 | Keep | Corruption loses the exactness claim, not the record. |
| V4-SRC-010 | Keep | Correct owner: native Nix validation. |
| V4-SRC-011 | Keep | Readable tree plus provenance. |
| V4-SRC-012 | Keep | Read access cannot mutate. |
| V4-SRC-013 | Defer | Contradicts V4 §12 policy item 5: "Expand indexing only when real searches demonstrate its value." Move to "when offered". |
| V4-SRC-014 | Defer | Same reason. No index is in P3 scope. |
| V4-SRC-015 | Keep | Capture makes no rebuild claim. Prevents the worst possible false claim. |
| V4-SRC-016 | Keep | Cheap under D-SRC-ACCESS. |
| V4-SRC-017 | Keep | Cheap under D-SRC-ACCESS. |
| V4-SRC-018 | Clarify | D-SRC-ACCESS: a read-only filesystem export over SSH. The method becomes an export and permission check, not a service query. |
| V4-SRC-019 | Clarify | The list already exists: `vendor/python/*.toml`, validated by `src/vendomat/catalog.py` with a 40-hex `rev`. Extend it; do not design it. |
| V4-SRC-020 | Clarify | Extend the shipped `vendomat vendor sync` stage rather than specify a new one. |
| V4-SRC-021 | Keep | Already true of the shipped code: "never writes a source into `pyproject.toml`, `[tool.uv.sources]`, or `uv.lock`". |
| V4-SRC-022 | Keep | Discovery without capture, per entry. |
| V4-SRC-023 | Keep | `vendomat vendor doctor` already reports this shape. |

## Attic and cold consumption

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-CACHE-001 | Keep | Exact path identity through check, push, and receipt. |
| V4-CACHE-002 | Clarify | Rewritten under D-ATTIC-SCOPE (F-03) to the paths no trusted configured substituter serves. The method names `nix path-info --store` or isolated-store substitution, because the Attic CLI documents no presence query (F-10). |
| V4-CACHE-003 | Defer | Under D-ATTIC-SCOPE this is no longer a gate. It becomes a measurement for a later disconnected-operation goal (F-03). |
| V4-CACHE-004 | Clarify | Owner moves from "Attic configuration" to Vendomat: accounting for the filter is publication policy. Under D-ATTIC-SCOPE the documented default filter is now the correct behavior, not an obstacle. |
| V4-CACHE-005 | Keep | Upload success is not availability. Core honesty requirement. |
| V4-CACHE-006 | Keep | Partial progress and safe retry. |
| V4-CACHE-007 | Keep | Local output survives an upload failure. |
| V4-CACHE-008 | Keep | Publication changes no selection. |
| V4-CACHE-009 | Clarify | Must record which substituter served each path, not only that a transfer happened. |
| V4-CACHE-010 | Split | Three observations in one ID. V4-CACHE-010 keeps priority behavior, rewritten for cache-advertised priority (F-06). New V4-CACHE-016 takes the missing-path case. V4-CACHE-011 already owns build fallback. |
| V4-CACHE-011 | Clarify | State that the build-fallback step needs `fallback = true`; its default is `false` (F-07). Mark unreachable-substituter behavior `[PROTOTYPE]`. |
| V4-CACHE-012 | Keep | Trust is correctly owned by NixOS. |
| V4-CACHE-013 | Keep | Credential and secret exclusion. Keep the canary method. |
| V4-CACHE-014 | Keep | Current availability is not a historical receipt. |

## Evidence, failure reporting, and restore

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-EVD-001 | Keep | Receipt binds selection to output identity. |
| V4-EVD-002 | Clarify | "Each required check" becomes each gate task name plus its origin (F-02). |
| V4-EVD-003 | Keep | Target, result, and verification time. |
| V4-EVD-004 | Keep | Separates source coverage from artifact checks. |
| V4-EVD-005 | Keep | Failed stage and side effects. |
| V4-EVD-006 | Keep | Canary method is sound. |
| V4-EVD-007 | Keep | Check success is not current availability. |
| V4-EVD-008 | Keep | Prepared, accepted, activated. |
| V4-EVD-009 | Keep | Restored evidence stays explainable. |
| V4-EVD-010 | Keep | A signature is not a rebuild proof. The sharpest claim in the set. |
| V4-REC-001 | Keep | Identity plus correspondence on restore. |
| V4-REC-002 | Keep | Signing state is part of the cache restore. |
| V4-REC-003 | Keep | Independent failure domains. |
| V4-REC-004 | Keep | Independent failure domains. |
| V4-REC-005 | Keep | No automatic deletion in initial V4. |
| V4-REC-006 | Clarify | Under D-ATTIC-SCOPE the measured closure is smaller. Keep as a measurement and state the reduced scope. |
| V4-REC-007 | Keep | Unreachable is not approval. Excellent requirement. |
| V4-REC-008 | Keep | Derived cleanup leaves identity intact. |
| V4-REC-009 | Clarify | Owner is the owner-operator, not "Consumer". |
| V4-REC-010 | Keep | Source retention and binary availability report separately. |
| V4-REC-011 | Keep | A cached output can be valid with unresolved correspondence. |
| V4-REC-012 | Keep | Mutable state stays out of immutable outputs. |

## Machine composition and native recovery

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-MACH-001 | Keep | The pin. Everything in P7 depends on it. Machines is "new in devenv 2.4. The interface may change before it is declared stable." |
| V4-MACH-002 | Keep | Target separation. |
| V4-MACH-003 | Keep | Documented: plan "records the NixOS system, access facts, and store closure changes". |
| V4-MACH-004 | Keep | Evidence links to the native plan. |
| V4-MACH-005 | Keep | Documented: apply "uses those exact outputs without rebuilding". |
| V4-MACH-006 | Keep | Documented staleness: "A changed NixOS generation or target definition makes the plan stale." |
| V4-MACH-007 | Keep | Check reuse only on matching inputs. |
| V4-MACH-008 | Clarify | Documentation already answers the question: apply "copies all outputs". Restate as recording the observed transfer path, and narrow P-MACHINES (F-08). |
| V4-MACH-009 | Keep | Documented: "If home-manager fails after NixOS succeeds, the NixOS deployment remains applied." |
| V4-MACH-010 | Keep | Watchdog deadline is 300 seconds by default; an unknown state must be read before a retry. |
| V4-MACH-011 | Keep | Documented limit: recovery "cannot ... reverse application data changes". |
| V4-MACH-012 | Keep | Bubblewrap cannot substitute for a VM activation test. |
| V4-MACH-013 | Conditional | True for standalone Home Manager only. Under the NixOS-module mode there may be no Home Manager profile at all, and the system profile references the Home Manager configuration (F-09). Condition it on the P0 mode record. |

## Reviewed upgrades and optional operations

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-UPG-001 | Keep | Recorded base in an isolated checkout. |
| V4-UPG-002 | Keep | Native tooling owns resolution. |
| V4-UPG-003 | Keep | A prior result cannot validate a changed diff. |
| V4-UPG-004 | Keep | Failure preserves logs and changes nothing. |
| V4-UPG-005 | Keep | Cached is not accepted. |
| V4-UPG-006 | Keep | Base match on acceptance. |
| V4-UPG-007 | Keep | Output availability on acceptance. |
| V4-UPG-008 | Keep | Acceptance applies only the diff. |
| V4-UPG-009 | Keep | Correctly scoped "when offered". |
| V4-OPT-001 | Keep | Gate failure blocks release success. |
| V4-OPT-002 | Keep | A published tag never moves. Matches this repo's existing rule that an iteration build gets its own version. |
| V4-OPT-003 | Keep | A sweep never accepts or deploys. |
| V4-OPT-004 | Keep | Reviewable patches, one setting authority. |

## First complete proof

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-PROOF-001 | Keep | P1, Neovim fixture under D-PROOF-SPLIT. |
| V4-PROOF-002 | Keep | P1, Neovim fixture. |
| V4-PROOF-003 | Clarify | Carried by the `*man` toolchain fixture under D-PROOF-SPLIT, which already has a flake-backed export and a real consumer check. |
| V4-PROOF-004 | Keep | P3. The existing `vendor/python` catalog supplies the third-party entry. |
| V4-PROOF-005 | Keep | The deliberate failed gate. Traces to V4-CHK-004. |
| V4-PROOF-006 | Clarify | Rewritten under D-ATTIC-SCOPE: the cold consumer realizes the output and performs no build. Drop the Attic-only full-closure phrasing (F-03). |
| V4-PROOF-007 | Keep | Restored source identity. |
| V4-PROOF-008 | Keep | Restored trusted substitution. |

## Conditional later-application requirements

All 31 `C` IDs stay conditional and outside V4 scope, per D-APP-SCOPE. Their technical
content survived the documentation audit. Four need sharper wording.

| ID | Disposition | Reason |
| --- | --- | --- |
| V4-APP-001 | Keep | Composition of three focused contributions. |
| V4-APP-002 | Keep | Local devenv contribution. |
| V4-APP-003 | Keep | NixOS contribution for persistent needs. |
| V4-APP-004 | Clarify | Cite the documented identity facts: a commit ID is "20 bytes long when using the Git backend", and "A divergent change is a change that has more than one visible commit." |
| V4-APP-005 | Keep | Change-ID movement cannot move an admitted request. Documented: rewriting yields a new commit ID while the change ID "generally remains the same". |
| V4-APP-006 | Keep | Files, paths, modes, symlinks. |
| V4-APP-007 | Keep | Only a verified read-only subvolume is publishable. |
| V4-APP-008 | Clarify | Name the identity fields: subvolume UUID and subvolume ID. Inode numbers are not identity; a subvolume root "has always inode number 256". |
| V4-APP-009 | Keep | Conflicted, escaping, and unsupported entries fail explicitly. |
| V4-APP-010 | Keep | Reuse rechecks mapping and read-only state. |
| V4-APP-011 | Keep | The old commit keeps its own runtime. |
| V4-APP-012 | Keep | Fail before launch. |
| V4-APP-013 | Keep | `--ro-bind` for the image, `--bind` for one instance's state. |
| V4-APP-014 | Keep | Cross-instance read denial. |
| V4-APP-015 | Keep | Host archive and credential denial. |
| V4-APP-016 | Clarify | Require the non-`try` namespace options. `--unshare-user-try` and `--unshare-cgroup-try` are documented to "skip it" on failure, which would pass this test while removing the guarantee (F-14). |
| V4-APP-017 | Keep | Unique instance ID and separate state. |
| V4-APP-018 | Keep | Two commits concurrently. |
| V4-APP-019 | Keep | Two instances of one commit. |
| V4-APP-020 | Keep | Limits apply across revisions. |
| V4-APP-021 | Keep | Explicit capacity result. |
| V4-APP-022 | Keep | A queued request never re-resolves a revset. |
| V4-APP-023 | Keep | Race test against small limits. |
| V4-APP-024 | Keep | No double launch across restart. |
| V4-APP-025 | Keep | Independent retention domains. |
| V4-APP-026 | Keep | Local run without Vendomat or Attic. Mirrors V4-OWN-003 and V4-OWN-004. |
| V4-APP-027 | Keep | Attic carries store paths only. Documented: `attic push` takes "The store paths to push". |
| V4-APP-028 | Keep | Native build or VM, not a sandbox run. |
| V4-APP-029 | Keep | Invalid limits fail evaluation. |
| V4-APP-030 | Keep | A running instance pins its image. |
| V4-APP-031 | Clarify | A rematerialization claim needs the tree identity, not only the commit ID: two commits can share one tree, and the commit ID identifies a commit. |

## Missing requirements and proposed new IDs

Sixteen new IDs. Each traces to a finding, an owner answer, or existing repository
behavior that no current ID covers.

| New ID | Phase | Required behavior | Owner | Source |
| --- | --- | --- | --- | --- |
| V4-OWN-012 | P0 | The P0 record inventories the current consumer surface — `vendomat.toml` faces, the installed `machine.json`, `plane`, `publish`, `vendor sync`, `install-hook` — and records keep, replace, or retire with a window for each. | Owner | F-04 |
| V4-OWN-013 | P1 | A composition report attributes each selection to its native authority and to RepoMan's manifest where one exists; Vendomat records no composition authority of its own. | Vendomat | F-01; `AGENTS.md` |
| V4-MOD-015 | P1 | An enabled target whose component the consumer disabled adds no shell-entry work. | Module repository | F-13; `README.md` |
| V4-MOD-016 | P2 | The delivery matrix evaluates `inputs.<name>.devenv.config` as a third documented route beside the plain import and the flake-backed export. | devenv | F-11 |
| V4-SEL-009 | P2 | A selection records active profiles and overrides, and records that profiles do not apply to cross-project references. | Vendomat | F-11; split from V4-SEL-005 |
| V4-CHK-016 | P4 | A module declares its gate set as named devenv task names, and the receipt records each task name with its result. | Module repository | F-02 |
| V4-CHK-017 | P4 | For a `*man`-family consumer, the default required gate is the existing Testee verification that `gitman.toml` already declares before publication. | Consumer | F-02; `gitman.toml`, `nix/testee.nix` |
| V4-SRC-024 | P3 | Source read access is a read-only filesystem export. No Vendomat daemon runs for reading, capture, or lookup. | Source store | D-SRC-ACCESS |
| V4-SRC-025 | P3 | Capture adds correspondence and status labels to the existing reviewed catalog without changing its schema authority or its immutable revision field. | Source store | Existing `vendor/python/*.toml` and `src/vendomat/catalog.py` |
| V4-CACHE-015 | P5 | The Attic cache advertises a priority value lower than every configured public cache. | Attic and NixOS | F-06 |
| V4-CACHE-016 | P5 | A closure path that no configured substituter serves produces a named failure or a permitted build under the recorded policy, not a silent outcome. | NixOS | F-06; split from V4-CACHE-010 |
| V4-CACHE-017 | P5 | Publication keeps the store index and the release-URL index in agreement; one build yields one artifact in both. | Vendomat | F-05; `README.md` |
| V4-MACH-014 | P7 | A change to the pinned devenv revision re-runs the P7 gates before the next machine apply. | Consumer | F-08; Machines is pre-stable |
| V4-MACH-015 | P0 | The P0 record names the Home Manager integration mode: standalone, or a NixOS module. | Owner | F-09 |
| V4-PROOF-009 | P5 | A cold `*man`-toolchain consumer realizes the published toolchain output and performs no build. | Nix consumer | D-PROOF-SPLIT |
| V4-PROOF-010 | P0 | The P0 record states which fixture carries each phase gate. | Owner | D-PROOF-SPLIT |

## Contradictions found

| Contradiction | Resolution |
| --- | --- |
| V4 §1 makes Vendomat the composition helper; `AGENTS.md` assigns composition to RepoMan. | Unresolved. Owner decision (F-01). The revised concept marks it and adds the RepoMan ownership row. |
| V4 §23 forbids a Vendomat deployment planner or rollback; `src/vendomat/plane.py` implements one. | Unresolved. Owner decision (F-04). New V4-OWN-012 records the surface. |
| V4 §14 cites devenv outputs for "declared checks"; that page documents no checks. | Resolved. Name devenv tasks as the carrier (F-02). New V4-CHK-016 and V4-CHK-017. |
| V4 §13 requires complete closure retention; Attic skips upstream-signed paths by default. | Resolved by D-ATTIC-SCOPE. V4-CACHE-002 rewritten, V4-CACHE-003 deferred. |
| V4 §11 implies a networked read service; invariant 5 forbids a required service. | Resolved by D-SRC-ACCESS. New V4-SRC-024. |
| V4 §12 policy item 5 defers indexing; V4-SRC-013 and V4-SRC-014 require it at P3. | Resolved. Both deferred to "when offered". |
| V4 §13 makes Attic the primary distribution service; `README.md` records the release-URL channel as the non-Nix adoption path. | Resolved. Both channels stated. New V4-CACHE-017. |

## Duplicate gates reviewed and kept

Three pairs looked duplicated and are not. Each keeps both IDs with tightened scope.

- **V4-CHK-005 and V4-CHK-012.** One is the report content; the other is the publication
  outcome. Both are observable and neither implies the other.
- **V4-CHK-004 and V4-PROOF-005.** One is the gate; the other is the fixture instance that
  exercises it. V4-PROOF-005 now traces to V4-CHK-004.
- **V4-EVD-007, V4-REC-010, and V4-REC-011.** Three different pairs of facts: check success
  against availability, source retention against availability, and cached validity against
  unresolved correspondence. No two are the same pair.

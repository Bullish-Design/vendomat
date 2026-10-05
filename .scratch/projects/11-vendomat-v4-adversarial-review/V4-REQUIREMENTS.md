# Vendomat V4 testable requirements

**Status:** Draft for owner review, 2026-10-04.  
**Authority:** [V4 concept](./CONCEPT-V4.md). [V4 specification](./V4-SPEC.md) states the system contract.  
**Rule:** An ID is stable. Add new IDs; do not reuse or renumber old IDs.
**Revision:** Revised 2026-10-04 by the adversarial review in this directory. Every existing ID kept its number. See [V4-REQUIREMENT-AUDIT.md](./V4-REQUIREMENT-AUDIT.md) for one disposition per ID and [V4-REVIEW.md](./V4-REVIEW.md) for the findings. `[OWNER DECISION]` marks a requirement awaiting an owner answer. `[PROTOTYPE]` marks one whose mechanism primary documentation does not settle.
**New decisions applied:** D-ATTIC-SCOPE, D-SRC-ACCESS, and D-PROOF-SPLIT, accepted 2026-10-04. Sixteen new IDs were added: V4-OWN-012, V4-OWN-013, V4-MOD-015, V4-MOD-016, V4-SEL-009, V4-CHK-016, V4-CHK-017, V4-SRC-024, V4-SRC-025, V4-CACHE-015, V4-CACHE-016, V4-CACHE-017, V4-MACH-014, V4-MACH-015, V4-PROOF-009, and V4-PROOF-010.

`M` requirements gate the stated V4 phase or apply whenever that V4 feature is offered. `C` requirements apply only to the later Jujutsu–btrfs–bubblewrap module. The owner accepted that scope as **D-APP-SCOPE** on 2026-10-04. The owner accepted semantics-first naming as **D-NAMES**. The owner also accepted **D-CHECK-OWNER**, **D-CHECK-GAP**, **D-CAPTURE**, **D-ATTIC-SCOPE**, **D-SRC-ACCESS**, and **D-PROOF-SPLIT** on 2026-10-04. New option and command names remain proposed.

Each verification method describes an observable result for a later fixture. It does not assert that V4 already implements the behavior. Phase labels follow V4 §22. P1–P6 form the first complete proof, split across two fixtures by D-PROOF-SPLIT: the Neovim application carries P1 and P3, and the `*man` toolchain carries P2 and P4–P6. P7 covers Machines; P8 covers one reviewed upgrade. P9–P10 require a separate measured need. The conditional application has no V4 phase gate.

## Mandatory V4 requirements

### Ownership and local independence

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-OWN-001 | P1 | A consumer's native declarations and locks determine its selected inputs. | Consumer | V4 §§2–3, 24 | Change one native lock in a fixture; evaluate and observe that the selected input changes only through that lock. |
| V4-OWN-002 | P1 | Vendomat introduces no editable dependency lock or resolver state. | Vendomat | V4 §§2, 8, 23 | Inspect generated files and dependency update trace; find only native declarations and locks as selection authorities. |
| V4-OWN-003 | P1 | A project can enter its accepted environment without a live Vendomat process. | devenv | V4 §§1, 9, 24 | Stop or remove Vendomat service and enter the pinned project shell. |
| V4-OWN-004 | P1 | A selected local command can run without Attic publication. | Native application | V4 §§1, 9, 24 | Deny Attic access and run an already realized local output. |
| V4-OWN-005 | P1 | Source lookup does not change native locks or installed outputs. | Source store | V4 §§11, 20 | Record file hashes and selected paths; perform lookup; compare them. |
| V4-OWN-006 | P1 | Evaluation, activation, and execution remain separate operations. | devenv | V4 §§7, 10 | Evaluate a module; observe no service start or user/system activation. |
| V4-OWN-007 | P1 | Current selection reports come from native files and evaluated state, and each reported field names its native authority. | Vendomat | V4 §15 | Change a native option; refresh report; observe new effective value and its named authority, without editing a Vendomat database. |
| V4-OWN-008 | P1 | Vendomat does not require project registration for normal module use. | Vendomat | V4 §§8–9 | Import a module in a new consumer and enter it without registering the project elsewhere. |
| V4-OWN-009 | P0 | The deployment record names tested host systems, storage owners, backup locations, native cache fallback policy, the `fallback` setting value, and each cache's advertised priority. | Owner | V4 §§13, 19, 22 | Inspect P0 record against fixture hosts and native settings; confirm `fallback` and advertised priority are recorded, not assumed. |
| V4-OWN-010 | P1 | Project-local pipeline stages run through named devenv tasks and focused native helpers. | devenv | V4 §16 | Trace a publication fixture; observe named task prerequisites and per-task results. |
| V4-OWN-011 | P7 | `[OWNER DECISION]` Machine activation delegates to the pinned Machines implementation and its plan. | Vendomat | V4 §§10, 23 | Trace apply; compare native plan ID and target activation; find no second plan path. Conditional on the Q-SURFACE decision, because `src/vendomat/plane.py` currently owns a generation lifecycle. |
| V4-OWN-012 | P0 | The P0 record inventories the delivered consumer surface — `vendomat.toml` faces, the installed `machine.json`, `plane`, `publish`, `vendor sync`, `install-hook` — and records keep, replace, or retire with a window for each. | Owner | V4-REVIEW F-04 | Inspect the P0 record against the shipped `modules/devenv.nix`, `src/vendomat/plane.py`, and the current command-line surface; every surface has exactly one disposition. |
| V4-OWN-013 | P1 | `[OWNER DECISION]` A composition report attributes each selection to its native authority, and to RepoMan's manifest where one exists. Vendomat records no composition authority of its own. | Vendomat | V4-REVIEW F-01; `AGENTS.md` | Compose a consumer that uses RepoMan; inspect the report and find no Vendomat-owned composition record. |

### Module contracts and delivery

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-MOD-001 | P1 | A module contract lists its supported native targets and exports. | Module repository | V4 §§4, 7 | Inspect fixture contract; compare each listed export with evaluated target outputs. |
| V4-MOD-002 | P1 | A consumer can import a reusable contribution without inheriting the author's whole development environment. | Module repository | V4 §8 | Import only the review command; verify author-only process and tools are absent. |
| V4-MOD-003 | P1 | Typed Nix options define configurable module behavior. | Module repository | V4 §4 | Evaluate valid and invalid option types; invalid type must fail natively. |
| V4-MOD-004 | P1 | Enabling a target gives relevant components documented defaults. | Module repository | V4 §§4, 7 | Enable the review target with no overrides; inspect evaluated command and editor settings. |
| V4-MOD-005 | P1 | A consumer can disable or override each documented component independently. | Module repository | V4 §§4, 21 | Disable editor integration while retaining command; evaluate and run command. |
| V4-MOD-006 | P1 | Incompatible options or editor bindings produce a named conflict. | Module repository | V4 §§4, 20 | Compose deliberate conflicts; inspect evaluation diagnostic and verify no silent choice. |
| V4-MOD-007 | P1 | Requesting an unsupported target fails with the unsupported contribution named. | Module repository | V4 §20 | Request a target absent from a fixture module; inspect the diagnostic. |
| V4-MOD-008 | P1 | The normal Neovim plugin and dedicated application use the same review implementation. | Module repository | V4 §§6, 21 | Exercise both outputs and compare the packaged implementation identity. |
| V4-MOD-009 | P1 | The editor interface invokes the selected command package by exact path. | Module repository | V4 §6 | Place a conflicting command earlier on `PATH`; run the editor check and observe the selected package. |
| V4-MOD-010 | P1 | The dedicated Neovim application can run beside the owner's normal editor configuration. | Module repository | V4 §§6, 21 | Launch both with distinct settings; confirm each retains its own expected configuration. |
| V4-MOD-011 | P2 | An ordinary repository export states every native input its consumer must supply. | Module repository | V4 §§8, 25 | Remove one required input from consumer; diagnostic identifies the missing native input. |
| V4-MOD-012 | P2 | A flake-backed export makes its proven transitive inputs available to the module implementation. | Module repository | V4 §§8, 21, 25 | Use a clean consumer with one module selection; evaluate and build with the locked transitive input. |
| V4-MOD-013 | P2 | Neither delivery path assumes recursive import of a remote `devenv.yaml`. | Module repository | V4 §8 | Give the remote author YAML an extra input; verify the consumer needs the documented explicit delivery path. This confirms the documented limit "devenv.yaml from imported projects is not evaluated". |
| V4-MOD-014 | P2 | Each profile and local override path that devenv supports has a recorded effective selection, and the record states that profiles do not apply to cross-project references. | devenv | V4 §§8–9, 25 | Evaluate the reduced matrix and compare reported inputs and outputs with native evaluation; confirm the documented cross-project profile limit is recorded, not retested as an unknown. |
| V4-MOD-015 | P1 | An enabled target whose component the consumer disabled adds no shell-entry work. | Module repository | V4-REVIEW F-13; `README.md` | Measure shell entry with the component enabled and disabled; the disabled case performs no probe and no extra evaluation. |
| V4-MOD-016 | P2 | The delivery matrix evaluates `inputs.<name>.devenv.config` as a third documented route beside the plain import and the flake-backed export. | devenv | V4-REVIEW F-11 | Reference another project's output through that attribute; compare the resulting selection with both other routes. |

The delivery gates rely on current [devenv imports](https://devenv.sh/composing-using-imports/), [polyrepo limits](https://devenv.sh/guides/polyrepo/), and [native inputs](https://devenv.sh/inputs/). Exact export syntax remains a prototype result.

### Exact selections and checks

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-SEL-001 | P2 | A local override is visible in the effective selection report. | Vendomat | V4 §§9, 24 | Select a local module checkout; inspect report and output change. |
| V4-SEL-002 | P2 | One consumer's local override does not change a second consumer's accepted lock. | Consumer | V4 §§9, 24 | Override consumer A; compare consumer B lock and evaluated path. |
| V4-SEL-003 | P4 | A publication selection identifies an immutable consumer revision or exact diff against a recorded base. | Vendomat | V4 §14 | Attempt publication from an unrecorded mutable checkout; verify it cannot receive an immutable success claim. |
| V4-SEL-004 | P4 | A selection records native declaration and lock identities. | Vendomat | V4 §14 | Inspect receipt; compare recorded digests to the selected consumer files. |
| V4-SEL-005 | P4 | A selection records the requested output attribute and target system. | Vendomat | V4 §14 | Vary each field separately; observe distinct records and evaluated selections. |
| V4-SEL-006 | P4 | A selection records effective module sources, derivation, and realized output paths. | Vendomat | V4 §14 | Compare selection record with native evaluation and Nix store queries. |
| V4-SEL-007 | P4 | Publication rejects identity drift between checked and uploaded outputs. | Vendomat | V4 §§14, 24 | Change a lock or output after checks; verify upload success is withheld. |
| V4-SEL-008 | P4 | A pure configuration module can publish its selected composed output without a separate module binary. | Vendomat | V4 §14 | Publish an application composed from a configuration-only module; verify output identity. |
| V4-SEL-009 | P4 | A selection records active profiles and overrides, and records that profiles do not apply to cross-project references. | Vendomat | V4 §14; V4-REVIEW F-11; split from V4-SEL-005 | Vary profiles and overrides separately; observe distinct records. For a cross-project reference, the record names the documented profile limit instead of a profile value. |
| V4-CHK-001 | P4 | Required pre-build gate tasks run before the selected output is built. | devenv task | V4 §§14, 16 | Instrument fixture order; fail a pre-build gate task and observe no build success and a recorded task result. |
| V4-CHK-002 | P4 | The gate rejects an artifact check run against a different output path than the selection records. | Vendomat | V4 §14 | Replace a test input with another output path; the gate rejects the identity mismatch. |
| V4-CHK-003 | P4 | Required consumer integration checks exercise the selected composition. | Consumer | V4 §§6, 14, 21 | Run the command through the project and editor fixtures against the chosen path. |
| V4-CHK-004 | P4 | A failed required check prevents successful publication. | Vendomat | V4 §§14, 20, 24 | Inject a deterministic failed gate; observe no success receipt or complete-publication claim. |
| V4-CHK-005 | P4 | An absent relevant check outside the required set appears in the coverage report. | Vendomat | V4 §§14, 20; D-CHECK-GAP | Remove a nonrequired editor integration check; inspect the coverage report's content. Publication outcome is V4-CHK-012's observation, not this one. |
| V4-CHK-006 | P4 | A failed build retains diagnostic logs and cannot report publication success. | Vendomat | V4 §§14, 20 | Break derivation; inspect failure record and absence of success result. |
| V4-CHK-007 | P4 | An idempotent stage verifies the state it reuses against the recorded gate-task result set for the frozen selection. | Vendomat helper | V4 §16 | Re-run with an existing output but a changed recorded task-result set; the stage reruns or fails rather than skipping. |
| V4-CHK-008 | P4 | Each enabled module exports its default gate set as named devenv task names for the selected output. | Module repository | D-CHECK-OWNER; V4 §§4, 14 | Enable and disable one component; inspect the module's effective default gate task names. |
| V4-CHK-009 | P4 | A consumer can append gate task names for its selected composition. | Consumer | D-CHECK-OWNER; V4 §14 | Add one native integration task name; inspect the effective gate set. |
| V4-CHK-010 | P4 | Publication runs the union of module default gate task names and consumer-added task names. | Vendomat | D-CHECK-OWNER; V4 §14 | Set one task name from each owner; verify both run against the same frozen selection. |
| V4-CHK-011 | P4 | A declared required gate task that cannot run blocks publication success. | Vendomat | D-CHECK-OWNER; V4 §§14, 20 | Remove a declared gate task's implementation; verify no success receipt. |
| V4-CHK-012 | P4 | An absent relevant check outside the required set does not block publication. | Vendomat | D-CHECK-GAP; V4 §§14, 20 | Omit a nonrequired relevant check; pass declared gates; inspect the success result. Report content is V4-CHK-005's observation. |
| V4-CHK-013 | P1 | The first-proof module declares checks for its enabled command and editor contributions. | Module repository | D-CHECK-OWNER; V4 §§6, 21 | Evaluate review module with editor enabled; inspect command and editor check declarations. |
| V4-CHK-014 | P4 | The selection records whether each required check came from a module or the consumer. | Vendomat | D-CHECK-OWNER; V4 §§14–15 | Inspect a mixed-check selection and match each gate to its declaration. |
| V4-CHK-015 | P4 | `[PROTOTYPE]` Coverage reporting identifies absent checks against documented enabled contribution behavior. | Vendomat | D-CHECK-GAP; V4 §§4, 14 | Enable editor contribution without its nonrequired integration check; report names the uncovered behavior. The expression mechanism is unproved; see experiment P-CHECK-COVERAGE. |
| V4-CHK-016 | P4 | A module declares its gate set as named devenv task names, and the receipt records each task name with its result. | Module repository | V4-REVIEW F-02 | Declare gate tasks in two modules; publish; inspect the receipt for each task name and result. devenv documents no output-bound or module-declared check mechanism, so tasks are the carrier. |
| V4-CHK-017 | P4 | For a `*man`-family consumer, the default required gate is the Testee verification that `gitman.toml` already declares before publication. | Consumer | V4-REVIEW F-02; `gitman.toml`, `nix/testee.nix` | Inspect the effective gate set of a `*man` consumer; find the existing Testee gate named, and no parallel Vendomat runner. |

### Inspection source

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-SRC-001 | P3 | Discovery lists selected modules and candidate direct dependency sources without requiring capture. | Source store | V4 §§11–12 | Inventory a consumer with capture disabled; inspect listed selections. |
| V4-SRC-002 | P3 | Capture retains selected owned module source outside disposable read views. | Source store | V4 §§11–12 | Delete read view; restore it from retained object and verify bytes. |
| V4-SRC-003 | P3 | Capture retains the first-proof consumer's listed third-party direct dependency. | Source store | D-CAPTURE; V4 §§12, 21 | Run capture stage; verify listed dependency's native revision or archive hash. |
| V4-SRC-004 | P3 | Each capture record names native source identity and its consumer selection. | Source store | V4 §11 | Inspect captured module and dependency records against locks. |
| V4-SRC-005 | P3 | An archive hash names its algorithm and hashed representation. | Source store | V4 §11 | Capture a compressed archive; verify recorded hash against those exact bytes. |
| V4-SRC-006 | P3 | Capture status and correspondence level appear as separate fields. | Source store | V4 §11 | Retain an upstream-only reference; observe `retained` with non-exact correspondence. |
| V4-SRC-007 | P3 | Packaging patches and known transformations appear beside selected source. | Source store | V4 §11 | Use a patched package; inspect source and patch references together. |
| V4-SRC-008 | P3 | An unavailable inspection source reports a gap without blocking a valid artifact check. | Vendomat | V4 §§11, 14, 20 | Make inspection source unavailable; pass artifact checks and inspect separate outcomes. |
| V4-SRC-009 | P3 | A mismatched inspection object cannot receive an exact-correspondence claim. | Source store | V4 §§11, 20 | Corrupt retained bytes; query correspondence and failure evidence. |
| V4-SRC-010 | P4 | A required build-source identity mismatch fails build validation. | Nix build/check | V4 §§14, 20 | Supply wrong fixed-output bytes; observe native validation failure and no publication success. |
| V4-SRC-011 | P3 | Read access returns a readable tree with provenance for the selected revision. | Source store | V4 §11 | Query from project context; open file and inspect locator, revision, and relationship. |
| V4-SRC-012 | P3 | Read access cannot mutate archive objects or consumer selection. | Source store | V4 §11 | Try writes through read view; verify denial and unchanged hashes/locks. |
| V4-SRC-013 | When offered | An index or summary identifies the source identities used to create it. | Source store | V4 §§5, 12 | Change selected source; observe stale marker or regenerated derived data. Deferred from P3: V4 §12 policy item 5 expands indexing only when real searches justify it. |
| V4-SRC-014 | When offered | Missing derived views can be regenerated without recapturing retained source. | Source store | V4 §§11–12, 20 | Delete index and view; regenerate and compare source identity. Deferred from P3 for the same reason as V4-SRC-013. |
| V4-SRC-015 | P3 | Source capture alone makes no archive-backed rebuild claim. | Vendomat | V4 §§11, 19, 23 | Inspect a capture-only receipt; rebuild proof field remains absent or false. |
| V4-SRC-016 | P3 | Project evaluation succeeds when the remote inspection tree is unmounted. | Consumer | V4 §11 | Unmount or deny source-store network path; evaluate accepted project. |
| V4-SRC-017 | P3 | Application startup succeeds when the remote inspection tree is unmounted. | Native application | V4 §11 | Unmount or deny source-store network path; start accepted application. |
| V4-SRC-018 | P3 | A client on the private network can read selected source and provenance without write access. | Source store | V4 §11; D-SRC-ACCESS | Read from a second host over the read-only export; read file and record; attempt write and verify denial at the export's permissions, not at an application layer. |
| V4-SRC-019 | P3 | A consumer can list selected direct dependencies for automatic source capture, using the existing reviewed catalog. | Consumer | D-CAPTURE; V4 §12 | Declare one selected direct dependency in `vendor/python/*.toml`; inspect the effective capture policy. The representation already exists and is validated by `src/vendomat/catalog.py`. |
| V4-SRC-020 | P3 | The capture stage automatically retains each listed selected direct dependency it can obtain. | Source store | D-CAPTURE; V4 §12 | List two available direct dependencies; run the existing `vendomat vendor sync` stage; verify both retained identities. |
| V4-SRC-021 | P3 | A capture-list entry cannot select or change a dependency revision. | Vendomat | D-CAPTURE; V4 §§3, 12 | Change list entry without native lock change; verify selected revision remains native. |
| V4-SRC-022 | P3 | Unlisted direct dependencies remain discoverable without automatic capture. | Source store | D-CAPTURE; V4 §12 | Inventory one unlisted direct dependency; verify discovery record and absent capture. |
| V4-SRC-023 | P3 | An entry that does not match a selected direct dependency reports a policy gap. | Vendomat | D-CAPTURE; V4 §12 | Add stale entry; inspect diagnostic and unchanged native selection. The shipped `vendomat vendor doctor` already reports this shape. |
| V4-SRC-024 | P3 | Source read access is a read-only filesystem export. No Vendomat daemon runs for reading, capture, or lookup. | Source store | D-SRC-ACCESS | Stop every Vendomat process; read selected source and provenance over the export; capture and lookup use commands, not a service. |
| V4-SRC-025 | P3 | Capture adds correspondence and status labels to the existing reviewed catalog without changing its schema authority or its immutable revision field. | Source store | D-CAPTURE; existing `vendor/python/*.toml` and `src/vendomat/catalog.py` | Add labels to a catalog entry; re-validate with the existing catalog validator; confirm the 40-character revision remains the single reviewed identity. |

Nix distinguishes an output's runtime closure from a derivation's build inputs. The inventory fixture must preserve this distinction. [Nix store query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query).

### Attic and cold consumption

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-CACHE-001 | P5 | Publication pushes the exact checked output path. | Vendomat | V4 §§13–14, 24 | Compare check, push, and receipt output paths byte for byte. |
| V4-CACHE-002 | P5 | Publication covers the selected output and every closure path that no trusted configured substituter already serves. | Vendomat | V4 §§13–14, 24; D-ATTIC-SCOPE | Enumerate the closure; partition it by which configured substituter serves each path; query the remainder with `nix path-info --store <endpoint>` or substitute it into an isolated store. The Attic command-line interface documents no cache-presence query. |
| V4-CACHE-003 | When offered | Closure coverage includes dependencies first obtained from public caches. | Vendomat | V4 §§13, 21, 25; D-ATTIC-SCOPE | Seed build host from public cache; push with `--ignore-upstream-cache-filter`; isolate consumer to Attic; realize the full closure. Deferred from P5 to a measurement: D-ATTIC-SCOPE removed the disconnected-operation goal this gate served. |
| V4-CACHE-004 | P5 | Publication records its decision about Attic's upstream filter, and the default filter remains enabled unless a measured goal requires otherwise. | Vendomat | V4 §§13, 25; D-ATTIC-SCOPE | Inspect the receipt for the recorded filter decision. Attic documents that paths signed with an upstream cache key "will be skipped by default", which D-ATTIC-SCOPE now wants. |
| V4-CACHE-005 | P5 | A successful upload command without availability proof cannot report complete publication. | Vendomat | V4 §§13–15 | Simulate missing closure member after push; inspect failure result. |
| V4-CACHE-006 | P5 | Partial upload records completed paths and can retry the same selection safely. | Vendomat | V4 §20 | Interrupt upload; retry; verify no false prior success and complete final check. |
| V4-CACHE-007 | P5 | An upload failure preserves the local realized output. | Nix local store | V4 §20 | Deny Attic upload; run local output after failure. |
| V4-CACHE-008 | P5 | Cache publication does not change consumer locks or accepted dependency state. | Vendomat | V4 §§13, 17, 24 | Publish candidate; compare active native files before and after. |
| V4-CACHE-009 | P5 | A cold laptop realizes the expected output without building it, and the evidence names which substituter served each path. | Nix consumer | V4 §§14, 21 | Use a clean store, disable builds, record the serving substituter per path, then run the output. |
| V4-CACHE-010 | P5 | Substituter selection matches the caches' advertised priority values, as recorded in the P0 policy. | NixOS and Attic | V4 §13; V4-REVIEW F-06 | Read each cache's advertised priority; realize a path; observe which cache served it. Nix documents that substituters "are tried based on their priority value, which each substituter can set independently", so client list order is not the control. |
| V4-CACHE-011 | P5 | Consumer build fallback matches declared policy, and the policy sets `fallback` explicitly. | NixOS | V4 §13; V4-REVIEW F-07 | Confirm the recorded `fallback` value; its documented default is `false`. Block Attic and the public cache; test the permitted development build and the prohibited expensive build. `[PROTOTYPE]` Unreachable-substituter behavior is undocumented; probe it on the pin. |
| V4-CACHE-012 | P5 | Consumers trust only the configured Attic public key for Attic substitutions. | NixOS | V4 §13 | Attempt trusted and wrong-key substitutions; inspect Nix acceptance. |
| V4-CACHE-013 | P5 | Push credentials and signing secrets stay outside tracked files, Nix outputs, and receipts. | NixOS | V4 §§13, 15 | Scan fixture store paths, tracked outputs, and redacted receipt; inspect service credential source. |
| V4-CACHE-014 | P5 | Attic availability is checked as a current fact, separate from a historical receipt. | Vendomat | V4 §15 | Remove a cached path after success; fresh report changes current availability only. |
| V4-CACHE-015 | P5 | The Attic cache advertises a priority value lower than every configured public cache. | Attic and NixOS | V4 §13; V4-REVIEW F-06 | Read the advertised priority of the Attic cache and of every configured public cache; confirm the ordering. |
| V4-CACHE-016 | P5 | A closure path that no configured substituter serves produces a named failure, or a permitted build under the recorded policy. | NixOS | V4 §13; split from V4-CACHE-010 | Remove one path from every cache; realize the output; inspect the named outcome against the P0 policy. |
| V4-CACHE-017 | P5 | Publication keeps the store index and the release-URL index in agreement; one build yields one artifact in both. | Vendomat | V4-REVIEW F-05; `README.md` | Publish one build through both channels; compare the store path's artifact with the release asset byte for byte. |

Attic's push defaults and upstream filter are documented in the [Attic CLI](https://docs.attic.rs/reference/attic-cli.html). Nix defines closure queries, substituter priority, trust, and fallback in its [store query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query) and [configuration reference](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).

### Evidence, failure reporting, and restore

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-EVD-001 | P4 | A receipt records the exact selection and output identities. | Vendomat | V4 §15 | Compare receipt with frozen selection and Nix output query. |
| V4-EVD-002 | P4 | A receipt names each required gate task, its origin, input, result, and log reference. | Vendomat | V4 §15 | Run a mixed module-and-consumer gate fixture; inspect every gate task entry and its origin. |
| V4-EVD-003 | P5 | A receipt records Attic target, upload result, and availability verification time. | Vendomat | V4 §15 | Publish fixture; inspect receipt and current cache query. |
| V4-EVD-004 | P3 | A receipt links source coverage without treating missing inspection source as a failed artifact check. | Vendomat | V4 §§14–15 | Inject inspection gap; inspect distinct fields. |
| V4-EVD-005 | P4 | Failure logs identify the failed stage and useful side effects. | Vendomat | V4 §§15, 20 | Fail build, check, and push in separate runs; inspect retained records. |
| V4-EVD-006 | P4 | Receipts exclude credentials and unrestricted environment dumps. | Vendomat | V4 §15 | Inject canary secret in environment; inspect receipt and stored logs. |
| V4-EVD-007 | P5 | Reports distinguish check success from current cache availability. | Vendomat | V4 §15 | Expire cache object after passed checks; compare fields. |
| V4-EVD-008 | P8 | Reports distinguish prepared, accepted, and activated states. | Vendomat | V4 §§15, 17 | Advance one proposal through each step; inspect state report. |
| V4-EVD-009 | P6 | Restored evidence explains prior check and upload results. | Vendomat | V4 §§15, 19 | Restore receipts and logs into fresh report store; inspect linked stages. |
| V4-EVD-010 | P6 | A cache signature does not set the independent-rebuild proof field. | Vendomat | V4 §15 | Import signed output without source build; inspect separate proof fields. |
| V4-REC-001 | P6 | Source restore verifies object identity and readable correspondence records. | Source store | V4 §19 | Restore archive and records; query selected source and verify hashes. |
| V4-REC-002 | P6 | Attic restore includes signing state and proves an existing consumer accepts an expected output. | Attic | V4 §19 | Restore cache and key; substitute from a clean trusted consumer. |
| V4-REC-003 | P6 | A failed source restore marks only the source recovery claim failed. | Vendomat | V4 §§19–20 | Corrupt source backup; inspect separate cache and source results. |
| V4-REC-004 | P6 | A failed cache restore marks only the cache recovery claim failed. | Vendomat | V4 §§19–20 | Remove signing state; inspect separate source and cache results. |
| V4-REC-005 | P6 | Initial V4 performs no automatic deletion from source archive or Attic. | Vendomat | V4 §19 | Run scheduled maintenance fixture; verify retained objects remain. |
| V4-REC-006 | P6 | Storage reports measure archive size and the published closure size under D-ATTIC-SCOPE. | Vendomat | V4 §§19, 25 | Capture and publish fixture; compare reported bytes with native storage queries. The measured closure is the published subset, not the complete runtime closure. |
| V4-REC-007 | P6 | An unreachable machine never counts as approval to delete its recovery paths. | Vendomat | V4 §19 | Make target unreachable during retention preview; verify its needs show unknown/protected. |
| V4-REC-008 | P6 | Cleanup of derived indexes or read views leaves retained archive identity intact. | Source store | V4 §19 | Delete derived data; verify archive hash and record survive. |
| V4-REC-009 | P0 | Each durable state class has a named storage and backup owner. | Owner | V4 §19 | Inspect P0 policy for source, evidence, Attic, and application data owners. |
| V4-REC-010 | P6 | Source retention and binary availability report separate results. | Vendomat | V4 §§15, 19 | Remove a test cache object while keeping source; inspect distinct fields. |
| V4-REC-011 | P6 | A cached output can remain valid when source correspondence is unresolved. | Vendomat | V4 §§15, 19 | Keep a signed output and force inspection gap; inspect distinct claims. |
| V4-REC-012 | P6 | Mutable application state remains outside immutable package outputs. | Native application | V4 §19 | Write application data; verify selected Nix output path remains unchanged. |

### Machine composition and native recovery

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-MACH-001 | P0 | One tested devenv executable and matching module revision are pinned for Machines. | Consumer | V4 §§10, 25 | Inspect native lock and executable/module versions in P0 report. |
| V4-MACH-002 | P1 | Module contracts identify project, NixOS, and Home Manager contributions separately. | Module repository | V4 §§4, 7, 22 | Evaluate each target and verify no project option is assumed to be a system option. |
| V4-MACH-003 | P7 | A native Machines plan identifies selected built output paths. | devenv Machines | V4 §10 | Produce plan; compare plan paths with native Nix outputs. |
| V4-MACH-004 | P7 | Vendomat evidence links to the native plan ID and checked paths. | Vendomat | V4 §§10, 15 | Inspect publication receipt and plan; compare IDs and paths. |
| V4-MACH-005 | P7 | Applying a saved valid plan uses its outputs without rebuilding. | devenv Machines | V4 §10 | Save plan, block build facility, apply; observe exact output use. |
| V4-MACH-006 | P7 | A stale native plan is rejected and reported without an alternate Vendomat apply path. | devenv Machines | V4 §§10, 20 | Change target generation or definition; apply old plan; inspect native rejection. |
| V4-MACH-007 | P7 | A new plan reuses past checks only when their recorded inputs still match. | Vendomat | V4 §10 | Change one check input after plan rejection; verify relevant check runs again. |
| V4-MACH-008 | P7 | Machine transfer evidence records the observed transfer path, which is a direct copy unless the pinned version documents a substituter route. | Vendomat | V4 §§10, 25; V4-REVIEW F-08 | Trace target Nix traffic during apply and label the observed path. Upstream documents that apply "copies all outputs", so a direct copy is the expected result, not a finding. |
| V4-MACH-009 | P7 | NixOS and Home Manager activation results appear separately. | Vendomat | V4 §§10, 15 | Fail Home Manager after successful NixOS role; inspect distinct statuses. |
| V4-MACH-010 | P7 | An unknown or pending NixOS activation is inspected before another deployment. | devenv Machines | V4 §§10, 20 | Interrupt controller confirmation; query native status before retry. |
| V4-MACH-011 | P7 | NixOS rollback reports its native outcome without claiming to undo application data. | Vendomat | V4 §§10, 19 | Fail health check after app writes; inspect system and app data separately. |
| V4-MACH-012 | P7 | A whole-system candidate test uses native build and activation or a VM where required. | NixOS | V4 §§10, 23 | Build VM fixture or apply native generation; verify service behavior. |
| V4-MACH-013 | P7 | `[OWNER DECISION]` Under standalone Home Manager, NixOS rollback does not report Home Manager files as restored. | Vendomat | V4 §§10, 19; V4-REVIEW F-09 | Fail user activation after system success, roll back the system, and inspect user files separately. Conditional on V4-MACH-015: as a NixOS module there may be no Home Manager profile at all, and the system profile references the Home Manager configuration. |
| V4-MACH-014 | P7 | A change to the pinned devenv revision re-runs the P7 gates before the next machine apply. | Consumer | V4-REVIEW F-08; V4 §10 | Change the pin; attempt an apply; observe that the machine gates run again. Machines is "new in devenv 2.4. The interface may change before it is declared stable." |
| V4-MACH-015 | P0 | The P0 record names the Home Manager integration mode: standalone, or a NixOS module. | Owner | V4-REVIEW F-09 | Inspect the P0 record; confirm one named mode and the rollback expectation that follows from it. |

Machines currently documents plan/apply identities, stale plan checks, NixOS watchdog limits, and separate Home Manager activation. [devenv Machines](https://devenv.sh/machines/). The [NixOS manual](https://nixos.org/manual/nixos/stable/) documents native generations and VM builds. [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html) has its own behavior.

### Reviewed upgrades and optional operations

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-UPG-001 | P8 | An upgrade proposal starts from a recorded consumer base in an isolated checkout. | Vendomat | V4 §17 | Prepare proposal; inspect base ID and confirm active tree unchanged. |
| V4-UPG-002 | P8 | Native tooling produces the proposed declaration and lock diff. | Native dependency tool | V4 §17 | Inspect diff and native update trace; find no Vendomat-selected revision database. |
| V4-UPG-003 | P8 | The proposal validates the exact changed composition. | Vendomat | V4 §17 | Modify diff after check; verify prior result cannot validate new diff. |
| V4-UPG-004 | P8 | A failed proposal preserves logs and leaves active files unchanged. | Vendomat | V4 §17 | Fail proposal check; compare active files and retained failure record. |
| V4-UPG-005 | P8 | A successful proposal may be cached without being accepted. | Vendomat | V4 §17 | Publish candidate; verify active declarations still select old output. |
| V4-UPG-006 | P8 | Acceptance checks base files still match the validated base. | Vendomat | V4 §17 | Change base file; acceptance rejects or requires revalidation. |
| V4-UPG-007 | P8 | Acceptance checks selected outputs remain available under the required policy. | Vendomat | V4 §17 | Remove cached output before acceptance; observe rejection or revalidation. |
| V4-UPG-008 | P8 | Acceptance applies only the validated native diff. | Vendomat | V4 §§17, 24 | Accept proposal; compare active diff, build logs, commits, and deployment status. |
| V4-UPG-009 | When offered | A managed hold records reason and date while native files remain selection authority. | Vendomat | V4 §17 | Add hold; inspect reason/date and native selected revision. |
| V4-OPT-001 | When offered | A release task cannot report success after a required gate failure. | Native task | V4 §18 | Inject failed release check; inspect task result and tag state. |
| V4-OPT-002 | When offered | A retry never moves an already published immutable tag to another commit. | Version control task | V4 §18 | Retry with different selection; observe rejection or new release identity. |
| V4-OPT-003 | When offered | A scheduled sweep may prepare proposals but never accepts or deploys them automatically. | Native timer and Vendomat | V4 §§17–18 | Run scheduled fixture; inspect native files and target activation. |
| V4-OPT-004 | When offered | A scaffold produces reviewable native source changes without duplicate editable settings. | Vendomat | V4 §16 | Generate fixture; inspect patch and setting authority. |

### First complete proof

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-PROOF-001 | P1 | The review command emits its documented meaningful result format. | Module repository | V4 §21 | Run command on known fixture; parse and compare expected findings. |
| V4-PROOF-002 | P1 | The Neovim interface displays the command's representative result. | Module repository | V4 §21 | Launch configured Neovim fixture and exercise review command. |
| V4-PROOF-003 | P2 | Both ordinary and flake-backed module exports work in clean consumers. | Module repository | V4 §21; D-PROOF-SPLIT | Evaluate and build one consumer of each delivery form, using the `*man` toolchain fixture, which already exports a flake-backed toolchain and already has a consumer check in `nix/consumer-module-check.nix`. |
| V4-PROOF-004 | P3 | The fixture exposes module and third-party source with correspondence labels. | Source store | V4 §21 | Query both selections and inspect labels and readable trees. |
| V4-PROOF-005 | P4 | A deliberate required-check failure blocks the selected output's success result. | Vendomat | V4 §21 | Inject failure and inspect publication result. |
| V4-PROOF-006 | P5 | A cold laptop runs the immutable published output and performs no build. | Nix consumer | V4 §21; D-ATTIC-SCOPE | Use a clean store with builds disabled; compare the output path, run the command, and record which substituter served each path. The Attic-only full-closure claim moved to V4-CACHE-003. |
| V4-PROOF-007 | P6 | Restored inspection storage preserves source identity. | Source store | V4 §21 | Restore backup and verify selected source records. |
| V4-PROOF-008 | P6 | Restored Attic storage preserves trusted substitution. | Attic | V4 §21 | Restore cache and signing state; substitute expected path on clean consumer. |
| V4-PROOF-009 | P5 | A cold `*man`-toolchain consumer realizes the published toolchain output and performs no build. | Nix consumer | D-PROOF-SPLIT | Use a clean store with builds disabled against `repoman-toolchain-core`; run one toolchain command; record the serving substituter. |
| V4-PROOF-010 | P0 | The P0 record states which fixture carries each phase gate. | Owner | D-PROOF-SPLIT | Inspect the P0 record; every phase names exactly one carrying fixture. |

## Conditional later-application requirements

These `C` IDs describe the requested Jujutsu–btrfs–bubblewrap case. They do **not** gate initial V4. Their source is the owner's application case and D-APP-SCOPE. Technical boundaries come from [Jujutsu identity](https://github.com/jj-vcs/jj/blob/main/docs/glossary.md), [Jujutsu conflicts](https://docs.jj-vcs.dev/latest/conflicts/), [btrfs subvolumes](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html), [bubblewrap](https://github.com/containers/bubblewrap/blob/main/bwrap.xml), [Attic](https://docs.attic.rs/reference/attic-cli.html), and [systemd services](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml).

| ID | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- |
| V4-APP-001 | The reusable application module composes focused Jujutsu, btrfs, and bubblewrap contributions. | Application module | Owner case; D-APP-SCOPE | Import only application module; inspect evaluated component contributions. |
| V4-APP-002 | The application exports a local devenv contribution. | Application module | Owner case; D-APP-SCOPE | Enter project shell and exercise local run without persistent machine activation. |
| V4-APP-003 | The application exports a NixOS contribution for persistent host needs. | Application module | Owner case; D-APP-SCOPE | Evaluate NixOS fixture; inspect service, storage, and permissions. |
| V4-APP-004 | A requested revset resolves to exactly one full Jujutsu commit ID before admission. | Jujutsu adapter | Owner case; D-APP-SCOPE | Request zero, one, and multiple revisions; only the single result proceeds. A commit ID is "20 bytes long when using the Git backend", that is 40 hexadecimal characters; "A divergent change is a change that has more than one visible commit." |
| V4-APP-005 | A queued or running request keeps its full commit ID when its change ID later moves. | Application module | Owner case; D-APP-SCOPE | Admit request, rewrite change, then compare executed commit ID. |
| V4-APP-006 | The adapter copies the pinned commit's file tree into a btrfs staging subvolume. | btrfs adapter | Owner case; D-APP-SCOPE | Materialize a commit; compare file contents, paths, modes, and symlinks. |
| V4-APP-007 | The adapter publishes only a fully verified read-only subvolume. | btrfs adapter | Owner case; D-APP-SCOPE | Interrupt materialization; ensure incomplete image cannot launch. |
| V4-APP-008 | A mapping record binds full commit ID, source manifest, filesystem UUID, subvolume UUID, and subvolume ID. | btrfs adapter | Owner case; D-APP-SCOPE | Materialize the same commit twice; inspect equal source identity and distinct physical identities. Inode numbers are not identity: a subvolume root "has always inode number 256". |
| V4-APP-009 | Unsupported or conflicted commit tree entries fail materialization explicitly. | btrfs adapter | Owner case; D-APP-SCOPE | Use conflicted, path-escape, and unsupported entry fixtures; inspect rejection. |
| V4-APP-010 | Reusing an image rechecks its mapping and read-only state. | btrfs adapter | Owner case; D-APP-SCOPE | Alter mapping or image mode; verify launch fails. |
| V4-APP-011 | The selected Nix runtime derives from native files and locks at the pinned commit or an exact verified mapping. | Application module | Owner case; D-APP-SCOPE | Run old commit after head runtime update; inspect old commit's runtime path. |
| V4-APP-012 | A missing or incompatible runtime selection fails before process launch. | Application module | Owner case; D-APP-SCOPE | Remove required runtime path; inspect failure and absence of process. |
| V4-APP-013 | Bubblewrap mounts the image read-only and one instance's state writable. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Attempt writes to image and state from inside; only state write succeeds. |
| V4-APP-014 | An instance cannot read another instance's writable state by default. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Start two instances; attempt cross-instance read from each sandbox. |
| V4-APP-015 | An instance cannot read host source archives or cache credentials by default. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Probe denied host paths from inside sandbox. |
| V4-APP-016 | Required sandbox setup failure prevents an unsandboxed launch, and the wrapper uses the non-`try` namespace options. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Deny namespace setup; verify no application process starts. Inspect the invocation for `--unshare-user-try` or `--unshare-cgroup-try`, which are documented to "skip it" on failure and would pass this test with weaker isolation. |
| V4-APP-017 | Each admitted instance has a unique ID and separate writable state. | Application module | Owner case; D-APP-SCOPE | Run two instances of one commit; compare IDs and independent writes. |
| V4-APP-018 | Two distinct commits can run concurrently on one host. | Application module | Owner case; D-APP-SCOPE | Start both; inspect simultaneous processes and pinned images. |
| V4-APP-019 | Two instances of one commit can run concurrently on one host. | Application module | Owner case; D-APP-SCOPE | Start both; inspect simultaneous processes and distinct state. |
| V4-APP-020 | Configured running and queued limits apply across all revisions of one application on a host. | Application module | Owner case; D-APP-SCOPE | Fill slots with mixed commits; inspect running and queued counts. |
| V4-APP-021 | A request beyond both limits receives an explicit capacity result and does not start. | Application module | Owner case; D-APP-SCOPE | Submit one excess request; inspect result and process list. |
| V4-APP-022 | A queued request retains its pinned commit and runtime selections until it starts or fails. | Application module | Owner case; D-APP-SCOPE | Queue request, change branch and lock, release slot, inspect executed IDs. |
| V4-APP-023 | Concurrent admission never exceeds the configured running or queued limits. | Application module | Owner case; D-APP-SCOPE | Race parallel requests against small limits; count accepted states. |
| V4-APP-024 | Supervisor restart cannot launch one accepted request twice. | Application module | Owner case; D-APP-SCOPE | Restart during queued and running work; compare durable instance IDs and processes. |
| V4-APP-025 | Instance state retention is independent of source, image, Nix output, and NixOS generation retention. | Application module | Owner case; D-APP-SCOPE | Change or roll back each domain; inspect retained instance data. |
| V4-APP-026 | A local run succeeds without a live Vendomat service or Attic publication. | Application module | Owner case; D-APP-SCOPE | Stop Vendomat, deny Attic, realize native inputs locally, run pinned commit. |
| V4-APP-027 | Attic publication covers selected Nix runtime outputs but makes no btrfs-image or mutable-state distribution claim. | Vendomat | Owner case; D-APP-SCOPE | Publish runtime; inspect receipt, remote cache, image, and state separately. |
| V4-APP-028 | A whole-system candidate uses native NixOS build and activation or a VM test. | NixOS | Owner case; D-APP-SCOPE | Change system module; perform native build/VM test, not only bubblewrap run. |
| V4-APP-029 | Invalid running or queued limit values fail configuration. | Application module | Owner case; D-APP-SCOPE | Set zero running or negative queued limit; inspect evaluation error. |
| V4-APP-030 | A running instance keeps its image available until it exits. | Application module | Owner case; D-APP-SCOPE | Attempt image cleanup during a run; verify image remains readable. |
| V4-APP-031 | A claimed rematerialization retains the exact commit object or a separately verified source copy, identified by tree identity rather than commit ID alone. | Jujutsu adapter | Owner case; D-APP-SCOPE | Remove commit and image; observe that the rematerialization claim fails unless a verified copy restores it. A commit ID identifies a commit, not a tree, and two commits can share one tree. |

The later module still needs decisions about queue durability, ordering, stopped-state retention, network access, and actual option names. These decisions do not block the V4 guide.

## Traceability map

The map lists all V4 sections. A section without an initial gate has a stated reason. IDs in a range are inclusive.

| Source | Requirement IDs or disposition |
| --- | --- |
| V4 §§1–2, purpose and decisions | V4-OWN-001–008, V4-OWN-012–013, V4-MOD-001–003 |
| V4 §3, ownership | V4-OWN-001–013; the RepoMan and Testee rows carry no gate of their own |
| V4 §4, reusable module | V4-MOD-001–007, V4-MOD-011–016, V4-CHK-008, V4-CHK-015 |
| V4 §5, applications, actions, context | V4-MOD-001–003, V4-SRC-011–012; V4-SRC-013–014 deferred; no global action registry gate |
| V4 §6, Neovim modules | V4-MOD-008–010, V4-CHK-003, V4-CHK-013, V4-PROOF-001–002 |
| V4 §7, native target composition | V4-OWN-006, V4-MOD-001–007, V4-MACH-002 |
| V4 §8, repository delivery | V4-OWN-001–002, V4-MOD-011–016, V4-PROOF-003 |
| V4 §9, daily development | V4-OWN-003–004, V4-SEL-001–002, V4-MOD-015 |
| V4 §10, Machines | V4-MACH-001–015, V4-OWN-011, V4-REC-007 |
| V4 §§11–12, inspection and coverage | V4-SRC-001–012, V4-SRC-015–025, V4-REC-001, V4-REC-008; V4-SRC-013–014 deferred |
| V4 §13, Attic, channels, and fallback | V4-CACHE-001–017, V4-REC-002 |
| V4 §14, exact checked publication | V4-SEL-003–009, V4-CHK-001–017, V4-CACHE-001–009 |
| V4 §15, evidence | V4-OWN-007, V4-CHK-014, V4-EVD-001–010, V4-CACHE-014, V4-REC-010–011 |
| V4 §16, tasks and generated files | V4-OWN-010, V4-CHK-001, V4-CHK-007, V4-CHK-016–017, V4-OPT-004 |
| V4 §17, reviewed upgrades | V4-UPG-001–009, V4-OPT-003 |
| V4 §18, releases and automation | V4-OPT-001–003, when offered |
| V4 §19, storage and recovery | V4-OWN-009, V4-REC-001–012, V4-MACH-011, V4-MACH-013 |
| V4 §20, failure behavior | V4-MOD-006–007, V4-CHK-004–012, V4-SRC-008–010, V4-CACHE-005–007, V4-CACHE-016, V4-MACH-006–011, V4-REC-003–004 |
| V4 §21, first complete proof | V4-PROOF-001–010 plus the P1–P6 requirement groups |
| V4 §22, sequence | Phase column in every mandatory requirement; V4-PROOF-010 records the fixture per phase; P9–P10 require measured need |
| V4 §23, boundaries | V4-OWN-001–013, V4-SRC-015, V4-MACH-012; excluded abstractions are not requirements to implement |
| V4 §25, technical proof | V4-MOD-008–016, V4-SRC-004–010, V4-MACH-001, V4-MACH-008, V4-MACH-014, V4-CACHE-002–004, V4-CACHE-010–011, V4-REC-006; see the experiment table below |
| V4 §26, references | Primary documentation cited next to relevant groups and in V4-SPEC.md |

### V4 §24 invariants, one row each

The earlier revision mapped §24 to nearly every ID, which traced nothing. Each invariant now names its gates.

| Invariant | Gates |
| --- | --- |
| 1. A module stays traceable to native files | V4-MOD-001, V4-SRC-002, V4-SRC-004 |
| 2. Native declarations and locks select dependencies | V4-OWN-001–002, V4-SRC-021 |
| 3. A module exposes distinct target contributions | V4-MOD-001, V4-MACH-002 |
| 4. Defaults stay overridable; conflicts are reported | V4-MOD-004–007 |
| 5. Ordinary use needs no live Vendomat service; inspection needs no daemon | V4-OWN-003–004, V4-SRC-016–017, V4-SRC-024 |
| 6. Local overrides stay visible and separate | V4-SEL-001–003 |
| 7. Source inspection records identity and correspondence | V4-SRC-004–007, V4-SRC-009 |
| 8. Inspection gaps do not block valid publication | V4-SRC-008, V4-EVD-004 |
| 9. The seven facts stay separate | V4-SRC-015, V4-EVD-007, V4-EVD-010, V4-REC-010–011 |
| 10. A required gate task failure blocks publication | V4-CHK-004, V4-CHK-011, V4-CHK-016 |
| 11. Publication identifies the output and verifies the published subset | V4-CACHE-001–002, V4-CACHE-005, V4-CACHE-014 |
| 12. Publication changes no selection | V4-CACHE-008 |
| 13. Current facts come from native authorities | V4-OWN-007, V4-CACHE-014 |
| 14. Acceptance is explicit and performs nothing else | V4-UPG-008 |
| 15. Machine operations use the pin and respect its limits | V4-MACH-001, V4-MACH-005–006, V4-MACH-011, V4-MACH-014 |
| 16. Source and binary retention stay distinct | V4-REC-005, V4-REC-010 |
| 17. New abstraction must solve a demonstrated problem | V4-OWN-002, V4-OWN-013 |

### Decisions

| Decision | Requirement IDs or disposition |
| --- | --- |
| D-APP-SCOPE, accepted 2026-10-04 | V4-APP-001–031 are conditional later-module requirements |
| D-NAMES, accepted 2026-10-04 | No proposed option or command name is a binding V4 interface |
| D-CHECK-OWNER, accepted 2026-10-04 | V4-CHK-008–011, V4-CHK-013–014, V4-CHK-016–017 |
| D-CHECK-GAP, accepted 2026-10-04 | V4-CHK-005, V4-CHK-012, V4-CHK-015 |
| D-CAPTURE, accepted 2026-10-04 | V4-SRC-003, V4-SRC-019–023, V4-SRC-025 |
| D-ATTIC-SCOPE, accepted 2026-10-04 | V4-CACHE-002–004, V4-CACHE-009–011, V4-CACHE-015–016, V4-PROOF-006, V4-REC-006 |
| D-SRC-ACCESS, accepted 2026-10-04 | V4-SRC-018, V4-SRC-024 |
| D-PROOF-SPLIT, accepted 2026-10-04 | V4-PROOF-003, V4-PROOF-009–010 |
| Owner's Jujutsu–btrfs–bubblewrap case | V4-APP-001–031 |

### Repository surfaces this review added

| Source | Requirement IDs |
| --- | --- |
| `AGENTS.md` and `docs/DESIGN.md` composition ownership | V4-OWN-013 |
| Delivered consumer surface: `modules/devenv.nix`, `machine.json`, `src/vendomat/plane.py` | V4-OWN-012 |
| `README.md` evaluation cost rule | V4-MOD-015 |
| `README.md` two-index publication rule | V4-CACHE-017 |
| `gitman.toml` and `nix/testee.nix` existing gate | V4-CHK-017 |
| `vendor/python/*.toml` and `src/vendomat/catalog.py` | V4-SRC-019–020, V4-SRC-025 |
| `docs/SOURCE_CATALOG.md` plain-directory store | V4-SRC-024 |

## Open questions, assumptions, and experiments

| ID | Status | Decision or proof needed | Affected IDs |
| --- | --- | --- | --- |
| Q-COMPOSE-OWNER | **Open owner decision** | Decide whether Vendomat owns composition, against `AGENTS.md` and `docs/DESIGN.md`. | V4-OWN-007, V4-OWN-013 |
| Q-SURFACE | **Open owner decision** | Decide the disposition of `vendomat plane`, the devman plane, and the installed `machine.json` consumer path. | V4-OWN-011–012 |
| Q-HM-MODE | **Open owner decision** | Name the Home Manager integration mode. | V4-MACH-013, V4-MACH-015 |
| P-GATE-CARRIER | P4 experiment | Prove that a module declares gate task names and a consumer appends to them, using only named devenv tasks. | V4-CHK-008–011, V4-CHK-014, V4-CHK-016–017 |
| P-CHECK-COVERAGE | P4 experiment | Prove how a module expresses expected coverage for behavior it enables, without new metadata. Narrowed: the carrier is settled. | V4-CHK-005, V4-CHK-015 |
| P-CAPTURE-LIST | **Resolved by existing code** | `vendor/python/*.toml` with `src/vendomat/catalog.py` is the reviewable declaration. The P3 fixture now proves the correspondence-label extension and the selected, unlisted, and stale entry cases. | V4-SRC-019–023, V4-SRC-025 |
| Q-QUEUE | Later module | Decide queue durability, order, count owner, and restart policy. | V4-APP-020–024 |
| Q-APP-STATE | Later module | Decide stopped-instance retention and backup. | V4-APP-017, V4-APP-025 |
| Q-APP-NET | Later module | Decide permitted network, devices, and interprocess communication. | V4-APP-013–016 |
| Q-NAMES | Open by accepted decision | Prove a useful configuration surface before fixing proposed names. | All proposed module options |
| P-DELIVERY | P2 experiment | Prove transitive flake inputs and the minimal plain-consumer input contract. Compare any helper with explicit native files, and compare both with `inputs.<name>.devenv.config`. | V4-MOD-011–013, V4-MOD-016 |
| P-PROFILES | P2 experiment, **reduced** | Test profiles and overrides on the paths devenv supports. Upstream already documents that profiles do not work with cross-project references. | V4-MOD-014, V4-SEL-009 |
| P-EDITOR | P1 experiment | Test shared plugin and dedicated editor configuration isolation. | V4-MOD-008–010 |
| P-SOURCE | P3 experiment | Test native metadata for selected source and patches. | V4-SRC-004–010 |
| P-ATTIC | P5 experiment, **reduced** | Prove the cold consumer performs no build, and that the Attic-side advertised priority makes Attic win. Attic's default upstream filter is now the wanted behavior. | V4-CACHE-002, V4-CACHE-004, V4-CACHE-009–010, V4-CACHE-015 |
| P-SUBSTITUTER-OUTAGE | P5 experiment | Prove what Nix does when a configured substituter is unreachable. The configuration reference does not define it. | V4-CACHE-011, V4-CACHE-016 |
| P-MACHINES | P7 experiment, **narrowed** | Determine whether the pinned version can prefer a target-side substituter. Apply is documented to copy all outputs. | V4-MACH-008, V4-MACH-014 |
| P-HM-ROLLBACK | P7 experiment | Prove rollback behavior in the chosen Home Manager mode. The activation reference documents no rollback mechanism. | V4-MACH-009, V4-MACH-013 |
| P-STORAGE | P3–P7 measurement | Measure source growth, published closure size, and transfer cost. | V4-REC-006 |
| P-IMAGE | Later module | Prove exact tree materialization, mode handling, conflict rejection, and atomic image publication. | V4-APP-006–010 |
| P-SANDBOX | Later module | Prove required bubblewrap namespaces and bind policy on selected hosts, using the non-`try` options. | V4-APP-013–016 |

Assumptions for initial fixtures: the owner supplies one desktop publisher, one cold laptop, a private Attic endpoint, and a pinned Machines-capable devenv revision of 2.4 or later (V4 §§10, 13, 21). The exact versions, host systems, storage paths, backup locations, Home Manager mode, `fallback` value, advertised cache priorities, and fixture-per-phase assignment remain P0 inputs. A result from current online documentation does not replace a test against that pinned toolchain.

## Readiness for a later implementation guide

These requirements can structure a separate implementation guide, with three conditions.

First, three owner decisions remain open: Q-COMPOSE-OWNER, Q-SURFACE, and Q-HM-MODE. A guide must not turn any of them into an interface. V4-OWN-011, V4-OWN-013, and V4-MACH-013 carry `[OWNER DECISION]` until they are answered.

Second, the required-check carrier is now named — a module declares gate task names and the consumer appends to them — but P-GATE-CARRIER has not run. A guide may specify that carrier, because devenv documents no alternative. It must not specify a coverage-metadata format before P-CHECK-COVERAGE passes.

Third, the guide must start with P0 and the named proof gates. It must not fix unproved export syntax, coverage metadata, source-mapping rules, target-side substitution behavior, Home Manager rollback behavior, or application queue internals before their fixtures pass. It may rely on the five facts primary documentation settled and the two the existing code settled; both lists are in V4 §25.

The owner policy choices for checks, coverage gaps, initial capture, Attic scope, source access, and the proof split are resolved. The later application case is illustrative and does not delay the P1–P6 proof.

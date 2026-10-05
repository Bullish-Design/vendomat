# Vendomat V4 testable requirements

**Status:** Draft for owner review, 2026-10-04.  
**Authority:** [V4 concept](./CONCEPT-V4.md). [V4 specification](./V4-SPEC.md) states the system contract.  
**Rule:** An ID is stable. Add new IDs; do not reuse or renumber old IDs.

`M` requirements gate the stated V4 phase or apply whenever that V4 feature is offered. `C` requirements apply only to the later Jujutsu–btrfs–bubblewrap module. The owner accepted that scope as **D-APP-SCOPE** on 2026-10-04. The owner accepted semantics-first naming as **D-NAMES**. New option and command names remain proposed.

Each verification method describes an observable result for a later fixture. It does not assert that V4 already implements the behavior. Phase labels follow V4 §22. P1–P6 form the first complete Neovim proof; P7 covers Machines; P8 covers one reviewed upgrade. P9–P10 require a separate measured need. The conditional application has no V4 phase gate.

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
| V4-OWN-007 | P1 | Current selection reports come from native files and evaluated state. | Vendomat | V4 §15 | Change a native option; refresh report; observe new effective value without editing a Vendomat database. |
| V4-OWN-008 | P1 | Vendomat does not require project registration for normal module use. | Vendomat | V4 §§8–9 | Import a module in a new consumer and enter it without registering the project elsewhere. |
| V4-OWN-009 | P0 | The deployment record names tested host systems, storage owners, backup locations, and native cache fallback policy. | Consumer | V4 §§13, 19, 22 | Inspect P0 record against fixture hosts and native settings. |
| V4-OWN-010 | P1 | Project-local pipeline stages run through devenv tasks and focused native helpers. | devenv | V4 §16 | Trace a publication fixture; observe task prerequisites and native stage results. |
| V4-OWN-011 | P7 | Machine activation delegates to the pinned Machines implementation and its plan. | Vendomat | V4 §§10, 23 | Trace apply; compare native plan ID and target activation; find no second plan path. |

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
| V4-MOD-013 | P2 | Neither delivery path assumes recursive import of a remote `devenv.yaml`. | Module repository | V4 §8 | Give the remote author YAML an extra input; verify the consumer needs the documented explicit delivery path. |
| V4-MOD-014 | P2 | Each supported profile and local override path has a recorded effective selection. | devenv | V4 §§8–9, 25 | Evaluate a profile/override matrix and compare reported inputs and outputs with native evaluation. |

The delivery gates rely on current [devenv imports](https://devenv.sh/composing-using-imports/), [polyrepo limits](https://devenv.sh/guides/polyrepo/), and [native inputs](https://devenv.sh/inputs/). Exact export syntax remains a prototype result.

### Exact selections and checks

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-SEL-001 | P2 | A local override is visible in the effective selection report. | Vendomat | V4 §§9, 24 | Select a local module checkout; inspect report and output change. |
| V4-SEL-002 | P2 | One consumer's local override does not change a second consumer's accepted lock. | Consumer | V4 §§9, 24 | Override consumer A; compare consumer B lock and evaluated path. |
| V4-SEL-003 | P4 | A publication selection identifies an immutable consumer revision or exact diff against a recorded base. | Vendomat | V4 §14 | Attempt publication from an unrecorded mutable checkout; verify it cannot receive an immutable success claim. |
| V4-SEL-004 | P4 | A selection records native declaration and lock identities. | Vendomat | V4 §14 | Inspect receipt; compare recorded digests to the selected consumer files. |
| V4-SEL-005 | P4 | A selection records requested output attribute, target system, profiles, and overrides. | Vendomat | V4 §14 | Vary each field separately; observe distinct records and evaluated selections. |
| V4-SEL-006 | P4 | A selection records effective module sources, derivation, and realized output paths. | Vendomat | V4 §14 | Compare selection record with native evaluation and Nix store queries. |
| V4-SEL-007 | P4 | Publication rejects identity drift between checked and uploaded outputs. | Vendomat | V4 §§14, 24 | Change a lock or output after checks; verify upload success is withheld. |
| V4-SEL-008 | P4 | A pure configuration module can publish its selected composed output without a separate module binary. | Vendomat | V4 §14 | Publish an application composed from a configuration-only module; verify output identity. |
| V4-CHK-001 | P4 | Required pre-build checks run before the selected output is built. | devenv task | V4 §§14, 16 | Instrument fixture order; fail a pre-build check and observe no build success. |
| V4-CHK-002 | P4 | Required artifact checks run against the realized selected output. | Module repository | V4 §14 | Replace a test input with another output path; gate rejects identity mismatch. |
| V4-CHK-003 | P4 | Required consumer integration checks exercise the selected composition. | Consumer | V4 §§6, 14, 21 | Run the command through the project and editor fixtures against the chosen path. |
| V4-CHK-004 | P4 | A failed required check prevents successful publication. | Vendomat | V4 §§14, 20, 24 | Inject a deterministic failed gate; observe no success receipt or complete-publication claim. |
| V4-CHK-005 | P4 | An absent relevant check appears as a coverage gap. | Vendomat | V4 §§14, 20 | Remove editor integration check; inspect coverage report. |
| V4-CHK-006 | P4 | A failed build retains diagnostic logs and cannot report publication success. | Vendomat | V4 §§14, 20 | Break derivation; inspect failure record and absence of success result. |
| V4-CHK-007 | P4 | An idempotent stage verifies the state it reuses. | Vendomat helper | V4 §16 | Re-run with an existing output but changed check evidence; stage reruns or fails rather than skipping. |

### Inspection source

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-SRC-001 | P3 | Discovery lists selected modules and candidate direct dependency sources without requiring capture. | Source store | V4 §§11–12 | Inventory a consumer with capture disabled; inspect listed selections. |
| V4-SRC-002 | P3 | Capture retains selected owned module source outside disposable read views. | Source store | V4 §§11–12 | Delete read view; restore it from retained object and verify bytes. |
| V4-SRC-003 | P3 | Capture retains an identifiable important direct dependency in the first fixture. | Source store | V4 §§12, 21 | Capture fixture dependency; verify native revision or archive hash. |
| V4-SRC-004 | P3 | Each capture record names native source identity and its consumer selection. | Source store | V4 §11 | Inspect captured module and dependency records against locks. |
| V4-SRC-005 | P3 | An archive hash names its algorithm and hashed representation. | Source store | V4 §11 | Capture a compressed archive; verify recorded hash against those exact bytes. |
| V4-SRC-006 | P3 | Capture status and correspondence level appear as separate fields. | Source store | V4 §11 | Retain an upstream-only reference; observe `retained` with non-exact correspondence. |
| V4-SRC-007 | P3 | Packaging patches and known transformations appear beside selected source. | Source store | V4 §11 | Use a patched package; inspect source and patch references together. |
| V4-SRC-008 | P3 | An unavailable inspection source reports a gap without blocking a valid artifact check. | Vendomat | V4 §§11, 14, 20 | Make inspection source unavailable; pass artifact checks and inspect separate outcomes. |
| V4-SRC-009 | P3 | A mismatched inspection object cannot receive an exact-correspondence claim. | Source store | V4 §§11, 20 | Corrupt retained bytes; query correspondence and failure evidence. |
| V4-SRC-010 | P4 | A required build-source identity mismatch fails build validation. | Nix build/check | V4 §§14, 20 | Supply wrong fixed-output bytes; observe native validation failure and no publication success. |
| V4-SRC-011 | P3 | Read access returns a readable tree with provenance for the selected revision. | Source store | V4 §11 | Query from project context; open file and inspect locator, revision, and relationship. |
| V4-SRC-012 | P3 | Read access cannot mutate archive objects or consumer selection. | Source store | V4 §11 | Try writes through read view; verify denial and unchanged hashes/locks. |
| V4-SRC-013 | P3 | An index or summary identifies the source identities used to create it. | Source store | V4 §§5, 12 | Change selected source; observe stale marker or regenerated derived data. |
| V4-SRC-014 | P3 | Missing derived views can be regenerated without recapturing retained source. | Source store | V4 §§11–12, 20 | Delete index and view; regenerate and compare source identity. |
| V4-SRC-015 | P3 | Source capture alone makes no archive-backed rebuild claim. | Vendomat | V4 §§11, 19, 23 | Inspect a capture-only receipt; rebuild proof field remains absent or false. |
| V4-SRC-016 | P3 | Project evaluation succeeds when the remote inspection tree is unmounted. | Consumer | V4 §11 | Unmount or deny source-store network path; evaluate accepted project. |
| V4-SRC-017 | P3 | Application startup succeeds when the remote inspection tree is unmounted. | Native application | V4 §11 | Unmount or deny source-store network path; start accepted application. |
| V4-SRC-018 | P3 | A client on the private network can read selected source and provenance without write access. | Source store | V4 §11 | Query from second host; read file and record; attempt write and verify denial. |

Nix distinguishes an output's runtime closure from a derivation's build inputs. The inventory fixture must preserve this distinction. [Nix store query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query).

### Attic and cold consumption

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-CACHE-001 | P5 | Publication pushes the exact checked output path. | Vendomat | V4 §§13–14, 24 | Compare check, push, and receipt output paths byte for byte. |
| V4-CACHE-002 | P5 | Publication covers every path in the selected output's runtime closure. | Vendomat | V4 §§13–14, 24 | Enumerate closure and query each path against Attic alone. |
| V4-CACHE-003 | P5 | Closure coverage includes dependencies first obtained from public caches. | Vendomat | V4 §§13, 21, 25 | Seed build host from public cache; isolate consumer to Attic; substitute full closure. |
| V4-CACHE-004 | P5 | Publication accounts for Attic's configured upstream filter. | Attic configuration | V4 §§13, 25 | Enable upstream filter in fixture; verify Attic-only closure or record failure. |
| V4-CACHE-005 | P5 | A successful upload command without availability proof cannot report complete publication. | Vendomat | V4 §§13–15 | Simulate missing closure member after push; inspect failure result. |
| V4-CACHE-006 | P5 | Partial upload records completed paths and can retry the same selection safely. | Vendomat | V4 §20 | Interrupt upload; retry; verify no false prior success and complete final check. |
| V4-CACHE-007 | P5 | An upload failure preserves the local realized output. | Nix local store | V4 §20 | Deny Attic upload; run local output after failure. |
| V4-CACHE-008 | P5 | Cache publication does not change consumer locks or accepted dependency state. | Vendomat | V4 §§13, 17, 24 | Publish candidate; compare active native files before and after. |
| V4-CACHE-009 | P5 | A cold laptop substitutes the expected output without building it. | Nix consumer | V4 §§14, 21 | Use a clean store, disable builds, record Attic transfer, then run output. |
| V4-CACHE-010 | P5 | Consumer cache priority and public-cache fallback match declared native Nix policy. | NixOS | V4 §13 | Use distinct cache traces with Attic present, absent, and missing one path. |
| V4-CACHE-011 | P5 | Consumer build fallback matches declared policy for an unavailable cache. | NixOS | V4 §13 | Block Attic and public cache; test permitted development build and prohibited expensive build. |
| V4-CACHE-012 | P5 | Consumers trust only the configured Attic public key for Attic substitutions. | NixOS | V4 §13 | Attempt trusted and wrong-key substitutions; inspect Nix acceptance. |
| V4-CACHE-013 | P5 | Push credentials and signing secrets stay outside tracked files, Nix outputs, and receipts. | NixOS | V4 §§13, 15 | Scan fixture store paths, tracked outputs, and redacted receipt; inspect service credential source. |
| V4-CACHE-014 | P5 | Attic availability is checked as a current fact, separate from a historical receipt. | Vendomat | V4 §15 | Remove a cached path after success; fresh report changes current availability only. |

Attic's push defaults and upstream filter are documented in the [Attic CLI](https://docs.attic.rs/reference/attic-cli.html). Nix defines closure queries, substituter priority, trust, and fallback in its [store query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query) and [configuration reference](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).

### Evidence, failure reporting, and restore

| ID | Phase | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- | --- |
| V4-EVD-001 | P4 | A receipt records the exact selection and output identities. | Vendomat | V4 §15 | Compare receipt with frozen selection and Nix output query. |
| V4-EVD-002 | P4 | A receipt names each required check, its input, result, and log reference. | Vendomat | V4 §15 | Run mixed check fixture; inspect all required check entries. |
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
| V4-REC-006 | P6 | Storage reports measure archive size and selected closure size. | Vendomat | V4 §§19, 25 | Capture and publish fixture; compare reported bytes with native storage queries. |
| V4-REC-007 | P6 | An unreachable machine never counts as approval to delete its recovery paths. | Vendomat | V4 §19 | Make target unreachable during retention preview; verify its needs show unknown/protected. |
| V4-REC-008 | P6 | Cleanup of derived indexes or read views leaves retained archive identity intact. | Source store | V4 §19 | Delete derived data; verify archive hash and record survive. |
| V4-REC-009 | P0 | Each durable state class has a named storage and backup owner. | Consumer | V4 §19 | Inspect P0 policy for source, evidence, Attic, and application data owners. |
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
| V4-MACH-008 | P7 | Machine transfer evidence distinguishes Attic substitution from direct build-host copy. | Vendomat | V4 §§10, 25 | Trace target Nix traffic during apply; label observed path correctly. |
| V4-MACH-009 | P7 | NixOS and Home Manager activation results appear separately. | Vendomat | V4 §§10, 15 | Fail Home Manager after successful NixOS role; inspect distinct statuses. |
| V4-MACH-010 | P7 | An unknown or pending NixOS activation is inspected before another deployment. | devenv Machines | V4 §§10, 20 | Interrupt controller confirmation; query native status before retry. |
| V4-MACH-011 | P7 | NixOS rollback reports its native outcome without claiming to undo application data. | Vendomat | V4 §§10, 19 | Fail health check after app writes; inspect system and app data separately. |
| V4-MACH-012 | P7 | A whole-system candidate test uses native build and activation or a VM where required. | NixOS | V4 §§10, 23 | Build VM fixture or apply native generation; verify service behavior. |
| V4-MACH-013 | P7 | NixOS rollback does not report Home Manager files as restored. | Vendomat | V4 §§10, 19 | Fail user activation after system success, roll back system, and inspect user files separately. |

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
| V4-PROOF-003 | P2 | Both ordinary and flake-backed module exports work in clean consumers. | Module repository | V4 §21 | Evaluate and build one consumer of each delivery form. |
| V4-PROOF-004 | P3 | The fixture exposes module and third-party source with correspondence labels. | Source store | V4 §21 | Query both selections and inspect labels and readable trees. |
| V4-PROOF-005 | P4 | A deliberate required-check failure blocks the selected output's success result. | Vendomat | V4 §21 | Inject failure and inspect publication result. |
| V4-PROOF-006 | P5 | A cold laptop runs the immutable published output with an Attic-provided full closure. | Nix consumer | V4 §21 | Use clean store and Attic-only fixture; compare output path and run command/editor. |
| V4-PROOF-007 | P6 | Restored inspection storage preserves source identity. | Source store | V4 §21 | Restore backup and verify selected source records. |
| V4-PROOF-008 | P6 | Restored Attic storage preserves trusted substitution. | Attic | V4 §21 | Restore cache and signing state; substitute expected path on clean consumer. |

## Conditional later-application requirements

These `C` IDs describe the requested Jujutsu–btrfs–bubblewrap case. They do **not** gate initial V4. Their source is the owner's application case and D-APP-SCOPE. Technical boundaries come from [Jujutsu identity](https://github.com/jj-vcs/jj/blob/main/docs/glossary.md), [Jujutsu conflicts](https://docs.jj-vcs.dev/latest/conflicts/), [btrfs subvolumes](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html), [bubblewrap](https://github.com/containers/bubblewrap/blob/main/bwrap.xml), [Attic](https://docs.attic.rs/reference/attic-cli.html), and [systemd services](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml).

| ID | Required behavior | Owner | Source | Verification method |
| --- | --- | --- | --- | --- |
| V4-APP-001 | The reusable application module composes focused Jujutsu, btrfs, and bubblewrap contributions. | Application module | Owner case; D-APP-SCOPE | Import only application module; inspect evaluated component contributions. |
| V4-APP-002 | The application exports a local devenv contribution. | Application module | Owner case; D-APP-SCOPE | Enter project shell and exercise local run without persistent machine activation. |
| V4-APP-003 | The application exports a NixOS contribution for persistent host needs. | Application module | Owner case; D-APP-SCOPE | Evaluate NixOS fixture; inspect service, storage, and permissions. |
| V4-APP-004 | A requested revset resolves to exactly one full Jujutsu commit ID before admission. | Jujutsu adapter | Owner case; D-APP-SCOPE | Request zero, one, and multiple revisions; only single result proceeds. |
| V4-APP-005 | A queued or running request keeps its full commit ID when its change ID later moves. | Application module | Owner case; D-APP-SCOPE | Admit request, rewrite change, then compare executed commit ID. |
| V4-APP-006 | The adapter copies the pinned commit's file tree into a btrfs staging subvolume. | btrfs adapter | Owner case; D-APP-SCOPE | Materialize a commit; compare file contents, paths, modes, and symlinks. |
| V4-APP-007 | The adapter publishes only a fully verified read-only subvolume. | btrfs adapter | Owner case; D-APP-SCOPE | Interrupt materialization; ensure incomplete image cannot launch. |
| V4-APP-008 | A mapping record binds full commit ID, source manifest, and btrfs subvolume identity. | btrfs adapter | Owner case; D-APP-SCOPE | Materialize same commit twice; inspect equal source ID and distinct physical IDs. |
| V4-APP-009 | Unsupported or conflicted commit tree entries fail materialization explicitly. | btrfs adapter | Owner case; D-APP-SCOPE | Use conflicted, path-escape, and unsupported entry fixtures; inspect rejection. |
| V4-APP-010 | Reusing an image rechecks its mapping and read-only state. | btrfs adapter | Owner case; D-APP-SCOPE | Alter mapping or image mode; verify launch fails. |
| V4-APP-011 | The selected Nix runtime derives from native files and locks at the pinned commit or an exact verified mapping. | Application module | Owner case; D-APP-SCOPE | Run old commit after head runtime update; inspect old commit's runtime path. |
| V4-APP-012 | A missing or incompatible runtime selection fails before process launch. | Application module | Owner case; D-APP-SCOPE | Remove required runtime path; inspect failure and absence of process. |
| V4-APP-013 | Bubblewrap mounts the image read-only and one instance's state writable. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Attempt writes to image and state from inside; only state write succeeds. |
| V4-APP-014 | An instance cannot read another instance's writable state by default. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Start two instances; attempt cross-instance read from each sandbox. |
| V4-APP-015 | An instance cannot read host source archives or cache credentials by default. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Probe denied host paths from inside sandbox. |
| V4-APP-016 | Required sandbox setup failure prevents an unsandboxed launch. | Bubblewrap contribution | Owner case; D-APP-SCOPE | Deny namespace setup; verify no application process starts. |
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
| V4-APP-031 | A claimed rematerialization retains the exact commit object or a separately verified source copy. | Jujutsu adapter | Owner case; D-APP-SCOPE | Remove commit and image; observe that rematerialization claim fails unless verified copy restores it. |

The later module still needs decisions about queue durability, ordering, stopped-state retention, network access, and actual option names. These decisions do not block the V4 guide.

## Traceability map

The map lists all V4 sections. A section without an initial gate has a stated reason. IDs in a range are inclusive.

| Source | Requirement IDs or disposition |
| --- | --- |
| V4 §§1–3, purpose, decisions, ownership | V4-OWN-001–011, V4-MOD-001–003, V4-CACHE-001–014 |
| V4 §4, reusable module | V4-MOD-001–007, V4-MOD-011–014 |
| V4 §5, applications, actions, context | V4-MOD-001–003, V4-SRC-011–013; no global action registry gate |
| V4 §6, Neovim modules | V4-MOD-008–010, V4-CHK-003, V4-PROOF-001–002 |
| V4 §7, native target composition | V4-OWN-006, V4-MOD-001–007, V4-MACH-002 |
| V4 §8, repository delivery | V4-OWN-001–002, V4-MOD-011–014, V4-PROOF-003 |
| V4 §9, daily development | V4-OWN-003–004, V4-SEL-001–002 |
| V4 §10, Machines | V4-MACH-001–013, V4-OWN-011, V4-REC-007 |
| V4 §§11–12, inspection and coverage | V4-SRC-001–018, V4-REC-001, V4-REC-008 |
| V4 §13, Attic and fallback | V4-CACHE-001–014, V4-REC-002 |
| V4 §14, exact checked publication | V4-SEL-003–008, V4-CHK-001–007, V4-CACHE-001–009 |
| V4 §15, evidence | V4-OWN-007, V4-EVD-001–010, V4-CACHE-014, V4-REC-010–011 |
| V4 §16, tasks and generated files | V4-OWN-010, V4-CHK-001, V4-CHK-007, V4-OPT-004 |
| V4 §17, reviewed upgrades | V4-UPG-001–009, V4-OPT-003 |
| V4 §18, releases and automation | V4-OPT-001–003, when offered |
| V4 §19, storage and recovery | V4-OWN-009, V4-REC-001–012, V4-MACH-011, V4-MACH-013 |
| V4 §20, failure behavior | V4-MOD-006–007, V4-CHK-004–007, V4-SRC-008–010, V4-CACHE-005–007, V4-MACH-006–011, V4-REC-003–004 |
| V4 §21, first complete proof | V4-PROOF-001–008 plus P1–P6 requirement groups |
| V4 §22, sequence | Phase column in every mandatory requirement; P9–P10 require measured need |
| V4 §23, boundaries | V4-OWN-001–011, V4-SRC-015, V4-MACH-012; excluded abstractions are not requirements to implement |
| V4 §24, invariants | V4-OWN-001–011, V4-MOD-001–014, V4-SEL-001–008, V4-SRC-001–018, V4-CHK-001–007, V4-CACHE-001–014, V4-EVD-001–010, V4-MACH-001–013, V4-UPG-008, V4-REC-001–012 |
| V4 §25, technical proof | V4-MOD-008–014, V4-SRC-004–010, V4-MACH-001, V4-MACH-008, V4-CACHE-003–004, V4-REC-006; see open experiments below |
| V4 §26, references | Primary documentation cited next to relevant groups and in V4-SPEC.md |
| D-APP-SCOPE, accepted 2026-10-04 | V4-APP-001–031 are conditional later-module requirements |
| D-NAMES, accepted 2026-10-04 | No proposed option or command name is a binding V4 interface |
| Owner's Jujutsu–btrfs–bubblewrap case | V4-APP-001–031 |

## Open questions, assumptions, and experiments

| ID | Status | Decision or proof needed | Affected IDs |
| --- | --- | --- | --- |
| Q-CHECK-OWNER | Owner choice pending | Decide who declares required checks when module and consumer compose. | V4-CHK-001–005 |
| Q-CHECK-MISSING | Owner choice pending | Keep V4 §14's visible gap policy or amend it to block publication. | V4-CHK-005, V4-CACHE-005 |
| Q-CAPTURE | Owner choice pending | Define initial automatic direct-dependency capture rule. | V4-SRC-001–003 |
| Q-QUEUE | Later module | Decide queue durability, order, count owner, and restart policy. | V4-APP-020–024 |
| Q-APP-STATE | Later module | Decide stopped-instance retention and backup. | V4-APP-017, V4-APP-025 |
| Q-APP-NET | Later module | Decide permitted network, devices, and interprocess communication. | V4-APP-013–016 |
| Q-NAMES | Open by accepted decision | Prove a useful config surface before fixing proposed names. | All proposed module options |
| P-DELIVERY | P2 experiment | Prove transitive flake inputs and the minimal plain-consumer input contract. Compare any helper with explicit native files. | V4-MOD-011–013 |
| P-PROFILES | P2 experiment | Test active profiles and override propagation per supported path. | V4-MOD-014, V4-SEL-005 |
| P-EDITOR | P1 experiment | Test shared plugin and dedicated editor configuration isolation. | V4-MOD-008–010 |
| P-SOURCE | P3 experiment | Test native metadata for selected source and patches. | V4-SRC-004–010 |
| P-ATTIC | P5 experiment | Prove complete Attic-only runtime closure under selected upstream filter. | V4-CACHE-002–005 |
| P-MACHINES | P7 experiment | Observe native transfer and cache use on pinned devenv. | V4-MACH-005, V4-MACH-008 |
| P-STORAGE | P3–P7 measurement | Measure source growth, closure sizes, and transfer cost. | V4-REC-006 |
| P-IMAGE | Later module | Prove exact tree materialization, mode handling, conflict rejection, and atomic image publication. | V4-APP-006–010 |
| P-SANDBOX | Later module | Prove required bubblewrap namespaces and bind policy on selected hosts. | V4-APP-013–016 |

Assumptions for initial fixtures: the owner supplies one desktop publisher, one cold laptop, a private Attic endpoint, and a pinned Machines-capable devenv revision (V4 §§10, 13, 21). The exact versions, host systems, storage paths, backup locations, and fallback policy remain P0 inputs. A result from current online documentation does not replace a test against that pinned toolchain.

## Readiness for a later implementation guide

These requirements can structure a separate implementation guide. That guide must start with P0 and the named proof gates. It must not fix unproved export syntax, source-mapping rules, Attic verification commands, Machines transfer behavior, or application queue internals before their fixtures pass. The three pending owner policy choices above need explicit resolution before their related requirements become final acceptance criteria. The later application case is illustrative and does not delay the Neovim P1–P6 proof.

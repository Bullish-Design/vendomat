# Vendomat V4 testable requirements

**Date:** 2026-10-06. **Status:** Canonical. **Authority:** [V4-SPEC.md](./V4-SPEC.md) holds the
rules. Each row here names one observable result for a fixture.

**ID rule:** An ID string is permanent. Add new IDs. Never reuse and never renumber an ID. §3 holds
the complete history of all 184 earlier IDs.

**Active count:** 60. Each active row gates its stated phase. A row does not assert that V4 already
implements the behaviour.

**Not gates:** 24 IDs assert upstream behaviour, not Vendomat behaviour. They live in
[NATIVE-BASELINE.md](./NATIVE-BASELINE.md), observed once on the pin. 44 IDs live in
[LATER-APPLICATION.md](./LATER-APPLICATION.md) and [FUTURE-WORK.md](./FUTURE-WORK.md). 9 become
combined acceptance scenarios in the implementation guide.

## 1. Active requirements

### Ownership and local independence

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-OWN-002` | P1 | Vendomat introduces no dependency lock, resolver state, cached selection authority, or project registration. | Vendomat | Inspect generated files and the dependency update trace. Find only native declarations and locks as selection authorities. Import a module in a new consumer and enter it without registering the project. |
| `V4-OWN-003` | P1 | A project enters its accepted environment and runs an already realized output with no Vendomat process and no Attic. | devenv, Nix | Stop or remove any Vendomat process, deny Attic, enter the pinned shell, and run the realized output. |
| `V4-OWN-007` | P1 | Current selection reports come from native files and evaluated state. | Vendomat | Change one native option, refresh the report, and observe the new effective value with no Vendomat database edit. |
| `V4-OWN-009` | Record | The pin record names tested host systems, target systems, storage owners, restore routes, and the native cache fallback policy. | Consumer | Inspect the pin record against the fixture hosts and the effective native settings. This is a record obligation, not a phase gate. |
| `V4-OWN-013` | P2 | A fresh local consumer realizes and runs through native inputs with no Vendomat service and no Attic. | Consumer | Deny Vendomat and Attic. Realize under the recorded native source and fallback policy. Run the selected command. Record every external source used. Do not call this an offline rebuild. |

### Module contracts and delivery

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-MOD-001` | P1 | A module contract lists its supported native targets and exports, and identifies project, NixOS, and Home Manager contributions separately. | Module repository | Compare each listed export with its evaluated target output. Confirm no project option is assumed to be a system option. |
| `V4-MOD-002` | P1 | A consumer imports a reusable contribution without inheriting the author's development environment. | Module repository | Import only the review command. Add an author-only tool and process to the author shell. Confirm the consumer has neither. |
| `V4-MOD-005` | P1 | Enabling a target gives documented defaults, and a consumer can disable or override each component independently. | Module repository | Evaluate defaults with no overrides. Disable the editor while keeping the command, and run the command. Change one supported option and confirm only its intended output changes. |
| `V4-MOD-008` | P1 | The normal-editor plugin and the dedicated editor use the same review implementation. | Module repository | Exercise both forms and compare the packaged implementation identity. |
| `V4-MOD-009` | P1 | The editor interface invokes the selected command by absolute store path. | Module repository | Place a conflicting command earlier on `PATH`. Run the representative editor command in both forms. Both invoke the selected store path. |
| `V4-MOD-010` | P1 | The dedicated editor runs beside the owner's normal editor configuration. | Module repository | Launch both with distinct settings. Each retains its own expected configuration. |
| `V4-MOD-011` | P2 | A plain devenv export states every native input its consumer must supply. | Module repository | Remove one required input from the consumer. The diagnostic identifies the missing native input. Add an extra input to the author's `devenv.yaml` and confirm the remote consumer does not receive it. |
| `V4-MOD-012` | P2 | A flake-backed export makes its locked transitive inputs available to its module implementation. | Module repository | Use a clean consumer with one module selection. Evaluate and build with the locked transitive input. Confirm a lock entry alone does not enable the module. |

### Selection

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-SEL-001` | P2 | A local override is visible in the effective selection report, with its path, profile, and override named. | Vendomat | Select a local module checkout. Compare the report with native evaluation. Revert the override and confirm the prior result returns. |
| `V4-SEL-002` | P2 | One consumer's local override does not change a second consumer's accepted lock. | Consumer | Override consumer A. Compare consumer B's lock and evaluated output path before and after. |
| `V4-SEL-003` | P4 | A publication selection identifies an immutable consumer revision, or one exact recorded diff against a recorded base. | Vendomat | Attempt publication from an unrecorded mutable checkout. Confirm it cannot receive an immutable success claim. |
| `V4-SEL-006` | P4 | The selection records module sources, derivation, realized output paths, NAR hashes, requested attribute, target system, profiles, and overrides, as stored native documents. | Vendomat | Compare each stored document with a fresh native query. Vary each field separately and observe distinct records and selections. |
| `V4-SEL-007` | P4 | Publication rejects identity drift between the checked output and the uploaded output. | Vendomat | Change a lock, derivation, output path, or checked NAR hash after the checks. Confirm success is withheld. |
| `V4-SEL-009` | P4 | A publishable selection evaluates with no access to undeclared host state. A selection that needs such state cannot be published, and the failure names the cause. | Vendomat | Evaluate with undeclared host access denied. Re-evaluate and compare the derivation path. Add a host-state read and confirm publication refuses with a named cause. |
| `V4-SEL-010` | P2 | A publishable selection resolves to a flake output attribute. | Vendomat | `nix build --json` returns the derivation path and every output path. `nix flake metadata --json` returns the complete `locks` graph. Record whether `devenv build` supplies an equivalent handle. |

### Checks

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-CHK-001` | P4 | Declared pre-build checks run before the selected output is built. | devenv task | Instrument the stage order. Fail a pre-build check and observe no build success. |
| `V4-CHK-002` | P4 | Declared artifact checks run against the realized selected output. | Module repository | Supply a different output path to an artifact check. The check fails identity validation. |
| `V4-CHK-004` | P4 | A declared required check that runs and fails blocks publication success with a `failed-required` result. | Vendomat | Inject a deterministic failed gate. Confirm no success receipt and no complete-publication claim. |
| `V4-CHK-006` | P4 | A failed build retains diagnostic logs and cannot report publication success, with its own reason. | Vendomat | Break the derivation. Inspect the failure record and the absence of a success result. |
| `V4-CHK-007` | P4 | An idempotent stage verifies the state it reuses, and a changed check input reruns its affected check. | Vendomat | Re-run with an existing output but changed check evidence. The stage reruns or fails rather than skipping. Confirm an existing output path alone is never success. |
| `V4-CHK-010` | P4 | The required set is one declared list: the union of enabled-module defaults and consumer-added checks. Each entry records its owner. | Vendomat | Enable and disable one component, and add one consumer check. Both run against the same frozen selection. Match each entry to its declaration. |
| `V4-CHK-011` | P4 | A declared required check that is absent or cannot run blocks success with a `missing-required` result, distinct from `failed-required`. | Vendomat | Check existence with `devenv tasks list --json` before running. Remove a declared check implementation. Separately remove a module's required-check declaration. Both give `missing-required` and no success receipt. |

### Source retention

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-SRC-002` | P3 | Retained source survives local Nix garbage collection through an explicit root. | Source retention | Add one root per archived path. Run local garbage collection in the fixture. Every archived path survives. |
| `V4-SRC-003` | P3 | Every locked native input of the selection is retained. | Source retention | Run `nix flake archive --json`. Compare the archived path set with the lock's complete input set. |
| `V4-SRC-004` | P3 | Each retained input has one identity record naming locator, locked revision, NAR hash, store path, and the consumer selection that chose it. | Source retention | Compare each record with `nix flake metadata --json` and the consumer lock. |
| `V4-SRC-006` | P3 | Capture status and correspondence level appear as separate fields. | Source retention | A locked input labels `retained` and exact selected source. A built package labels `unresolved`. Retain an upstream-only reference and observe `retained` with non-exact correspondence. |
| `V4-SRC-008` | P3 | A selected source with no retained object reports a coverage gap and does not block a valid artifact check. | Vendomat | Leave one selected package uncaptured. Pass the artifact checks. Inspect the two outcomes separately. |
| `V4-SRC-009` | P3 | A mismatched retained object cannot receive an exact-correspondence claim. | Source retention | Corrupt retained bytes. Query correspondence and inspect the preserved failure evidence. |
| `V4-SRC-011` | P3 | Reading retained source returns the file and its provenance, and changes no lock and no output path. | Source retention | Read from project context. Compare consumer locks and output paths before and after. Attempt a write and confirm the store denies it. |
| `V4-SRC-015` | P3 | Source retention alone makes no archive-backed rebuild claim, and a cache signature sets no rebuild field. | Vendomat | Inspect a retain-only record: the rebuild field is absent or false. Import a signed output without a source build and inspect the separate fields. |
| `V4-SRC-024` | P3 | Capture of a selected local source records an immutable content-addressed identity for the captured snapshot. | Source retention | Capture the working tree. Change local files. The retained object and its record still identify the captured bytes. |

### Attic publication and cold consumption

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-CACHE-001` | P5 | Publication pushes the exact checked output path. | Vendomat | Compare the check, push, and receipt output paths. |
| `V4-CACHE-002` | P5 | Publication covers every path in the selected output's runtime closure. | Vendomat | Enumerate the closure with `nix-store -qR`. Query each path from the cache alone. |
| `V4-CACHE-003` | P5 | Closure coverage includes dependencies the build host first obtained from a public cache. | Vendomat | Seed one dependency from a public cache. Clear the cache's upstream key list or pass `--ignore-upstream-cache-filter`. Confirm the seeded path is present afterwards. |
| `V4-CACHE-005` | P5 | A successful upload command without an availability check cannot report complete publication. | Vendomat | Remove one closure member after the push. Inspect the failure result. |
| `V4-CACHE-006` | P5 | A partial upload records its completed paths and retries the same selection safely. | Vendomat | Interrupt the upload. Retry. Confirm no false prior success and a complete final check. |
| `V4-CACHE-009` | P5 | A cold consumer substitutes the expected output without building it. | Nix consumer | Use a clean store with builds disabled. Record the transfer. Run the output. |
| `V4-CACHE-013` | P5 | Push credentials and signing secrets stay outside tracked files and Nix outputs, and a read-only token cannot push. | NixOS, Attic | Scan fixture store paths and tracked files. Create the pull token with `--pull` only and attempt a push with it. |
| `V4-CACHE-014` | P5 | Cache availability is reported as a current fact, separate from the historical receipt. | Vendomat | Remove a cached path after a passing run. The fresh report changes current availability only; the historical result is unchanged. |
| `V4-CACHE-015` | P5 | A cache-only cold substitution matches the checked output's NAR hash. | Vendomat | Substitute in an isolated store with other substituters and local builds disabled. Compare the served NAR hash with the checked hash. Record each closure member's metadata. |

### Evidence

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-EVD-001` | P4 | The receipt stores the four native documents verbatim and identifies the selection and its outputs. | Vendomat | Compare each stored document with a fresh native query and with the frozen selection. |
| `V4-EVD-002` | P4 | The receipt names each required check with its owner, input, result, and log reference, and classifies `failed-required`, `missing-required`, and the coverage statement separately. | Vendomat | Run a mixed fixture with one case of each. Inspect the distinct fields and outcomes. |
| `V4-EVD-003` | P5 | The receipt records the cache target, the upload result, and the closure availability verification with its time. | Vendomat | Publish the fixture. Inspect the receipt and compare with a fresh cache query. |
| `V4-EVD-005` | P4 | Failure evidence identifies the failed stage and its completed side effects. | Vendomat | Fail the build, a check, and the push in separate runs. Inspect each retained record. |
| `V4-EVD-006` | P4 | Receipts and preserved logs exclude credentials and unrestricted environment dumps. | Vendomat | Inject a canary secret into the environment. Inspect the receipt and every stored log. |
| `V4-EVD-009` | P6 | Restored evidence explains prior check and upload results. | Vendomat | Restore receipts and logs into a fresh location. Recreate the P4 and P5 reports and inspect the linked stages. |
| `V4-EVD-012` | P4 | The receipt records the tool version and JSON format of every stored native document. | Vendomat | Compare the recorded version and `--json-format` with the producing command. Re-read each stored document using the recorded format. |

### Recovery

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-REC-001` | P6 | Source restore verifies object identity and keeps provenance readable. A failed source restore marks only the source claim failed. | Source retention | Restore into a clean location. Compare NAR hashes with the records. Corrupt one backup and confirm only the source result fails. |
| `V4-REC-002` | P6 | Attic signing state restores, the output rebuilds from the retained source, and an existing trusted consumer accepts it. A missing signing state marks only the cache-trust claim failed. | Attic, Nix | Restore the signing state. Rebuild from a clean checkout of the retained source. Compare the output path and NAR hash with P4. Substitute from a clean trusted consumer. Remove the signing state and confirm only the cache-trust result fails. |
| `V4-REC-005` | P6 | Vendomat deletes no retained source and no cache object automatically. | Vendomat | Exercise retain and publish. Confirm retained objects remain and the source cache's Attic retention period is zero. |
| `V4-REC-009` | Record | Each durable state class has a named storage owner and restore route, and its off-host copy status is recorded. | Consumer | Inspect the pin record for retained source, evidence, Attic signing state, and application data. Record that source and binaries share one cache and therefore one loss domain. This is a record obligation, not a phase gate. |

### Machine claim

| ID | Phase | Required behaviour | Owner | Verification method |
| --- | --- | --- | --- | --- |
| `V4-MACH-001` | P7 entry | One Machines-capable devenv executable and its matching module revision are pinned and exercised. | Consumer | Record both identities. Evaluate a machine fixture and create a native plan on that pin. A version query alone does not pass. |
| `V4-MACH-004` | P7 | The receipt records the native plan identifier and its selected output paths. Vendomat creates no second plan or apply path. | Vendomat | Compare the recorded paths with `plan.json`. Trace apply and find no second path. Record that the plan identifier is random, not content-addressed. |
| `V4-MACH-009` | P7 | Machine reports keep NixOS, Home Manager, and application outcomes separate. A NixOS rollback claims nothing about user files or application data. | Vendomat | Fail Home Manager after NixOS succeeds. Roll the system back. Inspect user files and application data separately. Name the Home Manager activation driver. |
| `V4-MACH-015` | P7 | An application output in the cache sets no machine-generation cache field. | Vendomat | Publish only the application output. Inspect the plan and the report. The full-generation field stays absent. |

## 2. The two new IDs

| ID | Why it is new |
| --- | --- |
| `V4-SEL-010` | No earlier ID stated the publication form. The choice between a flake output attribute and `devenv build outputs.<name>` gates the design of both Vendomat operations, because `nix build --json`, `nix flake metadata --json`, and `nix flake archive` all need a flake reference. |
| `V4-EVD-012` | `nix path-info --json` takes `--json-format 1|2` (Nix 2.34.7), and `nix derivation show` changed shape across releases. A stored native document without its producing version and format is not readable later. |

Neither ID replaces an earlier ID.

## 3. ID history

Every one of the 184 earlier ID strings appears exactly once below. No ID is reused and none is
renumbered. The [project-10 requirement audit](../10-vendomat-v4-adversarial-review/V4-REQUIREMENT-AUDIT.md)
remains unchanged as the provenance for the 172 baseline IDs and the 12 IDs added in project 10.

Dispositions: **Active** gates a phase, and appears in §1. **Merged** retires into a named active ID
that keeps the observable result. **Baseline** moves to [NATIVE-BASELINE.md](./NATIVE-BASELINE.md),
observed once on the pin, no gate. **Retired** has no successor and no gate. **Scenario** becomes a
combined acceptance scenario in the implementation guide. **Trigger** waits for a named condition in
[FUTURE-WORK.md](./FUTURE-WORK.md). **Measurement** is recorded, not gated. **Note** moves to
[LATER-APPLICATION.md](./LATER-APPLICATION.md) or [FUTURE-WORK.md](./FUTURE-WORK.md).

| Group | Active | Merged into | Baseline | Retired, with reason | Other |
| --- | --- | --- | --- | --- | --- |
| OWN | `002`, `003`, `007`, `009`, `013` | `001`→`002`; `004`→`003`; `008`→`002`; `011`→`MACH-004` | `005`, `006` | `010`: no user-visible claim. `012`: pre-V4 consumer migration, outside V4 scope. | — |
| MOD | `001`, `002`, `005`, `008`, `009`, `010`, `011`, `012` | `004`→`005`; `014`→`SEL-001` | `003`, `006`, `007`, `013` | — | — |
| SEL | `001`, `002`, `003`, `006`, `007`, `009`, `010` | `004`→`006`; `005`→`006` | — | `008`: trivially true. | — |
| CHK | `001`, `002`, `004`, `006`, `007`, `010`, `011` | `008`→`010`; `009`→`010`; `014`→`010`; `016`→`011` | — | `005`, `015`: unfalsifiable, no closed set of documented behaviour exists. `012`: tautology once the required set is a declared list. | Scenario: `003` (P4), `013` (P1) |
| SRC | `002`, `003`, `004`, `006`, `008`, `009`, `011`, `015`, `024` | — | `005`, `010`, `012`, `016`, `017` | `001`: graph policy withdrawn. `014`, `018`, `025`: moot, retained source is a store path. `019`–`023`: capture list withdrawn. | Trigger: `007`, `013` |
| CACHE | `001`, `002`, `003`, `005`, `006`, `009`, `013`, `014`, `015` | `008`→`OWN-002` | `004`, `007`, `010`, `011`, `012` | — | — |
| EVD | `001`, `002`, `003`, `005`, `006`, `009`, `012` | `004`→`SRC-008`; `007`→`CACHE-014`; `010`→`SRC-015`; `011`→`002` | — | — | Note: `008` |
| REC | `001`, `002`, `005`, `009` | `003`→`001`; `004`→`002`; `010`→`001`; `011`→`002`; `013`→`MACH-009` | `012` | `008`: moot, there are no derived views. | Measurement: `006`. Note: `007` |
| MACH | `001`, `004`, `009`, `015` | `002`→`MOD-001`; `007`→`CHK-007`; `011`→`009`; `013`→`009` | `003`, `005`, `006`, `008`, `010`, `012`, `014` | — | — |
| PROOF | — | — | — | `007`, `008`: already retired in project 10 as duplicates of `REC-001` and `REC-002`. | Scenario: `001`–`006`, `009` |
| UPG | — | — | — | — | Note: `001`–`009` |
| OPT | — | — | — | — | Note: `001`–`004` |
| APP | — | — | — | — | Note: `001`–`031` |

**Arithmetic.** 58 active existing + 24 baseline + 26 merged + 16 retired + 9 scenario + 3 trigger
+ 1 measurement + 14 in the future-work note + 31 in the later-application note + 2 already retired
= **184**. Plus `V4-SEL-010` and `V4-EVD-012` = **186 ID strings, 60 active**.

## 4. Traceability

| Specification section | Active IDs |
| --- | --- |
| §1 decisions | `CHK-010`, `CHK-011`, `SRC-003`, `SEL-010`, `MACH-004` |
| §2 boundary | `OWN-002`, `OWN-003`, `OWN-007`, `OWN-013` |
| §3 module contract and delivery | `MOD-001`, `002`, `005`, `008`, `009`, `010`, `011`, `012` |
| §4 selection | `SEL-001`–`003`, `006`, `007`, `009`, `010` |
| §5 checks | `CHK-001`, `002`, `004`, `006`, `007`, `010`, `011` |
| §6 source retention | `SRC-002`, `003`, `004`, `006`, `008`, `009`, `011`, `015`, `024` |
| §7 deferred package graph | `SRC-006` (labels `unresolved`); trigger IDs in the future-work note |
| §8 Attic | `CACHE-001`–`003`, `005`, `006`, `009`, `013`–`015` |
| §9 the receipt | `EVD-001`–`003`, `005`, `006`, `009`, `012` |
| §10 machine claim | `MACH-001`, `004`, `009`, `015` |
| §11 failure behaviour | `CHK-004`, `006`, `011`; `SRC-008`, `009`; `CACHE-005`, `006`; `SEL-009`; `REC-001`, `002` |
| §12 open experiments | `SEL-010`, `MOD-011`, `012`, `SEL-001`, `MOD-005`, `CACHE-002`, `003`, `015`, `REC-006` |
| Recovery and records | `REC-001`, `002`, `005`, `009`, `OWN-009`, `EVD-009` |

## 5. Readiness

These requirements can structure the implementation guide. That guide must use the pin record and
per-phase entry conditions, not a combined preflight gate. It must not fix an export convention,
option name, command name, or receipt file format before its fixture passes. No V4 phase has passed.

## 6. Full-string disposition index

Every one of the 184 earlier ID strings appears below in full, so an audit can find any ID by
exact search. §3 gives the reason for each group. A full string also appears wherever that ID is
defined: §1 for active rows, and the three supporting notes for moved rows.

**Active, 58 — defined in §1:** `V4-CACHE-001`, `V4-CACHE-002`, `V4-CACHE-003`, `V4-CACHE-005`, `V4-CACHE-006`, `V4-CACHE-009`, `V4-CACHE-013`, `V4-CACHE-014`, `V4-CACHE-015`, `V4-CHK-001`, `V4-CHK-002`, `V4-CHK-004`, `V4-CHK-006`, `V4-CHK-007`, `V4-CHK-010`, `V4-CHK-011`, `V4-EVD-001`, `V4-EVD-002`, `V4-EVD-003`, `V4-EVD-005`, `V4-EVD-006`, `V4-EVD-009`, `V4-MACH-001`, `V4-MACH-004`, `V4-MACH-009`, `V4-MACH-015`, `V4-MOD-001`, `V4-MOD-002`, `V4-MOD-005`, `V4-MOD-008`, `V4-MOD-009`, `V4-MOD-010`, `V4-MOD-011`, `V4-MOD-012`, `V4-OWN-002`, `V4-OWN-003`, `V4-OWN-007`, `V4-OWN-009`, `V4-OWN-013`, `V4-REC-001`, `V4-REC-002`, `V4-REC-005`, `V4-REC-009`, `V4-SEL-001`, `V4-SEL-002`, `V4-SEL-003`, `V4-SEL-006`, `V4-SEL-007`, `V4-SEL-009`, `V4-SRC-002`, `V4-SRC-003`, `V4-SRC-004`, `V4-SRC-006`, `V4-SRC-008`, `V4-SRC-009`, `V4-SRC-011`, `V4-SRC-015`, `V4-SRC-024`

**Merged, 26 — the target keeps the observable result:** `V4-CACHE-008`→`V4-OWN-002`, `V4-CHK-008`→`V4-CHK-010`, `V4-CHK-009`→`V4-CHK-010`, `V4-CHK-014`→`V4-CHK-010`, `V4-CHK-016`→`V4-CHK-011`, `V4-EVD-004`→`V4-SRC-008`, `V4-EVD-007`→`V4-CACHE-014`, `V4-EVD-010`→`V4-SRC-015`, `V4-EVD-011`→`V4-EVD-002`, `V4-MACH-002`→`V4-MOD-001`, `V4-MACH-007`→`V4-CHK-007`, `V4-MACH-011`→`V4-MACH-009`, `V4-MACH-013`→`V4-MACH-009`, `V4-MOD-004`→`V4-MOD-005`, `V4-MOD-014`→`V4-SEL-001`, `V4-OWN-001`→`V4-OWN-002`, `V4-OWN-004`→`V4-OWN-003`, `V4-OWN-008`→`V4-OWN-002`, `V4-OWN-011`→`V4-MACH-004`, `V4-REC-003`→`V4-REC-001`, `V4-REC-004`→`V4-REC-002`, `V4-REC-010`→`V4-REC-001`, `V4-REC-011`→`V4-REC-002`, `V4-REC-013`→`V4-MACH-009`, `V4-SEL-004`→`V4-SEL-006`, `V4-SEL-005`→`V4-SEL-006`

**Retired, 16 — no successor, no gate:** `V4-CHK-005` (unfalsifiable), `V4-CHK-012` (tautology once the required set is declared), `V4-CHK-015` (unfalsifiable), `V4-OWN-010` (no user-visible claim), `V4-OWN-012` (pre-V4 consumer migration, outside V4 scope), `V4-REC-008` (moot, there are no derived views), `V4-SEL-008` (trivially true), `V4-SRC-001` (graph policy withdrawn), `V4-SRC-014` (moot, retained source is a store path), `V4-SRC-018` (moot, retained source is a store path), `V4-SRC-019` (capture list withdrawn), `V4-SRC-020` (capture list withdrawn), `V4-SRC-021` (capture list withdrawn), `V4-SRC-022` (capture list withdrawn), `V4-SRC-023` (capture list withdrawn), `V4-SRC-025` (moot, retained source is a store path)

**Native baseline, 24 — defined in NATIVE-BASELINE.md:** `V4-CACHE-004`, `V4-CACHE-007`, `V4-CACHE-010`, `V4-CACHE-011`, `V4-CACHE-012`, `V4-MACH-003`, `V4-MACH-005`, `V4-MACH-006`, `V4-MACH-008`, `V4-MACH-010`, `V4-MACH-012`, `V4-MACH-014`, `V4-MOD-003`, `V4-MOD-006`, `V4-MOD-007`, `V4-MOD-013`, `V4-OWN-005`, `V4-OWN-006`, `V4-REC-012`, `V4-SRC-005`, `V4-SRC-010`, `V4-SRC-012`, `V4-SRC-016`, `V4-SRC-017`

**Guide scenario, 9 — combined acceptance scenarios in the implementation guide:** `V4-CHK-003`, `V4-CHK-013`, `V4-PROOF-001`, `V4-PROOF-002`, `V4-PROOF-003`, `V4-PROOF-004`, `V4-PROOF-005`, `V4-PROOF-006`, `V4-PROOF-009`

**Measurement, 1 — recorded, not gated:** `V4-REC-006`

**Future work, 17 — defined in FUTURE-WORK.md:** `V4-EVD-008`, `V4-OPT-001`, `V4-OPT-002`, `V4-OPT-003`, `V4-OPT-004`, `V4-REC-007`, `V4-SRC-007`, `V4-SRC-013`, `V4-UPG-001`, `V4-UPG-002`, `V4-UPG-003`, `V4-UPG-004`, `V4-UPG-005`, `V4-UPG-006`, `V4-UPG-007`, `V4-UPG-008`, `V4-UPG-009`

**Later module, 31 — defined in LATER-APPLICATION.md:** `V4-APP-001`, `V4-APP-002`, `V4-APP-003`, `V4-APP-004`, `V4-APP-005`, `V4-APP-006`, `V4-APP-007`, `V4-APP-008`, `V4-APP-009`, `V4-APP-010`, `V4-APP-011`, `V4-APP-012`, `V4-APP-013`, `V4-APP-014`, `V4-APP-015`, `V4-APP-016`, `V4-APP-017`, `V4-APP-018`, `V4-APP-019`, `V4-APP-020`, `V4-APP-021`, `V4-APP-022`, `V4-APP-023`, `V4-APP-024`, `V4-APP-025`, `V4-APP-026`, `V4-APP-027`, `V4-APP-028`, `V4-APP-029`, `V4-APP-030`, `V4-APP-031`

**Already retired in project 10, 2:** `V4-PROOF-007`, `V4-PROOF-008`

Sum: 184 = 184. The two new IDs `V4-SEL-010` and `V4-EVD-012`
are defined in §2. Total ID strings: 186.

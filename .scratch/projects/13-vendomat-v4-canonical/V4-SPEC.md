# Vendomat V4 specification

**Date:** 2026-10-06. **Status:** Canonical and normative. **Authority:** This is the only
normative V4 document. [CONCEPT-V4.md](./CONCEPT-V4.md) states goals.
[V4-REQUIREMENTS.md](./V4-REQUIREMENTS.md) makes each rule here testable.

**Name rule:** No new Vendomat option name, command name, or file format is fixed. The P1 and P2
fixtures produce them. This document shows no proposed name as syntax.

## 1. Accepted decisions

| ID | Decision | Accepted |
| --- | --- | --- |
| `D-APP-SCOPE` | The Jujutsu–btrfs–bubblewrap application is a later module outside V4. Its case and `V4-APP-001`–`031` live in [LATER-APPLICATION.md](./LATER-APPLICATION.md). | 2026-10-04 |
| `D-NAMES` | Specify behaviour first. Every new name stays unproved until its fixture passes. No proposed name appears as syntax in this document. | 2026-10-04, enforced 2026-10-06 |
| `D-CHECK-OWNER` | The required check set is one declared list. It is the union of enabled-module defaults and consumer-added checks. Each entry records its owner. | 2026-10-04 |
| `D-CHECK-GAP` | Publication success does not claim complete test coverage. The receipt carries one coverage statement. Vendomat does not try to name documented behaviour that lacks a check. | 2026-10-04, narrowed 2026-10-06 |
| `D-CAPTURE` | Retain the source of **every** locked native input. There is no capture list, no capture policy file, and no selective capture. | Replaced 2026-10-06 |
| `D-PROOF-GATE` | P1–P6 prove the application. A separate P7 gates every machine claim. There is no combined preflight gate. | 2026-10-04, completed 2026-10-06 |
| `D-PUB-FORM` | Develop with the devenv command-line interface. Publish through a flake output attribute. | 2026-10-06 |
| `D-SRC-DIST` | Retained source travels through Attic as ordinary Nix store paths. | 2026-10-06 |

**Withdrawn:** `D-CAPTURE-GRAPH` (the two capture graphs are not symmetric; see §7).
`D-OFFLINE-SOURCE` (moot: retained source is a store path, so there is no remote tree to be
disconnected from). **Moved to project policy:** `D-REPO-BACKUP` (GitHub is a secondary copy of the
owner's local repositories, outside Vendomat; it creates no requirement).

## 2. System boundary

| Fact or state | Authority | Vendomat role |
| --- | --- | --- |
| Module source, exports, package recipes, checks | Module repository and version control | Inspect and report |
| Selected inputs, options, profiles, overrides, locks | Consumer repository and native locks | Explain the effective selection |
| Composition, tasks, outputs, machine plan | Pinned devenv | Invoke; link evidence |
| Derivations, output paths, store identity, substitution | Nix | Query identities; compare recorded with served |
| Host services, trusted keys, system generations | NixOS | Attach checks; report native status |
| User files and their activation | Home Manager | Report its status separately |
| Process behaviour and mutable data | The application | Check the selected output |
| Cached objects, signing, retention | Attic | Push; verify availability |
| Retained source bytes | The Nix store and Attic | Archive, root, push, record identity |
| Past checks, uploads, failures | Immutable receipts and logs | Own |

Vendomat owns exactly two durable state classes: receipts with their logs, and garbage-collection
roots. Everything else belongs to a native owner.

## 3. Module contract and exports

A module contract names its source revision, supported native targets, exported attributes,
required native inputs, typed options, default behaviour, component overrides, declared checks, and
side effects. One repository may export several modules.

| Contribution | Contract |
| --- | --- |
| devenv module | Native Nix module for packages, tasks, processes, and outputs. It declares its required inputs and its exact import path. |
| Package or application | Nix derivation or devenv output. It names its target system and its declared checks. |
| Editor interface | Native Neovim files. It invokes the selected command by **absolute store path**. |
| Home Manager module | Native user options, files, and user services. It names its user and home assumptions. |
| NixOS module | Native host options, services, storage, and trust settings. It names its host requirements. |
| Operation | Native script or function with arguments, result, exit behaviour, and side effects, at a real integration boundary only. |

Typed Nix options define configurable behaviour. Native module merging and explicit assertions
resolve or report shared settings. Importing a definition, enabling functionality, and activating
persistent configuration are three separate operations. An import activates no system or user
configuration.

A consumer imports only the contribution it needs. It does not inherit the author's development
environment.

### The Neovim contribution

The first module exports one shared review implementation, one command with a defined result
format, one plugin contribution for the normal editor, and one dedicated configured editor.

Both editor forms use the same packaged command. The editor reaches it by absolute store path
substituted at build time. A `PATH` prefix is not sufficient: the Nixpkgs and Home Manager Neovim
wrappers default to `--suffix PATH`, so a user's `PATH` entry would win. The dedicated editor
isolates its configuration through the native wrapper's `VIMINIT` mechanism.

### Delivery

Two delivery forms are supported, and they are not interchangeable.

- A **plain devenv repository** export must state every native input its consumer supplies. devenv
  merges an imported `devenv.yaml` only for local paths inside the git root. Remote inputs are not
  merged. No V4 interface assumes recursive remote `devenv.yaml` composition.
- A **flake-backed** export carries its locked transitive inputs and passes them to its
  implementation explicitly. A lock entry alone does not enable a module.

Under `D-PUB-FORM`, the publication path uses the flake form. The exact export convention is a P2
result.

## 4. Selection

The consumer records input locations, imports, options, active profiles, local overrides, and
native locks. The effective locks control selection. A local override is visible and reversible,
and it does not change a second consumer's accepted state.

An exact publication selection contains:

1. An immutable consumer revision, or one exact recorded diff against a recorded base.
2. The relevant declarations and lock contents, the requested output attribute, the target system,
   the active profiles, and the overrides.
3. The module source identities and the evaluated derivation identity.
4. The realized output paths, their NAR hashes, and their references.

**Purity.** A publishable selection evaluates with no access to undeclared host state. Prove this by
denying such access in the fixture, not by relying on a flag: the flake delivery form is impure by
default and needs `--no-pure-eval`. A selection that needs undeclared host state cannot be
published, and the failure names the cause. Re-evaluation of a pure selection reproduces its
derivation path, so Nix detects drift.

**Identity.** An input-addressed output path follows its derivation. Its NAR hash identifies its
serialized bytes. Path equality alone does not prove byte equality. The selection records both.
Publication aborts if the lock, derivation, output path, or checked NAR hash changes before upload.

The first publication path refuses a mutable checkout as an immutable selection. A later
development-cache mode would have to record the snapshot's exact bytes.

## 5. Checks

The required set is one declared list of native check names. Each entry records its owner: an
enabled module, or the consumer. The selection records the list, each entry's origin, and each
check's input.

The checked publication sequence for one frozen selection is:

```text
evaluate the selected output
  -> run the declared pre-build checks
  -> realize the exact output
  -> run the declared artifact and integration checks
  -> confirm the derivation and output identity
  -> push the output and its runtime closure
  -> query every closure path back from the cache
  -> retain the receipt
```

Three outcomes stay distinct:

| Outcome | Meaning | Effect |
| --- | --- | --- |
| `failed-required` | A declared required check ran and failed. | Blocks success. |
| `missing-required` | A declared required check is absent or cannot run. | Blocks success, with its own reason. |
| Coverage statement | The receipt states that only the declared required set ran. | Does not block. |

A failed build blocks success with its own reason and retains its logs.

Determine `missing-required` by checking existence before running. `devenv tasks run` exits 0 or 1
only, so its exit status cannot distinguish a missing check from a failed one. Never use a
`devenv:enterShell` task as a gate: shell entry proceeds after such a failure.

Vendomat declares which existing checks gate an output. It introduces no second test language and
no second workflow engine. A task's order does not prove a prerequisite succeeded. An existing
output path proves nothing.

## 6. Source retention

`retain` performs four native steps and records the result:

1. `nix flake archive` fetches every locked input's source tree into the store.
2. One garbage-collection root per archived path keeps it through local collection.
3. `attic push` sends those paths to the cache. `nix flake archive --to <cache>` cannot be used:
   Attic's binary-cache route serves `GET` only, and uploads use a separate endpoint.
4. One identity record per input holds its locator, locked revision, NAR hash, store path, and the
   consumer selection that chose it. `nix flake metadata --json` supplies the first three.

Reading retained source means substituting its store path. The store path is the read-only tree.
The store guarantees immutability. Reading changes no lock and no output path.

Correspondence and capture status are separate fields:

| Correspondence | When it applies |
| --- | --- |
| Exact selected source | A locked native input, retained, with a matching NAR hash. |
| Selected source with packaging changes | Reserved. It requires the deferred package-source capability. |
| Upstream reference | Useful source is retained; exact correspondence is not established. |
| Unresolved | Vendomat cannot connect the selected software to suitable source. A built package is `unresolved` under V4. |

Capture status is one of retained, identified but not captured, unavailable, or unidentified. A
record may be retained and still have non-exact correspondence. A mismatched object loses its
exact-correspondence claim. A selected source with no retained object reports a coverage gap, and
that gap never turns a valid artifact check into a failure.

Capture of a local working tree records a content-addressed identity for the captured bytes, so a
later edit does not change what the record names.

Source retention alone makes no archive-backed rebuild claim. A cache signature proves acceptance by
the cache key. It does not prove independent reproduction from source.

Set the source cache's Attic retention period to zero, because Attic's time-based collection uses
`created_at` and `last_accessed_at` and rarely-read source would otherwise expire.

## 7. Why the package-source graph is deferred

Two dependency graphs exist, and they are not symmetric.

- A locked native input's source is free and exact. `nix flake archive` retains it.
- A built package's source is reachable only by evaluating the package set that selected it.
  Patches apply during the build, not to `src`. So the result can never be labelled exact selected
  source. `pkgs.srcOnly` produces the unpacked and patched tree as a store path, and it is
  undocumented in the Nixpkgs manual.

V4 therefore retains the first graph unconditionally and reports the second as `unresolved`. The
deferred capability and its trigger are in [FUTURE-WORK.md](./FUTURE-WORK.md).

## 8. Attic publication and cold consumption

`attic push` pushes the closure by default. `--no-closure` disables it.

Attic's client-side upstream filter drops paths signed by a key in the cache's upstream key list.
Its default list has one entry, `cache.nixos.org-1`. Clear that list with
`attic cache configure --upstream-cache-key-name`, or pass `--ignore-upstream-cache-filter`.
Otherwise a dependency first obtained from the public cache is silently skipped.

`attic push` emits no machine-readable output. Its output is prefixed lines on standard error, and
its exit status is nonzero if any path failed while successful uploads remain on the server.
Therefore verify availability separately, by querying the cache as a store:
`nix path-info --store <cache> --json --json-format 2`.

Publication covers the exact checked output path and every path in its runtime closure. Here
runtime closure means the paths the selected output references. It is not every build input and not
any external service or mutable data.

A successful upload command alone cannot report complete publication. A partial upload records its
completed paths and retries the same selection safely. An upload failure leaves the local output
usable.

Attic re-hashes every upload and rejects a mismatch. Nix re-hashes every import and rejects a
mismatch. A cold cache-only substitution must still compare the served NAR hash with the checked
hash once, in an isolated store with other substituters and local builds disabled, including a
dependency first obtained from a public cache.

Cache availability is a current fact. Query it from Attic. A historical receipt cannot prove it.

NixOS owns the Attic service, its storage, its network access, the consumer's trusted public key,
and the placement of the push credential. A read-only token is made with `--pull` only. Attic signs
at read time with a per-cache server key, so regenerating that key invalidates every consumer's
trust setting. Secrets stay outside tracked files, Nix outputs, receipts, and logs.

Consumer preference is: an existing local output, then Attic, then configured public caches, then a
permitted local build. Configure and test that order through native Nix settings. Priority alone
does not prove outage behaviour.

## 9. The receipt

One immutable file per publication run. It stores four native documents verbatim:

1. `nix flake metadata --json` — the complete locked input graph.
2. `nix build --json` — the derivation path and every output path.
3. `nix path-info --json --recursive` — `narHash`, `narSize`, `references`, `deriver`,
   `signatures`, and `ca` for the whole closure.
4. The archived-source index from `retain`.

It adds six fields no native tool knows:

1. The required check list, with each entry's owner, result, and log reference.
2. The upload result.
3. The closure availability verification result and its time.
4. The coverage statement.
5. The optional native machine plan identifier.
6. The tool version and JSON format of every stored document.

Field 6 is required because `nix path-info --json` takes `--json-format 1|2|3` and
`nix derivation show` changed shape across releases. A stored document without its format is not
readable later.

Failure evidence records the failed stage and its completed side effects. Receipts and logs hold no
credential and no unrestricted environment dump.

## 10. The machine claim

Pin one devenv executable and its matching module revision with Machines support. Machines is
experimental.

`devenv machines plan` builds outputs and writes `plan.json` with a `plan-` identifier and one
garbage-collection root per output. `apply` re-observes the target, uses the saved outputs without
rebuilding, copies them, and activates them.

Record three upstream limits as design constraints:

1. The plan identifier is random, not content-addressed.
2. Staleness is checked against the target's generations and access facts only. It is not checked
   against the lock or a re-evaluation. The check covers the NixOS role only.
3. Transfer is a direct `nix copy --to ssh://<target>`. It does not substitute through Attic.

Vendomat therefore makes no machine transfer claim and no machine-cache claim. Its only machine
obligation is to record the native plan identifier and its selected output paths beside the receipt,
and to create no second plan or apply path.

NixOS and Home Manager activate separately. A Home Manager failure can leave NixOS applied. The
Home Manager role has no staleness check and no automatic rollback. A NixOS rollback claims nothing
about user files or application data. Report each outcome separately and name the Home Manager
activation driver.

An application output in the cache sets no machine-generation cache field.

## 11. Failure behaviour

| Condition | Required behaviour |
| --- | --- |
| Missing module input | Name the native input requirement. Invent no resolution. |
| Conflicting options or bindings | Name the conflict. Require an explicit choice. Choose nothing silently. |
| Unsupported requested target | Fail that composition. Name the missing native export. |
| Selection reads undeclared host state | Refuse publication. Name the cause. |
| Selected source has no retained object | Report the coverage gap. Valid build and publication work continues. |
| Retained object mismatch | Reject that correspondence claim. Preserve the failure evidence. |
| Required build source mismatch | Fail the build's native validation. Stop publication. |
| Declared required check fails | Report `failed-required`. Publish no success result. Keep logs. |
| Declared required check absent or unrunnable | Report `missing-required`. Publish no success result. |
| Build fails | Report the build failure with its own reason. Keep logs. |
| Upload fails | Keep the local output. Report publication failure. |
| Partial closure upload | Record partial progress. Retry safely. Claim no complete availability. |
| Closure path absent after upload | Report incomplete publication, not success. |
| Attic unavailable | Follow the recorded native fallback and build policy. |
| Native plan stale | Use the native rejection. Prepare a valid plan. Reuse a check only when its recorded inputs still match. |
| Activation fails or stays unknown | Report native status per role before another attempt. |
| Restore fails | Report only the corresponding recovery claim as failed. |

A failed publication alters no accepted dependency state. Source retention changes no installation
choice. A Vendomat failure never removes the native tools' ability to inspect and use accepted
state.

## 12. Open experiments

Five facts remain unproved. Each needs a fixture before its interface is fixed. Everything else the
earlier contract listed as an experiment is either answered in [NATIVE-BASELINE.md](./NATIVE-BASELINE.md)
or withdrawn.

| ID | Question | Evidence needed | Affected IDs |
| --- | --- | --- | --- |
| `P-PUB-FORM` | Can the flake output attribute express the P1 Neovim outputs, and does `devenv build` supply an equivalent handle? | P2 step 1. If the flake form cannot express them, stop and revise this document before P3. | `V4-SEL-010`, `V4-MOD-012` |
| `P-DELIVERY` | Which flake export convention passes transitive inputs, and what must a plain consumer declare? | P2 plain and flake-backed fixtures. | `V4-MOD-011`, `V4-MOD-012` |
| `P-PROFILES` | Which profiles and overrides survive each consumption path on the pin? | P2 matrix. | `V4-SEL-001`, `V4-MOD-005` |
| `P-ATTIC` | Does the cache serve every runtime closure path in an isolated store with the upstream filter accounted for? | P5 isolated-store substitution with a public-cache-seeded dependency. | `V4-CACHE-002`, `003`, `015` |
| `P-STORAGE` | What are archived source growth, closure size, and transfer cost? | Measure in P3 and P6 before wider retention. | `V4-REC-006` (measurement) |

No row here authorizes a new Vendomat resolver, lock, runtime, registry, index, or deployment
engine.

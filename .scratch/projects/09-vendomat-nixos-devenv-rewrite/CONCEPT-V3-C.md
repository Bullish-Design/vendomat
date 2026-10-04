# Vendomat V3-C: inspected source, checked outputs, and declared releases

**Status:** Proposed architecture, 2026-10-04.
**Scope:** One owner's NixOS machines and software projects on a trusted private network.
**Basis:** Greenfield rewrite. This concept records the decisions made after V2-C, V2-CC, and the combined refined draft.

## 1. Purpose

Vendomat coordinates source inspection, checked Nix builds, binary distribution, and reviewed upgrades.
It also provides a release pipeline that a person or a declared continuous integration workflow can start.

~~~text
native producer and consumer files
              |
              v
exact consumer selection
              |
              +----> source archive for human and agent inspection
              |
              v
checks and exact Nix output
              |
              v
Attic over the private network
              |
              v
normal Nix and NixOS consumption
~~~

Vendomat must keep these facts separate:

| Fact | Meaning |
| --- | --- |
| Source retained | The archive holds identifiable source for inspection. |
| Rebuild from archive proved | A separate test built from those retained bytes. |
| Output validated | The exact selection passed its required checks and build. |
| Output available | Attic serves the requested output path and closure. |
| Change accepted | The owner applied the reviewed native dependency change. |
| Machine deployed | A separate machine workflow activated the change. |

Source retention alone does not prove rebuildability.
Attic availability alone does not prove source retention.
A cached candidate does not change a consumer's lock.

The source archive serves people and agents who need to understand underlying code.
It is not a required source endpoint for ordinary consumer evaluation or publication.
Vendomat may publish a checked binary with an explicit source coverage gap.

## 2. Ownership

One system owns each authoritative fact.

| Owner | Holds |
| --- | --- |
| Producer repository | Source, native package metadata, build recipe, tests, release history |
| Consumer repository | Dependency declarations and committed native locks |
| Source archive | Retained source bytes, identities, and read-only inspection access |
| Nix | Evaluation, derivations, builds, and store-path identity |
| Attic | Signed Nix output paths and required closures |
| Git | Reviewed source and dependency history, immutable release tags |
| devenv | Preferred project options, outputs, tasks, tests, and hooks |
| NixOS | Host services, storage, trust, credentials, backups, networking, and timers |
| Vendomat | Capture, validation, publication, proposals, reports, releases, and evidence |

Vendomat introduces no dependency lock, package format, resolver, or version authority.
A consumer may use several native locks for one output.
For example, devenv.lock may select Nix inputs while uv.lock selects Python packages.
Vendomat records the relevant files instead of replacing them.

Normal shell entry, evaluation, and runtime need no live Vendomat service.
Removing Vendomat must leave the repository's dependency state understandable through native tools.

## 3. Exact selections

Every checked publication starts from an exact selection.
That selection includes:

1. An immutable consumer repository revision.
2. The relevant native declarations and lock contents.
3. The requested package or output attribute.
4. The target system and any required application binary interface.
5. Explicit profiles and input overrides.
6. The evaluated derivation and requested output path.

A producer tag alone cannot establish a consumer cache hit.
The consumer may use another Nix input graph, recipe, profile, or target system.
Vendomat confirms that the checked output path is the one the consumer requests.

For upgrades, the selection includes the exact proposed native file change.
Candidate evidence is bound to its base revision and proposed file hashes.
If either changes, Vendomat regenerates and revalidates the proposal.

## 4. Source archive

The archive keeps source available for human and agent reading.
Capture may add new immutable objects.
Inspection access must not modify captured objects or native consumer files.

Use native storage forms where they fit:

- Git mirrors or bundles with refs that retain exact commits.
- Verified archive files for archive inputs.
- Durable Nix source paths when explicit roots and backups make them safe.

The archive needs a stable way to find a source by project, locator, and revision or hash.
A read-only checkout or equivalent view should let a person or agent inspect the exact bytes.
Vendomat should report the original locator and the retained identity beside that view.

Git objects and fixed-output inputs need different verification:

| Kind | Identity check |
| --- | --- |
| Git source | Repository identity, retained revision, and object content |
| Fixed-output source | Exact match against the hash declared by the build |

Vendomat must not present a source copy as verified when its identity check fails.
A mismatch in source used by the selected build blocks publication.
Failure to capture optional inspection source creates a named coverage gap.

The source report distinguishes:

~~~text
retained for inspection
identified but unavailable
unavailable for retention
not yet identified
~~~

It reports any proved rebuild-from-archive result separately.
A successful build from ordinary upstream source does not establish that result.
The source archive can contain extra grounding repositories beyond a selected build graph.

### Source policy

A project may choose these policies where they are useful:

| Policy | Effect |
| --- | --- |
| upstream | Use the native source location. No archive claim follows automatically. |
| mirror | Capture source for read-only inspection. Do not change installation. |
| build | Explicitly build from retained or modified source. Record the changed derivation. |

The mirror policy does not add a dependency to pyproject.toml, uv.lock, or another native lock.
The build policy is explicit because it can change downstream derivations and cache hits.
These policies do not create a new package manager.

The archive may later support a tested rebuild path.
Such a test must show that the build uses retained bytes and still selects the claimed output.
That proof is optional and never follows merely from successful capture.
Full offline reconstruction needs all build inputs and toolchains, so it remains a separate claim.

## 5. Checked publication

The publication pipeline uses one immutable consumer selection.
devenv tasks provide the project-local task graph where the project uses devenv.
Another native Nix interface remains valid when it selects the consumer output more exactly.

~~~text
freeze consumer selection
        |
evaluate its locked graph
        |
discover and attempt source capture
        |
record source coverage
        |
run checks that precede the build
        |
build the selected output
        |
run checks that exercise the built output
        |
confirm the consumer requests that output path
        |
push the output and required closure to Attic
        |
verify Attic serves the requested paths
        |
write immutable publication evidence
~~~

Source capture gaps do not block this pipeline by themselves.
A failed source identity check for an input used by the selected build does block it.
If the build needs unavailable source, the build fails and publication stops.
Failed required checks, builds, or uploads never report publication success.

The check set includes:

- The producer's declared tests and build checks.
- Relevant consumer checks that the consumer already declares.
- A check of the built artifact when practical.

The task graph must allow checks both before and after the build.
Vendomat does not need a second checks format when native project checks already exist.
A declared check failure blocks publication.
If a consumer declares no relevant check, the report names a check coverage gap.
That gap does not block publication.

The output pushed to Attic is the output that passed this gate.
Vendomat does not rebuild during acceptance.
The first foundation proof must confirm substitution on a cold second machine.

## 6. Attic and consumer fallback

Attic serves the owner's binary cache over the private network.
NixOS configures the Attic endpoint and trusted signing key for each consumer.
The build host holds the push credential.
Consumers do not receive that credential.

The desired consumer order is:

~~~text
existing local Nix store path
        |
self-hosted Attic cache
        |
configured public binary caches
        |
native upstream fetch and local build, when allowed
~~~

Attic is the preferred binary source.
It is not the source archive.
An Attic miss does not make Vendomat a resolver or an evaluation service.
The consumer's native lock and Nix configuration govern fallback.
The cache-outage policy must say whether that consumer may build or should fail clearly.

Attic signatures establish trust in cached bytes.
They do not prove that archived source can rebuild those bytes.
An Attic upload counts as available only after Vendomat verifies the requested paths.

## 7. Evidence and current state

Vendomat queries current facts from their owners:

| Current question | Authority |
| --- | --- |
| What does this consumer select now? | Its native declarations and locks |
| Does archived source exist now? | The source archive |
| Does Attic serve this path now? | Attic |
| What does this state evaluate to? | Nix |
| What policy applies? | The project's evaluated configuration |

Vendomat does not keep shadow tables for those current facts.
It does retain immutable evidence about past events.
Past check results and upload results cannot always be reconstructed later.

A publication receipt records at least:

- Consumer revision and relevant native file hashes.
- Output attribute, target system, profiles, and overrides.
- Derivation and requested output path.
- Source identities, capture results, and coverage gaps.
- Checks that ran, checks missing, and their results.
- Attic target, upload result, and availability check.
- The release or candidate identity when one applies.

Receipts and logs live on backed-up storage.
They are evidence, not another dependency lock or current availability database.
A report must distinguish what passed at publication time from what remains available now.

## 8. Candidates and reviewed upgrades

Vendomat initially discovers candidates for the owner's managed codebases.
Native consumer constraints and declared policy decide which releases qualify.
A new Git tag is a possible candidate, not automatic adoption.
Third-party grounding mirrors do not create upgrade candidates by themselves.

A site is one consumer's use of one managed codebase.
Vendomat derives sites from native dependency files where possible.
It permits an explicit exceptional relationship when native files cannot express one.
It keeps a declared list of consumer repositories to inspect.

For each candidate, Vendomat:

1. Starts from an immutable consumer revision in an isolated checkout.
2. Runs the native dependency update tool.
3. Records the minimal proposed native file change.
4. Evaluates that exact proposed selection.
5. Runs the checked publication pipeline.
6. Reports the diff, checks, source gaps, and cache result.

The native tool remains the resolver.
Vendomat does not infer a package graph or write a parallel lock.
A failed candidate retains its logs and leaves the consumer unchanged.
A successful candidate can be cached before acceptance.

An on-demand candidate must work before scheduled sweeps are enabled.
A sweep may investigate and prepare proposals.
It may not accept, commit, or deploy a proposal.
The normal sweep sees pushed consumer revisions.
A local option may evaluate the owner's working tree.

### Holds and pins

A site may hold its current selection or pin an exact revision.
Pins carry a reason and creation date.
The report shows old pins and newer available releases.
Vendomat retains pinned Git commits through archive refs when it captures them.
A pin produces no automatic upgrade candidate until policy changes.

## 9. Acceptance

The owner reviews the proposed native diff and its evidence.
Before applying it, Vendomat verifies that the base files still match.
A stale candidate must be regenerated and revalidated.
Vendomat also verifies that the published candidate path remains available.

Acceptance writes the validated native file change.
It does not rebuild, commit, merge, tag, or deploy.
Git remains the owner's review and commit workflow.
The report shows accepted changes that remain uncommitted.
Deployment remains a separate machine action.

## 10. Retention and recovery

The initial policy is to keep all archived source and all Attic outputs.
Vendomat performs no automatic deletion.
It can still calculate and report the logical keep-set.

Future deletion, if enabled declaratively, must account for:

~~~text
active consumer locks
+ accepted states inside a recovery window
+ explicit pins
+ pending candidates
+ explicit source inspection holds
~~~

The candidate remains pending until the owner accepts or dismisses it.
Its bytes then remain for the configured recovery window.
One inventory drives retention for linked source objects and binary paths.
An output with a proved rebuild-from-archive claim must not outlive its required retained source.
An output with a source gap keeps that gap; retention cannot turn it into a rebuild proof.
The archive may retain extra source for inspection after its related output expires.

Before any future deletion, Vendomat must prove that it enumerates active consumers correctly.
It must preview deletions and verify backups.
Until that proof exists, the keep-set is a report, not a delete instruction.

Backups include the source archive, evidence, Attic data, and cache signing state.
A restore test verifies archive identities and confirms cache substitution.
Source and binary recovery remain separate results.

## 11. Declarative release pipeline

Vendomat provides one release command and one underlying pipeline.
A person may run the command.
A declared continuous integration or continuous delivery workflow may run the same command.

The project declares its release policy through a small Vendomat module where it uses devenv.
Other native projects may use an equivalent dedicated integration.
Policy may declare:

- Manual triggers.
- Repository events, such as a merge from dev to main.
- Whether every matching event releases or a native version change is required.
- Native version write targets and bump rules.
- Whether Vendomat creates the release commit or starts from an existing commit.
- Required target systems, checks, publication targets, and tag rules.

The dev-to-main event is an example, not a built-in global rule.
The policy is declarative, so repositories can choose different triggers.
Native package metadata remains the version authority.
Vendomat may update declared native version targets without creating a Vendomat version field.

Every trigger converges on the same ordered pipeline:

~~~text
prepare native release metadata under declared policy
        |
create or select the final immutable commit
        |
build and check that exact commit for required targets
        |
publish and verify required artifacts in Attic
        |
create an immutable tag on the tested commit
        |
push the release commit and tag
        |
record release evidence
~~~

No tag is created when a required build, check, or upload fails.
The command is safe to retry after an interruption.
It detects an existing tag and refuses to move it.
A bad release receives a new version.
The pipeline must avoid recursive releases when its own commit or tag triggers automation.

A producer release proves its configured producer outputs.
It does not prove every consumer can adopt that release.
Each consumer candidate still passes its own exact-selection gate.
Vendomat provides release logic; the configured CI/CD system supplies the event that invokes it.
Normal consumer evaluation never depends on that CI/CD system.

## 12. Project and machine interfaces

devenv is the preferred interface for projects that already use it.
Its typed module can declare Vendomat policy.
Its outputs, tests, hooks, and task graph can run the project-local pipeline.
Vendomat does not duplicate native names, dependencies, versions, or checks.

devenv is not mandatory for every consumer.
A direct Nix package output remains valid when it preserves the exact consumer graph better.
The Vendomat integration is a dedicated module, not an import of its development repository.
Implementation dependencies belong to the tool installation, not every consumer lock.

The standalone command handles work that spans repositories or runs without an active project:

~~~text
vendomat source
vendomat report
vendomat candidates
vendomat accept
vendomat sweep
vendomat release
vendomat retention
~~~

The command coordinates native tools and tasks.
It does not become another package manager or general workflow engine.

NixOS owns the Attic service, source storage, substituters, trusted keys, push credentials, backups, timers, and network exposure.
devenv declares project behavior.
NixOS declares machine trust and service behavior.

## 13. Failure behavior and security

| Condition | Required result |
| --- | --- |
| Optional archive capture fails | Report a source gap. Continue if the selected build and checks can pass. |
| Source identity used by the build mismatches | Block publication and report the mismatch. |
| Required build input is unavailable | Build fails. Publish nothing. |
| Declared check fails | Publish nothing. Change no consumer file. |
| Consumer check is absent | Report a check coverage gap. |
| Build fails | Keep the log. Change no consumer file. |
| Attic upload or path check fails | Keep the local build. Report publication failure. |
| Attic is unavailable to a consumer | Follow its declared fallback policy. |
| Candidate base changes | Regenerate and revalidate before acceptance. |
| Release gate fails | Create no tag. Keep evidence for retry. |
| Archive or cache restore fails | Report the corresponding durability claim as failed. |

The initial deployment has one owner and a trusted private network.
The build host holds a restricted Attic push credential.
Consumers hold the cache URL and public signing key.
Secrets stay outside tracked files and Nix store objects.
Consumers never receive the push credential.

## 14. Proof plan

The first milestone proves checked binary distribution and useful source inspection.
It does not require a rebuild from the archive.

**P0 — Baseline.**
Record machines, target systems, native versions, storage paths, backup destinations, and fallback policy.
Run the repository's normal verification gate.

**P1 — Exact package.**
Choose one real producer and consumer.
Commit their recipes, declarations, locks, and checks.
Show the exact derivation and output requested by the consumer.

**P2 — Inspection archive.**
Capture that producer and one useful grounding source.
Verify their identities.
Let a person or agent open the retained revisions without changing them.
Demonstrate a named gap for source that cannot be captured.

**P3 — Checked publication.**
Run producer checks, declared consumer checks, and an artifact check where practical.
Build the requested output once.
Push that output and closure to Attic.
Verify a cold second NixOS machine substitutes it without building.
Show that a source gap does not falsely become a rebuild claim.

**P4 — Evidence and recovery.**
Persist a publication receipt.
Restore archive, Attic, evidence, and signing state from backup.
Verify source identity and cache substitution after restore.

**P5 — One reviewed upgrade.**
Prepare an exact native diff in an isolated checkout.
Show one failed candidate and one passing candidate.
Accept the passing one without rebuilding or committing.
Confirm its lock requests the validated output.

**P6 — Release pipeline.**
Run vendomat release manually on an exact producer commit.
Then invoke the same pipeline from one declared repository event.
Prove that a failed gate creates no tag and that a passing tag names the tested commit.

**P7 — Scheduling and retention reports.**
Enable scheduled candidate discovery if useful.
Report pins, pending candidates, and the logical keep-set.
Keep deletion disabled until a later, separately proved phase.

Later work may add archive-backed rebuild proofs, broad source audits, full offline reconstruction, and garbage collection.
Each needs its own stated scope and test.

## 15. Invariants

1. Native producer metadata and consumer locks remain authoritative.
2. Every publication names an immutable consumer selection and target system.
3. The checked output is the output published and requested by that consumer.
4. Archived source is identifiable and available for read-only inspection.
5. Source retention and rebuild-from-archive proof are separate claims.
6. A named source gap may coexist with a checked, available binary.
7. A source identity mismatch used by the build blocks publication.
8. A failed declared check, build, or upload changes no consumer selection.
9. Missing consumer checks are reported as coverage gaps.
10. Attic is the preferred binary cache, with declared fallback.
11. Current state is queried from native authorities; historical evidence is retained.
12. Candidate acceptance is explicit and performs no rebuild or automatic commit.
13. Deployment is separate from acceptance.
14. Release triggers are declarative, and manual and CI/CD triggers run one pipeline.
15. A release tag identifies the exact commit that passed its required gates.
16. Source and Attic deletion are disabled initially.
17. Ordinary evaluation and runtime need no live Vendomat service.

Vendomat is a lifecycle coordinator and evidence system.
It is most visible when people inspect source, publish software, or review a change.
It stays out of the path when a machine simply uses an accepted package.

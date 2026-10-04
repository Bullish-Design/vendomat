# Vendomat V2-C: source, builds, and reviewed upgrades through devenv

**Status:** Proposed concept for a ground-up rewrite, 2026-10-04.
**Scope:** One owner's NixOS machines and projects on a trusted tailnet.

## 1. Purpose

Vendomat preserves available source for selected software, checks and builds it once, and distributes trusted Nix outputs through Attic.
It later finds candidate upgrades, tests the exact changes that consumers would accept, and presents those changes for review.
The owner decides which changes to accept and when to deploy them.

The architecture uses existing authorities:

> **Native package metadata describes a release. Native consumer locks select inputs. Nix identifies builds. Git records reviewed changes. Attic serves store paths.**

Vendomat coordinates these tools and records evidence.
It does not introduce a second package format or a permanent resolution that consumers must query.

The design has two useful milestones:

1. **Source and artifact foundation:** Retain exact source, build and check the selected output, publish it, and prove substitution on another machine.
2. **Reviewed upgrade loop:** Find a candidate, validate its exact proposed lock change, and let the owner accept it.

The first milestone remains useful if all upgrade automation is disabled.

## 2. System model

```text
producer source and package metadata
                  │
                  ▼
consumer declaration + native locks ──► exact proposed lock change
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                         retained source
                                  ▼
                    consumer-selected Nix output
                                  ▼
                       checks and central build
                                  ▼
                                Attic
                                  ▼
                        NixOS consumers
```

The normal consumer lock remains authoritative after an accepted change.
No Vendomat daemon participates in shell entry, package evaluation, or application runtime.

## 3. Ownership

| Owner | Responsibility |
| --- | --- |
| Producer repository | Source code, package metadata, build recipe, project checks, and release history |
| Consumer repository | Dependency declarations and the locks that select its effective input graph |
| devenv | Project inputs, its native lock, buildable outputs, tests, and task execution where the project uses devenv |
| Source archive | Retained source bytes, identity, provenance, coverage, and recovery records |
| Nix | Evaluation, derivations, builds, checks expressed as derivations, and store-path identity |
| Attic | Signed Nix store paths and their required closures |
| NixOS | Host services, storage, networking, client trust, credentials, backups, and timers |
| Vendomat | Source capture, coverage, validation coordination, publication proof, candidate reports, and proposal preparation |

A consumer may have several native locks with different jobs.
For example, `devenv.lock` can select Nix inputs while `uv.lock` selects Python packages.
A NixOS flake may use `flake.lock` instead of `devenv.lock`.
Vendomat records which locks define a specific output; it does not collapse them into one Vendomat lock.

## 4. devenv as the project interface

devenv is the default declaration and execution interface for projects that use it.
It can replace several proposed Vendomat interfaces:

- `devenv.yaml` declares Nix inputs; the committed `devenv.lock` pins them.
- `devenv.nix` declares a buildable package through `outputs` and adds project checks.
- `devenv build` builds an output and reports its Nix store path.
- `devenv test` runs project tests and can start required test processes.
- devenv tasks order capture, checks, build, publication, and reporting.
- Task inputs carry invocation parameters; task outputs carry structured results between steps.
- `devenv eval` exposes declared project facts without a second manifest parser.

A small Vendomat module may add typed policy options when a real workflow needs them.
It should not duplicate package names, versions, or dependency declarations that native files already own.
A shared module must be a dedicated module file, not an import of Vendomat's whole project workbench.

For a producer, `outputs.<name>` can be its publishable Nix package recipe.
A devenv consumer can select that producer as an input and reference its output.
This may remove a duplicate producer flake when the consumer can evaluate the same output from its locked graph.

That simplification needs one explicit proof.
The build host and consumer must evaluate the same derivation for the target system.
Remote devenv project references do not evaluate the remote project's `devenv.yaml`.
They also have profile limits.
The consumer must declare the inputs needed by the output, or use another native Nix package interface.
Do not require every NixOS or project consumer to adopt devenv merely to use Vendomat.

Publication runs from an immutable, committed checkout with its committed locks.
It uses an explicit target system and explicit profiles.
Local devenv overrides and hostname-dependent profiles must not change a publishable output without appearing in its recorded identity.
Evaluation does not fetch candidate versions or contact Vendomat.
Network, source, cache, and build-host operations run in tasks or commands after evaluation.

## 5. Exact consumer selection

Each publication starts with a **selection**:

- an immutable consumer repository revision;
- the effective native declarations and committed locks;
- the selected output or package attribute;
- the target system and any required application binary interface;
- explicit build profiles and input overrides, if used.

Vendomat records the evaluated derivation and requested output path for that selection.
A producer's source revision alone cannot prove a consumer cache hit.
The consumer may use different Nix inputs, a different target system, or a different package recipe.

For a candidate upgrade, the selection is an exact proposed change to the consumer's native files.
A candidate is not only a new tag or version number.
Its evidence is bound to the proposed lock content and the consumer revision from which that change was prepared.

## 6. Retained source

The source archive is a logical retention contract, not a new source protocol.
Start with native storage forms suited to the selected input:

- Git mirrors or bundles with refs that retain exact commits;
- verified archive files for archive inputs;
- retained Nix source paths with explicit garbage-collection roots where that is sufficient.

Attic may also serve copies of Nix source paths.
That distribution does not replace a retention and backup policy for the source itself.
Mirror refs may change as new source is captured; retained objects and identity records must remain immutable.

Each source record identifies its original location, exact revision or declared hash, content hash, retained location, capture result, and selecting lock.
Coverage reports distinguish retained, identified but unavailable, unavailable for retention, and unidentified source.
They report the reason for each gap.

A flake input archive does not cover every archive, patch, or repository that a package recipe fetches.
Vendomat inspects the selected build graph and expands source discovery from real unsupported cases.
It must not claim complete coverage from a runtime closure or a successful binary download.

The builder must use retained bytes for every source Vendomat claims to retain.
If the native lock still names an upstream location, the proof must show how that locked fetch uses identical retained bytes.
Changing the fetch location must not silently change the derivation being published.
The first proof clears relevant local caches, blocks tested upstream source endpoints, and observes the actual fetch path.

Source must survive ordinary Nix garbage collection.
Backups include retained bytes and their identity records.
A restore must pass hash checks and support the same selected build.

The first coverage target is selected software with Nix-defined builds.
Machine-wide coverage for all available source is a later audit, with explicit gaps for binary-only and non-Nix software.
Full offline reconstruction requires every transitive build input and toolchain; it is a separate claim and proof.

## 7. Checked publication

The foundation pipeline is:

```text
immutable consumer selection
         ↓
inventory locked inputs and evaluate the selected build graph
         ↓
capture and verify required available source
         ↓
re-evaluate with retained source and record the derivation
         ↓
run required checks and build the output
         ↓
confirm the consumer requests that output
         ↓
push output and required runtime closure to Attic
         ↓
confirm the cache serves the requested paths
         ↓
record publication evidence
```

devenv tasks can express this order and pass structured results between steps.
The first implementation can use inspectable tasks and small purpose-built commands.
It needs no general Vendomat workflow engine.
Initial discovery may reach upstream sources.
The final build proof blocks those endpoints and verifies the retained-source path.

Required checks belong to the selected producer and consumer contract.
They must exercise more than derivation evaluation when the package needs runtime or integration checks.
Build success alone does not establish that a consumer works.
No check or build failure may report publication success.

The publication record contains the consumer revision, relevant lock hashes, selected output, target system, source identities, derivation path, output path, checks, Attic target, and upload result.
It is evidence, not a second version pin.
Task output is useful during one run; durable evidence belongs in the publication record.

The build host holds a restricted Attic push credential.
Consumers receive the Attic endpoint and public trust key, with no push credential.
NixOS configures daemon trust and keeps secrets outside tracked files and Nix store objects.
Attic signatures establish cache trust, not independent reproduction from source.

Publication does not change a consumer lock or activate a machine.
The consumer must request the same output path for its target system.
A cold second machine must substitute that path without rebuilding it.

## 8. Candidates and reviewed upgrades

After publication works, Vendomat can discover newer releases for managed codebases.
It learns affected **sites** from known consumer repositories and their native dependencies where possible.
A site is one consumer's use of one managed codebase.
Vendomat needs a way to enumerate consumers, but it needs no separate authoritative site graph.
Declare an exceptional relationship only when native metadata cannot express it.

Candidate selection follows the consumer's constraints and explicit policy.
The newest tag is not automatically valid for every site.
A basic hold must be available when automated candidate discovery begins.
Richer pin reasons, stale-pin reports, and fleet rules can follow real usage.

For each candidate, Vendomat:

1. creates an isolated checkout of the consumer's current revision;
2. uses that consumer's native update command to prepare a minimal lock change;
3. captures and verifies the candidate's available source;
4. evaluates, checks, and builds the exact proposed consumer state;
5. compares the resulting derivation and output with what that state requests;
6. publishes successful outputs to Attic;
7. presents the native diff, check results, source coverage, and cache result.

For devenv inputs, its native update command can prepare the input change.
Other native locks use their own update tools.
Vendomat does not implement a parallel dependency resolver.

A candidate record binds the base consumer revision, proposed file hashes, target system, derivation, output path, check results, and publication result.
A failed candidate records its cause and changes no consumer.
A successful candidate may be cached before acceptance; a cache entry never selects a version by itself.

The owner reviews the proposed native diff and accepts it through the normal version-control workflow.
Acceptance does not imply deployment.
Before applying a prepared change, Vendomat checks that the base files have not changed.
If they changed, it regenerates and revalidates the proposal.
After acceptance, the committed native lock is again the only durable dependency selection.

A scheduled sweep may later fetch mirrors, find candidates, run this pipeline, and update reports.
The same work must first succeed on demand.
The sweep may investigate and prepare proposals; it may not accept or deploy them.

## 9. Producer releases

Producer release automation is a later convenience.
It uses the producer's native package metadata as the preferred version source.
Where several files must state the version, the producer declares the write targets and checks them for drift.
Vendomat should not add a required `vendomat.version` when existing package metadata already owns that fact.

The release operation prepares version changes and freezes the exact source revision to publish.
It builds and checks that committed revision before creating its release tag.
The tag records the tested commit, and Vendomat records the commit hash as the release identity.
Published tags must never be moved; a bad release gets a new version.

Once a release appears, candidate discovery applies the consumer workflow above.
Producer release success does not imply that every consumer can adopt it.

## 10. NixOS and machine delivery

NixOS declares the source storage, Attic service, builder, tailnet access, substituters, trusted keys, backups, and scheduled jobs.
Those services remain normal NixOS modules even if devenv provides the operator interface.

devenv Machines may build a machine configuration, prepare an exact deployment plan, apply those outputs, and manage NixOS rollback.
This can remove custom deployment glue if machine configurations use devenv.
Machines is experimental, so Vendomat's source and publication contract must not depend on it.
Package acceptance and machine activation remain separate actions.

The default cache-outage policy must be explicit for each consumer: build from available inputs or fail clearly.
A source-archive outage may block evaluation or rebuild if the source is not already available locally or from a configured cache.
Existing NixOS generations remain available for rollback.

## 11. Foundation proof

The first proof uses one real package, one source and build host, Attic, and a cold second NixOS machine.
The package and consumer may use devenv where its output and lock provide the exact required graph.
No current Vendomat implementation is an interface requirement for this proof.

1. Commit the producer source, package recipe, checks, and relevant locks.
2. Commit a consumer selection of that producer for one target system.
3. Inventory locked inputs and evaluate the selected build graph to discover source needs.
4. Retain and verify the required available source, and report coverage gaps.
5. Clear relevant local source caches and block tested upstream source endpoints.
6. Re-evaluate, run checks, and build from retained source; confirm the consumer requests the same output.
7. Publish the requested output and reachable runtime closure to Attic.
8. Confirm a cold second machine substitutes and runs the selected output.
9. Run local Nix garbage collection and verify the source archive remains intact.
10. Restore source and Attic state from backup, including cache signing state, and repeat the key checks.
11. Exercise source, check, build, upload, cache, and substitution failures without changing a consumer lock.

If devenv cross-project outputs cannot preserve the consumer's exact derivation, use a direct Nix package output for that path.
That decision does not require a new Vendomat package format.

## 12. First upgrade proof

The next proof uses the same selected package and consumer.

1. Discover one new producer release.
2. Prepare one exact native lock diff in an isolated consumer checkout.
3. Verify retained source, build, checks, and cache publication for that proposed state.
4. Show a failed candidate without changing the current consumer.
5. Review and accept one passing proposal.
6. Confirm the accepted lock requests the validated derivation and output.
7. Deploy through the normal machine workflow as a separate action.

Only after this proof should a periodic sweep or broad release automation become part of the system.

## 13. Invariants and non-goals

1. Native consumer locks remain authoritative.
2. Every published result is tied to an exact consumer selection and target system.
3. Claimed retained source must be verified and used by the tested build.
4. A source mismatch or missing required source blocks publication.
5. Failed checks, builds, or uploads never change a consumer selection.
6. Discovery and cache publication never promote a version.
7. Acceptance requires the owner's explicit review of the native change.
8. A stale candidate must be revalidated before acceptance.
9. Evaluation and runtime do not depend on a live Vendomat service.
10. Source retention, output caching, and backup have separate evidence.
11. Secrets stay outside tracked files and Nix store objects.
12. Release identity includes an exact commit; tags may not be moved.

Vendomat is not a package manager, graph database, mandatory daemon, public registry, or general agent platform.
It does not require editor, shell, Atuin, prediction, or semantic capability integration.
It does not claim full offline reconstruction or complete machine-wide source coverage without separate audits.

## 14. Architectural essence

```text
devenv or another native consumer declaration
                 ↓
          committed native locks
                 ↓
      retained and verified source
                 ↓
       exact checked Nix output
                 ↓
               Attic
                 ↓
        normal NixOS consumption
```

Later automation prepares a different native consumer state and validates that exact state before the owner accepts it.
devenv supplies the project interface, task graph, and build outputs where it fits.
Vendomat supplies the source and lifecycle evidence that devenv, Nix, and Attic do not provide on their own.

## Technical basis

- [devenv inputs and locks](https://devenv.sh/inputs/), [outputs](https://devenv.sh/outputs/), [tests](https://devenv.sh/tests/), and [tasks](https://devenv.sh/tasks/)
- [devenv cross-project references and limits](https://devenv.sh/guides/polyrepo/)
- [devenv Machines and deployment plans](https://devenv.sh/machines/)
- [Nix flake source archiving](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-flake-archive) and [garbage-collection roots](https://nix.dev/manual/nix/2.31/package-management/garbage-collector-roots)
- [Nix source and output closures](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query)
- [Attic push and closure handling](https://docs.attic.rs/reference/attic-cli.html)

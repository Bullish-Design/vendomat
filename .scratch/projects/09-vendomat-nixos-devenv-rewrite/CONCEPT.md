# Project 09: one source store, Nix builds, and Attic delivery

**Status:** Proposed architecture for a greenfield rewrite.
**Decision:** [Vendomat architecture](../../../docs/CONCEPT.md).
**Scope:** One person's NixOS machines on a tailnet.

## 1. Goal and boundary

Vendomat retains the available source code for software selected by the owner's machines.
One durable source store feeds a build host. The build host publishes checked Nix outputs to
Attic. Other NixOS machines select revisions in their own locks and obtain the matching outputs.

```text
machine and project locks
    → capture exact available source in one store
    → build and check from retained source
    → upload selected Nix output to Attic
    → substitute on another NixOS machine
```

The source store is not a second package manager. It retains source bytes and reports coverage.
Consumer locks select versions. Nix evaluates recipes and builds outputs. Attic serves binaries.
The source store, builder, and Attic can share one host. Consumers do not need a second curated
source store, although Nix can keep temporary source objects on each machine.

The first coverage target is Nix-managed software in a selected NixOS or project configuration.
Source for binary-only packages or external installation methods may be unavailable.
The inventory must name each gap. Do not claim complete machine coverage from one flake archive.

## 2. Ownership

| Owner | Declaration or state |
| --- | --- |
| NixOS configuration | Source host, builder, Attic service, Nix client settings, tailnet access, storage, and backups. |
| Producer repository | Source history, package recipe, package checks, and build inputs. |
| Consumer flake | Selected producer revision, effective dependency graph, and selected output. |
| Source store | Immutable acquired source, identity records, coverage report, and retention. |
| Attic | Signed Nix output paths and cache retention. |
| Vendomat command | Source capture and verification; checked build and publication when direct commands repeat risky steps. |
| devenv | Optional tools and task names for a producer's local workflow. |

No separate Vendomat daemon or global version catalog is required.
No shared NixOS or devenv module is required before real configurations repeat the same settings.
Each source fact has one owner. The source inventory reports what the locks select and what the
store holds; it cannot silently change a consumer's lock.

## 3. Source identity and storage

Store exact revisions, not moving branches or tags. Retain the original locator, revision or
declared hash, content hash, local location, capture result, and selecting lock. Use ordinary
Git mirrors for repositories and hash-verified archives for archive inputs when they suffice.
Expose immutable source references to the builder and consumers through a tailnet endpoint.

Persistent source storage and its backup sit outside the garbage-collected Nix store.
Nix may copy source into its own store during evaluation or a build. Such a copy does not satisfy
durable retention unless a root and backup policy explicitly preserve it. Verify a restored
source store before deleting its only original copy.

`nix flake archive` covers flake inputs. Package recipes may fetch additional upstream archives,
patches, or repositories. An installed output's runtime closure does not list every build input.
Source discovery must inspect the selected build graph and verify the source that Nix actually
uses. Report every source that remains unknown or unavailable. Avoid a general parser for all
Nix expressions; prove discovery on one real configuration and expand from failures.

Retention starts with sources selected by active locks and a stated recovery period for older
locks. Source retention is independent of Attic retention and local Nix garbage collection.
Backups must include retained bytes and their identity records.

## 4. Build identity and publication

A producer flake declares an installable package and meaningful checks. A developer can build
the working tree locally, but a publishable output must come from the retained immutable source.
The builder checks that source with the effective locked input graph, then builds the selected
output. Block upstream source access during the proof. Allow an external binary cache for build
tools only if the report distinguishes that dependency from retained source.

The top-level consumer `flake.lock` is the effective input graph. It can override inputs from a
producer flake. The builder must compare its evaluated derivation and output path with the path
requested by the consumer. The producer's source revision alone cannot establish a cache hit.
For a library built with the consumer's `pkgs`, build from the consumer graph.

The publication record contains the selecting lock, source identities, system, derivation path,
output path, check result, Attic target, and upload result. It is evidence, not another pin.
Only a successful check and upload can report publication success. The upload does not change a
consumer lock. Confirm that Attic or another configured cache serves the needed runtime closure.

Attic signs outputs that it serves. A signature proves acceptance by the trusted cache key,
not independent reproduction from source. A push credential therefore grants authority over
bytes that a consumer can execute. Restrict write tokens. Keep signing state on the cache host.
Back up Attic state and objects together, and test a restore with the existing client key.

## 5. Consume and failure rules

A consumer pins a producer through an immutable reference to the source store and selects a
package output. It reviews its top-level lock, including transitive changes. The source store
supports flake evaluation and a possible rebuild. Attic supplies the exact requested output.
Different architectures request distinct outputs.

A cache outage never updates the lock. A consumer either builds from available inputs or fails
with a clear cache dependency. A source-store outage may stop evaluation even when Attic has
the output. Keep a previous NixOS generation for rollback and test both outage paths.

A source hash mismatch blocks capture and publication. A missing source remains a named coverage
gap. A failed upload leaves the prior consumer configuration usable. If a cache token leaks,
replace it and treat outputs accepted during the exposure as untrusted until checked again.

## 6. Declarative and operational work

NixOS declares machine services and client settings. Flakes declare recipes and selected inputs.
devenv may declare tasks. Source acquisition, hash checks, builds, uploads, lock updates, backup,
restore, and activation are operations. Scheduling an operation does not prove it completed.

Start with direct Nix, Git, and Attic commands. Implement the smallest Vendomat command after
the first direct proof identifies repeated source capture or publication steps. A producer may
call it from devenv. Do not create `vendomat.yaml`, a global action registry, or package recipe
helpers before a real need appears.

## 7. Acceptance proof

One real producer and a second NixOS machine prove the first version when:

1. The source store retains the exact producer revision and required available source inputs.
2. The inventory names captured sources and every missing or unknown source.
3. The builder checks and builds with upstream source endpoints blocked.
4. The consumer and builder evaluate the same derivation and output path.
5. Attic serves the selected path and needed closure to the second machine.
6. Restored source storage passes hash checks and supports the same build.
7. Cache and source outages produce the documented fallback or clear failure.

This proof does not claim a full offline rebuild. That claim also requires retained build tools
and every other build input, plus a test without external binary caches.

## 8. Deferred work

The first system does not need a general action model, context provider, Atuin or Neovim adapter,
fleet scheduler, automatic watcher, or generated configuration. Package a useful command with
Nix and call it from another interface when an actual workflow needs it.

## References

- [Nix flakes and locks](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake.html)
- [Archiving flake inputs](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake-archive.html)
- [Source and binary closures](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query)
- [Garbage collection roots](https://nix.dev/manual/nix/2.35/package-management/garbage-collector-roots)
- [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html) and [Attic client](https://docs.attic.rs/reference/attic-cli.html)

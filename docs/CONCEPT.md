# Vendomat: one source store for personal NixOS machines

> Architecture decision, 2026-10-04. This describes a greenfield system for one owner's NixOS machines.

## Purpose

Vendomat keeps one durable local store of the available source code for software the owner uses.
One build host builds selected packages from that store and publishes Nix outputs to Attic.
Other NixOS machines select package revisions in their locks and obtain outputs from Attic.

```text
NixOS and project locks → one source store → build host → Attic → NixOS consumers
```

The source store retains source inputs. Attic distributes built outputs.
A successful cache download does not show that source was retained.
The source store, build host, and Attic may run on the same NixOS machine.
Consumers may hold temporary Nix copies, but they do not run separate vendor stores.

The first scope is Nix-managed software selected by the owner's machine and project locks.
Vendomat records source it cannot obtain. Binary-only software, unavailable source, and software
installed outside Nix remain visible gaps. Later work may cover other installation methods.

The existing Vendomat implementation does not define the rewrite's interfaces.
The [project concept](../.scratch/projects/09-vendomat-nixos-devenv-rewrite/CONCEPT.md) gives the detailed contract.
The [implementation guide](../.scratch/projects/09-vendomat-nixos-devenv-rewrite/IMPLEMENTATION_GUIDE.md) orders the proofs.

## Ownership

| Part | Responsibility |
| --- | --- |
| NixOS | Configure the source host, build host, Attic, tailnet access, Nix clients, storage, and backups. |
| Source repositories | Own source history and package recipes. Publish immutable revisions for the source store to acquire. |
| Consumer flakes | Select packages and their effective input graph in a reviewed `flake.lock`. |
| Nix | Evaluate recipes, build derivations, and identify source and output store paths. |
| Source store | Retain exact available source snapshots after local Nix garbage collection. |
| Attic | Serve signed Nix outputs. The consumer must reach the rest of each runtime closure. |
| devenv | Provide optional repository tools and local tasks. |
| Vendomat | Capture source, report coverage, and coordinate checked builds and publication when native commands leave repeated work. |

No Vendomat daemon, global version registry, package manager, or general NixOS module is required.
Each consumer lock selects its package revisions. The source inventory records retained bytes;
it does not select versions.

## The source store

The source host keeps immutable source snapshots in persistent, backed-up storage outside the
garbage-collected Nix store. It can use Git mirrors for repositories and verified files for archives.
Start with existing Git, file, and HTTP interfaces that Nix can fetch. A custom source protocol
or database needs a concrete failure that ordinary files cannot solve.

For each captured source, record its original locator, exact revision or declared hash, content
hash, local location, and capture status. Connect it to the machine or project lock that selected it.
Record missing source and the reason it is missing. A branch, tag, or mutable URL alone is not
an immutable source identity.

A flake archive captures a flake and its flake inputs. It does not establish that every upstream
archive used by package derivations is present. Installed output closures usually omit build-time
sources. Vendomat must inspect the evaluated build graph and test the selected recipes against
retained inputs. It must report source that it cannot identify or fetch.

Retain source needed by active locks. Keep old revisions for a stated recovery period.
Local Nix garbage collection must not delete the only copy. Test backup and restore before
calling the source store durable. Capture succeeds only when the source hash matches its identity
and a build can use the retained copy.

The source store exposes read-only, tailnet-reachable references when consumers need source to
evaluate flakes. A consumer must not need an upstream source repository for a revision that the
source store claims to supply. Write access belongs to the source host's capture operation.
NixOS configures storage, access, and backup paths. Secrets stay outside Nix store objects and
tracked configuration files.

## Build and publish

A producer exposes a Nix package output and meaningful checks. Its recipe remains usable with
direct Nix commands. Local working-tree builds remain development experiments.

For publication, the build host selects an immutable source snapshot retained in the source
store. It checks and builds from that snapshot. The report records the source identity, effective
input graph, system, derivation, output path, and check result. The build must not silently fetch
a different source from an upstream location.

The consumer's top-level `flake.lock` defines its effective input graph. A consumer can override
a producer's inputs and request a different derivation. For a standalone application, compare
the host's and consumer's evaluated output paths before claiming Attic can serve it. Build a
library that uses the consumer's package set from that consumer's locked graph.

After checks pass, the build host uploads the selected output to Attic. It must also make the
needed closure available through Attic or other caches that the consumer can reach. An upload
failure returns failure and never advances a consumer lock. Publication confirms that Attic
serves the expected path.

Attic signs served outputs. Its signature shows that a trusted cache key accepted those bytes.
It does not prove that an independent build would produce them. A push token therefore grants
real trust over executable code. Give publishers narrow credentials. Back up Attic state and
stored objects together, and keep signing state on the cache host.

## Consume

A consumer selects a producer revision and package output in its flake configuration.
It reviews and commits its top-level lock, including transitive inputs. The source store supplies
source needed for evaluation. Attic supplies bytes when the exact requested store path exists.
The consumer can build locally only when it can obtain the needed sources and build dependencies.

```text
consumer lock → exact source and effective inputs → requested output path
source store → source needed to evaluate or rebuild
Attic → trusted bytes for the requested output path
```

Changing the source store or Attic must not silently change a consumer's selected revision.
Different architectures require distinct outputs. Cache and source retention use separate rules.
Keep a previous NixOS generation for rollback when source or cache access fails.

## Declarative and operational boundary

NixOS declares machine services, endpoints, Nix settings, and storage paths.
Flakes declare recipes and selected inputs. devenv can declare a local task.
Source capture, hash checks, builds, cache creation, token issuance, upload, lock updates,
activation, backup, and restore are operations. A declaration does not prove their success.

Start with direct Nix, Git, and Attic commands. Add a Vendomat command when it removes repeated,
error-prone work in source capture or checked publication. A repository may call that command
from devenv. A shared module requires repeated settings in real repositories or machines.

## First complete proof

Use one real producer, one source and build host, Attic, and a second NixOS consumer.

1. Commit the producer recipe and source. Select its revision in a consumer lock.
2. Capture the exact producer source and required available build sources in the source store.
3. Record their identities and report any source that remains unavailable.
4. Block upstream source endpoints. Check and build on the host from retained sources.
5. Compare the host's output path with the consumer's requested output path.
6. Upload to Attic. Confirm a second machine substitutes the path and its needed closure.
7. Restore source storage from backup and repeat source verification.
8. Disable Attic and observe the stated local-build or clear-failure policy.

This proof establishes source retention. A full offline rebuild also needs build tools and other
inputs. Claim that stronger result only after testing without upstream services and external caches.

## Deferred work

The package path does not need action schemas, context bundles, editor adapters, Atuin skills,
automatic watchers, or a fleet scheduler. A useful command can later be installed as a Nix
package and invoked from Neovim or Atuin. Those integrations do not define Vendomat's contract.

## Technical basis

- [Nix flakes and locks](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake.html)
- [Archiving flake inputs](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake-archive.html)
- [Source and binary closures](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query)
- [Garbage collection roots](https://nix.dev/manual/nix/2.35/package-management/garbage-collector-roots)
- [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html) and [Attic client](https://docs.attic.rs/reference/attic-cli.html)

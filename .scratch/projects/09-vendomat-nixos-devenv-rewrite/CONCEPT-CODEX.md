# Vendomat: a personal source-to-capability system

**Status:** Proposed minimum viable product for a greenfield rewrite.
**Scope:** One person's NixOS machines on a tailnet.

## Purpose

Vendomat keeps one durable store of the available source code for software the owner uses.
It builds selected software from retained source and sends outputs to Attic.
Each NixOS machine selects usable software through its reviewed configuration and locks.

```text
reviewed machine and project locks
    → one durable source store
    → Nix checks and builds on one host
    → Attic cache
    → another NixOS machine
```

The first target is software selected by NixOS and project locks.
The long-term goal is source coverage for all software used on the owner's machines, where possible.
Vendomat records source it cannot obtain, including source for binary-only software.
The first version proves the path for one useful personal command on two machines.

## Ownership

| Part | Responsibility |
| --- | --- |
| Producer repository | Own the code, Nix package recipe, and meaningful checks. |
| Consumer flake and `flake.lock` | Select the package and its effective input graph for a machine. |
| Source store | Retain exact available source and report coverage. |
| Nix | Evaluate the selected recipe, run checks, and build the requested output. |
| Attic | Store and serve the built output and its required runtime closure. |
| NixOS | Configure storage, services, tailnet access, client trust, credential delivery, and backups. |
| devenv | Provide the human interface for capture, publication, and status tasks. |

The first version uses one source, build, and Attic host.
NixOS machines still have their normal local Nix stores.
They do not maintain separate durable source stores.
Vendomat needs no daemon, package registry, or new package format.

## The source store

The source store holds immutable revisions and verified archives outside ordinary Nix garbage collection.
It records each source's original location, revision or declared hash, content hash, local location, and selecting lock.
It exposes read-only source references to the builder and consumers when they need to evaluate or rebuild.
Only the capture operation can write source.

Source coverage includes more than flake inputs.
Package recipes can fetch other archives, patches, and repositories during a build.
Vendomat checks the selected build graph and reports every source it cannot retain or identify.
An installed program's runtime closure alone cannot establish source coverage.
The builder must use retained copies for source that the store claims to provide.
Backups protect retained source and its identity records.

## The devenv workbench

The Vendomat repository defines the first devenv tasks.
Run the tasks on the source and build host:

```text
devenv tasks run vendomat:publish --input consumer=<immutable-ref> --input package=<attribute>
devenv tasks run vendomat:status
```

`vendomat:publish` takes a committed consumer flake, selected package, and target system.
It uses that flake's lock to capture and verify source, run checks, and build the selected output.
It pushes the output closure to Attic and reports identities, paths, checks, and upload results.
A failed step stops publication and leaves consumer locks unchanged.
`vendomat:status` reports retained source, coverage gaps, and published outputs.

devenv declares and runs the workflow; each invocation is an operation.
Its lock pins workbench tools, while the consumer's lock selects package inputs.
Start with inspectable tasks. Extract a Vendomat command only when task code becomes hard to maintain.

## One complete publish and consume flow

1. Commit a producer's code, package recipe, checks, and input lock at an exact revision.
2. Capture that revision and its available build sources in the source store.
3. Select its immutable source-store reference in a consumer flake. Review, commit, and retain that flake and its top-level lock.
4. Run `vendomat:publish` against the retained consumer revision on the build host.
5. Compare the host's derivation and output path with the consumer's requested path.
6. Complete the checks and build, then push the requested output and runtime closure to Attic.
7. Deploy the consumer configuration and confirm that the second machine substitutes and runs the command.

Publication never updates a consumer lock or activates a machine.
The report records what happened; it does not select a version.
Attic's signature establishes cache trust, not independent reproduction from source.
The build host holds a restricted push credential.
Consumers hold the cache's public trust key, not a push credential.
Keep secrets outside tracked files and Nix store objects.

## Failure and recovery rules

A source hash mismatch or missing required source blocks publication and appears in the status report.
A failed check, build, or upload returns failure and leaves the previous machine generation usable.
A cache outage follows an explicit policy: build locally from available inputs or fail clearly.
A source-store outage can stop evaluation even when Attic holds an output.
Retain prior source revisions for a stated recovery period.
Back up and test restore for both the source store and Attic state, including signing keys.

## First proof and deferred work

The minimum viable product succeeds when one real command runs on a second NixOS machine from an Attic substitution.
The proof also verifies source after local garbage collection and after a backup restore.
It builds from retained source with upstream source endpoints blocked.
It confirms that the build host and consumer request the same output path.
It shows the stated behavior when Attic or the source store is unavailable.

This proof does not establish a full offline rebuild.
That requires retained build tools and every other build input, plus a separate offline test.
Defer a general action model, context providers, editor adapters, Atuin integration, automatic watchers, and fleet scheduling.
Package the first command normally; other interfaces can call it when a real workflow needs them.

## Technical basis

- [devenv tasks](https://devenv.sh/tasks/) and [devenv locks](https://devenv.sh/files-and-variables/)
- [Nix flakes and locks](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake.html)
- [Nix garbage collection roots](https://nix.dev/manual/nix/2.35/package-management/garbage-collector-roots)
- [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html) and [Attic client](https://docs.attic.rs/reference/attic-cli.html)

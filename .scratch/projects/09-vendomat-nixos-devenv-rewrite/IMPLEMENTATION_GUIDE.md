# Project 09: implementation guide

**Status:** Planned. No rewrite implementation has started.
**Architecture:** [Project concept](CONCEPT.md) and [repository decision](../../../docs/CONCEPT.md).

This guide proves one durable source store, builds from that store, and Attic delivery.
Complete each proof before expanding coverage. The old Vendomat interfaces are not requirements.

## Working rules

- Use Gitman for version control and Testee for repository verification, as `AGENTS.md` requires.
- Keep the selected package build available through a direct Nix command.
- Use the consumer's effective lock when proving the output that consumer requests.
- Keep retained source and Attic state in backed-up storage outside the local Nix garbage collector.
- Keep credentials out of tracked files and Nix store objects.
- Record source identity, system, derivation, output path, checks, and cache result for each publication.
- Report source that cannot be obtained. Do not turn an unknown source into an implicit success.

Use one real producer, one source and build host, Attic, and a second NixOS consumer.
The source host, builder, and Attic may share one machine. Start with one architecture.

## Phase 0: fix the proof boundary

1. Name the source and build host, Attic endpoint, producer, consumer, and source remote.
2. Record both machines' architectures and Nix versions.
3. Choose the first NixOS configuration whose source coverage will later be audited.
4. Locate durable source and Attic storage, backup destinations, and tailnet names.
5. State whether a consumer builds locally or fails when Attic is unavailable.
6. Run the current Testee gate and record pre-existing failures.
7. Create an isolated Gitman lane. Keep existing outputs available during the proof.

**Deliverable:** A short environment and failure-policy record.

**Gate:** The consumer can reach the source host and source remote. Storage and backup owners are named.

## Phase 1: prove the selected Nix package

1. Give the producer one useful `packages.<system>.default` output and a meaningful check.
2. Commit its recipe, source, and `flake.lock`. Publish an immutable revision to its remote.
3. Select that revision as a consumer flake input. Review the consumer's full lock graph.
4. Build and check the selected revision without Vendomat. Run the output locally.
5. Record the producer and consumer derivation and output paths.
6. Resolve any input override that makes the two paths differ. For a composable library, use
   the consumer's locked graph as the build graph.

The producer's working tree remains useful for development. It is not the publication input.

**Deliverable:** A useful direct Nix build and a reviewed consumer lock.

**Gate:** The consumer and build host request the same derivation and output path.

## Phase 2: prove durable source capture

1. Create persistent, backed-up source storage on the one source host.
2. Capture the producer's exact Git revision. Keep a ref or other retention mechanism that
   prevents a mirror from pruning that revision.
3. Capture available flake inputs and source archives required by the selected build.
4. Record original locators, revisions or declared hashes, content hashes, local locations,
   selecting lock, and capture results. Give missing sources explicit reasons.
5. Expose the retained producer revision through a read-only tailnet source reference.
6. Make the builder and consumer use that reference for the proof.
7. Block upstream source endpoints. Check and build the selected output again.
8. Compare its derivation and output paths with the paths from Phase 1.
9. Run local Nix garbage collection, then verify that the source store still holds the inputs.
10. Restore source storage and identity records from backup. Verify hashes and repeat the build.

`nix flake archive` covers flake inputs, not every source fetched by package recipes.
Inspect the evaluated build graph. An external binary cache may supply build tools during this
proof, but the report must name that dependency. Do not call this a full offline rebuild.

**Deliverable:** Retained source, a source inventory, and a restore procedure.

**Gate:** With upstream source endpoints blocked, the retained inputs produce the expected output
path. Garbage collection and backup restore do not remove the only usable source copy.

## Phase 3: prove direct Attic publication and substitution

1. Add Attic's NixOS module to the cache host. Declare service storage and its tailnet endpoint.
2. Choose a read policy. The default is unauthenticated reads on the restricted tailnet endpoint.
3. Create a scoped push token. Keep Attic signing state and tokens outside tracked Nix files.
4. Configure the consumer's NixOS `nix.settings` with the endpoint and trusted public key.
5. Upload the checked output with the Attic client. Confirm the needed runtime closure is
   available through Attic or other caches configured on the consumer.
6. Remove the selected output from the consumer's local store. Build or activate its configuration.
7. Inspect Nix's transfer log and confirm that Attic supplied the requested output path.
8. Test that read-only access cannot push. Record token expiry and replacement steps.
9. Restore Attic state and objects from backup. Confirm that the existing client key still works.
10. Disable Attic and observe the fallback or clear failure stated in Phase 0.

Attic creates and manages cache signing keys. Back up the state that preserves those keys.
Attic signatures establish cache trust, not independent reproduction from source.

**Deliverable:** A signed, cross-machine cache proof and a restore procedure.

**Gate:** The second machine substitutes the exact path selected in Phase 1. A cache outage
does not change its source pin. Attic restore preserves the client trust relationship.

## Phase 4: audit a machine's source coverage

1. Evaluate the selected NixOS configuration from Phase 0 and enumerate its package build graph.
2. Connect each selected source input to an immutable local copy or a specific gap reason.
3. Include flake trees, archives, patches, and other source objects used by those builds.
4. Classify binary-only and unavailable-source inputs. Record source from non-Nix installers
   separately until an integration can identify and retain it.
5. Build selected outputs from retained source where possible. Send checked outputs to Attic.
6. Block upstream source endpoints and rerun the source-dependent build checks.
7. Review the inventory after a consumer lock update and capture newly selected source before
   publication.

Start with the first producer and expand by actual build graph. Avoid a generic Nix parser.
Do not claim complete coverage while unknown inputs remain without a recorded reason.

**Deliverable:** A machine coverage report with retained sources, unavailable sources, and
unresolved sources shown separately.

**Gate:** Every source input identified for the selected configuration has a verified local copy
or a specific unavailable-source reason. No build silently fetches upstream source during the proof.

## Phase 5: add only the Vendomat code the proofs need

1. Repeat source capture and publication for a second real producer.
2. Record the exact repeated commands and failure cases from both producers.
3. Implement the smallest command that verifies source identity and reports coverage.
4. Add checked build and Attic upload to that command only if repetition causes real errors.
5. Keep direct Nix and Attic commands usable. Let devenv call the command if a producer wants
   a local task name.
6. Add shared NixOS or devenv modules only for settings repeated on real hosts or repositories.
7. Test a hash mismatch, a missing source, a failed check, and a failed upload.

The command report includes the selecting lock, source identities, system, derivation,
output path, checks, cache target, and result. It never edits a consumer lock.

**Deliverable:** Minimal source and publication code justified by observed repetition.

**Gate:** Direct and Vendomat paths select the same inputs and output. Failures cannot report
publication success. If native commands remain clear, stop without adding a shared module.

## Phase 6: cut over

1. Replace public Vendomat interfaces with the proven source and publication contract.
2. Remove old code, options, tests, and documentation that no longer describe Vendomat.
3. Update `README.md` and `AGENTS.md` after the new interfaces work.
4. Add tests for source identity, coverage reports, failure paths, and machine settings.
5. Run the normal Testee gate and the real two-machine proof again.
6. Confirm that active consumers no longer import interfaces slated for removal.
7. Land and push the completed Gitman lanes.

The old library has no compatibility requirement. Cut over only after source retention,
Attic delivery, and the machine coverage audit pass.

**Deliverable:** A repository whose public code and documentation match the new architecture.

## Final acceptance

- One central source store retains verified source despite local Nix garbage collection.
- A restored copy supplies the same selected source and build.
- The inventory reports source coverage and specific gaps for a selected NixOS configuration.
- A build with upstream source endpoints blocked uses retained sources.
- Checks block publication on failure.
- Builder and consumer evaluate the same derivation and output path.
- Attic serves that path and its needed closure to a second NixOS machine.
- Cache and source outages follow the recorded failure policy without changing a consumer lock.
- The old implementation is removed after the new path passes.

## Upstream references

- [Nix flakes and locks](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake.html)
- [Archiving flake inputs](https://nix.dev/manual/nix/2.35/command-ref/new-cli/nix3-flake-archive.html)
- [Source and binary closures](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query)
- [Garbage collection roots](https://nix.dev/manual/nix/2.35/package-management/garbage-collector-roots)
- [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html) and [Attic client](https://docs.attic.rs/reference/attic-cli.html)

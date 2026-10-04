# Project 09: step-by-step implementation guide

**Status:** Planned. No rewrite implementation has started.
**Architecture:** [Project concept](CONCEPT.md) and [repository decision](../../../docs/CONCEPT.md).

This guide orders the work. Complete each proof before adding the next layer.
The old Vendomat interfaces are not compatibility requirements.

## Working rules

- Use Gitman for version control and Testee for repository verification, as `AGENTS.md` requires.
- Keep every package build available through a direct Nix command.
- Keep one owner for each package revision, build recipe, and cache setting.
- Put runtime secrets and mutable state outside the Nix store.
- Record the selected source revision, system, store path, and cache result for every publication proof.
- Prefer a small real producer repository over a demonstration that only builds `hello`.

The core proof uses one cache host, one producer, and a second NixOS machine as consumer.
Choose a producer whose output the second machine can actually use.
Start with one system architecture. Add another architecture when a real consumer requires it.

## Phase 0: record the starting point

1. Record the selected cache host, consumer machine, source remote, and producer repository.
2. Record each machine's architecture and Nix version.
3. Locate the cache host's writable storage, backup destination, and tailnet name.
4. Run the repository's current Testee gate. Record any pre-existing failures.
5. Create an isolated Gitman lane for the rewrite. Keep old outputs available during the proof.

**Deliverable:** A short environment record in this project directory.

**Gate:** Every machine and repository in the proof has a named owner and reachable source remote.

## Phase 1: prove a direct Nix package

1. Give the producer one installable `packages.<system>.default` output.
2. Keep its package recipe in `flake.nix` or a file imported by `flake.nix`.
3. Pin its build inputs in `flake.lock`.
4. Add at least one meaningful Nix check for the output.
5. Build the output with `nix build .#default` and record its store path.
6. Run the check without Vendomat. Confirm that a failing check returns failure.
7. Install or run the output locally. Confirm that it performs its intended job.

Use the project's own build tools inside the Nix recipe. Do not copy build commands
into a Vendomat task yet. A package can use Rust, Python, shell, or another language.

**Deliverable:** A real producer flake and a recorded direct-build result.

**Gate:** The Nix package is useful and builds without any new Vendomat code.

## Phase 2: bring up the tailnet cache

1. Add Attic's NixOS module to the cache host configuration.
2. Declare Attic's service, writable storage, and retention policy in NixOS.
3. Put the cache behind a tailnet-only HTTPS endpoint with a stable name.
4. Create the signing key and upload credentials through the machine's secret mechanism.
5. Keep private key material and tokens out of tracked Nix files and the Nix store.
6. Configure the client NixOS machine with the cache URL and trusted public key.
7. Verify that the client can read the cache and cannot upload with read-only access.
8. Define how Attic state and signing keys are backed up and restored.

Use NixOS settings for the cache client. Avoid relying on a manual `attic use` step
that changes each user's Nix configuration outside the machine declaration.

**Deliverable:** Cache host and client NixOS declarations, plus a private credential procedure.

**Gate:** The client reaches the signed cache over the tailnet. Write access requires separate credentials.

## Phase 3: prove direct cache publication and substitution

1. Publish the producer's committed source revision to its source remote.
2. Build and check that revision on the producer machine.
3. Upload its exact store path with the Attic client.
4. Pin the producer as a flake input on the consumer machine.
5. Select its package output in the consumer's NixOS or project configuration.
6. Build or activate the consumer configuration with the local output absent.
7. Inspect Nix's result and logs. Confirm that the requested output came from Attic.
8. Disable the private cache for one test. Confirm the expected local build or clear failure.
9. Restore the cache setting after the test.

The source remote supplies the recipe. Attic supplies its built output.
Check that changing the cache does not change the consumer's selected source revision.

**Deliverable:** A cross-machine proof with source revision, output path, and cache evidence.

**Gate:** The second machine consumes the pinned package without a sibling checkout.

## Phase 4: add Vendomat's small shared interface

1. Export a reusable devenv module from Vendomat.
2. Let the producer select one flake output and one cache target in `devenv.nix`.
3. Implement `package:build` as a call to the selected Nix output.
4. Implement `package:check` as a call to the producer's declared Nix checks.
5. Implement `cache:push` as check, build, upload, and result reporting.
6. Implement `cache:status` as a read-only report of target and output availability.
7. Add a small NixOS module only for cache settings repeated on several machines.
8. Keep direct Nix and Attic commands documented beside their Vendomat task names.

The push task rejects source content that differs from the published revision.
It reports that revision and uploads the store path returned by the selected build.
It does not advance any consumer lock or claim that a cache upload is a package release.

Define task inputs and outputs before implementing the scripts. At minimum, reports include
the package output name, source revision, system, store path, cache target, and status.
Use consistent exit statuses for success, rejected publication, configuration failure, and invalid use.

**Deliverable:** A documented devenv task module and minimal helper commands.

**Gate:** Direct `nix build .#default` and `package:build` select the same output.
`cache:push` cannot report success after a failed check or upload.

## Phase 5: test reuse without a framework

1. Apply the shared task module to a second real producer repository.
2. Keep each producer's recipe and dependency pins in its own flake.
3. Check that the module adds only the selected tools and tasks.
4. Confirm that a task runs directly, without shell-entry side effects.
5. Record any duplicated package recipe logic across the two producers.
6. Extract a Nix helper only for logic that both producers actually share.
7. Add a second architecture build only if a selected consumer uses that architecture.

This phase tests whether Vendomat's options describe a real repeated pattern.
Do not add a global repository catalog, version registry, or language-wide builder collection.

**Deliverable:** Two producers using one small Vendomat module.

**Gate:** Both producers keep direct Nix builds and independent source pins.

## Phase 6: prove one cross-interface action

This phase starts after the package foundation works. It is a separate acceptance proof.

1. Implement one `code.review` command with a documented input and output format.
2. Make the command accept an explicit target and source snapshot identity.
3. Return structured findings with a format version and source references.
4. Build the command as a Nix package if another repository must consume it.
5. Add an Atuin skill that calls the command and presents its result.
6. Add a Neovim command that calls the same executable and presents its result.
7. Run both adapters against the same target and snapshot.
8. Compare their structured command results before display formatting.
9. Make context extraction record its inputs and replace derived output atomically.

The adapters may differ in display. They may not implement separate review logic.
No general action dispatcher, `vendomat.yaml`, keymap generator, or context server is needed.

**Deliverable:** One command, two thin adapters, one result contract, and an end-to-end proof.

**Gate:** Both surfaces receive the same structured findings for the same input.

## Phase 7: decide whether to add declarations

1. Use the first action in normal work.
2. Add a second action only when it solves a real task.
3. Compare their input, output, context, and adapter code.
4. List repeated declarations that Nix or devenv cannot express clearly.
5. If a repeated shape exists, specify the smallest schema that removes it.
6. Generate one native artifact from that schema and validate it with its owner tool.
7. Keep package pins and build recipes outside any new action schema.

If the repeated shape does not exist, keep the working commands and adapters.
This is a decision gate, not a requirement to build a manifest parser.

**Deliverable:** A recorded decision with examples of the actual duplication.

## Phase 8: cut over the repository

1. Replace Vendomat's public Nix and devenv exports with the proven small interfaces.
2. Remove old Python code, module options, tests, and documentation that no longer describe Vendomat.
3. Update `README.md`, `AGENTS.md`, and the repository concept to name the new interfaces.
4. Add tests for task failure paths, source pins, cache publication reports, and NixOS settings.
5. Run the normal Testee gate and the real two-machine package proof again.
6. Check that no consumer still imports an interface slated for removal.
7. Land and push the completed Gitman lanes.

There is no compatibility requirement for the old vendomat library.
Cut over only after the new build and cache path works end to end.

**Deliverable:** A repository whose code and public documentation match the new concept.

## Final acceptance checklist

- One producer builds through direct Nix and through the Vendomat task.
- Required checks block publication on failure.
- A clean, remote-reachable source revision identifies each published output.
- Attic serves a signed output to a second NixOS machine over the tailnet.
- The consumer lock, not the cache, selects the producer revision.
- Cache absence has a tested fallback or a clear failure.
- The cache signing key and upload token stay out of the Nix store.
- `code.review` has one command and two adapters with matching structured results.
- The old implementation and documentation are removed after the new path passes.

## Upstream references

- [Nix flakes](https://nix.dev/concepts/flakes.html)
- [devenv tasks](https://devenv.sh/tasks/)
- [Attic on NixOS](https://docs.attic.rs/admin-guide/deployment/nixos.html) and [cache use](https://docs.attic.rs/user-guide/)
- [Nix garbage collection](https://nix.dev/manual/nix/2.35/command-ref/nix-store/gc.html)

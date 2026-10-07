# Vendomat V4 implementation guide

**Status:** Canonical. No V4 phase has passed. **Date:** 2026-10-06.

This guide orders the V4 proof work. Each step has an instruction and a **Verify:** line.

Authority:

- [V4 specification](../.scratch/projects/13-vendomat-v4-canonical/V4-SPEC.md): the only normative contract.
- [V4 requirements](../.scratch/projects/13-vendomat-v4-canonical/V4-REQUIREMENTS.md): 60 active IDs.
- [V4 concept](../.scratch/projects/13-vendomat-v4-canonical/CONCEPT-V4.md): goals and boundary.
- [Native baseline](../.scratch/projects/13-vendomat-v4-canonical/NATIVE-BASELINE.md): 24 upstream facts.

The project-09 and project-10 documents do not define V4. Do not follow them for V4 work.

## How to run this guide

1. Open one Gitman lane for each phase. Record its base revision. **Verify:** `devenv shell -- gitman status` shows the
   intended lane and no unrelated work.
2. Before you implement, write the fixture inputs and the expected pass, fail, and gap results. **Verify:** Another
   reader can run each check without guessing a version, host, or selection.
3. Record the command, exit status, relevant output, selected revisions, and observed identities in a dated record. Keep
   raw logs outside the repository. **Verify:** The record separates observation from inference and links its preserved
   logs.
4. Run the repository gate after every change: `devenv shell -- testee verify --mode quick`. Run
   `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` when a change affects the Nix module, toolchain, or
   consumer integration. Do not advance past a failed gate. Fix the implementation, or revise the contract with a
   recorded decision. **Verify:** The next phase cites a passing prior gate and the exact fixture.

## Pin record

The pin record is a document. It is not a phase. It has no gate. There is no P0 and no combined
preflight gate. Record the devenv version, the Nix version, and the target systems. Record the publisher host, the
cold consumer host, and the Attic endpoint. Record each durable state class with its owner and
restore route. Record the native cache policy and the 24 native baseline facts.

The record itself satisfies `V4-OWN-009` and `V4-REC-009`. A missing host is a named blocker on the
phase that needs it. It does not block the programme. The [P0 record](V4_P0_PROOF.md) holds
observed evidence that the pin record may cite.

The pin record is [docs/V4_PIN_RECORD.md](V4_PIN_RECORD.md). Its baseline observations are in the
[native baseline](../.scratch/projects/13-vendomat-v4-canonical/NATIVE-BASELINE.md#observation-record-2026-10-06).

| Phase | Entry condition |
| --- | --- |
| P1, P2 | devenv and Nix. |
| P3 | P2 passed, and a writable store. |
| P4 | P3 passed. |
| P5 | P4 passed, a reachable Attic with a push token and a separate pull token, and a second machine with an empty store. |
| P6 | P5 passed. |
| P7 | A reachable NixOS target and the Machines pin (`V4-MACH-001`). |

## P1 — one focused native module

**IDs:** `V4-OWN-002`, `V4-OWN-003`, `V4-OWN-007`; `V4-MOD-001`, `V4-MOD-002`, `V4-MOD-005`, `V4-MOD-008`, `V4-MOD-009`, `V4-MOD-010`.
**Scenarios:** `V4-PROOF-001`, `V4-PROOF-002`, `V4-CHK-013`.

1. Put one review implementation and one command with a documented result format in one repository. Export a devenv
   module, a NixOS module, and a Home Manager module as distinct native targets. **Verify:** Run the command on known
   input and parse the expected result. Evaluate each target alone. Importing the project target activates no system or
   user configuration.
2. Export the plugin contribution as a `buildVimPlugin` derivation. Export the dedicated editor as `wrapNeovimUnstable`
   with `wrapRc = true`. Substitute the absolute store path of the command into the Lua at build time. **Verify:** Both
   forms invoke the same packaged implementation. Put a conflicting binary first on `PATH`. Both forms still invoke the
   selected store path. The Nixpkgs and Home Manager wrappers default to `--suffix PATH`. Record that a `PATH` lookup
   would lose.
3. Enable the module with no overrides. Then disable the editor and keep the command. Then change one supported option.
   **Verify:** Defaults evaluate as declared. The command runs without the editor. The override changes only its
   intended output.
4. Run the module with no Vendomat process and no Attic. Keep a normal editor profile active beside the dedicated
   output. **Verify:** Both editors keep their own settings. The command produces its expected result. Declare the
   required check set of the module, and confirm it evaluates.

**Gate:** One implementation serves the command and both editor forms. The editor reaches the
command by absolute store path. This gate makes no publication claim and no machine claim.
The result is in the [P1 record](V4_P1_RECORD.md).

## P2 — delivery, overrides, and the publication form

**IDs:** `V4-MOD-011`, `V4-MOD-012`; `V4-SEL-001`, `V4-SEL-002`, `V4-SEL-010`; `V4-OWN-013`.
**Scenario:** `V4-PROOF-003`.

1. Resolve the publication form. Build the same named output through a flake attribute and through
   `devenv build outputs.<name>`. **Verify:** `nix build --json` returns `drvPath` and the output path for the flake
   attribute. `nix flake metadata --json` returns the complete `locks` graph. Record whether `devenv build` supplies an
   equivalent handle. If the flake form cannot express the P1 outputs, stop and revise the contract before P3.
2. Build two clean consumers: a plain devenv repository and a flake-backed repository. Export only the focused module.
   **Verify:** Neither consumer inherits an author-only tool or process. Remove one required input from the plain
   consumer. The diagnostic identifies it. Add an extra input to the `devenv.yaml` of the author. The remote consumer
   does not receive it. This matches the documented limit that devenv does not merge remote `devenv.yaml` imports.
3. Test a reversible local checkout override through both paths, with two independent consumers. **Verify:** The
   effective selection report names each path, profile, and override. Reverting restores the prior result. The accepted
   lock of consumer B does not change.
4. Deny Vendomat and Attic to a fresh local consumer. Permit only the native sources and public caches that the pin
   record allows. **Verify:** The consumer realizes its inputs and runs the command. Record every external source used.
   Do not call this an offline rebuild.

**Gate:** One publication form is chosen and proved. Both delivery forms and a fresh local
realization pass. The tested syntax replaces every proposed name in the specification.
The result is in the [P2 record](V4_P2_RECORD.md).

## P3 — retain selected source

**IDs:** `V4-SRC-002`, `V4-SRC-003`, `V4-SRC-004`, `V4-SRC-006`, `V4-SRC-008`, `V4-SRC-009`, `V4-SRC-011`, `V4-SRC-015`, `V4-SRC-024`.
**Scenario:** `V4-PROOF-004`.

1. Run `nix flake archive --json` on the chosen selection. Add a garbage-collection root for each archived path.
   **Verify:** Every locked input has one store path. `nix flake metadata --json` supplies the `rev` and `narHash` of
   each input. After local garbage collection, every archived path survives. Measure the total archived bytes and record
   them.
2. Record one identity entry for each retained input. Include the locator, locked revision, NAR hash, store path, and
   the consumer selection that chose it. Label the correspondence. **Verify:** A locked input labels as exact selected
   source. A package dependency labels as unresolved, and the record names `pkgs.srcOnly` as the later mechanism.
   Corrupt one retained path. It loses its exact-correspondence claim. Capture a dirty local tree with `nix store add`.
   Change the working tree. The content-addressed identity still names the captured bytes.
3. Read one retained file through its store path from the project. Leave one selected package uncaptured. **Verify:**
   Reading returns the file and its provenance. No lock or output path changes. The uncaptured package reports a
   coverage gap, and the artifact checks still pass. A capture-only record sets no rebuild-proof field.

**Gate:** Every locked input is retained, rooted, identified, and readable. Package source is
reported as unresolved, not guessed. Source retention changes no selection.
The result is in the [P3 record](V4_P3_RECORD.md).

## P4 — bind declared checks to exact bytes

**IDs:** `V4-SEL-003`, `V4-SEL-006`, `V4-SEL-007`, `V4-SEL-009`; `V4-CHK-001`, `V4-CHK-002`, `V4-CHK-004`, `V4-CHK-006`, `V4-CHK-007`, `V4-CHK-010`, `V4-CHK-011`;
`V4-EVD-001`, `V4-EVD-002`, `V4-EVD-005`, `V4-EVD-006`, `V4-EVD-012`.
**Scenarios:** `V4-PROOF-005`, `V4-CHK-003`.

1. Freeze one immutable consumer revision. Evaluate the selection with undeclared host access denied. **Verify:**
   Evaluation succeeds under denial and reproduces the same derivation path on re-evaluation. A selection that needs
   host state cannot be published. The failure names the cause.
2. Assemble the required check set as a declared list of native check names. Tag each name with its owner. Check that
   each name exists with `devenv tasks list --json` before you run any check. **Verify:** The effective set changes when
   a component is enabled or disabled, and when the consumer adds a check. Remove the implementation of a declared
   check. The result is `missing-required`, distinct from `failed-required`. Never use a `devenv:enterShell` task as a
   gate, because shell entry proceeds after such a failure.
3. Run the declared pre-build checks. Realize the output. Then run the artifact and integration checks against that
   output. **Verify:** Instrument the stage order. A failed pre-build check prevents any build success. An artifact
   check given a different output path fails identity validation.
4. Store the four native documents and the six Vendomat fields in one receipt. Record the tool version and the JSON
   format of each document. **Verify:** Compare each stored document with a fresh native query. Inject a canary secret
   into the environment. Neither the receipt nor the preserved logs contain it. Break the derivation. The failure record
   names the stage, and no success result exists.
5. Retry the same selection after partial work. Then change one check input and retry again. **Verify:** Reuse requires
   matching recorded inputs. A changed input reruns its affected check. An existing output path alone is never success.

**Gate:** A failed required check and a missing required check both block success, with different
reasons. The receipt lets a reader reconstruct the exact checked bytes and their selection.
The result is in the [P4 record](V4_P4_RECORD.md).

## P5 — publish and prove Attic consumption

**IDs:** `V4-CACHE-001`, `V4-CACHE-002`, `V4-CACHE-003`, `V4-CACHE-005`, `V4-CACHE-006`, `V4-CACHE-009`, `V4-CACHE-013`, `V4-CACHE-014`, `V4-CACHE-015`; `V4-EVD-003`.
**Scenario:** `V4-PROOF-006`.

1. Configure the cache, a push token, a separate pull-only token, and the trusted public key of the consumer. Create the
   pull token with `atticadm make-token --pull` only. **Verify:** The pull token cannot push. Secrets stay outside
   tracked files and store paths. Record the effective substituter order and the accepted key on the cold machine. Set
   the retention period of the source cache to zero.
2. Seed one runtime dependency from a public cache. Then push the output with its closure. `attic push` includes the
   closure by default. Clear the `upstream_cache_key_names` list of the cache, or pass `--ignore-upstream-cache-filter`.
   Its default entry `cache.nixos.org-1` would otherwise drop the seeded path. **Verify:** The seeded path appears in
   `nix-store -qR` before the push and in the cache afterwards.
3. Query every closure path back from the cache as a store with `nix path-info --store <cache> --json --json-format 2`.
   **Verify:** Every path is present. Record the result and its time in the receipt. A successful push with one absent
   path is a failure. Interrupt an upload and retry. The record shows the partial progress and no false prior success.
4. In an isolated store with other substituters and local builds disabled, substitute the whole closure from the cache
   alone. **Verify:** Every path substitutes. The NAR hash of the served selected output equals the checked hash. Record
   the metadata of each closure member. Attic re-hashes the upload and Nix re-hashes the import. This step confirms the
   end-to-end result. It does not create the guarantee.
5. On the cold machine, select the same immutable output. Run the command and both editor forms. **Verify:** The machine
   starts without the output, obtains it from the cache, and performs no build. Both interfaces run. Remove one
   published object afterwards. The fresh availability report changes. The historical check result does not.

**Gate:** The cache alone serves every required runtime path with the checked bytes. The cold
machine runs the application. This gate makes no machine-generation claim.
Steps 1 to 4 passed 2026-10-07. The gate itself has not passed; it needs the cold machine. See the
[P5 record](V4_P5_RECORD.md).

## P6 — evidence and recovery

**IDs:** `V4-REC-001`, `V4-REC-002`, `V4-REC-005`; `V4-EVD-009`. **Measurement:** `V4-REC-006`.

1. Back up three state classes separately. They are the retained source store paths with their identity records, the
   Attic server signing state, and the receipts with failure logs. Do not back up Attic objects. **Verify:** Record the
   time, owner, restore target, and identity of each class. Source and binaries now share one cache and therefore one
   loss domain.
2. Restore the retained source into a clean location. Read one input again. **Verify:** The restored bytes match their
   recorded NAR hashes. The provenance stays readable. A damaged source backup fails only the source restore claim.
3. Restore the Attic signing state. Rebuild the selected output from a clean checkout of the retained source. Publish
   it, and substitute it with an existing trusted consumer. **Verify:** The output path and NAR hash match P4. The
   consumer accepts it under its existing trust policy. Record that Attic signs at read time with the key of each cache.
   Regenerating that key invalidates the trust setting of every consumer. A missing signing state fails only the
   cache-trust claim.
4. Restore the receipts and logs. Recreate the P4 and P5 reports. **Verify:** Prior check and upload outcomes stay
   explainable. A signature sets no rebuild-proof field. Measure the archived source bytes, the closure size, and the
   transfer bytes. Record them.

**Gate:** Source, cache trust, and evidence restore as three separate results. Do not claim machine
readiness from this gate.

## P7 — the separate machine claim

**IDs:** `V4-MACH-001` (entry), `V4-MACH-004`, `V4-MACH-009`, `V4-MACH-015`.
**Scenario:** `V4-PROOF-009`.

1. Compose a native machine fixture on the pinned Machines version. Include one persistent NixOS service and a separate
   Home Manager role. **Verify:** Each contribution evaluates. The NixOS input requirement `disko` is present, as the
   Machines documentation requires even for an existing host.
2. Create a native plan with `devenv machines plan`. Record its identifier and selected output paths beside the receipt.
   **Verify:** Every recorded path matches `plan.json`. Vendomat creates no second plan. Record two upstream limits. The
   identifier is random, not content-addressed. The plan has no staleness check against the lock or a re-evaluation.
3. Apply the saved plan. **Verify:** Apply uses the saved outputs. Transfer is a direct `nix copy --to ssh://<target>`.
   Record that no Attic substitution occurs. This is the documented upstream behaviour. Confirm that the target accepts
   the copied paths through `nix.settings.trusted-users` or a trusted signature.
4. Fail the NixOS health check after an application write. Separately, fail Home Manager activation after NixOS
   succeeds. **Verify:** System, user, and application outcomes report separately. A NixOS rollback claims nothing about
   user files or application data. Record that the Home Manager role has no staleness check and no automatic rollback.
   Name its activation driver. An application output in the cache sets no machine-generation field.

**Gate:** The pinned fixture proves plan, transfer, activation, and recovery limits. Only now may
V4 text make a machine claim.

## Later work

V4 has no P8, P9, or P10 phase. [FUTURE-WORK.md](../.scratch/projects/13-vendomat-v4-canonical/FUTURE-WORK.md)
holds reviewed upgrades and deferred capabilities, each with its trigger.
[LATER-APPLICATION.md](../.scratch/projects/13-vendomat-v4-canonical/LATER-APPLICATION.md) holds
the `V4-APP-*` IDs. A trigger permits a design session. It does not authorize an implementation.

## Pre-V4 consumer migration

Migration of pre-V4 consumers is a separate project. Start it after P6 passes. It is not a V4 phase
and not a V4 gate. `V4-OWN-012` is retired from V4 scope. Each migrated path needs its own
before-and-after fixture. Existing paths stay in service until their replacement passes.

## Final acceptance checklist

- [ ] The pin record exists. Each blocker names its phase, missing host, and evidence.
- [ ] P1 to P7 each have a dated record, preserved logs, and a passing gate, in order.
- [ ] Each of the 60 active IDs and the nine scenario IDs has a recorded result.
- [ ] `devenv shell -- testee verify --mode quick` passes.
- [ ] `VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick` passes for module, toolchain, or consumer changes.



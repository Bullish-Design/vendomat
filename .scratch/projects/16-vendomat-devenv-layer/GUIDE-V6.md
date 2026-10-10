# Vendomat V6 implementation guide

**Date:** 2026-10-09. **Updated:** 2026-10-10. **Status:** Draft implementation plan.
V5 remains authoritative until the
owner accepts a fixture-backed V6 specification. This guide does not authorize a real disk write,
machine deployment, firmware change, or secret transfer.

**Read with:** [CONCEPT-V6.md](./CONCEPT-V6.md), [SPEC-V6.md](./SPEC-V6.md),
[the concept update](./CONCEPT-UPDATE-2026-10-10.md),
[machine-path research](./RESEARCH-2026-10-09-MACHINE-PATHS.md), and
[the adoption VM plan](./fixtures/VM-TEST-PLAN.md). The research read pinned upstream source and
prior reports. It did not inspect the local Vendomat code or run a new NixOS VM. Project 15 holds
the earlier fixtures; its reports do not satisfy a production gate.

## Agreed direction and finish line

- Complete V6 through the new `server` system, Framework adoption, and workspace conversion.
- Prove the workspace user flow first. A workspace user creates and updates a workspace without
  editing Nix. Module authors may write Nix. The machine operator interface follows later.
- Cut over `server` first. Install it on the empty 4 TB drive. Keep the 512 GB system bootable.
- Adopt the existing Framework NixOS system in place. Keep its data, disk layout, and initial pins.
- Build devenv from a pinned upstream source and a short, ordered patch series. The CLI and modules
  must come from the same resulting source. Remove each patch when an upstream release replaces it.
- Make the supported patched `devenv machines install` command refuse an adopted host before it
  contacts the target, for every phase selection. A Vendomat wrapper is an additional check.
- Keep native `devenv machines plan`, `apply`, `deploy`, `status`, and `rollback` for activation.
  Vendomat supplies composition, input preparation, checks, and the fresh-install preflight.
- Keep V6 a draft until the missing fixtures run and the owner reviews the updated concept and spec.

**Complete** means every active requirement has a saved passing gate, an explicit blocker, or an
accepted deferral. It also means both machines boot and recover, a real workspace user completes
the no-Nix module-selection flow,
and source and build outputs cross the fleet. A passing unit test or a successful Nix build alone
does not establish any of those runtime results.

## Starting state

| Area | Current evidence | Work still needed |
| --- | --- | --- |
| Vendomat CLI | The V6 input resolver and command fixtures have passed in this repository; see the gate record | A no-Nix workspace selection and values interface, plus the open real consumer gates |
| Vendomat flake | One input and `packages.<system>.vendomat`; its current nixpkgs URL is `devenv-nixpkgs/rolling` | One tested plain nixpkgs revision and `devenvModules.default` |
| Source collection | A live `devman` tag and collection hook are reported in V5 records | Rebuild proof, remaining hooks, a cross-host tag push, and source recovery |
| Cache and builder | Attic and host settings have earlier fixture evidence | Real Vendomat output push, cold substitution, watch-store, builder, and recovery proofs |
| devenv | Project 15 built a four-change prototype on v2.4.0 | Reproducible patch source, adopted-host install denial, real install-payload run |
| Machines | Project 15 reports fresh two-disk and deployment VMs | V6 end-to-end VMs, fresh-install bypass guard, populated adoption VM, offline rescue |
| Hosts | `server` runs the old system; the Framework's current layout is unknown here | Privileged server blank-drive scan; read-only Framework inventory; separate cutovers |

The current `.scratch/CURRENT.md` records more exact V5 state and blockers. Check it again before
each implementation session. Treat historical Framework state versions and disk descriptions as
clues, not as observations of the running laptop.

## Rules for every step

1. Record the upstream revisions, source tags, Nix, devenv, disko, Home Manager, sops-nix, Testee,
   and host versions that the step uses. Pin a tool before a fixture tests it.
2. Save the exact command, expected result, exit code, actual result, and a short interpretation.
   Put raw output under `~/.local/state/vendomat/v6/<date>/<step>/<run>/`.
3. Start with a focused fixture. Run the Testee full gate before a release or pull request:
   `testee verify --full`. Run `testee check e2e` for Nix modules, toolchain, or consumer changes.
   Read Testee's saved report. Do not call pytest, ruff, or ty as separate gates.
4. Record source documentation as an upstream fact. Record a fixture as a fixture. Record a VM as a
   VM. Do not report a machine or cache proof from another level of evidence.
5. Before changing a requirement, search the V5 spec, V6 spec, concept, guide, tests, and consumer
   files for the same claim. Preserve every ID. Mark an old requirement superseded by a new ID.
6. Before each version-control change, inspect the working copy. Include all relevant active work.
   Use the owner-approved version-control workflow for that session. Write no attribution line.
   Keep a completed commit synchronized with its remote branch.
7. Treat an unknown disk identity, mount, key, boot path, or command behavior as a stop condition.
   Resume after a read-only observation or isolated fixture resolves it.

The real `server` and Framework operations in Steps 9 and 12 are future operator runbooks. Each
requires a new review of its exact plan and target facts immediately before execution.

The next implementation session should first prove the workspace user flow in one real consumer.
Assign a file and a fixture for the proposed registry values and generated module wiring. Keep
the existing resolver and command evidence. The current description builder is an implemented
prototype, not the new authoring contract. `nix-systems` remains a separate repository for the
machine phase. New file paths and registry keys remain proposed until a fixture proves them.

## Step 0 — Reconcile authority and establish a V6 evidence ledger

**Goal:** make the draft implementable without silently changing V5 authority.

1. Read `.scratch/CURRENT.md`, the active V5 concept/spec/guide, both V6 drafts, project 15's
   follow-up and agent reports, and the imported machine-path research.
2. List every active V5 ID. Record each V6 successor, unchanged ID, withdrawal, and deferral in
   one ledger. Fix the V6 draft's stale references, including `DESC-001` after `DESC-002` and the
   contradictory `FACE-004` count text. Do not replace a V5 ID in place.
3. Mark the machine research's `MACH-014` and later IDs as proposed. Resolve ID collisions against
   the complete ledger before using any of them. Keep the fresh server and adoption requirements
   separate. In particular, replace V6's current `MACH-011` before accepting the spec. Reconcile
   `MACH-001`, `MACH-002`, and `MACH-013` with a temporary Framework workspace on its old pins.
4. Inventory every external proof and blocker: PV-02 disk signatures, the real Attic push/pull,
   patched install payloads, Framework hardware, VM adoption, firmware BootNext, and fleet pins.
5. Create a gate record for each step below. Use `PASS`, `FAIL`, or `BLOCKED`, and link raw logs.

**Gate:** the ledger covers each active V5 and proposed V6 ID once, with no contradictory claim in
the concept, spec, guide, or earlier active guide. V6 remains a draft after this step.

## Step 1 — Produce the pinned devenv distribution

**Goal:** one reproducible CLI and module source, without a maintained moving fork branch.

1. Pin upstream v2.4.0 at `b904dcb51fe48c30db250038241507f60752f222`. The series is six patches in
   `devenv-dist/SERIES`: install SSH handshake, `latest-version`, locked-source offline reuse,
   release-build enforcement, the adopted-host install denial (0005), and the fresh-host preflight
   (0006). `devenv-dist/materialize` rebuilds the fork commit from the pin and the series.
2. Keep patches and their upstream references in version control. Record source commit, patch
   order, patch hashes, resulting source revision, build derivation, and `devenv version`.
3. Materialize a tagged distribution source in the collection so `inputs.devenv` can address its
   patched `src/modules` by the same revision used to build the CLI. Prove this packaging shape
   with a fixture before making it the V6 interface. Never pin a moving branch.
4. Carry an explicit machine mode from Vendomat's inventory to devenv machine metadata. The option is
   `machines.<name>.vendomat.mode`, and the CLI reads `machinesMeta.<name>.vendomat`. At the start of `machines install`,
   reject `adopt-existing` before SSH, payload preparation, kexec, facter, disko, install, or reboot.
   Reject every phase subset and disko mode, including `--phases install` alone.
5. The fresh-host direct-CLI rule is `MACH-021`: the patched CLI runs a target-side preflight
   program and accepts only a definite, target-bound, current pass. The contract is in
   `evidence/01-devenv-distribution.md` section 5. No environment variable counts as attestation.
6. Build the patched CLI as a release build. Check native `require_version` against its patched
   modules. Repeat the project-15 offline shell fixture with the source remote unavailable and an
   empty fetcher cache. Test the SSH install fix with real install payloads in a disposable VM.
7. Build on `server`, push the result to Attic, and prove cold substitution on another host or VM.
   Check upstream PR/release states before each bump. Drop only patches that a pinned release proves
   unnecessary.

**Gate:** direct patched `devenv machines install adopt-vm` refuses every tested phase before target
contact; fresh VM installation requires the proven preflight; CLI/module version checks work;
offline shell and payload fixtures pass; the same patched source identifies both CLI and modules.

**Stop if:** the CLI denial can be bypassed by a normal invocation of the supported patched command.
Arbitrary root commands and another downloaded binary are outside this command policy.

## Step 2 — Extend `vendomat sync` for devenv workspaces

**Goal:** keep the existing flake target and add the `.vendomat/` fragment without a second lock.

The input-resolution fixture for this step passed. Keep that behavior. Step 3A adds workspace
selections and values without replacing the native lock or the module's `devenv.yaml` inputs.

1. Extend the registry parser with `[imports]` and `[targets]`. Reject unknown top-level tables.
   Keep V5 store and flake-generation behavior for a registry that selects the flake target.
2. For a devenv target, generate `.vendomat/devenv.yaml`, `.vendomat/devenv.nix`, and
   `.vendomat/digest`. Keep `devenv.yaml` in the workspace limited to the local fragment import.
   Let devenv write `devenv.lock`.
3. Read an imported input's `devenv.yaml` recursively from its pinned source. Lift inputs to the
   top level and write only one-level `follows`. Define cycle handling and two-source name conflicts.
   Report registry precedence and whole-entry workspace/local overrides.
4. Make file replacement atomic. Check hashes for registry, imports, and generated fragment. Re-run
   the stale same-size/same-mtime evaluation case before choosing when to clear `.devenv` state.
5. Treat `devenv update` exit status as insufficient. Compare the resulting lock with requested
   inputs and surface fetch errors. Prove a failed update leaves the prior usable lock visible.
6. Implement `use_vendomat`: call the host launcher; sync only on a stale digest; then call
   `use devenv`. Test a new workspace with no lock, an unchanged workspace, a changed pin, and an
   unreachable collection. Record time against the V6 warm/full evaluation budgets.

**Gate:** a three-level imported-input fixture locks one node per source; every conflict and stale
case reports the cause; an unchanged workspace does no sync; Testee and end-to-end checks pass.

## Step 3 — Keep the Vendomat module; retire the description builder

**Goal:** retain the proved shell and machine checks while moving authored modules to native Nix.

The original three-target builder passed its recorded fixtures. Those fixtures remain evidence
about the prototype. They do not prove the revised workspace user flow.

1. Export `devenvModules.default` while retaining `packages.<system>.vendomat` and one `nixpkgs`
   flake input. Use the release-tested plain nixpkgs revision required by V6.
2. Prove a selected authored module in a focused fixture. Then remove the central description
   builder before the Step 3A gate. Import only selected workspace modules. Keep a library's
   Vendomat input optional.
3. Let an author provide a devenv module with its own `devenv.yaml`. Check its selected shell
   behavior and inherited inputs in a consumer. Do not require NixOS or Home Manager faces.
4. Keep native NixOS and Home Manager modules for machine roles that need them. Test each exported
   target in its own consumer or VM. Do not require one option path across targets.
5. Add pin checks as assertions for shell, test, and up. Run the same checks explicitly before
   Vendomat build/push commands. Do not assume `devenv build` evaluates shell assertions.
6. Add input paths, the derivation-valued JSON closure, host paths, and profile defaults. Prove the
   real `/etc/vendomat/paths.json` behavior after `nix-systems` exists.
7. Make the module the sole owner of `machines.<host>.nixos`. Put host imports and disk roles under
   `vendomat.inventory.<host>`. Add mode-sensitive assertions: fresh disko disks may name only
   `install-target`; adopted hosts have no disko disk layout and no install target. Require stable
   mount identities without rejecting legitimate mapped storage found in the Framework inventory.
   Do not let the general shell pin-check opt-out disable machine disk or mode assertions.

**Gate:** a selected authored module works; an unselected source leaves the shell unchanged; its
inputs reach the consumer lock; machine disk guards still fail on bad layouts. Preserve the old
builder fixture as historical evidence, not as this gate.

## Step 3A — Prove the no-Nix workspace user flow

**Goal:** let a workspace user create and update a workspace without editing Nix.

1. Use the bundled template generator to create a fresh devenv workspace. Give template-owned,
   user-owned, and Vendomat-owned files distinct ownership. Keep generated Nix in version control.
2. Put module selections and supported values in `vendomat.toml`. Reuse `[imports]` where it gives
   one clear selection source. Test the exact values table and types before adopting a name.
3. Extend `vendomat sync` to generate only the Nix wiring for selected modules and supported
   values. Reject unknown modules and unsupported values. Keep the root `devenv.nix` stable.
4. Select two composable authored modules whose `devenv.yaml` files declare inherited inputs.
   Enter the shell. Change one supported value and repeat. Record the registry diff, generated
   diff, lock nodes, shell result, and unchanged user-owned files.
5. Compare the shell derivation with and without an unselected source. Confirm that sync does not
   import its module. Run Testee and the consumer end-to-end gate.

**Gate:** a workspace user changes only `vendomat.toml` after template creation. Both selected
modules compose, their inputs lock, a supported value changes the result, and an unselected
source has no effect. The exact format remains proposed until this fixture passes.

## Step 4 — Complete the Vendomat command and launcher

**Goal:** run each workspace's pinned Vendomat while retaining a working host command elsewhere.

1. Install a small host launcher. Inside a workspace, resolve the locked Vendomat source by NAR
   hash and run its build. Outside one, use the host release. Do not put a second Vendomat command
   on the devenv shell PATH.
2. Prove bootstrap behavior for a new workspace with no `devenv.lock`, a missing build, a stale
   lock, an interrupted bump, and two workspaces on different Vendomat tags. Define when the host
   release is allowed to repair a workspace, and report that use.
3. Extend `path <name>` to devenv locks without network. Implement `check` for pin, CLI/module
   version, generated fragment, and host mode. Implement `push` using actual `devenv build` paths
   and `attic push <cache> --stdin`, after checks.
4. Implement `bump` only after one real workspace has converted. Make dry run the default. Define
   the fleet root and each repository's verify gate. Test a mixed fleet with one failing gate and
   confirm that the report preserves failures and does not claim a fleet pass.
5. Keep `machine install` scoped to fresh installations. It invokes the target-side preflight and
   the supported patched CLI. It refuses an adopted host, unreviewed phases, and `format` or `mount`
   modes. It does not wrap Machines deployment or rollback.
6. Update CLI help, error text, user docs, and Testee checks with each command. Do not add the
   deferred TOML commands without a new owner decision.

**Gate:** launcher/version/repair fixtures pass online and offline; `push` reaches real Attic;
`bump` dry run writes nothing; a bad pin prevents a push; fresh/adopt install policy is consistent
through both Vendomat and direct patched devenv.

## Step 5 — Finish source, cache, and builder infrastructure

**Goal:** recover inputs from the collection and substitute outputs across hosts.

1. Preserve the V5 collection contract: release tags only, immutable tag push, read-only `git://`
   on the tailnet, and `keep`/`mirror` semantics. Install the collection hook on intended repos.
   Test a tag push from Framework and a source fetch from both hosts.
2. Prove `STORE-010`: remove a disposable collection copy, repush its release tags, and compare
   refs and working-tree selection. Keep its raw log outside the repository.
3. Configure the Attic substituter and public key in the NixOS host core. Keep push credentials out
   of tracked files, store paths, and logs. Test real `vendomat push`, absent-path reporting, and
   NAR hash equality. Distinguish an upstream-sourced path from a Vendomat-cache hit.
4. Implement or verify the builder and `watch-store` path for each build host. Prove one tag builds
   only that input, a failed input does not stop others, and each result has command, status, and
   output paths. Prove both cross-host substitution directions with no local build.
5. Test a new host with a cold local store and the documented cache route. Keep PV-09 as a named
   blocker where a private pull credential is still required; a successful controller-to-target
   `nix copy` does not prove the independent cache route.

**Gate:** source recovery, one real Attic push, cold pull, and both host build directions have
separate saved evidence. The collection and Attic remain separate owners of source and outputs.

## Step 6 — Create `nix-systems` with a bootable core

**Goal:** compose machines in a new devenv repository while keeping the base system recoverable.

1. Create `nix-systems` as a separate repository with `vendomat.toml`, its generated fragment,
   `devenv.yaml`, `devenv.nix`, one pinned Vendomat module, and the pinned devenv command/modules.
2. Add one shared NixOS core, a `server` delta, a `framework` delta, Home Manager modules, and
   inventories. Keep the boot/recovery core usable without the Vendomat CLI. Install the launcher
   in a host layer. Avoid two definitions of `machines.<host>.nixos`.
3. Use plain pinned nixpkgs, disko, Home Manager, and sops-nix inputs. Record exact revisions and
   `follows`. Keep the server's fresh pin separate from any temporary Framework baseline pin.
4. Add root key-only deploy access and target SSH host-key pinning. Test owner-run root SSH to the
   server's disposable VM and self-deploy over `root@localhost` with devenv running as the owner.
5. Set a health check and rollback timeout per host. Keep `systemctl --failed` empty before deploy.
   Prove the shared core boots, mounts, and accepts SSH in a VM without Vendomat services.
6. Import authored NixOS and Home Manager modules through the inventory where a host needs them.
   Test enabled units and the system rollback of declarative Home Manager configuration. An
   unselected module must leave the host derivation unchanged.

**Gate:** both machine roles build in isolated VMs; the core boots without Vendomat; an enabled
library unit runs; Machines plan/apply/status/rollback work on a disposable NixOS VM.

## Step 7 — Prove the fresh server disk route in VMs

**Goal:** prove each safety barrier before touching the 4 TB drive.

1. Declare the 4 TB disk by `by-id` as `install-target` and the 512 GB disk as `keep`. Require
   model, serial, and size in the inventory. Use a host-unique disko disk name, preset partition
   GUIDs and filesystem UUIDs, and mount by stable UUID. Give the new disk its own EFI partition.
2. Make the runtime preflight reject a missing path, wrong model/serial/size, any signature, a disk
   backing any mounted filesystem or active swap, a mapped holder, the old root/boot disk, or an
   unexpected `/mnt` mount. Resolve the by-id path to a block identity and fail on unknown data.
3. Run the disko layout test and the complete two-disk QEMU install with persistent OVMF variables.
   Use the actual patched CLI, an install payload, and the controlled `disko,install` phases.
4. Inject each preflight mismatch. Confirm no partition, format, or installer write starts. Attempt
   direct patched `devenv machines install` without valid fresh authorization and confirm refusal.
5. Compare old disk GPT, partition GUIDs, ESP files, and firmware entries before/after. Boot the
   new disk alone. Test one-time boot and fallback. Record what firmware behavior remains unproven.

**Gate:** every bad target fails before a write; new disk boots alone; old disk and default boot
order match the baseline; payload secret works after boot; no plaintext enters a store path.

## Step 8 — Remove legacy dependencies before the server cutover

**Goal:** make the new host independent of Vendomat V4 and the old `nix-meta` composition.

1. Use `.scratch/CURRENT.md`'s V4 removal backlog as the inventory. First move `repoman` managers
   to host PATH tools. Give each tool its own flake and package. Remove V4 module imports from the
   central overlays, then convert `linkman` and the remaining V4 registry files.
2. Move the Dagu workflow registry to a tagged `devman` renderer input before switching the host.
   Prove the rendered store path and service start. Preserve the live generation until cutover.
3. Verify each converted library output without Vendomat installed, then verify its authored
   module in a selected consumer. Compare any changed behavior with the prior output.
4. Build the final `server` NixOS role with no V4 module path or stale toolchain manifest. Keep
   the old 512 GB system and its EFI partition available as the recovery reference.

**Gate:** Testee and relevant consumer gates pass; no new system unit depends on V4; the source,
Attic, SSH, and Dagu services run in the new-system VM. Do not delete the old host configuration.

## Step 9 — Install and evaluate the new `server` system

**Goal:** boot the 4 TB system once while retaining the 512 GB fallback.

1. On the real running server, collect a fresh privileged, read-only disk and mount inventory.
   Use `/run/wrappers/bin/sudo`, stable device links, `wipefs --no-act`, and `blkid -p`. Resolve
   PV-02. Compare exact model, serial, size, root/boot ancestry, swap, signatures, and `/mnt`.
2. Record and review the committed facter report, target host key, root deploy key, patched CLI
   revision, locked `nix-systems` inputs, built closure, and current old-disk/EFI/NVRAM baseline.
   Check all services and the cache/source routes. Stop on any unexplained mismatch.
3. Only after those gates and a separate operator review, run `vendomat machine install server`.
   It performs the fresh preflight again, then invokes the pinned Machines
   `disko,install` route. Do not select `format` or `mount` mode. Unmount `/mnt` safely afterwards.
4. Create a one-time firmware entry for the new ESP and set BootNext. Keep the old disk first in
   BootOrder. Boot once and verify actual root and boot UUIDs, key-only access, secrets, services,
   collection, Attic, Dagu, paths, and a Machines plan/status command.
5. Exercise the old-disk firmware fallback. Promote the new entry to default only after repeated
   good boots and a recorded recovery procedure. Review any later `bootctl install` against the
   mounted new ESP and the old ESP snapshot.

**Gate:** both disks boot independently, the old disk/ESP remains intact, the new system survives
reboot and provides its required services, and the owner has verified fallback. A VM result cannot
close this real firmware gate.

## Step 10 — Inventory Framework and prepare an adoption workspace

**Goal:** match the working laptop before changing its NixOS ownership.

1. Collect read-only, current Framework facts: by-id disk, GPT/PARTUUID, filesystem UUID and type,
   root/boot/ESP mounts, mapped storage, encryption and unlock path, swap, bootloader and Secure
   Boot, hardware modules, network, UID/GID, `system.stateVersion`, `home.stateVersion`, services,
   data directories, system/HM profile links, and exact effective source pins. Record public key
   identities only. Do not infer current state from the older `nix-meta` report.
2. Make and restore-test a backup of home and service data. Preserve the old NixOS and standalone
   Home Manager generations, boot files, and an offline rescue route. A system rollback cannot
   restore mutable data or a failed bootloader.
3. If the Framework's nixpkgs pin differs from the server's pin, create a temporary, separately
   locked Framework adoption workspace. It still imports the Vendomat module. Keep exact current
   nixpkgs, overlays, Home Manager, service, and state-version inputs during the first cutover.
4. Model its disk as `existing-system` with no `disko.devices.disk`. Keep the disko input only where
   Machines evaluation requires it. Keep current filesystem, unlock, user, boot, and service
   declarations. Evaluate old and proposed NixOS outputs and explain every delta.
5. Bootstrap root key-only SSH through the Framework's existing management route. Pin its SSH host
   key. Retain or securely provision the sops age identity without `install.secrets`. Prove public
   recipient match and decryption without writing a private key to the Nix store.
6. Leave standalone Home Manager in control for the first NixOS cutover. Plan its move into the
   NixOS role as a later generation, after system deployment and reboot work.

**Gate:** inventory and declarations match, backup restore works, old generations and rescue media
are usable, root SSH and secrets work, and the proposed first generation contains no unapproved
pin or service migration. No Framework disk operation has run.

## Step 11 — Prove adoption and recovery in a populated VM

**Goal:** test the same transition before deploying it to the laptop.

1. Start with a bootable NixOS VM on a populated persistent disk, an ESP, old generations,
   standalone Home Manager, unmanaged home files, service data, and matching baseline pins.
   Take an offline copy or snapshot. Keep OVMF variables persistent.
2. Build the proposed adopted NixOS role with no disko disk layout. Save `machines check`, the
   reviewed named plan, apply result, first reboot, status, and rollback. Capture GPT, GUID/UUID,
   mounts, selected data hashes, numeric owners, system/HM profiles, and ESP changes before/after.
3. Run the denial matrix: every raw patched `machines install` phase and disko mode must fail before
   network or target writes. Test wrong disk role, wrong UUID, missing root key, missing age key,
   failed health check, existing failed unit, and loss of SSH confirmation.
4. Cause a broken new boot. Select the old generation from the firmware menu. Then test offline
   rescue from external media if the old menu entry is absent. Do not count watchdog rollback as
   proof of recovery from a failed initrd or bootloader.
5. In a separate generation, move standalone Home Manager into NixOS. Reuse its exact revision and
   state version. Test occupied unmanaged files, enabled user units, reboot, and rollback. Retain
   the old standalone profile and a way to reactivate it until the new role is accepted.

**Gate:** all adoption VM cases in `fixtures/VM-TEST-PLAN.md` have raw logs and before/after data.
Existing partitions and selected data persist; old generation and offline rescue boot; HM changes
and rollback behave as recorded. The synthetic 11/11 policy fixture is not this gate.

## Step 12 — Adopt Framework without a disk install

**Goal:** put the existing laptop under `nix-systems` while keeping its data and recovery path.

1. Refresh the live read-only inventory and backup. Compare it with the approved VM baseline and
   proposed config. Check root SSH, age identity, failed units, disk roles, and old boot generation.
2. Build `machines.framework.build.nixos`. Run `devenv machines check framework` and a named
   `devenv machines plan framework`. Review the saved plan **and** a separate old/new NixOS option,
   systemd unit, initrd, filesystem, Home Manager, and bootloader diff. The native plan alone does
   not report every service or EFI file change.
3. After a separate review of the exact target and plan, apply the named plan. Do not call any
   `machines install` phase or disko command. Watch health, SSH, mounts, secrets, services, and
   current generation. Reboot only after the running system passes.
4. Compare UUIDs, PARTUUIDs, mounts, selected data hashes and owners, ESP files, users, and profile
   links after reboot. Retain the old generation and standalone HM profile. Test a later disposable
   generation's rollback without disturbing user data.
5. In a second reviewed generation, migrate Home Manager into NixOS as proved in Step 11. Move
   nixpkgs, services, or data formats only in later, independent changes with their own backups.

**Gate:** Framework boots and remains reachable from its existing disk; its partition table and
filesystems match baseline; selected data is intact; a working old boot and restore route remains.
An absence of disk formatting does not prove these outcomes.

## Step 13 — Convert workspaces and prove the fleet

**Goal:** make every intended workspace a pinned V6 devenv consumer with no routine Nix edits.

1. Convert one ordinary workspace first through the Step 3A template and registry flow. Add the
   generated fragment, selected authored modules, pinned devenv CLI/modules, and locked Vendomat
   tag. Keep its own flake only if it
   publishes flake outputs. Remove old Vendomat/V4 imports and unused toolchain declarations.
2. Run its Testee gate, full evaluation, shell/test/up, authored module checks, `vendomat check`,
   input path, real cache push/pull, and offline shell entry with locked sources in the store.
   Confirm an unselected source changes no derivation and the user edits no Nix.
3. Convert remaining repositories in dependency order. Give each library a native package and
   authored modules for the targets it needs. Keep its own lock authoritative. Preserve source
   collection tags, shared cores and variants, named paths, and required output isolation.
4. Use `vendomat bump` dry run over the fleet. Review each proposed tag, fork revision, nixpkgs
   default and consumer gate. Apply in batches; run each repository's gate and report failures.
   A failed workspace must remain named as incomplete.
5. Verify from both hosts: tagged source fetch, shell entry, input store paths, cache substitution,
   builder output, variant isolation, and the new `nix-systems` machine plan. Retire the V4
   `nix-meta` pin and stale overlays only after their replacements have passed.

**Gate:** every intended workspace pins one tested Vendomat release and supported patched devenv;
the fleet scan reports no divergent pin; every consumer gate and cross-host proof has a saved run.
At least one real consumer proves routine creation and updates with no Nix edits.

## Step 14 — Accept V6 and close the transition

1. Re-run the full Testee gate and opt-in end-to-end check. Re-run machine, cache, restore, and
   real-consumer gates only where an intervening change invalidated their earlier evidence.
2. Keep the workspace user values separate from deferred machine `SYS-*` and TOML commands. Decide
   the machine operator interface after the workspace flow passes and `nix-systems` runs. Decide
   `SEC-002` from a workspace SOPS fixture. Do not add a second configuration authority.
3. Reconcile the V5/V6 ID ledger. Search and repair duplicate claims, stale V4 instructions,
   obsolete command examples, and mismatched concept/spec/guide statements. Update
   `.scratch/CURRENT.md` to make V6 authoritative only after owner review.
4. Tag and publish the Vendomat release and patched devenv distribution. Record upstream source,
   patch ledger, tested nixpkgs default, closure hashes, Testee report, VM and host evidence,
   rollback instructions, and open infrastructure blockers. Commit and push the completed work.

**Gate:** the owner can rebuild either host, enter and update a workspace, recover source and
outputs, and restore a failed machine change using the recorded steps and pinned inputs. State any
remaining blocker by name. Do not call V6 complete while one of its required real-machine or
real-consumer proofs remains open.

# Vendomat and Basix: Two Independent Project Concepts

**Architecture concept and implementation direction**  
**Date:** 2026-10-12  
**Status:** Proposed refinement of the accepted Project 20 design; not an implementation claim

## Executive summary

This document specifies **two distinct products**:

1. **Vendomat** is a general-purpose, declarative management layer for development environments and NixOS machines. It provides a small, stable user interface over pinned devenv, Nix, and NixOS functionality. It is independently useful, with no required application ecosystem.
2. **Basix** is a usable, opinionated Linux environment and an educational system. It uses Vendomat as its management substrate while independently owning the OS experience, default profiles, capability collections, installer ISO, applications, and learning material.

The projects have **separate repositories, separate release lifecycles, and a one-way dependency**: Basix depends on a compatible Vendomat release; Vendomat does not depend on Basix. Each project has a self-contained concept below. A final integration contract explains their deliberately narrow point of contact.

The design preserves the accepted Project 20 principles of one routinely edited `vendomat.yaml`, direct evaluation without generated configuration files, a pinned devenv fork, native Nix semantics for advanced use, and minimal release-one scope. It **revises** the accepted shortcut that bundled the machine catalog into Vendomat. The separate-import extension and independent release behavior require new fixtures; they have not yet been proven.

---

# Concept I — Vendomat

## I.1 Mission and product definition

Vendomat is a **general-purpose declarative computer management tool**. A user describes what a workspace or machine should provide in a small data file, and Vendomat arranges the underlying pinned tools to build, run, install, or apply that configuration.

Its primary value is a consistent, comprehensible **front door** to native capabilities—not a new package manager, new build engine, or new operating-system configuration language.

### Product promise

- One routinely edited configuration file: `vendomat.yaml`.
- A small CLI, stable across workspaces and machines.
- Reproducible environments, with input revisions in the native `devenv.lock`.
- Composable declarative capabilities and native Nix semantics underneath.
- Practical local NixOS lifecycle operations, with explicit safeguards.
- Optional shared-store caching for multi-machine use.
- An explicit advanced path to native devenv and Nix when the bounded data catalog is insufficient.

**Non-negotiable independence:** the release and runtime must operate with no third-party profile, capability package, user interface, or educational content installed.

## I.2 Mental model

A workspace has a desired state, a fixed set of system mechanisms, and a revision lock. Vendomat connects the three.

```text
vendomat.yaml             user intent / bounded data catalog
       |
       v
Vendomat catalog module   parse once, decode and validate typed options
       |
       v
pinned devenv / Nix       resolve, evaluate, build, run
       |
       v
workspace or NixOS host   shell, service, build, install, activation
```

Vendomat should expose **intent** rather than duplicate every lower-level option. It should make routine tasks simple without concealing the existence of the native system from an advanced operator.

A workspace and a machine share the same configuration model; a machine adds system and lifecycle data as required by the relevant native modules.

## I.3 Architecture and ownership

### 1. Small host CLI

The host CLI is responsible for finding the workspace, invoking its matching pinned devenv build, preserving exit status and terminal behavior, and implementing only the intentionally named commands.

The accepted initial command shape is:

| Command | Contract |
| --- | --- |
| `vendomat` | Enter the pinned devenv shell. |
| `vendomat new` | Create a minimal workspace. |
| `vendomat apply` | Apply a supported local machine configuration using native activation. |
| `vendomat install` | Initiate a supported local machine installation from a suitable installer environment. |
| `vendomat update` | Pass through to native `devenv update`; update the lock according to native input rules. |
| `vendomat test`, `vendomat build`, etc. | Pass through to the matching pinned devenv command. |

Only `new`, `apply`, and `install` are separately implemented Vendomat verbs in the current concept. Avoid a parallel CLI for operations that devenv already provides. A named operation must retain documented exit codes, signals, and terminal behavior wherever it delegates to a native command.

`vendomat apply` is a **generic machine operation**, not a hardcoded profile switch. It should report the native activation status and failed units; do not add an unproven global failed-unit refusal gate. Rollback uses native generations and boot selection.

`vendomat install` is a **generic, guarded local install mechanism**. The install media and machine configuration supply the concrete system image and installer plan. Vendomat owns only the common invocation and safety invariants described below.

### 2. Bounded catalog module

The default user-facing catalog covers a deliberately small set:

- `programs`: supported nixpkgs package names.
- `languages`: common language toolchains and versions.
- `services`: commonly used development services.
- `env`: non-secret environment values.
- Generic machine facts and lifecycle settings needed by supported system operations.

Example:

```yaml
programs:
  - ripgrep
  - fd
languages:
  python:
    version: "3.13"
services:
  postgres:
    enable: true
env:
  PROJECT_MODE: local
```

The catalog is not intended to mirror all of nixpkgs, NixOS, Home Manager, or devenv. Unsupported settings belong in imported native modules or the advanced Nix door.

### 3. Parsing, type interpretation, and validation

Continue the accepted direct-reader mechanism:

1. Read `vendomat.yaml` with `builtins.readFile`.
2. Parse it through the pinned devenv fork's `vendomatFromYAML` primop.
3. Decode the resulting **string scalar** data into typed catalog options.
4. Validate **all provided fields**, including fields not referenced by the chosen operation.
5. Map validated values into native devenv or NixOS options and then evaluate/execute.

The parser is deliberately restricted to block maps, block lists, and string scalars. It rejects aliases, anchors, tags, flow collections, block scalars, multiple documents, duplicate keys, and other unsupported syntax. It must report syntax failures with file, line, and column. All scalars initially remain strings: `"3.10"` stays a version string; `no` must not silently become false; typed boolean fields must accept only the documented values.

The **Nix-side catalog remains the single authority for typed configuration**, rather than maintaining a separate Python validator, exported schema cache, or generated JSON copy. Unknown fields must fail. Error aggregation should identify every invalid field in one evaluation where feasible.

**Extension requirement (new proposal):** imported modules must be able to declare additional typed catalog namespaces without changing the parser or Vendomat core. A plausible interface is for the Vendomat entry module to expose its already-parsed data to a composition of typed Nix option declarations. Imported modules then own their namespaces and mappings. Unknown-key detection must happen **after** all imported catalog declarations are known, not from a hardcoded core-only key list. Exactly how this is represented in `options` and forced for eager validation is a required fixture, **not yet a proven interface**.

Do not build a dynamic plugin marketplace or second runtime registry. Ordinary explicit Nix module imports are enough.

### 4. Native execution layer

Devenv, Nix, and NixOS continue to perform actual dependency resolution, evaluations, builds, environments, service configuration, and activation. Vendomat should not reproduce their dependency graph or option-merging algorithms.

- Native `follows` resolves shared inputs.
- Native `devenv.lock` is the only dependency lock.
- Native module priority and merge rules govern advanced definitions.
- Prefer established devenv Machines behavior over a parallel remote-deployment engine.
- Use the pinned devenv **fork build and matching module input**, not whichever executable happens to be first on the host `PATH`.

The fork's custom YAML primop is a deliberate dependency. Track it as a patch, with release-build and compatibility testing; do not silently assume stock devenv supports it.

## I.4 Workspace contract

The baseline workspace contains four files:

```text
workspace/
  vendomat.yaml     # user-owned routine intent
  devenv.yaml       # template-owned native inputs and imports
  devenv.nix        # native advanced settings; initially { }
  devenv.lock       # native revision lock, written by devenv
```

A baseline `devenv.yaml` pins one Vendomat source on its release channel, keeps `nixpkgs` following that source's `nixpkgs`, and imports the fixed Vendomat catalog module. These are **conceptual relationships**, not a complete copy-paste `devenv.yaml` syntax example.

Rules:

- `vendomat.yaml` is the only file needed for routine usage.
- `devenv.yaml` and `devenv.nix` are intentionally editable for advanced use; Vendomat does not silently overwrite such edits.
- A missing `vendomat.yaml` means an empty routine catalog.
- No `.vendomat/` generated tree, canonical JSON mirror, custom schema-export process, or auto-repair layer.
- The lock file records immutable revisions; a branch name is merely the input update target, not the exact current revision.
- Version control can restore data and lock together. A machine rollback also has a native NixOS generation route.

One key distinction: the lock is **not** frozen unless the user elects to preserve it. Explicit native update commands can move branch-backed inputs.

## I.5 Generic machine management

Machine operations should be useful beyond development workspaces, but must stay thin.

### Installation responsibilities

Vendomat may provide reusable installer mechanics:

- Work only in a suitable local installer environment.
- Identify disks using stable `/dev/disk/by-id/` names.
- Exclude the boot medium and protected devices.
- Refuse occupied disks, existing partitions, or filesystem signatures on the supported **blank-disk** path.
- Require the user to type the full stable target identifier.
- Evaluate and show the selected target and operations before destructive execution.
- Call the native installation process with an explicitly supplied machine configuration.

Which system defaults, packages, users, filesystem policy, or applications the installer installs is **not a Vendomat default**. A native module or the installer image supplies those specifics.

The first implementation should support one narrow, tested UEFI/single-disk scenario. Other layouts, adoption of existing systems, and remote install/deploy go through native mechanisms until separately validated. Real disks require separate explicit authorization; passing a VM test is not permission to write a physical device.

### Applying and rolling back

`vendomat apply` translates the selected machine configuration into the supported native NixOS activation route. It reports build/switch results, failed services, and the active generation. It should never claim transactional rollback of all filesystem or application state: NixOS generation rollback does not automatically undo user data or database schema changes.

Use native boot-generation selection for recovery after a bad activation. Keep disk layout changes outside normal `apply`.

### Secret-free bootstrap

A new core system should be able to boot without supplied private keys, an external secret manager, or a cache service. Host-generated identity keys and optional later configuration are appropriate. Secrets must not be embedded in `vendomat.yaml`, the Nix store, generated installation artifacts, or logs. A general secret-delivery framework remains out of the first scope.

## I.6 Optional shared-store infrastructure

Offer a generic, small configuration for **one optional signed binary-cache host**.

- A serving machine generates its own signing key outside the Nix store and tracked files on first use; ensure the same key persists across reboot.
- Harmonia serves valid local store paths over an explicitly restricted reachable network.
- A client names the serving host and provides the host's public signing-key line.
- Derive the substituter URL and trusted public key, with `fallback = true` and a short connection timeout.
- A missing path, unavailable host, or unusable signature must not silently override local build/fallback behavior.
- Selected outputs can be kept alive with native Nix GC roots. Do not recreate a separate artifact database for initial use.
- This is **store sharing**, not a general write-through remote cache or a source-code distribution system.

Retain the existing Attic path in any live environment until a real two-machine Harmonia verification succeeds. Signing-key renewal/backup, multiple cache hosts, collection mirroring, and remote key delivery are later concerns.

**Important test nuance:** test signed cold substitution, wrong-key rejection, a 404/missing path, a down host, fallback, reboot key persistence, and root survival. A single-machine VM pass does not prove a two-machine deployment.

## I.7 Distribution, versions, and compatibility

Vendomat releases include the CLI, its fixed catalog module, its pinned devenv fork, and the compatible Nix source references. Versioning should follow a clear public release identity with tests for each supported platform.

- A host release is the launcher/default release.
- A workspace uses the revisions fixed in its own `devenv.lock` for native evaluation.
- The host CLI must not accidentally run a mismatched system devenv.
- A release-branch update should be intentional, while native locks identify exact revisions.
- Restore the previous tracked lock to restore the previous native input revisions, subject to their availability.

Avoid a second Vendomat lock, per-workspace Vendomat application build, homegrown source mirror, or always-running background service in release one.

## I.8 Repository organization

Proposed conceptual layout:

```text
vendomat/
  cli/                  # small host entry point
  nix/
    catalog/            # typed generic options and mappings
    machines/           # generic install/apply integration
    infrastructure/     # optional shared-store support
  fork-patches/         # devenv/YAML integration patches
  templates/            # minimal workspace template
  tests/
    parser/
    workspace/
    native-merge/
    machine-vm/
    cache-vm/
  docs/
    concepts/
    reference/
    advanced-native/
```

Folders are suggestions, not requirements. Keep modules independently testable and avoid organizing around speculative future extensibility.

## I.9 First-release scope and exclusions

**Release-one target:** a fresh minimal workspace, routine catalog, consistent pinned shell and native passthrough, generic guarded local machine install/apply, and an optional one-host signed store cache after its gate passes.

**Explicit exclusions:** custom source collection and `keep` clones, multiple caches, a second lock, generalized provider registry, automatic machine adoption, custom disk layout editor, fully managed secrets, automated cache key rotation, dynamic capability marketplace, and an additional UI service.

The CLI must remain usable even when the machine-install and cache features are not configured.

## I.10 Acceptance criteria

A release is not done until evidence shows:

1. Fresh workspace: create, enter shell, change `vendomat.yaml`, enter again, clone and enter again—without generating files.
2. YAML: accepted/rejected corpus, `3.10` and `no` preserved, duplicate keys, syntax locations, bad/unused typed field reporting.
3. Native entry points: shell, build, test, tasks, direnv, and CI/Testee read the same configuration with the pinned fork; unsafe Nix evaluation setting remains off.
4. Catalog extensibility: two separately imported typed catalog namespaces coexist; unknown or conflicting fields fail with useful locations; neither namespace needs to patch the reader.
5. Lock and rollback: branch update changes the lock; restoring the earlier data and lock restores the earlier evaluated configuration; no second resolver/lock.
6. Local machine VM: blank-disk install and boot; refuse used disk, nonselected disk and boot medium; apply and boot prior generation; no real disk writes.
7. Cache VMs: signed cold substitution, wrong-key rejection, absence/down fallback, persistent signing key, GC root retention.
8. Independent use: an unextended workspace and new host require no third-party capability module.

The **new extensibility check** is an explicit addition to the accepted Project 20 gate set. It must pass before external catalog modules can be treated as a supported interface.

---

# Concept II — Basix

## II.1 Mission and product definition

Basix is both:

1. **A usable, minimal, opinionated Linux environment** suitable for everyday computing and personal projects.
2. **An educational computing system** that progressively introduces fundamental capabilities by making them usable, observable, and composable.

Basix is **not** a rebranded Vendomat CLI and **not** merely a NixOS installer. Its primary deliverable is a coherent way to use and learn a computer: start with a working system, add understandable capabilities, compose them into applications, and eventually orchestrate them with more flexible human-computer interaction.

The system should hide Nix and devenv during normal use without hiding the important computing concepts being taught. Its advanced path reveals native details when the user is ready.

### Core principle

**Teach what the computer does, not the incidental syntax of its implementation.**

For example, learners first understand files, streams, services, state, networks, or databases in terms of behavior and small tools. Only later need they see the corresponding Nix modules, service units, package derivations, or lock files.

## II.2 Independent project identity

Basix has its own:

- Source repository and releases.
- Nix modules, catalog namespace, profiles, and capability definitions.
- Installer ISO and minimal bootable core.
- User-facing defaults, workflows, examples, and documentation.
- Integration tests against **declared compatible Vendomat releases**.
- Optional higher-level interfaces and applications.

It depends on Vendomat's stable management interfaces and on its pinned native execution stack. It must not modify or vendor Vendomat's implementation merely to add a capability.

A change to the Basix tutorial sequence, storage profile, or database module should not require releasing a new Vendomat binary. Conversely, a generic environment-management improvement should not require changes to Basix except when a documented compatibility boundary changes.

## II.3 Product layers

```text
Basix experience
  - guided onboarding and learning progression
  - composed personal applications and workflows
  - optional assisted interaction / suggestion layer
             |
Basix capability library
  - storage, text, processes, networking, databases, automation ...
  - typed catalog namespace and named profiles
             |
Basix distribution
  - bootable ISO, minimal NixOS core, hardware and UI defaults
             |
Vendomat management contract
  - one YAML intent file, typed composition, workspace/machine operations
             |
Pinned devenv + NixOS + Nix
```

All Basix-specific options, defaults, disk-layout choices, service arrangements, lesson states, and application recipes belong in Basix. Vendomat remains unaware of their meaning.

## II.4 The user experience

### A working system on day one

A learner starts with a prebuilt Basix ISO, boots a target machine, confirms a supported empty disk, and installs a minimal keyless core. After first boot, there is a usable login, basic tooling, clear local documentation, and a straightforward way to add capabilities.

The Basix ISO **includes** compatible Vendomat bits; it does not imply those bits contain Basix-specific implementation. Basix provides the machine profile and NixOS configuration, while Vendomat exposes the supported generic installation call.

The first-run experience should answer four questions without requiring Nix knowledge:

- What capabilities does this system already have?
- What can I add?
- What will change if I add it?
- How can I revert the system configuration if something breaks?

### Small, predictable configuration surface

A Basix workspace still uses `vendomat.yaml`. Conceptual example:

```yaml
programs:
  - ripgrep

basix:
  profile: desktop
  capabilities:
    - storage
    - networking
    - databases
```

This is **proposed syntax**, contingent on the external-namespace fixture. It is not supported by the accepted generic catalog as currently written. The file still uses strict YAML: only maps, lists, and string scalars; no YAML tags, implicit booleans, anchors, or inline object syntax.

The `basix` subtree is owned and validated by Basix. The generic `programs` field remains owned by Vendomat. This prevents duplicated names and unclear configuration authority.

### Complexity should be progressive, not irreversible

Normal Basix operation should not require editing `devenv.yaml`, `devenv.nix`, NixOS modules, or a flake. Advanced users may open those native files and understand exactly how their configuration reaches NixOS. A lesson may deliberately reveal those layers, but it is not a prerequisite for using the system.

Avoid presenting two competing ways to perform every task. Start with one supported path, explain its effect, and leave the native path available rather than reproducing the entire native CLI in Basix.

## II.5 Capabilities are the primary educational unit

A **capability** is an independently understandable unit of computer function, optionally backed by packages, system units, small commands, configuration, examples, and lessons.

Each capability definition should include:

| Field | Purpose |
| --- | --- |
| `id` | Stable capability identifier, e.g., `databases`. |
| `purpose` | What problem this enables the user to solve. |
| `requires` | Minimal prerequisite capabilities. |
| `config` | Typed Basix options and documented defaults. |
| `provides` | Commands, services, files, or interfaces that become available. |
| `checks` | Small executable checks confirming the capability works. |
| `examples` | Reusable small tasks and exercises. |
| `lesson` | Explanation, progression, and optional deeper investigation. |

This is a **content/convention contract**, not a requirement to implement a new machine-readable registry immediately. Start with an ordinary documented module and its tests. Add structured metadata only when multiple real capabilities require it.

### Initial capability progression

1. **Storage and files:** paths, directories, files, permissions, text, backup, and persistence.
2. **Processes and streams:** commands, input/output, pipelines, exit status, and environment variables.
3. **Parsing and generation:** simple structured formats, transforms, templates, and validation.
4. **Networking:** addresses, names, clients, servers, connectivity, and sharing.
5. **Services and state:** long-running processes, service units, logs, and recovery.
6. **Databases:** tables, queries, durable state, SQLite first; PostgreSQL as a later service example.
7. **Automation and composition:** scripts, scheduled jobs, small cooperating tools, and idempotent operations.
8. **Personal information workflows:** capture, organize, search, transform, and publish personal data.
9. **Assisted interaction:** contextual suggestions, speech input, refinement, and controlled actions.

This order is a proposed curriculum, not an implementation dependency graph. Lessons should be small and reorderable when possible.

## II.6 Profiles compose capabilities

Profiles answer **what kind of system am I building?** Capabilities answer **what can it do?**

Initial illustrative profiles:

- `core`: bootable local base, console access, file/network fundamentals, recovery information.
- `desktop`: a usable interactive Linux session, editor/terminal/file tools, basic application workflow.
- `developer`: development commands, pinned workspace integration, testing and version-control tools.
- `server`: headless operating defaults and the services needed for specific applications.
- `learning`: examples, exercises, inspection commands, and guided documentation layered over a working profile.

Profiles should be composed from normal Nix modules and simple declared choices. They are **Basix-owned opinionated defaults**, not separate operating systems or duplicate Vendomat implementations.

Avoid making every profile pair combinable on day one. Explicitly support and test a small set of combinations. Reject unsupported or conflicting combinations with clear errors.

## II.7 A single evolving reference project

A particularly useful pedagogical spine is a **personal information system** that becomes more capable as new concepts are introduced.

| Stage | What the user builds | Computing concepts illustrated |
| --- | --- | --- |
| 1 | Save a note in a directory. | Files, paths, text. |
| 2 | Search, tag, and transform notes. | Parsing, streams, commands. |
| 3 | Record tasks and structured records. | Schemas, SQLite, durable state. |
| 4 | Expose a local index or page. | Networking, servers, routing. |
| 5 | Automate capture and processing. | Services, events, tests, repeatability. |
| 6 | Connect related tools. | Small interfaces, composition, interoperability. |
| 7 | Offer context-aware suggestions. | Retrieval, evaluation, approval, assisted interaction. |

This project should remain a **reference application**, not a mandatory system service. It is valuable because each new concept produces an observable improvement in the same artifact. Learners should be able to replace any component, inspect its inputs/outputs, and explain the boundaries.

The project can naturally use an editor, command-line interface, local database, and eventually an optional local web interface, but those are implementation choices of the example—not hard prerequisites for every Basix machine.

## II.8 Installer ISO and minimal core

### Ownership

Basix owns the installer ISO, its boot experience, its tested hardware matrix, and the NixOS configurations installed onto target machines. Vendomat supplies common, generic install/apply mechanisms; NixOS performs system build/activation.

### Release-one install path

1. Download or build a versioned Basix ISO containing a compatible pinned Vendomat release.
2. Boot locally on a supported UEFI machine.
3. Show a clear install target and confirm the disk is blank and not the boot medium.
4. Require exact stable disk identifier confirmation.
5. Install the Basix core with a documented initial local login route.
6. Boot without externally supplied private keys, a secret provider, or a required binary cache.
7. Edit the one routine configuration file and use generic `vendomat apply` to activate the new Basix choices.
8. Recover using a previous boot generation where applicable.

The first profile should use a deliberately narrow known-good disk scheme. The exact partition layout, boot loader, filesystem, and initial console password procedure are **Basix design decisions not yet settled by the supplied sources**. They require a VM proof and explicit documentation before real-disk use.

Do not treat remote installation, in-place adoption, encrypted multi-disk installation, or automated post-install secret delivery as first-release capabilities. A knowledgeable user may use native devenv Machines outside the routine flow.

### Separate admin concerns

The core should have a minimal, recoverable administrative path. An unprivileged everyday user and a distinct administrator role may be appropriate, but their exact accounts and SSH policies are Basix configuration policy rather than Vendomat assumptions. A keyless first boot must not imply an open network service or weak default remote access.

## II.9 Basix modules and native dependency wiring

### Separate inputs, one lock

A Basix workspace imports:

- A pinned compatible Vendomat release for the core catalog and execution stack.
- A separately pinned Basix release for its own catalog namespace, profiles, and NixOS modules.
- A shared nixpkgs ancestry through native `follows` where supported and tested.

Those revisions are represented in the **same native `devenv.lock`**. They are not Vendomat-managed copies of the Basix source, not a second lockfile, and not runtime downloads from an ad hoc module registry.

Conceptual template:

```text
basix-workspace/
  vendomat.yaml       # routine data; generic and basix fields
  devenv.yaml         # template pins/imports two independent sources
  devenv.nix          # native advanced escape; initially { }
  devenv.lock         # native exact versions of both sources
```

Basix supplies this template and its Nix import wiring. The generic `vendomat new` template does not need to contain any of this. A Basix-provided initialization command or a preinstalled workspace on its ISO can create the template; do **not** add another required named Vendomat verb solely for Basix.

### Mapping data into options

On evaluation:

1. Vendomat's pinned reader parses `vendomat.yaml` once.
2. Generic options are checked by the Vendomat catalog declarations.
3. Basix-imported Nix modules declare additional typed options under `basix`.
4. A composed validation step rejects unknown or invalid fields after considering both module sets.
5. Basix modules map valid options to normal NixOS/devenv definitions.
6. Standard Nix priority and merge rules govern native advanced overrides.

The accepted Project 20 design proved a **fixed** catalog in fixtures; this **composable** catalog interface is an architectural extension that needs new tests. Until that interface passes, Basix can remain separate through native imports but should not claim its additional YAML fields are supported.

### Avoid hidden source-specific behavior

Do not add a branch in Vendomat such as “when profile X is installed, parse special keys.” Basix content lives entirely in Basix's imported modules, templates, installer image, and documentation.

## II.10 Versions, updates, and rollback

Basix uses its own semantically meaningful release identifiers or tagged release history. Each published Basix release must declare which Vendomat interfaces and releases it was tested against. A tested Basix distribution should pin an exact working combination.

Independence has several consequences:

- Basix may release documentation, module changes, or profiles without changing Vendomat.
- Vendomat may release a generic patch without forcing an immediate Basix release.
- Updating the Basix input is distinct from updating the Vendomat input.
- The distribution can choose to keep both pinned to a tested pair until a user explicitly upgrades.
- Rollback means restoring the tracked `vendomat.yaml` and `devenv.lock` together, or selecting an earlier native system generation after a machine apply.

The accepted `vendomat update` delegates to native `devenv update`. A selective-input update (such as native `devenv update <input>`) must be fixture-tested on the pinned fork. **Do not assume an unqualified `vendomat update` updates only one product.** The Basix docs should define a tested update recipe, and distinguish updating inputs from rolling back operating-system activation.

For release one, simple compatibility notes and integration tests are preferable to an automatic version solver or elaborate compatibility manifest.

## II.11 Education and documentation architecture

Each lesson should have four parts:

1. **Goal:** a real task the learner can complete.
2. **Concept:** the underlying computing primitive and why it matters.
3. **Practice:** a small tool, experiment, or executable check.
4. **Inspect:** how to observe behavior and optionally reveal the native implementation.

A fifth optional section, **Extend**, shows how the new capability composes with earlier ones.

Examples should be executable in a pinned Basix workspace, checked in CI, and written with clear expected inputs and outputs. Avoid teaching a huge framework before showing a small working example.

Keep educational material separate from executable core modules: documentation changes should not require rebuilding the ISO or modifying Vendomat.

## II.12 Longer-term interaction model

The optional future interaction layer makes computing more accessible through:

- Low-friction voice and small-controller input.
- Context derived from visible workspace, current command, files, and available capabilities.
- LLM-assisted interpretation that proposes **choices**, not opaque arbitrary side effects.
- Iterative refinement of a vague request into inspectable, declarative changes.
- Quality/approval gates for risky or ambiguous operations.
- Idempotent application, previews, version-control history, and deliberate rollback.

This layer should **operate on the same validated catalog and native mechanisms** that manual users employ. It must not form a second configuration authority, bypass typed checks, or write privileged machine state without authorization. Prompts and suggestions are not substitutes for disk safety checks, secret handling, or trusted module evaluation.

Treat assisted interaction as a later optional Basix application, not a prerequisite for installing or learning the core system.

## II.13 Repository organization

Suggested structure:

```text
basix/
  nix/
    catalog/            # basix.* typed options and mappings
    core/               # minimal bootable NixOS configuration
    profiles/           # curated system roles
    capabilities/       # storage, networking, databases, etc.
    installer/          # ISO composition and target profiles
  templates/            # Basix workspace with two pinned inputs
  curriculum/
    lessons/
    reference-project/
  examples/
  apps/                 # optional higher-level applications
  tests/
    interface/
    capability/
    profile-vm/
    installer-vm/
    curriculum/
  docs/
    user-guide/
    developer-guide/
    release-compatibility/
```

The separate repo is a hard architectural boundary. Subfolders are illustrative and can start much smaller.

## II.14 Release-one scope and exclusions

**Release-one product:** a bootable minimal Basix environment, independently pinned source modules, a simple profile, a small capability set, executable lessons, and one reference project that uses the capabilities in sequence.

Prioritize a real end-to-end path over a large catalog. An effective first vertical slice might be:

- Core ISO + keyless local install VM.
- Basix `core` and `learning` profiles.
- Storage/files and process/stream capabilities.
- A small note-capture reference project.
- A typed Basix namespace that configures a visible change through `vendomat.yaml`.
- A rollback demonstration.

**Defer:** large desktop customization matrix, many hardware targets, universal driver support, fully autonomous AI, voice/controller interaction, cloud synchronization, elaborate module registry, automated multi-host provisioning, and broad capability-combination guarantees.

A usable minimal system is more important than supporting every interesting capability in the first release.

## II.15 Acceptance criteria

Before calling the independent product viable, prove:

1. The Basix repository builds its module set and ISO while Vendomat remains unchanged.
2. Its workspace pins both projects in one native lock with documented compatibility.
3. A Basix-owned typed YAML namespace is accepted; unknown keys and bad values fail; a plain Vendomat workspace still works with no Basix imports.
4. A supported VM can boot the ISO, safely refuse an occupied disk, install a blank target, reboot keyless, apply a profile change, and boot a prior generation.
5. No secret provider, signing key, or network cache is mandatory at first boot.
6. Core capability tests pass, examples work, and a learner can complete the first lesson without editing native Nix/devenv files.
7. Basix source and documentation can be independently updated without changing Vendomat runtime code.
8. A tested update/rollback sequence names the exact input revisions and which system state it restores.

---

# Shared integration contract and transition plan

*This section defines the interface between the two projects. It is intentionally separate from both standalone concepts.*

## III.1 Ownership boundaries

| Topic | Vendomat owns | Basix owns |
| --- | --- | --- |
| Routine user file | File read, strict YAML grammar, generic catalog | `basix` subtree and its user-level meanings |
| Option system | Mechanism to compose/validate imported namespaces | Definitions of additional options and defaults |
| Packages/services | Generic configuration mechanism | Curated choices and capability compositions |
| Workspaces | Minimal general-purpose template and pinned runtime | Extended template with its own separately pinned source |
| Machines | Generic apply/install invocation and shared safety invariants | OS core, ISO, disk policy within the supported generic guard, user experience |
| Infrastructure | Generic store sharing and native Nix interfaces | Which profiles/machines use them |
| Versioning | Vendomat release + native input lock behavior | Basix release and compatibility declaration |
| Education and apps | No responsibility | All lessons, example projects, user applications |

**Dependency rule:** `Basix → Vendomat → devenv/NixOS/Nix`; no reverse imports, conditionals, build dependencies, or tests requiring Basix inside Vendomat's core release path.

## III.2 Minimal stable interface

Basix needs only a deliberately narrow Vendomat contract:

1. A pinned runtime and matching devenv fork/module source.
2. One YAML reader with stable strict grammar and errors.
3. A typed catalog composition point through ordinary Nix module imports.
4. A small native-backed shell/build/test/update/apply/install command surface.
5. Documented machine-safety and cache configuration primitives.
6. Stable enough templates that a separately versioned consumer may supply an additional import without editing Vendomat source.

Do not prematurely promise a general-purpose plugin protocol, a Python extension SDK, or arbitrary third-party module isolation. Nix modules remain executable configuration code and therefore part of the user's **trusted configuration**, not sandboxed untrusted plugins.

## III.3 Decisions revised from the October 12 accepted baseline

The uploaded `CONCEPT(20261012-214636).md`, `REQUIREMENTS.md`, and `DECISIONS.md` establish an accepted design but do not establish a completed implementation. The new separation changes **product ownership**, not the proven YAML/fork foundation.

| Existing accepted area | Disposition in this proposal |
| --- | --- |
| R1 / `DOOR-074`: `vendomat.yaml` parsed through fork primop, no generated tree | **Retain.** Expand template/import proof to an external namespace. |
| `DOOR-075`: strict YAML grammar, typed catalog, one validator | **Retain.** Extend unknown-key/type validation over imported declarations; new fixture required. |
| `DOOR-071`: only `new`, `apply`, `install` implemented; native passthrough | **Retain.** Ensure `install`/`apply` are truly generic operations. |
| R2 / `DOOR-072`: local installation using the Basix ISO | **Split ownership.** The ISO, bootable core, and opinionated machine catalog belong in Basix; common safe operations belong in Vendomat. |
| S34: ship the machine catalog in the Vendomat release | **Replace.** Import the separately released Basix catalog from the Basix template. |
| R3 / `DOOR-036`: native source refs/follows, deferred source collection | **Retain.** Add a separately pinned Basix input through the same native lock. |
| `DOOR-073`: optional Harmonia cache, host-created key | **Retain as generic infrastructure.** A profile may select it but does not own it. |
| R4 / `DOOR-063`: migration and old-runtime cleanup | **Retain migration discipline.** Revise consumer conversion records to include the independent project boundary. |

The current accepted IDs should not silently be relabeled as already proven. Maintain the historical requirement ledger and add successor requirements only when the owner accepts this split, following the decision log's rule on unnecessary ID churn.

## III.4 Implementation sequence and evidence gates

### Phase 0 — Freeze ownership

- Record the one-way dependency rule and two independent repo/release identities.
- Assign the generic machine/cache pieces and product-specific ISO/catalog pieces to their owners.
- Separate historical accepted decisions from new proposed changes.
- Preserve current live consumers and Attic until their respective cutover gates pass.

**Gate:** repository and dependency diagrams show no reverse dependency and no bundled product-specific module in Vendomat.

### Phase 1 — Establish generic Vendomat baseline

- Complete the pinned YAML primop and strict catalog fixtures.
- Verify new workspace, shell/native pass-through, lock restore, and direct direnv/Testee evaluation.
- Keep native files and lock behavior visible for advanced recovery.

**Gate:** independent Vendomat workspace passes without importing any external profile.

### Phase 2 — Prove the extension seam

- Build a tiny separate fixture module that declares one additional YAML namespace.
- Confirm one parse, composed typed validation, unknown-key failure, eager bad-unused-field failure, native Nix merge behavior, and no generated files.
- Confirm a template imports two pinned sources with a single `devenv.lock`.
- Measure whether implementation can use standard Nix option declarations without a second custom registry.

**Gate:** an external namespace works without changes to Vendomat's parser or CLI. **This is the highest-value architectural proof.**

### Phase 3 — Extract the standalone distribution

- Create the Basix repo with minimal core, ISO, profile, and its typed namespace.
- Move all product-specific machine defaults, installer experience, and educational content into Basix.
- Leave generic install/apply safety and execution in Vendomat.

**Gate:** a clean VM boots the Basix ISO, refuses an occupied disk, installs a supported blank disk, boots without secrets, applies a change, and rolls back by generation.

### Phase 4 — Establish independent releases

- Publish a Basix release against an exact tested Vendomat release.
- Verify independent source pin update and restoration through the native lock.
- Add a basic compatibility test matrix across at least two intentionally selected revision pairs.

**Gate:** updating only the Basix source changes Basix functionality without modifying Vendomat code or the generic workspace.

### Phase 5 — Add education and optional infrastructure

- Deliver two or three capability modules and executable lessons.
- Advance the small reference project from files to structured data.
- Finish a real two-machine Harmonia check before replacing any live Attic path.

**Gate:** documentation and executable examples pass; cache cutover is independently verified, not inferred from VM-only smoke tests.

## III.5 Risks and mitigation

| Risk | Why it matters | Response |
| --- | --- | --- |
| Fixed catalog rejects external keys | Separate project cannot own new routine data | Prove namespace composition before further product work. |
| Strict YAML cannot express complex Nix values | Advanced use cases may outgrow data catalog | Keep catalog intentionally bounded; native Nix remains an advanced door. |
| Extra input produces conflicting nixpkgs/devenv revisions | Reproducibility and compatibility may fail | Declare tested `follows` edges and verify exact locked graphs. |
| `vendomat update` updates more than expected | Projects would appear independently versioned but move together | Test selective native updates and document explicit input choices. |
| Generic installer is still product-specific internally | Separation becomes cosmetic | Enforce that install plan/defaults reside entirely in the importing distribution. |
| Normal use requires native Nix edits | Educational abstraction fails | Make the initial supported profiles and capabilities configurable in YAML. |
| Extension interface becomes a framework | Scope and complexity grow prematurely | One parse, typed Nix options, explicit imports, no runtime plugin marketplace. |
| Rollback is overstated | Users may think data or disk changes reverse automatically | Distinguish NixOS generations, revision lock, filesystem and application data. |
| Security assumptions hidden by approachable UI | Privileged installs and modules remain consequential | Clear plan/confirm steps; trusted module sourcing; no silent privilege escalation. |

## III.6 Final boundary rule

Ask two questions when assigning a new feature:

1. **Is this a reusable mechanism for declaring, building, running, applying, or managing a computer?** If so, it is a candidate for Vendomat.
2. **Does it select a computing experience, choose defaults, combine capabilities, teach concepts, or provide an application?** If so, it belongs in Basix.

When the feature has both parts, **split the mechanism from the policy**, retain one native execution path, and keep their versioned sources independent.

---

## Basis and status notes

This document is a deliberate refinement of the three supplied files, not a claim of an already-built architecture:

- `CONCEPT(20261012-214636).md`: the accepted minimal workspace, shell, install/apply, cache mental model, and release-one exclusions.
- `REQUIREMENTS.md`: especially accepted `DOOR-036`, `DOOR-038`, `DOOR-063`, `DOOR-071` through `DOOR-075`, the test gates, and superseded alternative designs.
- `DECISIONS.md`: October 12 owner rulings R1–R4 and the supporting P2A–P2G fixture progression. Rulings accept design; they do not imply that runtime implementation gates have passed.
- Subsequent design choices: Basix is both an educational system and usable Linux environment; Vendomat works independently; Basix has a separate repository/version; normal Basix use hides Nix/devenv.

**New proposals requiring confirmation and proof:** typed catalog extension by explicit module imports; independently pinned Basix module source; extraction of the bundled machine catalog; generic install/apply boundary; tested independent update behavior. No physical disk operations are authorized by this document.

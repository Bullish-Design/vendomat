# Vendomat V4

## Composable devenv modules, inspectable source, and checked Attic distribution

**Date:** 2026-10-04.  
**Status:** Consolidated concept for a ground-up rewrite, incorporating the owner's clarified goals and accepted recommendations.  
**Scope:** One owner's NixOS machines, development projects, and reusable personal applications.  
**Authority:** This document supersedes the earlier rewrite concepts and their implementation sequence.  
**Implementation status:** Design only. Examples describe intended contracts; they do not establish implemented Vendomat interfaces.
**Revision:** Revised 2026-10-04 by the adversarial review in `.scratch/projects/11-vendomat-v4-adversarial-review`. See [V4-REVIEW.md](./V4-REVIEW.md) for each finding and its evidence.

### Markers used in this revision

| Marker | Meaning |
| --- | --- |
| `[OWNER DECISION]` | The text stands until the owner decides. The review found a conflict it will not resolve for the owner. |
| `[PROTOTYPE]` | The claim needs a fixture on the pinned versions. Primary documentation does not settle it. |
| **proposed** | A name, not an interface. Accepted decision D-NAMES. |

### Accepted owner decisions

All eight carry the same authority. `V4-SPEC.md` §1 holds the full text of each.

| ID | Decision | Date |
| --- | --- | --- |
| D-APP-SCOPE | The Jujutsu-btrfs-bubblewrap application is a later reusable module outside initial V4. | 2026-10-04 |
| D-NAMES | Specify semantics first. New option and command names remain proposed. | 2026-10-04 |
| D-CHECK-OWNER | Enabled modules supply default required checks. Consumers may add gates. | 2026-10-04 |
| D-CHECK-GAP | A missing relevant check outside the required set is a visible gap. It blocks nothing by itself. | 2026-10-04 |
| D-CAPTURE | Initial automatic capture covers owned modules and direct dependencies on a consumer-maintained list, including the first-proof fixture. | 2026-10-04 |
| D-ATTIC-SCOPE | Attic exists so the laptop does not rebuild. Trusted public caches may serve upstream closure paths. Attic-only complete-closure retention is not a V4 gate. | 2026-10-04 |
| D-SRC-ACCESS | The source store is a plain directory, read over Secure Shell (SSH). No Vendomat daemon serves it. | 2026-10-04 |
| D-PROOF-SPLIT | Two fixtures carry the first proof. The `*man` toolchain carries delivery, closure, and publication. The Neovim application carries composition and application behavior. | 2026-10-04 |

## 1. Purpose

`[OWNER DECISION]` Vendomat helps the owner compose a personal system from reusable devenv-based modules.
It makes modules easier to discover, configure, develop, inspect, validate, and distribute.

This repository's `AGENTS.md` states the opposite ownership: Vendomat "is not the composition framework, manifest owner, or workspace orchestrator; those roles belong to RepoMan, `repoman.lock`, and the surrounding fleet tools".
`docs/DESIGN.md` repeats it.
The owner must decide whether V4 moves composition into Vendomat or leaves it with RepoMan.
Until then, read this document's composition content as a consumer-side convention that Vendomat reports on and does not own.
Vendomat's two core services below do not depend on that decision.

The foundation is ordinary Nix and devenv configuration, supported by native packages, scripts, and application configuration.
A module can provide a development environment, a command, an editor application, or a service.
A larger module can compose several smaller modules.

Vendomat adds two core services around that composition:

- A source store that gives people and agents access to identifiable source for inspection.
- Checked publication of selected Nix outputs and the runtime dependencies that a trusted cache does not already serve.

devenv is the main interface for project composition and machine operations.
NixOS and Home Manager retain their native configuration and activation responsibilities.
Vendomat provides conventions and small helpers where those tools otherwise require repeated manual work.

The intended experience is:

```text
choose modules
    -> compose and configure a project or machine
    -> develop with local overrides
    -> inspect relevant source
    -> check and build selected outputs
    -> publish outputs
    -> use the same outputs on another machine
```

Normal module execution needs no live Vendomat service.
Native declarations and locks remain understandable and usable without the Vendomat command.

## 2. Design decisions

| Concern | V4 decision |
| --- | --- |
| Primary abstraction | A reusable module with explicit native contributions |
| Main composition interface | devenv, using native Nix module behavior |
| Applications | Modules that compose useful commands, configuration, and interfaces |
| Actions | Named commands or functions with contracts where needed |
| Context | Source, files, notes, and retrieval commands; richer indexing can follow |
| Configuration | Native files and typed Nix options; no required `vendomat.yaml` |
| Module delivery | Support ordinary devenv repositories and flake-backed exports |
| Dependencies | Native inputs and locks; no Vendomat resolver or lock |
| Machine interface | A pinned, tested devenv release with Machines support |
| Source purpose | Inspection and useful context for people and agents |
| Source coverage | Broad discovery, selective capture, optional broader retention |
| Binary distribution | Two channels, one build: Attic serves store paths to Nix consumers; a release URL plus hash serves wheels to non-Nix consumers |
| Publication unit | An exact selected Nix output, plus every closure path no trusted configured substituter already serves (D-ATTIC-SCOPE) |
| Required checks | Named devenv tasks declared by the enabled modules and the consumer |
| First workflow | Compose, develop, inspect, check, build, publish, and consume |
| Upgrade assistance | On-demand native proposals before scheduled sweeps |
| Releases | Declared tasks using native version metadata |
| Generation | Small scaffolds and repeated integration wiring |
| Runtime state | Ordinary files, directories, and native service state |

This is a greenfield design for the module, source, and publication model.

`[OWNER DECISION]` It is not greenfield for the delivered consumer surface.
`modules/devenv.nix` is installed on a machine at `/run/current-system/sw/share/vendomat/consumer-module.nix` and resolves store paths from an installed `machine.json`.
That file names its input-delivery path a compatibility fallback "kept for one release".
`src/vendomat/plane.py` states "Vendomat owns this lifecycle" for machine-level plane generations, and the command-line interface exposes `plane plan`, `update`, `rollback`, `show`, and `recover`.
Section 23 forbids Vendomat from owning a deployment plan or rollback.
The owner must decide the disposition of each delivered surface before the first V4 machine generation.
Requirement V4-OWN-012 records that inventory.

## 3. Ownership and system model

Each authoritative fact has one owner.

| Owner | Responsibility |
| --- | --- |
| Module repository | Source, exported modules, package recipes, checks, and documentation |
| Consumer repository | Selected modules, configuration, overrides, and native locks |
| RepoMan and `repoman.lock` | Per-repository lifecycle composition and the module manifest, per `AGENTS.md` |
| Testee | Verification. It is the single verification interface for a `*man` repository |
| devenv | Project environments, module composition, tasks, outputs, and machine operations |
| Nix | Evaluation, derivations, builds, store identity, and substitution |
| NixOS | System configuration, host services, daemon trust, and system activation |
| Home Manager | User configuration and its activation |
| Native application | Its interface, runtime behavior, and application state |
| Source store | Retained source bytes and their inspection identity records |
| Attic | Cached Nix outputs, signing, and binary delivery |
| Version control | Reviewed source, configuration, and dependency history |
| Vendomat | Source lookup and capture, checked publication, reports, and evidence |

```text
module repositories
        |
        v
consumer declarations and native locks
        |
        v
devenv composition
        |
        +----> project environment and tasks
        +----> packages and Neovim applications
        +----> Home Manager contributions
        +----> NixOS contributions through devenv Machines
        |
        v
checks and selected Nix outputs ----> Attic ----> native consumption

selected dependencies ----> source inventory ----> retained source
                                                      |
                                                      v
                                              human and agent inspection
```

The source path and binary path have separate success conditions.
They can share identities and reports without depending on each other's availability.

## 4. The reusable module

A module is a reusable unit of functionality expressed through native configuration and implementation files.
It may live in a repository or a subdirectory.
A repository may export several modules.
No formal repository hierarchy is required.

Examples include:

- A Python development environment with tools, checks, and tasks.
- A review application with a command-line tool and Neovim interface.
- A navigation module that composes symbol lookup and history commands.
- A service with a package, project development process, and NixOS service configuration.
- A workstation module that combines editor, shell, and service modules.

A module exports only the contributions it needs.

| Contribution | Native form |
| --- | --- |
| Project tools, tasks, and processes | devenv module |
| Installable command or application | Nix package or devenv output |
| Neovim interface | Lua files, plugin files, and native editor configuration |
| User configuration | Home Manager module |
| System service or configuration | NixOS module |
| Reusable operation | Script, command, or library function |
| Inspection guidance | Documentation, source references, or retrieval commands |

The contract describes the module's exported contributions, options, dependencies, and checks.
Typed Nix options provide configuration contracts.
Commands document arguments, output formats, exit behavior, and side effects where relevant.
Machine-readable output is useful when another component consumes the result.

Vendomat does not require every small script to adopt a universal message schema.
A schema belongs at an actual integration boundary.

Composition breadth has an evaluation cost.
This repository already measured it: a repository that enables no contribution "must not import the module at all", because it pays a flake input's evaluation and a probe on every shell entry for no output (`README.md`).
A disabled component must add no shell-entry work.
Requirement V4-MOD-015 measures this.

### Names and conflicts

Modules use stable namespaces for options, tasks, commands, and editor functions.
Names identify functionality; source revisions identify versions.
Native package metadata remains authoritative for package names and versions.

The consumer selects shared configuration explicitly.
Normal Nix merge rules and assertions handle option conflicts.
Vendomat should expose useful diagnostics without silently choosing between incompatible definitions.

Conflicting editor bindings require an explicit consumer choice.
Shared defaults should remain overridable.
Tools with incompatible private dependencies can remain separate packaged commands.
Shared project settings must resolve consistently in the composed environment.

## 5. Applications, actions, and context

An application is a useful composition of modules.
It does not require another package type or resolver.
A review application can compose source inspection, review logic, a command, and an editor interface.

An action is a named operation exposed by one of those components.
A stable name and a small contract can support several callers.
An editor command, shell command, and agent instruction can invoke the same implementation.

Optional metadata may describe a command's name, purpose, invocation, and structured result.
Generate such metadata from existing declarations where practical.
Add a shared convention when multiple real integrations need it.
A global action registry is outside the initial design.

Context begins with readable source, notes, documentation, and retrieval commands.
Modules can request or produce these through ordinary paths and command interfaces.
No context server, graph database, or universal context identifier is required.

Generated summaries remain separate from source facts.
A summary records the source identities and generation inputs that produced it.
It can become stale even when its file still exists.
Reports must distinguish generated interpretation from retained source.

## 6. Neovim application modules

Neovim applications are a primary use case for the module contract.
A module can package scripts, reusable command-line tools, editor commands, panels, pickers, and default bindings.

For example:

```text
review module
    +-- review command and reusable implementation
    +-- structured findings format
    +-- Neovim commands, panel, and navigation
    +-- overridable default bindings
    +-- project tasks and checks
    +-- source inspection guidance
```

Neovim provides native packages that can contain cooperating plugins and optional components.
Use those mechanisms for the editor contribution.
See the [Neovim package documentation](https://github.com/neovim/neovim/blob/master/runtime/doc/pack.txt).

Where useful, a module exposes two delivery forms:

1. A plugin contribution for the owner's normal Neovim configuration.
2. A dedicated Neovim application output with a controlled configuration and launcher.

Both forms share implementation files and packaged dependencies.
The dedicated application can run beside the normal editor without replacing its configuration.
Its exact launcher and configuration isolation are proved in the first implementation fixture.

Reusable processing belongs in a command or library when multiple interfaces need it.
Editor-specific behavior can stay in Lua.
There is no requirement to force editor state through an external command.

User interface (UI) helpers can themselves be reusable modules or ordinary Lua libraries.
Vendomat does not need a new UI description language.
The editor contribution must use the intended command package, rather than accidentally finding an unrelated executable on `PATH`.

Checks cover both the reusable operation and the editor contribution.
A useful integration check launches the configured editor and exercises a representative command.

## 7. Composition across native targets

A module may contribute to devenv, Home Manager, and NixOS.
Each contribution is a native module for its target.
devenv project options do not automatically become NixOS or Home Manager options.

A higher-level composition selects the matching contributions for a project, user, or machine.
It passes shared settings explicitly where those contributions need them.
The contract must identify the target host and user for persistent configuration.

Once the consumer enables a module for a target, its relevant components may default to enabled.
Each component retains an override.
For example, a workstation can enable a review command and editor integration together.
A project shell can use the command and tasks without requiring an editor configuration change.

Importing definitions, enabling functionality, and activating persistent configuration are separate operations.
Evaluation describes the result.
Native project or machine commands start processes and activate configuration.

The first implementation should avoid assigning new global meaning to import order.
It should preserve native option merging and report incompatible settings.
See [devenv imports](https://devenv.sh/composing-using-imports/) for the underlying composition interface.

## 8. Repository and dependency delivery

Authors may use an ordinary devenv repository or a flake-backed export.
Both should expose the same conceptual module contract.
The delivery mechanism must preserve native dependency identities and locks.

A possible repository structure is:

```text
review/
    devenv.nix             author development environment
    devenv.yaml            author development inputs
    devenv.lock            native input lock
    flake.nix              optional reusable exports and transitive inputs
    modules/
        devenv.nix
        home-manager.nix
        nixos.nix
    nix/
        package.nix
    scripts/
    lua/
    plugin/
    tests/
    docs/
```

This is an example, not a mandatory layout.
Small modules may need only a few files.
Expose dedicated reusable modules so a consumer does not inherit the author's entire development environment.

### Ordinary devenv repositories

An ordinary repository can export a reusable Nix module and buildable outputs.
Its consumer supplies required native inputs where the export cannot carry them itself.

Upstream devenv documents two limits for cross-project composition.
"The remote repository must use `devenv.nix` only — `devenv.yaml` from imported projects is not evaluated."
And "Profiles don't work with cross-project references."
Both are documented facts, not open questions.
Supporting ordinary repositories therefore does not imply automatic recursive YAML composition.
See [devenv polyrepo behavior](https://devenv.sh/guides/polyrepo/).

The same page documents a third route this concept previously omitted.
A consumer can read another project's configuration and outputs without merging its modules, through `inputs.<name>.devenv.config`.
Evaluate that route beside the plain import and the flake-backed export.
It may remove the need for a flake wrapper in some cases.
Requirement V4-MOD-016 covers it.

### Flake-backed exports

A small flake can expose reusable modules, packages, and native transitive inputs.
This is the preferred initial route for a self-contained reusable module with its own input dependencies.
The export must make its dependencies available to its module implementation explicitly.
Their presence in a lock does not automatically import or enable them.

Native inputs support nested references and deliberate input sharing.
The consumer's effective native lock controls the resulting selection.
See [devenv inputs and locks](https://devenv.sh/inputs/).

### The intended convenience

The desired experience is one module selection with its required dependencies available.
Prove that experience for a flake-backed module and a plain devenv module early.
If the plain form needs consumer input declarations, show that requirement clearly.

A later helper may prepare native input declarations or a small wrapper.
It must make reviewable changes and preserve one authority for each dependency declaration.
Vendomat must not introduce a recursive YAML resolver or a shadow lock to hide this limitation.

### Package identity

Composition uses the consumer's package set by default where that is appropriate.
A packaged command may carry its own resolved dependency graph.
Vendomat does not force every package through one global package-set override.

Changing inputs, profiles, or package recipes can change the derivation and output path.
Two consumers of the same module revision may therefore need different cached outputs.
Cache reuse depends on the selected Nix output, not merely the module name or release tag.

## 9. The daily development workflow

The first workflow must make module development convenient.

1. Add a module through native input and import declarations.
2. Inspect its options and choose the relevant target contributions.
3. Enter the project environment or build the selected application.
4. Temporarily select a local checkout while developing the module.
5. Run checks against the composed consumer, including the changed module.
6. Review and commit the intended source and dependency changes.
7. Build and publish the exact selected output.

Local overrides are visible and reversible.
They must not silently change another consumer's accepted selection.
The report distinguishes development state from an immutable publication selection.

Local development does not require publishing each edit, creating a release, or contacting Attic.
Module source, user notes, and mutable application state remain outside immutable package outputs when they need editing.

Vendomat helpers should reduce repeated setup and explain the effective composition.
They should expose which module supplies a command, option, task, or configuration contribution where that information is available.
They should not require a separate project registration database for ordinary module use.

## 10. Machine composition and deployment

Use devenv Machines as the normal interface for the owner's machines.
Pin one tested devenv release or revision with Machines support.
Keep the executable and its module implementation consistent.
A minimum-version constraint alone does not establish that tested combination.

Machine definitions compose ordinary NixOS and Home Manager modules.
Project composition and machine composition share an operator interface while retaining distinct native configuration targets.

Upstream Machines provides `info`, `build`, `check`, `install`, `deploy`, `plan`, `apply`, `status`, and `rollback` operations.
A plan "builds outputs and records the NixOS system, access facts, and store closure changes", and stores them under `.devenv/machine-plans/<id>/`.
Apply "uses those exact outputs without rebuilding, checks that the machine still matches the plan, copies all outputs, then activates them".
Machines is "new in devenv 2.4. The interface may change before it is declared stable."
A pin change therefore re-runs the machine gates.
See [devenv Machines](https://devenv.sh/machines/).

Vendomat coordinates source reports, checks, cache publication, and evidence around those native operations.
It does not create another deployment plan format or activation engine.

The intended machine workflow is:

```text
prepare exact configuration
    -> run required checks
    -> create native machine plan
    -> check selected outputs
    -> publish and verify outputs in Attic
    -> review configuration, evidence, and plan
    -> apply that native plan
```

The publication report records the plan identity and selected paths.
If the native tool rejects a stale plan, prepare a new plan and revalidate its relationship to the evidence.
Reuse prior check results only when their recorded inputs still match.

The native watchdog "restores the previous system if activation or a health check fails, or if the controller cannot confirm success before the deadline. The default deadline is 300 seconds."
Its documented limits are explicit: recovery "cannot fix an early boot failure, reverse application data changes, or undo side effects of activation scripts. A kernel change still needs a reboot."
Upstream also states "The roles are separate activations. If home-manager fails after NixOS succeeds, the NixOS deployment remains applied. NixOS rollback does not revert home-manager files."
Report each activation result separately.
See the [upstream recovery boundaries](https://devenv.sh/machines/).

`[OWNER DECISION]` That separation holds for standalone Home Manager.
Home Manager documents that when it runs as a NixOS module, "we may not have a `home-manager` profile at all", and "the system profile will contain references to the corresponding Home Manager configurations".
A system rollback can then move the user configuration with it.
The P0 record must name which integration mode the owner's machines use.
Requirement V4-MACH-015 records it.
See [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html).

Cache publication and deployment remain distinct.
Publication proves cache availability; deployment proves an activation result.

Upstream documents the transfer path: apply "copies all outputs" with `nix copy`.
Direct copy from the build host is therefore the documented behavior, not an open question.
`[PROTOTYPE]` Whether the pinned version can prefer a target-side substituter instead remains unproved.
Nix's separate `builders-use-substitutes` setting shows that substitute-instead-of-copy is an explicit opt-in.
If the pinned version offers no such route, Attic is the laptop's interactive path and not the deployment path.

## 11. The inspection source store

The source store answers:

> Which retained source corresponds to the software selected by this project or machine, and where can I read it?

Its initial purpose is inspection, debugging, explanation, and agent context.
Rebuilding from the archive is a separate optional capability with a separate proof.
Source capture does not establish that proof.

### Source identity

An inspection record should include:

- Original source locator and ecosystem identity where available.
- Exact revision, archive hash, or other native source identity.
- The consumer selection that led to the source.
- Retained object location and capture result.
- Relationship between retained source and the selected software.
- Known patches, generated components, missing inputs, or mapping limitations.

Use native forms suited to the input.
Git mirrors or bundles can retain commits through explicit references.
Archives can retain verified source distributions.
Nix source paths can participate when explicit roots and backups make their retention durable.
Ordinary local Nix garbage collection must not remove the only retained inspection copy.

Git object verification and archive hash verification retain their native semantics.
An archive hash record includes its hash algorithm and the representation being hashed.
Do not compare a raw archive hash with a hash of its unpacked tree as if they were interchangeable.

### Correspondence and coverage

Report correspondence separately from whether bytes are present.

| Correspondence | Meaning |
| --- | --- |
| Exact selected source | Retained bytes match the identified source used by the selection |
| Selected source with packaging changes | The upstream source is known, with recorded patches or transformations |
| Upstream reference | Useful source is retained, but exact correspondence is not established |
| Unresolved | Vendomat cannot yet connect the selected software to suitable source |

Capture status distinguishes retained, identified but not captured, unavailable, and unidentified source.
A record may be retained yet still have only approximate correspondence.
The inspection interface must show both facts.

Prefer the selected revision over the latest upstream revision.
When a patched package differs from upstream, expose the patch information beside the source.
Do not silently describe an upstream checkout as the exact installed implementation.

### Read access

Provide read-only trees that people and agents can open with ordinary tools.
A lookup should identify the project or machine context, dependency, revision, and readable path.
The interface should expose provenance without requiring a special editor or agent runtime.

The durable source store is a plain directory on the build host (D-SRC-ACCESS).
It offers read-only access over Secure Shell (SSH) or a read-only export.
No Vendomat daemon serves it, so invariant 5 stays literally true for inspection as well as execution.
Clients may keep local read views for convenience or disconnected work.
Ordinary application startup and project evaluation must not require a mounted remote inspection tree.

This store already exists in part.
`docs/SOURCE_CATALOG.md` documents `~/vendor/<package>/` as the writable third-party checkout cache, overridable with `VENDOMAT_SOURCE_ROOT` or `--source-root`, and `.vendomat/sources.toml` as the generated map.
V4 extends that directory with correspondence labels and capture status.
It does not design a new store.

Unpacked trees and convenience checkouts can be derived from retained objects.
Deleting a derived view must not delete the archive or its identity records.
The read layer is outside normal package evaluation and builds.
An explicit source override uses native build inputs, not an inspection checkout selected implicitly.

Read access must not alter the source archive, consumer locks, or installation choices.
Agents can use scratch copies when an investigation requires edits.

## 12. Coverage policy: discover, capture, and index separately

Source coverage has three independent operations:

| Operation | Result |
| --- | --- |
| Discover | Identify selected dependencies and possible source mappings |
| Capture | Retain identifiable bytes for later inspection |
| Index | Prepare search data, symbols, summaries, or another derived view |

An inventory can be broad without downloading every dependency.
Captured source can remain useful without an index.
An index can be rebuilt without changing source identity.

The default policy is:

1. Retain the owner's reusable modules and their relevant configuration source.
2. Capture important direct dependencies of selected projects and applications automatically.
3. Capture deeper dependencies and system components when an inspection requests them.
4. Permit explicit holds and optional broader automatic capture.
5. Expand indexing only when real searches demonstrate its value.

Native declarations should identify direct dependencies where possible.
Allow explicit policy for dependencies that native metadata cannot classify usefully.
An explicit consumer list may support cross-repository discovery, but it does not become a dependency authority.

The reviewed capture list already exists.
`vendor/python/*.toml` records `name`, `kind`, `repository`, and an immutable 40-character revision, validated by `src/vendomat/catalog.py`.
`vendomat vendor sync` already "only clones, fetches, and detaches reviewed third-party sources" and "never writes a source into `pyproject.toml`, `[tool.uv.sources]`, or `uv.lock`".
D-CAPTURE is therefore satisfied by shipped, tested code.
Extend that schema with correspondence labels; do not re-derive it.

| Coverage scope | Main value | Main cost |
| --- | --- | --- |
| Owned modules | Understand composition and maintain personal functionality | Limited dependency context |
| Project dependencies | Investigate integration failures and improve agent context | Ecosystem-specific source mapping |
| Selected machine software | Investigate editors, services, and system components together | More storage, discovery work, and correspondence gaps |

Machine-wide inspection is a supported direction, not an initial completeness requirement.
The scope remains software selected by declared projects and machines, rather than every package available upstream.

Discovery uses native locks, package metadata, evaluated Nix information, and narrow ecosystem integrations.
Build and runtime graphs answer different questions.
A runtime closure omits some build inputs; a derivation graph includes build dependencies.
See [Nix closure queries](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query).

Neither graph automatically establishes a complete map to readable source.
Downloaded objects may be binaries, source can arrive during evaluation, and local or generated inputs need their own treatment.
Fixed-output derivations and lock entries are discovery inputs, not a universal source-completeness proof.
Report unsupported cases and expand from real inspection needs.

Search starts in the active project's selected dependencies and expands when requested.
Optional indexes and summaries record source identities so stale derived data can be recognized.
Useful source outside a selected dependency graph may be retained explicitly for research.

## 13. Attic distribution and fallback

Attic is the owner's primary binary distribution service.
The desktop normally prepares and publishes outputs; the laptop normally consumes them.
Both machines retain ordinary local Nix stores.

The build host reuses suitable existing Nix outputs and builds missing derivations.
Central preparation does not require recompiling everything from source.

### Publication scope

For a selected published output, retain the output and every closure path that no trusted configured substituter already serves (D-ATTIC-SCOPE).
The purpose is that the consuming machine performs no build.
It is not disconnected operation, and it is not insurance against a public cache losing a path.
Begin with application and development outputs.
Add complete machine generations after measuring storage and transfer costs.

Attic's documented default already matches this scope.
`attic push` computes closures by default, and `--upstream-cache-key-name <NAME>` names "The signing key name of an upstream cache. When pushing to the cache, paths signed with this key will be skipped by default."
Leaving that filter in place is now the correct behavior, not an obstacle.
`--ignore-upstream-cache-filter` defeats it.
Keep that flag as an explicit, measured opt-in for a later disconnected-operation goal.
It is not a V4 gate.

The observable claim is that the cold consumer realizes the selected output path and runs no build.
Verifying it needs a named mechanism, because the Attic command-line interface documents no cache-presence query.
Use `nix path-info --store <endpoint>` per path, or substitute into an isolated store with every other substituter and build disabled.
See the [Attic client reference](https://docs.attic.rs/reference/attic-cli.html).

Attic remains a binary cache.
`attic push` accepts "The store paths to push" and nothing else.
Mutable application databases, notes, and development worktrees need their own storage and backup policy.

Attic is not the only distribution channel, and V4 does not retire the other one.
`README.md` records the existing rule: "One build, one artifact, two indexes — the store and the release URL — which therefore cannot disagree."
It also records why the release URL stays: "a published, hashed wheel referenced by URL is what makes a tool adoptable in a repo that has never heard of Nix, and this repo does not replace it."
Attic serves store paths to Nix consumers.
A release URL plus hash serves wheels to non-Nix consumers.
One build feeds both, and publication keeps the two indexes in agreement.
Requirement V4-CACHE-017 covers it.

### Consumer policy

The intended preference is:

```text
existing local Nix output
    -> Attic
    -> configured public caches
    -> build from native inputs when allowed
```

Two native facts constrain that chain.
Nix documents that "Substituters are tried based on their priority value, which each substituter can set independently. Lower value means higher priority."
The cache advertises the priority; the consumer supplies only the list.
Making Attic win therefore needs an Attic-side priority lower than every configured public cache.
Nix also documents that `fallback` "falls back to building from source if a binary substitute fails" and that "The default is `false`."
The last step of the chain is off until the policy sets it.
`[PROTOTYPE]` Nix's configuration reference does not define what happens when a substituter is unreachable.
Prove that case on the pinned version.
See [Nix configuration](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).

Allow laptop builds for ordinary development.
Treat expensive machine builds as an explicit operation when the desktop is unavailable.
A publication failure does not invalidate an already installed system or change its locks.

### Machine ownership and trust

NixOS configures the Attic service, storage, network access, substituters, and trusted signing key.
The build host holds a restricted push credential.
Consumers receive the cache endpoint and public trust key.
Secrets remain outside tracked files and Nix store objects.

The initial deployment serves the owner's private network.
Use native Attic authentication and signing behavior.
Vendomat does not implement a cache protocol, signing system, or secret manager.

## 14. Exact selections and checked publication

Nix outputs are the build and distribution boundary.
devenv can expose ordinary derivations through named outputs, built with `devenv build outputs.<name>`.
See [devenv outputs](https://devenv.sh/outputs/).

devenv outputs carry no check concept.
The outputs reference documents derivations only, and the testing reference documents one mechanism: `enterTest`, a shell script attribute run by `devenv test`.
Neither page documents a check bound to an output, a module-declared required check that a consumer inherits, or coverage reporting.
See [devenv tests](https://devenv.sh/tests/).

**Named devenv tasks are the required-check carrier.**
Tasks have names, declare `before` and `after` prerequisites, and return per-task exit codes.
This repository already uses them: `nix/testee.nix` exports `testee:quick`, `testee:detailed`, `testee:ci`, and `testee:doctor`, and `devenv.nix` exports `vendomat:lint` and `vendomat:test`.
A module declares its gate set as a list of its own task names.
A consumer appends task names for its composition.
Vendomat runs the union against the frozen selection and records each task name, its origin, and its result.
This adds no runner and no test language, which V4 section 16 forbids.

For a `*man`-family consumer the default gate already exists.
`gitman.toml` declares `[publish] verify = ["devenv", "shell", "testee", "verify", "--mode", "ci"]`, and the Testee skill states that Testee "is the single verification interface" for the repository.
V4 names that gate; it does not define a parallel one.

A publication selection records:

- An immutable consumer repository revision or an exactly recorded proposed change against one.
- Relevant native declarations and lock contents.
- Requested output attribute and target system.
- Active profiles and explicit input overrides.
- Effective module source identities.
- Evaluated derivation and resulting output paths.
- Required checks and their inputs.

A local editable checkout is useful for development.
The initial checked publication path requires an immutable selection.
If development-cache publication is added later, its evidence must identify the actual snapshot rather than claim a clean commit.

For a pure configuration module, the publishable result may be a composed application, environment, or machine output.
There need not be a separate binary artifact for the module itself.
Its configuration source still travels through native input mechanisms.

The pipeline is:

```text
freeze exact selection
    -> evaluate requested output
    -> run required pre-build checks
    -> build or realize that output
    -> run required artifact and integration checks
    -> confirm selected derivation and output identity
    -> push output and the closure paths no trusted cache serves
    -> verify current Attic availability
    -> record publication evidence
```

Source discovery and capture can run alongside this pipeline.
Their reports attach to the same selection.
An inspection gap does not block publication.
A source identity failure in an actual build input blocks the build's validation.
An identity failure confined to an inspection copy prevents claiming that copy is valid.

Required checks are existing named devenv tasks.
Vendomat declares which task names gate an output; it invents no test language.
Checks can run before or after the build according to what they exercise.
A failed required task blocks publication.
A declared required task that cannot run has not passed, and also blocks publication.
A missing relevant check outside the required set appears as a coverage gap and blocks nothing by itself (D-CHECK-GAP).
`[PROTOTYPE]` How a module expresses expected coverage for behavior it enables, without a new metadata language, stays unproved. See experiment P-CHECK-COVERAGE.

The exact checked output is the output uploaded.
A producer's successful release alone does not prove a particular consumer's composition works.
Validate relevant consumer integration against the selected output.

A cold consumer must realize the expected output during the foundation proof and perform no build.
Verify current availability separately from the success of the upload command.
Record which substituter served each path.
Do not infer a cache hit from a successful local build.

## 15. Evidence and reports

Query current state from its owner.
Retain historical evidence that cannot be recovered from current state.

| Question | Authority |
| --- | --- |
| What is selected now? | Native consumer files and locks |
| Which source bytes remain? | Source store |
| Which outputs are available now? | Attic and the local Nix store |
| What does this configuration evaluate to? | Nix |
| What was activated? | Native machine status and target state |
| What passed during publication? | Immutable publication evidence |

Source identity records preserve captured provenance.
Publication receipts preserve check and upload history.
Derived indexes may cache query results, but must be rebuildable and must not become authoritative locks.

A publication receipt records the selection, output identities, check results, cache target, upload result, and availability verification.
It links any source inspection coverage report and native machine plan.
Keep logs sufficient to explain failures and the checks that ran.
Do not store credentials or unrestricted environment dumps in receipts.

Reports keep these facts separate:

```text
source retained for inspection
exact source correspondence established
rebuild from retained source separately proved
selected output passed declared checks
output available in Attic now
dependency change accepted
machine or user configuration activated
```

A historical receipt cannot prove current cache availability.
A signature establishes acceptance by the cache key, not independent reproduction from source.
Missing source correspondence does not erase a valid artifact check.

## 16. Tasks, commands, and generated files

devenv tasks provide the project-local pipeline.
They invoke native commands and small focused helpers.
Declare prerequisite relationships and failure conditions explicitly.
Ordering alone must not be assumed to establish a successful prerequisite.

Tasks can pass structured results and use status checks where appropriate.
See [devenv tasks](https://devenv.sh/tasks/) for the supported interface.
An idempotent stage verifies the state it would reuse.
An existing output path does not prove that all checks passed or that Attic still holds it.

Vendomat helpers remain responsible for validating their inputs, classifying errors, and recording side effects.
The task graph supplies execution structure; it does not remove those responsibilities.
There is no second general workflow engine.

The command-line interface supports operations that benefit from a common entry point, span repositories, or run outside a project shell.
Initial responsibilities include source lookup and capture, publication reports, and diagnostics.
`[OWNER DECISION]` Composition inspection stays out of that list until the owner resolves the RepoMan ownership question in section 1.
Project wrappers may invoke the same underlying tasks.
Command names remain an implementation decision until the proof establishes a useful interface.

Hooks, editor commands, agents, and later timers call those same operations.
They contain minimal trigger logic.
Publication hooks are optional; normal local editing must remain convenient.

Scaffolding can create a small module or add repeated integration wiring.
Generated runtime configuration is derived from native declarations and templates.
Generated source changes remain reviewable patches.
Do not keep two editable copies of the same setting.

Vendomat does not need to parse arbitrary Nix source to read evaluated project facts.
Use native evaluation or generated machine-readable data for tool integration.
Structural editing helpers should be added only for specific repeated changes that need them.

## 17. Reviewed upgrades

After the composition and publication path works, add one on-demand upgrade proposal.
A proposal is an exact change to native consumer files.
It is not only a version number or a release announcement.

The proposal workflow is:

1. Start from a known consumer revision in an isolated checkout.
2. Invoke the native dependency update mechanism.
3. Record the proposed declarations and lock changes.
4. Evaluate and validate that exact composition.
5. Publish the successful output and verify its cache availability.
6. Present the diff, checks, source report, and any machine plan.

Native tools remain responsible for dependency resolution.
Branches, tags, and constraints may identify potential updates; native locks record the selected revisions.
Vendomat does not require every ecosystem to publish release tags.

A failed proposal preserves its logs and leaves the active consumer unchanged.
A successful proposal can be cached before acceptance.
Cache presence does not select the candidate automatically.

Before acceptance, confirm that the relevant base files still match and the validated outputs remain available.
A changed base requires a new proposal or demonstrated revalidation.
Acceptance applies the validated native diff.
It does not rebuild, commit, merge, tag, or deploy.
The owner's version-control workflow records the accepted change.

Deployment remains a separate native operation.
The native plan must still be valid when applied.
Reports distinguish a prepared proposal, an accepted uncommitted change, and an activated configuration.

Holds and exact pins can preserve a selected dependency deliberately.
Record a reason and date when Vendomat manages a hold.
Native dependency files remain the authority for the actual selected revision.

Scheduled sweeps come after the on-demand workflow is proven useful.
They may discover, validate, cache, and report proposals under declared policy.
They do not accept or deploy them automatically.
Scheduling belongs to native host services and timers.

## 18. Releases and optional automation

Release helpers are declared tasks using native project version metadata.
Projects can compose their existing version, check, publication, and tagging commands.
Vendomat does not introduce a required version field or infer semantic versions from source changes.

When a project needs a release task, it should:

1. Prepare native release metadata through the chosen version-control workflow.
2. Select the final immutable source revision.
3. Run required checks and build its declared outputs.
4. Publish and verify required cache outputs.
5. Create an immutable release tag on the tested revision, if the project uses tags.
6. Publish source references and record the result through the existing workflow.

A required gate failure prevents the task from reporting release success.
Retries must inspect completed side effects and preserve existing tag identity.
A correction receives a new release rather than moving a published tag.

A person or continuous integration system can invoke the same task.
The event source remains outside Vendomat's core.
No generic event bus, release engine, or hosted automation service is required.

More extensive application generation, agent workflows, and editor adapters can be separate modules.
They should use the same source, checks, and publication facilities as other modules.
Their existence does not require adding those application concerns to Vendomat itself.

## 19. Storage, mutable state, and recovery

Keep retained source, evidence, Attic data, and mutable application state distinguishable.
Each has a clear storage and backup owner.

| State | Treatment |
| --- | --- |
| Module and consumer source | Native repositories and reviewed history |
| Inspection archive and identity records | Durable source storage and backup |
| Read views, indexes, and disposable summaries | Derived state that can be regenerated |
| Publication receipts and failure logs | Durable evidence, with an explicit retention policy |
| Attic objects and signing state | Native Attic storage and coordinated backup |
| Application data and human notes | Native application or user storage and backup |
| Temporary checkouts and local overrides | Development state with explicit cleanup |

Use normal directories and native service storage first.
Modules may declare state locations and required services.
Immutable package outputs must not contain mutable working state.
A special filesystem or Vendomat state daemon is unnecessary.

### Retention

Initially, Vendomat performs no automatic deletion from the inspection archive or Attic.
Measure actual growth and report storage use.
Derived inspection views and temporary work can have independent cleanup rules.

Source and binary retention need not share one universal keep-set.
The inspection archive may retain useful code after its binary expires.
A cached binary may remain available even when complete source correspondence is unknown.
Neither condition becomes a false rebuild claim.

If deletion is added later, compute and preview the relevant protected objects.
Binary retention must account for active selections, pending proposals, saved plans, and machine recovery needs.
Source retention must account for explicit inspection holds and retained evidence that promises source availability.
Any separately claimed archive-backed rebuild must retain its required inputs while that claim remains active.

Deployment and rollback state can exist on remote machines.
An unreachable target makes its retention needs unknown; it does not authorize deleting those objects.
Destructive retention needs its own inventory and recovery proof.

### Restore proof

Restore source objects with their identity records, then verify readable source correspondence.
Restore Attic data and signing state, then prove that an existing consumer accepts the selected cached output.
Restore evidence so prior results remain explainable.

These are separate recovery results.
A source restore need not demonstrate an offline build.
A cache restore need not demonstrate complete source retention.

## 20. Failure behavior

| Condition | Required behavior |
| --- | --- |
| Missing module input | Explain the native input requirement; do not invent a resolution |
| Conflicting options or bindings | Identify the conflict and require an explicit configuration choice |
| Unsupported requested target | Fail that requested composition and name the unsupported contribution |
| Inspection source unavailable | Report the gap; valid build and publication work may continue |
| Inspection identity mismatch | Reject that inspection claim and preserve the failure evidence |
| Required build source mismatch | Fail the build's validation and stop publication |
| Relevant checks absent | Report check coverage explicitly |
| Required check or build fails | Keep useful logs; publish no success result |
| Upload or cache verification fails | Keep the local output; report publication failure |
| Partial closure upload | Record partial progress; retry safely; do not claim complete availability |
| Attic unavailable | Follow the tested native fallback and build policy |
| Read view or index missing | Regenerate or report unavailable derived data |
| Candidate base changed | Prepare or revalidate the candidate against the new base |
| Native deployment plan stale | Use the native rejection and prepare a valid plan |
| Activation fails or remains unknown | Report native status and recovery outcome before another deployment |
| Restore fails | Report the corresponding recovery claim as failed |

Failed publication does not alter accepted dependency state.
Source lookup does not change installation choices.
Vendomat failures do not replace the native tools' ability to inspect and use accepted state.

## 21. First complete proof

Two fixtures carry the first proof, split by role (D-PROOF-SPLIT).

| Fixture | Carries | Why |
| --- | --- | --- |
| The `*man` toolchain | Delivery, exact selection, checked output, closure, cold consumption (P2, P4-P6) | It already exists and already has a real native build. `lib/mkMaturinWheel.nix` builds a Rust extension wheel, `flake.nix` composes six command packages into `repoman-toolchain-core`, and `nix/consumer-module-check.nix` with `tests/test_store_consumer_e2e.py` already exercise a real consumer shell behind `VENDOMAT_E2E=1`. |
| The Neovim review application | Module contract, target defaults and overrides, editor integration, source correspondence (P1, P3) | It is a clean, small composition test for the module contract and the editor claims. |

A fixture written only to pass its own gates proves little.
The toolchain fixture supplies real closure size, real native output identity, and a consumer that already exists.
The Neovim fixture supplies the composition and application behavior the toolchain does not exercise.

The Neovim fixture includes:

- A small reusable command with a meaningful result format.
- A Neovim interface that invokes it and displays the result.
- An application module that composes those parts.
- A project consumer and a workstation consumer.
- An ordinary module export and a flake-backed export for delivery tests.
- One identifiable third-party dependency for inspection.
- A desktop publication host, Attic, and a cold laptop consumer.

The proof succeeds when:

1. The consumers select the application through native inputs and module configuration.
2. Required transitive inputs work through the documented delivery convention.
3. Components have useful defaults and can be disabled or configured independently.
4. The command works both directly and through the editor interface.
5. The application works in the normal editor and as a dedicated configured Neovim output.
6. A local checkout override changes development behavior without changing another consumer's accepted state.
7. The source store exposes the selected module and dependency source with correspondence information.
8. A deliberate inspection gap is visible and does not prevent valid publication.
9. A deliberate required-check failure prevents successful publication.
10. The published output matches the immutable consumer selection.
11. Attic serves the selected output and every closure path no trusted configured substituter already serves (D-ATTIC-SCOPE).
12. The cold laptop realizes and runs the output without building it, and the evidence names which substituter served each path.
13. Restored inspection storage preserves identity, and restored Attic storage preserves accepted substitution.

This proof does not require complete machine source coverage, an action registry, an offline rebuild, or Attic-only closure completeness.
It must demonstrate a useful application, rather than only a successful cache upload.
Items 1 through 9 use the Neovim fixture; items 10 through 13 use the `*man` toolchain fixture.

## 22. Implementation sequence

Each phase produces evidence before expanding the scope.
Choose implementation details through the smallest real fixture that can test the claim.

| Phase | Deliverable and gate |
| --- | --- |
| P0: environment and boundaries | Pin the tested tool versions; record hosts, target systems, storage, backup, and fallback policy |
| P1: native module contract | Compose the review command and editor interface using native modules; prove target defaults and overrides |
| P2: delivery and local development | Prove plain and flake-backed exports, transitive dependencies, and a reversible local checkout override |
| P3: useful inspection | Capture selected module and dependency source; expose readable views and an honest correspondence gap |
| P4: checked output | Bind checks and a reproducible output selection to an immutable consumer state; demonstrate a failed gate |
| P5: Attic consumption | Publish the output and the closure paths no trusted cache serves; prove the cold laptop performs no build and the declared fallback behavior holds |
| P6: evidence and recovery | Persist receipts; restore inspection source and Attic signing state; repeat the relevant checks |
| P7: machine integration | Compose native machine contributions; attach evidence to a native plan; exercise activation and its recovery limits |
| P8: one reviewed upgrade | Prepare and validate one native dependency diff; accept it without rebuilding or committing |
| P9: repeated-use helpers | Add justified scaffolds, optional release tasks, and cross-repository reports |
| P10: broader operation | Add scheduled proposals, broader capture, and full machine caching as measured needs justify them |

P1 through P6 establish the first complete application proof.
P1 and P3 use the Neovim fixture; P2 and P4 through P6 use the `*man` toolchain fixture (D-PROOF-SPLIT).
P7 expands the same model to persistent machine contributions.
The module contract must support those targets from the start, without requiring early machine-wide coverage.

If dependency delivery needs repeated manual declarations, address that in P2.
Do not hide it behind a new resolver.
If the cold consumer builds instead of substituting, fix output identity or cache coverage before adding automation.
If source correspondence cannot be established, reduce that inspection claim and preserve the useful known facts.

## 23. Boundaries and later opportunities

Vendomat does not initially provide:

- A new package manager, dependency lock, build identity, or source protocol.
- A general application runtime, agent framework, or context server.
- A universal action registry, UI schema, or typed dataflow engine.
- Recursive composition of arbitrary imported `devenv.yaml` files.
- A replacement for NixOS, Home Manager, Neovim, or systemd behavior.
- A custom deployment planner or rollback implementation.
- Mandatory release management, inferred versions, or automatic adoption of upgrades.
- Complete machine source coverage or full offline reconstruction claims.
- A custom cache implementation, secret manager, or destructive retention engine.

Later modules can add richer context retrieval, agent-assisted configuration, editor interfaces, or reusable workflow templates.
Source indexes can grow into structural search when concrete queries justify the extra state.
Voice interfaces and prediction can invoke established commands if those workflows become useful.

An archive-backed rebuild facility is also possible later.
It requires retained build inputs, a mechanism that supplies those inputs, and a controlled build proof.
Full offline reconstruction adds toolchain and bootstrap requirements.
Neither capability is required for the inspection store to be useful.

## 24. Invariants

1. A module remains traceable to native configuration, packages, and implementation files.
2. Native declarations and locks select dependencies; Vendomat introduces no competing authority.
3. A module can expose distinct contributions for devenv, Home Manager, NixOS, and applications.
4. Defaults remain overridable, and incompatible composition is reported explicitly.
5. Ordinary use of accepted outputs requires no live Vendomat service. Source inspection requires no Vendomat daemon either (D-SRC-ACCESS).
6. Local development overrides remain visible and separate from immutable publication selections.
7. Source inspection records both retained identity and correspondence to selected software.
8. Inspection gaps do not imply failed builds or prevent otherwise valid publication.
9. Source retention, rebuild proof, cache availability, acceptance, and activation remain separate facts.
10. A required check is a named devenv task. A failure, or a declared task that cannot run, blocks successful publication.
11. Publication identifies the exact selected output and verifies current availability for every closure path no trusted configured substituter already serves (D-ATTIC-SCOPE).
12. Cache publication never changes a consumer's selected dependencies by itself.
13. Current facts come from native authorities; historical validation evidence is retained.
14. Candidate acceptance is explicit and performs no rebuild, automatic commit, or deployment.
15. Machine operations use the pinned native devenv implementation and respect its recovery boundaries.
16. Source and binary retention follow their distinct purposes; deletion requires a separate proven policy.
17. New abstractions and automation must solve demonstrated problems in the module workflow.

## 25. Technical facts to prove before fixing interfaces

The architecture is decided; these implementation details remain evidence-driven.

Still open:

- The exact export convention that gives flake-backed modules self-contained transitive inputs.
- The smallest explicit input contract for a plain devenv repository, and how `inputs.<name>.devenv.config` compares with both.
- Whether a helper materially improves plain-repository delivery without duplicating dependency declarations.
- How a module declares its gate task set, and how a consumer appends to it, using only named devenv tasks.
- How a module expresses expected check coverage for behavior it enables, without new metadata.
- How a shared Neovim plugin and dedicated application reuse the same implementation without configuration collisions.
- Which native package metadata reliably identifies source and packaging patches for the initial dependencies.
- Whether the pinned devenv version can prefer a target-side substituter during machine apply.
- What Nix does when a configured substituter is unreachable.
- Whether the owner's machines use standalone Home Manager or the NixOS-module mode, and what rollback then does.
- Actual archive growth, closure sizes, and upload costs for the owner's selected applications and machines.

Resolved by primary documentation during the 2026-10-04 review, and no longer experiments:

- Profiles do not work with cross-project references. An imported project's `devenv.yaml` is not evaluated.
- Machine apply copies all outputs; it does not substitute by default.
- Attic skips upstream-signed paths by default, which D-ATTIC-SCOPE now wants.
- devenv provides no output-bound or module-declared check mechanism. Named tasks are the carrier.
- The Attic command-line interface provides no cache-presence query. Use `nix path-info --store` or an isolated store.

Resolved by existing code in this repository:

- The reviewed capture list is `vendor/python/*.toml` with `src/vendomat/catalog.py`.
- The plain-directory source store is `~/vendor` with the generated `.vendomat/sources.toml` map.

Measure the open items through the proof fixtures.
Keep proposed command syntax and schemas provisional until those proofs pass.

## 26. Primary technical references

These references support the native interfaces used by this design.
They do not replace tests against the pinned implementation.

- [devenv module imports](https://devenv.sh/composing-using-imports/)
- [devenv cross-project composition and its limits](https://devenv.sh/guides/polyrepo/)
- [devenv inputs and native locking](https://devenv.sh/inputs/)
- [devenv build outputs](https://devenv.sh/outputs/)
- [devenv task execution](https://devenv.sh/tasks/)
- [devenv Machines, plans, activation, and recovery](https://devenv.sh/machines/)
- [Neovim native package structure](https://github.com/neovim/neovim/blob/master/runtime/doc/pack.txt)
- [Nix source and runtime closure queries](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query)
- [devenv testing and `enterTest`](https://devenv.sh/tests/)
- [Nix substituter priority, trust, and fallback](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html)
- [Home Manager activation and profile modes](https://nix-community.github.io/home-manager/internals/activation.html)
- [Attic closure publication and upstream filtering](https://docs.attic.rs/reference/attic-cli.html)

This repository supplied further evidence during the 2026-10-04 review: `AGENTS.md`, `README.md`, `docs/DESIGN.md`, `docs/SOURCE_CATALOG.md`, `modules/devenv.nix`, `nix/testee.nix`, `gitman.toml`, `src/vendomat/catalog.py`, and `src/vendomat/plane.py`.

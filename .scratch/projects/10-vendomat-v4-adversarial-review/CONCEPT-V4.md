# Vendomat V4

## Composable devenv modules, inspectable source, and checked Attic distribution

**Date:** 2026-10-04.  
**Status:** Revised design for owner review. Accepted owner decisions remain fixed; named choices and prototype facts remain open.  
**Scope:** One owner's NixOS machines, development projects, and reusable personal applications.  
**Authority:** This document supersedes the earlier rewrite concepts and their implementation sequence.  
**Implementation status:** Design only. Examples describe intended contracts; they do not establish implemented Vendomat interfaces.

## 1. Purpose

Vendomat helps the owner compose a personal system from reusable devenv-based modules.
It makes modules easier to discover, configure, develop, inspect, validate, and distribute.

The foundation is ordinary Nix and devenv configuration, supported by native packages, scripts, and application configuration.
A module can provide a development environment, a command, an editor application, or a service.
A larger module can compose several smaller modules.

Vendomat adds two core capabilities around that composition:

- A source store that gives people and agents access to identifiable source for inspection.
- Checked publication of selected Nix outputs and their runtime dependencies to Attic.

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
    -> publish outputs to Attic
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
| Binary distribution | Attic is core; public caches remain available as fallback |
| Publication unit | An exact selected Nix output and its complete runtime closure |
| First workflow | Compose, develop, inspect, check, build, publish, and consume |
| Upgrade assistance | On-demand native proposals before scheduled sweeps |
| Releases | Declared tasks using native version metadata |
| Generation | Small scaffolds and repeated integration wiring |
| Runtime state | Ordinary files, directories, and native service state |

Accepted owner decisions for this review remain fixed.
`D-APP-SCOPE` keeps the Jujutsu–btrfs–bubblewrap application in a later module.
`D-NAMES` keeps new option and command names proposed.
`D-CHECK-OWNER` assigns default required checks to enabled modules and permits consumer-added gates.
`D-CHECK-GAP` makes a missing nonrequired relevant check visible without blocking publication by itself.
`D-CAPTURE` starts automatic capture with owned modules and listed direct dependencies, including the first-proof fixture.
`D-CAPTURE-GRAPH` includes direct native inputs and direct package dependencies of selected outputs; each capture-list entry names its graph.
`D-PROOF-GATE` lets the P1–P6 application proof finish before a separate P7 Machines fixture. P7 gates machine-readiness claims.
`D-OFFLINE-SOURCE` permits source lookup to report unavailable when the client cannot reach retained source. Local applications keep running; initial V4 needs no local source replica.
`D-REPO-BACKUP`, accepted 2026-10-06, scopes GitHub as a secondary location for the owner's local repository backups. That backup runs outside Vendomat. Vendomat does not depend on GitHub, and no Vendomat requirement names it. Attic objects are not backed up.

This is a new interface design, but current consumers exist.
Before replacement, inventory their delivery paths and either preserve, migrate, or explicitly retire each path.
The current repository delivers a devenv module through a NixOS package and machine manifest, and its consumer fixture imports that module.
No V4 interface inherits a legacy name solely for compatibility.
See the current [module](../../../modules/devenv.nix), [flake exports](../../../flake.nix), and [consumer fixture](../../../tests/fixtures/store-consumer/devenv.yaml).

## 3. Ownership and system model

Each authoritative fact has one owner.

| Owner | Responsibility |
| --- | --- |
| Module repository | Source, exported modules, package recipes, checks, and documentation |
| Consumer repository | Selected modules, configuration, overrides, and native locks |
| devenv | Project environments, module composition, tasks, outputs, and machine operations |
| Nix | Evaluation, derivations, builds, store identity, and substitution |
| NixOS | System configuration, host services, daemon trust, and system activation |
| Home Manager | User configuration and its activation |
| Native application | Its interface, runtime behavior, and application state |
| Source store | Retained source bytes and their inspection identity records |
| Attic | Cached Nix outputs, signing, and binary delivery |
| Version control | Reviewed source, configuration, and dependency history |
| Vendomat | Integration helpers, source lookup and capture, publication, reports, and evidence |

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

Upstream devenv currently does not evaluate an imported project's `devenv.yaml`.
Cross-project references also have profile limitations.
Supporting ordinary repositories therefore does not imply automatic recursive YAML composition.
See [devenv polyrepo behavior](https://devenv.sh/guides/polyrepo/).

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
The current checkout runs devenv 2.2.2; [Machines is new in 2.4 and experimental](https://devenv.sh/machines/).
The P0 fixture must prove a new pin and the transition of current consumer imports before machine behavior becomes an implementation assumption.

Machine definitions compose ordinary NixOS and Home Manager modules.
Project composition and machine composition share an operator interface while retaining distinct native configuration targets.

Upstream Machines provides build, plan, apply, status, and rollback operations.
A saved plan identifies built outputs; applying it uses those outputs without rebuilding.
Machines remains experimental, so upgrades require deliberate validation.
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

The native NixOS watchdog can restore the previous system after certain deployment failures.
It does not reverse application data changes.
Home Manager activation is separate, and NixOS rollback does not undo its files.
Report each activation result separately.
See the [upstream recovery boundaries](https://devenv.sh/machines/).

Cache publication and deployment remain distinct.
Publication proves cache availability; deployment proves an activation result.
The first machine integration must observe whether the native copy operation actually substitutes through Attic.
A successful direct copy from the build host is not evidence of Attic substitution.
P7 links application publication evidence to a native plan but does not claim that Attic holds the whole machine generation.

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
Client lookup access is a separate fact. A network outage does not change the retained source's capture status.

Prefer the selected revision over the latest upstream revision.
When a patched package differs from upstream, expose the patch information beside the source.
Do not silently describe an upstream checkout as the exact installed implementation.

### Read access

Provide read-only trees that people and agents can open with ordinary tools.
A lookup should identify the project or machine context, dependency, revision, and readable path.
The interface should expose provenance without requiring a special editor or agent runtime.

The first durable store may live on the build host and expose inspection access over the private network.
Under `D-OFFLINE-SOURCE`, lookup may report retained source unavailable from a disconnected client. That result does not mean the retained bytes are lost.
Initial V4 does not require a local source replica. Clients may keep local read views when a later need is established.
Ordinary application startup and project evaluation must not require a mounted remote inspection tree.

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
2. Capture direct dependencies on a consumer-maintained list automatically, including the first-proof dependency.
3. Capture deeper dependencies and system components when an inspection requests them.
4. Permit explicit holds and optional broader automatic capture.
5. Expand indexing only when real searches demonstrate its value.

The consumer-maintained list is capture policy, not a dependency declaration or lock.
Under `D-CAPTURE-GRAPH`, each entry names either a direct native input or a direct package dependency of a selected output, and names that graph.
Each entry must resolve to a selected native dependency before capture.
The P3 fixture must prove how the pinned tools expose both graphs, resolve listed entries, and report stale entries as gaps. It must not silently narrow the accepted scope if either graph cannot be resolved.

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

For a selected published output, retain its complete runtime closure in Attic.
This includes runtime dependencies previously obtained from public caches.
Here, runtime closure means Nix paths referenced by the selected output, not external services or mutable application data.
Begin with application and development outputs.
Add complete machine generations after measuring storage and transfer costs.

Complete closure retention makes those selected paths available without relying on another cache for their runtime dependencies.
It does not retain every build input or guarantee evaluation without upstream access.
It also does not create an offline copy on a disconnected laptop until the required paths are present there.

Attic supports closure pushes, but its upstream filter can omit paths signed by configured upstream caches.
Full closure publication must account for that filter and verify the resulting availability.
See the [Attic client reference](https://docs.attic.rs/reference/attic-cli.html).
Attic's documented default priority is 41, while the public NixOS cache is 40.
Test a lower Attic priority if Attic-first consumption is required; priority does not prove outage fallback.
See the [Nix substituter reference](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html).

Attic remains a binary cache.
Mutable application databases, notes, and development worktrees need their own storage and backup policy.

### Consumer policy

The intended preference is:

```text
existing local Nix output
    -> Attic
    -> configured public caches
    -> build from native inputs when allowed
```

Configure and test cache priority, unavailable-cache behavior, and build fallback through native Nix settings.
The priority alone is not proof that every failure takes the intended fallback path.

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
devenv can expose ordinary derivations through named outputs.
Vendomat consumes those outputs and their declared checks.
See [devenv outputs](https://devenv.sh/outputs/).

A publication selection records:

- An immutable consumer repository revision or an exactly recorded proposed change against one.
- Relevant native declarations and lock contents.
- Requested output attribute and target system.
- Active profiles and explicit input overrides.
- Effective module source identities.
- Evaluated derivation and resulting output paths.
- Nix Archive (NAR) hash and references of the checked selected output.
- Required checks and their inputs.

An input-addressed Nix output path follows its derivation; its NAR hash identifies the serialized output bytes.
Path equality alone cannot prove that the checked bytes are the bytes later served by Attic.
See the [Nix store path specification](https://nix.dev/manual/nix/2.25/protocols/store-path) and [store object metadata](https://nix.dev/manual/nix/2.35/protocols/json/store-object-info.html).
The selection must also freeze or reject effective inputs outside the consumer revision and locks, including host-delivered paths and local overrides.

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
    -> push output and complete runtime closure
    -> verify Attic availability
    -> record publication evidence
```

Source discovery and capture can run alongside this pipeline.
Their reports attach to the same selection.
An inspection gap does not block publication.
A source identity failure in an actual build input blocks the build's validation.
An identity failure confined to an inspection copy prevents claiming that copy is valid.

Enabled modules supply default required checks for their selected contributions.
Consumers may add required checks.
Required checks use the project's existing mechanisms.
Vendomat may declare which existing checks gate an output without inventing another test language.
Checks can run before or after the build according to what they exercise.
A failed required check blocks publication.
A declared required check that is missing or cannot run also blocks publication, with a distinct failure reason.
A documented relevant check outside the required set may be absent; report that nonblocking coverage gap separately.
The P4 fixture must prove how documented gaps are reported without pretending to infer every relevant test automatically.

The exact checked output is the output uploaded.
A cold substitution must match its recorded NAR hash before the receipt claims byte identity.
A producer's successful release alone does not prove a particular consumer's composition works.
Validate relevant consumer integration against the selected output.

A cold consumer must substitute the expected output during the foundation proof.
Verify complete closure availability separately from the success of the upload command.
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
Initial responsibilities include composition inspection, source lookup and capture, publication reports, and diagnostics.
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
| Attic objects | Rebuildable from the selected source and Nix inputs; not backed up |
| Attic signing state | Native secret storage and backup |
| Application data and human notes | Native application or user storage and backup |
| Temporary checkouts and local overrides | Development state with explicit cleanup |

### Backup scope

Each Vendomat state class needs a named storage owner and restore route.
Off-host copies of Vendomat state remain an open decision.
A local snapshot or a backup on the same host does not count as off-host.
Attic objects are not backed up. Selected source and Nix inputs rebuild them.
The owner's GitHub copy of local repositories is outside Vendomat (`D-REPO-BACKUP`).

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
Restore Attic signing state, rebuild Attic outputs from the selected source, then prove that an existing consumer accepts a selected output.
Restore evidence so prior results remain explainable.

These are separate recovery results.
A source restore need not demonstrate an offline build.
Attic objects are not restored from backup. Selected source and Nix inputs rebuild them.

## 20. Failure behavior

| Condition | Required behavior |
| --- | --- |
| Missing module input | Explain the native input requirement; do not invent a resolution |
| Conflicting options or bindings | Identify the conflict and require an explicit configuration choice |
| Unsupported requested target | Fail that requested composition and name the unsupported contribution |
| Selected source lacks a retained inspection object | Report the coverage gap; valid build and publication work may continue |
| Client cannot reach retained source or a local view | Report lookup unavailable from that client; keep the retained source status and local application use separate |
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

The first proof is a Neovim review application with a shared command-line tool.
It demonstrates composition, inspection, and distribution together.

The fixture includes:

- A small reusable command with a meaningful result format.
- A Neovim interface that invokes it and displays the result.
- An application module that composes those parts.
- A project consumer and a workstation declaration; P7 tests machine activation.
- An ordinary module export and a flake-backed export for delivery tests.
- One identifiable direct native input and one direct package dependency of a selected output for the P3 capture-list proof. One is the first-proof third-party inspection dependency.
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
11. Attic serves the complete runtime closure, including dependencies obtained from upstream caches.
12. The cold laptop substitutes and runs the output without building it.
13. Restored inspection storage preserves identity, and restored Attic storage preserves accepted substitution.

This proof does not require complete machine source coverage, an action registry, or an offline rebuild.
It must demonstrate a useful application, rather than only a successful cache upload.
P1 through P6 prove the application, inspection, and distribution path.
They do not prove NixOS service activation, Home Manager recovery, or Machines transfer.
A separate P7 machine fixture is required before making those claims.
Under `D-PROOF-GATE`, P1–P6 may finish the first application proof before P7. Machine-readiness claims wait for the separate P7 fixture.

## 22. Implementation sequence

Each phase produces evidence before expanding the scope.
Choose implementation details through the smallest real fixture that can test the claim.

| Phase | Deliverable and gate |
| --- | --- |
| P0: environment and boundaries | Pin a Machines-capable CLI and matching module; inventory current consumer paths; record hosts, target systems, storage, backup, and fallback policy |
| P1: native module contract | Compose the review command and editor interface using native modules; prove target defaults and overrides |
| P2: delivery and local development | Prove plain and flake-backed exports, transitive dependencies, and a reversible local checkout override |
| P3: useful inspection | Capture selected module and dependency source; expose readable views and an honest correspondence gap |
| P4: checked output | Bind checks and output bytes to a frozen selection; distinguish failed, missing required, and nonrequired coverage results |
| P5: Attic consumption | Publish the complete runtime closure; prove cold-laptop substitution and declared fallback behavior |
| P6: evidence and recovery | Persist receipts; restore inspection source and Attic signing state; rebuild Attic outputs from the selected source; repeat the relevant checks |
| P7: machine integration | Compose native machine contributions; attach evidence to a native plan; exercise activation and its recovery limits |
| P8: one reviewed upgrade | Prepare and validate one native dependency diff; accept it without rebuilding or committing |
| P9: repeated-use helpers | Add justified scaffolds, optional release tasks, and cross-repository reports |
| P10: broader operation | Add scheduled proposals, broader capture, and full machine caching as measured needs justify them |

P1 through P6 establish the first complete application proof, not the machine proof.
P7 expands the same model to persistent machine contributions.
The module contract must support those targets from the start, without requiring early machine-wide coverage.

If dependency delivery needs repeated manual declarations, address that in P2.
Do not hide it behind a new resolver.
If cold substitution fails, fix output identity or cache coverage before adding automation.
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
The Jujutsu–btrfs–bubblewrap application is one later reusable composition example, outside initial V4.
Its full Jujutsu commit ID, verified btrfs image, Nix runtime, bubblewrap process, and application state keep separate identities and recovery outcomes.
It does not add a Vendomat runtime, image cache, or deployment engine.
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
5. Ordinary use of accepted outputs requires no live Vendomat service.
6. Local development overrides remain visible and separate from immutable publication selections.
7. Source inspection records both retained identity and correspondence to selected software.
8. Inspection gaps do not imply failed builds or prevent otherwise valid publication.
9. Source retention, rebuild proof, cache availability, acceptance, and activation remain separate facts.
10. Required check failures block successful publication.
11. Publication identifies the exact selected output and verifies its complete runtime closure in Attic.
12. Cache publication never changes a consumer's selected dependencies by itself.
13. Current facts come from native authorities; historical validation evidence is retained.
14. Candidate acceptance is explicit and performs no rebuild, automatic commit, or deployment.
15. Machine operations use the pinned native devenv implementation and respect its recovery boundaries.
16. Source and binary retention follow their distinct purposes; deletion requires a separate proven policy.
17. New abstractions and automation must solve demonstrated problems in the module workflow.

## 25. Technical facts to prove before fixing interfaces

The architecture is decided; these implementation details remain evidence-driven:

- The exact export convention that gives flake-backed modules self-contained transitive inputs.
- The smallest explicit input contract for a plain devenv repository.
- Whether a helper materially improves plain-repository delivery without duplicating dependency declarations.
- Which profiles and overrides the pinned devenv version preserves across each supported consumption path.
- How a shared Neovim plugin and dedicated application reuse the same implementation without configuration collisions.
- Which native package metadata reliably identifies source and packaging patches for the initial dependencies.
- How the selected Attic configuration proves complete runtime closure availability despite upstream filtering.
- How checked NAR hashes and closure-member metadata compare with bytes served by Attic.
- How native machine plan application uses caches during transfer on the selected devenv version.
- How current machine-delivered imports and host paths move to the new pinned contract without hidden selection drift.
- How a fresh local consumer realizes and runs with Vendomat and Attic unavailable under its native input and fallback policy.
- Actual archive growth, closure sizes, and upload costs for the owner's selected applications and machines.

Measure these through the proof fixtures.
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
- [Attic closure publication and upstream filtering](https://docs.attic.rs/reference/attic-cli.html)

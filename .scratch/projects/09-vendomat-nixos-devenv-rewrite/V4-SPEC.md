# Vendomat V4 system specification

**Status:** Draft for owner review, 2026-10-04.  
**Authority:** [CONCEPT-V4.md](./CONCEPT-V4.md) defines V4. This specification makes its contracts testable.  
**Scope:** Specification only. Examples and names marked **proposed** are not implemented interfaces.

## 1. Decisions and proof gates

### Fixed V4 decisions

1. A reusable module exports focused native contributions. devenv composes projects and exposes Machines. NixOS and Home Manager own their own configuration and activation.
2. Consumer declarations and native locks select dependencies. Vendomat has no dependency resolver, second lock, general runtime, action registry, or deployment engine.
3. Source inspection and checked Attic publication are Vendomat's two core services. Source availability, source correspondence, build checks, cache availability, acceptance, and activation remain distinct facts.
4. The first complete proof is the Neovim review application, shared command, project consumer, workstation consumer, desktop publisher, and cold laptop.
5. Local module use does not need a Vendomat service or Attic. The first publication path requires an immutable selection.
6. Machine deployment uses one pinned and tested devenv Machines implementation. A native plan selects the outputs to apply.
7. Vendomat initially deletes neither inspection source nor Attic objects automatically. Each other state class has its own retention and restore result.

These decisions come from V4 §§1–3, 8–10, 13–15, 19, 21, 23–24.

### Facts that require proof before an interface is fixed

V4 §25 leaves the flake export convention, plain repository input contract, profile behavior, Neovim packaging, source metadata, Attic closure verification, Machines transfer behavior, and storage costs to fixtures. A guide must cite the pinned tool versions and results. This specification defines the required outcome without selecting an unproved command or schema.

### Accepted application scope decision

**D-APP-SCOPE, accepted 2026-10-04:** The Jujutsu–btrfs–bubblewrap application is a later reusable module outside initial V4. Its case below shows what native composition can express. Its requirements remain conditional and do not gate V4's Neovim proof. Its contract does not change Vendomat's core.

**D-NAMES, accepted 2026-10-04:** This session specifies behavior first. All new names remain proposed. The concept says a special filesystem and general application runtime are not initially required (V4 §§19, 21, 23).

## 2. System boundary and authoritative state

| Fact or state | Authority | Vendomat role |
| --- | --- | --- |
| Module source, exports, package recipes, checks | Module repository and version control | Inspect and report |
| Selected module inputs, options, profiles, overrides, locks | Consumer repository and native locks | Explain effective selection |
| Project composition, tasks, outputs, machine plan | Pinned devenv | Invoke and link evidence |
| Derivations, output paths, local store, substitution | Nix | Check identities and consumption |
| Host service, trusted keys, system generation | NixOS | Attach checks and report native status |
| User files and activation | Home Manager | Report its status separately |
| Process behavior and mutable data | Application | Inspect and check selected output |
| Retained source and identity records | Source store | Own capture and lookup |
| Cached Nix paths and signing state | Attic | Publish and verify |
| Past checks, uploads, failures | Immutable evidence | Own receipt and logs |

Vendomat may cache evaluated facts for speed. Each cached fact names its native source and can be refreshed. No cached fact selects a dependency or overrides a native lock. Ordinary project entry, editor startup, and accepted output execution work without a live Vendomat service, mounted inspection tree, or Attic upload. V4 §§3, 9, 11, 15, 24.

## 3. Module contract and exports

A module contract names its source revision, supported targets, exported files or attributes, required native inputs, options, default behavior, component overrides, checks, and side effects. A repository may export several modules. A consumer imports only the needed contribution, not the author's whole development environment.

| Contribution | Contract |
| --- | --- |
| devenv module | Native Nix module for packages, tasks, processes, and outputs. It declares its required inputs and exact delivery path. |
| Package or application | Nix derivation or devenv output. It names its target system and checks. |
| Editor interface | Native Neovim files and configuration. It uses the selected command package by explicit path. |
| Home Manager module | Native user options, package references, files, and user services. It names the user and home assumptions. |
| NixOS module | Native host options, packages, services, storage, and trust settings. It names host requirements. |
| Operation | Native script or function with arguments, result, exit behavior, and side effects at real integration boundaries. |
| Inspection guidance | Readable source links and lookup guidance; no mandatory agent protocol. |

Typed Nix options define configurable behavior. Component defaults activate only after a consumer enables the relevant target contribution. Consumers can disable or override components independently. Nix module merging and explicit assertions resolve or report shared settings. A conflicting key binding or unsupported target fails the requested composition with a useful diagnostic. An import alone does not activate a system or user configuration. [devenv imports](https://devenv.sh/composing-using-imports/), [devenv options](https://devenv.sh/reference/options/), V4 §§4–7.

The first Neovim module exports one shared review implementation, one command with a defined result format, one normal-editor plugin contribution, and one dedicated configured Neovim output. The two editor forms must use the same packaged command and isolate their configuration. An integration check must exercise a representative editor command. V4 §§6, 21.

### Native delivery examples

The following **proposed** names `review.enable`, `review.command.enable`, and `review.editor.enable` describe the contract. They are not current devenv or Vendomat options. The native `inputs`, `imports`, and `machines` forms follow current devenv documentation. The fixture must confirm the proposed module exports before using these examples as instructions. [devenv imports](https://devenv.sh/composing-using-imports/), [Machines](https://devenv.sh/machines/).

An ordinary repository consumer can select a local module without publication:

```yaml
# devenv.yaml — example consumer; review.* names are proposed
inputs:
  review:
    url: path:../review-module
    flake: false
imports:
  - review
```

```nix
# devenv.nix — example consumer; review.* names are proposed
{ ... }: {
  review.enable = true;
  review.command.enable = true;
  review.editor.enable = false;
}
```

The ordinary import reads the imported `devenv.nix`; remote imports do not recursively evaluate that repository's `devenv.yaml`. The consumer supplies any native inputs the export cannot carry. Cross-project references have profile limits. [devenv polyrepos](https://devenv.sh/guides/polyrepo/), [devenv inputs](https://devenv.sh/inputs/).

A machine can select local native contributions with the pinned Machines interface. The paths and `services.review` and `programs.review` options below are **proposed** module exports. This example illustrates target separation, not a tested V4 fixture:

```nix
# devenv.nix — proposed fixture, subject to pinned Machines evaluation
{ ... }: {
  machines.workstation = {
    system = "x86_64-linux";
    target.host = "root@workstation.example";
    nixos = {
      imports = [ ./modules/review/nixos.nix ];
      programs.review.enable = true;
    };
    home-manager = {
      imports = [ ./modules/review/home-manager.nix ];
      home.username = "owner";
      home.homeDirectory = "/home/owner";
      programs.review.enable = true;
    };
  };
}
```

Machine system and user roles are separate activations. The fixture must prove that the local module paths and chosen options evaluate under the pinned devenv version. [devenv Machines](https://devenv.sh/machines/).

### Flake-backed exports

A flake-backed module may carry modules, packages, and native transitive input references. It must pass required inputs to its implementation explicitly. A lock entry does not enable a module. The **exact export convention remains a P2 experiment**. Do not prescribe a flake output attribute, follow rule, or generated input wrapper until a plain and a flake-backed consumer prove the same conceptual contract. [devenv inputs](https://devenv.sh/inputs/), V4 §§8, 25.

## 4. Native configuration, locks, and exact selections

The consumer records input locations, imports, options, active profiles, local overrides, and native lock files. The effective consumer lock controls transitive input selection. The selected Nix output path, not a module name, tag, or Jujutsu change ID, is the binary distribution identity. A local checkout override is visible and reversible. It does not change a second consumer's accepted state. V4 §§8–9, 14, 24.

An exact publication selection contains:

1. An immutable consumer revision, or an exact proposed native diff against a recorded base.
2. The relevant declarations and lock contents, requested attribute, target system, active profiles, and overrides.
3. Module source identities and the evaluated derivation identity.
4. The realized output path or paths and the checks bound to those outputs.

The selection is frozen before checks. Publication aborts if evaluation, locks, derivation, or output path changes before upload. The first publication path refuses a mutable checkout as proof of an immutable selection. A future development-cache mode would record an exact source snapshot. Native Nix evaluation remains the authority for derivations and paths. V4 §14.

## 5. Source inspection

The source store supports discovery, capture, and indexing as separate operations. It defaults to retaining owned modules and important direct dependencies. It discovers broader dependency and machine source without promising to capture everything. It captures deeper source on request or under an explicit hold. It may regenerate indexes and read views. V4 §§11–12.

Each capture record identifies the locator, ecosystem, native revision or archive hash, hash algorithm and hashed representation, selected consumer context, retained object, capture result, packaging patches or transformations, and known gaps. It labels correspondence as exact selected source, selected source with packaging changes, upstream reference, or unresolved. Capture status separately labels retained, identified but uncaptured, unavailable, or unidentified. A retained upstream checkout is not automatically the installed source. [Nix store closure query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query), V4 §11.

The store gives people and agents a read-only tree and provenance record. An explicit source override changes native inputs; reading an inspection tree does not. A missing inspection source reports a gap but does not invalidate a valid artifact check. A mismatched inspection copy loses its correspondence claim. A source mismatch in a required build input fails build validation. Source retention is durable outside ordinary local Nix garbage collection. V4 §§11, 14, 20.

The durable store normally resides on the build host and offers read access over the private network. A client may keep a derived local read view. Project evaluation and application startup cannot depend on a mounted remote inspection tree. V4 §11.

Runtime and derivation graphs support different inventory questions. A runtime closure lists referenced output paths; it does not list every build input or prove a complete source map. [Nix store closure query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query).

## 6. Checks, Attic publication, and cold consumption

devenv tasks order project-local stages and invoke native commands plus narrow Vendomat helpers. Each task declares prerequisites and failure conditions. A helper validates inputs and side effects; task order or an existing path alone does not prove check success. [devenv tasks](https://devenv.sh/tasks/), V4 §16.

For one frozen selection, the checked publication sequence is:

```text
evaluate selected output
  → run declared pre-build checks
  → realize exact output
  → run declared artifact and consumer integration checks
  → confirm derivation and output identity
  → publish output and runtime closure
  → verify current Attic availability for every closure path
  → retain receipt
```

Missing relevant checks appear as a coverage gap. A failed required check or build blocks a success receipt and publication success. A failed upload leaves the local output usable. A partial closure upload records partial progress and can retry against the same selection. A successful upload command alone cannot establish complete availability. V4 §§14, 20, 24.

Attic distributes Nix store paths and closure members. Its default upstream filter may skip paths signed by an upstream cache. The publication policy must account for that filter. A verification fixture must query or substitute **every** required runtime path from Attic in an isolated store with other caches and builds disabled. It must include paths first fetched from a public cache. This tests an Attic-only closure claim; normal consumers may still use public caches as fallback. [Attic CLI](https://docs.attic.rs/reference/attic-cli.html), [Attic tutorial](https://docs.attic.rs/tutorial.html), [Nix closure query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query).

The first proof publishes application and development outputs. Publish complete machine generations only after measuring their closure size and transfer cost. A machine plan may still link to checked application outputs before full-generation caching enters scope. V4 §§13, 22.

A cold laptop fixture starts without the selected output. It consumes the expected output path from Attic and runs the application without a build. Its logs identify the cache source. The fixture tests local-store preference, Attic priority, public-cache fallback, and permitted build fallback separately. Nix substituter priority, signing trust, and `fallback` settings are native policy; priority alone does not prove outage behavior. [Nix configuration](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html), V4 §13.

NixOS owns the Attic service, private-network access, consumer trusted public key, and build-host push credential placement. A receipt stores no push token, signing secret, or unrestricted environment dump. Attic's documented push accepts Nix store paths. Therefore, a btrfs subvolume, application database, user notes, or editable worktree outside the store needs a separate transfer policy. [Attic CLI](https://docs.attic.rs/reference/attic-cli.html), V4 §§13, 19.

## 7. Machine plans, activation, and recovery

Pin the devenv executable and its module implementation to one tested release or revision with Machines support. Machines is experimental. The native interface builds a plan without target activation; apply uses saved outputs without rebuilding and rejects a stale target or generation. Vendomat links its selection, checks, publication receipt, and source report to the native plan ID and paths. It creates no alternate plan. [devenv Machines](https://devenv.sh/machines/), V4 §§10, 25.

Before apply, verify that the native plan still selects the checked paths and that any required cache paths remain available. If the plan is stale, prepare a new plan and rerun or reuse checks only when their recorded inputs match. Report native status after activation. A direct build-host copy does not count as Attic substitution; the transfer path needs its own observation in P7. [devenv Machines](https://devenv.sh/machines/).

NixOS builds system generations and activates them through native scripts. A whole-system candidate check may require a virtual machine. Bubblewrap cannot stand in for that activation or VM test. [NixOS manual](https://nixos.org/manual/nixos/stable/). Machines can recover some NixOS activation and health-check failures, but cannot repair an early boot failure or undo application data. It activates Home Manager afterward; a Home Manager failure can leave NixOS applied. Home Manager has separate activation and generation behavior. [devenv Machines](https://devenv.sh/machines/), [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html).

Track these rollback and retention domains separately:

| Domain | Native rollback or restore | Protected state |
| --- | --- | --- |
| NixOS system | Native generation and Machines recovery, subject to watchdog limits | Target generations, roots, plan outputs |
| Home Manager | Native user activation or generation recovery; no Machines automatic rollback | User profile and affected files |
| Application | Application-defined migration and backup | Per-instance mutable data |
| btrfs source image | Re-select a retained, verified image or rematerialize the pinned commit | Commit objects, image and mapping record |
| Inspection source | Restore archive and identity records, then verify correspondence | Source objects, holds, records |
| Attic | Restore objects and signing state, then prove consumer substitution | Cache objects and trust material |
| Evidence | Restore receipts and failure logs | Historical records |

The btrfs row applies only if the conditional application enters scope. A btrfs snapshot is not a backup by itself. [btrfs subvolumes](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html). Source and binary retention may differ. An unreachable machine gives unknown recovery needs; it does not authorize deletion. Initial V4 performs no automatic source or Attic deletion. V4 §19.

## 8. Evidence and reviewed changes

A publication receipt records selection identity, native lock identity, output and closure paths, named checks with inputs and results, source coverage link, Attic target, upload result, current availability check and time, and any machine plan ID. Failure evidence records the failed stage and partial side effects. Reports use separate fields for retained source, source correspondence, archive-backed rebuild proof, check pass, current cache availability, dependency acceptance, and activation. A signature proves acceptance by a configured cache key; it does not prove independent reproduction. V4 §§14–15, 20.

An on-demand upgrade starts from a known base in an isolated checkout. Native tooling updates declarations and locks. Vendomat checks the exact proposed diff, publishes selected outputs, and presents the diff and evidence. Acceptance checks that base files still match and outputs remain available. It applies the validated native diff only. Version control records the change; native deployment applies it later. A cache hit never accepts a proposal. V4 §17.

Optional release tasks use native version metadata and immutable tags. Failed gates cannot report release success. Scheduled sweeps and scaffolds follow the first proof; they do not select or deploy candidates automatically. V4 §§18, 22.

## 9. Conditional Jujutsu–btrfs–bubblewrap composition case

### Purpose and ownership

A reusable application module composes three focused contributions: Jujutsu selects a commit, a btrfs adapter materializes its files, and bubblewrap runs those files with a matching Nix runtime. The application contract states admission, instance identity, and mutable state behavior. A devenv contribution supplies project tools, checks, and a local run. A NixOS contribution supplies persistent host service, storage, permissions, and supervision. A Home Manager contribution is optional for a user launcher or user service. Vendomat inspects source, gates selected Nix outputs, publishes their runtime closures, and records evidence. It does not own the application's runtime state or schedule arbitrary applications.

The following **proposed, illustrative** configuration shows the consumer interface. The reusable `revisionApp` module would import its focused Jujutsu, btrfs, and bubblewrap contributions internally. A prototype must establish the actual options and paths. No name here is an established devenv, NixOS, or Vendomat API.

```nix
# devenv.nix — proposed local project consumer
{ ... }: {
  imports = [ ./modules/revision-app/devenv.nix ];

  revisionApp = {
    enable = true;
    repository = ./.;
    runtime.output = "revision-runtime";
    limits.running = 3;
    limits.queued = 5;
  };
}
```

```nix
# devenv.nix — proposed host composition with native Machines syntax
{ ... }: {
  machines.workstation = {
    system = "x86_64-linux";
    target.host = "root@workstation.example";
    nixos = {
      imports = [ ./modules/revision-app/nixos.nix ];
      services.revisionApp = {
        enable = true;
        stateRoot = "/var/lib/revision-app";
        limits.running = 3;
        limits.queued = 5;
      };
    };
  };
}
```

The requested revision is an operation input, not a mutable Nix option. The operation resolves it to one full commit ID before admission. The machine example deliberately uses native `machines` and a proposed NixOS service option; it does not introduce a `vendomat.*` option or a new deployment plan. [devenv Machines](https://devenv.sh/machines/).

Jujutsu documents that a change ID may refer to several commit versions after rewriting or divergence. A commit ID identifies one commit. The application resolves the requested revset to **exactly one full commit ID** before any materialization or queue admission. An empty or multi-commit result fails. A later change-ID movement cannot change an accepted request. [Jujutsu glossary](https://github.com/jj-vcs/jj/blob/main/docs/glossary.md), [Jujutsu templates](https://github.com/jj-vcs/jj/blob/main/docs/templates.md).

### Materialization contract

The adapter reads the exact commit tree from Jujutsu. It creates a new writable staging subvolume on a btrfs filesystem, writes the selected files and metadata, verifies them, then publishes a read-only subvolume for execution. A read-only snapshot of the staged subvolume is one possible implementation. A Jujutsu commit is **not** a btrfs snapshot: a btrfs snapshot copies another btrfs subvolume's initial contents. [Jujutsu file commands](https://docs.jj-vcs.dev/latest/cli-reference/), [btrfs subvolume commands](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html).

The mapping record binds repository identity, full commit ID, tree or file manifest identity, materialization format version, btrfs filesystem and subvolume identity, read-only status, creation result, and verification result. The commit ID identifies selected source; the btrfs UUID identifies one materialized storage object. Neither identifier substitutes for the other. A second materialization of the same commit may have a different btrfs UUID. The adapter must handle regular files, paths, executable bits, and symlinks consistently; it must reject unsupported entries, path escapes, and unresolved conflicts rather than claim exact correspondence. Jujutsu can record conflicts inside commits and materialize markers in a working copy. [Jujutsu conflicts](https://docs.jj-vcs.dev/latest/conflicts/).

Publication of the image is atomic for readers: a failed or incomplete stage never becomes runnable. A reused image must pass mapping and read-only checks. Retain the Jujutsu commit object or an independently verified source representation for any claimed rematerialization. An image alone proves neither that its commit remains fetchable nor that it can be regenerated. A running instance pins its image against cleanup. A snapshot is local storage and needs its own backup or transfer plan. [btrfs subvolumes](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html).

### Matching Nix runtime and sandbox

The runtime selection evaluates the native Nix declarations and lock at the pinned commit, or uses a previously verified output mapped to that exact selection. The record binds full commit ID, relevant native lock contents, target system, derivation, and output paths. It never silently uses the current branch's runtime for an older commit. Missing or incompatible runtime inputs fail the request. Local realization can use the local Nix store and native build policy without Attic or Vendomat. Attic may distribute the runtime output closure, **not** the btrfs image or writable state. [Nix closure query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query), [Attic CLI](https://docs.attic.rs/reference/attic-cli.html).

Bubblewrap runs one application's selected process tree. Its mount policy exposes the read-only image, required Nix runtime paths, and one instance's writable state. It hides unrelated host homes, source archives, credentials, and other instance state. The module declares network, device, process, and interprocess communication access explicitly. The wrapper validates the image and runtime identities before launch and records what it actually mounted. The chosen host must support the required namespace setup; it must fail closed if required isolation cannot be established. Bubblewrap provides bind mounts and namespaces for a process; it does not build or activate a NixOS system. [bubblewrap options](https://github.com/containers/bubblewrap/blob/main/bwrap.xml), [NixOS manual](https://nixos.org/manual/nixos/stable/).

Each instance receives a unique durable instance ID and a distinct writable state directory. Several commits and several instances of one commit can run at once. State survives or expires under the application's declared policy, independently of image, source, Nix output, and system generation retention. A NixOS rollback does not undo writes in an instance directory. The process supervisor may use systemd instance units and resource controls. Those units do not by themselves define an application-wide running and queued admission limit. [systemd service templates](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml), [systemd execution directories](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml), [systemd resource controls](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml).

### Admission and concurrent runs

The application contract exposes configurable positive running and nonnegative queued limits. `limits.running` and `limits.queued` above are **proposed names**. The counts apply across all revisions of this application on one host. Admission atomically starts a request when a running slot exists, queues it when only a queue slot exists, or rejects it with a capacity result. A queued record pins the full commit ID and runtime selection; it never resolves a mutable revset again. Cancellation, process exit, failed preparation, and supervisor restart must not double launch or exceed limits. Queue durability, ordering, and count ownership belong to this later module's design and prototype. Do not infer them from systemd's unit job queue.

The application declares whether each instance is a user or system service. NixOS supplies its host storage and service policy; Home Manager may supply a user-facing launcher. The devenv contribution permits a local run with native inputs and a writable local state path. The same exact commit/runtime/image checks apply. No local run contacts a Vendomat daemon or requires an Attic push.

### Conditional fixture and failure probes

An application fixture must run two different commits and two instances of one commit concurrently. It must show the same pinned commit and runtime in each instance report, distinct writable state, and a read-only image. It must fill running and queued capacity, reject the next request, and show a queued request start after a slot opens. It must reject ambiguous revisions, conflicted or unsupported trees, altered image mappings, missing runtime closure paths, and sandbox setup failure. It must restart the host supervisor during queued work without duplicate execution. It must restore source, image, Nix output, and instance state as separate results. These gates apply only if the owner includes this application in V4 scope.

## 10. Unresolved questions and experiments

| ID | Question or fact | Needed evidence or decision |
| --- | --- | --- |
| D-APP-SCOPE | Later reusable module outside initial V4. | Accepted owner decision, 2026-10-04. |
| D-NAMES | Specify semantics; keep new names proposed. | Accepted owner decision, 2026-10-04. |
| Q-CHECK-OWNER | Who declares the required checks for a selected output? | Owner decision; test module and consumer composition. |
| Q-CHECK-MISSING | Does an absent relevant check remain a visible coverage gap, as V4 §14 states, or become a publication blocker? | Owner decision; blocking would amend V4. |
| Q-CAPTURE | Which direct dependencies qualify for automatic capture at first use? | Owner decision; test discovery and capture separately. |
| Q-QUEUE | How does the later module implement its limits, queue ordering, and restart behavior? | Later owner decision and concurrent fixture. |
| Q-APP-STATE | How long must stopped instance state and queued requests remain? | Owner retention policy and restore fixture. |
| Q-APP-NET | Which network and device access does the first application need? | Application threat model and bubblewrap host probe. |
| P-DELIVERY | Which flake export passes transitive inputs, what must a plain consumer declare, and does a helper remove repeated declarations? | P2 plain and flake-backed fixtures; compare a small helper against explicit native files. |
| P-PROFILES | Which profiles and overrides survive each consumption path? | P2 matrix on pinned devenv. |
| P-EDITOR | How do normal and dedicated Neovim forms share files without collisions? | P1 integration fixture. |
| P-SOURCE | Which native metadata maps the first dependencies to selected source and patches? | P3 capture fixture with an intentional gap. |
| P-ATTIC | Which Attic configuration and check prove all runtime paths are available? | P5 isolated-store substitution test. |
| P-MACHINES | Does the pinned Machines transfer actually substitute through Attic? | P7 target transfer trace. |
| P-STORAGE | What are archive growth, closure size, and transfer costs? | Measure P3–P7 outputs before broad retention. |
| P-IMAGE | How does the adapter preserve tree entries and reject conflicts safely? | Btrfs fixture with files, modes, symlinks, conflicts, and failure injection. |
| P-SANDBOX | Which bubblewrap mount and namespace policy works on the selected NixOS hosts? | Host test, including denied host access and setup failure. |

No row here authorizes a new Vendomat resolver, lock, runtime, registry, or deployment engine. V4 §25 remains the authority for the first eight technical gates.

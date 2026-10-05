# V4 adversarial review

**Review date:** 2026-10-04. **Scope:** concept, specification, requirements, and current repository evidence.  
**Baseline:** [BASELINE.md](./BASELINE.md) records the exact copied bytes. Locations below link to the unchanged source files in project 09.  
**Status:** Design review. No V4 implementation or implementation guide is part of this review.

## Verdict and simpler comparison

The smallest credible V4 keeps native module declarations and locks as the only selection authority. It adds two narrow facilities: verified source retention for inspection and checked publication evidence for selected Nix outputs. This is a coherent goal. The current documents still overclaim what a path identifies, what the first Neovim proof covers, and what the present devenv pin can run.

A native-only trial can compose modules with devenv, build with Nix, push a closure with Attic, and deploy with Machines. A short task and a human checklist could record checks and source links. Vendomat earns its extra state only if a repeat fixture shows that native commands alone fail to give durable source correspondence, an exact check-to-output binding, or an auditable Attic-only closure claim. The review keeps the proposed source store and publication helper because those are V4 goals. It does not assume a daemon, registry, mirror for every dependency, or second deployment controller.

| Component | User need and native owner | Smallest useful contract, state, and recovery | Failure, local use, and simplification test |
| --- | --- | --- | --- |
| Module composition | Reuse commands and settings; devenv, NixOS, Home Manager, and the module repository own their targets. | Import a focused native contribution with documented inputs, defaults, and checks. Native files and locks retain selection. | A missing input or conflicting option fails the requested target. A local consumer can evaluate and run without Vendomat or Attic. Test whether a plain import is enough before adding a wrapper. |
| Neovim application | Prove one shared command and editor interface; Neovim owns editor loading. | One command package, plugin contribution, and optional dedicated output. The consumer owns editor settings. | Test command identity and configuration isolation. It proves the application path, not system activation. Keep editor wiring in its module. |
| Source inspection | Read the selected source later; repositories, locks, and package metadata own source facts. | Retained bytes, identity, correspondence, and a readable view. Back up bytes and records; rebuild views. | A source outage reports a gap. Project evaluation and local execution continue. Test whether existing Git archives plus a small manifest meet the need before adding indexes or a service. |
| Check and publication evidence | Know which checks passed for which output; native check tools and Nix own execution and builds. | A frozen selection, effective required set, result references, output path and NAR hash, and an Attic verification result. Back up the receipt. | Failed or missing required checks block success. An absent nonrequired check remains a visible gap. A local run does not depend on publication. Do not add a second test runner. |
| Attic delivery | Reuse built outputs across machines; Attic and Nix own cache paths and trust. | Push the selected output closure and prove each path is available from Attic alone. Attic owns objects and signing state. | A partial push remains partial. Public-cache fallback and local builds follow Nix policy. Vendomat needs no cache protocol. |
| Machine operation | Review and apply system and user configuration; Machines, NixOS, and Home Manager own plans and activation. | Link checked paths and evidence to the native plan. Native targets retain generations and status. | A stale plan uses native rejection. Direct copy is not an Attic hit. No Vendomat apply or rollback path is needed. |
| Reviewed upgrades and release tasks | Propose a native diff and publish exact candidates; native update tools and version control own changes. | An isolated diff and validation record, only when offered after the core proof. | Failed proposals leave accepted files intact. Native tasks can cover release work. Keep scheduled sweeps and scaffolds outside the first proof. |
| Later Jujutsu application | Run pinned revisions with isolated state; Jujutsu, btrfs, bubblewrap, and systemd own their operations. | One full commit ID, verified image mapping, matched Nix runtime, instance state, and admission policy in a separate module. | Each recovery domain fails independently. No new Vendomat runtime or deployment plan follows from this example. |

## Severity-ranked findings

### High — F01: The current devenv pin cannot prove Machines, and existing consumers need a transition

**Location:** Baseline [concept §2 and §10](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L67), [spec §§1, 3, 7](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L11), and `V4-MACH-001`. Current [devenv.lock](../../../devenv.lock#L3), [module](../../../modules/devenv.nix#L42), [flake exports](../../../flake.nix#L317), and [consumer fixture](../../../tests/fixtures/store-consumer/devenv.yaml#L10) are the counterexample.

**Failure scenario and consequence:** The installed CLI reports `devenv 2.2.2+b8030c5`; the upstream Machines interface is new in 2.4. A guide that starts with the present pin cannot run its machine steps. The current NixOS module also installs a machine manifest and central overlay, while V4 proposes new native imports and no required `vendomat.toml`. A new contract can silently break active consumers. The repository's [AGENTS.md](../../../AGENTS.md#L3) also assigns composition and workspace orchestration outside Vendomat. [devenv Machines](https://devenv.sh/machines/) documents the new interface and its experimental status.

**Correction:** Keep V4's greenfield interface freedom, but require a P0 inventory and an explicit preserve, migrate, or retire outcome for each live consumer path. Pin one matching CLI and module revision with Machines support. Keep machine operation native. **Evidence:** Run the current consumer fixture before and after the pin change, then evaluate and plan one machine fixture on the new pin. Record the transition and tool identities. No current machine claim is proven by the online documentation alone.

### High — F02: The output path does not identify the checked bytes by itself

**Location:** Baseline [concept §14](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L565), [spec §4](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L127) and [§6](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L154), and `V4-SEL-006–007`, `V4-CACHE-001`.

**Failure scenario and consequence:** An input-addressed Nix output path follows the derivation, while its NAR hash records its serialized bytes. Path equality between a check and an upload therefore cannot alone prove byte equality. A cache could serve different bytes for that path, or a receipt could omit the distinction. [Nix store path calculation](https://nix.dev/manual/nix/2.25/protocols/store-path) and [store object metadata](https://nix.dev/manual/nix/2.35/protocols/json/store-object-info.html) state these separate identities.

**Correction:** Record the checked output path, NAR hash, derivation, and references. Compare the Attic-served object after cold substitution; record closure-member hashes when making a complete closure evidence claim. Do not call a path a content hash. **Evidence:** Inject a same-path, different-hash fixture or a mismatched cache metadata fixture. It must fail the exact checked-byte claim.

### High — F03: A frozen repository revision does not freeze every effective input

**Location:** Baseline [concept §14 selection list](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L571), [spec §4](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L127), `V4-SEL-003–007`. The current [machine manifest lookup](../../../modules/devenv.nix#L47) and [local override guidance](../../../README.md#L351) show inputs outside the consumer commit.

**Failure scenario and consequence:** A consumer commit and lock stay fixed while `/run/current-system/sw/share/vendomat/machine.json`, a local path input, or a local override changes. Checks then describe one evaluated graph and upload another. The current module reads host state during evaluation, so this is a real project constraint.

**Correction:** Freeze or reject every effective non-lock input that affects the selected derivation. Record host-delivered store paths, profiles, and overrides with the selection. Treat a dirty local tree as development state unless its bytes are captured as an exact immutable snapshot. **Evidence:** Change a machine-delivered path or local input after checks; publication must reject drift.

### High — F04: Check coverage examples contradict required module defaults

**Location:** Baseline [spec §6](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L154), `V4-CHK-005`, `V4-CHK-008`, `V4-CHK-011–015`, and [first-proof checks](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L204).

**Failure scenario and consequence:** The requirements say the enabled editor contribution supplies a default required editor check. They also use removal of its editor integration check as an example of a nonrequired coverage gap. The same removal would be either a missing required gate or a nonblocking gap. Publication cannot classify it consistently. No native tool can infer every relevant but undeclared test from arbitrary behavior.

**Correction:** Bind the enabled module's declared required set to the frozen selection. A failed gate and a declared required gate that is absent or unavailable each block success, with distinct reasons. A documented relevant check outside that set is a visible nonblocking gap. Make gap discovery an explicit review or module documentation input until the P4 fixture proves a better mechanism. Do not create a second test language; the current repository verifies through [Testee](../../../testee.toml#L1). **Evidence:** Three fixtures must show separate failed, missing-required, and nonrequired-gap results.

### High — F05: The first Neovim proof cannot establish machine and service claims

**Location:** Baseline [concept §21](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L840) and [§22](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L874), [spec §1](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L7) and [§7](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L183), `V4-PROOF-001–008` and `V4-MACH-003–013`.

**Failure scenario and consequence:** A project and editor fixture can pass while a NixOS service fails to activate, Home Manager changes user files, or a Machines plan becomes stale. P1–P6 prove the application and cache path. They cannot certify the promised machine path. [Machines](https://devenv.sh/machines/), [NixOS](https://nixos.org/manual/nixos/stable/), and [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html) assign different operations to those targets.

**Correction:** State the Neovim proof's limit. Require a distinct P7 machine fixture with a real service, user activation, plan, transfer trace, and recovery observation before making machine-readiness claims. Whether P7 joins the first release gate remains an owner question. **Evidence:** P7 must run on the pinned Machines version, including a Home Manager failure after system success.

### High — F06: Attic's upstream filter and default priority can defeat the claimed cache path

**Location:** Baseline [concept §13](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L509), [spec §6](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L154), `V4-CACHE-002–005`, `V4-CACHE-009–011`.

**Failure scenario and consequence:** Attic can skip paths signed by the configured upstream key. Its documented default cache priority is 41, while `cache.nixos.org` is 40. A normal cold laptop may therefore fetch public-cache paths first and still look successful, although Attic lacks closure members. [Attic CLI](https://docs.attic.rs/reference/attic-cli.html) and [Nix substituter policy](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html) document both behaviors.

**Correction:** Prove every selected runtime-closure path from Attic alone in a fresh isolated store with builds and public caches disabled. Include a dependency first obtained from a public cache. Set and test native cache priority separately. **Evidence:** Show an Attic-only substitution trace and a normal-policy trace. Do not infer the source of a path from successful execution.

### Medium — F07: “Direct dependency” has no stable graph in the initial capture policy

**Location:** Baseline [concept §12](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L460), [spec §5](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L140), `V4-SRC-019–023`.

**Failure scenario and consequence:** A direct devenv input can be a module repository. A directly selected Neovim package can instead come from `nixpkgs`, while its source is outside the runtime closure. A list entry may resolve against one graph and miss the source the owner meant to inspect. Nix distinguishes derivation and output closures; neither is a complete source map. [Nix closure queries](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query) document that boundary.

**Correction:** Keep the accepted consumer-maintained list. Leave its graph and syntax open until the owner answers and P3 proves native resolution. Record the graph and selected identity per entry. Unmatched entries report gaps without changing locks. **Evidence:** Test selected, unlisted, stale, and patched dependencies in the first-proof consumer.

### Medium — F08: Local independence is tested only with an already realized output

**Location:** Baseline `V4-OWN-003–004`, [concept §1](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L11), [§9](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L324), and [§13](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L509), [spec §2](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L37).

**Failure scenario and consequence:** A command already in `/nix/store` runs while Attic is down, yet a new local consumer may still need Vendomat or Attic to realize its native inputs. The existing test proves less than the stated local-use promise. Nix can build or substitute according to native policy when required inputs remain reachable. [Nix realization](https://nix.dev/manual/nix/2.28/command-ref/nix-store/realise) and [fallback](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html) define this limit.

**Correction:** Test fresh local realization with Vendomat and Attic unavailable, while documenting which native sources or public caches remain necessary. Do not promise a fully offline build. **Evidence:** Run the project and editor from a clean local consumer under the declared fallback policy.

### Medium — F09: Recovery claims need driver-specific and domain-specific outcomes

**Location:** Baseline [spec §7 recovery table](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L190), `V4-MACH-009–013`, `V4-REC-001–012`, `V4-APP-025`.

**Failure scenario and consequence:** Home Manager may have no independent profile when embedded as a NixOS module. A successful NixOS rollback cannot claim user files, application writes, an inspection archive, Attic state, or historical evidence are restored. [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html) states that profile ownership depends on its driver; [Machines recovery](https://devenv.sh/machines/) excludes application data and early boot failures. A [btrfs snapshot is not a backup](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html).

**Correction:** Record separate status for each domain. Name the Home Manager activation driver in the fixture. Keep btrfs image recovery conditional on the later application. **Evidence:** Restore source, Attic, and evidence separately; fail Home Manager after NixOS succeeds; inspect application data after system rollback.

### Medium — F10: Machines transfer and Attic publication are separate claims

**Location:** Baseline [concept §10](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L347), [spec §7](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L183), `V4-MACH-004–008`.

**Failure scenario and consequence:** Machines `apply` copies saved outputs to the target. A target can receive them directly from the build host even when Attic never serves them. A checked application output linked to the plan also does not mean the whole NixOS generation is in Attic. [Machines](https://devenv.sh/machines/) documents plan, copy, activation, and stale-plan behavior.

**Correction:** Let Machines own plan, copy, apply, status, and rollback. Record observed transfer origin separately from application closure publication. Defer a whole-generation Attic claim until its closure is measured and independently verified. **Evidence:** Trace P7 target transfers with Attic present and absent.

### Medium — F11: A central source host risks unnecessary state and service coupling

**Location:** Baseline [concept §§11–12 and §19](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L392), [spec §5](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L132), `V4-SRC-013–018`.

**Failure scenario and consequence:** Git mirrors, archives, Nix paths, unpacked read views, indexes, and remote mounts can each become another copy to protect. A retained Nix source path without a root or backup disappears under garbage collection. The documents already distinguish retained objects from derived views, but a private-network host is described as the normal first shape before an offline-read need is established.

**Correction:** Start with one durable object plus a small identity record per selected source. Rebuild read views; add indexes and local replicas only for demonstrated queries. Keep local execution independent of the host. Whether disconnected source reads are a first-phase need awaits the owner. **Evidence:** Delete a derived view, restore the retained object and record, then read it from the intended client.

### Medium — F12: The later application specifies a staging method before proving the adapter

**Location:** Baseline [spec §9 materialization](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L259), `V4-APP-006–010`, `V4-APP-020–024`.

**Failure scenario and consequence:** A Jujutsu change ID survives rewrites and can become divergent. A full commit ID selects one commit, but the commit is not a btrfs subvolume. The proposed staging subvolume and queue policy may be one sound design, yet neither follows from Vendomat's core. [Jujutsu identity](https://docs.jj-vcs.dev/latest/glossary/), [btrfs snapshots](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html), [bubblewrap mounts](https://github.com/containers/bubblewrap/blob/main/bwrap.xml), and [systemd service templates](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml) assign distinct roles.

**Correction:** Specify a verified commit-to-image mapping and atomic reader-visible image as the contract. Keep writable staging and queue storage as later prototype choices. Attic covers Nix runtime paths only; bubblewrap runs processes and cannot build or activate NixOS. **Evidence:** The later fixture tests conflicts, file modes, image tampering, sandbox failure, restart, and separate source/image/runtime/state recovery. None gate initial V4.

### Low — F13: Optional operations can obscure the first useful release

**Location:** Baseline [concept §16](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L662), [§17](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L696), [§18](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L738), and [§22](../09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md#L874), [spec §8](../09-vendomat-nixos-devenv-rewrite/V4-SPEC.md#L205), `V4-UPG-*` and `V4-OPT-*`.

**Failure scenario and consequence:** A guide might schedule upgrades, release tasks, scaffolds, and storage reports before the first application and cache path works. That adds orchestration state before repeat use is shown.

**Correction:** Keep P8 as one later on-demand proposal. Keep P9–P10 conditional on measured use. A native update command, task, or timer remains the first option. **Evidence:** Only add a helper when two real consumers need the same repeated operation and the native-only trial leaves a concrete gap.

## Claims that survive the adversarial test

- A [Jujutsu change ID can name evolving or divergent commits](https://docs.jj-vcs.dev/latest/glossary/). Resolve a request to one full commit ID before admission. A commit ID is still distinct from the image's verified file manifest.
- A [btrfs snapshot starts from another subvolume](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html). The later adapter must materialize and verify the pinned tree first.
- [Attic pushes Nix store paths and closures](https://docs.attic.rs/reference/attic-cli.html). It makes no btrfs-image or mutable-state distribution claim.
- [Bubblewrap makes process namespaces and mounts](https://github.com/containers/bubblewrap/blob/main/README.md). [NixOS](https://nixos.org/manual/nixos/stable/) builds and activates system generations.
- [Machines](https://devenv.sh/machines/) owns plans, transfer, activation, status, and native rollback. The pinned-version fixture still must prove the exact behavior V4 uses.

## Open decisions and proof gates

**Owner decisions requested early:** `Q-CAPTURE-GRAPH` defines the direct-dependency graph; `Q-PROOF-GATE` decides whether P7 joins the first release gate; `Q-OFFLINE-SOURCE` decides whether the laptop needs a source replica. The revised documents keep these open until answered.

**Prototype-dependent:** P0 pinned Machines transition and consumer migration; P1 editor packaging; P2 native delivery and overrides; P3 source mapping and capture-list representation; P4 effective checks and frozen bytes; P5 Attic-only closure and fallback; P7 transfer and separate activation; the later application adapter and sandbox. Online documentation is evidence of upstream behavior, not a fixture on this repository's selected versions.

**Resolved in revised text:** output path versus content hash; three check outcomes; Neovim proof boundary; Attic filter and priority; native Machines ownership; driver-specific recovery; later-application staging as an example; and a required migration inventory. The accepted owner decisions remain unchanged.

## Cross-document traceability and consistency

| Contract | Revised concept | Revised specification | Revised requirements and audit result |
| --- | --- | --- | --- |
| Native selection and local use | §§2–3, 8–9, 14 | §§2–4 | `V4-OWN-001–013`, `V4-SEL-001–009`; new fresh-local and host-input gates close F03/F08. |
| Focused modules and Neovim proof | §§4–8, 21–22 | §§3, 10 | `V4-MOD-001–014`, `V4-PROOF-001–006`; workstation declaration does not claim activation. |
| Three check outcomes | §§14, 20 | §§6, 8 | `V4-CHK-004–016`, `V4-EVD-011`; failed and missing required checks block, documented nonrequired gaps do not. |
| Listed source capture | §§11–12, 19 | §§5, 10 | `V4-SRC-001–024`; accepted listed capture remains, while `Q-CAPTURE-GRAPH` and remote-read scope remain open. |
| Exact Attic publication | §§13–15, 21 | §§4, 6, 8 | `V4-SEL-006–009`, `V4-CACHE-001–015`; NAR identity and Attic-only closure need P4/P5 fixtures. |
| Native Machines and separate recovery | §§7, 10, 19, 21–22 | §§7–8, 10 | `V4-MACH-001–015`, `V4-REC-001–013`, `V4-PROOF-009`; P7 is required for machine claims. |
| Later Jujutsu application | §23 | §9 | `V4-APP-001–031` remain conditional; staging, queue, and sandbox details remain later proofs. |
| Later upgrades and helpers | §§16–18, 22 | §8 | `V4-UPG-001–009`, `V4-OPT-001–004`; P8 or offer conditions keep them outside the first application proof. |

The requirement audit gives one disposition to each of 172 baseline IDs. The revised requirement file retains all 172 IDs and adds 11 distinct IDs. `V4-PROOF-007–008` remain visible as retired duplicates of `V4-REC-001–002`. All three revised documents preserve D-APP-SCOPE, D-NAMES, D-CHECK-OWNER, D-CHECK-GAP, and D-CAPTURE. The source project's hashes still match [the baseline](./BASELINE.md). No V4 product code or implementation guide changed.

**Guide verdict:** The revised documents can support a separate, evidence-first implementation-guide session. That session must start with P0 and preserve the open owner choices. It cannot present P2, P5, or P7 command syntax and behavior as proven before their fixtures run. This review does not write that guide.

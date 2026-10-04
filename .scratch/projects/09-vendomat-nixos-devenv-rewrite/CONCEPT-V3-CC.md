# Vendomat V3

## Machine-wide source retention, checked builds, Attic distribution, reviewed upgrades

**Status:** Proposed greenfield architecture, 2026-10-04. Supersedes every earlier concept in this
directory.
**Scope:** One owner. Two NixOS machines on a private tailnet — a desktop build host and a laptop
consumer. Personal use only.
**Basis:** Ground-up rewrite. The current implementation defines no interface and no requirement.
**Version floor:** devenv 2.4.1 or later, pinned. See section 13.

---

## 1. Purpose

> **Retain the source for everything the owner's machines install, build it once on the build host,
> serve the outputs through Attic, keep the source readable, and prepare upgrades for explicit
> review.**

```text
declare machine
    → enumerate its source
    → retain and verify that source
    → one checked build
    → Attic over the tailnet
    → candidate report
    → explicit acceptance
    → separate deployment
```

Two properties drive the design, and they are not the same property:

> **Retained source proves that an output can be rebuilt.
> Attic proves that an output's bytes are available.
> Neither may stand in for the other.**

Vendomat coordinates Nix, devenv, Git, and Attic. It replaces none of them. It adds no lock, no
package format, no version authority, and no dependency resolver.

Five capabilities must stay separable:

| Capability | Purpose |
| --- | --- |
| Source retention | Keep the bytes needed to reproduce a build |
| Checked builds | Build and test the exact output a machine selects |
| Distribution | Publish validated outputs and closures through Attic |
| Upgrade preparation | Find and validate candidate changes |
| Evidence | Record what was actually validated |

A machine may keep using a built package when the source archive is down. A package stays
reproducible when Attic is down. A candidate may be built and cached without acceptance. An accepted
change may exist without deployment. Vendomat must never collapse these into one idea of
"published" or "available".

---

## 2. The covered set

"Everything installable" is derived, never declared.

| Covered | How it is enumerated |
| --- | --- |
| Each machine's system closure | `machines.<host>` in `devenv.nix` |
| Every build input of that closure | The recursive derivation graph, not the runtime closure |
| Each declared project shell | Its devenv output, same treatment |
| Flake inputs | `devenv.lock`, which records `rev` and `narHash` |

Two machines means two covered sets. They overlap heavily, and section 5 deduplicates that overlap
for free.

Out of scope: all of nixpkgs. Vendomat retains source for what the machines select, not for what
they could select.

---

## 3. Source discovery is enumeration, not parsing

This is the load-bearing technical claim of the design.

Nix sandboxes builds with no network. Anything that fetches during a build must therefore be a
**fixed-output derivation** carrying the hash the build trusts. So:

```text
complete source set =
    every fixed-output derivation in the machine's recursive derivation graph
  + every input locked in devenv.lock
```

Both are mechanical queries. `nix derivation show -r <drvPath>` emits the whole graph as JSON, and a
fixed-output entry is identified by its declared output hash.

**Do not write a general Nix expression parser.** None is needed. Earlier concepts deferred
machine-wide coverage because they assumed one was required. That assumption was wrong.

Three qualifications. Phase P1 tests each rather than assuming it.

- **Evaluation-time fetches** (`builtins.fetchTarball`, `builtins.fetchGit`, import-from-derivation)
  run before any derivation exists. Flake inputs are the common case and `devenv.lock` covers them.
  Any other eval-time fetch is a reported gap, never a silent one.
- **Build-only inputs** appear in the derivation graph and not in the runtime closure. Using the
  derivation graph is what makes the claim complete. A runtime closure would understate it.
- **Vendored source** inside a tarball sits inside the fixed-output derivation. Retaining that
  derivation's output retains it.

### Coverage states

The report distinguishes four states and claims nothing more:

retained · identified but unavailable · cannot be retained · not yet identified.

Vendomat gives a reason for every gap.

### Two record kinds

A git revision is self-identifying. An archive or patch is identified by the hash Nix declares, and
that declared hash is what the build trusts. These verify differently, so the archive keeps two
record kinds:

| Kind | Verified by |
| --- | --- |
| Git object | Revision reachability in the mirror, plus content |
| Fixed-output input | Exact match against the hash Nix declares |

Merging these is how an implementation quietly accepts a mismatch. Keep them apart.

---

## 4. Two stores and one derived view

| Layer | Holds | Answers | Durable? |
| --- | --- | --- | --- |
| **Source archive** | Content-addressed verified source bytes | Can this be rebuilt? | Yes. Backed up. Evidence. |
| **Attic** | Signed Nix outputs and closures | Can this be installed now? | Yes. Backed up including signing state. |
| **Read layer** | Unpacked trees and Git checkouts | What does this code say? | No. Derived from the archive. |

A signature proves bytes are authentic. It proves nothing about reproducing them from source.

### The read layer

The read layer is an unpacked, name-addressed, searchable view of the archive. It is exported
read-only over the tailnet. The owner or an agent reads it to answer a question about a
dependency's actual code.

Three rules keep it from corrupting the design:

1. It is **derived**. Delete it and regenerate it from the archive at any time.
2. It is **never evidence**. A retention claim cites the archive, never the read layer.
3. It is **never in the build or evaluation path**. No derivation reads it.

Readability is a property of the whole store, not a per-dependency policy.

---

## 5. Content addressing makes "retain everything" affordable

Store every source blob under the hash Nix already declares for it.

That gives deduplication across machines and across generations. A `nixpkgs` bump changes thousands
of derivations, but only the source of packages whose version changed. Identical source across two
generations is stored once. Attic has the same property for outputs.

So the growth cost of retaining everything is the genuinely new source per upgrade, not a full copy
per generation. Phase P0 measures the real numbers before anything commits to them.

---

## 6. Selections

Every build, publication, and candidate starts from an immutable **selection**:

| Field | Meaning |
| --- | --- |
| Project revision | The devenv project commit being validated |
| Locks | `devenv.lock`, and any other native lock the output depends on |
| Output | `machines.<host>`, or a project output attribute |
| Target system | Architecture and platform |
| Profiles | Any active devenv profile |
| Overrides | Any explicit input override |

Vendomat records the evaluated derivation path and output path for that selection.

This forbids the vague claim. Not "nixpkgs updated and it worked", but "host `laptop` at project
revision X with lock Y for `x86_64-linux` evaluated to derivation D, passed checks C, produced
output O."

Several native locks may legitimately own different parts of one selection. Vendomat records which
ones mattered. It never collapses them into one Vendomat lock.

---

## 7. Evidence, not shadow state

Query current facts from their authority:

```text
what this machine selects   → devenv.lock
is this source retained     → the archive, by hash
is this output available    → Attic
what does this evaluate to  → Nix
what is deployed            → devenv machines status
```

Persist only what no authority can reconstruct later. A completed validation creates historical
facts that no store can answer for afterwards, so Vendomat keeps **evidence records** — immutable
receipts of an event:

project revision and lock hashes · selection · source identities and coverage result · derivation
path · output path · checks run and their results · Attic target and upload result · cache
verification result · the devenv plan ID, when one exists.

The rule:

> **Do not persist facts that can be queried from an authority. Persist historical evidence that
> describes what happened.**

An evidence record is never authoritative dependency state.

---

## 8. The source-use proof

Retention is a claim about the future, so it needs a test, not a record:

```text
capture → verify identity → clear local fetch caches
       → block tested upstream endpoints → build → identical output path
```

Changing where source comes from must not change the derivation being validated. If a lock still
names an upstream URL, the proof must show that fetch resolving to identical retained bytes. If a
build tool arrives from a binary cache, the report names it.

This runs on the build host against one package first (P3), then against a whole machine closure
(P7). Make it a scheduled check, not a milestone. A store that passed one restore test is not a
store that restores.

---

## 9. Attic and the substituter policy

The build host builds the full system closure for both machines and pushes it to Attic. The laptop
substitutes from Attic and builds nothing.

The build host must push the **complete closure**, not only what it built locally. Pushing only
locally-built paths leaves the laptop depending on `cache.nixos.org` for the rest, which restores
the upstream availability dependency this project exists to remove.

Keep `cache.nixos.org` on the laptop as a **fallback** substituter rather than removing it. That
gives independence without turning an Attic outage into a dead laptop. P5 measures whether the
storage and upload cost is acceptable. If it is not, the fallback becomes load-bearing and this
document must say so.

Use HTTP over the tailnet. Tailscale already encrypts the traffic, and a certificate adds work
without adding security here.

**Attic trust cannot be declared in devenv.** devenv exposes only `cachix.pull` and `cachix.push`.
An arbitrary substituter and its public key need Nix daemon configuration, and an untrusted user
cannot add one. The endpoint and the trusted key live in NixOS `nix.settings`, per machine.

---

## 10. Retention and the keep-set

Nothing is deleted. The keep-set is defined now and enforced later.

> **No retained output may outlive the source required to reproduce it. Source retention is a
> superset of cache retention.**

The failure this prevents: Attic serves an output whose source was dropped, and the owner holds
executable bytes that can never be reproduced again.

The keep-set is computed from:

```text
active machine and project locks
+ a stated recovery window
+ explicitly pinned revisions
+ retained devenv plans in .devenv/machine-plans/<id>/
+ rollback systems held on each target under /nix/var/nix/gcroots/devenv-machines/
```

The last two are easy to miss and both are real retention roots. A plan retains its outputs. A
target keeps the previous system so the watchdog can restore it. **The keep-set must therefore read
remote state, not only local locks.** Dropping source for a system a target can still roll back to
breaks the invariant.

Attic's own garbage collection is time-based and disabled by default, and its retention reference
point is undocumented. So Vendomat computes the keep set and deletes through Attic's API.

Because nothing is deleted today, the invariant holds trivially. It becomes a real constraint at
P13, and only if deletion is wanted at all.

---

## 11. devenv is the user-facing layer

devenv declares what a project is and what a machine is. It supplies configuration, outputs, tests,
tasks, task dependencies, structured task inputs and outputs, git hooks, profiles, and machines.

Vendomat adds a small module with Vendomat-specific policy only. It must not duplicate package
names, dependency declarations, or version numbers that native files already own.

**Vendomat declares no `checks` option.** A project already declares its tests through `enterTest`.
The gate runs the project's own `devenv test`.

**Vendomat adds no `vendomat.version`.** Native package metadata — `project.version` in
`pyproject.toml`, `package.version` in `Cargo.toml` — stays authoritative.

### Transitive inputs work; no mechanism is needed

A resolved flake input exposes its own inputs, and they are real flakes nesting arbitrarily deep.
A flake lock is transitive. devenv splats the resolved inputs into module arguments. So a consumer
declares **one** input and **one** import:

```yaml
# devenv.yaml
inputs:
  nixpkgs:  { url: "github:cachix/devenv-nixpkgs/rolling" }
  disko:    { url: "github:nix-community/disko", follows: nixpkgs }
  vendomat: { url: "github:Bullish-Design/vendomat" }
imports: [ vendomat/modules/devenv.nix ]
```

Vendomat's own dependencies are locked transitively in the consumer's `devenv.lock` and reached as
`vendomat.inputs.<name>`. Adding an input to Vendomat adds a lock node on the next
`devenv update vendomat`. No consumer edits anything.

Two rules keep this safe:

1. Expose `modules/devenv.nix`, never the repository root. A root import merges Vendomat's whole
   development environment into the consumer.
2. The module takes `pkgs` from the consumer and never introduces a second nixpkgs into a
   consumer's build graph. Vendomat's own tools are exposed as built packages, not as recipes
   evaluated against Vendomat's nixpkgs.

---

## 12. Machines

A machine is a NixOS configuration declared in `devenv.nix`. The desktop declares both machines in
one project and deploys to the laptop over the tailnet.

```nix
machines.laptop = {
  system = "x86_64-linux";
  target.host = "root@laptop.tailnet";
  hardware.facter = ./hardware/laptop.json;
  nixos = import ./nixos/laptop.nix;
  deploy = {
    rollbackTimeout = 300;
    healthCheck = ''/run/current-system/sw/bin/systemctl is-system-running --quiet'';
  };
};
```

devenv supplies the whole machine lifecycle:

| Command | What it does |
| --- | --- |
| `devenv machines info` | Metadata, no build, no target contact |
| `devenv build machines.<host>` | Build the closure locally |
| `devenv machines check <host>` | Compare declared SSH access with facts read from the target |
| `devenv machines plan <host>` | Build, record system, access facts, and closure delta. Copy nothing. |
| `devenv machines apply plan-<id>` | Use those exact outputs with no rebuild, then activate |
| `devenv machines deploy <host>` | Build, review, confirm, copy, activate |
| `devenv machines status` / `rollback` | Report or reverse the last operation |
| `devenv machines install <host>` | Provision a fresh host: kexec, facter, disko, install, reboot |

**`plan` and `apply` already implement the invariant that validation and publication are one act.**
A plan records exact outputs and retains them. `apply` never rebuilds. A changed NixOS generation or
target definition makes the plan stale.

Activation is transactional. It runs in a systemd service on the target, with a watchdog that
restores the previous system when activation fails, a health check fails, or the controller cannot
confirm success before the deadline. The target retries recovery after a reboot.

**Vendomat drives `devenv machines plan`. It does not re-implement it.**

### Version floor and the pin

devenv 2.2.2 declared the `machines` option with no implementation behind it. devenv 2.4.1 ships the
full pipeline. Pin devenv at 2.4.1 or later and bump deliberately.

Machines is marked experimental and its interface may change before it is declared stable. That is
the reason for the pin, not a reason to avoid it. **Review trigger:** when devenv declares machines
stable, compare and adopt the stable interface.

### Constraints to design around

- NixOS machines require the `disko` input, even for deploy-only use.
- `hardware.facter` takes a committed report per host, or `null` when the module supplies hardware
  configuration itself.
- `install` partitions and formats without confirmation. There is no dry run and no resume.
- `--use-machines-as-builders` needs the C-Nix backend. Plain `devenv build` rejects it.
- NixOS gets watchdog rollback. home-manager and nix-darwin do not.
- `deploy` does not reboot after a kernel change.
- A plan selects executable store paths. Treat it as a trusted input.

---

## 13. Candidates

A candidate is **an exact proposed change to a native lock**, not a version number.

For a machine that is one `devenv update nixpkgs` diff of `devenv.lock`. For a project it may be
`uv.lock` or another native lock. Machines and projects now share one update command and one lock
format.

```text
isolated checkout of the current project revision
  → run the native update command
  → the resulting native diff IS the candidate
  → capture and verify the new source it requires
  → evaluate, check, and build the exact proposed state
  → publish the validated artifact to Attic and verify the cache serves it
  → record evidence
  → present the diff, the evidence, and the devenv plan
```

Vendomat never implements a parallel resolver. It drives the native one.

**Branch following is correct here.** Tracking `nixos-unstable` is the normal way to run NixOS, and
the lock pins the exact resolved revision. The lock makes it reproducible; the branch only decides
which revision gets proposed.

### Pins and holds

A machine or project may stay on an older revision. A pin carries a **reason** and a **date**, and
the report names stale ones:

```text
nixpkgs  pinned at 4870686 for 8 months  reason: upstream regression #41  stale
```

The real failure of "pin when needed" is not the pin. Forgotten pins accumulate until "I never have
to update" has quietly become "I never do update".

Where a pinned commit could disappear upstream, Vendomat keeps a retention reference in the archive.

### The gate

A candidate must build, pass the project's own `devenv test`, and clear `devenv machines check`.
The validated artifact is the published artifact. Acceptance never rebuilds.

A failed candidate records its cause and leaves every machine and lock unchanged.

---

## 14. Acceptance and deployment

Acceptance writes the native lock change and stops. It does not commit, merge, tag, deploy, or
rebuild. Git stays the owner's workflow.

Before applying a prepared candidate, Vendomat confirms the base files still match the state it
validated. If they moved, the candidate is stale: regenerate and revalidate. Evidence must never
detach from the state it claims to prove.

**Deployment is a separate act.** `devenv machines apply plan-<id>` activates the already-validated
outputs, under the watchdog. Accepting a lock change and activating a machine are two decisions.

The report carries the state that stops an accepted change from going missing:

```text
laptop   nixpkgs 2026-09-12 → 2026-10-01  validated, cached        plan-7f3a ready
desktop  nixpkgs 2026-09-12 → 2026-10-01  accepted, uncommitted    review and land
desktop  nixpkgs pinned at 4870686        8 months, reason stated  stale pin
```

---

## 15. The pipeline

The project-local pipeline is a devenv task DAG on the build host. Task dependencies encode
ordering, so an ordering rule stops being prose and becomes structure. Status commands make stages
idempotent. Failure propagation stops later stages.

```text
enumerate → capture → verify → evaluate → check → build
          → confirm-selection → push → verify-cache → record
```

Vendomat therefore needs no orchestrator, no sequencer, and no step-failure handling.

The full loop for a machine upgrade:

```text
devenv update nixpkgs            → the candidate lock diff
devenv build machines.<host>     → the system closure
  Vendomat enumerates its fixed-output derivations
  Vendomat captures and verifies source, runs the source-use proof
  Vendomat pushes the closure to Attic and verifies the cache serves it
  Vendomat writes the evidence record
devenv machines check <host>     → access facts, into the report
devenv machines plan <host>      → system, access facts, closure delta
  the owner reviews the diff, the evidence, and the plan
devenv machines apply plan-<id>  → no rebuild, watchdog-guarded activation
```

`plan` builds, and so does Vendomat. The same selection produces the same derivation, so the second
build is a Nix no-op. Prefer having Vendomat invoke `plan` and read its JSON over building
separately.

### The CLI boundary

> **Tasks are the project-local pipeline. The CLI is what spans repositories or runs without a
> project.**

Likely CLI surface: `sweep`, `candidates`, `accept`, `report`, `verify`, `read`. It stays a thin
coordinator and never becomes a second task framework.

---

## 16. Boundaries

```text
Nix       evaluation, derivations, store identity
devenv    machine and project declaration, evaluation, build, plan, apply, activation,
          rollback, tasks, tests, outputs, hooks, profiles — the user-facing layer
NixOS     daemon trust, Attic service, archive storage, backups, sweep timers —
          what a module cannot declare
Vendomat  source enumeration, capture, verification, the source-use proof, the read
          layer, Attic publication, evidence, candidate preparation, retention
```

NixOS keeps only what a devenv module cannot declare:

| Concern | Why NixOS |
| --- | --- |
| Substituters and trusted keys | The daemon needs trusted-user rights; devenv exposes only Cachix |
| Attic server, storage, backups | A system service, not a project service |
| Source archive storage and export | Durable host storage; `.devenv` GC roots are not retention |
| The sweep timer | The sweep runs with no project context |
| Push credential placement | A machine secret |

---

## 17. Failure semantics

| Failure | Required result |
| --- | --- |
| Source hash mismatch | Block capture and publication. Report the identity failure. |
| Required source unavailable | Report the gap with a reason. Claim no coverage. |
| Eval-time fetch found | Report it as an uncovered source kind. Never fail silently. |
| Evaluation failure | No publication. |
| Check or build failure | Record evidence and the log. Change no lock. Publish nothing. |
| Attic upload failure | Keep the local build. Report publication failure. |
| Attic reachable, path absent | A passing build is not a cache hit. Re-push. |
| Attic unreachable on the laptop | Fall back per machine policy, or fail naming the dependency. |
| Source archive unavailable | Report the source dependency separately from cache state. |
| Read layer missing or stale | Regenerate it. Never a correctness failure. |
| Stale candidate | Regenerate and revalidate before applying. |
| Activation fails | The devenv watchdog restores the previous system. Report the outcome. |
| Deployment outcome unknown | Block the next deployment until `status` resolves it. |
| Backup restore failure | The durability claim fails. Say so. |
| Upstream prunes a pinned commit | The retention reference holds it. Report that upstream lost it. |
| Sweep fails | Existing locks and environments stay usable. |

> **Automation may investigate aggressively. It must fail conservatively.**

---

## 18. Security

The tailnet is the boundary. One owner, no multi-tenancy. The complete model:

- build host: one restricted Attic push credential;
- laptop: the Attic URL and the cache public signing key, no push credential;
- read layer: read-only, tailnet-only;
- secrets stay outside tracked files and outside Nix store objects, placed by hand.

Nothing else. No secret manager, no token scoping, no authorization model.

For machine bootstrap only, devenv's `install.secrets` resolves SecretSpec values and streams them
over SSH without writing them into the Nix store. Use sops-nix or agenix for ongoing secrets.

Attic signing establishes trust in cached bytes. It does not prove those bytes can be reproduced
from retained source. Report the two as separate facts.

---

## 19. Phases

Each phase states a gate and a stop condition. A gate that can be relaxed under pressure is not a
gate, so every phase names what makes the work stop.

**P0 — Baseline.**
Record both hosts, systems, Nix and devenv versions, storage paths, backup destinations, and the
tailnet names. Declare both machines in one devenv project. Measure the derivation-graph size and
fixed-output count per machine, and estimate archive and Attic storage from them.
*Gate:* `devenv machines info` lists both machines, and the measurements exist.
*Stop:* If measured storage exceeds what the host can hold, reduce scope now, not at P7.

**P1 — Enumerate.**
From one machine's derivation, list every fixed-output derivation and every locked input. Report the
four coverage states. Capture nothing.
*Gate:* The enumeration is reproducible and every gap carries a reason.
*Stop:* If eval-time fetches outside `devenv.lock` appear in volume, section 3's central claim is
weaker than stated. Reduce the claim before building on it.

**P2 — Capture.**
Retain every enumerated source, content-addressed, verified against its declared hash. Record both
source record kinds.
*Gate:* Every claimed retention verifies. Every gap has a reason.

**P3 — Source-use proof.**
One package. Clear caches, block tested upstream endpoints, rebuild from the archive.
*Gate:* Identical output path with upstream unreachable. A build tool arriving from a binary cache
is named in the report.
*Stop:* If the locked fetch cannot be shown to resolve to retained bytes, the retention claim is
not yet true. Fix that before P4.

**P4 — Durability.**
Run Nix garbage collection. Restore the archive from backup, including identity records. Re-verify
hashes. Rebuild.
*Gate:* Retained source survives collection, and a restored copy produces the same output path.
*Stop:* If restore needs an undocumented manual step, write it down before continuing.

**P5 — Attic and the cold laptop.**
The build host pushes a complete closure. The laptop declares the endpoint and trusted key in NixOS.
Back up and restore Attic **including its signing state**.
*Gate:* The laptop substitutes the path with no builder running. A restored Attic still serves bytes
the laptop accepts.
*Stop:* If the laptop's store path differs from the build host's, the selection is not shared. Fix
that before anything else.

**P6 — Evidence.**
Persist publication records for everything P5 published.
*Gate:* An evidence record answers every question in section 7 without querying a live store.

**P7 — Whole-machine coverage.**
Extend P2 and P3 from one package to one machine's complete closure.
*Gate:* Every fixed-output derivation in the closure is retained and verified, or is a named gap.

**P8 — Read layer.**
Unpack the archive into a searchable, name-addressed, tailnet-exported view.
*Gate:* Deleting the read layer and regenerating it loses nothing. No derivation reads it.

**P9 — Candidate.**
One `devenv update nixpkgs` diff, validated end to end in an isolated checkout, ending in a devenv
plan with evidence attached.
*Gate:* A broken candidate records its cause and changes nothing.
*Stop:* If validation needs a resolver Vendomat wrote, the native path is wrong. Fix it here.

**P10 — Acceptance and deployment.**
Apply the validated change. Then `devenv machines apply plan-<id>`. Exercise a failed health check
and confirm the watchdog restores the previous system.
*Gate:* Acceptance creates no commit and triggers no build. A failed activation rolls back and
`devenv machines status` reports it.
*Stop:* If acceptance rebuilds, validation and publication have come apart. Fix it here.

**P11 — Sweep.**
A systemd timer runs discovery and candidate preparation. It may prepare. It may not accept or
deploy.
*Gate:* A new upstream revision becomes a validated candidate without the owner asking.

**P12 — Offline reconstruction.**
Empty store, source archive, no network. Rebuild a machine closure.
*Gate:* The bootstrap seed and the full toolchain come from the archive alone.
*Note:* Machine-wide retention makes this reachable, because the bootstrap tarball and stdenv are
themselves fixed-output derivations in the graph. It stays a separate claim with its own proof.

**P13 — Keep-set garbage collection.**
Only if deletion is wanted. Enforce section 10 across both stores, reading remote rollback roots.
*Gate:* Deleting from Attic never removes source an active lock, plan, or rollback root still names.
*Stop:* If the keep-set cannot enumerate remote rollback roots, delete nothing.

---

## 20. Invariants

1. Native locks remain authoritative. Vendomat adds no lock, resolver, or version authority.
2. Vendomat is never in the evaluation path and never required at runtime.
3. Every validation binds to an immutable project revision and a target system.
4. The covered source set is derived from the build graph, never declared.
5. Retained source is identified by the hash Nix declares and verified against it.
6. A retention claim is proven by a build with tested upstream endpoints blocked.
7. Source retention and output availability are separate facts, reported separately.
8. No retained output outlives the source needed to reproduce it.
9. Evidence is persisted. Derivable state is queried from its authority.
10. The validated artifact is the artifact published and later activated. Acceptance never rebuilds.
11. Acceptance writes a lock and stops. Deployment is a separate act.
12. The read layer is derived, never evidence, never in the build or evaluation path.
13. Consumers substitute from Attic. They never read the source archive to evaluate.
14. A check, build, source, or publication failure changes no lock and no machine.
15. A release tag is immutable. A bad release is corrected by a new release.
16. NixOS owns daemon trust, host services, storage, backups, and scheduling.
17. Removing Vendomat leaves every machine and project buildable by its native tools.

---

## 21. Not in scope

- Retaining all of nixpkgs rather than what the machines select.
- A general Nix expression parser.
- A new package format, a second package manager, a public index, or a dependency resolver.
- A runtime daemon, a resolver in the evaluation path, a graph database, or prediction.
- Inferred version numbers and automatic promotion.
- Secret management beyond hand-placed credentials and devenv's install-time bootstrap.
- A semantic capability layer, an action registry, and editor or shell adapters.
- Any full offline rebuild claim before P12 proves it.

---

## 22. Verified against primary sources

Every item below was checked on this machine on 2026-10-04.

**Flake inputs expose their own inputs, nesting arbitrarily deep.** Evaluated offline against this
repository's lock:

```text
inputs.uv2nix                              → attrNames include "inputs"
inputs.uv2nix.inputs                       → [ "nixpkgs" "pyproject-nix" ]
inputs.uv2nix.inputs.pyproject-nix.outPath → /nix/store/8v7igf57cn6gxv2lg7y5wm9343873fcw-source
inputs.uv2nix.inputs.pyproject-nix.inputs  → [ "nixpkgs" ]
```

**A flake lock is transitive.** This repository's `flake.lock` holds 17 nodes for 13 root inputs,
with nested input maps.

**devenv passes resolved inputs to modules.** `specialArgs = inputs // { inherit inputs secretspec
primops; }` — `.devenv/bootstrap/bootstrapLib.nix:235`, also lines 515 and 602, devenv 2.2.2.

**devenv.yaml imports resolve against the input set.** `input = inputs.${name} or (throw "Unknown
input ${name}"); devenvpath = input + subpath;` — `bootstrapLib.nix:146`.

**devenv's default nixpkgs is a wrapper flake.** `github:cachix/devenv-nixpkgs/rolling` holds 12
files, no `nixos/`, no `pkgs/`. It exposes `legacyPackages`, `lib`, and two `nixosModules`
(`notDetected`, `readOnlyPkgs`). It has no `lib.nixosSystem`. Its input `nixpkgs-src` is a real
nixpkgs tree with `nixos/lib/eval-config.nix`, declared `flake = false`.

**devenv 2.4 handles that itself.** `src/modules/machines.nix:48` defines `nixosSystemFor`, which
uses `inputs.nixpkgs.lib.nixosSystem` when present and otherwise imports
`inputs.nixpkgs.inputs.nixpkgs-src + "/nixos/lib/eval-config.nix"` with
`pkgs = inputs.nixpkgs.legacyPackages.${system}`. It throws when neither is possible. The result is
memoized at line 683 so `nixosSystem` runs once per machine. **No separate machines nixpkgs input is
needed.**

**devenv 2.2.2 machines was declaration-only.** `src/modules/machines.nix` was 68 lines of options.
Nothing read `config.machines`, no Rust source referenced it, there was no `devenv machines`
subcommand, and no docs page existed. This is the reason for the 2.4.1 version floor.

**devenv 2.4.1 ships the full pipeline.** Revision `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`. An
896-line `machines.nix`, a `src/modules/machines/` directory (`deploy.nix`, `deploy.py`,
`facts.nix`, `recovery.nix`), `devenv/src/devenv/machines.rs`, 12 machines test suites, and
`docs/src/content/docs/machines.md`. `MachinesCommand` at `devenv/src/cli.rs:1324` covers `info`,
`check`, `install`, `deploy`, `plan`, `apply`, `status`, and `rollback`.

**Plan and apply semantics**, from `docs/machines.md`: `plan` builds outputs and records the NixOS
system, access facts, and store closure changes, and copies nothing. `apply` uses those exact
outputs without rebuilding. A changed NixOS generation or target definition makes the plan stale.
Plans live under `.devenv/machine-plans/<id>/` and retain their outputs.

**Transactional activation**, from the same source: activation runs in a systemd service on the
target; a watchdog restores the previous system when activation or a health check fails, or when the
controller cannot confirm success before the deadline. `deploy.rollbackTimeout` accepts 30 to 600
seconds and defaults to 300. State lives in `/var/lib/devenv-machines`, and retained system paths in
`/nix/var/nix/gcroots/devenv-machines/` on the target.

**Nix requires fixed-output derivations for build-time fetches**, because the build sandbox has no
network. This is the basis of section 3.

**Attic's time-based garbage collection is disabled by default** and its retention reference point
is undocumented.

---

## 23. Unverified

State these as open, not as facts.

- Whether fixed-output derivations plus `devenv.lock` genuinely cover every source on a real machine
  closure. P1 tests it.
- Real archive and Attic storage for two machine closures, and incremental growth per `nixpkgs`
  bump. P0 measures it.
- Whether Attic permits unauthenticated substitution over the tailnet in the current release.
- Whether a complete closure push to Attic is fast enough to be routine.
- Whether `devenv machines plan --json` carries enough closure detail to drive Vendomat's push
  without a separate `nix path-info` pass.
- Whether Attic substitution composes with the copy step inside `devenv machines deploy` on the
  target.
- Whether `devenv update <input>` propagates a new transitive Vendomat node without a manual
  `follows`. The read path is verified; the update path is not.
- Whether devenv's machines interface changes before it is declared stable, and how much.

---

## 24. The shape in one place

```text
source archive ─┐
                ├─ one keep-set ─ no output outlives its source
attic          ─┘
       │
read layer (derived, searchable, never evidence)

declare machine → enumerate → capture → verify → build → check → publish → evidence
                                          └──── one act ────┘
                                                              │
                              report → accept (writes a lock) → plan → apply
                                        └ the only manual gate ┘   └ separate act ┘
```

Vendomat stores bytes it cannot recreate and facts it cannot ask for. Everything else is a query.

> **Removing Vendomat must not make a machine's dependency state unintelligible.**

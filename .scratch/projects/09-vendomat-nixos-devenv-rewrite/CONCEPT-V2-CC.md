# Vendomat V2: two byte stores, one keep-set, a devenv-native pipeline

**Status:** Proposed architecture, 2026-10-04. Supersedes `CONCEPT.md`, `CONCEPT-CODEX.md`, and
`CONCEPT-CLAUDE.md` in this directory.
**Scope:** One owner's NixOS machines on a private Tailscale network. Personal use only.
**Basis:** Greenfield rewrite. The current implementation defines no interface and no requirement.

## 1. Purpose

Vendomat keeps the source it can obtain, builds selected software once, serves the result over the
tailnet, and tells the owner which upgrades are ready. The owner never writes a version pin.

```text
declared release
    → retained source
    → one checked build
    → Attic over the tailnet
    → candidate report
    → explicit acceptance
    → the consumer's own lock
```

Two properties drive the whole design, and they are not the same property:

> **Retained source proves that an output can be rebuilt.
> Attic proves that an output's bytes are available.
> Neither may stand in for the other.**

Vendomat coordinates `git`, `nix`, `devenv`, and `attic`. It replaces none of them.

## 2. The two stores

| Store | Holds | Answers | Keyed by |
| --- | --- | --- | --- |
| Source store | Immutable source bytes, outside Nix garbage collection, backed up | Can I rebuild this? | Locator plus revision or declared hash |
| Attic | Signed Nix outputs and runtime closures | Can I install this now? | Nix store path |

Both stores are core and permanent. Both run on one build host. Neither is optional.

A consumer trusts Attic's signing key to accept bytes. That trust says nothing about source.
A retained source set supports a rebuild. It does not make an output available.

## 3. Core invariants

These are requirements, not preferences. Each one is testable.

1. A source hash mismatch blocks capture and blocks publication.
2. Source that Vendomat cannot retain appears in the report as a named gap, with a reason.
3. **No output stays served after its source is dropped.** Source retention is a superset of cache
   retention. One keep-set computation feeds both stores.
4. Nothing is published that was not the artifact of the check that gated it.
5. Nothing is accepted that was not already published. Acceptance triggers no build.
6. A resolution is always a function of (policy, mirror state, accepted candidates). Vendomat can
   recompute it at any time and compare.
7. Vendomat persists no fact that it can ask a store or a lock for.
8. A failed capture, check, build, or upload leaves every consumer lock unchanged.
9. Only an explicit acceptance changes what a site uses.
10. A release tag is immutable. A bad release is corrected by a new release.
11. Generated files are never hand-edited. Vendomat refuses a hand edit; it does not overwrite it.
12. Ordinary shell entry and ordinary evaluation never need a live Vendomat service.
13. Cache authenticity and source reproducibility are reported as separate facts.

## 4. Ownership

One fact has one owner.

| Owner | Holds |
| --- | --- |
| Producer repository | Source history, release declaration, build recipe, its own tests |
| Consumer repository | Its generated lock, reviewed and committed by the owner |
| Source store | Retained source bytes and their identity |
| Nix | Evaluation, derivations, store-path identity, builds |
| Attic | Output bytes over the tailnet |
| Git tags | Release identity. A tag is the version. |
| devenv | What a project is: policy, outputs, tasks, tests, hooks |
| NixOS | What a machine trusts and runs: substituters, keys, storage, timers, backups |
| Vendomat | Capture, sweep, candidate builds, publication, reports, acceptance |

## 5. The owner's surface

The `vendomat` option group in `devenv.nix` carries the whole owner-facing surface. devenv's module
system supplies types, defaults, and assertions, so Vendomat needs no configuration format and no
schema validator. `nix eval` is the configuration reader. A malformed declaration fails at
evaluation.

```nix
vendomat = {
  name    = "pyjutsu";                 # this site's key. The only required field.
  version = "0.23.0";                  # this project's release. Producers only.

  pins.tyo3 = {
    commit = "4870686";
    reason = "upstream PR #41";        # required. See section 10.
  };

  sources.pydantic = "mirror";         # see section 7.
};
```

A plain consumer writes one line. `name` keys the site and marks this repository as the home of a
managed codebase, so the library stays editable here and is never vendored into itself.

**Declare the name. Do not infer it.** One Git remote has two spellings. A rename, a host move, or
a fork changes the URL while the project stays the same. A declared name is reviewed and cannot drift.
Vendomat refuses when two mirrors claim one name.

**Vendomat declares no `checks` option.** A project already declares its tests through `enterTest`.
The candidate gate runs the project's own `devenv test`.

## 6. State: derived by default

Every fact Vendomat needs is already held by a system of record. A devenv task `status` command
queries that record; when it exits 0, devenv skips the task and restores the previous run's outputs.
So a publication record is a **view**, not a table.

| Question | Where the answer already lives |
| --- | --- |
| Which revision does this site use? | The consumer's committed lock |
| Is this source retained? | `git -C <mirror> cat-file -e <rev>^{commit}` |
| Does its content still match? | The declared hash, re-verified |
| Do bytes exist for this output? | `nix path-info --store <attic> <path>` |
| What does this graph build? | `nix derivation show` on the consumer's locked graph |
| Has policy changed? | `execIfModified = [ "devenv.nix" "devenv.lock" ]` |

Vendomat stores only what it cannot ask for:

- candidate build logs;
- the last-seen tag set per managed codebase;
- the declared list of consumer repositories the keep-set must scan.

That list is a list, not a database. There is no provenance store, no coverage table, and no
publication-record store. State cannot disagree with the stores it describes, because there is none.

## 7. Source: two tiers, two record kinds

### Tiers

| Tier | What it is | Candidates | Install source |
| --- | --- | --- | --- |
| Managed codebase | The owner's own repository | Yes, from tags | Vendomat's build |
| Grounding mirror | A declared third-party repository | No | Unchanged |

`sources.<dep>` selects the mode:

- `upstream` is the default. Declare nothing and nothing changes.
- `mirror` clones source for reading, searching, and grounding. **It never changes installation.**
  A grounding clone must not enter `pyproject.toml`, `[tool.uv.sources]`, or `uv.lock`.
- `build` builds from the retained copy. It changes that derivation and every derivation downstream,
  so it loses `cache.nixos.org` for the whole subtree. Set `build` on a low-level package such as
  `openssl` and most of the system rebuilds. Use `build` for the owner's own code, and for a
  dependency with a concrete reason to patch it.

### Record kinds

A git revision is self-identifying. An archive, a patch, or a fixed-output derivation is identified
by the hash Nix declares, and that declared hash is what the build trusts. These verify differently,
so the store keeps two record kinds:

| Kind | Verified by |
| --- | --- |
| Git object | Revision reachability in the mirror, plus content |
| Fixed-output input | Exact match against the hash Nix declares |

Merging these two is how an implementation quietly accepts a mismatch. Keep them apart.

### Coverage

The report distinguishes four states and never claims more than it proved:

retained · identified but unavailable · cannot be retained · not yet identified.

A flake archive covers flake inputs. Package recipes fetch further archives, patches, and
repositories during a build, and an output's runtime closure omits its build inputs. So Vendomat
inspects the evaluated build graph of the selected package.

**Do not write a general Nix expression parser.** Prove discovery on one real configuration and
expand from observed failures. Machine-wide coverage auditing is a later phase (section 14).

### Pinned commits need retention

A tag is durable. An arbitrary commit is not: upstream rebases, force-pushes, or prunes it, and the
pin stops resolving. Vendomat creates a retention ref in the mirror for every pinned commit and for
every active resolution.

### Who fetches source at evaluation time

The build host fetches from the source store. **Consumers do not.** They fetch from upstream as
usual, and the store serves the build host and disaster recovery.

This keeps invariant 12 intact: no machine's shell depends on one host being up. It still proves
retention, because the retention claim is tested on the build host with upstream unreachable.

The target state is consumers preferring the store with upstream as fallback. Adopt it only with the
evaluation-time dependency stated and accepted.

## 8. The pipeline is a task DAG

devenv tasks supply `before`, `after`, `wantedBy`, and `@succeeded` failure propagation, plus
`$DEVENV_TASK_OUTPUT_FILE` and `$DEVENV_TASKS_OUTPUTS` for JSON between stages. Vendomat therefore
needs no orchestrator, no sequencer, and no step-failure handling.

Ordering rules stop being prose and become structure:

```nix
tasks."vendomat:tag".after = [ "vendomat:build" "vendomat:check" ];
```

A tag can no longer precede a passing build. The declaration enforces it.

```text
capture → verify → build → check → push → record
                                      ↑
                        tag depends on build and check
```

Each stage carries a `status` command, so a repeated run does the work that remains and skips the
work already done.

### Producer outputs

A producer declares its publishable artifact in `devenv.nix`:

```nix
outputs.app = config.languages.rust.import ./. {};
```

Rust routes through crate2nix and Python through uv2nix. `devenv build outputs.app` prints the store
path, which is what Attic pushes. A producer then hand-writes no flake package.

Verify this early. It is cheap to test and it removes a declaration surface. The test is the one the
first phase already needs: does the build host reproduce that store path from retained source.

## 9. Delivery and the keep-set

The build host pushes to Attic. Consumers substitute from it over the tailnet. Use HTTP; Tailscale
already encrypts the traffic, and a certificate adds work without adding security here.

**Attic trust cannot be declared in devenv.** devenv exposes only `cachix.pull` and `cachix.push`.
An arbitrary substituter and its public key need Nix daemon configuration, and an untrusted user
cannot add one. So the endpoint and the trusted key live in NixOS `nix.settings`, per machine.

This fixes the boundary, and the document must keep it sharp:

> **devenv declares what a project is. NixOS declares what a machine trusts.**

### One keep-set

Derive one keep-set from the active consumer locks plus a stated recovery window. Feed it to both
stores. Source retention must cover everything cache retention covers.

The failure this prevents is silent and fatal to the design: the source store drops source for a
revision whose output Attic still serves and a lock still names. The owner then holds executable
bytes that can never be reproduced.

Attic's own garbage collection is time-based and disabled by default. Vendomat computes the keep set
and deletes through Attic's API, because a version-based keep set does not depend on a retention
reference point that the documentation leaves unstated.

## 10. Resolution, candidates, and acceptance

### Sites are derived

> A **site** is one place where one managed codebase is used.

A Python repository already names its dependencies. Vendomat intersects that list with the codebases
it manages. **Derive the site list. Never declare it.** Adding a dependency to the native file is the
only action required.

### Resolutions live in the consumer repository

A resolution is that site's property, not the property of whichever machine the owner is using.
Keeping it in Git gives a reviewable diff, per-repository rollback, and pure evaluation over
repository files.

### Candidate rules

| Rule | Behaviour |
| --- | --- |
| Newest tag (default) | Offer each new tag as a candidate |
| `pins.<lib>.commit` | Hold this exact commit. Produce no candidate. |
| `pins.<lib>.hold` | Stay at the current resolution. Produce no candidate. |

There is no branch rule. Branch following returns the churn and the irreproducibility that tags
prevent. To follow a branch tip, pin the commit it points at — that is what the build uses anyway.

### The gate

A candidate must build, then pass the project's own `devenv test`. **The candidate build is the
published artifact** (invariants 4 and 5), so verification and publication are one act and acceptance
never rebuilds. Nix caches the build, so a candidate shared by several sites builds once.

A failed candidate keeps its log and leaves that site on its last good resolution. Sites diverge onto
different versions by themselves. That is the intent.

### Pins must not rot

The real failure of "pin when needed" is not the pin. It is that forgotten pins accumulate until
"I never have to update" has quietly become "I never do update". So every pin carries a reason and a
date, and the report names stale ones:

```text
tyo3   pinned at 4870686 for 8 months   6 newer tags   reason: upstream PR #41
```

### Acceptance writes; it does not commit

`vendomat accept` writes the site's lock and stops. Version control stays the owner's workflow, and a
tool that commits on its own would collide with work in flight.

So the report carries the state that keeps an accepted change from going missing:

```text
pyjutsu   v0.22.0 → v0.23.0   candidate builds clean      available
gitman    v0.9.1  → v0.9.2    accepted, uncommitted       review and land
tyo3      pinned at 4870686   6 newer tags                stale pin
```

### The sweep sees pushed revisions only

The build host derives sites from pushed consumer revisions. Unpushed work is invisible by design.
`vendomat sweep --local` evaluates the working tree when the owner wants it.

A hand-edited lock or version field is refused at commit time by a git hook, not discovered later:

```nix
git-hooks.hooks.vendomat-drift = {
  enable = true;
  entry = "vendomat check-drift";
  language = "system";
  pass_filenames = false;
};
```

## 11. Release

The owner edits `vendomat.version`, or runs `vendomat release --minor`, which computes the next
number and writes it back into `devenv.nix`. The declaration drives everything downstream.

Vendomat never infers a version from a diff. Whether a change is `0.23.0` or `1.0.0` is a judgement
about meaning, and a tool that guesses gets it wrong in the costly direction.

Order is fixed, and section 8 makes it structural:

```text
write version fields → build → check → commit → tag → push → push bytes to Attic
```

Reverse this and a tag that cannot build enters the candidate stream. Every site then tries it and
fails, and the report fills with noise from a release that never worked.

**Declare the version write targets. Do not detect them.** A missed target ships metadata that
disagrees with its tag. Defaults cover `project.version` in `pyproject.toml` and `package.version`
in `Cargo.toml`. Do not write `__version__` into source; read it from installed metadata. A
hand-edited version field is drift, and section 10's hook refuses it.

## 12. Consent has three parts

Conflating these makes the design read more dangerous than it is.

| Consent | Who gives it | When |
| --- | --- | --- |
| A release exists | The owner, by declaring a version | Explicit |
| A candidate is built and cached | Granted in advance | Automatic |
| **A site adopts a version** | **The owner, by accepting** | **Always explicit** |

Only the third is manual. That is what licenses the sweep to be aggressive: build everything, cache
everything, change nothing.

## 13. Security: the tailnet is the boundary

One owner, one tailnet, no multi-tenancy. The complete model:

- one push token on the build host;
- one cache public key per consumer;
- both placed by hand, outside the Nix store and outside tracked files.

Nothing else. No secret manager, no token scoping, no authorization model. Replacing the manual
placement with a declarative secret tool is later work.

## 14. Failure model

| Failure | Required behaviour |
| --- | --- |
| Source hash mismatch | Block capture and publication. Report the identity failure. |
| Required source missing | Block publication. Report the coverage gap with a reason. |
| Candidate does not build | Record the log. The site keeps its last good resolution. |
| Project test fails | Record the failure. Publish nothing. Change no lock. |
| Attic upload fails | Keep the build locally. Report publication failure. |
| Attic unreachable | Build locally, or fail naming the cache dependency. |
| Attic reachable, path absent | A passing build is not evidence of a cache hit. Re-push. |
| Source store unavailable | Report the source dependency. Attic does not prove rebuildability. |
| Upstream prunes a pinned commit | The retention ref holds it. Report that upstream lost it. |
| Hand-edited lock or version field | The commit hook refuses it. Revert, or change the declaration. |
| Two mirrors claim one name | The sweep refuses. Rename one project. |
| Bad release already tagged | Release a new patch version. Never move the tag. |
| `build` set on a low-level package | Large rebuild, lost upstream cache hits. Revert to `upstream`. |
| Accepted change never committed | The report shows "accepted, uncommitted". |
| Sweep fails | Existing locks and environments stay usable. |

## 15. Where each tool stops

Lean on devenv for what a project is. Lean on NixOS for what a machine does. Do not cross over.

| Concern | Owner | Why |
| --- | --- | --- |
| Policy, outputs, tasks, tests, hooks | devenv | Typed module system, task DAG, hook wiring already exist |
| Substituters and trusted keys | NixOS | devenv exposes only Cachix; the daemon needs trusted-user rights |
| Attic server, storage, backups | NixOS | A system service, not a project service |
| The sweep timer | NixOS (systemd) | The sweep runs with no project context |
| Durable source retention | NixOS storage plus the source store | `.devenv` GC roots are per-project and gitignored. They are not retention. |

### The interface question, resolved

**Tasks are the pipeline. The CLI is only what must run without a project.**

The sweep is the one component that genuinely needs a standalone binary. `status`, `accept`, and
`check-drift` can be tasks in the Vendomat repository.

### Module delivery

The machine installs the Vendomat devenv module. A consumer declares no Vendomat input and carries
no Vendomat lock entry.

This is required, not preferred. A devenv import merges the whole imported `devenv.nix`, and an
imported project's `devenv.yaml` is not evaluated. A module shipped through an input cannot declare
its own inputs, so every consumer would have to copy Vendomat's input block, and one new input
would break every consumer at once. Expose a dedicated module file, never the repository root.

## 16. Phases

Each phase states a gate and a stop condition. A gate that can be relaxed under pressure is not a
gate, so every phase names what makes the work stop.

**P0 — Honest baseline.**
Record both machines, tailnet names, architectures, Nix versions, the build host, storage paths, and
backup destinations. State the policy for an Attic outage: build locally, or fail.
*Gate:* The verification suite is green, or every failure is recorded with a reason.
*Stop:* Do not start P1 against a red gate. No later phase can be verified against one.

**P1 — The producer output.**
One managed codebase declares `outputs.<name>` through `languages.*.import`. Build it. Run its tests.
*Gate:* `devenv build outputs.<name>` prints a store path, and `devenv test` passes.
*Stop:* If the importer cannot produce the artifact, decide now whether to hand-write a flake
package. Do not carry the question forward.

**P2 — Capture and prove retention.**
Capture the exact revision and the available build sources of P1's selected package. Record both
source record kinds. Expose nothing to consumers yet.
*Gate:* **With every upstream source host unreachable, the build host reproduces the same output
path from retained source alone.** If a build tool arrives from a binary cache, the report names it.
*Stop:* If coverage cannot be established for one package without a general Nix parser, stop and
reduce the claim. Do not write the parser.

**P3 — Durability.**
Run Nix garbage collection. Restore the source store from backup. Verify hashes. Rebuild.
*Gate:* Retained source survives collection, and a restored copy produces the same output path.
*Stop:* If restore needs an undocumented manual step, write it down before continuing.
Make both checks scheduled verifications, not milestones. A store that passed one restore test is
not a store that restores.

**P4 — Attic and a cold second machine.**
The build host pushes. The consumer machine declares the endpoint and trusted key in NixOS.
*Gate:* On the consumer, `nix path-info --store http://<cache> <path>` prints the path, and
`nix build -L` reports copying from the cache with no builder running.
*Stop:* If the consumer's store path differs from the build host's, the resolution is not shared.
Fix that before anything else.

**P5 — The keep-set.**
Compute one keep-set from active locks plus the recovery window. Apply it to both stores.
*Gate:* Deleting a candidate from Attic never removes source that an active lock still names.
Invariant 3 holds under a forced collection on both sides.
*Stop:* If the keep-set cannot enumerate active locks, fix the consumer list before deleting anything.

**P6 — Sites, candidates, and acceptance.**
Derive sites from native dependency files in two consumers. Sweep on a timer. Build candidates.
Report. `vendomat accept` writes a lock and stops.
*Gate:* A new tag appears as a built candidate without the owner asking. A broken candidate reports
its log and changes no lock. Acceptance creates no commit and triggers no build.
*Stop:* If the site list needs hand declaration, the derivation is wrong. Fix it here.
If acceptance needs a rebuild, verification and publication have come apart. Fix that here.

**P7 — Release from the declaration.**
`vendomat release --minor` writes the version back into `devenv.nix`, writes the declared targets,
builds, checks, commits, tags, pushes, and uploads, in that order.
*Gate:* A failed build produces no tag. The tag, the metadata, and the built artifact report one
version.
*Stop:* If a tag can be pushed before a passing build, the DAG is wrong. Fix the dependency edges.

**P8 — Pins, drift, and grounding mirrors.**
`pins.<lib>.commit` holds a site behind a retention ref. The drift hook refuses a hand edit.
`sources.<dep> = "mirror"` clones a third-party repository for reading.
*Gate:* A pinned site produces no candidate across two sweeps. Deleting the upstream branch does not
break the pin. A grounding mirror changes no `uv.lock` and no `pyproject.toml`. The stale-pin report
names a pin older than the stated window.

## 17. Verified against primary sources

- devenv tasks support `exec`, `cwd`, `package`, `before`, `after`, `wantedBy`, `status`,
  `execIfModified`, and `input`. `status` runs first and skips `exec` when it exits 0, restoring the
  previous successful run's outputs. `execIfModified` tracks timestamps and content hashes.
  `$DEVENV_TASK_INPUT`, `$DEVENV_TASK_OUTPUT_FILE`, `$DEVENV_TASKS_OUTPUTS`, and
  `$DEVENV_TASK_EXPORTS_FILE` carry data between tasks. `@succeeded` propagates failure;
  `@completed` does not. — <https://devenv.sh/tasks/>
- `outputs.<name>` accepts `config.languages.rust.import` (crate2nix) and
  `config.languages.python.import` (uv2nix). `devenv build outputs.<name>` prints Nix store paths,
  documented as suitable for consumption by other tools for distribution. — <https://devenv.sh/outputs/>
- devenv documents only `cachix.pull` and `cachix.push`. It exposes no option for an arbitrary
  substituter or trusted public key; those need Nix daemon configuration and trusted-user rights.
  — <https://devenv.sh/binary-caching/>
- `git-hooks.hooks.<name>` accepts `enable`, `name`, `entry`, `files`, `types`, `excludes`,
  `language`, and `pass_filenames`, so a custom local hook needs no external tooling.
  — <https://devenv.sh/git-hooks/>
- A devenv import merges the whole imported `devenv.nix`. An imported project's `devenv.yaml` is not
  evaluated, so a module delivered through an input cannot declare its own inputs.
- Nix `netrc-file` defaults to `/dummy/netrc`, and an untrusted user cannot add a substituter, so a
  user-level `attic use` does not configure the daemon.
- A flake lock transitively locks indirect inputs. `follows` re-points a dependency's input and
  changes the resulting store path.
- Attic's time-based garbage collection is disabled by default (`default-retention-period = 0`).
  Its retention reference point is undocumented.
- Jujutsu in a colocated repository sets Git `HEAD` to the parent of the working-copy commit. Nix can
  then fail to see a new file that a flake must read. Confirm Git sees a new file before building.

**Unverified:** whether a public Attic cache permits unauthenticated substitution in the current
release; whether `devenv build` composes with remote building on a separate build host.

## 18. Decisions recorded

| Decision | Choice |
| --- | --- |
| Centre of the design | Two byte stores with different properties |
| Source store | Core and permanent, not deferred |
| Attic over the tailnet | Core and permanent, not deferred |
| Publication records | A view over the stores and locks, never a stored table |
| Retention | One keep-set for both stores. Source covers cache. |
| Who fetches source at evaluation | The build host only. Consumers use upstream. |
| Source identity | Two record kinds: git object, fixed-output input |
| Where resolutions live | In each consumer repository, as its generated lock |
| Site list | Derived from native dependency files, never declared |
| Candidate gate | Build, then the project's own `devenv test` |
| Verification and publication | One act. Acceptance never rebuilds. |
| What acceptance does | Writes the lock. Never commits. |
| Drift | Refused by a commit hook, not reported after the fact |
| Policy format | A devenv module. No Vendomat configuration format. |
| Pipeline | A devenv task DAG. Ordering is structural. |
| Producer artifact | `outputs.<name>` through `languages.*.import` |
| Substituters and keys | NixOS `nix.settings`, per machine |
| Interface | Tasks are the pipeline. The CLI is the sweep. |
| Module delivery | Installed by the machine, never a flake input |
| Sweep visibility | Pushed revisions only. `--local` for the working tree. |
| Candidate source | Git tags. Commit pins are declarative overrides. |
| Security | The tailnet is the boundary. Two files, placed by hand. |
| Coverage auditing | One package first. Machine-wide is a later phase. |
| Fleet policy layer | Deferred. The module system makes it free when wanted. |

## 19. Not in scope

- Branch following, automatic promotion, and inferred version numbers.
- Candidates for third-party dependencies. Managed codebases only.
- Machine-wide source coverage auditing, and any full offline rebuild claim. That needs the retained
  build toolchain and its own proof.
- A general Nix expression parser.
- A new package format, a second package manager, a public index, or a general Nix module system.
- A runtime daemon, a resolver in the evaluation path, a graph database, or prediction.
- Secret management, token scoping, and an authorization model.
- A semantic capability layer, an action registry, and editor or shell adapters.

## 20. The shape in one place

```text
source store  ─┐
               ├─ one keep-set ─ no output outlives its source
attic         ─┘

declare → capture → build → check → publish → report → accept → lock
                              └── one act ──┘            └ the only manual gate
```

Vendomat stores bytes it cannot recreate and facts it cannot ask for. Everything else is a query.

> **Removing Vendomat must not make a repository's dependency state unintelligible.**

# Vendomat: managed source, automatic versions

**Status:** Proposed MVP architecture, 2026-10-04. Supersedes `CONCEPT.md` in this directory.
**Scope:** One owner's NixOS machines on a private tailnet. Personal use only.
**Basis:** Greenfield rewrite. The existing implementation defines no interface.

## 1. The idea

Vendomat keeps a clone of every codebase the system uses. It resolves a version for
each place a codebase gets used. The owner never writes a version pin and never bumps one.

Vendomat upgrades nothing on its own. It builds candidate versions in advance. It then
reports which upgrades are available. The owner accepts an upgrade or ignores it.

This removes the investigation and the bookkeeping, not the decision:

- The owner never works out which revision a repository should use.
- The owner never learns about an upgrade by accident.
- The owner never discovers a broken build after accepting it.

Consent stays with the owner, so nothing breaks without warning.

## 2. One loop

The producer side and the consumer side are one mechanism, entered from a declaration.

```text
vendomat.version = "0.23.0"     the owner declares a release
    → write pyproject.toml and Cargo.toml
    → build and check
    → commit, tag v0.23.0, push
    → the tag becomes a candidate for every site that uses this library
    → build the candidate per site
    → report the available upgrade
    → the owner accepts
    → Vendomat writes that site's lock. The owner reviews and commits it.
```

Every step after the declaration is generated or verified. The owner writes one line.

## 3. Vocabulary

| Term | Meaning |
| --- | --- |
| Managed codebase | A repository Vendomat versions, releases, and builds. The owner's own code. |
| Grounding mirror | A declared third-party repository, cloned for reading. Never an install source. |
| Site | One place a codebase gets used. Keyed by the consumer's declared name. |
| Resolution | The revision a site uses. Vendomat writes it into that repository's lock. |
| Candidate | A newer revision available to a site, with its build result. |
| Policy | The owner's rules about what Vendomat may select. |

## 4. Ownership

| Owner | Declares or holds |
| --- | --- |
| devenv (`vendomat` group) | Project name, version, pins, source modes, extra checks. |
| NixOS | Mirrors, sweep service, Attic, substituters, tailnet access, storage, backups. |
| Nix | Build recipes, derivations, store paths. |
| Attic | Output bytes over the tailnet. |
| Git tags | Release identity. A tag is the version. |
| Consumer repository | Its own generated lock, reviewed and committed by the owner. |
| Vendomat CLI | Resolve, build candidates, report, accept, release. All logic. |

One fact has one owner. The version lives in `devenv.nix`. `pyproject.toml`, `Cargo.toml`,
and the git tag are generated from it. A consumer's lock is generated from its resolution.

## 5. State

| State | Content | Lives | Written by |
| --- | --- | --- | --- |
| Mirrors | A clone per codebase. Retention refs for pinned commits. | Build host | Sweep |
| Sites | Each (consumer, dependency) pair. Derived, not declared. | Build host | Sweep |
| Candidates | Newer revisions per site, with build result and log. | Build host | Sweep |
| **Resolutions** | **The revision each site uses.** | **In each consumer repository, as its lock** | Accept |
| Machine artifacts | Toolchain closure and wheelhouse store paths. | Machine, from its NixOS generation | `nixos-rebuild` |

Resolutions live in the repository, not on the machine. A site's resolution is a property of
that site, not of whichever machine the owner is using. Keeping it in Git gives a reviewable
diff, per-repository rollback, and pure devenv evaluation over repository files.

Machine artifacts are different. The resolved toolchain closure and wheelhouse are installed
by the machine's NixOS generation, so their paths come from the machine.

**Derive the site list. Do not declare it.** A Python repository already names `pyjutsu` in
`[project.dependencies]`. Vendomat intersects that list with the codebases it manages.
Adding a dependency to the native file is the only action needed.

## 6. The owner's interface

The `vendomat` group in `devenv.nix` carries the whole owner-facing surface.

```nix
vendomat = {
  name    = "pyjutsu";                            # identity: this site's key. Required.
  version = "0.23.0";                             # this project's release. Producers only.
  provides = "templateer";                        # only when the package name differs.

  pins.tyo3 = {
    commit = "4870686";
    reason = "upstream PR #41";
  };

  sources.pydantic = "mirror";                    # see section 8.

  checks = [ "testee verify --mode quick" ];      # optional second promotion gate.
};
```

`name` is the only required field. A plain consumer writes one line.

`name` serves two purposes. It keys the site. It also tells Vendomat that this repository is
the source of a managed library, so the library stays editable here and is never vendored
into itself.

`devenv.nix` is a module system, so these options get types, defaults, and assertions for
free. A malformed pin fails at evaluation.

### Why a declared name, not an inferred one

A Git remote URL looks stable and is not. One remote has two spellings, `git@host:x/y.git`
and `https://host/x/y`. A repository rename, a host move, or a fork changes the key while the
project stays the same. A declared name is reviewed, lives in Git, and cannot drift.

Two worktrees of one repository share one name and one site. That is correct: they are one
project. Vendomat refuses when two different mirrors claim one name.

## 7. Policy and resolution

Two kinds of file, two owners.

**Policy** is authored, declarative, and committed. It states what Vendomat may select. The
default rule is implicit: take the newest tag. An override is explicit.

**The lock** is generated. Vendomat writes it. The owner reviews and commits it, and never
hand-edits it.

The invariant: **a resolution is always a function of (policy, mirror state, accepted
candidates).** Vendomat can recompute it at any time. A hand edit makes the recomputation
disagree, and Vendomat reports the drift.

Policy is read on every sweep. A pinned site produces no candidate. The pin therefore
survives re-resolution, which is what makes the declaration real.

Policy is per repository. A fleet-wide policy layer is deferred until a real fleet-wide hold
is needed. The precedence rule when it arrives: the repository wins.

### Candidate rules

| Rule | Behaviour |
| --- | --- |
| Newest tag (default) | Offer each new tag as a candidate. |
| `pins.<lib>.commit` | Hold this exact commit. Produce no candidate. |
| `pins.<lib>.hold` | Stay at the current resolution. Produce no candidate. |

There is no branch rule. Branch following returns both the churn and the irreproducibility
that tags prevent. To use a branch tip, pin the commit it points at. That is what the build
actually uses.

### Pins must not rot

Each override carries a `reason` and a date. The real failure of "pin when needed" is not the
pin. It is that forgotten pins accumulate until "I never have to update" has quietly become
"I never do update".

So the report names stale pins:

```text
tyo3   pinned at 4870686 for 8 months   6 newer tags   reason: upstream PR #41
```

The pin stays until the owner clears it. It stops being invisible.

### Pinned commits need retention

A tag is durable. An arbitrary commit is not. Upstream rebases, force-pushes, or prunes it,
and the pin becomes unresolvable. So Vendomat creates a retention ref in the mirror for every
pinned commit. Retention covers pinned commits and active resolutions, not every source input
on the machine.

## 8. Source tiers and where a dependency comes from

Vendomat mirrors every repository in the system, and declared third-party repositories too.
Two tiers, with different rights.

| Tier | What it is | Candidates | Install source |
| --- | --- | --- | --- |
| Managed codebase | The owner's own repository | Yes, from tags | Vendomat's build |
| Grounding mirror | A declared open-source repository | No | Unchanged |

This is the `kind = "project"` and `kind = "vendor"` split the existing `catalog.py` already
models. The distinction transfers.

### Per-dependency source mode

```nix
vendomat.sources = {
  tyo3     = "build";      # build from our mirror. A managed codebase.
  pydantic = "mirror";     # clone source for reading. Install is unchanged.
  openssl  = "upstream";   # default. Take the built bytes from a configured cache.
};
```

- `upstream` is the default. Declare nothing and nothing changes.
- `mirror` is cheap. It clones source for reading, searching, and agent grounding.
  **It never changes installation.** A grounding clone must not enter `pyproject.toml`,
  `[tool.uv.sources]`, or `uv.lock`. The existing `SOURCE_CATALOG.md` states this rule
  already, and it stays.
- `build` is expensive and has blast radius. See below.

### The blast radius of `build`

Building a dependency from your own mirror changes its derivation. Every derivation
downstream of it changes too. You then lose `cache.nixos.org` for that whole subtree.
Setting `build` on a low-level package such as `openssl` rebuilds most of the system.

Use `build` for your own code, and for a dependency you have a concrete reason to patch.
Nothing else.

### Binary caches are machine-level, not per-dependency

A cache is not a per-dependency choice. Nix takes a path from whichever configured
substituter holds it. So declare `cache.nixos.org`, any Cachix cache, and the tailnet Attic
once per machine in `nix.settings.substituters`.

The per-dependency axis is where **source** comes from. The substituter list is where
**bytes** come from. Keep them separate.

### Third-party candidates are deferred

A managed codebase gets candidates from its Git tags. A third-party Python dependency gets
its version from `uv.lock`, which uv resolves. Those are different mechanisms with different
gates.

The MVP generates candidates for managed codebases only. Driving `uv lock
--upgrade-package <name>` as a candidate source is a later extension, not part of this proof.

## 9. The gate

**Build success is the bar.** `nix build` of the candidate for that site must succeed.

This gate is correct for two reasons beyond its low cost.

First, **verification and publication are the same act.** The candidate build is the artifact.
It goes straight to Attic. No second build happens at accept time.

Second, Nix already caches it. A candidate shared by several sites builds once.

A site may declare extra checks. Vendomat runs them after the build as a second gate. The
default stays build-only. Use `checks` when an application earns more structure.

A failed candidate stays recorded with its log. The site keeps its last good resolution.
Sites therefore diverge onto different versions by themselves, which is the intent.

## 10. Accept

Accept writes the site's lock. **It does not commit.**

This repository routes version control through Gitman lanes. A tool that commits on its own
would bypass that workflow and could collide with an open lane. Writing the file keeps the
diff reviewable and leaves version control with the owner.

`vendomat status` therefore reports three states, so an accepted change cannot go quietly
missing:

```text
pyjutsu   v0.22.0 → v0.23.0   candidate builds clean      available
gitman    v0.9.1  → v0.9.2    accepted, uncommitted       review and land
tyo3      pinned at 4870686   6 newer tags                stale pin
```

## 11. Release

The owner edits `vendomat.version`, or runs `vendomat release --minor`, which computes the
next number and **writes it back into `devenv.nix`**. The command edits the declaration. The
declaration drives everything downstream.

Vendomat never infers a version from a diff. Whether a change is `0.23.0` or `1.0.0` is a
judgement about meaning, and a tool that guesses gets it wrong in the costly direction.

Order is fixed, because a pushed tag is permanent and immediately becomes a candidate:

```text
write version fields → build and check → commit → tag → push → push bytes to Attic
```

Reverse this and a tag that cannot build enters the candidate stream. Every site then tries
it and fails, and the report fills with noise from a release that never worked.

**Never move a tag.** Release `0.23.1` instead. A moved tag breaks the immutable identity
that every resolution depends on.

### Version write targets

Declare the targets. Do not detect them. A missed target ships a wheel whose metadata
disagrees with its tag.

Defaults cover the structured fields: `project.version` in `pyproject.toml` and
`package.version` in `Cargo.toml`. A repository may name extra targets.

Do not write `__version__` into source. Read it from installed metadata instead.

Vendomat applies the same drift check here. A hand-edited `pyproject.toml` version makes the
generator disagree, and Vendomat reports it instead of overwriting it.

## 12. Delivery

Attic serves outputs over the tailnet. The build host pushes to it.

Attic is correct here because the build host is a separate machine from the workstation. A
cache that serves only its own store would force building and serving onto one box.

| Consumer | Wiring |
| --- | --- |
| uv and Python | `UV_FIND_LINKS` points at the resolved wheelhouse. |
| Shared CLIs | The resolved closure on `PATH`, plus an environment variable for tasks. |
| Nix builds | The resolved store path, exposed for the repository's own derivations. |

Tasks read the environment variable, never `PATH`. An unrelated virtualenv can shadow a
selected tool when a task uses `command -v`.

Use HTTP over the tailnet. Tailscale already encrypts the traffic, and Nix accepts an HTTP
substituter. A certificate adds work and no security here.

### Security is deferred

The tailnet is the access boundary. This MVP builds no secret management, no token scoping,
and no authorization model.

Two files must still exist for the software to run at all: Attic's server token secret, and a
push token for the build host. Place them by hand, outside the Nix store and outside tracked
files. Replacing that with a declarative secret tool is later work.

### Cache retention

Start with no time-based collection. Attic disables it by default
(`default-retention-period = 0`), so this needs no configuration.

The target state is **version-based retention that Vendomat drives**: keep the newest N tags
per managed codebase, plus every output an active resolution names, and delete the rest.
Attic's own retention setting is time-based, so Vendomat must compute the keep set and delete
through Attic's API.

Version-based retention is the better target because it does not depend on Attic's retention
reference point, which the documentation does not state.

## 13. Module delivery

The machine installs the Vendomat devenv module. A repository declares no Vendomat input and
carries no Vendomat lock entry.

This is required, not a preference. devenv does not evaluate an imported project's
`devenv.yaml`. A module shipped through an input cannot declare its own inputs, so every
consumer must copy Vendomat's input block, and a new input breaks every consumer until each
is updated.

Expose a dedicated module file, never the repository root. A devenv import merges the whole
imported `devenv.nix`, so importing the root would give every consumer Vendomat's own shell.

## 14. The rules that keep this safe

1. **Evaluation never resolves.** `devenv.nix` evaluation is a pure function of
   (repository policy, the repository's own lock). No network, no Git, no resolver.
   Otherwise shell entry becomes slow and non-reproducible, and a resolver fault takes the
   shell down.
2. **Read machine state at task runtime, not at evaluation time.** Anything that can fail
   fails inside a task, where it does not take the shell with it.
3. **Generated files are never hand-edited.** Locks and version fields are outputs.
   Vendomat reports drift instead of overwriting it.
4. **Nothing is promoted without consent.** The sweep builds and reports. Accept is explicit.
5. **Accept never commits.** Gitman lanes stay the owner's workflow.
6. **A tag is immutable.** Resolution identity depends on it.
7. **A grounding mirror never becomes an install source.**
8. **Native commands keep working.** `nix build`, `git`, `uv`, and `attic` stay usable
   directly. Vendomat removes repeated work; it does not become the only path.

## 15. Failure modes

| Failure | Detection | Recovery |
| --- | --- | --- |
| Candidate does not build | Sweep records the failure and log | Site keeps its last good resolution. Report names the break. |
| Upstream prunes a pinned commit | Retention ref holds it | Mirror still resolves. Report warns that upstream lost it. |
| Attic unreachable | `nix store info --store <cache>` fails | Build from the mirror, or fail with a named cache dependency. |
| Attic reachable, path absent | `nix path-info --store <cache> <path>` | A passing build is **not** evidence of a cache hit. Re-push from the build host. |
| Source remote unreachable at evaluation | Evaluation error naming the input | The mirror supplies source over the tailnet. |
| Hand-edited lock or version field | Recomputation disagrees | Report the drift. Revert, or change the declaration. |
| Two mirrors claim one name | Sweep refuses | Rename one project. |
| Bad release already tagged | Candidate build fails per site | Release a new patch version. Do not move the tag. |
| `build` set on a low-level package | Enormous rebuild, lost upstream cache hits | Revert to `upstream`. See section 8. |
| Accepted change never committed | `vendomat status` shows "accepted, uncommitted" | Land the Gitman lane. |

## 16. Declarative and operational, stated honestly

**Declarative:** machine services, substituters, storage and backup paths, build recipes,
repository policy, source modes, project identity, and the declared version.

**Operational:** the sweep, candidate builds, accept, review and commit, tag and push, mirror
fetch, uploads, backup and restore, and activation. A declaration does not prove that an
operation succeeded.

Vendomat needs one always-on component: a daily job on the build host that fetches mirrors,
builds candidates, and writes the report. `vendomat sweep` runs the same job on demand.
Without the timer the owner has to go and ask, which is the burden this design removes. The
job mediates nothing at runtime.

## 17. Not in scope

- Machine-wide source coverage auditing, or proving a full offline rebuild.
- Candidates for third-party dependencies. The MVP covers managed codebases only.
- A semantic capability layer, action registry, context model, or editor and shell adapters.
  That is a separate concern and belongs in its own repository.
- A public package index, a second package manager, or a general Nix module system.
- A runtime daemon, a context server, a graph database, or prediction.
- Secret management, token scoping, and an authorization model.
- A fleet-wide policy layer.
- Branch following, automatic promotion, and inferred version numbers.

## 18. MVP phases

Each phase has one proof gate and one stop condition. Never pass a substitution gate on a
passing build alone.

**P0 — Clear the ground.**
Resolve or deliberately delete `test_every_first_party_input_is_pinned_to_a_tag`
(project 08) with a recorded reason. That test is this design's core invariant, so its
failure matters. Record machines, tailnet names, architectures, Nix versions, and the build
host.
*Gate:* Testee green on an honest baseline.
*Stop:* Do not start P1 with a red gate. No later phase can be verified against one.

**P1 — One mirror, one site, the uv bridge.**
Mirror one library. Build its wheelhouse. Prove `UV_FIND_LINKS` installs the prebuilt wheel
in a real consumer.
*Gate:* `uv sync` compiles no Rust, and the wheel version matches the tag.
*Stop:* If the wheel cannot satisfy uv's resolution, stop. This is the project's real risk,
so it comes first.

**P2 — Resolution as a generated lock.**
Declare `vendomat.name` in two consumers. Derive the site list from their native dependency
files. Generate each consumer's lock from its resolution.
*Gate:* Vendomat recomputes identical locks from policy and mirror state. A hand edit is
reported as drift, not overwritten.
*Stop:* If the site list needs hand declaration, the derivation is wrong. Fix it here.

**P3 — Attic, and a cold second machine.**
Build host pushes. Consumer machine declares the endpoint and trusted key.
*Gate:* On the consumer, `nix store info --store http://<cache>` succeeds,
`nix path-info --store http://<cache> <path>` prints the path, and `nix build -L` prints
`copying path ... from 'http://<cache>'` with no builder running.
*Stop:* If the consumer's store path differs from the build host's, the resolution is not
actually shared. Fix that before anything else.

**P4 — The sweep, the report, and accept.**
Daily job: fetch mirrors, find new tags, build candidates per site, record results.
`vendomat status` reports available upgrades, failures, stale pins, and uncommitted accepts.
`vendomat accept` writes the lock and stops.
*Gate:* A new upstream tag appears as a built candidate without the owner asking. A broken
candidate reports its log and changes no lock. Accept creates no commit.
*Stop:* If accept needs a rebuild, verification and publication have come apart. Fix it.

**P5 — Release from the declaration.**
`vendomat release --minor` writes the version back into `devenv.nix`, writes the version
fields, builds, commits, tags, pushes, and uploads, in that order.
*Gate:* A failed build produces no tag. The tag, `pyproject.toml`, and the built wheel all
report one version.
*Stop:* If a tag can be pushed before a successful build, stop and fix the order.

**P6 — Pins, overrides, and grounding mirrors.**
`pins.<lib>.commit` holds a site, with a retention ref protecting the commit.
`sources.<dep> = "mirror"` clones a third-party repository for reading.
*Gate:* A pinned site produces no candidate across two sweeps. Deleting the upstream branch
does not break the pin. A grounding mirror changes no `uv.lock` and no `pyproject.toml`.

**P7 — Cut over.**
Remove the old implementation, its tests, and its documentation. Rewrite `README.md` and
`AGENTS.md`.
*Gate:* No sibling repository imports a removed interface. Testee green. P3 and P4 repeated
after deletion.
*Stop:* Do not delete before P4 passes.

## 19. Verified against primary sources

- devenv tasks support `exec`, `before`, `after`, `status`, `cwd`, and `input`, with
  `$DEVENV_TASK_OUTPUT_FILE` for structured output. Failure propagates through `@succeeded`.
- devenv imports merge the whole imported `devenv.nix`. An imported project's `devenv.yaml`
  is not evaluated.
- Nix `netrc-file` defaults to `/dummy/netrc`. An untrusted user cannot add a substituter,
  so a user-level `attic use` does not configure the daemon.
- A flake lock transitively locks indirect inputs. `follows` re-points a dependency's input
  and changes the resulting store path.
- Attic's time-based garbage collection is disabled by default
  (`default-retention-period = 0`). Its retention reference point is undocumented.
- Jujutsu in a colocated repository sets Git `HEAD` to the parent of the working-copy commit.
  Nix can then fail to find a new file that a flake must read. Confirm Git sees a new file
  before building.

**Unverified:** Attic's retention semantics; whether a public Attic cache permits
unauthenticated substitution in the current release.

## 20. Decisions recorded

| Decision | Choice |
| --- | --- |
| Where resolutions live | In each repository, as its generated lock |
| What accept does | Writes the lock. Never commits. |
| Mirror scope | Every repository, plus declared third-party source |
| Third-party install source | Unchanged by default. `mirror` grounds, `build` is opt-in. |
| Cache retention | None now. Version-based with pinned resolutions later. |
| Fleet policy layer | Deferred until a real fleet-wide hold is needed |
| Sweep frequency | Daily timer, plus `vendomat sweep` on demand |
| Candidate source | Git tags. Commit pins are declarative overrides. |
| Security | Deferred. The tailnet is the boundary. |

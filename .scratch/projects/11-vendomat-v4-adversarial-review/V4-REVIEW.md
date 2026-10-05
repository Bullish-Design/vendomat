# Vendomat V4 adversarial review

**Date:** 2026-10-04.
**Method:** Falsification. Each finding tries to break the design, not to confirm it.
**Baseline:** the three files named in [BASELINE.md](./BASELINE.md), at their recorded hashes.
**Sources:** primary vendor documentation, fetched 2026-10-04, plus this repository's current code.

Abbreviations on first use: Simplified Technical English (STE), Home Manager (HM),
continuous integration (CI), Secure Shell (SSH).

## Owner answers obtained during this review

The owner answered three questions on 2026-10-04. This review applies the answers and
records them as new decision IDs.

| New ID | Question | Owner answer |
| --- | --- | --- |
| D-ATTIC-SCOPE | What need does Attic-only complete-closure retention serve? | Avoid laptop rebuilds. Public caches may legitimately serve upstream paths. |
| D-SRC-ACCESS | Is the source store a plain directory or a service? | A plain directory, read over SSH. No daemon. |
| D-PROOF-SPLIT | Which fixture carries the first proof? | Both, split by role. The `*man` toolchain carries delivery, closure, and publication. The Neovim application carries composition and application behavior. |

D-ATTIC-SCOPE revises CONCEPT-V4 §13, invariant 11, and §21 item 11. Those texts were
not among the five accepted decisions, so this review applies the revision directly.

## Verdict first

The fact-separation model is V4's real contribution. Keep it. The document correctly
splits source retention, source correspondence, rebuild proof, check pass, current cache
availability, dependency acceptance, and activation into seven independent results. No
simpler design reproduces that, and the surrounding tools do not supply it.

Three structural problems block a V4 implementation-guide session as the documents stand:

1. V4 claims an ownership role that this repository's own `AGENTS.md` assigns to RepoMan.
2. V4's required-check system rests on a devenv mechanism that does not exist.
3. V4 treats work this repository already ships as unbuilt design that needs new experiments.

All three have cheap corrections. This review applies them to the revised documents and
names the two that need an owner decision.

## Severity scale

| Severity | Meaning |
| --- | --- |
| S1 | Blocks a sound implementation guide. The design is wrong, unowned, or rests on a mechanism that does not exist. |
| S2 | Material. The guide would encode a false technical claim or an untestable gate. |
| S3 | Requirement-level defect. Covered individually in [V4-REQUIREMENT-AUDIT.md](./V4-REQUIREMENT-AUDIT.md). |

---

## S1 findings

### F-01 — Vendomat does not own composition; `AGENTS.md` assigns that role to RepoMan

**Location.** `CONCEPT-V4.md:13`: "Vendomat helps the owner compose a personal system from
reusable devenv-based modules." Also §2 row "Main composition interface", §3 Vendomat row,
and `V4-SPEC.md` §1 decision 1.

**Counterexample.** This repository's `AGENTS.md` states: "It is not the composition
framework, manifest owner, or workspace orchestrator; those roles belong to RepoMan,
`repoman.lock`, and the surrounding fleet tools." `docs/DESIGN.md:113-114` repeats it:
"Not a composition framework — **repoman** is. Not a manifest/registry —
**`repoman.lock`** is." `docs/DESIGN.md:13-15` records the reason: "The composition
framework vendomat seemed to want **already exists**: it's `repoman` ... vendomat should
**not** re-invent composition, a manifest, or a registry."

**Failure scenario.** V4 §16 gives Vendomat "composition inspection" as an initial command
responsibility. RepoMan is already the per-repo lifecycle front door and `repoman.lock` is
already the module manifest. A consumer changes `repoman.lock`. Two tools now answer "what
is composed in this repository", from two different inputs, with no tie-break rule. The
first disagreement has no owner.

**Architectural consequence.** V4 either absorbs RepoMan's role — an unstated scope
expansion that breaks the fleet's one-owner rule, which is V4's own §3 premise — or it
duplicates it. V4 §3 omits RepoMan from the ownership table entirely, which is how the
conflict stayed invisible.

**Recommended correction.** Add RepoMan to the §3 ownership table as the owner of
per-repo composition and the module manifest. Restate V4's purpose as its two core
services plus the native-artifact face it already owns. Keep composition *reporting* in
Vendomat only where Vendomat reads native evaluation and attributes nothing to itself.

**Evidence needed.** Owner decision. This review does not delete V4 §1's purpose
sentence; it marks it `[OWNER DECISION]` and adds the RepoMan ownership row, because
removing V4's stated purpose is the owner's call, not the reviewer's.

### F-02 — D-CHECK-OWNER has no native carrier; devenv has no output-bound required check

**Location.** `CONCEPT-V4.md:569`: "Vendomat consumes those outputs and their declared
checks", citing [devenv outputs](https://devenv.sh/outputs/). `V4-SPEC.md` §6: "The
required set is the union of default checks from enabled modules and checks added by the
consumer." Requirements V4-CHK-005, V4-CHK-008 through V4-CHK-012, V4-CHK-014,
V4-CHK-015.

**Counterexample.** [devenv outputs](https://devenv.sh/outputs/) documents
`outputs.<name>` as derivations built with `devenv build outputs.<name>`. It documents no
check concept at all. [devenv tests](https://devenv.sh/tests/) documents exactly one test
mechanism: `enterTest`, a Bash script attribute, run by `devenv test`. Binding a test to
an output, a module declaring required checks that a consumer inherits, and check coverage
reporting are all absent from that page. The cited source does not support the claim made
beside it.

**Failure scenario.** P4 begins. A module author wants to declare "my editor integration
check gates the review output." There is no option to write that in. `enterTest` merges
into one shell script with no check names, no per-check results, and no output binding.
Vendomat must therefore invent a check registry — which V4 §16 forbids: "There is no
second general workflow engine", and P-CHECK-COVERAGE asks for coverage "without a new
test language".

**Architectural consequence.** Eleven of fifteen CHK requirements, and the accepted
D-CHECK-OWNER decision itself, rest on a mechanism that does not exist. V4's own boundary
prohibits the only escape it left itself.

**Recommended correction.** Name **devenv tasks** as the carrier. Tasks are named, declare
`before`/`after` prerequisites, and return per-task exit codes. This repository already
does exactly this: `nix/testee.nix` exports `testee:quick`, `testee:detailed`,
`testee:ci`, and `testee:doctor`; `devenv.nix` exports `vendomat:lint` and
`vendomat:test`. The smallest contract is: a module exports gate tasks in its own
namespace and declares a list of gate task names; the consumer appends task names;
Vendomat runs the union against the frozen selection and records each task name with its
result. This adds no runner and no test language.

Second, defer to the existing *man gate. `gitman.toml` already declares
`[publish] verify = ["devenv", "shell", "testee", "verify", "--mode", "ci"]`, and the
`testee` skill states "This repository uses **Testee** as its single verification
interface." The *man-family default required check already exists and already runs before
publication. V4 must name it, not define a parallel one.

**Evidence needed.** A P4 fixture in which two modules contribute named gate tasks, a
consumer adds one, and the receipt records each task name, its origin, and its result.

### F-03 — Attic-only complete-closure retention bought nothing the owner wants

**Location.** `CONCEPT-V4.md:520`: "For a selected published output, retain its complete
runtime closure in Attic. This includes runtime dependencies previously obtained from
public caches." Also `CONCEPT-V4.md:937` invariant 11, §21 item 11, `V4-SPEC.md` §1
decision 3 and §6. Requirements V4-CACHE-002, V4-CACHE-003, V4-CACHE-004, V4-PROOF-006,
experiment P-ATTIC.

**Counterexample.** The [Attic CLI reference](https://docs.attic.rs/reference/attic-cli.html)
documents `--upstream-cache-key-name <NAME>`: "The signing key name of an upstream cache.
When pushing to the cache, paths signed with this key will be skipped by default." Attic's
designed default is to skip upstream-signed paths. V4 required the opposite and called the
conflict an open experiment. Defeating it needs
`--ignore-upstream-cache-filter`: "Ignore the upstream cache filter."

Owner answer D-ATTIC-SCOPE: the need is that the laptop does not rebuild. Public caches
may serve upstream paths.

**Failure scenario.** P5 runs as written. The fixture must pass
`--ignore-upstream-cache-filter` and re-upload glibc, Python, and every compiler path into
private storage, for a laptop that already trusts `cache.nixos.org` and would have fetched
them anyway. The hardest gate in the plan fights the cache's default design to satisfy a
requirement the owner does not hold.

**Architectural consequence.** The most expensive P5 gate is removable. With it goes the
storage measurement that P-STORAGE was created to justify.

**Recommended correction.** Replace "complete runtime closure" with "every closure path
that no trusted configured substituter already serves". The observable claim becomes: the
cold laptop realizes the selected output path and performs no build. Keep
`--ignore-upstream-cache-filter` as an explicit, measured opt-in for a later
disconnected-operation goal. Retire V4-CACHE-003 to a measurement; rewrite V4-CACHE-002
and V4-CACHE-004; revise invariant 11 and §21 item 11.

**Evidence needed.** None for the removal. A P5 fixture must still show zero builds on the
cold consumer and must name which substituter served each path.

### F-04 — V4 declares greenfield, but a machine-installed consumer module and a live generation lifecycle exist

**Location.** `CONCEPT-V4.md:68`: "The current Vendomat implementation supplies no
compatibility requirements." Also §23's exclusion of "A custom deployment planner or
rollback implementation", and V4-OWN-011.

**Counterexample.** `modules/devenv.nix` documents two live delivery shapes. One is
installed by the machine's NixOS module at
`/run/current-system/sw/share/vendomat/consumer-module.nix`, resolving store paths from an
installed `machine.json`. The other is named in the file as "Input delivery (the
compatibility fallback) ... Kept for one release." `src/vendomat/plane.py` states:
"Machine-level Devman plane generations. Vendomat owns this lifecycle." The CLI exposes
`vendomat plane plan`, `update`, `rollback`, `show`, and `recover`.

**Failure scenario.** The first V4 machine generation ships. A machine that already
installs the consumer module keeps reading `machine.json` for a `wheelhouse`, `cli`,
`toolchain`, and `vendor_root` that the V4 package no longer defines. Evaluation throws
from the `machineValue` branch in `modules/devenv.nix`. Separately, `vendomat plane` and
the devman plane integration disappear with no stated replacement, while V4 §23 forbids
Vendomat from owning a plan or rollback at all.

**Architectural consequence.** "No compatibility requirements" is false for the installed
module path and for `plane`. The module's own text promises a one-release window that V4
does not honor.

**Recommended correction.** Add one P0 requirement that inventories the current consumer
surface — `vendomat.toml` faces, `machine.json`, `plane`, `publish`, `vendor sync`,
`install-hook` — and records, per surface, keep, replace, or retire with a window. Do not
design the migration in the concept. Name the owner and the decision point.

**Evidence needed.** Owner decision on `vendomat plane` and the devman plane. V4 §23 and
the existing code cannot both stand.

### F-05 — V4 replaces a working non-Nix distribution channel with a Nix-only one, silently

**Location.** `CONCEPT-V4.md:511`: "Attic is the owner's primary binary distribution
service." Also §2 row "Binary distribution".

**Counterexample.** `README.md` records the existing channel and the decision behind it:
"`vendomat publish <lib>` uploads that exact store file to the library's GitHub release.
One build, one artifact, two indexes — the store and the release URL — which therefore
cannot disagree." And: "For every other case the consumer declares the release URL in
`[tool.uv.sources]` and needs no Nix, no vendomat, and no flake input. gitman project 35
settled that: a published, hashed wheel referenced by URL is what makes a tool adoptable
in a repo that has never heard of Nix, and this repo does not replace it."

**Failure scenario.** Attic serves Nix store paths to Nix clients. A repository that has
never heard of Nix cannot substitute from Attic. If Attic becomes the distribution
boundary, that adoption path ends, and a settled decision is reversed without a statement.

**Architectural consequence.** V4 narrows Vendomat's reach while appearing only to add a
cache.

**Recommended correction.** State both channels in §13 with distinct audiences and one
shared build: Attic distributes store paths to Nix consumers; the GitHub release URL plus
hash distributes wheels to non-Nix consumers. Add a requirement that publication keeps the
two indexes in agreement, which `README.md` already names as the governing rule.

**Evidence needed.** None. The correction records existing behavior.

---

## S2 findings

### F-06 — Substituter priority is advertised by the cache, not chosen by the consumer

**Location.** `CONCEPT-V4.md:541` consumer preference chain. Requirement V4-CACHE-010.

**Counterexample.** [Nix configuration](https://nix.dev/manual/nix/2.35/command-ref/conf-file.html):
"Substituters are tried based on their priority value, which each substituter can set
independently. Lower value means higher priority." The client supplies the list; the cache
supplies the priority.

**Failure scenario.** The P5 fixture lists Attic first and concludes "Attic-first is
proved". Nix instead orders by advertised priority. `cache.nixos.org` advertises 40. If the
Attic cache does not advertise a lower value, the public cache wins and the fixture
measured nothing.

**Correction.** Name cache-advertised priority as the control and assign it to Attic and
NixOS configuration. Rewrite V4-CACHE-010 to read both caches' advertised priority, then
observe which one served each path.

### F-07 — The preference chain's last step is off by default

**Location.** `CONCEPT-V4.md:541` chain step "build from native inputs when allowed".
Requirement V4-CACHE-011.

**Counterexample.** Nix configuration, `fallback`: "If set to `true`, Nix falls back to
building from source if a binary substitute fails. This is equivalent to the `--fallback`
flag. The default is `false`."

**Failure scenario.** Attic is down and a path is missing from the public cache. With
default settings Nix does not build from source; it fails. The documented V4 chain never
reaches its last step.

**Correction.** State that the build-fallback step needs `fallback = true` explicitly, and
record it in the P0 policy. The documentation does not define unreachable-substituter
behavior, so keep that as a `[PROTOTYPE]` fact.

### F-08 — devenv Machines `apply` copies outputs; documentation already answers P-MACHINES

**Location.** `CONCEPT-V4.md` §10: "The first machine integration must observe whether the
native copy operation actually substitutes through Attic." Requirement V4-MACH-008,
experiment P-MACHINES.

**Counterexample.** [devenv Machines](https://devenv.sh/machines/): plan "builds outputs
and records the NixOS system, access facts, and store closure changes"; apply "uses those
exact outputs without rebuilding, checks that the machine still matches the plan, copies
all outputs, then activates them". Transfer uses `nix copy`. Nix's separate
`builders-use-substitutes` setting exists for the inverse case, which shows that
substitute-instead-of-copy is an explicit opt-in, not a default.

**Failure scenario.** P7 is scheduled to discover a fact the documentation states. The
real open question is different: whether the pinned version can be made to prefer a
target-side substituter at all.

**Correction.** Restate V4-MACH-008 as: evidence records the transfer path as a direct
copy unless the pinned version documents a substituter route. Narrow P-MACHINES from
"observe whether" to "determine whether target-side substitution is configurable; if not,
record Attic as the laptop's interactive path and not the deployment path."

### F-09 — The Home Manager recovery row assumes standalone HM and is false in NixOS-module mode

**Location.** `V4-SPEC.md` §7 recovery table, HM row. Requirements V4-MACH-009,
V4-MACH-013. `CONCEPT-V4.md` §10.

**Counterexample.** [Home Manager activation](https://nix-community.github.io/home-manager/internals/activation.html):
"in some cases we may not have a `home-manager` profile at all!" — "This is the case when
Home Manager is used as a NixOS or nix-darwin module, in these cases the system profile
will contain references to the corresponding Home Manager configurations." The page
documents no rollback mechanism and makes no atomicity statement.

**Failure scenario.** V4-MACH-013 asserts "NixOS rollback does not report Home Manager
files as restored". Under the NixOS-module mode there is no separate HM profile and the
system profile references the HM configuration, so a system rollback can move HM
configuration with it. The requirement would assert a falsehood on that host.

**Correction.** Record the HM integration mode as a P0 decision. devenv Machines treats
`nixos` and `home-manager` as separate roles, which implies standalone HM. State that
assumption, and make V4-MACH-013 conditional on it. Mark HM rollback `[PROTOTYPE]`: no
primary source documents it.

### F-10 — V4-CACHE-002's verification names a capability the Attic CLI does not document

**Location.** V4-CACHE-002 method: "Enumerate closure and query each path against Attic
alone."

**Counterexample.** The Attic CLI reference documents no command for querying whether a
path is present in a cache.

**Correction.** Name the mechanism: `nix path-info --store <attic-endpoint>` per path, or
substitution into an isolated store with every other substituter and builds disabled.
`V4-SPEC.md` §6 already says "query or substitute"; the requirement must match the spec.

### F-11 — Cross-project profile behavior is already documented as unsupported

**Location.** `CONCEPT-V4.md` §8, requirement V4-MOD-014, experiment P-PROFILES.

**Counterexample.** [devenv polyrepo](https://devenv.sh/guides/polyrepo/): "Profiles don't
work with cross-project references." The same page documents a third delivery route V4
omits: `inputs.<name>.devenv.config.<attr>`, for referencing another project's
configuration and outputs "without full merging".

**Correction.** Record the documented limitation instead of scheduling an experiment to
find it. Reduce the P2 matrix to paths where profiles can work. Add the
`inputs.<name>.devenv.config` route to §8 as a documented third option, because it may
remove the need for the flake-backed export in some cases.

### F-12 — The Neovim proof under-tests the claims P5 depends on

**Location.** `CONCEPT-V4.md` §21, §22 phase table.

**Counterexample.** A review command plus Lua has a small closure and no native build.
P5's gates concern closure coverage, closure size, and native output identity. This
repository already contains a better fixture: `lib/mkMaturinWheel.nix` builds a real Rust
extension wheel; `flake.nix` composes six uv2nix command packages into
`repoman-toolchain-core`; `nix/consumer-module-check.nix` and
`tests/test_store_consumer_e2e.py` already exercise a real consumer shell, which
`AGENTS.md` gates behind `VENDOMAT_E2E=1`.

**Owner answer D-PROOF-SPLIT.** Both fixtures, split by role.

**Correction.** The `*man` toolchain carries P2 and P4 through P6: delivery, exact
selection, checked output, closure, and cold consumption. The Neovim application carries
P1 and P3: module contract, target defaults and overrides, editor integration, and source
correspondence. Split §21's success list and §22's phase table accordingly.

### F-13 — Module-import evaluation cost is a measured constraint V4 omits

**Location.** `CONCEPT-V4.md` §4, §7, §9.

**Counterexample.** `README.md`: "**A repo that enables no face must not import the module
at all** — it pays a flake input's evaluation and an `install-hook` probe per shell entry
for no output."

**Failure scenario.** V4 encourages broad composition and defaults components to enabled
once a target is selected. Each import costs evaluation on every shell entry. The owner
already measured this cost and wrote a rule against it. V4 does not mention it.

**Correction.** Add one concept line: composition breadth has an evaluation cost, and the
fixture measures it. Add one requirement: an enabled-but-unused contribution adds no
shell-entry work.

### F-14 — `--unshare-*-try` options silently degrade isolation

**Location.** `V4-SPEC.md` §9 sandbox paragraph. Requirement V4-APP-016.

**Counterexample.** [bwrap](https://github.com/containers/bubblewrap/blob/main/bwrap.xml)
describes itself as "an unprivileged low-level sandboxing tool", states "the user
namespace is required if bwrap is not run as root", and documents that
`--unshare-user-try` and `--unshare-cgroup-try` "skip it" when namespace creation fails.
A `--not-a-security-boundary` option exists to declare the opposite intent.

**Failure scenario.** The conditional module uses a `-try` variant for convenience.
Namespace setup fails on one host. The process starts with weaker isolation and reports
success. V4-APP-016 ("Required sandbox setup failure prevents an unsandboxed launch")
passes its own test while the guarantee is gone.

**Correction.** State that required isolation uses the non-`try` options, and that the
wrapper records which namespaces it actually created. Keep this in the conditional module.

---

## Claims tested explicitly

The task named nine claims. Each verdict below cites its source.

| Claim | Verdict | Evidence |
| --- | --- | --- |
| A Jujutsu change ID is not immutable file-content identity; execution needs one full commit ID. | **Confirmed.** | [jj glossary](https://github.com/jj-vcs/jj/blob/main/docs/glossary.md): "Rewriting a commit results in a new commit, and thus a new commit ID, but the change ID generally remains the same." "A divergent change is a change that has more than one visible commit." "A commit ID is a unique identifier for a commit. They are 20 bytes long when using the Git backend." Sharpening: a commit ID identifies a commit, not a tree. Two commits can share one tree. Admission pins the commit ID; a content claim needs the tree identity, which `V4-SPEC.md` §9 already records separately. |
| A commit is not a btrfs snapshot; materialization needs an adapter and a verified identity mapping. | **Confirmed.** | [btrfs subvolume](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html): "A snapshot is also subvolume, but with a given initial content of the original subvolume." A snapshot's source is a btrfs subvolume. A commit is not one. Also "A snapshot is not a backup". Sharpening: identity is the subvolume UUID plus subvolume ID; "Inode number is not a filesystem-wide unique identifier" and a subvolume root is always inode 256, so inode numbers are not identity. |
| Attic distributes Nix paths, not btrfs images or mutable state. | **Confirmed.** | Attic CLI: `attic push [OPTIONS] <CACHE> [PATHS]...`, where `[PATHS]` are "The store paths to push". Nothing else is transferable. |
| Bubblewrap runs isolated processes; it does not build or activate NixOS generations. | **Confirmed.** | bwrap: "bwrap is an unprivileged low-level sandboxing tool"; its options are bind mounts and namespaces. See also F-14. |
| NixOS, HM, application state, source retention, btrfs images, Attic, and evidence have separate recovery outcomes. | **Confirmed, with one correction.** | devenv Machines: "The roles are separate activations. If home-manager fails after NixOS succeeds, the NixOS deployment remains applied. NixOS rollback does not revert home-manager files." The correction is F-09: this holds for standalone HM only. |
| A local run must work without a live Vendomat service or Attic. | **Confirmed and now cheaper.** | Owner answer D-SRC-ACCESS removes the networked read service. The existing `~/vendor` plain-directory store (`docs/SOURCE_CATALOG.md`) already satisfies it. |
| Required-check failure, missing required checks, and nonrequired coverage gaps have distinct outcomes. | **Sound as semantics, unimplementable as written.** | See F-02. The three outcomes are correct. devenv supplies no mechanism to name, attribute, or bind the checks they classify. |
| A complete Attic publication claim requires a verified runtime closure, including paths first obtained from public caches. | **Technically true, and now out of scope.** | Attic's `--upstream-cache-key-name` skips upstream-signed paths "by default"; `--ignore-upstream-cache-filter` defeats it. Owner answer D-ATTIC-SCOPE removes the requirement. See F-03. |
| Machines plans, transfer, activation, and rollback remain native responsibilities. | **Confirmed.** | devenv Machines documents `plan`, `apply`, `status`, `rollback`, plan storage under `.devenv/machine-plans/<id>/`, staleness from "A changed NixOS generation or target definition", and a watchdog with a "default deadline is 300 seconds" that "cannot fix an early boot failure, reverse application data changes, or undo side effects of activation scripts". V4 correctly claims none of this. |

One further verified claim worth recording: V4's build-versus-runtime graph distinction is
documented. [Nix store query](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query):
"To obtain a build-time dependency graph, apply this to a store derivation. To obtain a
runtime dependency graph, apply it to an output path." And V4 §6's Neovim claim is
documented: [pack.txt](https://github.com/neovim/neovim/blob/master/runtime/doc/pack.txt)
confirms a package "can contain multiple plugins that depend on each other", loaded from
`pack/*/start` or on demand from `pack/*/opt` with `:packadd`. Note that `vim.pack` is a
Git-based plugin manager that wants semver tags and owns `site/pack/core/opt`; it is the
wrong carrier for Nix-delivered files. Use the `pack/*/start` and `pack/*/opt` layout.

---

## Overall architecture assessment

### What survives falsification

The seven-way fact separation (§15, invariant 9) is correct, useful, and unavailable from
any native tool. Nix knows what a path depends on. Attic knows what it holds now. Neither
records that a named check passed against a frozen selection, nor that retained source
corresponds exactly to that selection. That gap is real and V4 fills it.

The ownership table (§3) is the right instrument, and the failure-behavior table (§20) is
unusually complete for a design document. The refusal to build a resolver, a second lock,
an action registry, or a deployment engine is correct and consistently held.

### What does not survive

V4 reads as a design written without reading the repository it rewrites. Four components it
presents as new design already exist here:

| V4 presents as new | Already shipped |
| --- | --- |
| A consumer-maintained capture list, pending experiment P-CAPTURE-LIST | `vendor/python/*.toml`, validated by `src/vendomat/catalog.py`, with `name`, `kind`, `repository`, and a 40-hex immutable `rev` |
| A source store with identity records | `~/vendor/<package>/` plus the generated `.vendomat/sources.toml` map, documented in `docs/SOURCE_CATALOG.md` |
| The separation of inspection source from installed software | Already enforced: "these checkouts are for agent grounding and investigation, not Python installation" |
| The correspondence-versus-selection distinction | Already stated: "The revision identifies reference source; compare the separately resolved installed version and origin in `uv.lock` before treating it as runtime truth" |

P-CAPTURE-LIST is not an open experiment. It is answered by shipped, tested code. The P3
phase should extend that code and add correspondence labels, not re-derive the design.

### The simpler native-tool-only alternative

Subtract everything another tool already owns:

| Concern | Native or existing owner | Vendomat addition |
| --- | --- | --- |
| Composition and module manifest | RepoMan, `repoman.lock`, devenv imports | None (F-01) |
| Required checks and the pre-publish gate | devenv tasks, testee, `gitman.toml [publish] verify` | A named gate-task set bound to a frozen selection (F-02) |
| Source capture and lookup | `vendor/python/*.toml`, `vendomat vendor sync`, `~/vendor` | Correspondence labels and capture status |
| Dependency selection | Native declarations and locks | None, by design |
| Machine plan, transfer, activation, rollback | devenv Machines | Evidence links to the plan ID |
| Binary transfer between two machines | `nix copy --to ssh-ng://laptop` | None required |
| Non-Nix consumer distribution | GitHub release URL plus hash | None (F-05) |

After the subtraction, exactly three things remain that nothing else supplies:

1. A publication receipt binding a frozen selection to named check results and a
   current cache-availability check.
2. Correspondence and capture-status labels on retained source.
3. The closure-coverage check for the paths Attic must actually serve.

That is a small, defensible Vendomat. It is also roughly what V4 §15 already describes.
The rest of V4 is either owned elsewhere or already built.

### On Attic specifically

For a two-machine owner, `nix copy --to ssh-ng://laptop <path>` moves a closure with no
service, no signing key management, and no upstream filter. Attic earns its place in two
cases: the laptop pulls when the desktop is not reachable at that moment, and the consumer
count grows beyond two. Both are plausible, so this review does not recommend removing
Attic.

It does recommend demoting it. Make P5's gate "the cold laptop realizes the selected
output and performs no build". Attic is then the normal mechanism, and `nix copy` is the
fallback that proves the need is met even if the Attic fixture slips. That keeps the owner's
Attic decision intact and removes a service from the critical path of the first proof.

### Premature generalization to remove

- Index and summary requirements (V4-SRC-013, V4-SRC-014) contradict V4 §12's own policy
  item 5: "Expand indexing only when real searches demonstrate its value." Move them to
  "when offered".
- The §5 action and context discussion correctly refuses a registry, then specifies
  optional command metadata anyway. It carries no requirement and needs none. Shorten it.
- The conditional Jujutsu–btrfs–bubblewrap case is 31 requirements and roughly a quarter
  of the specification, for a module the owner placed outside V4. Its technical content is
  accurate and worth keeping. Its length invites the guide to treat it as scope. Keep the
  requirements, compress the specification prose, and mark the section explicitly as
  out-of-scope reference material.

### What needs an owner decision

1. **F-01.** Does Vendomat own composition, against `AGENTS.md`? If not, V4 §1's purpose
   sentence changes.
2. **F-04.** What happens to `vendomat plane`, the devman plane, and the installed
   `machine.json` consumer path?

### What needs a prototype

F-07 (unreachable-substituter behavior), F-08 (target-side substitution on the pinned
devenv), F-09 (HM rollback behavior in the chosen mode), and F-02's gate-task carrier.
Each is marked `[PROTOTYPE]` in the revised documents.

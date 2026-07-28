# Vendor Workspace: Ground-Up Product Concept

## 1. Purpose

`~/Vendor` is a managed polyrepo workspace for the author's personal libraries. It is the one predictable location where the checked-out source code for every managed library lives, alongside the tooling that coordinates those repositories.

It is deliberately not a package registry, a monorepo, or a mirror of remote hosting. It is a local development control plane. Its job is to make this normal situation dependable:

1. Several applications and libraries are being developed together.
2. Their source is cloned locally and should be consumed directly during day-to-day work.
3. Commits, pull requests, CI, and other machines must instead see portable remote dependency references.
4. Agents need concise, trustworthy context about these repositories and a durable way to turn repeated investigations into reusable guidance.

The product is named **vendomat**. It owns workspace metadata, commands, adapters, hooks, validation, and the local knowledge portal. It does not own the history or source of the individual library repositories.

## 2. Core Model

The workspace has two independent layers:

```text
~/Vendor                         workspace/control plane
├── vendomat/                    vendomat's own repository clone
├── library-alpha/               independent Git clone
├── library-beta/                independent Git clone
└── .vendomat/                   workspace-owned metadata and generated state
```

Each child library remains its own Git repository with its own remote, branches, hooks, CI configuration, release process, and permissions. The parent directory may itself be a lightweight Git repository for workspace configuration, but it must never turn the children into submodules or absorb their histories.

Vendomat provides a consistent contract across those repositories:

- **local mode** makes managed dependencies resolve to checked-out source under `~/Vendor`;
- **portable mode** makes dependencies resolve through canonical Git or registry references suitable for commits and CI;
- **knowledge mode** makes known decisions and troubleshooting answers discoverable to people and agents.

The source checkout is first-class. A registry entry is not merely an abstract package name: it declares the exact local clone location and the canonical remote identity of a library.

## 3. Workspace Layout

The initial layout should make ownership and mutability obvious:

```text
~/Vendor/
├── devenv.nix                   shared development environment entry point
├── devenv.yaml                  devenv services, scripts, and shell definition
├── vendomat.nix                 pinned vendomat package/module integration
├── vendor.toml                  human-maintained workspace manifest
├── README.md                    setup and operator guide
├── vendomat/                    clone: tooling implementation itself
├── <library-id>/                clone: one directory per managed repository
├── .git/                        optional Git history for control-plane files only
└── .vendomat/
    ├── config.toml              machine-local overrides; normally untracked
    ├── state/                   regenerated operational state; untracked
    │   ├── inventory.json
    │   ├── dependency-graph.json
    │   ├── locks/
    │   └── sessions/
    ├── hooks/                   generated hook launchers and hook state
    ├── cache/                   adapter and search caches
    ├── worktrees/               temporary portable-mode worktrees
    ├── patches/                 generated, reviewable dependency rewrites
    ├── inbox/                   incoming structured questions/cases
    ├── cases/                   evidence-rich investigations
    ├── answers/                 approved reusable guidance
    ├── playbooks/               maintained workflows and policies
    └── indexes/                 generated keyword/vector/search indexes
```

`vendor.toml`, devenv files, approved answers, and playbooks are durable control-plane assets. Caches, locks, temporary worktrees, generated patches, and session records are disposable. This separation prevents runtime state from accidentally becoming policy or documentation.

The workspace is relocatable. `~/Vendor` is the default, but the active root is determined by `VENDOR_ROOT`, a command-line `--root` flag, or discovery of `vendor.toml`. Repository metadata must use relative paths from the workspace root whenever possible; home-directory paths belong only in local overrides.

## 4. Architectural Components

### 4.1 Workspace manager

The workspace manager is responsible for discovering the root, parsing the manifest, checking clone state, cloning or repairing repositories, and presenting a single inventory. It must work without network access for all local inspection and linking actions.

### 4.2 Manifest and registry

The manifest describes the desired workspace. Vendomat derives inventory and dependency graph state from it plus repository inspection; it should not make a generated database the source of truth.

### 4.3 Repository inspector

The inspector reads Git remotes, current branch/commit, cleanliness, hooks, supported ecosystems, and declared dependencies. It generates a normalized inventory so commands and agents do not need bespoke assumptions for each repo.

### 4.4 Dependency resolver and adapter host

The resolver asks an ecosystem adapter how a dependency is represented, linked locally, converted to a portable reference, locked, and verified. The host owns cross-cutting rules such as allowed targets, graph traversal, changesets, and rollback; adapters own file format semantics.

### 4.5 Portable-session engine

Portable sessions construct a Git/CI-safe dependency state without mutating the developer's active checkout. They use an isolated worktree or a copied metadata surface, generate a patch and verification report, then remove the session on success or retain it for diagnosis on failure.

### 4.6 Hook installer and hook dispatcher

Vendomat installs a small dispatcher into managed repositories. The dispatcher invokes the versioned vendomat command available through devenv, records no secrets, and never rewrites source files directly. Hooks provide fast local gates; deeper validation remains available as explicit commands and CI jobs.

### 4.7 Knowledge portal

The portal exposes search, context retrieval, intake, and case promotion to people and agents. It is initially a local CLI and MCP-compatible service, rather than a web application. It can inspect the known workspace topology and read approved project knowledge, but it must not grant autonomous write or network authority merely because an agent queried it.

### 4.8 Devenv integration

The root `devenv.nix` provides a reproducible toolchain: vendomat itself, Git, supported ecosystem managers, formatting/lint tooling, hook setup, and local portal commands. Entering the shell should validate prerequisites and make `vendor` available. It should not silently clone, pull, modify hooks, or alter dependency declarations; those actions require explicit commands.

## 5. Manifest and Data Model

The manifest needs stable IDs independent of package names and directory names. A simplified example:

```toml
[workspace]
schema_version = 1
default_remote = "origin"
portable_policy = "git-pinned"

[libraries.vendomat]
path = "vendomat"
remote = "git@github.com:example/vendomat.git"
ecosystems = ["nix", "rust"]
roles = ["tooling"]

[libraries.library-alpha]
path = "library-alpha"
remote = "git@github.com:example/library-alpha.git"
ecosystems = ["node"]
package_names = { npm = "@example/library-alpha" }

[libraries.library-beta]
path = "library-beta"
remote = "git@github.com:example/library-beta.git"
ecosystems = ["rust"]
package_names = { cargo = "library-beta" }

[[bindings]]
consumer = "library-alpha"
dependency = "library-beta"
adapter = "cargo"
mode = "linkable"
```

A library record contains:

- stable `id`, workspace-relative clone `path`, and canonical Git remote;
- one or more ecosystems and package identities;
- default branch, optional allowed remotes, and visibility/credentials policy;
- capability flags such as `linkable`, `publishable`, or `read_only`;
- ownership and documentation tags for routing questions.

A binding describes a directed dependency relation, not necessarily every third-party dependency. It records the consumer, managed dependency, adapter, representation policy, and optional constraints such as whether local linking is allowed or whether portable form must use a tag, semver release, or exact Git revision.

Generated inspection output adds ephemeral facts: clone present, remote match, HEAD SHA, dirty state, lockfile state, detected references, reverse dependencies, last validation time, and applicable knowledge IDs.

## 6. Dependency Representations

Vendomat distinguishes intent from representation.

| Intent | Local representation | Portable representation |
| --- | --- | --- |
| Consume unreleased sibling source | relative/absolute path, workspace link, editable install | canonical Git remote plus immutable revision |
| Consume released sibling package | local override allowed for development | registry package/version |
| Consume tooling/config repository | local checkout path | Git remote/revision or pinned flake input |

The exact syntax is adapter-specific. Examples include `file:` links in JavaScript manifests, Cargo `path` dependencies, Python editable/path sources, Nix path inputs, or Go `replace` directives. The common model is a **binding** with two legal materializations: `local` and `portable`.

Portable Git references must identify an immutable commit SHA unless a binding explicitly requires a signed tag or registry version. Floating branches are forbidden as a portable dependency form. If a dependency revision has not reached an allowed remote, validation fails with an actionable explanation.

## 7. Primary Workflows

### 7.1 Bootstrap

```text
git clone <workspace-control-plane> ~/Vendor
cd ~/Vendor
devenv shell
vendor doctor
vendor sync --clone-missing
vendor hooks install
vendor graph refresh
```

`doctor` verifies tooling and access. `sync` honors the manifest, cloning only explicitly requested or missing entries. It does not discard local changes, switch branches, or force-pull.

### 7.2 Daily local development

```text
cd ~/Vendor/library-alpha
vendor link library-beta
vendor check --scope changed
```

`link` asks the relevant adapter to materialize the local side of a managed binding and update any required lockfiles according to policy. Before modification it previews affected files. It refuses a target outside the configured workspace or a dependency whose clone identity does not match the manifest.

The developer edits and tests the actual sibling code in `~/Vendor/library-beta`. `vendor graph` and `vendor status` show forward and reverse local impact, including which consumers use a local override.

### 7.3 Pre-push gate

The pre-push hook is intentionally fast and non-destructive:

```text
pre-push
  -> vendor hook pre-push --repo <current-repo>
  -> verify manifest identity and Git remote
  -> detect disallowed local references in pushed commits
  -> verify portable dependencies are pinned and reachable
  -> run configured quick checks
  -> allow or reject push
```

The hook should normally reject a push if committed files would expose `../` paths or nonportable local overrides. It must print the exact `vendor prepare-push` or `vendor portable apply` command needed to resolve the issue. It must not silently amend commits, change the index, or push additional dependency repositories.

### 7.4 Preparing a portable change

When local development is ready for sharing:

```text
vendor prepare-push --repo library-alpha
```

Vendomat creates a session under `.vendomat/worktrees/`, based on the requested branch and commit. The adapter rewrites only declared linkable bindings to their portable representation, refreshes necessary lock files, and produces:

- a patch showing every altered manifest and lockfile;
- a dependency provenance report (remote, SHA/tag/version, reachability);
- results from adapter validation and configured tests;
- an isolated worktree that can be inspected, committed, or discarded.

The original local checkout remains linked and unchanged. The user may then use `vendor portable commit <session>` to commit the portable patch in the isolated worktree, or apply the reviewed patch to their active branch explicitly. This makes the Git-visible transition deliberate and reversible.

### 7.5 Returning to local mode

```text
vendor link --repo library-alpha --all
```

This converts eligible managed bindings back to local representation after a portable commit, again previewing changes and updating locks according to adapter policy. A project may choose to retain portable form by default; vendomat records mode per binding rather than assuming all dependencies should always be local.

### 7.6 CI verification

CI runs `vendor verify --portable --no-workspace-paths`. It checks the committed repository state rather than relying on `~/Vendor`. CI receives the manifest policy or a small vendomat configuration bundle, but never assumes sibling clones exist. The same adapter versions are pinned by Nix/devenv where practical.

### 7.7 Workspace maintenance

```text
vendor status
vendor graph
vendor sync --fetch
vendor doctor
vendor hooks install --all
```

Status is read-only and summarizes dirty repositories, missing clones, remote drift, active sessions, local bindings, failed validations, and relevant inbox items. Fetching is explicit; automatic pulling is avoided because it can disrupt in-progress work.

## 8. Safety Properties and Invariants

The rewrite should treat these as product invariants, enforced centrally and tested end to end:

1. **No hidden mutation.** Read-only commands stay read-only. Commands that alter dependency files, lockfiles, hooks, Git configuration, or clones show a plan and require the named action.
2. **Active worktree preservation.** A portable conversion never edits the active local development checkout by default. Temporary sessions are isolated.
3. **Portable commits are self-contained.** A committed dependency declaration cannot require a path beneath `~/Vendor`, another developer's home, or an unpushed Git object.
4. **Canonical identity.** A local target is valid only when its resolved path, Git remote, and configured library identity agree. A random directory with a matching package name cannot impersonate a managed dependency.
5. **Immutable provenance.** Portable Git dependency references are pinned to a full commit SHA (or a policy-approved immutable release reference), with remote reachability verified.
6. **Lockfile coherence.** If an ecosystem uses lockfiles, representation conversion either updates and validates them or fails. Vendomat never claims a conversion is ready while the lockfile disagrees.
7. **No cross-repository implicit commit/push.** Vendomat can report a missing dependent commit and guide the operator, but it never commits, pushes, rebases, or force-updates sibling repositories on their behalf.
8. **Hook fail-safe behavior.** If vendomat is unavailable, the hook gives a clear failure or policy-defined bypass message; it never pretends verification passed. Bypasses must be visible in the command/audit record where feasible.
9. **Secrets remain local.** Credentials, private remotes, tokens, and machine-specific locations live in ignored local config or normal credential tooling, never in generated knowledge or portable reports.
10. **Knowledge has trust states.** Unreviewed agent output cannot be automatically injected as authoritative guidance.

## 9. CLI Surface

The CLI should be narrow, composable, and designed for both a terminal user and tool-calling agents.

```text
vendor init                         initialize a control-plane workspace
vendor doctor                       inspect prerequisites and configuration
vendor inventory                    list desired and discovered repositories
vendor clone <id>                   clone a declared library
vendor sync [--fetch]               reconcile clone presence; optional fetch only
vendor status [repo]                summarize clone, binding, and validation state
vendor graph [--reverse <id>]       show managed dependency relationships

vendor link <dependency>            materialize a consumer's local binding
vendor unlink <dependency>          materialize its portable binding
vendor diff [--session <id>]        show planned or generated representation change
vendor check [--scope changed]      validate workspace/local policy
vendor prepare-push --repo <id>     create isolated portable conversion session
vendor portable commit <session>    commit reviewed session in its isolated worktree
vendor portable discard <session>   remove an isolated session
vendor verify --portable            CI-compatible portable-state verification

vendor hooks install [--all]        install vendomat dispatchers
vendor hooks verify                 check installed hook integrity

vendor ask <query>                  retrieve concise approved context
vendor context --repo <id> --task <text>
vendor inbox create                 create a structured question/case
vendor inbox list
vendor case investigate <id>        open/continue an evidence record
vendor answer propose <case-id>     create reviewable reusable guidance
vendor answer approve <id>          promote guidance to approved state
vendor knowledge index              rebuild local search index
```

All commands support structured JSON output, stable error codes, `--dry-run` where they mutate state, and `--no-network` where meaningful. Human-readable output explains the next safe action; JSON records enough provenance for an agent to decide whether to continue or escalate.

## 10. Hook Design

Hooks are installed per managed clone but configured from the workspace. The implementation should use a tiny durable shell launcher that resolves `vendor` from the environment and forwards Git hook arguments; complex logic remains in vendomat.

Pre-push behavior is scoped to refs actually being pushed. It should inspect the range that will become remote-visible, not simply the working tree. That prevents a local link used only in uncommitted development from blocking an unrelated push, while still catching a committed path dependency before it escapes.

Optional hooks can improve feedback without becoming mandatory policy:

- `post-checkout` / `post-merge`: mark the dependency graph stale and suggest refresh;
- `pre-commit`: detect obvious absolute home-directory paths;
- `pre-push`: enforce portable visibility and run quick adapter checks.

Hook installation must coexist with existing user hooks. Vendomat should prefer `core.hooksPath` dispatching only after explicitly adopting existing hooks, or generate a dispatcher that invokes preserved hooks in documented order. It must never overwrite an existing hook without a migration/backup plan.

## 11. Multi-Ecosystem Adapter Contract

Adapters turn ecosystem specifics into a common lifecycle:

```text
discover(repository) -> bindings, package identities, lockfiles
render(binding, mode, provenance) -> file changes
lock(repository, changes) -> file changes or error
validate(repository, mode) -> checks and findings
references(repository) -> normalized dependency references
```

The adapter host supplies normalized `Binding`, `PortableProvenance`, `ChangePlan`, and `ValidationFinding` models. An adapter may not directly rewrite files outside its declared repository boundary or invoke a network operation unless the caller allowed it.

Initial adapters should be chosen by actual personal-library needs, but a ground-up design can support these categories:

- **Node package managers:** workspace/file/link package specs; package lock/pnpm/yarn lock behavior; Git URLs and registry versions.
- **Rust/Cargo:** `path` dependencies, Git dependencies with `rev`, workspace inheritance, and `Cargo.lock` refresh.
- **Python:** editable local sources and path URLs versus VCS/registry dependencies across the selected project manager.
- **Nix flakes:** path inputs versus Git inputs with revisions and lockfile updates.
- **Go modules:** local `replace` directives versus module/version dependencies; stricter policy because arbitrary Git URL rewriting is not always semantically equivalent.

Not every ecosystem supports every conversion safely. A binding can be `validate-only`: vendomat detects and blocks unsafe publishing but does not offer automatic rewriting. Correct refusal is preferable to a generic rewrite that produces an invalid project.

## 12. Agent Portal, Inbox, and Knowledge System

### 12.1 Design objective

The portal reduces rediscovery. When an agent encounters a recurring setup question, dependency failure, design decision, or unusual repository convention, it should obtain a compact, relevant answer before starting a broad investigation. If no trusted answer exists, it should create a structured request that a designated repo agent or human can investigate.

### 12.2 Knowledge tiers

```text
inbox        untriaged reports/questions; not evidence or guidance
cases        investigations with commands, findings, links, and uncertainty
proposals    distilled answer candidates awaiting review
answers      approved concise guidance eligible for automatic context
playbooks    maintained, procedural workflows and escalation rules
```

Only `answers` and selected `playbooks` are eligible for automatic context injection. Cases are searchable as supporting evidence but must be labeled as investigation material. Every answer carries a confidence/trust level, owning scope, last verified date, source case IDs, related repository revisions, and a precise verification command.

### 12.3 Case record

A case is structured Markdown with machine-readable front matter:

```yaml
id: case-2026-0017
status: investigating
repos: [library-alpha, library-beta]
tags: [dependencies, cargo, local-link]
created_at: 2026-07-12T00:00:00Z
source: agent-inbox
evidence: [command-output-redacted, commit:abc123]
```

The body records the observed symptom, scope, reproduction, evidence, discarded hypotheses, resolution, uncertainty, and next verification. This creates an audit trail without forcing future agents to ingest full conversational transcripts.

### 12.4 Answer record and context budget

An approved answer is deliberately short. It includes triggers, a 5--10 line answer, affected repositories, confidence, staleness policy, links to deeper cases, and a command to verify it. `vendor context` returns a bounded context packet:

1. an instant summary within a configured token budget;
2. the top relevant approved answers/playbooks;
3. repository state facts needed to apply the guidance;
4. links to full cases only when the caller asks for depth;
5. an explicit `unknown` result when no trusted answer applies.

This prevents an agent from blindly receiving a huge, stale notebook and avoids confusing historical speculation with current policy.

### 12.5 Intake and routing

`vendor inbox create` records an issue with affected repos, task type, urgency, current branch/commit, sanitized logs, and desired outcome. A routing policy can assign a repo agent based on ownership tags or dependency graph locality. The repo agent receives least-privilege context: it may inspect its repository and relevant approved knowledge, then proposes an investigation or answer. External actions—publishing, pushing, changing permissions, or modifying source—require the normal explicit authority and are not implied by inbox assignment.

### 12.6 Access interfaces

The first release provides:

- a CLI for people and scripted agents;
- a local MCP server exposing `search_knowledge`, `get_context`, `create_inbox_item`, and `get_workspace_status`;
- filesystem-backed, versionable records for portability and review.

A browser UI, shared hosted service, embeddings service, or autonomous background agents are optional future layers, not prerequisites. Search should work with deterministic keyword/tag/index retrieval before adding semantic retrieval.

## 13. Security and Privacy

The workspace is personal but must not assume all local data is safe to expose to every agent. Vendomat should apply repository-level visibility and knowledge access labels. Portal responses redact configured patterns and never include credential files, Git config secrets, untracked source outside a scoped repository, or raw command output marked sensitive.

Knowledge indexing must be opt-in for source content. By default, index only maintained knowledge files and manifest metadata; inspect source code on demand under the current agent's authorized repository scope. All indexes are local by default. Sending content to an external model/provider is a separate, explicit integration with a clear data boundary.

## 14. Rollout Plan

### Phase 0: Product skeleton

Create the control-plane repository at `~/Vendor`, define `vendor.toml`, package vendomat through `devenv.nix`, and implement `vendor doctor`, `inventory`, and `status`. Add only two or three representative library clones. The measure of success is a reliable inventory, not automation volume.

### Phase 1: Read-only graph and validation

Implement one adapter for the primary ecosystem. Discover managed local references, render the dependency graph, and add `vendor check` plus a non-mutating pre-push hook. Capture real failures as inbox/case records.

### Phase 2: Explicit local linking

Add previewable `vendor link` and `unlink` flows, lockfile verification, and reverse-dependency reporting. Keep portable conversions manual until actual project behavior proves the adapter semantics.

### Phase 3: Isolated portable sessions

Implement temporary-worktree conversion, patch/provenance reports, and CI-compatible `vendor verify --portable`. Require a green portable session before declaring a binding's automation mature.

### Phase 4: Knowledge portal

Add filesystem knowledge records, `vendor ask`, context packets, inbox intake, and reviewed answer promotion. Start deterministic search; add semantic indexing only if keyword/tag retrieval fails to serve real cases.

### Phase 5: Additional adapters and policy hardening

Add ecosystems one at a time, each with fixtures for local, portable, invalid, dirty, and lockfile-drift states. Introduce stricter policies only after migration tools and clear diagnostics exist.

## 15. Non-Goals

Vendomat should explicitly not attempt to be:

- a monorepo migration tool or a parent Git repository for child histories;
- a replacement for package registries, release managers, or hosted CI;
- a generic universal dependency rewriter that guesses unsupported ecosystem semantics;
- an automatic committer, pusher, rebaser, dependency publisher, or force-update tool;
- a daemon that pulls every repository or changes branches in the background;
- a surveillance/search system that indexes all personal source and secrets by default;
- a source of unquestioned agent truth—unreviewed investigations remain untrusted;
- a requirement that every repository use local links or every dependency live under `~/Vendor`.

## 16. Definition of a Useful First Release

The first release is successful if a developer can enter `~/Vendor`, see the health and local dependency graph of a small set of clones, link a supported sibling dependency safely, and receive a clear pre-push failure before a nonportable path reference reaches a remote. The tool must also produce a portable-session patch that can be reviewed without disrupting the working local link.

The knowledge system is successful at first when it can return a short, approved answer to a repeat question and preserve the evidence for that answer. It does not need an elaborate autonomous agent network to provide value. The durable combination is a predictable local codebase, explicit portable boundaries, and context that gets better only through reviewed experience.

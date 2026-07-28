# Prompt: plan the clean-slate Vendor workspace implementation

You are the technical planning lead for a ground-up rewrite of **vendomat** into a managed personal-library workspace. Do not begin implementation. Produce a rigorous, decision-ready implementation plan that preserves only the parts of the current repository that demonstrably support the new product.

## Product outcome

Create a `~/Vendor` managed polyrepo workspace that physically contains clones of all personal library repositories plus its shared control-plane files. Vendomat is the local control plane for that workspace.

It must make three modes dependable:

1. **Local development:** managed libraries consume sibling source checkouts under `~/Vendor` through ecosystem-appropriate local references.
2. **Portable collaboration:** commits, pushes, CI, and other machines use portable Git or registry references, never machine-local paths. A pre-push hook is fast and non-destructive; a separate explicit command prepares, previews, verifies, and applies portable dependency representations.
3. **Durable agent context:** agents and people can query a local inbox/portal, inspect the workspace and repository state within their authority, investigate cases, and promote approved findings into concise reusable answers and playbooks.

The result is a **managed polyrepo workspace**, not a monorepo, package registry, or an automation system that silently changes developers’ repositories.

## Required source material

Read these two documents completely before planning:

- `CODE_REVIEW.md` in this directory: evidence-based analysis of the current vendomat implementation.
- `VENDOR_CONCEPT.md` in this directory: the clean-slate product concept and architectural direction.

Treat the concept document as the intended product direction, but challenge it where its design is incomplete, inconsistent, unsafe, unnecessarily complex, or not feasible. Treat the code review as evidence, not as a mandate to retain current architecture or terminology.

Also inspect the current repository where needed to validate the review and identify reusable tests, Nix patterns, packaging constraints, documentation, and operational conventions.

## Planning principles

- Start from the new workspace model; do **not** frame the work as extending the present hard-coded `pyjutsu` wheel cache or Python dependency-knowledge tool.
- Keep independent library repositories independent. The `~/Vendor` parent control plane must not absorb child Git histories, make them submodules, or force shared release processes.
- Use a declarative manifest as the durable source of truth. Caches, inventory, indexes, sessions, generated patches, and lock state are derived and disposable.
- Make `~/Vendor` the default but allow a relocatable root through explicit discovery/override rules. Never bake a user’s home path into portable metadata.
- Default to explicit, reviewable, reversible mutations. Never let shell entry, a query, or a Git hook silently clone/pull, alter dependency files, alter the index, amend commits, or push a second repository.
- Make the hook a quick validator. Put rewrites, lock regeneration, broader checks, and cleanup in explicit portable-session commands.
- Treat cross-ecosystem support as an adapter boundary. Do not pretend JavaScript, Cargo, Python, Nix, and Go dependency syntax can share one file-level implementation.
- Separate raw agent investigations from approved guidance. Automatic context injection may use only concise, reviewed/approved material and must respect an explicit context budget.
- Design the first useful release narrowly. Do not require an always-running web service, vector database, autonomous agent, or every ecosystem before delivering value.
- Account for offline use, dirty working trees, partially cloned workspaces, unpushed commits, incompatible locks, hook bypasses, concurrent commands, failures, and rollback/recovery.

## Decisions that the plan must make

Resolve these explicitly, recording alternatives and rationale:

1. **Implementation shape:** language/runtime, package boundaries, CLI framework, Nix/devenv packaging, and what runs from the workspace versus per-repo hooks.
2. **Workspace ownership:** whether the root control-plane configuration is itself a Git repository; tracked vs ignored files; bootstrap and upgrade story.
3. **Manifest schema:** stable library IDs, workspace-relative paths, remotes, ecosystems, package identities, bindings, policy/capability fields, schema versioning, validation, and machine-local overrides.
4. **Adapter contract:** discovery, local materialization, portable materialization, lock handling, diff/preview, verification, rollback, and adapter capability negotiation. Identify which ecosystem adapter should ship first and why.
5. **Portable sessions:** isolation strategy (for example, temporary Git worktree), lifecycle, commit/index/dirty-tree rules, generated patch/report artifacts, reachability checks, failure retention, cleanup, and what `prepare-push` actually does.
6. **Git hook model:** installation, dispatcher location, version resolution, performance budget, supported hook behavior, bypass policy, CI-equivalent checks, and safe failure messages.
7. **Git/revision policy:** allowed remotes, canonical remote resolution, immutable SHA/tag/registry rules, unpublished dependency revisions, authentication boundaries, and whether/how dependent repositories are pushed separately.
8. **Knowledge portal:** minimal local CLI/MCP interface, intake/case/answer/playbook schemas, routing, evidence links, approval/promotion lifecycle, repository access boundaries, search/indexing strategy, context assembly and budget, retention, and human approval controls.
9. **Security and privacy:** path traversal, untrusted repository content, prompt injection in docs/issues, unsafe hook execution, secret exposure, network authority, and write authorization boundaries.
10. **Observability and recovery:** structured events/logs, reports, session state, user-visible diagnostics, lock/concurrency strategy, cache invalidation, and disaster-free recovery commands.

## Required evaluation of the existing repository

Create a retention matrix that classifies every meaningful current capability or asset as one of:

- **Retain substantially** — compatible and valuable as-is or with modest extraction.
- **Reuse as a pattern/test/reference** — useful lesson, code, fixture, test technique, Nix pattern, or documentation, but not a direct architectural component.
- **Replace** — has a related purpose but needs a new abstraction or implementation.
- **Retire** — conflicts with the new direction or adds unnecessary product scope.

For each classification, cite the relevant current files and explain the migration implication. Address at minimum:

- the Nix flake/devenv integration and wheel-building path;
- the present CLI and Python packaging;
- `vendor/libs` knowledge content, `sync`, `add`, and `doctor` behavior;
- dependency parsing and normalization code/tests;
- current documentation and implementation-plan material;
- the concrete missing Nix runtime dependencies identified by the review (`PyYAML` and `tomli-w`);
- assumptions tied to a hard-coded sibling repository or absolute path.

Do not preserve code merely because it exists. Conversely, do not discard existing tests or carefully designed safety behavior without explaining why a replacement provides equivalent or better coverage.

## Required deliverable

Write a single planning document, suitable for a technical decision meeting. It should contain:

1. An executive recommendation and the proposed v1 boundary.
2. A concise corrected architecture, including a workspace/component diagram and data/control-flow diagrams where helpful.
3. Decisions and rationale for every required decision above, including unresolved questions that truly need owner input.
4. The retention matrix for the current repository.
5. A concrete target directory/package layout and manifest examples.
6. Command/interface specifications for the initial CLI, hooks, and portal, including expected inputs, outputs, exit codes, mutation behavior, and failure cases.
7. A portable-session transaction specification and threat/failure model.
8. A phased implementation roadmap. Each phase must state its user-visible capability, files/components likely affected, dependencies, migration/compatibility approach, verification strategy, and objective acceptance criteria.
9. A test strategy spanning unit, adapter contract, Git/worktree integration, hook integration, Nix/devenv packaging, offline/error recovery, and agent-knowledge lifecycle tests.
10. Risks, non-goals, sequencing constraints, and a clearly marked list of decisions requiring human confirmation.

Be concrete enough that another engineer can turn the plan into implementation tasks without re-discovering core architecture. Flag assumptions. Prefer small, independently verifiable increments over a single rewrite milestone.

## Quality bar

The plan is successful only if it explains how a developer can:

1. bootstrap `~/Vendor` and clone declared repos without disturbing existing clones;
2. link one local managed dependency and see what files changed;
3. prepare a portable, CI-safe version without mutating their active checkout unexpectedly;
4. have a pre-push hook reject an unsafe local dependency reference with an actionable next command;
5. recover safely from a failed rewrite, dirty tree, lockfile conflict, or unpushed dependency commit; and
6. ask a repository question and receive small, trustworthy, approved context without granting an agent unsupervised write/network authority.

If the current concept fails any of these tests, improve it in the plan rather than carrying the flaw forward.

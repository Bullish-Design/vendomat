# Vendomat managed polyrepo workspace — implementation plan

Status: decision-ready proposal  
Prepared: 2026-07-12  
Scope: clean-slate replacement of the current artifact/knowledge prototype

## 1. Executive recommendation

Build vendomat as a Python CLI and library that manages a separate, lightweight control-plane
Git repository at `~/Vendor`. Keep every library checkout as an independent sibling Git
repository. Make `vendor.toml` the only durable workspace topology and policy source; derive all
inventory, graph, session, index, and lock state.

Ship one complete vertical adapter first: **Python projects managed by uv using PEP 621 plus
`[tool.uv.sources]`**. This is narrower than a generic Python adapter. It is the best evidenced
starting point because this repository contains a real sibling path source (`testee` in
`pyproject.toml`), already uses uv lockfiles, and has dependency parsing and normalization tests.
Do not ship Cargo, Node, Go, Nix-flake rewriting, or the native-wheel cache in v1. They must use
the same contract later, but unsupported bindings are validate-only.

Use isolated Git worktrees for portable preparation. `prepare-push` never edits the active
checkout. The pre-push hook only inspects commits being pushed and cached remote facts; it never
rewrites, locks, fetches, commits, or pushes. An explicit `portable apply` is the only v1 path
from a reviewed session patch back to an active checkout.

The first release includes a small filesystem knowledge portal: deterministic search, structured
inbox/case/proposal/answer/playbook records, human approval, bounded context, and an on-demand
stdio MCP facade. It has no daemon, browser UI, embeddings, autonomous investigator, or implicit
source indexing.

### v1 boundary

V1 supports:

- initializing or adopting a relocatable control-plane workspace;
- validating a versioned manifest and safely cloning declared repositories;
- read-only inventory, status, and managed-binding graph;
- uv binding discovery, previewed local materialization, lock regeneration, and validation;
- isolated portable sessions, patch/report generation, remote-reachability proof, explicit apply,
  and CI verification;
- a fast, non-mutating pre-push dispatcher for uv bindings;
- keyword/tag search over approved knowledge, bounded context, intake/cases, proposal and explicit
  approval, plus four least-privilege MCP tools;
- human and JSON output with stable exit semantics, local structured events, locks, cleanup, and
  recovery diagnostics.

V1 does not build wheels, publish packages, pull or switch branches, commit or push any
repository, handle uncommitted application changes in a portable session, automatically install
hooks during shell entry, or rewrite ecosystems other than the declared uv subset.

### Success path

```text
vendor init ~/Vendor                 # creates control-plane files only
vendor manifest validate
vendor sync --clone-missing --apply  # refuses collisions; clones only missing declared repos
vendor link testee --repo vendomat   # preview by default
vendor link testee --repo vendomat --apply
vendor prepare-push --repo vendomat  # active checkout remains locally linked
vendor portable diff <session>
vendor portable apply <session>      # explicit, clean/exact-base preconditions
vendor verify --portable --repo vendomat
vendor ask "how do checks run?"      # approved, budgeted context only
```

## 2. Corrected architecture

The concept's main separation is retained, with three corrections:

1. Durable knowledge belongs in a visible tracked `knowledge/` tree, not mixed with disposable
   `.vendomat/` state. Sensitive raw captures stay in ignored `.vendomat/private/` until redacted.
2. The root control plane is a Git repository by default, but child clone paths are explicitly
   ignored and are never submodules or parent-repository content.
3. V1 MCP is an on-demand stdio process over the same application service as the CLI, not an
   always-running service.

```text
                         control-plane Git repository
  ~/Vendor/
  ├── vendor.toml ───────────────┐
  ├── policy/                    │ desired state / reviewed guidance
  ├── knowledge/                 │
  ├── flake.nix + devenv.nix     │
  ├── vendomat/   independent Git clone (tool source)
  ├── testee/     independent Git clone
  └── .vendomat/  ignored derived/local state
          │                      │
          ▼                      ▼
   root/config discovery → manifest validator → inventory + binding graph
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                  ▼
                Git facade       adapter host       knowledge store
                    │                 │                  │
              clone/status/      uv adapter       CLI + stdio MCP
              worktree/hooks   plan/lock/verify   search/context/intake
                    └─────────────────┬──────────────────┘
                                      ▼
                          reports/events/session state
```

### Local-link data flow

```text
manifest binding + inspected clone identity
              │
              ▼
uv discover → capability check → render in memory → temp-tree lock regeneration
              │                                      │
              └──────── ChangePlan + unified diff ◄──┘
                                     │
                         default: stop after preview
                                     │ --apply
                                     ▼
                    acquire repo lock → recheck hashes/HEAD
                    → atomic file replacement → verify
                    → restore snapshots on failure → event/report
```

### Push and portable flow

```text
explicit prepare-push                       Git pre-push
HEAD + manifest + dependency provenance     stdin ref updates + manifest bundle
        │                                           │
detached temporary worktree                        inspect pushed commit trees
        │                                           │
uv portable render + uv lock                        no worktree/network/mutation
        │                                           │
verify + reachability check                         │
        ▼                                           ▼
patch + provenance + report + retained worktree   allow or reject with session command
        │
explicit apply to unchanged, clean active checkout OR discard
```

## 3. Product and implementation decisions

### D1. Implementation shape

**Decision.** Retain Python, Typer, Pydantic, uv, and the existing Testee verification entrypoint.
Target Python 3.12+ unless the pinned fleet requires 3.13; use stdlib `tomllib` to read, `tomli-w`
to write controlled TOML, and PyYAML only for knowledge front matter. All Git and ecosystem
commands run through argument-vector subprocess wrappers with sanitized environments and explicit
timeouts. No shell-evaluated manifest content or plugin discovery from child repositories.

Use these package boundaries: CLI/output, workspace/manifest, Git facade, adapter API and uv
adapter, transaction/session engine, hooks, knowledge, security/redaction, and event/state store.
The `vendor` executable is a thin edge over application services. Adapters are built-in Python
modules in v1; a third-party plugin ABI is deferred until two adapters prove the contract.

The workspace flake pins vendomat and runtime tools. Root `devenv.nix` puts a Nix-built `vendor`
on PATH and may print read-only health hints, but shell entry performs no clone, fetch, hook, link,
index, or file mutation. Hooks invoke a generated fast launcher at `.vendomat/bin/vendor`, which
resolves to the workspace-pinned Nix package and does not import a child's virtual environment.

**Alternatives rejected.** Rust would improve startup/distribution but discards proven Python
tests and slows the first safe slice. A long-running service adds lifecycle and authority risks.
Calling arbitrary adapter executables from repositories makes untrusted repository content code.

### D2. Workspace ownership, bootstrap, and upgrade

**Decision.** The root is a lightweight Git repository for control-plane assets. It tracks
`vendor.toml`, lock/pin files, root Nix/devenv files, policies, redacted cases, proposals, approved
answers, playbooks, schemas, and operator docs. It ignores `.vendomat/` and every declared child
clone path. Child paths may not overlap tracked root paths and may not be nested within one another.

`vendor init [ROOT]` defaults to `~/Vendor`, creates a candidate plan, and requires `--apply` to
write. It refuses a nonempty directory unless `--adopt`; adoption inventories every collision and
never initializes inside an existing unrelated Git worktree. Existing matching clones are adopted
only after their real path and canonical fetch remote match the manifest. Mismatches are reported,
never moved or overwritten. Root creation and Git initialization are separate reported actions.

`vendor sync --clone-missing` previews; `--apply` clones to a same-filesystem temporary directory,
validates remote identity, then renames into the declared path. It never pulls, checks out a
different branch in an existing clone, or repairs by deletion. `--fetch` is a separate explicit
network action.

The workspace pins vendomat through `flake.lock`; the CLI refuses a newer unsupported manifest
schema. `vendor workspace upgrade --to N` emits and validates a patch, backs up changed control
files under a session, and requires `--apply`. Downgrades are not automatic. The implementation
repository upgrades independently; the root pin decides the operational version.

### D3. Root discovery and manifest

Resolution order is `--root`, `VENDOR_ROOT`, upward discovery of `vendor.toml` from CWD (crossing
from a child clone into its parent is allowed), then `~/Vendor`. Conflicting explicit roots fail.
All persisted paths are workspace-relative POSIX paths. `~`, absolute paths, `..`, symlink escapes,
case-fold collisions, `.git`, and `.vendomat` targets are invalid. Machine paths and remote aliases
belong in ignored `.vendomat/config.toml` and cannot weaken manifest security policy.

Stable IDs are manifest table keys and never inferred from package or directory names. IDs match
`[a-z][a-z0-9-]{1,62}`. Renames require an explicit `aliases` entry for one schema generation.
Unknown fields are errors. Schema validation includes uniqueness, graph references, capability
compatibility, URL syntax, and cross-field policy.

```toml
[workspace]
schema_version = 1
id = "personal-vendor"
default_remote = "origin"
context_token_budget = 1200

[policy]
portable_default = "git-rev"
remote_reachability = "required"
hook_failure = "closed"
allowed_remote_hosts = ["github.com"]

[libraries.vendomat]
path = "vendomat"
remote = "ssh://git@github.com/Bullish-Design/vendomat.git"
default_branch = "main"
ecosystems = ["uv"]
packages = { python = "vendomat" }
capabilities = ["inspect", "link", "portable"]
visibility = "private"
owners = ["andrew"]
tags = ["tooling"]

[libraries.testee]
path = "testee"
remote = "ssh://git@github.com/Bullish-Design/testee.git"
allowed_remotes = ["origin", "upstream"]
default_branch = "main"
ecosystems = ["uv"]
packages = { python = "testee" }
capabilities = ["inspect", "link", "portable"]
visibility = "private"

[[bindings]]
id = "vendomat-testee"
consumer = "vendomat"
dependency = "testee"
adapter = "uv"
package = "testee"
local = { kind = "path", editable = true }
portable = { kind = "git-rev", remote = "canonical" }
lock_policy = "required"
```

Machine-only overrides are deliberately small:

```toml
# .vendomat/config.toml (ignored)
schema_version = 1
[remote_aliases]
"ssh://git@github.com/" = "https://github.com/"
[runtime]
max_parallel_inspection = 4
```

Overrides may select equivalent credentials/transports and runtime limits; they may not change
library IDs/paths, bindings, allowed hosts, portable policy, visibility, or approval state.

### D4. Adapter contract and first adapter

Adapters receive a read-only repository view, declared binding, invocation capabilities, and a
host-owned path boundary. They return data and change plans; they do not write directly.

```text
metadata() -> adapter version + supported project/lock formats + capabilities
discover(view) -> package identities, declared references, lockfiles, findings
plan(binding, local|portable, provenance) -> preconditions + proposed file edits
lock(staged_tree, plan, network_policy) -> generated edits + command record
verify(view_or_tree, mode) -> findings
scan_treeish(git_object_reader, treeish, bindings) -> findings
```

Capabilities are independently negotiated: `discover`, `render-local`, `render-portable`,
`lock-offline`, `lock-network`, `verify-tree`, and `scan-treeish`. A missing capability produces a
validate-only result, never a guessed rewrite. Plans name every permitted file, before/after hash,
command, network need, and rollback snapshot.

The uv v1 adapter supports `pyproject.toml` PEP 621 dependencies, `[tool.uv.sources]` path/editable
and Git+full-rev sources, and `uv.lock` generated by the pinned uv version. It refuses workspace
source variants, mixed source indexes, dynamic dependency metadata, absent direct declarations,
ambiguous normalized package identities, or unfamiliar lock schema. Local paths are rendered
relative to the consumer repository when the dependency lies inside the same workspace; portable
form uses the manifest canonical URL and 40-hex commit SHA. It runs `uv lock` only inside a staged
copy/worktree and verifies with `uv lock --check` plus vendomat's no-local-path scan.

PEP-503 normalization from `deps.py` is reusable. The old “first existing dependency file wins”
behavior is not: the adapter reconciles manifest and lock semantics rather than merging generic
package-name sets.

### D5. Portable-session transaction

`prepare-push` accepts one consumer repository and committed `HEAD`. V1 does not incorporate
staged or uncommitted application changes. A dirty active checkout is allowed only because it is
excluded; the report warns that those changes were not prepared. `--require-clean` converts the
warning to a refusal. An unborn branch, merge/rebase in progress, missing HEAD, or dirty submodule
state fails.

Lifecycle:

1. Resolve and validate workspace, repository identity, bindings, adapter versions, HEAD, and
   dependency provenance. Acquire the repository/session-creation lock.
2. Create `.vendomat/worktrees/<session-id>` with `git worktree add --detach <HEAD>`. The ID is
   random plus timestamp, not user-controlled. Record base SHA, input hashes, tool versions, and
   authorized network mode in `session.json` using create-exclusive and atomic rename.
3. Resolve each dependency SHA from its clone. Reject dirty dependency content as provenance;
   only committed HEAD is eligible. Reject a SHA not reachable from an allowed remote. With
   network enabled, use `git ls-remote` through normal Git credentials without logging secrets.
   With `--no-network`, require cached remote-tracking evidence and label its observation time.
4. Ask the adapter to render portable files in the isolated worktree, regenerate locks, and
   verify. Capture only redacted command metadata and bounded output.
5. Emit `change.patch`, `provenance.json`, `verification.json`, `summary.md`, and final state.
   A failed session is retained. A green session is still retained until apply/discard.
6. `portable apply` reacquires the repository lock and requires the active checkout to be clean,
   at the exact base SHA, with matching input hashes and no Git operation in progress. It runs
   patch preflight, snapshots affected files, applies to the working tree without staging, then
   verifies. Any failure restores snapshots and leaves a recovery report. It never commits.
7. `portable discard` removes the registered worktree through Git, then prunes only that session.
   It refuses a worktree with user changes unless `--force` is paired with the session ID and a
   generated recovery patch. `portable cleanup` removes only expired, terminal, clean sessions.

`portable commit` is deferred from v1: committing on a detached/session branch creates confusing
branch integration semantics. Users explicitly apply, inspect, test, and commit normally. A later
command may create a named branch, but never push it.

Session states are `creating → prepared|failed → applying → applied|failed → discarded`. State
transitions are compare-and-swap under a lock. Re-running prepare creates a new session; it does
not mutate an old audit record.

### D6. Git hooks

Install a generated POSIX launcher per clone at its effective Git hooks directory. Do not change
`core.hooksPath` in v1. If `pre-push` exists, installation refuses by default. `--adopt-existing`
moves it to a uniquely named preserved hook, records its hash, and creates a dispatcher that runs
the preserved hook first and vendomat second; any nonzero result stops. Verification detects drift.
Uninstall restores the preserved hook only if generated hashes still match.

The launcher contains only a generated absolute workspace path, repository ID, expected vendomat
major version, and an `exec "$workspace/.vendomat/bin/vendor" hook pre-push ...` call. Those
machine-local paths are never committed to child repositories. The pinned launcher is refreshed
explicitly by `hooks install`.

The hook reads Git's pre-push stdin and checks only objects that would become visible: existing
remote refs use `remote_sha..local_sha`; new refs use commits reachable from `local_sha` but not
known remote refs; deletions need no dependency scan. It parses relevant blobs from commit trees
through the Git object reader, not the working tree. It validates canonical repository identity,
forbidden path/editable references, immutable portable refs, and locally cached reachability.
It never runs `uv lock`, tests, fetch, or representation conversion. Target p95 is under 2 seconds
for 100 pushed commits and 20 bindings; a 5-second hard timeout fails closed with diagnostics.

On rejection it prints offending commit/file/binding and exactly:

```text
Push rejected: vendomat-testee is local in commit abc1234 (pyproject.toml).
Run: vendor prepare-push --repo vendomat
Then review: vendor portable diff <session-id>
```

`VENDOMAT_BYPASS=<nonempty-reason>` allows a policy-configured emergency bypass and appends a
local event. Git's `--no-verify` can bypass all hooks and cannot be reliably audited; CI
`vendor verify --portable` is therefore authoritative. Missing vendomat fails closed by default
with reinstall and bypass instructions. CI uses the same `scan-treeish` logic without hooks.

### D7. Git, revision, and network policy

Canonical remotes are normalized identities, treating configured SSH/HTTPS aliases as equivalent
only after host and owner/repository match. Scp-like Git URLs are parsed, not string-replaced.
Manifest host allowlists and per-library canonical remotes bound every clone and portable render.
Redirected or file-protocol remotes are forbidden. Local clone identity requires realpath
containment, a Git top-level equal to the manifest path, and a matching fetch URL.

V1 portable Git sources require full 40-hex SHAs. Tags and registry versions are schema-reserved
but validate-only until signature/immutability and registry provenance are implemented. Branches,
short SHAs, local paths, mutable tags, and uncommitted dependency state are invalid portable
provenance. Reachability means the exact object is advertised by, or is an ancestor of a ref
advertised by, an allowed remote according to explicit network evidence; a mere local object or
remote-tracking name is not fresh network proof.

Vendomat uses the user's Git credential helper/SSH agent and never reads or stores credentials.
Reports redact URL userinfo and sensitive environment variables. Network is denied to read-only
inspection and hooks. Clone, fetch, reachability refresh, and uv lock network access are distinct
declared capabilities. Vendomat never pushes a dependency. If its SHA is unpublished, preparation
fails with the dependency ID/SHA and a suggested manual push; the user reruns preparation after
publishing it.

### D8. Knowledge portal

Durable records are UTF-8 Markdown with strict YAML front matter validated against versioned
schemas. IDs are generated, filenames derive from IDs, and state transitions never trust a path
from record content.

```text
inbox:    id, status, reporter, repos, question, urgency, created_at, sensitivity
case:     id, inbox_ids, status, repos, investigator, evidence[], uncertainty, conclusion
proposal: id, case_ids, scope, triggers[], body, verification, confidence, reviewer
answer:   proposal fields + approved_by, approved_at, expires_at/reverify_after, source revisions
playbook: id, scope, triggers[], ordered steps, stop/escalation rules, approval metadata
```

Inbox items and cases are not guidance. `answer propose` creates a proposal; `answer approve`
requires an interactive human by default, records identity/time and a content hash, and refuses
DRAFT/TODO text, missing evidence, expired revisions, or self-approval when policy requires two
people. Agents may create intake/cases/proposals but cannot approve. Amendments create new versions;
withdrawal immediately removes eligibility from rebuilt and live search.

Intake routing is deterministic and advisory: explicit repository IDs select their declared
owners; otherwise tags and nearest declared dependency-graph scope rank candidate owners. The
router records why it suggested an owner but does not start an agent or grant authority. Ambiguous
or cross-visibility cases remain unassigned for a human. Evidence links use typed references
(`repo:ID@SHA:path`, `case:ID`, or redacted report artifact and hash), are containment-checked, and
do not make the linked content eligible for automatic context.

Search v1 indexes only manifest metadata and tracked `answers/`/approved `playbooks/` using a
deterministic SQLite FTS index in `.vendomat/indexes`. It does not index repository source, raw
cases, untracked files, Git configuration, or command logs. Results are filtered by caller-provided
repository scope and manifest visibility before ranking. The index is disposable and rebuilt when
schema/content hashes change; correctness never depends on it because direct scan is the fallback.

`vendor context --repo ID --task TEXT --budget 1200` returns an instant state summary, top approved
records, verification commands, staleness flags, and links—not raw case bodies. It caps per-record,
total-token estimate, and result count, and returns `unknown` when no eligible result clears the
threshold. Prompt-like instructions found in evidence/source are quoted as untrusted data and
never promoted automatically.

`vendor portal mcp` is an on-demand stdio server using the same authorization and redaction layer.
V1 tools are `search_knowledge` and `get_context` (read), `create_inbox_item` (writes only a
validated intake record after preview/explicit client confirmation), and `get_workspace_status`
(read-only cached/local inspection). No tool grants shell, arbitrary file, network, source-write,
approval, commit, or push authority.

Retention: tracked knowledge is durable indefinitely until explicit archive/withdrawal. Raw
private captures default to 30 days. Generated indexes/events default to 90 days with size caps.
Cleanup previews and never deletes the only copy of a case or recovery artifact.

### D9. Security and privacy

- Resolve and compare every path beneath the authorized workspace/repository before reading or
  writing; use directory file descriptors/no-follow semantics where available and reject symlinks
  for mutation targets.
- Treat repositories, manifests from untrusted branches, docs, issues, lockfiles, hook stdin, and
  case evidence as data. Never execute repository-provided hooks, adapter code, commands, or
  front-matter instructions as part of inspection.
- Use pinned binaries, argument arrays, minimal inherited environment, time/output limits, and no
  shell. Permit uv/Git commands only from fixed templates owned by vendomat.
- Redact tokens, URL userinfo, credential-like environment names, configured patterns, home paths,
  and private remote aliases before persistence. Raw output is opt-in private state, never context.
- Separate capabilities: read workspace, mutate one declared repo, network Git, network package
  resolution, write knowledge intake, and approve knowledge. A command receives only those it
  needs; an MCP query cannot acquire more.
- Verify hook file ownership/mode/hash. Never source shell from a child repo. Preserved user hooks
  run only because the human explicitly adopted them.
- Automatic context consumes only current approved answers/playbooks within repository visibility
  and budget. Source text and cases are never interpreted as authority.

### D10. Observability, concurrency, and recovery

Every command emits a stable JSON result envelope under `--json`:

```json
{"schema_version":1,"command":"status","outcome":"ok","exit_code":0,
 "findings":[],"changes":[],"next_actions":[],"report_path":null}
```

Exit codes preserve the current family convention: `0` success (warnings allowed and explicit),
`1` policy finding or safe domain refusal, `2` environment/operation failure, `3` invalid usage or
schema. JSON goes to stdout; diagnostics go to stderr. Human output always states whether mutation
occurred and gives a next action.

Append redacted JSONL events to `.vendomat/state/events/YYYY-MM-DD.jsonl` with command ID,
timestamps, tool/schema versions, repo/session IDs, declared capabilities, outcomes, and artifact
hashes. Do not log file contents, queries marked sensitive, credentials, or full command output.
Reports are immutable per command/session.

Use an OS advisory root lock for manifest-changing/bootstrap operations, per-repository locks for
mutation, and per-session locks for state transitions. Lock metadata has PID/start time/command ID;
`vendor locks inspect` diagnoses owners. Never break a live lock. `locks recover` removes a stale
lock only after PID/start-time and protected-state checks and explicit confirmation. Read commands
avoid locks or use snapshots.

All caches carry schema/tool/input hashes and are safe to delete. `vendor cache rebuild` and
`vendor knowledge index --rebuild` recover without network. `doctor` detects abandoned worktrees,
half-written state, hook drift, path/remote mismatch, stale caches, and retained failures. Recovery
commands are scoped (`session recover ID`, `portable discard ID`, `hooks repair REPO`) and preview
actions. No recovery deletes or resets a developer branch.

## 4. Current repository retention matrix

| Current capability/asset | Classification | Evidence | Migration implication |
|---|---|---|---|
| Python package scaffold, `src/` layout, Typer/Pydantic edge, 0/1/2/3 convention | **Retain substantially** | `pyproject.toml`, `src/vendomat/cli.py`, `src/vendomat/checks.py`, CLI tests | Keep the package and output convention; replace product commands/models and relax Python floor if fleet permits. |
| Testee single verification interface and devenv test tasks | **Retain substantially** | `.claude/skills/testee/SKILL.md`, `testee.toml`, `nix/testee.nix` | Continue all verification through Testee; remove the unmanaged absolute/sibling development assumption by declaring `testee` as the first workspace binding. |
| Pure `Path`-based functions and injected metadata lookup | **Reuse as a pattern/test/reference** | `add.py`, parser/install tests | Preserve dependency injection and temp-fixture testability in inspectors/adapters; do not carry the old entry model. |
| PEP-503 package normalization and dependency fixtures | **Reuse as a pattern/test/reference** | `deps.py`, `tests/test_deps.py` | Extract normalization into uv package identity; replace precedence/all-transitive semantics with binding-aware discovery. |
| No-clobber drafting and visible DRAFT/TODO state | **Reuse as a pattern/test/reference** | `add.py`, `tests/test_add.py` | Apply to inbox/case/proposal promotion and versioning; old `vendor add <lib>` command retires. |
| Idempotence, usage gating, front-matter/TOML round trips | **Reuse as a pattern/test/reference** | `install.py`, `models.py`, `tests/test_install.py`, `tests/test_models.py` | Reuse test techniques and validation posture for knowledge schemas/indexing; replace file-copy installation. |
| `vendor/libs/typer` curated content | **Reuse as a pattern/test/reference** | `vendor/libs/typer/{meta.toml,notes.md,SKILL.md}` | Manually review and migrate useful Typer guidance into a sourced proposal/answer; never auto-approve legacy prose. |
| Current `sync` knowledge copying | **Retire** | `cli.py`, `install.py` | No skills are copied into child repos. Agents query bounded approved context centrally; migration lists stale `dep-*` but deletes nothing automatically. |
| Current `add` distribution scaffolder | **Replace** | `cli.py`, `add.py` | Replace with structured inbox/case/proposal commands; keep offline/no-clobber principles. |
| Current `doctor` knowledge freshness behavior | **Replace** | `checks.py` | New doctor covers root, clones, remotes, locks, sessions, hooks, adapters, packaging, and knowledge. Advisory vs fatal findings become typed policy. |
| Free-form `.vendor-source` manifest | **Retire** | `install.py`, `checks.py` | Derived inventory/state become versioned JSON with content hashes; durable truth is `vendor.toml` and approved records. |
| Nix flake/devenv CLI delivery | **Reuse as a pattern/test/reference** | `flake.nix`, `devenv.nix`, `devenv.yaml`, `modules/devenv.nix` | Retain pinned Nix delivery and quiet shell behavior, but replace consumer wheel/knowledge module with root workspace packaging and hook launcher. |
| `PyYAML`/`tomli-w` packaging | **Replace** | Declared in `pyproject.toml`, absent from `flake.nix` `buildPythonApplication` dependencies | New Nix package must declare the complete Python closure and include an import/CLI smoke test. If the legacy package remains during transition, fix this defect before calling it supported. |
| `mkArtifact` dispatcher and `mkMaturinWheel` builder | **Reuse as a pattern/test/reference** | `lib/mkArtifact.nix`, `lib/mkMaturinWheel.nix` | Archive as optional artifact prior art. Wheel building is neither dependency representation nor v1 workspace management; do not make it an adapter capability. |
| Wheelhouse, `UV_FIND_LINKS`, `UV_NO_BUILD_PACKAGE`, `vendor.self` | **Reuse as a pattern/test/reference** | `flake.nix`, `modules/devenv.nix`, README | Carry forward explicit local/portable separation and fail-loudly safety; retire the hard-coded product path. A future artifact service must be independently proposed. |
| Hard-coded `pyjutsu` flake input, absolute `/home/andrew/...`, x86_64/Python 3.13 assumptions | **Retire** | `flake.nix`, README, module examples | Replace topology with relative manifest paths and canonical remotes. Platform/interpreter constraints become tool packaging metadata, never library identity. |
| Current `testee = { path = "../testee" }` development source | **Replace** | `pyproject.toml`, `uv.lock` | Use it as the first managed uv binding and integration fixture; portable committed form becomes canonical Git+SHA. |
| Shared Cargo target/sccache module behavior | **Reuse as a pattern/test/reference** | `modules/devenv.nix` | Useful explicit performance configuration but outside workspace core; never silently set child build environments. |
| Existing 54 unit-test cases | **Reuse as a pattern/test/reference** | `tests/test_{add,checks,cli,deps,install,models}.py` | Preserve relevant normalization, validation, no-clobber, idempotence, CLI, and exit tests while replacing assertions tied to copied skills. |
| README wheel claims and operator examples | **Replace** | `README.md` | Write workspace bootstrap/local/portable/hook/recovery/portal guide; retain legacy artifact notes in history, not primary docs. |
| Old design and implementation plan | **Retire** | `docs/DESIGN.md`, `docs/IMPLEMENTATION_PLAN.md` | Superseded because they reject the manifest/registry now required. Keep accessible in Git history and cite lessons only. |
| Historical scratch kickoff packets | **Reuse as a pattern/test/reference** | `.scratch/projects/01-face-b-knowledge/` | Evidence of sequencing and conventions only; no product authority. |
| Existing unrelated working-tree changes | **Retain substantially** | `flake.nix`, `flake.lock` noted by review | Do not overwrite or fold them into the rewrite. Begin implementation with a cleanly scoped branch/change after owner disposition. |

## 5. Target layouts

Implementation repository:

```text
vendomat/
├── src/vendomat/
│   ├── cli.py, output.py, errors.py, capabilities.py
│   ├── workspace/{discovery,manifest,inventory,graph,bootstrap}.py
│   ├── git/{runner,identity,objects,worktrees,hooks,reachability}.py
│   ├── adapters/{base,host}.py
│   ├── adapters/uv/{discover,render,lock,verify}.py
│   ├── sessions/{models,engine,recovery}.py
│   ├── knowledge/{models,store,search,context,promotion,mcp}.py
│   └── state/{events,locks,cache,redaction}.py
├── schemas/{vendor-v1,config-v1,session-v1,knowledge-v1}.json
├── tests/{unit,contract,integration,fixtures}/
├── nix/{package,module,checks}.nix
├── flake.nix, devenv.nix, pyproject.toml, testee.toml
└── docs/{operator-guide,manifest,adapters,security,recovery}.md
```

Workspace control-plane repository:

```text
~/Vendor/
├── vendor.toml
├── flake.nix, flake.lock, devenv.nix, devenv.yaml
├── policy/{hooks.toml,redaction.toml}
├── knowledge/{inbox,cases,proposals,answers,playbooks}/
├── schemas/                  # optional pinned copies/links for editors
├── README.md
├── vendomat/, testee/, ...  # ignored independent clones
└── .vendomat/
    ├── config.toml, bin/, state/, locks/, sessions/, worktrees/
    ├── reports/, cache/, indexes/, private/, hooks/
    └── .gitignore marker
```

The root `.gitignore` is generated from a fixed control-plane allowlist plus manifest clone paths.
`manifest validate` compares it to the manifest. Updating ignore rules is a separate previewed
control-plane change; initialization never stages or commits it.

## 6. Initial command and interface specification

All mutators preview by default and require `--apply`, except commands whose name is itself an
explicit state transition (`inbox create`, `answer propose`, `answer approve`, `portable discard`);
those still support `--dry-run`. `--json`, `--root`, and `--no-network` are global where meaningful.

| Command | Inputs and output | Mutation | Principal failures |
|---|---|---|---|
| `init [root] [--adopt] [--apply]` | Candidate files/collisions | Root/control files only with apply | Nonempty/unrelated Git root, unsafe path (1/3), I/O (2) |
| `manifest validate` | Typed errors/warnings | None | Invalid/unsupported schema (3), unsafe topology (1) |
| `doctor` | Tool, root, clone, remote, hook, lock, session, adapter, index checks | None | Findings 1, environment 2 |
| `inventory [--refresh]` | Desired/present/identity/capabilities | Refresh writes disposable cache only when explicitly requested | Inspection 2 |
| `status [repo]` | Dirty/HEAD/mode/session/findings; local only | None | Identity/inspection 1/2 |
| `sync --clone-missing [--apply]` | Clone plan/results | Missing clone creation only | Collision/remote mismatch 1; auth/network 2 |
| `sync --fetch [--apply]` | Per-repo fetch plan/results | Remote refs only; no merge/checkout | Dirty tree does not block; auth/network 2 |
| `graph [--reverse ID]` | Declared plus discovered managed edges | None | Ambiguous/invalid binding 1 |
| `link DEP --repo ID [--apply]` | Plan/diff/lock/verify report | Declared files only; rollback on failure | Wrong clone, dirty target files, unsupported form, lock conflict 1/2 |
| `check [--repo ID]` | Local-mode and policy findings | None | Policy finding 1 |
| `prepare-push --repo ID` | Session ID, patch, provenance, verification | Derived worktree/session only | Unpublished SHA, unsupported lock, operation in progress 1; tool/network 2 |
| `portable diff ID` | Stored summary/unified diff | None | Unknown/corrupt session 2/3 |
| `portable apply ID` | Preflight and affected paths | Active working files only; never index/commit | Dirty/diverged checkout 1; rollback failure 2 |
| `portable discard ID` | Cleanup/recovery-patch result | Session only | Modified worktree refusal 1 |
| `verify --portable [--repo ID]` | CI findings/JSON/SARIF later | None, works without sibling clones using bundle | Local path, mutable/unreachable ref, lock drift 1 |
| `hooks install [--all] [--adopt-existing] [--apply]` | Per-repo plan/hashes | Hook files/state only | Existing hook/drift 1; permissions 2 |
| `hooks verify|uninstall` | Integrity or restoration plan | Uninstall only explicitly | Modified dispatcher/preserved hook 1 |
| `ask QUERY` | Approved scoped answers or unknown | None | Index failure falls back to scan; invalid scope 3 |
| `context --repo ID --task TEXT [--budget N]` | Bounded context packet | None | Unauthorized scope 1; invalid budget 3 |
| `inbox create ...` | New validated record ID | Tracked record, sanitized | Sensitive/unvalidated content 1/3 |
| `case open|update ID` | Evidence record/version | Tracked case, explicit | Scope/transition violation 1 |
| `answer propose CASE` | Proposal/diff | Tracked proposal | Missing evidence/DRAFT policy 1 |
| `answer approve ID` | Signed content-state transition | Approved version; human-only | Agent/nonhuman caller, stale evidence 1 |
| `knowledge index --rebuild` | Counts/content hash | Disposable SQLite index | Corrupt records 1; I/O 2 |
| `portal mcp` | stdio MCP protocol | Tool-dependent; no network/source writes | Auth/protocol 1/3 |

`link` never means “apply immediately”: human output ends with the exact repeated command plus
`--apply`. On successful application it lists changed files and verification; it never stages.

CI receives a small generated, committed verification bundle containing schema version, binding
IDs, package identities, portable policies, canonical public/private remote fingerprints, and
adapter version constraint. It contains no workspace paths or credentials. `vendor verify` can
also read full `vendor.toml` in the control-plane workspace.

## 7. Threat and failure model for transactions

| Threat/failure | Required behavior and recovery |
|---|---|
| Dirty active consumer | Prepare excludes it and warns; apply refuses. Commit/stash manually, or keep using session only. No reset/stash by vendomat. |
| Dirty dependency | Never use dirty bytes as portable provenance. Commit manually; rerun. |
| HEAD/index changes after preview | Before-hash/HEAD compare aborts without writes. Generate a fresh plan/session. |
| Lockfile generator conflict/failure | Confined to staged tree/worktree; retain failed session and bounded logs. Active tree unchanged. |
| Partial file write/process crash | Temp files + fsync + atomic rename; snapshots and journal identify incomplete transition. `session recover` restores or completes only matching hashes. |
| Patch partially applicable | `git apply --check` plus clean/exact base; snapshots restore every target. Never touch index. |
| Unpushed dependency SHA | Session fails readiness, reports remote/SHA/manual push command; never pushes. Rerun after publication. |
| Offline/stale refs | Local inspection/link works. Portable session may render but cannot be green without policy-sufficient cached proof; hook rejects with fetch/prepare guidance. |
| Worktree already registered/abandoned | Unique IDs; doctor reconciles Git worktree registry and session journal. Cleanup only terminal clean sessions. |
| Concurrent commands | Per-root/repo/session locks and hash rechecks serialize mutations; read snapshots may report staleness. |
| Symlink/path swap | No-follow/realpath checks repeated after lock and before rename; abort on identity change. |
| Malicious manifest/repository data | Strict schemas, no shell/plugin execution, bounded parsing/output, allowlisted paths/remotes. |
| Hook unavailable/timeout | Fail closed with reinstall/bypass text; CI remains authoritative. |
| Secret in command output/evidence | Redact before persistence; sensitive raw capture stays private and cannot be promoted until sanitized. |
| Stale approved answer | Omit after expiry or source-revision policy mismatch; return unknown/link to case, never silently trust. |

## 8. Phased roadmap

### Phase 0 — preserve evidence and establish the new contract

**Capability.** No new product behavior; maintainers have accepted decisions, schemas, fixtures,
and a migration inventory.  
**Likely files.** This plan, ADRs, `schemas/`, fixture repositories, updated README roadmap.  
**Dependencies.** Owner confirmations below; disposition of existing `flake.*` changes.  
**Migration.** Freeze legacy Face A/B features except critical packaging repair. Record Typer
knowledge as an unapproved migration candidate.  
**Verification.** Schema examples validate; threat-model review maps every mutator to authority and
rollback.  
**Acceptance.** Every implementation task cites an invariant, command contract, and objective test;
no task assumes `pyjutsu` or an absolute home path.

### Phase 1 — workspace skeleton and safe inventory

**Capability.** Initialize/adopt, validate manifest, clone missing repos without collision, and run
doctor/inventory/status offline.  
**Files.** CLI/output/errors; workspace discovery/manifest/bootstrap/inventory; Git identity/runner;
state events/locks; Nix package and docs.  
**Dependencies.** Python package, complete Nix dependency closure, Git.  
**Migration.** Current repo becomes one declared child; no source history moves. Existing clones
are validated and adopted.  
**Verification.** Unit schema/path/URL tests; Git fixtures for absent/matching/mismatched/nonempty
paths; Nix-built CLI import/smoke; offline tests.  
**Acceptance.** A fresh temp root and a pre-populated root both reach accurate inventory; clone
preview has zero writes; apply never disturbs an existing directory or clone.

### Phase 2 — uv discovery, graph, portable verification, and hook

**Capability.** See the managed graph, detect unsafe committed uv references, install/verify a
fast pre-push hook, and run the identical CI check.  
**Files.** adapter base/host and uv discover/verify/tree scanner; Git objects/reachability/hooks;
graph; verification bundle.  
**Dependencies.** Phase 1; pinned uv schema knowledge, but hook itself does not invoke uv.  
**Migration.** Declare vendomat→testee binding. Existing local path may remain in working state;
hook exposes committed portability debt with next action. Existing hooks require adoption.  
**Verification.** Adapter contract corpus; pushed-range tests for update/new/delete/multiple refs;
existing-hook coexistence; missing executable/timeout/bypass; p95 benchmark; CI without `~/Vendor`.
**Acceptance.** A commit containing the current `../testee` source is rejected in under budget with
the exact prepare command; an uncommitted local link does not block an unrelated portable push.

### Phase 3 — previewed local linking

**Capability.** Link vendomat to the sibling testee source, see exact changes, update a coherent uv
lock, verify, and roll back on failure.  
**Files.** uv render/lock; change-plan and atomic mutation engine; repository locks/reports.  
**Dependencies.** Phases 1–2; pinned uv executable; matching dependency clone.  
**Migration.** Replace current hand-authored path binding through an explicit plan. No automatic
cleanup of legacy skill directories.  
**Verification.** Golden manifest/lock fixtures; changed-hash, dirty file, symlink, generator
failure, offline and rollback injection tests.  
**Acceptance.** Preview is byte-nonmutating; apply changes only named files, local import resolves
to the sibling, and injected failures restore original hashes.

### Phase 4 — isolated portable sessions

**Capability.** Prepare and verify a portable Git+SHA uv state without altering the active local
checkout; inspect/apply/discard and recover failures.  
**Files.** sessions engine/models/recovery; Git worktrees/reachability; uv portable render/lock;
reports and CI verify.  
**Dependencies.** Phase 3; allowed remote and published dependency commit.  
**Migration.** First successful session replaces the committed machine-local binding. Active local
representation can remain as uncommitted daily state.  
**Verification.** Real bare remotes/worktrees; dirty active tree, divergent HEAD, unpublished SHA,
auth/offline, lock conflict, crash points, concurrent sessions, cleanup.  
**Acceptance.** Original checkout hashes remain unchanged after prepare; green artifacts prove
remote reachability and lock coherence; apply refuses dirty/diverged state and succeeds atomically
on exact clean base.

### Phase 5 — trusted knowledge portal and v1 release

**Capability.** Create/triage cases, propose/approve concise guidance, ask/context within a budget,
and use the four stdio MCP tools without implicit authority.  
**Files.** knowledge models/store/search/context/promotion/MCP; redaction; tracked templates/docs.  
**Dependencies.** Phase 1 identity/visibility and state services; phases 2–4 provide useful state
facts but portal can be developed against fixtures.  
**Migration.** Typer notes become a proposal linked to legacy evidence and require review. Old
installed `dep-*` skills are reported as legacy; removal is a separate user action.  
**Verification.** Schema/state-machine, approval authorization, expiry/withdrawal, deterministic
ranking, corrupted-index fallback, visibility/redaction, prompt-injection fixtures, context budget,
MCP protocol/capability tests.  
**Acceptance.** A repeated repository question returns only a short approved answer plus evidence
links and verification; no match returns unknown; an agent can propose but cannot approve or gain
network/source-write authority.

### Phase 6 — hardening and additional adapters (post-v1)

**Capability.** Operational migrations and one new adapter at a time based on actual fleet demand.
  
**Files.** performance/recovery refinements; selected adapter and fixtures.  
**Dependencies.** Production evidence from v1; owner selects Cargo, Nix flakes, Node, or Go.  
**Migration.** Bindings remain validate-only until their adapter passes the entire contract.  
**Verification.** Same local/portable/dirty/lock/offline/worktree/hook corpus for every adapter;
cross-version fixtures.  
**Acceptance.** No adapter is labeled render-capable until it creates a green isolated portable
session and CI verification from a repository without sibling clones.

## 9. Test strategy

- **Unit:** root precedence, schema/version/unknown fields, path containment and symlink attacks,
  remote normalization, package IDs, capability negotiation, change hashes, redaction, exit/JSON
  envelopes, event and record state machines, ranking and budgets.
- **Adapter contract:** a shared harness requires discovery idempotence, read-only planning,
  declared-file boundaries, local↔portable semantic round trips, deterministic diffs, lock
  coherence, offline declaration, unknown-format refusal, and treeish scanning. Each supported uv
  and lock schema has golden fixtures; newer schemas fail clearly.
- **Git/worktree integration:** create actual independent and bare repos in temp directories;
  exercise remote aliases, missing/mismatched clones, dirty/indexed/untracked states, operations in
  progress, new/unpublished/reachable commits, worktree create/remove, crash journals, exact-base
  apply, and concurrent locks. Never mock the safety-critical Git behavior exclusively.
- **Hook:** feed real pre-push stdin for updates, creations, deletions, force pushes, multiple refs,
  and zero SHA; verify commit-tree rather than working-tree behavior, existing hook chaining,
  launcher drift, fail-closed/unavailable/timeout/bypass output, and latency budgets.
- **Nix/devenv:** evaluate supported systems; build the CLI with declared Typer, Pydantic, PyYAML,
  and tomli-w closure; run import/help/schema smoke in the derivation; enter the root shell without
  mutation; verify launcher uses the pinned package. Test the supported Python floor explicitly.
- **Offline/error recovery:** deny network and credentials; inject Git/uv failures and process
  termination at journal points; assert active file hashes/index/HEAD remain unchanged or snapshots
  restore; rebuild every disposable cache from durable inputs.
- **Knowledge lifecycle:** intake→case→proposal→approval→expiry/withdrawal, unauthorized approval,
  content-hash change, sensitive redaction, visibility filtering, malicious instructions in source
  and evidence, index corruption/fallback, exact context budget, and MCP tool authority.
- **End-to-end acceptance:** scripted temp `Vendor` proves all six quality-bar scenarios. Capture
  human and JSON golden output, report artifacts, and mutation before/after inventories.

Verification continues through `devenv shell testee verify --mode quick` during development and
`--mode detailed`/CI for integration. Nix and multi-repository fixtures must be Testee targets so a
passing unit subset cannot masquerade as full verification. If Nix daemon access is unavailable,
report packaging as unverified rather than treating Python tests as equivalent.

## 10. Risks, non-goals, and sequencing constraints

### Principal risks

- uv manifest/lock semantics change. Pin uv, version adapter support, maintain cross-version
  fixtures, and refuse unknown schemas.
- Portable commit ergonomics may tempt users to commit local representations. The hook and CI
  guard remote visibility, but documentation must explain the intentional apply/commit workflow.
- Reachability checks can false-reject offline or with stale refs. Prefer conservative rejection
  with an explicit fetch/rerun path over accepting an unpublished object.
- Root Git ignore drift could expose child directories. Generate/verify exact clone-path ignores,
  and test `git status` from the root; never stage or commit automatically.
- Hook bypass is inherently possible. State plainly that hooks are feedback and CI is enforcement.
- Knowledge can leak secrets or amplify prompt injection. Default indexing is narrow, promotion is
  human-controlled, redaction precedes persistence, and approved context remains bounded.
- The current dirty `flake.nix`/`flake.lock` overlap with packaging work. Resolve ownership before
  modifying those files; implementation must not overwrite them.

### Non-goals

No monorepo/submodules, registry, release manager, publisher, artifact cache, autonomous commits or
pushes, automatic pulls/branch changes, background daemon, browser UI, vector database, generic
dependency rewriter, child-repo source indexing, secret manager, or cross-repository transaction.
Vendomat does not guarantee that bypassed hooks prevent bad pushes; CI policy does.

### Sequencing constraints

Manifest/path/identity and Git object-reader correctness precede mutation. Read-only uv validation
and CI equivalence precede local render. Local render/rollback precede portable render. Portable
sessions precede claiming hook remediation is actionable. Knowledge approval/visibility precede
automatic context or MCP exposure. A second adapter follows—not precedes—production evidence from
the full uv lifecycle.

## 11. Decisions requiring human confirmation

These are the only owner choices that materially change the plan:

1. **First real binding:** confirm that vendomat→testee with uv represents the fleet's highest-value
   local/portable case. If not, name the actual consumer/dependency and ecosystem; do not choose an
   adapter from hypothetical breadth.
2. **Root control-plane remote/privacy:** provide the remote (if any), whether tracked cases/inbox
   may be pushed, and the reviewer identity policy. The default is a private root repository with
   sanitized durable records.
3. **Python floor/platforms:** confirm Python 3.12+ versus retaining 3.13 and list required Nix
   systems. This affects package/test matrix, not workspace metadata.
4. **Hook failure/bypass policy:** confirm fail-closed locally and whether reasoned bypass is
   permitted. CI portable verification remains required either way.
5. **Reachability proof:** confirm that a network-fresh remote advertisement is mandatory for a
   green portable session, with offline cached proof only advisory. This plan recommends yes.
6. **Context defaults:** confirm the 1,200-token estimate, knowledge retention periods, and whether
   two-person approval is necessary in a personal workspace.
7. **Legacy Face A:** confirm archival/removal timing for the pyjutsu wheel outputs. This plan keeps
   them operational only during migration and excludes them from workspace v1.

Everything else is intentionally specified so implementation can proceed in independently
verifiable phases without rediscovering the architecture.

# vendomat — current-state code review

Reviewed: 2026-07-12.  This is a read-only review of the checked-out repository, not a
proposal for the new `~/Vendor` workspace.  The repository is a small, focused prototype with
two largely independent products: a Nix-native wheel cache (**Face A**) and a Python CLI that
copies usage-gated dependency knowledge into consumer repositories (**Face B**).

## Executive assessment

vendomat has a credible, well-tested *local* knowledge workflow and a concise Nix proof of the
“build a native wheel once” mechanism.  It is not currently a vendor workspace manager.  It has
no registry of repositories, clone/sync/status operations, dependency graph, local-path-to-Git
conversion, hook installation, release transaction, inbox/portal, cross-repo search, or agent
routing.  Its current assumptions are instead a fixed `pyjutsu` input at a hard-coded path and a
single authored knowledge entry for `typer`.

That distinction matters for a ground-up `~/Vendor` design: the existing implementation offers
useful lessons and potentially reusable behavior, but its data model begins at **Python package
dependencies**, not **personal Git repositories**.

## Repository and working-tree state

- The committed project is a Python 3.13 package (`pyproject.toml:1-54`) plus Nix flake/devenv
  integration.  Its console command is `vendomat` (`pyproject.toml:32-33`).
- The latest committed slices are M0 (CLI scaffold), M2 (knowledge install), and M3 (knowledge
  draft scaffolding); Git history names them explicitly in commits `8d4c991`, `5847631`, and
  `0c298b4`.
- The working tree has two pre-existing, unrelated-to-this-review modifications: `flake.nix` and
  `flake.lock` change the local input spelling from `.../Pyjutsu` to `.../pyjutsu`.  This review
  did not alter them.
- No `AGENTS.md` exists. Repository-local operational instructions are in
  `.claude/skills/gitman/SKILL.md` and `.claude/skills/testee/SKILL.md`; the latter requires
  verification through `testee`, rather than invoking pytest/ruff/ty directly.

## Architecture

```text
                   Face A: binary artifact path

local pyjutsu Git checkout
      │ git+file Nix input
      ▼
flake.nix → mkArtifact → mkMaturinWheel → Nix-store .whl
                                             │
                                             ▼
                                    wheelhouse (symlinkJoin)
                                             │
consumer devenv module ── UV_FIND_LINKS / UV_NO_BUILD_PACKAGE ──► uv install

                   Face B: knowledge path

consumer repo's uv.lock | pyproject.toml | repoman.lock
                   │ first existing file wins
                   ▼
              normalized package names
                   │ intersect
vendor/libs/<dependency>/{meta.toml,notes.md,SKILL.md}
                   │ copy matching SKILL.md files
                   ▼
consumer/.claude/skills/dep-<dependency>/SKILL.md
consumer/.claude/skills/.vendor-source
```

The two faces are coupled only by repository branding, the `modules/devenv.nix` import, and the
intention that both consume a `vendor/` directory.  Face A does not read that directory; Face B
does not know which repository/Git revision a dependency came from.

## Implemented behavior

### Face A — native artifact vending

1. `flake.nix:4-18` defines one non-flake source input, `pyjutsu`, as an absolute
   `git+file:///home/andrew/Documents/Projects/pyjutsu` checkout.  The comments correctly note
   that `git+file` avoids copying untracked build output into the store.
2. `lib/mkArtifact.nix` is a one-entry dispatcher whose only registered builder is
   `maturinWheel`.  It has a reasonable future extension seam and fails clearly on an unknown
   builder.
3. `lib/mkMaturinWheel.nix` imports `Cargo.lock`, runs `maturin build --offline --release` against
   Python 3.13, and emits the generated wheel(s) into a derivation output.  It intentionally does
   not run the source crate’s tests.
4. `flake.nix:40-80` builds `pyjutsu-wheel` and exposes a `wheelhouse` made with `symlinkJoin`.
   `default` points to this wheelhouse.  The flake declares only `x86_64-linux`
   (`flake.nix:21-24`).
5. A consumer imports `modules/devenv.nix`.  With `vendor.enable = true`, the module provides
   `UV_FIND_LINKS`, a `vendor:status` task, optional shared Cargo+sccache configuration, and
   `UV_NO_BUILD_PACKAGE` for `vendor.libs` minus `vendor.self`
   (`modules/devenv.nix:35-64`, `82-111`).  Thus a missing compatible wheel is intended to fail
   rather than silently compile from source.

### Face B — per-dependency knowledge

1. `deps.py` reads **exactly one** dependency source, in strict precedence: `uv.lock`, then
   `pyproject.toml`, then `repoman.lock` (`src/vendomat/deps.py:80-98`).  It PEP-503-normalizes
   names.  `uv.lock` contributes all listed packages (including transitive dependencies);
   pyproject parsing includes direct, optional, and string dependency-group entries; repoman
   parsing includes its self-entry and manager entries.
2. `install.py` enumerates `vendor/libs/*` entries that contain a `SKILL.md`, intersects those
   names with detected dependencies, and copies matches to flat sibling directories named
   `dep-<lib>` under a configured skills root (`src/vendomat/install.py:31-101`).  It writes a
   simple text `.vendor-source` manifest recording the installed skills, pin values, and installed
   vendomat version.
3. The only curated shipped entry is `vendor/libs/typer/`.  It has metadata, raw notes, and a
   useful agent skill.  Its metadata pins Typer to `0.12.5`; its skill speaks to CLI construction,
   testing, and the family exit-code convention.
4. The Typer CLI supplies `sync`, `add`, and `doctor`.  It uses `DEVENV_ROOT`/the CWD as consumer
   root; `REPOMAN_SKILLS_DIR` or `.claude/skills` as destination; and a command option or
   `VENDOMAT_VENDOR_ROOT` as the read-side vendor tree (`src/vendomat/cli.py:31-72`).
5. `vendomat add <lib>` is deliberately offline: `add.py` queries installed distribution metadata
   via an injectable function, drafts the three entry files, marks unresolved prose as DRAFT/TODO,
   validates structured metadata/frontmatter, and refuses to overwrite unless `--force`
   (`src/vendomat/add.py:49-208`).  This is a safe scaffolder, not an agent research capability.
6. `doctor` checks installed skills and vendomat-version manifest freshness; it also validates all
   author-side frontmatter/meta when a vendor tree exists.  All knowledge drift outcomes are
   warn-only and exit 0; `fail` maps to exit 2 (`src/vendomat/checks.py:18-99`).
7. When `knowledge.enable = true`, `modules/devenv.nix:113-130` puts a Nix-built vendomat CLI on
   PATH, points it at the flake’s immutable store copy of `vendor/`, and exposes an explicit
   `vendor-sync` script.  It does **not** automatically run on shell entry.

## Strengths

- **Clear division between development and consumption.** `vendor.self` avoids accidentally
  replacing a library’s own editable build with its wheel, while `UV_NO_BUILD_PACKAGE` guards
  consumers against a slow, invisible fallback (`modules/devenv.nix:29-32`, `97-101`).
- **Good local-testability in Face B.** Parsing, installation, drafting, and validation operate
  on explicit `Path` arguments or injected metadata.  This supports focused unit tests without a
  Nix build, network, or sibling repository.
- **A sensible conservative curation posture.** The generated knowledge entry is never silently
  published: existing entries are protected from clobbering and unresearched content remains
  visibly marked as draft (`src/vendomat/add.py:25-33`, `180-208`).
- **Useful compatibility hygiene.** The package-normalization function, `dep-` namespace, flat
  skill layout, and manifest attempt to coexist with the related `*man` environment rather than
  overwrite it.
- **Tests track the implemented Python contract.** There are 54 named unit tests across six test
  modules. They cover dependency-source precedence, normalized matching, idempotent installation,
  manifest pins, CLI exit paths, draft rendering/no-clobber behavior, and model/frontmatter
  round-trips. This is strong coverage for the currently narrow Python surface.
- **Documentation communicates the intended first value well.** `README.md` makes the Nix-store
  wheel flow concrete. `docs/DESIGN.md` and `docs/IMPLEMENTATION_PLAN.md` candidly call the wider
  fleet/workspace layer deferred, rather than pretending it already exists.

## Gaps and risks

### Fundamental scope gap relative to `~/Vendor`

The requested new concept needs a canonical filesystem of Git clones and a cross-repository
control plane. Current code has none of the foundational records or commands:

- no `$VENDOR_ROOT` / `~/Vendor` concept (only `VENDOMAT_VENDOR_ROOT`, which means the immutable
  *knowledge data* directory, not a clone workspace);
- no registry mapping logical name → local checkout, remote URL, default branch, package
  identity, ecosystems, or dependency rules;
- no clone, discover, sync, status, dirty-check, branch/checkpoint, or workspace-graph operation;
- no Git hooks at all (there is no `hooks/` directory or `pre-push` implementation);
- no safe conversion between local references and Git references, no lockfile regeneration, no
  temporary worktree/transaction, and no push/revision-reachability validation;
- no inbox, issue schema, portal/API/MCP interface, repository-scoped agent, investigation store,
  search/index, approval state, answer distillation, or automatic context assembly.

The present `vendor/libs/` is a catalog of third-party Python *knowledge*, not local clones of
personal libraries.  The names and responsibilities should not be conflated in a rewrite.

### Face A risks

- **One hard-coded library and one machine path.** `flake.nix:15-18` is an absolute checkout path
  with a single `pyjutsu` input.  There is no declarative, user-editable multi-library catalog;
  Nix input overrides are a manual per-invocation escape hatch, not workspace management.
- **Platform and interpreter restriction.** Only `x86_64-linux` and `python313` are emitted.
  Maturin ABI/tag compatibility can reject consumers on other platforms/Python floors.  The README
  documents this constraint, but no machine-readable compatibility check reports it early.
- **Nix build is unverified in this checkout.** `devenv shell testee verify --mode quick` was
  attempted through the repository-mandated interface and failed during Nix/devenv evaluation,
  before tests ran, because this environment cannot access `/nix/var/nix/daemon-socket/socket`
  (`Operation not permitted`).  Consequently neither Python tests nor `nix build .#wheelhouse`
  were confirmed here.
- **The Nix-built CLI dependency closure is incomplete.** `pyproject.toml:14-19` requires
  `pyyaml` and `tomli-w`; the Nix `buildPythonApplication` lists only Typer and Pydantic
  (`flake.nix:55-68`).  `models.py` imports both `tomli_w` and `yaml` at module load.  Therefore
  the consumer-facing Nix CLI will likely fail to import unless those happen to be pulled in
  indirectly, which is not declared or reliable.  This is the most concrete implementation
  defect found in the review.
- **The wheel builder assumes an ordinary locked Cargo project.** It reads `Cargo.toml` and
  imports `Cargo.lock` unconditionally; Git Cargo dependencies require hash maintenance and
  nonstandard maturin projects may need additional build inputs.  The README identifies part of
  this, but the builder does not detect/report the conditions specially.

### Face B semantic and operational risks

- **“Usage gated” does not necessarily mean direct usage.** Selecting `uv.lock` first imports all
  resolved packages, including transitive dependencies (`deps.py:39-41`).  The outcome can install
  skills for libraries the repository never imports.  Selecting a single source also means a
  stale lock hides a newly declared dependency, while an existing `uv.lock` prevents the richer
  `repoman.lock` toolchain information from contributing.
- **No cleanup of obsolete skills.** `install_knowledge` copies current matches but never removes
  `dep-*` directories that no longer match.  It overwrites `.vendor-source` to say only the new
  set is installed, leaving stale files that an agent can still discover.  `doctor` checks missing
  expected skills but does not detect unexpected installed skills.
- **Manifest freshness is weak.** It checks whether a literal `vendomat version: …` occurs in a
  free-form text file, rather than parsing a versioned structured manifest.  It does not verify
  source revision/content hashes, copied SKILL.md hashes, per-lib pins against a resolved package
  version, or the manifest’s installed-skill list.  M4-style review-on-bump is documented but not
  implemented.
- **Malformed source metadata can break `sync`.** `lib_pin` parses TOML without validation/error
  handling.  `expected_libs` requires only SKILL.md, so an entry with malformed/missing
  `meta.toml` can be matched and raise during manifest generation.  `doctor`’s warn-only
  frontmatter check does not protect `sync` beforehand.
- **Knowledge validation is permissive.** `SkillFrontmatter` only guarantees a nonempty `dep-`
  prefix; it does not ensure the frontmatter name corresponds to its directory/library.  `LibMeta`
  does not validate its `lib.name` against the directory.  A mismatched but syntactically valid
  entry can be installed and labeled incorrectly.
- **No concurrency or containment safeguards.** Copy/write operations lack atomic writes,
  locking, destination traversal controls, or permissions handling.  A user-supplied absolute
  `REPOMAN_SKILLS_DIR` causes `repo_root / skills_dir` to resolve outside the repo in Python,
  which may be intended flexibility but deserves an explicit policy for a workspace tool.
- **No remote documentation/research.** `vendor add` intentionally operates offline, so it cannot
  perform the agent inquiry, source/history lookup, issue resolution, or answer prebuilding
  described for the new system.  The current skill is static markdown copied into consumers.

### Documentation and design drift

- The README presents Face A as end-to-end proven, while this repository has no integration test
  fixture that builds the wheelhouse and installs it in a consumer.  The plan explicitly identifies
  the essential repoman-side `wheel:` resolver work as a separate M1b change; it is not in this
  repository.  Current Nix environment variables alone cannot make an existing local/Git
  dependency resolve as a wheel.
- `docs/DESIGN.md` describes several deferred milestones and adjacent repositories.  It is valuable
  history, but it is not an implementation specification for a fresh workspace product.  In
  particular, it deliberately rejects a `vendomat.toml`/registry and fleet scan—exactly the
  capabilities the new concept now needs.
- Several comments retain milestone wording after implementation (for example `cli.py:5-7` says
  sync/add are wired later).  This does not affect behavior but makes current-state reading less
  precise.

## Test and verification evidence

| Area | Evidence | Result in this review |
| --- | --- | --- |
| Python unit tests | `tests/test_{add,checks,cli,deps,install,models}.py` | 54 test functions present; not executed because devenv evaluation failed before the test runner started. |
| Repository-required test entry point | `.claude/skills/testee/SKILL.md`, `nix/testee.nix` | Used `devenv shell testee verify --mode quick` as required. |
| Environment result | Nix/devenv evaluation | Blocked by denied Nix daemon socket access; not a source-test failure, but no pass claim is justified. |
| Wheel build | `flake.nix`, `lib/mkMaturinWheel.nix` | Not executed; dependent local pyjutsu checkout and Nix daemon are unavailable to this review environment. |
| Consumer integration | README claims and `modules/devenv.nix` | No in-repo integration test found. |

## What is worth carrying forward

For a ground-up workspace rewrite, retain the *ideas*, not the current topology:

1. Keep safe, explicit “local development versus portable consumption” modes; the current
   `vendor.self` and no-fallback approach illustrates the desired safety property.
2. Preserve normalized identifiers and a declarative data format, but raise the primary identity
   from package names to repository records with local path and remote provenance.
3. Continue usage-gated, human-reviewed knowledge publication.  The `add` draft/no-clobber model
   is a good precedent for agent-generated answers that must not become trusted context without
   curation.
4. Make manifests structured, versioned, and content-addressed; use them for both workspace
   state and knowledge provenance.
5. Test the true boundaries: Git push portability, lockfile transformations, clone/remote state,
   worktree restoration, and cross-repo agent context—not only pure parsers and copy routines.

## Bottom line

The library is a solid early prototype of **artifact vending plus curated dependency skills**.
It is not an adaptation-ready implementation of the proposed `~/Vendor` polyrepo workspace.
The new system should treat this codebase as prior art for Nix artifact caching, deterministic
skill installation, validation, and cautious curation, while defining a new repository-centric
core and its Git/agent workflows from first principles.

# Project 04 kickoff — implement Vendomat's Python source catalog

You are working in `/home/andrew/Documents/Projects/vendomat`.

Implement the first vertical slice of **Project 04: Python source catalog for agent grounding**.
Read the complete design first:

```text
.scratch/projects/04-python-source-catalog/CONCEPT_REFINEMENT.md
```

## Goal

Vendomat should maintain locally searchable, pinned source checkouts for approved Python
dependencies, but **must not use those checkouts as Python installation sources**. `uv` remains
the authority for installing normal PyPI wheels or explicitly pinned upstream Git dependencies.

The value is agent grounding: when an agent has a dependency-specific question, it can read the
exact Vendomat-managed local source checkout, its tests, and curated notes quickly and
deterministically.

## Fixed decisions

These are already decided; do not reopen or dilute them.

1. **No third-party path installs.** Vendomat's third-party clone cache must never be written into
   a consumer's `[tool.uv.sources]`, `pyproject.toml`, or `uv.lock`.
2. **No editable installs.** The clone cache is for source investigation, never a live runtime
   dependency.
3. **Owned project repos are canonical.** For a personal dependency such as KnapPy, Vendomat
   references its actual checkout (for example `../knappy`) and must never make a duplicate clone
   under Vendomat.
4. **Third-party repos are Vendomat-managed clones.** Their clone bytes are ignored local state;
   their repository URLs and exact revisions are committed policy.
5. **No silent upstream guessing.** A package receives a source checkout only after a reviewed
   catalog entry explicitly names its repository and immutable commit.
6. **Source revision is not installed-artifact identity.** Doctor/status must show both the
   catalog source revision and the installed version from `uv.lock`; never claim that a source
   commit is byte-identical to a PyPI wheel unless separately proven.
7. **Preserve existing functionality.** The knowledge layer, native-wheel path, and current
   local-path-to-Git publish hook already exist and must remain working. The publisher is now a
   separate, opt-in mechanism, not the general dependency-source workflow.

## First vertical slice

Implement the catalog and source synchronization for these entries:

- `knappy` — kind `project`, canonical local checkout at `../knappy` from a consumer such as
  `../loci-core`.
- `pydantic` — kind `vendor`, Vendomat-managed local Git clone.

Do not modify `../loci-core` in this slice unless the user explicitly asks. It is a read-only
integration target and acceptance reference. Do not create third-party clones during unit tests.

### Required user-visible commands

Implement a `vendomat vendor` Typer command group with at least:

```text
vendomat vendor sync [--repo-root PATH] [--dry-run]
vendomat vendor status [--repo-root PATH]
vendomat vendor doctor [--repo-root PATH]
```

Exact flags may be improved where needed, but preserve the intent.

### Required catalog layout

Use a committed, per-package TOML catalog under this repository:

```text
vendor/python/knappy.toml
vendor/python/pydantic.toml
```

The schema should minimally represent:

- normalized distribution name;
- `kind = "project" | "vendor"`;
- canonical upstream repository URL;
- full immutable Git revision;
- `project` local path for owned repos;
- `cache` location for third-party clones, relative to Vendomat's root.

Validate the schema with Pydantic models. Reuse `vendomat.deps.normalize` for package-name
normalization rather than duplicating PEP 503 logic.

Suggested examples (replace placeholder commits only with verified ones):

```toml
[package]
name = "knappy"
kind = "project"
repository = "https://github.com/Bullish-Design/knappy"
rev = "<40-char-commit>"

[local]
path = "../knappy"
```

```toml
[package]
name = "pydantic"
kind = "vendor"
repository = "https://github.com/pydantic/pydantic"
rev = "<40-char-commit>"

[local]
cache = "vendor/src/pydantic"
```

Do not invent a revision. If a real clone/fetch is required to establish a revision, request the
appropriate network approval, then record the resolved full commit. If this cannot happen in the
current session, leave a clear, validated draft mechanism rather than pretending a fake revision
is usable.

### Source map

For a consumer repository, write a generated ignored map:

```text
<consumer>/.vendomat/sources.toml
```

Example:

```toml
[sources]
knappy = "../knappy"
pydantic = "/absolute/path/to/vendomat/vendor/src/pydantic"
```

The map must contain only dependencies that the consumer actually uses. Determine the dependency
set with the existing `read_deps` helper. It must not mutate `pyproject.toml`, `uv.lock`, or any
package source declaration.

The map needs a small generated-file header or equivalent metadata sufficient for doctor to
identify it as Vendomat output. Add `.vendomat/` to this repository's relevant ignore guidance if
needed, but do not broadly ignore a consumer's unrelated configuration without justification.

## Command behavior

### `vendor sync`

1. Read the consumer dependency set with `read_deps`.
2. Intersect it with catalog entries.
3. For `project` entries:
   - resolve the declared path relative to the consumer root;
   - verify it exists and is a Git checkout;
   - inspect its current full `HEAD` revision;
   - report a mismatch from the catalog revision clearly (whether mismatch is fatal in sync is a
     deliberate documented decision; it must be fatal in doctor).
4. For `vendor` entries:
   - create the cache parent if needed;
   - clone the declared repository only when missing;
   - fetch the declared immutable revision and check out a detached `HEAD` at that revision;
   - refuse to overwrite a dirty clone;
   - never use branch names as identity.
5. Write `.vendomat/sources.toml` atomically and deterministically.
6. Be idempotent: a second sync with unchanged inputs makes no source-state changes and produces
   byte-stable map output.

`--dry-run` must perform no clone, fetch, checkout, or file write. It should report planned
actions and problems.

### `vendor status`

Read-only, concise output showing every catalog entry relevant to the consumer:

- dependency name and kind;
- expected catalog revision;
- discovered local path;
- current revision / missing state / dirty state;
- resolved installed version from `uv.lock`, if available.

### `vendor doctor`

Read-only and compatible with Vendomat's existing 0/1/2/3 CLI contract. It should diagnose at
least:

- missing or malformed catalog entry;
- missing owned-project checkout;
- missing third-party clone;
- wrong revision;
- dirty third-party clone;
- missing/stale `.vendomat/sources.toml`;
- a dependency found in the consumer but not present in the catalog (warn-only in this first
  slice, because the catalog is intentionally incremental).

Do not merge this behavior into the existing knowledge `doctor` in a way that makes its output
ambiguous. Reuse its normalized check model if appropriate.

## Architecture guidance

- Add a dedicated module such as `src/vendomat/catalog.py` for TOML parsing + Pydantic models,
  and `src/vendomat/sources.py` for Git/source-map operations. Keep filesystem and subprocess
  boundaries explicit and injectable where practical.
- Use `subprocess.run([...], check=False, capture_output=True, text=True)` rather than shell
  strings for Git operations. Surface stderr in domain errors.
- Validate all catalog-relative paths: no absolute path and no `..` traversal for Vendomat-owned
  cache locations. The owned-project path is intentionally consumer-relative and may use `..`.
- Keep Git operations narrowly scoped. Never reset, clean, or modify a personal project checkout.
- Avoid network in ordinary unit tests. Mock or inject the Git boundary. Add a local bare-repository
  integration test only if it exercises clone/revision behavior without external network.
- Keep the existing `vendomat publish` code separate; do not make `vendor sync` invoke `uv lock`.

## Tests and verification

Start by adding focused tests before implementation where practical. Cover at least:

- catalog TOML validation and normalized names;
- relevant-dependency filtering;
- generated source-map content and idempotency;
- missing/mismatched/dirty project checkout diagnostics;
- managed third-party clone behavior against a temporary local bare Git remote;
- refusal to replace a dirty third-party clone;
- `--dry-run` makes no clone or map write;
- CLI exit codes and concise output.

Use the project-prescribed verification command:

```sh
devenv shell -- testee verify
```

The Nix daemon may require escalated permission. Preserve unrelated worktree changes. Do not edit
the existing historical scratch projects or sibling repositories.

## Acceptance criteria

This slice is complete only when:

1. The catalog entries exist and validate.
2. A temporary consumer depending on KnapPy/Pydantic gets a deterministic `.vendomat/sources.toml`.
3. KnapPy resolves to its canonical project checkout, never a duplicate Vendomat clone.
4. Pydantic resolves to a detached, pinned Vendomat-managed clone.
5. No consumer packaging file or lockfile changes during source sync.
6. Status/doctor report useful, actionable source state.
7. All project verification passes.

## Out of scope

- Bulk discovery of repository URLs from PyPI metadata.
- Installing dependencies from local paths, editable installs, or rewriting consumer uv sources.
- Loci-Core migration itself.
- Git submodules/LFS, monorepo subdirectory support, and catalog authoring automation beyond what
  is needed for a well-validated first slice.
- Any dependency version upgrade or lock regeneration as part of source synchronization.

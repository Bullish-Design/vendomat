# Vendomat M4 kickoff prompt

```text
Work in `/home/andrew/Documents/Projects/vendomat`.

Your task is to finish and land Milestone M4 from `docs/IMPLEMENTATION_PLAN.md`: shared `vendor/constraints.txt` plus review-on-bump warnings in `vendomat doctor`.

Start by reading these files in full:

- `docs/IMPLEMENTATION_PLAN.md`, especially M4, the sequencing section, and cross-cutting risks
- `docs/DESIGN.md`, especially §7.3 and the doctor/manifest design
- `src/vendomat/install.py`
- `src/vendomat/deps.py`
- `src/vendomat/checks.py`
- `src/vendomat/cli.py`
- `tests/test_install.py`
- `tests/test_deps.py`
- `tests/test_checks.py`
- `vendor/libs/typer/meta.toml`
- `vendor/constraints.txt`
- `modules/devenv.nix`

Repository state and scope

Committed milestones are:

- M0: Python/Typer package bootstrap
- M1a: Nix artifact-builder dispatcher
- M2: usage-gated dependency knowledge skills
- M3: `vendomat add <lib>` scaffolding

M4 implementation has already been started in the working tree but is not committed. The expected M4-related modifications are in:

- `src/vendomat/install.py`
- `src/vendomat/deps.py`
- `src/vendomat/checks.py`
- `src/vendomat/cli.py`
- `tests/test_install.py`
- `tests/test_deps.py`
- `tests/test_checks.py`
- `vendor/libs/typer/meta.toml`
- new `vendor/constraints.txt`

There are also unrelated/unconfirmed worktree changes:

- `flake.nix`
- `flake.lock`
- `.scratch/projects/02-vendor-workspace/`
- `REPOMAN_M1B_SESSION_PROMPT.md`

Preserve these unrelated changes. Do not reset, discard, stage, or include them in an M4 commit unless inspection proves they are directly required for M4.

Required M4 behavior

1. `vendor/constraints.txt` is the shared authoritative source for exact external dependency pins.

   - It currently contains `typer==0.12.5`.
   - When an exact normalized `<lib>==<version>` entry exists there, it must take precedence over that library’s `[lib].pin` metadata when writing `.vendor-source`.
   - Metadata remains the fallback during the M2-to-M4 transition.
   - Ignore comments and malformed/non-exact constraint lines safely.

2. `vendomat sync` must record the exact pin each installed `dep-<lib>` skill was written against in `.vendor-source`.

   - Preserve existing install behavior: usage-gated skills, flat `dep-<lib>` directories, idempotent manifest generation.
   - The pin checked later must be the one recorded at installation time, not whichever pin happens to be in the vendor tree later.

3. Add resolved-version reading from `uv.lock`.

   - Read package `name` and exact `version` from `[[package]]` entries.
   - Normalize package names consistently with the existing dependency reader.
   - If no `uv.lock` exists, return no resolved versions; this is “cannot judge,” not an error.

4. Extend `vendomat doctor` with warn-only review-on-bump checking.

   - Compare the manifest-recorded pin for every installed skill to the consumer repo’s resolved version from `uv.lock`.
   - If they differ, emit a `vendor:pins` warning that identifies the affected skill and version transition, e.g. `dep-typer (0.12.5→0.13.0)`.
   - If pins match, report success.
   - If a skill is unpinned or its resolved version is unknown, do not warn.
   - Preserve the shared `0/1/2/3` exit-code contract: this is advisory and must not make doctor exit nonzero.

5. Ensure the M4 tests cover:

   - resolved-version parsing and normalization;
   - constraints pin overriding per-library metadata;
   - fallback to metadata when no applicable exact constraint exists;
   - manifest pin round-trip parsing;
   - matching pin = OK;
   - bumped resolved version = `vendor:pins` warning;
   - absent `uv.lock` / unknown version = no false warning.

Review quality before changing anything

- Treat the existing unstaged M4 code as a draft, not automatically correct.
- Check for regressions in existing M2/M3 behavior and naming/manifest conventions.
- Keep functions pure and path-explicit where the current code does so.
- Do not broaden scope into selective vendored `src/`, registries, more artifact builders, or repoman changes.
- M1b remains a separate cross-repo repoman task; a draft handoff exists in `REPOMAN_M1B_SESSION_PROMPT.md`. Do not implement it here.

Verification

Use the project’s intended verification path first:

```sh
devenv shell -- testee verify
```

If Nix/devenv cannot run in this environment, report the precise failure and run the strongest safe fallback available, including:

```sh
python -m compileall -q src tests
git diff --check
```

and the focused unit tests through the available project Python environment. Do not claim tests passed if they did not run.

Finish criteria

- M4 is correct, well-tested, and limited to its intended files.
- Unrelated worktree changes are untouched.
- If verification is adequate, create a focused commit for M4 only, following the repository’s existing commit style.
- End with a concise summary of behavior, changed files, commit hash (if created), tests run, and any verification limitation.
```

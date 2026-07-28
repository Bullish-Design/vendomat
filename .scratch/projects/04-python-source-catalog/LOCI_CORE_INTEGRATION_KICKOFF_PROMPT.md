# Loci-Core Source Catalog Integration — Clean Session Kickoff Prompt

You are continuing Project 04 in the Vendomat repository. The first source-catalog vertical slice is implemented and verified. Your job in this phase is to integrate **Loci-Core as the first real consumer**, covering its three relevant Python dependencies—KnapPy, Pydantic, and `ruamel.yaml`—without weakening reproducibility or confusing source review with package installation.

The user explicitly grants full permission to modify Loci-Core as needed for this phase. This authorization includes its dependency metadata, lockfile policy, devenv configuration, generated source map, tests, and documentation. It does **not** implicitly authorize commits, pushes, destructive cleanup, or changes to KnapPy; ask before committing or pushing anything.

## Working directories

- Vendomat: `/home/andrew/Documents/Projects/vendomat`
- Loci-Core: `/home/andrew/Documents/Projects/loci-core`
- Owned KnapPy checkout: `/home/andrew/Documents/Projects/knappy`
- Global third-party source cache: `/home/andrew/vendor`

The active writable workspace may initially be Vendomat only. If modifying Loci-Core requires a sandbox escalation, request it directly; the user has already approved the repository changes conceptually.

## Read these first, in order

From Vendomat:

1. `.scratch/projects/04-python-source-catalog/CONCEPT_REFINEMENT.md`
2. `.scratch/projects/04-python-source-catalog/KICKOFF_PROMPT.md`
3. `.scratch/projects/04-python-source-catalog/RESEARCH_REPORT.md`
4. `docs/SOURCE_CATALOG.md`
5. `src/vendomat/catalog.py`
6. `src/vendomat/sources.py`
7. The `vendor` CLI commands in `src/vendomat/cli.py`
8. `modules/devenv.nix`
9. `vendor/python/knappy.toml`
10. `vendor/python/pydantic.toml`

From Loci-Core:

1. `README.md`
2. `pyproject.toml`
3. `devenv.yaml`
4. `devenv.nix`
5. `.gitignore`
6. Any repository-local guidance you discover

Before editing, inspect `git status --short`, the current branch, and HEAD in all three repositories. Do not rely blindly on the state snapshot below if the working trees have changed.

## Mission

Produce a proven Loci-Core consumer integration where:

- Vendomat resolves the exact reviewed sources for KnapPy, Pydantic, and `ruamel.yaml`.
- Loci-Core receives a deterministic generated `.vendomat/sources.toml` map.
- Third-party sources live under `~/vendor`; KnapPy continues to resolve to the owned sibling checkout for source review.
- Neither `pyproject.toml` nor `uv.lock` installs packages from `~/vendor` or another local source-review checkout.
- Loci-Core has a deliberate, reproducible public install form for KnapPy instead of the currently committed editable sibling path.
- Loci-Core’s complete existing verification suite passes after the integration.
- Repeated Vendomat syncs are idempotent and do not rewrite unchanged generated files.

Treat the source catalog and Python package resolver as separate systems:

```text
Vendomat source catalog -> reviewed local source locations for humans/agents
uv / pyproject / uv.lock -> canonical reproducible package installation inputs
```

Never collapse those two roles into one mechanism.

## Evidence snapshot from 2026-07-21

Re-check every item before acting, but this is the known starting state.

### Vendomat

- Project 04 currently supports:
  - validated TOML catalog entries;
  - immutable Git synchronization;
  - generated `.vendomat/sources.toml` consumer maps;
  - `vendomat vendor sync`, `status`, and `doctor`;
  - `~/vendor` as the default third-party source root;
  - owned-project resolution through declared relative paths.
- Catalog entries already exist for:
  - KnapPy at commit `9fe266e30bd02cb4f453d5a9586c3c412e0b453f`, path `../knappy`;
  - Pydantic at commit `cf67d4b3193c3fe43ede18612ed62785eee11382`, cache name `pydantic`.
- The Pydantic source is already synchronized at `/home/andrew/vendor/pydantic`.
- The latest Vendomat verification passed with report:
  - `.testee/runs/2026-07-21T19-24-15Z-e4f3ca/testee-report.json`
- The repository is intentionally dirty with Project 04 plus unrelated earlier work. Preserve all existing edits and untracked files. Do not broadly reformat, reset, clean, or discard anything.

### Loci-Core

- Branch: `main`
- HEAD: `57c83f41192092a9ca4b132046e9eadf77dfeeb2`
- Origin: `git@github.com:Bullish-Design/loci-core.git`
- Known pre-existing dirty change: `.gitignore` appends:

  ```gitignore
  # Nix build output
  /result
  /result-*
  ```

  Preserve that user change exactly while making any additional `.gitignore` edits.
- There is no `uv.lock`, `vendomat.toml`, or `.vendomat/sources.toml` yet.
- `.gitignore` currently ignores `uv.lock`. Revisit that deliberately if the chosen reproducibility policy is to commit a lockfile; do not accidentally erase the existing `/result` rules.
- Relevant `pyproject.toml` dependencies are:

  ```toml
  pydantic>=2.12.5
  ruamel.yaml==0.18.6
  knappy
  ```

- KnapPy currently has this local development override:

  ```toml
  [tool.uv.sources]
  knappy = { path = "../knappy", editable = true }
  ```

  That is not an acceptable final public install form for this phase.
- `ruamel.yaml==0.18.6` is intentional: Loci-Core comments state that serializer output is byte-locked and exact pinning supports reproducibility.
- Loci-Core directly imports both Pydantic and `ruamel.yaml`; KnapPy also depends on both.
- Existing verification is exposed through devenv tasks, especially:

  ```sh
  devenv tasks run loci:build
  devenv tasks run loci:lint
  devenv tasks run loci:typecheck
  devenv tasks run loci:test
  devenv tasks run loci:verify
  ```

- `devenv.yaml` does not yet import Vendomat, and `devenv.nix` does not yet enable Vendomat knowledge integration.
- `lsp/` is a separate uv project and is out of scope unless a failure proves a narrowly necessary change.

### KnapPy

- HEAD: `9fe266e30bd02cb4f453d5a9586c3c412e0b453f`, matching the catalog.
- Known pre-existing dirty change: `.gitignore` only.
- Do not edit, reset, clean, commit, or otherwise mutate this repository during this phase.

## Fixed architectural decisions

These are constraints, not open design questions:

1. The global third-party source location is `~/vendor`, producing paths such as `~/vendor/pydantic` and, if a valid catalog entry is established, `~/vendor/ruamel-yaml`.
2. Vendomat’s catalog policy remains in Vendomat under `vendor/python/*.toml`; generated consumer state belongs in each consumer’s `.vendomat/sources.toml`.
3. Owned KnapPy source review resolves to the canonical sibling checkout `../knappy`; it is not copied into `~/vendor`.
4. Local catalog clones/checkouts are read-only reference material. Never write their paths into Loci-Core’s `[project].dependencies`, `[tool.uv.sources]`, `uv.lock`, editable installs, or runtime import configuration.
5. A source revision and an installed package version are distinct identities. Report and verify them separately.
6. Catalog revisions must be immutable full commits. Do not use branches, floating tags, or guessed revisions.
7. Do not invent a `ruamel.yaml` GitHub mirror. Establish its canonical upstream source from primary evidence. If there is no suitable canonical Git repository for the reviewed version, report that clearly and stop that subtask rather than creating a misleading entry.
8. Preserve all existing dirty work in every repository. Never use destructive Git commands.
9. Do not commit or push unless the user explicitly asks in the new session.

## Critical Vendomat input issue

The Project 04 implementation and catalog files are currently uncommitted/untracked in Vendomat. A `git+file:///home/andrew/Documents/Projects/vendomat` flake input reads Git state and may omit untracked Project 04 files. Therefore:

- Do not add a `git+file` input to Loci-Core and assume it exposes the current implementation.
- First verify exactly what the proposed flake/devenv input sees.
- Prefer the smallest safe local-development input that exposes the current Vendomat working tree without copying enormous ignored state.
- If a clean Vendomat checkpoint commit is the only sound solution, stop and request explicit commit authorization; full permission to modify Loci-Core is not permission to commit Vendomat.
- You may run Vendomat from its own verified devenv environment against `--repo-root /home/andrew/Documents/Projects/loci-core` while resolving the module-input question. Do not let that temporary execution route become an undocumented final architecture.

## Required execution plan

Maintain a short working plan and keep an evidence log under:

`/home/andrew/Documents/Projects/vendomat/.scratch/projects/04-python-source-catalog/`

Append a dated section to `RESEARCH_REPORT.md` for this phase, and place raw command logs in a new dated artifacts subdirectory. Preserve failures as evidence instead of overwriting logs.

### Phase 0 — Baseline and safety checks

1. Record branch, HEAD, remotes, and `git status --short` for Vendomat, Loci-Core, and KnapPy.
2. Record hashes of Loci-Core’s `pyproject.toml`, `.gitignore`, and any existing lockfile.
3. Confirm the exact Vendomat and KnapPy commits and catalog state.
4. Run Loci-Core’s current verification before changing dependency metadata. Use its documented devenv interface. If baseline verification fails, classify whether the failure is pre-existing and preserve the full log.
5. Confirm the installed/resolved dependency state in the baseline environment where possible, but do not treat environment state as catalog truth.

### Phase 1 — Establish the `ruamel.yaml` source entry

1. Verify from Loci-Core code and metadata that `ruamel.yaml` remains in use and that `0.18.6` is still the intended installed version.
2. Research the canonical upstream repository using primary sources. Network access may require approval.
3. Determine the immutable source commit corresponding to the reviewed code for `0.18.6`, if one can be established honestly.
4. Record separately:
   - distribution name: `ruamel.yaml`;
   - installed version: `0.18.6`;
   - canonical repository URL;
   - immutable reviewed source revision;
   - local cache name/path.
5. If a trustworthy canonical Git mapping exists, add a validated catalog entry under Vendomat’s `vendor/python/`, using a filesystem-safe cache name such as `ruamel-yaml`.
6. Run catalog/unit verification before network sync.
7. Dry-run and then synchronize the source into `~/vendor/ruamel-yaml`.
8. If no trustworthy canonical Git mapping exists, document the limitation and continue only with the parts of Loci-Core integration that remain truthful. Do not substitute a random mirror.

### Phase 2 — Wire Loci-Core to Vendomat safely

1. Resolve the flake/devenv input issue described above with evidence.
2. Add the minimum appropriate Vendomat input/import and `knowledge.enable = true` configuration if the current module interface supports it cleanly.
3. Do not enable or create publisher configuration merely because that feature exists. `vendomat.toml` is optional and belongs only to the separate install-source publishing workflow.
4. Add `.vendomat/` to Loci-Core’s `.gitignore` if generated consumer state is meant to remain local. Preserve the existing `/result` additions.
5. From a verified Vendomat environment, first run the equivalent of:

   ```sh
   vendomat vendor sync --dry-run \
     --repo-root /home/andrew/Documents/Projects/loci-core
   ```

   Supply explicit catalog/source-root flags only when necessary to remove ambiguity; the intended third-party default is `~/vendor`.
6. Perform the real sync and inspect `.vendomat/sources.toml` manually.
7. The generated map should include only relevant cataloged dependencies discovered from Loci-Core metadata. Expected entries are KnapPy, Pydantic, and `ruamel.yaml` if Phase 1 established it.
8. Confirm:
   - KnapPy maps to `/home/andrew/Documents/Projects/knappy`;
   - Pydantic maps to `/home/andrew/vendor/pydantic`;
   - `ruamel.yaml`, if cataloged, maps to `/home/andrew/vendor/ruamel-yaml`;
   - every entry records its catalog revision;
   - no generated path leaks into package installation metadata.
9. Run sync a second time and prove that unchanged output is not rewritten. Compare file bytes and modification time or another robust signal.

### Phase 3 — Make Loci-Core installation reproducible

The current editable KnapPy sibling override is the main policy issue. Resolve it deliberately.

1. Research whether the required KnapPy release is available from its intended public package index. Do not infer publication merely from its local version number.
2. Choose the canonical committed install form:
   - If an appropriate KnapPy release is published, use a normal versioned dependency and remove the local path source.
   - If it is not published, use an immutable upstream Git source pinned to a full commit in `[tool.uv.sources]`; do not use a branch, editable path, source-cache path, or moving tag.
3. Keep Pydantic and `ruamel.yaml` as normal registry dependencies unless strong evidence requires another public distribution source.
4. Decide and document lockfile policy. For a reproducible application/library development environment, the expected outcome is a generated, tracked `uv.lock`; if so, remove only the `uv.lock` ignore rule and preserve all unrelated `.gitignore` content.
5. Generate/update the lockfile through the repository’s documented devenv/uv workflow.
6. Inspect the resulting lockfile and prove:
   - KnapPy uses the chosen public release or immutable Git commit;
   - Pydantic and `ruamel.yaml` resolve as distributions, not local catalog paths;
   - no `/home/andrew/vendor`, `../knappy`, or other machine-local checkout path is recorded;
   - the pinned `ruamel.yaml` distribution version remains `0.18.6` unless a separately justified compatibility change was necessary.
7. If local editable development is still desired, keep it as a clearly opt-in developer action using Vendomat’s existing publisher mechanism only after proving the canonical committed form. Do not make an editable override the default, and do not conflate publishing with source sync.

### Phase 4 — Source-grounded agent ergonomics

Inspect the current Vendomat knowledge/skill integration before modifying it. Do not assume that catalog entries automatically create dependency skills.

The minimum acceptable outcome is that an agent working in Loci-Core can discover the generated map and understand that the mapped sources are revision-pinned reference material. If existing skills cover this cleanly, install/configure them. If a small generic source-catalog skill or documentation hook is required, implement it in Vendomat with focused tests and reuse the generated `.vendomat/sources.toml`; do not create three large duplicated dependency-specific instruction sets.

Any skill or documentation must state:

- where the dependency source is located;
- which catalog revision is reviewed;
- that installed package versions are checked separately;
- that source cache paths must not be used as install sources.

Keep this work minimal. Do not turn the phase into a full ecosystem-wide skill/catalog expansion.

### Phase 5 — Verification and evidence

Run all relevant checks after the final edits.

Vendomat:

```sh
devenv shell -- testee verify
```

Loci-Core:

```sh
devenv tasks run loci:build
devenv tasks run loci:lint
devenv tasks run loci:typecheck
devenv tasks run loci:test
devenv tasks run loci:verify
```

Vendomat consumer checks, using explicit paths where useful:

```sh
vendomat vendor sync --dry-run --repo-root /home/andrew/Documents/Projects/loci-core
vendomat vendor sync --repo-root /home/andrew/Documents/Projects/loci-core
vendomat vendor status --repo-root /home/andrew/Documents/Projects/loci-core
vendomat vendor doctor --repo-root /home/andrew/Documents/Projects/loci-core
```

Also verify:

1. repeated sync is idempotent;
2. Pydantic and `ruamel.yaml` caches, if present, are clean detached checkouts at catalog revisions;
3. KnapPy remains untouched at its pre-phase HEAD and retains its pre-existing worktree change only;
4. Loci-Core’s new diff contains only intentional integration changes plus its preserved pre-existing `.gitignore` edit;
5. no machine-local source-review paths appear in `pyproject.toml` or `uv.lock`;
6. Loci-Core can build/test from its canonical committed dependency form, without relying on the sibling editable KnapPy checkout;
7. any Vendomat bugs found during real-consumer integration receive focused regression tests before or with the fix.

Use fresh logs for the final run. Do not claim success from a pre-edit verification report.

## Acceptance checklist

The phase is complete only when all applicable items are true:

- [ ] Baseline state and pre-existing dirty files were recorded and preserved.
- [ ] Loci-Core’s three relevant dependencies were detected accurately.
- [ ] KnapPy and Pydantic catalog entries validate at immutable full revisions.
- [ ] `ruamel.yaml` has a truthful canonical source mapping, or the inability to establish one is explicitly documented without a guessed mirror.
- [ ] Third-party sources resolve under `~/vendor`; KnapPy resolves to the owned sibling checkout.
- [ ] `.vendomat/sources.toml` is generated deterministically for Loci-Core.
- [ ] A second source sync leaves unchanged output untouched.
- [ ] Loci-Core no longer has a canonical committed editable `../knappy` install override.
- [ ] The selected KnapPy install source is public and reproducible: a released distribution or immutable upstream Git commit.
- [ ] `pyproject.toml` and `uv.lock` contain no source-cache or machine-local checkout paths.
- [ ] The `ruamel.yaml==0.18.6` distribution pin remains deliberate and is distinguished from the reviewed source revision.
- [ ] Vendomat status and doctor succeed, allowing only explicitly documented warn-only findings.
- [ ] Vendomat’s complete verification suite passes after any changes.
- [ ] Loci-Core’s complete `loci:verify` suite passes after all changes.
- [ ] KnapPy was not modified.
- [ ] Research report and raw evidence logs were updated.

## Out of scope

- Editing KnapPy.
- Integrating Loci-Core’s separate `lsp/` uv project.
- Bulk-cataloging every transitive dependency.
- Treating wheels/sdists and source repository snapshots as the same artifact identity.
- Installing packages from `~/vendor`.
- Making local editable paths the committed default.
- Broad redesigns of Vendomat’s publisher or knowledge systems.
- Commits, pushes, releases, or pull requests without a new explicit request.

## Working style and final handoff

- Lead with evidence and make the smallest coherent changes.
- Use dry-runs before mutations when available.
- Preserve and classify failures.
- Do not silently work around a reproducibility problem.
- If a decision materially changes public dependency policy, state the evidence and tradeoff before implementing it; then proceed with the safest evidence-backed option unless user input is genuinely required.
- At the end, report:
  - files changed in each repository;
  - catalog source URLs and exact revisions;
  - installed package versions and install origins;
  - generated map locations;
  - exact verification commands and outcomes;
  - remaining warnings or blockers;
  - confirmation that KnapPy and all pre-existing dirty work were preserved.

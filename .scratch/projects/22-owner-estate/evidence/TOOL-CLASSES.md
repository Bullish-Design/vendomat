# Tool classes: project dependency or personal layer — 2026-10-13

<!-- Provenance: written by a read-only research subagent on 2026-10-13. Sources: testee, repoman, devman, linkman, mancore, loci-core, flora, eventic and others under ~/Documents/Projects. The subagent changed no file except this one. Statements marked "Inference" are not measured. -->

## The test

Ask one question about each tool: would someone who clones this repository still need it? If yes, the tool is a project dependency. The repository may pin it like any dependency. If no, the tool belongs to the owner's personal layer. The owner's Home Manager delivers it. No repository pins it.

## Classification

| Tool | Class | Evidence | Consequence for repos |
|---|---|---|---|
| testee, module part (`testee.checks`, `testee.prepare`, `testee.keep`) | Split: project data | `testee/nix/testee.nix` is a pure options module. It emits a manifest and puts nothing on PATH. Consumer `devenv.nix` files hold plain argv lists such as `uv run --no-sync ruff check .`. | The check commands are project facts. The Testee pin is not needed to run them. |
| testee, runner (`testee verify`, `status`, `show`, `doctor`, `gc`) | Personal layer | `testee/README.md`: "Install one testee per machine." `testee/CHANGELOG.md` 0.6.0: the module "no longer ships a runner". Consumer comments: "the host profile puts testee on PATH". | Remove the `testee:` input, the `testee/nix/testee.nix` import and the lock node, after the manifest moves (see Recommendation). |
| repoman | Personal layer | `repoman/modules/devenv.nix` and `modules/managers/*.nix`. `linkman/devenv.yaml` comment: remove the input if the central overlay imports it. `repoman/devenv.local.nix` links to `~/.config/devman/projects/repoman/`. | Remove the `repoman:` input, the import and `repoman.enable = true;`. The central overlay imports the module. |
| copyroom | Personal layer, one exception | Host tool. `loci-core/pyproject.toml` lists it as a dev dependency. A cloner needs it only to update from a template. | Do not pin it in `devenv.yaml`. `loci-core` may keep its dev dependency. |
| gitman | Personal layer | `loci-core/pyproject.toml`: "gitman is NOT here. It is a host tool on PATH from the user profile." | Nothing is pinned. |
| devman | Personal layer | `devman/README.md`: one Dagu control plane per machine. `devman/groups/base/README.md`: the repo supplies only task bodies. | The repo keeps `.devman/project.toml` and its `base:*` task bodies. |
| linkman | Personal layer | `linkman/README.md`: a symlink manager for development repositories. The central overlay (`devman.link`) does the same work. Inference: a cloner needs no symlinks. | No repo pins it. |
| mancore | Project dependency | `linkman/pyproject.toml` and `loci-core/pyproject.toml` list `mancore` and pin it in `[tool.uv.sources]` at tag v0.1.0. Both import it. | The pin is legitimate. Keep it. |
| docman | Neither | `docman/README.md`: archived. Repoman 0.13.0 removed the `doc` manager. No repo uses it. | Ignore it. |

## Testee

**Module and runner are separate.** The module is a Nix options file. It turns `testee.checks`, `testee.prepare` and `testee.keep` into a manifest. The runner is a separate program on the host PATH. It does not come from the repo's `devenv.lock`.

**Tags.** The tags are v0.6.0, v0.6.1, v0.6.2 and v0.7.0 (2026-10-10 to 2026-10-12). All 22 repos with a `testee` input in `devenv.yaml` pin v0.6.1. The 0.7.0 release does not change the module options. It removes deprecated commands and `testee.package`. The migration note says a repo that locks the 0.6.x module works with a 0.7.0 host runner. The testee README and AGENTS still say 0.6.0.

**What `testee verify` does.**
1. It checks out the commit into a detached worktree that testee owns.
2. It runs `devenv shell --clean`.
3. It runs `testee.prepare`, then each check argv.
4. It stores one verdict per check, keyed by tree, check ID, gate epoch, system and devenv version.

Exit 0 is green. Exit 1 is red. Exit 2 is no verdict. The checks are plain commands. Testee orchestrates them and caches the verdict.

**Machine-coupled prepare hooks.**
- `loci-core` symlinks `.agents` and `.loci` from the main checkout. It fails if they are missing.
- `flora` requires sibling checkouts `flora-core`, `poddantic` and `flora-qc`.
- A cloner cannot run these hooks. They are owner-layer content.

**Consumer tasks.** Five repos were sampled: linkman, mancore, loci-core, flora, eventic. Four define `base:check` and `base:test` as `testee verify ...`. `loci-core` uses `after` on native tasks. Its checks run `uv run --extra dev --no-sync ruff ...`.

**No CI calls testee.** A search of `.github/workflows` in all projects finds no match for "testee". The eventic `ci.yml` runs `uv sync`, `uv build` and `uv run ruff check .` directly. The testee README describes a CI recipe, but no repo uses it.

**What a cloner runs today.** A cloner must run `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check .` and `uv run pytest`. These commands exist in `pyproject.toml` and the `dev` group. The cloner cannot run `base:check` or `base:test` as written, because they call `testee`.

## Repoman

**What the module adds to a shell.**
- Env vars `REPOMAN_MANAGERS` and `REPOMAN_SKILLS_DIR`.
- The script `repoman-sync`, which writes the router skill under `.agents/skills`.
- An `enterShell` banner and a PATH line for the venv.
- Packages `git` and `gnupatch`, and the task `repoman:template:status` (runs `copyroom status`).

**The roster.** The roster is `.repoman/project.toml`. The default is `copy git test`.

**No project build or test depends on it.** A search of the other projects' code and workflows for `REPOMAN_` and `repoman-sync` found no match outside repoman. Repoman is agent and owner ergonomics. Repoman is already moving to the personal layer. Repoman is pinned at v0.14.0 or v0.14.1 in 19 `devenv.yaml` files. Inference: the grep covered `.py`, `.toml` and `.yml` only. Nix and shell files were not searched by that command.

**Both import sites must change together.** A repo that drops the import must also drop `repoman.enable = true;`. If the central overlay and the repo both import the module, devenv fails with "option repoman.enable is already declared".

## Base group contract

- `devman/groups/base/workflows/check.yaml` runs one step: `devenv tasks run -v base:check`. `test.yaml` runs `devenv tasks run -v base:test`.
- The repo owns the task bodies. The group README gives `tasks."base:check".exec = "ruff check ."` and `tasks."base:test".exec = "pytest"` as examples.
- Devman fixes only the names and the budgets: check at most 5 s warm, test at most 5 min.
- The group does not mention testee.
- 49 repos define `base:check`. 16 contain `testee verify` in `devenv.nix`.

## Recommendation for Testee

Make testee an owner tool that runs the `base:*` tasks. The repo-side contract has two parts.

1. `base:check` and `base:test` run plain commands directly. Example: `uv run --no-sync ruff check . && uv run ty check .` and `uv run --no-sync pytest`. A cloner runs `devenv tasks run base:test` with no testee installed.
2. The owner's testee manifest (`testee.checks`, `testee.prepare`, `testee.keep`) moves to the central overlay at `~/.config/devman/projects/<name>/devenv.local.nix`. The owner's host `testee` runs the checks from there.

**Why the cheaper variant fails.** The cheaper variant keeps the manifest in the repo's `devenv.nix` and drops only the pin. The `testee.*` options come from `testee/nix/testee.nix`. Without the input, `devenv.nix` sets an option that does not exist. A cloner's evaluation then fails with an undefined-option error.

**Mitigation for duplicated commands.** Let the overlay checks call `devenv tasks run base:check` and `devenv tasks run base:test`. One definition then exists, in the repo's tasks.

## Risks

1. **Drift.** If the overlay repeats the argv lists, two copies exist and drift apart. The devman AGENTS file calls this a smell. The mitigation above removes it.
2. **Lost granularity.** Testee keeps one verdict per check ID. A check that calls `base:test` gives one verdict. Partial reruns are lost. Inference.
3. **Machine-coupled hooks.** The `loci-core` and `flora` prepare hooks must stay in the overlay.
4. **Lock churn.** Removing the input changes `devenv.lock` in every repo. Testee refuses with `lock_stale` if an eval changes a lock file. Plan one lock commit per repo.
5. **Overlay reach.** Inference: the overlay can set `testee.*` options only if the overlay imports `testee/nix/testee.nix` itself.
6. **Gate is owner-side.** A cloner loses the verdict gate. This is the intended outcome of the rule.

## Unproved

- No one evaluated `testee.manifestJson` from an overlay-only module. The recommendation assumes it works.
- No one tested that `testee verify` finds a manifest that the overlay supplies.
- No one tested that an overlay check can call `devenv tasks run base:*` inside the clean shell and keep one verdict.
- The search for repoman use outside repoman covered `.py`, `.toml` and `.yml` files only.

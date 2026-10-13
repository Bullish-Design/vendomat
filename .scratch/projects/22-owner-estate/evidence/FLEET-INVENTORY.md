# Fleet inventory: personal-tool pins and copies in project repos — 2026-10-13

<!-- Provenance: a subagent scan on 2026-10-13. Raw data, scripts, and commands are in
~/.local/state/vendomat/p22/inventory/ (repos.tsv, overlay.tsv, templates.md, summary.txt,
INVENTORY.md). Rerun: `python3 -I collect.py <dir>`, then `python3 -I summarize.py <dir>`. The
base-task classes and the lock family-node column are heuristic. The orchestrator wrote this record
from summary.txt and the subagent's report, with the owner's permission. A later re-check
(FAMILY-DELIVERY) found that 2026-10-13 commits removed devman or RepoMan from loci.nvim,
nix-secrets, nix-desktop, nix-nvim, and nix-paseo, and that mnemonix has uncommitted edits that
remove its devman input. -->

## Scope

70 version-controlled repositories directly under `~/Documents/Projects`. Skipped: `.devenv`,
`.worktrees`, `.gitman`, `gitman-workspaces`, `.archive`, and the archived set (allium-env,
forgelab, lodestar, fleetman, my-ai; only forgelab exists). No repository or overlay file changed.

## Counts

| Change type | Count | Repositories |
| --- | --- | --- |
| `devenv.yaml` input and import `repoman` | 18 | agentman, argentic, devenv-py, eventic, flora, flora-core, flora-qc, inferference, linkman, llgym, mancore, mnemonix, poddantic, pyllij, repoman, scopeman, shellij, talkee |
| — of which by local `path:` | 2 | mnemonix, repoman |
| — refs | | v0.14.0 for most; eventic v0.12.1; mancore v0.14.1 |
| `devenv.yaml` input and import `testee` (all v0.6.1) | 22 | agentman, argentic, devenv-py, eventic, flora, flora-core, flora-qc, fornix, inferference, linkman, llgym, loci-core, mancore, poddantic, pyllij, pytuin, repoman, scopeman, shellij, talkee, templateer_v2, vendomat |
| `devenv.yaml` input `devman` | 1 | mnemonix |
| `devenv.yaml` input `mancore` (a real dependency) | 1 | devman |
| `devenv.yaml` input `vendomat` with nested family pins | 1 | mancore |
| `vendomat.toml` pins family tools | 2 | nix-systems, vendomat-demo |
| `devenv.nix` `repoman.` options (1 line each; repoman 3) | 18 | the 18 `repoman` repositories |
| `devenv.nix` `testee.` block (734 lines in total) | 23 | the 22 `testee` repositories plus testee itself; largest: vendomat 100, devenv-py 64, argentic 57 |
| `devenv.nix` `devman = {` block | 1 | mnemonix (5 lines) |
| `base:check` and `base:test` defined | 48 | see summary.txt |
| — `base:check` calls `testee verify` | 11 | agentman, argentic, devenv-py, eventic, flora, flora-core, inferference, linkman, llgym, mancore, pyllij |
| — `base:test` calls `testee verify` | 13 | the 11 plus repoman, scopeman |
| — base tasks chain to project tasks only | 25 to 27 | see summary.txt |
| — base tasks run other commands | 10 | devman, interplay, loci.nvim, nix-desktop, nix-nvim, nix-paseo, nix-secrets, nixbuild, nixvim, siteman |
| No base tasks | 11 | PyGentic, clinch, copyroom, devman-spike, docman, fsdantic, mnemonix, nix-systems, nvim-review, testee, vendomat-demo |
| `devenv.lock` gitignored | 11 | atuout, browsee, copyroom, devman, docman, fsdantic, grail, knappy, nixbuild, tyo3, zelligate |
| `devenv.local.yaml` present (none tracked) | 9 | active keys: browsee, templateer_v2, tyo3, zelligate (secretspec), pydantree (devman path override); comments or empty: agentman, linkman, repoman, scopeman |
| `gitman.toml` (all tracked) | 62 | 47 default `trunk = "main"`; 15 custom: atuout, devman, loci.nvim, nix-meta-channel4, nix-nvim, nix-paseo, nix-terminal, nixbuild, nixos-core, pyjutsu, silverbullet-server, structured-agents-v2, zelligate (`[publish] verify`), llama-infernal (`[lanes]`), talkee-futo (`trunk = "master"`) |
| `.gitman/` directory (all ignored) | 66 | see summary.txt |
| `.repoman/project.toml` (tracked) | 18 | the 18 `repoman` repositories |
| `.copyroom-local.json` | 20 | template-py v0.8.1 with `repoman_ref`/`testee_ref`: agentman, argentic, eventic (repoman v0.12.1), flora, flora-core, flora-qc, linkman, llgym, poddantic, pyllij, scopeman (testee v0.5.1), shellij; template-py v0.8.0: inferference, pytuin; template-nix v0.4.2 with `devman_ref` v0.5.1: loci.nvim, mnemonix, nix-desktop, nix-nvim, nix-paseo, nix-secrets |
| `.copier-answers*` | 1 | talkee (template-py v0.5.0, repoman v0.12.0, testee v0.5.1) |
| `.devman/project.toml` | 60 | all schema 1, policy stable; groups beyond `base`: devman, observantic |
| Repository-layer `links.yaml` | 1 | linkman (0 links) |
| Real `.agents` | 1 | llama-infernal |
| `.agents` linked to the overlay | 58 | see summary.txt |
| `.claude` with extra real files | 8 | agentfs, flora, gitman, loci-core, nix-secrets, structured-agents-v2, talkee, vendomat |
| `repoman/SKILL.md` reached through the overlay | 22 | 9 distinct contents; 0 real files in repositories |
| `pyproject.toml` family dependencies | 8 | linkman and loci-core (mancore, tag v0.1.0); devman (linkman, path `../linkman`); loci-core (copyroom); argentic, copyroom, devenv-py, devman-spike (templateer); scopeman (zensical) |

## Central overlay

- 74 project directories. 59 match a repository; forgelab is in the archived set; `.archive/` is
  not a project.
- 62 `devenv.local.nix` files import `/run/current-system/sw/share/devman/link-module.nix` and no
  other path.
- 13 directories have no repository: copyroom-consumer, copyroom-consumer-final,
  copyroom-consumer-review, copyroom_probe_xyz, copyroom_template_nix_{basic,custom,home,joined,
  none,probe}, demo_home, demo_service, my_paseo_lib.
- 11 overlay files use `devman.link` without importing the link module: the 10 orphans above
  (except the consumers) and mnemonix. They rely on the repository's own devman import.
- 11 repositories have no overlay directory: agentfs, devman-spike, llama-infernal, mancore,
  nix-meta-channel4, nix-systems, nvim-review, talkee-futo, template-nix,
  terminal-app-dsl-spike, vendomat-demo.
- `~/.config/devman/devenv.yaml` holds only `nixpkgs` and no imports.

## Template sources

Neither template renders `gitman.toml`, `devenv.local.nix`, `.agents`, or `.claude`. Both keep
`.devman/project.toml`, a project fact.

**template-py (v0.8.1):**

- `source/templates/devenv_yaml/template.j2`: `repoman` and `testee` inputs and imports.
- `source/templates/devenv_nix/template.j2`: `repoman.enable`, the `testee.*` block, and base
  tasks that call `testee verify`.
- `source/templates/repoman_project_toml/*` and its entry in `source/manifest.json`.
- `source/templates/pyproject_toml/template.j2` (comment lines 17-21) and `readme_md/template.j2`.
- `source/static/AGENTS.md` (67 lines of personal tool workflow) and `source/static/dot-gitignore`
  (lines 20-31).
- Nine `schema.py` files: `managers`, `repoman_ref`, `testee_ref` (lines 36-42).
- `scripts/check_render.py`; goldens `goldens/py/{basic,probe}`.

**template-nix (v0.4.2):**

- `devenv_yaml/template.j2`: an absolute-path `repoman` input (`repoman_dev_root`) and a `devman`
  input.
- `devenv_nix/template.j2`: `repoman.enable` and a `devman = {}` block.
- The `repoman_project_toml` template and manifest entry; the `agents_md` and `readme_md`
  templates.
- Nine `schema.py` files and nine `scenarios/*.yml`: `repoman_dev_root`, `devman_ref`.
- `scripts/check_render.py`, goldens, and a stale `source/base/templates/repoman_lock/`.

## Repositories that need manual attention

- **mnemonix:** template-nix shape with a local `repoman` input, a `devman` input, and a
  `devman = {}` block. Its overlay relies on that import. No `.devman/project.toml`, no base tasks.
- **nix-systems, vendomat-demo:** managed by `vendomat sync`; pins live in `vendomat.toml`.
- **mancore:** pins Vendomat with nested repoman, copyroom, and gitman pins, plus repoman v0.14.1
  and testee. No overlay directory.
- **devman:** `mancore` is a real dependency; a uv path source `../linkman`; a gitignored lock.
- **testee:** uses its own module, with no input.
- **repoman:** self-hosting with `path:./modules`.
- **pydantree:** `devenv.local.yaml` overrides a `devman` input that `devenv.yaml` does not declare.
- **nix-meta-channel4:** a repository with no commits, a stale lock, and the project name
  `nix-meta`.
- **llama-infernal, talkee-futo:** forks with their own `.agents` or trunk.
- **flora, loci-core, nix-secrets:** real settings files in `.claude`.

## Drift found

- talkee: Copier answers record repoman v0.12.0 and testee v0.5.1; `devenv.yaml` pins v0.14.0.
- scopeman: records `testee_ref` v0.5.1; pins v0.6.1.
- eventic: pins repoman v0.12.1.
- pytuin, fornix, loci-core, templateer_v2, vendomat: pin testee without repoman.

## Limits

The base-task classes and the lock family-node column are heuristic; the raw text is in
`repos.tsv`. The scan reflects the working trees at scan time, including uncommitted edits.

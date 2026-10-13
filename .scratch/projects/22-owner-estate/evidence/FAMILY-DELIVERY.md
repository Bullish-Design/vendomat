# How the family reaches the machine and the repos — 2026-10-13

<!--
Provenance: a read-only subagent survey of ~/Documents/Projects (70 repos with .git or .jj),
~/.config/devman, ~/.local/{share,state}/devman, ~/.local/state/vendomat, the host PATH,
~/.config/systemd/user, nix-meta, nix-meta-channel4, nix-terminal, nix-systems and nixos-core.
Commands used: ls, readlink, grep, git show, git log, and Python JSON reads of devenv.lock.
No file was changed while surveying. Date of the facts: 2026-10-13.
Items marked INFERENCE are conclusions from the evidence, not measured facts.

Correction to the first report: it said six repos (loci.nvim, mnemonix, nix-desktop,
nix-nvim, nix-paseo, nix-secrets) declared an in-repo devman block and pinned devman v0.5.1.
That was true when the survey began. It is false now. Commits dated 2026-10-13 removed the
devman input, import and block from loci.nvim (0340216) and nix-secrets (1efe32e). They removed
RepoMan, and its .repoman directory, from nix-desktop (6fdc90c), nix-nvim (00c6b91) and
nix-paseo (90b11a9). The re-check below gives the current fact.
-->

## Re-check of the two disputed claims

1. **The devman v0.5.1 block.** Today, only mnemonix still has it, and only in its committed
   HEAD (a4da850). HEAD `devenv.yaml` has `repoman` and `devman` inputs. HEAD `devenv.nix` has
   `repoman.enable` and a `devman = { ... }` block. The mnemonix working copy has uncommitted
   edits that already remove both (`devenv.nix`, `devenv.yaml`, `devenv.lock` modified, `gitman.toml`
   deleted, `.devman/project.toml` added). Its `.repoman` directory is still present.
   No other repo has a devman input or block. The six devman v0.5.1 lock entries are gone.
2. **The repoman pin counts.** See the table in "Pins and skew in locks". The count is 18
   repos with a repoman input in `devenv.yaml` and 18 repos with `repoman.enable` in
   `devenv.nix`. It is no longer 23. The count of `.repoman` directories fell to 19.

## Delivery channels

| Tool | How it reaches a repo or the machine today |
|---|---|
| devman | Host: NixOS module from nix-meta puts `devman` 0.6.0 and Dagu 2.15.0 in `/run/current-system/sw/bin`. The same package ships `/run/current-system/sw/share/devman/link-module.nix`. Repo: 63 central overlays import that file. No consumer repo pins a devman module input now. Exceptions: mnemonix at HEAD, and pydantree through a local `path:` overlay. mancore and nix-systems pin devman as a build input. |
| repoman | Repo: a `repoman` module input in the `devenv.yaml` of 18 repos, with `repoman.enable = true` in `devenv.nix`. Central: `~/.config/devman/devenv.yaml` imports it (v0.14.0). Host: not installed since nix-meta commit f173fd0 (2026-10-13). Generated: one `agents/skills/repoman/SKILL.md` copy per project in the central repo. |
| gitman | Host: `gitman` 0.13.1 in `/etc/profiles/per-user/andrew/bin`, built from the gitman flake input in nix-meta. Repo: 62 real `gitman.toml` files in 12 variants. Skill: symlink to the central skill. |
| testee | Repo: a `testee` module input at v0.6.1 in 20 repos. Host: `~/.nix-profile/bin/testee` 0.6.1, installed with `nix profile`. Skill: symlink to the central skill. |
| copyroom | Not on PATH. The skills reach repos by symlink. Versions come from the vendomat toolchain (nix-meta, v0.8.6), mancore (v0.7.7) and nix-systems (v0.8.6). Repo state: 20 `.copyroom-local.json` files. |
| vendomat | Host: `vendomat` 0.5.0 in `/run/current-system/sw/bin`. Repo: nix-systems and vendomat-demo import `inputs.vendomat.devenvModules.default`. |
| docman, agentman | No consumer-repo channel. Both are pinned in the mancore, nix-meta and nix-systems locks. agentman also runs as a home-manager user service built from the vendomat toolchain. |
| linkman, scopeman, siteman, mancore | No pin in any other repo. linkman resolves on PATH only through devman's own venv. |

Symlink channel (one set, central), counted over the 70 repos:

- `devenv.local.nix`: 60 symlinks to `~/.config/devman/projects/<repo>/devenv.local.nix`.
- `.agents`: 59 symlinks to `~/.config/devman/projects/<repo>/agents`. One real directory (llama-infernal).
- `.claude/skills`: 50 symlinks to central. 9 real directories.
- `.envrc`: 55 symlinks to `~/.config/devman/common/envrc`.
- `CLAUDE.md`: 61 symlinks to `AGENTS.md`.

Copied-file channel (real files, no sync):

- `AGENTS.md`: 62 files, 25 to 628 lines.
- `gitman.toml`: 62 files, 12 distinct contents. One content covers 47 repos.
- `.devman/project.toml`: 60 files.
- `.repoman/project.toml`: about 19 files. The count was 23 before the 2026-10-13 removals.
- `.copyroom-local.json`: 20 files. They record answers such as `repoman_ref` and `testee_ref`.
- `links.yaml`: 1 file (linkman, empty). `.copier-answers.yml`: 1 file (talkee).

The canonical gitman, copyroom and testee skills live in the central repo `~/.config/devman/skills`,
not in their tool repos. devman's own skills live only under
`~/.config/devman/projects/devman/agents/skills/`.

## Pins and skew in locks

Repoman, consumer `devenv.lock` files (current):

| Pin | Rev, date | Repos |
|---|---|---|
| v0.14.0 | 6695db36, 2026-10-11 | 14: agentman argentic devenv-py flora flora-core flora-qc inferference linkman llgym poddantic pyllij scopeman shellij talkee |
| v0.14.1 | d50c3029, 2026-10-12 | 1: mancore (it also holds a second v0.14.0 node) |
| v0.12.1 | 3f3df9b1, 2026-10-09 | eventic, nix-systems |
| unpinned or local | no rev | forgelab (`git+file://`, archive list), repoman (`path:./modules`), nix-meta and nix-meta-channel4 (flake locks) |

Latest repoman tag: v0.14.1. Only mancore holds it. Older tags sit in nix-meta (v0.7.5, v0.10.0)
and nix-meta-channel4 (v0.7.5, v0.9.2). Oldest repoman pin: v0.7.5, 2026-09-07.

Devman, consumer locks (current):

| Pin | Where |
|---|---|
| v0.5.2, 8e7c3be6, 2026-09-12 | mancore |
| v0.8.0, c8647250, 2026-10-09 | nix-systems |
| local `path:` to the devman checkout | pydantree (untracked `devenv.local.yaml`) |

The 2026-09-10 v0.5.1 pin (8311f143) no longer appears in any consumer lock.
nix-meta holds devman v0.7.0 (4c9927ad, 2026-09-15), v0.5.2 and a `main` from 2026-01-01.
nix-terminal holds the same `main`. The host runtime is `devman-0.6.0`.
Tag v0.7.0 and v0.8.0 do not match pyproject 0.6.0 (see "Drift hazards").

Other tools:

- testee: 20 consumers at v0.6.1 (b5ec947d, 2026-10-11). nix-systems at v0.5.0. Latest tag v0.7.0.
- gitman: v0.13.1 (nix-meta, mancore), v0.13.0 (nix-systems), v0.9.1 (nix-meta-channel4).
- copyroom: v0.8.6 (nix-meta, nix-systems), v0.7.7 (mancore, nix-meta-channel4).
- docman: v0.2.1 (mancore, nix-meta), v0.3.1 (nix-systems).

mancore aggregator lock: agentman 0.0.3, copyroom 0.7.7, devman 0.5.2, docman 0.2.1, gitman 0.13.1,
pyjutsu 0.22.0, repoman 0.14.1 and 0.14.0, templateer 0.4.1, testee 0.6.1, vendomat 0.4.5.
Most of these lag the nix-systems pins. The devman checkout also pins mancore v0.1.0 (af557e16).

nix-meta lock (host build, 2026-10-13): gitman v0.13.1, vendomat rev d5a90f0a with templateer
v0.6.0 and copyroom v0.8.6 overrides, pyjutsu v0.23.0, docman v0.2.1, agentman v0.0.3.

Skew count: repoman has at least 6 distinct tags in use (v0.7.5, v0.9.2, v0.10.0, v0.12.1, v0.14.0,
v0.14.1) plus local paths. Devman has 4 tags (v0.5.2, v0.7.0, v0.8.0 and the 0.6.0 runtime) plus `main`
and a local path.

## Host installation

| Command | Path | Version | Source |
|---|---|---|---|
| `devman` | `/run/current-system/sw/bin/devman` | 0.6.0 | nix-meta NixOS module |
| `dagu` | `/run/current-system/sw/bin/dagu` | 2.15.0 | same |
| `vendomat` | `/run/current-system/sw/bin/vendomat` | 0.5.0 | system profile (repo is at 0.7.0-rc.1) |
| `gitman` | `/etc/profiles/per-user/andrew/bin/gitman` | 0.13.1 | home-manager, gitman flake input |
| `testee` | `~/.nix-profile/bin/testee` | 0.6.1 | imperative `nix profile` install |

Not on PATH: repoman, copyroom, docman, linkman, scopeman, siteman, mancore, agentman, templateer.
The nix-meta commit f173fd0 "Stop installing RepoMan machine-wide" removed the repoman toolchain.
Copyroom came with that toolchain. Many `devenv.yaml` comments still say the host profile puts
copyroom on PATH. That is stale.

Per-repo venvs also hold some family commands (counts of repos with the command in
`.devenv/state/venv/bin`): gitman 3, linkman 2, copyroom 2, devman 1, repoman 1, docman 1, agentman 1,
testee 1, vendomat 1. INFERENCE: these appear because of each repo's own dev group, not by design.

`/etc/nixos/configuration.nix` is a plain host config with no family references. nixos-core has no
family references. nix-systems pins by tag in `vendomat.toml`.

## Central layer and state roots

- `~/.config/devman` is a git and jj repo with its own `devenv.yaml` (repoman v0.14.0) and `devenv.nix`
  (`base:check` evaluates each overlay's argument contract). Recent commits: 00b369d8 (2026-10-13)
  "remove the RepoMan input, import, and project manifest"; 801dda21 and f3abcfed removed the RepoMan
  import from tyo3 and loci.nvim overlays.
- Contents: `skills/` (14 skills), `agents/devenv`, `hooks/` (testee_integrate_gate.py), `common/`
  (`envrc`, `claude.json`), `projects/` (73 entries), `dags/` (10, derived), and
  `.devman-link-state.json` (link hashes).
- 63 of the 73 project entries import `link-module.nix`. The 10 that do not are copyroom probe
  and demo entries.
- Skills inside each project's `agents/skills/` link back to `~/.config/devman/skills/*`, except the
  generated `repoman/SKILL.md`. That file exists in 23 project directories with 10 distinct contents.
- State roots (three, each with a different owner):
  - `~/.local/share/devman`: `dags/` (183 files), `projects/` (58), `watch/`. The old compatibility registry.
  - `~/.local/state/devman`: `projects/`, `watch/`, `reload.target`. The stable state root.
  - `~/.local/state/vendomat/devman`: `active -> generations/4`. `generation.json` shows
    `devman_runtime: v0.6.0` and `generation: 4`. nix-meta sets `registryDir` to this path.
- `~/.local/state/vendomat` also holds vendomat's own probe and proof state (v4-proof, v5, v6, v7,
  v7-spikes, p17-probe, p20, p21, secrets, and test logs). INFERENCE: vendomat is the tool that now
  owns the machine plane, because nix-meta points devman's registry into its state directory.
- The devman repo's CLAUDE.md says the active generation is 3. The machine is on generation 4.

## systemd units

- `~/.config/systemd/user/devman-maintain.service` and `.timer`: real, hand-written files. The service
  runs `/run/current-system/sw/bin/devman run maintain --project X` for devman, siteman, pyjutsu,
  nix-paseo and pydantree. The timer runs daily with a 15-minute random delay.
  The service says `After=dagu.service`.
- `dagu.service` does not exist at system level. The user bus was not reachable from the survey shell,
  so the user-level Dagu state is unverified.
- `agentman.service` and `agentman.socket`: home-manager units, built from the vendomat toolchain
  (`agentman migrate`, then `agentman serve --systemd-socket`).
- `argentic-overlay.service`: runs `argentic/.venv/bin/argentic overlay serve`. It is a repo venv, not a
  store path.
- `flora-showcase.service`: symlink into the flora repo.
- `mnemonix-render-coding-agent-config.{path,service,timer}`: home-manager units.

## Drift hazards

1. **Many pin sets.** Repoman has 6 tags in use. Devman has 4 tags plus `main`. Check
   `~/.config/devman/devenv.yaml` (v0.14.0) against the v0.14.1 tag, and the nix-meta locks against both.
2. **Unfinished removals.** mnemonix HEAD still has the devman and repoman inputs, and its working
   copy holds uncommitted removal edits. 18 repos still enable repoman, while the host no longer
   installs it. INFERENCE: a RepoMan retirement is under way and not complete.
3. **Gitignored locks.** 11 repos ignore `devenv.lock` (atuout, browsee, copyroom, devman, docman,
   fsdantic, grail, knappy, nixbuild, tyo3, zelligate). Their pins can lag and no commit shows it.
4. **Host lags repos.** Host vendomat is 0.5.0, the repo is 0.7.0-rc.1. testee is installed outside
   any declarative config. The `devman` runtime is 0.6.0 while the locks name v0.7.0 and v0.8.0.
5. **Tag does not equal pyproject version.** devman tag v0.8.0 and pyproject 0.6.0. testee v0.7.0 and
   0.6.0. docman v0.3.1 and 0.3.0. linkman v0.1.1 and 0.1.0. A version number does not name one revision.
6. **Stale comments.** `devenv.yaml` comments in about 20 repos say the host profile puts copyroom on
   PATH. The "devman: the automation plane's repo interface (CONCEPT.md §3.2)" comment stays above an
   `imports:` list with no devman in it (devman, docman, gitman, siteman, copyroom).
7. **Skills live in the central repo only.** The gitman, copyroom and testee skills are not in their
   tool repos. A tool repo change cannot update its own skill.
8. **Copied files with no sync.** `gitman.toml` (12 variants), `AGENTS.md` (62 files),
   `testee.checks` blocks per repo, `.repoman/project.toml`, `.copyroom-local.json`, and the 23
   generated `repoman/SKILL.md` copies with 10 contents.
9. **Older copies mislead.** nix-meta-channel4 and nix-terminal hold older pins of the same tools
   (repoman v0.7.5, gitman v0.9.1, devman `main` from 2026-01-01).
10. **Unlinked tools.** linkman, scopeman, siteman and mancore have no consumer channel, so no repo
    reaches them by pin. linkman is on PATH only through devman's venv.

Key paths: `/home/andrew/.config/devman/`, `/home/andrew/Documents/Projects/mancore/devenv.lock`,
`/home/andrew/Documents/Projects/nix-meta/flake.nix`,
`/home/andrew/Documents/Projects/nix-meta/profiles/{developer,devman}.nix`,
`/home/andrew/Documents/Projects/nix-systems/vendomat.toml`,
`/home/andrew/.config/systemd/user/devman-maintain.service`,
`/home/andrew/.local/state/vendomat/devman/active/generation.json`.

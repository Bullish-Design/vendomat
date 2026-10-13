# Project 22: The owner's estate — machine, home, overlay, project

**Draft concept, 2026-10-13.** The owner asked for a canonical way to use the personal tool family
(devman, repoman, linkman, gitman, copyroom, testee, mancore, agentman, and their siblings). The
owner also asked for the best structure for nix-meta, aligned with the Vendomat and Basix concept
of [project 21](../21-vendomat-basix-split/CONCEPT.md). The owner's words are in
[DECISIONS.md](DECISIONS.md). One spike ran ([W1](evidence/W1-DEVLAYER-PATH.md)). The other
evidence records are read-only surveys. No production code, consumer, or machine changed. Each new
option name, command, path, and file format here stays proposed until a fixture proves it on the
pinned tools.

## Goal

One owner has a few machines and about 70 project repositories. The owner's personal tools behave
the same in every repository, at one version, chosen in one place. A tool change reaches every
repository without an edit in any repository. Each repository still says how the tools treat it,
and each repository still owns its own scripts. Someone who clones a repository gets a working
project without the owner's tools.

## The problem

The personal tools are environment, like an editor or a shell. Today they are delivered like
project dependencies. Each repository pins them, copies their configuration, or receives their
versions from a template. Every tool change therefore becomes work in every repository.

Measured on 2026-10-13 ([FLEET-INVENTORY](evidence/FLEET-INVENTORY.md),
[FAMILY-DELIVERY](evidence/FAMILY-DELIVERY.md), [NIX-META-AUDIT](evidence/NIX-META-AUDIT.md)):

| Symptom | Count |
| --- | --- |
| Repositories that pin the `repoman` devenv module in `devenv.yaml` | 18 (16 by tag, 2 by local path) |
| Repositories that pin the `testee` devenv module | 22 |
| Lines of `testee.*` configuration in repository `devenv.nix` files | 734, in 23 repositories |
| `gitman.toml` files that no Gitman version reads since 0.12.0 | 62 (47 identical) |
| Template answer files that record tool tags (`repoman_ref`, `testee_ref`, `devman_ref`) | 20 |
| Repositories with a gitignored `devenv.lock`, so a local pin drifts unseen | 11 |
| devman nodes in nix-meta's `flake.lock` | 3 (v0.7.0, `main` from 2026-01-01, v0.5.2) |
| gitman and repoman nodes in nix-meta's `flake.lock` | 2 each |
| nixpkgs trees in nix-meta's `flake.lock` | 7 |
| nix-meta commit subjects that mention a pin, a bump, or a lock | 77 of 265 |

The same structure produced broken contracts that nothing reported:

- devman's `agent` group calls `agentman run --request` and the `agentman.devman/v1` contract.
  Agentman deleted both on 2026-09-18.
- The only `linkman` on `PATH` is in devman's own virtual environment. It fails with
  `ModuleNotFoundError: click`, because it locks mancore at tag v0.1.0.
- A repository shell put Claude Code 2.1.207 ahead of the host's 2.1.291. The API refused the
  model. The repository pin sat in a gitignored lock.
- About 20 repository comments say the host puts copyroom on `PATH`. Nothing does today.

One channel works with no drift: the central overlay. 60 repositories link `devenv.local.nix`, 59
link `.agents`, and 55 link `.envrc` from `~/.config/devman`. None of them holds a copy. This
concept extends that model to everything else.

## The clone test

One question decides where a tool or a file belongs:

> Would someone who clones this repository still need it?

- **Yes:** it is a project fact or a project dependency. It stays in the repository, tracked, and
  the repository may pin it like any dependency.
- **No:** it belongs to the owner. It comes from the owner's home or the central overlay. No
  repository pins it or holds a copy of it.

devman already uses this test to place files (its charter, project 025, §P0). This concept applies
the same test to tools and versions. [TOOL-CLASSES](evidence/TOOL-CLASSES.md) applies it to each
tool.

| Tool | Class | Consequence |
| --- | --- | --- |
| devman, linkman, gitman, repoman, copyroom | Personal | No repository pins them. They come from the home. |
| testee | Personal | It runs the repository's standard tasks. The tasks and their commands are project facts (R10). |
| agentman | Personal service | Its daemon is a home service. Its database is machine infrastructure. |
| mancore | Project dependency | linkman and loci-core import it. They pin it in `pyproject.toml`, correctly. |
| Vendomat | Project dependency, where used | A workspace that builds with `vendomat.yaml` needs Vendomat. It pins Vendomat in its own lock. |
| docman | Archived | Remove the stale references. |
| siteman | Product | Outside the personal layer. A site repository may pin it as a dependency. |

## Four layers

The estate has four layers. Each layer has one owner, one source of truth, and one way to roll
back.

| Layer | Holds | Source | Activation | Changes | Rollback |
| --- | --- | --- | --- | --- | --- |
| **Machine** | Hardware, disks, boot, users, linger, system secrets, root services | nix-systems | `vendomat apply` (sudo) | Rarely | NixOS generations; Vendomat's health check |
| **Home** | Shell, editor, agent tools, the personal tools, user services, the devenv modules that repositories import | nix-meta, as standalone Home Manager | `home-manager switch` (no sudo) | Often | Home Manager generations |
| **Overlay** | Skills, workflows, per-project overlays, hooks, link declarations | `~/.config/devman` (git) | Symlinks, kept by the link plane | Often | git |
| **Project** | Manifests, devenv task bodies, project dependencies | The repository | Shell entry | Per project | git |

The machine and the home are the two things the owner switches. Each has exactly one repository,
one lock, and one generation line. The overlay and the project need no build.

### Machine

The machine layer holds what needs root or describes hardware:

- disks, boot, kernel, hardware modules (the ARCTIC fan controller, the AMD GPU power profile,
  `gpu-compute`)
- users and their IDs, `linger` for the owner, SSH, Tailscale, the firewall
- system secrets (sops-nix, nix-secrets)
- root services: Postgres and its roles, atticd, the git daemon that serves the collection, the
  atuin server, the Hindsight service, Paseo, SilverBullet, the inferference router
- Nix daemon settings, such as substituters and trusted users
- the platform: the patched devenv binary (project 21 R22, R31) and the `vendomat` launcher
  (owner ruling R13). Every workspace needs them, including a workspace that someone else clones,
  and `vendomat apply` needs root.

**The machine holds no version of a personal tool.** The platform is not a personal tool. The home and the machine then cannot disagree
about a tool, and a machine rollback never changes a tool.

The machine follows project 21: machines are devenv Machines on a pinned devenv (project 21
ruling R4). nix-systems already works this way ([NIX-SYSTEMS](evidence/NIX-SYSTEMS.md)). It
declares hardware facts in an inventory, it has a minimal core that boots with no Vendomat service,
and its VM tests cover plan, apply, health-check rollback, and a disk harness.

### Home

The home layer holds everything that belongs to the owner as a user. It is a standalone Home
Manager configuration, one per user and machine: `homeConfigurations."andrew@<machine>"`.

- shell, terminal, editor (nix-terminal, nix-nvim)
- the atuin client and daemon, atuout, pytuin
- agent tools: Claude Code, Codex, Pi, zellij, the mnemonix coding-agent wiring
- **the personal layer**: the personal tools on `PATH`, their user services (Dagu, the devman
  watcher, the agentman daemon), the devman registry, and the eval-time devenv modules that
  repositories import

`home-manager switch` activates a change with no sudo and no system rebuild. A tool change needs
one input bump in nix-meta and one switch.

The home never runs as a NixOS module. One user has exactly one Home Manager. Two would write the
same files and keep two generation lines ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)).

### Overlay

The overlay is the git repository at `~/.config/devman`. It holds the owner's content: skills,
workflows, hooks, the shared `.envrc`, and one directory per project with that project's
`devenv.local.nix`, `links.yaml`, and agent files. The link plane links these files into each
repository and adds the matching `.git/info/exclude` lines.

The overlay already works. This concept adds three things to it:

1. Each overlay `devenv.local.nix` imports the personal layer's devenv modules from the home path
   (see [The devenv import path](#the-devenv-import-path)).
2. Personal setup for a project that only the owner needs, such as a Testee hook that needs sibling
   checkouts.
3. One canonical copy of each skill. The generated `repoman/SKILL.md` has 9 distinct contents
   across 22 project directories today.

### Project

A repository holds only facts that are true for anyone who clones it:

| File | Holds |
| --- | --- |
| `devenv.nix` | The project's packages, languages, services, and task bodies, including `base:check` and `base:test` |
| `devenv.yaml` | Real project dependencies only |
| `devenv.lock` | The project's lock, tracked |
| `.devman/project.toml` | The project's identity, groups, and policy, with `schema = N` |
| `links.yaml` | The repository layer of link declarations, if any |
| `AGENTS.md` | Project-specific agent instructions |
| `vendomat.yaml` | Only in a workspace that builds with Vendomat |

A repository holds no personal-tool input, no personal-tool option, no copied tool configuration,
and no generated skill. The overlay links supply everything personal, and git ignores them.

## Rules

1. **One activation unit, one repository, one lock.** The machine is nix-systems. The home is
   nix-meta. A personal tool appears in exactly one lock: the home lock. A flake check fails when
   the home lock holds two nodes for one family tool.
2. **The machine holds no personal-tool version.**
3. **Personal inputs come from the collection by tag.** The source is `git://server/<repo>` at a
   release tag, as project 21 states. No input uses `git+file://`, `path:`, or a branch such as
   `?ref=main`. Development uses `--override-input` (see [How a change flows](#how-a-change-flows)).
4. **Modules are plain NixOS or Home Manager modules.** Settings arrive as options. A module does
   not read `specialArgs`, `osConfig`, or the other half's configuration. Host facts come from one
   inventory. The same modules then work in nix-meta today and in devenv Machines later.
5. **Tools read repository data. Repository data never imports a tool.** Each repository manifest
   carries a schema number. A tool accepts the schemas it knows and refuses any other one with an
   error that names the file. The schema replaces the version pin as the compatibility check.
6. **Tools talk through command contracts, not imports.** A tool calls another tool's command and
   reads its JSON output and exit code. devman already chose this for linkman (devman project 044,
   D23). mancore becomes the written contract (exit codes, report shape, `capability --json`), and
   stays an optional library for tool authors.
7. **A repository never holds a copy of personal content.** It holds a symlink or nothing.
8. **Every rule has a check that can fail.** The fleet doctor (below) checks rules 1, 5, and 7 in
   every repository.

## How a change flows

### Release

1. The tool's repository tags a release and pushes the tag to the collection.
2. `nix flake update <tool>` in nix-meta. One commit in one repository.
3. `home-manager switch --flake ~/Documents/Projects/nix-meta#andrew@<machine>`.
4. The fleet doctor runs over every repository and reports any manifest the new version refuses.

No project repository changes.

### Development

The owner develops a tool and tries it in real repositories:

```bash
home-manager switch --flake .#andrew@server --override-input linkman path:/home/andrew/Documents/Projects/linkman
```

Every repository then uses the development build. A plain `switch` restores the release. No
repository file and no lock changes. A trial in one repository puts the override in that
project's overlay `devenv.local.nix`, never in the repository. **Proposed:** W2 must prove
`--override-input` on the installed `home-manager`.

This replaces three routes in use today: `path:` overrides in `devenv.local.yaml`, committed
`path:/home/andrew/...` pins, and editable path dependencies in `pyproject.toml`.

### Rollback

A bad tool release rolls back with the previous home generation: `home-manager generations` names
it, and its `activate` script restores it. The machine does not change. A lasting rollback is the
same as in project 21: restore `flake.lock` from version control, then switch.

### Changes that span both layers

A few things have a machine half and a home half:

| Pair | Machine half | Home half |
| --- | --- | --- |
| atuin | atuin server (pytuin's server module) | atuin client and daemon |
| agentman | Postgres role `agentman`, database `agentman`, peer authentication for `andrew` | agentman daemon (user service) |
| mnemonix | Hindsight service, ports 8891 and 9991 | coding-agent wiring that calls the API |
| Secrets | sops-nix writes `/run/secrets/*` with owner `andrew` | Tools read those paths at run time |

For each pair, one flake owns the shared package or constants: pytuin owns the atuin package,
mnemonix owns its ports. Both halves pin the same tag. The change order is machine first, home
second. A check compares the versions that run (for example `atuin --version` against the
server's version). Today one `nixos-rebuild` does both halves at once; the two-step order is a
cost of this design.

## Per-project configuration

A repository still controls how the tools treat it. It does so with data and with named tasks,
never with a tool version.

**Precedence.** A tool that reads configuration resolves each key in this order:

1. a command-line flag
2. the repository manifest (tracked)
3. the project's overlay directory (`~/.config/devman/projects/<name>/`)
4. the owner's default (`~/.config/<tool>/`)
5. the tool's built-in default

The repository layer accepts a closed set of keys. A key outside the set is an error. Agentman
already works this way: a repository may set `agent` and `model`, and a repository that sets
`database_url` fails, and `agentman config` prints the source of each value.

**Scripts.** Tools call fixed task names. The repository owns the task bodies. devman's `base`
group already works this way: it runs `devenv tasks run base:check` and `base:test`, and the
repository defines what they do. A cloner runs the same tasks with no personal tool. Personal
per-project scripts (for example a Testee `prepare` hook that needs sibling checkouts) live in the
project's overlay `devenv.local.nix`.

**Testee** (owner ruling R10). Each repository defines a small fixed set of devenv tasks. They are
project facts, and a cloner runs them with no personal tool:

| Task | Meaning | Called by |
| --- | --- | --- |
| `check:lint` | Lint | `base:check`; both Testee profiles |
| `check:format` | Format check; never rewrites a file | `base:check`; both Testee profiles |
| `check:types` | Type check | `base:check`; `testee verify` |
| `test:quick` | Fast subset for the edit loop | `testee verify --profile quick` |
| `test:full` | Full suite | `base:test`; `testee verify` |

- Testee runs these task names against a clean checkout of the commit and keeps one verdict per
  task. It needs no devenv module, no input, and no per-repository configuration.
- The templates write each task as a placeholder. A placeholder prints how to configure it and
  exits 78 (`EX_CONFIG`). Testee reports exit 78 as **not set up**, apart from green and red. A
  placeholder never exits 0: a check that passes while it checks nothing is the failure this design
  prevents.
- A repository that has no use for a task replaces it with an explicit `exit 0` and a one-line
  reason. Each task is therefore in one visible state: not set up, wired, or not applicable.
- `base:check` and `base:test` chain to the standard tasks with `after`. Extra steps (`uv sync`, a
  documentation build) hook into a standard task with `after`. No separate prepare step exists.
- Personal setup that only the owner needs (for example a hook that needs sibling checkouts) lives
  in the project's overlay `devenv.local.nix`.

**Proposed:** W4 must prove the Testee change (task mode and the exit 78 state).

## The devenv import path

devenv evaluates each project shell. The personal layer's devenv modules (devman's link module
today) must reach that evaluation. Today 62 overlay files import
`/run/current-system/sw/share/devman/link-module.nix`, a system path.

### What devenv tracks

W1 ([W1](evidence/W1-DEVLAYER-PATH.md)) measured devenv 2.4.0's evaluation cache, and W9
([W9](evidence/W9-EVAL-CACHE.md)) explained it from devenv's source:

- Nix reports an evaluated file by its path as written, unless the final path component is a
  symlink. Then it reports the symlink's target.
- devenv drops every reported path in `/nix/store`. An import whose final component links into the
  store therefore gets no cache row and is never checked again.
- devenv re-hashes the tracked paths on a cache hit, so a change behind a directory symlink is
  caught. Nothing promises this. Open issue cachix/devenv#3154 asks for a time shortcut that would
  end it, because every store file has modification time 1.

**Rule:** devenv re-checks an import only when the final component of its path is not a symlink.

Consequences:

- **Today's import is stale-prone.** `/run/current-system/sw/share/devman/link-module.nix` is a file
  symlink into the devman-link package. The real cache has no row for it. After a devman-link
  upgrade, a repository keeps the old module until `--refresh-eval-cache` runs or another tracked
  input changes.
- The layout first planned under R11 (a Home Manager directory over a `linkFarm` of file links) is
  stale for the same reason.
- A layout of real files behind a directory symlink works today, but only through the re-hash that
  issue #3154 may remove.

### The pointer file (owner ruling R12)

The home builds the layer as one store directory. Home Manager activation then writes one **real
file outside the store**, the pointer, that names the layer's store path:

```nix
# ~/.local/state/devlayer/current.nix (proposed path), written by activation, never a symlink
import /nix/store/<hash>-devlayer
```

- Each overlay `devenv.local.nix` imports the pointer, never a store path or a symlink.
- Activation rewrites the pointer only when the layer's store path changes. Its content and its
  modification time then change, so both of devenv's checks catch the change, with or without the
  time shortcut of issue #3154. The pointer does not depend on how Nix reports directory symlinks.
- The pointer is not a Home Manager-managed file: such files are symlinks into the store and would
  go untracked.
- The layer's own files are immutable store paths. A new layer has a new path, which changes the
  pointer.

W10 ([W10](evidence/W10-POINTER.md)) proved the pointer on devenv 2.4.0. A rewrite is caught with
no flag, by the time check alone, and still caught when the time is forced back. A rewrite with the
same content does not force a new evaluation. Its pin fixture (`pin-fixture.sh`) fails when the
pointer case breaks and warns when the directory case breaks.

**The configurable path (owner ruling R14).** The pointer path is a Home Manager option. One shared
regular file in the overlay (for example `~/.config/devman/common/devlayer.nix`) names the pointer
and guards the import with `builtins.pathExists`. Each project's overlay `devenv.local.nix` imports
the shared file by relative path. A relative import resolves against the overlay file, the target
of the project's symlink. A change of the option is then one edit in the home and one in the shared
file, and the fleet doctor fails when the two disagree. The pointer and the shared file are regular
files, never symlinks (W10, `ESTATE-038`).

The pointer must not be under `~/.local/share/devman/`, because `devman doctor --prune` manages that
root. The name `devlayer` stays proposed.

## The fleet doctor

Each rule needs a check that can fail. One command checks every registered repository. The owner
runs it after each switch. **Proposed:** it is a devman doctor mode (`devman doctor --fleet`),
because devman doctor is already the one check of the whole plane.

It fails on:

- a personal-tool input, import, or option in a repository's `devenv.yaml` or `devenv.nix`
- a manifest schema that the installed tool refuses
- a real file where the overlay should link (`.agents`, `.claude/skills`, `devenv.local.nix`,
  `.envrc`)
- a file that belongs to a retired concept (`gitman.toml`, `.repoman/project.toml`, a template
  answer that records a tool tag)
- an import in an overlay `devenv.local.nix` whose final path component is a symlink, or that has
  no row in the repository's evaluation cache (W9)
- a second family-tool node in the home lock
- a personal tool on `PATH` from a second source (system profile, `~/.nix-profile`, a repository
  virtual environment)

It warns on an overlay directory with no repository (13 today) and on a repository with no overlay
directory.

W5 ([W5](evidence/W5-FLEET-DOCTOR.md)) built a prototype of these checks and took a baseline. The
doctor writes nothing in a repository: it reads a copy of each evaluation cache (`ESTATE-044`).

## Relation to project 21

Project 22 adopts project 21's machine path, its tag-pinned collection, and its rules "native
first", "one value, one place", and "Vendomat packages no one else's tools". Project 21 states the
Vendomat and Basix products, and its design is final (2026-10-13). Project 22 states where each part
of the owner's estate lives.

Project 21 answered the three proposals of this concept:

| Proposal | Project 21 answer |
| --- | --- |
| The clone test settles the pin topology | **R33** (`VMT-112`): a workspace that builds with `vendomat.yaml` pins Vendomat in its own `devenv.lock`; a personal tool never enters a workspace lock. |
| A standalone home is a native target, or outside Vendomat | **R35** (`VMT-122`): homes stay outside Vendomat. The catalog maps no home key; devenv's native `machines.NAME.home-manager` is reachable only through the escape hatch. A two-command alias may later make a home switch look native. |
| Host-side modules use the layer and the pointer file | **R36** (`VMT-123`): Vendomat ships no host-side module. A workspace gets Vendomat only through its own lock. The project 14 `consumer-module.nix` and `machine.json` go with the project 14 code. The pointer file stays a project 22 idea, for the personal layer only. |

Other project 21 rulings that shape this concept:

- **R22, R31, slice S2:** hosts and the Basix ISO install `pkgs.devenv` from Vendomat's pinned
  nixpkgs with patches 0003 and 0005. Switching the host to that binary is an owner gate. Owner
  ruling R13 of this project therefore puts the devenv binary and the `vendomat` launcher in the
  machine layer.
- **R34:** Vendomat opens no upstream pull request, so the patched devenv binary is long-lived.
  A binary patch that tracks a symlinked import by its path as written would fix W9's finding at
  the source. Project 22 does not depend on it: the pointer file works on stock devenv. Such a patch
  needs a project 21 ruling, because `VMT-105` fixes the patch set.
- **R19 (`VMT-093`):** in a Vendomat workspace, the overlay `devenv.local.nix` is a hatch file, and
  shell entry prints an `advanced:` line for it. A personal setting hides that line.

nix-systems runs Home Manager as a NixOS module on purpose, so a system rollback also rolls back
home state. Owner ruling R8 reverses that choice, and project 21 R35 agrees: homes stay outside
Vendomat. The reason: rule 2 removes the risk that the shared rollback guards against, and the
owner wants home changes without a system rebuild.

Basix is a learner distribution and is not built. It is outside the owner's personal layer. If
Basix later offers capabilities the owner wants, nix-systems consumes them as machine inputs.

## How the current system changes

[NIX-META-AUDIT](evidence/NIX-META-AUDIT.md), [SUB-FLAKES](evidence/SUB-FLAKES.md),
[HOME-PORT](evidence/HOME-PORT.md), and [FLEET-INVENTORY](evidence/FLEET-INVENTORY.md) hold the
file and line references for each item. The raw inventory is under
`~/.local/state/vendomat/p22/inventory/`.

### nix-meta becomes the home repository

Target shape (proposed):

```
flake.nix             inputs and outputs only
lib/inventory.nix     user, machines, tailnet name, paths: the only place they appear
homes/andrew/         default.nix (shared) and <machine>.nix (per-machine extras)
modules/home/         terminal, atuin, agent, devlayer, mnemonix: one concern each, with enable
checks/               evaluate each home; one node per family tool in flake.lock; module tests
```

Outputs: `homeConfigurations."andrew@<machine>"`, `homeModules.*`, and `checks`. nix-meta stays a
flake: project 21 R35 keeps homes outside Vendomat, so a Vendomat workspace is not an option for it.
Use a plain flake, or flake-parts to remove per-system boilerplate. The dendritic pattern gains most when one
file spans NixOS and Home Manager, and this split removes that need. snowfall-lib's own README
says it is effectively unmaintained ([NIX-PATTERNS-RESEARCH](evidence/NIX-PATTERNS-RESEARCH.md)).

Changes:

- Replace the Home Manager NixOS module (`profiles/developer.nix:29`, `terminal.nix`, `agent.nix`,
  `machines/server.nix:30`) with one standalone `homeConfigurations."andrew@server"`. Do it in one
  change. Never run both.
- Move the user-level content of `terminal.nix`, `developer.nix`, `agent.nix`, and `mnemonix.nix`
  into `modules/home/`. The devenv binary is the exception: it moves to the machine (R13). Move `claude-code`, `codex`, and `zellij` from `environment.systemPackages`
  to `home.packages`.
- Replace the reads across the halves with constants or shared packages:
  - `terminal.nix:22` reads `config.users.users.<user>.uid`; use a constant UID, set on the machine
    too.
  - `mnemonix.nix` reads `config.services.mnemonix.hindsight.*`; use constants that mnemonix owns.
  - The flake check at `flake.nix:309` reads `home-manager.users.andrew.programs.atuin.package`;
    read pytuin's package output instead.
- Remove the stale inputs and nodes:
  - nix-terminal's `devman` (`main`) and `repoman` (v0.7.5) inputs, its `programs.devman` and
    `repoman` modules, and the import at `profiles/developer.nix:148`
  - the `vendomat` input at raw rev `d5a90f0` with its copyroom and templateer overrides, and the
    `repoman-toolchain-core` closure that `developer.nix:178` appends to `PATH`
  - the `git+file://` and `path:` inputs (nix-paseo, nix-secrets, nix-terminal, mnemonix, atuout,
    pytuin, argentic, fornix-host), replaced by tagged collection inputs
  - the floating refs (`?ref=main` on nixos-core, nix-paseo, nix-terminal, silverbullet-server,
    inferference, claude-code, codex-cli)
- Add `follows` for nixos-core, or move it to nix-systems with the machine.
- Delete the dead parts: `machines/wsl.nix`, `machines/desktop.nix`, `profiles/gui.nix`, the
  disabled fornix-host, the commented zelligate, structured-agents, and snapper blocks, and the
  `nix-meta.developer.repoman.*` options. Rewrite `AGENTS.md`.
- Move the machine content to nix-systems as nix-systems takes over each machine: `server.nix`
  (773 lines), `backup.nix` (736 lines), `gpu-compute.nix`, the hardware modules, `secrets.nix`,
  and the root services. nix-meta's `nixosConfigurations` then disappears.

### The composed flakes

- **nix-terminal:** remove the `devman` and `repoman` inputs and modules. Split the `terminal`
  module into `zsh`, `atuin`, `tmux`, `development`, and `neovim`, each with `enable`. Fix the
  README, which still names nixvim.
- **nix-nvim:** pin by tag in nix-terminal.
- **nixvim:** archive. nix-nvim supersedes it.
- **nix-meta-channel4:** delete. It is a worktree of nix-meta with no commits.
- **atuin:** keep one package definition, in pytuin. Remove nix-meta's `nix/atuin-18.23.0.nix`
  and the `atuinsh/atuin` input. Remove pytuin's vendored atuout package.
- **mnemonix, nix-paseo, nixos-core:** remove the hardcoded `andrew` and `/home/andrew/...`
  defaults, so the modules work in a standalone home.
- **nixbuild:** a plain package flake, installed by the home.
- **nix-desktop:** keep as a home module for a future laptop home, or archive.

### nix-systems

- Stop running Home Manager as a NixOS module (`nixos/home.nix`), per R8.
- Take over the server's machine content from nix-meta, module by module, each with its VM test.
- Remove the personal tools from `nixos/server.nix` `environment.systemPackages` (gitman, repoman,
  testee, copyroom) and from `vendomat.toml`. Keep the Dagu `linger` setting.
- Move from `vendomat.toml` to `vendomat.yaml` when project 21's catalog ships.

### devman

- Export a `homeManagerModules.default`. Split `nix/nixos-module.nix` into shared options, a
  neutral service description, and two translators (NixOS and Home Manager). The Home Manager
  translator writes `systemd.user.*` in Home Manager form, `home.packages`, an explicit service
  `PATH`, the layer directory, and the activation step that writes the pointer file. `linger` stays
  on the machine.
- Put the link module into the layer directory. Put the store path of `devman-link`, not
  `/run/current-system/sw/bin/devman-link`, into the module.
- Remove the `agent` group, or port it to agentman's current interface.
- Finish the linkman switch-over: devman calls the linkman command, and the old `devman_link`
  engine and the `DEVMAN_LINK_ENGINE` flag go.
- Fix the docs that teach the retired route (`imports: devman/modules` in `README.md`, `USER.md`,
  and the adopt skill).
- Add the fleet doctor.

### The other tools

| Tool | Change |
| --- | --- |
| repoman | Its module moves to the home layer, imported once by the overlay. Its generated skill becomes one central copy. 18 repositories lose the input, the import, `repoman.enable`, and `.repoman/project.toml`. Its future as a separate tool is open (A9). |
| testee | Installed by the home, not by an imperative `nix profile`. Gains task mode: it runs the standard tasks and reports exit 78 as "not set up". 22 repositories lose the input and the import. The 23 `testee.*` blocks become wired standard tasks. The devenv module retires. |
| gitman | Installed by the home. The 62 `gitman.toml` files and the `.gitman/` leftovers go. `docs/USING_GITMAN.md` stops offering a per-repository pin. |
| linkman | Installed by the home. Its broken lock is fixed: a new mancore tag, or mancore's current `main`. |
| mancore | Cut a release; tag v0.1.0 is 18 commits behind `main`. Becomes the written command contract (rule 6). |
| copyroom | Installed by the home. Delete the Copier remnants. |
| agentman | Daemon in the home, database on the machine. |
| docman | Remove the remaining references, for example in the repoman skill table. |

### The central overlay

- Rewrite the 62 imports of `/run/current-system/sw/share/devman/link-module.nix` to the pointer
  file. All 62 files live in one repository, so this is one commit.
- Keep only personal Testee setup (hooks that need sibling checkouts), if any.
- Keep one canonical copy of each skill.
- Remove or archive the 13 overlay directories with no repository.
- Remove the `repoman` input from `~/.config/devman/devenv.yaml`.

### The templates

The templates write today's pins into each new repository. Change them first, so no new repository
starts stale.

- **template-py:** remove the `repoman` and `testee` inputs and imports from the `devenv.yaml`
  template; remove `repoman.enable` and the `testee.*` block from the `devenv.nix` template; write
  the five standard tasks as placeholders and chain `base:check` and `base:test` to them; remove the `.repoman/project.toml` template;
  remove `managers`, `repoman_ref`, and `testee_ref` from the nine `schema.py` files; cut the
  personal tool workflow from the static `AGENTS.md`; regenerate the goldens.
- **template-nix:** remove the absolute-path `repoman` input (`repoman_dev_root`), the `devman`
  input, `repoman.enable`, and the `devman = {}` block; remove the matching answers from the nine
  `schema.py` files and nine scenarios.

### The fleet

For each repository, in one change per repository:

- Remove the personal-tool inputs and imports from `devenv.yaml`, and update `devenv.lock`.
- Remove `repoman.enable` from `devenv.nix`.
- Convert the `testee.*` block into wired standard tasks; chain `base:check` and `base:test` to
  them.
- Delete `gitman.toml`, `.repoman/project.toml`, and template answers that record tool tags.

[FLEET-INVENTORY](evidence/FLEET-INVENTORY.md) names the repositories for each item. These
repositories need manual attention: mnemonix (its overlay depends on its own devman import),
nix-systems and vendomat-demo (managed by `vendomat sync`), mancore (pins Vendomat with nested
tool pins), devman (a real `mancore` dependency), pydantree, talkee, and llama-infernal.

## Migration order

Each phase leaves the estate working. A later phase does not start until the fleet doctor (or,
before it exists, the phase's own check) is green.

1. **Stop new staleness.** Change template-py and template-nix. Fix the docs that teach the
   retired routes.
2. **Clean without behaviour change.** Remove the dead nix-meta inputs and files, the nix-terminal
   pins, nix-meta-channel4, and nixvim. Before this phase, inspect nix-meta's 23 `.worktrees` and
   its 1 Gitman workspace for work that `main` lacks.
3. **Make modules portable.** Add `lib/inventory.nix`. Remove hardcoded user facts from mnemonix,
   nix-paseo, and nixos-core. Replace the reads across the halves with constants.
4. **Stand up the home.** Add devman's Home Manager module, the layer directory, and the pointer
   file. Add
   `homeConfigurations."andrew@server"`, and remove the Home Manager NixOS module in the same
   change. Keep `/run/current-system/sw/share/devman/link-module.nix` until phase 5 ends.
5. **Move the import path.** This phase starts only after W10 proves the pointer file (owner
   rulings R11 and R12). Rewrite the 62 overlay imports. Check that every repository's shell
   loads the module through the pointer, and that the fleet doctor passes.
6. **Remove the fleet pins.** Release Testee's task mode, convert each repository's `testee.*`
   block into standard tasks, then remove the repository pins, one repository per change. The fleet doctor gates each change.
7. **Move the machine.** As nix-systems matures, move each machine module out of nix-meta, with its
   VM test. nix-meta's `nixosConfigurations` then ends.

## What gets worse

- **A change that spans both layers takes two steps,** machine first. Today one rebuild does both.
- **A new machine needs two activations:** `vendomat apply`, then `home-manager switch`.
- **A breaking tool release reaches every repository at once.** Today breakage arrives one
  repository at a time, and some repositories never show it. The fleet doctor and the home rollback
  make the new behaviour safer, but only if the owner runs the doctor.
- **Testee gives one verdict per base task,** not one per tool.
- **devenv's evaluation cache stays a hazard.** Any import that ends in a symlink goes untracked.
  The pointer file, the doctor check, and the pin fixture must hold together.

## Open questions

A1 to A4 are ruled (R8 to R12), project 21 answered A7 (R33, R35, R36), and R13 and R14 settle the
platform's layer and the pointer path. Every remaining question is in
[OPEN-ITEMS.md](OPEN-ITEMS.md), with its options and a recommendation.

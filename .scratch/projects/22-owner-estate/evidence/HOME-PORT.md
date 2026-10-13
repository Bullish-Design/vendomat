<!-- Provenance: written by a read-only Sonnet subagent on 2026-10-13, saved by the orchestrator. The subagent read files, ran `--version`, and grepped. It built nothing, evaluated nothing, and changed no file. Unverified items are listed in "Unproved" at the end. Repos read: devman (/home/andrew/Documents/Projects/devman), nix-meta (/home/andrew/Documents/Projects/nix-meta), vendomat at d5a90f0 (read with `git show`), mnemonix, inferference. -->

# Home port: what moves from NixOS to standalone Home Manager — 2026-10-13

Notation: DM = devman checkout. NM = nix-meta. HM = Home Manager. Observation = read in a file or printed by a command. Inference = reasoning, labeled "Inference". Unproved = no command ran it.

## Summary

1. devman has no `homeManagerModules` output. Its module is NixOS-only (observation).
2. The vendomat machine module has 0 live readers (observation). Drop it, or move it at no cost.
3. The 64 central `devenv.local.nix` files import one system path. That path is the main migration cost.
4. One true eval-time cross-read exists: NM `profiles/mnemonix.nix` reads NixOS options inside its HM block.
5. The deployed system is older than the lock. It runs devman 0.6.0. The lock pins v0.7.0.

## 1. devman module

### Outputs (observation)

`DM/flake.nix` exports `nixosModules.default` and `nixosModules.devman-dagu`. Both are `./nix/nixos-module.nix`. It also exports `overlays.default` and `packages.{dagu,devman,default,devman-link}`. No `homeManagerModules` output exists. The module imports no other module. It calls `dagu.nix`, `devman-cli.nix` and `link-adapter.nix` with the importing machine's `pkgs`.

### Options (observation)

Namespace `services.devman-dagu`, `DM/nix/nixos-module.nix:368-650`.

- `enable`, `package`, `installClient`, `installCli`, `installLinkAdapter` (368-420)
- `watch.enable`, `watch.package`, `watch.watchexecArgs` (421-460)
- `dagHome` (default `%h/.local/share/dagu`, 463), `registryDir` (469), `stateDir` (482), `reloadMaxWaitSec` (494)
- `host` (516), `port` (533), `coordinatorPort` (539)
- `queues` (545): light 4, normal 2, heavy 1, gpu 1, exclusive 1, llm 2. `defaultQueue` (597), `histRetentionDays` (611)
- `servicePath` (617), `lingerUsers` (638)

### Effects and class

| Effect | Where | Class |
|---|---|---|
| `users.users.<u>.linger = true` | `nixos-module.nix:695` | system-only |
| `environment.pathsToLink = /share/devman` | `:706` | system-only |
| `environment.systemPackages` (dagu, devman wrapper, devman-link) | `:697` | either. In HM it becomes `home.packages`. |
| `assertions` (loopback host, `defaultQueue` in `queues`) | `:658` | either |
| `warnings` (empty `lingerUsers`) | `:688-693` | either. Drop it in HM. |
| `systemd.user.services.dagu` | `:710` | user-level, in NixOS option shape |
| `systemd.user.paths.devman-dagu-reload` and `services.devman-dagu-reload` | `:784-800` | user-level, in NixOS option shape |
| `systemd.user.services.devman-watch` | `:808` | user-level, in NixOS option shape |
| `config.yaml` and `base.yaml` written by `installConfig` (ExecStartPre of `dagu`) | `:96-110` | user-level |
| `UnsetEnvironment = SHELL` on the dagu unit | `:751` | user-level |
| `restartTriggers` (configFile, baseFile, cli) | `:775`, `:858` | NixOS-specific |
| `share/devman/link-module.nix` | `DM/nix/link-adapter.nix:67` | user-level file at a system path |

Environment variables: the module sets only `DAGU_HOME` on the units (`:733`, `:794`). The CLI sets `DEVMAN_*` at trigger time. The module does not.

### What a homeModule needs (inference)

1. Split `nixos-module.nix` into a shared options file and a neutral unit description.
2. Write two translators: one for the NixOS unit shape, one for the HM `Unit/Service/Install` shape.
3. Set `Environment=PATH` explicitly in the HM units. NixOS adds coreutils, findutils, grep, sed and systemd to a unit `path`. HM does not.
4. Change `servicePath` defaults. Drop `/etc/profiles/per-user/%u`. Keep `%h/.nix-profile` and `/run/current-system/sw`.
5. Replace `restartTriggers` with HM's `X-Restart-Triggers` and sd-switch.
6. Keep `linger` machine-side. It stays in NM `machines/server.nix:528`.
7. Write the link module to a user path with `home.file` or `xdg.dataFile`.
8. Keep `nixosModules.default` for other machines.

### How nix-meta configures it (observation)

`NM/profiles/devman.nix:17-52` imports `inputs.devman.nixosModules.default`. It sets `enable = true`, `lingerUsers = [ username ]`, and `registryDir = "$HOME/.local/state/vendomat/devman/active"`. Everything else is default. NM pins devman at `v0.7.0` (`NM/flake.nix`, input `devman`). `NM/profiles/terminal.nix:90` sets `devman.enable = false` for the old nix-terminal devman.

### Version skew (observation)

The deployed system runs devman 0.6.0, devman-link 0.6.0 and dagu 2.15.0. The lock pins v0.7.0. The devman checkout has tag v0.8.0. Active generation 4 reports `devman_runtime` v0.6.0.

## 2. vendomat module

### What it does (observation)

NM pins vendomat at d5a90f0 (`NM/flake.nix`, input `vendomat`). NM imports its `nixosModules.default` at `NM/machines/server.nix:71`. Source: `git show d5a90f0:flake.nix`.

- One option exists: `vendomat.installConsumerModule`, default true.
- The module adds the wrapped `vendomat` package to `environment.systemPackages`.
- The module adds `/share/vendomat` to `environment.pathsToLink`.
- The wrapper sets `VENDOMAT_DEVMAN_PLANE_MANIFEST`. The manifest names the devman runtime, renderer, dagu and toolchain closures.
- The package installs `share/vendomat/consumer-module.nix` (a copy of `modules/devenv.nix`) and `share/vendomat/machine.json`.
- `machine.json` holds `cli`, `toolchain`, `vendor_root` and `wheelhouse`. `cli` is the fixed string `/run/current-system/sw/bin/vendomat`.
- `modules/devenv.nix:47` reads `/run/current-system/sw/share/vendomat/machine.json`.
- The vendomat flake pins its own devman at v0.5.2.

Both files exist on the machine today. They point into vendomat 0.5.0.

### The 0-reader finding (observation)

- A grep of `~/.config/devman/projects` (73 project directories) for `share/vendomat` found 0 files.
- A grep of every `Projects/*/devenv.nix` and `devenv.yaml` found 0 imports.
- The only mention is the comment at `NM/machines/server.nix:66-71`.
- nix-systems and vendomat-demo use `vendomat sync`. It writes `.vendomat/devenv.yaml` from flake inputs. Neither reads `machine.json`.

Inference: the consumer-module delivery is unused. Drop it or move it. Neither costs a repository anything.

Inference: the `vendomat` CLI must move to HM. Generation activation under `~/.local/state/vendomat/devman` is user-level work.

## 3. Port table

| Item | Today | Target half | Replacement interface | Risk |
|---|---|---|---|---|
| devman service, CLI, watcher | `NM/profiles/devman.nix:17-52` | home (units, packages). Machine keeps linger. | New `homeManagerModules.default` from shared options | PATH and unit-shape rewrite. A same-name unit in `~/.config/systemd/user` shadows `/etc/systemd/user`. Overlap would collide on ports 8080 and 50055. Restart instead of overlap. |
| linger for andrew | `NM/machines/server.nix:528`, `devman.lingerUsers` | machine | none | low |
| link module and `devman-link` | system profile, `DM/nix/nixos-module.nix:697,706` | home | file at a user path; store path baked into `enterShell` | High. See section 6. |
| vendomat CLI | `NM/machines/server.nix:71` | home | `home.packages` | low |
| vendomat consumer module and `machine.json` | `NM/machines/server.nix:66-71` | drop | none (0 readers) | low |
| agentman user socket and service | `NM/profiles/developer.nix:184-211` | home | store path of toolchain, constants | Peer auth needs both halves to agree. |
| agentman Postgres role and identMap | `NM/machines/server.nix:419-439` | machine | shared constants file (role, db, socket dir, user) and a flake check that compares them | medium |
| devenv, gitman, jj, gh, uv, nodejs, python3 | `NM/profiles/developer.nix:34-49` | home | `home.packages` | low |
| toolchain PATH append | `NM/profiles/developer.nix:178-180` (`home.sessionVariablesExtra`) | home | HM sources `hm-session-vars` in `.zshenv` | Login and interactive shells only. Same as today. |
| `nix.settings` substituters | `NM/profiles/developer.nix:131-136` | machine (keep) | none | `/etc/nix/nix.conf` holds them now. andrew is in `trusted-users`. HM `nix.settings` would need `nix.package`. |
| nixbuild and repoman HM modules | `NM/profiles/developer.nix:147-148,219-238` | home | existing nix-terminal HM modules | low |
| claude-code, codex-cli, zellij | `NM/profiles/agent.nix:39-46` (`environment.systemPackages`) | home | `home.packages` | low |
| `DISABLE_AUTOUPDATER` | `NM/profiles/agent.nix:51` (`environment.variables`) | home | `home.sessionVariables` | low |
| `/run/secrets` reads | `NM/profiles/agent.nix:89-95,171` | home reads, machine owns | path constants. Machine keeps `owner = andrew`, mode 0400 (`NM/profiles/secrets.nix`). | A renamed secret fails silently at run time. |
| atuin socket path | `NM/profiles/terminal.nix:21-23` (`config.users.users.<u>.uid or 1000`) | home | constant 1000. Machine sets `users.users.andrew.uid = 1000` explicitly. | `id -u` prints 1000. The NixOS option is null today. |
| atuin client and daemon | `NM/profiles/terminal.nix:196-204` | home | shared package helper `NM/nix/atuin-18.23.0.nix` | low |
| atuin sync server | `NM/machines/server.nix:315-334` | machine | same package helper (`server.nix:9`) | `checks.atuin-server-runtime` reads `config.home-manager.users.andrew…`. It must read `homeConfigurations."andrew@server"`. |
| mnemonix HM config | `NM/profiles/mnemonix.nix:50-67`, reads `config.services.mnemonix.hindsight` at `:12,60-64` | home | shared constants (ports 8891 and 9991, `projectsRoot`, `memprojectsFile`). Derive `apiUrl` in HM. Add an equality check. | The only true eval-time cross-read. |
| mnemonix container and `/etc/claude-code/managed-settings.d/mnemonix.json` | `mnemonix/modules/hindsight.nix:647,735` | machine | none | Both halves should build one `codingAgents` derivation. |
| inferference-router user unit | `NM/machines/server.nix:117-131`, module `inferference/nix/nixos-module.nix:103` | machine (keep) | none | The unit reads `/run/arctic-fan/status` and a system unit. The module has NixOS options only. |
| root ssh fetch workaround | `NM/machines/server.nix:545-564` | machine (keep) | none | `/etc/ssh` is global, so andrew's `home-manager switch` also uses it. Root still evaluates the flake. |
| HM bootstrap | `NM/profiles/developer.nix:29`, `terminal.nix:35`, `agent.nix:30`, `machines/server.nix:30` | home | one `homeConfigurations."andrew@server"` output with a module list | `useGlobalPkgs` ends. Standalone `pkgs` needs the same overlays and `allowUnfree`. `backupFileExtension` becomes `switch -b hm-backup`. |

Inference: profile order matters after the split. Today four profiles merge into one `home-manager.users.andrew` value. The standalone output must list the four modules.

## 4. Where each family binary comes from today

Observation. Versions come from `<bin> --version`, from store path names, or from `toolchain.json`.

| Binary | Source today | Version |
|---|---|---|
| devman | `/run/current-system/sw/bin` | 0.6.0 |
| devman-link | `/run/current-system/sw/bin` | 0.6.0 |
| dagu | `/run/current-system/sw/bin` | 2.15.0 |
| vendomat | `/run/current-system/sw/bin` | 0.5.0 |
| claude | `/run/current-system/sw/bin` | 2.1.291 |
| codex | `/run/current-system/sw/bin` | 0.160.1 |
| gitman | `/etc/profiles/per-user/andrew/bin` | 0.13.1 (store name) |
| jj | `/etc/profiles/per-user/andrew/bin` | 0.46.0 |
| devenv | `/etc/profiles/per-user/andrew/bin` | 2.4.0 |
| pi | `/etc/profiles/per-user/andrew/bin` | 1.0.4 |
| atuin, atuout, pytuin | `/etc/profiles/per-user/andrew/bin` | atuin 18.23.0 (per lock), atuout 0.2.0, pytuin 0.2.0 |
| gh, uv | `/etc/profiles/per-user/andrew/bin` | 2.96.0, 0.11.25 |
| repoman | toolchain, appended by `hm-session-vars.sh` line 16 | 0.10.0 |
| copyroom | toolchain | 0.8.6 |
| docman | toolchain | 0.2.1 |
| templateer | toolchain | 0.6.0 |
| agentman | toolchain | 0.0.3 |
| pyjutsu | toolchain | 0.23.0 |
| gitman (toolchain copy) | toolchain, shadowed by per-user gitman | 0.9.1 |
| linkman | devman devenv venv only | broken: `ModuleNotFoundError: click` |
| mancore | not on PATH | not run |

Other observations:

- The toolchain store path is `/nix/store/1s165d7ira2kgi61x5amyv6wm4cza5c3-repoman-toolchain-core`. It matches `machine.json`.
- The toolchain is not in `/run/current-system/sw/bin`, `/etc/profiles/per-user/andrew/bin` or `~/.nix-profile/bin`. `type -a repoman` finds nothing in a non-login shell.
- `~/.nix-profile` holds only `act` and `testee` 0.6.1.
- PATH order is `~/.nix-profile/bin`, `/etc/profiles/per-user/andrew/bin`, `/run/current-system/sw/bin`.
- `devman` appears in the system profile and in the devman venv. Inference: remove it from the system profile after the port. Two copies resolved by profile order is the hazard `DM/nix/nixos-module.nix:384-398` describes.

## 5. Contract paths and migration

Counts come from `grep` over `~/.config/devman/projects` and `git grep` over each repository, excluding `*.md`, `.scratch`, `docs` and `tests`.

| Path | Dependents | Migration (inference) |
|---|---|---|
| `/run/current-system/sw/share/devman/link-module.nix` | 64 central `devenv.local.nix` files under `~/.config/devman/projects`. 1 error string at `DM/src/devman_link/reconcile.py:46`. 1 option description at `nixos-module.nix:405`. | 1. HM writes the module to a user path. 2. One commit in the central overlay repository rewrites the 64 imports. 3. The old machine file stays until that commit lands. A shim at the old path that imports the user path is the fallback. |
| `/run/current-system/sw/bin/devman-link` | `DM/modules/link.nix:71`, run at shell entry of those 64 repositories | Bake the store path into the new module. The old module keeps working while the machine profile keeps the binary. |
| `/run/current-system/sw/share/vendomat/{consumer-module.nix,machine.json}` | 0 live readers | Delete with the NixOS module. |
| `/etc/profiles/per-user/<user>/bin` (PATH augment) | 6 repositories: devenv-py (3 files), devman (1), fornix (1), pydantree (1), structured-agents-v2 (1), vendomat (1) | Change to `$HOME/.nix-profile/bin`. 8 repositories already name `.nix-profile`. |
| `/run/current-system/sw/bin` (PATH augment) | 11 repositories, about 56 files: structured-agents-v2 30, nixvim 13, fornix 4, devenv-py 2, vendomat 2, six others 1 each | No change. The system profile keeps base tools. Only moved user tools are affected. |
| `/run/secrets/*` | nix-meta 3 files, nix-secrets 3, mnemonix 1 | Keep the machine side. Treat the names as constants. |
| `~/.local/state/vendomat/devman/active` | Dagu `registryDir` and the reload path unit | No change. |
| `~/.local/share/devman/` (compat registry) | devman `registryDir` default. Holds `dags`, `projects`, `watch`. | Do not place HM-written files here. Inference: `devman doctor --prune` may delete unknown entries. Use a separate root. |
| `/run/current-system/sw/share/repoman/module` | `repoman/flake.nix:82` mentions it | No current consumer found. Ignore. |

The 64 files are central overlay content. The boundary test in `DM/CLAUDE.md` puts a per-user absolute path in them. Inference: `/home/andrew/...` is acceptable there.

## Unproved

No command built or evaluated any of the following.

1. HM `nix.settings` with a null or unset `nix.package` on this machine. Not tried.
2. Where standalone HM puts packages. Inference: it manages a `home-manager-path` entry in the existing `~/.nix-profile` (manifest v3). Not run.
3. Whether a same-name unit in `~/.config/systemd/user` shadows `/etc/systemd/user` cleanly. Not run.
4. Whether `devman doctor --prune` deletes unknown files in `~/.local/share/devman`. Not read from source.
5. Whether `home-manager switch` over SSH has `XDG_RUNTIME_DIR` for the user-unit reload. Not run.
6. Whether root still fetches HM-only private inputs when the NixOS and HM outputs share one flake. Not measured.
7. Whether mnemonix's NixOS and HM halves resolve to one `codingAgents` store path. Not compared.
8. Whether the HM atuin module sets `systemd_socket` on a non-NixOS host. Not read.
9. Dependent counts for `/run/current-system/sw/bin` and `/etc/profiles/per-user` come from `git grep` of tracked files. Untracked and generated files are not counted. I did not open each file to confirm it is PATH augmentation.
10. `devman doctor` was not run. The live plane's health is not checked.
11. The `linkman` failure (`click` missing) comes from one run in the devman venv. I did not diagnose the cause.

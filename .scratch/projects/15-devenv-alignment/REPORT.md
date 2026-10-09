# devenv alignment review of Vendomat V5

**Follow-up:** [FOLLOWUP-2026-10-09.md](./FOLLOWUP-2026-10-09.md) records the owner's answers and
VM-proven results that replace several unverified claims below (U1 to U6).

**Date:** 2026-10-09. **Status:** Research report. It changes no requirement. Section 3 proposes
successor IDs for the owner to accept or reject. **Authority reviewed:** `.scratch/projects/14-vendomat-local/`
(CONCEPT-V5, SPEC-V5, GUIDE-V5, REFINEMENT-2026-10-08, `prelim-verification/DECISIONS.md` and
`RESULTS.md`).

## Versions under review

| Item | Value | How known |
| --- | --- | --- |
| devenv command line | `devenv 2.4.0+b904dcb (x86_64-linux)` | `devenv version` |
| `v2.4.0` tag | `b904dcb51fe48c30db250038241507f60752f222` | `git rev-parse 'v2.4.0^{commit}'` in a clone of `cachix/devenv` |
| devenv modules in `vendomat/devenv.lock` | `fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4`, `dir=src/modules`, lastModified 2026-09-29 | `devenv.lock` node `devenv` |
| Distance | `b904dcb` is an ancestor of `fe20b5c`, 17 commits behind. The 17 commits touch none of: `machines.nix`, `machines.rs`, `config.rs`, `bootstrapLib.nix`, `outputs.nix`, `profiles.nix`, `cachix.nix`, the lock code, `flake.nix` | `git merge-base --is-ancestor`; `git diff --stat b904dcb fe20b5c` |
| `nix-meta` flake input `devenv` | `github:cachix/devenv/v2.4.0`, locked to `b904dcb` | `nix-meta/flake.nix:37`, `flake.lock` |
| Other repositories | six different devenv module revisions across eight `devenv.lock` files (`fe20b5c`, `190959a`, `a73c5b8`, `d1fb321`, `9d93b83`); all use `github:cachix/devenv-nixpkgs/rolling` | `devenv.lock` in vendomat, nix-meta, repoman, linkman, devman, gitman, loci-core, nix-paseo |

All source citations below are at `fe20b5c` and hold for `b904dcb`, except where marked.

## Method

Four background agents ran in parallel. Their final reports are the raw evidence. They are in
[`raw/`](./raw/), extracted unedited from the agent transcripts. Agent D ran twice; both reports are
in one file.

- **A:** devenv.sh documentation, `devenv … --help`, `gh release view` for 2.0 to 2.4.0.
- **B:** `gh` against `cachix/devenv`: open pull requests, issues, milestones. NixOS Discourse thread 80271.
- **C:** the V5 documents, `src/vendomat/`, and `nix-meta` (read only).
- **D:** a clone of `cachix/devenv` at `fe20b5c`, plus three disposable fixtures under `/tmp`.

Fixture commands run by D, all in `mktemp -d` directories, all removed afterwards:

| Fixture | Command | Result |
| --- | --- | --- |
| F1 | `devenv machines info` with `machines.web` (NixOS, `target.host = "root@web.invalid"`) and `machines.me` (Home Manager, no target) | Table printed both machines. No host contacted |
| F1 | `devenv build machines.web.build.nixos` with no `disko` input | Failed at evaluation: "To use 'machines.<name>.nixos', run the following command: $ devenv inputs add disko github:nix-community/disko --follows nixpkgs" |
| F2 | `path:` input `shared` (`flake: false`) with `devenv.nix` setting `env.FROM_SHARED` and a `devenv.yaml` declaring `extra-from-shared`; `imports: [shared]`; `devenv shell -- printenv FROM_SHARED` | Printed `yes`. `devenv.lock` root inputs: `devenv`, `nixpkgs`, `shared`. `extra-from-shared` was not merged |
| F3 | `devenv.yaml` input `devman: { url: "git://server/devman?ref=refs/tags/v0.7.0", flake: false }`; `devenv update devman` | Exit 0. Lock node: `type: git`, `url: git://server/devman`, `ref: refs/tags/v0.7.0`, `rev: 4c9927ada27a5c12a5ee2acdf8ad85648f7aafa1`, `narHash: sha256-pKf7QG4dLxfqakacpc9Yzbuo+rFY0ZcEhQoTgv4/jts=`. This read from the live collection daemon on `server` |

No agent ran `devenv machines apply`, `deploy`, `install`, or `rollback`. No agent ran a command as
root or touched a disk.

**Observation and inference.** In the tables, a cited file, line, page, or command result is an
observation. Text marked *Inference* is my reading. An upstream fact is evidence about devenv. It
passes no Vendomat requirement.

---

# 1. Verdict

V5 is aligned with devenv in the parts it has built, and it is not aligned in the parts it has only
specified. The built parts — the registry, the flake generator, the source collection, and `vendomat path`
— have no devenv equivalent, and devenv reads the `git://` collection without change (F3). Lock
ownership is also aligned in substance: `devenv.lock` is a Nix lock file written by Nix's own locker,
so "Nix owns the lock" holds for both files. The unbuilt machine parts overlap devenv 2.4: Machines
already gives a reviewed plan, a confirmed deploy, a watchdog rollback, and a status record. These
cover `apply` and `rollback` in `systemcfg`, and disko covers most of `fromInventory`. But Machines
is experimental, it activates NixOS only over root SSH (also for `localhost`), and its `install`
formats disks with no prompt and no local-disk mode. So it cannot do Step 7, and it conflicts with
`DISK-002` and `DISK-003` unless a Vendomat preflight runs first. **The largest gap is the workspace
layer.** V5 does not say how a workspace opens on the core. Its one stated route, a shell defined in
`flake-outputs.nix` through `devenv.lib.mkShell` (`GEN-022`), is devenv's reduced flake mode: no
SecretSpec, no dotenv, no evaluation cache, an impure root, and a four-command shim. A devenv-native
workspace avoids that, but then has a second lock beside `flake.lock`. devenv already has every piece
for a workspace layer (direnv, `devenv hook`, profiles, `devenv.local.*`, input imports). V5 needs a
short convention, not code.

---

# 2. Alignment table

Verdicts: **aligned**, **duplicates**, **conflicts**, **unused opportunity**, **planned-change risk**.
Evidence keys (`E1` …) refer to [Appendix B](#appendix-b-evidence). "Spec only" means V5 specifies the
piece and no code exists (Agent C: `rg` over `~/Documents/Projects` found no definition of `mkModules`,
`fromToml`, `fromInventory`, `vendomat.paths`, or `systemcfg`).

| # | Area | devenv feature | V5 today | Verdict | Recommended action | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Machine activation | Machines `plan`, `apply <plan>`, `deploy` (confirms unless `--yes`), `status`, `rollback`; transactional with a watchdog timer and a boot recovery unit. 2.4.0, experimental. [machines](https://devenv.sh/machines/) | `CLI-010` to `CLI-015`, Step 9 (spec only) | duplicates (planned V5 code); planned-change risk | Do not build `apply` or `rollback` beyond a thin `nixos-rebuild` call now. Reassess when Machines is stable or #3226 lands. Owner decision D2 | E2, E7, E8, E10 |
| 2 | Local activation | NixOS and nix-darwin need `target.host`. `localhost` "still routes through SSH" and needs root SSH. Only Home Manager activates in process | `CLI-011` drives `nixos-rebuild switch` on the host | conflicts (if adopted on `server`) | Keep `nixos-rebuild` for `server`. Do not open root SSH to itself | E10 |
| 3 | Machine install | `install`: kexec, facter, disko, install, reboot, over root SSH to a remote host. No prompt, no `--yes`, no dry run, no resume, no local block device | `DISK-002`, `DISK-003`, `BOOT-018`, `BOOT-021` to `BOOT-024`, Step 7 | conflicts | Never run `devenv machines install` against `server`. Keep the reviewed `nixos-install` route for Step 7 | E5, E6 |
| 4 | Laptop install | Same `install`. The controller copies the closure with `nix copy --to ssh://`. The target needs no substituter and no cache credential | `BOOT-019`, `CACHE-007`, PV-09 (installer credential, open), Step 10 | unused opportunity | Test `machines install` from `server` to a disposable VM. If it passes, Step 10 no longer needs the installer cache route | E5, E9 |
| 5 | Closure transfer | `nix_copy` runs `nix copy --to ssh://…`; no `--substitute-on-destination` | `NAT-009` (cited "upstream documentation") | aligned (fact holds) | Replace the citation with source lines: `NAT-019` | E9 |
| 6 | Disk layout | disko is a required input for every NixOS machine; layout selects disks by `/dev/disk/by-id/`; `--disko-mode format\|mount` | `fromInventory`, `DISK-004`, `DISK-005` (spec only) | unused opportunity; reducible | Use disko for the 4 TB layout after the preflight passes. Keep `DISK-004` by overriding mounts to `by-uuid` (unverified, U5) | E4 |
| 7 | Hardware facts | nixos-facter report per host at `.machines/<name>/facter.json`; `null` opts out | Hand-written `hardware/*.nix`; `DISK-001` inventory | unused opportunity (partial) | Optional. A facter report records hardware. It does not guard a write | E3 |
| 8 | Cross-repository import | `imports: [<input>/<dir>]` loads `<dir>/devenv.nix` and `devenv.local.nix` from the input | `MOD-001` exports the devenv face as the flake attribute `devenvModules.default` | conflicts (shape) | Export the devenv face also as a directory that holds `devenv.nix`. Draft `MOD-011` | E12 |
| 9 | Imported `devenv.yaml` | Local imports merge `devenv.yaml`. Input imports ignore it (F2). #2205 open; PR #3055 would merge it | `NAT-006`; SPEC section 2 rationale | aligned; planned-change risk | Supersede `NAT-006` with `NAT-018`. Watch #3055 | E12, E13 |
| 10 | Multi-face modules | No convention. `machines.<n>.nixos` takes any module; `specialArgs = { inputs, self }` | `MOD-001` to `MOD-010` (spec only) | required (no equivalent) | Keep, but optional. PV-07 found 1 of 18 providers with all three faces | E11, CONCEPT:447 |
| 11 | `extra` escape | No devenv-to-systemd bridge; services are processes only | `MOD-006`, `MOD-008` | aligned | Keep `extra` | E23 |
| 12 | Build outputs | `outputs.<name>`; `devenv build` returns JSON; `inputs.<x>.devenv.config.outputs.<y>` for another devenv project. 2.0 | `INP-003` (`packages.<system>.<name>`) | aligned (different consumers) | Keep flake `packages` for repositories that NixOS consumes. A workspace may use `outputs` | E16 |
| 13 | Workspace opening | direnv `use devenv`; `devenv hook` plus `devenv allow` (2.1); profiles with `hostname` and `user` auto-selection (1.9); `devenv.local.nix` and `devenv.local.yaml`; input imports; tasks before `devenv:enterShell`; `require_version` (2.1) | No requirement. Section 14 excludes "a workspace orchestrator" | unused opportunity (**largest gap**) | Add the `WS-*` convention in section 3. No Vendomat code | E17, E18, E25 |
| 14 | Project shell through a flake | `lib.mkShell` and `flakeModules.default`: impure `devenv.root`, CLI shim with `up`, `test`, `tasks`, `version` only, SecretSpec and dotenv assert off, no evaluation cache, no native process manager (#2610 open) | `GEN-022` lets the project define its shell in `flake-outputs.nix` | conflicts | Supersede `GEN-022` with `GEN-023`: a shell uses devenv's own files | E19 |
| 15 | Lock ownership | `devenv.lock` is the Nix lock format (version 7), written by Nix's `InputsLocker` through the C API. devenv never reads a project `flake.lock` | `GEN-008`; "Nix owns `flake.lock`" | aligned in substance; duplicates when a project has both files | `WS-004`: one shared personal input has one tag across both files | E20 |
| 16 | Input declaration | `devenv inputs add <name> <url> --follows <input>`; `devenv update [name]` | `vendomat sync`, `REG-011`, `GEN-015` to `GEN-021` | reducible for devenv-native workspaces; required for flake-backed authors | Generator stays for flake authors. A workspace writes `devenv.yaml` directly. Check tag pins with a lint (`WS-003`) | E14 |
| 17 | `git://` inputs | Not in the documented list. Parsed by Nix's flake-reference parser. Works (F3) | `STORE-008`, `REG-016` | aligned | Record as `NAT-020` | E14, E15 |
| 18 | Collection offline | PR #3244 (open): `devenv shell` fails when a locked input's remote is unreachable, even when the store holds it | `NAT-015` (Nix only) | planned-change risk | Test a devenv shell with the daemon stopped (U3). Until #3244 ships, a devenv workspace may need `server` up | E26 |
| 19 | Binary cache | `cachix.pull` (effective default `["devenv"]`) maps names to `https://<name>.cachix.org` only. No generic substituter option. No Attic (#1539 open). An untrusted user's request is dropped silently (#3175 open) | `CACHE-001`, `BOOT-002`: Attic in `nix.settings` on the host | aligned | Keep Attic in the NixOS daemon settings. devenv then substitutes from it without any devenv option | E22 |
| 20 | `devenv-nixpkgs` | Default nixpkgs `github:cachix/devenv-nixpkgs/rolling`. Machines rebuilds `nixosSystem` from its `nixpkgs-src` input | `[passthrough] nixpkgs`; `nix-meta` system nixpkgs is `nixos-unstable` | aligned; risk only if Machines is adopted | If Machines is adopted, set the machine nixpkgs to the same `nixos-unstable` revision as `nix-meta` | E11 |
| 21 | Named paths | None | `PATH-001` to `PATH-004` (spec only) | required | Keep. Export `VENDOMAT_PATH_*` from NixOS or Home Manager session variables, so a devenv shell inherits them | E34 |
| 22 | Drive identity | None. disko docs advise `by-id`. No model, serial, size, or signature check | `DISK-001` to `DISK-007` | required | Keep the preflight. It must run before any disko or install command | E5, E6 |
| 23 | Secrets | SecretSpec 0.21 crate in the shell (providers include SOPS); Machines `install.secrets`, `install.extraFiles`, `install.encryptionKeys` write once at install; no deploy-time secrets (#3232 open); no sops-nix integration | `CACHE-002`; PV-09 open choice 2 | unused opportunity | If D2 picks Machines for `framework`, deliver the Attic pull credential with `install.secrets`. Runtime secrets stay in NixOS modules | E21 |
| 24 | Services | 45 service modules, all devenv processes under `$DEVENV_RUNTIME`; native process manager default | `server.nix`: Paseo, SilverBullet, Postgres, Atuin, atticd, git daemon are NixOS units | aligned | Apply the rule in Appendix A, Q6 | E23 |
| 25 | Testing | `devenv test` runs `devenv:enterTest` tasks (git hooks), builds `test`, starts processes, runs `enterTest` | Testee gate in `AGENTS.md`; no SPEC ID | aligned; unused opportunity | Keep Testee as the authority. Optional: `enterTest = "testee verify --mode quick"`, so `devenv test` is the same gate | E24 |
| 26 | Command-line pin | `require_version` in `devenv.yaml` (2.1) | GUIDE "Fleet and pins" names 2.4.0 | unused opportunity | Add `require_version` to Vendomat's `devenv.yaml` (syntax unverified, U9) | E25 |
| 27 | Machines from a flake | #3226 (open): accept a composed `nixosConfigurations.*`. Maintainer suggests `nixos = inputs.<x>.nixosModules.<y>` | `nix-meta` builds `nixosConfigurations.server` with `mkMachine` | planned-change risk | Expose each host as `nixosModules.<host>` in `nix-meta`. Then both `nixos-rebuild` and Machines can consume it | E28 |
| 28 | devenv 3 | `TODO(v3.0)` removes camelCase `devenv.yaml` aliases (`config.rs:310,337,2741`). 2.0 blog: "0.x … dropped in devenv 3". No date | Vendomat `devenv.yaml` uses none of the aliases | planned-change risk (low) | None now | E29 |

---

# 3. Requirement IDs to supersede, and new IDs

Every ID below is new. No existing ID is edited or reused. Each proposal is **proposed** until a
fixture proves it on the pinned tools.

## 3.1 Supersede

| Old ID | Problem | Successor | Draft successor wording | Duplicates of the claim to update |
| --- | --- | --- | --- | --- |
| `NAT-006` | "devenv merges an imported `devenv.yaml` only for local paths inside the git root." Correct, but unsourced and incomplete. | `NAT-018` | devenv 2.4.0 merges `devenv.yaml` for local path imports only. The project file wins over imports, and `devenv.local.yaml` wins last. An import that names an input loads that input's `devenv.nix` and `devenv.local.nix` and ignores its `devenv.yaml`. Evidence: `config.rs:681-745`, `bootstrapLib.nix:120-163`, fixture F2. #2205 and PR #3055 are open. | SPEC section 2, second bullet: "The `devenv.yaml` route could not offer that". This holds for devenv-native inputs. It is unverified for flake-backed inputs declared in `devenv.yaml` (U1). |
| `NAT-009` | Cited "upstream documentation" only. | `NAT-019` | devenv 2.4.0 Machines copies each planned output to the target with `nix copy --to ssh://<host>`, without `--substitute-on-destination`. The target receives the controller's closure and does not fetch from its own substituters. Evidence: `machines.rs:508-521`, `machines.rs:3181-3205`. | SPEC:514 rationale. CONCEPT "Observed mechanisms" has no row for it. Add one. |
| `GEN-022` | Its second sentence sends a project shell into devenv's reduced flake mode. | `GEN-023` | The generator MUST NOT emit `devShells`, `devenv.lib.mkShell`, or a `devenv` input. A project that wants a development shell SHOULD use devenv's own files (`devenv.nix`, `devenv.yaml`, `devenv.lock`), not `devenv.lib.mkShell` in `flake-outputs.nix`. The flake mode has no SecretSpec, no dotenv, no evaluation cache, an impure root, and a reduced command set. Verify: `nix flake show` lists only the outputs the project file defines (PV-13 F2), and the shell enters with `devenv shell` and no `--impure`. | CONCEPT:384-387 ("A project that wants a development shell defines it here"); SPEC:191 comment (`lib.shell = nixpkgs.lib.evalModules …`); SPEC:533 acceptance A ("A project that wants a shell defines it in its own outputs file"). |

**Document correction, no ID.** CONCEPT "Observed mechanisms" says "devenv supports a flake-backed
consumer first-class". The devenv guide says the flake route has "performance limitations and
reduced features compared to the dedicated devenv CLI" (E19). Change the row to say the integration
exists and is reduced.

## 3.2 Conditional successors (only if the owner picks Machines in D2)

Keep `CLI-011` and `CLI-013` unchanged if D2 stays on option A.

| Old ID | Successor | Draft wording |
| --- | --- | --- |
| `CLI-011` | `CLI-017` | `apply` MUST activate through one native mechanism per host: `nixos-rebuild switch` on the local host, or `devenv machines deploy <host>` for a host declared under `machines`. It MUST report the exit status and name the stage. |
| `CLI-013` | `CLI-018` | `rollback` MUST restore the prior system with the same mechanism that activated it: the previous generation under `nixos-rebuild`, or the recorded previous system under `devenv machines rollback`. |
| `CLI-001` (already narrowed by `DEL-012`) | `CLI-019` | The surface MUST be `add`, `remove`, `sync`, `status`, `query`, `path`, `explore`, `set`, `get`, `unset`, `diff`. Activation and rollback belong to `nixos-rebuild` or `devenv machines`. |

## 3.3 New IDs (no supersession)

| New ID | Draft wording | Verify |
| --- | --- | --- |
| `NAT-020` | devenv 2.4.0 accepts a `git://` URL with `?ref=refs/tags/<tag>` as a `devenv.yaml` input and locks the tag and revision in `devenv.lock`. The scheme is not in devenv's documented list. | Fixture F3. Repeat with `flake: true` on a tagged flake in the collection. |
| `NAT-021` | devenv 2.4.0 does not read `devenv.yaml` in flake mode. Its flake shim supports only `up`, `test`, `tasks`, and `version`. SecretSpec and dotenv assert off. | `flake-compat.nix:35-80`, `secretspec.nix:55-61`, `dotenv.nix:157`. |
| `NAT-022` | devenv 2.4.0 `machines install` works only over root SSH to a target with `target.host`. It formats with no prompt and no dry run. It has no local block-device mode. NixOS deploy to `localhost` also uses SSH. | `machines.rs:1268,1275,1851`; `machines.md:133-135`; `machines.nix:263-264`. |
| `NAT-023` | devenv 2.4.0 `cachix.pull` adds only `https://<name>.cachix.org` substituters. Other substituters come from the Nix daemon settings or `--nix-option`. | `cachix.rs:190-207`. |
| `MOD-011` | An input that exports a devenv face MUST also place it in a directory that holds `devenv.nix`, so a consumer can name it in `devenv.yaml` `imports` as `<input>/<dir>`. | A consumer `devenv.yaml` with `imports: [knappy/modules/devenv]` enters a shell, and the face is inert until `enable`. |
| `DISK-008` | A disko layout MUST name its target by `/dev/disk/by-id/`. A disko command MUST run only after the `DISK-002` and `DISK-003` preflight passes for that identifier. Mounts generated from the layout MUST still satisfy `DISK-004`. | Evaluate `fileSystems` from the layout; no kernel name and no partition label appears as a device. |
| `BOOT-025` | `framework` MAY be installed with `devenv machines install` from `server`. Then the closure comes from `server`'s store by `nix copy`, and `CACHE-007` MUST be proven separately after first boot. | A disposable VM installs from `server` with the real layout; the install log shows no build on the target. |
| `WS-001` | A workspace is a devenv project: `devenv.nix`, `devenv.yaml`, and `devenv.lock`. It needs no `vendomat.toml` and no generated `flake.nix` unless another flake consumes its outputs. | `devenv shell` enters with Vendomat absent from `devenv.yaml`. |
| `WS-002` | A shared workspace base MUST be one tagged repository in the collection that exposes a directory holding `devenv.nix`. A workspace imports it with `inputs.<base>` (a `git://` tag) and `imports: [<base>/<dir>]`. Until devenv merges remote `devenv.yaml` (#3055), the workspace MUST declare every input the base needs. | Two workspaces import the base; each shell has the base's packages and scripts. |
| `WS-003` | Every personal input in a workspace `devenv.yaml` MUST pin a tag, by the same rule as `REG-017`. A lint task or git hook checks it. | A branch ref fails the check and names the input. |
| `WS-004` | A project that has both `flake.nix` and `devenv.yaml` MUST pin the same tag for a personal input that both declare. | The check compares both lock files and names any difference. |
| `WS-005` | Host-specific workspace settings MUST live in `profiles.hostname.<host>`. Personal, uncommitted settings MUST live in `devenv.local.nix` or `devenv.local.yaml`. | Enter the shell on two hosts; each gets its own profile values. |
| `WS-006` | A workspace MUST reach host values (`vendomat.paths`, Attic, the Vendomat command) through the host environment and `PATH`, never through a Vendomat input. | `DEL-010` fixture extended to read `VENDOMAT_PATH_NOTES`. |

---

# 4. Revised build order for the machine steps

**Removed by Machines** means devenv Machines would replace the step's own work if the owner adopts it.
**Changed** means the step stays and a devenv feature changes how it runs.

| Step | Work | Machines effect | Revised content |
| --- | --- | --- | --- |
| 0 | Drive identity preflight (PV-02) | **Kept.** Machines has no identity check (E6) | Unchanged. It now also gates any disko command (`DISK-008`) |
| 1 | Machine core | Kept | Write the core as a NixOS module. Export it as `nixosModules.core` from `nix-meta`, so `nixosConfigurations` and `machines.<n>.nixos` can both import it |
| 2 | Cache access inside the core | Kept | Attic stays in `nix.settings` (E22). Step 2.2, the installer route, is **removed for `framework`** if Step 10 uses Machines |
| 3 | Core in a VM | Kept | Unchanged. Add `devenv build machines.<n>.build.nixos` as a second evaluation check only if D2 picks B or C |
| 4 | `mkModules`, `fromToml`, `vendomat.paths` | Kept | Add `MOD-011` (devenv face as a directory). Build `mkModules` only when a second three-face provider exists (D4) |
| 5 | `nvim-core` split | No effect | Unchanged |
| 6 | Builder, `watch-store`, collection | No effect | Unchanged. 6.3 is done |
| 6a | **New:** workspace base | No effect | Create the `WS-002` base repository and convert one workspace. No Python |
| 7 | Install `server` on the 4 TB drive | **Not removable.** Machines install is remote-only, kexecs the target, and needs another controller, which breaks `BOOT-018` and `BOOT-022` (E5) | Keep `nixos-install --system` from the running system. **Changed:** partition with disko after the preflight (D5) |
| 8 | Registry and generator | No effect | Built. Scope narrows to flake-backed authors (`WS-001`) |
| 9 | `systemcfg` | **`apply` and `rollback` removed** if D2 picks C. `set`, `get`, `unset`, `diff` stay: Machines `plan` reports closure changes, not option values | Build `set`, `get`, `unset`, `diff` first. Build `apply` as a thin `nixos-rebuild switch` call only |
| 10 | Install `framework` | **Removed in part** if D2 picks B: `machines install` from `server` replaces the installer, the cache route, and the credential delivery (PV-09) | Run `BOOT-025` in a VM first. Then install. Prove `CACHE-007` after first boot |

---

# 5. Decisions only the owner can make

**D1. Workspace shape.**
1. devenv-native workspaces (`WS-001` to `WS-006`): `devenv.yaml` and `devenv.lock`, a shared base imported from the collection, no generated flake.
2. Flake-only: every project gets a generated `flake.nix`, and shells use `devenv.lib.mkShell` (reduced mode).
3. Both files in every project, with two locks kept in step by `WS-004`.

Recommendation: 1. The generator stays for repositories that a flake consumes (`nix-meta`, other authors).

**D2. devenv Machines.**
1. A: not now. `nixos-rebuild` activates every host. Reassess when Machines is stable or #3226 lands.
2. B: Machines for the `framework` install only (`BOOT-025`), after a VM fixture. `server` stays on `nixos-rebuild`.
3. C: full adoption. Hosts move into a `devenv.nix` in `nix-meta`, `apply` and `rollback` go to Machines, and every NixOS host accepts root SSH.

Recommendation: B. It removes the PV-09 blocker for Step 10. It does not put an experimental tool
on `server`, and it needs no root SSH to `server`.

**D3. Which concept governs the system shape.** The owner's
`composable-devenv-system-distribution-concept.md` (2026-10-09) makes devenv "the primary system
composition interface". It imports `vendomat.modules.*` and `vendomat.profiles.*`, runs PostgreSQL as
a devenv process, and treats Machines as "the system-level target". V5 says Vendomat is never
imported (`DEL-008`), has no profiles, and keeps Postgres as a NixOS unit.
1. V5 governs. The devenv-first goal arrives through D1 option 1 and D2 option B.
2. The composable-distribution concept governs. V5 then needs a Vendomat devenv module library, which `DEL-011` and `DEL-012` now forbid.

Recommendation: 1. `COMPUTING-AS-COMPOSABLE-CAPABILITIES-CONCEPT.md` (also 2026-10-09) already agrees with V5.

**D4. `mkModules`.**
1. Build it now, as specified (`MOD-001` to `MOD-010`).
2. Write the three-face convention and `MOD-011` now. Build the helper when a second provider needs all three faces.

Recommendation: 2. PV-07 found 14 of 18 providers with one face.

**D5. Partitioning for Step 7.**
1. disko, selecting the 4 TB drive by `by-id`, run by hand after the preflight, with mounts forced to `by-uuid` (`DISK-008`).
2. Hand-written `sgdisk` and `mkfs` commands after the preflight.

Recommendation: 1. The layout is then declarative and testable in a VM first.

---

# 6. Unverified claims

| # | Claim | What would verify it |
| --- | --- | --- |
| U1 | A flake-backed input declared in `devenv.yaml` (`flake: true`) brings its own transitive flake inputs into `devenv.lock`, as in `flake.lock`. *Inference:* devenv uses Nix's `InputsLocker` (E20) | Fixture: A → B → C flakes in a test collection; a `devenv.yaml` that names A only; read `devenv.lock` for B and C nodes |
| U2 | `imports = [ inputs.knappy.devenvModules.default ]` inside `devenv.nix` works without infinite recursion. *Inference:* `inputs` is in `specialArgs` (`bootstrapLib.nix` ~247) | Fixture with one flake input that exports `devenvModules.default` |
| U3 | A devenv shell with a `git://server/…` input fails when the daemon is stopped, though the store holds the revision (PR #3244) | Fixture F3, then stop the daemon or point the URL at a closed port, and run `devenv shell -- true` |
| U4 | `devenv machines install` from `server` installs a disposable VM, and the target builds nothing | VM fixture with root SSH, a disko layout on a virtual disk, `hardware.facter = null` |
| U5 | disko's generated `fileSystems` use `/dev/disk/by-partlabel/…` devices, and an override to `by-uuid` is accepted | Evaluate a disko layout's `config.fileSystems` in a VM fixture |
| U6 | `disko.nixosModules.disko` with no `disko.devices` changes nothing in the `server` configuration | Compare `nixosConfigurations.server.config.system.build.toplevel` with and without the module |
| U7 | PR #3255 (install hang on a fresh SSH connection) is not in 2.4.0 | Read the 2.4.1 release notes when published; or run U4 on 2.4.0 |
| U8 | Discourse thread 80271 posts #7 and #15 (plugin system "probably after devenv 3"; deploy-rs "tied to flakes") | Read the posts directly; Agent B read them through a summarizing fetch |
| U9 | `require_version` accepts a range such as `">=2.4.0"` | `devenv shell` in a fixture with the key set |
| U10 | Machines `plan` output is usable as the `vendomat diff` report | Run `devenv machines plan --json` against a VM target; compare with an option-level diff |
| U11 | GitHub states of #2205, #3055, #3167, #3096, #3226, #3232, #3242, #3244, #2610, #1539, #3175 as of 2026-10-09 | Agent B read them with `gh`; Agent D did not. Re-read with `gh issue view` / `gh pr view` before acting |
| U12 | `nix-meta` holds a `devenv.lock` and a `devenv.local.nix` but no `devenv.nix` or `devenv.yaml` | `ls ~/Documents/Projects/nix-meta/devenv.*` showed only those two files; the reason was not checked |

---

# Appendix A. Answers by question

## Q1. Machines

- **devenv.** `machines.<name>` with roles `nixos`, `nix-darwin`, `home-manager` (`machines.nix:301,568,581`). Subcommands: `info`, `check`, `plan`, `apply`, `deploy`, `install`, `status`, `rollback` (`cli.rs:1324-1470`). There is no `machines build`; use `devenv build machines.<n>`. disko is required for every NixOS role (`machines.nix:127-128`). Facter is required unless `hardware.facter = null` (`machines.nix:132-134,329`). Rollback switches to a recorded previous system, with a watchdog timer and a boot recovery unit (`deploy.py:326-330,545-555`; `recovery.nix:4-20`). Install runs only over root SSH to `target.host`, kexecs the target, and wipes with no prompt (E5, E6).
- **V5.** `vendomat set`, `diff`, `apply`, `rollback` are spec only (`CLI-009` to `CLI-015`). `fromToml` and `fromInventory` are spec only. `nix-meta` has `nixosConfigurations.server` through `mkMachine` (`flake.nix:278,292`).
- **Why V5 dropped Machines.** No V5 document states it. CONCEPT-V3-CC used Machines (`:344-347`, `:367`, `:377`) and listed its limits: experimental (`:384`), disko required (`:390`), facter report per host (`:391`), "install partitions and formats without confirmation" (`:393`). V5's only link is `NAT-009` and SPEC:514: activation uses `nixos-rebuild` because Machines does not substitute through Attic. *Inference:* the `DISK-*` preflight and `BOOT-022` replaced `machines install` after the disk-name incident of 2026-10-08.
- **Verdict.** Machines could replace `apply`, `rollback`, and a status record, not `set`, `get`, `diff`, or `fromToml`. It does not change the core and delta split: the core is a module that each machine imports. PV-02 breaks because `install` has no identity check and no prompt. It installs only to a remote host over SSH; it has no local second-drive mode. Recommendation: D2 option B.

## Q2. Module composition

- **devenv.** `imports` entries are local paths or `<input>/<dir>`. An input import loads `devenv.nix` and `devenv.local.nix` and ignores the input's `devenv.yaml` (F2). `outputs` builds derivations for `devenv build`. No convention for devenv plus NixOS plus Home Manager faces exists. Machines takes plain modules with `inputs` and `self` in `specialArgs`.
- **V5.** `mkModules` returns three faces; `extra` holds face-specific content (`MOD-001` to `MOD-010`, spec only).
- **Verdict.** No devenv duplicate. `extra` does not duplicate a devenv feature, because devenv has no service-to-systemd bridge. One conflict: devenv's `imports` takes a directory, not a flake attribute (`MOD-011`).

## Q3. Per-workspace opening

- **devenv.** direnv (`use devenv`), `devenv hook <shell>` with `devenv allow` (2.1), profiles (`profiles.<name>`, `profiles.hostname.<host>`, `profiles.user.<user>`, `--profile`, persisted by `devenv allow`), priority base < hostname < user < `--profile` with `mkOverride` on leaf options only (`bootstrapLib.nix:276,330`), `devenv.local.nix` loaded after `devenv.nix` at the same priority (`bootstrapLib.nix:231-246`), `devenv.local.yaml` loaded last, tasks with `before = [ "devenv:enterShell" ]`, `require_version`.
- **V5.** Nothing. The nearest text is CONCEPT:426-428 and `DEL-010`.
- **Verdict.** Unused opportunity. A minimal workspace layer needs `WS-001` to `WS-006`: one base repository, a tag-pin lint, hostname profiles, local files for personal settings, and host values through the environment. No Vendomat code. Limit: until #3055 lands, each workspace repeats the base's inputs.

## Q4. Flake integration

- **devenv.** `lib.mkShell` and `flakeModules.default` exist (`flake.nix:313-379`). In flake mode devenv does not read `devenv.yaml`, needs an impure root or `readDevenvRoot`, and offers a four-command shim (E19). devenv never reads a project `flake.lock`.
- **V5.** A generated `flake.nix` with a bridge; no devenv input (`GEN-015`, `GEN-017`, `GEN-022`).
- **Verdict.** `GEN-017` loses nothing. `GEN-022` loses nothing in the generator, but its "MAY define its own shell" pushes a shell into the reduced mode (`GEN-023`). `vendomat sync` duplicates `devenv inputs add --follows` only for a project that is devenv-native. Lock: Nix owns `flake.lock`; devenv owns `devenv.lock`, through Nix's locker. A project with both has two locks (`WS-004`).

## Q5. Hosts and paths

- **devenv.** No named paths, no drive identity, no inventory. Nearest: `profiles.hostname`, `target.host`, `.machines/<n>/facter.json`. Secrets: SecretSpec in the shell; Machines bootstrap secrets at install; no sops-nix integration.
- **V5.** `PATH-*`, `DISK-*`, `fromInventory` (spec only).
- **Verdict.** Required. disko reduces `fromInventory`; the identity guard stays.

## Q6. Services and processes

- **devenv.** 45 service modules, all devenv processes with state under the project; no systemd output (E23).
- **V5 and nix-meta.** Paseo (`server.nix:197`), SilverBullet (`:268`), Postgres (`:410`), Atuin server (`:318`), atticd (`:341`), git daemon (`:174`) are system units. The inferference router and Dagu are user units.
- **Rule.** A NixOS unit for anything that must run without a shell open, serves other machines or the tailnet, or owns durable data outside a project. A Home Manager or user unit for a per-user daemon. A devenv service or process for anything a project needs only while someone works in it, with state under `$DEVENV_STATE` or `$DEVENV_RUNTIME`. Under this rule every service in `server.nix` stays a NixOS unit. A project may run its own throwaway Postgres or SilverBullet as a devenv service for tests.

## Q7. Cache and source

- **devenv.** Cachix only, through `cachix.pull` and `cachix.push`. Other substituters come from the daemon. An untrusted user's substituter request is dropped silently. Default nixpkgs is `devenv-nixpkgs/rolling`. Inputs use Nix's URL parser, so `git://` works (F3).
- **V5.** Attic in `nix.settings`; the collection over `git://`; nixpkgs and devenv never mirrored (`REG-018`, `REG-019`).
- **Verdict.** No conflict. One risk: PR #3244 (U3).

## Q8. Testing

- **devenv.** `devenv test` runs `devenv:enterTest` tasks (including git hooks), builds `test`, starts processes, runs `enterTest`, stops processes (`mod.rs:2517-2603`).
- **V5.** `devenv shell -- testee verify --mode quick` and the opt-in end-to-end mode (`AGENTS.md`).
- **Verdict.** Aligned. Optional: run Testee from `enterTest`. Testee stays the authority.

## Q9. Roadmap risk

| Item | State on 2026-10-09 | Target | Effect on V5 |
| --- | --- | --- | --- |
| Machines experimental | Released 2.4.0, 2026-09-24 | "may change before stable", no date | Any adoption (D2) may need rework |
| #3255 install hang fix | Merged 2026-10-08 | 2.4.1, unreleased | 2.4.0 `install` can hang (U7) |
| #3055 remote `devenv.yaml` composition | Open PR, last activity 2026-10-06 | none | Would remove the input repetition in `WS-002`; root wins on conflicts |
| #3167, #3096 `--from` loads remote YAML | Open | none | Out-of-tree workspaces |
| #3226 Machines accepts composed configurations | Open issue | none | Would let `nix-meta` keep `nixosConfigurations` as is |
| #3242 non-root SSH | Open issue | none | Would ease D2 option C |
| #3232 deploy-time secrets | Open issue | none | Runtime secrets through Machines |
| #3244 offline locked inputs | Open PR, 2026-10-01 | none | U3 |
| #2610 native process manager in flake mode | Open PR, 2026-03-12 | none | Narrows the `GEN-023` gap |
| #1539 custom caches (Attic) | Open since 2024-10-17 | none | devenv could configure Attic itself |
| #3175 Cachix substituters miss the daemon | Open, 2026-09-10 | none | None for V5: Attic is in the daemon |
| devenv 3 | `TODO(v3.0)` in `config.rs`; 2.0 blog | no date; milestone "2.5" has no due date | Low |

## Q10. V5 pieces

| Piece | Built | Class | Reason |
| --- | --- | --- | --- |
| `registry` | Yes | required | Tag pins, `[forge]`, `[follows]` checks; devenv has none |
| `generate` | Yes | required for flake-backed authors; redundant for devenv-native workspaces | `devenv.yaml` plus `devenv inputs add` does the same job for a workspace |
| `store` | Yes | required | devenv has no source collection, `keep`, or `mirror` |
| `mkModules` | No | required (no equivalent), low value | One provider in 18 has three faces |
| `fromToml` | No | required | devenv has no TOML host settings |
| `paths` | No | required | devenv has no named host paths |
| `fromInventory` | No | reducible | disko declares the layout and its mounts; the identity guard stays |
| `systemcfg` | No | reducible | Machines covers `apply`, `rollback`, status; `set`, `get`, `unset`, `diff` stay |
| `locate` | Yes | required | devenv has no command that prints a locked input's store path. Nix does (`nix flake archive`), and `locate` wraps it |

---

# Appendix B. Evidence

Source paths are relative to the `cachix/devenv` repository at `fe20b5c`. Agent letters name the
agent that observed the item.

| Key | Observation | Source |
| --- | --- | --- |
| E1 | Versions and revision distance (see "Versions under review") | D: `devenv version`, `git rev-parse`, `git merge-base`, `git diff --stat` |
| E2 | "Experimental. Machines are new in devenv 2.4. The interface may change before it is declared stable." | `docs/src/content/docs/machines.md:5-7`; [devenv.sh/machines](https://devenv.sh/machines/); [2.4 blog](https://devenv.sh/blog/2026/09/24/devenv-24-machines/) line 25; `gh release view v2.4.0` (A, B, D) |
| E3 | Option surface: `target.host` (257), `nixos` (301), `hardware.facter` default `.machines/${name}/facter.json` (317-329), `deploy.rollbackTimeout` 30-600 default 300 (636), build outputs (604-672), `configurations` alias (753), `machines` (757-760) | `src/modules/machines.nix` (D) |
| E4 | disko required: comment 118; `throw` 127-128; module added 145. Docs: "NixOS machines require the disko input, even when you only deploy to an existing host" | `machines.nix`; `machines.md:26`; fixture F1 (D) |
| E5 | Install: "always operates over SSH" (1275); NixOS only (1268); "install requires root SSH access" (1851); kexec tarball via `curl … \| tar … && /root/kexec/run` (1904); phases kexec, facter, disko, install, reboot; `localhost` "still routes through SSH" | `devenv/src/devenv/machines.rs`; `devenv/src/cli.rs:1104-1111`; `machines.nix:263-264` (D) |
| E6 | "Install wipes disks without a confirmation prompt"; "there is no dry run or automatic resume"; no `yes` field on `Install`; "`install` never runs bare because it wipes disks"; system built before disko (1680-1690); root-auth refusal (1664) | `machines.md:133-135`; `cli.rs:1380-1430,1427`; `machines.rs` (A, D) |
| E7 | Deploy prompt `Confirm::new().with_prompt("Apply this fleet plan?").default(false)`; non-interactive without `--yes` fails; `apply` takes a saved plan in `.devenv/machine-plans/<id>/` | `machines.rs:2449-2465,2785-2802`; `cli.rs:1331-1342,1437` (D) |
| E8 | Rollback: `nix-env --profile /nix/var/nix/profiles/system --set <previous>` then `switch-to-configuration switch`; watchdog `systemd-run --on-active=<timeout>s`; `devenv-machines-recover` unit; state in `/var/lib/devenv-machines` and `/nix/var/nix/gcroots/devenv-machines`; no rollback for nix-darwin or Home Manager | `src/modules/machines/deploy.py:52-54,326-330,405-409,545-555`; `src/modules/machines/recovery.nix:4-20`; `machines.rs:3031-3070`; `machines.md:224,249` (D) |
| E9 | `nix copy --to ssh://…`; no `substitute` match in `machines.rs`; the target must trust the copier or the signatures | `machines.rs:508-521,2886-2897,3181-3205`; `machines.md:298,360` (D) |
| E10 | NixOS and nix-darwin "require target.host for system deployment"; activation always over SSH; local activation only for Home Manager; no hostname match | `machines.rs:2519-2527,2942-2955,2963-2975` (D) |
| E11 | `nixosSystem { specialArgs = { inherit inputs self; }; modules = [ … disko.nixosModules.disko ./machines/recovery.nix ./machines/facts.nix machine.nixos … ] }`; `inputs.nixpkgs.lib.nixosSystem` or `eval-config.nix` from `nixpkgs-src`; inputs from `devenv.lock` | `machines.nix:48-60,141-149,208`; fixture F1 (D) |
| E12 | `importModule` resolves `<input>/<sub>` and `tryImport` loads `devenv.nix` and `devenv.local.nix`; local YAML load order "source first, then imports, then base last"; "Remote inputs are not yet supported for `devenv.yaml` imports." | `devenv-nix-backend/bootstrap/bootstrapLib.nix:120-163`; `devenv-core/src/config.rs:681-745,1006,1040,1222,1273`; `docs/…/composing-using-imports.mdx:33-34`; fixture F2 (D) |
| E13 | #2205 open (2025-10-07); PR #3055 open (2026-07-31, last activity 2026-10-06), root `devenv.lock` stays the single lock; #3167, #3096 open | `gh issue view 2205`, `gh pr view 3055` (A, B) |
| E14 | URL parsing by `FlakeReference::parse_with_fragment` through the Nix C API; `flake` defaults to true; `url` plus `follows` is an error; defaults `github:cachix/devenv-nixpkgs/rolling` and `github:cachix/devenv?dir=src/modules`; `devenv inputs add … --follows` | `devenv-nix-backend/src/lib.rs:84-93,95,113,147,162,175`; `config.rs:178-239`; `devenv inputs --help` (A, D) |
| E15 | Fixture F3 result | D |
| E16 | `outputs` type `outputOf attrs`; `devenv build` builds every output-typed option, including `machines.<n>.build.*` | `src/modules/outputs.nix:3-35`; `devenv/src/devenv/mod.rs:2620-2680`; `bootstrapLib.nix` ~466-558 (D) |
| E17 | `profiles`, `profiles.hostname`, `profiles.user`; `orderedProfiles = hostnameProfiles ++ userProfiles ++ manualProfiles`; `profilePriority = (defaultOverridePriority - 1) - index`; `--profile`/`-P` | `src/modules/profiles.nix:27-51`; `bootstrapLib.nix:261-276,330,433`; `cli.rs:359-364`; `docs/…/profiles.mdx:93-98` (D) |
| E18 | Load order: imports, `devenv.nix`, `devenv.local.nix`, `--option` values; `devenv.local.yaml` last | `bootstrapLib.nix:231-246`; `config.rs:725` (D) |
| E19 | Flake shim "comes with a subset of functionality"; `devenv.root` from `PWD`; SecretSpec assertion "not supported when using devenv with Nix Flakes"; dotenv assertion; comparison table; `devenv.yaml` not read in flake mode; PR #2610 open | `src/modules/flake-compat.nix:35-80,130-142`; `src/modules/integrations/secretspec.nix:55-61`; `integrations/dotenv.nix:157`; `docs/…/guides/using-with-flakes.md:35-48`; `flake.nix:313-379` (A, B, D) |
| E20 | `DEFAULT_LOCK_FILE = "devenv.lock"`; Nix `LockFile` and `InputsLocker`, `LockMode::Virtual`, `use_registries(true)`; lock version 7; no project `flake.lock` read | `devenv-core/src/paths.rs:9`; `devenv-nix-backend/src/lib.rs:189-300,311-374` (D) |
| E21 | SecretSpec crate 0.21; `SecretspecConfig { enable, profile, provider, cachix_auth_token }`; no sops integration; Machines bootstrap secrets; "Use sops-nix or agenix in your NixOS or home-manager modules"; #3232 open | `Cargo.toml:125`; `config.rs:441-471`; `secretspec.nix:7-95`; `machines.md:302,338` (A, B, D) |
| E22 | `cachix.pull = [ "devenv" ] ++ …`; `format!("https://{cache}.cachix.org")`; daemon drops an untrusted user's substituters "without an error in the shell"; #1539 and #3175 open | `src/modules/cachix.nix:11-44`; `devenv-core/src/cachix.rs:190-207`; `docs/…/binary-caching.mdx:96-128` (A, B, D) |
| E23 | 45 service modules; `rg systemd src/modules/services/*.nix` finds nothing; no `nixosModules` output; native process manager default for CLI ≥ 2.0 | `src/modules/services/`; `src/modules/processes.nix:447-455` (D) |
| E24 | `devenv test` phases; `enterTest`; `devenv:git-hooks:run` before `devenv:enterTest` | `mod.rs:2517-2603`; `src/modules/tests.nix:5-24`; `src/modules/integrations/git-hooks.nix:20-28,105,296` (D) |
| E25 | direnv `use devenv`; `devenv hook` and `devenv allow` (2.1); `devenv init` no longer writes `.envrc` (2.2); `require_version` (2.1) | [direnv](https://devenv.sh/integrations/direnv/), [auto-activation](https://devenv.sh/auto-activation/), `gh release view v2.1.0`, `v2.2.0` (A) |
| E26 | PR #3244 "reuse locked inputs already in the store", open 2026-10-01 | `gh pr view 3244` (B) |
| E27 | PR #3255 merged 2026-10-08, CHANGELOG "2.4.1 (unreleased)" | `gh pr view 3255`; `CHANGELOG.md` on `main` (B) |
| E28 | #3226 (composed configurations), #3242 (non-root SSH), #3232 (deploy secrets), all open | `gh issue view` (B) |
| E29 | `TODO(v3.0): remove deprecated alias`; 2.0 blog "devenv 0.x is now deprecated. Support will be dropped entirely in devenv 3."; milestones "2.4" and "2.5", no due dates; Discussions disabled | `config.rs:310,337,2741` (D); `gh api repos/cachix/devenv/milestones?state=all` (B) |
| E30 | V5 inventory: only `registry`, `generate`, `store`, `locate`, `cli` exist; `sync` (`cli.py:26`) and `path` (`cli.py:67`) are the only commands | `src/vendomat/`; `tests/test_repo_shape.py` (C) |
| E31 | CONCEPT-V3-CC Machines use and limits | `.scratch/projects/09-vendomat-nixos-devenv-rewrite/CONCEPT-V3-CC.md:319,344-347,367,377,384,390-393` (C) |
| E32 | Owner concept documents: `composable-devenv-system-distribution-concept.md` (2026-10-09; `:44`, `:158-164`, `:376-411`, `:547-566`), `COMPUTING-AS-COMPOSABLE-CAPABILITIES-CONCEPT.md` (2026-10-09; `:349-358`, `:411-424`), `simplified-nixos-devenv-development-system-concept.md` (2026-10-04; `:18`, `:32`), `canonical-devenv-development-platform-concept.md` (2026-09-18; `:11`, `:233-240`) | `~/.paseo/uploads/upload_*/` (C) |
| E33 | `nix-meta` services and lines quoted in Appendix A, Q6 | `nix-meta/machines/server.nix`, `profiles/devman.nix` (C) |
| E34 | No named-path, host-inventory, or drive-identity feature in the documentation or the module tree. *Observation of absence:* Agent A searched every fetched devenv.sh page; Agent D found no such option in `src/modules/` | A, D |

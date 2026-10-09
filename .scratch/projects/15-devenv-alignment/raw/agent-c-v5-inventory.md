<!-- Raw final report of Agent C (V5 requirement inventory, sonnet), 2026-10-09. Extracted unedited from the agent transcript. Model output: an observation here is the agent's claim, not a Vendomat gate. -->

# Vendomat V5 inventory (Agent C)

Paths: SPEC = `/home/andrew/Documents/Projects/vendomat/.scratch/projects/14-vendomat-local/SPEC-V5.md`. CONCEPT, GUIDE, REFINEMENT, DECISIONS (in `prelim-verification/`) sit in the same project directory. Code is in `/home/andrew/Documents/Projects/vendomat/src/vendomat/`. Every ID below is **active** unless marked otherwise. Most are "proposed until a fixture runs".

## Headline finding
Only the registry, generator, store and `path` exist in code. There is no `lib/` or `nix/` Nix library in the repo, and `nix/testee.nix` is the only Nix file.

`test_repo_shape.py` pins the library to six modules: `__init__`, `cli`, `generate`, `locate`, `registry`, `store`. The built CLI has exactly two commands, `sync` (`cli.py:26`) and `path` (`cli.py:67`). Everything else is spec only: `mkModules`, `fromToml`, `fromInventory`, `vendomat.paths`, `systemcfg`, `add`, `remove`, `status`, `query`, `explore`, `set`, `get`, `unset`, `diff`, `apply`, `rollback`.

A search of `*.nix` and `*.py` under `~/Documents/Projects` (excluding `.worktrees`, `.devenv`, `.venv`) finds no definition or use of `mkModules`, `fromToml`, `fromInventory`, `vendomat.paths` or `systemcfg`. They appear only in `.scratch` docs. `nix-meta` has no `vendomat.toml`, no host TOML and no inventory file.

## 1. Pieces

| Piece | What it does | Req IDs (SPEC lines) | Source | Devenv mentions |
|---|---|---|---|---|
| **registry** (built) | Reads and validates `vendomat.toml` (`[forge]`, `[inputs]`, `[passthrough]`, `[follows]`). Folds `ref`/`rev` into URL queries and enforces tag pins. Returns sorted `Source`s plus a digest. Never writes the file. | REG-001,002,006,007\*,008,009\*,010–014,016–021 (131–153); REG-003/005/015 superseded; REG-004 withdrawn. \*`add`/`remove` do not exist, so REG-007/009 are checked for `sync` only (PV-14:52) | `registry.py` `parse_registry:95`, `_entry:149`, `_check_pin:211`, `_follows:269`, `_digest:295` | REG-018/019 and CONCEPT:44: nixpkgs and devenv are "never mirrored or kept". `NEVER_LOCAL={"nixpkgs","devenv"}` at `registry.py:35`. The `nixpkgs` passthrough URL is `devenv-nixpkgs` (SPEC:104). |
| **generate** (built) | Writes `flake.nix`: header, digest, direct inputs, `follows` lines, and the bridge `outputs = inputs: import ./flake-outputs.nix inputs;`. Refuses a hand-written flake. Fails if `flake-outputs.nix` is missing but never opens it. Never touches `flake.lock`. | GEN-005–008, 015–022 (199–222). Superseded: GEN-001,002,003,004,009,010,011,013,014. GEN-012 withdrawn. | `generate.py` `render:52`, `_stanza:79`, `sync_flake:88` | Generated flake has no devenv input or shell (GEN-015, GEN-022). CONCEPT:59 and :384: a `devenv.nix` exists "only if the project has its own devenv shell". |
| **store** (built) | Runs `keep` clones, `mirror` copies (only under `--collection`) and the newest-tag checkout. Uses Git subprocesses, exit codes 0/1/2, and a dry-run mode. | STORE-001,003,005–009,012–023 (313–335). Superseded: STORE-002,004,011. STORE-010 "not yet built". | `store.py` `sync_store:178`, `_sync_clone:195`, `refresh_collection:252`; `hooks/collection-post-receive` | Only the exclusion above. |
| **locate** (built) | `vendomat path <name>` runs `nix flake archive --json --no-write-lock-file` and prints `inputs.<name>.path`. | CLI-007, CLI-016 (451, 459) | `locate.py` `input_path:27`, `_archive:46` | None. |
| **`sync`** (built) | Writes the flake, then does store work. Flags `--root`, `--collection`, `--dry-run`. | CLI-001 (partial), STORE-016, STORE-021, GEN-018 | `cli.py:26-64` | DEL-010: reachable from a devenv project shell (PV-25). |
| **mkModules** (spec only) | One declaration `{name, options, packages, extra}` returns `{devenv, nixos, homeManager}` modules. Options land at `<name>.*` (devenv) and `programs.<name>.*` (NixOS/HM). Each face has `enable=false`. `packages` is `cfg: pkgs: [drv]`. | MOD-001–006, 008–010 (374–383); MOD-007 superseded by MOD-010. INP-003,004,006,007. CORE-001. DEL-003 (author repos may add a Vendomat input). | CONCEPT:430–476 (example), GUIDE Step 4 (`mkMerge` snippet), PV-07. No code. | Devenv face = `devenvModules.default`, install path `packages`; `extra.devenv` can set `processes`/`tasks` (CONCEPT:467, MOD-008). NixOS face = `environment.systemPackages`; HM = `home.packages` (MOD-005). |
| **`extra`** | `extra = cfg: pkgs: { <face> = module content; }`. A key reaches only its own face. Merged with `lib.mkMerge`. CONCEPT:475 says to promote a shape to a real `mkModules` key after three uses. | MOD-006, MOD-008, MOD-010 | none | CONCEPT:472: "A system service, a user service, and a devenv process are three different mechanisms with three different lifetimes. `extra` keeps them honest." |
| **fromToml** (spec only) | Converts `<host>.toml` `[options]` dotted keys into one NixOS module `{ config = mkMerge [...]; }`. Resolves package names only for allowlisted paths (`environment.systemPackages`). Native option-type merge applies. | SYS-001,004,006–010 (243–252). Superseded: SYS-002,003,005. DEL-004 (reached via nix-meta's own Vendomat input). | CONCEPT:248–268 (schematic), GUIDE:256–271, PV-06. No code. | None. |
| **paths** (spec only) | `options.vendomat.paths : attrsOf str` (never `path`). Exports `VENDOMAT_PATH_<NAME>` to shells. Services get their own `Environment=`. An undeclared name throws, naming the input. | PATH-001–004 (274–278) | REFINEMENT:6–28, CONCEPT:480–506, GUIDE:286–335 ("`lib/paths.nix`"). No code. | The host's `devenv.nix` declares it (REFINEMENT:12). "A service gets its own environment setting. It does not inherit the devenv shell's environment." |
| **fromInventory** (spec only) | Generates NixOS `fileSystems` from recorded hardware IDs plus post-format UUIDs. Updates the inventory before emitting mounts. Logical names such as `new-system`, `previous-system`, `shared`, `backup`. | DISK-001,004,005,007 (279–286); DEL-004 | CONCEPT:521–531, 598 ("`fromInventory.nix` 25 lines"), REFINEMENT:42–48. No code. The observed fileSystems are hand-written in `nix-meta/machines/server.nix:696–752`. | None. |
| **systemcfg** (spec only) | `set/get/unset/diff/apply/rollback` over the host TOML. `diff` evaluates `nixosConfigurations.<host>.config.<path>` before and after and compares JSON. | CLI-009–015 (452–458) | CONCEPT:589 (`systemcfg.py`, 120 lines), GUIDE Step 9 | None. `apply` drives `nixos-rebuild switch` (CLI-011), not devenv. |
| **module.nix / cache.py** (spec only) | CONCEPT:599 lists a consumer module (substituter, key, credential path, `.vend/` out-links, `explore`). `cache.py` does presence checks. Neither exists. | CACHE-001,005 (343,347); CLI-005,008 | CONCEPT:585–599 | The V4 consumer module is a devenv module, and V5 removes it. |

**CLI status.** CLI-001 lists 13 commands (`add remove sync status query path explore set get unset diff apply rollback`). DEL-012 (SPEC:433) redefines the surface as "the built subset of CLI-001".

| Status | Commands |
|---|---|
| In code | `sync`, `path` |
| Spec only | `add`, `remove`, `status`, `query`, `explore`, `set`, `get`, `unset`, `diff`, `apply`, `rollback` |

CLI-006 is withdrawn. CLI-003 (`--json` on read commands) is met only by `path`.

## 2. Requirement text

**GEN-017** (SPEC:217), exact: "The generator MUST NOT scan, filter, or import any module face of any input. A module is used only when the project file names it" | Verify: "The generated body has no `devenvModules`, `nixosModules`, `homeManagerModules`, or `filterAttrs`. PV-13 F3 and F4: an unselected face has no effect; a selected face is inactive until enabled".

**GEN-022** (SPEC:222), exact: "The generator MUST NOT emit `devShells`, `devenv.lib.mkShell`, or a `devenv` input. A project MAY define its own shell in its outputs file; it owns that shell and its `devenv.root` setting" | Verify: "PV-13 F2: `nix flake show` lists only the outputs the project file defines".

Other quotes (trimmed):
- **GEN-015** (215): "`inputs` MUST carry exactly one entry per distinct name in `[inputs]` and `[passthrough]`. The generator MUST add no input of its own: no `devenv`, no `nixpkgs`, and no Vendomat input".
- **GEN-016** (216): "`outputs` MUST be the fixed bridge `outputs = inputs: import ./flake-outputs.nix inputs;`. It MUST reference no Vendomat input, output, or library".
- **GEN-018** (218): "`sync` MUST fail, naming `flake-outputs.nix`, before any write when that file is missing. `sync` MUST NOT open, read, or write it".
- **GEN-019** (219): "A project output selected through the generated flake MUST evaluate and build with no Vendomat input and no Vendomat command on `PATH`. The gate needs no `--impure` and no generated shell".
- **GEN-020/021** (220–221): the file names no transitive input. It writes `<child>.inputs.nixpkgs.follows = "nixpkgs";` for each `[follows]` pair and no other edge.
- **GEN-005–007**: header, byte-identical output, refusal to overwrite a hand-written flake.
- **Lock ownership, GEN-008** (212): "Vendomat MUST never read or write `flake.lock`".

**Devenv input / `devenv.yaml`**
- GEN-015 and GEN-022 (above).
- INP-001 superseded by INP-008 (265): "Vendomat MUST NOT require `devenv.yaml` for dependency resolution".
- CORE-007 superseded by CORE-008.
- REG-018/019 (150,151): nixpkgs and devenv never mirrored or kept.
- SPEC:292–302: RES/EMIT withdrawn; "a generated `devenv.yaml` lock" is gone.
- GUIDE:620: "Do not use `devenv.yaml` as a second dependency declaration."

**Attic / cache**
- CACHE-001 (343): consumer module adds substituter and trusted key.
- CACHE-002 (344): push credential not in tracked file, store path or log.
- CACHE-003 (345): a pull-only credential is refused on push.
- CACHE-005 (347): an unpushed path reports absent.
- CACHE-006 (349): `attic watch-store` runs on every builder.
- CACHE-007 (349): a cold consumer gets cached output with no local build. "collected, not gated".
- CACHE-008 (350): NAR hash equals the hash recorded at build.
- CACHE-009 (351): builder reports an upstream skip, and consumers keep the source cache as fallback.
- CACHE-004 is superseded by CACHE-009.
- BUILD-001–008 (359–366).
- STORE-012 (324): "No Vendomat step MAY require a source path to be present in Attic."
- Attic holds build outputs only (SPEC:80).

**git:// collection**
- STORE-008 (320): "one set of repositories on the collection host (`server`), at `/home/andrew/vendor/<repo>`, served read-only to the tailnet over `git://`. The serving process MUST sleep when idle".
- STORE-014 (325): `pre-receive` hook refuses refs outside `refs/tags/` and any tag update or delete.
- STORE-015 (326): "The daemon MUST serve a repository only when it carries `.git/git-daemon-export-ok`. It MUST NOT accept a push over `git://`. Port 9418 MUST be open on the tailnet interface only".
- STORE-013 (327), STORE-022 (334), STORE-023 (335): newest-tag working tree, via `sync --collection` or a `post-receive` hook.
- STORE-010 (322): rebuildable by re-pushing tags. **Not built.**
- REG-016 (148): forge URL. REG-017 (149): "Every `[inputs]` entry MUST pin a tag".
- REG-018–020 (150–152): `mirror`, `keep`, `backup`. The explicit use of `backup` is not built.
- STORE-006/007 (318,319): portable URLs; local checkout only by explicit override.
- STORE-011 is superseded by STORE-014.

**Core vs delta**
- BOOT-001 (561): core boots with no Vendomat process or Python.
- BOOT-002 (562): core carries cache access.
- BOOT-003 (563): core holds only what every machine needs.
- BOOT-016 (580): "An element that only one machine needs MUST be a delta, never part of the core".
- DEL-006 (427): "The shared machine core MUST boot without the Vendomat CLI; a host MAY add the CLI in a later host delta".
- DEL-007 (428): the CLI is `packages.<system>.vendomat`, never `.default`.
- DEL-011 (432): "The CLI MUST NOT be installed through devenv or the shared boot core. A host delta installs it". Open: nix-meta still pins `d5a90f0`.
- Editor/Python cores: CORE-001–008 (393–400), ISO-001–007 (408–414).
- BOOT-010 (584): a converted input matches the tree it replaces, or the difference is named.

**Machine install / disk / preflight**
- DISK-001–007 (279–286), all active but unproven (PV-02 blocked).
- DISK-001: "record each physical drive by a stable hardware identifier".
- DISK-002: "A partition or format operation MUST reject a target that backs the running root or boot filesystem".
- DISK-003: reject a missing identifier or a mismatched model, serial, size, mount or signature.
- DISK-004: mounts use UUIDs.
- DISK-005: record the actual UUIDs after format.
- DISK-006: new server has its own ESP; the 512 GB drive is left intact.
- DISK-007: a service requires its data mount.
- BOOT-021 (576): the 512 GB install stays independently bootable.
- BOOT-022 (577): "built on the running old system and installed as a prebuilt closure... `nixos-install` is given `--system`, `--closure`, or `--store-path`".
- BOOT-023 (578): fresh install, never in place.
- BOOT-024 (579): neither install writes the other's boot entries.
- Superseded: BOOT-004,005,011,013,014. BOOT-007 withdrawn. BOOT-015 narrowed.
- PV-02: preflight blocked. Inventory and a synthetic checker pass, but `wipefs --no-act` is denied, so the target's partition table and signatures are unknown.
- GUIDE:77–91: the old `PREFLIGHT PASS` checker was removed. Step 0 and Step 7 are withdrawn or blocked.
- BOOT-006,012,018–020 cover the VM, cold installer and no-laptop-dependency rules.

**Rollback**
- CLI-013 (456): "`rollback` MUST select the prior system generation" (not built).
- CLI-011 (454): `apply` drives `nixos-rebuild switch`.
- CLI-012 (455): `apply` refuses on a dirty host file.
- CLI-015 (458): `diff` compares the committed host TOML with the working one.
- CLI-010 (453): `diff` reports the option delta.
- BOOT-021: the fallback is a second bootable drive, not a generation.
- PV-08: no switch or rollback was tested.

**Secrets**
- No dedicated ID.
- CACHE-002 (344) is the only secret rule.
- CONCEPT:222–223: "Those stay in Nix. So does hardware and so do secrets."
- CONCEPT:154,230: `profiles/secrets.nix`.
- PV-09 / DECISIONS open choice 2: the installer credential delivery is undecided.

**Workspace / project opening on the core**
- No requirement and no mechanism. See section 6.
- Out of scope (SPEC:613): "a workspace orchestrator".

**Testing / Testee gates**
- No SPEC requirement ID.
- AGENTS.md: the gate is `devenv shell -- testee verify --mode quick`, plus `VENDOMAT_E2E=1` for Nix, toolchain or consumer changes. No raw pytest, ruff or ty.
- GUIDE:333: "**Verify:** `devenv shell -- testee verify --mode quick` passes."
- SPEC:49: "A requirement is satisfied when its **Verify** column runs and passes."
- PV-14: 260 tests; the normal gate skips 30 Nix tests and the opt-in gate runs all 260.

## 3. Build order (GUIDE steps; CONCEPT table 684–695)

| Step | One line | IDs | State |
|---|---|---|---|
| 0 | Drive-identity preflight with no writes. Original commands withdrawn. | DISK-001–005 | Blocked (PV-02) |
| 1 | Write `core/default.nix`: nix settings, user, zsh, ssh, tailscale, basics, no CLI. | BOOT-001, 003, 016 | Not run |
| 2 | Cache access in the core. | BOOT-002, CACHE-001, 002 | Blocked (PV-09: cold VM gets 401) |
| 3 | `nixos-rebuild build-vm` of the core on an empty store. | BOOT-001, 006 | PV-11 passed as a disposable fixture |
| 4 | `mkModules`, `fromToml`, `vendomat.paths` (4.5). | MOD-001–010, INP-006/007, SYS-001–010, PATH-001–004 | Not built |
| 5 | Split `nvim-core` out of `nix-nvim`. | CORE-001–008, BOOT-010, ISO-001–005 | Not run |
| 6 | `attic watch-store` (6.1) and the builder timer (6.2). | CACHE-006, 009, BUILD-001–007 | Not run |
| 6.3 | Source collection: git daemon, `collection-add`, hooks. | STORE-008, 012–015, 022, 023 | Done (PV-18/19/22/24); `framework` push untested |
| 7 | Fresh install of `server` on the 4 TB drive. | DISK-001–007, BOOT-021–024 | Blocked (PV-02, PV-09) |
| 8 | Registry and generator. | REG-\*, GEN-005–008, 015–022, STORE-\* | Built; fixtures pass; acceptance needs observed `framework` fetch |
| 9 | `systemcfg`: set, get, diff, apply, rollback. | SYS-001–010, CLI-009–015 | Not built |
| 10 | Install `framework` with no local build. | CACHE-007, BOOT-002, 019, BUILD-008 | Blocked (PV-09) |

Rules: no step before 10 may depend on the laptop (BOOT-018, 020). Steps 1–7 need no Python (BOOT-009).

## 4. Why V5 dropped devenv Machines and disko

**No explicit reason exists.** Disko, `nixos-anywhere` and `facter` never appear in project 14 or in projects 10–13. They appear only in `CONCEPT-V3-CC.md` (`.scratch/projects/09-vendomat-nixos-devenv-rewrite/`). Project 14 never records a decision to drop `devenv machines`.

V3-CC used them as follows:
- `:319` declares `disko: { url: "github:nix-community/disko", follows: nixpkgs }` in `devenv.yaml`.
- `:344–347` declares `machines.laptop = { ... hardware.facter = ./hardware/laptop.json; nixos = import ./nixos/laptop.nix; ... }`.
- `:367` says "`devenv machines install <host>` | Provision a fresh host: kexec, facter, disko, install, reboot".
- `:377` says "**Vendomat drives `devenv machines plan`. It does not re-implement it.**"

Nearest evidence for the drop:
1. **Transfer path.** SPEC-V5.md:504 `NAT-009`: "devenv Machines transfers with `nix copy --to ssh://` and does not substitute through Attic". SPEC-V5.md:514: "`NAT-009` is why system activation runs through `nixos-rebuild`, which substitutes normally." This is the only V5 statement tying Machines to a design choice. CONCEPT-V4 (canonical) line 77 says the same, and V4 made "no machine-cache claim".
2. **Machines is experimental.** V3-CC:384: "Machines is marked experimental and its interface may change before it is declared stable."
3. **Constraints listed by V3-CC itself.**
   - `:390`: "NixOS machines require the `disko` input, even for deploy-only use."
   - `:391`: facter needs a committed report per host.
   - `:393`: "`install` partitions and formats without confirmation. There is no dry run and no resume."
4. **V5 added a guard against exactly that.** V5 requires a read-only preflight that checks identity, ancestry, mounts and signatures before any write (DISK-002/003).
   - GUIDE Step 7 and BOOT-022 use `nixos-install` with a prebuilt closure instead of a Machines install.
   - Inference: this is a replacement for `machines install`, not an explicit statement.
5. **Scope.** BOOT-007 (withdrawn): "`nixosConfigurations` holds only `server`." `nix-meta/flake.nix` uses plain `lib.nixosSystem` via `mkMachine` (`:278`).
6. **"Machine plane" wording is easy to misread.** DECISIONS.md:88 and CURRENT.md:76 say "The machine plane is not part of V5". That refers to V4's Vendomat generation/activation layer and the Dagu registry, not to devenv Machines. CURRENT.md:76 says: "NixOS generations give the atomic switch and the rollback."

## 5. nix-meta server services

Evaluated host: only `nixosConfigurations.server` (`flake.nix:292`). All of the following are NixOS-level declarations in `machines/server.nix` unless noted.

| Service | Declaration | Data, port, user | Scope |
|---|---|---|---|
| **Paseo** | `server.nix:197` `nix-paseo.paseo` options. The wrapper `nix-paseo/modules/paseo.nix` sets upstream `services.paseo` (paseo flake `v0.10.3`, `nix-paseo/flake.nix:13`). Adds `systemd.services.paseo-tailscale-serve` (`paseo.nix:753`). | `dataDir` `/home/andrew/.paseo` (`paseo.nix:271`); `workspaceRoot` `/home/andrew/Documents/Projects`; port 6767 (`paseo.nix:466`) bound to loopback with Tailscale Serve HTTPS on 8443 (`server.nix:210–219`); `user=andrew`, `group=users`; `plugins.sources.devman-panel` at `~/.paseo/plugins/devman-panel` | **System-wide** system unit, one instance. It runs as `andrew` and works inside the user's project tree. |
| **SilverBullet** | `server.nix:268` `services.silverbulletServer.enable`. The module `silverbullet-server/modules/silverbullet-server.nix:144` wraps nixpkgs `services.silverbullet`, then adds `silverbullet-tailscale-serve` (`:270`) and `silverbullet-git-backup` plus a timer (`:296–320`). | Space `/home/andrew/Notes`; port 3000, loopback only; Serve at `/notes` on 443; `StateDirectory=silverbullet` (`/var/lib/silverbullet`, Chrome profile in `chrome-data`); service user `silverbullet`; owner `andrew`, group `users`; git backup every 15 min | **System-wide** system unit. The data is the owner's notes. |
| **Postgres** | `server.nix:410` `services.postgresql` (nixpkgs module) | `postgresql_17`; cluster `/var/lib/postgresql/17` (comment at `:402`); `ensureDatabases=["agentman"]`, role `agentman`, peer auth with identMap `agentman andrew agentman` (`:424–429`); local Unix socket; no TCP port declared | **System-wide**, single cluster. Atuin's DB also goes here via `createLocally`. |
| **Atuin sync server** | `server.nix:318` `services.pytuin.server`. `pytuin/nix/modules/nixos/server.nix:117` wraps nixpkgs `services.atuin`, plus `atuin-tailscale-serve` (`:138`). | `127.0.0.1:8888`; Serve at `/atuin` on 443; `openRegistration=false`; `database.createLocally=true` (Postgres); package `atuin-18.23.0` (`nix/atuin-18.23.0.nix`) | **System-wide** server. Clients are per-user via Home Manager (`profiles/terminal.nix`). |
| Attic (`atticd`) | `server.nix:341` `services.atticd` plus custom units `atticd-storage-setup` (`:363`), a `systemd.services.atticd` override (`:374`), and `atticd-tailscale-serve` (`:381`) | Listen `127.0.0.1:8089`; storage `/mnt/wd_green1/attic` (ext4, `fileSystems` at `:748`); sqlite at `/mnt/wd_green1/attic/server.db`; user `atticd` (system user, `:358`); `RequiresMountsFor` | System-wide |
| Git daemon (collection) | `server.nix:174` `services.gitDaemon` | `basePath /home/andrew/vendor`; user `andrew`, group `users`; port 9418 opened on `tailscale0` only (`:159`) | System-wide |
| argentic overlay | `server.nix:282` `services.argenticOverlay` (from `inputs.argentic`) | `127.0.0.1:8790` (comment `:273`); user `andrew`; pi from `pi-nixpkgs` | System unit running as the owner |
| inferference router | `server.nix:113`, plus `systemd.user.services.inferference-router.environment` (`:120–134`) | User service; config in `~/.config/inferference`; repo `/home/andrew/Documents/Projects/inferference` | **Per-user** systemd user service |
| devman Dagu | `profiles/devman.nix:21` `services.devman-dagu` | Systemd **user** service; ports 8080 and 50055 (defaults); `registryDir=$HOME/.local/state/vendomat/devman/active`; linger for `andrew` | **Per-user**. The comment at `:33` ("Vendomat now owns generation, activation, and rollback") is stale V4 text. |
| Hindsight (mnemonix) | `profiles/mnemonix.nix:20` `services.mnemonix.hindsight` | `apiPort 8891`, `uiPort 9991`; `projectsRoot` `/home/andrew/Documents/Projects` | Module-defined; unit kind not checked |
| restic backup | `server.nix:760` `nix-meta.backup`; `profiles/backup.nix` | Target `/mnt/wd_green1`; passwordless repo | System-wide |
| Other | `programs.coolercontrol`, `services.btrfs.autoScrub` (`:630`), `services.fornix-host.enable=false` (`:455`), zelligate (commented out), `structuredAgents*` (commented out), `systemd."user@".Delegate` (`:463`) | | |

Observations:
- Every long-running app service on `server` is a NixOS-level unit. None is a devenv process.
- The two per-user services are the inferference router and Dagu. Both are systemd user units, not devenv services.
- `vendomat.nixosModules.default` is still imported at `server.nix:68` (V4 text; the lock pins `d5a90f0`). The package is on the system `PATH` via that module.
- The nix-meta `flake.nix` carries a pinned `devenv.url = "github:cachix/devenv/v2.4.0"` input (`:37`), installed through `profiles/developer.nix`.

## 6. How a workspace or module "opens" on the minimal core

**V5 docs.** There is no mechanism or requirement for opening a workspace or app module on the core. The nearest text:
- CONCEPT:426–428: "An input's module reaches a project only through a line in that project's `flake-outputs.nix`."
- CONCEPT:384–388: "A project that wants a development shell defines it here, with the shell tool and root setting it chooses... The installed `vendomat` command is a host program, reachable from a project shell through the host `PATH`; a project does not import it (`DEL-010`, not yet proved)."
- DEL-010 (431): the host CLI is reachable from an existing project shell. Proved on two throwaway fixtures (PV-25); not run in any real repository and not on `framework`.
- The example `# lib.shell = nixpkgs.lib.evalModules { modules = [ nvim-core.devenvModules.default ]; };` is commented out in SPEC:191.
- INP-006 and MOD-003: every face is inert until `enable=true`.
- `vendomat.paths` is the only core-to-workspace link: a host-declared path read by a devenv shell.

**Owner concept docs** (newest copy of each; mtime):

| Doc | mtime | Other copies |
|---|---|---|
| `composable-devenv-system-distribution-concept.md` | 2026-10-09 10:23 | none |
| `COMPUTING-AS-COMPOSABLE-CAPABILITIES-CONCEPT.md` | 2026-10-09 10:23 | none |
| `simplified-nixos-devenv-development-system-concept.md` | 2026-10-04 18:41 | 10-03 copy is byte-identical |
| `canonical-devenv-development-platform-concept.md` | 2026-09-18 18:13 | 09-17 and 09-18 07:20 copies are byte-identical |

All are under `~/.paseo/uploads/upload_<id>/`.

**composable-devenv-system-distribution** (the largest departure from V5):
- Target architecture: "NixOS as a thin substrate, devenv as the primary system composition interface, Vendomat as the reusable module library and bridge layer, and Jujutsu as the change/history model." (:44)
- "Users should primarily interact with: `devenv.nix` and imported devenv modules" (:158–164).
- Import lines look like `vendomat.modules.shell`, `vendomat.profiles.ai-development` (:171, :988).
- Activation rule: "Put it at the highest practical layer." Environment (devenv), then user (Home Manager), then NixOS (:997–1019).
- Services such as PostgreSQL and LLM servers should be devenv processes, with "Only truly machine-global services" becoming NixOS services (:376–411).
- :547–566 says devenv Machines is "the system-level target" and that the "user-facing composition layer stays consistent even when activation falls through to NixOS".
- Lists `modules/`, `profiles/` and `lib/` under a `vendomat/` repo (:830–853).
- This conflicts with V5: V5 has no `vendomat.modules.*`, no profiles, no devenv input, and no Machines.

**COMPUTING-AS-COMPOSABLE-CAPABILITIES-CONCEPT** (an educational series; it aligns with V5):
- Four execution levels: Workspace (devenv), Runtime (devenv processes), User (Home Manager), Host (NixOS) (:349–358).
- Vendomat is "deliberately kept out of the learning runtime": system-installed, input-only flake bridge, "The project chooses which modules to import and which outputs or shells to define" (:411–424).
- Keeps module faces `devenvModules`/`nixosModules`/`homeManagerModules`, inert until enabled (:488–496).
- Says "A host service does not inherit a project's shell environment by default" (:359).
- Says "Importing a module should not silently start a persistent service or change the host" (:90).

**simplified-nixos-devenv-development-system**:
- "If devenv can express it, use devenv. If a shell command can implement it, use a shell command. If a small CLI is clearly useful, write one. Everything else waits." (:18)
- NixOS holds machine configuration, services, packages, mounts and security.
- devenv is the "main composition layer" for per-repo environments, tasks and reusable imports.
- "Repositories may import other repositories when useful. No separate module/layer/project framework is required." (:32)
- Attic is optional and caches build outputs only (:385–413).
- Mutable state sits in plain directories exposed through env vars. This anticipates `vendomat.paths` (:218–248).

**canonical-devenv-development-platform**:
- One canonical devenv repo defines the shared shell; each project imports it through `devenv.yaml` (`imports: [dev-env]`) and adds a thin overlay plus `devenv.local.*` (:11, :233–240).
- `devenv.nix` is "the public reusable definition" (:182).
- Package outputs are consumed separately via `inputs.<name>.devenv.config.outputs.<output>` (:781).
- A flake is "an adapter" only (:811).
- This is what `devenv.local.nix` and `devman.link` implement in vendomat today, and it is the V4 central-overlay model that V5 removes.

## 7. Pinned devenv

devenv.lock files (root `devenv` and root `nixpkgs` nodes):

| Repo | devenv rev | nixpkgs |
|---|---|---|
| vendomat | `fe20b5cba7ab` (2026-09-29) | `cachix/devenv-nixpkgs` `rolling` @ `256551e45f63` |
| nix-meta | `190959a9a4bb` (2026-09-07) | `cachix/devenv-nixpkgs` `rolling` @ `256551e45f63` |
| repoman | `a73c5b84c952` (2026-10-09) | `cachix/devenv-nixpkgs` `rolling` @ `c2f38fe7f9e0` |
| linkman | `fe20b5cba7ab` (2026-09-29) | `cachix/devenv-nixpkgs` `rolling` @ `c2f38fe7f9e0` |
| devman | `d1fb321e7304` (2026-07-08) | `cachix/devenv-nixpkgs` `rolling` @ `6004ea8c229f` |
| gitman | `d1fb321e7304` | same `6004ea8c229f` |
| loci-core | `d1fb321e7304` | same `6004ea8c229f` |
| nix-paseo | `9d93b838def8` (2026-08-03) | `cachix/devenv-nixpkgs` `rolling` @ `c946ff36bf19` |

Notes:
- All use the `devenv-nixpkgs` `rolling` ref, so there are six distinct devenv revs across the eight repos.
- vendomat's `devenv.yaml` pins `nixpkgs` at `github:cachix/devenv-nixpkgs/rolling` and adds `nixpkgs-python` at `github:cachix/nixpkgs-python`.
- vendomat's flake input is `github:cachix/devenv-nixpkgs/rolling` as the only input (`flake.nix:7`). Its `flake.lock` has only `nixpkgs`.
- nix-meta also has a flake-level devenv input, `github:cachix/devenv/v2.4.0`, locked to `b904dcb51fe48c30db250038241507f60752f222`.
  - It carries its own nixpkgs, `devenv-nixpkgs` `rolling` @ `256551e45f63`, "DELIBERATELY NOT following this flake's nixpkgs" (`flake.nix:21`).
  - The system `nixpkgs` is `NixOS/nixpkgs nixos-unstable` @ `d407951447dc`.
  - GUIDE:47 names the fleet pin: "devenv | 2.4.0+b904dcb". That matches this flake-level input, not the `devenv.lock` files above.
- vendomat's `devenv.lock` rev `fe20b5c` is the revision cited for `NAT-003` and in V3-CC as "devenv 2.4.1".
- nix-meta's flake pins `vendomat` at `d5a90f0aff97224b34e9bc2647e56b44cbf790d5` (V4). The code is now 0.6.0, so the machine still runs V4's CLI and consumer module.

## Inconsistencies for the reviewer
- The V5 docs describe `mkModules`, `fromToml`, `fromInventory`, `paths` and `systemcfg` in detail, but no code, fixtures or tests exist for any of them. The only evidence is the PV-06, PV-07 and PV-08 throwaway fixtures under `~/.local/state/vendomat/v5/...`. I did not open those fixture directories, only the result write-ups.
- SPEC says Step 8 acceptance is not complete: the `framework` fetch and build are owner-reported and the output source was not observed (PV-19).
- SPEC §1.4 uses the heading number twice: "The input contract" and "Named paths and drive identity".
- `nix-meta/profiles/devman.nix:33` and `machines/server.nix:63–74` still describe V4 delivery of the vendomat consumer module.
- I ran no tests or builds, only reads.

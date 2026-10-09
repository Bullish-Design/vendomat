# Vendomat V6 specification

**Date:** 2026-10-09. **Status:** Draft for owner review. Normative once the owner accepts it.
**Concept:** [CONCEPT-V6.md](./CONCEPT-V6.md). **Base:** [SPEC-V5.md](../14-vendomat-local/SPEC-V5.md).
**Evidence:** [project 15](../15-devenv-alignment/). Agent letters (A to K) name the reports in
`../15-devenv-alignment/raw/`. Their command logs are in `~/.local/state/vendomat/v5/2026-10-09/devenv-alignment/`.

## How to use this document

- A requirement is satisfied when its **Verify** runs and passes. A fixture result in project 15 is
  evidence for the mechanism. It does not satisfy a requirement on the real system.
- **MUST** is normative. **SHOULD** states the default; a deviation needs a recorded reason.
- Preserve every ID. Never reuse or renumber one. A changed requirement gets a new ID, and the old one
  is marked superseded.
- Every V5 ID not named in section 0 stays active with its V5 text.
- The draft IDs in `../15-devenv-alignment/REPORT.md` section 3 (`WS-001` to `WS-006`, `MOD-011`,
  `DISK-008`, `BOOT-025`, `CLI-017` to `CLI-019`, `GEN-023`, `NAT-018` to `NAT-023`) were proposals and
  were never adopted. This document defines its own text for every ID it uses. Where a number matches a
  report draft, the text here replaces the draft.

## Terms

| Term | Meaning |
| --- | --- |
| Workspace | A devenv project: `devenv.nix`, `devenv.yaml`, `devenv.lock`, and a `vendomat.toml` |
| Library | A repository that exports packages and faces from its own `flake.nix` |
| Face | A library's module for one target: devenv, NixOS, or Home Manager |
| Fragment | The `.vendomat/` directory that `vendomat sync` writes and the workspace `devenv.yaml` imports |
| Fork | The owner's devenv: upstream tag plus the patch series, in the collection |
| Inventory | `vendomat.inventory.<host>`: the host's NixOS module and its disks with roles |

---

# 0. Relation to V5

| V5 ID | V6 status | Successor or note |
| --- | --- | --- |
| `DEL-008` | Superseded | `VMOD-001`: every workspace imports the Vendomat module |
| `DEL-009`, `GEN-019`, `ISO-007` | Narrowed | `DEL-013`: they hold for library outputs, not for workspaces |
| `DEL-010`, `DEL-011` | Superseded | `DEL-017`: a host launcher runs each workspace's pinned Vendomat |
| `DEL-012` | Superseded | `DEL-015`: the Vendomat flake also exports the devenv module |
| `DEL-004` | Superseded | `DEL-016`: `nix-meta` is retired |
| `GEN-022` | Superseded | `GEN-023`: a workspace shell is a devenv project |
| `GEN-017` | Kept | It covers the flake target only. The module imports faces (`VMOD-003`), not the generator |
| `REG-021` | Superseded | `REG-022`: adds `[imports]` and `[targets]` |
| `CACHE-001` | Superseded | `CACHE-010`: the host core sets the substituter |
| `CLI-001` | Superseded | `CLI-017` |
| `CLI-011`, `CLI-012`, `CLI-013` | Superseded | `MACH-005`: activation and rollback through devenv Machines |
| `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015`, `SYS-001` to `SYS-010` | Deferred | Host settings in TOML: open decision |
| `MOD-001` to `MOD-010` | Deferred | `FACE-001` to `FACE-004` now; the helper later |
| `BOOT-008`, `BOOT-010` | Withdrawn 2026-10-09 | Blank slate: no capability parity and no tree comparison |
| `BOOT-009` | Withdrawn 2026-10-09 | No conversion step exists. `BOOT-001` keeps the core free of Vendomat |
| `BOOT-022` | Superseded | `MACH-008`: install with devenv Machines from the running `server` |
| `DISK-005` | Superseded | `DISK-008`: UUIDs are declared before formatting |
| `NAT-006` | Superseded | `NAT-018` |
| `NAT-009` | Superseded | `NAT-019` |

---

# 1. One pinned devenv

| ID | Requirement | Verify |
| --- | --- | --- |
| `DVN-001` | Every host MUST install exactly one devenv command line, built from the fork tag, through the host core | `devenv version` prints `2.4.0+<fork rev>` on each host, and `command -v -a devenv` lists one path |
| `DVN-002` | The fork build MUST be a release build (`isRelease = true`), so `require_version: true` is enforced | With the fork CLI, `require_version: true` against stock `v2.4.0` modules exits 1: "does not match the modules version 2.3.1" (agent J Q3) |
| `DVN-003` | The fork MUST be the upstream tag plus a listed patch series. Each patch MUST name its upstream commit or pull request, or be marked fork-only | `git log <upstream tag>..<fork tag>` lists only the series in `../15-devenv-alignment/prototypes/devenv-v2.4.0-vendomat.1.patch` |
| `DVN-004` | Every devenv project MUST set `require_version` to the fork's version string and pin `inputs.devenv` to the fork revision with `?dir=src/modules` | The fleet pin check exits 0 over `~/Documents/Projects` (prototype: `devenv-pin-check.py`, agent G) |
| `DVN-005` | The fork's `src/modules/latest-version` MUST equal the CLI crate version | `git show <fork>:src/modules/latest-version` equals `devenv version` without `+rev` |
| `DVN-006` | Attic MUST hold the fork's build. A host with Attic configured MUST build nothing to install it | `nix build --dry-run` of the fork package on a cold host lists no derivation to build |
| `DVN-007` | Each upstream bump MUST run the bump checklist: changes under `devenv-nix-backend/bootstrap/`, `machines.rs`, and `latest-version`; PR #3244 state; the `isRelease` hook; the `require_version` matrix; the offline test; the version string | The bump log records each item (list: agent J Q6) |
| `DVN-008` | A workspace MUST enter its shell with the collection unreachable and an empty fetcher cache, when the store holds every locked source and nixpkgs is a plain `github:NixOS/nixpkgs` input | Fork CLI exits 0; stock 2.4.0 exits 1 at `resolve-lock.nix:89` (agent J Q4) |

---

# 2. The Vendomat devenv module

| ID | Requirement | Verify |
| --- | --- | --- |
| `VMOD-001` | Every workspace and `nix-systems` MUST import `inputs.vendomat.devenvModules.default`. The `vendomat` input MUST pin a release tag in the collection | The lock's `vendomat` node has `original.ref = refs/tags/…`; the shell has the module's options (agent K Q8) |
| `VMOD-002` | A face that the module imports but that is not enabled MUST NOT change the shell derivation | `devenv build shell` gives the same store path with and without the import (agent K Q1) |
| `VMOD-003` | The module MUST import `devenvModules.default` of every flake input except Vendomat itself (matched by `outPath`), `devenv`, `nixpkgs`, `self`, and any input without that attribute. It MUST wrap each with `lib.setDefaultModuleLocation "inputs.<name>.devenvModules.default"` | Agent K Q1: no recursion; skipped inputs are skipped; an option clash names both inputs |
| `VMOD-004` | A check that must stop shell entry MUST be an assertion. A task MAY report a warning | A failing assertion makes `devenv shell -- true` exit non-zero; a failing task does not (agents I Q5, K Q2) |
| `VMOD-005` | The module MUST assert that every git node in `devenv.lock`, direct or transitive, has `original.ref` under `refs/tags/` and a 40-hex `locked.rev`. `vendomat.check.enable = false` MUST turn the check off | A branch ref stops the shell and names the node; the option turns it off (agent K Q2) |
| `VMOD-006` | Every Vendomat command that builds or pushes MUST run the same checks first, because devenv does not evaluate assertions for `devenv build` or `devenv eval` | `vendomat push` with a branch ref in the lock exits non-zero and pushes nothing |
| `VMOD-007` | With `vendomat.cache.push = true` and `vendomat.cache.name` set, the module MUST provide a `vendomat:push` task and a `vendomat-push` script that pipe the built output paths to `attic push <name> --stdin` | A stand-in `attic` receives exactly the `devenv build` paths (agent K Q3). **Open:** a push to the real Attic |
| `VMOD-008` | Everything the module puts under `outputs` MUST be a derivation. `vendomat.inputPaths` MUST give each input's store path, and an output MUST carry them as a JSON file whose closure holds every input source | `devenv eval vendomat.inputPaths`; `nix-store -qR` of the output lists the sources (agent K Q4) |
| `VMOD-009` | `vendomat.paths` MUST be `attrsOf str`, default from `/etc/vendomat/paths.json`, and MUST export `VENDOMAT_PATH_<NAME>`. A missing file MUST give `{}`. Implements `PATH-001` to `PATH-004` | The shell shows the variables (agent K Q5). **Open:** the real host file |
| `VMOD-010` | Host and user defaults MUST use `profiles.hostname.<host>` and `profiles.user.<user>` with `lib.mkDefault`, so a workspace can override them | The defaults apply on the named host; a workspace value wins (agent K Q6) |
| `VMOD-011` | The module MUST own `machines.<host>.nixos`. The owner MUST write `vendomat.inventory.<host>.nixos`. Any other definition of `machines.<host>.nixos` MUST fail evaluation, naming the host | Agent K Q7: a direct definition fails with "is also defined outside vendomat.inventory" |
| `VMOD-012` | For each host, the module MUST assert: every `disko.devices.disk.*.device` is a `/dev/disk/by-id/` path listed in the inventory with role `install-target`; no `fileSystems.*.device` uses `by-partlabel` or a kernel name | `devenv build machines.<host>.build.nixos` fails on each bad layout with a named message and passes on a good one (agent K Q7) |

---

# 3. The pre-resolver

| ID | Requirement | Verify |
| --- | --- | --- |
| `REG-022` | A top-level table other than `[forge]`, `[inputs]`, `[passthrough]`, `[follows]`, `[imports]`, and `[targets]` MUST be an error naming it. `[inputs]` MUST be present | Unit tests |
| `PRE-001` | `[targets]` MUST select the outputs: `devenv = true` writes the fragment; `flake = true` writes `flake.nix` by `GEN-005` to `GEN-021`. Both MAY be set | Unit tests for each combination |
| `PRE-002` | With the devenv target, `vendomat sync` MUST write `.vendomat/devenv.yaml`, `.vendomat/devenv.nix`, and `.vendomat/digest`. A workspace `devenv.yaml` of only `imports: [ ./.vendomat ]` MUST lock every fragment input into the workspace's own `devenv.lock` | Agent I Q1 |
| `PRE-003` | For each `[imports]` entry `<input>/<dir>`, `sync` MUST read that directory's `devenv.yaml` from the input's source and add its inputs as top-level inputs, recursively. Two imported files with different URLs for one name MUST be an error naming both. A registry entry wins and `sync` MUST report it | Agent I Q3 (the conflict path is not yet run) |
| `PRE-004` | `sync` MUST NOT write a `follows` deeper than one level. It MUST express a nested edge as a top-level input plus one-level `follows` | Agent I Q4: one node per source |
| `PRE-005` | `sync` MUST add `<input>.inputs.<name>.follows = <name>` for every child that shares a top-level source, and MUST report a child whose source differs instead of following it | Lock node count per source is one (agent I Q3) |
| `PRE-006` | `.vendomat/devenv.nix` MUST assert that the digest exists, that `vendomat.toml` matches the recorded hash, and that the fragment matches the recorded hash | Each case exits 1 with its message (agent I Q5) |
| `PRE-007` | `sync` MUST warn when the workspace `devenv.yaml` or `devenv.local.yaml` redeclares a generated input, because that entry replaces the generated one entirely | Fixture: a redeclared input with `follows` in the fragment prints the warning (agent I Q2 shows the replacement) |
| `PRE-008` | `sync` MUST judge a lock update by the lock contents and the error text, never by the exit status of `devenv update` | An unreachable input makes `sync` exit non-zero, though `devenv update` exits 0 (`NAT-026`) |
| `PRE-009` | A `use_vendomat` direnv function MUST re-sync only when the digest is stale, then run `use devenv` | Agent I Q6: about 0.35 s with no change |
| `PRE-010` | The fragment MUST add no measurable time to a warm shell entry and at most 100 ms to a full evaluation | Agent I Q7: 0.173 s against 0.175 s warm; +65 ms full |

---

# 4. Faces

| ID | Requirement | Verify |
| --- | --- | --- |
| `FACE-001` | A library MUST export each face it supports at `devenvModules.default`, `nixosModules.default`, or `homeManagerModules.default`, and no other face (`INP-007`) | `nix flake show` of the library |
| `FACE-002` | Each face MUST declare `<name>.enable`, default false, and change nothing until it is true (`INP-006`) | The library's check evaluates each face alone and compares the result with and without the import |
| `FACE-003` | Each library's verification MUST evaluate every exported face alone | The library's Testee gate runs the check |
| `FACE-004` | *Proposed, open decision.* Options land at `<name>.*` under devenv and `programs.<name>.*` under NixOS and Home Manager | Decided by the owner |

---

# 5. Machines and `nix-systems`

| ID | Requirement | Verify |
| --- | --- | --- |
| `MACH-001` | `nix-systems` MUST be a devenv project that defines `machines.server` and `machines.framework` through `vendomat.inventory`, with one shared core module and one delta module per host | `devenv machines info` lists both; `devenv build machines.<host>.build.nixos` succeeds (agent G Q2) |
| `MACH-002` | Machines and workspaces MUST use a plain `github:NixOS/nixpkgs/<rev>` of nixos-unstable, not `devenv-nixpkgs` | The lock's `nixpkgs` node is `NixOS/nixpkgs`; `DVN-008` passes |
| `MACH-003` | `nix-systems` MUST declare `disko`, and `home-manager` when a host has a Home Manager role. Each host MUST commit `.machines/<host>/facter.json` or set `hardware.facter = null` | The build fails without them (agent G Q2) and passes with them |
| `MACH-004` | Each host MUST accept the owner's deploy key for root, key-only (`PermitRootLogin prohibit-password`, no password login). devenv MUST run as the owner, not as root | A self-deploy as the owner to `root@localhost` succeeds (agents F Q5, G Q4) |
| `MACH-005` | Activation, status, and rollback MUST use `devenv machines plan`, `deploy`, `apply`, `status`, and `rollback`. Vendomat MUST NOT wrap them | Agent G Q3 |
| `MACH-006` | Every host MUST set `deploy.healthCheck`. Every service MUST start cleanly; a host MUST NOT be deployed while a unit is failed | `systemctl --failed` is empty before a deploy; a failing health check rolls back (agent G Q3) |
| `MACH-007` | A host with install payloads (`install.secrets`, `install.extraFiles`, `install.encryptionKeys`) MUST be installed with a CLI that carries `a5fd551a`. An `install.extraFiles` key MUST NOT contain a dot | Agent G Q5b. **Open:** a runtime install with the fork CLI |
| `MACH-008` | `server` MUST be installed on the 4 TB drive by `vendomat machine install server`: the preflight (`MACH-010`), then `devenv machines install server --phases disko,install` with the default disko mode, from the running `server` to `root@localhost`. It MUST refuse `--disko-mode format` and `mount`, and MUST unmount `/mnt` afterwards | VM: the old disk's partition table, ESP files, and NVRAM unchanged; the new disk boots alone (agent F Q2). **Open:** the real hardware |
| `MACH-009` | The first install MUST set `boot.loader.efi.canTouchEfiVariables = false`. The new system MUST be tried once with `efibootmgr -C` and `efibootmgr -n`. It MUST become the default only after it has run reliably | VM (agent F Q4). **Open:** the real firmware keeps the entry and honours `BootNext` |
| `MACH-010` | Before disko runs, the preflight MUST check on the target: the `by-id` path resolves; model, serial, and size match the inventory; `wipefs --no-act` and `blkid -p` show no signature; the disk does not back `/` or `/boot`; nothing is mounted under `/mnt`; `.machines/<host>/facter.json` is committed. Any mismatch or unknown result MUST stop it. Implements `DISK-002` and `DISK-003` | A fixture injects each mismatch; no write runs. The real scan on `server` (PV-02) |
| `MACH-011` | `framework` MUST be installed from `server` with `devenv machines install`, with its own facter report | A VM fixture first |

---

# 6. Disks, cache, delivery, command line

| ID | Requirement | Verify |
| --- | --- | --- |
| `DISK-008` | A disko layout MUST preset partition GUIDs (`uuid`) and filesystem UUIDs (`extraArgs = ["-U" …]` for ext4, `["-i" …]` for vfat), MUST mount by UUID, and MUST use a disk attribute name unique on the host | `lib.testLib.makeDiskoTest` boots with the preset UUIDs (agent E Q1); `VMOD-012` passes |
| `CACHE-010` | The host core MUST set the Attic substituter and its public key in `nix.settings` | `nix config show` lists both on each host; the machine `nix.conf` equals a plain NixOS build (agent G Q5a) |
| `DEL-013` | A library's flake outputs MUST evaluate and build with no Vendomat input and no Vendomat command. A workspace MAY depend on the Vendomat module | `GEN-019`'s check, run on a library only |
| `DEL-014` | *Decided 2026-10-09, see `DEL-017`.* Where the `vendomat` command runs from | — |
| `DEL-017` | The host MUST install a small `vendomat` launcher, not the full command. Inside a workspace, the launcher MUST run the Vendomat build that the workspace's `devenv.lock` pins, found in the store by its NAR hash, with no network when the build is present. Outside a workspace, it MUST run the host's pinned release. The module MUST NOT put a second `vendomat` on the shell `PATH`. The direnv hook (`PRE-009`) MUST call the launcher | Two workspaces that pin different tags each report their own version; with the network off and the builds present, both still run; outside a workspace the host release runs |
| `DEL-015` | The Vendomat flake MUST export `packages.<system>.vendomat` and `devenvModules.default`, and MUST have `nixpkgs` as its only input | `nix flake show`; `tests/test_repo_shape.py` |
| `DEL-016` | `nix-systems` MUST reach every Vendomat Nix function through its own `vendomat` input | No machine file names a Vendomat path |
| `GEN-023` | The generator MUST NOT emit `devShells`, `devenv.lib.mkShell`, or a `devenv` input in `flake.nix`. A workspace shell MUST be a devenv project that uses the devenv target | `nix flake show` lists only the project's outputs |
| `CLI-017` | The surface MUST be `sync`, `path`, `check`, `push`, and `machine install`. Deferred commands (`set`, `get`, `unset`, `diff`) MAY return later | `--help` lists exactly the built commands |
| `CLI-018` | `path <name>` MUST also work in a devenv workspace, from `devenv.lock`, with no network | The `lockpath.nix` method gives the same path as `vendomat.inputPaths` (agent H Q5) |
| `CLI-019` | `check` MUST run the pin check, the devenv version check, and the fragment check, and MUST name each problem | Each injected problem is named; a clean workspace exits 0 |

---

# 7. Observed facts

Each was observed on devenv 2.4.0 (`b904dcb5`), Nix 2.34.7, nixpkgs nixos-unstable `e7439b6b`, and
disko v1.13.0 unless noted. None is a gate.

| ID | Fact | Evidence |
| --- | --- | --- |
| `NAT-018` | devenv merges `devenv.yaml` for local path imports only; the project file wins, and `devenv.local.yaml` loads last. An input-style import loads `devenv.nix` and ignores that input's `devenv.yaml` | `config.rs:681-745`; `bootstrapLib.nix:120-163`; agents D, H Q3 |
| `NAT-019` | Machines copies outputs with `nix copy --to ssh://<host>`, with no `--substitute-on-destination` | `machines.rs:508-521,3181-3205` (agent D) |
| `NAT-020` | A `git://` input with `?ref=refs/tags/<tag>` locks in `devenv.lock`, though devenv's documentation does not list the scheme | Agent D fixture F3 |
| `NAT-021` | In flake mode devenv reads no `devenv.yaml`, ships a shim with `up`, `test`, `tasks`, and `version` only, and asserts SecretSpec and dotenv off | `flake-compat.nix:35-80`; `secretspec.nix:55-61` (agent D) |
| `NAT-022` | `devenv machines install` works only over root SSH to `target.host`, formats with no prompt and no dry run, and has no local block-device mode. NixOS deploy to `localhost` also uses SSH | `machines.rs:1268,1275,1851`; `machines.md:133-135` (agent D) |
| `NAT-023` | `cachix.pull` adds only `https://<name>.cachix.org` substituters | `cachix.rs:190-207` (agent D) |
| `NAT-024` | A failing task before `devenv:enterShell` does not stop `devenv shell`; an assertion does | `mod.rs:2239-2252` (agents I, K) |
| `NAT-025` | devenv evaluates `assertions` for `devenv shell`, `test`, and `up`, not for `devenv build` or `devenv eval` | Agent K Q2 |
| `NAT-026` | `devenv update` exits 0 when an input fetch fails, on the stock and the fork CLI | Agents H Q4, J Q4 |
| `NAT-027` | The upstream flake builds a development CLI (`isRelease ? false`), so `require_version: true` is not enforced. At tag `v2.4.0`, `latest-version` says `2.3.1` | `nix/workspace.nix:33`; agents G Q1, J Q2 |
| `NAT-028` | With a cold fetcher cache and an unreachable input, the stock shell fails at `resolve-lock.nix:89` though the store holds the source. `devenv-nixpkgs` fetches its own `nixpkgs-src` outside that file | Agents H Q4, J Q4 |
| `NAT-029` | Two definitions of `machines.<host>.nixos`: two functions fail; two attribute sets merge shallowly and silently drop one side | Agent K Q7 |
| `NAT-030` | disko mounts by `/dev/disk/by-partlabel/disk-<disk>-<part>` by default. Labels come from the attribute names. With two same-named disks, the label pointed at the old disk after a reboot | `gpt.nix:81-90,146`; agent E Q1, Q2 |
| `NAT-031` | disko wipes only disks in its config. The legacy `diskoScript`, devenv's default, has no prompt. Destroy modes run `umount -Rv /mnt`. With `--disko-mode format`, devenv's install wrote the system into the running root | Agents E Q3, F Q2 |
| `NAT-032` | `canTouchEfiVariables = true` puts the new ESP first in `BootOrder`; `false` passes `--variables=no` and writes no entry; neither touches another drive's ESP. systemd-boot has no `efiInstallAsRemovable` | `systemd-boot-builder.py:35,498-499`; agents E Q5, F Q4 |
| `NAT-033` | Machines deploys to `root@localhost` from the same host. devenv run as root fails with "cannot remount /nix/store writable" unless `NIX_REMOTE=daemon` | Agents F Q5, G Q4 |
| `NAT-034` | A failed systemd unit makes `switch-to-configuration` exit 4, so the deploy fails and rolls back. A unit that failed before the deploy also makes the rollback fail | Agent G Q3 |
| `NAT-035` | Profiles defined in an imported module activate; profiles reached through `inputs.X.devenv.config` do not | Agent H Q8 |
| `NAT-036` | A `follows` deeper than one level is dropped without a message | `lib.rs:116-154`; agent H Q1 |
| `NAT-037` | devenv 2.4.0 `machines install` hangs at the first `nix copy` when the machine has install payloads; `a5fd551a` fixes it | Agent G Q5b |
| `NAT-038` | Plain `github:NixOS/nixpkgs` inputs let the fork CLI enter a shell with no network; `devenv-nixpkgs` does not | Agent J Q4 |

---

# 8. Out of scope

Vendomat is not and MUST NOT become a deployment engine, a second lock, a version solver, a daemon,
a retention engine, or a workspace orchestrator. devenv Machines deploys. Nix owns `flake.lock` and
`devenv.lock`. Each workspace stays a plain devenv project that imports one module.

## Count

V6 defines 78 new IDs: 8 `DVN`, 12 `VMOD`, 10 `PRE`, 1 `REG`, 4 `FACE`, 11 `MACH`, 1 `DISK`,
1 `CACHE`, 5 `DEL`, 1 `GEN`, 3 `CLI`, and 21 `NAT` facts. `DEL-014` is decided by `DEL-017`.
`FACE-004` is open. No new ID reuses a V5 ID. Section 0 supersedes 17 V5 IDs, narrows 3, withdraws 3, and
defers the active `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015`, `SYS-*`, and `MOD-*` IDs.

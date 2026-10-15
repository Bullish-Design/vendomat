# S8: proposal to move nix-systems to the project 21 catalog — 2026-10-15

Analysis and proposal only. Nothing in nix-systems, vendomat-demo, or any machine changed. Every
measurement used a temporary copy under `/tmp` (deleted after the run). Raw logs and the prototype
files: `~/.local/state/vendomat/p21/2026-10-15/s8/nix-systems-proposal/`.

Read this with [S8-CONSUMERS](S8-CONSUMERS.md) (the stop report of step 1), the
[implementation guide](../IMPLEMENTATION-GUIDE.md) section S8, and rulings R13, R21, R23, R33, R36,
R40, R42, R43, R49, R50, R52. Project 22 rulings R8, R9, R13 apply to the machine layer.

## 1. Summary

1. **The move works in a prototype.** A copy of nix-systems on `vendomat.yaml`, the S3 template
   inputs, and a hatch `devenv.nix` evaluates both machines (`machines.server` and
   `machines.framework`). The prototype is in section 4.
2. **nixpkgs is not a problem today.** nix-systems pins nixpkgs `e7439b6b…`. Vendomat pins the same
   revision with the same NAR hash. `nixpkgs: follows: vendomat/nixpkgs` gives the same
   `drvPath` (section 4). The risk is the future: one `vendomat update` that moves Vendomat's
   nixpkgs moves every machine.
3. **The catalog adds Harmonia to every machine.** That is the only intended closure change for
   `framework` (63 new derivations, section 4). `server` also changes its tools, which section 4
   names.
4. **Three things have no home and need a ruling:** the `disks` facts with the disk preflight (retired
   with patch 0006); the `apply` and `rollback` watch set, which excludes imported files; and
   the install route of `server` (R13 moved `install` to Basix).
5. **`main` of nix-systems cannot evaluate `machines.server` at its own pin.** Its server role sets
   `vendomat.libs.docman.enable`. Vendomat `v0.7.0-rc.1` has no such option (observed, section 2.5).
   Fix that first, so a baseline exists.
6. **Recommendations:** (a) keep machine content in the hatch and inventory as plain data, option 1;
   (b) follow Vendomat's nixpkgs, option 1; module settings: a free `settings` map, option 2.

## 2. Observations: what nix-systems uses

Source: nix-systems `main` `1346752a6313` ("chore: pin CopyRoom to v0.8.6"). The `default` workspace is
an empty commit above it. Tools: devenv 2.4.0+b904dcb (`/nix/store/axhrys71…-devenv-wrapped-2.4.0`),
Nix 2.34.7. The `secrets/` directory was not read. One command copied `secrets/secrets.yaml` (cipher
text, not read) into the temporary copy, because `nixos/server.nix` names it by path. The copy is gone.

### 2.1 `vendomat.toml` and `.vendomat/`

| Item | Value |
| --- | --- |
| `[forge] url` | `git://server` |
| `[targets]` | `devenv = true` |
| `devenv` | fork tag `v2.4.0-vendomat.2`, `dir=src/modules`, rev `e2acb5b0…` |
| `devenv-cli` | the same fork tag (no `dir`): the patched command line, used as a package |
| `vendomat` | GitHub tag `v0.7.0-rc.1`, rev `275bf06f…` |
| `repoman` `gitman` `testee` `docman` `copyroom` `devman` | GitHub tags `v0.12.1` `v0.13.0` `v0.5.0` `v0.3.1` `v0.8.6` `v0.8.0` |
| `[passthrough]` `sops-nix` | rev `dcd241ba…` |
| `[passthrough]` `disko` | rev `de570873…` (v1.13.0, pinned by commit) |
| `[passthrough]` `nixpkgs` | rev `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| `[passthrough]` `home-manager` | rev `6b88c12c…` |
| `[follows]` | nine inputs follow `nixpkgs`: `disko` `home-manager` `sops-nix` `repoman` `gitman` `testee` `docman` `copyroom` `devman` |
| generated | `.vendomat/devenv.nix` (a freshness assertion), `.vendomat/devenv.yaml`, `.vendomat/digest` |
| `devenv.yaml` | `require_version: "2.4.0"`; `imports: [ ./.vendomat ]` |

`devenv.lock` also holds transitive nodes (`pyjutsu`, `templateer`, `nixpkgs-src`, and devenv's own
inputs). They come with the listed inputs.

### 2.2 `devenv.nix` and `inventory/default.nix`

| Field | Where used |
| --- | --- |
| `imports = [ inputs.vendomat.devenvModules.default ]` | `devenv.nix` |
| `vendomat.inventory.<host>.mode` | read from `inventory.hosts.<host>.mode`; the old module sets `machines.<host>.vendomat.mode` and the preflight from it |
| `vendomat.inventory.<host>.disks` | read from `inventory.hosts.<host>.disks`; the old module builds `machines.<host>.vendomat.preflight.program` from it (`byId`, `role`, `model`, `serial`, `sizeBytes`) |
| `vendomat.inventory.<host>.nixos.imports` | `common ++ [ hardware, disk, delta, home-manager, home ]` for `server`; `common ++ [ framework.nix ]` for `framework` |
| `machines.<host>.system` | both hosts |
| `machines.server.target.host` and `.target.sshOpts` | `root@localhost`; options that name `.machines/server/known_hosts` |
| `machines.<host>.hardware.facter = null` | both hosts (the explicit hardware module stands in for a report) |
| `machines.server.install.copyHostKeys` | `true` |
| `machines.<host>.deploy.rollbackTimeout`, `.deploy.healthCheck` | both hosts |
| `_module.args = { inventory, inputs }` | passed to every NixOS module |
| `inventory.deployKey`, `.loginKeys` | `nixos/core.nix` |
| `inventory.hosts.server.ids`, `.disks.newsys` | `nixos/server-disk.nix` (disko layout) |
| `inventory.hostKeys.server`, `inventory.hosts.server.disks.oldsys`, `inventory.hosts.framework.*` | no reader in code; the old preflight read the disks |

### 2.3 NixOS modules that name Vendomat or input packages

| Line | Content |
| --- | --- |
| `nixos/server.nix` `vendomat.libs.docman.enable = true` | a library face (docman's flake exports a `vendomat` description) |
| `nixos/server.nix` `inputs.devenv-cli.packages.${system}.devenv` | the patched command line in `environment.systemPackages` |
| `nixos/server.nix` `inputs.vendomat.packages.${system}.launcher` and `.vendomat` | the launcher, and the host release at `/etc/vendomat/host-release` |
| `nixos/server.nix` gitman, jujutsu-bin, repoman, testee, copyroom packages | personal tools (project 22 moves them to the home) |
| `nixos/server.nix` `inputs.devman` | `nixosModules.default`, `lib.mkRegistry`, `services.devman-dagu` |
| `nixos/server.nix` `inputs.sops-nix` | `sops-nix.nixosModules.sops` |
| `nixos/server.nix` `services.atticd`, sops `attic-signing-key` | Attic. R39 and `VMT-127` say the new system configures no Attic |
| `nixos/core.nix` `nix.settings.substituters` | names the Attic cache `…/attic/vendomat` |
| `nixos/home.nix`, `home/andrew.nix`, `inputs.home-manager` | Home Manager inside the role. Project 22 R8 drops it |

### 2.4 Old-flow steps in the docs and tests

| File | Old step |
| --- | --- |
| `AGENTS.md` | "imports `inputs.vendomat.devenvModules.default`"; "write each host's module under `vendomat.inventory.<host>.nixos`"; "use `vendomat machine install`"; "`vendomat sync` writes `.vendomat/`"; "run `vendomat check`" (and the command block) |
| `README.md` | layout lines for `vendomat.toml`, `devenv.yaml imports: [ ./.vendomat ]`, `inventory`; install steps 1 to 3 (`vendomat check`, target preflight, `vendomat machine install server`) |
| `tests/run` | stage 1 serves a test collection of Vendomat, the fork, and a library; stage 2 `lock-and-build`; stages 3 and 4 boot VMs |
| `tests/core/lock-and-build` | `vendomat sync`, lock pins, `vendomat check`, `build machines.server.build.vendomatPreflight` |
| `tests/core/ws-prepare`, `tests/services/ws-prepare` | `sed` on `vendomat.toml` (forge URL, pinger input), then `vendomat sync` |
| `tests/core/vendomat-cli` | runs `vendomat.cli` from a checkout |
| `tests/core/devenv.local.nix`, `tests/services/devenv.local.nix` | `vendomat.inventory.vm`, `.svc`, `.svcbase` |
| `tests/core/plain-nixos.nix` | imports `nix/devenv-module/builder.nix` (the face builder). That file is absent from `v0.7.0-rc.1` and from the repository today |
| `tests/core/vm-flow` | library-face section with `vendomat.libs.pinger` |
| `tests/core/framework-tripwire` | `machines install` of `framework` is refused (patch 0005, mode from the module) |
| `tests/disk/*` | the preflight matrix; `matrix.py` sets `machines.server.vendomat.preflight.program` (patch 0006, retired in S6) |
| `tests/services/services-vm` | boots the unmodified server role; the unlanded commit changes it |

### 2.5 State of the repository

- **Unlanded work.** Workspace `v6-services-rerun` holds `f6de84c91ec1` ("test: services VM check
  runs the unmodified role only (fork .2, no fixes variants)"). It changes three files:
  `tests/services/devenv.local.nix`, `tests/services/overlay.nix`, and `tests/services/services-vm`.
  Its parent `fe848434` is an ancestor of `main`. Bookmark `v6-services-rerun` is on `origin`. The other
  four extra workspaces hold nothing that `main` lacks (checked with `jj log -r main..W@`; the empty
  `v6-server-role` and `v6-vm-core` heads are working-copy commits).
- **`main` does not evaluate `machines.server` at its pin.** Command, in a copy: `devenv eval
  machines.server.build.nixos.drvPath`. Result: `The option 'vendomat' does not exist` for
  `vendomat.libs.docman.enable` (log `eval-server-A0-as-committed.log`). Cause (inference, backed by
  reading): the face builder (`nix/devenv-module/builder.nix`) was retired in Vendomat commit
  `89bedc9d`, and the `v0.7.0-rc.1` tree has no such file (observed). The nix-systems tests serve a
  test collection from a Vendomat checkout (`VENDOMAT_TREE`) and tag it `v0.7.0`; I infer that tree
  still had the face builder. `framework` evaluates.

## 3. Mapping to the new flow

The prototype files are in `prototype-C/` of the log directory.

| Old item | New home | Note |
| --- | --- | --- |
| `[forge] url` | URLs in `devenv.yaml` | `git://server/...` |
| `[targets] devenv = true` | none | |
| `devenv` (fork `.2`) | `devenv.yaml`: `devenv: follows: vendomat/devenv` | Template line. Gives `v2.4.0-vendomat-modules.1` (`061c2184`) |
| `devenv-cli` (fork `.2`) | none as an input | The host binary replaces it (S2). The hatch line in `server.nix` becomes `inputs.vendomat.packages.${system}.devenv` (project 22 R13: the machine layer holds the binary) |
| `vendomat` (GitHub `rc.1`) | `devenv.yaml`: `vendomat: url: git://server/vendomat?ref=release` | R33: the workspace lock pins it |
| `repoman` `gitman` `testee` `docman` `copyroom` `devman` | `devenv.yaml` inputs, same tag URLs, `inputs.nixpkgs.follows: nixpkgs` | Keep them in the move. Project 22 removes the personal tools in a later change |
| `sops-nix` `disko` `home-manager` | `devenv.yaml` inputs, `github:...?rev=...`, `follows: nixpkgs` | Same text as the old fragment |
| `nixpkgs` rev pin | `devenv.yaml`: `nixpkgs: follows: vendomat/nixpkgs` | Same revision today (section 4). See (b) |
| `[follows]` nine entries | `inputs.nixpkgs.follows: nixpkgs` under each input | |
| `require_version`, `imports: [ ./.vendomat ]` | `imports: [ vendomat/devenv ]`; no `require_version` | R22 |
| `vendomat.toml`, `.vendomat/` | deleted | |
| `imports = [ …devenvModules.default ]` | deleted | The template import `vendomat/devenv` replaces it |
| `vendomat.inventory.<host>.nixos` | `machines.<host>.nixos` (hatch) | `nixos` is `deferredModule` (R14), so `imports = [ … ]` works. AGENTS rule flips |
| `….mode` | catalog: omit for `server`; `mode: adopt-existing` for `framework` in `vendomat.yaml` | R42. Neither host has a committed `facter.json`. Never leave `mode: fresh-install` in YAML after the install: it overrides R42 |
| `….disks` | **no home, needs a ruling** (N2) | |
| `machines.<host>.system`, `deploy.*`, `install.*`, `target.sshOpts` | hatch (native options) | |
| `machines.server.target.host` | hatch, not the YAML `host` key | The YAML `host` also becomes the peer address of `server` (`VMT-128`). `localhost` would be wrong for the other machines |
| `hardware.facter = null` | hatch | The YAML key `virtual: "true"` sets it too, but it means a test VM or an ISO (R23). Do not use it here |
| `.machines/<host>/known_hosts` | stays; the hatch reads it | |
| new `.machines/<host>/cache-key.pub` | committed after the first `vendomat apply` | `VMT-157`, `VMT-161` |
| Harmonia and its firewall opening | catalog, automatic (`serve` on) | New. `trustedInterfaces: [ tailscale0 ]` on `server` needs a Vendomat release that carries R52. `release` moved to v0.9.0 (`9b8885e3`) after the measurement, and v0.9.0 carries it |
| `vendomat.libs.docman.enable` | hatch line: `inputs.docman.packages.${system}.docman` in `environment.systemPackages` | Needs no ruling unless faces return. Project 22 may move docman to the home |
| launcher and host release lines | hatch, unchanged | They evaluate. Their run behaviour is not tested here |
| Attic (`services.atticd`, sops key, substituter) | out of scope for the move | Already ruled (R39, `VMT-127`). Remove in a separate change so the drvPath comparison stays clean |
| Home Manager and the personal-tool packages | out of scope for the move | Project 22 R8 and its nix-systems section. Separate change |
| `vendomat sync`, `vendomat check` | `devenv eval machines.NAME.build.nixos.drvPath`; `devenv build machines.NAME.build.nixos`; `vendomat explain` | `check` and `sync` go in S8 step 3 |
| `vendomat machine install` | Basix (R13) or native `devenv machines install` | Needs a ruling (N2) |

R42 and R13 in short: a committed `.machines/NAME/facter.json` marks a machine installed. Basix
writes it at install. Vendomat owns `apply`. Neither host has a report today, so `framework` needs
the explicit `mode` key. `server` stays unmarked until it installs.

## 4. Measurement: nixpkgs and the closure

**Method.** `devenv eval machines.NAME.build.nixos.drvPath` in copies under `/tmp/ns-measure/`. No
build, no `nixos-rebuild`, no sudo, no disk write. The evaluation wrote derivation files and fetched
inputs into the Nix store. Before the run: `btrfs filesystem usage -b /`: unallocated 32.07 GB,
metadata 77.09 % used, data 97.59 % used, free (estimated) 42.1 GB. `store diff-closures` was
skipped (it needs builds). The derivation closures came from `nix-store -qR` on each `.drv`.

**Variants.**

| ID | Description |
| --- | --- |
| A | Today's flow and lock, unchanged, except the `vendomat.libs.docman.enable` line removed from `server.nix` (the committed pin cannot evaluate it, section 2.5) |
| B | A, with `nixpkgs: follows: vendomat/nixpkgs` and no `follows` under `vendomat` (so no loop). `vendomat` stays at `v0.7.0-rc.1` |
| C | The new flow prototype: `vendomat` = `release` (`e5923a8f`, v0.8.0), `devenv` modules `061c2184`, `nixpkgs` follows Vendomat, `vendomat.yaml` with `server` and `framework`, a hatch `devenv.nix`, and `server.nix` with the two edits of section 3 |
| C2 | C with `serve: "false"` on both machines, to isolate the sharing module |

**Nixpkgs inputs (observed).** nix-systems `devenv.lock`: `nixpkgs_2` = `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, NAR
`sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=`. Vendomat `flake.lock` (tag `v0.7.0-rc.1`
and `main`): the same rev and NAR hash.

**drvPath results (observed).**

| Machine | Variant | drvPath |
| --- | --- | --- |
| framework | A | `/nix/store/s29rq0ml5zrgnjd85scv0azbwv1px16a-nixos-system-framework-26.11.20261008.e7439b6.drv` |
| framework | B | `/nix/store/s29rq0ml5zrgnjd85scv0azbwv1px16a-…` (identical to A) |
| framework | C | `/nix/store/7zzvhgc05gd3d6vcw47jk7zs2bmzfsgs-…` |
| framework | C2 | `/nix/store/s29rq0ml5zrgnjd85scv0azbwv1px16a-…` (identical to A) |
| server | A | `/nix/store/9kdrr6lx18cmcsgi1m0nndp8yjz1ikf1-nixos-system-server-26.11.20261008.e7439b6.drv` |
| server | B | `/nix/store/9kdrr6lx18cmcsgi1m0nndp8yjz1ikf1-…` (identical to A) |
| server | C | `/nix/store/1pgq6zhmvr97w27ak2rgi9cxfzfwyaff-…` |
| server | C2 | `/nix/store/khg9a2df0z8a565i7xkxpdyyivay462h-…` |

**Derivation closure sizes (observed, `nix-store -qR`).** Framework: A 4357, C 4408 (12 paths only in
A, 63 only in C). Server: A 11133, C 6946, C2 6937 (4664 paths only in A, 477 only in C).

**Reading (inference from the derivation names).**

- Following Vendomat's nixpkgs changes nothing today (A = B, both machines). The input is the same
  tree.
- `framework` differs from A only by the sharing module: C2 equals A, and the 63 new derivations in C
  are `harmonia-3.3.0` (with its vendored crates), `harmonia.toml`, and the units. The difference is
  new design (R39), not a nixpkgs effect. BOOT-010 is met: the result is the same, or the
  difference is named (Harmonia).
- `server` differs for two more reasons. (1) The old closure builds the fork `.2` command line from
  its own tree (about 4.6k derivations: crates, `devenv-nixpkgs` sources). C takes the host binary
  from Vendomat's nixpkgs (`devenv-2.4.0`, `nix-*-2.35`, `nixd`, `cargo-nextest`, `libghostty-vt`,
  `vendomat-0.8.0`). (2) The sharing module adds 8 more names (Harmonia, `vendomat-cache-key`
  units).
- Not measured: a build, a store-path difference count, boot behaviour, and a Vendomat release with
  a different nixpkgs.

## 5. Options for the open design points

### (a) Where inventory, disks, and per-host NixOS imports live

| Option | What | Pros | Cons |
| --- | --- | --- | --- |
| 1 | Hatch holds machine content. `devenv.nix` has `machines.NAME.nixos.imports`, `target`, `deploy`, `install`, `hardware`. `inventory/default.nix` stays plain data. `vendomat.yaml` lists the machines with catalog keys only (`mode`, `serve`, `trustedInterfaces`, `programs`). | Smallest change. The prototype evaluates. R6 and R12 intend the hatch for this use. `nixos/*.nix` keep their shape. | Two files name each machine. `disks` has no consumer except `server-disk.nix`, so `role`, `model`, `serial`, `sizeBytes` enforce nothing until N2 is ruled |
| 2 | New catalog keys for per-machine `disks` and a list of module files. | Machine facts sit in the YAML. | Grows the catalog beyond the 90 % path (owner rule: simplicity first). Disk checks belong to Basix (R13, R16). Module paths in YAML move Nix concerns into text |
| 3 | Typed inventory module in nix-systems: `nixos/inventory.nix` declares options (disks, keys) with assertions (no kernel names; a `keep` disk never reaches disko). | Keeps the safety intent of the old preflight at evaluation time. No Vendomat change. | More code in nix-systems. It does not check the live disk (model, serial, blank): only a hook can |
| 4 | Make nix-systems a Basix workspace. | One layering story. | Basix is a learner distribution and outside the owner's personal layer (project 22). Not wanted |

**Recommendation: option 1 now, with option 3 as a follow-up.** Rule on the disk guard separately (N2).
Option 2 may return if several consumers want the same keys (promotion rule, concept).

### (b) nixpkgs: follow Vendomat or keep a pin

| Option | What | Pros | Cons |
| --- | --- | --- | --- |
| 1 | `nixpkgs: follows: vendomat/nixpkgs` (the template). | Same closure now (section 4). One tested pair (R28). The host tools, Harmonia, and the machines come from one nixpkgs, so cache hits stay high. No template exception. | Each `vendomat update` that moves Vendomat's nixpkgs moves every machine. Review the `drvPath` change before `apply` |
| 2 | Hatch override: keep `nixpkgs: url: github:NixOS/nixpkgs?rev=…` in `devenv.yaml`. | Machines move only when the owner moves the rev. | Two nixpkgs trees: Vendomat's packages (host `devenv`, Harmonia, launcher) differ from the machine's. `vendomat update` may rewrite the line (not tested). The workspace `pkgs` and the machine `pkgs` stay equal only because both use the input |
| 3 | Follow, and hold: pin `vendomat` to a tag and update on purpose. | Same as option 1, with a stable pin. | `release` is a moving branch; a tag needs the collection to hold one (the lock already pins the rev) |

**Recommendation: option 1.** BOOT-010 is met today: zero difference for nixpkgs. Keep the nixpkgs
line free of overrides. The lock already holds the revision, so `devenv.lock` is the hold. Add a
check to nix-systems that prints the `drvPath` of both machines, and run it before and after every
`vendomat update`. Switch to option 2 only if an update moves nixpkgs when the owner does not want
that. The switch is one line.

### Module settings: the general gap

vendomat-demo found it: its two authored modules define `vendomat.settings.greeting.text` and
`vendomat.settings.marker.label`. The catalog has no key for them, so the values sit in `devenv.nix`
(`vendomat explain` lists them under "Set only in Nix"). nix-systems does not need this key: its
NixOS settings belong in the hatch. The gap affects workspaces with authored modules.

| Option | What | Pros | Cons |
| --- | --- | --- | --- |
| 1 | Hatch only (today). | No change. | A workspace user needs a Nix edit. Breaks R6 for authored modules |
| 2 | A free `settings` map. `settings: MODULE: FIELD: text` maps to `vendomat.settings.MODULE.FIELD` as plain definitions (R23, `_file = vendomat.yaml`). The catalog declares no option. The authored module declares its own options. | One key. The module system rejects an unknown module or field with the file name. `explain` can list it. | Values are text, so each module option must accept text (`"true"`). Faults have no line number (like `VMT-035`) |
| 3 | Modules export a schema (like docman's `vendomat` description); the catalog builds typed keys. | Typed, line-numbered errors. | Large. It revives the retired description and face builder (`DESC-002`). Needs a format ruling |
| 4 | The authored module reads `config.vendomat.parsed` itself. | No catalog change. | The schema must still allow a free top-level key. Each module re-implements checks. `explain` cannot map the key |

**Recommendation: option 2.** It restores the demo's claim with one key, and option 3 can replace it
later without a file format change. A per-machine form (`machines.NAME.settings`) would close the same
class of gap as `VMT-172` did, but this proposal does not rule on it.

## 6. Items that need a ruling

| # | Question | Options | Recommendation |
| --- | --- | --- | --- |
| N1 | Unlanded `f6de84c91ec1` | land it, drop it, or keep it | Land it first (3 files, tests only, parent on `main`): rebase it onto `main` in its own workspace, verify, land. The move rewrites `tests/services` afterward. If the owner drops it, record why |
| N2 | The `server` install and the disk guard. `vendomat machine install` goes (R40). Patch 0006 is gone, so `disks` (`role: keep`, model, serial, size) guards nothing. Stock `devenv machines install` kexecs the target before disko | (i) Basix ISO local install with the Basix guard (R13, R16); (ii) native remote install to self with a nix-systems `preCreateHook` guard built from `inventory.disks`; (iii) keep both open until S7 | (i) for the real disk write, which needs the owner's separate approval. Until then record a named blocker, and keep `disks` as data. Do not run any install |
| N3 | `apply` and `rollback` watch `vendomat.yaml`, `devenv.lock`, `devenv.nix`, `devenv.local.nix`. Files that the hatch imports (`nixos/*.nix`, `inventory/default.nix`) are not watched (`VMT-163`). A default rollback restores only watched paths | (i) `rollback --exact` as the nix-systems habit; (ii) widen the watch set (Vendomat change); (iii) keep all machine content in `devenv.nix` | (i) now; raise (ii) as a gap (`VMT-180`) |
| N4 | The `vendomat.libs` face (docman) | plain package line; or revive faces | Plain package line |
| N5 | Attic and Home Manager in the server role | remove with the move, or later | Later, as separate changes (R39; project 22 R8) |

## 7. Step list for a later agent

Work in a nix-systems workspace, with Gitman and jj only. Run no install, no `nixos-rebuild`, no
activation, and no disk command. Use `devenv eval` and `devenv build machines.NAME.build.nixos`
only after a `btrfs filesystem usage -b /` check.

0. **Resolve `f6de84c91ec1` (N1).** The owner decides. If the owner says land: in workspace
   `v6-services-rerun`, rebase onto `main`, verify with the repository's own check
   (`tests/run`, needs `/dev/kvm`), land on `main`, remove the workspace. List all nix-systems
   workspaces first and report any work that `main` lacks. Do not start step 1 before this ends.
1. **Rule N2, N3, N4, and the open choices (a) and (b).** Record each as a ruling in project 21
   (R53 onward) or as a named blocker.
2. **Fix the baseline.** In a new workspace, remove `vendomat.libs.docman.enable` from
   `nixos/server.nix` and add `inputs.docman.packages.${system}.docman` to
   `environment.systemPackages`. Evaluate both `drvPath` values (copy method of section 4) and
   record them. Land this as its own commit.
3. **Pick a Vendomat release.** Use a `release` revision that has the catalog keys the move needs
   (`trustedInterfaces`, R52, `VMT-173`). On 2026-10-15 `release` is v0.9.0 (`9b8885e3`). Check
   `git ls-remote git://server/vendomat release` first. Repeat the section 4 measurement on that
   revision, because the prototype used v0.8.0.

4. **Rewrite the inputs.** Create `devenv.yaml` as in `prototype-C/devenv.yaml` (template lines first,
   then the carried inputs). Delete `vendomat.toml` and `.vendomat/`. Run `devenv update`. Check that
   `nixpkgs` in `devenv.lock` is still `e7439b6b…` and that `devenv-cli` is gone.
5. **Write `vendomat.yaml` and the hatch.** Machines `server` and `framework`; `mode:
   adopt-existing` for `framework`; `trustedInterfaces: [ tailscale0 ]` for `server`. Move
   `machines.NAME.nixos.imports`, `target`, `deploy`, `install`, and `hardware.facter` into
   `devenv.nix` (see `prototype-C/devenv.nix`). Keep `target.host` in the hatch. Replace the
   `devenv-cli` package line with `inputs.vendomat.packages.${system}.devenv`.
6. **Compare.** Evaluate both `drvPath` values. Expect `framework` to differ by Harmonia only
   (63 derivations in the prototype) and `server` to differ by the host tools and Harmonia. Name every
   difference in the commit message (BOOT-010). Run `vendomat explain` and check the machine keys.
7. **Rewrite the docs.** `AGENTS.md`: delete the rules about `vendomat.inventory`, `vendomat sync`,
   `vendomat check`, and `vendomat machine install`. Add: write machine content in the hatch; keep
   `devenv.lock` committed; evaluate the `drvPath` before and after a `vendomat update`; install is
   out of scope until N2 ends. `README.md`: update the layout and the install summary.
8. **Rewrite the tests.** Replace `ws-prepare` (use a `devenv.local.yaml` or `sed` on `devenv.yaml`
   for the loopback forge), `lock-and-build` (no `sync`, `check`, or preflight build), the two
   `devenv.local.nix` files (`machines.vm` in the hatch), `plain-nixos.nix` (no face builder),
   `vm-flow` (drop the library-face section or use a plain module), and `vendomat-cli`. Decide the
   fate of `tests/disk` by N2. Keep `core-vm` and the `framework-tripwire` cases; the tripwire now
   reads `mode` from the catalog.
9. **Prove in a VM.** Run the repository's VM checks on disposable images. No real host and no real
   disk.
10. **Land and tell Vendomat.** Land the nix-systems change. Then S8 step 3 in this repository may
    remove the TOML flow. Update the S8 row of `PLAN.md` and `CURRENT.md`.
11. **Later, separate changes:** remove Attic (R39), Home Manager (project 22 R8), and the personal
    tools from the server role; commit `.machines/NAME/cache-key.pub` after the first `apply`; commit
    `facter.json` after the real install.

## 8. Limits

- No build ran. The `drvPath` values prove evaluation only.
- A is not today's real closure: the committed pin cannot evaluate `server` (section 2.5). The
  `docman` face adds one package that A lacks.
- The host binary evaluated all variants, not the fork `.2` command line. The failure in section 2.5
  is an option error, which I infer does not depend on the binary.
- The prototype used `release` `e5923a8f` (v0.8.0). `release` is now v0.9.0 (`9b8885e3`); the
  prototype was not re-measured on it.
- Launcher, host-release, Dagu, sops, and the services were not run.
- `jj` reads in nix-systems used `--ignore-working-copy` after the first `jj log`. No file changed
  (checked with `find -mmin`).

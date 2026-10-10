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
| `DEL-012` | Superseded | `DEL-019`: the Vendomat flake also exports the devenv module (the chain is `DEL-015`, `DEL-018`, `DEL-019`) |
| `DEL-003` | Superseded | `MOD-013`: no `mkModules` helper exists, so no library needs a Vendomat input |
| `DEL-004` | Superseded | `DEL-016`: `nix-meta` is retired |
| `GEN-022` | Superseded | `GEN-023`: a workspace shell is a devenv project |
| `GEN-017` | Kept | It covers the flake target only. The module builds faces from descriptions (`VMOD-013`), not the generator |
| `REG-021` | Superseded | `REG-022`: adds `[imports]` and `[targets]` |
| `CACHE-001` | Superseded | `CACHE-010`: the host core sets the substituter |
| `CLI-001` | Superseded | `CLI-021` (the chain is `CLI-017`, `CLI-021`) |
| `CLI-011`, `CLI-012`, `CLI-013` | Superseded | `MACH-005`: activation and rollback through devenv Machines |
| `CLI-005`, `CLI-008` | Deferred | Not built in V5 0.6.0 and not in `CLI-021`. Decide with `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015` |
| `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015`, `SYS-001` to `SYS-010` | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `MOD-001`, `MOD-002` | Superseded (owner 2026-10-09: Vendomat builds the modules from a library description) | `MOD-001` → `DESC-002` (through `DESC-001`); `MOD-002` → `FACE-005` |
| `MOD-004`, `MOD-006` | Superseded | `DESC-002`: `packages` is `pkgs: [ derivation ]` and `extra` is `{ cfg, pkgs, lib }: { devenv; nixos; homeManager }` |
| `MOD-003`, `MOD-005`, `MOD-008` to `MOD-010` | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `BOOT-008`, `BOOT-010` | Withdrawn 2026-10-09 | Blank slate: no capability parity and no tree comparison |
| `BOOT-009` | Withdrawn 2026-10-09 | No conversion step exists. `BOOT-001` keeps the core free of Vendomat |
| `BOOT-019` | Superseded | `BOOT-026`: no laptop install exists; Framework is adopted in place |
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
| `DVN-009` | *Proposed.* The patched `devenv machines install` MUST refuse a host whose mode is `adopt-existing` at the start of the command, before SSH, payload preparation, kexec, facter, disko, install, or reboot, for every `--phases` selection and every `--disko-mode` | A phase-matrix fixture: each call exits non-zero and a tripwire target sees no contact |

---

# 2. The Vendomat devenv module

| ID | Requirement | Verify |
| --- | --- | --- |
| `VMOD-001` | Every workspace and `nix-systems` MUST import `inputs.vendomat.devenvModules.default`. The `vendomat` input MUST pin a release tag in the collection | The lock's `vendomat` node has `original.ref = refs/tags/…`; the shell has the module's options (agent K Q8) |
| `VMOD-002` | A face that the module imports but that is not enabled MUST NOT change the shell derivation | `devenv build shell` gives the same store path with and without the import (agent K Q1). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): shell, NixOS toplevel, and Home Manager activation derivations are equal with and without a disabled described library |
| `VMOD-003` | *Superseded by `VMOD-013` (2026-10-09).* The module imported each input's `devenvModules.default` | — |
| `VMOD-004` | A check that must stop shell entry MUST be an assertion. A task MAY report a warning | A failing assertion makes `devenv shell -- true` exit non-zero; a failing task does not (agents I Q5, K Q2). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): a branch pin makes `devenv shell -- true` exit non-zero |
| `VMOD-005` | The module MUST assert that every git node in `devenv.lock`, direct or transitive, has `original.ref` under `refs/tags/` and a 40-hex `locked.rev`. `vendomat.check.enable = false` MUST turn the check off | A branch ref stops the shell and names the node; the option turns it off (agent K Q2). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): a `refs/heads/` git node stops the shell and names the node; a tag passes |
| `VMOD-006` | Every Vendomat command that builds or pushes MUST run the same checks first, because devenv does not evaluate assertions for `devenv build` or `devenv eval` | `vendomat push` with a branch ref in the lock exits non-zero and pushes nothing |
| `VMOD-007` | With `vendomat.cache.push = true` and `vendomat.cache.name` set, the module MUST provide a `vendomat:push` task and a `vendomat-push` script that pipe the built output paths to `attic push <name> --stdin` | A stand-in `attic` receives exactly the `devenv build` paths (agent K Q3). **Open:** a push to the real Attic |
| `VMOD-008` | Everything the module puts under `outputs` MUST be a derivation. `vendomat.inputPaths` MUST give each input's store path, and an output MUST carry them as a JSON file whose closure holds every input source | `devenv eval vendomat.inputPaths`; `nix-store -qR` of the output lists the sources (agent K Q4). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): `vendomat.inputPaths` and the output closure hold every input source |
| `VMOD-009` | `vendomat.paths` MUST be `attrsOf str`, default from `/etc/vendomat/paths.json`, and MUST export `VENDOMAT_PATH_<NAME>`. A missing file MUST give `{}`. Implements `PATH-001` to `PATH-004` | The shell shows the variables (agent K Q5). **Open:** the real host file. **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): `VENDOMAT_PATH_*` variables and a missing file giving `{}`. The real host file is still open |
| `VMOD-010` | Host and user defaults MUST use `profiles.hostname.<host>` and `profiles.user.<user>` with `lib.mkDefault`, so a workspace can override them | The defaults apply on the named host; a workspace value wins (agent K Q6). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): the profile default applies on this host; a workspace value wins. The option names are `vendomat.hosts` and `vendomat.users` |
| `VMOD-011` | The module MUST own `machines.<host>.nixos`. The owner MUST write `vendomat.inventory.<host>.nixos`. Any other definition of `machines.<host>.nixos` MUST fail evaluation, naming the host | Agent K Q7: a direct definition fails with "is also defined outside vendomat.inventory". **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): a direct definition is refused naming the host |
| `VMOD-012` | *Superseded by `VMOD-016` (2026-10-09).* For each host, the module asserted that every disko disk is an `install-target` `by-id` path and that no filesystem device uses `by-partlabel` or a kernel name | — |
| `VMOD-013` | The module MUST build a devenv module from each flake input's `vendomat` description (`DESC-002`) and import it. For an input with no description, it MUST import the input's hand-written `devenvModules.default`, if any. An input with both MUST be an error naming it. Two inputs with the same `name` MUST be an error naming both. Vendomat itself, `devenv`, `nixpkgs`, and `self` are skipped | Agent L Q1, Q3: identical shell derivation when disabled; both error messages. **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): duplicate names, a description plus a hand-written face, a missing name, an unknown key, and options that define `enable` each stop evaluation naming the input |
| `VMOD-014` | In `nix-systems`, the module MUST build the NixOS module from each description and add it to each host through the inventory. The NixOS module MUST add the Home Manager module through `home-manager.sharedModules` when the host imports `home-manager.nixosModules.home-manager` (`MACH-017`). Host-side values go in `vendomat.inventory.<host>.nixos` as `vendomat.libs.<name>.*`; user-side values as `home-manager.users.<user>.vendomat.libs.<name>.*` | Agent L Q4: disabled gives an identical toplevel; enabled installs the package, the system unit, and the user unit. **Open:** the units running on a VM. **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`) and `tests/nix/faces-vm.nix` (a NixOS VM: the system unit, the Home Manager user unit, and the start-script PATH ran) |
| `VMOD-015` | The module MUST also import a library's hand-written `nixosModules.default` and `homeManagerModules.default` into each host, as it does for described libraries | A hand-written NixOS face is present on a host build. **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): a hand-written devenv and NixOS face is present on a host build and in the shell |
| `VMOD-016` | *Proposed (machine-path research 2026-10-09).* Each inventory host MUST set `mode` to `fresh-install` or `adopt-existing`, and the mode MUST reach the machine metadata that `DVN-009` reads. In `fresh-install` mode, every `disko.devices.disk.*.device` MUST be an `install-target` `by-id` path of the inventory, and no `keep` or `existing-system` disk MAY be a disko device. In `adopt-existing` mode, there MUST be no `disko.devices.disk`, no `install-target`, and at least one `existing-system` disk. In both modes, no `fileSystems.*.device` MAY use `by-partlabel` or a kernel name, unless the filesystem is virtual, mapped, or temporary. `vendomat.check.enable = false` MUST NOT disable these assertions | `devenv build machines.<host>.build.nixos` fails on each bad layout with a named message and passes on a good one, in both modes (direct NixOS build fixtures). **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): 12 bad layouts fail a direct build with a named message and two good layouts pass, in both modes |
| `VMOD-017` | The builder MUST skip these inputs: `self`, `devenv`, `nixpkgs`, Vendomat itself (by store path), and the infrastructure inputs `disko`, `home-manager`, and `sops-nix`. The machine layer imports the infrastructure inputs, and their default modules are not Vendomat faces. A `flake = false` input has no face and is skipped by shape. Supplements `VMOD-013` | Same fixture: a library named `disko` or `home-manager` is not read |

---

# 3. The pre-resolver

| ID | Requirement | Verify |
| --- | --- | --- |
| `REG-022` | A top-level table other than `[forge]`, `[inputs]`, `[passthrough]`, `[follows]`, `[imports]`, and `[targets]` MUST be an error naming it. `[inputs]` MUST be present | Unit tests |
| `REG-023` | An `[inputs]` or `[passthrough]` entry MAY set `dir`, a relative path inside the input's source. `sync` writes it as the `dir` URL query parameter. A path that leaves the input is an error | Unit tests; the fragment URL of a `dir` entry ends in `dir=<path>` |
| `REG-024` | `[imports]` maps a direct input name to one directory or a list of directories (`"."` names the source root). `sync` writes each as `<input>/<dir>`. A name that is not a direct input is an error. A registry with no `[targets]` table selects the flake target only. A `[targets]` table selects what it names and MUST select at least one | Unit tests (`tests/test_registry_v6.py`) |
| `PRE-001` | `[targets]` MUST select the outputs: `devenv = true` writes the fragment; `flake = true` writes `flake.nix` by `GEN-005` to `GEN-021`. Both MAY be set | Unit tests for each combination |
| `PRE-002` | With the devenv target, `vendomat sync` MUST write `.vendomat/devenv.yaml`, `.vendomat/devenv.nix`, and `.vendomat/digest`. A workspace `devenv.yaml` of only `imports: [ ./.vendomat ]` MUST lock every fragment input into the workspace's own `devenv.lock` | Agent I Q1. **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): a three-level chain locks every input with a 40-hex revision |
| `PRE-003` | For each `[imports]` entry `<input>/<dir>`, `sync` MUST read that directory's `devenv.yaml` from the input's source and add its inputs as top-level inputs, recursively. Two imported files with different URLs for one name MUST be an error naming both. A registry entry wins and `sync` MUST report it | Agent I Q3 (the conflict path is not yet run). **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): three levels, one lock node per source. Conflict, cycle, and registry-wins cases: `tests/test_devenvgen.py` |
| `PRE-004` | `sync` MUST NOT write a `follows` deeper than one level. It MUST express a nested edge as a top-level input plus one-level `follows` | Agent I Q4: one node per source. **V6 fixture:** `tests/test_devenvgen.py`: only one-level `follows` are written; deeper edges are reported |
| `PRE-005` | `sync` MUST add `<input>.inputs.<name>.follows = <name>` for every child that shares a top-level source, and MUST report a child whose source differs instead of following it | Lock node count per source is one (agent I Q3). **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): `shared` has one node although four flakes declare it |
| `PRE-006` | `.vendomat/devenv.nix` MUST assert that the digest exists, that `vendomat.toml` matches the recorded hash, and that the fragment matches the recorded hash | Each case exits 1 with its message (agent I Q5). **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): a registry edit and a hand edit each stop `devenv shell` with a named message |
| `PRE-007` | `sync` MUST warn when the workspace `devenv.yaml` or `devenv.local.yaml` redeclares a generated input, because that entry replaces the generated one entirely | Fixture: a redeclared input with `follows` in the fragment prints the warning (agent I Q2 shows the replacement). **V6 fixture:** `tests/test_devenvgen.py`: a redeclared input gives a warning |
| `PRE-008` | `sync` MUST judge a lock update by the lock contents and the error text, never by the exit status of `devenv update` | An unreachable input makes `sync` exit non-zero, though `devenv update` exits 0 (`NAT-026`). **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): `devenv update` of an unreachable input leaves the prior lock and exits 2 |
| `PRE-009` | A `use_vendomat` direnv function MUST re-sync only when the digest is stale, then run `use devenv` | Agent I Q6: about 0.35 s with no change. **V6 fixture:** `tests/test_use_vendomat.py` (stale cases and a failed sync). Direnv itself is not run |
| `PRE-010` | The fragment MUST add no measurable time to a warm shell entry and at most 100 ms to a full evaluation | Agent I Q7: 0.173 s against 0.175 s warm; +65 ms full. **V6 fixture:** `tests/test_devenv_sync_e2e.py` (Testee run `20261010T021235Z-496f611f02bf`): an unchanged `sync` took 0.142 s with the source daemon stopped |
| `PRE-011` | `sync` MUST replace generated files atomically with a new modification time, and MUST clear `.devenv` evaluation state when the inputs change | Agent L Q3 saw a stale result after swapping same-size, same-mtime `devenv.yaml` files with `.devenv` kept. Cause UNPROVEN. **V6 re-run (2026-10-09, stock 2.4.0, evaluation cache on, `.devenv` kept):** the stale result did NOT reproduce, so `sync` clears `nix-eval-cache*` only when the fragment content changes, as a precaution |

---

# 4. Faces

| ID | Requirement | Verify |
| --- | --- | --- |
| `FACE-001` | *Superseded by `FACE-006` (2026-10-09).* A library exported its faces as flake modules | — |
| `FACE-002` | Each face MUST declare `<name>.enable`, default false, and change nothing until it is true (`INP-006`) | The library's check evaluates each face alone and compares the result with and without the import |
| `FACE-003` | Each library's verification MUST evaluate every exported face alone | The library's Testee gate runs the check |
| `FACE-007` | The inertness check MUST compare the shell, NixOS toplevel, and Home Manager generation derivations with and without the library, on a workspace that sets none of the library's options | `../15-devenv-alignment/prototypes/face-check.sh`: PASS for a described library, FAIL for a leaky hand-written module (agent L Q6) |
| `MOD-011` | *Superseded by `MOD-013` (2026-10-09).* The helper was exported to libraries as `lib.mkModules` | — |
| `MOD-012` | *Superseded by `MOD-013` (2026-10-09).* | — |
| `MOD-013` | The module builder MUST live inside the Vendomat module, never in a library. Libraries MUST NOT need a Vendomat input to be described. Every module it builds MUST pass `FACE-002` and `FACE-003` | A described library's `flake.lock` has no `vendomat` node; the built modules pass the face check (agent L) |
| `DESC-001` | *Superseded by `DESC-002` (2026-10-09), after agent L's fixture.* The proposed description shape | — |
| `DESC-002` | A library's `vendomat` description MUST be an attribute set with: `name` (string, required; a missing name fails and names the input); `packages` (`pkgs: [ derivation ]`; use `pkgs.stdenv.hostPlatform.system` to select the library's package); optional `options` (`lib: { … }`, which MUST NOT define `enable` or `service`); optional `service` (`{ pkgs, cfg }: { exec = "<command>"; }`; only `exec` is read); optional `extra` (`{ cfg, pkgs, lib }: { devenv ? {}; nixos ? {}; homeManager ? {}; }`, plain configuration, applied only when enabled). It MUST use only the `pkgs` and `lib` passed in | Agent L: `../15-devenv-alignment/prototypes/library-description-example.nix`; the library's lock holds only `nixpkgs`. **V6 fixture:** `tests/test_devenv_module_e2e.py` (Testee run `20261010T022850Z-82b3e6de8adb`): description keys are checked; `enable` and `service` are reserved |
| `DESC-003` | The builder MUST run a service's `exec` through a `<name>-start` script that puts the library's packages on `PATH`. In devenv, an enabled library with a `service` gets `processes.<name>` with no second switch; in NixOS and Home Manager, `service.enable` (effective only with `enable`) adds a system or user unit | Agent L Q1, Q4: `ExecStart` is the start script; the process ran under `devenv up`. **V6 fixture:** `tests/nix/faces-vm.nix` and `tests/test_devenv_module_e2e.py::test_the_devenv_process_runs_under_devenv_up` |
| `FACE-004` | *Decided 2026-10-09, see `FACE-005`.* Option paths | — |
| `FACE-005` | Every module that Vendomat builds, and every hand-written face, MUST put its options under `vendomat.libs.<name>.*` in all three targets: `enable` (default false), the library's own options, and `service.enable` for a daemon in NixOS or Home Manager | Evaluate each target; the options exist only at that path |
| `FACE-006` | A library SHOULD export a `vendomat` description (`DESC-002`). It MAY instead export hand-written `devenvModules.default`, `nixosModules.default`, or `homeManagerModules.default` that follow `FACE-005` (`MOD-009`) | `nix flake show` of the library |

---

# 5. Machines and `nix-systems`

| ID | Requirement | Verify |
| --- | --- | --- |
| `MACH-001` | *Superseded by `MACH-023` (2026-10-09).* `nix-systems` MUST be a devenv project that defines `machines.server` and `machines.framework` through `vendomat.inventory`, with one shared core module and one delta module per host | — |
| `MACH-002` | *Superseded by `MACH-019` (2026-10-09).* Machines and workspaces MUST use a plain `github:NixOS/nixpkgs/<rev>` of nixos-unstable, not `devenv-nixpkgs` | — |
| `MACH-003` | *Superseded by `MACH-015` (2026-10-09).* `nix-systems` MUST declare `disko`, and `home-manager` when a host has a Home Manager role. Each host MUST commit `.machines/<host>/facter.json` or set `hardware.facter = null` | — |
| `MACH-004` | Each host MUST accept the owner's deploy key for root, key-only (`PermitRootLogin prohibit-password`, no password login). devenv MUST run as the owner, not as root | A self-deploy as the owner to `root@localhost` succeeds (agents F Q5, G Q4) |
| `MACH-005` | Activation, status, and rollback MUST use `devenv machines plan`, `deploy`, `apply`, `status`, and `rollback`. Vendomat MUST NOT wrap them | Agent G Q3 |
| `MACH-006` | Every host MUST set `deploy.healthCheck`. Every service MUST start cleanly; a host MUST NOT be deployed while a unit is failed | `systemctl --failed` is empty before a deploy; a failing health check rolls back (agent G Q3) |
| `MACH-007` | A host with install payloads (`install.secrets`, `install.extraFiles`, `install.encryptionKeys`) MUST be installed with a CLI that carries `a5fd551a`. An `install.extraFiles` key MUST NOT contain a dot | Agent G Q5b. **Open:** a runtime install with the fork CLI |
| `MACH-008` | `server` MUST be installed on the 4 TB drive by `vendomat machine install server`: the preflight (`MACH-016`), then `devenv machines install server --phases disko,install` with the default disko mode, from the running `server` to `root@localhost`. It MUST refuse `--disko-mode format` and `mount`, and MUST unmount `/mnt` afterwards | VM: the old disk's partition table, ESP files, and NVRAM unchanged; the new disk boots alone (agent F Q2). **Open:** the real hardware |
| `MACH-009` | The first install MUST set `boot.loader.efi.canTouchEfiVariables = false`. The new system MUST be tried once with `efibootmgr -C` and `efibootmgr -n`. It MUST become the default only after it has run reliably | VM (agent F Q4). **Open:** the real firmware keeps the entry and honours `BootNext` |
| `MACH-010` | *Superseded by `MACH-016` (2026-10-09).* Before disko runs, the preflight MUST check on the target: the `by-id` path resolves; model, serial, and size match the inventory; `wipefs --no-act` and `blkid -p` show no signature; the disk does not back `/` or `/boot`; nothing is mounted under `/mnt`; `.machines/<host>/facter.json` is committed. Any mismatch or unknown result MUST stop it. Implements `DISK-002` and `DISK-003` | — |
| `MACH-011` | *Superseded by `MACH-014` (2026-10-09).* `framework` MUST be installed from `server` with `devenv machines install`, with its own facter report | — |
| `MACH-012` | *Superseded by `MACH-017` (2026-10-09).* On `server` and `framework`, Home Manager MUST run inside the NixOS role (`home-manager.nixosModules.home-manager`), so a system rollback also restores the home configuration. A separate `machines.<host>.home-manager` role is only for a host that does not run NixOS | — |
| `MACH-013` | *Superseded by `MACH-018` (2026-10-09).* nixpkgs MUST be plain `github:NixOS/nixpkgs` on nixos-unstable. Each Vendomat release MUST carry one tested nixpkgs revision as the default `nixpkgs` input that `sync` writes; a workspace MAY override it, and `sync` MUST report the override | — |
| `MACH-014` | *Proposed.* A host in `adopt-existing` mode MUST be adopted in place with `devenv machines plan` and `apply`, or `deploy` with a host name. No `install`, `kexec`, `facter`, `disko`, `nixos-install`, or `reboot` phase MAY run for it | An adoption VM: partition table, GUIDs, UUIDs, mounts, and selected data hashes match before and after; the new generation boots and rolls back (`fixtures/VM-TEST-PLAN.md` A1) |
| `MACH-015` | *Proposed.* Every NixOS role MUST pin a `disko` input, because Machines evaluation imports its module. An adopted host MUST declare no `disko.devices.disk`. Each host MUST commit `.machines/<host>/facter.json`, or set `hardware.facter = null` and keep its existing hardware module | Direct NixOS builds of one fresh and one adopted fixture host pass; adding a disko disk to the adopted host fails |
| `MACH-016` | *Proposed.* Before disko, a `fresh-install` host MUST pass every check that `MACH-010` named. An adopted host MUST compare its live hardware, layout, mounts, keys, boot files, and data hashes, read-only, with the approved baseline, and MUST NOT need a blank disk. Both MUST stop on an unknown result | A fixture injects each mismatch for each mode; no write runs |
| `MACH-017` | *Proposed.* On `server`, Home Manager MUST run inside the NixOS role (`home-manager.nixosModules.home-manager`) from the first install. On an adopted host, it MUST move into the NixOS role only in a later generation, after a lossless standalone-to-embedded VM cutover that keeps the revision and the state version, and the standalone profile MUST stay until the owner accepts the new role | A VM: deploy a home change, roll back, and the old managed links return; an occupied unmanaged file is not overwritten (`A10`, `A11`) |
| `MACH-018` | *Proposed.* A Vendomat release MAY carry one tested `nixpkgs` revision as the default for a new workspace. A workspace MAY override it, and `sync` MUST report the override. An adoption MUST pin the host's current effective revision and MUST postpone every package, service, and state migration to a later change | The fragment's `nixpkgs` URL equals the release's revision; an override is reported; an adoption plan lists no unapproved package or service change |
| `MACH-019` | *Proposed.* Machines and workspaces MUST use a plain `github:NixOS/nixpkgs/<rev>` input, not `devenv-nixpkgs`. A fresh host uses the release's tested revision. An adopted host MAY use its exact legacy revision in a separately locked adoption workspace that still imports the Vendomat module | The lock's `nixpkgs` node is `NixOS/nixpkgs`; `DVN-008` passes; the adoption lock equals the baseline revision |
| `MACH-020` | *Proposed.* Before the first apply to an adopted host, the host MUST accept the owner's deploy public key for root, key-only, through its existing configuration route, and the controller MUST pin its SSH host key. `apply` MUST refuse when root SSH is unverified | A VM with the key missing refuses; with the key present, `ssh -o BatchMode=yes` succeeds against the pinned host key (`A7`) |
| `MACH-021` | *Proposed; the Step 1 fixture defines the contract.* The patched `devenv machines install` MUST refuse a `fresh-install` host unless a target-side preflight has just passed, bound to the host, the target identity, and the `install-target` disks. A missing, stale, mismatched, or malformed result MUST refuse before any target write | A fixture runs the direct CLI for each case and sees a non-zero exit and no target write |
| `MACH-022` | *Proposed.* Before a deploy, `systemctl --failed` on the target MUST be empty, and critical user units MUST be healthy, or the failure MUST be resolved and named in the reviewed plan | A VM with a pre-failed unit is refused by the gate; a bypass shows the native rollback failing (`A9`) |
| `MACH-023` | *Proposed.* `nix-systems` MUST be a devenv project that defines `machines.server` through `vendomat.inventory`, with one shared core module and one delta module per host. `machines.framework` MUST be defined through `vendomat.inventory` in `nix-systems` or in a temporary adoption workspace that has its own lock and imports the same module, and never in both | `devenv machines info` lists each host once; `devenv build machines.<host>.build.nixos` succeeds |

## Secrets

| ID | Requirement | Verify |
| --- | --- | --- |
| `SEC-001` | *Superseded by `SEC-003` (2026-10-09).* Host runtime secrets MUST use sops-nix, with encrypted files in `nix-systems`. Each host's age key MUST be placed at install by `install.secrets` (`MACH-007`) | — |
| `SEC-002` | *Proposed.* Workspaces SHOULD read the same encrypted files through SecretSpec's SOPS provider | A workspace fixture resolves one secret from a sops-nix file |
| `SEC-003` | *Proposed.* Host runtime secrets MUST use sops-nix, with encrypted files in `nix-systems`. A fresh host MAY receive its age key through `install.secrets` with a CLI that carries `a5fd551a`. An adopted host MUST keep its existing age or host identity, with no install phase, and MUST decrypt after a deploy and after a reboot. No plaintext MAY enter the store | A VM: a service reads its decrypted secret after install or adoption, after a deploy, and after a reboot; no secret value is in the store (`A8`) |

---

# 6. Disks, cache, delivery, command line

| ID | Requirement | Verify |
| --- | --- | --- |
| `DISK-008` | *Superseded by `DISK-009` (2026-10-09).* A disko layout MUST preset partition GUIDs (`uuid`) and filesystem UUIDs (`extraArgs = ["-U" …]` for ext4, `["-i" …]` for vfat), MUST mount by UUID, and MUST use a disk attribute name unique on the host | — |
| `DISK-009` | *Proposed.* A fresh disko layout MUST preset partition GUIDs and filesystem UUIDs (`extraArgs = ["-U" …]` for ext4, `["-i" …]` for vfat), MUST mount by UUID, and MUST use a disk attribute name unique on the host. An adopted host MUST keep its observed GUIDs, UUIDs, filesystem types, ESP, and unlock and mount paths | `lib.testLib.makeDiskoTest` boots with the preset UUIDs; the adoption VM compares GPT and UUIDs before and after |
| `CACHE-010` | The host core MUST set the Attic substituter and its public key in `nix.settings` | `nix config show` lists both on each host; the machine `nix.conf` equals a plain NixOS build (agent G Q5a) |
| `DEL-013` | A library's flake outputs MUST evaluate and build with no Vendomat input and no Vendomat command. A workspace MAY depend on the Vendomat module | `GEN-019`'s check, run on a library only |
| `DEL-014` | *Decided 2026-10-09, see `DEL-017`.* Where the `vendomat` command runs from | — |
| `DEL-017` | The host MUST install a small `vendomat` launcher, not the full command. Inside a workspace, the launcher MUST run the Vendomat build that the workspace's `devenv.lock` pins, found in the store by its NAR hash, with no network when the build is present. Outside a workspace, it MUST run the host's pinned release. The module MUST NOT put a second `vendomat` on the shell `PATH`. The direnv hook (`PRE-009`) MUST call the launcher | Two workspaces that pin different tags each report their own version; with the network off and the builds present, both still run; outside a workspace the host release runs |
| `DEL-015` | *Superseded by `DEL-018` (2026-10-09).* The flake exported the package and the module only | — |
| `DEL-018` | *Superseded by `DEL-019` (2026-10-09).* The flake also exported `lib.mkModules` | — |
| `DEL-019` | The Vendomat flake MUST export `packages.<system>.vendomat` and `devenvModules.default`, and MUST have `nixpkgs` as its only input. It exports no library helper | `nix flake show`; `tests/test_repo_shape.py` |
| `DEL-016` | `nix-systems` MUST reach every Vendomat Nix function through its own `vendomat` input | No machine file names a Vendomat path |
| `GEN-023` | The generator MUST NOT emit `devShells`, `devenv.lib.mkShell`, or a `devenv` input in `flake.nix`. A workspace shell MUST be a devenv project that uses the devenv target | `nix flake show` lists only the project's outputs |
| `BOOT-026` | *Proposed.* A Framework deploy MUST build nothing on the laptop. The controller or the builder on `server` builds, the plan copies the closure, and no format or install step runs | The deploy log and the builder log show no compilation on the target |
| `CLI-017` | *Superseded by `CLI-021` (2026-10-09).* The surface lacked `bump` | — |
| `CLI-021` | The surface MUST be `sync`, `path`, `check`, `push`, `bump`, and `machine install`. Deferred commands (`set`, `get`, `unset`, `diff`) MAY return later | `--help` lists exactly the built commands |
| `CLI-020` | `bump` MUST update every workspace under a root to a given Vendomat tag and fork revision, re-run `sync`, run each repository's verify gate, and report each result. It MUST default to a dry run that changes nothing | A dry run reports and leaves every file unchanged; a real run on a fixture fleet moves each pin and reports one failing gate |
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
| `NAT-039` | `nix flake check` warns "unknown flake output 'vendomat'" for a described library and still passes | Agent L Q2 |
| `NAT-040` | Described libraries cost about 40 ms of shell evaluation when disabled (0, 2, 10 libraries: 1143, 1181, 1187 ms); 10 enabled libraries add about 400 ms to the shell and to a NixOS evaluation | Agent L Q7 |

---

# 8. Out of scope

Vendomat is not and MUST NOT become a deployment engine, a second lock, a version solver, a daemon,
a retention engine, or a workspace orchestrator. devenv Machines deploys. Nix owns `flake.lock` and
`devenv.lock`. Each workspace stays a plain devenv project that imports one module.

## Count

`LEDGER-V6.md` holds every count and every disposition. It is generated from this file and from
`SPEC-V5.md`, and a Testee check fails when it differs. This document keeps no count, so none can go
stale. No new ID reuses a V5 ID. A row that starts with *Superseded* names its successor.

# Step 6 — `nix-systems` bootable core and the Machines flow in disposable VMs

**Date:** 2026-10-09. **Gate:** G6. **Status:** PASS for items 1 to 6 on QEMU VMs, with the limits
under "Not covered". The VM is not the real server: no real firmware, disk, or tailnet.

**Branch:** `nix-systems` bookmark `v6-step6-vm`, commit `29e485bba43b17d8cd81a1c118e72762b0b4ef04`,
based on `main` `094669ef9814da1eec28b8298b91aa947b403b46`. Pushed to origin. `main` is not moved.

## Pins and tools

| Item | Value |
| --- | --- |
| Patched devenv | `devenv 2.4.0+9726240`, `/nix/store/6djw5w3sil4c0s8z0dvaqcq832y4cfvb-devenv-wrapped-2.4.0` |
| Fork modules | `972624027d5788c0590e4b9f09bd3c3fbc53adb4`, tag `v2.4.0-vendomat.1`, `dir=src/modules` |
| Vendomat | `vendomat 0.6.0` CLI from the `v6-implementation` checkout (main `b30100b7`). The test collection serves that tree as tag `v0.7.0` (commit differs per run) |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (`NixOS/nixpkgs`, root `nixpkgs` input) |
| disko | `de5708739256238fb912c62f03988815db89ec9a` (v1.13.0) |
| Home Manager | `6b88c12cc6d234de4888f5d21076fb11199d0844` |
| sops-nix | `dcd241ba97088c22569d1573286e1b9daad340c0` (from `main` of nix-systems) |
| Nix | 2.34.7 |
| QEMU, OVMF | `qemu_kvm` 11.1.1 and OVMF 202608 from the pinned nixpkgs; `-m 2048`, KVM |
| NixOS test driver | the pinned nixpkgs `pkgs.testers.runNixOSTest`, run outside the build sandbox |

## What was built

Files under `tests/core/` in `nix-systems` (the repository holds no Testee config; `tests/run` is
the runner):

| File | Role |
| --- | --- |
| `tests/run` | Runner: collection, `lock-and-build`, `run-core-vm`, `vm-flow all`. Cleans up on exit |
| `make-test-collection.sh` | Serves `vendomat` (tag `v0.7.0`), the fork `devenv` (tag `v2.4.0-vendomat.1`), and `pinger` (tag `v0.1.0`) on loopback `git://` |
| `ws-prepare` | Copies the repository, rewrites `[forge] url`, adds the overlay, runs `vendomat sync`. Never commits the lock |
| `lock-and-build` | Item 1 |
| `core-vm.nix`, `core-vm.py`, `run-core-vm` | Item 2 |
| `devenv.local.nix`, `vm-hardware.nix`, `vm-delta.nix`, `vm-flow`, `gate-failed-units` | Items 3, 4, 5 |
| `lib-pinger/` | The described library fixture (no Vendomat input; its lock holds only `nixpkgs`) |
| `framework-tripwire` | Item 6 |
| `plain-nixos.nix` | The plain NixOS baseline for `CACHE-010` |

## Result

| Item | Result | Raw log (under `~/.local/state/vendomat/v6/2026-10-09/06-nix-systems/final2/`) |
| --- | --- | --- |
| 1. Lock, check, evaluate, build, `CACHE-010` | PASS | `lock-and-build/` |
| 2. Core boots with no Vendomat | PASS | `core-vm/` (`core-vm.log`, `exit.txt`) |
| 3. Machines flow, owner-run | PASS | `vm-flow/` (`steps.json`, numbered command logs) |
| 4. Library face runs, inert when disabled | PASS | `vm-flow/` steps `library-*` |
| 5. Home Manager in the NixOS role | PASS | `vm-flow/` steps `hm-*` |
| 6. Framework builds, no target, install refused | PASS | `vm-flow/framework/` (17 cases) |
| 7. `tests/run` | PASS, exit 0 | `summary.txt`, `collection.out`, `lock-and-build.out`, `core-vm.out`, `vm-flow.out` |

Earlier runs (`run1` to `run4`, `final`) are development history. `final` ran the same runner and
failed only `cache-010`, because its plain baseline lacked the Vendomat face imports (see Findings).
`run2` holds the first bypass experiment (see item 3).

## 1. Lock and evaluate

Command: `tests/core/lock-and-build WS LOG git://127.0.0.1:19520` (inside `tests/run`). Expected: every
step exits 0. Actual: 9 of 9 steps PASS (`lock-and-build/steps.txt`).

- `vendomat sync` wrote `.vendomat/` and `devenv.lock`: 13 inputs, one note (`devenv-cli`'s
  `nixpkgs` differs and is not followed).
- Lock pins (`lock-and-build/lock-pins.txt`): `devenv` `972624027d5788c0590e4b9f09bd3c3fbc53adb4`
  (`refs/tags/v2.4.0-vendomat.1`, `dir=src/modules`); `vendomat` tag `v0.7.0`; `disko`,
  `home-manager`, `sops-nix`, `nixpkgs` (root input, node `nixpkgs_2`) as in the table above;
  `repoman`, `gitman`, `testee`, `docman`, `copyroom`, `devman` at the GitHub tags of `main`.
- `vendomat check`: `clean`, exit 0. This includes the CLI and module revision check.
- `devenv machines info` lists `framework` (no target) and `server` (`root@localhost`).
- `devenv build machines.server.build.nixos` and `machines.framework.build.nixos` exit 0.
  `machines.server.build.vendomatPreflight` exit 0.
- `CACHE-010`: `/etc/nix/nix.conf` of the server toplevel is byte-identical to the plain NixOS build
  of the same modules (`nix-conf.txt`: same store path `8nm1bfp0...-nix.conf`). It lists the Attic
  substituter `https://server.tail770f47.ts.net/attic/vendomat` and the key `vendomat:SRJCMEnuS...`.

Interpretation. Machines and the Vendomat guard add nothing to `nix.conf`. The plain baseline is not
free of Vendomat: `nixos/server.nix` enables `vendomat.libs.docman`, whose options exist only
through the face builder. The baseline therefore imports `builder.nixosImports` but no devenv
Machines module and no guard. Other `/etc` files differ between the two builds: `etc/devenv/` and the
recover unit exist only in the Machines build, and a few files hold other store paths of
`system-path`. I did not trace the store-path differences. `CACHE-010` covers `nix.conf` only.

## 2. The core boots with no Vendomat

Command: `tests/core/run-core-vm LOG`. It generates two disposable key pairs, builds the test driver
with only the public keys as arguments, and runs the driver outside the sandbox with the private
keys read at run time. Expected: exit 0. Actual: `driver exit: 0` (19 s of test script).

The node imports `nixos/core.nix` and nothing else. The test replaces `inventory.deployKey` and
`inventory.loginKeys` through `_module.args.inventory`. The repository data is unchanged.

- `systemctl is-system-running --wait` is `running`. `systemctl --failed` is empty.
- SSH as root with the deploy key works (`id -un` is `root`, `hostname` is `server`).
- A password login is refused (`Permission denied (publickey)`; `sshd -T`:
  `passwordauthentication no`, `kbdinteractiveauthentication no`, `permitrootlogin prohibit-password`).
- The other key is refused for root and accepted for `andrew`, so the refusal comes from root's key list.
- `command -v vendomat` fails. No unit file matches `vendomat`. `nix-store -qR /run/current-system`
  holds no `vendomat` path. `nix config show` lists the Attic substituter and key.

Limit: the NixOS test framework supplies the boot path (direct kernel). The systemd-boot path of the
core boots in item 3.

## 3. Machines flow, owner-run, against a disposable QEMU VM

Setup. `machines.vm` is the core, a minimal delta (`tests/core/vm-delta.nix`), the VM hardware module,
Home Manager inside the role, and no disko disk. Mode `adopt-existing`, disk by-id
`virtio-NSVMROOT` as `existing-system`. The image comes from `make-disk-image.nix` (qcow2, EFI,
systemd-boot installed by `nixos-install`). QEMU runs under OVMF with the loopback port 22955 and a
pinned host key. devenv runs as `andrew`.

| Check | Expected | Actual |
| --- | --- | --- |
| Boot, base state | marker `A`, `/nix/var/nix/profiles/system` exists, 0 failed units | PASS |
| Raw SSH, wrong key | refused | exit 255, `Permission denied (publickey)` |
| Raw SSH, wrong host key | refused | exit 255, `REMOTE HOST IDENTIFICATION HAS CHANGED` |
| `machines check vm` | exit 0 | exit 0 |
| `machines check vm`, wrong key file | non-zero, VM unchanged | exit 1 (ssh exit 255), marker `A` |
| `machines check vm`, wrong known_hosts | non-zero, VM unchanged | exit 1 (ssh exit 255), marker `A` |
| Gate on a clean VM | exit 0 | `gate: ok` |
| `machines plan vm` | named plan, no change | `plan-G635k1BBFes1aAGD3iHa8IYX`, marker `A` |
| `machines apply plan-...` | marker `B` | exit 0, marker `B` |
| `machines status vm` | succeeded | `outcome: succeeded` |
| `machines rollback vm` | marker `A`, same system path | exit 0, system `...xzp307j7...` as before |
| Health check `false` | deploy fails, rolled back | exit 1, marker `A`, `outcome: rolled-back`, 45 s |

Failed unit before the deploy (`MACH-022`, `NAT-034`). The gate is `tests/core/gate-failed-units`: one
read-only `systemctl --failed` over the pinned key-only connection. It exits 1 and names the unit.

| Case | Gate | Bypass (`machines deploy vm --yes`) |
| --- | --- | --- |
| Transient unit `ns-prefail` (no generation declares it) | exit 1, names it | deploy succeeded, outcome `succeeded` |
| Declared service `ns-flaky`, killed after a deploy, start condition false | exit 1, names it | exit 1, outcome `rollback-failed`, `switch-to-configuration` exit 4 for deploy and for rollback |
| Same, and the next generation changes the unit file | (as above) | exit 1, outcome `rollback-failed`, system unchanged |

Interpretation. `NAT-034` holds for a declared unit that fails again when `switch-to-configuration`
starts it. A failed unit that restarts cleanly does not block a deploy: the first run (`run2`) used a
unit that restarts, and the bypass deploy succeeded. The gate refuses in every case, so the gate is
the safe rule, and the bypass shows the native recovery failing. After each case, `reset-failed` and
one deploy of the base generation restored the VM (`vm-recovered`: 0 failed units).

Observation about devenv: `machines check` hides the ssh error text (it prints the remote script and
`exited with exit status: 255`). The refusals above are proved by the raw ssh runs with the same
options, plus the passing control with the right key and known_hosts.

## 4. A library face runs

`pinger` is a flake with a `vendomat` description (`name`, `packages`, `options.port`, `service`) and
no Vendomat input. The test workspace adds it through `vendomat.toml` (`pinger = { ref =
"refs/tags/v0.1.0" }`). The host enables it with `vendomat.libs.pinger = { enable; port; service.enable; }`.

- Inertness: the toplevel `.drv` of `machines.vm` is the same with no `pinger` input and with the
  input present and disabled: `/nix/store/lx0l53irs0x7w81lksnv72z412gml1fg-...drv` both times.
- Enabled: a different `.drv` (`zbz74273...`). The deploy exits 0. In the VM `pinger.service` is
  `active`, `pinger` is on the system PATH, the unit runs `pinger-start`, and
  `curl http://127.0.0.1:7077/` returns `pinger-ok`.

## 5. Home Manager inside the NixOS role

`home-manager.nixosModules.home-manager` is in the role, with `useGlobalPkgs`. The user file
`~/.config/nix-systems/managed` is a link into a `home-manager-files` store path. An unmanaged
file `~/.config/nix-systems/unmanaged` is made by root before the deploy.

- Base: link `...35zn8qiq...-home-manager-files/.config/nix-systems/managed`, content `v1`.
- Deploy with content `v2`: link `...nm4hkszy...`, content `v2`, unmanaged file `mine`.
- `machines rollback vm`: link `...35zn8qiq...` again (equal to the base), content `v1`, unmanaged
  file `mine`.

Not covered: the occupied-path collision (`A10`). The fixture made the unmanaged file at a path that
no generation manages, so Home Manager had no collision to refuse.

## 6. Framework

`framework-tripwire` puts a fake `ssh` (exit 255) and a fake `nix copy` first on PATH. 17 cases, 0
failed (`vm-flow/framework/summary.json`):

- `build machines.framework.build.nixos` exit 0. `eval machines.framework.target.host` is `null`.
  `machines info framework` shows `(no target)`.
- `machines install framework` is refused with no fake call, for: default, `--phases` `disko,install`,
  `kexec`, `facter`, `reboot`, all five, `--disko-mode format`, `--disko-mode mount`,
  `--stop-after-disko`, `--no-reboot`. The message names `machines.framework`, `adopt-existing`, and
  "devenv made no connection to the target".
- `machines deploy|plan|check framework`: exit 1, `requires target.host`, no fake call.
- Positive control: `machines check vm` under the same PATH made 10 fake `ssh` calls, so the
  tripwire sees calls when a machine has a target.

## Changes to `nix-systems` (commit `29e485bb`)

| Path | Change | Why |
| --- | --- | --- |
| `home/andrew.nix`, `nixos/home.nix` (new) | A minimal Home Manager user module and the NixOS glue | `MACH-017`: `server` runs Home Manager inside the NixOS role from the first install. `home/` was empty |
| `devenv.nix` | The `server` role imports `inputs.home-manager.nixosModules.home-manager` and `./nixos/home.nix` | Same. Without it item 5 had nothing to test on the `server` role |
| `nixos/core.nix` | Comment only: `inventory` arrives as a module argument | Documents the injection point that item 2 uses |
| `README.md` | Layout lines for `tests/run`, `tests/core/`, `home/`, and a "Checks" section | The runner is documented |
| `tests/run`, `tests/core/*` (new) | The files listed above | Items 1 to 7 |

`.gitignore` already ignores `*.qcow2`. The test copies are outside the repository.

## Findings

1. **`machines.server` pulled main's role into the tests.** While this lane ran, `main` moved to
   `094669ef`: `nixos/server.nix` now carries sops, Tailscale, Attic, and the docman face, and
   `vendomat.toml` adds six GitHub inputs. The VM tests therefore use `tests/core/vm-delta.nix`
   (host name and state version) and not `nixos/server.nix`. The services need their own disks,
   keys, and tailnet; each needs its own VM check (not in this lane).
2. **`nixos/server.nix` cannot build with no Vendomat.** It sets `vendomat.libs.docman`, so a plain
   NixOS build of the role needs the face builder. `VMOD-014` already says so. The `CACHE-010` check
   uses `builder.nixosImports`.
3. **The lock carries a second nixpkgs.** `devenv-cli` (the whole devenv repository as a flake, from
   `main`) brings `cachix/devenv-nixpkgs` `rolling` and `nixpkgs-src` into `devenv.lock`. The root
   `nixpkgs` is the plain `NixOS/nixpkgs` revision, so `MACH-019` holds for the root input. `DVN-008`
   (offline shell entry) was not run on this lock.
4. **The test driver can hang on `ssh` with no `-n`.** One run of `core-vm` stopped at an `ssh
   ... andrew@server true` step. The fixture now passes `-n` and wraps `ssh` in `timeout 60`.
   Cause unproven.
5. **Disk.** The btrfs root had 8.95 GiB unallocated at the start. It fell to 0.98 GiB during this
   lane (the 2.7 GB disk image, the builds, and other lanes) and was 17 MiB once. Metadata stayed
   at 79 to 80%. I ran no GC. I deleted every qcow2 under `/mnt/shared/vendomat-v6/nix-systems/`.
   The 2.7 GB image `nixos-disk-image` stays in the store until the owner runs GC.
6. **`nix-systems` holds no `.vendomat/` fragment and no `devenv.lock`.** `AGENTS.md` says to commit
   both. The lock cannot name `git://server` before the collection holds the tags. The tests create
   both in a copy.

## Not covered

- **Real systemd-boot update on the VM across a reboot.** The VM booted from the image under OVMF
  (systemd-boot), and deploys did not reboot it. A reboot after a deploy is not tested.
- **`install` for `vm`, `server`, or any disk.** Step 7 owns the disk route. No disko disk was used.
- **The real `server` role**: sops decryption, Tailscale, Attic, the collection, and the docman face
  have no VM check here (Finding 1).
- **Hand-written faces** and the Home Manager side of a described library
  (`home-manager.users.<user>.vendomat.libs.<name>`) in this workspace. Step 3 covered them.
- **`A10` collision**, **`A6` lost SSH during deploy**, **`A8` sops key**: not run.
- **The Vendomat gate.** `tests/core/gate-failed-units` is a fixture script. No `vendomat` command
  runs it (see proposals).

## Proposed document changes

For the lead to merge. IDs are proposals.

### SPEC-V6.md

- `NAT-034`: replace the Fact with: "A declared unit that fails when `switch-to-configuration`
  starts it makes the switch exit 4. If a unit failed before the deploy and fails again on start, the
  deploy fails and the native rollback fails (`outcome: rollback-failed`). A failed unit that
  restarts cleanly does not block a deploy." Evidence: step-6.md item 3.
- `MACH-022`: add to **Verify**: "Fixture: `nix-systems/tests/core/gate-failed-units` refuses with
  exit 1; a bypass of a declared, failing unit shows `rollback-failed` (step-6.md)." Keep
  *Proposed* until a Vendomat command runs the gate before `machines deploy` and `apply`.
- `MACH-017`: add to **Verify**: "VM fixture: step-6.md item 5 (link returns, unmanaged file stays).
  The occupied-path case (`A10`) is open."
- `MACH-004`: add "VM fixture: owner-run `devenv machines` against a loopback VM with a pinned host
  key; a wrong key and a wrong host key are refused (step-6.md item 3). The self-deploy to
  `root@localhost` is not run here."
- `CACHE-010`: add "Fixture: `nix.conf` of `machines.server.build.nixos` equals a plain NixOS build
  of the same modules, with the face builder (step-6.md item 1)."
- New observed fact `NAT-041`: "`devenv machines check` prints no ssh error text for a refused key
  or host key. Only `exited with exit status: 255` shows."

### GUIDE-V6.md Step 6

- Item 4: say that the owner-run proof uses a loopback VM with a pinned key and that the
  `root@localhost` self-deploy is a Step 9 item.
- Item 5: add the failed-unit gate as a named script and say that no Vendomat command runs it yet.
- **Gate** line: add "`tests/run` in `nix-systems` exits 0".

### CONCEPT-V6.md

- Section on machines: say that a described library's NixOS face is part of the role definition, so
  a plain NixOS build of a role needs the face builder (Finding 2).

## Commands to reproduce

```text
cd ~/Documents/Projects/gitman-workspaces/v6-vm-core   # or any checkout of v6-step6-vm
NS_TEST_KEYS=<dir with deploy and wrong keys>   # optional; a new run makes new keys and a new image
tests/run                                       # needs /dev/kvm and about 3 GB of Nix store for the image
```

## Update 2026-10-10: rerun on fork `v2.4.0-vendomat.2`

`tests/run` ran once, alone, on `nix-systems` `main` `fe848434` with the patched CLI
`2.4.0+e2acb5b`. All four stages exit 0 (`collection`, `lock-and-build`, `core-vm`, `vm-flow`).
Raw logs: `~/.local/state/vendomat/v6/2026-10-09/06-nix-systems/final3/`. The item list above
(1 to 6) holds for the new fork.

# D: machine path for project 20, local install versus remote controller

Date: 2026-10-12. Kind: read-only design research. No repository change. No VM build, no disk write, no sudo.

Short names for paths:

- `P20` = `/home/andrew/Documents/Projects/vendomat/.scratch/projects/20-vendomat-front-door`
- `FORK` = `~/.local/state/vendomat/v7/2026-10-11/devenv-v2.4.0-vendomat.3` (fork tag `v2.4.0-vendomat.3`, CLI `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0`)
- `P16` = `/home/andrew/Documents/Projects/vendomat/.scratch/projects/16-vendomat-devenv-layer`

Note: the 2026-10-09 machine-paths research sits at `P16/RESEARCH-2026-10-09-MACHINE-PATHS.md`, not under `evidence/`.

## Fixture run in this task (eval only)

Question: does the fork evaluate a NixOS machine that has no `target.host`, and what do `plan` and `install` do then?

Inputs: copy of the S4 workspace `~/.local/state/vendomat/p20/2026-10-11/S4/ws/valid`, with every `target` key removed from `.vendomat/config.json` (`bin/strip_target.py`). Fork CLI above. Mock `ssh`, `nix`, `nix-store`, `nixos-install` first on `PATH` for the commands that could connect. Workspace: `ws-notarget/`. Logs: `logs/`.

| Command | Expected | Actual |
| --- | --- | --- |
| `devenv eval machines.box.build.nixos` | Evaluates without a target | rc 0. Output `/nix/store/yrzzns3093dyqz7x7a7li5c0pn63c05n-nixos-system-box-26.11.20261008.e7439b6`. This is the same path as S4 case V1, which had a target. The toplevel does not depend on `target.host`. (`logs/F1.out`) |
| `devenv machines info` | Lists machines | rc 0. Both machines show `(no target)`. |
| `devenv machines plan box` | Refuse or work | rc 1: `machines.box.nixos requires target.host for system deployment` (`logs/F-plan.err`) |
| `devenv machines install box --phases disko,install` | Refuse or work | rc 1: ``machines.box does not have `target.host` set. `devenv machines install` always operates over SSH.`` (`logs/F-install.err`). The mock `ssh.log` stayed empty. |

Limit: the Basix wrapper `basix-machines.nix` is the S4 fixture, not production. The fixture proves fork behavior for a target-less NixOS machine. It does not prove a local activation.

## Q1. Install routes the fork supports today

Evidence:

- Native Rust, no nixos-anywhere. `S7-keyless-secrets.md:96-97`: "`devenv machines install` is native Rust in the fork (`devenv/src/devenv/machines.rs`): phases `kexec, facter, disko, install, reboot`. It does not call `nixos-anywhere`." I searched `FORK/devenv/src/devenv/machines.rs` for `nixos-anywhere`: no hit. The options only mirror its flags.
- Every route runs over SSH. `FORK/devenv/src/devenv/machines.rs:1704-1708` refuses an install without `target.host`: "`devenv machines install` always operates over SSH". Fixture F-install confirms it.
- Kexec route. `FORK/docs/src/content/docs/machines.md:131`: "The target must allow root SSH, support kexec, and have `tar` and `curl`." Code: `install_kexec`, `machines.rs:2439-2495`. Default image URL: `machines.rs:723-735`.
- Installer-ISO route. `machines.md:131`: "If kexec is unavailable, boot a suitable installer yourself and use `--phases facter,disko,install,reboot`." The controller still reaches the ISO over root SSH.
- Patch 0006 refuses a phase set that joins `kexec` or `reboot` with `disko` or `install`. `machines.rs:765-830`. Run `--phases facter`, then `--phases disko,install`, then reboot by hand. S4 section 4.3 line 135 shows the refusal.
- Preflight program runs on the target. `FORK/src/modules/machines.nix:590-600`: "Target-side preflight program ... `devenv machines install` builds it, copies it to the target, and runs it". The CLI binds the report to a nonce, machine id, boot id, and disk set (`machines.rs:~890-1100`).
- Local routes: only for Home Manager. `machines.md:47`: "A home-manager-only machine can omit `target.host` to activate locally. Setting it to `localhost` still uses SSH." NixOS has no local route.
- Tested installs. S7 task 4 installed over SSH into a running NixOS VM (`S7:171-190`). G7 used the controller's own `root@127.0.0.1:PORT` with a second blank disk (`R4-user-journeys.md:190`). Nobody has run kexec or a real ISO (`S7:188-190`, `RESEARCH-2026-10-11.md:332`).

Finding: the fork supports a remote install over root SSH with either kexec or a hand-booted installer. It has no local-install mode. "Local install" on an ISO means either SSH to `localhost` inside the ISO (needs sshd, a root key, and the fork CLI on the ISO) or a path that skips the fork's install.

Inference: SSH to `root@localhost` inside an ISO would work, since the G7 pattern is SSH to self. It brings back an installer key.

Unproved: kexec, a real ISO, `facter` phase, SSH to localhost inside an ISO.

## Q2. Local-install hypothesis

Design under test: the learner boots a Basix ISO on the target and runs one command there. The command picks the disk, runs the preflight, runs disko and `nixos-install`, and does not use SSH. It does not use the fork's `machines install`.

Mechanism by mechanism:

| Mechanism | Local install | Reason and evidence |
| --- | --- | --- |
| Temporary installer key | Disappears | The key exists only so the controller can reach the installer (`S7:183-190`, `RESEARCH-2026-10-11.md:97`, D13). No SSH, no key. |
| Admin key at install time | Disappears as a required field. Becomes an optional later setting | It serves the controller's root SSH. A learner needs a console login instead. See the login note below. |
| Host-key re-pin | Disappears | Re-pin protects the controller's `known_hosts` (`S7:83`, `S7:277`). With no controller there is no pin. It returns if the learner later enables remote deploy. |
| Controller | Disappears for the first machine | The ISO is the installer. |
| Target address | Disappears | Nothing connects. |
| Remote preflight (copy, nonce, boot-id binding by the CLI) | Disappears. The preflight checks stay | `vendomat-preflight` already runs on the target and reads it read-only. The CLI binding guards against a stale or forged report from a remote program. A script that the same ISO runs gains nothing from it. Inference. |
| Disk choice (stable by-id) | Stays | Types cannot prove hardware identity (`CONCEPT.md:60`). |
| Protected-disk check | Stays, in a simpler form | See below. |
| Root authentication check | Stays in a new form | The fork refuses an install whose config has no root auth (`machines.rs:2086-2105`). A local install needs a console credential for the same reason. This also answers R4 gap G17 (user password). |
| UEFI check | Stays | `CONCEPT.md:57`: one standard UEFI disk. The ISO tests `/sys/firmware/efi`. Inference. |
| Hardware report (facter) | Stays | The report must exist before the build (`R4:G04`). Locally the ISO runs `nixos-facter` and stores the report in the new workspace. Unproved: the `facter` phase never ran. |
| Failed-unit proof of the core | Stays as a test gate | `DOOR-060` proof: zero failed units on a keyless boot. |

Simplest disk choice that makes a wrong disk hard (design proposal; unproved):

1. The installer lists whole disks from `/dev/disk/by-id/` only. It hides partition links (`-part*`), `wwn-` and `nvme-eui` duplicates of a disk already listed, and removable boot media.
2. It excludes any disk that backs a mounted filesystem or swap. The existing script already does this: `preflight/vendomat-preflight`, check `not-mounted` (ancestry through `lsblk -s`). The ISO boot medium is mounted at `/iso`, so its parent disk fails this check. Unproved: the R4 gap G01 asks whether the preflight passes inside a live ISO (root on tmpfs, empty `/mnt`).
3. It refuses any disk with a partition, a holder, or a signature (`no-partitions`, `no-holders`, `no-signature-wipefs`, `no-signature-blkid`). This is the strongest guard for a learner: it makes "wrong disk with data on it" impossible without a separate erase step. Cost: a used laptop disk is refused (R4 G03). The first release gives no guarded erase.
4. It prints model, serial, and size of each remaining candidate and the exact by-id string.
5. The learner types the full by-id string (or its serial) to confirm. A number choice alone is not enough. The command writes that string to the record. The record keeps one identity field, the by-id. The model, serial, and size fields (required today by `guard.nix`, R4 Journey 5 step 1) become displayed facts, not typed input. This also answers R4 gap G04 (a blank-machine user cannot fill model, serial, size).
6. With one blank candidate the installer still asks for the typed confirmation.

The explicit "protected disks" list exists for a machine with a second disk the owner keeps (the `server` case). A learner has no such list. Rules 2 and 3 protect every other disk by default, because every other disk either backs a mount or carries data. A blank second disk is not protected, but the learner names the target by its by-id, so the risk is a typing choice. Inference.

Changes this needs in existing material (all proposed):

- A local mode for `preflight/vendomat-preflight`. Today it bakes model, serial, and size at build time (`vendomat-preflight:19-24`, `:88`) and accepts only `--phases disko,install` (`:110-118`). A local call passes the chosen by-id and reads identity live.
- A local install script (disko, then `nixos-install`) that does not use the fork's `machines install`. The fork's patch 0005 and 0006 guards stay for the remote door.
- A Basix ISO. `RESEARCH-2026-10-11.md:113` (O9) already plans one. Build and release of that ISO is a new artifact to own.

Risks to flag:

- The live ISO store sits in RAM. The fork builds on the controller and copies the closure, so the target needs about 1 GB (`machines.md:131`). A local install builds or substitutes on the target. `R4` journey 5 prerequisite 3 gives 3.4 GiB and 905 paths for `server`. Mitigation: the ISO carries the Basix core closure, so the install builds only small machine-specific parts. Unproved. Measure RAM use in a VM.
- The learner needs network or an ISO with the core inside. Unproved.
- The learner needs one computer, once, to write the USB medium. That is not a controller, but it is a prerequisite to state.
- Login: the core has SSH key-only and root login off (`basix-machines.nix:166-168`, `S7` core). A learner with no key cannot log in. The installer must set a console password for the first user. Proposal: `nixos-enter --root /mnt -c 'passwd USER'` after the install, so no hash enters the store or the record. Unproved.
- `DOOR-060` says the record MUST hold target and admin public key. A local flow needs a successor ID. Preserve the old ID (project rule).

## Q3. Remote deploy for the second machine

Finding: remote deploy is not needed for journey 4 (second machine, shared outputs).

Evidence:

- The review lists journey 4 as: "Repeat fresh install; optional signed Harmonia after key placement; client fallback; build and root selected outputs on server" (`SIMPLIFY-REVIEW-2026-10-12.md:15`). It names no remote deploy.
- `DOOR-068` (`REQUIREMENTS.md:193`): the cache data selects one host and declares its address and public key once. That is data on the second machine. No controller moves it.
- `DOOR-061`/`DOOR-068`: shared outputs "MUST be built and rooted on that host". `R4` gap G07 says the fork's Machines build the closure on the controller and copy it to the target, so a laptop controller defeats this. With local apply on each machine, the cache host builds its own outputs in its own store. The gap closes by construction. Inference.
- A native local apply exists in the pinned nixpkgs: `nixos-rebuild --store-path PATH` with `switch`, `boot`, `test`, or `dry-activate` (`/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source/pkgs/by-name/ni/nixos-rebuild-ng/src/nixos_rebuild/__init__.py:146-152, 340-352`). The fork builds the toplevel without a target (fixture F1: same store path with and without a target). So the local apply is: `devenv build machines.NAME.build.nixos`, then switch to that path with the native tool. Unproved: nobody ran this pair.
- The fork's own apply cannot run locally for NixOS: it needs `target.host` and SSH (fixture F-plan, `machines.md:47`, `:167`). Local use of the fork's deploy needs sshd on the machine itself, a root key, and a host pin. That brings back the admin key and the re-pin. (`R4` Journey 7 step 1 shows the same point for a laptop that is its own controller.)

Signing key. `CONCEPT.md:70-73` says the administrator places a signing key outside the store. If the cache host creates the key itself, the secret never moves, and the S7 receiver, `secret push`, and path unit for delivery are not needed. Public key: the learner copies one short line from the cache host into the second machine's `vendomat.toml`. Fetching it over the network would be trust on first use and would defeat signing. Proposal: activation (or one `vendomat cache init`) generates the key if missing. Unproved. The Harmonia unit still needs a start condition so it does not fail before the key exists (`RESEARCH-2026-10-11.md` D11).

What remote deploy adds:

1. One controller for several machines. It builds once and copies.
2. A reviewed plan (`plan` then `apply`), a stale-plan check, and an SSH-access check (`machines.md:171-181`).
3. A target-side watchdog that restores the previous system when activation or a health check fails, or when the controller cannot confirm (`machines.md:183`, `FORK/src/modules/machines/deploy.py`).
4. Headless machines with no keyboard.

Verdict: remote deploy belongs to the 10 %, behind the explicit native door (`vendomat devenv machines deploy`). It also owns the admin key, the host pin, the re-pin, and the target address. Those mechanisms stay in the code and in the owner's path, not in the learner's record. Item 3 is a real loss for the learner: no automatic rollback after a bad activation (see Q4).

Unproved: a second ISO install from the same release, a local apply on a Basix machine, two-machine substitution with locally built outputs.

## Q4. Failed-unit gate (O10)

Evidence:

- Native behavior. `SPEC-V6.md:285` (`NAT-044`): "A declared unit that fails when `switch-to-configuration` starts it makes the switch exit 4. If a unit failed before the deploy and fails again on start, the deploy fails and the native rollback fails (`outcome: rollback-failed`). A failed unit that restarts cleanly does not block a deploy." The record is `P16/evidence/step-6.md` item 3.
- The `rollback-failed` outcome comes from the fork's target-side executor (`FORK/src/modules/machines/deploy.py`, states at lines 21, 148, 557). That executor is part of remote deploy.
- The gate: `SPEC-V6.md:202` (`MACH-022`): `systemctl --failed` empty before a deploy. `DOOR-066` requires it before apply and deploy.

Finding (simplest honest answer): for a local apply, native NixOS covers the case that matters. `switch-to-configuration` exits non-zero when a unit fails, and the previous generation stays in the boot menu. A refusal gate adds little there. The failed-unit gate protects one case only: a unit that was already failed makes the fork's automatic rollback fail (NAT-044). That case belongs to remote deploy. So:

1. Remote deploy and apply: keep the gate. This is the `MACH-022` case.
2. Local apply: print `systemctl --failed` after the switch and exit non-zero if the list is not empty. Do not refuse before the switch.
3. Keep "zero failed units on a keyless first boot" as a test gate on the Basix core (`DOOR-060`). It costs no runtime code in the learner path.

Inference: `nixos-rebuild switch --rollback` behaves like a normal switch, so a pre-failed unit makes it exit non-zero but still activates the old system. I did not run this. Unproved: any local apply on a Basix machine, and the exit status after a pre-failed unit.

Capability lost: no automatic rollback on a bad local activation. The learner recovers by running `nixos-rebuild switch --rollback` (or the equivalent) or by choosing the previous generation at boot. A bad activation that kills the console still needs the boot menu.

## Q5. Adoption of an existing NixOS install

Finding: adoption can be deferred. The plan already defers it (`PLAN.md:12-13`, `PLAN.md:62`; `SIMPLIFY-REVIEW-2026-10-12.md` mechanism row "Two machine modes", verdict "simplify").

R4 journeys affected (`R4-user-journeys.md`):

- Journey 7 (adopt a running NixOS machine) breaks: it is the adoption journey. Gap G06 (foreign configuration, `stateVersion`, Home Manager, root SSH on a laptop) stays open. Fixture-level only: `S7:206-230` proves an adopted VM gets the core with no partition tool executed. A foreign configuration was never adopted.
- Journey 5 (fresh install) and Journey 8 (several machines and a cache) do not break. Machine B and C come from fresh installs.
- Journeys 1 to 4 and 6 do not touch adoption. Journey 6 (later key delivery) names an adopted host, but its fresh route is the first-release route.

Side effects of the deferral:

- The first-release record loses the `mode` field. The fork still requires `vendomat.mode` for its remote `install` (patch 0006, `machines.rs:765-830`). The remote door keeps working only if the record sets `fresh-install`. Keep the fork patches 0005 and 0006 as they are.
- Owner's `framework` is an adoption (`P16` research, `memory: new-system-full-machines-blank-slate`). It waits. Local apply would make a later adoption simpler, because root SSH to self is not needed (`R4` Journey 7 step 1). That is inference.

Unproved: adoption of a foreign configuration (G06).

## Q6. The owner's own machines

Evidence: `memory/new-system-full-machines-blank-slate.md`: `server` goes on the 4 TB drive from a blank slate. The 512 GB system stays as a boot fallback. Installing from the same machine is not required. `.scratch/CURRENT.md` says `server` is installed fresh, then `framework` is adopted in place.

Differences from the learner path:

| Point | Learner | Owner `server` |
| --- | --- | --- |
| Install route | ISO on the target, local | Remote over root SSH, or SSH to self from the running 512 GB system (the G7 pattern) |
| Other disks | None to protect, or auto-protected | The 512 GB disk is a `keep`/protected disk. It must appear in the protected list, and the preflight checks it (`vendomat-preflight` `PROTECTED_BAKED`). |
| Identity fields | by-id only | by-id, model, serial, size baked at build (existing `guard.nix` rule) |
| Keys | None required | Installer key, admin key, host pin, re-pin |
| Secrets | None | `sops` age key and Tailscale, `install.secrets` or route 1 (`S7`) |
| Later changes | Local apply | Remote `plan`/`apply`/`deploy` from `framework` |

Finding: the owner's remote install does not need to be in the first release as a Vendomat routine workflow. The pinned fork already supports it with patches 0005 and 0006 and the G7 QEMU proof. The owner can run it through the explicit native door (`vendomat devenv machines install server --phases disko,install`). A real disk write needs separate authorization anyway (`PLAN.md:52-57`, `O7`). The first release must not delete the fork patches or the S7 key-separation fixture. The remote door keeps them. `server` and `framework` stay fixtures, not defaults (`R4` fact 5, gap G19: the module still names them in `nix/devenv-module/default.nix:172-181`).

Open owner decision: if the owner wants `server` installed by the same routine as the learner, then the local ISO flow must handle a protected second disk. That needs the optional protected list in the local mode.

## Summary of removals under the local-first design

Removed from the learner's first path: installer key, required admin key, required target address, controller, host-key re-pin, remote copy of the preflight, key delivery to a cache host (if the host generates its key), failed-unit refusal before a local switch, `mode` field, model/serial/size input.

Kept: stable by-id selection with typed confirmation, preflight against boot medium, mounts, partitions, signatures, and the target set, UEFI check, a console login credential, hardware report, zero-failed-units boot gate on the core, native rollback.

Moved to the explicit native door (10 %): remote install, remote deploy, the installer key, the admin key, the host pin and re-pin, the plan/apply watchdog, the failed-unit refusal.

Capability lost: install of a used disk (refused), unattended or headless install, one controller for many machines in the routine path, automatic rollback after a bad local activation, reviewed plans in the routine path, identity binding of model and serial in the learner record.

## What stays inference, what stays unproved (all questions)

Inference: the local flow needs no CLI-side binding; a live ISO store can hold the install; a cache host can create its own key; `nixos-rebuild --store-path` accepts a toplevel from the fork.

Unproved: kexec; a real installer ISO; the preflight inside a live ISO (G01); a local install script; RAM use of an install on a live ISO; console password set after install; local apply on a Basix machine; `nixos-rebuild --store-path` with the fork's `build.nixos`; exit status after a pre-failed unit; a real Basix core; hardware (`facter` phase, firmware boot); two-machine substitution with local builds.

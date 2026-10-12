# S7: keyless Basix core install and boot, installer credentials, post-install secret delivery

**Date:** 2026-10-11. **Spike:** S7 of project 20. **Status:** Tasks 1, 2, 3 (route 3 prototype), 4, 5 PASS on
disposable QEMU VMs. The role under test is a fixture core, not the real Basix core. No requirement ID is
allocated here. Every interface stays proposed until the real module passes the same fixtures.

## 1. Questions and hypotheses

| # | Question | Hypothesis |
| --- | --- | --- |
| Q1 | Do G7 and PV-11 prove a keyless Basix core boot? | No. G7 installed with payloads and ended with a failed unit. PV-11 booted a core without install. |
| Q2 | Can a core with no secret, no SecretSpec, and no cache client setting boot to zero failed units, and can a dependent service wait for a later key? | Yes, if each secret-dependent unit has a start condition. |
| Q3 | Which post-install route delivers, rotates, and recovers a key for fresh and adopted hosts? | A controller transfer over SSH works for both. A Machines extension serves install time only. Host-side resolution still needs one bootstrap credential. |
| Q4 | Does the installer's temporary credential persist on the target? | No, if the installed configuration lists its own admin public key. |
| Q5 | Does an adopted host need any disk step to receive the core and a later secret? | No. |

## 2. Exact inputs

| Item | Value |
| --- | --- |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the reference server pin) |
| Nix on the host | 2.34.7. Guest Nix 2.34.8 |
| Guest | NixOS 26.11 from that pin; systemd 261.3; OpenSSH 10.5p1; kernel 6.18 (nixosTest) |
| Fork CLI | `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0`; modules from tag `v2.4.0-vendomat.3` (`git+file://` of the fork, `dir=src/modules`) |
| SecretSpec | `secretspec 0.21.1` from the pinned nixpkgs (`/nix/store/fqqpg1vdcbfbwcbzvdldv1858iy0yz9m-secretspec-0.21.1`). The fork CLI bundles 0.21.0 |
| QEMU, OVMF | `qemu-host-cpu-only-11.1.1`, `OVMF-202608-fd`; KVM; unprivileged user `andrew`; no sudo |
| Fixture | `evidence/fixtures/s7-secrets/` (test-only keys and values; header in each file) |

Commands (the runner is `~/.local/state/vendomat/p20/2026-10-11/S7/bin/run.sh`):

```text
nix build --no-link --print-out-paths -f default.nix a.driver      # Spike A, routes 1 and 3
nix build --no-link --print-out-paths -f default.nix adopt.driver  # Task 5
TMPDIR=/mnt/shared/vendomat-p20/S7/run-X <driver>/bin/nixos-test-driver
python3 -I vm-keyless <fork devenv> <modules url> <rundir> <logdir> <qemu> <ovmf> <rev>   # Task 4
```

Disk guard before work: unallocated 6.09 GiB, metadata 84.5%. See section 10 for what happened later.

## 3. Task 1: what G7 and PV-11 proved

| Record | What ran | Credentials present at install | After first boot | Disk guards | Keyless core boot? |
| --- | --- | --- | --- | --- | --- |
| G7 (`16/evidence/step-7.md`) | Real `vendomat machine install` of the `server` role into a two-disk QEMU VM, boot of the new disk alone, one-shot `BootNext` | Controller deploy key; `install.secrets` (random runtime value); `install.extraFiles`; `install.copyHostKeys = true` (the installer's SSH host private key copied to the new disk) | Token 0400 and extra file 0640 present; key-only SSH; **1 failed unit** (`tailscaled-autoconnect`, no age key and no auth key: finding N1) | Real preflight: 25 of 25 injection cases and 10 of 10 direct CLI cases refuse with no write; identity, blank signature, mount, holder, `/mnt` checks | **No.** It carried secrets and the gate item `systemctl --failed` empty FAILED |
| G1 `vm-fixture` (`devenv-dist/fixtures/vm-fixture`) | Fork `install` with a stand-in preflight, then boot, then native `check/plan/deploy/rollback` on an adopt-mode machine | The same one SSH key for installer and installed root; `install.secrets` via SecretSpec `env` provider; `install.extraFiles` | Payload present | Stand-in preflight, dirty-disk refusal | **No.** Payload install by design |
| Step 6 `core-vm` (G6) | NixOS test of `nixos/core.nix` only, direct kernel boot, no install | Two test public keys injected | `is-system-running` = running, `--failed` empty, key-only SSH, no Vendomat | None (not an install) | **Partly.** Keyless and clean, but not installed, and the core excludes sops, Tailscale, Attic |
| PV-11 | NixOS test of a Nix-only core (user, SSH, Tailscale service, cache trust) | None | multi-user reached, name lookup, SSH restrictions; Tailscale not reachable | None | **Partly.** Pre-V6, no install, cache trust config only |
| PV-09 | Attic cold substitution | Pull credential | Not run in an installer VM | n/a | n/a. The credential problem disappears with Harmonia (no pull credential) |

**Precise statement.** No earlier record installed a core with no payload and then booted it to zero failed units.
G6 proves a keyless core boot without install. G7 proves the install route with payloads. G7 also shows the
exact keyless fault class: a role unit that needs a secret fails on first boot. Section 6 closes the gap for a
fixture core only. The real Basix core, real hardware, and the real preflight are not part of this proof.

## 4. Task 2: Spike A (nixosTest, nodes `controller` and `target`)

**Expected:** boot with zero failed units and no key; dependent service inactive but not failed; delivery,
rotation, deletion, reboot, and total disk loss all end with zero failed units; a control proves the failure
check can fail. **Actual:** `SUMMARY {"checks": 43, "failed": []}`, exit 0 (run `a8`).

Design under test (`basix-core.nix`, `basix-dep.nix`):

- Core: key-only `sshd`, one admin public key, `basix-secret-put` (a 25-line receiver), directories under
  `/var/lib/basix/` (mode 0700). No secret, no SecretSpec, default Nix cache config.
- Dependent unit `basix-dep.service`: `ConditionFileNotEmpty=/var/lib/basix/secrets/dep-key` and
  `LoadCredential=` of that file. A path unit (`PathChanged`) runs `systemctl restart basix-dep.service`.
- Receiver: writes into `/var/lib/basix/.staging`, sets 0400 root, then `mv` into place. The rename is atomic.

| Check | Result |
| --- | --- |
| T1 boot: `is-system-running` = `running`; `systemctl --failed` empty | PASS |
| T1 `basix-dep`: ActiveState inactive, Result success, ConditionResult no; path unit `waiting` | PASS |
| T1 no secret file, no `secretspec`, no `/etc/basix/secretspec.toml`; only `/etc/ssh/ssh_host_*` private keys on disk (made on first boot) | PASS |
| T1 `nix config show`: only `cache.nixos.org` and its key | PASS |
| T1 sshd: password and keyboard-interactive off, root key-only; wrong key refused; password login refused | PASS |
| T1 host key scanned by the controller equals the target's file (trust on first use) | PASS |
| T2 first delivery: service starts, sha256 of the credential equals the controller's value; file 0400 root:root; credential copy on `tmpfs`; value absent from the unit environment, the system closure, and the journal; staging directory empty | PASS |
| T3 rotation: new value, service restarted (new PID), new sha in the service; 0 failed units | PASS |
| T4a delete key: service stops, Result success, `/run/basix-dep` gone, 0 failed units | PASS |
| T4b redeliver: service active again | PASS |
| T4c reboot with key: key persists, service active, same host key, 0 failed units | PASS |
| T4d reboot after key removal: clean boot, service inactive, 0 failed units | PASS |
| T4e total disk loss (qcow2 deleted, same configuration): boots clean, secrets gone, **the pinned host key is now refused** (`REMOTE HOST IDENTIFICATION HAS CHANGED`), re-pin plus redelivery restores service | PASS |
| T4f control: an unguarded unit fails without the key and appears in `systemctl --failed`; `reset-failed` clears it | PASS (the failure check is real) |
| T4f observation: `scp` straight into the secrets directory leaves mode **0644** (umask), yet the service started with the full file | observed; not asserted |
| T5 route 3: see section 5 | PASS |

Development history: runs `a`, `a1` to `a7` failed on harness faults only (lint, `nix-command` flag, a `ssh-keyscan`
comment line, an `xargs` exit code, and a hang caused by `ssh` without `-n` reading the driver's console input).
They are not product defects. The final run is `run-a8.log`.

## 5. Task 3: route comparison and the route 3 prototype

### Fork findings (read from the fork source and docs; upstream docs are evidence about the tool only)

- `devenv machines install` is **native Rust** in the fork (`devenv/src/devenv/machines.rs`): phases
  `kexec, facter, disko, install, reboot`. It does not call `nixos-anywhere`. The option names mirror its flags
  (`install.extraFiles` "matches nixos-anywhere's `--extra-files`").
- `install.secrets`, `install.extraFiles`, `install.encryptionKeys`, `install.copyHostKeys` run **only in
  `install`**. Files go under `/mnt` (`stream_install_file` with `allowed_root "/mnt"`). The docs say: "Bootstrap
  files are written only by `install`, not refreshed by `deploy`." The `deploy`, `plan`, `apply`, and `rollback`
  code paths contain no secret or file hook.
- The streaming receiver (`install_file_receiver_script`) already does atomic replace with mode and owner. A
  `deploy`-time secret hook would reuse it with another `allowed_root`. That is a new fork patch.
- A host of mode `adopt-existing` never runs `install` (patch 0005). Route 2 as shipped cannot serve it.
- Upstream docs (devenv.sh machines, fetched 2026-10-11) say the same and recommend sops-nix or agenix for ongoing secrets.
- SecretSpec docs (secretspec.dev providers, fetched 2026-10-11): headless providers include `env`, `dotenv`, `file`,
  `pass`, `vault`, `age`, `sops`, `systemd-credential`; `keyring` needs a desktop; credentials for a provider can
  come from another provider (`credentials = { access_token = "keyring" }`).
- `secretspec` is in the pinned nixpkgs (0.21.1, 51.9 MiB download, 177 MiB unpacked).

### Route 3 prototype (SecretSpec resolves on the host): PASS

`basix-route3.nix` is a later specialisation of the target. It adds `secretspec`, a declaration-only
`/etc/basix/secretspec.toml`, and `basix-dep3.service` that runs `secretspec run --provider dotenv://<file>` at
start. `ExecCondition=secretspec check` keeps the unit skipped, not failed, while the provider cannot answer.

| Check | Result |
| --- | --- |
| After the switch the core now holds `secretspec`; `basix-dep3` skipped without the provider file; 0 failed units | PASS |
| Provider file delivered by route 1; unit starts; SecretSpec resolved the value; sha equals | PASS |
| Provider content rotated; unit restarted with the new value | PASS |
| Provider file without the secret: unit skipped (`Result=exec-condition`, not in `--failed`) | PASS |
| Provider file mode 0400 root:root | PASS |

Host-run probes with `secretspec 0.21.1` (unprivileged, loopback only): `dotenv://` works headless; `file://`
takes a **directory** (`<root>/<project>/<profile>/<KEY>`); `systemd-credential://` works only inside a unit that
has credentials; a missing secret exits 1 (no prompt when stdin is closed); the manifest default
`require_reason` is `"agents"`, which refused every call inside this agent session until the manifest set
`require_reason = false` (the project 20 fixture manifest already sets it).

The prototype shows that route 3 does not remove the bootstrap: the dotenv file is itself a secret that route 1
had to deliver. A remote provider (1Password service account, Vault AppRole) moves the same problem to one
provider credential on the host. That variant is **not tested**: no provider account, no network service.

### Comparison

| | Route 1: controller transfer (SSH, atomic receiver, path unit) | Route 2: Machines extension (`install.secrets` today; a `deploy` hook if patched) | Route 3: SecretSpec on the host |
| --- | --- | --- | --- |
| Operator steps | `secretspec get NAME \| ssh target basix-secret-put put NAME` (or a Vendomat wrapper). Dependent unit starts by path trigger | Install: set `install.secrets` and run `install`. Later: nothing exists. A patch would add an `apply`-time payload | Add the host-side declaration and provider; deliver the one provider credential (route 1); the unit resolves at start |
| What persists where | Plain value in `/var/lib/basix/secrets` (0400 root) on the target; a tmpfs copy in the service; the source of truth stays on the controller | Value on the target disk at the chosen path (install). Source on the controller (SecretSpec resolved locally) or in the installer (`execution = "target"`) | Provider credential on the target disk (or in the unit); values live in the provider; the unit holds them in memory |
| Rotation | Run `put` again. Tested: service restarts with the new value | Install only. A running host needs another route today | Change the value in the provider; restart the unit. With a file or dotenv provider it is route 1 again. Tested for dotenv; remote providers need a restart trigger |
| Recovery after disk loss | Reinstall (keyless), re-pin the new host key, run `put` again. Tested (T4e) | Fresh install re-runs the payload. Adopted host: not applicable | Reinstall, deliver the provider credential again; values stay in the provider. A bare-metal rebuild needs network reach to the provider |
| Adopted-host fit | Yes. Tested (A3, A4): the receiver arrives with the core switch | **No.** Install only; adopt never runs it. A fork patch could change this | Yes after the core switch adds the package and the credential arrives. Not tested on the adopted VM |
| Needs on the host | The core receiver; an authorized admin public key; ssh | Nothing extra for install | `secretspec` (177 MiB unpacked), manifest, provider reach, a bootstrap credential |
| Vendomat/Basix must build | Receiver script and directories in the core; guard pattern for dependent units; a controller command `vendomat secret push HOST NAME` that pipes `secretspec get`; host-key re-pin step | Nothing for install. For adoption: a fork patch (Rust plus option) that must survive every devenv bump | Option to enable the host resolver per service; provider choice; a restart trigger for remote providers; documentation of the bootstrap credential |
| Risks | Plaintext at rest on the target; the file stays after rollback (A6); raw `scp` writes 0644 and is not atomic; the controller needs a pinned host key; an `ssh` call that reads console stdin can hang a harness | A secret that exists only at install is stale after rotation; plan files must never carry values; fork maintenance | A standing provider credential on the host reads every secret in scope; network and provider uptime on the boot path; `require_reason` policy surprises; larger closure |

### Candidate route 4 (not tested here)

sops-nix or agenix with the age identity derived from the host's SSH key. The first boot generates the host key.
The controller reads the public host key, re-keys the ciphertext, and deploys through the normal `machines
deploy`. No private value moves. Project 16 step 8 proved a sops decrypt with a test key in a VM, but with a
host key that the install had copied in (`copyHostKeys`). The first-boot-generated variant, and the activation
behavior of sops-nix while its key is absent, are unproved. G7 finding N1 shows what an absent key does to a unit.

## 6. Task 4: fresh install, keyless variant (QEMU, fork `devenv machines install`)

**Feasible and run.** The G7 fixture is scripted, runs as `andrew`, and uses `/dev/kvm` (mode 0666). `vm-keyless`
(copy of `vm-fixture`, in `fixtures/s7-secrets/`) differs as follows: two keys; the installer key A reaches the
source VM and `devenv`; the installed configuration lists only the admin key B; no `install.secrets`, no
`install.extraFiles`, no `copyHostKeys`, no SecretSpec; the fixture core imports `basix-core.nix` and
`basix-dep.nix`. The preflight is the fixture **stand-in**, not `vendomat-preflight`. This run does not test disk
guards; G7 owns them.

**Expected:** install exits 0; the installed disk boots alone; zero failed units; A is refused; only the generated
SSH host keys exist as private keys; a later key arrives by route 1. **Actual:** `summary: 20 pass, 0 fail`.

| Step | Result |
| --- | --- |
| Source VM accepts A only; `devenv machines install fresh --phases disko,install` exit 0 | PASS |
| Boot the installed disk alone under OVMF; SSH works with **B** | PASS |
| SSH with **A** on the installed system: `Permission denied (publickey)` (exit 255) | PASS |
| Installed host key differs from the source VM's host key (generated at first boot; the file is 20 s old at 26 s uptime) | PASS |
| `is-system-running` = `running`; `systemctl --failed` empty | PASS |
| `/etc/ssh/authorized_keys.d/root` holds B only; no `/root/.ssh` entry | PASS |
| A's public key blob: not in `/etc /root /var /home /boot`, not in the system closure | PASS |
| Only `/etc/ssh/ssh_host_*` private keys on disk; no `secretspec`; no `/var/lib/bootstrap`; default Nix cache config only | PASS |
| `basix-dep` inactive/success with no key | PASS |
| Route 1 `put` over SSH as B: service starts, sha equals, mode 400 root:root | PASS |
| Reboot: key persists, host key unchanged, service active, 0 failed units | PASS |

**Installer credential persistence finding.** The temporary installer credential did **not** persist. The installed
system trusts only the keys that its own configuration declares. The installer's host key does not persist either
(unless `copyHostKeys = true`, which copies the installer's SSH host *private* key to the new disk; G7 used it).
The G1/G7 fixtures hide this because they use one key for both roles (`keyFiles = [id_ed25519.pub]`), so the
installer key becomes a permanent root key. Basix must name the admin public key in the inventory and treat the
installer key as separate.

Inference, not run: after install, the controller's `target.sshOpts` `IdentityFile` must change from A to B, and the
pinned `known_hosts` must change to the new host key, before `devenv machines check` or `deploy` works. The kexec
route (`install_kexec`) was not run; how the nixos-images kexec installer seeds its own root authorized keys is an
upstream behavior that this spike did not read or test.

## 7. Task 5: adopted host (nixosTest, nodes `controller` and `adopted`)

The `adopted` node boots as a plain NixOS host with sshd, one admin public key, `auditd` with an exec rule, one
formatted-but-unmounted disk `vdb`, and one blank disk `vdc`. The Basix core is a specialisation. The controller
holds its toplevel, runs `nix copy`, `nix-env --set`, and `switch-to-configuration`, then delivers a key.

**Expected:** core active, 0 failed units, key delivered, no partition or install tool executed, disks unchanged.
**Actual:** `SUMMARY {"checks": 20, "failed": []}`, exit 0 (run `d7`).

| Check | Result |
| --- | --- |
| A0 baseline: no `basix-secret-put`, no `basix-dep` unit, 0 failed, auditd active | PASS |
| A1 control: the audit trail records `sfdisk --version` | PASS (the detector can see a partition tool) |
| A2 a controller-only path moves over `ssh-ng` (`nix copy --no-check-sigs`) | PASS |
| A3 switch to the Basix toplevel: receiver present, 0 failed units, `basix-dep` skipped, no secret material | PASS |
| A4 later key by route 1: service active, 0400 root:root, 0 failed units | PASS |
| A5 `lsblk`/`blkid`/`sfdisk -d`/swap facts identical before and after; `vdb` and `vdc` full-device sha256 equal; **47 distinct executables** ran in the window, none in the partition and install list (`sfdisk fdisk cfdisk parted sgdisk gdisk wipefs mkfs.* mke2fs mkswap disko nixos-install blkdiscard partprobe cryptsetup dmsetup lvm losetup`); `/mnt` never mounted | PASS |
| A6 switch back to the booted system: Basix units and receiver gone; `dep-key` **still on disk** | PASS (observation: rollback does not remove delivered secrets) |

Limits. The test store is shared with the host, so `nix copy` of the toplevel reports `copying 0 paths`. The
second path (A2) proves that the transport moves new paths. Plain `nix copy` as root over `ssh-ng` failed with
`lacks a signature by a trusted key` until `--no-check-sigs`; root is a trusted user by default, so the cause is
unproved. The fork's own copy passed in G6 and G7, but the adopt procedure must state the trust requirement.
The audit window shows execution only for this switch, not for a full `devenv machines apply`.

## 8. Log paths

All under `~/.local/state/vendomat/p20/2026-10-11/S7/`:

- `run-a8.log`: final Spike A run (43 checks). `run-a1.log` to `run-a7.log`: harness development.
- `run-d7.log`: final adoption run (20 checks), includes `EXES` (the executed binaries). `run-d1.log` to `run-d6.log`: development.
- `fresh.out`, `fresh-logs/` (`steps.json` and numbered command logs): keyless fresh install (20 steps).
- `build-secretspec.log`, `build-*.err`, `bin/run.sh`, `bin/fresh.sh`, `fx/` (the fresh-install variant tree).
- Large images lived under `/mnt/shared/vendomat-p20/S7/` and were deleted.

## 9. Proves, inference, unproved

**Proves (fixture core, QEMU, pinned tools):**

1. A core with no secret, no SecretSpec, and default cache config boots to `running` and zero failed units, fresh-installed by the fork's Machines (Task 4) and in a test boot (Task 2).
2. A start condition (`ConditionFileNotEmpty` plus a path unit) keeps a dependent unit inactive, not failed, until a key arrives, and stops it cleanly when the key is removed. An unguarded unit fails (control).
3. Route 1 delivers, rotates, and recovers a key for a fresh host and an adopted host. After total disk loss, delivery restores service and the old pinned host key is refused.
4. The installer's temporary SSH key does not persist when the installed configuration lists a separate admin key.
5. An adopted host receives the core and a later key with no partition or install tool executed and identical disk facts.
6. SecretSpec resolution on the host works as a service-start step with a dotenv provider, and it skips cleanly when the provider cannot answer.
7. The fork has no post-install secret path. `install.*` payloads are install-only and are not refreshed by `deploy`.

**Inference:** the real Basix core can follow the same unit pattern; a remote SecretSpec provider behaves like the dotenv prototype; the controller identity and `known_hosts` must change after a keyless install; the `nix copy` signature fault comes from the stdio daemon trust rule.

**Unproved:** the real `nixos/core.nix` or Basix module; the real preflight on a keyless install; the kexec route; real firmware and disks; `devenv machines deploy` and `apply` against the keyless target; route 4 (sops-nix with a first-boot host key); a remote SecretSpec provider; Harmonia signing-key delivery (the same route 1, but not run); `systemd-creds`/TPM sealing; secret removal on rollback.

## 10. Disk and safety notes

- No sudo, no real disk, no host service, no GC. All VMs were QEMU/nixosTest with test-only keys.
- Before the work: unallocated 6.09 GiB, metadata 84.5%. During the work, concurrent builds (mine and other lanes') moved
  data chunks from 411.9 GiB to 417.9 GiB. After my last run: **unallocated 93 MiB**, metadata 85.6% (11.07 of 12.94 GiB),
  data used 375.9 of 417.9 GiB. That is below the 2 GiB stop rule. I ran nothing after seeing it. The root file system can
  still write data inside the allocated chunks (42 GiB free) but cannot allocate a new chunk. The owner should balance or
  free space before the next heavy build. My Nix store additions (VM closures, qemu, secretspec) stay in the store; I ran no GC.

## 11. Recommendation

1. Make **route 1** the one supported post-install route for fresh and adopted hosts. The Basix core ships the atomic
   receiver and the directory. Vendomat adds a controller command that reads the value from SecretSpec (or a file) and pipes it to the receiver.
   Never pass a value in `argv`. Never use raw `scp` for secrets.
2. Require the **guard pattern** on every role unit that needs a secret (`ConditionFileNotEmpty` or `ExecCondition`, plus a path
   unit for activation). Add a fixture check that `systemctl --failed` is empty on a keyless boot. This is the G7 N1 fix.
3. Keep `install.secrets` for the install-time convenience case. Do not patch `deploy` for secrets until route 1 proves too clumsy.
   A patch costs a Rust change and a rebase on every devenv bump.
4. Treat route 3 as optional per service for users with a remote provider. The host never requires SecretSpec. Note that its
   bootstrap credential still needs route 1.
5. Evaluate route 4 (sops-nix, first-boot host key) as the no-delivery alternative before the real Harmonia key work.
6. Put the admin public key in the inventory, separate from the installer key. Add a re-pin step after the first boot.
7. Add a removal verb and a documented rollback rule, because delivered secrets survive a rollback.

## 12. `NEW:` claims (proposed; no ID allocated)

- NEW: A fresh Basix core MUST reach `running` with zero failed units when no secret exists.
- NEW: Each unit that needs a secret MUST be skipped, not failed, until its secret is present, and MUST stop cleanly when the secret is removed.
- NEW: The core MUST include an atomic secret receiver: stage in a directory outside the watched path, mode 0400 root, then rename.
- NEW: The controller MUST send a secret over stdin to the receiver. It MUST NOT put a value in `argv`, the Nix store, or `scp` with the default umask.
- NEW: The inventory MUST hold an admin public key for each host, separate from the installer's temporary key. The installer key MUST NOT become a permanent root key.
- NEW: After a keyless first boot or a disk loss, the controller MUST re-pin the new SSH host key before it delivers a secret or runs a Machines command.
- NEW: A rollback or removal of a secret-dependent role MUST either remove the delivered secret or document that it stays on disk.
- NEW: SecretSpec MUST NOT be a host requirement. It MAY be the controller's value source and a host-side resolver for services that opt in.
- NEW: The adopted-host proof records the executed binaries during the switch and shows no partition or install tool in them.
- NEW: Fork `install.*` payloads are install-only; a later secret has no native fork route (observed in source and docs).

## 13. Concept changes

1. **Project 19 and project 20 disagree on SecretSpec.** Project 19 decision 7 ("SecretSpec is required configuration from the first
   setup") and its `install.secrets` text assume a SecretSpec setup before the first install. Decision 7 is already marked superseded by
   decisions 8 and 9, but the row still reads as live, and project 19 section 10 still lists keyless boot and post-install delivery as
   "Not proven". Project 20 section 6 says SecretSpec becomes required "when the first secret is used". This spike shows that SecretSpec is
   required nowhere on the host and only on the controller when `install.secrets` is used. Route 1 works with any value source.
   **Change:** state "SecretSpec is the recommended controller-side value source; the host never needs it." Mark project 19 decision 7 as
   superseded in its own row. Update project 19 section 10 to point to this record. Reword project 20 section 6 and `DOOR-016` accordingly.
2. **"Without a private key" needs a definition.** Every host has an SSH host private key from first boot (or copied from the installer with
   `copyHostKeys`). Write "no user-supplied private key or secret; the host generates its own SSH host key on first boot".
3. **Post-install route is no longer open.** Project 20 section 6 calls it "open until a fixture proves secure delivery and recovery". Route 1
   passed delivery, rotation, deletion, reboot, and disk-loss recovery for a fresh and an adopted fixture host. Keep it proposed until the real
   Basix core passes the same fixtures. Move the remaining open items to: secret removal on rollback, route 4, and host-key re-pin automation.
4. **Proof items 6 and 8** of project 20 section 8 have fixture-level evidence here. They stay open for the real Basix core and the real preflight.
5. **G7 N1** becomes a requirement shape (the guard pattern above), not only a server-role patch.
6. **PV-09** needs no installer pull credential under Harmonia; record the item as closed by design, not as passed.

# Step 8, services — the real `server` role in a disposable VM

**Date:** 2026-10-10. **Gate:** G8, services part. **Status:** PASS for the eight checks, with four
findings (one defect that blocks a fresh install) and the limits under "Not proven".

The VM is not the real server: no real firmware, disk, tailnet, or ciphertext.

**Branch:** `nix-systems` bookmark `v6-step8-services`, commit `39c86d39eb0483de9f038cfed3f981239d772a37`,
based on `main` `29e485bba43b17d8cd81a1c118e72762b0b4ef04`. Pushed to origin. `main` is not moved.
`nixos/server.nix` and `nixos/core.nix` are unchanged.

`[O]` = observed. `[I]` = inference. Raw logs: `~/.local/state/vendomat/v6/2026-10-09/08-legacy/services-vm/run3/`
(called `$L` below). Numbered files `NNN-name.log` hold one command each. `checks.json` holds the
check table. `disk.log` holds the disk figures.

## Pins and tools

| Item | Value |
| --- | --- |
| Patched devenv | `devenv 2.4.0+9726240`, `/nix/store/6djw5w3sil4c0s8z0dvaqcq832y4cfvb-devenv-wrapped-2.4.0`, fork tag `v2.4.0-vendomat.1` |
| Vendomat | CLI from the `v6-implementation` checkout (`main` `3cfe1b31a01b`); the disposable collection serves it as tag `v0.7.0` (locked rev `eb20b8f6b54e`) |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (node `nixpkgs_2`) |
| Inputs (lock, `$L/lock-pins.json`) | `repoman` v0.12.1, `gitman` v0.12.1, `testee` v0.5.0, `docman` v0.3.1, `copyroom` v0.8.1, `devman` v0.8.0, `sops-nix` `dcd241ba`, `home-manager` `6b88c12c`, `disko` `de570873` |
| Nix | 2.34.7 |
| QEMU, OVMF | `qemu_kvm` 11.1.1, OVMF 202608, KVM, `-m 4096 -smp 2`, systemd-boot under OVMF |
| Guest | NixOS 26.11.20261008.e7439b6; closure 892 paths |
| Role toplevel (unmodified) | `/nix/store/0h24dxaaslmwsd42s9hxfdaxi9jil8mf-nixos-system-server-26.11.20261008.e7439b6` |

## What was built

Files under `tests/services/` in `nix-systems`:

| File | Role |
| --- | --- |
| `services-vm` | Runner (Python, stdlib only). Stages `up`, `deploy`, `checks`, `down`, `all`. Records `checks.json` |
| `overlay.nix` | The only test change to the role (see "Overlay") |
| `devenv.local.nix` | Workspace overlay: machines `svcbase` and `svc`, and the base disk image |
| `ws-prepare` | Copies the repository, rewrites `[forge] url`, adds the overlay and parameters, runs `vendomat sync` |

The runner reuses `tests/core/make-test-collection.sh`, `tests/core/vendomat-cli`, and
`tests/core/vm-hardware.nix`. It never commits a lock: the lock names a loopback daemon and lives in
the copy only.

## Route and why

Route: the Step 6 flow. `svcbase` (core and VM hardware) is a small qcow2 image that boots first.
The runner then deploys `svc` (production `nixos/server.nix` plus the overlay) with the patched
`devenv machines plan` and `apply`, owner-run, over loopback SSH with a pinned host key. A reboot
follows, so the services start at boot.

Reasons `[I]`:

1. `system.build.vm` (`qemu-vm.nix`) replaces `fileSystems` with `mkVMOverride`. That drops
   `fileSystems."/mnt/wd_green1"`, the mount that `nixos/server.nix` defines. The deploy route keeps
   the generated `mnt-wd_green1.mount` from the production definition.
2. The deploy route runs the real `switch-to-configuration`, the real health check, and the real
   rollback. The failed-unit finding F1 came from that.
3. The base image stays small. The 3.4 GiB closure comes from the host store through `nix copy`.

## Overlay (what differs from production)

| Change | Where | Why |
| --- | --- | --- |
| `nixos/hardware/server.nix` and `nixos/server-disk.nix` replaced by `tests/core/vm-hardware.nix` | `devenv.local.nix` | Allowed. A VM has no disko disk |
| `inventory.deployKey` is a disposable public key | `devenv.local.nix` | Same as Step 6. The real deploy key's private half stays on the host. `loginKeys` stay the real public keys |
| `sops.defaultSopsFile` is a ciphertext made at test time | `overlay.nix` | The real `secrets/secrets.yaml` decrypts only with the real host key |
| `systemd.services.tailscaled-autoconnect.enable = false` | `overlay.nix` | The VM cannot join a tailnet. The unit is masked |
| `systemd.services.atticd-tailscale-serve.wantedBy = []` | `overlay.nix` | The unit needs a joined tailnet. It stays defined as the module defines it. The runner starts it by hand (below) |
| `svcTest.fixes`, empty in every check run | `overlay.nix` | Proves proposed diff F1 in one deploy |
| second disk, ext4, UUID `21488349-01cb-4efe-9d21-a72f74a908e0` | QEMU command line | The module mounts it at `/mnt/wd_green1` by that UUID |

The ciphertext: the runner generates an ed25519 key pair, derives the age recipient with
`ssh-to-age`, and encrypts four secret names with `sops` (`$L/004-sops-encrypt.log`). It installs the
private half in the VM as `/etc/ssh/ssh_host_ed25519_key` over SSH stdin (`$L/011-install-host-key.log`)
and pins the new host key (`setup` entries in `checks.json`). The private keys and plaintext live in a
0700 directory on tmpfs and are deleted by `down`. No private key is in the repository or the store.

**The real `secrets/secrets.yaml` was not decrypted.** It needs the real host key. The names in it
(`tailscale-auth-key`, `attic-signing-key`, and two unused ones) match what the module declares `[O]`,
but the value formats are unproven (see "Not proven").

## Result

| # | Check | Result | Raw log (under `$L`) |
| --- | --- | --- | --- |
| 1 | `systemctl --failed` empty after boot, and after a second deploy of the same plan | PASS | `044-failed-units-after boot of the deployed system.log`, `035-…`, `039-…`, `084-…` |
| 2 | SSH key-only | PASS | `045-ssh-root-deploy-key.log`, `085` to `089` |
| 3 | sops secrets, mode, no value in the store | PASS | `046` to `052`, `090-scan-logs-plaintext.log` |
| 4 | Collection over `git://` | PASS | `053` to `057` |
| 5 | Attic | PASS | `076` to `078`, `082-attic-mount-absent.log`, `083` |
| 6 | Dagu | PASS | `071` to `075` |
| 7 | Tools | PASS | `058` to `068` |
| 8 | No V4 | PASS | `069-v4-closure.log`, `070-v4-env.log` |

The final checks pass ran once, alone, on the VM that `deploy` booted (`checks.json` entries 23 to 68:
66 PASS, 3 OBSERVED, 0 FAIL). The failed units were empty at the end of the pass too.

### 1. Failed units

Commands: `systemctl --failed --no-legend --plain`, `systemctl is-system-running`, and
`systemctl --user --machine=andrew@ --failed`. Expected: none, `running`, none.

- After the first deploy of the unmodified role: 0 failed, `running` (`032-…`).
- After `machines apply` of the same plan id: `devenv` refuses it. `Stale deployment plan for svc:
  target generations changed; create a new plan`, exit 1, system unchanged (`033-apply-1-again.log`).
  0 failed units after (`035-…`).
- After a new plan and apply with no change: exit 0, same system, 0 failed (`036` to `039`).
- After the reboot into the deployed generation: 0 failed, `running`, system equals the toplevel
  (`042`, `044`).
- At the end of the pass, after the mount test and the refused logins: 0 failed (`084-…`).

### 2. SSH

| Command | Expected | Actual |
| --- | --- | --- |
| `ssh -i deploy root@vm 'id -un; sshd -T'` | `root`; `PasswordAuthentication no`; `PermitRootLogin prohibit-password` | exit 0, as expected, `KbdInteractiveAuthentication no` |
| `ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive root@vm` | refused | exit 255, `Permission denied (publickey)` |
| same, user `andrew` | refused | exit 255, `Permission denied (publickey)` |
| `ssh -i wrong root@vm` and `andrew@vm` | refused | exit 255 each |
| `ssh -i deploy andrew@vm` | refused (the deploy key is in root's list only) | exit 255 |

The pinned host key equals the disposable key's fingerprint (`setup` entry 3).

### 3. sops

- `stat`: `/run/secrets/attic-signing-key`, `/run/secrets/tailscale-auth-key`, and
  `/run/secrets/rendered/atticd.env` are `400 root root` (`046`). `sops-install-secrets` imported the
  host key as an age key (journal of the deploy, seen in `run1`).
- `cmp - /run/secrets/<name> < plaintext` prints `SAME` for both (`047`, `048`).
- `atticd.env` holds one `ATTIC_SERVER_TOKEN_RS256_SECRET_BASE64=` line and no `SOPS:` placeholder (`049`).
- Plaintext search with a positive control: `grep -c -F -f patterns /run/secrets/attic-signing-key` is
  1. Over the VM store (290 180 files) and `/etc`: 0 matches (`050`). Over the 892 host store paths of
  the toplevel: `grep` exit 1, no file (`052`). Over the raw logs of the run, plus a JWT-shape
  search: no file (`090`, `091`).

### 4. Collection

- Created `demo` (with `.git/git-daemon-export-ok`) and `private` (without) under
  `/home/andrew/vendor`. Pushed tag `v1.0.0` into both by path (`053`).
- `git ls-remote --tags git://127.0.0.1/demo` lists `refs/tags/v1.0.0` (`054`).
- `git ls-remote git://127.0.0.1/private`: exit 128, `access denied or repository not exported: /private` (`055`).
- `git push git://127.0.0.1/demo v1.0.1` and `... main`: exit 128 each, `access denied or repository
  not exported`. The repository keeps only `v1.0.0` (`056`).

Not run: the `post-receive` hook over SSH. The hook is not part of the module, and the run has no
login private key.

### 5. Attic

- `atticd`, `atticd-storage-setup`, and `mnt-wd_green1.mount` are `active`. `GET /` on
  `127.0.0.1:8089` returns 200. `findmnt -T /mnt/wd_green1/attic`: `/dev/vdb ext4
  21488349-01cb-4efe-9d21-a72f74a908e0`. The directory is `atticd:atticd 750` and holds `server.db`
  (`076`).
- `atticd-atticadm make-token` (reads the sops-rendered `atticd.env`) made an admin token and a pull
  token. `attic cache create`, `attic push` of one small path (`1 paths ... 0 already cached`), and
  `curl` of its `.narinfo`: with the pull token HTTP 200 and `StorePath:`; with no token 401; an
  absent path 404. A push with the pull token: `AccessError`. No token value is in a log (`078`).
  The Attic client is not in the role. The runner copied it into the VM store (`077`).
- Mount absent (`082`): `systemctl stop mnt-wd_green1.mount` stops `atticd` and
  `atticd-storage-setup`. The runner removed the data disk's PCI device. `systemctl start atticd` then
  failed after 90 s with `A dependency job for atticd.service failed`
  (`Dependency failed for /mnt/wd_green1`). After a PCI rescan, `atticd` and the mount were `active`.
  `systemctl show atticd -p RequiresMountsFor` lists `/mnt/wd_green1 /var/lib/atticd` (`083`).

### 6. Dagu

- `loginctl show-user andrew`: `Linger=yes`, `State=lingering`. `systemctl --user --machine=andrew@
  is-active dagu.service devman-watch.service`: `active`, `active`. `NRestarts=0` (`071`).
- Registry `/nix/store/n38bbpjfbpvff8293f9c6gri4y2lvp7n-server-registry` holds `dags`,
  `generation.json` (`"generation": 1`, `devman_runtime` 0.8.0), and `projects`; 26 DAG files (`073`).
- `GET /api/v1/dags?perPage=100` on `127.0.0.1:8080`: HTTP 200, 26 DAGs (7 projects with `check`,
  `maintain`, `test`; `devman` also `format`, `release`) (`074`). The Dagu page names `apiURL: /api/v1`.
- One disposable checkout `/home/andrew/Documents/Projects/docman` (a `devenv.nix` with one
  `base:check` task that prints `svc-dag-ran`). `POST /api/v1/dags/docman.check/start`, then the DAG
  run log: `DAG run finished status=succeeded`, and the task printed `svc-dag-ran` (`075`).
  The step ran `devenv tasks run -v base:check` as the Dagu user and fetched devenv and nixpkgs from
  GitHub (the VM has outbound network through QEMU user networking). In this pass the run took 1.5 s
  and the start call returned HTTP 500 (finding F3). An earlier pass, whose run took 64 s, returned 200.

### 7. Tools

All run as `andrew` in a login shell (`runuser -l andrew`), exit 0 (`058` to `068`):

- `devenv version`: `devenv 2.4.0+9726240 (x86_64-linux)`.
- `cd /tmp && vendomat --version`: `vendomat 0.6.0` (the launcher runs
  `VENDOMAT_HOST_RELEASE=/etc/vendomat/host-release/bin/vendomat` outside a workspace).
- `docman --help`, `repoman --help`, `gitman --help`, `testee --help`, `copyroom --help`: exit 0.
- `jj --version`: `jj 0.46.0-7d382314…`. `gh --version`: 2.102.0. `uv --version`: 0.12.22.
- `command -v` resolves each name under `/run/current-system/sw/bin`.

### 8. No V4

- `nix-store -qR /run/current-system` (892 paths): 0 names match `toolchain|consumer-module` (`069`).
- `REPOMAN_TOOLCHAIN_BIN`: 0 files among 445 unit files and the `etc` tree of the system, 0 in
  `/proc/*/environ`, 0 in the system and user manager environments, 0 in `systemctl show '*' -p
  Environment` (`070`).

## Findings

### F1. `git-daemon.service` fails on a fresh install (defect in `nixos/server.nix`)

- **Observed.** The first deploy of the unmodified role to a VM with no `/home/andrew/vendor` rolled
  back: `outcome: rolled-back`, `switch-to-configuration` exit 4, 316 s. The system returned to the
  base path. The journal: `git-daemon-start: fatal: base-path '/home/andrew/vendor' does not exist or
  is not a directory` (`017`, `018`, `020`).
- **Reproduction.** `python3 -I tests/services/services-vm deploy RUNDIR LOGDIR` (first step).
  By hand: a host with no `/home/andrew/vendor`, then `devenv machines apply` of `machines.server`.
- **Cause.** `services.gitDaemon.basePath = "/home/andrew/vendor"` is a directory that nothing
  creates. The health check (`systemctl --failed` is empty) turns that one failed unit into a rollback
  `[I]`. The live server has the directory. The Step 9 fresh install does not.
- **Proposed diff** (`nixos/server.nix`, after the `services.gitDaemon` block):

```nix
  # The base path of the git daemon. A fresh install has no vendor directory.
  systemd.tmpfiles.rules = [ "d /home/${user}/vendor 0755 ${user} users -" ];
```

- **Proof of the diff.** The overlay variant `fixes = [ "vendor-tmpfiles" ]` deployed the same role
  with exit 0, `andrew:users 755`, `git-daemon` active, 0 failed units (`021` to `026`, toplevel
  `…zlcn8g7pxfhdsjqg5cg2c409grs43dgm…`). The checks then ran on the unmodified role with the directory
  present, as on the live server.

### F2. The Dagu user units also start for root (devman module, `systemd.user.services`)

- **Observed.** A `systemd.user.services` unit belongs to every user manager. Root's manager exists
  while a root SSH session lives (every deploy). In the VM, `root: failed` for `dagu.service`:
  `failed to create listener on 127.0.0.1:50055: address already in use`, repeated restarts, then
  `start-limit-hit`. Andrew's `dagu` (PID 831) held `127.0.0.1:8080` and `:50055`
  (`072`). `devman-watch.service` also ran as root (seen in `run1`).
- **Risk.** `[I]` When root's manager wins the ports, root runs the automation plane, with
  `HOME=/root` and the wrong state directory. In the VM andrew's unit won, because the linger unit
  starts at boot.
- **Proposed diff** (`devman` `nix/nixos-module.nix`, on both user units; `lingerUsers` is the module's option):

```nix
  systemd.user.services.dagu.unitConfig.ConditionUser = map (u: "|${u}") cfg.lingerUsers;
  systemd.user.services.devman-watch.unitConfig.ConditionUser = map (u: "|${u}") cfg.lingerUsers;
```

- **Proof of the idea.** A runtime drop-in `ConditionUser=|andrew` in root's manager: `start` exits 0,
  `ConditionResult=no`, `inactive`, journal `skipped, no trigger condition checks were met`; andrew's
  `dagu` stayed active. Without the drop-in, root's `dagu` ran into `exit-code` restarts
  (`$L/finding-experiments.log`). The module change itself is not built or tested.

### F3. Dagu 2.15.0: the start API returns 500 for a run that ends in under 2 s (upstream)

- **Observed.** `POST /api/v1/dags/docman.check/start` returned HTTP 500 `DAG start process exited
  before publishing status`, while the run finished `succeeded` after 1.5 s (`075`). A run of 64 s
  returned 200 (`checks-pass1/075-dagu-run-dag.log`, the first run of that DAG in the VM).
- **Impact.** A caller that trusts the status code reports a failed start for a run that succeeded.
  No change proposed for this repository.

### F4. SSH is open on every interface, against the comment in `nixos/server.nix`

- **Observed.** `iptables -S nixos-fw`: `-A nixos-fw -p tcp -m tcp --dport 22 -j nixos-fw-accept` (no
  interface), plus `-i tailscale0 ... --dport 22` and `... --dport 9418`. Port 9418 is open on
  `tailscale0` and `lo` only. `sshd` listens on `0.0.0.0:22` (`$L/finding-experiments.log`,
  `079-tailscale-state.log`).
- **Cause.** `services.openssh.openFirewall` defaults to true. `nixos/server.nix` says "SSH and the
  collection are reachable from the tailnet only".
- **Decision for the owner.** Either change the comment, or add to `nixos/server.nix`:

```nix
  services.openssh.openFirewall = false;   # SSH only on tailscale0, as the comment says
```

  That choice removes LAN SSH. The Step 9 self-deploy uses `root@localhost`, which the loopback rule keeps.
  Not tested.

### Smaller observations

- `atticd-atticadm` prints `cd: /root: Permission denied` and a warning when run from `/root`. The
  wrapper runs as `atticd` with `--same-dir`. Cosmetic.
- `devenv machines apply <plan id>` of an applied plan is refused as stale (exit 1). A second deploy
  of the same configuration needs a new plan.
- OpenSSH `PerSourcePenalties` refuses new connections from one source after a few failed logins.
  QEMU user networking shows one source, so the refused-login tests run last and spaced.
  An early run lost its later checks to this.

## Not proven

- **The tailnet join.** `tailscaled-autoconnect` is masked. `tailscaled` runs and `tailscale status`
  says `Logged out`. The auth key never reached a control plane.
- **Tailscale Serve.** The unit text matches the module (`ExecStartPre tailscale wait`, `ExecStart
  tailscale serve ... --set-path=/attic http://127.0.0.1:8089`, `ExecStop`). Started by hand with no
  tailnet it failed after 60 s at `tailscale wait` (`080`). Publishing, the HTTPS endpoint
  `https://server.tail770f47.ts.net/attic`, its start order after a joined `tailscaled`, and the
  `ExecStop` are not run. `[I]` With the unit in `wantedBy`, an offline VM would fail it at boot and
  the health check would roll every deploy back; the runner did not run that variant.
- **The `tailscale0` firewall rules from a real peer.** The rules exist (F4). No peer connected.
- **The real ciphertext.** `secrets/secrets.yaml` was not decrypted. The real
  `attic-signing-key` value format (base64 of a PEM RSA key) and the real recipient list are unproven.
  The run used a 2048-bit key made by `openssl genrsa -traditional`.
- **Real hardware and disks.** The data disk is a 3 GiB virtio ext4 image, not the real drive.
  `fileSystems."/mnt/wd_green1"` by UUID is proven for that UUID only.
- **Migration.** The live collection, the live Attic database and cache, and the live Dagu generation
  were not touched or copied.
- **The real repositories' DAGs.** One toy checkout ran one `base:check`. The 26 DAGs list and render.
  No real repository ran, and the run needed GitHub.
- **Collection hooks over SSH** (`STORE-*`), and an SSH login as `andrew` (no login private key).
- **`machines install` and the fresh-disk route** (Step 7), and a self-deploy to `root@localhost` (Step 9).

## Run history and cleanup

| Run | What | Kept |
| --- | --- | --- |
| `run1` | Development. First deploy rolled back and found F1. The runner was killed during a second apply | logs only |
| `run2` | Development. Full flow. Harness faults: `sshd -T` path, git in `/root`, Dagu API version, registry lookup, `sshd` penalties | logs only |
| `run3` | Final. `up`, `deploy`, `checks`. Contents above | logs, `checks.json` |

In `run3`, the first `checks` passes overlapped (I started a second pass before the first ended; the
refused logins and the mount test of one disturbed the other). Their logs are in `$L/checks-pass1/` and
`$L/discarded-overlap/`. They are not evidence. The final pass is the one alone, `checks.json` entries
23 to 68, after fixing the runner (`git -C /tmp`, Dagu `/api/v1`, registry lookup, spaced logins).

Disk (`$L/disk.log`). Before the first build: `btrfs filesystem usage /` unallocated 977 MiB, metadata
79.5%. It was 1.00 MiB from the first deploy of `run1` on, because another lane took the last chunk.
It never reached 0. Metadata stayed at 79.6%. Data chunks went from 88.95% to 91.19% used. Each run
built a new 2.6 GiB `nixos-disk-image` in the store (new disposable keys, new image): four are mine.
Run `nix-collect-garbage` as the owner when free. I ran no GC. The qcow2 images, the data image, the
collection copies, and the keys are deleted.

## Commands to reproduce

```text
cd ~/Documents/Projects/gitman-workspaces/v6-services-vm   # any checkout of v6-step8-services
python3 -I tests/services/services-vm all /mnt/shared/vendomat-v6/services-vm/runN LOGDIR
# needs /dev/kvm, Nix, the patched devenv, about 12 GB of free store for one image and the closure
```

## Proposed document changes

For the lead to merge. IDs are proposals.

- `GATES.md` G8: "Closure, tool flakes, and the role-services VM PASS (step-8-services.md). Open: F1
  fix in `nixos/server.nix`, V4 removal in repositories with open work, `agentman`."
- `GUIDE-V6.md` Step 8 **Gate**: add "`tests/services/services-vm all` exits 0 in `nix-systems`".
- New observed facts: `NAT-045` (an applied plan is refused as stale), `NAT-046` (a `systemd.user.services`
  unit runs in every user manager, including root's), `NAT-047` (Dagu 2.15.0 start API 500 for a run
  under 2 s that succeeds), `NAT-048` (`PerSourcePenalties` and a single QEMU source).
- `nixos/server.nix` (F1, F4) and `devman` `nix/nixos-module.nix` (F2): apply the diffs above after
  the owner decides on F4.

## Addendum 2026-10-10: rerun on `main` `fe848434` (fork `v2.4.0-vendomat.2`)

**Status:** the services run PASS for all eight checks, with one runner fault named below. The
`tests/run` core rerun is **BLOCKED by disk** (no result). F1, F2, and the F4 comment are applied in
`main`.

**Branch:** `nix-systems` bookmark `v6-services-rerun`, commit `f6de84c91ec1bda9970d5e57467954427a108221`,
on `main` `fe8484347c55`. The commit changes only the runner and the overlay: the `fixes` variants and
the F1 reproduction steps are gone, and the disk guard stops under 1 GiB unallocated or over 85%
metadata. Pushed. `main` is not moved.

| Item | Value |
| --- | --- |
| Fork | `v2.4.0-vendomat.2`, rev `e2acb5b02b8627602e223128a082ecfd024850ab` (modules and CLI, `$A/lock-pins.json`) |
| CLI | `/nix/store/3mfmgg65mf08h7rhwd7w4f2vvcr9ia9i-devenv-wrapped-2.4.0`, `devenv 2.4.0+e2acb5b` |
| Role toplevel (unmodified) | `/nix/store/yvgz4rxkld5flxr5kvd9sash0x21464q-nixos-system-server-26.11.20261008.e7439b6`, 895 paths |
| Raw logs `$A` | `~/.local/state/vendomat/v6/2026-10-09/08-legacy/services-vm/rerun1/` |

### Services VM (`python3 -I tests/services/services-vm all RUNDIR LOGDIR`, one run, exit 1)

Expected for the first deploy: exit 0, no rollback, `git-daemon` active, 0 failed units, on a VM with
no `/home/andrew/vendor`. Observed `[O]`: `/home/andrew/vendor` absent before the deploy; `machines
apply` exit 0 in 21.2 s, `outcome: succeeded`, system equals the toplevel, `andrew:users 755`,
`git-daemon` active, 0 failed units (`$A/018-apply-unmodified.log`, `022-…`). No `fixes` variant ran.

| # | Check | Result | Raw log (under `$A`) |
| --- | --- | --- | --- |
| 1 | Failed units: after first deploy, same plan again, new plan, reboot, end of run | PASS | `022`, `025`, `029`, `034`, `074` |
| 2 | SSH key-only; password, another key, deploy key for `andrew` refused | PASS | `035`, `075` to `079` |
| 3 | sops: 0400 root, `SAME` content, no value in the store, `/etc`, host closure, or logs | PASS | `036` to `042`, `080` |
| 4 | Collection: tag listed; unmarked repository and push refused | PASS | `043` to `047` |
| 5 | Attic: API, `/mnt/wd_green1`, tokens, push, narinfo, mount absent | PASS | `066` to `068`, `072`, `073` |
| 6 | Dagu: linger, registry, API (26 DAGs), one DAG run (`start http=200`, `succeeded`) | PASS | `061`, `063` to `065` |
| 6b | Root's manager does not run `dagu` or `devman-watch` | PASS on content, FAIL as recorded (below) | `062-dagu-per-user.log` |
| 7 | Tools: `devenv version` is `2.4.0+e2acb5b`; the rest exit 0 | PASS | `048` to `058` |
| 8 | No V4: 0 of 895 paths match; 0 `REPOMAN_TOOLCHAIN_BIN` in 445 unit files, `etc`, environments | PASS | `059`, `060` |

Check 6b, observed `[O]` (`062`): `root dagu.service: inactive`, `ActiveState=inactive
ConditionResult=no Result=success`; the same for `devman-watch.service`; `andrew: active`; PID 788
(andrew) holds `127.0.0.1:8080` and `:50055`; 0 `address already in use` lines in the boot journal.
That is the expected result (F2 applied). `checks.json` still says FAIL: the command's last pipeline
stage, `grep -c`, exits 1 when the count is 0, and the runner required exit 0. The pushed commit
appends `; true`. I did not rerun this check on a VM (disk, below), so the record keeps FAIL and
the `; true` fix is untested. `checks.json`: 60 PASS, 1 FAIL, 1 OBSERVED (the Serve unit started by
hand, which fails at `tailscale wait`, as before). The limits under "Not proven" stand unchanged.

### `tests/run` (Step 6 core and Machines flow): BLOCKED, DISK

- Started with the services rerun, in parallel (`rerun2` of the services runner and `tests/run`).
- The services runner stopped itself after the base image build: `DISK blocker: unallocated
  1.00MiB at after-image` (`$A/../rerun2/all.err`, exit 3). I stopped `tests/run` at `lock-and-build`
  by hand. Its stage `collection` exited 0; no other stage ran
  (`06-nix-systems/rerun-fork2.out`). No result: neither PASS nor FAIL for any runner step.
- Disk: unallocated 7.01 GiB at the start, 3.01 GiB after the first services run (the run built one
  2.6 GiB image), 1.00 MiB when the two runs built their images together (data chunks 412.86 GiB to
  419.88 GiB; other lanes build at the same time). Metadata 77.9%. Free in chunks 37.6 GiB. I ran
  no GC. The qcow2 images, run directories, keys, and daemons of both runs are deleted. Each run
  leaves a new 2.6 GiB `nixos-disk-image` in the store.
- Mistake of mine: starting two image builds together while unallocated was 3 GiB. One at a time
  would have stayed above 1 GiB.

### What the next lane needs

1. Free chunk space (owner: `nix-collect-garbage`, or `btrfs balance`), or wait until another lane
   frees unallocated space above 3 GiB.
2. Run `tests/run` once, alone, from `main` `fe848434` or from `v6-services-rerun`.
3. Optionally rerun `tests/services/services-vm all` to turn check 6b green with the `; true` fix.

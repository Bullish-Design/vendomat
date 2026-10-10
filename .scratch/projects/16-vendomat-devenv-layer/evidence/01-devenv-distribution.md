# Evidence 01: the pinned devenv distribution (Guide Step 1)

**Date:** 2026-10-09. **Lane:** `v6-devenv-dist`. **Recipe:** `devenv-dist/` at the repository root.
**Raw logs:** `~/.local/state/vendomat/v6/2026-10-09/01-devenv/run1/` (early runs) and
`.../run1/final/` (the runs below). Observation and inference are kept apart in each gate.

## Result

| Gate | Result | Raw log (under `final/`) |
| --- | --- | --- |
| Upstream status check | PASS (recorded) | `../upstream-status.txt` |
| Series materializes, reproducible commit id | PASS | `materialize-commits.txt`, `materialize-b.json` |
| Release build, `devenv version`, derivation | PASS | `release-build.log`, `release-build-facts.txt` |
| `DVN-001` version string, `DVN-005` `latest-version` | PASS | `dist-fixture.out` |
| `DVN-002` `require_version: true` patched vs stock modules | PASS | `dist-fixture.out` |
| `DVN-004` packaging shape (git tag, `?dir=src/modules`) | PASS | `dist-fixture.out` |
| `DVN-008` offline shell, empty fetcher cache | PASS | `dist-fixture.out` |
| Patch 0005 unit tests and CLI tripwire fixture | PASS | `unit-tests.log`, `cli-fixture.out` |
| Patch 0006 unit tests and CLI fixture, every negative case | PASS | `unit-tests.log`, `cli-fixture.out` |
| Real install payload in a disposable QEMU VM, then boot | PASS | `vm-fixture.out`, `vm-fixture/` |
| Native commands on an `adopt-existing` machine (VM) | PASS | `vm-fixture.out` |
| `testee verify --full` | PASS | Testee run `20261010T023918Z-f9b95065a989` (pytest, ruff, ruff-format, ty) |
| Build on `server`, Attic push, cold substitution (`DVN-006`) | NOT RUN | not in this lane |
| `kexec` route with the patched CLI | NOT RUN | not needed for `MACH-008` |

## Pins and versions

| Item | Value |
| --- | --- |
| Upstream | `https://github.com/cachix/devenv`, tag `v2.4.0`, `b904dcb51fe48c30db250038241507f60752f222` |
| Fork commit | `972624027d5788c0590e4b9f09bd3c3fbc53adb4`, tag `v2.4.0-vendomat.1` (lightweight) |
| Patched CLI | `devenv 2.4.0+9726240 (x86_64-linux)` |
| Build output | `/nix/store/6djw5w3sil4c0s8z0dvaqcq832y4cfvb-devenv-wrapped-2.4.0` (391.6 MiB closure) |
| Build derivation | `/nix/store/ifjm5420pl8lcpsy9nlcwpvxwy048jp5-devenv-wrapped-2.4.0.drv` |
| Stock CLI used for comparison | `devenv 2.4.0+b904dcb`, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0` |
| Nix | 2.34.7 |
| nixpkgs (fixtures) | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| disko (fixtures) | `v1.13.0` |
| QEMU, OVMF | 11.1.1 (`qemu-host-cpu-only`), OVMF 202608 |

## 1. Upstream status

Observed on 2026-10-09 at 23:47 UTC with `gh api` and `gh pr view` (`../upstream-status.txt`).

- PR #3244: state OPEN, head `86b798f1e69781a5da68b7bcfc3691aad537e935`, last updated 2026-10-01,
  not merged, no review.
- `a5fd551a9a4a47532ccf2bd4f62fb48f37893947` (PR #3255, 2026-10-08) and
  `a5c34429421e077df6f8f133e502617bedc22206` (2026-09-26) are ancestors of `main`
  (`a73c5b84c9527760f009232988466763068f9f61`). No release or tag carries them.
- Latest release and newest tag: `v2.4.0`. There is no `v2.4.1`.
- `v2.4.0..main` is 24 commits. Two touch the series' files: `machines.rs` and `latest-version`.

Interpretation: no patch is unnecessary on a pinned release. The patch queue is unchanged.

## 2. The series

Applied in this order on `v2.4.0`. Each patch is a plain `git format-patch` file with an
`Upstream:` line in its header. The committer is fixed (`Vendomat Fork`, 2026-10-09T00:00:00Z).

| # | Patch | Upstream | sha256 (first 12) |
| --- | --- | --- | --- |
| 0001 | `fix(machines): allow Nix SSH connection handshake` | `a5fd551a` (PR #3255) | `514e1a90b766` |
| 0002 | `Update latest devenv version` | `a5c34429` | `206700fda87b` |
| 0003 | `fix(bootstrap): reuse locked inputs already in the store` | PR #3244, `86b798f1` (open) | `c4a121b9d237` |
| 0004 | `vendomat: build the devenv CLI as a release` | fork-only | `1cefc1dab785` |
| 0005 | `vendomat: refuse machines install for an adopted machine` | fork-only | `85eea6e22e52` |
| 0006 | `vendomat: require a target-bound preflight before a fresh install writes disks` | fork-only | `200d0325bbe4` |

Full hashes are in `devenv-dist/MANIFEST.sha256`. `git log v2.4.0..v2.4.0-vendomat.1` lists exactly
these six commits (`DVN-003`).

## 3. Materialization and reproducibility

Command: `python3 -I devenv-dist/materialize DEST [--source URL] --verify`. It needs an empty `DEST`.
It checks each patch against the manifest, fetches the pinned tag, checks the commit, applies the
series with `git am` under a fixed committer, and tags the result.

Observation: three runs into new directories from a local mirror, one run from the GitHub URL, and
the lane's own work clone gave the same commit id `972624027d5788c0590e4b9f09bd3c3fbc53adb4` and the
same tree. `--verify` against `devenv-dist/RESULT` passed each time.

## 4. Build and checks

Command: `nix build "git+file://<materialized>?ref=refs/tags/v2.4.0-vendomat.1#devenv" --accept-flake-config --max-jobs 3`.
Expected: build succeeds, `isRelease = true` from patch 0004. Actual: exit 0.

- `devenv version`: `devenv 2.4.0+9726240 (x86_64-linux)`. The `+rev` comes from `self.shortRev`,
  so a build needs a git ref (a `path:` source gives no rev).
- Unit tests (`machines::` filter, built through crate2nix `runTests`): 67 passed, 0 failed.
  The run used the lane's work clone plus a one-line `flake.nix` export that is not in the series.
  The 67 include the patch 0001 test and 15 new tests for patches 0005 and 0006.
- Dist fixture (`devenv-dist/fixtures/dist-fixture`, 10 checks, 0 failed):
  - `DVN-005`: `latest-version` `2.4.0`, crate version `2.4.0`, CLI `2.4.0`. Stock tag has `2.3.1`.
  - `DVN-002`: with `require_version: true` and patched modules, the shell exits 0. With stock
    `v2.4.0` modules it exits 1: "devenv CLI version 2.4.0 does not match the modules version
    2.3.1." A string constraint (`"2.4.0"`) with stock modules exits 0, as in project 15.
  - `DVN-004`: a `git+git://127.0.0.1:<port>/devenv?ref=refs/tags/v2.4.0-vendomat.1&dir=src/modules`
    input locks `rev` to the fork commit with `dir: src/modules`.
  - `DVN-008`: after an online `update` and shell, the git daemon stopped, `.devenv` removed, an empty
    `XDG_CACHE_HOME`, and proxies pointed at a dead port. Patched CLI exit 0, same source path as
    online. Stock CLI exit 1, failing at `resolve-lock.nix`.

## 5. Exact interface for the next lanes

### Nix option path and metadata path

Option on each machine: `machines.<name>.vendomat.mode`, type
`null or one of "fresh-install" | "adopt-existing"`, default `null`.

The CLI reads `devenv.config.machinesMeta.<name>.vendomat`:

```json
{ "mode": "adopt-existing" | "fresh-install" | null,
  "preflight": { "hasProgram": true, "ttlSeconds": 300 } }
```

Other options: `machines.<name>.vendomat.preflight.program` (null or a derivation whose output is
one executable file) and `machines.<name>.vendomat.preflight.ttlSeconds` (1 to 900, default 300).
The program builds as `machines.<name>.build.vendomatPreflight`. The lazy
`machines.<name>.installCheck.diskoDevices` holds the `device` of every disko disk.

### Policy before any contact (`machines_install`, after the names are validated)

| `vendomat.mode` | Result |
| --- | --- |
| `"adopt-existing"` | Refuse for every phase set, every `--disko-mode`, `--stop-after-disko`, `--no-reboot`. |
| `null` | Refuse for every phase set. |
| `"fresh-install"` | Allow. When the phases include `disko` or `install`, `preflight.program` must be set. |

`kexec`, `facter`, and `reboot` alone need no preflight: they write to no disk.

### Preflight contract (patch 0006), `vendomat.preflight/v1`

The CLI builds the program, runs `nix copy --to ssh://<target> <program>`, then runs over SSH on the
target, right before the encryption-key copy, disko, or nixos-install:

```
<program> --machine NAME --nonce HEX32 --phases CSV --disko-mode disko|format|mount
          --disk /dev/disk/by-id/ID [--disk ...]
```

- `--nonce`: 32 lowercase hex digits from `/dev/urandom`, new for each run.
- `--phases`: the selected phases in canonical order (`kexec,facter,disko,install,reboot`).
- `--disk`: one per disko disk. The CLI refuses a device that is not a `/dev/disk/by-id/` path.
- Stdout: exactly one JSON document. Stderr goes to the operator. Exit 0 only on a definite pass.
  Exit 1 for a definite fail (the program should still print a report that names failed checks).

```json
{
  "schema": "vendomat.preflight/v1",
  "result": "pass",
  "machine": "server",
  "nonce": "<the nonce from --nonce>",
  "host": { "machine_id": "<32 lowercase hex, /etc/machine-id>",
            "boot_id": "<36 characters, /proc/sys/kernel/random/boot_id>" },
  "disks": [ { "by_id": "/dev/disk/by-id/...", "model": "...", "serial": "...", "size_bytes": 4000787030016 } ],
  "checks": [ { "id": "blank-signature", "status": "pass", "detail": "optional text" } ]
}
```

The CLI accepts the report only when all of these hold. A single failure refuses the install:

1. The JSON parses with no unknown field, and `schema` is `vendomat.preflight/v1`.
2. `nonce` and `machine` equal the values the CLI sent.
3. `host.machine_id` and `host.boot_id` equal what the CLI reads itself with a second SSH command
   (`cat /etc/machine-id; cat /proc/sys/kernel/random/boot_id`) after the program run.
4. The set of `disks[].by_id` equals the set of disko devices of the evaluated NixOS config. Every
   disk has a non-empty `model` and `serial` and a non-zero `size_bytes`. No duplicate.
5. `result` is `"pass"`, `checks` is non-empty, and every check has `status` `"pass"`. A status of
   `"unknown"` or any other value refuses the install.
6. The program exit status is 0.
7. Time to live: the CLI measures the age from acceptance on its own clock. Each of the encryption-key
   copy, disko, and nixos-install checks the age against `ttlSeconds` and refuses past it.

The program, not the CLI, checks model, serial, size, signatures, and mounts against the inventory.
The Vendomat Python preflight (`MACH-010`) implements those checks behind this contract. The
stand-in `devenv-dist/fixtures/project/preflight-standin.sh` is a working reference.

A resume after a partial install (`--phases install` alone on a formatted disk) fails the stand-in
`blank-signature` check by design. Run `disko,install` again.

## 6. Patch 0005 and 0006 tests

### CLI fixture, fake `ssh`, fake `nix copy`, tripwire listener (`cli-fixture.out`, 29 cases, 0 failed)

For each adopt case: exit non-zero, message names `machines.adopt` and `adopt-existing`, the fake
call log is empty, the loopback listener saw 0 connections.

- Adopted machine refused for: default phases; `--phases` `kexec`, `facter`, `disko`, `install`,
  `reboot`, `disko,install`, `facter,install`, all five; `--stop-after-disko`; `--no-reboot`;
  `--disko-mode` `disko`, `format`, `mount`; `install` with `mount`; `disko` with `format`; and an
  adopted name in a list with a fresh name.
- A machine with no mode, and a fresh machine with no program, are refused with no contact.
- Fresh machine, `--phases disko`, scenarios (each refused before the disko run; the log shows the
  program copy and run only): program fails, result `unknown`, malformed output, wrong nonce, wrong
  machine, wrong host id, wrong disk.
- Pass scenario: copy, program run, identity read, disko copy, disko run, in that order, exit 0.
- Expired: ttl 1 s with a 3 s disko run: disko runs, nixos-install is refused ("3s old, limit 1s").
- Native `machines info adopt`: exit 0.

### Unit tests (Rust, in `machines.rs`)

Every non-empty subset of the five phases (31) for: adopted refused, no mode refused, program
required only for disko or install. Report validation: malformed, unknown field, fail, unknown,
mixed statuses, empty checks, wrong schema, nonce, machine, host id, boot id, wrong, missing, and
extra disk, empty serial. Disk set: kernel names, by-uuid, traversal, duplicates. TTL edge. Command
quoting. Nonce freshness.

### Real VM (`vm-fixture.out`, 21 steps, 0 failed)

Source VM: NixOS from `system.build.vm` with a second virtio disk (serial `TARGETDISK`). Root SSH on
`127.0.0.1:22833`. Pinned host key. `install.secrets` (SecretSpec `env` provider, dummy value) and
`install.extraFiles`. The stand-in preflight program, built by Nix.

1. Dirty disk (ext4 made in the VM): `--phases disko,install`, `install`, and `disko` each exit 1
   with the failed `blank-signature` check. `wipefs --no-act` after each still shows the signature.
2. Clean disk: `devenv machines install fresh --phases disko,install` exit 0. The program ran 4
   times on the target (3 refused runs and 1 pass), shown by its run record.
3. Unmount `/mnt`, power off, boot the installed disk alone under OVMF (systemd-boot, no NVRAM
   entry). SSH up on the same port. Hostname `vmfresh`, marker `GENERATION-1`,
   `/var/lib/bootstrap/token` mode 400 `root:root`, `/var/lib/bootstrap/extra` mode 640 `root:root`,
   sha256 of both equal the sha256 of the source values. 0 failed units. No file in `/nix/store`
   holds the token value.
4. On the booted system, as an `adopt-existing` machine with the same target: `machines install
   adopt --phases install` exit 1, and sshd logged no new login from it. Then `info`, `check`,
   `plan`, `deploy --yes`, `status`, and `rollback` all exit 0; the marker went `GENERATION-2`
   then back to `GENERATION-1`.

Image hashes (qcow2 deleted after the run): target after install
`3b260ea65710e031e456fce63ed93c1849300383356f5c2c6e9946265bcbb736`, after native deploy and
rollback `e5d344f526ad99614e7dc90510cae0832ea36965a44781b071296a10da474db3`.

An earlier VM run (`vm-fixture-attempt1`) failed one assertion of the fixture itself: the sshd login
counter counted its own measuring logins. The fixture now compares the step of one measurement with
the step across the refusal. The install parts of that run passed too.

Interpretation: the patched CLI installs a payload through the 0001 handshake fix, only after a real
preflight on the VM. The VM is not the real server: no real firmware, no kexec, no 4 TB disk.

## 7. Findings

- **F1.** `git+file://` inputs, even a bare repository, lock without `rev` or `narHash` in
  `devenv.lock` (keys: `dir`, `ref`, `type`, `url`). Only `git://` locks `rev`. The collection
  serves `git://`, so the production shape is unaffected. A `git+file` URL is not a pin.
- **F2.** devenv prints only the outermost message of an `install` failure
  (`- <machine>: <message>`). A `wrap_err` cause stays hidden. Patch 0006 puts each cause into the
  message text itself.
- **F3.** Mode `null` is refused for install. A workspace that defines machines without
  `vendomat.mode` cannot run `devenv machines install` with this CLI. The Vendomat module (`VMOD-016`)
  must set the mode for every machine.
- **F4.** A repeated install over a disk that a failed run left formatted fails the preflight. This
  is intended.

## 8. Not covered

- Building on `server`, the Attic push, and cold substitution (`DVN-006`, Guide Step 1 item 7).
- The `kexec` phase of the patched CLI, and `--phases` with `kexec` against a real installer.
- The real server: the PV-02 disk scan, real firmware, and `BootNext`.
- The Vendomat Python preflight itself (`MACH-010`). Only the contract and a stand-in exist.
- Multi-machine concurrency with a mix of modes (unit-tested only: one adopted name refuses all).

## Proposed document changes

For the lead to merge. IDs are proposals. Check them against the ledger before use.

### SPEC-V6.md

- `DVN-003`: Verify now reads `git log v2.4.0..v2.4.0-vendomat.1` lists the six patches in
  `devenv-dist/SERIES`. The prototype patch file in project 15 is history.
- `DVN-004`: add to Verify that the pin is a `git://` URL with `?ref=refs/tags/<fork tag>&dir=src/modules`
  and that the lock holds `rev` and `dir`. A `git+file` URL gives no `rev` (finding F1).
- New `DVN-009`: The patched `devenv machines install` MUST refuse a machine whose
  `machines.<name>.vendomat.mode` is `"adopt-existing"` before it reads a payload, builds, or
  contacts the target, for every `--phases` set, `--stop-after-disko`, `--no-reboot`, and
  `--disko-mode`. **Verify:** `devenv-dist/fixtures/cli-fixture` adopt cases and the VM step
  `adopt-install-refused-no-contact`. Supersedes the research draft's first half of `DVN-009`.
- New `DVN-010`: The patched CLI MUST refuse any install of a machine with no `vendomat.mode`, and
  MUST run a target-side preflight (`vendomat.preflight/v1`, contract in evidence 01 section 5)
  before the encryption-key copy, disko, and nixos-install of a `"fresh-install"` machine. It MUST
  accept only a definite pass bound to the nonce, the machine, the host's machine-id and boot-id, and
  exactly the disko disks, and MUST refuse a result older than `ttlSeconds`.
  **Verify:** unit tests and cli-fixture fresh cases; the VM dirty-disk and clean-disk steps.
- `MACH-007`: its **Open** note closes with the VM step `install-fresh` and `payload-on-installed-disk`.
  Keep **Open** for the real server.
- `MACH-008` and `MACH-010`: state that the CLI gate (`DVN-010`) is in addition to the Vendomat
  command, and that the preflight program is the `MACH-010` implementation behind the contract.
- `VMOD-016` proposal (research section 8): require `vendomat.mode` for every machine, because
  the patched CLI refuses a machine without it (F3).
- New `NAT-041`: a `git+file://` input in `devenv.yaml` locks without `rev` (F1).
  New `NAT-042`: `devenv machines install` shows only the outermost error message of each failed
  machine (F2).
- `NAT-037` (install hang): add that patch 0001 fixed it on `v2.4.0` and a real install completed
  with `install.secrets` and `install.extraFiles` in a VM (evidence 01).

### GUIDE-V6.md Step 1

- Item 1: the series is six patches: four from project 15, then 0005 (adopted denial) and 0006
  (fresh preflight). State that the recipe is `devenv-dist/` and the tool is `devenv-dist/materialize`.
- Item 3: "Materialize a tagged distribution source in the collection" is done up to the bare tag.
  Push of the tag to the collection stays an operator step. The packaging shape is proven on a
  loopback `git://` daemon.
- Item 4: name the option path `machines.<name>.vendomat.mode` and the metadata path
  `machinesMeta.<name>.vendomat`.
- Item 5: name the contract in evidence 01 section 5 as the fresh-host rule.
- Item 7: still open (`server` build, Attic push, cold substitution).
- **Stop if** line: the denial test exists and passes for the tested phase and mode set.

### CONCEPT-V6.md

- Section 1 table: add rows for the two fork-only machine patches, and say that the fork has six
  patches. The "Evidence" line can cite the 67 unit tests and the VM run.
- Section 7: the preflight is run by the patched CLI, and the Python preflight is the program that
  it runs. A direct `devenv machines install server` fails without a current preflight.

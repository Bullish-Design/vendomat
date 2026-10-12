# R4: user journeys through the project 20 design

**Date:** 2026-10-11. **Task:** R4. **Kind:** read-only trace. No spike, build, or command ran.
Every status below comes from reading the documents and code named in the cells.

**Read:** `AGENTS.md`, `.scratch/CURRENT.md`, project 20 (`CONCEPT`, `DECISIONS`, `REQUIREMENTS`,
`PLAN`), project 16 (`CONCEPT-V6`, `CONCEPT-UPDATE-2026-10-10`, `CUTOVER-REVIEW`,
`RESEARCH-2026-10-09-MACHINE-PATHS`, `evidence/GATES`, `wrapper-spikes`, `fork-3-inheritance`,
`01-devenv-distribution`, `step-3a`, `step-5`, `step-6`, `step-7`), projects 17, 18 (`CONCEPT`,
`exp-A-harmonia`), and 19 (`CONCEPT`, `DECISIONS`). Code: `launcher/vendomat`,
`src/vendomat/{cli,devenvgen,check,machine,yamlsubset,defaults}.py`, `nix/devenv-module/*.nix`,
`templates/workspace/*`, `direnv/vendomat.sh`, and `devenv-dist/patches/0005` to `0008`.

## Status legend

| Status | Meaning |
| --- | --- |
| EXISTS | Code implements the step today. The cell cites the code. The code still uses `vendomat.toml`. |
| PROVED-ELSEWHERE | An older gate proved the mechanism. The cell says why this is not proof of the project 20 interface. |
| PROPOSED | Only the project 20 design states the step. No fixture exists. |
| GAP | The design does not say. A fixture or an owner decision must answer. |

Gap IDs (`G01` and up) point to the consolidated list at the end.

## Facts that apply to every journey

1. Today the launcher serves only `sync` inside a workspace and exits 3 for any other command
   (`launcher/vendomat:56-66`). Project 20 decision 1 and `DOOR-010` reverse that. The launcher
   test `test_in_a_workspace_every_command_but_sync_is_sent_to_the_shell` must change.
2. Today the launcher finds a workspace by `vendomat.toml` (`launcher/vendomat:43`). The project 20
   marker file is not named in code. See `G11`.
3. The launcher says nothing when it runs the pinned build. It speaks only when it falls back to
   the host release (`launcher/vendomat:70-74`, `115-118`). The rule "every command reports which
   release it used" (CONCEPT section 2) is not implemented. See `G11`.
4. No project 20 runtime or machine gate has passed (`CURRENT.md`). Fork `v2.4.0-vendomat.3` is the
   only piece of the new path that has a passing record (`fork-3-inheritance.md`, 9 of 9 cases).
5. `server` and `framework` appear only as fixtures. The module defaults in
   `nix/devenv-module/default.nix:172-181` still name them (`hosts = [ "server" "framework" ]`,
   `users = [ "andrew" ]`). See `G19`.

---

## Journey 1: new workspace with no lock

Goal: a user makes a workspace and enters a shell. The host release creates the first lock.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Create the workspace. Today: `vendomat-workspace-init model.json DIR`. | Today: renders `vendomat.toml` with Templateer; copies `devenv.nix` and `devenv.yaml` stubs (`templates/workspace/init`). | Nothing. | New `vendomat.toml`, `devenv.nix`, `devenv.yaml`. | None. Needs `templateer` on `PATH`; the model holds `forge_url`, `vendomat_tag`, `devenv_tag`. | EXISTS for TOML (`step-3a.md`, `testee check workspace-e2e`). The project 20 command, model, and `vendomat.yaml` stub are a GAP (`G10`, `G12`). |
| 2 | Edit `vendomat.yaml`: inputs, imports, values. | Nothing. | Nothing. | `vendomat.yaml`. | None. | PROPOSED. |
| 3 | `vendomat shell` | The host launcher finds the workspace root, sees no `devenv.lock`, says "using the host release to bootstrap it", and runs the host release (`launcher/vendomat:70-74`). | Nothing. | None. | None. | Bootstrap EXISTS (`test_a_new_workspace_with_no_lock_bootstraps_with_the_host_release`). The `shell` command through the launcher is PROPOSED (today exit 3). |
| 4 | (automatic) | Parse and lint `vendomat.yaml` with no Nix. Report file, line, key, reason. | Nothing. | None. | None. | PROPOSED. `yamlsubset.py` is not the project 20 subset: it accepts flow collections and rejects block lists of maps. Vendomat depends only on Typer, so no YAML library exists (`G10`). |
| 5 | (automatic) | Build the input fragment. Today: prefetch each import, read its `devenv.yaml`, add `follows`, write `.vendomat/devenv.yaml` (`devenvgen.py` `_Discovery`). | `nix flake prefetch`-class fetches. | `.vendomat/devenv.yaml` (and today `.vendomat/devenv.nix`, `.vendomat/digest`). | Network: collection (`git://`), `github:NixOS/nixpkgs`. No credential for `git://` read. | EXISTS for TOML. Project 20 says "do not resolve a second transitive graph" (CONCEPT section 5), but fork-3 says shared-child `follows` (`PRE-005`) stays a Vendomat job. Which one holds is a GAP (`G13`). |
| 6 | (automatic) | Ask devenv to lock. Today: `ensure_lock` runs `devenv update`, judges the result by lock contents, and restores the old lock on failure (`devenvgen.py:408-452`). | `devenv update` writes `devenv.lock`. | `devenv.lock`. | Network: every input. | EXISTS for TOML (`PRE-008` fixture). |
| 7 | (automatic) | Load or generate the option schema for the locked revisions; validate values. | `devenv eval` of the workspace with an introspection module. | Schema file under `.vendomat/` (location unnamed). | Network only if sources are not yet in the store. | PROPOSED. PROVED-ELSEWHERE for the exporter: project 17 `GM2` (1330 records, stable hash) and the strict models for five subtrees. Not proof here: it ran in the `devenv-py` harness project (private repo), not in a user workspace, and not under Vendomat. The neutral-data question in CONCEPT section 4 is open (`G15`). |
| 8 | (automatic) | Write `.vendomat/config.json` (option data), schema, hashes. Write only on change (`DOOR-007`). | Nothing. | `.vendomat/*`. | None. | Atomic write with new mtime EXISTS for the fragment (`devenvgen._replace`, `PRE-011`). `config.json` is PROPOSED. |
| 9 | (automatic) | Run `devenv shell` (the pinned fork). | Module reads `config.json` with `builtins.fromJSON`; assertions check the digest and tag pins; fork patch 0007 inherits inputs; patch 0008 copies a lazily mounted source into the store; builds or substitutes the shell closure. | `.devenv/` state. | Network: collection, substituters (cache.nixos.org). | PROVED-ELSEWHERE: fork-3 live proof on the real collection, cold then warm, 9 of 9 fixture cases. Not proof of project 20: the fixture consumer declares its imports in `devenv.yaml`, not through `vendomat.yaml` and `config.json`. Which `devenv` binary the pinned Vendomat runs is a GAP (`G12`). |
| 10 | (automatic) | Print the release used. | Nothing. | None. | None. | GAP (`G11`). |
| 11 | Commit the workspace. | Nothing. | Nothing. | VCS. | None. | GAP: no rule says whether `.vendomat/` and `devenv.lock` are committed (`G09`). |

Failure modes and the error the user should see:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Invalid YAML (alias, tag, flow collection, implicit string) | `vendomat.yaml:LINE: key 'K': reason`; exit before Nix | PROPOSED (`DOOR-012`) |
| Key not declared by any imported module | `vendomat.yaml:LINE: 'basix.x' is not an option of the locked modules; is the module in imports?` | PROPOSED. Only possible after step 6 (`G14`). |
| Tag missing in the collection, or collection down | `devenv update ... did not lock every requested input; no devenv.lock was kept` plus the failing input | EXISTS (`devenvgen.py:440-452`) |
| Input pinned to a branch | `vendomat: these git inputs are not pinned to a tag ... Set '?ref=refs/tags/<tag>'` | EXISTS (`lock-pin.nix`, `default.nix` assertion). The text still names `vendomat.toml` and `vendomat sync`. |
| No host release | `vendomat: no host release at PATH` exit 2 | EXISTS (`launcher/vendomat:30`) |
| No network on first run, empty store | A single message: "first run needs the network; nothing is cached" | GAP. Today devenv or Nix prints its own fetch error. |
| `devenv` on `PATH` is stock, not the fork | `the CLI was built from X but the locked modules are Y` | EXISTS in `vendomat check` (`check.py` `version_problems`). The fork-only features fail with a Nix error otherwise (`G08`). |
| Recognized secret field holds a value | `vendomat.yaml:LINE: key 'K' is a secret field; use secretspec.toml` | PROPOSED (`DOOR-014`) |
| Host is low on btrfs metadata space | Build fails with a Nix I/O error | Host fact from memory; not a design gap. |

Gaps in this journey: `G09`, `G10`, `G11`, `G12`, `G13`, `G15`.

---

## Journey 2: existing pinned workspace

Goal: a workspace already has a lock. The lock pins a Vendomat release. The launcher hands off.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `vendomat shell` | Launcher finds the root; reads `.nodes.vendomat.locked.narHash` from `devenv.lock`; converts it to hex (`launcher/vendomat:75-83`). | Nothing. | None. | None. | EXISTS (`test_a_pinned_workspace_runs_its_own_build_found_by_nar_hash`). |
| 2 | (automatic) | If `~/.cache/vendomat/launcher/<hex>` names an executable, run it with no Nix call (`:85-91`). | Nothing. | None. | None. | EXISTS (`test_the_build_is_cached_by_nar_hash_and_runs_without_nix`). |
| 3 | (automatic) | Cache miss: compute the store path with `nix-store --print-fixed-path`; build `path:$store#packages.$system.vendomat` with `--offline`, then online (`:93-101`). | Nix builds the Python package. | Launcher cache file. | None when the source is in the store. | EXISTS (`test_a_missing_source_is_fetched_from_the_locks_own_reference`). |
| 4 | (automatic) | Source not in store: build from the lock's own reference. Handles `git` and `github` nodes only (`:103-116`). | Nix fetches. | Launcher cache file. | Network: the lock's source. | EXISTS. Other node types fall to the host release without saying why. |
| 5 | (automatic) | Pinned build is missing and unfetchable: run the host release and say so (`:117-122`). | Nothing. | None. | None. | EXISTS for `sync`. Project 20 serves all commands, so this fallback now reaches `build`, `test`, and `machines` (`G11`). |
| 6 | (automatic) | Pinned build runs the command sequence: lint, compare digest, skip generation when unchanged, run `devenv`. | `devenv shell`. | None when unchanged. | None offline if sources are in the store. | Unchanged-digest fast path EXISTS for TOML (`devenvgen._unchanged`; `PRE-010` 0.142 s with the daemon stopped). The project 20 digest must cover `vendomat.yaml`, the lock, and the schema (`G13`). |
| 7 | (automatic) | Print the release used. | Nothing. | None. | None. | GAP (`G11`). |

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Lock has no `vendomat` node | `devenv.lock pins no vendomat input; using the host release` | EXISTS |
| Pinned build missing, source unreachable | `the Vendomat pinned by LOCK is not in the store and cannot be fetched` and `using the host release to repair` | EXISTS. For a `machines` command the host release must refuse instead (`G11`). |
| Host release older than the pin; it cannot read `vendomat.yaml` | `vendomat.yaml needs Vendomat >= X; this release is Y` | GAP. The file has no format version (`G11`). |
| Stale `vendomat.yaml` after a direct edit, then plain `devenv shell` | `vendomat: STALE. ... Run: vendomat shell` | EXISTS for TOML, text names `vendomat sync` (`devenvgen.NIX_MODULE`). `DOOR-009` PROPOSED. |
| `VENDOMAT_USE_HOST=1` set | `vendomat: VENDOMAT_USE_HOST=1: using the host release` | EXISTS |

Gaps: `G11`, `G13`.

---

## Journey 3: offline workspace

Goal: no network. The user enters a pinned workspace.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `vendomat shell` | Launcher resolves the pinned build. Cache hit or an in-store source works with no network (`:85-101`). | Nothing. | None. | None. | EXISTS. If the source was collected, the launcher tries an online build, then a fetch. Each waits for a timeout (`:100`, `:112`). No `--offline` is forced (`G13`). |
| 2 | (automatic) | Lint; compare the digest of `vendomat.yaml`, lock, and generated files. All equal: no Nix call. | Nothing. | None. | None. | Fast path EXISTS for TOML. Lock is not in today's digest (`G13`). |
| 3 | (automatic) | Load the schema "for its locked revisions". Missing: stop with a missing-schema error. | Nothing. | None. | None. | PROPOSED (`DOOR-011`). Schema location and key are GAPs: committed, or derived and ignored (`G13`). A fresh clone offline has no schema if `.vendomat/` is ignored. |
| 4 | (automatic) | Run `devenv shell`. | Patched devenv reuses locked inputs already in the store (patches 0003 and 0008). | `.devenv/` state. | None if every input and the shell closure are in the store. | PROVED-ELSEWHERE: `DVN-008` passed on `server`: the source in the store, the daemon stopped, the patched shell entered; stock devenv failed (`fork-3-inheritance.md`). Not proof of P20: it covers input reuse, not the shell closure or the launcher. `G1` cold substitution on another host stays BLOCKED (`GATES.md`). |
| 5 | The `vendomat.yaml` changed since the last lock | Cannot lock. Stop. | Nothing. | None. | Needs network. | GAP: the message and the rule that the old lock must not be used silently (`G14`). |

"Missing pinned build" has two meanings. The first is the pinned Vendomat build (launcher, steps 1
and the failure table in Journey 2). The second is a shell closure that a substituter held. In the
second case Nix builds from source offline, or fails. The design names neither.

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Schema for the locked revisions absent | `no option schema for these locked revisions; connect once and run vendomat prepare` | PROPOSED text; command name GAP (`G10`) |
| Locked source absent from the store | `input NAME is not in the store and the network is down` | GAP. Today devenv prints `path ... is required, but there is no substituter` (`fork-3-inheritance.md`, cold defect). |
| `vendomat.yaml` newer than the lock | `vendomat.yaml changed (input X); locking needs the network` | GAP (`G14`) |
| Slow timeouts on dead substituters | A bounded wait and one line | GAP. No `connect-timeout` or `--offline` rule exists. |
| Launcher cache entry points to a collected path | Rebuild; if offline, host release | EXISTS (the launcher tests `-x`; falls through). |

Gaps: `G11`, `G13`, `G14`, `G15`.

---

## Journey 4: change an imported tag; a new option appears; set it in the same edit

Example: the user raises input `tools` from `v1.0.0` to `v1.1.0`. Release `v1.1.0` adds option
`services.foo.level`. The user sets `services.foo.level: 3` in the same edit.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Edit `vendomat.yaml`: new tag and new key. `vendomat shell` | Lint the shape only. The key `services.foo.level` cannot be checked against the old schema. | Nothing. | `vendomat.yaml`. | None. | PROPOSED (`DOOR-011`: shape first, schema after the pin). |
| 2 | (automatic) | Digest differs. Regenerate the fragment. | Prefetch of the new tag. | `.vendomat/devenv.yaml`, `digest`. | Network: collection. | EXISTS for TOML. |
| 3 | (automatic) | Update the lock for the changed input. `ensure_lock` runs `devenv update NAME` when one input differs, else `devenv update` (`devenvgen.py:422`). | Re-lock. Patch 0007 re-reads the imported source's `devenv.yaml`. | `devenv.lock`. | Network. | EXISTS for direct inputs. Whether inherited child nodes (for example `tools-defaults`) re-lock at the new tag is unproven. `fork-3` has no tag-change case (`G14`). |
| 4 | (automatic) | Generate the schema for the new revisions. Validate the new key. | `devenv eval` over the new modules. | Schema file. | Network if the source is not in the store. | PROPOSED. Exporter PROVED-ELSEWHERE (project 17). A changed pin means a changed export hash by design (`MDL-006`); the project 17 cold cost was 103 s for four subtrees (`step-15-final.md`). The cost for a whole workspace is unmeasured (`G15`). |
| 5 | (automatic) | Write `config.json` and the new digest. | Nothing. | `.vendomat/config.json`, `digest`. | None. | PROPOSED. |
| 6 | (automatic) | Run `devenv shell`. | The new module declares `services.foo.level`; the value merges natively. | `.devenv/`. | Network or store. | PROPOSED. A plain definition of the same option in the new release conflicts with the YAML value. Under `DOOR-013` the conflict stops with both locations (`G16`). |

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Typo in the tag | `input tools: ref refs/tags/v1.1.9 not found`; old lock restored | EXISTS (`ensure_lock` restores) |
| Branch instead of tag | The pin assertion text (see Journey 1) | EXISTS |
| New key invalid in the new schema | `vendomat.yaml:LINE: services.foo.level: expected int, got "high" (option declared in tools@v1.1.0)` | PROPOSED. The lock has already moved. Existing code restores the prior lock and fragment only when locking fails (`devenvgen.py:526-535`). The rule after a validation failure is a GAP (`G14`): keep the new lock and report, or restore. |
| New release removed or renamed an option the file uses | `unknown option 'X'; renamed to 'Y'` when the module declares a rename | GAP. Project 17 leaves renamed and alias options out of the models (`MDL-035`). Native Nix accepts them with a warning. Vendomat could reject a key that Nix accepts (`G16`). |
| New option has an unsupported type (function, `deferredModule`, `output`) | `option 'K' needs native Nix; put it in devenv.nix` | PROPOSED. Project 17 maps these to `NixExpr`, a coverage miss. |
| Two imports declare one input differently | The fork error names both imports | PROVED-ELSEWHERE (`fork-3` fixture case 4). The message points at `devenv.yaml`, not `vendomat.yaml`. |
| Offline | See Journey 3 step 5 | GAP |

Gaps: `G13`, `G14`, `G15`, `G16`.

---

## Journey 5: fresh NixOS install from a controller onto a new disk

Goal: a user installs NixOS on a blank disk of another machine. The machine boots with no key.

Controller prerequisites (a list, since the design names none):

1. Nix, the pinned devenv fork CLI, and a Vendomat release (host release or pinned shell).
2. A system workspace with a `fresh-install` host, its disk identities, and its NixOS module.
3. Disk space for the system closure (3.4 GiB, 905 paths for `server`; `CUTOVER-REVIEW.md` section 6)
   and for the build. The host btrfs metadata fact in memory applies to the owner's host only.
4. A deploy key pair. The private key stays on the controller. The public key goes into the
   inventory. A public key is not a secret.
5. Network access to the collection, nixpkgs, and a cache. The target needs only a route to the
   controller (inference: `nixos-install` runs from a copied closure; `01-devenv-distribution.md`
   section 6 shows no fetch on the target).

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Write the host in `vendomat.yaml`: `mode: fresh-install`, disks with `byId`, `role: install-target`, plus `model`, `serial`, `sizeBytes`. | Map `basix.machines.*` to `vendomat.inventory.*`. | Nothing. | `vendomat.yaml`. | None. | `vendomat.inventory` EXISTS (`default.nix:86-110`). The `basix.machines` names are PROPOSED. The CONCEPT example omits `model`, `serial`, and `sizeBytes`, but `guard.nix` requires them for an install-target (`incomplete` assertion). How a user learns them is a GAP (`G04`). |
| 2 | Give the host `target.host`, `target.sshOpts`, known-host pin. | Pass `sshOpts` and the port to its own `ssh` calls (`machine.py:62-69`, `MACH-025`). | Machines uses root SSH. | `vendomat.yaml` or `devenv.nix`. | SSH key. | The names in YAML are a GAP (`G20`). The CONCEPT example has no `target`. |
| 3 | Boot the target from an installer; give the controller temporary root access. | Nothing. | Nothing. | None on the controller. | Temporary credential: a root key or password on the installer. | GAP (`G01`). The wrapper's own ssh uses `BatchMode=yes` (`machine.py:63`), so a password prompt fails. The fork refuses `kexec` joined with `disko` or `install` (patch 0006), so the default `machines install` that boots an installer by kexec cannot run. The proven route used a running OS with a second blank disk, not a live installer. |
| 4 | Get hardware facts: facter report or `hardware.facter = null` and an explicit hardware module. | `plan_install` stops if `.machines/HOST/facter.json` is missing or untracked (`machine.py:145-163`). | `machines install --phases facter` runs `nixos-facter` on the target and writes the report into the repository. | `.machines/HOST/facter.json`. | SSH. | EXISTS as a stop. The `facter` phase was never run in any record (`step-7.md` "Not covered"). `server` used a hand-written hardware module. A blank machine needs the report before the install can start (`G04`). |
| 5 | `vendomat machine install HOST --dry-run`, then without `--dry-run`. | Runs `check_workspace`, reads `vendomat.modes`, refuses non-fresh hosts, then runs exactly `devenv machines install HOST --phases disko,install` (`machine.py:123-181`). | Builds `machines.HOST.build.nixos`; guard assertions run at build. | `.devenv/` plans. | Network: builds. SSH to target. | EXISTS (`test_machine_install.py`). The CONCEPT names `vendomat machines ...`; the code has `vendomat machine install`. The name is a GAP (`G20`). |
| 6 | (automatic) | Nothing more. | Patched devenv: refuses adopted mode and a bad phase set before contact; copies the preflight to the target; runs it with a nonce; needs a definite pass bound to machine-id and boot-id; then disko, then `nixos-install --no-root-password`; copies host keys and extra files. | Target disk. | SSH root. Optional `install.secrets`. | PROVED-ELSEWHERE: G7 in QEMU (25 of 25 injection cases, 10 of 10 direct cases, install in 69-71 s, old disk and ESP unchanged, new disk boots alone; `step-7.md`) and the 21-step payload fixture (`01-devenv-distribution.md` section 6). Not proof of project 20: the VM was the running controller's own `root@127.0.0.1:PORT` with a second blank disk. No live installer, no remote machine, no kexec. Real firmware and the real drive are unproven (`GATES.md` G9). |
| 7 | (automatic) | After success, unmount `/mnt` and turn off the new swap over ssh (`machine.py:184-197`). | Nothing. | Target runtime state. | SSH. | EXISTS (`step-7.md` W1 to W3). |
| 8 | Remove installer media; reboot; pick the boot entry. | Nothing. The wrapper never reboots. | Firmware loads the bootloader. | None. | None. | GAP on real hardware. In QEMU the new disk booted from the removable path (`EFI/BOOT/BOOTX64.EFI`) with `canTouchEfiVariables = false`. Real firmware may need a menu choice. CUTOVER steps 12 to 15 are manual `efibootmgr` commands for the owner's dual-disk case only. |
| 9 | First boot. `devenv machines status HOST`. | None. | Core role boots; sshd key-only; root accepts the deploy key. | None. | SSH to the new system. Host key: the installer's key is copied (`copyHostKeys`) so the first pin holds. | PROVED-ELSEWHERE: the core booted with no Vendomat and only public keys (`step-6.md` item 2); the installed system booted alone in QEMU (`step-7.md`). The first-contact trust of the installer's host key is trust-on-first-use (`G01`). A secret consumer in the role leaves a failed unit (`step-7.md` N1), so the keyless core must hold none. |

Disk identity guards, in order:

1. Module assertions at build: every disko disk is an install-target of the same name and `byId`; no
   shared id with a `keep` or `existing-system` disk; no kernel name or `by-partlabel` mount; model,
   serial, and size present (`guard.nix`). EXISTS, QEMU-proved.
2. Target preflight: path resolves; model, serial, size match; no signature (`wipefs`, `blkid`);
   not the running root or `/boot`; nothing under `/mnt`; protected disks resolve; tools present
   (`MACH-010`, `MACH-024`). EXISTS, QEMU-proved. A live installer environment was never the target.
3. Fork CLI gate: result bound to nonce, machine, machine-id, boot-id, and the disko disk set; expires
   after `ttlSeconds` (default 300 s). A slow disko run can let the `install` phase see an expired
   result (`01-devenv-distribution.md`: ttl 1 s case refused `nixos-install`). Disk size and speed
   against the 300 s default are unmeasured (`G04`).

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Disk has any signature or partition | Preflight names `no-signature-wipefs`, `no-signature-blkid`, `no-partitions` | PROVED-ELSEWHERE (matrix cases d, e, e2). No supported way to wipe a used disk exists. The user wipes by hand with no guard (`G03`). |
| Wrong model, serial, or size | Preflight names `identity` | PROVED-ELSEWHERE (cases a to c) |
| Install-target is the running disk | Names `not-mounted` and `no-partitions` | PROVED-ELSEWHERE (case i) |
| Direct `devenv machines install` with default phases | `use --phases disko,install` before any contact | PROVED-ELSEWHERE (`C1`, fork `.2`) |
| Adopted host | `host 'H' has mode 'adopt-existing'. machine install runs only for a fresh-install host.` | EXISTS (`machine.py:139-144`) |
| Facter report missing | `.machines/H/facter.json is missing. Commit a nixos-facter report ...` | EXISTS |
| Disko fails midway | The install failed (exit N). Nothing was unmounted. Inspect the target | EXISTS (`cli.py` `machine_install`). A rerun then fails the preflight on the half-formatted disk (`01-devenv-distribution.md` F4). The user must wipe by hand (`G03`). |
| Target unreachable | SSH error from devenv | GAP: no Vendomat message for a missing or wrong temporary credential (`G01`). |
| Installed system has no Wi-Fi credential, no user password, no disk passphrase | The machine boots and cannot be reached | GAP (`G17`). "Keyless" covers signing keys. Laptops need a network credential. Disk encryption needs a passphrase. |

Credentials touched: temporary installer root access (removed by the reboot); the controller's deploy
private key (persistent, controller only); public keys (inventory). None enters the store.

---

## Journey 6: later key delivery and service activation

Example: deliver the Harmonia signing key, then enable the cache server.

Common steps for all routes:

| # | Step | Status |
| --- | --- | --- |
| a | Create a signing key pair: `nix-store --generate-binary-cache-key NAME secret public`. Where it runs and where the secret rests are not stated. | GAP (`G05`) |
| b | Commit the public key into the inventory (a non-secret value). | PROPOSED (P19 decision 10) |
| c | Deliver the secret to a root-owned path on the target, before the service starts. | GAP: route open (`G05`) |
| d | Set the cache-server mark in `vendomat.yaml`; `vendomat machines plan HOST`; review; `apply`. | PROPOSED. The mark's name is a GAP (`G07`). |
| e | The `services.harmonia` module starts and signs. | Not proven. Project 18 ran the standalone `harmonia-cache` binary as a user, on loopback. It did not run the NixOS module (`exp-A-harmonia.md` "Not shown"). |
| f | If the service fails, devenv rolls the deploy back after `rollbackTimeout`. The key stays on disk. | PROVED-ELSEWHERE for the native watchdog (`step-6.md` item 3, health check `false` gave `rolled-back`). A failed unit before a deploy makes rollback fail (`NAT-034`, `step-6.md`). |

Ordering rule that every route needs: the secret must exist before `apply` starts the unit. A unit
that finds no secret fails; one failed unit fails the whole deploy (`NAT-034`; `step-7.md` N1).

Route comparison:

| Question | A. Authenticated controller transfer | B. devenv Machines extension | C. Host-side SecretSpec resolution |
| --- | --- | --- | --- |
| Mechanism | The controller reads the secret from its SecretSpec provider and pipes it over the root SSH session into a file (owner, mode set). No file on the controller disk, no argv. | Fork patch: the `apply` or `deploy` step writes SecretSpec values to target paths, like `install.secrets` does at install. | The target resolves the secret itself (`secretspec` on the host) from a provider that the host can reach. |
| Vendomat or fork code needed | A small command, or a documented `ssh` line. None exists. | New Rust patch for `apply`. The fork carries 8 patches; patch 0006 alone adds 1049 lines to `machines.rs`. | A SecretSpec install on the target, a boot-time unit, and a provider credential on the host. |
| Works on a fresh host | Yes, after first boot. | Yes. | Only when the provider is host-local. |
| Works on an adopted host | Yes (root SSH is already required). | Yes if the patch covers `apply`. | Same limit. |
| Trust chain | Controller key to root SSH. Already the base of all Machines. | Same, plus the plan file must not hold values. Plans live in `.devenv/machine-plans/` (`RESEARCH` section 1). | The provider credential on the host is a second secret. Delivering it is the same problem again. |
| Atomic with the reviewed plan | No. Two steps. The key can exist while the apply fails. | Yes, if written in the same transaction as the switch. | No. Resolved at runtime. |
| Evidence | Plain SSH. No Vendomat fixture. | `install.secrets` with the SecretSpec `env` provider, dummy value, PASS in QEMU: mode 400, `root:root`, hashes equal, no secret in the store (`01-devenv-distribution.md` section 6; `step-7.md` success path). Upstream tool behavior in the install phase only. The extension has no fixture. | `install.secretspec.execution` exists as install-time metadata (patch 0005 context). No runtime fixture. |
| Failure and recovery | Re-run the transfer. Idempotent if the path is overwritten. | A failed apply rolls back; the delivered file may stay. | Boot-time unit fails if the provider is unreachable; the dependent service fails the deploy. |
| Leaves the key where after rollback | On disk | Depends on the patch | On disk or resolved at boot |

Reading of the comparison (inference, not a decision): route A needs no fork change and fits both
host modes. Route B gives one reviewed step but adds fork upkeep and has no fixture. Route C does
not remove the first-secret problem. A fourth route, a NixOS secret module (sops-nix or agenix),
needs its own age identity on the host. `CUTOVER-REVIEW.md` section 7 proved decrypt in a VM with a
test key only. The age key delivery is the same problem.

Evidence conflict: project 19 section 10 lists `install.secrets` as "documented upstream; not run
here". `01-devenv-distribution.md` section 6 and `step-7.md` record a passing QEMU run of it with
the `env` provider. Project 19 understates the evidence (`G05`).

Credentials touched: the signing secret (new); root SSH (existing). Network: SSH to the target.

Gaps: `G05`, `G07`, `G17`, `G22`.

---

## Journey 7: adopt a running NixOS machine without disk installation

Goal: manage a machine that already runs NixOS. No disk is written.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Make root SSH key-only on the host through the host's current configuration route. | Nothing. | The host's own `nixos-rebuild`. | The host's config. | Deploy public key on the host; private key on the controller. | PROPOSED (`MACH-020`). A laptop that is its own controller needs an SSH server on itself (`root@localhost`). Enabling it changes the host before adoption (`G06`). |
| 2 | Write the host: `mode: adopt-existing`, disk `role: existing-system` with `byId`. | Map to `vendomat.inventory`. | Nothing. | `vendomat.yaml`. | None. | Module EXISTS (`guard.nix` adopt rules: no disko disk, no install-target, one existing-system). YAML names PROPOSED. |
| 3 | Bring the host's existing configuration into the NixOS module: hardware, bootloader, filesystems, users, `stateVersion`, Home Manager. | Nothing in the design. | Native modules. | `devenv.nix` or an imported file. | None. | GAP (`G06`). Research says the first generation must keep the exact nixpkgs revision and state versions (`RESEARCH` section 6, `MACH-018`, `MACH-019`). The Basix core role imposes sshd, users, and keys; merging it with an existing config is untested. |
| 4 | `vendomat machines check HOST`, `plan HOST`. | Pass through to `devenv machines`. | Evaluates; builds closure; records `plan-ID`; reads the current generation over SSH. | `.devenv/machine-plans/`. | SSH root. | PROVED-ELSEWHERE: `check`, `plan`, `apply`, `status`, `rollback` ran against an adopted VM (`step-6.md` item 3). The VM image came from the same toolchain, not from a legacy host. No adoption VM of a foreign config has run (`CONCEPT-V6` build order step 6). |
| 5 | Review the plan. Run `vendomat machines apply plan-ID`. | Should run the failed-unit gate first. | `nix copy`; the target executor switches; the watchdog waits for the health check. | Target store, profile, `/etc`, services, boot entries. | SSH root. | Apply PROVED-ELSEWHERE as in step 4. The gate (`MACH-022`) is `Proposed` and not part of any Vendomat command (`G22`). |
| 6 | Run `vendomat machine install HOST` by mistake. | Refuse: `host 'H' has mode 'adopt-existing'`. | Nothing. | None. | None. | EXISTS (`machine.py:139-144`, `test_machine_install.py`). |
| 7 | Run `devenv machines install HOST ...` directly. | Nothing. | Patched devenv refuses before any SSH contact, for every phase set and disko mode. | None. | None. | PROVED-ELSEWHERE: unit tests for all 31 phase subsets; VM step: exit 1, sshd logged no new login (`01-devenv-distribution.md`). Root or `sudo` can still run `disko` by hand (`CONCEPT-V6` section 8). |
| 8 | `vendomat machines rollback HOST`. | Pass through. | Selects `previousSystem`; runs `switch-to-configuration switch`. | Profile, boot entries. | SSH root. | PROVED-ELSEWHERE on the VM (`step-6.md`). Cannot undo mutable data. Fails when a unit failed before the deploy (`NAT-034`). |
| 9 | Deliver a later secret before activating a dependent service. | See Journey 6. | | | | GAP (`G05`). `SEC-003` is `Proposed`: an adopted host keeps its own age identity. |

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| No root SSH, or wrong host key | `machines check` exit 1; host unchanged | PROVED-ELSEWHERE (`step-6.md`, wrong key and wrong known_hosts rows) |
| Plan shows an unplanned upgrade (nixpkgs differs from the host's) | The plan names changed services and boot entries | PROPOSED. No Vendomat check compares the host's revision with the pin (`G06`). |
| A failed unit exists before apply | Gate names the unit | `MACH-022` Proposed; the native bypass shows `rollback-failed` (`step-6.md`) |
| New generation does not boot | The user picks the previous generation in the boot menu | Not in the design (`CUTOVER-REVIEW.md` section 10 covers `server` only) |
| Existing config uses `by-partlabel` or kernel names | `vendomat guard (H): a fileSystems device uses by-partlabel or a kernel name` | EXISTS (`guard.nix`). This blocks adoption of many existing hosts until the user edits their config (`G06`). |

Gaps: `G05`, `G06`, `G20`, `G22`.

---

## Journey 8: grow from one machine to several machines that share a cache

Goal: machine A has a local store. Machines B and C should substitute from A through Harmonia.

| # | The user runs | Vendomat does | devenv, Nix, NixOS do | Files change | Network and credentials | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Nothing to start. One machine uses its local store. | Nothing. | Nix store. | None. | None. | PROPOSED (P19 section 4). Nothing to run. |
| 2 | Mark machine A as the cache server in the inventory. | Validate that exactly one host is marked. | Nothing. | `vendomat.yaml`. | None. | Name and place of the mark are a GAP. P19 says "inventory first". `basix` names are PROPOSED (`G07`). |
| 3 | Create and deliver the signing key (Journey 6). Commit the public key. | Check that the public key is present before clients trust it. | Nothing. | `vendomat.yaml` (public key). | Signing secret via the chosen route. | GAP (`G05`). |
| 4 | `plan` and `apply` on A. | Derive Harmonia settings from the mark: listen address, firewall. | The `services.harmonia` NixOS module serves A's store, signed. | A's system. | Listener on a trusted network. | The module was not run (`exp-A-harmonia.md`). The default listener is a GAP: P19 proposes loopback plus one named interface; HTTP on a trusted network. Tailscale Serve is the owner's choice, not a default (`G07`). |
| 5 | Plan and apply on B and C. | Derive `substituters` (after upstream caches), `trusted-public-keys`, and fallback from the mark. | `nix.conf` changes. | B and C configs. | Read access to A over the network. No credential. | Wiring PROPOSED. Cold signed substitution PROVED-ELSEWHERE on loopback only, as the owner's user (`exp-A-harmonia.md`: cold copy exit 0, NAR hash equal). No second machine, no module, no cache failure test (`PLAN` stage 6). |
| 6 | Build on A. | Nothing. | A's store holds the outputs. Harmonia serves them. | A's store. | None. | See the build-locality gap below. |
| 7 | Build on B while A is off. | Nothing. | Nix tries the substituter, fails, and builds locally if `fallback = true`. | B's store. | None. | PROPOSED ("retain normal cache fallback"). `connect-timeout` and the wait are a GAP (`G23`). |
| 8 | Release roots: build a tag on A; run garbage collection. | A builder writes `nix build --out-link <roots>/<input>/<tag>` per tag. | GC keeps rooted paths. | Root links. | None. | PROPOSED (P19). The V5 builder module exists only as the Attic watch-store test fixture (`step-5.md` B1). No Harmonia version and no GC-survival test exist. |

Build-locality gap (`G07`): devenv Machines builds the closure on the controller and copies it to
the target (`RESEARCH` section 1: `plan` builds, `apply` runs `nix copy --to ssh://`). CONCEPT
section 5 says shared outputs are built on the serving host. If B and C are deployed from a laptop
controller, their closures sit in the laptop's store and A's Harmonia never serves them. The design
does not say whether the controller must be A, or whether a remote builder is used.

Visibility gap (`G07`): Harmonia serves every valid path in A's store. `exp-A-harmonia.md` showed a
host-only path answered HTTP 200. This includes `.drv` files, fetched source, and any secret that a
careless module put in the store. Network reach must match this. The design says so in one
sentence and gives no default boundary.

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Client lists the cache before the key exists | `trusted-public-keys` empty; Nix refuses unsigned paths | GAP: ordering of the client change after the key exists (`G23`) |
| Public key mismatch (key rotated) | Nix says the path has no valid signature and falls back to a local build | PROVED-ELSEWHERE for the signature check (`exp-A`). The rotation story is `sign_key_paths` change only (project 18). |
| Cache host down | A bounded delay and a local build | GAP (`G23`) |
| Path absent from A | HTTP 404 and a local build | PROVED-ELSEWHERE on loopback (`exp-A`) |
| Client trusts the wrong host | Nothing detects it | GAP. Trust derives from the mark; a wrong mark is a wrong trust (`G07`). |
| GC removes an unrooted served path | Path leaves the cache | PROVED-ELSEWHERE by analysis only; test absent (`exp-A` "Not shown"). |

Gaps: `G05`, `G07`, `G23`.

---

## Journey 9: direct `devenv`, direnv, and CI or Testee entry in a P20 workspace

| # | The user or tool runs | Vendomat does | devenv, Nix do | Files change | Network | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Plain `devenv shell` after the user edited `vendomat.yaml` | Nothing. The guard is a generated assertion. | The assertion compares hashes of `vendomat.yaml` and the generated files; fails with the message. | None. | None. | Guard EXISTS for TOML (`devenvgen.NIX_MODULE`). Text names `vendomat sync`; must name the new command (`G10`). `devenv build`, `eval`, `info`, and `machines` do not run assertions (`NAT-025`, `wrapper-spikes` S1). |
| 2 | `devenv machines plan` directly after an edit | Nothing. | No assertion runs; builds with the old generated data. | `.devenv/machine-plans/`. | Build. | EXISTS as a known hole; CONCEPT section 4 states it. A stale plan is a real risk because machines are the high-stakes path (`G22`). |
| 3 | direnv `.envrc` with `use_vendomat` | Today: `use_vendomat` re-runs `vendomat sync` when the digest is stale, then `use devenv` (`direnv/vendomat.sh`). | `use devenv`. | `.vendomat/*`. | As needed. | EXISTS for TOML (`PRE-009`, about 0.35 s unchanged). `sync` ends at cutover. direnv needs a command that prepares without entering a shell. The name is a GAP (`G10`). PLAN stage 4 says "update direnv" and names nothing. |
| 4 | `testee verify` | Testee checks the commit in its own workspace and runs `devenv` itself. The checks run inside that shell. | `devenv` reads the committed `devenv.yaml`, `.vendomat/`, `devenv.lock`. | Testee workspace only. | The lock's inputs. | See the three questions below. |
| 5 | CI on a hosted runner | Nothing unless Vendomat is installed there. | `devenv` resolves inputs. | Runner. | The runner cannot reach a tailnet `git://` collection (`G08`). | GAP. |
| 6 | An editor or a script calls `devenv print-dev-env` | Nothing. | Same as step 1. | None. | None. | Same hole as step 1. |

The three Testee and CI questions:

1. **Committed or ignored?** The design says nothing (`G09`). V6 says "keep generated Nix in version
   control" (`GUIDE-V6.md` step 3A item 1). The Vendomat repository's own `.gitignore` ignores
   `/.vendomat/`, but that line is for a different file set (a "source-grounding map"). Testee builds
   from the commit. If `.vendomat/` is ignored, the Testee workspace has no fragment. The template
   `devenv.yaml` imports `./.vendomat`. devenv then fails with its own import error. The digest guard
   lives inside the generated `.vendomat/devenv.nix`, so a missing fragment also removes the guard.
   If `.vendomat/` is committed, Testee tests the committed copy. A commit with a stale fragment fails
   the guard, which is the wanted result. Committing also commits the schema. Its size is unknown
   (the project 17 export holds 1330 records at one pin).
2. **Which `devenv` runs?** Stock devenv ignores an imported source's `devenv.yaml`. `fork-3` shows
   stock failing with `attribute 'greeting-defaults' missing` where the fork passes. A project 20
   workspace that relies on inheritance therefore needs the fork everywhere: Testee, CI, direnv, and
   editors. Today `devenv` on `PATH` decides, and `require_version: "2.4.0"` does not tell the fork
   from stock (`check.py` compares the revision only inside `vendomat check`). The V6 `sync` fragment
   flattened every input, so stock devenv worked in V6 (`G2`, `demo-consumer.md`). Project 20 removes
   that fallback. Whether a lock that the fork wrote lets stock devenv enter is unproven (`G08`).
   Memory also records that an inherited `PATH` can run Testee 0.5.1 instead of 0.6.1.
3. **Who prepares the committed state?** A CI job needs a read-only check that the generated files
   match `vendomat.yaml` and that the lock pins tags. Today that is `vendomat check` (reads TOML,
   `check.py`). The project 20 successor is not named (`G10`).

Failure modes:

| Failure | Error the user should see | Status |
| --- | --- | --- |
| Stale generated files, `devenv shell` or `test` | `vendomat: STALE. vendomat.yaml changed since the last prepare. Run: vendomat prepare` | Guard EXISTS (TOML text). New text PROPOSED. |
| `.vendomat/` missing in Testee | A Vendomat-worded message | GAP. devenv prints its own error (`G09`). |
| Stock devenv on a P20 workspace | `devenv X is not the Vendomat build; install the pinned devenv` | GAP (`G08`) |
| Lock absent in CI | `devenv.lock is missing; run vendomat prepare and commit it` | GAP. devenv would create an unpinned-in-VCS lock in the runner. |
| CI cannot reach the collection | The input name and URL | GAP (`G08`) |
| `vendomat.yaml` changed, `devenv.lock` not | The guard names `vendomat.yaml` only, not the lock | GAP. Today's digest does not cover the lock (`G13`). |

Gaps: `G08`, `G09`, `G10`, `G13`, `G22`.

---

## Consolidated GAP list, ranked by risk

Risk order: first harm to disks or secrets, then a blocked design, then lost work or confusion.

| Rank | ID | Gap | Journeys | Why it ranks here | Question a fixture or an owner decision must answer |
| --- | --- | --- | --- | --- | --- |
| 1 | G01 | **No route from controller to a blank remote target.** The proven install ran on a running OS with a second disk, to `root@127.0.0.1`. The fork refuses `kexec` joined with disko or install. The wrapper's ssh is `BatchMode`. | 5 | Destructive path with an unproven environment. Gate 6 differs from G7. | Fixture: controller plus a blank VM booted from a minimal installer with a temporary key. Does the preflight pass inside the installer (root on tmpfs, `/mnt` empty)? Who sets and removes the temporary credential? How does the controller pin the installer host key? Is a non-NixOS target out of scope? |
| 2 | G06 | **Adoption of a real, foreign NixOS config is untested.** The design does not say how an existing configuration, hardware module, bootloader, `stateVersion`, Home Manager, and users merge with the Basix core. Root SSH on a laptop is a precondition. | 7 | An error can make a daily machine unbootable. Only a synthetic VM image passed. | Fixture: adopt a VM built from an unrelated `configuration.nix` with by-label mounts and a standalone Home Manager. What does the user write? What does `plan` show? Does the guard block common legacy mounts? Owner decision: is enabling local sshd acceptable? |
| 3 | G05 | **Post-install secret route is unchosen.** Three routes, none with a project 20 fixture. Ordering with `apply` is unspecified. P19 understates the `install.secrets` evidence. | 6, 7, 8 | Controls cache serving and every later secret. Failure rolls back the deploy and leaves the key. | Fixture per route on a fresh and an adopted VM: deliver, apply, kill the service, roll back, reboot. Where does the controller hold the secret? Is a fork patch worth its upkeep over route A? |
| 4 | G07 | **Cache build locality, visibility, and the mark.** Machines builds on the controller. Harmonia serves only the host store and all of it. The mark's name is unset. The NixOS module did not run. | 8 | Shared outputs may not be shared. Wrong network scope exposes the store. | Must the controller be the serving host? Remote builder? What listener and firewall default fits any user? Fixture: two VMs, module, cold substitution, a client that deploys from a third machine. |
| 5 | G08 | **Stock `devenv` and hosted CI cannot enter a P20 workspace.** The V6 fragment flattened inputs. Inheritance exists only in the fork. `require_version` does not tell them apart. A hosted runner cannot reach a tailnet collection. | 9 | Breaks Testee, CI, direnv, editors with cryptic errors. | Fixture: stock devenv with a fork-written lock; Testee on a P20 commit. Should Vendomat commit a flat fragment so stock works? Should the fork stamp itself in `devenv.yaml` checks? |
| 6 | G09 | **No VCS rule for generated files** (`.vendomat/`, schema, `config.json`, `devenv.lock`). | 1, 9 | Testee builds from the commit; an ignored fragment removes the guard too. | Commit or ignore, per file. How large is the schema? Does a merge conflict in generated files have a fix command? |
| 7 | G10 | **No non-entering prepare command, no init command, no YAML parser.** `sync` ends; `shell` enters. direnv, CI, Testee, and editors need generation and lint without a shell. | 1, 3, 9 | Every non-interactive entry depends on it. | Name and contract of `prepare` (steps, exit codes, offline behavior). Name of `init` and its model. Which strict YAML parser, given Typer-only dependencies? What are the successors of `check`, `path`, `bump`? |
| 8 | G14 | **Tag change is not atomic.** The lock moves before validation. After a validation failure the design does not restore or keep. Inherited nodes may not re-lock. A key valid only in the new release lints as unknown first. Offline with a changed file has no rule. | 3, 4 | Leaves lock, fragment, and file out of step. | Fixture: tag bump with a new option, with an invalid value, offline. Do inherited children move? Keep or restore the lock on failure? |
| 9 | G15 | **Schema export is unproven for a user workspace.** The exporter ran in the `devenv-py` harness. Cold cost for a whole workspace is unmeasured. Neutral-data export is open. The generator is Python/Pydantic in a private repository. | 1, 3, 4 | The step that makes `vendomat.yaml` possible. | Run the export in a workspace with no `config.json`: time cold and warm, size, does it need user values, how does the Typer-only Vendomat package carry the generator? |
| 10 | G11 | **Launcher semantics for all commands.** Root marker, fallback to the host release for `build` and `machines`, no release report, no `vendomat.yaml` format version. | 2, 3 | A host release older or newer than the pin could regenerate or deploy with the wrong guard. | Which commands may fall back? Does a format key exist? What exact line reports the release? |
| 11 | G12 | **First-lock defaults.** `defaults.py` carries only nixpkgs. The `vendomat` pin, the `devenv` fork pin, the collection URL, and the `devenv` binary that Vendomat runs have no source. A Basix user with no collection has none. | 1 | A new workspace cannot lock without them. | Where does the host release read its own tag, fork tag, and collection URL? Is the devenv CLI in Vendomat's closure? |
| 12 | G16 | **Priority and rename rules.** Plain module definitions conflict with YAML values. Renamed options are outside the models yet native Nix accepts them. | 4 | The "one file" promise weakens when overrides fail. | The priority matrix (`DOOR-013`). Should YAML values use `mkOverride`? How are renamed options treated? |
| 13 | G17 | **"Keyless" omits first-boot credentials.** Wi-Fi keys, a login password, and a disk passphrase are secrets. The linter cannot find arbitrary strings. | 5, 6 | A laptop that cannot reach the network is unreachable. | Does the Basix core use wired or key-based access only? Where does a user password come from? Is disk encryption out of scope for the first install? |
| 14 | G03 | **Used disks are refused and have no guarded wipe.** The preflight refuses any signature. A half-failed disko needs a manual wipe. | 5 | Manual `wipefs` has no guard. | Does Basix provide an identity-checked erase, or only refuse? |
| 15 | G04 | **Hardware and identity discovery.** Model, serial, size, and facter report must exist before install. The `facter` phase never ran. The 300 s result lifetime is unmeasured on large disks. | 5 | A blank-machine user cannot fill the required fields. | Fixture: `facter` phase on a VM; a helper that prints the inventory fields; the TTL against a real format time. |
| 16 | G20 | **Machine target and command names in YAML.** `target.host`, `sshOpts`, known hosts, `rollbackTimeout`, `healthCheck` have no data names. Code has `machine install`; CONCEPT says `machines ...`. | 5, 7 | The example cannot deploy. | Which target fields are data? One command family or two? |
| 17 | G22 | **Stale or ungated machine operations.** Direct `devenv machines` skips the digest guard. The failed-unit gate is not wired into any Vendomat command. | 6, 7, 9 | A stale plan or a pre-failed unit makes rollback fail. | Can a fork patch or a module check refuse machine commands on a stale digest? Does `vendomat machines apply` run `MACH-022`? |
| 18 | G13 | **Digest, schema cache, and offline rules.** The digest ignores the lock. The schema has no named place or key. No `--offline` rule. Shared-child `follows` conflicts with the claim that Vendomat resolves no transitive graph. | 1, 2, 3, 9 | Wrong "unchanged" decisions; slow offline waits. | What does the digest cover? Where does the schema live? Does Vendomat pass `--offline`? Keep `PRE-005`? |
| 19 | G23 | **Client cache wiring and fallback.** Timeouts, ordering of trust after the key, wrong-mark detection. | 8 | Slow builds when the cache host is off. | Fixture: server off, `connect-timeout`, `fallback`. |
| 20 | G18 | **Source collection operations lost.** `keep`, `mirror`, `sync --collection`, the post-receive hook, and `path` have no successor while `sync` ends and `inputs` mean devenv's. | 1, 8 | Third-party source handling disappears. | Where do `keep` and `mirror` live? |
| 21 | G19 | **Owner names in module defaults** (`hosts`, `users`). | all | Contradicts "any user installs Basix". | Remove the defaults; fixture with neutral names. |
| 22 | G21 | **Real firmware.** One-time boot, removable-path boot, and entry creation are VM-only. | 5 | Unbootable first boot on hardware. | Owner-run hardware record after the VM gates. |

---

## Where the concept contradicts itself or the evidence

| # | Contradiction | Where |
| --- | --- | --- |
| C1 | The launcher refuses every command but `sync` (`DEL-020`, code and test). Project 20 decision 1 and `DOOR-010` require it to serve all of them. | `launcher/vendomat:56-66`; DECISIONS 1 |
| C2 | CONCEPT section 5: Vendomat "does not resolve a second transitive input graph". `fork-3` says shared-child `follows` (`PRE-005`) stays a Vendomat job; without it the lock holds duplicate nodes. | CONCEPT 5; `fork-3-inheritance.md` "Not proved" |
| C3 | Project 19 section 10: `install.secrets` is "not run here". The project 16 records show a passing QEMU run with the `env` provider and a payload. | P19 section 10; `01-devenv-distribution.md` section 6; `step-7.md` |
| C4 | Gate 6 says "a controller installs a fresh virtual machine". The only install proof (G7, `MACH-008`) installs from the running host to a second disk at `root@localhost`, with no live installer. CONCEPT section 6 also says Vendomat "forwards native machine commands"; `MACH-005` says Vendomat does not wrap them; the code wraps only `install`. | CONCEPT 8 and 6; `MACH-008`, `MACH-005` |
| C5 | CONCEPT section 5: "shared work is built on the serving host". devenv Machines builds on the controller. | CONCEPT 5; `RESEARCH` section 1 |
| C6 | CONCEPT section 2 names `vendomat machines ...`. The code names `vendomat machine install`. | CONCEPT 2; `cli.py:273-278` |
| C7 | CONCEPT section 3 calls `inputs` "devenv's meaning". The V5 and V6 input entries also carried `mirror`, `keep`, `backup`, `repo` for the collection. CONCEPT section 5 keeps "mirrored or kept". No YAML key holds them. | CONCEPT 3 and 5; `registry.py` `INPUT_KEYS` |
| C8 | CONCEPT section 2 promises routine work in one file. CONCEPT section 4 stops any conflict with a module's plain definition. A YAML value cannot override a module default that is not `mkDefault`. | CONCEPT 2 and 4 |
| C9 | Project 17 leaves renamed and alias options out of the models (`MDL-035`). Native Nix accepts them. A schema-based linter can reject a key that Nix accepts. | `17 CONCEPT.md` MDL-035 |
| C10 | The module defaults name `server`, `framework`, and `andrew`. Project 19 and the task rules say owner names are fixtures only. | `default.nix:172-181` |
| C11 | The Vendomat repository ignores `/.vendomat/`. In a workspace, `.vendomat/` is generated input the guide says to commit. The directory name now means two things. | `.gitignore`; `GUIDE-V6.md` step 3A |

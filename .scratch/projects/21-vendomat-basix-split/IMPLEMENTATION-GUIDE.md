# Project 21: implementation guide

**Written 2026-10-13, at the design freeze.** This guide turns the final project 21 design into
work steps. A new session can follow it from the start without the conversation that made the
design. It names every input, command, check, owner gate, and ledger row.

The guide does not replace the design. When the guide and an authority document disagree, the
authority document wins. Fix the guide in the same change.

| Authority | File |
| --- | --- |
| What to build | [CONCEPT.md](CONCEPT.md) |
| Owner rulings R1 to R36 | [DECISIONS.md](DECISIONS.md) |
| Requirement ledger (`VMT-`, `BSX-`) | [REQUIREMENTS.md](REQUIREMENTS.md) |
| Slices and owner gates | [PLAN.md](PLAN.md) |
| Spike results W1 to W10 | [evidence/](evidence/) |
| Durable repository rules | [AGENTS.md](../../../AGENTS.md) |

## How to use this guide

1. Do Phase 0 once per session.
2. Settle the decisions in [Section 4](#4-decisions-to-settle) that the next slice needs. Ask the
   owner. Record each answer as a ruling in `DECISIONS.md` (R37 onward) before you build on it.
3. Do the slices in dependency order: S1 and S2 first (they are independent), then S3, S4, S5, S6,
   S7, and S8. Each slice section lists its steps, its checks, and the ledger rows it closes.
4. Close each slice with the steps in [Section 1.6](#16-close-a-slice).

A step that says **Owner gate** stops the work until the owner says yes in the session. Approval
in an earlier session does not carry over.

---

## 1. Rules for every step

### 1.1 Version control

- Use Gitman to open and close workspaces. `AGENTS.md` says "do not run raw `git` or `jj`"; the
  Gitman skill names the native jj commands for describe, rebase, bookmark, and push, and every
  project 21 change so far landed with them. Use exactly the jj steps below, and never raw `git`.
- Before you open a workspace, list the workspaces and any work that `main` lacks. Report each
  result:

  ```sh
  cd /home/andrew/Documents/Projects/vendomat
  jj workspace list
  jj log -r '(::working_copies() ~ ::trunk()) ~ empty()'
  ```

- Open one workspace per change: `gitman work NAME`. Work in
  `/home/andrew/Documents/Projects/vendomat/.gitman/workspaces/NAME`.
- Another session works on project 22 in the same repository. It lands often. Rebase before you
  land. Do not edit project 22 files.
- Land a green change by default. The owner's standing rule: verify, save, land on `main`, push.
  1. `testee verify` is GREEN.
  2. `jj describe -m "..."`, `jj git fetch`, `jj rebase -b @ -d 'trunk()'`. Verify again if the
     tree changed.
  3. `jj bookmark set main -r @`.
  4. `jj git push --bookmark main`. Run it as its own command; a hook requires that.
  5. In the main checkout: if `jj status` shows no changes, run `jj new main`. Otherwise leave it
     and tell the owner.
  6. From the main checkout: `gitman done NAME`.
- Stop and ask before you land if verify fails or is skipped, a conflict appears, or the change
  touches secrets, CI, or release branches.

### 1.2 Verification

- Run `testee verify` from the workspace root. It must print GREEN with every required check.
- Run `testee verify --profile quick` (ruff and ruff-format) during an edit.
- Run the named opt-in checks that a slice lists, for example `testee verify catalog-e2e`.
- Check `testee --version` once per session. On 2026-10-13 it was 0.7.0 from
  `/etc/profiles/per-user/andrew/bin/testee`.
- Never call pytest, ruff, or ty directly. Never wrap Testee in `devenv shell`.
- Testee finds `devenv` on the inherited `PATH`. Until the owner switches the host binary (S2
  owner gate), a check that needs the patched binary must set `PATH` itself, for example
  `PATH=<patched-devenv>/bin:$PATH testee verify binary-e2e`.

### 1.3 Records

- Each slice ends in an evidence file `evidence/S<n>-<NAME>.md`. Record exact inputs, versions,
  commands, expected results, and actual results. Separate observation from inference.
- Raw logs go under `~/.local/state/vendomat/p21/<date>/<slice>/`. Never in the repository.
- Update the ledger rows the slice names. A fixture pass changes the status. A changed claim gets
  a new ID that supersedes the old one. Never reuse or renumber an ID. The highest IDs on
  2026-10-13 are `VMT-123` and `BSX-124`; numbers continue across both prefixes.
- Treat a new option name, command, or file format as proposed until a fixture proves it on the
  pinned tools.
- A unit test does not replace a required real-consumer, cache, restore, or machine proof.
- If a fixture disproves an interface, change the concept, this guide, and the code together.

### 1.4 Safety

- **Disks.** Never select a disk by kernel name. Use `/dev/disk/by-id/` for hardware,
  `/dev/disk/by-partuuid/` for a partition, `/dev/disk/by-uuid/` to mount. VM fixtures use image
  files only. Never pass a host block device to a VM.
- **VM files.** VM images, VM state, and VM scratch (`TMPDIR`) go under
  `/mnt/shared/vendomat-p21/<slice>/` (owner rule). Delete them when the slice lands, unless a
  later slice needs them. Ask before you delete files you did not create.
- **Root file system.** Before each build, run `btrfs filesystem usage /`. If metadata use is
  above 90 % while unallocated space is 10 GiB or more, wait 60 s and check once more. Stop and
  report if it stays above 90 % or unallocated space falls below 15 GiB. Each ISO adds about
  1.5 GB to the store; the patched devenv build adds about 5 GiB.
- **Garbage collection.** Do not run `nix-collect-garbage`, `nix store gc`, or
  `nix-store --delete` without the owner's approval.
- **sudo.** Use `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid.
- **uv.** Sessions started from the Vendomat devenv carry `UV_PROJECT_ENVIRONMENT`. Run devenv and
  uv in another repository with `env -u UV_PROJECT_ENVIRONMENT`.
- **Upstream.** Never open, draft, or plan an upstream pull request for a devenv patch (R34).
  Watching upstream (PR #3244, releases) is fine.
- **GitHub** is a backup copy only. It is never part of the pipeline.

### 1.5 Subagents

The owner prefers this split: background Sonnet subagents explore, build, and test; the main
session orchestrates and reviews. Give each subagent a complete brief: paths, the slice step,
the checks, the safety rules of Section 1.4, the evidence format, and the expected Testee version.
A subagent's Write tool may refuse report files; tell it to write reports with a shell heredoc or
to return the report as text. Check each result against its logs before you record it.

### 1.6 Close a slice

1. All slice checks pass, and `testee verify` is GREEN.
2. The evidence file exists and links the raw logs.
3. The ledger rows carry their new status.
4. `PLAN.md` marks the slice done, with the evidence link.
5. `.scratch/CURRENT.md` names the next slice.
6. Land as in Section 1.1.

---

## 2. Facts the implementer needs (observed 2026-10-13)

### 2.1 Host

| Fact | Value |
| --- | --- |
| Host | `server`, x86_64-linux, Nix 2.34.7. It runs nix-meta's `nixos-system-server`. |
| devenv first on `PATH` | `devenv 2.4.0+b904dcb`: upstream v2.4.0, no fork patch. Source: nix-meta `flake.nix:16-37` (`github:cachix/devenv/v2.4.0`), installed by `profiles/developer.nix:10,75`. |
| System-path devenv | nixpkgs `pkgs.devenv` 2.4.0, `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0`. |
| QEMU | Not on `PATH`. W2 used `/nix/store/brsnkyr2fwhiq8g8f1dxkpqw0iys3yin-qemu-host-cpu-only-11.1.1/bin`. |
| OVMF | `/nix/store/xd1njdj3251gc4nkk6m0lq57b9n011kd-OVMF-202608-fd/FV/`. `/dev/kvm` is readable and writable. |
| Space | `/`: about 35 GiB unallocated, metadata 82 %. `/mnt/shared`: about 1.7 TB free. |

Store paths can be garbage-collected. In a new fixture, get QEMU and OVMF from the pinned nixpkgs
(add them to the fixture's devenv `packages`), not from a hard-coded path.

### 2.2 The collection

- A read-only git daemon on `server` serves `/home/andrew/vendor` on port 9418 (nix-meta
  `machines/server.nix:176-182`). A repository is served only if it holds
  `.git/git-daemon-export-ok`. Served today: `devenv`, `devman`, `vendomat`, `vendomat-demo`.
- Consumers read `git://server/<repo>?ref=refs/tags/<tag>[&dir=...]`, or
  `git://server/vendomat?ref=release`.
- Publishing is a push into the non-bare repositories in `~/vendor` over the local path (an
  `ssh://server` push failed with `Permission denied (publickey)` on 2026-10-10). The Vendomat
  repository's hooks guard it: `hooks/collection-pre-receive` accepts only new tags (tags never
  move) and, for the repository named `vendomat` only, a fast-forward of `refs/heads/release`.
  `hooks/collection-post-receive` checks out the newest tag when the work tree is clean.
- The fork release procedure that worked: `python3 -I devenv-dist/materialize DEST --verify`, then
  `jj git push --remote collection --tag`, then `nix flake prefetch --json` over `git://server`
  ([live release record](../16-vendomat-devenv-layer/evidence/live-release-2026-10-10.md),
  [published channel](../20-vendomat-front-door/evidence/slice-1/PUBLISHED-CHANNEL-2026-10-12.md)).
- An unrelated test daemon listens on 127.0.0.1:19418. Leave it alone.

### 2.3 Attic (history; R39)

**R39: the new system configures no Attic.** No slice pushes to Attic or configures it. The
facts below describe today's `server` only. Leave that Attic untouched.


- Cache `vendomat`. Server `atticd` on 127.0.0.1:8089 (nix-meta `machines/server.nix:338-359`),
  behind Tailscale Serve at `https://server.tail770f47.ts.net/attic/vendomat`. Public key
  `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=`.
- Client config `~/.config/attic/config.toml` (`default-server = "vendomat-server"`). Tokens:
  `~/.local/state/vendomat/secrets/attic-{publisher,pull}.jwt`.
- `attic` is not on `PATH`. Use the client from the pinned nixpkgs, for example
  `nix shell nixpkgs#attic-client -c attic push -j 1 vendomat <path>`. Use one job: the default
  five jobs hit `Connection pool timed out` on 2026-10-10.
- This host does not substitute from Attic (its `nix.conf` lists only cache.nixos.org and
  devenv.cachix.org). Other machines do (nix-systems `nixos/core.nix:26-31`).

### 2.4 The repository today

- The code implements project 14, the V6 layer, and project 20 slice 1. `AGENTS.md:63-69` and
  `README.md` are stale on this point; S3 updates them.
- `flake.nix`: one input (`nixpkgs`, NixOS/nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`).
  Outputs: `packages.<sys>.vendomat`, `packages.<sys>.launcher`, `lib.<sys>.mkLauncher`,
  `devenvModules.default`. `flake.nix:15` hard-codes the `.4` fork CLI store path.
- `devenv/devenv.nix` is the slice 1 catalog. It calls the fork primop `vendomatFromYAML`
  (`:23-28`). It already has `guard`, `prune`, `_file`, one error for all faults, and mappings for
  programs, env, python, javascript, rust, postgres, and redis.
- `templates/workspace/` is the slice 1 template: `vendomat.yaml`, `devenv.yaml`
  (`vendomat` at `git://server/vendomat?ref=release`, `nixpkgs` follows `vendomat/nixpkgs`,
  imports `vendomat/devenv`), `devenv.nix` (`{ }`), `.gitignore`.
- `launcher/vendomat` dispatches: no argument enters the fork shell; `new` copies the template;
  the old verbs (`sync`, `path`, `check`, `push`, `bump`, `machine`) run the Python CLI; anything
  else passes through to devenv.
- `devenv-dist/` holds the fork recipe: `UPSTREAM` (v2.4.0, `b904dcb5`), `SERIES` (0001 to 0009),
  `MANIFEST.sha256`, `RESULT` (`c66ba875`, tag `v2.4.0-vendomat.4`), and `materialize`.
- Shape tests that constrain every slice (`tests/test_repo_shape.py`):
  - The set of `src/vendomat/*.py` names is fixed. Adding or removing a module needs a `MODULES`
    edit.
  - No root directory named `vendor`, `modules`, `lib`, `docs`, `examples`, or `pkgs`. Put Nix
    code under `devenv/` or `nix/`.
  - `flake.lock` root inputs equal `{"nixpkgs"}`.
  - `[project].dependencies` names only `typer`.
- `tests/test_devenv_dist.py` requires patch numbers 1..N with no gap, pins `.4`, and has
  per-patch tests for 0006 to 0009.
- `tests/test_fleet_shape.py`: no `/home/<user>/` path in `flake.nix`; no `file://` or path pin in
  `flake.lock`; every git lock node has a `refs/tags/` ref and a rev.
- The Python package needs only `typer`. Exit codes: 0 ok, 1 a decision is needed, 2
  infrastructure or configuration, 3 invalid usage.
- Live consumers use the old `vendomat.toml` flow: nix-systems (pins devenv `.2`) and
  vendomat-demo. nix-meta pins an old Vendomat and imports the old NixOS module that installs
  `share/vendomat/consumer-module.nix` and `machine.json` (`machines/server.nix:66-71`). No
  consumer uses `vendomat.yaml` yet.

### 2.5 Pins

- **nixpkgs.** Use Vendomat's flake pin, NixOS/nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`,
  everywhere: the flake, the host binary, the template (through `follows`), and Basix. W2, W3, W5,
  W6, W7, W8, W9, and W10 used it. W4 used `cachix/devenv-nixpkgs` at `256551e4` only because it
  copied the repository's own `devenv.lock`; S3 re-runs the W4 fixtures on the flake pin.
- **devenv.** Upstream v2.4.0, commit `b904dcb51fe48c30db250038241507f60752f222`.
- **disko** `de570873`, **nixos-facter-modules** `139dcef4`, **nixpkgs-python** `4d2bd16c`
  (the spike pins; refresh only with a fixture run).

---

## 3. Spike artifacts

The spikes left working code under `S=~/.local/state/vendomat/p21`. Phase 0 checks the hashes.
If a file is missing, rebuild it from the evidence record that describes it.

| Artifact | Path under `$S` | sha256 | Used in |
| --- | --- | --- | --- |
| Parser v3 (261 lines) | `2026-10-12/yaml-spike-2/parse.nix` | `857b4198304fe58f083be75718ff463fa8f66f221ef22ef934351c21fc9e536b` | S3 |
| Parser corpus and harness | `2026-10-12/yaml-spike-2/cases/` (17 subdirectories, about 29 000 files), `bin/runall_v3.sh`, generators `bin/gen2.py`, `gen3.py`, `fuzz_gen.py`, `edge_cases.py` | — | S3 |
| W4 catalog (240 lines) | `2026-10-13/w4-catalog/catalog/catalog.nix` | `64c1661c19db4fc80c0d25658c0878fb0cf8dca17535cff4c897d844347b6e35` | S3 |
| W4 template `devenv.yaml` | `2026-10-13/w4-catalog/tmpl/devenv.yaml` | `b9c4953453d13c67a928bd41a974718c88aaa41922a16152904ccc659ed64cbc` | S3 |
| W4 fixture scripts and logs | `2026-10-13/w4-catalog/{bin,harness,logs}/` (F1 to F14, F4b) | — | S3 |
| `deferredModule` change (one line, `machines.nix:302`) | `2026-10-13/w2-machines/logs/T4-patch.diff` | `72667ee285410a881e86c28bf4bb0416557e159dcd18ea16eaa422ddae1229a7` | S1 |
| Build options patch 1 (`build.vm`, `build.iso`; +21) | `2026-10-13/w8-iso-policy/patches/patch1.diff` (equals W7 `d1.diff`) | `efe2b226be07490132c80cf61317a045780ebde853f431741cb74d21805ce1d2` | S1 |
| Build options patch 2 (`isoEval`, `iso.modules`; +46 −4) | `2026-10-13/w8-iso-policy/patches/patch2.diff` | `ee671053ca62835af8f5a6a843d632fe274ad3fef4f2742914adca43428e39eb` | S1 |
| `iso.modules` docs paragraph | `2026-10-13/w8-iso-policy/REPORT.md` lines 96 to 112 | — | S1 |
| Patch 0005, module half (39 lines) | `2026-10-13/w6-host-binary/patches/0005-module-hunk.patch` | `5364904078a92fc492aab69d9ed66d2a291095ac7d3b33249dc54dd32d0427cc` | S1 |
| Host binary overlay | `2026-10-13/w6-host-binary/devenv-vendomat-overlay.nix` | `ab1d8c061fd1b39940a0bc851b87430deec0f13a1421bebb0e0bcb3d56fab213` | S2 |
| Overlay test harness | `2026-10-13/w6-host-binary/pkgs.nix` | `23f6da5377c299a1f02914439ce5e6ef2424e70d937ca726c7a0f542ced07fa2` | S2 |
| Patch 0003 | `2026-10-13/w6-host-binary/patches/0003.patch` | `c4a121b9d237740e47243754a3ec6c6b9d7dc83e7fb05f019b6e769052aaa1c5` | S2 |
| Patch 0005 (full) | `2026-10-13/w6-host-binary/patches/0005.patch` (equals `devenv-dist/patches/0005-*`) | `85eea6e22e52fdc3103381a69fa9765305433b4273d0e728e553123c0aedd2a3` | S2 |
| Offline-entry reproduction | `2026-10-13/w1-fork/bin/` (`first-entry*.sh`, `daemon-start.sh`) | — | S2 |
| Basix disk layout | `2026-10-13/w5-disk-guard/ws/basix-disk.nix` | `08777adb6cd0e9cd1f1fbd51612980a2b93318683c8ce53d76bcf9c78ddc87e5` | S5 |
| Blank-disk guard | `2026-10-13/w5-disk-guard/ws/basix-disk-guard.sh` | `efb4f7e723ff42a509d097a7064221909c7555d0cdb0e561ab6bef66f3f043fa` | S5 |
| Disk list guard (older, `list` mode) | `2026-10-13/w2-machines/ws-t3/guard.sh` | — | S5 |
| W3 stub Basix flake and entry module | `2026-10-13/w3-topology/repos/basix/{flake.nix,devenv.nix}`; working `devenv.yaml` in `logs/min-working-devenv.yaml` | — | S5 |
| Local apply script | `2026-10-13/w9-rollback/bin/apply.sh` | `39ef4fce51eea77965cd952820da51cbf605487979376e81fda7ee9d408f3035` | S4 |
| Rollback scripts | `2026-10-13/w9-rollback/bin/{prev-gen,rev,state,boot}.sh` | — | S4 |
| Hardware report filter | `2026-10-13/w10-facter/bin/drop.jq` (`del(.hardware.cpu[].tlb_size)`) | `92b29d328a41c8e4acf28cd327d260cba77e89b4448bae40f821fc6e55aaeedf` | S5 |
| VM scripts | `2026-10-13/w2-machines/bin/` (`env.sh`, `t1-boot.sh`, `iso-boot.sh`, `t3-prebuilt.sh`, `vmssh`), `common/box.nix`, `common/expose.nix` | — | S1, S4, S5 |

`/mnt/shared/vendomat-p21/` is empty: the spike VM images were deleted on 2026-10-13. Rebuild
images from the scripts.

---

## 4. Decisions (all ruled)

The owner ruled D1 to D8 on 2026-10-13. The full records are in
[DECISIONS.md, D1 to D8](DECISIONS.md#implementation-decisions-awaiting-a-ruling-d1-to-d8).

| # | Ruling | Used by | Outcome |
| --- | --- | --- | --- |
| D1 | R40 | S3 (launcher), S8 | The old verbs and the `vendomat.toml` flow keep working until nix-systems and vendomat-demo move to `vendomat.yaml`. S8 removes them all, `push` included. `machine install` moves to Basix (R13). |
| D2 | R41 | S1, S3 | The module fork tag is Vendomat's second flake input `devenv` (`dir=src/modules`). The template writes `devenv: follows: vendomat/devenv`. The "one flake input" shape rule changes in S1 step 9. |
| D3 | R37 | S5 | Basix publishes like Vendomat: immutable tags plus a fast-forward `release` branch. The collection hook allows `release` for any repository. |
| D4 | R42 | S3 | A committed `.machines/NAME/facter.json` marks a machine installed (`adopt-existing`). `mode: fresh-install` overrides it. |
| D5 | R38 | S5 | Basix keeps its keys in `basix.yaml`. Vendomat builds no extension point for keys. |
| D6 | R43 | S4 | `/var/lib/vendomat/generations.jsonl`, one line per apply. `apply` refuses uncommitted changes unless `--dirty`; `rollback` uses clean entries only. |
| D7 | R44 | S1 | `v2.4.0-vendomat-modules.N`. |
| D8 | R45 | S3 | `VENDOMAT_HIDE_ADVANCED=1` hides the `advanced:` line. |

---

## 5. Phase 0: session setup

Do this once per session.

1. Read `AGENTS.md`, `.scratch/CURRENT.md`, and this guide. Read the authority files the next
   slice names.
2. Check the tools:

   ```sh
   testee --version                    # expect 0.7.0 or the version CURRENT.md names
   which -a devenv && devenv version   # record it; the host binary changes only at the S2 gate
   nix --version
   btrfs filesystem usage / | sed -n '1,12p'
   df -h /mnt/shared
   ```

3. List workspaces and unlanded work (Section 1.1). Report any work that `main` lacks.
4. Check the spike artifacts of Section 3:

   ```sh
   S=~/.local/state/vendomat/p21
   cd "$S" && sha256sum \
     2026-10-12/yaml-spike-2/parse.nix \
     2026-10-13/w4-catalog/catalog/catalog.nix \
     2026-10-13/w2-machines/logs/T4-patch.diff \
     2026-10-13/w8-iso-policy/patches/patch1.diff \
     2026-10-13/w8-iso-policy/patches/patch2.diff \
     2026-10-13/w6-host-binary/patches/0005-module-hunk.patch \
     2026-10-13/w6-host-binary/devenv-vendomat-overlay.nix \
     2026-10-13/w6-host-binary/patches/0003.patch \
     2026-10-13/w5-disk-guard/ws/basix-disk.nix \
     2026-10-13/w5-disk-guard/ws/basix-disk-guard.sh \
     2026-10-13/w10-facter/bin/drop.jq
   ```

   Compare with the table. Report any mismatch before you copy a file.
5. Optional, recommended once: archive the spike directories so a cleanup cannot lose them:

   ```sh
   mkdir -p /mnt/shared/vendomat-p21/archive
   tar -C ~/.local/state/vendomat -cf - p21 | zstd -T0 > /mnt/shared/vendomat-p21/archive/p21-spikes-2026-10-13.tar.zst
   ```

6. Settle the Section 4 decisions that the next slice needs.

---

## 6. Slices

### S1: the module-only devenv fork

**Goal.** One tag in the collection's `devenv` repository holds upstream v2.4.0 plus only module
changes. A workspace uses it as its `devenv` input with any devenv 2.4.0 binary.

**Depends on:** D2, D7. **Ledger:** `VMT-064`, `VMT-082`, `VMT-095`, `VMT-106`, `VMT-107`,
`VMT-108`, `VMT-118`. **Evidence:** `evidence/S1-MODULE-FORK.md`.

**Module patch series** (each a separate commit on upstream `b904dcb5`):

| # | Change | Source | Notes |
| --- | --- | --- | --- |
| m1 | `machines.NAME.nixos` typed `nullOr deferredModule` | `T4-patch.diff` | W2 T4 proved `nixos` only. Leave `home-manager` and `nix-darwin` as upstream has them (R35 keeps homes outside Vendomat). |
| m2 | `src/modules/latest-version` says `2.4.0` | content of old patch 0002 | Silences `devenv 2.4.0 is newer than devenv input (2.3.1)` (`VMT-118`). |
| m3 | Public `build.vm` and `build.iso`, typed `nullOr package` | `patch1.diff` | Not `output` type: an `output` makes `devenv build` build every image (W7). |
| m4 | `build.iso` for any machine through `extendModules`, six required overrides at priority 60, `iso.modules` (`listOf deferredModule`) | `patch2.diff` | A machine with its own ISO module keeps its own image (`VMT-108`). |
| m5 | `machines.NAME.vendomat.mode` (`null`, `fresh-install`, `adopt-existing`) copied into `machinesMeta` | `0005-module-hunk.patch` | The binary half ships in S2 (`VMT-106`). Nothing has proved that m5 applies on top of m3 and m4; check it first. |

Steps:

1. Open a workspace: `gitman work s1-module-fork`.
2. Restructure `devenv-dist/` for two series. Proposed layout:
   - `devenv-dist/modules/{SERIES,MANIFEST.sha256,RESULT,patches/m000N-*.patch}`
   - keep the old binary series where it is until S6.
   - Extend `materialize` with `--series modules` (or a sibling script) that applies the module
     series with the same fixed committer and date, and tags the result with the D7 tag.
3. Write each module patch as a `git format-patch` style file with a fixed header and an
   `Upstream: none (Vendomat module fork; R34: no upstream pull request)` line, as the old series
   does. Record each sha256 in the manifest.
4. Materialize into a scratch directory outside the repository:

   ```sh
   python3 -I devenv-dist/materialize ~/.local/state/vendomat/p21/<date>/s1/devenv-modules --series modules --verify
   ```

   It must apply m1 to m5 with no fuzz. If m5 does not apply, rebase the hunk by hand, record the
   change, and re-hash.
5. Add fixtures. Port them into `tests/` as one opt-in Testee check, `modules-e2e`, that uses
   devenv 2.4.0 from `PATH` and the materialized tree as a `path:` input. Fixtures:
   - **merge** (W2 T4): one machine's `nixos` set from an attribute set, a function, and a default
     module; all three settings reach `/etc` in `build.nixos`. The stock input fails with
     `Cannot merge definitions` (control).
   - **build.nixos unchanged** (W7 H1): the toplevel path equals the stock input's for a plain
     machine and for a machine with `facter.json` and a disko layout.
   - **no images by default** (W7, W8 Q6): `devenv build machines.NAME` returns no VM or ISO.
   - **iso error** (W7 H6): `build.iso` on a machine whose `nixos` imports an ISO module returns
     that image; `iso.modules` with a plain `boot.loader.timeout` does not change the image;
     with `lib.mkForce` it does (W8 Q2, `VMT-107`).
   - **mode option** (m5): `devenv eval machines.NAME.vendomat.mode` returns the set value.
   - **no version warning** (`VMT-118`): shell entry prints no `is newer than devenv input` line.
   - **VM boot** (opt-in check `modules-vm`): `build.vm` of a plain machine and `build.iso` of a
     machine with a disko layout boot under OVMF with zero failed units (W7 H2, W8 Q4). Images
     under `/mnt/shared/vendomat-p21/s1/`.
6. Update `tests/test_devenv_dist.py` for the module series: contiguous numbers, manifest hashes,
   `RESULT` matches, each patch has the header.
7. Run `testee verify`, then `testee verify modules-e2e` and `testee verify modules-vm`.
8. Publish the tag (Section 2.2): push the materialized tag from its scratch clone with
   `jj git push --remote collection --tag` (or push into `~/vendor/devenv` by local path), then
   check it:

   ```sh
   nix flake prefetch --json 'git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules'
   ```

   A pushed tag is permanent. Push only after every check passes.
9. If D2 chose a flake input: add `inputs.devenv` (the tag above, `dir=src/modules`,
   `flake = false` if devenv's module directory has no `flake.nix`; check) to `flake.nix`, update
   `tests/test_repo_shape.py` (root inputs `{nixpkgs, devenv}`) and the "one input" lines in
   `AGENTS.md`. Record the rule change in the evidence.
10. Close the slice (Section 1.6).

### S2: the host binary

**Goal.** Vendomat's flake builds the host and ISO devenv binary: `pkgs.devenv` from the pinned
nixpkgs with patches 0003 and 0005. It stays in the local store under a GC root (R39: no Attic).
The owner switches the host to it.

**Depends on:** nothing (B5 below needs S1). **Ledger:** `VMT-074`, `VMT-099`, `VMT-105`.
**Evidence:** `evidence/S2-HOST-BINARY.md`.

Steps:

1. Open a workspace: `gitman work s2-host-binary`.
2. Add the binary patches to the repository, for example `devenv-dist/binary/patches/0003.patch`
   and `0005.patch` (the full 0005; W6 built the binary with it). Keep 0008 out (R31).
3. Add the overlay as `nix/devenv-overlay.nix`, from `devenv-vendomat-overlay.nix`. Keep its
   `filterdiff -x '*/CHANGELOG.md'` step: the `CHANGELOG.md` hunk of 0003 needs patch 0001.
   Remove the `with0008` argument.
4. Extend `flake.nix` without a new input:
   - `overlays.devenv = import ./nix/devenv-overlay.nix { patchDir = ./devenv-dist/binary/patches; };`
   - `packages.x86_64-linux.devenv` from the pinned nixpkgs with that overlay.
   - Replace the hard-coded `defaultFork` store path (`flake.nix:15`) with
     `self.packages.x86_64-linux.devenv`, so the launcher uses the patched binary.
   - Update the output list in `AGENTS.md`.
5. Build, after the btrfs check. The build takes 23 minutes without the cargo tests and 49 with
   them. Release builds keep the tests.

   ```sh
   nix build .#devenv --print-out-paths
   ./result/bin/devenv version    # expect devenv 2.4.0
   ```

6. Fixtures, as the opt-in Testee check `binary-e2e` with `PATH` set to the new binary:
   - **B2 offline entry** (W6, `VMT-074`): a locked git input whose source is in the store, an
     empty fetcher cache (`XDG_CACHE_HOME` to an empty directory), and the remote stopped. Stock
     fails with `Failed to fetch git repository ... Connection refused`; the patched binary enters.
     Reuse `w1-fork/bin/` for the git daemon and the first-entry steps. Use a free port, not 19418.
   - **B5 refusal** (W6, `VMT-099`; needs the S1 tag): a machine marked
     `vendomat.mode = "adopt-existing"`. `devenv machines install NAME` refuses before any contact
     against a running VM. Record the VM's boot id, uptime, `/root` listing, and store path count
     before and after; all stay the same. An unmarked machine passes the refusal step (stop it at
     the SSH preflight with a closed port). VM files under `/mnt/shared/vendomat-p21/s2/`.
   - **B6 catalog**: the binary enters a slice 1 or S3 catalog workspace.
7. **Keep the binary; no Attic (R39).** Make an indirect GC root outside the repository, for
   example `nix build .#devenv --out-link ~/.local/state/vendomat/roots/devenv-<commit>`. Record
   the store path, its NAR hash (`nix path-info --json`), and its closure size. Other machines
   get it through Harmonia once S3's sharing module runs, and the ISO carries it.
8. **Owner gate: switch the host binary.** Prepare the change; do not apply it. Today nix-meta
   installs devenv in `profiles/developer.nix:10,75` (`pinnedDevenv` from
   `github:cachix/devenv/v2.4.0`). The change points that at Vendomat's `packages.devenv` (or adds
   the overlay). Project 22 moves the machine layer to nix-systems; check its state and
   coordinate before you choose the repository. Show the owner the diff and the rollback (the
   previous NixOS generation). Apply only after a yes in the session.
9. Close the slice. Record in `CURRENT.md` whether the host switch happened.

### S3: the catalog, the template, and the Vendomat commands

**Goal.** A workspace uses `vendomat.yaml`, read by the Nix parser, with every ruled key, on stock
devenv 2.4.0 and the S1 module input. The commands `update` and `explain` exist. Errors show the
`vendomat.yaml:` lines first.

**Depends on:** S1 (R40, R41, R42, R45 settle D1, D2, D4, D8). **Ledger:** `VMT-002`, `VMT-003`, `VMT-010` to `VMT-013`,
`VMT-020` to `VMT-022`, `VMT-030` to `VMT-036`, `VMT-040` to `VMT-046`, `VMT-050` to `VMT-058`,
`VMT-060` to `VMT-063`, `VMT-090` to `VMT-094`, `VMT-099` (catalog half), `VMT-103`, `VMT-111`,
`VMT-112`, `VMT-116`, `VMT-117`, `VMT-121` (first half), `VMT-122`, `VMT-127` (two VMs), `VMT-128`. **Evidence:**
`evidence/S3-CATALOG.md`.

Steps:

1. Open a workspace: `gitman work s3-catalog`.
2. **Parser.** Copy parser v3 to `devenv/parse.nix` (check the hash first). Then close two gaps:
   - `VMT-013`: count nesting depth while parsing and fail with
     `vendomat.yaml:LINE:COL: nesting deeper than N levels` before Nix runs out of stack. W4 saw
     the overflow between 800 and 850 levels. Choose N well below it, for example 64, and record
     the choice.
   - `VMT-035`: return positions for values, for example a side table from key path to
     `LINE:COL`, so a schema fault can say `vendomat.yaml:LINE:COL: <path> ...`.
3. **Catalog.** Rewrite `devenv/devenv.nix` from the W4 catalog (`catalog.nix`, hash in Section 3)
   and the slice 1 checks. Remove the primop call. Keep:
   - one parse; a missing or empty file means an empty catalog (`VMT-021`);
   - `structure`, `typeFaults`, `programFaults`, `jsFaults`, `pyFaults`; one error that lists
     every fault (`VMT-030` to `VMT-032`);
   - `guard` on each value and `_module.check = guard true` (`VMT-031`). Keep the `config` shape
     a literal attribute set: `config = guard mapping` gave infinite recursion in W4;
   - `prune`, and mappings in an inner module with `_file = "vendomat.yaml"` (`VMT-050`);
   - YAML values as plain definitions; catalog defaults with `lib.mkDefault` (R23, `VMT-091`).

   Keys:

   | YAML key | Native option | Rule |
   | --- | --- | --- |
   | `programs` | `packages` | `VMT-033` |
   | `env` | `env` | `VMT-033` |
   | `languages.python.version` | `languages.python.{enable,version}` | `VMT-040`, `VMT-045` |
   | `languages.python.uv` | `languages.python.uv.enable` (default on) | R20, `VMT-092` |
   | `languages.python.uv.sync` (`auto`, `true`, `false`) | `languages.python.uv.sync.enable` | `auto`: on only if `pyproject.toml` exists (`VMT-041`, `VMT-042`) |
   | `languages.javascript.version` | `languages.javascript.{enable,package}` | from slice 1 |
   | `languages.rust.version` | `languages.rust.{enable,channel,version}` | `VMT-044` |
   | `services.postgres`, `services.redis` | `services.<name>.enable` | R23, `VMT-090` |
   | `machines.NAME.host` | `machines.NAME.target.host` | `VMT-060` |
   | `machines.NAME` (always) | `networking.hostName = NAME` | R21, `VMT-061`, `VMT-062` |
   | `machines.NAME.virtual` | `hardware.facter = null` | R23, `VMT-063` |
   | `machines.NAME.mode` | `machines.NAME.vendomat.mode` | D4, `VMT-099` |

   No home key (R35, `VMT-122`). Basix keys live in `basix.yaml` (R38), so the catalog builds no
   extension point for them. Keep the parser a plain function that another module can import.
4. **Template.** Rewrite `templates/workspace/devenv.yaml` (R11, R28, R22):
   - `vendomat` at `git://server/vendomat?ref=release`;
   - `nixpkgs` follows `vendomat/nixpkgs`;
   - `devenv` follows `vendomat/devenv` (if D2 chose the flake input) or the S1 tag;
   - `nixpkgs-python` and `rust-overlay`, each with `inputs.nixpkgs.follows: nixpkgs`;
   - `imports: [vendomat/devenv]`;
   - no `require_version`.

   Remove `devenv/devenv.yaml`'s input list: it existed for patch 0007, which is gone.
5. **Hatch line** (`VMT-054` to `VMT-056`, `VMT-093`): shell entry prints one `advanced:` line
   that counts the leaves each hatch file writes (call the file as a module and count its
   attribute leaves; W4 F11). It says "settings", not "options". `devenv.local.nix` counts
   separately and says "(this checkout only)". `{ }` and empty files print nothing. The D8
   setting hides the line.
6. **`vendomat explain`** (R27, `VMT-057`): the catalog exposes a lazy option tree that
   `devenv eval` can read (W4 F12: `devenv eval X` reads `config.X`; inside map options, read the
   key's priority to name the right file). A Python command prints the user's YAML keys, each
   with its native option, value, and source file, then a section for options set only in Nix.
   `--json` prints the same data.
7. **Error trimming** (`VMT-117`): before the launcher `exec`s the shell, it runs a cheap evaluation
   (the eval cache makes it fast) and captures standard error. On failure it prints the text
   after the last `error:` with the `vendomat.yaml:` lines first, and writes the full trace to
   `~/.local/state/vendomat/logs/`. On success it `exec`s the shell as today.
8. **`vendomat update`** (R25, `VMT-094`, `VMT-058`): read `devenv.yaml` with the existing
   `yamlsubset.py`, compare with the template's required lines, add missing lines and keep the
   user's lines, name each added line, then run `devenv update`. With `--check`, report missing
   lines and exit 1.
9. **Spike `VMT-116`:** do unused template inputs (`rust-overlay` in a Python-only workspace) cost a
   fetch on shell entry? Test with an empty fetcher cache and network blocked after the lock
   exists. Record the answer; if they do, propose a fix to the owner.
10. **Launcher.** Add `update` and `explain` to the dispatch (they run the Python CLI). Keep the
    project 14 verbs as D1 decided. Add new Python modules to `MODULES` in
    `tests/test_repo_shape.py`.
11. **Tests.**
    - Rewrite `tests/nix/catalog.nix` and `tests/test_catalog_module_nix.py` for the Nix parser (no
      stub primop).
    - Update `tests/test_catalog_template.py`: the primop string assertions go; the new template
      lines come.
    - Copy a curated parser corpus into `tests/fixtures/yaml/` (the hand cases `p4`, `edge`,
      `deep`, and `rust`: about 365 files) with expected results. Copy the generators to
      `tests/tools/` and add an opt-in `parser-fuzz` check that generates the large corpora from
      fixed seeds.
    - Port W4 F1 to F14 and F4b as the opt-in check `catalog-e2e` on the pinned nixpkgs (Section
      2.5).
11b. **Sharing module** (R39, `VMT-127`, `VMT-128`): a NixOS module in Vendomat that the catalog
    turns on for every machine unless `serve: false`. It runs Harmonia, makes the signing key at
    first boot (secrets never enter the store), and gives the other machines of the workspace the
    substituter, the public key, `fallback = true`, and a short timeout. Project 19 and project 20
    (S6, S7) hold the earlier proofs and the keyless-boot facts. Prove it with two VMs as the
    opt-in check `sharing-vm`: machine A builds a path, machine B substitutes it from A, and a
    machine with `serve: false` runs no Harmonia. VM files under `/mnt/shared/vendomat-p21/s3/`.
12. **Docs.** Update `AGENTS.md` (layout, outputs, modules) and `README.md` to the project 21
    state. Keep project state out of `AGENTS.md`.
13. Run `testee verify`, `catalog-e2e`, `parser-fuzz`, `sharing-vm`, and the updated `front-door-e2e`.
14. **Release.** Tag a Vendomat version and fast-forward `release` in the collection
    (`git://server/vendomat`). A fresh workspace from `vendomat new` must enter the shell with the
    S1 module input and stock devenv. This proves `VMT-020`'s "pin through a published lock".
15. Close the slice.

### S4: `vendomat apply` and `vendomat rollback`

**Goal.** A machine applies its own configuration with no SSH, and rolls back to an earlier commit
with a lasting result.

**Depends on:** S3, D6. **Ledger:** `VMT-072`, `VMT-075`, `VMT-098`, `VMT-110`. **Evidence:**
`evidence/S4-APPLY-ROLLBACK.md`.

Steps:

1. Open a workspace: `gitman work s4-apply`.
2. **`vendomat apply`** (local, R15):
   1. Read the machine name from `/etc/devenv/machine-facts.json` (`hostname`; R21 makes it the
      machine name). `vendomat apply NAME` with another machine's name passes through to
      `devenv machines deploy NAME`.
   2. Refuse uncommitted changes to `vendomat.yaml`, `devenv.lock`, and the hatch files unless
      `--dirty` (D6).
   3. `devenv build machines.NAME.build.nixos`.
   4. `/run/wrappers/bin/sudo nix-env --profile /nix/var/nix/profiles/system --set TOP`.
   5. `/run/wrappers/bin/sudo TOP/bin/switch-to-configuration switch`.
   6. Append the D6 record line.
   7. Report the new generation and `systemctl --failed`.

   Reuse `w9-rollback/bin/apply.sh` for the order of steps.
3. **`vendomat rollback`** (R30, W9 design):
   1. Read the record and the target's generations.
   2. Pick the newest earlier entry with a different toplevel and a clean commit, or
      `--to REV`, or `--generation N`.
   3. Refuse uncommitted changes, an unknown commit, or a commit missing from the repository.
      Show the diff first.
   4. Restore `vendomat.yaml`, `devenv.lock`, and the hatch files from that commit, and commit
      them as `rollback to REV`. A bare working-copy restore is not allowed: the next apply would
      silently roll forward (W9 R3).
   5. Apply.
   6. Options: `--exact` checks out REV and gives the identical earlier store path; `--fast` does
      a profile rollback plus switch and still commits; `--boot-only` runs `bootctl set-oneshot`
      for recovery only.
4. Do not set `system.configurationRevision` (`VMT-110`).
5. Python modules: for example `apply.py`, `rollback.py`, `record.py`. Update `MODULES`.
6. **VM fixtures** (opt-in check `machines-vm`; images under `/mnt/shared/vendomat-p21/s4/`): build
   a qcow2 EFI disk from `_nixosEval` (`w2-machines/common/expose.nix`). Run W2 T1 and W9 R1 to R6
   through the real commands:
   - apply A, then A';
   - rollback gives the identical A path, copies nothing, adds a generation that is the default
     boot entry, and boots with zero failed units;
   - a working-copy-only restore is refused;
   - rollback after the A path left the target store;
   - `--fast` and `--boot-only`.
7. Run `testee verify` and `testee verify machines-vm`.
8. Close the slice.

### S5: the Vendomat side of Basix

**Goal.** Vendomat serves the Basix release channel. Vendomat never names Basix in code (R1). The
Basix repository is `../basix`; its build is the Basix plan, `../basix/.scratch/projects/001-initial-concept/PLAN.md`. The Basix design, the `BSX-`
ledger, and steps 1 to 15 of the former S5 moved there on 2026-10-13.

**Depends on:** S1 to S4. D3 (R37) and D5 (R38) are ruled. **Ledger:** `VMT-121` (with Basix).
**Evidence:** `evidence/S5-BASIX.md` here; the Basix evidence is in the Basix repository.

Steps:

1. **Collection hook** (D3, R37). Extend `hooks/collection-pre-receive` so any repository may
   fast-forward `refs/heads/release`, not only `vendomat`, with a test in
   `tests/test_collection_hook.py`. Creating `~/vendor/basix` is an owner gate and a Basix plan step.
2. **Parser import** (D5, R38). Basix reads `basix.yaml` with the parser from the Vendomat source.
   Check that S3 leaves the parser a plain function that another module can import, with the file
   name in its error lines.
3. **Fixtures.** The fresh Basix workspace and the pair update (`VMT-121`) run from the Basix
   repository. Record the Vendomat-side result in `evidence/S5-BASIX.md`.
4. Close the slice in both repositories (Section 1.6).

### S6: retire the old binary fork

**Goal.** Nothing in Vendomat depends on `v2.4.0-vendomat.4` or on patches 0001, 0002, 0004, or 0006
to 0009.

**Depends on:** S1, S2. **Ledger:** `VMT-080`, `VMT-081`. **Evidence:** `evidence/S6-FORK-RETIRED.md`.

Steps:

1. Open a workspace: `gitman work s6-retire-fork`.
2. Remove the old series from `devenv-dist/` (`SERIES`, `MANIFEST.sha256`, `RESULT`, `UPSTREAM`
   lines for `.4`, and the patches 0001, 0002, 0004, 0006, 0007, 0008, 0009). Keep the binary
   patches of S2 and the module series of S1.
3. Update the hard-coded `.4` values: `tests/test_devenv_dist.py:57,159`,
   `tests/test_front_door_e2e.py:21`, `devenv.nix:109,116,117`, and the `.3` values in
   `templates/workspace-registry/examples/*`, `tests/test_registry_v6.py`, and
   `tests/test_commands_v6.py` (or remove those with S8).
4. Remove the per-patch tests for 0006 to 0009 and the 0009 `fn case_` count test.
5. Never delete a published tag. The collection keeps `v2.4.0-vendomat.2`, `.3`, and `.4`.
   nix-systems still pins `.2`; it moves in S8.
6. Run `testee verify` and every opt-in check that a removed pin touched.
7. Close the slice.

### S7: real-machine gates

**Goal.** Prove the design on real hardware and between two real machines.

**Depends on:** S5. **Ledger:** `BSX-119`, `VMT-127`. **Evidence:** `evidence/S7-REAL-MACHINES.md`.

Steps:

1. **Owner gate: real disk write.** Name the machine, the disk by its full `/dev/disk/by-id/`
   name, and what the disk holds now. Get a yes in the session. Stop otherwise.
2. Boot the Basix ISO on the machine. Run `basix install`. Record the guard's list, the chosen
   disk, the hardware report (filtered), the time, and the first boot (no keys, zero failed
   units).
3. On the installed machine: `vendomat apply` a change, then `vendomat rollback`.
4. **Two-machine sharing** (`VMT-127`, R39): each installed machine makes its own signing key at
   first boot and runs Harmonia; the other substitutes from it with `fallback = true` and a short
   timeout.
5. Record everything. The new system has no Attic. Leave today's `server` Attic to project 22.

### S8 (proposed): move the consumers and retire the project 14 code

This slice is not in `PLAN.md` yet. It follows D1. Add it to the plan when the owner rules on D1.

**Goal.** No consumer uses `vendomat.toml`, and the repository holds only the project 21 code.

**Depends on:** S3, S4, D1, and project 22's migration order (its concept: "Move from
`vendomat.toml` to `vendomat.yaml` when project 21's catalog ships").

Steps:

1. Move vendomat-demo, then nix-systems, from `vendomat.toml` and `.vendomat/` to
   `vendomat.yaml` and the S3 template. Each repository is its own change in its own repository,
   coordinated with project 22.
2. In nix-meta (project 22 territory): remove the old Vendomat NixOS module import that installs
   `share/vendomat/consumer-module.nix` and `machine.json` (R36, `VMT-123`;
   `machines/server.nix:66-71`, `profiles/developer.nix:16`). Coordinate with project 22.
3. In this repository, remove the TOML flow and its tests: `registry.py`, `generate.py`,
   `devenvgen.py`, `locate.py`, `lockpath.py`, `bump.py`, `store.py`, the `sync`, `path`, `bump`,
   and `machine` commands, `direnv/vendomat.sh`, `templates/workspace-v6`,
   `templates/workspace-registry`, the V6 module under `nix/devenv-module/`, `preflight/`, and
   every test that covers them (see the inventory in Section 2.4). Keep `push.py` until
   `VMT-120` passes. Keep `hooks/` and `launcher/`. Update `MODULES`, `AGENTS.md`, and
   `README.md`.
4. Update `.scratch/CURRENT.md`: project 21 becomes the implementation contract; project 14 is
   history.

---

## 7. Order and parallel work

```text
Phase 0 ── D1..D8 as needed
  ├── S1 module fork ──┬── S3 catalog ── S4 apply/rollback ── S5 Basix ── S7 real machines
  └── S2 host binary ──┤                      │
                       └── S6 retire fork     └── S8 consumers and project 14 code (after D1)
```

- S1 and S2 can run in parallel in two workspaces. S2's refusal fixture (B5) waits for S1's tag.
- S6 can run as soon as S1 and S2 land.
- S8 waits for the consumers' migration, which project 22 schedules.
- The two owner gates (S2 host switch, S7 disk write) can happen at any time after their slice is
  otherwise done. The rest does not wait for them, except S7.

## 8. Done

Project 21 is implemented when:

- every ledger row is "Fixture pass" or better, or names a recorded owner decision to leave it
  open;
- S7's real-machine gates pass;
- `.scratch/CURRENT.md` names project 21 as the implementation contract.

# W6: the patched host devenv binary (R22, A13) — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w6-host-binary/REPORT.md (Sonnet subagent). Overlay: /home/andrew/.local/state/vendomat/p21/2026-10-13/w6-host-binary/devenv-vendomat-overlay.nix with pkgs.nix and patches/ beside it. Logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w6-host-binary/logs/. Overlays under /mnt/shared/vendomat-p21/w6/ deleted; installed-golden.qcow2 sha256 unchanged (golden-sha-before/after). Orchestrator spot-check: logs/B2-stock.log fails with 'Failed to fetch git repository', logs/B2-patched.log ends rc=0; logs/B5-refuse-running.log shows the refusal for machines.running, and B5-before/after show the same boot_id, /root listing, and store count; logs/B4-upstream.log shows PR #3244 OPEN, no reviews. -->


Fixtures only. No change to the Vendomat repository, a host disk, or a host profile. No sudo, no GC, no profile install.

## Inputs and versions

- Stock binary `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0` is `pkgs.devenv` of nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the Vendomat `flake.lock` pin). Checked: `nix eval` of `devenv.outPath` at that rev returns the same path.
- Source: cachix/devenv v2.4.0 (`/nix/store/n1zz8rrfw0sx39dizqj4a6468lxga71q-source`). Patches: `devenv-dist/patches/0003`, `0005`, `0008` (copies and sha256 in `patches/`).
- Built binaries: `result-p35` = 0003 + 0005 (`/nix/store/x8b8q02h1wd597nkr571bcv72m1bgzzd-devenv-2.4.0`); `result-p358` = 0003 + 0005 + 0008 (`/nix/store/f7930qbd07n0ngqnms2i50x068v9mq80-devenv-2.4.0`).
- Overlay: `devenv-vendomat-overlay.nix` (args `patchDir`, `with0008`, `skipChecks`); `pkgs.nix` imports the pinned nixpkgs with it.
- Upstream read 2026-10-13 15:25 EDT. QEMU 11.1.1 with KVM; disk-image files only. Work dir: this directory.

## B1. Build

- Command: `nix build -f pkgs.nix devenv` and `nix build -f pkgs.nix --arg with0008 true --arg skipChecks true devenv` (logs `logs/B1-build-*.log`).
- Expected: patches apply; binary builds.
- Actual patch fit: 0005 applies to the nixpkgs source with offsets only (-11, -29 lines), no failure. 0008 applies after 0003. 0003 fails on its `CHANGELOG.md` hunk, because that hunk needs patch 0001 (not in this binary). The overlay drops that hunk with `filterdiff -x '*/CHANGELOG.md'`; the code hunks apply unchanged.
- Build time: 48 min 51 s (patched, with the cargo test phase) and 23 min 08 s (+0008, `doCheck = false`), on a loaded host. The test phase ran the three new 0005 unit tests: all PASS (`vendomat_metadata_parses_mode_and_defaults_to_none`, `install_policy_refuses_adopted_machine_and_names_it`, `install_policy_allows_a_fresh_install_machine`).
- The first build (2 patch filters + devenv) needed 58 fetched paths (549 MiB download, 3.1 GiB unpacked) from cache.nixos.org; nothing outside it. No cargo or nix source build was needed beyond devenv itself.
- Size: each patched output is a new 218 MiB path (NAR 228.2 MB, stock 228.1 MB). The closure is 460 MiB, 90 paths, and the other 89 paths are identical to the stock closure.
- Store growth by me: about 4.6 GiB estimate (3.1 GiB fetched build inputs + 2 x 0.22 GiB outputs + sources) plus 0.54 GiB in `exp/` (fetcher caches). Path counts moved 98786 to 99538, but two other spikes also built, so that count is not mine alone.
- `devenv version` of both prints `devenv 2.4.0 (x86_64-linux)`.
- Verdict: PASS. Both variants build from the pinned nixpkgs with the overlay.

## B2. Offline entry (A13)

- Case: locked git source in the store; empty fetcher cache (`XDG_CACHE_HOME` = new empty dir); remote (own git daemon, port 19628) stopped; `--no-eval-cache shell`. Script `bin/q2.sh`. Control: stock with the default cache.
- Expected: stock fails, patched enters.
- Actual:
  - stock, empty cache: FAIL. `Failed to fetch git repository 'git://127.0.0.1:19628/extra.git'` at `resolve-lock.nix:89` (`logs/B2-stock.log`).
  - stock, default cache (control): enters, `EXTRA=/nix/store/jymrrna...-source` (`logs/B2-stock-control-defaultcache.log`).
  - patched (0003+0005): enters (`logs/B2-patched.log`).
  - patched + 0008: enters (`logs/B2-patched0008.log`).
- Extra: first entry with no lock, source not in the store, daemon up, empty cache: both patched variants enter (`logs/B2-patched-firstentry.log`, `logs/B2-patched0008-firstentry.log`). I did not run stock on that case (W1 did).
- Verdict: PASS. 0008 changed no outcome in any case I ran. Same finding as W1.

## B3. Warm the cache with the stock binary

Script `bin/b3.sh`, log `logs/B3-warm-cache.log`. State: store holds the source, remote down. Each step used a fresh cache dir.

| Step | Result |
| --- | --- |
| S2 `nix flake prefetch` of the locked git URL while the remote is DOWN | FAIL (`Failed to fetch git repository`); stock still fails afterwards |
| S1 the same prefetch while the remote is UP, then remote down | works: stock enters offline. The prefetch took about 10 s and left a 56 KiB cache for this 1-commit repo |
| S3 copy the S1 cache dir to a new empty cache dir | works (cache dir 43 MiB after the entry also fetched nixpkgs; the git part is the small part) |
| control: empty cache, remote down | FAIL |

- First attempt mistake: I put `narHash` into the prefetch URL; git then used it as part of the path. I removed it; the table shows the corrected run.
- Observation: a warm fetcher cache fixes the entry. It needs the remote to be up once per user and cache dir. The failure case (new user, ISO, cleared cache, remote down) has no warm cache, so the cache must come from somewhere else: a one-time online step at first login, or a copied cache dir (size grows with the shallow clone of the real collection).
- Inference: the cheap pre-step is enough only for a machine that was online once. It does not help a fresh machine that must enter with the remote down, and that is the A13 case.
- Not tried (limit of three): a `path:/nix/store/...` input (W1 E1 works but loses provenance), a substituter (W1: fetchTree does not consult one for git types).

## B4. Upstream (read-only; nothing posted)

- PR #3244 `fix(bootstrap): reuse locked inputs already in the store`: state OPEN, created and last updated 2026-10-01, mergedAt null, reviewDecision empty, 0 reviews, 1 comment (the auto reviewer bot), CI check rollup 1 SUCCESS.
- Latest release: v2.4.0 (2026-09-24). Next: v2.3.1 (2026-09-11), v2.3, v2.2.2, v2.2.1. No release after 2026-09-24.
- Verdict: unchanged since W1. The PR sits 12 days without review. 0003 stays until it merges and a release (and then a nixpkgs bump) carries it.

## B5. Patch 0005 in the new design

What 0005 reads: the option `machines.<name>.vendomat.mode` (null | "fresh-install" | "adopt-existing", default null). The module copies it into `machinesMeta.<name>.vendomat.mode`. The CLI deserialises `MachineMeta.vendomat.mode` (serde default None) and, in `machines_install` right after name validation, bails if any named machine has `adopt-existing`. It reads no file and does not look at the target. The option and the `machinesMeta` entry live in `src/modules/machines.nix`, which is the module half of 0005. The Rust half is in `machines.rs`. In the module-only fork the module half belongs to the module input and the Rust half to the binary. The binary build ignores the module half.

Proposed trigger (smallest): keep this option and this patch unchanged. The catalog sets `vendomat.mode = "adopt-existing"` for every machine its `vendomat.yaml` marks as installed, and `"fresh-install"` for the rest. Reasons: the module half is 39 lines and ships inside the module fork you already need; the Rust half is already unit-tested; no new file format. A bool `installed` would save a few lines only.

Fixture: workspace `ws-b5` (module input = stock modules + the 0005 module hunk, `mod5/`); machines `running` (adopt-existing) and `unmarked` (no mode) on the VM; `ghost*` machines on port 2269 where nothing listens. VM: overlay `run.qcow2` on `installed-golden.qcow2`, booted on port 2261. Binary: `result-p35`.

| Test | Expected | Actual |
| --- | --- | --- |
| `install running` (VM up, adopt-existing) | refuse, no contact | Refused: "devenv made no connection to the target". VM before/after: boot_id `1ead5518...` unchanged, uptime 2141.61 to 2142.10 s, `/root` = `.nix-channels .nix-defexpr .ssh` both times, store entries 588 both, no `/root/kexec`. sshd "Accepted" count 3 to 4, and the +1 is my own "after" probe session. (`logs/B5-before.txt`, `B5-after.txt`, `B5-refuse-running.log`) |
| `install ghostadopted`, also with `--phases reboot` and `--disko-mode mount --no-reboot` | refuse in every phase and mode | Refused each time |
| `install ghost unmarked running` | one adopted name refuses all | Refused, names only `machines.running` |
| `install ghost` (no mode), `ghostfresh` (fresh-install), closed port | pass the refusal step | Both stop at `Preflight probe failed` (SSH), so they passed refusal |
| `install unmarked --phases kexec` against the running VM | pass refusal, stop before disko | It ran the kexec phase: boot_id changed to `cf9c2622...`, hostname `nixos-installer`, root on tmpfs. Disko did not run (phase list ends at kexec). The VM was an overlay. This is the damage 0005 prevents for a marked machine |
| `machines plan ghostadopted` | not refused | Not refused: it tries SSH |
| stock binary + module that sets `vendomat.mode` (`logs/B5-stock-compat.log`) | stock ignores the key | Stock ignores it (no `deny_unknown_fields` on `MachineMeta`) and contacts the target: `Preflight probe failed` |
| patched binary + stock module (no option), machine unmarked | fail open | Fail open: no guard. `logs/B5-stockmodule.log` |
| stock module + catalog sets `vendomat.mode` | eval error | Eval error "option does not exist" (fails closed) |

- Verdict: PASS. 0005 in the new design needs the binary patch AND the module option. Two risks: (1) a catalog that forgets to set the mode gets no guard; make the catalog set the mode for every machine. (2) A module without the option plus the patched binary is silently unguarded; the setting fails at evaluation in that case, so a set mode always has the option behind it.

## B6. Catalog workspace sanity

- Command: copy of W4 `ws-f2` to `ws-b6` (lock sha256 `4f87b032...` identical before and after); `result-p35 shell -- printenv GREETING`, `hello`, `vendomat-explain env.GREETING` (`logs/B6-patched-catalog.log`).
- Expected: same as the W4 stock run.
- Actual: `hi`, `Hello, world!`, `env.GREETING = "hi"  set by: vendomat.yaml`. Same output as W4 `F2.log` (including the "devenv 2.4.0 is newer than devenv input (2.3.1)" warning).
- Verdict: PASS.

## Verdicts

- R22 binary: BACKED. `pkgs.devenv.overrideAttrs` with 0003 and 0005 builds from the pinned nixpkgs in 23 to 49 min, adds one 218 MiB store path, and keeps the stock closure. Work needed in the new design: split 0005 into a binary half (`machines.rs`) and a module half (`machines.nix`, goes to the module fork), and drop the 0003 `CHANGELOG.md` hunk. Do not add 0008.
- A13: the offline failure reproduces on stock and the patched binary fixes it. PR #3244 is still open, unreviewed, unreleased. The "warm the cache" option works only if the machine was online once (per user); it does not cover a fresh machine with the remote down. Keep the 0003 binary (A13 as written) until #3244 ships; recheck at each nixpkgs bump.

## Observation versus inference

- Observation: every table row above comes from a logged run. Inference: the statements about fresh machines, ISO, and risk (1) and (2).
- Gaps: no test of the real collection source size in the cache; no test of 0003 with a github input offline; no run of the full 0005 + module-fork + facter install on a blank target (W5 covers that path); the 0008 build skipped cargo tests.

## Cleanup

- Overlay `run.qcow2`, OVMF vars, TMPDIR removed (`/mnt/shared/vendomat-p21/w6/` deleted). VM stopped. My git daemon on port 19628 stopped; port 19418 untouched.
- `installed-golden.qcow2` sha256 `c1054b7c...` unchanged (`logs/golden-sha-*.txt`).
- btrfs (`logs/btrfs.log`, 7 readings): metadata 80.7 to 83.0 %, unallocated 43.9 down to 29.9 GiB (other spikes shared the drop). Never near a stop condition.

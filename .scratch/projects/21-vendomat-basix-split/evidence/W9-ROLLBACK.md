# W9: a lasting rollback (A11) — 2026-10-13

<!-- Copied from /home/andrew/.local/state/vendomat/p21/2026-10-13/w9-rollback/REPORT.md (Sonnet subagent). Scripts, the git workspace, and logs stay in /home/andrew/.local/state/vendomat/p21/2026-10-13/w9-rollback/. The W2 image was used through an overlay and is unchanged; the overlay is deleted. Orchestrator spot-check: logs/R2-rebuild.log shows 'copying 0 paths'; logs/R2-apply-reboot.log shows system-3-link -> j7p826jd (A), state running, failed []. -->


## Inputs and versions
- Host: Nix 2.34.7, QEMU 11.1.1 (KVM), OVMF 202608. Guest Nix 2.34.8, nixpkgs e7439b6, kernel 6.18.55.
- Stock devenv 2.4.0 (`/nix/store/5sbcspxm...-devenv-2.4.0`), run with `env -u UV_PROJECT_ENVIRONMENT`. W2 pins reused (`devenv.yaml`, `devenv.lock`, `box.nix` copied from `w2-machines/ws-t1-b`).
- VM: qcow2 overlay on the W2 image `t1/box.qcow2` and a copy of `vars.fd`, both in `/mnt/shared/vendomat-p21/w9/`. The overlay and the copy are deleted. The W2 image is unchanged (mtime 00:15).
- Reset step: the W2 image ended at generation 2 (A'). I switched the VM profile to generation 1, deleted generation 2, rebooted, and ran the VM's own GC. Start state: generation 1 = A, A' not in the guest store (`logs/R0-vm-reset.log`).
- Workspace (git repo, raw git allowed): `ws/`. Stand-ins: `devenv.yaml` + `devenv.lock` for `vendomat.yaml`, `hatch.nix` for the hatch file. Commits: C1 78cf925 (A), C2 4227fea (A'), revert 0c8b087, C5 7f29902 (fetchGit revision), C9 6d0cc79 (env-var revision, config A), C10 a5f690d (A'), K 2402057 (kernel 6.12).
- Scripts: `bin/apply.sh` (nix copy, then the two commands), `bin/state.sh`, `bin/rev.sh`, `bin/prev-gen.sh`. Logs: `logs/`. Disk readings: `logs/btrfs.log` (metadata 80.5 to 82.8 %, unallocated 40.87 to 43.87 GiB; never near the stop limits). No host GC, no sudo, port 19418 untouched. Host store growth: small (kernel 6.12 variant plus a few toplevels; well under 4 GiB).

## Fixtures
Times are wall-clock over loopback SSH. Treat them as ordering, not as network figures.

### R1. Build and apply A and A'
- Commands: `devenv build machines.box.build.nixos` at C1 and C2; `bin/apply.sh TOP` (= `nix copy --no-check-sigs --to ssh-ng://root@127.0.0.1`, `nix-env --profile /nix/var/nix/profiles/system --set TOP`, `TOP/bin/switch-to-configuration switch`).
- Expected: A = j7p826jd (W2's A), A' = h7rxzs79 (W2's A'). Apply A' makes generation 2.
- Actual: both paths equal W2's, although the config now lives in `hatch.nix` and the workspace path differs. Copy of A' = 11 paths. Marker `A-prime`, `hello` runs, `systemctl --failed` empty, default boot entry = generation 2. A itself is the installed generation 1 from W2 (not re-applied).
- Verdict: PASS. Inference: the toplevel depends on the config values and the pins, not on the file layout or the workspace path.

### R2. Rollback by files
- Commands: `git restore --source=C1 --worktree -- devenv.yaml devenv.lock hatch.nix`; `devenv build ...`; `bin/apply.sh`; `reboot`.
- Expected: same store path as A, nothing copied, generation 3 -> A, default entry generation 3, reboot gives A with zero failed units.
- Actual: rebuild (13.2 s, all evaluation) gives j7p826jd = A. `nix copy` copies 0 paths. `system-3-link -> A`. `loader.conf` default = the generation 3 entry. Apply took 3.5 s (copy 0.8, set 0.3, switch 2.4). After reboot: current system = A, marker `A`, no `hello`, `systemctl --failed` empty, bootctl "Current Entry" = generation 3 (second boot id confirmed).
- Verdict: PASS. Observation.

### R3. New commit or working-copy restore
- Working-copy restore (`logs/R3a-workingcopy.log`):
  - Version control: HEAD stays C2; `git status` shows ` M hatch.nix`; history does not record the rollback.
  - Machine: generation 3 -> A.
  - Later `vendomat apply` with the restore still in place builds A. `nix-env --set` of the path that is already current creates NO new generation (verified: still 1 to 3, 3 boot entries).
  - If the restore is lost (`git stash`, `git checkout .`, a fresh clone, another machine), the build gives A' (verified, 15 s). The next apply silently rolls forward.
- Revert commit (`logs/R3b-revert.log`):
  - Version control: history C1, C2, C3 = `Revert C2`. `git diff C1 HEAD` is empty (same tree). Clean tree.
  - Machine: same as above, A, generation 3.
  - Later `vendomat apply` builds A (no new generation). Later work on top (add `jq`) builds A + jq (c9iy6rvd...) with no surprise.
- Verdict: the revert (or restore) commit is the durable form. The working-copy restore is only a step before the commit. Observation, except "another machine sees C2" (inference from how git works).

### R4. `system.configurationRevision`
- Setup: `system.configurationRevision = rev` in the machine module. Two ways to supply `rev`: `builtins.fetchGit ./.` (C5 to C8) and `builtins.getEnv "VENDOMAT_REV"` (C9 on).
- Where it lands: in the `nixos-version` package (a JSON blob in the script), so it flows into `system-path`, `etc`, `system-units` and the toplevel. There is no `configuration-revision` file in the toplevel. Per generation: `system-N-link/sw/bin/nixos-version --configuration-revision` prints the rev (`configuration revision is unknown` for generations built without it). Verified in the VM for generations 4 to 7.
- Store paths: every commit gives a new toplevel. A README-only commit (C8) changed the toplevel kl1bxizg -> laij3987. A change of revision touches about 10 small paths (nixos-version, system-path, dbus-1, units, etc, toplevel). Applying it copies 10 paths, 2 s, reloads dbus-broker, creates a new generation and boot entry.
- Uncommitted changes: `fetchGit` returns `rev = 0000...` plus `dirtyRev = <HEAD>-dirty`. Reading `src.rev` first (my first try) records a null revision; read `dirtyRev` first. Two different dirty edits give different toplevels with the same `<HEAD>-dirty` string, so a dirty revision cannot identify a state.
- Pitfall 1: untracked, non-ignored files do not show in `fetchGit`. An untracked `devenv.local.nix` that devenv imports changed the config (`/etc/local-only` present) while the revision stayed clean. `git status --porcelain` in `bin/rev.sh` catches untracked files but not ignored ones.
- Pitfall 2 (stale cache): the devenv eval cache does not track the git HEAD. After a README-only commit, cached `devenv build` returned the old toplevel and the old revision; `--no-eval-cache` gave the right one. `getEnv` IS tracked by the cache: changing `VENDOMAT_REV` re-evaluated every time. Use the env var, set by the CLI.
- Pitfall 3 (jj): a secondary jj workspace of a colocated repo still had `.git`, and `fetchGit` returned the commit of `@-` (checked). jj has no dirty state: the working copy `@` is itself a commit. The CLI should read `jj log -r @-` and treat a non-empty `@` as dirty. Not tested beyond `fetchGit`. Gitman flow untested.
- Rollback matrix from C10 (gen 6) back to C9 (gen 5, rev C9), path of gen 5 = aramir53... (`logs/R4-rollback-matrix.log`):
  - working-copy restore of files from C9: rev `C10-dirty`, path k5rdsfk4... (not gen 5)
  - revert commit: rev = the revert commit, path cgzjhm1l... (not gen 5)
  - `git checkout --detach C9` (whole tree, HEAD = C9): path aramir53... = gen 5. Applied: 0 paths copied, new generation 7 -> gen 5's toplevel, reboot clean, rev C9.
  - So with a revision, the same path returns only when HEAD is the original commit. The R2 expectation (same path) no longer holds for a restore commit. The function is the same; the path differs by the revision files.
- Choosing the previous commit: `bin/prev-gen.sh` over SSH lists each generation with toplevel and rev, then picks the newest generation whose toplevel differs from the current one (gen 6, rev C10 from gen 7). It works. Limits: generations built without a revision give none; the rev must exist in the repo (history rewrite breaks it); "previous" after a rollback is the pre-rollback generation, so two rollbacks in a row flip back.
- Verdict: PASS with caveats. A revision gives provenance, drift detection (R6), and a rollback target. It costs one new toplevel and one new generation per apply, even for an unrelated commit. Inference: a sidecar record (`toplevel -> rev`, kept by `vendomat apply` on the target) would keep paths stable and still give a rollback target. NOT tested.

### R5. Rollback when A is gone
- R5a, gone from the target only (`logs/R5a.log`): deleted generations 2, 4, 6 in the VM and ran the VM's own GC (31 paths, 12.9 MiB). Rolled back to C10 by checkout: host build 17 s (eval; outputs still in the host store), same path as old gen 6, copy 12 paths in 1.6 s, apply total 4.6 s.
- R5b, heavy generation (kernel 6.12, `logs/R5b-*.log`): the host build took 36.8 s (kernel fetched into the host store). Copy to the VM: 16 paths, about 190 MiB, 5.0 to 5.5 s, apply total 8 to 9 s. After deleting the generation and the VM GC (190.6 MiB freed), a second copy cost the same. Over a real link, expect size / bandwidth. The running kernel did not change (still 6.18.55) after `switch`; the new kernel needs a reboot. /boot gets one more kernel and initrd per distinct kernel (85 MB used of 249 MB after two kernels).
- R5c, gone from the host too: I cannot GC the host, so I simulated a host with only the cache. Copied the K derivation closure into a scratch chroot store on tmpfs (`/dev/shm/w9-alt`, deleted after) and ran `nix-store --store local?root=... --realise`: 35 s, 414 paths fetched (518.5 MiB download, 1.3 GiB unpacked), 250 derivations built locally (small), same toplevel path. Add the evaluation time (about 15 to 40 s) and the first fetch of the nixpkgs and devenv inputs (not measured). Offline, with the inputs missing, the rollback fails; `devenv.lock` pins them but does not keep them.
- Verdict: PASS. Files rollback works for any past commit as long as the lock inputs are fetchable. Cost grows with how much the old generation differs, from 2 s (small) to under a minute (kernel).

### R6. Profile rollback
- Commands in the VM: `nix-env --profile /nix/var/nix/profiles/system --rollback`; `/nix/var/nix/profiles/system/bin/switch-to-configuration switch`.
- Actual: 0.3 s + 2.3 s = 2.5 s, vs 3.5 to 4.6 s for the apply of an existing path, plus 13 to 17 s of host evaluation for the files route. Profile moved to generation 10 (no new generation), default boot entry = generation 10, failed units empty. Generation 11 stays as a "future" entry.
- Drift: the workspace was clean at K, the machine ran C10. Nothing in the files tells that. With the revision the CLI can see it (`nixos-version` rev C10 vs HEAD K). A later `bin/apply.sh K` re-pointed the profile to generation 11 and created no generation 12, so the roll-forward is silent. The next `--rollback` from generation 10 goes to the next lower existing number, not to the commit before.
- Verdict: PASS. It is faster, works offline, and needs no workspace, but it leaves the files and the machine apart. It fits recovery on the machine, not a lasting rollback.

## Observation and inference
- Observation: everything marked PASS above ran in the VM with logs in `logs/`.
- Inference: behaviour across other hosts or clones, the jj dirty rule, the sidecar idea, bandwidth scaling, and the claim that the boot menu stays recovery only (this comes from W2, not re-run here).

## Proposed `vendomat rollback`
1. Read: the target's generations over SSH (`system-N-link` toplevel and `nixos-version --configuration-revision`), the workspace HEAD and `git status` / `jj` state.
2. Choose the target: default = newest generation with a different toplevel and a known revision (undo the last change); `--to REV` or `--generation N` to pick another. Refuse when the workspace is dirty, when the revision is unknown, or when the rev is not in the repo. Print the diff (`git diff REV..HEAD --stat`) and the generation numbers before it acts.
3. Restore: make the tracked config files (`vendomat.yaml`, `devenv.lock`, hatch files) equal to REV's tree and COMMIT the result as "rollback to REV" (not a revert of the last commit: it works over many commits). Do not leave a bare working-copy restore.
4. Apply: build with `VENDOMAT_REV` = the new commit id (+ `-dirty` rule), copy what is missing, run the two commands. Report the new generation and `systemctl --failed`.
5. Options: `--exact` checks out REV detached and skips the commit (gives the same store path as the old generation; the history then needs a manual follow-up); `--fast` does the profile rollback plus switch when the target generation exists (2.5 s, offline) and then still records the restore commit so the files match; `--boot-only` only runs `bootctl set-oneshot` (recovery).
6. Always set `VENDOMAT_REV` from the CLI and keep `--no-eval-cache` or the env var in the key. Never rely on `fetchGit` inside the module.

## Verdict on A11
CONFIRMED with amendments.
- Restore-and-apply works: new generation 3 -> A, default boot entry, reboot clean (R2). It needs no special state beyond the files.
- Amend: "restore the files" must end in a commit (R3), or a later reset, stash, clone, or another machine silently rolls forward.
- Amend: if the machine records the commit (R4), the restored toplevel differs from the old one by the revision files, so "same store path" holds only for `checkout REV`. Decide between `configurationRevision` (provenance, churn: new generation per commit) and a sidecar record (stable paths, untested).
- The boot menu and the profile rollback stay recovery tools: they leave files and machine apart (R6).
- A rollback to a gone generation needs only the lock inputs and a cache (R5).

## Gaps
- Real network speed, real hardware, and the ESP size limit with many kernels are untested.
- The host-absent case was simulated with a scratch chroot store, not on the host store; input fetch time not measured.
- The sidecar alternative, the jj/gitman workspace flow, and the deployer watchdog (A4) are not tested.
- `vendomat.yaml` does not exist yet: `devenv.yaml` + `devenv.lock` stood in for it.
- No test of `bootctl set-oneshot` in this run; W2 covers it.

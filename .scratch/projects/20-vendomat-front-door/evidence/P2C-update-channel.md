# Spike C: update channel (H1 release branch) against tag edit (H2)

Date: 2026-10-12. Host: server, x86_64-linux. Project 20, DOOR-067. No repository changed.
Status: fixture proof on the pinned fork. Nothing here is a passed gate.

## Tools and fixture

- Fork: `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`. Every log starts with `devenv 2.4.0+fb5d382 (x86_64-linux)`.
- Disk check before work: unallocated 37.09 GiB, metadata 71 percent. No garbage collection ran. No uv. No VM build.
- Fixture is under `work/`. Setup scripts are in `scripts/` (`setup.sh`, `rebuild.sh`, `env.sh`). Logs are in `logs/`.
- Loopback `git daemon` serves `repos/vendomat` and `repos/extra` over `git://127.0.0.1:<port>/`. The fork-3 and S9 records say `git+file` does not lock a revision on 2.4.0. Q1c re-checks that.
- `repos/vendomat` has branch `release` with tags `v1`, `v2` and branch `main` with one extra commit `v3-unreleased`.
  Each commit has `flake.nix` (input `nixpkgs`), `devenv/devenv.yaml` (inputs `nixpkgs` = devenv-nixpkgs `256551e4`, and `extra` = tag `e1` or `e2`), and `devenv/devenv.nix` (sets `VENDOMAT_VERSION` and `VENDOMAT_EXTRA`).
  `v1` uses `extra` `e1`; `v2` uses `e2`.
- `repos/extra` is data only (`marker.txt`), tags `e1`, `e2`.
- Workspace (H1): `devenv.yaml` has one input, `vendomat: git://127.0.0.1:<port>/vendomat?ref=release`, and `imports: [vendomat/devenv]`. The workspace is its own git repository, so rollback uses git.
- Two daemon ports appear. Port 43985 (Q1, Q2, Q3a, Q3b) and port 34125 (Q3c, Q4, Q5, Q1b, Q1c). The fixture was rebuilt between them. Shapes agree.
- Fixture lesson 1: the Vendomat input needs a `flake.nix`. Without it the lock fails: `path '«git://...»/flake.nix' does not exist`. Real Vendomat has one (flake.nix, one input).
- Fixture lesson 2: Nix caches the branch-to-revision lookup per URL. A rebuilt fixture on the same port kept the old revision. I used a fresh port per rebuild.

## Q1. Does one input plus inheritance enter the shell, and does `devenv update` move v1 to v2 and never to main?

- Hypotheses: H1 yes. H2 does not apply (no tag).
- Inputs: release at `v1` (`e342df4f`), then release at `v2` (`4ac511b0`); main at `59614404`. Port 43985.
- Commands: `devenv --no-eval-cache shell -- sh -c 'echo VERSION=$VENDOMAT_VERSION EXTRA=$VENDOMAT_EXTRA'`, then fast-forward `release` to `v2`, then `devenv shell`, `devenv update`, `devenv shell`.
- Expected: shell shows v1, update moves to v2, never main.
- Actual:
  - First entry: `VERSION=v1 EXTRA=extra-1`, exit 0. The lock holds `vendomat git e342df4f release`, plus `extra` e1 (inherited from the Vendomat devenv.yaml).
  - After `release` moved to v2, `devenv shell` without update: `VERSION=v1 EXTRA=extra-1`. The lock holds.
  - `devenv update`: exit 0. Lock: `vendomat git 4ac511b0 release` and `extra` `5b059d75 refs/tags/e2`. Main (`59614404`) is not in the lock.
  - `devenv shell` after update: `VERSION=v2 EXTRA=extra-2`.
  - `git diff` of the workspace shows only `devenv.lock` changed (8 lines).
- Log: `logs/q1-enter-v1.log`, `logs/q1-update-v2.log`, `logs/q1-lock-v1.json`, `logs/q1-lock-v2.json`.
- Proves: with one `vendomat` input, the fork enters the shell and inherits the Vendomat inputs (`extra`). `devenv update` moves the lock to the newest release commit and ignores main. The shell shows v2. An inherited input follows the new Vendomat declaration (e1 to e2) in the same update. No file edit happens.
- Finding that bites: nixpkgs is not inherited from Vendomat. The workspace root lock holds `nixpkgs github 760b8522 rolling devenv-nixpkgs`. That is the devenv default. The Vendomat pin `256551e4` appears only as a child node of the Vendomat flake (`nixpkgs_2`). This matches the patch rule "nixpkgs and devenv count as consumer inputs". A workspace with only the `vendomat` input therefore runs on the unpinned devenv default nixpkgs.
- Q1c fix: add `nixpkgs: {follows: vendomat/nixpkgs}` to the workspace devenv.yaml (static, written once). Log `logs/q1c-nixpkgs-follows.log`: exit 0, root `nixpkgs` is `['vendomat','nixpkgs']`, lock node `nixpkgs github 256551e4`, `VERSION=v2`. So a Vendomat bump of nixpkgs would reach the workspace through `devenv update`. I did not test a bump (it needs a second nixpkgs download).
- Inference: with that static follows, the Vendomat release also controls nixpkgs. Not tested with a changed nixpkgs revision.
- Unproved: a real Vendomat flake with real module sources. A cold store. A force-pushed `release` branch.
- Q1b, `git+file://<dir>?ref=release` (log `logs/q1b-gitfile.log`): the shell enters. The lock node holds no `rev` (`{'ref': 'release', 'type': 'git', 'url': 'file:///...'}`). `devenv update` shows v2. This agrees with S9: `git+file` does not pin a revision. Use `git://`, `git+ssh://`, `github:` or another form that locks a `rev`. A `git+file` lock is not a pin (see Q2b).

## Q2. Rollback by restoring the old devenv.lock

- Hypotheses: H1 the old lock gives v1 again with no other step.
- Inputs: workspace committed with lock v1, then lock v2. `release` still at v2.
- Command: `git checkout HEAD~1 -- devenv.lock`, then `devenv shell`.
- Expected: `VERSION=v1`.
- Actual: the restored file equals `logs/q1-lock-v1.json` (`cmp` silent). Shell: `VERSION=v1 EXTRA=extra-1`, exit 0. The lock stayed byte-identical after the shell. Lock nodes: `vendomat e342df4f`, `extra 858f4141 e1`.
- Log: `logs/q2-rollback.log`.
- Proves: rollback is a version-control restore of `devenv.lock`. No devenv command is needed.
- Q2b (`logs/q2b-gitfile-rollback.log`): with `git+file`, restoring the lock does not roll back. The shell showed `VERSION=v2` and rewrote the lock (`M devenv.lock`). The `git+file` form has no `rev` to restore.
- Unproved: rollback with a cold store (the old source path garbage collected). The old commit must stay fetchable from the remote. A force-pushed release branch could lose it. I did not test either.

## Q3. Update one input alone on the fork

- Exact syntax (from `devenv update --help`): `devenv update [OPTIONS] [NAME]`. One optional positional name.
- Q3c (port 34125, `logs/q3c-two-inputs.log`): workspace has `vendomat` (`?ref=release`) and `other` (`extra` repo, `?ref=stable`). Lock at release v1 and stable e1. Then release moved to v2 and stable to e2.
  - `devenv shell` (no update): `VERSION=v1 EXTRA=extra-1 OTHER=extra-1`.
  - `devenv update vendomat`: exit 0. `vendomat` moved to `89b58f8b` (v2). `other` stayed at e1. Shell: `VERSION=v2 EXTRA=extra-2 OTHER=extra-1`.
  - `devenv update other`: exit 0. `other` moved to e2. `vendomat` unchanged. Shell: `VERSION=v2 EXTRA=extra-2 OTHER=extra-2`.
- Detail: right after `devenv update vendomat`, the lock still showed `extra` at e1. The next `devenv shell` locked `extra` at e2 (the new Vendomat declaration). The full `devenv update` in Q1 moved `extra` at once. So `update <name>` leaves a new inherited declaration to the next shell entry, which writes the lock.
- Q3a (`logs/q3a-update-vendomat.log`, port 43985): `devenv update vendomat` on a v1 lock moved to v2 (`VERSION=v2 EXTRA=extra-2`).
- Q3b (`logs/q3b-update-extra.log`): `devenv update extra` (an input that only the Vendomat devenv.yaml declares) exits 0 and changes nothing (`git diff` empty, `vendomat` still v1). `devenv update nosuchinput` exits 0 and prints nothing. The fork gives no error for an unknown name.
- Proves: `devenv update <name>` works per input on the fork when the input is in the workspace devenv.yaml. It does not move other inputs.
- Not proved: updating `nixpkgs` alone (needs a download). An inherited-only input cannot be updated alone; update its parent.

## Q4. What a learner loses under H1; can the advanced door still do it?

- H1 channel gives: newest release only. H2 gives: an exact version by tag.
- Loss under H1 by default: no exact older version, no hold-back, and no choice of when a new release arrives except by running `devenv update`.
- Advanced door, test 4a (`logs/q4-pin-and-holdback.log`): edit the workspace devenv.yaml from `?ref=release` to `?ref=refs/tags/v1`.
  - A plain `devenv shell` re-locked and showed `VERSION=v1 EXTRA=extra-1` (lock `vendomat e1ac785b refs/tags/v1`). No update command was needed after the edit.
  - `devenv update vendomat` after that stayed at v1 (the tag pins).
  - Edit back to `?ref=release` plus `devenv update vendomat` gave `VERSION=v2` (`89b58f8b release`).
- Advanced door, test 4b: the lock held Vendomat v1. The workspace declared `extra` itself at tag `e1` (consumer wins by name). `devenv update vendomat` gave `VERSION=v2 EXTRA=extra-1`. Lock: `extra` stays `0e4a387d refs/tags/e1`. So a learner can hold back one inherited dependency by declaring it.
- A bad yaml edit (an input added after `imports`) failed with `Failed to parse configuration from: ./devenv.yaml`, exit 1, and the lock stayed intact.
- Proves: the advanced door (edit devenv.yaml, tag or consumer-declared input) still gives exact versions and hold-back under H1. The edit is the learner's own native edit. Vendomat needs no protocol for it.
- Inference: a learner who wants the previous release can also restore the lock (Q2), so the exact-older-version loss is small when the lock is in version control.
- Unproved: whether Vendomat commands should name the advanced door. Whether a tag-pinned workspace can return to the channel without confusion. Only the edit back was tested here.

## Q5. Does `devenv update` fail cleanly when the release input is unreachable?

- Hypotheses: it fails with a non-zero exit and keeps the lock. Observed: it fails with a message and keeps the lock, but exits 0.
- Inputs: workspace on channel, lock at v2. Rename `repos/vendomat` to `repos/vendomat.away`, so the daemon cannot serve it.
- Commands: `devenv update`, `devenv update vendomat`, `devenv shell`.
- Actual:
  - `git ls-remote`: `fatal: remote error: access denied or repository not exported: /vendomat`.
  - `devenv update` prints `✖ error: Failed to fetch git repository 'git://127.0.0.1:34125/vendomat'` and the exit status is **0**. `devenv update vendomat` does the same, exit **0**.
  - `cmp devenv.lock logs/q5-lock-before.json`: lock unchanged. `git status --short` is empty.
  - `devenv shell` with the intact lock and the source in the store still enters (`VERSION=v2 EXTRA=extra-2`, lock unchanged).
- Log: `logs/q5-unreachable.log`, `logs/q5-raw1.txt`, `logs/q5-raw2.txt`.
- Proves: a failed fetch never damages the lock. The fork reports the error on stderr only. The exit status does not show failure.
- Consequence: a Vendomat `update` wrapper cannot trust the exit status of `devenv update`. It needs a guard: compare the lock before and after, or read stderr for the error line. The plain `devenv update` for a human is safe because the lock stays.
- Unproved: a partial failure (the release input fetches, an inherited input does not). A timeout (a hung remote). Whether newer fork builds still exit 0.

## Verdict

H1 works on the pinned fork, with two conditions.

1. The input URL must lock a revision (`git://`, `git+ssh://`, `github:`). `git+file` does not lock one, so rollback fails.
2. The workspace needs a static `nixpkgs: {follows: vendomat/nixpkgs}` line. Without it, nixpkgs is the unpinned devenv default, not the Vendomat declaration.

Under H1:

- Update is `devenv update` (or `devenv update vendomat`). It moves the lock to the newest `release` commit and ignores main.
- Rollback is a version-control restore of `devenv.lock`: `git checkout <old-rev> -- devenv.lock`, then `devenv shell`.
- No edit protocol is needed for update or rollback. An edit stays only in the advanced door (exact tag, hold back one input). That edit works as plain native devenv.yaml editing.
- A Vendomat `update` command that wraps `devenv update` needs an exit-status guard (Q5).

What stays unproved: a real Vendomat flake, cold-store rollback, a force-pushed release branch, a nixpkgs bump through the channel, and the Nix branch cache window (a fresh lock for a moved branch showed the old revision once on a rebuilt fixture, cause inferred as the per-URL ref cache).

# Wrapper spikes: can Vendomat live inside devenv? (2026-10-10)

**Question.** Can every Vendomat capability be a devenv script, task, assertion, or output, with no
step before shell entry? Three spikes tested the parts that could block it. A fourth tests the
upstream route and is recorded separately when it ends.

**Tools.** `devenv 2.4.0+b904dcb (x86_64-linux)` (stock), `nix (Nix) 2.34.7`, nixpkgs `e7439b6b`.
Spike S3 also built the fork `v2.4.0-vendomat.2` with one added patch. S1 ran with every
`DEVENV_*` variable removed from the environment.

**Raw logs.** `~/.local/state/vendomat/v7-spikes/2026-10-10/` (`s1-assert-vs-tasks/`,
`s2-task-rewrites-fragment/`, `s3-fork-inheritance/`). The `.devenv` directories and the S3 build
root were removed afterwards to free disk space. The logs, fixtures, and the patch remain.

## S1: does a failing assertion block a repair task?

**Expected.** Unknown. A "sync" task can repair a stale fragment only if the stale assertion does not
stop it.

**Fixture.** An assertion fails while a file `stale` exists. The task `vendomat:sync` and the script
`vendomat-sync` delete it. A second task runs `before = [ "devenv:enterShell" ]`. The case was
repeated with the real module's lock-pin assertion (an unpinned `git+file://` node).

| Command, assertion failing | Exit | Repair ran |
| --- | --- | --- |
| `devenv tasks run vendomat:sync` | 1 | no |
| `devenv shell -- vendomat-sync` | 1 | no |
| `devenv shell -- true` | 1 | no; the `before enterShell` task did not run either |
| `devenv test` | 1 | no |
| `devenv eval shell` | 1 | no |
| `devenv build`, `devenv info`, `devenv tasks list` | 0 | not applicable |
| `devenv -O vendomat.check.enable:bool false tasks run vendomat:sync` | 0 | yes |

**Observed.** A failing assertion stops every command that evaluates `shell`, before any task runs.
`NAT-025` held. `NAT-024` held only for `devenv shell`: there a failing task warns and the shell
starts. `devenv test` and `devenv tasks run` exit 1 on a failing task. An `-O` override of an option
that gates the assertion lets the repair run.

**Inference.** A task cannot repair the fragment while the stale assertion fails. The generated
digest assertions in `.vendomat/devenv.nix` (`src/vendomat/devenvgen.py`) have no gating option, so
the `-O` route does not reach them today.

## S2: does a fragment rewrite take effect in the same shell entry?

**Expected.** Next entry only, because devenv resolves inputs before any module or task runs.

**Fixture.** The consumer imports `./.vendomat`. A task before `devenv:enterShell` rewrites
`.vendomat/devenv.yaml` to add a `path:` input and import its module, which sets `ADDED_MODULE=1`.
Command: `devenv shell --no-tui -- sh -c 'echo ADDED=$ADDED_MODULE'`.

| Entry | Fragment at start | Module active | Lock changed | Time |
| --- | --- | --- | --- | --- |
| 1 | empty; the task writes it | no | no | 0.30 s |
| 2 | full | yes | yes; node added with no `devenv update` | 3.4 s |
| 3 | full | yes | no | 0.63 s |
| removal, entry 1 | full; the task empties it | yes | no | 0.31 s |
| removal, entry 2 | empty | no | yes; node pruned | 0.49 s |

**Observed.** Each change takes effect one entry late, in both directions. The evaluation cache
invalidates correctly. A task that rewrites the fragment and exits 1 does not stop the shell:
`devenv shell -- cmd` ran the old shape and exited 0, on a pty and through a pipe. Reload in a live
shell did not pick up the change. The devenv 2.4.0 help and documentation name no hook that runs
before input resolution. `devenv direnvrc` watches `devenv.yaml` and `devenv.lock`.

**Inference.** Inside stock devenv 2.4.0 no task-only sync is correct. With the digest assertion it
deadlocks (S1). Without it, every change leaves one silently stale entry, and scripts and CI runs
exit 0 on the old shape. Something must run before `devenv shell`.

## S3: how large is a fork patch that removes the pre-resolver?

**Expected.** Unknown. The patch must make devenv read an imported source's `devenv.yaml` inputs
(`NAT-018`) and, if possible, keep `follows` deeper than one level (`NAT-036`).

**Observed.** A prototype patch `0007` changes 4 files, +526 and −76 lines; about 250 added lines are
tests and comments. It touches `devenv-core/src/config.rs`, `devenv-nix-backend/src/lib.rs` and
`lock.rs`, and `devenv/src/devenv/mod.rs`. It locks in memory, fetches each imported input, reads its
`devenv.yaml`, and repeats until no new import appears.

- `nix build .#devenv` passed. 229 core unit tests passed, 6 of them new. The Nix-backend test binary
  failed to link on boost symbols.
- On a `path:` fixture, the inherited input appeared in `devenv.lock`, a second run left the lock
  byte-identical, and `devenv update` worked. Stock devenv failed on the same fixture with
  `attribute 'extra' missing`.
- Passed: a consumer entry wins; two sources with different URLs fail and name both imports; a
  transitive import; a `tarball+file://` source; a consumer with no input-style import is unchanged.
- Not tested: GitHub or git sources, and `?dir=`.
- Deep `follows` works where every intermediate input has a URL. A pass-through follows through an
  input without a URL still cannot reach Nix; the patch now fails with a message there.

Conflict rule: an input that the consumer declares wins; `nixpkgs` and `devenv` stay the consumer's;
two sources that declare one input differently fail. Shared-child `follows` (`PRE-005`) and the tag
check stay outside the patch.

**Upstream (evidence about upstream only).** Issue cachix/devenv#2205 is open; a maintainer plans a
two-pass locking fix. PR cachix/devenv#3055, open since 2026-07-31 with no review, implements the
same loop in about 830 lines. No upstream item covers nested follows.

## Decision (owner, 2026-10-10)

1. Keep `vendomat sync` and the direnv hook as the one step before shell entry.
2. Put the pinned `vendomat` in the workspace shell and run `check` and `push` as devenv tasks
   (`VMOD-020`, `VMOD-021`). The host launcher serves `sync` only inside a workspace (`DEL-020`).
3. Test PR #3055 against these fixtures. Remove `sync`, the fragment, and the launcher's workspace
   role when input inheritance lands upstream or the fork patch proves itself.

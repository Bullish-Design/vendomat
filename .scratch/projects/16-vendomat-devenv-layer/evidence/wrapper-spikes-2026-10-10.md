# Wrapper spikes: can Vendomat live inside devenv? (2026-10-10)

**Question.** Can every Vendomat capability be a devenv script, task, assertion, or output, with no
step before shell entry? Three spikes tested the parts that could block it. A fourth (S4) tested the
upstream route.

**Tools.** `devenv 2.4.0+b904dcb (x86_64-linux)` (stock), `nix (Nix) 2.34.7`, nixpkgs `e7439b6b`.
Spike S3 also built the fork `v2.4.0-vendomat.2` with one added patch. S1 ran with every
`DEVENV_*` variable removed from the environment.

**Raw logs.** `~/.local/state/vendomat/v7-spikes/2026-10-10/` (`s1-assert-vs-tasks/`,
`s2-task-rewrites-fragment/`, `s3-fork-inheritance/`, `s4-pr3055/`). The `.devenv` directories and the S3 build
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

## S4: does upstream PR #3055 cover the same need?

**Expected.** Unknown. If #3055 covers Vendomat's need, track it instead of carrying `0007`.

**Built.** PR head `a653caf1d597104594c6eb13945e655b224048de` (base `3d4859de`, 355 commits behind
v2.4.0; it builds as devenv 2.2.1). On the fork and on stock v2.4.0, the PR met two conflicts
(`devenv/src/main.rs` and one docs file); the six fork patches caused neither. Four trees were built:
fork plus PR, the PR head, stock v2.4.0 plus PR, and that tree plus a one-line fix. Fork plus `0007`
was rebuilt so each case ran on both.

| Case | `0007` | #3055 on v2.4.0 |
| --- | --- | --- |
| Inherit one input; lock stable on a second run and after `devenv update` | pass | pass |
| Consumer entry wins | pass | pass |
| Two sources declare one input differently | error that names both imports | no error; the later import wins |
| Transitive import | pass | pass |
| `tarball+file://` source | pass | fails: "Failed to canonicalize source for imported input"; passes with the fix |
| No input-style import | unchanged | unchanged |
| `git daemon` source at `ref=refs/tags/v1` | pass; lock keeps the tag ref and rev | fails as above; with the fix, the same lock shape |
| Source declares `path:../extra` | error | resolves inside the source |
| Shared child without `follows` | duplicate nodes | duplicate nodes |
| Inherited nested `follows` `a.b.c -> c` | honored | dropped without a message |
| Consumer-declared nested `follows` | honored | dropped without a message |
| Source declares `nixpkgs` and `devenv`; consumer does not | consumer defaults stay | the source replaces both |

**Observed.** On v2.4.0 the PR fails for every non-path source. Replacing `require_string` with
`realise_string(&value, false)` in `input_paths_from_json` (`lock.rs`) fixed the tarball and git cases.
**Inference:** Nix 2.35 gives a lazy store path that does not exist on disk until it is realised.
The PR merges the whole imported `devenv.yaml`, not only `inputs`.

**Inference.** #3055 covers the inheritance core but not Vendomat's conflict error, nested `follows`,
or default pins. It is not mergeable today. Review notes, not posted: realise before `canonicalize`
and test a non-path source on Nix 2.35; rebase onto v2.4.0; error on conflicting inputs across
imports; warn on dropped nested `follows`; reject or document relative `path:` inputs in sources.

## Decision (owner, 2026-10-10)

1. Keep `vendomat sync` and the direnv hook as the one step before shell entry.
2. Put the pinned `vendomat` in the workspace shell and run `check` and `push` as devenv tasks
   (`VMOD-020`, `VMOD-021`). The host launcher serves `sync` only inside a workspace (`DEL-020`).
3. Test PR #3055 against these fixtures. Remove `sync`, the fragment, and the launcher's workspace
   role when input inheritance lands upstream or the fork patch proves itself.

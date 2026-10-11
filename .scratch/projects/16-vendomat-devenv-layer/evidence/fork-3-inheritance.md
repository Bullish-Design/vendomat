# Fork `v2.4.0-vendomat.3`: input inheritance and a cold-store fix (2026-10-11)

**Goal.** Carry input inheritance in the fork, so `vendomat sync` can later go away
([decision](./wrapper-spikes-2026-10-10.md)). Prove it on fixtures and on the real collection.

## Inputs

| Item | Value |
| --- | --- |
| Host | `server`, x86_64-linux; host Nix 2.34.7 |
| Upstream | `cachix/devenv` `v2.4.0`, `b904dcb51fe48c30db250038241507f60752f222` |
| Series | patches 0001 to 0006 (unchanged, `.2` = `e2acb5b0`), **0007** input inheritance, **0008** cold-store fix |
| Fork commit | `fb5d382b822f6ecf58365a77f2f872ba6f7ce79d`, tag `v2.4.0-vendomat.3` (local only) |
| Patched CLI | `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0` |
| Stock CLI | `devenv 2.4.0+b904dcb`, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0` |
| Fork `.2` CLI | `devenv 2.4.0+e2acb5b`, `/nix/store/3mfmgg65mf08h7rhwd7w4f2vvcr9ia9i-devenv-wrapped-2.4.0` |
| Raw logs | `~/.local/state/vendomat/v7/2026-10-11/` |

Command: `python3 -I devenv-dist/materialize DEST --source <local upstream mirror> --verify`
exited 0 and matched `devenv-dist/RESULT`. `nix build .#devenv` in the materialized tree built the
patched CLI.

## Patch 0007 changes since spike S3

The spike prototype inherited a source's inputs, but not its modules. A fixture case put the module
in `lib-c`, behind `lib-b`'s own `imports: [lib-c/devenv]`. The shell entered, but `EXTRA_PATH` was
unset: `lib-c` and `extra` were in the lock, and the `lib-c` module was not imported. Today's
pre-resolver (`src/vendomat/devenvgen.py`) does import nested modules, so this was a gap.

The patch now returns the imports that each source lists, and devenv imports their modules after
the consumer's own. A local import inside a source (`./sub` in `lib-b/devenv`) becomes
`lib-b/devenv/sub`. A local import that leaves its input fails. The `Upstream:` line now names
`cachix/devenv PR #3055`, as the series convention requires.

## Unit tests

`devenv-core` with `runTests = true` and `git` in `testInputs`: 230 passed, 0 failed, 7 of them
inheritance tests (log `tests-core-3b.log`). The first run without `git` failed 11 existing tests
with "Failed to git init: NotFound"; that is the build sandbox, not the patch. These tests ran on
the tree with 0007; patch 0008 changes only a bootstrap Nix file.

## Fixture: `devenv-dist/fixtures/inherit-fixture`

`python3 -I devenv-dist/fixtures/inherit-fixture PATCHED STOCK WORKDIR LOGDIR` on the final CLI:
9 of 9 cases passed (`inherit-fixture-final/logs/results.json`).

| Case | Result |
| --- | --- |
| Inherit one input; a second run keeps the lock bytes; `devenv update` works | pass |
| Stock devenv on the same consumer fails (`extra` missing) | pass |
| A consumer entry wins | pass |
| Two sources declare one input differently: the error names both imports | pass |
| A transitive import inherits its inputs and imports its module | pass |
| A local import inside a source is imported and inherits | pass |
| A local import that leaves its input fails | pass |
| A tag-pinned `git://` source with `dir=` (loopback `git daemon`): the lock keeps the tag and a 40-hex revision | pass |
| A consumer with no input-style import enters | pass |

## Live proof on the collection

Consumer: `~/.local/state/vendomat/v7/2026-10-11/demo-inherit/consumer/`. Its `devenv.yaml` declares
`nixpkgs` (`e7439b6b`), `devenv` (`git://server/devenv?ref=refs/tags/v2.4.0-vendomat.2&dir=src/modules`),
and the two module sources `greeting` and `marker` from `git://server/vendomat-demo` at `v0.2.0`. It
imports `greeting/devenv` and `marker/devenv`. It does **not** declare `greeting-defaults` or
`marker-defaults`; the sources declare them in their own `devenv.yaml`. Command:
`devenv --no-eval-cache shell -- sh -c 'echo "G=$DEMO_GREETING"; echo "M=$DEMO_MARKER"'`.

Before each cold run, the consumer's `.devenv` and `devenv.lock` were removed, and
`nix-store --delete` removed the two collection source paths (`41qb8ijp…-source`, the demo
repository at `v0.2.0`, and `6v7hc265…-source`, the fork modules).

| CLI | Consumer | Store | Result |
| --- | --- | --- | --- |
| stock | inheritance (defaults not declared) | cold | exit 1, `attribute 'greeting-defaults' missing` |
| stock | control (every input declared) | cold | exit 0, `Hello from Vendomat defaults` |
| fork `.2` | control | cold | exit 1, `path '/nix/store/41qb…-source' is required, but there is no substituter that can build it`; a retry failed the same way |
| `.3` without 0008 | control and inheritance | cold | exit 1, the same error |
| `.3` with 0008 | inheritance | cold, then warm | exit 0 twice: `G=Hello from Vendomat defaults`, `M=demo-default`; the same lock bytes (`30b5db70…`) both times |

The lock holds `greeting`, `greeting-defaults`, `marker`, and `marker-defaults`, each with
`ref=refs/tags/v0.2.0`, its `dir`, and revision `487012f1007b…`.

## The cold-store defect and patch 0008

**Observed.** Fork `.2`, the tag that the live release uses, fails the first shell entry of a workspace
whose git source is not in the store. Stock devenv does not. The failure is at the `storedSource`
branch that patch 0003 (PR #3244) adds to `resolve-lock.nix`: `builtins.pathExists` on the store path
derived from `narHash` was true, and `builtins.appendContext` then required a path that the store
did not hold.

**Inference.** The in-process locker makes the fetched source visible at that path without
registering it. `vendomat sync` hid the defect, because it prefetches each source into the store
before the shell runs. Without the pre-resolver, every cold first entry would fail.

**Fix.** Patch 0008 produces the path with `builtins.path { path; name = "source"; sha256 = narHash; }`.
It copies an unregistered tree into the store with the expected hash, and returns a registered path
unchanged. It is fork-only; report it on PR #3244.

## Publication

Date: 2026-10-11, on `server`. Raw log: `~/.local/state/vendomat/v7/2026-10-11/publish-3.log`.

Method. The collection is the local repository `/home/andrew/vendor/devenv`, the same remote that
published `.2` (`collection`). The `.3` materialized repo is a plain git repo, so a git push sent
only the tag.

| Step | Command | Expected | Actual |
| --- | --- | --- | --- |
| Check | `git -C ~/.local/state/vendomat/v7/2026-10-11/devenv-v2.4.0-vendomat.3 rev-parse HEAD v2.4.0-vendomat.3^{commit} HEAD^` | `fb5d382b…`, `fb5d382b…`, parent `1d431d51…` | as expected; `git status` clean |
| Push | `git -C <that repo> push /home/andrew/vendor/devenv refs/tags/v2.4.0-vendomat.3:refs/tags/v2.4.0-vendomat.3` | one new tag, no other ref changes | `* [new tag] v2.4.0-vendomat.3`; exit 0 |
| Read side | `git ls-remote git://server/devenv` | tag `.3` at `fb5d382b…`; `.2` unchanged | `.3` at `fb5d382b822f6ecf58365a77f2f872ba6f7ce79d`; `.2` at `e2acb5b0…` |
| Prefetch | `nix flake prefetch --json 'git://server/devenv?ref=refs/tags/v2.4.0-vendomat.3&dir=src/modules'` | rev `fb5d382b…` | `rev` `fb5d382b822f6ecf58365a77f2f872ba6f7ce79d`, `dir` `src/modules`, `revCount` 7377 |
| Build | `nix build --no-link --print-out-paths 'git://server/devenv?ref=refs/tags/v2.4.0-vendomat.3#devenv' --accept-flake-config` | the existing patched CLI path | `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0` |

The push hook of the collection printed `working tree now shows v2.4.0-vendomat.3`. Nothing went to
GitHub. Live pins in templates, tests, and `CONCEPT-V6.md` moved to `.3` after this publication.

## Not proved

- The tag is not on GitHub. The owner did not ask for it there.
- No GitHub or GitLab source was tested with inheritance.
- A nested `follows` through an input that has no URL still cannot reach Nix; the patch fails with a
  message there (spike S3).
- Shared-child `follows` (`PRE-005`) stays a Vendomat job; the lock can hold duplicate nodes.

## Fixture: `devenv-dist/fixtures/dist-fixture`

The fixture now reads the fork tag from `devenv-dist/UPSTREAM`. On the final CLI it reported
10 pass, 0 fail (`dist-fixture.out`): the fork tag is HEAD (`fb5d382b`); `DVN-001`, `DVN-002` (three
cases), `DVN-004` (git daemon shape, the revision pinned), `DVN-005`; and `DVN-008`: with the source
in the store and the daemon stopped, the patched shell entered offline on the same source path
(`1pmb65l4…-source`), and stock devenv failed at `resolve-lock.nix`. Patch 0008 keeps patch 0003's
offline reuse.

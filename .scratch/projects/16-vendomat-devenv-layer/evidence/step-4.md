# Step 4 — the command and the launcher

**Date:** 2026-10-09. **Gate:** G4. **Status:** see the table. Real Attic push (`VMOD-007`) is G5.

## What was built

| Part | File | Interface |
| --- | --- | --- |
| Launcher | `launcher/vendomat`, `packages.<system>.launcher` | Runs the workspace's pinned build by NAR hash; the host release elsewhere |
| `path` | `src/vendomat/lockpath.py` | `vendomat path <name>` from `devenv.lock`, no network (`CLI-018`) |
| `check` | `src/vendomat/check.py` | Pins, CLI/module revision, fragment, lock vs fragment (`CLI-019`) |
| `push` | `src/vendomat/push.py` | `check`, then `devenv build`, then `attic push <cache> --stdin` (`VMOD-006`) |
| `bump` | `src/vendomat/bump.py` | Dry run default; `--apply` edits two `ref` values, syncs, runs each gate (`CLI-020`, `REG-025`) |
| `machine install` | `src/vendomat/machine.py` | Fresh-only second guard; one command: `devenv machines install <host> --phases disko,install` |
| Preflight program | `preflight/vendomat-preflight`, `nix/devenv-module/preflight.nix` | The `vendomat.preflight/v1` program that the patched CLI runs on the target |
| Direnv | `direnv/vendomat.sh` | `use_vendomat` |

## Interface that Step 1 fixed (read from the patched devenv)

- Nix: `machines.<host>.vendomat.mode` and `machines.<host>.vendomat.preflight.{program,ttlSeconds}`.
  The module writes them only when the devenv modules define them (patched modules).
- The CLI refuses `adopt-existing` before any contact, and a `null` mode. A fresh host needs the
  preflight program for `disko` or `install`.

## Runs

| Run | Command | Result |
| --- | --- | --- |
| C1 | `testee verify --full`, run `20261010T025707Z-2818879e52a6`, exit 0 | PASS |
| C2 | `testee check e2e`, run `20261010T024934Z-cf03a75c29f8`, exit 0 | PASS. Includes the launcher story on real Nix |
| C3 | `nix build .#packages.x86_64-linux.launcher .#packages.x86_64-linux.vendomat` | PASS. `vendomat --version` printed `vendomat 0.6.0` |

Raw logs: `~/.local/state/vendomat/v6/2026-10-09/04-cli/`.

## Observations

1. **Launcher, real Nix.** `tests/test_launcher_e2e.py` copies this tree twice, as tags `v0.6.0`
   and `v0.6.1`, and serves them over `git://` on loopback. It builds the launcher, then:
   - Outside a workspace the host release ran, with an empty stderr.
   - A workspace with no lock was bootstrapped by the host release, and stderr said `bootstrap`.
   - After `sync`, two workspaces printed `vendomat 0.6.0` and `vendomat 0.6.1`.
   - With the daemon stopped and the launcher cache deleted, both still printed their own version:
     the build was found in the store by the NAR hash of its source.
2. **Fallback cases** (`tests/test_launcher.py`, stubbed Nix): a lock with no `vendomat` node, a
   missing pinned source (it is fetched from the lock's own reference), a missing and unfetchable
   source (the host release repairs, and stderr says so), `--root`, and `VENDOMAT_USE_HOST=1`.
3. **`check`** names a branch pin, a transitive unpinned node, a git node without a revision, a stale
   registry, a hand edit, an input missing from the lock, a CLI built from another revision than
   the locked modules, and a `devenv` input without `dir=src/modules`.
4. **`push`** with a stand-in `devenv` and `attic` sends exactly the built paths; a failed check, a
   failed build, and a failed push each push nothing or report the failure. The real Attic push is G5.
5. **`bump`** dry run changed no byte. `--apply` on a three-workspace fleet moved each pin and
   reported one failing gate as `1 of 3 workspace(s) incomplete: beta`. It never says `all`.
6. **`machine install`** runs one command. An adopted host, an unknown host, a missing facter report,
   and a failed check each stop before any install call.

## Findings

- `vendomat bump` writes the registry, which `REG-009` forbade. `REG-025` supersedes `REG-009`.
- A `git+file://` input does not lock a revision in devenv 2.4.0 (a Step 2 finding). The launcher
  needs a `git://` pin for the NAR-hash route. The fixtures use `git daemon`.
- The Testee shell lacked `jq`. The launcher tests skipped silently until `devenv.nix` added it.
  A silent skip is a hazard: a test that needs a tool should fail in the full gate.

## Not covered

- The preflight program (`preflight/vendomat-preflight`) is built and its syntax is checked. Its
  checks run against real block devices only in the Step 7 VM.
- The module e2e uses stock devenv, so `machines.<host>.vendomat.*` is not written there. The
  patched modules are exercised in the Step 6 workspace.
- A real Attic push and the cold substitution are G5.

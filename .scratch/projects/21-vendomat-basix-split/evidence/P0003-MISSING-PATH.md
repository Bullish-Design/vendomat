# P0003: missing store path in the offline entry (patch 0003)

Date: 2026-10-15. Ledger: `VMT-184`. Logs: `~/.local/state/vendomat/p21/2026-10-15/p0003/`. Fixtures:
`/mnt/shared/vendomat-p21/p0003/` (r1 to r4, `scripts/`).

## The defect (observed)

The vendomat-demo smoke run `20261015T203154Z` failed to enter its shell: `path '/nix/store/41qb8ij...-source'
is required, but there is no substituter that can build it`, at `resolve-lock.nix:120` (the `appendContext` in
`storedSource`), while realising the context of `import (outPath + "/flake.nix")`. The owner had freed disk space.

## Reproduction (observed)

Fixture r4: one local `git daemon` repository with `a/` and `b/` (each a `flake.nix` and `data.txt`), tag `v1`.
The workspace has two inputs `git+git://127.0.0.1:PORT/extra.git?ref=refs/tags/v1&dir=a` and `...&dir=b`. Both
lock the same `narHash`. The source path was not in the store.

| Case | Binary | Result |
| --- | --- | --- |
| first entry, eval cache on | host S2 binary `0ca6h7n4...` | FAIL, the error above (`r4-enter1.log`) |
| `--no-eval-cache` | host S2 binary | FAIL (`r4-enter2-patched-nocache.log`) |
| `--refresh-eval-cache` | host S2 binary | FAIL (`r4-enter3-patched-refresh.log`) |
| `--no-eval-cache` | stock `5sbcspxm...` | enters (`r4-enter4-stock.log`) |
| one input only (`ws-single`), source missing | host S2 binary | enters (`r4-single-patched-missing*.log`) |
| two inputs, plain Nix 2.35.2 on `resolve-lock.nix` | n/a | FAIL, same error (`scripts/harness.sh`) |
| remote down, empty fetcher cache, source missing | harness, old and fixed file | `Failed to fetch git repository` (`r4-harness-missing-remote-down.log`) |

Fixtures r1 to r3 (one input, `flake: false`, source read or imported) did not fail. The source was rooted or had
referrers (r1), or Nix never made it real (r2, r3). A path that devenv's own shell derivation refers to cannot be
deleted alone (`Cannot delete path ... since it is still alive`), so r4 reads files and puts no source path in the
shell. Only the one source path was deleted (`nix store delete`, unrooted, no referrers).

## Cause (proved)

The eval cache is not the cause. The failure occurs with the cache on, off, and refreshed, and on a first entry.

The cause is `builtins.pathExists storedPath`. With Nix 2.35 (devenv 2.4.0 links 2.35), `fetchTree` of a locked git
input is lazy. It mounts the source at its store path in the evaluator and does not write it to the store. After
the first input fetches, `pathExists` is true for that path for every later input with the same `narHash`, although
the store lacks it. `isStored` is then true, `storedSource` adds a hard path context, and the first `import`
realises the context. Nothing can build the path, so the entry fails.

Proof (`r4-proof-nix235.log`, Nix 2.35.2, path absent on disk): `pathExists` before `fetchTree` is false, after
`fetchTree` is true, and the path is still absent on disk. Stock devenv has no such context, so it reads the mounted
source and enters. The single-input case enters because nothing mounts the path first.

A real eval-cache effect did not appear in any run.

## Fix

`0003.patch` returns the stored source through `builtins.path { path = storedPath; name = "source"; sha256 =
locked.narHash; }` instead of `builtins.appendContext`. Nix keeps a path that the store holds (offline reuse) and
copies the mounted source into the store otherwise (fallback). The patch sha256 is
`aa7fb1e59e36cbdbde74bed9c1d941ff7febebbc1cf3add479a4d2c7169c550b`. It applies to the nixpkgs source with the
`CHANGELOG.md` hunk filtered, as before. Harness checks with the fixed file (Nix 2.35.2): source missing and remote
up enters; source present, remote down, empty cache enters (offline reuse); source missing, remote down fails with
`Failed to fetch git repository` (as stock).

## New binary

- Store path: `/nix/store/s3x37wa0x8y3c9wkkzjbgpk44z2sgbx5-devenv-2.4.0`
- NAR hash: `sha256-ms5am2ZD9h8gLF87qDNIhSiDWfd1Te9YOB+8MbmLpSs=`
- GC root: `~/.local/state/vendomat/roots/devenv-p0003-build`. The root `devenv-s2-build` stays (the host still
  runs that binary).
- Build: `nix build .#devenv`, log `nix-build.log`.

## Runs

- New binary on fixture r4, source deleted each time, remote up: cache on, `--no-eval-cache`, and
  `--refresh-eval-cache` all enter (`r4-new-binary*.log`).
- `PATH=<new binary>/bin:$PATH testee verify opt:binary-e2e`: PASS, run `20261015T223008Z-8266b625fca7`, 4 tests
  (B2, B2b, B5, B6), 192 s. Fixture logs: `.../p21/2026-10-15/s2/binary-e2e/20261015T223029Z/` (link
  `binary-e2e-run`).
- The new test `test_b2b_entry_falls_back_to_a_fetch_when_the_store_path_is_gone` covers stock and patched with the
  source deleted (cache on, off, refreshed) and the remote-down failure. Its optional control
  `VENDOMAT_BINARY_E2E_PREVIOUS` did not reach the Testee worker, so it did not run in that run. The old binary
  failure is the hand run above.
- `testee verify`: GREEN 4/4, run `20261015T223519Z-189644c282de`, tree `e3bbb52ca2`.

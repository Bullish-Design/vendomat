# Step 2 — `vendomat sync` for devenv workspaces

**Date:** 2026-10-09. **Gate:** G2. **Status:** PASS for the sync interface on stock devenv 2.4.0.
The patched CLI does not change `sync`; Step 1 owns that build.

## Pins and tools

| Tool | Version |
| --- | --- |
| Nix | 2.34.7 (host) |
| devenv | 2.4.0+b904dcb (host, stock) |
| nixpkgs default | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| Git daemon | host Git 2.55.0, `git://127.0.0.1:<port>` |
| Testee | 0.5.0 |

## What was built

`src/vendomat/` gains `yamlsubset.py` (a `devenv.yaml` subset reader), `nixio.py` (the resolver
and lock comparison), `devenvgen.py` (the fragment generator), and `defaults.py` (the release
nixpkgs). `registry.py` reads `[imports]`, `[targets]`, and `dir`. `cli.py` runs the devenv target
beside the flake target. `direnv/vendomat.sh` holds `use_vendomat`. The V5 flake target and its
digest are unchanged (`tests/test_registry_v6.py::test_the_flake_digest_ignores_imports_and_targets`).

## Runs

| Run | Command | Expected | Actual |
| --- | --- | --- | --- |
| E1 | `testee check e2e`, runs `20261010T021235Z-496f611f02bf` and, after a typing fix, `20261010T021558Z-1c5f4945b242` (exit 0) | `tests/test_devenv_sync_e2e.py::test_the_whole_sync_story` and the migrated V5 fixtures pass | PASS. 239 tests passed |
| E2 | `testee verify --full`, run `20261010T021536Z-19d0b8489dfa` (exit 0, full gate) | pass | PASS: pytest, ruff, ruff-format, ty |

Raw logs: `~/.local/state/vendomat/v6/2026-10-09/02-sync/testee-e2e-run*.log` and
`~/.local/state/vendomat/v6/fixture-logs/20261010T021252Z/`.

### Observations from the story fixture

1. A new workspace with no lock: `sync` wrote the fragment and `devenv update` created the lock. All
   five source inputs (`lib-a`, `lib-b`, `lib-c`, `leaf`, `shared`) have a 40-hex `locked.rev`.
2. `shared` is declared as an input by four flakes. The lock holds one node for it.
3. `devenv info` passed. `devenv shell -- true` was the only entry that evaluates assertions
   (`NAT-025`: `info`, `eval`, and `build` skip them).
4. With the source daemon stopped, an unchanged `sync` took 0.142 s, printed `unchanged .vendomat/`,
   and left every file's modification time alone.
5. A registry edit without a sync stopped `devenv shell` with `STALE ... vendomat.toml`.
6. A hand edit of the fragment stopped it with `edited by hand`. `sync` repaired it.
7. A registry that added an unreachable input made `devenv update ghost` exit 1. `sync` named
   `ghost`, restored the prior fragment and lock, and exited 2.

### Inference and decisions

- **PRE-011 stale case.** I swapped two fragments of equal size and equal modification time with the
  evaluation cache on and `.devenv` kept. The new value showed at once. The agent L result did not
  reproduce, so the cause stays unproven. `sync` replaces files with a later time and clears
  `.devenv/nix-eval-cache*` only when the fragment content changes.
- **`git+file://` inputs do not lock in devenv 2.4.0.** The lock holds `locked = original` with no
  revision. A real `git://` route locks to a 40-hex revision. The fixture serves its repositories
  with `git daemon`, which is the production route (`NAT-020`).
- **A failed update rolls the fragment back too.** The prior digest then names the prior registry
  hash, so the shell reports the registry change as stale, and the next `sync` retries.
- `require_version` is not written into the fragment yet. It waits for the patched CLI version
  string (Step 1) and `vendomat check` (Step 4).

## Not covered by this gate

- Direnv is not run. `tests/test_use_vendomat.py` drives the function with stubs.
- The time budget of `PRE-010` on a large fleet is not measured.
- Offline shell entry with the collection down is Step 1 (`DVN-008`).

# Live cache check, 2026-10-10

Requirement: `CACHE-012`. Check: `testee check live-cache` and `testee check live-cache-load`.
Code: `tests/livecache.py`; fake-world tests: `tests/test_live_cache.py`. Both checks are opt-in.

## What the check does

1. Read the push and pull credentials from `~/.config/attic/config.toml` (`vendomat-server`,
   `vendomat-pull-check`). A token never reaches an argument list, a log, or the report.
2. Add one unique file of random bytes to the store, so every run makes a real upload.
3. Build the Vendomat package from this checkout as the second root.
4. Push both roots with `attic push -j 1`. Retry up to 3 attempts, 20 s apart.
5. Ask the cache for each closure path with the pull credential (`narinfo`). A 404 is absent. A 5xx or
   a timeout is an error, and it fails the attempt. A 401 or 403 is a blocker.
6. `nix copy` both roots into an empty root store with signature checking on and no other
   substituter. Compare the unique file by SHA-256.
7. Write `report.json` under `~/.local/state/vendomat/v6/live-cache/<UTC time>/`.

`live-cache` uses a 1 MiB unique object. `live-cache-load` uses 64 MiB (about 1000 chunks at the
server's 64 KiB average). The Testee shell drops host variables, so the size is set in the argv.

## Inputs

Host `server`, x86_64-linux; Nix 2.34.7; attic-client 0.1.0
(`/nix/store/9r5fng0g7gkaq8ym3v4vhdyysvhywhx2-attic-0-unstable-2026-06-26`); Testee 0.5.1; cache
`vendomat` at `http://127.0.0.1:8089/vendomat`, private. Server config is the same as in
[live-release-2026-10-10.md](live-release-2026-10-10.md): SQLite on `/mnt/wd_green1`, 64 KiB chunks.

## Runs

Run directories are under `~/.local/state/vendomat/v6/live-cache/`.

| Run (UTC) | Check | Result | Push attempts | Notes |
| --- | --- | --- | --- | --- |
| `20261010T204149Z` | live-cache | blocked | 0 | Check bug: `attic cache info` prints to stderr. Fixed |
| `20261010T204229Z` | live-cache | pass | 1 (6.4 s) | 36 closure paths, 2 new |
| `20261010T204308Z` | live-cache | pass | 1 (7.4 s) | |
| `20261010T204334Z` | live-cache | pass | 1 (7.3 s) | |
| `20261010T204359Z` | live-cache | pass | 1 (7.3 s) | Meant as a load run; the size variable did not reach the check, so it is a 1 MiB run |
| `20261010T204456Z` | live-cache-load | blocked | n/a | Check bug: a `narinfo` HTTP 500 raised a blocker. Fixed: a 5xx now fails the attempt |
| `20261010T205004Z` | live-cache-load | pass | 2 (239 s, 0.3 s) | Attempt 1 exit 0, then 1 `narinfo` HTTP 500 |
| `20261010T205442Z` | live-cache-load | pass | 2 (228 s, 2.8 s) | Attempt 1 exit 1 with 1 upload error; attempt 2 uploaded the rest |

`testee verify --full` passed on the same source before the last two runs (run
`20261010T204941Z-57adeac8b2d9`).

## Observations

- The cold substitution passed in every complete run: signature checking on, no other
  substituter, content equal.
- A 1 MiB push never failed. A 64 MiB push took about 230 s (about 280 KiB/s) and needed a second
  attempt in both complete runs.
- At 20:49:00 UTC, `atticd` logged `Failed to acquire connection from pool: Connection pool timed
  out` on `GET /vendomat/<hash>.narinfo` (`get_store_path_info`, latency 30004 ms, HTTP 500). That
  is a read request, not an upload. The pool was starved while a large push ran.
- The default workload (1 MiB) does not reproduce the timeouts. The load workload does.

## Limits

This is one host and one client. It proves push and cold pull through the pull credential on
`server`. It does not prove another host, a remote substitution, or a push that needs no retry.
The cause of the pool timeouts is not established; the investigation is a separate task.
Every run leaves its unique object in the cache. The cache has no retention period.

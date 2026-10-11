# Experiment E: Attic control on the HDD

**Date:** 2026-10-11, 08:20-08:27 EDT. Method, versions, and limits: [README.md](README.md).
Raw: `~/.local/state/vendomat/v6/single-disk-cache/runs/E/`.

## Setup

- Server: the patched `atticd` that production runs (`yp3z60h1…`), monolithic mode, on
  `127.0.0.1:18093`. `--mode check-config` passed first.
- TOML: SQLite and local storage under `<scratch>/attic/` on the HDD; `acquire-timeout = "1 minute"`,
  `max-connections = 4`, `busy-timeout = "30 seconds"`; chunks 16/64/256 KiB, threshold 65536. These
  equal production except the paths.
- A fresh database per run. A push token (`--push sdc --pull sdc --create-cache sdc`) and a pull-only
  token, both from `atticadm make-token` with a throwaway RS256 key.
- Push: `attic push -j 1 --ignore-upstream-cache-filter t:sdc <paths>`. The filter was off so the
  cache held the whole closure, like B. Production keeps the filter (`CACHE-009`).
- Cold: `nix copy --from http://127.0.0.1:18093/sdc --to local?root=<scratch>/cold-copy --option
  netrc-file <pull-only netrc> --option trusted-public-keys <cache key> --option substituters '' …`.

The owner's placement rule put this arm on the HDD, so it repeats today's placement, not the NVMe.

## Expected

As B, plus: a push with the pull-only token is refused.

## Results (three runs)

| Measure | Median (min-max) |
| --- | --- |
| Unique 64 MiB push | 1.567 s (1.453-1.648) |
| `sync -f` on the HDD after that push | 1.618 s (1.562-1.679) |
| NAR hash: source = cache narinfo | equal, 3 of 3 |
| Vendomat closure push (35 paths) | 12.440 s (10.949-12.450) |
| Closure probes | 35 of 35 HTTP 200; Vendomat NAR hash equal to the host |
| Cache bytes added by the closure | 158,055,658 (157,728,496-158,238,898), 66 % of the NAR bytes |
| Four concurrent 64 MiB pushes | exits 0,0,0,0; wall 12.512 s (11.986-12.809) |
| `sync -f` after the concurrent pushes | 7.994 s (7.982-8.189) |
| Seed probes during concurrent pushes | 24-26 per run, all HTTP 200, max 0.033 s (0.032-0.095) |
| Cold copy | exit 0, 2.507 s (2.426-2.658); file bytes equal |
| Never-existing path | HTTP 404; `nix path-info --store` exit 1, `is not valid` |
| Host-only path, never pushed | HTTP 404 |
| Push with the pull-only token | exit 1, `AccessError: … User does not have permission to complete this action.` (3 of 3) |
| Kill at 0.49, 0.99, 1.48 s | probe 404 after each kill; retry exit 0; probe 200 |
| Retry time after a kill | 4.782 s (3.843-5.006), against 1.567 s for a clean push |
| Bytes used at the end | 933,199,135 (927,751,024-933,467,018) |

The payload at the end was eight 64 MiB NARs plus the closure, about 695 MB. The measured use was
233-238 MB more. That excess holds the database, chunk overhead, and any chunks from killed uploads.
This run did not separate them.

The server log had seven lines per run: start, migrations, listen, and SIGTERM. It logged no request.

## Observations

- On a fresh database, with no other load, no request waited near the pool timeout. Every probe stayed
  below 0.1 s while four pushes ran.
- A retry after a kill took about three times as long as a clean push.
- Attic stored the closure in 66 % of its NAR bytes; the `file://` cache with zstd used 37 %.

## Inference

- These numbers are close to the earlier four-connection throwaway result (1.5-1.6 s). They do not
  explain the original 228-239 s production pushes. The production database is older and larger.
  The cause of the original failure stays **not established**.
- The control shows that Attic itself works on this host for this workload. The reasons to remove it
  are the database, the patch it needs (`CACHE-013`), and the failure that is still unexplained, not a
  failure in this run.

# Experiment B: static `file://` cache served by Caddy

**Date:** 2026-10-11, 08:18-08:31 EDT. Method, versions, and limits: [README.md](README.md).
Raw: `~/.local/state/vendomat/v6/single-disk-cache/runs/B/` and `runs/B2/`.

## Setup

- Cache directory on the HDD: `<scratch>/cache`. Throwaway key `sdc-B-1` from `nix key generate-secret`.
- Server: `caddy run` with a Caddyfile of `root * <cache>` and `file_server` on `127.0.0.1:18091`.
  Caddy stands in for the Tailscale Serve file route, which was not used (it would change the
  production node's Serve configuration).
- **B (local push):** `nix copy --to 'file://<cache>?compression=zstd&secret-key=<key>' <paths>` from
  the host store.
- **B2 (remote push):** an SSH key whose `authorized_keys` line is
  `command="<nix>/bin/nix-daemon --stdio --store 'file://<cache>?compression=zstd&secret-key=<key>'",restrict <key>`.
  The client runs `nix copy --from local?root=/dev/shm/<src> --to ssh-ng://andrew@127.0.0.1` with
  `NIX_SSHOPTS` naming the port, the key, and a pinned `known_hosts`.
- Cold: `nix copy --from http://127.0.0.1:18091 --to local?root=<scratch>/cold-copy --option
  trusted-public-keys <sdc-B-1 public key> --option substituters '' <u64 path> <vendomat path>`.

## Expected

Every push exits 0. Every pushed path answers HTTP 200 with a narinfo signed by `sdc-B-1`. The cold
copy passes with only that key trusted. A path that was never pushed answers 404. A killed push
publishes nothing, and a retry succeeds.

## Results (B: three runs; B2: one run)

| Measure | B, median (min-max) | B2 |
| --- | --- | --- |
| Unique 64 MiB push | 0.520 s (0.472-0.582) | 0.913 s |
| `sync -f` on the HDD after that push | 0.919 s (0.916-0.922) | 0.821 s |
| NAR hash: source = cache narinfo | equal, 3 of 3 | equal |
| Cache signatures on the narinfo | `sdc-B-1` (plus the source signatures for upstream paths) | `sdc-B-1` |
| Vendomat closure push (35 paths) | 2.038 s (2.031-2.682) | not run |
| Closure probes | 35 of 35 HTTP 200 | — |
| Vendomat NAR hash: host = cache | `sha256-u524vCPHaEtBuByq0qRPyF9j9TteW0Wla75fGWRXkao=` both | — |
| Cache bytes added by the closure | 88,244,801 for 239,940,216 NAR bytes (37 %) | — |
| Four concurrent 64 MiB pushes | exits 0,0,0,0; wall 0.755 s (0.733-0.768) | exits 0,0,0,0; 1.464 s |
| `sync -f` after the concurrent pushes | 4.357 s (4.339-4.375) | 3.855 s |
| Seed probes during concurrent pushes | 2 per run, all 200, max 0.002 s | 3, all 200, max 0.001 s |
| Cold copy (closure and 64 MiB file) | exit 0, 1.922 s (1.787-2.112); file bytes equal | exit 0 (five 64 MiB paths), 1.316 s; equal |
| Never-existing path | HTTP 404; `nix path-info --store` exit 1, `path '…' is not valid` | — |
| Host-only path, never pushed | HTTP 404 | — |
| Kill at 0.15, 0.28, 0.42 s (B) and 0.27, 0.55, 0.82 s (B2) | killed while running each time; probe 404; retry exit 0 in 0.50-0.87 s; probe 200; NAR size 67,108,976 | same |
| Partial files after a kill | one `*.nar.zst.tmp.4075862.1` after the 0.42 s kill; no orphan NAR in any trial | none |
| Push with an SSH key not in `authorized_keys` | — | exit 1, `failed to start SSH connection`; probe 404 |
| Client asks `?remote-store=file://<other dir>` | — | exit 0; the other directory was not created; the path landed in the forced cache |

Bytes used: 490,911,664 after runs 1 and 2. That is exactly six 64 MiB NARs plus the compressed
closure. Run 3 used 673,269,974 bytes. That is 48,154,365 bytes more than its eight NARs plus the
closure. Inference: the excess is the left temp file.

## Observations

- The 64 MiB push returned before the data reached the disk: a following `sync -f` took 0.92 s, and
  4.4 s after four concurrent pushes.
- No narinfo existed without its NAR in any of the six kill trials. One trial left a temp file that
  no reader requests.
- `nix copy` to the `file://` store copied all 35 closure paths, including the 34 upstream-signed ones.
  It has no upstream filter.
- Caddy logged no request without a `log` directive.

## Inference

- The static cache meets the requirement semantics of Attic for absent paths, NAR identity, signed
  cold substitution, and atomic publication, with no database and no daemon of its own.
- The forced-command SSH key gives a push route from another machine. The key is the push credential.
  The signing key stays on the server. The HTTP route has no write method, so a pull-only client
  cannot push.
- A crash right after a push could lose data that was not yet on disk. The client checks the NAR
  hash, so the result would be a failed substitution, not wrong content. Whether Nix calls `fsync`
  was not checked.

## Not shown

The Tailscale Serve file route, TLS, another host, a NixOS module, the real directory owner and
permissions, `xz` compression, cleanup of temp files, and any retention.

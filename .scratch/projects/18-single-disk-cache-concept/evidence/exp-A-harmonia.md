# Experiment A: harmonia serves the host store

**Date:** 2026-10-11, 08:22-08:28 EDT. Method, versions, and limits: [README.md](README.md).
Raw: `~/.local/state/vendomat/v6/single-disk-cache/runs/A/`.

## Setup

- Server: `harmonia-cache` 3.3.0 as `andrew`, `CONFIG_FILE` with `bind = "127.0.0.1:18090"`,
  `workers = 4`, `priority = 41`, and `sign_key_paths = [<throwaway key sdc-A-1>]`. It read the live
  `/nix/var/nix/db/db.sqlite` (mode 0644) read-only.
- Push route (shared with C): a throwaway `sshd` as `andrew` on `127.0.0.1:18092`, with the client
  key forced to `<nix>/bin/nix-daemon --stdio`. The client runs
  `nix copy --from local?root=/dev/shm/<src> --to ssh-ng://andrew@127.0.0.1`. The remote
  `nix-daemon --stdio` forwards to the host daemon as `andrew`, who is a trusted user. So the test
  did not exercise signature checks on push.
- Cold: `nix copy --from http://127.0.0.1:18090 --to local?root=<scratch>/cold-copy --option
  trusted-public-keys <sdc-A-1 public key> --option substituters '' <u64 path> <vendomat path>`.

## Expected

As B. A path that exists only in the host store is served, because harmonia has no allow-list.

## Results (three runs)

| Measure | Median (min-max) |
| --- | --- |
| Unique 64 MiB push over `ssh-ng` into the host store | 0.817 s (0.778-0.855) |
| `sync -f` on root after that push | 0.254 s (0.149-0.435) |
| NAR hash: source store = harmonia narinfo | equal, 3 of 3; narinfo signed `sdc-A-1` |
| Vendomat closure "push" | 0.231 s (0.216-0.269): every path was already valid on the host, so nothing moved |
| Closure probes | 35 of 35 HTTP 200; Vendomat NAR hash equal to the host |
| Cache bytes added by the closure | 0 |
| Four concurrent 64 MiB pushes | exits 0,0,0,0; wall 1.205 s (1.181-1.284) |
| Seed probes during concurrent pushes | 3 per run, all HTTP 200, max 0.003 s |
| Cold copy | exit 0, 2.083 s (1.932-2.097); file bytes equal |
| Never-existing path | HTTP 404; `nix path-info --store` exit 1, `is not valid` |
| **Host-only path, never pushed** | **HTTP 200**, 3 of 3 |
| Kill at 0.25, 0.49, 0.74 s | probe 404 after each kill; retry exit 0 in 0.769 s (0.765-0.828); probe 200 |
| Bytes | the store holds each path once, unpacked: 536,941,664 NAR bytes for eight 64 MiB paths; no second copy |

The harmonia log at `info` level had ten lines per run: start, workers, and shutdown. It logged no
request.

## Observations

- Every path in the host store is served, including paths that nobody published.
- A path built on the host is served with no push and no second copy.
- A killed `ssh-ng` push left the path invalid; the Nix daemon's own import is atomic.
- Reads of the Nix database stayed at 1-3 ms while the daemon wrote four paths.

## Inference

- The cache boundary becomes "valid in the server store". `CACHE-005` and `CACHE-011` would need new
  text. Any store path is readable by every tailnet device: build outputs, `.drv` files, and fetched
  source (flake inputs). That conflicts with the "two tracked things" decision, which keeps source out
  of the cache.
- Retention becomes the host's garbage collector. With `nix.gc` on, an unrooted published path
  disappears from the cache. The builder runs `nix build --no-link`, so its outputs have no root.
- harmonia signs whatever the store holds. A trusted pusher can therefore publish anything with the
  host's signature; that equals Attic's push token today.

## Not shown

The `services.harmonia` module (socket activation, `DynamicUser`), Tailscale Serve in front of it, a
non-trusted `nix-ssh` push that needs signatures, and the host GC removing a served path.

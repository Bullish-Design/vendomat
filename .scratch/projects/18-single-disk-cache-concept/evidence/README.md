# Project 18 evidence: method and index

**Date:** 2026-10-11. **Host:** `server`, x86_64-linux, kernel 6.18.38. **Status:** throwaway
experiments only. No production service, configuration, or cache changed.

Raw records stay outside the repository, under
`~/.local/state/vendomat/v6/single-disk-cache/`. Each run has its own directory
`runs/<candidate>/<UTC start>/` with `summary.json`, `events.jsonl` (every command, exit code, and
time), one log per command, and the server log.

## Records

| Record | Content |
| --- | --- |
| [host-facts.md](host-facts.md) | Phase 1 read-only observations of disks, store, settings, and backups |
| [upstream.md](upstream.md) | Upstream source and documentation facts for each candidate tool |
| [exp-B-static.md](exp-B-static.md) | Candidate B: `file://` cache served by Caddy, local push and SSH push (B2) |
| [exp-E-attic.md](exp-E-attic.md) | Candidate E: Attic control, patched build, on the HDD |
| [exp-A-harmonia.md](exp-A-harmonia.md) | Candidate A: harmonia serves the host `/nix/store` |
| [exp-C-ssh-ng.md](exp-C-ssh-ng.md) | Candidate C: `ssh-ng://` as push and pull route |

Candidate D (an S3-compatible service) has no experiment. `../CONCEPT.md` gives the reason.

## Placement (owner decision, 2026-10-11)

The owner chose **HDD only** for throwaway cache data. Cache data (B, E) and every cold store used
`/mnt/wd_green1/attic-investigation-andrew/sdc-<candidate>-*/` (ext4, rotational WDC WD20EADS). Each
run deleted its directory at the end. Candidates A and C serve the host `/nix/store`, so their
"cache" is the root btrfs on the old NVMe by design. The push source for A, C, and B2 was a RAM
store under `/dev/shm`, which stands in for another machine. **No timing here was taken on the 4 TB
target.** The NVMe numbers for Attic come from the earlier trial in project 16.

## Tools and versions

| Item | Value |
| --- | --- |
| Nix | 2.34.7 (`/nix/store/yr2bi0ih7kq27rqqpadn4vdi5vpq6fah-nix-2.34.7`) |
| nixpkgs pin for tools | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| harmonia | 3.3.0, `/nix/store/6mdk83lxcxwnsa8fimqvwp1kb21rfiqq-harmonia-3.3.0/bin/harmonia-cache` |
| Caddy | 2.11.7, `/nix/store/95hr3qbmspavzzkwmbc7bf6bmlxi1ncd-caddy-2.11.7` |
| OpenSSH | 10.3p1, `/nix/store/ww2wf5b928m0b53dp2bdifpgqqyfshvb-openssh-10.3p1/bin/sshd`, run as `andrew` |
| Attic server | 0.1.0, patched, `/nix/store/yp3z60h1mwd8qiwrqn9r5ybmb191csai-attic-0-unstable-2026-06-26` (the binary the production unit runs) |
| Attic client | 0.1.0, `/nix/store/ffya2y53xy8pjmgj43haqyd5nxl17l82-attic-0-unstable-2026-07-06` (the production client build `9r5fng0g…` is no longer in the store) |
| Vendomat package (closure input) | `/nix/store/7mfczgvin17r781daaiw375cwfzl6nh7-vendomat-0.7.0-rc.1`: 35 paths, 239,940,216 NAR bytes; 34 paths carry `cache.nixos.org-1`, the package itself is unsigned |

## Harness

`~/.local/state/vendomat/v6/single-disk-cache/tools/harness.py` (candidates A, B, C, E) and
`tools/b2.py` (B with an SSH push route). `tools/aggregate.py` writes `aggregate-20261011.json`.
One candidate ran at a time, from 08:18 to 08:32 EDT. Load average was 1.2 before the first run and
4.5 during the last runs, mostly from the runs. No build ran at the same time.

Each run did these steps, in order:

1. **push:** a 64 KiB seed, then one unique 64 MiB random file (`nix store add-file`). Then a timed
   `sync -f` on the data filesystem.
2. **closure:** push the Vendomat package closure; probe each of its 35 paths.
3. **concurrent:** four new unique 64 MiB pushes at once; a narinfo probe of the seed every 0.5 s.
4. **cold:** `nix copy --from <cache> --to local?root=<empty store>` with
   `--option substituters ''`, `--option trusted-public-keys <the cache key only>`, and signature
   checking on. Compare the copied 64 MiB file byte for byte.
5. **absent:** probe a random store path that never existed, and run `nix path-info --store <cache>`
   for it. Then probe a path that exists only in the host store and was never pushed.
6. **kill:** for each of 0.3, 0.6, and 0.9 of the single-push time, start a push of a new 64 MiB path,
   send SIGKILL, probe, list partial files, push again, and probe.
7. **bytes:** bytes used by the cache data against the NAR bytes pushed.

Every `nix path-info` used `narinfo-cache-negative-ttl 0` and `narinfo-cache-positive-ttl 0`, because
a negative narinfo cache entry hid a path in project 16 Step 5.

A "probe" is an HTTP GET of `<hash>.narinfo` for A, B, and E (E with the pull token), and
`nix path-info --store ssh-ng://…` for C.

## Runs used

| Candidate | Runs (UTC) | Excluded |
| --- | --- | --- |
| A | `20261011T122242Z`, `20261011T122504Z`, `20261011T122709Z` | `20261011T122210Z`: harness defect (the forced command resolved `nix-daemon` to `nix`); every push failed with `unrecognised flag '--stdio'` |
| B | `20261011T121858Z`, `20261011T121943Z`, `20261011T122023Z` | The first two runs had two harness defects: files under 1 MiB were empty, and the kill step listed every NAR. Their push, closure, cold, and absent results stand; only the third run gives the kill matrix |
| B2 | `20261011T123116Z` | — |
| C | `20261011T122307Z`, `20261011T122524Z`, `20261011T122729Z` | — |
| E | `20261011T122052Z`, `20261011T122359Z`, `20261011T122602Z` | — |

## Cleanup

`cleanup-paths.txt` lists the 124 host-store paths the harness added. They were deleted by exact path
with `nix store delete` (exit 0, "124 store paths deleted, 5.8 GiB freed"; log `cleanup-delete.log`).
No general garbage collection ran. The scratch directories and RAM stores were deleted.

## Limits that apply to every record

- One host, one client, loopback only. No Tailscale, no TLS, no second machine.
- Three runs per candidate (one for B2). Random 64 MiB files do not compress and do not share chunks.
- The HDD carried B and E data, so their timings show the rotational disk, not the NVMe target.
- The servers ran as `andrew`, not under their NixOS modules and systemd hardening.
- The cache key, tokens, and SSH keys were throwaway. The harness never printed them.

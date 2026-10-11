# Project 18: a single-disk cache with no Attic server

**Date:** 2026-10-11. **Status:** Draft concept for owner review. Nothing is implemented. No
production service, cache, or configuration changed.
**Base:** [project 16](../16-vendomat-devenv-layer/) (`SPEC-V6.md` section 6, `CUTOVER-REVIEW.md`,
`evidence/attic-timeouts.md`) and [project 14](../14-vendomat-local/SPEC-V5.md) rows `CACHE-002` to
`CACHE-009`. **Evidence:** [evidence/](evidence/README.md). **Rows:**
[REQUIREMENTS-DELTA.md](REQUIREMENTS-DELTA.md). **Decisions:** [OPEN-DECISIONS.md](OPEN-DECISIONS.md).
This draft does not change the authority of project 14 or project 16.

**Superseded in direction (2026-10-11):** [project 19](../19-vendomat-foundation-layer/CONCEPT.md)
chose candidate A (the serving host's store, through harmonia) with release roots. The evidence
here stays valid; the recommendation of B does not.

## Answer

**Yes, as a mechanism. Not yet established on the target.** On `server`, three Attic-free designs
passed every throwaway step: a static `file://` cache (B), harmonia over the host store (A), and
`ssh-ng://` (C, with one named gap). Each push, cold substitution with signature checking on, absent
path, NAR hash, and killed-push retry behaved as Attic does today, except where this document says
otherwise. None ran on the 4 TB disk, over Tailscale, or under its NixOS module.

**Recommendation: B, a static directory cache.** Machines publish with `nix copy` into one directory
on the root disk. A forced-command SSH key lets another machine publish into it. Tailscale Serve
publishes the directory read-only. It has no database and no daemon of its own. It keeps the publish
boundary that Attic gives today. A is the alternative if the owner accepts that the server store
itself is the cache.

## Problem

The cache today is Attic 0.1.0: a daemon, a SQLite database, chunked storage, a push token, a pull
token, and a cache named `vendomat`. Its data sits on a second, rotational disk (`/mnt/wd_green1`).
Three problems follow.

1. **Failure modes.** A 64 MiB push once took 228-239 s and returned HTTP 500 "Connection pool timed
   out", on uploads and on a plain narinfo read. The cause is not established. The mitigation is a
   source patch (`CACHE-013`) whose keys a stock Attic ignores without an error.
2. **A second disk.** The new role needs `/mnt/wd_green1` mounted by UUID. The cutover must stop
   `atticd` and unmount that disk, because the preflight refuses anything under `/mnt`.
3. **A pull credential.** A cold installer meets HTTP 401 without a pull token (PV-09, an open owner
   decision).

## What "everything on one disk" means

The owner's 4 TB NVMe holds, for the new `server` role:

- the operating system, `/nix/store`, and the Nix database;
- the cache bytes and any cache metadata;
- the cache signing key, through sops-nix as today;
- the source collection (`/home/andrew/vendor`), as the role already places it.

No unit of the role mounts, requires, or writes another disk. The role has no `fileSystems` entry for
`/mnt/wd_green1`. Other disks may stay attached; the role does not use them.

Out of scope, and unchanged: the restic repository on `/mnt/wd_green1` (a `nix-meta` backup profile
that the new role does not carry), the data on `/mnt/shared`, and the declared but absent
`/mnt/wd_re1`, `/mnt/wd_re2`, and `/mnt/flex`. [OPEN-DECISIONS.md](OPEN-DECISIONS.md) item 6 asks
about them.

**Failure domain:** with one disk, the loss of that disk removes the system, the store, the cache,
the source collection, and the signing key together.

## Goals

1. Serve build outputs from the root disk with no Attic daemon and no cache database.
2. Keep the requirement semantics in `CACHE-002` to `CACHE-012`, or change a row with a reason.
3. Keep "two tracked things": the cache holds build outputs only; source stays in the collection.
4. Use native Nix behavior and stock packages. Carry no source patch.
5. Cut cutover steps and owner decisions, not add them.

## Non-goals

- Off-host copies of the cache, the source, or the keys (deferred by the owner).
- A retention engine in Vendomat (`SPEC-V6.md` section 8 excludes it).
- A cache protocol of Vendomat's own, a second lock, or a daemon in Vendomat.
- Implementation. This project ends with this concept and the owner's decisions.

## Candidates

### The six questions

| | A. Host store over HTTP (harmonia) | B. Static `file://` directory | C. `ssh-ng://` | D. S3 service (Garage) | E. Attic on the root disk |
| --- | --- | --- | --- | --- | --- |
| Who populates it | Every build and copy into the server store | Each publisher, with `nix copy --to file://…` | Every build and copy into the server store | Each publisher, `nix copy --to s3://…` | Each publisher, `attic push` or `watch-store` |
| How a machine pushes | `nix copy --to ssh-ng://nix-ssh@server`; a build on `server` needs no push | On `server`: `nix copy --to file://`. Elsewhere: `nix copy --to ssh-ng://cache-push@server`, the key forced to `nix-daemon --stdio --store file://…` (B2) | As A | S3 key and endpoint | Push token |
| How a cold installer pulls | HTTPS on the tailnet, public key in `nix.settings`; no credential | As A | Root SSH key, pinned host key, public key | S3 or HTTPS, S3 key if private | HTTPS plus pull token in a netrc (PV-09) |
| Trust and credentials | Signing key read by harmonia; push = SSH key; trusted pusher or pusher-side signatures | Signing key read by the forced command and the local publisher; push = SSH key; no pull credential | Server must sign its builds (`secret-key-files`); SSH key on every client root | Signing key at the publisher; S3 keys; RPC secret | Token RS256 key; cache key in the database; push and pull tokens |
| Retention and GC | The host garbage collector. A path without a root leaves the cache | None in Nix. Paths stay until someone deletes files | As A | Bucket lifecycle | Attic GC (`default-retention-period`, off today) |
| What breaks | Serves every store path, source and `.drv` files too; absent means "not in the store"; host GC is the retention policy | No GC; a second copy of server-built outputs; temp files after a killed push | No signatures on server builds today; SSH key on every client; 0.2-0.4 s per query | A daemon, a metadata database, and keys again | The database, the patch, the unexplained 230 s failure |

### Measured on this host (HDD for B and E; loopback; medians of three runs)

| Measure | A | B | B2 | C | E |
| --- | --- | --- | --- | --- | --- |
| Unique 64 MiB push | 0.82 s | 0.52 s + 0.92 s flush | 0.91 s | 0.73 s | 1.57 s + 1.62 s flush |
| Vendomat closure (35 paths, 240 MB NAR) | 0 s, already in the store | 2.0 s, 88 MB | — | 0 s, already in the store | 12.4 s, 158 MB |
| Four concurrent 64 MiB pushes | 1.2 s, all exit 0 | 0.76 s + 4.4 s flush | 1.5 s | 1.2 s | 12.5 s + 8.0 s flush |
| Narinfo read during those pushes, max | 0.003 s | 0.002 s | 0.001 s | 0.29 s | 0.033 s |
| Cold copy, signatures on, one key | pass | pass | pass | **fails** on unsigned server builds | pass |
| Never-existing path | 404, `is not valid` | 404, `is not valid` | — | `is not valid` | 404, `is not valid` |
| Host-only path, never pushed | **200 (served)** | 404 | — | **valid (served)** | 404 |
| Push killed, then retried | 404, retry 0.77 s | 404, retry 0.50 s; one temp file | 404, retry 0.80 s | not valid, retry 0.79 s | 404, retry 4.8 s |
| Extra disk per closure | 0 (server builds) | 37 % of NAR | 37 % | 0 | 66 % |

Details and limits: [evidence/](evidence/README.md). The HDD placement was the owner's choice. The
earlier project 16 trial measured Attic with database and storage on the NVMe root at 1.6 s for 64 MiB
(stock, one connection).

### D is excluded

An S3-compatible service brings back each part this project removes. Garage needs a daemon, an LMDB or
SQLite metadata store, an RPC secret, a layout, a bucket, and S3 keys, even on one node. The MinIO
community repository is archived and unmaintained. Nix still writes a `file://`-style layout into the
bucket, so nothing is gained over B.

### Evaluation against the criteria

| Criterion | A | B | C | E |
| --- | --- | --- | --- | --- |
| Writes queue behind one database connection | No; the Nix daemon writes, harmonia reads | No database | No | Yes, unless patched |
| Chunk-heavy writes on a slow disk | No chunks | No chunks; one compressed file per path | No chunks | Yes |
| A config key that silently needs a patched build | No | No | No | Yes (`CACHE-013`) |
| Integrity | Nix NAR hash; narinfo signed on the fly | Nix NAR hash; narinfo signed at publish | Nix NAR hash; needs signed paths | Attic re-hash; signed |
| Atomic publish | Nix daemon import | Rename per file; narinfo last | Nix daemon import | Database row |
| Partial-push recovery | Path stays invalid; retry | No narinfo; retry; temp file left | As A | Retry; chunks left until GC |
| Concurrent writers | Nix daemon locks | Distinct files; same path is identical content | Nix daemon locks | Database pool |
| Read latency under writes | 1-3 ms | 1-2 ms | 0.2-0.4 s | under 0.1 s |
| Signing key | Server, read by harmonia | Server, read by the publisher | Server, `secret-key-files` | In the Attic database |
| Key rotation | Change `sign_key_paths`; every narinfo re-signs at once | New key signs new narinfos; old ones need a re-sign | New key signs new builds only | Attic command |
| Retention and rollback | GC roots; profile generations | Keep all; deletion is manual | GC roots | Attic retention |
| Disk overhead | None for server builds | About 37 % of NAR for a typical closure | None | About 66 % |
| Restore after loss, within one disk | Rebuild; `nix store verify --repair` | Rebuild; delete and re-publish | As A | Rebuild; database too |
| Observability | No request log at `info` | Optional access log; files are the state; `sshd` logs pushes | `sshd` logs each connection | Little; no request log |
| Credential on the tailnet | None for reads; SSH key to push | None for reads; SSH key to push | SSH key for both | Two tokens |
| Installer cost | Tailnet membership and the public key | Tailnet membership and the public key | An SSH key in the installer | A pull token (PV-09) |

## Recommendation

Choose **B** for these reasons:

1. It removes the daemon, the database, the patch, and the second disk.
2. It keeps the publish boundary. A path is in the cache only after someone publishes it. `CACHE-005`,
   `CACHE-009`, and `CACHE-011` keep their meaning, and source stays out of the cache.
3. Its write path is plain files with an atomic rename and the narinfo last. That path showed no
   partial publication in six kill trials.
4. It was the fastest arm on the HDD. On the NVMe it should be no slower (inference).
5. Tailscale Serve can serve the directory, so no new service runs at all (documented; not tested
   here).

The costs of B, stated plainly:

- **No garbage collection.** Nix has no delete for a binary cache. Today Attic has no retention
  period either, so behavior does not change. A later sweep would be a separate, owner-approved
  tool outside Vendomat.
- **A second copy** of outputs that the server builds: about 37 % of their NAR size with zstd.
- **No upstream filter.** `nix copy` publishes upstream-signed paths too. The publisher must filter
  them to keep `CACHE-009` (the builder already finds them for `BUILD-009`).
- **No fsync check.** A push returned before its data reached the HDD. A crash right after a push
  could lose a published file; the client's hash check refuses it (inference).

Choose **A** instead if the owner prefers zero copies and no publish step on `server`, and accepts
these terms: the cache serves the whole server store to the tailnet, including source and `.drv` files;
"absent" means "not in the store"; and retention follows the host's GC roots.

Do not choose **C** as the substituter. It keeps a credential on every client and is 100 times
slower per query. Its push half is part of A and B.

Keep **E** only if the owner wants no change before the cutover. Then carry `CACHE-013` into the role
and move the database and storage to the root disk.

## Flows for B

### Publish (push)

- **On `server`:** `vendomat push` (and the builder) run
  `nix copy --to 'file:///var/lib/nix-cache?compression=zstd&secret-key=<key path>' <paths>` as the
  cache owner. The path filter drops upstream-signed paths and logs each one.
- **From another machine:** `nix copy --to ssh-ng://cache-push@server <paths>`. The `cache-push`
  key is forced to `nix-daemon --stdio --store 'file:///var/lib/nix-cache?compression=zstd&secret-key=<key>'`.
  The client key is the push credential. The client never reads the signing key.
- Order and atomicity come from Nix: NAR first, narinfo last, each by rename. A retry skips paths
  whose narinfo exists.

### Pull

- The core sets `substituters = [ "https://cache.nixos.org" "https://server.<tailnet>/cache" ]` and
  the cache's public key in `trusted-public-keys`. No `netrc-file` is needed for this cache.
- Tailscale Serve maps `/cache` to the directory, read-only. The tailnet policy decides which
  devices can reach it.

### Installer

- `server` installs from itself: devenv Machines copies the closure over SSH (`NAT-019`); the cache
  is not on that route.
- A cold machine needs tailnet membership and the public key, both already part of joining the fleet.
  It needs no pull secret. PV-09 closes by a decision, not by a credential route.

### Retention

- None at first. Every published path stays. Disk: about 88 MB per Vendomat closure. The current
  Attic holds 69 GB after the V6 work; the root disk has about 3.6 TiB for the store and the cache.
- Rollback of any generation works while its paths stay published.
- A later sweep, if the owner wants one, deletes narinfos by a rule, then NARs that no narinfo names,
  then `*.tmp.*` files older than a day. It runs as a NixOS timer in `nix-systems`, not in Vendomat.

## What changes at cutover

Steps refer to `CUTOVER-REVIEW.md` section 8.

| Step | Today | With B |
| --- | --- | --- |
| 5 | Push the machine closure to Attic | Not needed before the install. After the first boot, publish the new system closure from the new store |
| 6 | Place `/etc/nix/netrc` (PV-09) | Removed, if the owner accepts tailnet-only reads |
| 8 | Stop `atticd`, unmount both data disks | **Stays**: the old system mounts both under `/mnt`, and the preflight refuses. Alternative: move the old mount points out of `/mnt` first |
| 10 | Install | Unchanged |
| 11 | Remount the data disks, start the units | Only for the old system's own use. The new role needs no data disk |
| 20 | `curl … /attic/vendomat/nix-cache-info` | `curl … /cache/nix-cache-info` |
| Section 9 | Check `atticd` and the `/mnt/wd_green1` mount | Check the cache directory and the Serve route |

The new cache starts empty. The 69 GB of Attic data is not migrated by default
([OPEN-DECISIONS.md](OPEN-DECISIONS.md) item 4). The cache key changes, unless the owner reuses the
Attic key pair (untested).

## What reopens gates G1 and G5

- **G1** stays BLOCKED, and its cache evidence becomes history. `DVN-006` says "Attic MUST hold the
  fork's build". The 2026-10-10 proof used the live Attic. A successor row and a cold dry-run against
  the new cache are needed.
- **G5** changes from BLOCKED (PV-09 only) to OPEN. The cache VM test (`tests/nix/infra/attic-server.nix`,
  `cache.nix`), the builder VM test (`attic watch-store`, `BUILD-005`), the `attic push --stdin` shape
  (`VMOD-021`, `CLI-021`), and `testee check live-cache` and `live-cache-load` (`tests/livecache.py`)
  all name Attic. Each needs a successor fixture and a rerun. PV-09 can close by decision.

## Proofs still needed before acceptance

1. A NixOS VM: the cache directory served by Tailscale Serve, or by Caddy as a stand-in, with the
   module's user and permissions; cold substitution from a VM store image (`BOOT-027`).
2. The forced-command push from a second VM as a dedicated user, not the owner.
3. The builder publishing after each build, with the upstream filter and its log line.
4. Kill tests at more points, and a crash test (VM power-off) right after a publish.
5. A run on the 4 TB ext4 root after the install.

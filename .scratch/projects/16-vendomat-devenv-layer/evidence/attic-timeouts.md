# Attic pool timeouts, 2026-10-10

Requirement: `CACHE-012`. Status: **cause not established**. No production cache, service, or NixOS configuration changed.

## Inputs and method

- Host: `server`, x86_64-linux; Nix 2.34.7; Testee 0.5.1.
- Server: `/nix/store/4fwzb3rc8dwnhc20gabq2hz989lv4d0f-attic-0-unstable-2026-06-26/bin/atticd`.
- Client: `/nix/store/9r5fng0g7gkaq8ym3v4vhdyysvhywhx2-attic-0-unstable-2026-06-26/bin/attic`.
- Both commands report Attic 0.1.0. The server source pins `b7c905657cb81b8ec9c26b0d9f53aa2e4f231810`.
- Production uses SQLite and local storage under `/mnt/wd_green1/attic`. Its chunk sizes are 16/64/256 KiB.
- The trial script is `~/.local/state/vendomat/v6/attic-investigation/repro/run.sh`.
- Each trial used the same 67,108,976-byte random NAR from one 64 MiB store file.
- Each trial started a new Attic server on `127.0.0.1:18089` with a private token and cache.
- The client pushed one path with `attic push -j 1`. The script sent one cached narinfo GET each second.
- The script stopped the server and deleted its database, storage, and token after each trial.
- The expected result was push exit 0 and HTTP 200 for every narinfo GET.
- Repository gate: `testee verify --full` passed with exit 0 and a full gate in run `20261010T214245Z-697235a4261a`.

The script ran each command below three times, in order. Each trial finished before the next trial started.
No live-cache check, VM, or other timing test ran concurrently.

```text
run.sh disk --runs 3
run.sh root-db --runs 3
run.sh root-all --runs 3
run.sh large-chunks --runs 3
run.sh no-chunks --runs 3
```

The first, fourth, and fifth commands placed the database and storage on `/mnt/wd_green1`.
The second moved only the database to root. The third moved both to root.
The fourth used 64/256/1024 KiB chunks. The fifth set the NAR threshold to 128 MiB.
All other trial settings matched the checked production TOML.

## Five findings

1. **Deployment observation:** The service runs in monolithic mode on loopback. The database and storage share a rotational WDC ext4 disk.
   The disk has 1.7 TiB free. Root is btrfs on NVMe with 48 GiB free.
   The unit does not impose a low memory or file limit.
2. **Source observation:** Attic uses SeaORM 1.1.20's one-connection SQLite API pool.
   SQLx 0.8.6 waits 30 seconds for that connection.
   Upload workers make separate per-chunk writes. They do not hold one transaction throughout the upload.
   Each chunk guard starts an asynchronous database update when it drops.
   Narinfo GET needs the same API pool.
   Attic requests WAL and `synchronous=normal`, but ignores pragma errors.
3. **Host I/O observation:** The same 64 MiB synchronous write test took 59.742 seconds on the disk and 4.373 seconds on root.
   A 1,024-transaction SQLite WAL/NORMAL test took 1.753 and 0.177 seconds.
   The mounts also use different filesystems, so these tests do not isolate drive hardware.
4. **Log observation:** Seven production requests returned HTTP 500 after 30.003–30.006 seconds: five upload PUTs and two narinfo GETs.
   Both GETs began after a large push command returned.
   The failed client paths ranged from 180,240 to 15,182,576 NAR bytes.
   Four 1 MiB checks passed on the first attempt. Both complete 64 MiB checks needed a retry.
   Their first attempts took 228–239 seconds, including post-push surveys.
   The client reported 318–332 KiB/s for the large upload paths.
5. **Upstream claims:** [Issue #24](https://github.com/zhaofengli/attic/issues/24) reports similar SQLite pool errors.
   [PR #139](https://github.com/zhaofengli/attic/pull/139) added WAL tuning already present in this build.
   [PR #311](https://github.com/zhaofengli/attic/pull/311) proposes pool options but remains open.
   The [configuration template](https://github.com/zhaofengli/attic/blob/main/server/src/config-template.toml) recommends PostgreSQL for production.
   These upstream claims do not establish this host's cause.

## Throwaway-server results

The table uses the median of three push times and the nearest-rank p95 of all GET samples.
Every push exited 0. Every GET returned HTTP 200.

| Variant | Runs | Push failures | Narinfo errors | Median push | p95 narinfo |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1. Database and storage on disk | 3 | 0 | 0/18 | 5.501 s | 0.306 s |
| 2. Database on root, storage on disk | 3 | 0 | 0/6 | 1.801 s | 0.009 s |
| 3. Database and storage on root | 3 | 0 | 0/6 | 1.602 s | 0.005 s |
| 4. Disk with 256 KiB average chunks | 3 | 0 | 0/6 | 1.502 s | 0.012 s |
| 5. Disk with no chunking for this NAR | 3 | 0 | 0/6 | 1.201 s | 0.005 s |
| 6. Pool or pragma option | 0 | — | — | — | — |

Variant 6 has no supported setting in this build. Attic exposes no pool size or timeout option.
SQLx rejects unrecognized SQLite URL keys.

The production database snapshot was 9,146,368 bytes with 14,863 chunk rows and 221 NAR rows.
Its journal mode was WAL, and `PRAGMA quick_check` returned `ok`.
Two NAR rows were pending. The chunk holder counts summed to 5,841 before the snapshot trials.
The snapshot is deleted; aggregate results remain in the raw record.

An extra API-only comparison held the disk and storage location fixed.
A fresh database took 5.301 seconds median; the snapshot took 11.703 seconds median.
Moving that snapshot database to root took 6.502 seconds median.
Three monolithic snapshot trials took 11.501 seconds median.
All extra pushes and narinfo GETs succeeded.

In one new-database diagnostic, chunk holders summed to 732 just after the push and zero one second later.
With the snapshot, the sum rose from 5,841 to 6,665 just after the push.
It returned to 5,841 within five seconds.
These results show post-push database work, but not a 30-second queue in the trials.

## Inference and proposed change

**Strongest hypothesis:** Per-chunk writes and guard updates can queue behind the API pool's sole connection.
Slow storage or another live workload could make that queue exceed 30 seconds.
The production first attempts took 228–239 seconds, while the closest snapshot trial took about 12 seconds.
The trials did not reproduce a timeout or identify the live connection holder.
Database placement, chunk count, production service state, and concurrent work remain possible contributors.

The smallest measured mitigation is larger chunks.
The disk trial's median push fell from 5.501 to 1.502 seconds, and its GET p95 fell from 0.306 to 0.012 seconds.
This result does not prove that the change will remove production timeouts.
The following diff is **proposed only** against `nix-meta/machines/server.nix`:

```diff
   services.atticd = {
     enable = true;
     environmentFile = config.sops.templates."atticd.env".path;
     settings = {
       listen = "127.0.0.1:8089";
       database.url = "sqlite:///mnt/wd_green1/attic/server.db?mode=rwc";
+      chunking = {
+        avg-size = 262144;
+        min-size = 65536;
+        max-size = 1048576;
+        nar-size-threshold = 65536;
+      };
       storage = {
         type = "local";
         path = "/mnt/wd_green1/attic";
       };
     };
   };
```

The trial proved these Attic TOML keys on the pinned server with `--mode check-config` and real uploads.
`nix eval --json --expr` accepted the proposed attribute names on Nix 2.34.7.
The proposed nix-meta module has not been evaluated or activated.
The change needs a NixOS activation and an Attic restart.
New uploads will share fewer chunks with older uploads and may use more storage and network traffic.
The change could leave the pool timeouts unresolved.
Moving the database to root is another candidate, but root has only 48 GiB free and prior btrfs metadata exhaustion.
A safe move would also need a consistent database migration.

## Open evidence and raw records

- The production database file size was not measured directly. The read-only backup supplied the snapshot size and counts.
- No query trace identifies which operation held the pool connection for 30 seconds.
- The production journal has one corrupt file and does not name store paths for upload PUTs.
- The live-cache load check needs a no-retry run after any approved change.
- The trial results do not prove a fix for the existing production service.

Raw files stay outside the repository:

- [Source report](/home/andrew/.local/state/vendomat/v6/attic-investigation/source/findings.md)
- [Deployment records](/home/andrew/.local/state/vendomat/v6/attic-investigation/deployment/)
- [Host I/O report](/home/andrew/.local/state/vendomat/v6/attic-investigation/host-io/summary.md)
- [Log forensics](/home/andrew/.local/state/vendomat/v6/attic-investigation/log-forensics/summary.md)
- [Upstream report](/home/andrew/.local/state/vendomat/v6/attic-investigation/upstream/report.md)
- [Trial commands, GET series, push logs, server logs, and summaries](/home/andrew/.local/state/vendomat/v6/attic-investigation/repro/)
- Prior production logs: `~/.local/state/vendomat/v6/releases/` and `~/.local/state/vendomat/v6/live-cache/`.

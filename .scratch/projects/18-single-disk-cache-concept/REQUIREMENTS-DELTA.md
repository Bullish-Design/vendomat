# Project 18 requirements delta

**Date:** 2026-10-11. **Status:** Proposal for owner review. This file does not edit `SPEC-V5.md`,
`SPEC-V6.md`, or `LEDGER-V6.md`. If the owner accepts a row, that spec gets the row and the old row is
marked superseded, with the ledger rebuilt in the same change.

The dispositions below assume the recommended candidate **B** (static directory cache,
[CONCEPT.md](CONCEPT.md)). The last column says how the row changes if the owner chooses **A** or keeps
**E** instead.

## ID check

On 2026-10-11 the highest IDs in `SPEC-V5.md`, `SPEC-V6.md`, and the project 16 records were
`CACHE-013`, `BUILD-009`, `DVN-010`, `BOOT-028`, and `VMOD-021`. Closed V4 records use the separate
names `V4-CACHE-014` to `V4-CACHE-017`; they are not V5 or V6 IDs. New IDs here start at `CACHE-014`,
`BUILD-010`, `DVN-011`, and `VMOD-022`.

## Existing CACHE rows

| ID | Today | Disposition (B) | Reason | If A / if E |
| --- | --- | --- | --- | --- |
| `CACHE-001` | Superseded by `CACHE-010` | No change | — | — |
| `CACHE-002` | The push credential never in a tracked file, a store path, or a log | **Keep** | The push credential becomes an SSH private key; the signing key stays on `server`. The rule and its check (grep files, closure, logs) still apply | A: keep. E: keep |
| `CACHE-003` | A pull-only credential is refused on push | **Change** → `CACHE-017` | B has no pull credential. The read route (a file server) has no write method; only a listed SSH key can publish. Observed: an unlisted key failed (B2) | A: as B. E: keep |
| `CACHE-004` | Superseded by `CACHE-009` | No change | — | — |
| `CACHE-005` | A path never pushed reports absent, never a false success | **Keep** | Observed in B: HTTP 404 and `is not valid`, also for a path present only in the host store. `CACHE-016` adds the exact check | A: **change**, because A serves every host-store path. E: keep |
| `CACHE-006` | `attic watch-store` runs on every builder | **Change** → `BUILD-010` | No watch-store exists without Attic. The builder publishes after each build | A: drop on `server` (no publish); a laptop still needs a push. E: keep |
| `CACHE-007` | A cold consumer obtains a cached output with no local build | **Keep** | Mechanism observed in B with signatures on. The laptop proof stays collected, not gated | A, E: keep |
| `CACHE-008` | NAR hash of a served output equals the build hash | **Keep** | Observed equal in every run of A, B, B2, C, and E | Keep |
| `CACHE-009` | The builder reports an upstream skip; consumers keep the source cache | **Change** → `CACHE-018` | Attic skipped upstream paths natively. `nix copy` to `file://` does not: all 35 closure paths, 34 of them upstream-signed, were published. The publisher must filter | A: drop the skip (the store holds them anyway; cache.nixos.org keeps priority 40). E: keep |
| `CACHE-010` | The host core sets the Attic substituter and its key | **Change** → `CACHE-019` | The URL, the key, and `netrc-file` change | A: as B with the harmonia key. E: keep |
| `CACHE-011` | A never-pushed path: HTTP 404 through the pull credential; `nix path-info` exit 1 `is not valid` | **Change** → `CACHE-016` | "Through the pull credential" no longer applies. The check also covers a host-only path | A: change the meaning to "not valid in the server store". E: keep |
| `CACHE-012` | *Proposed.* Live check with the push and pull credentials of the host Attic | **Change** → `CACHE-020` | The check must publish through the B routes and read the directory route | E: keep |
| `CACHE-013` | Attic database pool keys and the patched build | **Drop** (mark superseded by `CACHE-014`) | No Attic, no database, no patch | A: drop. **E: keep, and carry it into the role** |

## Other rows that name Attic

| ID | Disposition (B) | Reason |
| --- | --- | --- |
| `BUILD-005` (V5) | **Change** → `BUILD-010` | "The builder MUST NOT push explicitly; watch-store moves the paths" cannot hold without watch-store |
| `BUILD-008` (V5) | Keep | The route changes (B2 publish from the laptop); the claim does not |
| `BUILD-009` | Keep, reword the reason | Its reason cites `attic watch-store`. The log line is still needed for `CACHE-018` |
| `DVN-006` | **Change** → `DVN-011` | It says "Attic MUST hold the fork's build" |
| `VMOD-021` | **Change** → `VMOD-022` | It passes `vendomat.cache.attic` as `VENDOMAT_ATTIC` |
| `VMOD-006` | Keep | The rule (check before build or push) holds; its fixture uses a stand-in `attic`, which changes with the implementation |
| `CLI-021` | Keep | `push` stays a command |
| `STORE-012` (V5) | Keep | "No source path in Attic" becomes "no source path in the cache"; B publishes only what a publisher names |
| `NAT-004`, `NAT-009` (V5) | Keep | Observed facts about Attic and Machines; they stay true as history |
| `BOOT-002` (V5) | Keep | The core still carries cache access |
| `BOOT-027` | Keep | The store-image rule applies to any cold-substitution VM |
| PV-09 (project 14) | Close by decision | B needs no pull secret if the owner accepts tailnet-only reads ([OPEN-DECISIONS.md](OPEN-DECISIONS.md) item 2) |

## Proposed rows

Each row is *Proposed*. None is proved on the target. "B evidence" names the throwaway runs in
[evidence/](evidence/README.md); they are evidence for the mechanism only.

| ID | Requirement | Verify |
| --- | --- | --- |
| `CACHE-014` | *Proposed.* The Vendomat cache MUST be a Nix binary cache directory on the host's root filesystem. Only `nix copy` writes it, locally or through the route in `CACHE-015`. A file server MUST serve it read-only. The role MUST run no cache daemon and no cache database, and MUST NOT require another disk. Supersedes `CACHE-013` | A NixOS VM of the role: the unit list has no cache daemon; `systemctl show` names no `RequiresMountsFor` outside `/`; a cold store substitutes from the route. B evidence: Caddy stand-in |
| `CACHE-015` | *Proposed.* Another machine MUST publish through an SSH key whose `authorized_keys` entry forces `nix-daemon --stdio --store 'file://<dir>?compression=zstd&secret-key=<key>'` for a dedicated user. The signing key MUST NOT leave `server`. A client-chosen remote store MUST have no effect | A second VM publishes; an unlisted key is refused; `?remote-store=` is ignored; the key file is mode 0400 and absent from the store. B2 evidence: all three on loopback as the owner |
| `CACHE-016` | *Proposed.* A path that was never published MUST answer HTTP 404 on the read route, and `nix path-info --store <cache>` MUST exit 1 with `path … is not valid` (Nix 2.34.7). This MUST also hold for a path that is valid in the server store but was never published. Supersedes `CACHE-011` | B evidence: three runs, both cases |
| `CACHE-017` | *Proposed.* The read route MUST accept no write. Only the keys listed for `CACHE-015` MAY publish. Supersedes `CACHE-003` | A PUT to the read route fails; an unlisted key fails to publish. B2 evidence: the unlisted key |
| `CACHE-018` | *Proposed.* A publisher MUST skip each path that carries a signature from a key in its upstream key list (default `cache.nixos.org-1`) and MUST log each skipped path. Consumers MUST keep the upstream cache as a substituter. Supersedes `CACHE-009` | Publish a closure with upstream paths; the cache holds only the others; the log names each skip; a cold consumer takes the rest from upstream |
| `CACHE-019` | *Proposed.* The host core MUST set the cache URL and its public key in `nix.settings`. It MUST NOT need a pull secret for this cache. Supersedes `CACHE-010` | `nix config show` lists both; `/etc/nix/nix.conf` names no `netrc-file` for the cache |
| `CACHE-020` | *Proposed.* A live cache check MUST publish a unique object and the Vendomat package through each route of `CACHE-015` and the local route, find every closure path on the read route, and copy both roots into an empty store with signature checking on. It MUST report each attempt and MUST NOT print a key. Missing infrastructure is a named blocker. Supersedes `CACHE-012` | `testee check live-cache` against the new route |
| `CACHE-021` | *Proposed.* A publish that is killed MUST leave no narinfo for the killed path, and a retry MUST complete it. Temporary files MAY remain; no reader may request them | B evidence: six kill trials, one temp file, no orphan NAR. Needs a VM power-off trial |
| `BUILD-010` | *Proposed.* The builder MUST publish each output it built with one `nix copy` to the cache after the build, and its log MUST carry the command, the exit status, and the published paths. Supersedes `BUILD-005` and `CACHE-006` | Builder VM: a tag builds, publishes, and a second machine substitutes it |
| `DVN-011` | *Proposed.* The cache MUST hold the fork's build. A host with the cache configured MUST build nothing to install it. Supersedes `DVN-006` | `nix build --dry-run` of the fork on a cold host lists no derivation to build |
| `VMOD-022` | *Proposed.* As `VMOD-021`, without `vendomat.cache.attic` and `VENDOMAT_ATTIC`. The task runs the pinned `vendomat push --cache <name>`. Supersedes `VMOD-021` | The module test with a stand-in push |

## Rows not proposed

No retention row is proposed. Nix has no delete for a binary cache, Attic retention is off today, and
`SPEC-V6.md` section 8 keeps retention out of Vendomat. [OPEN-DECISIONS.md](OPEN-DECISIONS.md) item 5
asks the owner.

## Disagreements found

- The brief says one disk removes the `/mnt` refusal at cutover. It does not: the running old system
  mounts both data disks under `/mnt` (see [evidence/host-facts.md](evidence/host-facts.md)).
- The `nix-systems` core comment says "a missing file only disables that substituter" for the netrc.
  This project did not test that claim. With B the netrc is no longer needed for this cache.
- The running host's `substituters` do not include its own Attic, while the new core does. Today's
  `server` does not prove the substituter setting of `CACHE-010`.

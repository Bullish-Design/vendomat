# Step 5 — source, cache, and builder infrastructure

**Date:** 2026-10-09. **Gate:** G5.
**Status:** each of the three VM fixtures passed on its own. The Testee e2e gate did **not** complete:
**BLOCKED by disk** (see "Blockers"). `main` did not move. PV-09 stays **BLOCKED** (owner decision).

## Pins and tools

| Tool | Version |
| --- | --- |
| Nix | 2.34.7 (host). The VMs use nixpkgs `nix` 2.34.8 |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (V6 release default), for host and VMs |
| NixOS test driver | `pkgs.testers.runNixOSTest`, QEMU with `/dev/kvm`, virtiofs store |
| Attic | `attic-0-unstable-2026-07-06` (client reports `attic-client 0.1.0`), module `services.atticd` |
| Git | 2.55.0 (VMs) |
| Python (test driver) | 3.14.7 |
| Testee | 0.5.0 |
| Vendomat package | `.#packages.x86_64-linux.vendomat`, `/nix/store/fm6p1k779x545gnggb0xzlry6kqz3kf6-vendomat-0.6.0`, NAR hash `sha256-N5LFbGdR0R/4moRHZR7H8drixBTT4jK0VjOIlMpSZyM=` |

## What was built

All files are under `tests/nix/infra/` unless named otherwise.

| File | Role |
| --- | --- |
| `pin.nix` | Shared pin, the Vendomat package from `VENDOMAT_PACKAGE`, public SSH test keys |
| `collection.nix`, `collection-add` | Two-VM collection test. `collection-add` is a verbatim copy of `nix-meta/scripts/collection-add` |
| `attic-server.nix` | Real `atticd` with sqlite; the signing secret is made at first boot; a stand-in upstream cache on port 8081 |
| `cache.nix` | `server` (Attic) and `cold` (store image of its own closure) |
| `builder.nix` | The build-host NixOS module (options below) |
| `builder-vm.nix` | `server` and `framework`, both import `builder.nix`; both directions |
| `../test_infra_e2e.py` | Pytest wrapper. It builds the package, runs each VM test, reads the log, scans it for JWT-shaped strings |

`tests/fixtures/collection-vm/` (the V5 fixture) moved from nixpkgs `d407951…` to the V6 pin, with its
lock. Its docstring named `STORE-011` (superseded by `STORE-014`); it names `STORE-008`, `STORE-014`,
and `STORE-015` now. Nothing else in the V5 fixtures disproved a claim.

### Builder module options (`vendomat.builder`)

| Option | Type, default | Meaning |
| --- | --- | --- |
| `enable` | bool, false | Turn the module on |
| `inputs.<name>.url` | str | Collection URL, for example `git://server/knappy` |
| `inputs.<name>.attr` | str, `packages.x86_64-linux.default` | Flake attribute that one build produces |
| `cache.name` | str, `vendomat` | Attic cache name |
| `cache.endpoint` | str | Attic server endpoint |
| `cache.tokenFile` | str | Run-time path of the push credential. An assertion refuses a store path |
| `cache.package` | package, `pkgs.attic-client` | Attic client |
| `cache.upstreamKeyNames` | list of str, `[ "cache.nixos.org-1" ]` | Keys whose signed outputs the log reports |
| `watchStore.enable` | bool, true | Run `attic watch-store` |
| `buildArgs` | list of str, `[]` | Extra `nix build` arguments |
| `scan.onCalendar` | null or str, null | Timer for the tag scan |

It installs `vendomat-build`. Units: `vendomat-build@<input>:<tag>.service` (one input at one tag),
`vendomat-build-scan.service` (every new tag of every input), `vendomat-watch-store.service`. The
watch-store unit has `ConditionPathExists` on the token file and an Attic client configuration with
`token-file` only. A build unit sets `ProtectSystem=strict` and writes only to its cache directory.
The `nix-systems` lane imports `tests/nix/infra/builder.nix` and sets `cache.endpoint` and
`cache.tokenFile`.

## Runs

Raw logs: `~/.local/state/vendomat/v6/2026-10-09/05-infra/r1/`. Each log is the stderr of
`nix build --impure --no-link -L --file tests/nix/infra/<name>.nix`, run by
`~/.local/state/vendomat/v6/2026-10-09/05-infra/scripts/run-vm.sh <name> <dir>`. The `*.env.log`
files hold the package, the Nix version, and disk figures before and after.

| Run | Command | Expected | Actual |
| --- | --- | --- | --- |
| C1 | `run-vm.sh collection` (`collection-run1.log`, 136 s, exit 0) | STORE-008, 010, 013 to 015, 018, 022, 023 | PASS. 18 RESULT lines |
| K1 | `run-vm.sh cache` (`cache.log`, `cache.env.log`, 189 s, exit 0) | CACHE-001 to 003, 005, 007 to 009, BOOT-012 | PASS. 25 RESULT lines. See note N1 |
| B1 | `run-vm.sh builder-vm` (`builder-vm.log`, `builder-vm.env.log`, 144 s, exit 0) | BUILD-001 to 006, 008, CACHE-006, 009, BOOT-017 | PASS. 27 RESULT lines |
| T1 | `testee verify --full`, runs `20261010T032142Z-a1ec4f776b69` (before the commit) and `20261010T033510Z-fd527d5b4f5d` (on the commit plus this record), exit 0 | pass | PASS: pytest, ruff, ruff-format, ty. First report copied to `r1/testee-verify-full-report.json` |
| T2 | `testee check e2e`, run `20261010T032234Z-def5a3b27e32` | pass | **INFRA, stopped by me** at 617 s with signal 15. Cause: disk. No result |

Earlier failed runs (fixture faults, not claim failures) are not kept: wrong builder file name; drv
paths as `additionalPaths` (`exportReferencesGraph` needs their outputs); `ty` errors in the test
script; the test script's string context placed the package in the cold store image; a negative
narinfo cache entry hid a path that I had just copied to the stand-in upstream cache.

Note N1. After K1 I added two checks to `cache.nix`: `attic push --stdin` (the `vendomat-push`
shape) and a JSON absent-path query. The driver type check passes (derivation
`nixos-test-driver-vendomat-cache`). The VM run with those two lines **has not run**. The commit
holds that file. Treat `--stdin` as untested until K2 runs.

## Gate by gate

All results below are VM observations from C1, K1, and B1 unless marked.

### Collection (STORE-*): PASS (C1)

| Claim | Observation |
| --- | --- |
| Hook installs on a new repository (STORE-023) | `collection-add lib-a` made `pre-receive`, `post-receive` (mode 755) and the export marker. `cmp` against `hooks/collection-post-receive`: identical. An existing repository, `--hooks` without a marker, and `../x` were refused |
| Release tags only (STORE-014) | Tag push over ssh from `framework`: accepted; pusher saw `collection: working tree now shows v1.0.0`. Branch push refused: `collection: only release tags are accepted, not refs/heads/main`. Repository ended with tags and 0 branches |
| Immutable tags | Forced push of a moved `v1.0.0` and a tag deletion both refused: `collection: refs/tags/v1.0.0 exists; releases are immutable` |
| Version order (STORE-023) | `v1.0.1` pushed, then `v0.9.0`: tree stayed at `v1.0.1` |
| Read-only `git://` (STORE-015) | Push of a tag and of `main` over `git://` failed from `framework` and from `server`. An unmarked repository was not served |
| Source fetch from both VMs (STORE-008) | `git ls-remote` and `nix flake lock` plus `nix eval` of `git://server/lib-a?ref=refs/tags/v1.0.1` returned `lib-a-1.0.1` on both VMs; the lock names the URL and the tag |
| `keep` (STORE-009, 016 to 019) | `vendomat sync` cloned at the tag, detached; rerun `unchanged`; pin moved to `v1.0.1` fetched; dirty tree refused with exit 1; clone deleted and restored |
| `mirror` (STORE-018) | Without `--collection`: `mirror skipped: not the collection host`, no copy. With it: cloned at `v0.1.8`, no marker, no hook, not served over `git://` |
| Refresh (STORE-022) | `lib-b` had its hook removed and three tags pushed: empty tree. `sync --collection` checked out `v1.0.1`. `collection-add --hooks lib-b` restored the hook |
| STORE-010 | `cp -a` copy of the collection; `lib-a`, `lib-b`, and the mirror deleted; both recreated with `collection-add`; all tags pushed from the authoring clone with `git push --tags`; mirror restored by `sync --collection`. Refs (name and object id), the selected tag (`v1.0.1`), the commit, the file list, status, and the detached HEAD are equal. Both listings are in `collection-run1.log` under `RESULT STORE-010 original` and `RESULT STORE-010 rebuilt` |
| Idle cost (STORE-008) | `CPUUsageNSec` of `git-daemon.service` rose by 0 in 15 s |

### Cache (CACHE-*, BOOT-012, BOOT-019): PASS for K1; N1 open

| Claim | Observation |
| --- | --- |
| Real push (VMOD-007 shape, partial) | `attic push vendomat <vendomat package>`: `Pushing 35 paths … (0 already cached, 0 in upstream)`. Second push: `35 already cached` |
| CACHE-002 | Tokens and the signing secret were made in the VMs and read from files. A pattern scan of `/nix/store`, `/etc`, `/var/log`, and the journal on both VMs found none. The Attic client config holds `token-file` only. The raw log has no JWT shape (`eyJ`: 0 matches) |
| CACHE-003 | `attic push` with a pull-only token, on `server` and on `cold`: `AccessError: User does not have permission to complete this action.`, exit 1 |
| CACHE-005 | `nix path-info --store <cache> <never-pushed>`: exit 1, `path … is not valid`. The raw narinfo request, with the pull credential: HTTP 404. The same request for a pushed path: HTTP 200 |
| CACHE-008 | Package: host build `sha256-N5LFbG…`, cache narinfo, and `cold` store are equal, and `nix-store --verify-path` passed. In-VM output: recorded at build, served, and substituted hashes equal (`sha256-Y2CLw+…`) |
| CACHE-009 | A path signed `upstream-test-1` (the cache lists that key): `attic push` printed `(0 already cached, 1 in upstream)`; the Vendomat cache answered 404; the stand-in upstream had it. `cold` fetched it from `http://server:8081` and not from the Vendomat cache. A path with a non-upstream key was pushed (B1 control) |
| CACHE-007, BOOT-012 | `cold` has a store image of its own closure: the package is absent (`test -e` failed; `nix path-info` failed). Without a credential: HTTP 401, exit 1. With a run-time netrc and `--max-jobs 0`: 10 of 35 closure paths were absent and all 10 came from `http://server:8080/vendomat`; the other 25 were in the VM's own system. No `building` line. An empty chroot store in the same VM took all 35 from the cache. `vendomat --help` ran from the substituted path |
| Cache config on the consumer (CACHE-001, CACHE-010 shape) | `nix config show` on `cold` lists the Attic substituter, both keys, and `netrc-file`. They come from a file written at run time, because the cache key exists only after the VM starts. The real host core sets them in `nix.settings` (Step 6) |

### Builder (BUILD-*, CACHE-006): PASS (B1)

| Claim | Observation |
| --- | --- |
| CACHE-006 | `vendomat-watch-store.service` active on `server` and `framework`; `ExecStart` is `attic watch-store vendomat`; its config has `token-file` only |
| BUILD-001 | Five tags of four inputs gave five distinct outputs; the cache served each narinfo (HTTP 200) |
| BUILD-002 | Starting `vendomat-build@alpha:v1.0.0` built `alpha` and left the `bravo` output absent. After a new tag `alpha:v1.0.1`, the scan printed exactly one `command: nix build`, `built=1 skipped=2`. A rerun printed `built=0 skipped=3` |
| BUILD-003 | The unit journal holds `command: nix build --no-link --print-out-paths git://server/alpha?ref=refs/tags/v1.0.0#packages.x86_64-linux.default`, `status: 0 …`, and `output: /nix/store/…-alpha-1.0.0` |
| BUILD-004 | `broken` exited 1 (`status: 1`, `FAILED input=broken`), and `charlie`, which sorts after it, still built. The scan unit exited non-zero. Summary: `built=1 skipped=3 failed=1: broken:v1.0.0` |
| BUILD-005 | `attic push` appears in no unit and not in the script. `alpha` reached the cache with the build unit finished; the `framework` watch-store journal shows `✅ …-bravo-1.0.1` |
| BUILD-006 | No state directory. The only writable path of a build unit is its cache directory; outside `.cache/nix` it holds nothing |
| BUILD-008, BOOT-017 | A: `alpha:v1.0.0` built on `server`; `framework` ran `nix build --max-jobs 0` and logged `copying path … from 'http://server:8080/vendomat'`, no `building`. B: `bravo:v1.0.1` built on `framework`; `server` substituted it the same way. Both receivers had the path invalid before. NAR hash equal on builder, cache, and receiver |
| CACHE-009 in the builder | Input `delta` builds to an upstream-signed path. Nix substituted it from the stand-in. The build log says `upstream: <path> is signed by upstream-test-1; Attic skips it …`. The cache answered 404. `attic watch-store` printed nothing for it, while it pushed the control path |

### PV-09: BLOCKED (owner decision)

A private-pull credential is a secret. How a real installer obtains it is the owner's choice.
PV-09 lists the options and recommends a root-only short-lived file from the installer medium.
I did not choose a route and did not use `nix copy` from a controller. The `cold` VM shows only the
end of the route: with no credential the cache answers 401, and with a pull-only netrc file that
the test driver wrote at run time, substitution works. The driver copy stands in for the unknown
delivery step. Not covered: the Tailscale Serve `/attic` prefix, tailnet membership of a new host,
and the real cache key and credential.

## Observation versus inference

- **Observed:** every table row above.
- **Inferred:** a VM on a virtual LAN stands in for the tailnet. The `git://` port and the Attic
  port were open on all interfaces in the Attic test and on `eth1` in the collection test. The real
  firewall rule is `tailscale0` only (`STORE-015`). That rule is not tested here.
- **Inferred:** `attic watch-store` skips an upstream-signed path by its signature, because the
  control path with another key was pushed and the upstream one was not. The Attic server does not
  verify the signature.
- **Not shown:** that `watch-store` also pushes paths that arrive by substitution from a trusted
  upstream with *no* listed key name. B1's control path (non-upstream key) covers that case.

## Blockers

1. **DISK (open).** The root btrfs reported `Device unallocated` 977 MiB at 2026-10-10 03:33 UTC and 17 MiB a few minutes later, with none of my runs active
   (it was 15.95 GiB at the start of the lane; metadata 79% used, below 90%). Other lanes wrote
   to the same file system during the lane (07-disk-vm, nix-systems install, v6-implementation).
   Each of my VM runs used under 1 GiB of unallocated space. The e2e gate pulled it from 3.95 GiB
   to 0.98 GiB in about ten minutes, with other lanes active. I stopped it by the rule "stop at 0".
   Needed: unallocated space returns (a balance needs root) or the e2e gate runs later on a
   quieter system. Then run: `testee check e2e` and, once, `run-vm.sh cache` (N1).
2. **PV-09 (open, owner).** See above.

## Proposed document changes

For the owner and the lanes that own the documents.

1. `CACHE-005` verify column: replace "`nix path-info --store <cache>` returns null" with "the
   narinfo request returns HTTP 404 with the pull credential, and `nix path-info --store` exits 1
   with `path … is not valid`" (Nix 2.34.7).
2. `CACHE-009`: add that `attic watch-store` prints nothing for a skipped path. The builder
   reports it from the output's signatures (`vendomat.builder.cache.upstreamKeyNames`). Explicit
   `attic push` prints `N in upstream`.
3. New `BUILD-009` (proposed): the build log reports each output that carries an upstream key.
   Fixture: B1 `delta`.
4. `BUILD-002`: say that a tag trigger is `vendomat-build@<input>:<tag>.service` or the scan, and
   that the scan decides "new" by store validity of the output path. This keeps `BUILD-006`.
5. `BOOT-012`, `BOOT-019`: add that a cold VM needs `virtualisation.useNixStoreImage = true`, and
   that the test script must not carry the package as string context. Without both, the
   package sits in the VM store image and the proof is false (found in this lane).
6. `VMOD-007`: leave "Open" until K2 runs `attic push --stdin`. The devenv task itself still has
   no real-Attic run.
7. `CACHE-010`: owned by Step 6. The fixture shows the shape: `nix.settings.substituters`,
   `trusted-public-keys`, and `netrc-file`; `netrc-file` names a run-time path.
8. Tidy: `nix-meta` embeds a copy of the post-receive hook. The fixture installs that copy and
   `cmp` finds it equal to `hooks/collection-post-receive` on 2026-10-09. Keep that comparison in
   any `nix-meta` change.

## Not covered by this gate

- `vendomat push` (Step 4) and the `vendomat:push` devenv task against the real Attic.
- The real tailnet, Tailscale Serve, real keys, and the live collection and cache (not touched).
- A timer-driven scan (`scan.onCalendar`) and a GC of the cache (`CACHE` retention).
- A build host with a failing `attic watch-store` (restart behavior).

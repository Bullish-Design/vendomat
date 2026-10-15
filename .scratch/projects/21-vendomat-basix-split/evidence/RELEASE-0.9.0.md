# Release v0.9.0

**Date:** 2026-10-15. **Owner approval:** "Tagged release is approved." (2026-10-15). Ruling R52
(`VMT-173`) was approved the same day with "VMT 172 - yes".

## Result

| Item | Value |
| --- | --- |
| Release commit | `9b8885e38d34a1fd20f3ecf29d6475e1f1b1e178` ("Release Vendomat 0.9.0"), on `main` and on origin |
| Tag `v0.9.0` | the release commit (lightweight tag, as `v0.8.0`) |
| `release` branch | the release commit, a fast-forward from `e5923a8f` (`v0.8.0`) |
| Prefetch rev (both refs) | `9b8885e38d34a1fd20f3ecf29d6475e1f1b1e178` |
| narHash | `sha256-3q0Znxb8iEmWlO5pVc6QtULoGCU57gzF8xB6ESPxgYU=` |
| Store path | `/nix/store/xkwa1mapckk0ml0h8nvgpizihwwhw5rq-source` |
| Part 1 commit (R52, `VMT-173`) | `7a1f16156757d64f1ff6a7ffcb4ab1b68c96b77f` |

## What v0.9.0 adds since v0.8.0 (`e5923a8f`)

Source: `jj log -r 'e5923a8f..main'`.

- The machine key `trustedInterfaces` (R52, `VMT-173`).
- An empty machine entry in `vendomat.yaml` takes every default (R51, `VMT-170`).
- `machines.NAME.programs`, the Basix contract fixes, the sharing module's `trustedInterfaces` option,
  and the `apply` commit step (R49, R50, `VMT-164` to `VMT-169`).
- The collection pre-receive hook accepts the `release` branch in every repository (R37, `VMT-171`).
- The `v2.4.0-vendomat.4` binary fork and its patches are gone (S6).
- Records: rulings R46 to R52 and the S5, S6, and S8 evidence.
- Version `0.9.0` in `pyproject.toml` and `uv.lock` (edited by hand to match). `flake.nix` reads the
  version from `pyproject.toml`. `README.md` carries the release sentence. The repository keeps no
  change log, so this file holds the release note.

## Checks before the release

Tree `0a5c363bde`, commit `9b8885e38d`, Testee 0.8.0, 32.07 GB unallocated before each heavy run.

| Check | Run | Result |
| --- | --- | --- |
| `testee verify` | `20261015T142016Z-2e22b255de2e` | GREEN 4/4 |
| `opt:front-door-e2e` | `20261015T142108Z-2872c17f182c` | PASS, 1 test |
| `opt:catalog-e2e` | `20261015T142228Z-761c56d8d557` | PASS, 21 tests |

Part 1 runs, on tree `2741edde98`: see `VMT-173`. After the rebase onto the records change of
`5ff1eddf`, `testee verify` was GREEN on commit `7a1f161567` (run `20261015T141848Z-958eda04cca2`).

## Commands (run in the workspace `release-0-9-0`)

```
jj tag set v0.9.0 -r 9b8885e3
jj git push --remote collection --tag v0.9.0
jj bookmark set release -r 9b8885e3
jj git push --remote collection --bookmark release
```

- Before the push, `git ls-remote git://server/vendomat` showed `release` and `v0.8.0` at `e5923a8f` and no
  `v0.9.0`. The collection hook accepted both pushes. The tag push printed
  `collection: working tree now shows v0.9.0`. No raw `git` write ran, and no tag was moved or deleted.
- After the pushes, `git ls-remote git://server/vendomat` showed `HEAD`, `refs/heads/release`, and
  `refs/tags/v0.9.0` at `9b8885e3`, `v0.8.0` at `e5923a8f`, and `v0.7.0-rc.1` at `275bf06f`.
- `nix flake prefetch --json 'git://server/vendomat?ref=refs/tags/v0.9.0'` gave rev `9b8885e3`.
- `nix flake prefetch --json 'git://server/vendomat?ref=release'` gave rev `e5923a8f` on the first call, from
  the Nix git cache that holds a branch for a time. `--refresh` gave rev `9b8885e3`, the same narHash as the
  tag. Use `--refresh` to read a moved branch.

## Smoke test (PASS)

Directory `/mnt/shared/vendomat-p21/release-0-9-0/` (deleted at the end). Logs:
`~/.local/state/vendomat/p21/2026-10-15/release/p2-smoke-*.log`.

1. `nix build --refresh 'git://server/vendomat?ref=refs/tags/v0.9.0#launcher'` built
   `vendomat-launcher-0.9.0` (two small derivations).
2. `vendomat new smoke-ws` printed "workspace ready". `devenv.yaml` has `vendomat` at
   `git://server/vendomat?ref=release`, and `nixpkgs` and `devenv` follow `vendomat/...`.
3. `vendomat shell --no-tui -- bash -c 'echo IN_SHELL; devenv version'` returned rc 0, `IN_SHELL`,
   `devenv 2.4.0 (x86_64-linux)`.
4. `devenv.lock`: `vendomat` is git, ref `release`, rev `9b8885e38d34a1fd20f3ecf29d6475e1f1b1e178`, narHash
   `sha256-3q0Znxb8iEmWlO5pVc6QtULoGCU57gzF8xB6ESPxgYU=`. `devenv` is
   `git://server/devenv` `dir=src/modules` `ref=refs/tags/v2.4.0-vendomat-modules.1` rev
   `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`.
5. A `vendomat.yaml` with `machines.box.trustedInterfaces: [eth1]`: `vendomat explain` returned rc 0 and
   mapped the key to `machines.box.nixos.vendomat.sharing.trustedInterfaces` with value `["eth1"]`. The lock did not change.

## Limits

- The smoke test used the host launcher path and stock devenv 2.4.0; no machine VM ran for the release.
- The catalog proof of `trustedInterfaces` is at evaluation level (`VMT-173`).
- Nothing changed under `~/vendor/` except the collection `vendomat` repository by the two pushes; the live hooks
  stayed as they were. `~/vendor/basix` still does not exist.

# Release v0.10.0

**Date:** 2026-10-15. **Owner approval:** "do the v0.10.0 tag and release, and the vendomat demo change."

## Result

| Item | Value |
| --- | --- |
| Release commit | `c6b36c1e2010fba19185f39584cec9f520434c9e` ("Release Vendomat 0.10.0"), on `main` and on origin |
| Tag `v0.10.0` | the release commit (lightweight tag, as `v0.9.0`) |
| `release` branch | the release commit, a fast-forward from `9b8885e3` (`v0.9.0`) |
| Prefetch rev (both refs) | `c6b36c1e2010fba19185f39584cec9f520434c9e` |
| narHash | `sha256-DkrKlhp3LmD7mOOYNxsepRM3R8fVxz77YRJ+SfW6kRQ=` |
| Store path | `/nix/store/hhn3jmm0aicyd8gsql50kr711g2z5wip-source` |
| vendomat-demo commit | `bb6bad05bf63` (see [S8-CONSUMERS](S8-CONSUMERS.md)) |

## What v0.10.0 adds since v0.9.0 (`9b8885e3`)

Source: `jj log -r '9b8885e3..main'`.

- The catalog key `settings: MODULE: FIELD: text` (R60, `VMT-183`).
- `apply` and `rollback` keep a record as a whole commit (R55, `VMT-182`).
- The `vendomat.toml` flow is gone (S8 step 3). The old verbs exit 3.
- `push` runs without its pre-push check.
- nix-systems runs on the catalog (S8 step 1, `VMT-180` shape half).
- Records: rulings R53 to R61 and the project 22 work records.
- Version `0.10.0` in `pyproject.toml` and `uv.lock` (edited by hand) and the `README.md` release sentence.

## Checks before the release

Tree `2ba8ee2a59`, commit `c6b36c1e20`, Testee 0.8.0, 35.29 GB unallocated before the VM.

| Check | Run | Result |
| --- | --- | --- |
| `testee verify` | `20261015T201927Z-32f7b67e0349` | GREEN 4/4 |
| `opt:front-door-e2e` | `20261015T202021Z-9bd59fa4c431` | PASS |
| `opt:catalog-e2e` | `20261015T202116Z-5094d2a74a2f` | PASS |
| `opt:machines-vm` | `20261015T202409Z-a68f5f8bc37d` | PASS (no io_uring failure; no wrapper needed) |

## Commands

```
jj tag set v0.10.0 -r c6b36c1e
jj bookmark set release -r c6b36c1e
jj git push --remote collection --tag v0.10.0
jj git push --remote collection --bookmark release
```

- Before the push, `git ls-remote git://server/vendomat` showed `release` and `v0.9.0` at `9b8885e3` and no
  `v0.10.0`. The tag push printed `collection: working tree now shows v0.10.0`. The bookmark push
  printed `move forward from 9b8885e38d34 to c6b36c1e2010`. No tag was moved or deleted.
- After the pushes, `HEAD`, `refs/heads/release`, and `refs/tags/v0.10.0` are at `c6b36c1e`. `v0.9.0`, `v0.8.0`,
  and `v0.7.0-rc.1` did not move.
- `nix flake prefetch --refresh --json` gave the same rev and narHash for `?ref=release` and `?ref=refs/tags/v0.10.0`.

## Smoke test (PASS)

Directory `/mnt/shared/vendomat-p21/release-0-10-0/` (deleted at the end). Logs:
`~/.local/state/vendomat/p21/2026-10-15/release-0-10-0/`.

1. `nix build --refresh 'git://server/vendomat?ref=refs/tags/v0.10.0#launcher'` built `vendomat-launcher-0.10.0`.
2. `vendomat new smoke-ws` printed "workspace ready".
3. `vendomat shell --no-tui -- devenv version` returned rc 0 and `devenv 2.4.0 (x86_64-linux)`.
4. `devenv.lock`: `vendomat` is git, ref `release`, rev `c6b36c1e2010fba19185f39584cec9f520434c9e`. `devenv` is
   `ref=refs/tags/v2.4.0-vendomat-modules.1`, rev `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`.
5. An authored module (`mod.nix`, option `vendomat.settings.greeting.text`) with `settings: greeting: text: hello smoke`:
   `vendomat explain` mapped the key to the option with value `"hello smoke"`, from `vendomat.yaml`, and
   "Set only in Nix: (none)". The shell printed `SMOKE_GREETING=hello smoke`.
6. `vendomat sync` exited 3 with one line: `vendomat: 'sync' was removed with the vendomat.toml flow; edit vendomat.yaml and run 'vendomat update'`.

## Limits

- The smoke test used the host launcher path and stock devenv 2.4.0.
- Nothing changed under `~/vendor/` except the collection `vendomat` repository by the two pushes. The live hooks stayed as they were.

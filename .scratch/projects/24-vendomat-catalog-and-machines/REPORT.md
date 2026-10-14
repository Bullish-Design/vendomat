# Project 24 report: S3 and S4

**Date:** 2026-10-14. **Result:** S3 and S4 are on `main`. Vendomat v0.8.0 is published on `release`.

## Commits on `main`

Every commit passed `testee verify` GREEN 4/4 (Testee 0.8.0, gate epoch 2).

| Commit | Change |
| --- | --- |
| `bd7baeb06b1a` | Testee 0.8 tasks replace the Testee module (owner ruling in session; project 22 R18) |
| `ccd419ddee93` | S3 part 1: Nix parser, catalog, template, curated parser corpus |
| `b43d23e6b9cb` | S3 part 2: hatch line, `explain`, error trimming, `update`, launcher dispatch, new `front-door-e2e` |
| `b575e4f424b0` | S3: `opt:parser-fuzz` and `opt:catalog-e2e` |
| `845172f0768f` | S3 step 11b: Harmonia sharing module and `opt:sharing-vm` |
| `79e46310ef30` | S3 step 11b: catalog wiring of `serve` and the peers |
| `0109ae1f2de8` | S3 records: evidence, ledger, docs |
| `56642bac8660` | Fixtures on the published S1 tag; version 0.8.0 |
| `e5923a8f5c0f` | S4: `vendomat apply` and `vendomat rollback`, with records |

## Opt-in checks

devenv requires a namespace in task names, so the kickoff's checks are `opt:NAME` tasks.

| Task | Result | Tree |
| --- | --- | --- |
| `opt:catalog-e2e` | PASS, 21 of 21 (W4 F1 to F14, F4b) | published S1 tag |
| `opt:parser-fuzz` | PASS, 16 tests, about 38 000 generated files | not tree-dependent |
| `opt:sharing-vm` | PASS, two VMs | plain NixOS evaluation; needs no devenv tree |
| `opt:machines-vm` | PASS, 12 of 12 steps (W2 T1, W9 R1 to R6, record, dirty skip) | published S1 tag, from `flake.lock` |
| `opt:front-door-e2e` | PASS, also on `e5923a8f` | published S1 tag |
| `opt:catalog-eval`, `opt:catalog-devenv` | PASS | stub options; published S1 tag |

## S1 module tree

Until the S1 tag existed, every fixture used a scratch tree: upstream `b904dcb5` plus m1 to m5. Its
`src/modules` hash, `sha256-BJLQl3uuGrP+f7+Q5Bjoatq9PJhcwDrdon9hGUbTVQ0=`, equals the hash of the
published tag `v2.4.0-vendomat-modules.1` (rev `061c2184`). The fixtures were rerun on the published
tag before the release.

## VMT-116

No. Unused template inputs cost no fetch on shell entry. devenv 2.4.0 resolves lock entries lazily.
Locking and `update` fetch every input once.

## Release

Pushed with the owner's approval in this session: tag `v0.8.0` and `release` (fast-forward from
`d3c279e0`) at `e5923a8f`. A fresh `vendomat new` workspace on `git://server/vendomat?ref=release`
entered the shell with stock devenv 2.4.0. Its lock pins `devenv` to the S1 tag rev `061c2184`.

## Ledger

- Closed or advanced in S3: `VMT-013`, `VMT-020`, `VMT-022`, `VMT-035`, `VMT-045` (stub input only),
  `VMT-054` to `VMT-057`, `VMT-090`, `VMT-092` to `VMT-094`, `VMT-099` (catalog half), `VMT-116`,
  `VMT-117`, `VMT-122`, `VMT-127` (two VMs), `VMT-128`.
- Closed in S4: `VMT-072`, `VMT-075`, `VMT-098`, `VMT-110`.
- Still open: `VMT-058` (beyond the missing-line check), `VMT-094` (a shell-entry error that names the
  line), `VMT-111` and `VMT-112` (later halves), `VMT-121` (no ISO or VM through the catalog),
  `VMT-127` (real machines, S7).
- New rows: `VMT-157` (key publication), `VMT-158` (depth limit 64), `VMT-159` (`opt:` task names),
  `VMT-160` (gap: a machine entry needs one key), `VMT-161` (`apply` copies the cache key),
  `VMT-162` (exit 4 of `switch-to-configuration` is a warning; proposed), `VMT-163` (watched files).
  New rows start at 157, because the Basix ledger reaches `BSX-156`.

## Disk

- `/` at the start: 25.87 GiB unallocated, metadata 79 %. Low point: 14.87 GiB, which fired the
  guard. The owner freed space. At the end: 28.87 GiB, metadata about 80 %.
- `/mnt/shared/vendomat-p21/`: the agents deleted every VM image and scratch file under `s3/` and
  `s4/`. The empty `s3/` and `s4/` directories are removed. The spike archive
  `archive/p21-spikes-2026-10-13.tar.zst` (977 MB) stays. `vr7/` belongs to another session.

## Open items for the owner

1. Confirm `VMT-162`: `apply` treats exit 4 of `switch-to-configuration` as a warning and writes the
   record line.
2. Confirm `VMT-157`: the owner commits each machine's public key as `.machines/NAME/cache-key.pub`.
   A bare `apply` writes the file and asks for a commit.
3. Rule on `VMT-160`: the grammar rejects empty values, so a machine needs at least one key.
4. Fallback with a peer off takes about 25 s (5 attempts of 5 s). `download-attempts` can shorten it.
5. The key unit failed once in about 6 early boots. The cause is unproved. The changed unit passed
   18 of 18 boots.
6. Host fact: QEMU io_uring fails for `andrew` (memlock budget exhausted, cause unknown). The VM
   harnesses run QEMU in a `systemd-run --user` unit with io_uring filtered.
7. No VM boots a machine built through `vendomat.yaml`. The catalog-to-machine path is proved at
   evaluation level only.
8. `opt:workspace-e2e` fails because `../templateer_v2/.devenv/state/venv/bin/templateer` is missing.
9. `AGENTS.md` still says "Attic owns cached objects", which R39 makes stale.
10. The main checkout holds project 22 work that is not on `main` (`kxstxvlk` and uncommitted edits).
    I did not run `jj new main` there.
11. Agents broke the tool rules a few times before the Testee 0.8 gate worked: one direct pytest run,
    `ruff format` through `uv run`, and one read-only raw `git diff`. The evidence files record each.
    All final verdicts come from Testee.
12. nix-systems and vendomat-demo still use `vendomat.toml` (R40). S8 moves them.

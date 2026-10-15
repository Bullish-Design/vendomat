# S8 steps 3 and 4: remove the vendomat.toml flow — 2026-10-15

R40's condition holds: vendomat-demo and nix-systems use `vendomat.yaml` ([S8-CONSUMERS](S8-CONSUMERS.md)).
Raw logs and the inventory: `~/.local/state/vendomat/p21/2026-10-15/s8/step3/`.

## Removed

- Modules: `registry`, `generate`, `devenvgen`, `locate`, `lockpath`, `bump`, `store`, plus `check`
  (only the old `check` verb and `push` used it), `machine` (`machine install` moves to Basix, R13),
  and `nixio` (only `check` and `devenvgen` used it).
- Commands: `sync`, `path`, `check`, `bump`, `machine`.
- Files: `direnv/`, `preflight/`, `nix/devenv-module/`, `templates/workspace-v6/`,
  `templates/workspace-registry/`, the flake output `devenvModules.default`, and the package files
  `vendomat-workspace-init` and `share/vendomat/direnv`.
- Tests (14 files): registry, registry_v6, generate, devenvgen, store, commands_v6, sync_nix,
  project_output_interface, use_vendomat, machine_install, devenv_sync_e2e, devenv_module_e2e,
  workspace_user_e2e, launcher_e2e. Task `opt:workspace-e2e` removed. `opt:e2e` became `opt:infra-vm`.
- `consumer-module.nix`, `machine.json`, and `nixosModules` were already absent from `main`.
  No project 21 code used `devenvModules.default`. `VMT-123` is done.

## Kept, with changes

- `push.py` stays (`VMT-120` has no real-machine pass). Its pre-push `check` step is gone: it read the
  removed `.vendomat/` fragment, and its tag-pin rule rejects the template's `?ref=release` input.
  `vendomat push` now builds and pushes. Judgment call.
- `yamlsubset.py` (`update.py` needs it), `defaults.py` (tests compare it to the flake), `hooks/`, `launcher/`.
- Launcher: the pinned-build machinery (NAR hash, `VENDOMAT_USE_HOST`, `VENDOMAT_LAUNCHER_CACHE`) is gone.
  `push`, `--version`, `--help` run the host release. `sync`, `path`, `check`, `bump`, `machine` exit 3 with one line.
- Hook proof: `test_collection_hook.py` no longer imports `refresh_collection`. The test "agrees with the sync
  refresh" became "picks the newest tag by version and leaves tags alone", on the hook alone. The hook and the
  `collection-add` copy under `tests/nix/infra/` lose the words `vendomat sync --collection` (comment and
  error text). **Open:** nix-meta's live `collection-add` embeds the old hook text. It differs only in that
  comment and message. Update it with S8 step 2.
- `collection.nix`: kept the hooks, tag and branch rules, version order, `git://` read only, Nix fetch,
  `STORE-010` rebuild, idle CPU, and `--hooks` reinstall. Removed `keep` (STORE-009, 016 to 019), `mirror`
  (STORE-018), and the `sync --collection` refresh (STORE-022): they proved only the removed CLI.
- `cache.nix`, `builder*.nix`, `attic-server.nix` and their `test_infra_e2e.py` tests, `test_live_cache.py`:
  kept. They prove Attic and build-host behavior, not the removed CLI. They belong to the V4 backlog and R39.

## Verification (Testee 0.8.0, tree before this note)

| Check | Run | Verdict |
| --- | --- | --- |
| `testee verify` | 20261015T195256Z-3d0515a677fd | GREEN 4/4 |
| `opt:catalog-eval`, `opt:catalog-devenv`, `opt:catalog-e2e`, `opt:front-door-e2e` | 20261015T195359Z-55308e428e63 | PASS (4) |
| `opt:machines-vm` | 20261015T195936Z-857dfd17a929 | PASS |
| `opt:sharing-vm` | 20261015T200545Z-79086381084c | PASS |
| `collection.nix` (VM, `VENDOMAT_PACKAGE` `/nix/store/41ahbycw618syaaxyzi518q0phkplri7-vendomat-0.9.0`) | `collection.log` | exit 0; RESULT lines for hooks, tags, release branch, `git://`, Nix fetch, STORE-010, idle CPU 0 ns |

`btrfs` unallocated was 35 GB before each VM. QEMU needed no `io_uring` wrapper. The task `opt:infra-vm`
itself did not run: its cache and builder VMs are unchanged, and only `collection.nix` changed.

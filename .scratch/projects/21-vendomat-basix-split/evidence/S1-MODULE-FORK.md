# S1: the module-only devenv fork, tag `v2.4.0-vendomat-modules.1` — 2026-10-14

Slice S1 of the implementation guide. This record changes the Vendomat repository (patch series,
`materialize`, two fixtures, the flake input) and publishes one permanent tag in the source
collection. No host disk, no host profile, no Attic, no upstream contact.

## Goal and rulings

Ship the module half of the devenv changes as a fork that holds only `src/modules`, with no Rust
change. Workspaces follow the fork as `vendomat/devenv`.

- R41 (D2 a): the fork tag is Vendomat's second flake input `devenv` (`dir=src/modules`).
  `tests/test_repo_shape.py` and `AGENTS.md` change with it.
- R44 (D7 a): fork tags are `v2.4.0-vendomat-modules.N`. This slice publishes `.1`.
- R34: no upstream pull request. The fork is long-lived. Every patch says `Upstream: none`.
- R35: homes stay outside Vendomat. The fork does not touch `home-manager` or `nix-darwin` option types.

## Inputs and versions

| Item | Value |
| --- | --- |
| Upstream | `cachix/devenv` tag `v2.4.0`, commit `b904dcb51fe48c30db250038241507f60752f222`. `~/vendor/devenv` already holds it. |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (unchanged in `flake.lock`) |
| `devenv` on `PATH` | `devenv 2.4.0+b904dcb` (wrapped, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0`) |
| Stock devenv for the version fixture | `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0` (`pkgs.devenv` of the pinned nixpkgs) |
| Testee | 0.8.0 (kfhxs4c) from the first gate run on. The series-only run used 0.7.0. The host changed from 0.7.0 to 0.8.0 during the session. |
| Fork commit and tag | `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9` = `devenv-dist/modules/RESULT`, tag `v2.4.0-vendomat-modules.1` |
| Vendomat change | `sqlprpppppnm` (workspace `s1-module-fork`), parent `ccd419dd` (local `main`) |

The parent chain is five commits on the upstream commit.

## The patch series

`devenv-dist/modules/` holds `SERIES`, `UPSTREAM`, `MANIFEST.sha256`, `RESULT`, and `patches/`. All
five patches applied cleanly with `git am --no-3way`. Patch m0005 applied on m0003 and m0004 with no hand change.

| Patch | sha256 (start) | Change | Ledger rows |
| --- | --- | --- | --- |
| `m0001` | `a6282af5…` | `machines.NAME.nixos` becomes `nullOr deferredModule` (`machines.nix`, one line) | `VMT-064`, `VMT-082` |
| `m0002` | `39601fdf…` | `src/modules/latest-version` set to `2.4.0`. Same content as upstream `a5c34429`, which is on main after v2.4.0. | `VMT-118` |
| `m0003` | `052c7050…` | public options `machines.NAME.build.vm` and `build.iso`, typed `nullOr package` (not `output`, so `devenv build` builds no image by default) | `VMT-095` |
| `m0004` | `bddbd5c3…` | `build.iso` extends the machine with the ISO module through `extendModules`; the `iso.modules` option; the six required settings | `VMT-095`, `VMT-107`, `VMT-108` |
| `m0005` | `ff37a3a2…` | option `machines.NAME.vendomat.mode` (null, `fresh-install`, `adopt-existing`), copied to `machinesMeta.NAME.vendomat.mode` | `VMT-106` (module half) |

Full hashes are in `devenv-dist/modules/MANIFEST.sha256`.

m0004 equals the proven W8 patch 2 ([W8](W8-ISO-POLICY.md)). A machine that imports its own ISO
module keeps its own image (`VMT-108`).

## Materialize changes

`devenv-dist/materialize` gained two things.

- `--series modules` applies `devenv-dist/modules/` on the same upstream pin. It reads the fork tag from `modules/UPSTREAM` and compares with `modules/RESULT`.
- A fallback: when the `v2.4.0` tag is absent in the source, it fetches the pinned commit by hash and creates the tag. `--source ~/vendor/devenv` needs this, because the collection holds the commit but not the upstream tag.

`tests/test_devenv_dist.py` keeps its binary-series tests and adds 11 module-series tests: contiguous numbers, manifest hashes, the fixed header and the R34 line, module files only, the content of m1 to m5, the R44 tag, and a refused tampered patch. The `opt:modules-e2e` task materializes `--series modules` end to end. `src/modules/flake.nix` of the fork tree exists (upstream file, `outputs.modules = ./.`), so `dir=src/modules` is a flake.

## Determinism

Command, run from the workspace before the push:

```text
python3 -I devenv-dist/materialize /tmp/s1-verify.b0b9gf/tree2 --series modules --source ~/vendor/devenv --verify
```

Expected: exit 0 and fork commit `061c2184…`. Actual: exit 0, `HEAD` = tag = `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`. A first run in a second directory gave the same commit. The test `modules-e2e` materializes a third tree and verifies it again (log `001-materialize-modules.log`).

## Fixtures

All fixtures run through Testee as `opt:modules-e2e` (evaluation, six tests) and `opt:modules-vm` (two boots). The devenv binary is the `PATH` one (stock 2.4.0 plus upstream commit b904dcb, no patch). Each fixture uses the fork as the `devenv` input, and the stock modules of the upstream pin as the control. Observation and inference are separate.

| # | Fixture (test) | Command | Expected | Actual (observation) |
| --- | --- | --- | --- | --- |
| E1 | `test_merge_nixos_definitions` | `devenv eval` of `machines.box.build.nixos` with an attribute set, a function, and a default module for `machines.box.nixos` | Fork merges; stock does not | Fork evaluates: `/etc` carries all three definitions. Stock fails: ``Cannot merge definitions of `machines.box.nixos'``. |
| E2 | `test_build_nixos_is_unchanged` | `build.nixos.outPath` of `box`, `iso`, `target` on both trees | Same path | Identical: box `fbp1k0vs…`, iso `sa86g98f…`, target `6c1gfvkg…`. |
| E3 | `test_no_images_by_default` | `devenv build machines.target` on the fork | stock outputs, no image | Outputs: `build.nixos`, `build.deployer`, `build.diskoScript`, `build.diskoFormatScript`, `build.diskoMountScript`. No VM, no ISO. |
| E4 | `test_iso_policy` | `build.iso.drvPath` for an ISO machine, a plain-timeout box, and a `mkForce` box | own image kept; plain value ignored; `mkForce` changes | ISO machine: `build.iso` = its own `isoImage` drv (`8wpcmywg…`), no second ISO module. Plain timeout: `m4ing7zi…`, equal to a box with no setting. `mkForce`: `3i9g7x4q…`. `build.nixos` drv of the three boxes is the same (`amcn92yh…`). |
| E5 | `test_mode_option` | read `machines.N.vendomat.mode` and `machinesMeta.N.vendomat.mode` | set value, `null` by default | `fresh-install`, `adopt-existing`, `None`; the same three in `machinesMeta`. |
| E6 | `test_no_version_warning` | `devenv shell` on stock nixpkgs devenv 2.4.0 with each module tree | stock warns; fork does not | Stock prints `devenv 2.4.0 is newer than devenv input (2.3.1)`. Fork prints nothing. |
| V1 | `test_build_vm_of_a_plain_machine_boots_with_no_failed_units` | `devenv build machines.box.build.vm`, run, ssh | boots clean | VM `/nix/store/n88qvd2ajn1xknhv3nik62akpc60w36i-nixos-vm`: state `running`, 0 failed units, `multi-user.target` active. |
| V2 | `test_build_iso_of_a_disko_machine_boots_with_no_failed_units` | `devenv build machines.target.build.iso`, boot under OVMF with a blank 4 GiB qcow2 | boots clean, disk untouched | ISO `/nix/store/c8szjimmjppk4cgj1sww99mzmh2p4irx-nixos-26.11.20261008.e7439b6-x86_64-linux.iso`: state `running`, 0 failed units, tmpfs root, EFI boot, the disk stays one blank disk with no partition. |

Version fixture detail (E6): the `PATH` devenv `2.4.0+b904dcb` never prints the warning. It is a build from the upstream commit that carries the same fix. The test therefore uses the nixpkgs devenv 2.4.0 as the binary.

Inference: E2 and E4 say the fork does not change what a plain machine builds. They do not prove that a machine with a LUKS or swap config boots as an ISO; W8 B5 covers that on the earlier patch, and m0004 equals it.

## Testee runs

| Run | Tool | Check | Verdict | Subject |
| --- | --- | --- | --- | --- |
| `20261014T134057Z-d86b3e789dba` | 0.7.0 | `testee verify` | GREEN | patch series only |
| `20261014T164841Z-77cf5cb7acb0` | 0.8.0 | `verify --profile quick` | PASS | tree `35a604c1cc`, commit `f40192d9` |
| `20261014T164909Z-99ef1960b849` | 0.8.0 | `verify` | GREEN 4/4 | same |
| `20261014T164929Z-74009d1e75d4` | 0.8.0 | `opt:modules-e2e` | passed (6 tests, 0 fail, 0 skip, 258 s) | same |
| `20261014T165430Z-f05c678cd523` | 0.8.0 | `opt:modules-vm` | passed (2 tests, 577 s) | same |
| `20261014T170718Z-85108588b124` | 0.8.0 | `verify --profile quick` | PASS | after the flake input, tree `2e064bea84`, commit `afc54dcd` |
| `20261014T170722Z-dc3114061037` | 0.8.0 | `verify` | GREEN 4/4 | same |
| `20261014T170745Z-3dc189e02201` | 0.8.0 | `opt:modules-e2e` | passed (6 tests, 0 fail, 0 skip, 313 s) | same, with the tag already published |

After the ledger, plan, and CURRENT edits, `verify --profile quick` passed (`20261014T171515Z-8f8b7672a720`) and `verify` was GREEN 4/4 (`20261014T171518Z-2cab03215657`, tree `d8b1ecbb9a`, commit `eecb1ab5`). Adding these run IDs to this file changed the tree again. A last `verify` ran on that final commit; the commit hash is in the hand-off report.

## Tag publication

The tag push used the local repository path of the collection. The pre-receive hook accepts only new tags.

```text
cd /tmp/s1-verify.b0b9gf/tree2     # materialized tree, outside the Vendomat repository
git push /home/andrew/vendor/devenv refs/tags/v2.4.0-vendomat-modules.1:refs/tags/v2.4.0-vendomat-modules.1
To /home/andrew/vendor/devenv
 * [new tag]           v2.4.0-vendomat-modules.1 -> v2.4.0-vendomat-modules.1
```

Only that ref moved. No force, no other ref, no deletion. The collection now holds
`v2.4.0-vendomat-modules.1` besides `v2.4.0-vendomat.2`, `.3`, `.4`.

```text
$ git ls-remote git://server/devenv 'refs/tags/v2.4.0-vendomat-modules.1*'
061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9	refs/tags/v2.4.0-vendomat-modules.1
```

The tag is lightweight, so the ref names the commit directly. The post-receive hook checked out
the newest tag in the collection work tree: `git -C ~/vendor/devenv log -1` printed `c66ba875`
(the `.4` fork) afterwards and the tree was clean. The hook did not move the work tree to the new tag.
The hook ranks tags with `git for-each-ref --sort=-v:refname`. That ranking puts `v2.4.0-vendomat.4` first, so the work tree stayed on it. `git://server` serves the object database and does not depend on the work tree.

```text
$ nix flake prefetch --json 'git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules'
{"hash":"sha256-tOYEk6WSJZ8yquJv61p6Xwi0giBjZqeutcBMSOaeZkQ=","locked":{"dir":"src/modules","lastModified":1791504000,"ref":"refs/tags/v2.4.0-vendomat-modules.1","rev":"061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9","revCount":7374,"type":"git","url":"git://server/devenv"},"original":{"dir":"src/modules","ref":"refs/tags/v2.4.0-vendomat-modules.1","type":"git","url":"git://server/devenv"},"storePath":"/nix/store/c8l2347km7r60798yajrsgzj50s619fh-source"}
```

## Flake input and shape rule

`flake.nix` gains `inputs.devenv.url = "git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules";`. The outputs function takes `{ self, nixpkgs, ... }`. No output uses `devenv`. The input is a flake (the fork has `src/modules/flake.nix`); `flake = false` was not needed. The comment above the inputs now says two inputs and names R41.

`nix flake lock` added only the `devenv` node (type `git`, `ref` `refs/tags/v2.4.0-vendomat-modules.1`, `rev` `061c2184…`, `narHash` `sha256-tOYEk6WSJZ8yquJv61p6Xwi0giBjZqeutcBMSOaeZkQ=`). The `nixpkgs` node is unchanged at `e7439b6b…`.

- `tests/test_repo_shape.py`: the root-input test now expects `{"nixpkgs", "devenv"}` and takes the name `test_the_flake_has_nixpkgs_and_the_module_fork_as_its_only_inputs`.
- `AGENTS.md`: the layout line says two inputs; the shape sentence says "a third flake input".
- `tests/test_fleet_shape.py` passes unchanged: the `devenv` node has `type` `git`, a `refs/tags/` ref, a locked rev, and a `git://server` URL.

## Deviations

1. **m0004 wording.** The ledger and the guide say "six required overrides". The patch has four `mkImageMediaOverride` settings (priority 60: file systems, swap devices, LUKS devices, loader timeout) and `makeEfiBootable` and `makeUsbBootable` at normal priority. These are the six settings that W8 kept. Only the four are hard to change from `iso.modules` (`VMT-107`).
2. **`VMT-118` binary.** The `PATH` devenv never prints the version warning, so the fixture uses the nixpkgs devenv 2.4.0. The proof covers the module change (m0002) with that binary. The catalog path is not proved (S3).
3. **No docs paragraph.** The guide proposes an `iso.modules` paragraph in the docs. m0004 touches no docs file, so none was added.
4. **QEMU memory lock.** QEMU fails with `ENOMEM` from io_uring on this host unless `RLIMIT_MEMLOCK` is 64 KiB. `tests/test_modules_vm.py` lowers it in the child.
5. **ssh in the sandbox.** The Testee sandbox needs `ssh -F /dev/null`. The test passes it.
6. **Workspace diff.** I ran a read-only `git diff --stat` once inside the Vendomat workspace by mistake. It changed nothing. All later checks used `jj`.
7. **Testee version.** Testee changed from 0.7.0 to 0.8.0 during the session. Only the series-only GREEN run used 0.7.0.

## Raw logs

- `~/.local/state/vendomat/p21/2026-10-14/s1/modules-e2e/`: one directory per run, with `observations.txt` and numbered command logs.
- `~/.local/state/vendomat/p21/2026-10-14/s1/modules-vm/`: VM and ISO boot logs and serial output.
- `~/.local/state/vendomat/p21/2026-10-14/s1/publish/`: `push.log`, `ls-remote.log`, `prefetch.json`.
- `~/.local/state/vendomat/p21/2026-10-14/s1/logs/`: gate output (`step3-quick.log`, `step3-verify.log`, `step3-modules-e2e.log`) and `materialize-1.log`.
- `~/.local/state/vendomat/p21/2026-10-14/s1/devenv-modules/`: the materialized fork tree.
- Testee reports: `~/.local/state/testee/repos/e6fc47612c7a1650/slots/s1-module-fork-e9b1bf67/runs/<run id>/report.json`.

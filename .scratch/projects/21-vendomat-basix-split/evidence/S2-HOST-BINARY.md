# S2: the patched host devenv binary, built from Vendomat's flake — 2026-10-14

Slice S2 of the implementation guide. This record changes the Vendomat repository (two patches, one
overlay, three flake outputs, one fixture file, one Testee task). It builds one binary and keeps it
under a GC root. No host profile change, no host disk, no Attic, no upstream contact, no push.

## Goal and rulings

Build `pkgs.devenv` of the pinned nixpkgs with patches 0003 and 0005, from the Vendomat flake, and
prove it with fixtures B2, B5, and B6.

- R31: the binary carries 0003 and 0005 and no 0008. Patch 0005 splits: the Rust half (`machines.rs`)
  is in this binary, and the module half ships in the module fork (S1).
- R34: no upstream pull request. The patches stay in this repository. Patch 0003 mirrors upstream PR
  #3244. A nixpkgs bump rechecks that PR.
- R39: no Attic. The binary stays in the building machine's store under a GC root. No slice pushes it
  to a cache.

## Inputs

| Item | Value |
| --- | --- |
| nixpkgs pin | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (unchanged in `flake.lock`) |
| Source | `devenv` 2.4.0 of that nixpkgs (stock `/nix/store/5sbcspxmvsj6g41dmv20flpvj9v8pzi8-devenv-2.4.0`) |
| `devenv-dist/binary/patches/0003.patch` | sha256 `c4a121b9d237740e47243754a3ec6c6b9d7dc83e7fb05f019b6e769052aaa1c5` |
| `devenv-dist/binary/patches/0005.patch` | sha256 `85eea6e22e52fdc3103381a69fa9765305433b4273d0e728e553123c0aedd2a3` |
| Overlay | `nix/devenv-overlay.nix` |
| Testee | 0.7.0 for the first GREEN run, 0.8.0 for all later runs |
| Vendomat change | `pnwmwprpwmlz` (workspace `s2-host-binary`), rebased on local `main` `722f7b34` (S1) |

The patches are the W6 patches (`devenv-dist/patches/0003` and `0005`), copied byte for byte. The older
`devenv-dist/patches/` series stays until S6.

### The overlay and the spike

`nix/devenv-overlay.nix` descends from the W6 spike overlay
(`~/.local/state/vendomat/p21/2026-10-13/w6-host-binary/devenv-vendomat-overlay.nix`). The differences:

- The argument `patchDir` is now required. The spike defaulted it to `./patches`. The flake passes
  `./devenv-dist/binary/patches`.
- The argument `with0008` and the 0008 line are gone (R31).
- The argument `skipChecks` stays, with default `false`. It sets `doCheck = false` when true. The
  flake never sets it, so the build runs the test phase.
- The comment names the new paths. The `filterdiff -x '*/CHANGELOG.md'` step stays, because the
  `CHANGELOG.md` hunk of 0003 needs patch 0001.

## Flake changes

`flake.nix` (the diff is on top of S1's two inputs; no input changed):

- `devenvOverlay = import ./nix/devenv-overlay.nix { patchDir = ./devenv-dist/binary/patches; };`
- `devenvFor system` imports nixpkgs with that overlay and returns `.devenv`.
- New output `overlays.devenv = devenvOverlay`.
- New output `packages.<system>.devenv = devenvFor system`.
- `packages.<system>.launcher` now calls `mkLauncher { devenvFork = "${devenv}/bin/devenv"; }`. The
  fixed store path `defaultFork` (the `v2.4.0-vendomat.4` binary) is removed.

`nix eval .#packages.x86_64-linux.devenv.drvPath` gives
`/nix/store/1qabl9qb2zhm5ggqrw25x5cr6v67p79b-devenv-2.4.0.drv` before and after the rebase on S1.
`AGENTS.md` names the outputs and the new opt-in task.

## The build

| Item | Value |
| --- | --- |
| Command | `nix build .#devenv --out-link ~/.local/state/vendomat/roots/devenv-s2-build` |
| Start and end | 2026-10-14T13:31:44Z to 14:43:41Z (72 min), exit 0 |
| Store path | `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0` |
| `devenv version` | `devenv 2.4.0 (x86_64-linux)` |
| NAR hash | `sha256-ef9WVFzW+JIst6xnUUi+42MCv1ePgF2/ksi7juhWmn4=` |
| NAR size | 228189168 bytes |
| Closure size | 482575576 bytes |
| Test phase | cargo nextest: `284 tests run: 284 passed, 1 skipped` |

The build phase took 29 min 17 s and the check phase 36 min 43 s (`build.log`).

Facts about the test phase, observed with `nix eval` on the pinned nixpkgs:

- `devenv.doCheck` is `true` in nixpkgs, and the overlay does not change it.
- The package uses `cargoNextestHook`. Its flags are `-p devenv -- --skip waits_for_previous_proxy_to_release_control_socket`.
- The one skipped test is therefore the nixpkgs skip, not a Vendomat choice.
- The patched build runs the three new 0005 unit tests with the rest. They pass.

The stock store path differs from the patched one, as the drv path does. Stock and patched closures
share every path except the devenv output itself (W6 B1 observed the same).

## The GC root

`~/.local/state/vendomat/roots/devenv-s2-build` is a symlink that `nix build --out-link` made. It is an
indirect GC root through `/nix/var/nix/gcroots/auto`. The root keeps the binary, and the closure
paths it needs, in the store. The binary is not in any cache (R39).

## Fixtures

The fixtures live in `tests/test_binary_e2e.py` with `tests/fixtures/binary-e2e/`. The opt-in task
`opt:binary-e2e` runs them. The binary under test is `devenv` on `PATH`. The control is the stock
`pkgs.devenv` of the pinned nixpkgs. B5 and B6 use the module fork tag
`v2.4.0-vendomat-modules.1` (the published S1 tag) as the workspace `devenv` input; no override.

Command:

```text
PATH=$HOME/.local/state/vendomat/roots/devenv-s2-build/bin:$PATH testee verify opt:binary-e2e
```

| # | Test | Ledger | Expected | Actual (observation) |
| --- | --- | --- | --- | --- |
| B2 | `test_b2_patched_binary_enters_offline_with_a_locked_git_input` | `VMT-074` | With the source in the store, the fetcher cache empty, and the remote stopped, stock fails and the patched binary enters | Stock: exit non-zero, `Failed to fetch git repository 'git://127.0.0.1:PORT/extra.git'` and `Connection refused`. Patched: exit 0, `EXTRA=/nix/store/…-source`, `b2 data`. |
| B5 | `test_b5_install_of_an_adopted_machine_is_refused_before_any_contact` | `VMT-099`, `VMT-106` | `machines install` refuses a machine marked `adopt-existing` before it contacts the target; the running VM stays unchanged | Three install forms refused (`running`, `running --phases reboot`, `unmarked running`) with the text ``Refusing to install: machines.running set `vendomat.mode = "adopt-existing"` `` and `devenv made no connection to the target`. The VM kept its boot id, `/root` listing, store counts, and had no `/root/kexec`. sshd logins grew 3, 4, 5, one per probe. The unmarked and fresh machines passed the refusal and stopped at `Preflight probe failed` on a closed port. The control: stock ignored the mark on `adopted-closed` and stopped at the preflight. |
| B6 | `test_b6_patched_binary_enters_a_catalog_workspace` | `VMT-099` (binary half, catalog) | The binary enters a workspace made from the workspace template and the catalog; a bad entry names file, line, and field; a machine marked adopted is refused | Entered. `GREETING=hello-b6` and `rg` from the store. The bad program gave `vendomat.yaml:2:5: programs[0]: unknown program "vendomat-no-such-package-7319"`. The adopted machine `demo` was refused by the patched binary and reached the preflight under stock. |

### Hand runs before the Testee run

Before Testee could run the opt-in task, I ran the same steps by hand and with a small driver
(`driver.py`, which calls the three test functions without the pytest runner). Logs are under
`~/.local/state/vendomat/p21/2026-10-14/s2/binary-e2e/`.

- `hand/b2.log`: stock fails, patched enters (`EXTRA=/nix/store/r495y8z6…-source`, `b2 data`).
- `hand/b5-run.log`: the same refusals; boot id `2d5a0ac2…` unchanged; sshd logins 3, 4, 5 (one per probe).
- `hand/b6.log`: `GREETING=hello-b6`, `rg`, and the line-and-field error.
- `driver-20261014T170837Z-final/driver-output.txt`: `b2: PASS`, `b5: PASS`, `b6: PASS`.
- `driver-negative-hostpath/`: the driver on the older `PATH` binary `2.4.0+b904dcb` (not this one). It stops at the stock-binary check, as designed.

### Testee run of the fixtures

Run `20261014T182736Z-e8b7d16bba14` (Testee 0.8.0): `opt:binary-e2e` passed, 3 tests, 0 failures,
0 skips, 104 s. Fixture logs: `~/.local/state/vendomat/p21/2026-10-14/s2/binary-e2e/20261014T182737Z/`.
Disk guard in the test read 17.87 GiB unallocated and 72.0 % metadata before the VM build. The
VM image and scratch were under `/mnt/shared/vendomat-p21/s2/`. QEMU exited with status 0.

B5 facts of that run (`notes.log`): boot id `06b21f85-66ad-4a69-b5ae-5a55f9b4ccdd` in all three probes,
`/root` = `.nix-channels .ssh`, closure count 588, `kexec` absent, uptime 12.36 s, 13.05 s, 14.28 s.

Inference: the refusal runs before any contact, because the boot id, the files, and the login count
did not change from any install form. The test cannot see a connection that sshd does not log. The
closed-port control and the message "made no connection" support the claim; they do not prove it alone.

### The B6 finding: the slice-1 catalog needs a primop

The slice-1 catalog (`vendomat-slice1-primop` copy, `hand/b6-primop.log`) reads `vendomat.yaml`
through the fork primop `vendomatFromYAML` (patch 0009). The S2 binary lacks that patch. Observation:
`devenv shell` on the S2 binary stopped with `vendomat.yaml: this devenv has no vendomatFromYAML
primop. Put the Vendomat devenv fork first on PATH.`

The S3 catalog parses the file in plain Nix (`devenv/parse.nix`). Observation: B6 passes with the S3
catalog and the S2 binary. Inference: with the S3 catalog the host binary needs no primop, so patch
0009 can retire (S6). The test fails with a clear message if a catalog asks for the primop.

### B6 template changes

The template `templates/workspace/devenv.yaml` has two inputs that B6 removes: `nixpkgs-python` and
`rust-overlay`. The test drops them because they fetch from GitHub and the B6 shell needs no Python or
Rust version. The test asserts that both names are gone. The test also sets `vendomat` to a copy of this
repository (`path:`), and `devenv` to the module fork tag instead of `follows: vendomat/devenv`.
The copy goes to the pytest temporary directory. The test does not write into the repository.

## Testee runs

| Run | Tool | Check | Verdict | Subject |
| --- | --- | --- | --- | --- |
| `20261014T133210Z-037d0626da81` | 0.7.0 | `testee verify` | GREEN | before the Testee change, on the old parent |
| `20261014T181957Z-9658cc3a5e59` | 0.8.0 | `verify --profile quick` | PASS | after the rebase, tree `567386e420`, commit `ecc116f2d8` |
| `20261014T182014Z-36de1026e109` | 0.8.0 | `verify` | GREEN 4/4 | same |
| `20261014T182038Z-1a894536791a` | 0.8.0 | `opt:binary-e2e` | NO VERDICT (I stopped it) | the disk guard read 14.87 GiB unallocated; the stop limit is 15 GiB |
| `20261014T182736Z-e8b7d16bba14` | 0.8.0 | `opt:binary-e2e` | passed (3 tests, 0 fail, 0 skip, 104 s) | same tree, patched binary first on `PATH` |
| `20261014T182955Z-9403908924cc` | 0.8.0 | `opt:modules-e2e` | passed (6 tests, 0 fail, 0 skip, 247 s) | same tree, stock devenv from `PATH`; S2's flake change did not disturb S1 |
| `20261014T183424Z-6a72f3510974` | 0.8.0 | `verify --profile quick` | PASS | after the ledger, plan, and evidence edits, tree `5df8f92ac8`, commit `935b89f0df` |
| `20261014T183425Z-a6ac64a2000e` | 0.8.0 | `verify` | GREEN 4/4 | same |

Adding these run IDs to this file changed the tree again. A last `verify --profile quick` and `verify` ran on the final commit; the hand-off report names them.

## Deviations

1. **Hand runs.** Testee was not available when the fixtures first ran, so B2, B5, and B6 ran by hand
   and through `driver.py`. The Testee run above repeats them.
2. **Testee version.** Testee changed from 0.7.0 to 0.8.0 during the session. Only the first GREEN run
   used 0.7.0. The 0.8.0 runs use the devenv tasks in `nix/tasks.nix`.
3. **B6 template.** The test drops `nixpkgs-python` and `rust-overlay` (see above).
4. **Disk guard stop.** The first Testee run of `opt:binary-e2e` started while the host held 14.87 GiB
   unallocated (17.87 GiB a few minutes earlier; another job wrote 3 GiB and freed it). I stopped it
   with SIGTERM and waited. Unallocated returned to 17.87 GiB. The second run is the one that counts.
5. **QEMU memory lock.** As in S1, QEMU needs `RLIMIT_MEMLOCK` at 64 KiB on this host. The test lowers it
   in the child.
6. **Overlay `skipChecks`.** The argument stays in the overlay for a quick local build. The flake does not
   use it.

## Host switch (owner gate)

The owner approved the switch on 2026-10-14 (R48) and ran it the same day. The owner reported
"Rebuilt". Observed after the switch:

- `/run/current-system` is `/nix/store/mqsc6x484fbvj2dmk6nmhsspnpvnrjwa-nixos-system-server-26.11.20260705.d407951`,
  the path built below. The previous generation is `wgnhiw8d…`.
- `/etc/profiles/per-user/andrew/bin/devenv` resolves to
  `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0/bin/devenv`; `devenv version` prints
  `devenv 2.4.0 (x86_64-linux)` (the old build printed `2.4.0+b904dcb`).
- `systemctl --failed` lists no unit.
- A process that started before the switch keeps the old store path `axhrys71…-devenv-wrapped-2.4.0`
  on its inherited `PATH`. A new login shell gets the profile path.

- Change: nix-meta `main` `cf8ef3cc` (pushed). New input `vendomat-host`
  (`git+file:///home/andrew/Documents/Projects/vendomat?rev=465ce48f…`). `profiles/developer.nix`
  takes `pinnedDevenv` from `inputs.vendomat-host.packages.<system>.devenv`.
- Evaluation: the home package list of `server` holds
  `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0`, the S2 path under the GC root.
- Build: `nix build .#nixosConfigurations.server.config.system.build.toplevel` gave
  `/nix/store/mqsc6x484fbvj2dmk6nmhsspnpvnrjwa-nixos-system-server-26.11.20260705.d407951`, out link
  `~/.local/state/vendomat/roots/server-host-devenv-switch`. It built 30 small derivations and no devenv.
- `nix store diff-closures /run/current-system` to that path: `devenv-wrapped: 2.4.0 → ∅`,
  `devenv: ∅ → 2.4.0`, and the libraries of the patched build (Nix 2.35 libraries, `curl`, `xz`,
  `libgit2` and others). No service or unit changed.
- Switch: `sudo nixos-rebuild switch --flake ~/Documents/Projects/nix-meta#server`.
- Rollback: `sudo nixos-rebuild switch --rollback` (the previous NixOS generation).

## Raw logs

- `~/.local/state/vendomat/p21/2026-10-14/s2/`: `build.log`, `build.start`, `build.end`, `build.exit`, gate logs.
- `~/.local/state/vendomat/p21/2026-10-14/s2/binary-e2e/`: hand runs, driver runs, and the Testee run directory `20261014T182737Z`.
- Testee reports: `~/.local/state/testee/repos/e6fc47612c7a1650/slots/s2-host-binary-172c18d7/runs/<run id>/report.json`.
- VM scratch under `/mnt/shared/vendomat-p21/s2/`.

# Slice 1, lane A: fork patch 0009 (`vendomatFromYAML`)

Date: 2026-10-12. Serves DOOR-074 (the fork carries the primop as patch 0009) and DOOR-075 (the strict
YAML subset and `vendomat.yaml:LINE:COL: reason` errors). Raw logs: `~/.local/state/vendomat/p20/2026-10-12/slice-1/A-fork/`
(`$L` below).

## Inputs and versions

| Item | Value |
| --- | --- |
| Spike patch | `evidence/fixtures/p2g/0009-vendomat-add-the-vendomatFromYAML-primop.patch` (P2G) |
| Case files | `evidence/fixtures/p2g/cases/*.yaml`, 27 files |
| Base | upstream `cachix/devenv` `v2.4.0`, `b904dcb51fe48c30db250038241507f60752f222`, plus patches 0001 to 0008 = `fb5d382b822f6ecf58365a77f2f872ba6f7ce79d` |
| New fork commit | `c66ba8754c0e57971e6f27824b088c95f375f406` (patch 0009 on `fb5d382b`) |
| Patch sha256 | `3ce1b78dc4f68f1b552cef88cf530eb9bf7ec51e3c6fbd8d6ac03644fbec27ad` |
| Toolchain for the tests | the materialized tree's own devenv shell: stock `devenv 2.4.0+b904dcb`, `rustc 1.97.1` |
| Fork binary | `/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0`, `devenv 2.4.0+c66ba87` |
| Disk gate before the build | unallocated 25.09 GiB, metadata 74.00 %. After: 21.09 GiB, 77.77 %. |

## Steps, expected results, actual results

1. Materialize the current series (0001 to 0008) into `$L/src8`. Expected: commit `fb5d382b`.
   Actual: `fb5d382b`. Command: `python3 -I devenv-dist/materialize $L/src8 --source <P2G source copy>`.
   Log: `$L/materialize-0008.json`. The `--source` copy is a local mirror with tag `v2.4.0`. The script checks
   the tag commit against `UPSTREAM`.
2. Apply the spike patch with `git apply`. Replace its 3 hand tests with 27 tests, one for each case file. Name
   each test `case_<file>` with `-` written as `_`. Each accept case asserts the exact tree with `json!`. Each
   reject case asserts the full error text, including `LINE:COL`. Commit as `Vendomat Fork`, dated
   `2026-10-12 00:00 +0000`.
3. Run the unit tests: `devenv shell -- cargo test -p devenv-nix-backend yaml_subset` in `$L/src8`.
   Expected: 27 pass. Actual: `test result: ok. 27 passed; 0 failed; 0 ignored; 0 measured; 55 filtered out`.
   Log: `$L/unit-test.log`. The log mixes the output of two overlapping `devenv shell` starts (I started
   the command twice by mistake; one `npm` step failed from the clash). The `cargo test` that ran was one process.
4. Make the patch file: `git format-patch -1 --no-signature --zero-commit`, then the subject number set to
   `[PATCH 9/9]`. The header has the fixed `From 0000...` line, the author `Vendomat Fork`, the date, and an
   `Upstream: fork-only.` line, like 0001 to 0008. Add it to `SERIES` and `MANIFEST.sha256`.
5. Materialize the full series into `$L/src9`. Expected: the tree of `$L/src8`. Actual: both trees are
   `4c6fa867b3559511cbc0cc5f66de194a4c80d0d3`, so the patch applies cleanly after 0008. Fork commit
   `c66ba875...`. Log: `$L/materialize-0009.json`.
6. Write `RESULT` (`fork_commit=c66ba875...`). Run `materialize $L/src9v --source <mirror> --verify`.
   Expected: exit 0. Actual: exit 0, commit `c66ba875...`. Logs: `$L/materialize-verify.json`, `.err`.
7. Build: `nix build .#devenv -o $L/result-devenv --print-build-logs` in `$L/src9` (clean git tree). Exit 0.
   Log: `$L/build.log`. The out-link `$L/result-devenv` is the GC root. `result-devenv/bin/devenv version`
   prints `devenv 2.4.0+c66ba87 (x86_64-linux)`.
8. Smoke test: `sh $L/smoke.sh $L/result-devenv/bin/devenv <p2g/workspace> $L/smoke-ws`. Log: `$L/smoke.log`.
   The log starts with `devenv 2.4.0+c66ba87`.

   | Case | Expected | Actual |
   | --- | --- | --- |
   | valid `vendomat.yaml` (P2G `base`) | shell starts, data visible | `SEEN PYV=3.10 EN=true NAME=no PROG=ripgrep,jq`, exit 0 |
   | tab on line 4 | exit 1, `vendomat.yaml:4:1` | `error: Error from custom function: vendomat.yaml:4:1: tabs are not accepted; use spaces`, exit 1 |

9. Add repository test `test_patch_0009_adds_the_yaml_primop_with_one_unit_test_for_each_spike_case` to
   `tests/test_devenv_dist.py`. It checks the patch text (primop name, plugin, 27 `fn case_` tests).

## What this proves

- Patch 0009 applies cleanly after 0008 and the materialize recipe reproduces the commit (`--verify` passes).
- The Rust parser gives the stated tree or the stated error with `LINE:COL` on all 27 case files.
- The built fork reads a valid file through the primop and fails a tab with `vendomat.yaml:LINE:COL`.

## Observation versus inference

- Observation: all results above. The unit tests ran in a debug build of the crate, not in the Nix build.
- Observation: the P2G record says "13 trees, 14 errors" for the 27 cases. The case list gives 9 accepted
  trees (`base`, `good`, `traps`, `err-maybe`, `err-no`, `err-yes`, `err-traps`, `err-twoerr`, `err-typo`)
  and 18 errors. The 27 total is right; the split in P2G is wrong. The tests use 9 and 18.
- Inference: the 27 expected values come from the P2G Rust output (`q9-difftest.log`, which matched the
  P2F Python reference 27 of 27) and not from an independent oracle. The case files state no expected value.
- Inference: the unit tests would catch a drift of the subset rules. Mutation checks were not run.

## Not done

- `UPSTREAM` and `RESULT` still say `fork_tag=v2.4.0-vendomat.3`. The tag `.3` names commit `fb5d382b`. The
  new series gives `c66ba875`. The release step must set `fork_tag=v2.4.0-vendomat.4` in `UPSTREAM` and
  `RESULT` and change the pin in `tests/test_devenv_dist.py::test_the_upstream_pin_names_tag_and_commit`.
  The orchestrator owns the tag. I did not create it, publish it, or change the pin.
- `materialize` used a local mirror (`--source`) for the upstream clone, not the GitHub URL. The tag commit check
  is the same.
- `devenv-core` tests and the other `devenv-nix-backend` tests did not run (55 filtered out, by name).
- The Nix build did not run the unit tests (crate2nix has no `runTests`).

## How the host and Vendomat consume the fork today

All facts are observations from file reads on 2026-10-12. No pin changed.

- The `devenv` on the host PATH is stock: `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0`,
  `devenv 2.4.0+b904dcb`. The pin is `~/Documents/Projects/nix-meta/flake.nix:37`
  (`devenv.url = "github:cachix/devenv/v2.4.0"`), installed by `nix-meta/profiles/developer.nix:10` (`pinnedDevenv`).
- `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0` (`devenv 2.4.0+fb5d382`, the `.3` fork) is on no
  profile or flake. Its only GC root is `~/.local/state/vendomat/v7/2026-10-11/result-devenv-3`.
- The Vendomat flake (`flake.nix`) has one input, `nixpkgs`, and carries no fork pin.
- The recipe is `devenv-dist/UPSTREAM:5` and `devenv-dist/RESULT:2-3` (`fork_tag`, `fork_commit`).
  `devenv-dist/fixtures/dist-fixture:29-37` reads `fork_tag` from `UPSTREAM`.
- The fork modules reach a workspace as a git tag in the collection (`git://server/devenv`). The tag `v2.4.0-vendomat.3`
  was published through `~/.local/state/vendomat/v7/2026-10-11/publish-3.log` (commit `fb5d382b`).
- A workspace pins that tag in its own `vendomat.toml` `[inputs]`:
  `~/Documents/Projects/vendomat-demo/vendomat.toml:10` (`.3`), `~/Documents/Projects/nix-systems/vendomat.toml:13`
  and `:28` (`devenv-cli`, `.2`). `vendomat sync` writes the tag into `.vendomat/devenv.yaml`.
- The registry template renders the pin: `templates/workspace-registry/template.j2:10-11` with input
  `devenv_tag` (example: `templates/workspace-registry/examples/default.input.json:4`).
- Other places that name `v2.4.0-vendomat.3`: `tests/test_devenv_dist.py:57`, `tests/test_registry_v6.py:62,66`,
  `tests/test_commands_v6.py:186,191`, `templates/workspace-registry/examples/default.output.toml:10`.
- Inference: no host-wide fork CLI is installed. A fork CLI runs only when a shell puts it first on PATH (by
  absolute path or a GC root). Lane D must decide how the host gets the `.4` CLI.

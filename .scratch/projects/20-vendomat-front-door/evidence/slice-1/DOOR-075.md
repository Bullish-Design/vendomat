# `DOOR-075`: YAML catalog gate

Date: 2026-10-12. Result: the catalog gate passes on the `.4` fork build.

## Inputs and versions

| Item | Value |
| --- | --- |
| Fork | `devenv 2.4.0+c66ba87` |
| Primop | `vendomatFromYAML`, patch 0009 |
| Unit cases | 27 YAML fixtures from P2G |
| Testee | `0.6.1`, with `.4` first on `PATH` |
| Gate | `testee verify front-door-e2e` |
| Raw logs | `~/.local/state/vendomat/p20/2026-10-12/slice-1/F-front-door/` |
| Fork record | [Patch 0009 record](A-fork-patch.md) |

## Observations

- Patch 0009 passed 27 Rust tests. The fork materialized and built as `2.4.0+c66ba87`.
- Unknown keys, a bad used value, a bad unused value, and an unknown program stopped `shell`,
  `test`, `build shell`, `build outputs.hello`, and `tasks run` before user work.
- One run listed the bad program, invalid Python enable, unknown Python key, missing JavaScript
  version, invalid Postgres enable, invalid environment value, and unknown top-level key.
- A tab on line 3 failed as `vendomat.yaml:3:1`. `3.10` and `name: no` stayed text. `enable: no`
  failed its typed option.
- A valid `build outputs.hello` passed even though that output reads no catalog value. An invalid
  catalog then stopped the same build during evaluation.
- Testee returned RED for a valid `CATALOG_VALUE: 3.11` because the consumer check expected
  `3.10`. For `enable: no`, Testee refused evaluation with exit 2 before running a check. Restoring
  the valid file returned GREEN. Testee 0.6.1 does not report an evaluation refusal as RED.

## Commands and results

| Command | Expected | Actual | Log |
| --- | --- | --- | --- |
| `devenv shell -- cargo test -p devenv-nix-backend yaml_subset` | Pass all spike cases | 27 passed | `A-fork/unit-test.log` |
| `nix build .#devenv` | Build the fork | Exit 0; `2.4.0+c66ba87` | `A-fork/build.log` |
| Catalog fault matrix | Stop each command before user work | All 20 command/case pairs failed with a `vendomat.yaml` field error; no marker appeared | `fault-*.log` |
| Combined invalid file | List each fault | Every expected field appeared in one error | `all-faults.log` |
| Syntax fault | Report line and column | `vendomat.yaml:3:1` | `syntax-line-column.log` |
| Testee valid edit, invalid value, restore | RED, refusal, GREEN | RED, exit 2 refusal, GREEN | `testee-red.log`, `testee-invalid-refusal.log`, `testee-green-again.log` |

## Limits

The module and catalog gate used the real Vendomat source from the throwaway release repository.
The source URL was local. The published `.4` tag and `git://server/vendomat?ref=release` branch
still need a read-side smoke check. The Testee RED result requires a valid value that fails the
consumer's check. Invalid catalog evaluation produces a refusal, not RED.

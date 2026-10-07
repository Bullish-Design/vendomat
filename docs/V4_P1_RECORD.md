# V4 P1 record

**Date:** 2026-10-06. **Result:** The P1 checks pass on the pinned tools. No other phase passed.

P1 is the first proof module. It lives in its own repository, `nvim-review`, not in Vendomat.
Vendomat added no code for P1. This record cites the module repository and its raw logs.

## Inputs and versions

| Item | Value | Source |
| --- | --- | --- |
| Nix | 2.34.7 | `nix --version` |
| devenv | 2.4.0+b904dcb | `devenv --version` |
| Module repository | `nvim-review` at `215f02d85f4a066b4f54c30ab86ac8a8dcf321a9` on `main` | `gitman status` |
| nixpkgs | `151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4` | `flake.lock` |
| home-manager | `fae6e9e42c3b762ab47635cddcfaf6f52374a61b` | `flake.lock` |
| Neovim | 0.12.5 | `nix build` output |
| System | `x86_64-linux` | `flake.nix` |
| Proof script | `tests/p1-proof.sh` in `nvim-review` | repository |

## Command and result

Run the proof from the `nvim-review` root:

```sh
tests/p1-proof.sh ~/.local/state/vendomat/v4-proof/2026-10-06/p1/run-3
```

The final run, `run-3`, passed all checks on the final commit. Its summary is `run-3/summary.txt`.
Raw output is in the same directory. Runs `run-1` and `run-2` also passed. They were made before the
final commit, and they are kept for provenance. Two failed attempts before `run-1` are not kept. They
found a wrong plugin path and a process check that matched too widely. Both are fixed in the script.

## Checks

| Step | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| 1 Command | Result equals the expected document | Equal | `command-actual.json`, `command-expected.json` |
| 2 One implementation | Plugin Lua and editor closure name one command | Both name `/nix/store/7lr8dshj…-nvim-review` | `plugin-command-path.txt`, `editor-closure-review.txt` |
| 2 Conflicting `PATH` | A fake `nvim-review` first on `PATH` does not run | Editor output equals expected | `dedicated-expected.txt` |
| 3 Override | `maxLength = 40` changes only the limit and the line-2 message | Diff has 4 changed lines and nothing else | `max40-diff.txt` |
| 3 Targets | Each target evaluates alone. Import adds no package. Editor off keeps the command | As expected | `eval-targets.json` |
| 4 No Vendomat process | No process named `vendomat` | None | `vendomat-processes.txt` |
| 4 Bare run | Command runs with an empty environment | Two findings | script step 4 |
| 4 Normal editor | Normal profile keeps `tabstop = 2` and does not load the dedicated profile | As expected | `normal-expected.txt` |
| 4 Isolation | Dedicated editor does not load the normal config | As expected | `isolated-expected.txt` |
| Check set | `nix flake check` passes | All checks passed | `flake-check.log` |
| Consumer | Consumer shell has the command and the editor, not the author tool | As expected | `consumer-shell.txt` |

## Requirement IDs observed

| ID | Observation |
| --- | --- |
| `V4-OWN-002` | No Vendomat file or process is involved. The consumer shell enters without registration. |
| `V4-OWN-003` | The command runs with an empty environment and no Vendomat process. Nix and Attic are not used in that run. |
| `V4-OWN-007` | Changing `maxLength` changes the output, with no Vendomat database edit. The report refresh is not a P1 feature. Partly observed. |
| `V4-MOD-001` | Three native exports exist. Each evaluates alone. |
| `V4-MOD-002` | The consumer shell has the command and not `shellcheck`, the author tool. |
| `V4-MOD-005` | Defaults evaluate. The editor can be disabled while the command stays. `maxLength` changes only its intended output. |
| `V4-MOD-008` | The plugin and the editor both use one command path. |
| `V4-MOD-009` | The editor calls the command by absolute store path. A conflicting `PATH` entry does not change the result. |
| `V4-MOD-010` | The dedicated and normal editors keep separate configuration. |

## Gaps

- The guide names scenarios `V4-PROOF-001`, `V4-PROOF-002`, and `V4-CHK-013` for P1. It gives no
  text for them. This record cites the P1 steps as their evidence. The owner must define them.
- The NixOS and home-manager targets evaluate. Neither is built or activated. The P1 gate does not
  require activation.
- Step 4 denies no substituter. The run uses no Nix. It shows that the command needs no Attic.
- The proof runs on one machine. No second machine has run it.
- `V4-SEL-010` and `V4-EVD-012` belong to P2 and P4. P1 does not observe them.

## Gate

The P1 checks passed on 2026-10-06 in run 3. The gate makes no publication claim and no machine
claim. P2 needs a git root for `MOD-013`. That is `BLK-P2-01`, and it is still open.

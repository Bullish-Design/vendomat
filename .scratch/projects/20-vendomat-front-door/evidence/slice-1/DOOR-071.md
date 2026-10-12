# `DOOR-071`: host command gate

Date: 2026-10-12. Result: the host command passes its local gate on the patched fork.

## Inputs and versions

| Item | Value |
| --- | --- |
| Fork | `devenv 2.4.0+c66ba87`, `/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin/devenv` |
| Host launcher | Built from `.#launcher` in the Testee workspace |
| Testee | `0.6.1`, `/home/andrew/.nix-profile/bin/testee` |
| Gate | `testee verify front-door-e2e`, with the fork directory first on `PATH` |
| Raw logs | `~/.local/state/vendomat/p20/2026-10-12/slice-1/F-front-door/` |

## Observations

- `vendomat new DIR` wrote the four template files. A bare `vendomat` entered the fork shell.
- `vendomat version` reached the fork. An unknown command returned the fork's exit code 2.
- Lane D's Testee check used a fake fork to prove exit status 7 and signal forwarding. See
  [D host command](D-host-command.md).
- The launcher wrapper contains the `.4` fork path. A store reference query did not list the fork.
  A host flake should call `mkLauncher` with its locked fork package to keep that package in the
  host closure. The host profile was not changed here.

## Commands and results

| Command | Expected | Actual | Log |
| --- | --- | --- | --- |
| `nix build --no-link --print-out-paths .#launcher` | Build the launcher | Exit 0 | `build-launcher.log` |
| `vendomat new DIR` | Copy the fixed template | Four files copied | `vendomat-new.log` |
| `vendomat` in the workspace | Enter the fork shell | Exit 0 | `vendomat-bare-entry.log` |
| `vendomat version` | Pass through to the fork | Printed `2.4.0+c66ba87`, exit 0 | `vendomat-pass-through.log` |
| `vendomat front-door-unknown-command` | Return the fork status | Exit 2 | `vendomat-unknown-command.log` |

## Limits

The test uses a launcher build and explicit fork path on this host. It does not prove that a
future system profile retains the fork after store garbage collection. The host profile still puts
stock devenv first on its normal PATH. The Testee gate therefore needs the explicit PATH prefix.

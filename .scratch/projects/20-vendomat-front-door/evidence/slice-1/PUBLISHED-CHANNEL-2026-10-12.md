# Slice 1 published-channel smoke, 2026-10-12

Result: the fork tag and Vendomat release branch are published. A fresh workspace loaded the
catalog through the live collection and entered the fork shell.

## Inputs

| Item | Value |
| --- | --- |
| Vendomat main and release | `d3c279e02c41649addfdd0715a7aadb6159e975b` |
| Vendomat release ref | `refs/heads/release` |
| Fork release tag | `v2.4.0-vendomat.4` |
| Fork tag target | `c66ba8754c0e57971e6f27824b088c95f375f406` |
| Fork executable | `/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin/devenv` |
| Fork version | `devenv 2.4.0+c66ba87 (x86_64-linux)` |
| Launcher | `/nix/store/8kb2xpl4307vw8dbdpghiq0xc5r4fzmx-vendomat-launcher-0.7.0-rc.1/bin/vendomat` |
| Nix-meta hook change | `0640a6c905f3c76719ec56a9382fc47d484b393b` on `main` |
| Raw logs | `~/.local/state/vendomat/p20/2026-10-12/slice-1/published-channel/` |

## Observations

- The collection pre-receive hook was refreshed by landed `nix-meta` `main`.
- The hook file is executable at `/home/andrew/vendor/vendomat/.git/hooks/pre-receive`.
- The collection accepted the new fork tag and the new Vendomat `release` branch.
- Git daemon lookup returned the `.4` tag, peeled to the expected fork commit.
- Git daemon lookup returned Vendomat `release` at `d3c279e02c41649addfdd0715a7aadb6159e975b`.
- `vendomat new` created a fresh workspace with `vendomat.yaml`, `devenv.yaml`, `devenv.nix`, and `.gitignore`.
- The first fork shell fetched the real collection branch and wrote `devenv.lock`.
- The lock records both original and locked ref as `release`, with the expected revision.
- The Vendomat launcher passed `shell --no-tui -- bash -c ...` to the pinned fork.
- The shell printed `CHANNEL=release`, found `ripgrep` in the Nix store, and printed `ripgrep 15.2.0`.

## Commands and results

| Command | Expected | Actual | Log |
| --- | --- | --- | --- |
| `nix build .#packages.x86_64-linux.launcher --no-link --print-out-paths` | Build the host launcher | Exit 0; launcher path recorded above | `launcher-build.log` |
| `vendomat new DIR` | Create a fresh workspace | Four template files created | `vendomat-new-final.log` |
| `vendomat shell --no-tui -- bash -c ...` | Pass the command to the pinned fork | Exit 0; expected environment and `ripgrep` output; log starts with `devenv version` | `final-smoke.log` |
| `jq -e ... devenv.lock` | Check source ref and revision | `true` | `final-lock-check.log` |
| `git ls-remote git://server/vendomat refs/heads/release` | Read the published branch | `d3c279e02c41649addfdd0715a7aadb6159e975b` | `remote-refs.log` |
| `git ls-remote git://server/devenv refs/tags/v2.4.0-vendomat.4 ...` | Read the published tag | Tag object `b0428f9c...`; peeled target `c66ba875...` | `remote-refs.log` |

Hook refresh output and the live hook checksum are in `hook-install.log`. The Nix-meta flake check
log is `~/.local/state/vendomat/p20/2026-10-12/slice-1/nix-meta-flake-check.log`.

## Limits

The host profile still selects stock devenv first. The smoke used the `.4` fork explicitly.
The launcher embeds a store path; host packaging must retain the fork in its closure. No host
profile switch, Basix machine gate, or real disk write ran.

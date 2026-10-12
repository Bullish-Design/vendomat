# `DOOR-076`: collection release branch gate

Date: 2026-10-12. Result: the two-VM collection gate passes. The published channel smoke remains.

## Inputs

| Item | Value |
| --- | --- |
| Vendomat tree | `c2f41293da`, commit `f5cd39f078` |
| Nix | `2.34.8` |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` |
| Testee | `0.6.1` |
| Gate | `testee verify e2e` |
| Testee run | `20261012T213552Z-f0e2e647d00a` |
| Collection log | `~/.local/state/vendomat/p20/20261012T213553Z/slice-1/F-infra/infra-collection.log` |

## Observations

- The VM generated the installed `pre-receive` hook from `collection-add`.
- The installed hook matched `hooks/collection-pre-receive` byte for byte.
- The `vendomat` repository accepted creation and fast-forward of `refs/heads/release`.
- The hook refused a rewind, deletion, and `refs/heads/main` in `vendomat`.
- The hook refused `refs/heads/release` in `lib-a`.
- The generic `lib-a` repository still accepted a new release tag and rejected branches and moved tags.
- `testee verify e2e` passed. It ran 395 tests and skipped two in 569 seconds.

## Command and result

| Command | Expected | Actual |
| --- | --- | --- |
| `PATH=/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin:$PATH ~/.nix-profile/bin/testee verify e2e` | Run the NixOS collection, cache, and builder fixtures | Exit 0; all three VM tests passed. |

The raw collection log contains the hook equality and branch result lines. The Testee report and
JUnit file are under `~/.local/state/testee/repos/e6fc47612c7a1650/slots/p20-gates-4fb62778/runs/20261012T213552Z-f0e2e647d00a/`.

## Limits

The VM used a test collection. It did not update the live hook or publish a branch. The
`git://server/vendomat?ref=release` read-side smoke still needs to run after publication.

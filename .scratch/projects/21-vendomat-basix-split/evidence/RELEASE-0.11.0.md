# Release v0.11.0

**Date:** 2026-10-15. **Owner approval:** The agent asked: "Do you approve a Vendomat v0.11.0 release to the
local cache: a tag plus a `release` move, with no GitHub push?" The owner answered, verbatim: "Yes, please do".

## Result

| Item | Value |
| --- | --- |
| Release commit | `b614b6430ecf6b70e70a99cb03ab817a1f22a8eb` ("Release Vendomat 0.11.0"), on `main` and on origin |
| Tag `v0.11.0` | the release commit (lightweight tag, as `v0.10.0`) |
| `release` branch | the release commit, a fast-forward from `c6b36c1e` (`v0.10.0`) |
| Prefetch rev (tag ref) | `b614b6430ecf6b70e70a99cb03ab817a1f22a8eb` |
| narHash | `sha256-TDR3gw7HpqSVMGorUe5xE874GutikLFFHW1il7xHGsU=` |
| Store path | `/nix/store/9fx2y8cb9bwchv5zk7j2vhmihr3yczld-source` |

## Scope

The owner approved the local collection cache only. The tag and `release` went to the remote `collection`
(`~/vendor/vendomat`). Neither ref went to GitHub `origin`. Only `main` went to origin, as for any landing.

## What v0.11.0 adds since v0.10.0 (`c6b36c1e`)

- The list option `vendomat.watch` (R62, `VMT-280`). It adds workspace files to the files that `apply` and
  `rollback` watch. Basix request VR8 is resolved.
- `apply` and `rollback` print the first fault line of a workspace file first (`VMT-281`). VR9 is resolved.
- The fix of patch 0003 for a missing input path (`VMT-184`).
- Version `0.11.0` in `pyproject.toml` and `uv.lock` (edited by hand) and the `README.md` release sentence.

Evidence for R62: [R62-VR8-VR9-WATCH](R62-VR8-VR9-WATCH.md).

## Checks before the release

Tree `0de00fb6c9`, commit `b614b6430e`, Testee 0.8.0.

| Check | Run | Result |
| --- | --- | --- |
| `testee verify` | `20261016T014700Z-3b995dfb77af` | GREEN 4/4 |

The opt-in checks did not run for this release. R62 ran its own checks (see the R62 evidence).

## Commands

```
jj tag set v0.11.0 -r b614b643
jj git push --remote collection --tag v0.11.0
jj bookmark set release -r b614b643
jj git push --remote collection --bookmark release
```

- Before the push, `git ls-remote git://server/vendomat` showed `release` and `v0.10.0` at `c6b36c1e` and no
  `v0.11.0`. The tag push printed `collection: working tree now shows v0.11.0`. The bookmark push printed
  `move forward from c6b36c1e2010 to b614b6430ecf`. No tag moved or was deleted.
- After the pushes, `HEAD`, `refs/heads/release`, and `refs/tags/v0.11.0` are at `b614b643`. Older tags did
  not move.
- `git ls-remote origin` shows no `v0.11.0` tag and no `release` branch on GitHub.

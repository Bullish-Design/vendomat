# Release v0.11.1

**Date:** 2026-10-16. **Owner approval:** The owner answered, verbatim: "Great, do #1". Option 1 was: "Fix VR10 in Vendomat: apply writes the key before its commit and puts it in that commit. Then release Vendomat v0.11.1 to the local cache, bump the Basix pin, and tag `rc.3`." Basix R15 limits every tag and `release` push to the local collection cache.

## Result

| Item | Value |
| --- | --- |
| Release commit | `f86403bdc4bfa9ab4d6962ef409d0c7d1f6926e1` ("Release Vendomat 0.11.1") |
| Tag `v0.11.1` | the release commit (lightweight tag, as `v0.11.0`) |
| `release` branch | the release commit, a fast-forward from `b614b643` (`v0.11.0`) |

## Scope

The tag and `release` go to the remote `collection` (`~/vendor/vendomat`) only. Neither ref goes to GitHub `origin`. Only `main` goes to origin.

## What v0.11.1 adds since v0.11.0

- `apply` writes the public cache key before its commit and puts it in that commit (R63, `VMT-282`). Basix request VR10 is resolved.
- `rollback` keeps the key file (`VMT-283`).
- Version `0.11.1` in `pyproject.toml` and `uv.lock` (edited by hand) and the `README.md` release sentence.

Evidence for R63: [R63-VR10-KEY-COMMIT](R63-VR10-KEY-COMMIT.md).

## Checks before the release

Tree `199df2acef`, commit `f86403bdc4`, Testee 0.8.0.

| Check | Run | Result |
| --- | --- | --- |
| `testee verify` | `20261016T133559Z-c8cdbcfe2cb2` | GREEN 4/4 |

No opt-in check ran.

## Commands

```
jj tag set v0.11.1 -r f86403bdc4bf
jj git push --remote collection --tag v0.11.1
jj bookmark set release -r f86403bdc4bf
jj git push --remote collection --bookmark release
```

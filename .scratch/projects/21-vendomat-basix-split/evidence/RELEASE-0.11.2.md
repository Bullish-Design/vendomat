# Release v0.11.2

**Date:** 2026-10-16. **Owner approval:** The owner answered, verbatim: "Yes, please proceed in a
background sonnet subagent". Option 1 was: "Fix Vendomat and release v0.11.2 to the local cache. A
missing `vendomat.watch` attribute means 'no extra files', so apply carries on with the four fixed
files and prints no error. A real evaluation error still stops apply, with its first line first.
Update the VM test to expect that. Then rerun `opt:machines-vm`. Basix moves its pin at its next
`rc`." Basix R15 limits every tag and `release` push to the local collection cache.

## Result

| Item | Value |
| --- | --- |
| Release commit | `74caad2d90a2ea74eec842d31265e37bc20154a4` ("Release Vendomat 0.11.2: a missing vendomat.watch means no extra files (R64, VMT-284)") |
| Tag `v0.11.2` | the release commit (lightweight tag, as `v0.11.1`) |
| `release` branch | the release commit, a fast-forward from `f86403bd` (`v0.11.1`) |

## Scope

The tag and `release` go to the remote `collection` (`~/vendor/vendomat`) only. Neither ref goes to
GitHub `origin`. Only `main` goes to origin.

## What v0.11.2 adds since v0.11.1

- A workspace whose modules do not declare `vendomat.watch` has no extra watched files. `apply` and
  `rollback` go on with the four fixed files (R64, `VMT-284`).
- `opt:machines-vm` expects the R63 state: a clean working copy after apply and after rollback.
- Version `0.11.2` in `pyproject.toml` and `uv.lock` (edited by hand) and the `README.md` release
  sentence.

Evidence for R64: [R64-WATCH-MISSING](R64-WATCH-MISSING.md).

## Checks before the release

| Check | Run | Result |
| --- | --- | --- |
| `opt:machines-vm` | `20261016T150342Z-e4c94a8a015c` | 12 passed |
| `opt:catalog-devenv` | `20261016T151008Z-ea493b63da88` | PASS |
| `testee verify` | `20261016T151519Z-98609026a439` (tree `880bec855e`, commit `74caad2d90`) | GREEN 4/4 |

## Proof after the push

`git ls-remote git://server/vendomat` shows `refs/heads/release` and `refs/tags/v0.11.2` at `74caad2d90a2`. `git ls-remote` on GitHub `origin` shows neither ref. `main` went to `origin`.

## Commands

```
jj tag set v0.11.2 -r 74caad2d90a2
jj git push --remote collection --tag v0.11.2
jj bookmark set release -r 74caad2d90a2
jj git push --remote collection --bookmark release
```

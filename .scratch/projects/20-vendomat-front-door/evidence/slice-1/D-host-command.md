# Slice 1, lane D: the host `vendomat` command

Date: 2026-10-12. Requirement served: `DOOR-071` (slice 1 builds `new` and the pass-through; `apply`
and `install` come in slice 2). `DOOR-063` holds: the old verbs stay until the release.
Raw logs: `~/.local/state/vendomat/p20/2026-10-12/slice-1/D-host/`.

## Inputs and versions

| Item | Value |
| --- | --- |
| Base | `main` at `de5279e8` |
| Fork | `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv` (log `devenv-version.txt`) |
| Stock devenv (first on PATH) | `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0/bin/devenv` |
| Host `vendomat` today | `/run/current-system/sw/bin/vendomat` is the plain package `vendomat-0.5.0`. It is not the launcher. |
| Built launcher | `/nix/store/km216qa5w335xjnijk4450lcbvvbw0zi-vendomat-launcher-0.7.0-rc.1` (`nix-build-launcher.log`) |

## How the host gets the fork today (observation)

- No host configuration carries the fork CLI. `nix-meta` pins stock devenv (`devenv.url = github:cachix/devenv/v2.4.0`).
- The fork CLI is a package of the fork repository: `git://server/devenv?ref=refs/tags/v2.4.0-vendomat.N#devenv`
  (project 16, `live-release-2026-10-10.md`). A person builds it by hand. The only GC root of the current path
  is `~/.local/state/vendomat/v7/2026-10-11/result-devenv-3`.
- A workspace reads the fork's Nix modules through `devenv.yaml` (`...&dir=src/modules`). That is separate from the CLI.

## The dispatch as built (`launcher/vendomat`)

| First argument | Action |
| --- | --- |
| none | `exec "$fork" shell`, anywhere |
| `new [DIR]` | copy the template files from `<host release>/../share/vendomat/templates/workspace` into DIR (default `.`); refuse with exit 1 and one line when any file exists; make files user-writable; print one next-step line; run no git or devenv; more than one argument is exit 3 |
| `sync`, `path`, `check`, `push`, `bump`, `machine`, `--version`, `--help` | the old logic, unchanged: pinned build for `sync` in a workspace with `vendomat.toml`, a refusal (exit 3) for the others inside such a workspace, the host release elsewhere |
| anything else | `exec "$fork" "$@"` |

Changes to the old logic: the refusal now applies to the old verbs only, because an unknown verb passes to the
fork. `VENDOMAT_USE_HOST=1` now forces the host release for the old verbs only. The old scan for the first
non-flag argument is gone: the launcher reads `$1`. A missing fork gives `vendomat: no devenv fork at PATH`, exit 2.

## How the fork path is set

- Build time: `flake.nix` substitutes `@DEVENV_FORK@` in the launcher, as it does `@HOST_RELEASE@`.
  `packages.<system>.launcher` uses `defaultFork`, the fixed path above.
- Another fork without touching the dispatch: `lib.<system>.mkLauncher { devenvFork = "${fork}/bin/devenv"; }`.
- Run time (tests): `VENDOMAT_DEVENV_FORK`, documented at the top of the launcher.
- The launcher wrapper now uses `--suffix PATH` (was `--prefix`) and adds `findutils`, so the fork sees the caller's PATH order.
- The flake keeps one input. `tests/test_repo_shape.py` passes.

## Pin options (task 2)

1. Fixed store path in `flake.nix` (built now). Cost: no store reference, so garbage collection can remove the fork; edit and rebuild per fork tag.
2. `mkLauncher` called by the host with the fork built from a host flake input (`git://server/devenv?ref=...`). Cost: one `nix-meta` input and one profile edit; the lock pins the tag and the store keeps the fork.
3. Build the fork inside the Vendomat flake with a fetched, hashed source. Cost: a 390 MiB build and a second lock inside this flake; this breaks the one-input rule in spirit.
4. Read the path from a file or environment variable at run time. Cost: unpinned; a stale value runs the wrong fork.

Recommendation: option 2. Keep option 1 as the default until `nix-meta` adopts it. Inference: option 2 has not run; I did not touch `nix-meta`.

## Tests (`tests/test_launcher.py`, fake fork)

Expected: each case below passes. Actual: `testee verify pytest` passed, 379 tests, 0 failures (the 65 skips are the opt-in
checks). Cases: bare call runs `shell` in and out of a workspace and starts no build; `test`, `update`, `update vendomat`,
`shell -- ls -l`, `--verbose test`, `tasks run "x y"` pass with exact argv; exit status 7 passes; a missing fork gives one line;
SIGTERM reaches a trapping fork and its status 42 returns; `sync` still uses the pinned build and `machine install` the host
release; `new` copies all files (including a dotfile and a subdirectory), makes them writable, creates DIR, refuses on a clash
with one line and writes nothing, and rejects two arguments.

## Smoke test with the real fork (`smoke.log`)

Launcher `km216qa5...`, directory `smoke/empty`. Actual: `--version` printed `vendomat 0.7.0rc1` (host release);
`version` printed `devenv 2.4.0+fb5d382 (x86_64-linux)`, exit 0; `bogus-verb` printed the fork's usage, exit 2;
`new` copied the current three template files, a second `new` refused with exit 1; `test` and bare `vendomat` reached
the fork, which exited 1 on `./.vendomat/devenv.nix file does not exist` (the old template, before lanes B and C).

## What this proves, and what stays inference

Proves: the dispatch table and the exit-status pass-through, with a fake fork and with the real fork for `version` and an
error exit. Signals are proved with a fake fork only. Inference: `shell` on a lane B and C workspace, `new` against the new
four-file template (the code copies whatever the template holds, but the next-step line names `vendomat.yaml`), the
host install through `mkLauncher`, and tty behaviour of `shell` (the smoke test has no terminal).
Not covered: `vendomat --help` still shows the Typer help, which does not list `new`.

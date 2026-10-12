# Project 20 decisions

**Date:** 2026-10-11. The owner chose project 20 as the future Vendomat concept. This turn changes
concept and plan only. The current implementation remains in place until the new gates pass.

| # | Decision | Effect |
| --- | --- | --- |
| 1 | Vendomat is the user command and runs pinned devenv after preparing a workspace. | The host launcher expands beyond `sync`. |
| 2 | `vendomat.yaml` is the routine user file for workspaces and the Basix system workspace. | The TOML runtime and separate `sync` step end at cutover. |
| 3 | Vendomat uses real declared option paths and native Nix merging. | Data values need type checks; unsupported values use native Nix. |
| 4 | Basix owns machine defaults, inventory, guards, fresh install, and adoption. | Vendomat prepares configuration and forwards native machine commands. |
| 5 | The source, store, Harmonia cache, and keyless first install decisions of project 19 carry forward. | The first boot needs no secret provider or signing key. |
| 6 | A new pin may require Nix to produce its option schema. | Syntax lint runs first; schema validation finishes before the requested operation. |
| 7 | There is one new runtime format after cutover. | A one-time converter may help, but the runtime has no permanent TOML compatibility path. |

The following choices need fixtures before they become implementation requirements: exact Basix
machine option names, the generated module priority, schema refresh after a pin change, the
post-install secret route, and the value of a one-time converter. See [PLAN.md](PLAN.md).

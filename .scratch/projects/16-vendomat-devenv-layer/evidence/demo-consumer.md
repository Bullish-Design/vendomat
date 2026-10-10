# Private demo consumer: first live workspace run

**Date:** 2026-10-10. **Result:** PASS for the no-Nix workspace flow on a private, tagged source.
This is not the Step 13 fleet gate.

## Inputs and commands

The demo is `Bullish-Design/vendomat-demo`, private, with source tag `v0.1.0` at
`9b8896da7d6a07fb905759a007a07c8e45f68e4d`. Templateer 0.4.1 created its root
`devenv.nix` and `devenv.yaml`. Its `sources/vendomat` snapshot came from Vendomat commit
`89bedc9dffb253fb3fe0464cb1e4b6824560a5f9`. The host used Nix 2.34.7 and stock devenv
2.4.0+b904dcb and Testee 0.5.1. The corrected local Vendomat 0.6.0 package was
`/nix/store/p5iy1jfkggsk5i3nm5jh8si1149s3vjk-vendomat-0.6.0`.

| Command | Expected | Actual |
| --- | --- | --- |
| `vendomat sync` | Resolve both authored modules and their inherited inputs | Exit 0; 8 inputs, 2 imports; both inherited inputs have lock nodes at the demo tag revision |
| `devenv eval env.DEMO_GREETING`, `devenv eval env.DEMO_MARKER` | Read user settings | Exit 0; `Hello from Vendomat`, `demo` |
| `devenv shell -- ...` | Enter the composed shell | Exit 0; both values matched |
| `vendomat check` | Validate lock and fragment | Exit 0; `clean` |
| `scripts/smoke` in the demo | Change only TOML in a copied workspace | Exit 0; a supported value changed, removing an unselected input left `shell.drvPath` equal, and the template files stayed byte-identical |
| `testee verify --full` in Vendomat | Repository gate passes | Exit 0; final run `20261010T170544Z-e3c9fcb429dc` |
| `testee check e2e` in Vendomat | Consumer and infrastructure tests pass | Exit 0; run `20261010T165655Z-68db24400dae`, 330 passed |

The smoke log and workspace copy are under
`~/.local/state/vendomat-demo/runs/20261010T165623Z/`. The Testee reports are under `.testee/runs/`
for the run IDs above. The demo repository has its own `EVALUATION.md`.

## Findings

The first sync found only five inputs. Nix `flake prefetch` returned the Git repository root for
an input with `dir=sources/greeting`; Vendomat looked for `devenv.yaml` without that directory.
Vendomat now joins the URL's `dir` to the fetched root before it reads the imported file. The
second sync found seven inputs but failed to update an existing lock: it passed two names to
`devenv update`, which accepts one. Vendomat now runs a full update when more than one input
needs updating. Tests cover both cases. The final sync found eight inputs after the demo pinned
the stock devenv modules explicitly.

The observations prove the workspace user can change selected modules and supported values in
TOML alone. They do not prove the patched V6 devenv distribution, the owner's collection, Attic,
offline shell entry, a machine, or a fleet conversion. The demo pins stock devenv until the fork
has a published source route. The Vendomat module is a source snapshot until V6 has a release tag.

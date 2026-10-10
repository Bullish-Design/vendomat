# Step 3A: no-Nix workspace user flow

**Date:** 2026-10-10. **Result:** PASS for a template-created local consumer.

## Inputs and commands

The host ran Nix 2.34.7, devenv 2.4.0+b904dcb, Templateer 0.4.1, and Testee 0.5.1.
The consumer fixture served six local Git repositories through `git daemon` on loopback.
Each source had a `v1` tag. The fixture copied the current Vendomat module into a slim tagged
flake. It used authored `alpha` and `beta` modules, their own tagged dependencies, and an
unselected `unused` source. Both authored modules declared inputs in `devenv.yaml`.

| Command | Expected | Actual |
| --- | --- | --- |
| `templateer check workspace-registry -p templates` | The bundled template validates | Exit 0; three probes, zero findings |
| `testee check workspace-e2e` | The template-created consumer passes | Exit 0; run `20261010T155624Z-6ba99f842e36` |
| `nix build --no-link --print-out-paths "path:$PWD#vendomat"` | The Vendomat package includes the template files and init command | Exit 0; `/nix/store/457nximaiz79k2gpc1c7rdz72z57p88f-vendomat-0.6.0` |
| `/nix/store/457nximaiz79k2gpc1c7rdz72z57p88f-vendomat-0.6.0/bin/vendomat-workspace-init templates/workspace-registry/examples/default.input.json ~/.local/state/vendomat/v6/installed-workspace-final` | The installed command creates three workspace files | Exit 0; three files under the output directory |
| `testee verify --full` | All required repository checks pass | Exit 0; run `20261010T161706Z-f7ed481f78ef`; 266 passed, 62 opt-in cases skipped |
| `testee check e2e` | Real consumer and existing integration checks pass | Exit 0; run `20261010T160815Z-7533da901018`; 328 passed in 463.99 s |

The first full end-to-end run failed in two test fixtures. The removed description-builder VM
test still named its deleted Nix file. The launcher fixture omitted the new `templates/`
directory from its source copy. The corrected run above passed. The first run did not prove a
product failure.

## Observations

- Templateer created `vendomat.toml`, `devenv.nix`, and `devenv.yaml`. The workspace user edited
  only `vendomat.toml` after creation. The test compared both template-owned files byte for byte.
- `[imports]` selected `alpha` and `beta`. Sync wrote two imports and resolved seven input
  sources, including both authored modules' dependencies. The consumer lock held one named node
  for each source.
- The consumer evaluated `ALPHA_VALUE=first` and `BETA_VALUE=second`, then entered its shell.
  A TOML edit changed `ALPHA_VALUE` to `changed` after sync. No Nix file changed.
- The unselected `unused` source exported a module that would throw if imported. Removing that
  source left `shell.drvPath` equal to
  `/nix/store/hjhh840jyglmj7zn3slw063c4p72rhz8-devenv-shell.drv` in both evaluations.
- An unknown `[imports]` name made sync exit 2 and named `missing`. An unsupported authored
  setting made devenv eval exit 1 and named `vendomat.settings.alpha.wrong`.
- The packaged init command created the three files from the installed Templateer library.
  The command requires a Templateer executable on `PATH`, or `VENDOMAT_TEMPLATEER`.

The complete fixture commands, exit codes, and output are under
`~/.local/state/vendomat/v6/fixture-logs/20261010T160815Z/workspace-*.txt`.
The Testee reports and structured results are under `.testee/runs/` for the run IDs above.
The end-to-end Testee run used the sibling Templateer checkout's 0.4.1 executable.

## Inference and limits

The observations satisfy G3A for a workspace user and a local, tag-pinned consumer. Native
devenv imports and Nix options provide module selection and value validation. A stable
template-owned root module can read `[settings]` directly. Vendomat needs no generated
`.vendomat/modules.nix` file or description builder.

This fixture did not use the live source collection, the owner's Attic, or a real machine
activation. The two authored modules used small test values rather than production services.
G1, G5, G8, and G9 keep their separate blockers. Machine operator coverage remains a later
interface decision.

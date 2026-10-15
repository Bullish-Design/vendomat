# S6: the old binary fork retired — 2026-10-14

Slice S6 of the implementation guide. This record changes the Vendomat repository only: it removes
the `v2.4.0-vendomat.4` series and its fixtures, and it changes pins in tests and examples. No
host change, no build of the host binary, no tag change, no Attic, no upstream contact, no sudo.

## Goal and rulings

Nothing in Vendomat depends on fork tag `v2.4.0-vendomat.4` or on patches 0001, 0002, 0004, 0006,
0007, 0008, and 0009. Keep the S1 module series and the S2 binary patches.

- R34: no upstream pull request. R31: the binary keeps 0003 and 0005 only.
- R40: the project 14 and V6 verbs and the `vendomat.toml` flow stay until S8.
- A published tag is never deleted. The collection keeps `v2.4.0-vendomat.2`, `.3`, and `.4`.
  This slice touched no tag.

## Inputs

| Item | Value |
| --- | --- |
| Base | `main` `6f9b1e60` |
| Workspace | `s6-retire-fork` |
| Module fork tag (kept) | `v2.4.0-vendomat-modules.1`, commit `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9` |
| Binary patches (kept) | `devenv-dist/binary/patches/0003.patch` sha256 `c4a121b9…aaa1c5`, `0005.patch` sha256 `85eea6e2…edd2a3` (unchanged) |
| Host binary (not rebuilt) | `/nix/store/0ca6h7n4d4yrmj044idsnl7fjpg48l9v-devenv-2.4.0` |
| Testee | 0.8.0 |

## Removed files

From `devenv-dist/` (the old `.4` recipe):

- `SERIES`, `MANIFEST.sha256`, `RESULT`.
- `patches/0001-…handshake-3255.patch`, `0002-Update-latest-devenv-version.patch`,
  `0003-…reuse-locked-inputs….patch`, `0004-…build-the-devenv-CLI-as-a-release….patch`,
  `0005-…refuse-machines-install-for-an-adopted-mach….patch`, `0006-…target-bound-preflight….patch`,
  `0007-…inherit-the-inputs….patch`, `0008-…lazily-mounted-locked-source….patch`,
  `0009-…vendomatFromYAML-primop.patch`. Patches 0003 and 0005 of this series equal the S2 copies in
  `binary/patches/` byte for byte (S2 evidence); those copies stay.
- `fixtures/` (14 files): `cli-fixture`, `dist-fixture`, `inherit-fixture`, `vm-fixture`,
  `fixture-common`, `fakebin/nix`, `fakebin/ssh`, `project/*` (5 files), `vm/*` (2 files).

The guide does not name the fixtures. I removed them for these reasons (observation, then inference):

- Observation: each of the four scripts takes a `.4` binary or a `.4` fork repository as an
  argument. They test patches 0006 (`cli-fixture`, `vm-fixture`), 0007 (`inherit-fixture`), and the
  `.4` tag read from `UPSTREAM` (`dist-fixture`).
- Observation: no test, task, or Nix file refers to them (`grep` over the tree outside `.scratch`).
- Inference: no check can run them against the current stack, so they only keep dead pins. The S2
  fixtures B2, B5, and B6 (`opt:binary-e2e`) cover the kept patches 0003 and 0005.

## Changed files and pins

| File | Change |
| --- | --- |
| `devenv-dist/UPSTREAM` | The line `fork_tag=v2.4.0-vendomat.4` is gone. The pin keeps `repo`, `tag`, and `commit`. |
| `devenv-dist/materialize` | `--series modules` is now required. The default binary series is gone. The fork tag comes from `modules/UPSTREAM`. Usage text updated. |
| `tests/test_devenv_dist.py` | Removed the binary-series tests (order, manifest, headers, per-patch tests for 0006, 0007, 0008, the 0009 test with its `fn case_` count of 27, the `.4` pin at old line 57, and the `.1` check at old line 159). Removed the `DIST / "RESULT"` comparison in the module test. Added four tests: the pin has no `fork_tag`; the old series files are gone; `binary/patches` holds exactly `0003.patch` and `0005.patch` with the S2 hashes; `materialize` needs `--series`. The module-series tests stay. |
| `templates/workspace-registry/examples/default.input.json` | `devenv_tag` `v2.4.0-vendomat.3` → `v2.4.0-vendomat-modules.1` |
| `templates/workspace-registry/examples/default.output.toml` | `refs/tags/v2.4.0-vendomat.3` → `refs/tags/v2.4.0-vendomat-modules.1` |
| `tests/test_registry_v6.py` | Two `.3` values → `v2.4.0-vendomat-modules.1` (a long line split in two). |
| `tests/test_commands_v6.py` | Two `.3` values → `v2.4.0-vendomat-modules.1`. |
| `templates/workspace-registry/schema.py` | The `devenv_tag` description reads "Devenv module fork tag" (was "Patched devenv tag"). |
| `AGENTS.md` | The `devenv-dist/` line no longer lists the old series. |
| `.scratch/…/REQUIREMENTS.md` | Status column of `VMT-080` and `VMT-081` only. |
| `.scratch/…/PLAN.md`, `.scratch/CURRENT.md` | S6 marked done; one line added. |

Observation: the `.3` values in the V6 files are data. `parse_registry` and the version check read
the tag only as text, and no V6 code resolves it. The change keeps the V6 flow working (R40); the
V6 tests pass (see Testee runs).

The guide names `tests/test_front_door_e2e.py:21` and `devenv.nix:109,116,117`. Those lines no longer
carry a `.4` value: S1 and S3 already moved them. `grep` finds no `vendomat.4` in either file.

## Hits left for S8 (R40)

| Hit | Reason it stays |
| --- | --- |
| `preflight/vendomat-preflight` header names "devenv-dist patch 0006" | Comment in the V6 install flow. S8 removes `preflight/`. |
| `nix/devenv-module/default.nix:42` comment names patches 0005 and 0006 | Comment in the V6 module. S8 removes that module. |
| `src/vendomat/machine.py`, `src/vendomat/cli.py`, `nix/devenv-module/preflight.nix`, `tests/test_machine_install.py`, `tests/test_devenv_module_e2e.py`, `tests/test_launcher_e2e.py` (preflight code and tests) | The `machine` command and the V6 module. S8 removes them. |
| `launcher/vendomat` and its variable `VENDOMAT_DEVENV_FORK` | The name says "fork"; the value is the S2 binary since S2. No `.4` pin. The launcher stays (S8 keeps `launcher/`). |

Historical text that stays as written: `devenv/parse.nix` (comment on the Rust primop and patch 0009
as the parser's origin), `tests/test_parser_fuzz.py` (the oracle history), `tests/test_catalog_template.py`
and `tests/test_binary_e2e.py:587` (assertions that the primop is absent), and every document under
`.scratch/projects/0*` to `20-*`, plus the older text in `.scratch/CURRENT.md`.

## Published tags

Not touched. The collection keeps `v2.4.0-vendomat.2`, `.3`, and `.4`. nix-systems still pins `.2`
and moves in S8.

## Testee runs

| Command | Run ID | Verdict |
| --- | --- | --- |
| `testee verify --profile quick` | `20261015T000439Z-a2bc0b006ba8` | PASS (format, quick tests) |
| `testee verify` | `20261015T000448Z-b14bdc3addfe` | GREEN 4/4 (tree `cd076dc442`) |
| `testee verify opt:modules-e2e` | `20261015T000523Z-87d4e91b06a6` | PASS, 6 tests, 0 failures, 0 skips |

The first quick run (`20261015T000418Z-7025fdc7ae74`) was RED: ruff flagged one line over 120
characters in `tests/test_registry_v6.py` (my `.3` replacement). I split the line.

Why `opt:modules-e2e`: it runs `devenv-dist/materialize --series modules --verify`, the one script
this slice changed, and the `UPSTREAM` file. The logs are under
`~/.local/state/vendomat/p21/2026-10-15/s1/modules-e2e/20261015T000524Z/` (the task writes a
fixed `s1` path and UTC date).

Not run, with reasons:

- `opt:binary-e2e`: the overlay, the two patches, and the flake are unchanged. `nix eval
  .#packages.x86_64-linux.devenv.drvPath` gives `/nix/store/1qabl9qb2zhm5ggqrw25x5cr6v67p79b-devenv-2.4.0.drv`
  before and after the change, so the host binary path does not change.
- `opt:modules-vm`: it calls `materialize` with the same arguments as `modules-e2e` and no other
  changed file. It builds and boots two images. Inference: `modules-e2e` covers the change.
- `opt:front-door-e2e`, `opt:catalog-*`: no file they read changed.
- `opt:live-cache`, `opt:live-cache-load`: forbidden for this slice.

## Deviations

1. I removed `devenv-dist/fixtures/` (the guide does not name it). See the reasons above.
2. I made `--series` required in `materialize`. The guide does not say what the script does without
   the old series. The change keeps one meaning for the script.
3. I changed the `devenv_tag` description in `templates/workspace-registry/schema.py`. The change is
   a text label.
4. I did not run `opt:modules-vm` and `opt:binary-e2e` (reasons above).

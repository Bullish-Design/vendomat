# Progress — uv2nix templateer prototype

## 2026-09-08

Templateer v0.4.1 now tracks `uv.lock`. Vendomat pins the `templateer_v2` input
to that tag and adds `pyproject-nix`, `uv2nix`, and
`pyproject-build-systems`. All three inputs follow vendomat's `nixpkgs` and
`uv2nix` follows vendomat's `pyproject-nix`.

The public `.#templateer` package now uses the uv2nix virtual environment.
The legacy package remains available as `.#templateer-hand-pinned`. The
parallel `.#templateer-uv2nix` name also remains for prototype inspection.

## Evidence

The following commands passed:

```text
nix build .#templateer --no-link --print-out-paths
nix run .#templateer -- --version
templateer, version 0.4.1
nix build .#templateer-hand-pinned --no-link --print-out-paths
nix build .#repoman-toolchain-core --no-link --print-out-paths
devenv shell testee verify --mode quick
```

The toolchain still exposes `repoman`, `copyroom`, `docman`, `gitman`, and
`templateer`. The toolchain rebuild after promotion rebuilt templateer and the
join only. It did not rebuild the other roster tools.

## Dependency comparison

The uv2nix closure contains the versions recorded in `templateer_v2/uv.lock`:

| Distribution | `uv.lock` and uv2nix | Legacy hand pin |
|---|---:|---:|
| click | 8.4.2 | nixpkgs 8.3.1 |
| genai-prices | 0.1.1 | 0.1.6 |
| httpcore2 | 2.9.1 | 2.7.0 |
| httpx2 | 2.9.1 | 2.7.0 |
| idna | 3.18 | 3.18 |
| jiter | 0.16.0 | 0.16.0 |
| minijinja | 2.22.0 | 2.24.0 |
| openai | 2.53.0 | 3.8.0 |
| pydantic-ai-slim | 2.23.0 | 2.40.0 |
| pydantic-graph | 2.23.0 | 2.40.0 |

The legacy path therefore does not reproduce the tool's lockfile. uv2nix
removes the hand-maintained wheel filenames and hashes, but it introduces a
larger build: this prototype built 91 derivations. The prototype did not need
manual build-system fixups for templateer.

## Recommendation

Proceed with uv2nix for the remaining roster tools after adding a test that
compares installed versions with each tool's lockfile. Keep the hand-pin file
until each tool completes the same build and runtime checks.

The kickoff brief requested a 0.4.0 runtime while also requiring a 0.4.1 tag.
This prototype follows the release tag and reports 0.4.1.

## Remaining roster migration — 2026-09-08

The shared `mkUv2nixCli` constructor now builds repoman, copyroom, docman, and
gitman from each tool's own lockfile. All four use Python 3.13. The public
roster packages and the composed toolchain use these uv2nix derivations.

Published lockfile-backed inputs:

- repoman v0.7.5 already contained its tracked lockfile.
- copyroom v0.7.7 tracks its lockfile and aligns its runtime version constant.
- docman v0.2.1 tracks its lockfile.
- gitman v0.6.2 tracks its lockfile.

The following builds and runtime checks passed:

```text
nix build .#repoman --no-link --print-out-paths
nix build .#copyroom --no-link --print-out-paths
nix build .#docman --no-link --print-out-paths
nix build .#gitman --no-link --print-out-paths
nix build .#repoman-toolchain-core --no-link --print-out-paths
repoman --version       # 0.7.5
copyroom --version      # 0.7.7
gitman --version        # 0.6.2
templateer --version    # 0.4.1
devenv shell testee verify --mode quick
```

Testee passes ruff, ruff-format, ty, and pytest.

## Legacy cleanup — 2026-09-08

Removed the legacy roster dependency path after the full live check passed.
Deleted `pkgs/templateer-deps.nix`, `lib/mkPythonCli.nix`, and
`lib/mkPypiWheel.nix`. Removed the nixpkgs dependency table and all
`*-hand-pinned` package outputs. The pyjutsu wheel builders remain because
vendomat still exports those artifacts independently.

## Lockfile guard and PATH cleanup — 2026-09-08

Added `test_uv2nix_closure_matches_each_tool_lockfile`. The guard evaluates
the lock versions exposed by each uv2nix package and compares every matching
runtime distribution in its Nix closure. The focused test and the full Testee
quick suite pass.

uv2nix virtual environments contain console scripts from their dependencies.
The first composed closure exposed commands such as `httpx`, `python`, and
`activate`, which failed the downstream PATH safety check. Each public package
now exports only the project's declared console scripts. The rebuilt closure
exports exactly `copyroom`, `docman`, `gitman`, `repoman`, and `templateer`.

The local rebuilt closure is:

```text
/nix/store/z6ayz3iz2c3plgidf7kfslwnwrzc7yk2-repoman-toolchain-core
```

The nix-meta live check still reads the older deployed closure. The consuming
system must update its vendomat input and run its normal system rebuild before
that check can validate the new PATH and version set.

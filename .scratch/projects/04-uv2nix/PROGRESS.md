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

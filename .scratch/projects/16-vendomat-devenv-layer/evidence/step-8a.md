# Step 8a — tool flakes, the devman registry function, repoman

**Date:** 2026-10-09. **Gate:** G8 (first half). **Status:** PASS for the items below.
`agentman` is deferred with named reasons. G8 stays OPEN: the `server` role build and the
V4 overlay import removal (second half) are not part of this record.

`[O]` = observed. `[I]` = inference. Raw logs sit under
`~/.local/state/vendomat/v6/2026-10-09/08-legacy/`.

## Pins

- Host: Nix 2.34.7, devenv 2.4.0, jj 0.46.0, Testee 0.5.0 wrapper.
- Every new flake uses `github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`
  (`python313`, rustc 1.98.1, maturin 1.15.0). `copyroom` makes `pyjutsu` and `templateer`
  follow that input.
- Every bookmark is `v6-flake` (`devman`: `v6-registry`). Each bookmark is one commit on `main`.
  No `main` moved. The lead merges.

## Result per repository

| Repo | Commit | Tag | Flake output | Gate | Smoke |
| --- | --- | --- | --- | --- | --- |
| `docman` | `888a1c4521c9` | `v0.3.0` | `packages.<system>.default`, `.docman` | No Testee config. `nix flake check` exit 0; suite 19 passed in the build | `docman --help` exit 0 |
| `pyjutsu` | `b5373881f606` | `v0.23.1` | `packages.<system>.default`, `.pyjutsu`, `.pyjutsu-lib`; `overlays.default` | No Testee config. `devenv tasks run pyjutsu:verify` exit 0 (build, clippy twice, `cargo test`); direct `pytest -q` run all dots (about 1 min 20 s) | `pyjutsu --help` exit 0; import check `pyjutsu 0.23.1 jj-lib 0.44.0`, no test hooks |
| `templateer_v2` | `a342d1e473b4` | `v0.4.2` | `packages.<system>.default`, `.templateer`, `.templateer-lib`, `.minijinja`; `overlays.default` | No Testee config. Repo gate (`ruff check`, `pytest`) 445 passed; the build runs the same suite | `templateer --help` exit 0 |
| `copyroom` | `ad744e2be118` | `v0.8.1` | `packages.<system>.default`, `.copyroom`; `overlays.default` | No Testee config. Repo gate (`ruff check`, `pytest`) 160 passed, 26 deselected as `slow`; log `copyroom/gate.log`. The build runs 156 tests | `copyroom --help` exit 0; `copyroom doctor` finds the pinned guard (`ok: true`, `templateer 0.4.2`) |
| `devman` | `c86472504734` | `v0.8.0` | `lib.<system>.mkRegistry`; `nixosModules.default` | No Testee config. `nix flake check` exit 0 (8 checks, 770 Python tests); log `devman/gate-flake-check.log` | VM test below |
| `repoman` | none | none (`v0.12.1` stays) | unchanged | `testee verify --full` run `20261010T032246Z-994a87ee5722`, PASS (pytest, ruff, ruff-format, ty) | consumer shell below |
| `agentman` | none | none | none | not run | DEFERRED |

Remote tags were read back with `gh api .../git/ref/tags/<tag>`. The SHA matches each commit.
Each tag also built from its `git+https` URL on a clean fetch (`docman`, `templateer_v2`,
`Pyjutsu`, `copyroom`): exit 0.

## Why each tool got a new version

A flake must sit in a tagged commit. A tag must equal the version in `pyproject.toml`
(`pyjutsu:publish` derives it). `docman` already held an untagged 0.3.0. The other three took
a patch bump that adds only packaging. `[O]` A bump needs one edit per version file: `pyjutsu`
has five (`Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `__init__.py`, `tests/test_build.py`,
plus the `uv.lock` own entry that `uv sync` rewrote).

## Findings

1. `[O]` `templateer` `main` failed its own suite before this change. The test
   `tests/test_cli.py::TestHelp::test_version_flag` asserted `"0.4.0"` while the package was
   0.4.1. The Nix build reported `1 failed, 444 passed`. The release commit makes the test
   read the installed version. The repository gate was red on `main`. This commit fixes the
   cause. It does not skip the test.
2. `[O]` nixpkgs has no `minijinja` Python binding. `templateer/nix/minijinja.nix` builds it
   from the PyPI sdist 2.22.0 (the version in `uv.lock`) with maturin. The vendor hash is
   fixed. No wheel download.
3. `[O]` nixpkgs has `pydantic-ai-slim` 2.52.0 but no `openai` extra. The package lists
   `openai` directly.
4. `[O]` `copyroom` does not import `pyjutsu`. It runs the `pyjutsu` command by path
   (`COPYROOM_PYJUTSU`, else `PATH`) and probes it. The flake wraps `COPYROOM_PYJUTSU` to the
   pinned command with `--set-default`. It wraps no `jj`: the host supplies one `jj`.
5. `[O]` `pyproject.toml` of `copyroom` pins `pyjutsu==0.23.0` for uv through a release wheel
   URL. The 0.23.1 release has no wheel upload. The Nix package relaxes only that pin
   (`pythonRelaxDeps`). `[I]` The delta 0.23.0 to 0.23.1 holds the flake and docs only.
   Upload of a 0.23.1 wheel to the GitHub release is a publication and was not done.
6. `[O]` `copyroom/modules/copyroom.nix` built a stale package: version label 0.7.7,
   `templateer` 0.4.1, and a runtime check that failed on `pyjutsu`. A build of the old file
   alone failed with `pyjutsu not installed`. The module now builds the same
   `packages/copyroom-cli.nix`, pins `templateer` 0.4.2, and skips the `pyjutsu` check
   (`pythonRemoveDeps`). The module gives no guard, as before.
7. `[O]` The `pyjutsu` Nix package runs no test suite. The suite shells out to `jj` 0.44.0 as
   an oracle. The repository gate runs it. The Nix smoke command runs in `postInstallCheck`.
8. `[O]` In this nixpkgs, `buildPythonPackage` runs checks in `installCheckPhase` and gates
   them on `doCheck`. Overriding `installCheckPhase` skips `pytestCheckHook`. `gitman`'s
   `nix/package.nix` does so (its comment says the build runs the suite). `[I]` Its suite does
   not run in the build. This record does not change `gitman`.
9. `[O]` `nix flake show` on `devman` v0.8.0 fails while it evaluates the Darwin `checks`
   (`optionalAttrs pkgs.stdenv.hostPlatform.isLinux`). `nix flake check` on Linux passes.
   `[I]` Low risk for the Linux server. Not investigated.

## repoman (item 3)

`[O]` v0.12.1 reads no `REPOMAN_TOOLCHAIN_BIN`, no `toolchainBin` option, and no
`toolchain.json`. `tests/test_modules_nix.py` and `tests/test_toolchain_coherence.py` assert
that. `repoman`'s `nixosModules.default` only installs the `repoman-module` tree.

Consumer proof, a throwaway devenv project in `/tmp` (removed). Roster `copy git doc`. It
imports `repoman` v0.12.1 (`modules/` as `flake: false`). `packages` holds flake outputs:
`repoman` v0.12.1, `gitman` v0.12.1 and its `jujutsu-bin` 0.46.0, `docman` v0.3.0,
`copyroom` v0.8.1 (with `pyjutsu` 0.23.1 and `templateer` 0.4.2 behind it).

- Command: `devenv shell -- repoman doctor`. Expected: no `REPOMAN_TOOLCHAIN_BIN`; rows
  `installed:copy|git|doc` OK. Actual: exit 0. `TOOLCHAIN_BIN=unset`. `installed:copy`,
  `installed:git`, `interface:git` (jj 0.46.0), `installed:doc` all OK. Three WARN rows: no
  `docman` input (`provisioned:doc`) and no skills in the throwaway project.
- Command: `devenv tasks run repoman:docs:doctor` and `repoman:template:status`. Actual:
  both tasks ran the commands from `PATH` and exited 1. `[I]` The failures describe the
  empty throwaway project (`zensical` absent, no CopyRoom marker). They are not toolchain
  failures. Log: `repoman/consumer-tasks.log`.
- The `repoman doctor` output was read on the terminal and not saved to a file. The task
  log is saved.

`[O]` Nothing is dead in `repoman`'s README. Its `CHANGELOG.md` names V4 only as history.
`CONCEPT.md` keeps one sentence about the ignored legacy `cliProvider` key. No change was
made, so no release was cut.

## devman (item 2)

Relayed from the sub-lane. I verified the tag on origin, the `lib.<system>` attribute names
(`[ "mkRegistry" ]`), and the exit lines of the logs.

- Function: `inputs.devman.lib.<system>.mkRegistry { projects = { <name> = { path; groups;
  policy ? "stable"; triggers ? null; writes ? null; source ? null; }; }; policyRoot ?
  <flake groups>; overlayRoot ? null; generation ? 1; toolchainDigest ? null; name; }`.
  It returns one store path: `generation.json`, `projects/<p>/{metadata.json,projection.json,
  workflows/*.yaml}`, `dags/<p>.<w>.yaml`. `path` is the absolute run-time checkout. The
  renderer is the existing one, with a new `--checkout PATH` option. `dagu validate` runs on
  every workflow in the build.
- Module: a `registryDir` under the store dir creates nothing in it and watches nothing.
  The reload path unit and service exist only for a mutable directory. A store `stateDir`
  is an assertion failure. `[O]` The VM measured that Dagu 2.15.0 fails to start when it
  cannot `mkdir <dags_dir>/wiki`. The module sets `paths.wiki_dir` under `$DAGU_HOME`. Dagu
  logs a non-fatal warning for `dags/.dag.index`.
- VM test `checks.x86_64-linux.dagu-store-registry`, command
  `nix build --no-link -L path:$PWD#checks.x86_64-linux.dagu-store-registry`, exit 0, log
  `devman/vm-store-registry-4.log`. It asserts: the registry holds only `dags`,
  `generation.json`, `projects`; the `dagu` user unit is active on the store path; the API
  on `127.0.0.1:8080` lists `demo.check`, `demo.probe`, `beta.check`, `beta.format`; a run of
  `demo.probe` succeeds; no reload unit exists; `NRestarts=0` after 20 s. Runs 1 to 3 failed
  and found the `wiki` finding (`vm-store-registry*.log`). Run 4 passed.
- Comparison with live generation 4 (read-only, `devman/live-compare.log`). Same: workflow
  files byte for byte, `policy_digest`, `dagu_digest`, `manifest_digest`, `source_digest`.
  Different: `renderer_digest`, `devman_runtime` (`0.6.0` and `v0.6.0`), `toolchain_digest`
  (`unspecified`), `workflows.*.source` (store path against checkout), `overlay`.
- `USER.md` section 2.7 now describes `mkRegistry`. The live Dagu and
  `~/.local/state/vendomat/devman` were not touched.
- `[O]` devman had no written release rule. Version 0.7.0 left three files at 0.6.0. The
  release commit sets `pyproject.toml`, `nix/devman-cli.nix`, and `nix/renderer.nix` to
  0.8.0. `nix/link-adapter.nix` and `packaging/devman-link` stay at 0.6.0.

## Deferrals and blockers

| Item | State | Evidence |
| --- | --- | --- |
| `agentman` flake | DEFERRED | `dbos` and `pydantic-ai-harness` are absent from the pinned nixpkgs (`python313Packages` eval). `inferference` is a private repository on an `ssh://` URL (`gh repo view`: private). `import-linter` (dev) is absent too. The server still runs `agentman` from the old closure (survey item 4) |
| Python core repository with uv2nix | NOT NEEDED | Every converted tool built from plain nixpkgs. No uv2nix fallback was used |
| `pyjutsu` 0.23.1 release wheel | NOT DONE | A GitHub release asset is a publication. `copyroom` keeps its 0.23.0 wheel pin for uv |
| Merge to `main` in the tool repositories | NOT DONE | By instruction. Each bookmark fast-forwards from `main` |
| Testee run ids for five repos | NOT AVAILABLE | `docman`, `pyjutsu`, `templateer_v2`, `copyroom`, `devman` have no `testee.checks`. Each used its own `gitman.toml` `[publish] verify` |
| Overlay import removal (backlog item 4), `nix-meta` repin | OPEN | Second half of Step 8. Needs the host `PATH` tools |
| `mancore/CONCEPT.md` | NOT TOUCHED | Out of the list |
| `devman` `AGENTS.md` and `README.md` V4-era `active` wording | OPEN | The sub-lane edited only `USER.md` |

## Disk

`df -h /`: 63 GB free at the start, 51 GB at the end. `btrfs filesystem usage /`: unallocated
17.95 GiB at the start, 3.95 GiB at the end (another lane builds at the same time). Metadata
77.5% used. No GC ran. Build targets and `.devenv` directories in the lane workspaces were
removed.

## Inputs for the next lane

```nix
inputs = {
  repoman.url   = "git+https://github.com/Bullish-Design/repoman?ref=refs/tags/v0.12.1";
  gitman.url    = "git+https://github.com/Bullish-Design/gitman?ref=refs/tags/v0.12.1";
  testee.url    = "git+https://github.com/Bullish-Design/testee?ref=refs/tags/v0.5.0";
  docman.url    = "git+https://github.com/Bullish-Design/docman?ref=refs/tags/v0.3.0";
  pyjutsu.url   = "git+https://github.com/Bullish-Design/Pyjutsu?ref=refs/tags/v0.23.1";
  templateer.url = "git+https://github.com/Bullish-Design/templateer_v2?ref=refs/tags/v0.4.2";
  copyroom.url  = "git+https://github.com/Bullish-Design/copyroom?ref=refs/tags/v0.8.1";
  devman.url    = "git+https://github.com/Bullish-Design/devman?ref=refs/tags/v0.8.0";
};
```

- `repoman.packages.<system>.default`, `repoman.nixosModules.default`.
- `gitman.packages.<system>.default` (`gitman`) and `.jujutsu-bin`. Install one `jj`.
- `testee.packages.<system>.default` (also `.testee`) and `testee.devenvModules.default`.
- `docman` and `copyroom` take `packages.<system>.default`. `docman` is a private repository.
- `devman.lib.<system>.mkRegistry` and `devman.nixosModules.default`
  (`services.devman-dagu.registryDir = "${registry}"`).
- The tagged commits are not on `main` yet. Pin the tags, not `main`.

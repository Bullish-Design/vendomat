# Step 7 record: harvest and triage the corpus

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`.
**Raw report:** `~/.local/state/devenv-py/step-7/REPORT.md`. Summaries: `summary-final.json`,
`summary-all.json`, `summary-public.json`, `bench.json` in the same directory.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Commit | `18ad476966a8`: feat: add the corpus harvest, triage, and truth (Step 7). The agent reported change `xmpokozovmpp` (`af941eef919e`) on `main` `4052991b`; the change was rebased. |
| Workspace | `~/Documents/Projects/gitman-workspaces/dpy-corpus` |
| Testee | run `20261011T130620Z-b33822909882`, PASS (pytest, ruff, ruff-format, ty) |
| Full run command | `python -m devenv_py.corpus {harvest SOURCE \| evaluate [SOURCES] \| all \| bench}` |

The guide proposed `dpy harvest`. The code ships `python -m devenv_py.corpus`. The default tests
run only small cases. The full corpus run is manual.

## Counts (final run)

| Source | batch | alone | secret | fails | total |
| --- | --- | --- | --- | --- | --- |
| devenv-examples | 45 | 24 | 0 | 3 | 72 |
| devenv-tests | 119 | 21 | 4 | 15 | 159 |
| fleet (private, local state) | 17 | 48 | 11 | 35 | 111 (142 found, 31 duplicates) |

Every `batch` and `alone` fixture has a stable truth: 0 unstable fixtures (two cold runs; raw and
normalized equal). The fleet run found 0 broken symlinks after the `.archive/` and `.worktrees/`
exclusion. No `devenv.local.nix` is in the output.

## Reasons for the `fails` class

- Examples (3): `compose/projectB` imports a sibling outside the copy. `go` lacks `gomod2nix.toml`
  in the yaml-input overlay. `overlays` lacks its `path:` input subflake.
- Tests (15): 5 internal tests use `path:` inputs into devenv's `src/modules` or sibling
  directories. `eval-cache-path-input/project` uses a path input. 5 nested fixtures import siblings
  or the git root. `dotenv-nix` lacks attribute `BASE`. `multiverse` needs a lambda argument.
  `syntax-error` has a Nix syntax error. `missing-input-error` fails the validity probe (attribute
  `package` missing, the `git-hooks` input is absent).
- Fleet (35): 11 import a sibling or input module that the copy lacks. 4 template goldens use
  `repoman.managers`, which is undeclared in a stock pin. 3 miss a path or file in the copy. Others
  fail for named reasons in `summary-final.json`.

Observation: most fleet failures are limits of the harvest (the copy holds one directory). They are
not devenv failures. Inference: the cause for the fleet fixtures `nixvim` and three
`structured-agents` fixtures is not checked.

## Pilot coverage (fixtures that evaluate and touch the subtree)

| Subtree | examples | tests | public total | fleet |
| --- | --- | --- | --- | --- |
| `languages.python` | 8 | 16 | 24 | 46 |
| `services.postgres` | 5 | 5 | 10 | 3 |

The static prediction of phase A (23 and 10 public fixtures) holds: 24 and 10. The corpus size
threshold of Step 15 is met without the fleet.

## Timing (final run, all sources)

Total 978 s. Truth run 1 took 294 s, truth run 2 took 243 s, validity took 440 s. Public `alone`
fixtures fetched their inputs from the network (first run, 554 s for truth run 1). Free disk stayed
above 60 GiB. No build ran. The batch timing table is in [step-2-3.md](./step-2-3.md).

## The validity check

`nix/validity.nix` is a new file (request `-O dpyValidity.request:path`). `introspect.nix` is
untouched. It runs three checks.

1. Undeclared option.
2. Each touched option, forced to shallow depth: attribute names and weak-head children. A
   submodule with declared options goes only to weak head, because `git-hooks.src` has no default.
3. A probe of `config.enterShell`. It exposes a missing integration input (`missing-input-error`).

Errors that `tryEval` cannot catch abort the evaluation, and bisection isolates them. Limit: the
check is not a full `devenv shell` build. It misses a failure inside a nested value, such as a
script `exec` that throws.

## Departures and notes

1. Triage input rule: compare input name and `url` only. An extra key other than `url` or `inputs`
   makes a fixture `alone`. `follows` differences are ignored. A pin `devenv` URL that holds the
   revision makes a fixture with `devenv: github:cachix/devenv` `alone`. `gleam` and `simple` are
   `alone` by their `nixpkgs` URL, so 45 fixtures are `batch` where the survey predicted 47.
2. `secret` detection: `secretspec` (any `.nix` or `.yaml`, or `secretspec.toml`), `sops`, `agenix`,
   and `vault` only as `vault-agent|vault secrets|VAULT_TOKEN|config.vault`, so `services.vault` is
   not secret. 4 public tests and 11 fleet fixtures are `secret`. The harness does not evaluate
   them.
3. `alone` fixtures run in `~/.local/state/devenv-py/corpus/alone/<source>__<name>/`. The pin yaml
   merges under the fixture yaml. The directory gets the pin lock and the harness modules. A
   relative yaml `imports` entry becomes an extra candidate module. An input-relative import
   (`simple-remote`) stays in yaml and gives an empty truth. The timeout is 600 s per fixture.
4. Truth holds the project directory where an option interpolates `config.devenv.root` (`nginx`,
   `mkcert`, `claude-agents`). `corpus.py` first scrubbed it to `<root>` and the home directory to
   `<home>`. `ad9476284450` moved this into the normalizer.
5. A nested fixture (a directory inside another fixture) is a separate fixture named with `__`.
   Those that import siblings fail with the real devenv message. Fleet fixtures copy `devenv.nix`,
   `devenv.yaml`, `secretspec.toml`, and relative literal imports inside the project. Five fleet
   projects with outside imports are recorded in the provenance field `unresolved_imports`.
6. The Nix store source path of the pin was garbage collected once during the run. `prefetch_devenv`
   refetches it.
7. The corpus size is 5.7 MB in 1357 files (below the 20 MB limit). `LICENSE` (Apache 2.0) and
   `NOTICE` sit in `corpus/devenv-examples` and `corpus/devenv-tests`. No `/home/andrew` path is in
   a committed file.
8. `pyyaml` joined `pyproject.toml` and `uv.lock` as a direct dependency. It was transitive.
9. The agent ran `ruff format` on `corpus.py` and `test_corpus.py` as an editor step. Verification
   ran through Testee only.

## Gate GM4

Met. Every fixture has a class. Every `batch` and `alone` fixture has a stable truth (0 unstable).
Every `fails` entry has a reason.

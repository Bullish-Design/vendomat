# Sub-phase 0 — inventory and decisions

**Date:** 2026-09-07
**Scope:** the facts CONCEPT §6 phase 0 asks for, plus the two owner calls.

## Owner decisions

### §8.2 — source authority in store mode

**Vendomat's `flake.lock` alone is authoritative.**

`repoman.lock` gains no `toolchain:` source kind. In store mode `repoman.lock`
carries no manager entries at all. `repoman-sync` reads the closure's provenance
manifest and fails, actionably, if `repoman.lock` still names a manager by
`path:` or `git:`. There is no implicit precedence and no silent fallback.

Rationale: one lock, one truth. It also matches the target — a consumer repo
declares zero first-party Python dependencies, so it has no per-repo toolchain
policy left to express.

### Roster

Four packages: `repoman`, `copyroom`, `docman`, `gitman`. The roster is complete.

**`testee` is deliberately out.** Its tools — pytest, ruff, ty — import the
consumer's own code, so a shared `testee` cannot do its job. It stays a per-repo
`pyproject.toml` dev dependency, installed by `uv sync` into the consumer venv.
This keeps RepoMan's registry entry (`install="uv"`, project 12) correct and
unchanged. Owner decision, 2026-09-07.

**`templateer` is out too** (owner, 2026-09-07). It was the heaviest tool to
materialize and the only one needing new derivations, and it is not a RepoMan
manager: it has no key in the registry and no manager module. Treat it like
testee — a per-repo `pyproject.toml` dependency where a repo actually uses it.

That leaves the closure with exactly the four commands RepoMan's registry names.

`zelligate`, `mypi-agent` and `alliman` from CONCEPT §3.2 are out of scope. They
are not in the machine venv today, so packaging them buys nothing yet.

Consequence: CONCEPT §6 phase 2 reads "add `testee`, then `docman`". Only docman
remains in it. `pytest-json-report` and `import-linter` no longer need Nix
derivations — they stay uv-resolved dependencies of testee.

## Console scripts and interpreters

Every roster tool already requires Python >= 3.13. The 3.13 baseline of CONCEPT
§8.3 needs no negotiation. (templateer, now out of scope, asks for >= 3.12, which
3.13 satisfies anyway.)

| tool | version | console script | entry point | backend |
| --- | --- | --- | --- | --- |
| repoman | 0.7.2 | `repoman` | `repoman.cli:main` | setuptools |
| copyroom | 0.7.4 | `copyroom`, `demo` | `copyroom.cli:main` | hatchling |
| testee | 0.3.0 | `testee` | `testee.cli:app` | hatchling |
| docman | 0.2.0 | `docman` | `docman.cli:app` | hatchling |
| gitman | 0.6.1 | `gitman` | `gitman.cli:main` | hatchling |
| templateer | 0.4.0 | `templateer` | `templateer.cli:entrypoint` | hatchling |

`copyroom` exports a second script, `demo` (`demo:main`). It is a generic name
and must not enter the roster closure — CONCEPT §3.2 requires the join to fail
on duplicate executable names, and `demo` would be the first collision. Drop it
in the package, or expose only the named executables.

## Runtime dependencies, against nixpkgs

Probed at python313Packages. `MISSING` means the package must be materialized
in Vendomat before its consumer can be built.

| dependency | nixpkgs | needed by |
| --- | --- | --- |
| pydantic 2.12.5 | yes | all six |
| typer 0.24.0 | yes | repoman, copyroom, testee, docman, gitman |
| jinja2 3.1.6 | yes | repoman, testee |
| pyyaml 6.0.3 | yes | copyroom, templateer |
| copier 9.16.0 | yes | copyroom |
| tomlkit 0.14.0 | yes | copyroom |
| pytest 9.0.3 | yes | testee |
| ruff 0.15.20 | yes | testee |
| ty 0.0.56 | yes | testee |
| pytest-json-report | **MISSING** | testee — out of the closure |
| import-linter | **MISSING** | testee — out of the closure |
| minijinja | **MISSING** | templateer — out of the closure |
| pydantic-ai-slim[openai] | **MISSING** | templateer — out of the closure |
| click | yes | templateer |
| pyjutsu 0.21.1 | vendomat-built | gitman |

Cost, final: **the roster needs no new derivations at all.** repoman, copyroom
and docman resolve entirely from nixpkgs; gitman adds only the pyjutsu wheel this
flake already vends. Every `MISSING` row above belongs to testee or templateer,
and both are out of the closure. CONCEPT §8.1 named package materialization as
the principal cost of this project; scoping the roster to RepoMan's own managers
removed it.

## Venv-path call sites

The mutable machine venv is `~/.local/share/repoman/venv`. It currently holds
`copyroom`, `docman`, `gitman`, `repoman`, `templateer`, `vendomat`, `copier`,
`demo`, `dunamai`, `typer` and `pygmentize`.

RepoMan already has most of the seam CONCEPT §4.1 asks for:

- `modules/devenv.nix` declares `repoman.toolchainBin`, a read-only shell
  expression for the machine venv's `bin`. Manager modules interpolate it.
  This is the option that becomes provider-aware.
- `modules/devenv.nix` `enterShell` prepends `$REPOMAN_TOOLCHAIN_VENV/bin` ahead
  of the consumer venv. The order is already correct for store mode.
- `modules/managers/testee.nix` is the exception: it hard-codes
  `${config.devenv.state}/venv/bin/testee` for `repoman:test`,
  `repoman:test:ci` and `enterTest`. It must move to the resolver.
- `modules/scripts/repoman-sync.sh` holds the venv installation: line 57 and 353
  probe `$toolchain_venv/bin`, line 368 runs `uv pip install`, line 95 runs
  `install-skills`. Only the last survives in store mode.
- `src/repoman/checks.py:132` mirrors the testee venv path in Python and must
  follow the same resolver.

## Shell-entry constraint

The `enterShell` block above prints a warning and continues when the toolchain
is absent. Store mode must keep that shape: report, do not abort. A broken
closure took loci-core's devenv down once (gitman project 32, G3) and must not
be able to again.

# Project 04 research report — 2026-07-21

## Target and boundaries

Implement the first Python source-catalog vertical slice for `knappy` (owned project) and
`pydantic` (Vendomat-managed vendor source). Source checkouts are agent-grounding material only:
the implementation must not change a consumer's `pyproject.toml`, `uv.lock`, or uv source tables.
Owned repositories are inspected but never cloned, reset, cleaned, or checked out by Vendomat.

Environment baseline:

- Vendomat commit: `064072dc8a262e893e647e2ac60c699f32044684`
- Branch: `main`, with pre-existing uncommitted publisher and documentation work preserved
- Prescribed environment: `devenv shell`, Python 3.13.13
- Baseline command: `devenv shell -- testee verify`
- Baseline result: passed (`ruff`, `ruff-format`, `ty`, and `pytest`) before Project 04 edits
- Baseline artifact: `artifacts/2026-07-21-baseline-02/verify.log`

The first sandboxed baseline stopped before project tests because Nix could not open its user
fetcher cache. The identical command succeeded with host/Nix access. This was an environment
boundary, not a project failure.

## Revision evidence

KnapPy's canonical sibling checkout was inspected read-only. Its `origin` is
`git@github.com:Bullish-Design/knappy.git`; local `main` and the upstream `main` ref both resolved
to `9fe266e30bd02cb4f453d5a9586c3c412e0b453f`. The committed policy uses the canonical HTTPS
repository spelling and that full revision:

- [KnapPy repository](https://github.com/Bullish-Design/knappy)
- [KnapPy reviewed commit](https://github.com/Bullish-Design/knappy/commit/9fe266e30bd02cb4f453d5a9586c3c412e0b453f)

Vendomat's current `uv.lock` resolves Pydantic `2.13.4`. A read-only `git ls-remote` showed that
the annotated `v2.13.4` tag object `07b73712023f052c7c008c4a9c5121b4894e44ec` peels to source
commit `cf67d4b3193c3fe43ede18612ed62785eee11382`. The catalog records the peeled commit, never the
mutable tag name or tag object:

- [Pydantic v2.13.4 release](https://github.com/pydantic/pydantic/releases/tag/v2.13.4)
- [Pydantic reviewed commit](https://github.com/pydantic/pydantic/commit/cf67d4b3193c3fe43ede18612ed62785eee11382)

This matching version/revision choice is useful grounding, but it does not prove that the PyPI
wheel in `uv.lock` is byte-identical to this checkout. Status and doctor therefore report the
installed version and catalog revision as separate fields.

## Git lifecycle findings

The implementation follows Git's documented model:

- [`git clone`](https://git-scm.com/docs/git-clone) creates the managed checkout and records the
  declared repository as `origin`.
- [`git fetch`](https://git-scm.com/docs/git-fetch) obtains the exact catalog commit without using
  a branch name as identity.
- [`git checkout --detach`](https://git-scm.com/docs/git-checkout) leaves managed source at the
  immutable reviewed commit rather than on an advancing branch.

Existing managed clones are inspected before mutation. A dirty tree or unexpected `origin` is a
hard refusal; no reset or clean fallback exists. An owned-project revision mismatch is also fatal
to sync and doctor, but Vendomat never repairs it. This conservative choice prevents generating a
map that appears canonical while pointing at the wrong source.

## Regression strategy

Focused tests cover catalog validation, dependency intersection, deterministic atomic source-map
output, owned-project diagnostics, dry-run immutability, dirty-clone refusal, CLI exit codes, and
clone/fetch/detached-HEAD behavior against a temporary local bare repository. Ordinary tests make
no external network request and never clone the real Pydantic repository.

There is no temporary compatibility patch to remove. The evidence does not prove Loci-Core
integration (explicitly out of scope for this slice), submodule/LFS behavior, source-to-wheel byte
identity, or source grounding for dependencies that do not yet have reviewed catalog entries.

## Final evidence

### Global source-root amendment

On 2026-07-21 the cache layout was explicitly made machine-global. Vendomat now reads committed
catalog policy from its checkout (or the Nix-provided `VENDOMAT_VENDOR_ROOT`) and independently
defaults writable third-party source state to `~/vendor`. A catalog vendor `cache` is relative to
that global root, so Pydantic's `cache = "pydantic"` resolves to `~/vendor/pydantic`. Owned project
paths remain consumer-relative and are never moved into the global vendor cache.

The existing clean 428 MB Pydantic checkout was moved from the old repository-local
`vendor/src/pydantic` location to `/home/andrew/vendor/pydantic`; it was not downloaded again.
Its detached revision and clean state were preserved.

The final repository-prescribed run passed on 2026-07-21:

```text
devenv shell -- testee verify
Verification: PASSED
Commands: ruff=passed, ruff-format=passed, ty=passed, pytest=passed
```

The latest captured log is `artifacts/2026-07-21-global-root-verification-02/verify.log`; Testee's
normalized report is `.testee/runs/2026-07-21T19-24-15Z-e4f3ca/testee-report.json` (ignored
runtime state).

The local bare-repository integration test synchronizes a temporary consumer whose lock contains
KnapPy, Pydantic, and an uncataloged package. It verifies that the map contains only KnapPy and
Pydantic, KnapPy remains the canonical sibling checkout with no managed duplicate, Pydantic is
detached at the exact revision, a second sync is byte/mtime stable, and the consumer's
`pyproject.toml` and `uv.lock` remain byte-identical.

A real catalog acceptance run, with no `--source-root` override, found Pydantic at
`/home/andrew/vendor/pydantic`, detached at `cf67d4b3193c3fe43ede18612ed62785eee11382`, and updated
this repository's ignored `.vendomat/sources.toml` to that absolute path. A second identical sync
reported both the clone and map unchanged. Status reported catalog revision `cf67d4b…` separately
from installed version `2.13.4`; doctor returned only the intended warn-level list of dependencies
not yet cataloged. Before/after hashes remained:

```text
31ff818c2c090cbc84bf250ea503a962dd045413a8611ba1c9c607a135556882  pyproject.toml
f3a6fac3f54d51b4f5eccd8d18e1ed510e8df86031e67efedb9f4a31b38d2638  uv.lock
```

## Loci-Core consumer integration — 2026-07-21

### Phase 0 baseline

The integration began from Vendomat `064072dc8a262e893e647e2ac60c699f32044684`,
Loci-Core `57c83f41192092a9ca4b132046e9eadf77dfeeb2`, and KnapPy
`9fe266e30bd02cb4f453d5a9586c3c412e0b453f`, all on `main`. Vendomat's existing
Project 04 and earlier dirty work was preserved. Loci-Core and KnapPy each had only their known
pre-existing `.gitignore` modification.

Loci-Core initially had no `uv.lock`. Its initial file hashes were:

```text
6668aa2ef9cd4199461306491413104469290f567c975733349347f8b60b0c41  pyproject.toml
fb6aa57f0892ee946b5cdeb716506508eee1665f82769f8e269b05577d97fbcc  .gitignore
```

The documented `devenv tasks run loci:verify` baseline passed all seven tasks: lint and typecheck
passed, 98 unit tests passed, 31 golden tests passed, and 241 property tests passed. The aggregate
reported `RESULT: GREEN`. The first two non-PTY captures ended during devenv's interactive shell
evaluation rather than at a project failure boundary; the successful PTY run established the real
baseline. Baseline state is in `artifacts/2026-07-21-loci-integration-baseline-01/state.log`, and
the two incomplete attempts are retained rather than overwritten.

The baseline build generated an ignored `uv.lock` with SHA-256
`29df5ff158d1ae57b0807994e23f9e168c1de261fa5c9786d3086879a8bde5a0`. It records KnapPy as the
editable `../knappy` checkout and Pydantic and `ruamel.yaml` as PyPI registry distributions. This
is observed environment state, not acceptable final dependency policy.

### `ruamel.yaml` canonical-source finding

Loci-Core deliberately pins the distribution to `ruamel.yaml==0.18.6`; its serializer golden
tests and source commentary still describe ruamel-derived byte behavior. PyPI records the 0.18.6
sdist (SHA-256 `8b27e6a217e786c6fbe5634d8f3f11bc63e0f80f6a5890f28863d9c45aac311b`), release date
2024-02-07, and the project repository as SourceForge:

- https://pypi.org/project/ruamel.yaml/0.18.6/
- https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/

The canonical upstream code repository is Mercurial, not Git. Vendomat's current catalog and sync
contract require a full 40-character Git commit and Git clone lifecycle. Consequently there is no
truthful `vendor/python/ruamel-yaml.toml` entry that can be added under the present schema. A GitHub
mirror would violate the explicit no-guessed-mirror constraint. Phase 1 therefore stops at this
honest limitation; the installed distribution identity remains separately reproducible through
the exact PyPI version and artifact hashes. This does not prove a source-repository revision to
sdist byte-identity mapping.

### Loci-Core integration implementation

KnapPy is not published on PyPI: the official `https://pypi.org/pypi/knappy/json` endpoint
returned HTTP 404. The canonical HTTPS Git repository exposes the reviewed commit
`9fe266e30bd02cb4f453d5a9586c3c412e0b453f` on `main`. Loci-Core therefore retains the ordinary
`knappy` requirement and replaces its editable sibling override with this immutable uv Git source:

```toml
[tool.uv.sources]
knappy = { git = "https://github.com/Bullish-Design/knappy.git", rev = "9fe266e30bd02cb4f453d5a9586c3c412e0b453f" }
```

The resulting tracked `uv.lock` resolves KnapPy 0.1.2 from that exact Git commit, Pydantic 2.13.4
from PyPI, and `ruamel.yaml` 0.18.6 from PyPI. Installed KnapPy's `direct_url.json` independently
records the canonical repository, requested full revision, and matching commit ID. Neither the
manifest nor lock contains `../knappy`, `/home/andrew/vendor`, or another source-review path.

Loci-Core now imports Vendomat's module and enables `knowledge.enable`. A `git+file` input was
rejected because direct inspection proved that it omitted the untracked Project 04 implementation.
A root `path:` input worked but copied the entire 831 MB dirty workspace, including `.git`,
`.devenv`, caches, and evidence. The final local-development input instead points at the 164 KB
filtered snapshot under `consumer-flake-input/`, containing only flake/package metadata plus
`lib/`, `modules/`, `src/`, and `vendor/`. This exposes current uncommitted code without staging or
committing user work. Its removal condition is an authorized Vendomat Project 04 checkpoint; at
that point Loci-Core should use the canonical Vendomat Git URL.

The generated source map is ignored by Loci-Core. Real-consumer inspection found that the initial
map recorded paths but not reviewed revisions, contrary to this phase's acceptance contract.
Focused tests failed first, then Vendomat gained a deterministic `[revisions]` table while
preserving the compatible `[sources]` table. The final map records:

```text
knappy path=../knappy rev=9fe266e30bd02cb4f453d5a9586c3c412e0b453f
pydantic path=/home/andrew/vendor/pydantic rev=cf67d4b3193c3fe43ede18612ed62785eee11382
```

Two consecutive final real syncs produced SHA-256
`3ffdcb7381418007a5e9ffd43e00729f9538698dc786e8aeca4b4241a3edf4be`; the second reported
`unchanged` and retained mtime `1784664403`. Source doctor exits 0 with the map current. Its only
warnings are the preserved dirty owned KnapPy checkout and intentionally incremental catalog
coverage, including the documented Git-incompatible `ruamel-yaml` source.

Loci-Core's README now provides the minimal agent discovery hook: it names the generated map,
explains paths and reviewed revisions, requires separate installed-version/origin checks, and
forbids using review checkouts as package sources.

### Final verification

Vendomat's prescribed `devenv shell -- testee verify` passed after the source-map change: ruff,
ruff-format, ty, and pytest all passed. The normalized Testee report is
`.testee/runs/2026-07-21T20-00-49Z-5d6f6e/testee-report.json`; raw output is in
`artifacts/2026-07-21-loci-integration-vendomat-final-01/verify.log`.

All required Loci-Core commands passed from the canonical Git/registry dependency form:

```text
devenv tasks run loci:build      PASS (18 packages resolved; 17 checked)
devenv tasks run loci:lint       PASS
devenv tasks run loci:typecheck  PASS
devenv tasks run loci:test       PASS
devenv tasks run loci:verify     PASS (golden, unit, property, lint, typecheck; 131s task graph)
```

Separate raw logs are under `artifacts/2026-07-21-loci-integration-loci-final-01/`. Final source
sync/status/doctor logs are under `artifacts/2026-07-21-loci-integration-source-final-01/`, and
final worktree/hash/cache evidence is in
`artifacts/2026-07-21-loci-integration-final-state-01/state.log`.

Pydantic is clean and detached at its catalog revision with canonical origin. KnapPy remains at
its original HEAD with only the pre-existing `.gitignore` modification. No repository was
committed, pushed, reset, or cleaned. The evidence proves the tested Python 3.13/devenv workflow;
it does not prove source-to-wheel byte identity or provide Mercurial support in Vendomat.

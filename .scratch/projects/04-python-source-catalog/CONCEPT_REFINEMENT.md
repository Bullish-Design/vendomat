# Project 04 — Python source catalog for agent grounding

## Refined decision

Vendomat maintains a local, pinned Git clone for every approved Python dependency so agents can
search implementation code, tests, packaging metadata, and curated library-specific notes.

Those clones are **not installation sources**. Python environments continue to install the
dependency form declared by the consumer and locked by uv: normally a PyPI wheel, or a pinned
Git/release source where PyPI is not appropriate. Vendomat's clone cache is a knowledge and
investigation layer, not a replacement package index or build system.

This removes the major costs of source installs: per-machine compilation, platform-toolchain
requirements, divergence from published artifacts, and publish-time lock churn. It preserves the
main benefit: a stable, fast, locally searchable source tree for every dependency an agent needs
to understand.

## Source ownership

There are two local source locations, determined by ownership.

| Kind | Local source of truth | Vendomat action | Install source |
|---|---|---|---|
| `project` | The canonical checkout of one of Bullish Design's repos | Reference and inspect; never clone/copy | A normal release/Git dependency, not that checkout |
| `vendor` | Vendomat's managed third-party clone cache | Clone, pin, refresh, and inspect | Normal PyPI wheel or an explicitly declared upstream source |

Vendomat must never create a duplicate clone of an owned project merely to satisfy a cache layout.
KnapPy remains the canonical `../knappy` checkout. Pydantic and ruamel.yaml are third-party
checkouts Vendomat maintains itself.

## Installation policy

The consumer's `pyproject.toml` remains the runtime/install authority. It must not point at
Vendomat's clone cache or a consumer `vendor/` link.

Example Loci-Core target:

```toml
[project]
dependencies = [
  "pydantic>=2.12.5",
  "ruamel.yaml==0.18.6",
  "knappy",
]

[tool.uv.sources]
# Use this only while KnapPy is unpublished; pin an immutable commit.
knappy = { git = "https://github.com/Bullish-Design/knappy", rev = "<40-character-commit>" }
```

When KnapPy is published to PyPI, the preferred final form is simply a version requirement and a
normal `uv.lock` entry. Pydantic and ruamel.yaml stay ordinary registry/wheel dependencies.

This means:

- `uv sync` uses its normal cache and compatible wheels.
- Native or platform-specific dependencies do not suddenly require local compilers.
- The lock is the exact installed artifact graph, rather than a graph built from arbitrary local
  checkout state.
- Editing a clone can never accidentally change a running environment.

The existing Vendomat local-path publisher remains useful, but becomes a narrow opt-in for a
project intentionally developing against an unpublished local sibling. It is not the mechanism
for the general dependency source catalog.

## Catalog: committed metadata, local clone bytes

Vendomat needs a committed catalog that answers: *where is this distribution's canonical source,
which immutable revision has been reviewed, and where should an agent search it?*

Suggested layout:

```text
vendor/
  python/
    knappy.toml
    pydantic.toml
    ruamel-yaml.toml
  src/                         # ignored: managed third-party Git checkouts
    pydantic/
    ruamel-yaml/
```

Owned-project entry:

```toml
[package]
name = "knappy"
kind = "project"
repository = "https://github.com/Bullish-Design/knappy"
rev = "0123456789abcdef0123456789abcdef01234567"

[local]
path = "../knappy"
```

Third-party entry:

```toml
[package]
name = "pydantic"
kind = "vendor"
repository = "https://github.com/pydantic/pydantic"
rev = "0123456789abcdef0123456789abcdef01234567"

[local]
cache = "vendor/src/pydantic"
```

`vendor/src/` is ignored local state. The TOML entry is versioned policy. A managed clone must be
at the catalog revision; a missing, dirty, or mismatched clone is visible to `vendomat doctor`.
The catalog revision is for source grounding, not a claim that the installed wheel was built from
that exact commit unless that relationship has been explicitly verified.

## Consumer declaration and agent paths

Consumers declare which catalog entries matter to their direct and resolved dependency graph:

```toml
[python]
packages = ["knappy", "pydantic", "ruamel-yaml"]
```

`vendomat vendor sync` then ensures each required clone/checkpoint exists and writes a generated,
ignored source map for tools and agents. It does **not** rewrite `pyproject.toml`, `uv.lock`, or the
environment.

Suggested generated map:

```text
.vendomat/sources.toml

[sources]
knappy = "../knappy"
pydantic = "/…/vendomat/vendor/src/pydantic"
ruamel-yaml = "/…/vendomat/vendor/src/ruamel-yaml"
```

Avoid a `consumer/vendor/<package>` symlink unless a tool specifically needs it. The generated map
is clearer about its non-install role and avoids users mistaking source clones for runtime inputs.

The dependency skill can direct agents precisely:

> For implementation questions about Pydantic, inspect the `pydantic` entry in
> `.vendomat/sources.toml`. Vendomat has pinned that checkout to `<commit>`; compare any behavior
> against the installed `uv.lock` version before treating it as runtime truth.

## Loci-Core: first real integration

Loci-Core remains the first appropriate consumer because it has a real owned dependency (KnapPy),
ordinary third-party dependencies (Pydantic and ruamel.yaml), an actual GitHub remote, and no
pre-push-hook conflict.

Its current KnapPy path source is useful evidence of active sibling development:

```toml
knappy = { path = "../knappy", editable = true }
```

The refined migration is not to replace that path with another local source. It is:

1. Add catalog entries for KnapPy, Pydantic, and ruamel.yaml, each with a reviewed immutable
   source revision.
2. Run `vendomat vendor sync` to validate the KnapPy checkout and clone the third-party sources.
3. Add Loci-Core's concise `vendomat.toml` package declaration.
4. Write `.vendomat/sources.toml` and install the corresponding dependency skills.
5. Create and commit Loci-Core's `uv.lock` if it is absent.
6. Decide KnapPy's install form deliberately: a pinned Git commit while unpublished, or a normal
   PyPI requirement after release. Remove the editable sibling path from the committed public form.
7. Run Loci-Core's normal verification and confirm an agent can locate each catalog source.

The existing pre-push publisher may still be used temporarily if local-path KnapPy development
needs a public Git rewrite. It is separate from the all-dependency clone workflow.

## Clone lifecycle and safety

Not every PyPI distribution maps reliably to a Git repository. Vendomat must never guess silently.

- A distribution becomes source-grounded only after a reviewed catalog entry names its repository
  and immutable revision.
- Package/distribution spelling differences (`ruamel.yaml` vs `ruamel-yaml`) are normalized using
  PEP 503; the upstream repository spelling remains separate metadata.
- Monorepos record an optional `subdirectory` solely to help agents locate the package source.
- Git submodules and LFS must be explicit catalog flags; `vendor sync` either initializes them or
  fails clearly.
- A clone is detached at the catalog revision. Dirty trees are allowed for investigation but
  reported; skills identify them as non-canonical.
- The catalog's source revision and the installed package version are separate facts. `doctor`
  reports both; it does not imply equivalence without a verified release mapping.

## Command surface

```text
vendomat vendor add <distribution> --repository <url> [--project]
vendomat vendor sync [--repo-root <consumer>]
vendomat vendor status [--repo-root <consumer>]
vendomat vendor doctor [--repo-root <consumer>]
```

- `vendor add` drafts a catalog entry. It may display candidate upstream URLs but never selects one
  without review.
- `vendor sync` clones or validates required sources, checks revisions, and writes the generated
  source map.
- `vendor status` reports catalog revision, clone revision, dirty state, canonical owned-project
  path, and the resolved installed version from `uv.lock` when available.
- `vendor doctor` reports missing clone, missing owned-project checkout, wrong revision, dirty
  clone, source-map drift, untracked dependency, and stale skills.

## Non-goals

- No third-party path or editable installs.
- No replacement of uv's wheel cache, resolver, hashes, or lockfile authority.
- No automatic repository guessing or bulk cloning from PyPI metadata.
- No copying of owned repositories into Vendomat.
- No automatic rewrite of `pyproject.toml` or `uv.lock` for general source grounding.
- No transformation of Loci-Core's separate `lsp/` uv project until the root workflow is proven.
- No replacement of Vendomat's native-wheel path; Nix wheel artifacts and source grounding solve
  different problems.

## Acceptance evidence

Project 04 is complete when Loci-Core proves all of the following:

1. KnapPy is found at its canonical `../knappy` checkout; Vendomat does not create a duplicate.
2. Pydantic and ruamel.yaml are present as Vendomat-managed, pinned third-party clones.
3. `.vendomat/sources.toml` maps all three dependencies to their local search locations.
4. Dependency skills cite those locations and revisions.
5. Loci-Core installs normally from its declared PyPI/pinned-Git sources; no dependency is
   installed from Vendomat's clone cache.
6. Loci-Core's normal verification passes with a committed `uv.lock`.
7. Missing, dirty, or revision-mismatched sources produce clear `vendomat vendor doctor` output.

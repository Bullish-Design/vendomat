# Issue: vendor subsystem assumes Python-package identity — can't ground non-Python sources

**Status:** open — **subsumed by `06-generic-vendor-manager`** (this is now step 1
of that larger store-first reframe, not a standalone patch)
**Filed:** 2026-07-22
**Area:** `vendor` subsystem (`src/vendomat/sources.py`, `docs/SOURCE_CATALOG.md`, `vendor/python/`)

## Summary

Vendomat's third-party source catalog is documented and implemented as a
**Python** source catalog. But its actual value — a pinned local checkout of an
upstream repo "for agent grounding and investigation" (`SOURCE_CATALOG.md`) — is
useful for **any** codebase, including non-Python ones (Rust, TypeScript, Go).
Today a non-Python source can be cataloged but can **never be synced**, and the
docs frame the whole feature as Python-only. This surfaced while vendoring
`silverbulletmd/silverbullet` (a Rust + TypeScript app) as reference material for
the `015-silverbullet-server` project.

## Root cause

`sync_sources` selects what to clone via `relevant_entries`:

```python
# src/vendomat/sources.py:130-134
def relevant_entries(catalog, dependencies):
    normalized = {normalize(dependency) for dependency in dependencies}
    return [catalog[name] for name in sorted(catalog.keys() & normalized)]
```

`dependencies = read_deps(consumer_root)` is the consumer's **Python** dependency
set (from `pyproject.toml`). An entry is synced only if its normalized name is in
that set (`catalog.keys() & normalized`). A Rust/TS project like `silverbullet`
is in no `pyproject.toml`, so it is **never "relevant"** and never clones —
regardless of a valid catalog entry.

Reinforcing Python assumptions:
- Catalog dir is hardcoded `vendor/python/` (`catalog.py:15` `CATALOG_DIR = Path("vendor/python")`).
- `docs/SOURCE_CATALOG.md` is titled "Python source catalog" and describes the
  contract purely in Python-install terms.
- The generated consumer map + `dep-<lib>` knowledge-skill install (`app sync`)
  are keyed on Python deps.

## Impact

- Cannot vendor a non-Python upstream for agent/notes grounding through the
  blessed path — the exact use case the catalog advertises ("for agent grounding
  and investigation, not Python installation").
- Workaround used for now: the catalog entry `vendor/python/silverbullet.toml`
  was added for policy/pin record, but the checkout at `~/vendor/silverbullet`
  (detached at `2.9.0` / `72bba941…`) had to be materialized **out-of-band** with
  a plain `git clone`, bypassing `vendomat vendor sync`.

## Proposed directions (pick one, discuss)

1. **Docs-first (minimum):** reframe `SOURCE_CATALOG.md` and the `vendor/python/`
   naming to state the catalog is for *source grounding of any ecosystem*, and
   document that sync selection is currently Python-dep-gated (known limitation).
2. **A `reference`/`always` selection mode:** let an entry opt out of the
   consumer-dep gate (e.g. `[package] select = "always"` or `kind = "reference"`)
   so `relevant_entries` includes it unconditionally. Smallest code change that
   unblocks non-Python grounding.
3. **Ecosystem-agnostic catalog layout:** generalize `CATALOG_DIR` beyond
   `vendor/python/` (e.g. `vendor/sources/`) and make selection independent of
   `read_deps` for non-Python kinds.

Recommendation: **(1) now + (2) next** — the docs change is honest and cheap; the
`select = "always"` escape hatch makes the feature actually deliver on its stated
"agent grounding" purpose without disturbing the Python-install path.

## Cross-reference

- Consumer of the vendored source: `~/Documents/Projects/.scratch/projects/015-silverbullet-server`.
- Catalog entry added: `vendor/python/silverbullet.toml`.

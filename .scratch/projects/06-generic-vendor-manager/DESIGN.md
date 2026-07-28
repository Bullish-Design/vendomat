# Design + plan: vendomat as a generic local vendor manager

**Status:** ACCEPTED — committed reframe (full, from the start). Supersedes the
narrow patch in `05-vendor-non-python-sources`.
**Filed:** 2026-07-22
**Area:** whole `vendor` surface — `lib/`, `modules/`, `src/vendomat/{catalog,sources,deps,install,publish}.py`, `vendor/`, `flake.nix`, docs

## 0. Decision

vendomat becomes a **store-first local vendor manager**:

> A machine-local vendor store holding (a) **pinned source checkouts of any repo**
> (any language) for exploration/research/grounding, and (b) **Nix-cached build
> artifacts of local owned libraries** consumed by other local libs to make
> development faster. The **store is the primary object**; consumer repos are
> optional users that draw from it.

We commit to the **full reframe now** — not an incremental `select`-field patch
that we might stop at. The phases in §6 are execution ordering for one committed
design, not decision points.

**Locked decisions** (previously open questions):

1. **`~/vendor` holds source checkouts only.** Build artifacts stay
   **store-resident in `/nix/store`**, surfaced via `packages.wheelhouse`; they
   never need a writable working copy under `~/vendor`. Layout:
   `~/vendor/<name>/` = a source checkout, full stop.
2. **Dep-gating is removed from the core.** Source entries are **always
   materialized** — no consumer required, no `pyproject` intersection. The only
   surviving dep-gated behavior is the **knowledge-skills** layer (install a
   `dep-<lib>` skill into a repo only if that repo actually depends on the lib) —
   which is a property of that optional layer, not of vendoring.
3. **Knowledge-skills stay PEP 503 / Python-dep keyed;** source entries use
   free-form store names. They serve different masters and do not share a
   namespace.
4. **Broaden vendomat's identity** (flake description + README headline) as part
   of this work — the narrow "vend maturin/PyO3 wheels" charter is retired.

## 1. Baseline — what vendomat is today

Four concerns, fused under a consumer-pull model:

1. **Build cache.** `lib/mkMaturinWheel.nix` + `lib/mkArtifact.nix` (has a
   `builder ? "maturinWheel"` seam, one builder) → `packages.wheelhouse` →
   consumers get `UV_FIND_LINKS` via `modules/devenv.nix` (`nativeLibs`,
   `sharedCargo`). Content-addressed wheels, built once, shared. **Works — kept.**
2. **Source catalog.** `vendor/python/*.toml` (pydantic `CatalogEntry`) →
   `~/vendor/<cache>` checkouts. Selection = `catalog.keys() ∩ consumer deps`
   (`sources.py:130` `relevant_entries`). **Reframed** (see below).
3. **Knowledge/skills.** `vendor/libs/<lib>/{meta.toml,notes.md,SKILL.md}`;
   `vendor add` scaffolds, `app sync` installs `dep-<lib>` skills. **Kept as an
   optional layer**, still dep-gated.
4. **Publishing.** local↔GitHub publishing + pre-push hooks (`publish.py`).
   **Kept as an optional layer.**

Everything today hangs off a consumer (`DEVENV_ROOT`, `read_deps`,
`relevant_entries`, `UV_FIND_LINKS` injected into the consumer shell). The reframe
inverts this.

## 2. The inversion (consumer-pull → store-first)

| | vendomat today | committed target |
|---|---|---|
| Primary object | the consumer repo | the vendor store itself |
| Source selection | inferred from Python deps | explicit — you track what you want |
| Language (source) | Python/uv assumptions | agnostic |
| Entry types | scattered code paths | one typed notion: `source \| artifact` |
| Knowledge + publish | baked into core | optional layers over the store |
| `~/vendor` | mixed cache | source checkouts only |

## 3. Couplings — shed / keep / demote

**Shed (accidental Python/consumer coupling on the source side):**
- Consumer-dep-gated selection for source entries (`relevant_entries`).
- The `vendor/python/` directory name → `vendor/sources/`.
- PEP 503 name normalization for source entries (`catalog.py:33-38`).
- Full-40-char-commit requirement at author time (`catalog.py:47-52`) — accept a
  ref (tag/branch/HEAD), resolve to a pinned commit for the user.

**Keep (legitimate):**
- Wheels are Python/uv-specific *because that is their consumption path*.
  `mkArtifact { builder }` is the generalization seam for other build types
  **later, only when a real non-wheel artifact exists** — not speculatively.
- The whole wheelhouse → `UV_FIND_LINKS` mechanism, unchanged.

**Demote to optional layers:** knowledge-skills (#3) and publishing (#4).

## 4. The model — typed vendor entry

Two entry types, each with its own committed materialization:

```
# source entry  →  vendor/sources/<name>.toml
[entry]
name       = "silverbullet"        # free-form store name (not PEP 503)
type       = "source"
origin     = "https://github.com/silverbulletmd/silverbullet"
ref        = "2.9.0"               # tag | branch | commit; authored input
rev        = "72bba941…"           # resolved 40-char commit; pinned truth
# materialization: ~/vendor/silverbullet/ (git checkout, detached at rev)

# artifact entry  →  the existing wheelhouse (owned local libs)
#   authored as today via the nix lib/module; NOT under ~/vendor.
#   surfaced via packages.wheelhouse → UV_FIND_LINKS. Unchanged mechanism.
```

- **`source`**: always materialized under `~/vendor/<name>`. No consumer needed.
  `ref` is what the human wrote; `rev` is the resolved pin (authoritative). Both
  third-party repos and owned sibling checkouts are `source` — "consume as an
  editable path" is a separate, optional consumer-side wiring, not a vendor kind.
- **`artifact`**: the wheelhouse path, store-resident, unchanged.

The old `kind = project|vendor` distinction collapses: both were "a checkout";
their difference (editable-path consumption vs read-only grounding) moves to the
consumer layer and stops being a vendoring concern.

### CLI (store-first)

```
vendomat vendor track <git-url> [--ref <r>] [--name <n>]   # resolve ref→rev, author entry, clone now
vendomat vendor list                                       # what the local store holds
vendomat vendor sync                                       # materialize every source entry (consumer-optional)
vendomat vendor status | doctor                            # store health; consumer-optional
vendomat vendor rm <name>                                  # drop entry + checkout
```

`track` is the "explore before using" ergonomic: it resolves the ref via
`git ls-remote`, writes `vendor/sources/<name>.toml`, and clones into
`~/vendor/<name>` immediately — first-classing the manual steps used for
`silverbullet` in `015-silverbullet-server`.

## 5. Consumer layer (optional, over the store)

Consumers opt in explicitly; nothing is inferred to decide *what may be
vendored*:
- **Artifacts:** `nativeLibs = [ … ]` in `modules/devenv.nix` (as today).
- **Skills:** `app sync` still installs `dep-<lib>` skills gated on the repo's
  real Python deps — this is the *only* place dep-gating remains, and it is a
  skills-install policy, not a vendoring gate.
- **Editable source consumption** (formerly `kind = project`): an explicit
  consumer-side path wiring, out of scope for the vendor core.

## 6. Implementation plan (phases of the one committed design)

Each phase is an execution slice toward the §4 model; we are building all of it.

**P1 — Store core (new typed entry + `vendor/sources/`).**
- New `SourceEntry` model (free-form name, `origin`, `ref`, resolved `rev`);
  catalog dir `vendor/sources/`. Retire PEP 503 / full-sha constraints for source
  entries. Reader validates + materializes independent of any consumer.

**P2 — Ref resolution + `vendor track` / `list` / `rm`.**
- `git ls-remote` ref→rev resolution; `track` authors + clones; `list`/`rm`
  manage the store. `sync` materializes all source entries with no consumer.

**P3 — Decouple selection.** Remove `relevant_entries` gating from source
materialization entirely (delete the consumer-dep path from `sync_sources`; keep
`read_deps` only for the skills layer).

**P4 — Demote knowledge + publishing** to clearly-optional modules (docs +
layout); no behavior change, identity change. `app sync` skill-gating stays.

**P5 — Naming/identity sweep.** `vendor/python/` → `vendor/sources/` migration
(+ any lingering entries), `VENDOMAT_*` env + nix-module references updated in
lockstep, docs retitled ("Python source catalog" → "vendor store"), `flake.nix`
description + README headline broadened per Decision §0.4.

**P6 — Deferred:** generalize `mkArtifact.builder` beyond `maturinWheel` — only
when a real second builder exists.

Dependencies: P1→P2→P3 are the source-vendoring spine; P4/P5 pay identity debt and
can land alongside; P6 is out until motivated.

## 7. Retrofit of existing artifacts

- `vendor/python/silverbullet.toml` → move to `vendor/sources/silverbullet.toml`
  in the new schema (`type="source"`, `ref="2.9.0"`, `rev="72bba941…"`). The
  `~/vendor/silverbullet` checkout already matches the target materialization.
- `vendor/python/pydantic.toml` (real Python dep, `kind=vendor`): re-express as a
  `source` entry; its skill/dep behavior, if any, moves to the skills layer.

## 8. Conventions / guardrails for implementation

- VCS via **gitman** (jj + colocated git) — never raw jj/git.
- Verify via **testee** — never invoke pytest/ruff/ty directly.
- Keep pydantic-validated models + the man-family CLI contract (0/1/2/3 exit
  codes, `doctor` preflight, Pydantic-normalized output).

## 9. Cross-references

- `05-vendor-non-python-sources` — subsumed (its `select=always` idea is now
  "source entries are always materialized," P3).
- `~/Documents/Projects/.scratch/projects/015-silverbullet-server` — first
  consumer of generic source vendoring (`~/vendor/silverbullet`).
- Baseline code: `lib/mkArtifact.nix` (`builder` seam), `sources.py:130`
  (`relevant_entries`, to be removed from source path), `catalog.py:15,29,33-52`
  (Python-isms to shed).

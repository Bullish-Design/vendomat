# vendomat — design: the vendor layer (artifacts + knowledge) for the `*man` family

> Status: design draft (scope **C — narrow now, broad-ready**). This revision is grounded in
> the *actual* sibling repos on disk (`repoman`, `zelligate`, `gitman`/`Pyjutsu`), not just
> vendomat's README. Where an earlier draft guessed, the guess is called out and corrected.
>
> vendomat has **two faces**: *artifacts* (build native deps once into wheels, §3) and
> *knowledge* (per-dependency notes + agent skills, §7). Both read from one dedicated `vendor/`
> data repo.

## 0. TL;DR

The composition framework vendomat seemed to want **already exists**: it's `repoman`, the
conductor for the `*man` family, with `repoman.lock` as its manifest. vendomat should **not**
re-invent composition, a manifest, or a registry. Its real job — named verbatim as an open
item in `repoman/CONCEPT.md` §8 — is the **fleet path**: build native modules (pyjutsu, and
any future native `*man` dep) **once** into content-addressed wheels so `repoman.lock` entries
resolve to a *prebuilt wheel* instead of a per-repo `cargo` compile.

Scope C: ship that native-artifact vendor now, behind two cheap seams (an open `source`-kind
vocabulary and a `VENDOMAT_DEV_ROOT` indirection) so a broader fleet layer can grow later *if
usage demands it* — without rework.

The same `vendor/` repo that anchors artifacts also carries vendomat's **second face**:
per-dependency **knowledge** — your notes plus a curated agent skill for each library your
personal libs use, installed into a repo gated on the deps it actually imports. This is
repoman's `devman` pattern (curated skills installed into `.claude/skills/`) generalized from
"skills about devenv" to "skills about each dependency." It ships in a deliberate 1→3→2 rollout
(knowledge → shared constraints → selective vendored source); see §7.

## 1. The ecosystem as it actually is (verified)

### 1.1 repoman — the conductor (this is the composition framework)

`repoman/CONCEPT.md`: *"One devenv import that turns any repo into a fully-managed agentic
repo… RepoMan is the conductor for the `*man` family: a per-repo lifecycle front door that
composes the individual managers."*

- **The modules are the `*man` family**, each its own devenv repo with tests/examples/CLI:
  `copyroom` (templating), `gitman` (vcs), `testee` (verify), `docman` (docs), `zelligate`
  (sessions), `mypi-agent` (agent runtime), `allium-env` (specs). Shared contract: one Typer
  CLI per tool, Pydantic-normalized output, `init`/`doctor`, runs inside `devenv shell`, a
  `0/1/2/3` exit-code contract, distributed as a devenv module imported via `devenv.yaml`.
  **This is the "small composable modules with tests/examples/server interfaces" vision.**
- **`repoman.lock` (TOML) is the manifest** (verified against `repoman/tests/consumer-example/
  repoman.lock`). Each entry is two fields — `package` (the dist name) + `source` — e.g.
  `[managers.git]` → `package = "gitman"`, `source = "path:…/gitman"`.
  `modules/scripts/repoman-sync.sh` resolves `source` two ways, and the lock's own header
  documents exactly these two forms:
  - `source = "path:/local/checkout"` → `uv pip install --editable=<path>` (live local edits);
  - `source = "git+https://…@vX.Y.Z"` → uv resolves the pinned ref.
  - **That `path:` vs `git+@ref` switch is already a hybrid local/release model** at the uv
    layer. Native-dep "pseudo-entries" key off a manager — verified: `[managers.git-pyjutsu]`
    with `package = "pyjutsu"`, base = part before the first `-` — and install alongside it.
- **`src/repoman/registry.py` is the roster only** — key → `command`, `tier`, `doctor`/`status`
  args, `nix_input`. It carries **no remote URLs or paths**; name→source lives in
  `repoman.lock`. (Correction to an earlier draft that expected the registry to map remotes.)
- **No dev-root / fleet authority exists.** `CONCEPT.md` §2: *"Fleet/workspace management is
  explicitly out of scope for v1."* There is no `config.py` anymore. The `repoman_dev_root`
  named in vendomat's README is **not** a real repoman feature.

### 1.2 The gap vendomat fills (named in repoman itself)

`repoman/CONCEPT.md` §6 + §8:
- gitman depends on **pyjutsu**, a Rust/maturin/PyO3 native extension. To make it installable,
  `modules/managers/gitman.nix` provisions a **full Rust toolchain + maturin into every
  consumer devenv** that enables `git`, and pyjutsu is installed from a `path:`/`git+` source
  — i.e. **compiled from scratch per repo**.
- §8, remaining gitman follow-up, verbatim: *"a fleet path (published pyjutsu wheel + `git+…`
  sources) so `path:` checkouts aren't required."*

**That fleet path is vendomat.** Vend pyjutsu's wheel once; consumers install it with zero
cargo and without the Rust toolchain.

### 1.3 zelligate — a *session* orchestrator (orthogonal, but sets conventions)

`zelligate/README.md`: a Docker-first persistent **Zellij web terminal** per repo. A daemon
scans a workspace dir for opted-in repos and runs a per-repo browser terminal (ports, status,
restart backoff). Its discovery is about **terminals**, not artifacts or dependency wiring —
so a broader vendomat would **not** collide with it. Two conventions worth matching:

- **Dev-root is an env var:** `ZELLIGATE_WORKSPACE_DIR` (default `/workspaces`). The ecosystem
  idiom for "where the repos are" is env-driven, not a config file. → confirms decision 4.
- **Per-repo manifest is emitted by a devenv task as JSON:** the daemon runs
  `devenv shell zelligate-manifest`, cached on `devenv.{nix,yaml,lock}` mtime. A reusable shape
  for any per-repo declaration vendomat might later need.

## 2. What vendomat is (scope C)

vendomat is the **vendor layer** for the `*man` family, with two faces that share one `vendor/`
data repo:

- **Face A — artifacts:** build native deps (pyjutsu, …) once into content-addressed wheels so
  `repoman.lock` entries resolve to a prebuilt wheel instead of a per-repo `cargo` compile (§3).
- **Face B — knowledge:** install per-dependency notes + agent skills into a repo, gated on the
  deps it actually uses — "devman, but per dependency" (§7).

**Now (narrow):** ship Face A (closes the named gap) and Face B's first slices (knowledge, then
shared constraints). vendomat plugs into repoman's existing `source` resolution and skill
router — it does **not** introduce a competing manifest, registry, or composition layer.

**Broad-ready (later, only if usage demands):** the fleet/dev-root layer repoman deferred —
cross-repo build-once + local-path composition. Not built now; kept reachable by two seams
(§4).

### What vendomat is NOT (boundaries)

- Not a composition framework — **repoman** is.
- Not a manifest/registry — **`repoman.lock`** is.
- Not a session/workspace orchestrator — **zelligate** is.
- Not a skill *router* — **repoman** generates that from its manager roster; vendomat installs
  per-dependency skills *alongside* it, discovered via standard SKILL.md frontmatter (§7.2).

## 3. Face A — artifacts: the mechanism (narrow scope, build now)

### 3.1 `lib/mkArtifact.nix` — generalize `mkMaturinWheel`

Today `lib/mkMaturinWheel.nix` builds a maturin crate → one `.whl` in a content-addressed
derivation. Generalize to `mkArtifact { pname; src; version?; builder ? "maturin"; }` that
dispatches to a per-kind builder (§5). The maturin path is the existing code, unchanged.

### 3.2 A new `source` kind in `repoman.lock` — `wheel:`

`repoman-sync.sh`'s `target()` resolves `path:` → editable and `git+…` → uv. Add one kind:

```python
# in repoman-sync.sh's embedded resolver
if source.startswith("wheel:"):
    return source[len("wheel:"):]   # a bare requirement, e.g. "pyjutsu>=0.8"
                                    # uv resolves it from UV_FIND_LINKS (the vendomat wheelhouse)
```

vendomat's devenv module supplies the wheelhouse and the safety latch (this is essentially the
*current* `modules/devenv.nix`, repurposed):

```nix
env.UV_FIND_LINKS      = "${wheelhouse}";              # store dir of vended wheels
env.UV_NO_BUILD_PACKAGE = "pyjutsu";                   # fail loudly, never compile from source
```

So a consumer's `repoman.lock` flips one field:

```toml
# before — every repo recompiles pyjutsu
[managers.git-pyjutsu]
package = "pyjutsu"
source  = "path:/home/andrew/Documents/Projects/Pyjutsu"   # → uv pip install --editable (cargo build)

# after — every repo installs the vended wheel, zero cargo
[managers.git-pyjutsu]
package = "pyjutsu"
source  = "wheel:pyjutsu>=0.8"                             # → resolved from vendomat's UV_FIND_LINKS
```

`wheel:` is a genuinely **new third** `source` form — the lock currently documents only `path:`
and `git+…@ref` (verified in its header), so adding it is an explicit, additive change to
repoman's resolver and the lock's documented vocabulary (the open `source`-kind seam, §4).

### 3.3 The hybrid, expressed through the existing `source` switch

No new mode flag is needed — repoman.lock's `source` already encodes it, and it maps cleanly
onto vendomat's existing `vendor.self` idea:

| who | `repoman.lock` source | effect |
|---|---|---|
| pyjutsu's **own** repo (you're developing it) | `path:…/Pyjutsu` | editable; shared `CARGO_TARGET_DIR` + `sccache` for fast rebuilds (`vendor.self`) |
| **consumers** (gitman, others) | `wheel:pyjutsu>=0.8` | prebuilt wheel, no cargo, no Rust toolchain |
| **release/CI** pin | `git+https://…@<rev>` (built into a store wheel) | reproducible, content-addressed (decision 3) |

### 3.4 Building the wheelhouse

`nix build .#wheelhouse` (already present) builds every vended lib once; the store path is
shared across all repos on the same input rev — first repo builds, the rest are cache hits.
The flake `inputs` keep pyjutsu as a `git+file://` source (tracked files only — excludes the
multi-GB untracked `target/`), exactly as today.

## 4. The two broad-ready seams (cheap insurance, build now)

1. **Open `source`-kind vocabulary.** Make `wheel:` one member of an extensible set rather than
   a pyjutsu special-case, so future kinds (`bin:` for a vended `rust-cli`, `closure:` for a
   service) slot in without touching the resolver's shape.
2. **Dev-root indirection.** Resolve "where a module's source lives" through a single
   `VENDOMAT_DEV_ROOT` lookup (default `~/Documents/Projects`, overridable; consistent with
   zelligate's `ZELLIGATE_WORKSPACE_DIR`). Narrow mode reads explicit `path:`/`git+` from the
   lock and barely needs it — but routing through the seam now is what lets a future fleet mode
   resolve names→paths itself and auto-init missing checkouts.

Nothing else fleet-related is built now: no cross-repo scan, no clone-on-miss, no compose
graph. Those are the broad layer, gated on evidence.

## 5. Builders (pluggable; only maturin needed now)

Each builder implements `provideLocal` (editable + shared cache, for the lib's own repo) and
`buildRelease` (content-addressed artifact). Only `maturinWheel` is required for scope C; the
rest are sketched so the dispatch shape is right.

| kind | `provideLocal` (dev) | `buildRelease` | needed now |
|---|---|---|---|
| `maturinWheel` (native-python) | `maturin develop`, shared `CARGO_TARGET_DIR` + `sccache` | today's wheel derivation | ✅ |
| `pythonEditable` (pure) | `uv` editable / `path:` | wheel/sdist | later |
| `rustCli` | `cargo build` shared target; symlink onto PATH | store derivation of binary (`bin:`) | later |
| `service` | run from checkout | container / store closure (`closure:`) | later |

## 6. Worked example — gitman/pyjutsu, before & after

**Before:** any repo with `repoman.managers = [ … "git" … ]` gets, via
`repoman/modules/managers/gitman.nix`: `pkgs.maturin`, `languages.rust.enable = true`, and a
`path:`/`git+` pyjutsu that `uv` **compiles from source** — minutes of cargo + a multi-GB
`target/`, per repo.

**After (vendomat):**
1. `nix build .#wheelhouse` builds pyjutsu's `cp313-abi3` wheel once into the store.
2. The consumer imports vendomat's module → `UV_FIND_LINKS` + `UV_NO_BUILD_PACKAGE=pyjutsu`.
3. `repoman.lock`'s `git-pyjutsu` entry uses `source = "wheel:pyjutsu>=0.8"`.
4. `repoman-sync` installs the prebuilt wheel — **zero cargo**; `gitman.nix` no longer needs to
   provision Rust/maturin for consumers (only pyjutsu's *own* repo does).

This is the §8 "fleet path," delivered.

## 7. Face B — the knowledge layer (per-dependency notes + skills)

The second face attaches *knowledge* to the dependencies your personal libs use, so an agent
working in a repo has your curated guidance for each library it actually imports. This is the
exact pattern repoman's `devman` already proves — it installs curated devenv-literacy skills
into `.claude/skills/` and routes them — generalized from "skills about devenv" to "skills
about each dependency."

### 7.1 The `vendor/` repo (pure data)

Knowledge lives as version-controlled data, one entry per library:

```
vendor/
  constraints.txt              # unified external version pins (see 7.3)
  libs/
    pydantic/
      meta.toml                # version range, docs URL, "why I use it / what I rejected"
      notes.md                 # freeform gotchas / patterns — the raw material
      SKILL.md                 # curated skill; frontmatter name/description/auto_trigger.keywords (devman's format)
      src/                     # OPTIONAL: vendored sdist/source for the agent to grep (7.4)
    typer/
      ...
  modules/devenv.nix           # the importable module: reads a repo's deps, installs matches
```

The same repo also holds Face A's artifact inputs, so `vendor/` is the single anchor for
"everything vendomat knows about my dependencies" — both their bytes and their meaning.

### 7.2 `vendor-sync` — install knowledge, gated on usage

Mirrors devman's `install_devman` (verified in `repoman/src/repoman/devman/install.py`): on
`enterShell` (or an explicit task), vendomat
1. reads the consuming repo's dependency set (`uv.lock` / `pyproject.toml` / `repoman.lock`),
2. intersects it with `vendor/libs/`,
3. installs each matching `SKILL.md` as a **flat sibling** under the skills dir —
   `<skills_dir>/dep-<lib>/SKILL.md` (devman uses `<skills_dir>/<name>/SKILL.md`, one level deep
   — the layout Claude Code's skill discovery expects, so **not** a nested `deps/<lib>/`),
4. writes a drift manifest `<skills_dir>/.vendor-source` (version + installed-skill list),
   mirroring devman's `.devman-source` / allium's `.allium-…-source`, so `repoman doctor` can
   flag staleness.

**How they're discovered (verified):** repoman's "router" is a *generated* entrypoint skill
(`repoman/src/repoman/skills.py` → `<skills_dir>/repoman/SKILL.md`) rendered from the **manager
roster** — it lists managers only, so vendomat's per-dependency skills do **not** appear in that
table. They're surfaced instead by Claude Code's own skill mechanism via SKILL.md frontmatter
(`name`, `description`, `auto_trigger.keywords` — the format devman's skills use). So vendomat
installs skills *alongside* repoman's, discovered independently; it does not (and need not) touch
the router. Optional later: extend repoman's entrypoint to add a "dependencies" routing section.

The discipline that makes this useful, not noise: **only install skills for deps the repo
actually uses.** An agent with 40 irrelevant dependency skills is worse off than one with none.

### 7.3 Rollout: 1 → 3 → 2 (knowledge, then constraints, then source)

Deliberately staged so the cheap, certain value lands first and heavier mechanics are gated on
it proving out:

1. **Knowledge only (first).** `meta.toml` + `notes.md` + `SKILL.md` per lib, usage-gated.
   Validates the curation loop (write / agent-draft → install → does it help?) at near-zero risk
   and near-zero maintenance. No byte-vendoring — uv's global cache already holds the bytes.
2. **+ Shared constraints (fast follow).** A top-level `constraints.txt` the personal libs
   reference, so they pin the *same* external versions. This is the one slice of byte-vendoring
   that isn't redundant with uv, and it's the backbone the knowledge layer hangs on: every skill
   becomes "the pydantic 2.9 skill," giving usage-gating and **review-on-bump** a concrete
   trigger. Cost: introduces real cross-repo coupling (a breaking bump touches all consumers at
   once) — adopt deliberately.
3. **+ Vendored source (selective, per library).** Add `src/` only for the handful of libraries
   worth grounding (the ones you fight with). The skill then says "the implementation is at
   `vendor/libs/<lib>/src/` — grep it" instead of the agent guessing. High payoff *when scoped*;
   blanket source-vendoring is disk + noise + a second staleness axis.

### 7.4 Why vendored *source* (not wheels) is the only byte-vendoring worth doing

uv already caches and hardlinks the installed wheel, so a wheelhouse of pydantic saves nothing
for *external* deps. The distinct value of `src/` is **grounding**: vendored *source* carries
tests, docstrings, and internals a built wheel may strip — material an agent can read and verify
your notes against. Reserve it for libraries where that grounding pays for the upkeep. (Native
*personal* libs like pyjutsu are the opposite case — there the *wheel* is the win, §3.)

### 7.5 Staleness is the real enemy

A wrong skill is worse than no skill. Defenses, in order of leverage:
- **tie every skill to its pin** (7.2/7.3) so a version bump flags the matching skill for review;
- **agent-assisted drafting + human curation** — a `vendor-add <lib>` task drafts `notes.md` +
  `SKILL.md` from the lib's docs/source/changelog; you approve;
- **usage-gating** so unused, drifting skills never reach an agent.

## 8. Decisions — revised against the verified ecosystem

| # | Decision | Final | Why (changed from earlier draft?) |
|---|---|---|---|
| 1 | Manifest | **Extend `repoman.lock`** with a `wheel:` source kind | ✅ changed — do **not** invent `vendomat.toml`; the manifest already exists |
| 2 | Name→source | **Read `repoman.lock`'s `source`** field; no parallel registry | ✅ changed — `registry.py` is roster-only; source lives in the lock |
| 3 | Release identity | **Committed git rev** (`git+…@rev` → store wheel); `--allow-dirty` escape hatch | ✔ confirmed — matches repoman.lock's existing pin style |
| 4 | Dev-root | **`VENDOMAT_DEV_ROOT` env var**, default `~/Documents/Projects` | ✅ changed — repoman has no dev-root; env-var idiom matches zelligate |
| 5 | Knowledge home | **vendomat's second face** (one "vendor layer": artifacts + knowledge) | new — matches the vendor identity; contributes skills to repoman's router, no collision |
| 6 | `vendor/` contents | **Knowledge first → + shared constraints → + selective source** | new — cheap certain value first; constraints as backbone; source scoped per-lib |
| — | Scope | **C: narrow native-vendor now, broad-ready seams** | new — narrow closes the named gap; seams keep fleet reachable |

## 9. Open items / next steps

**Face A (artifacts):**
- ~~Confirm `repoman.lock` shape~~ — **done.** Verified two-field entries (`package` + `source`)
  and the real `[managers.git-pyjutsu]` pseudo-entry in `repoman/tests/consumer-example/
  repoman.lock`; the lock documents only `path:` and `git+…@ref` today, so `wheel:` is a new
  third form (§1.1, §3.2).
- **Land the `wheel:` resolver** in `repoman-sync.sh` (one `elif`) — coordinate as a small PR to
  repoman, since the file lives there. Note its `target()` reads `source` only (not `package`),
  so `wheel:pyjutsu>=0.8` → returns `pyjutsu>=0.8` for uv to resolve from `UV_FIND_LINKS`.
- **abi3 / interpreter tag** still binds consumers to the wheel's `cp313-abi3` floor (README
  constraint stands) — `UV_NO_BUILD_PACKAGE` turns a tag mismatch into a hard error, by design.

**Face B (knowledge):**
- ~~Verify repoman's skill-router reuse~~ — **done.** repoman generates a roster-driven
  entrypoint skill (`skills.py`); manager skills install as flat siblings under
  `<skills_dir>/<name>/SKILL.md` (`devman/install.py`) with a `.<tool>-source` drift manifest.
  vendomat follows the same shape (`dep-<lib>/SKILL.md` + `.vendor-source`); per-dep skills are
  discovered via SKILL.md frontmatter, not the generated router (§7.2).
- **Build `vendor-sync`'s dep-reader** — parse the consuming repo's dependency set from
  `uv.lock` / `pyproject.toml` / `repoman.lock`, intersect with `vendor/libs/`.
- **Build `vendor-add <lib>`** — the agent-assisted draft task (notes + SKILL.md from docs/
  source/changelog) feeding human curation; emit devman-style frontmatter.
- ~~**Wire review-on-bump**~~ — **done (M4).** `vendor/constraints.txt` carries the unified pins;
  `vendomat doctor`'s `vendor:staleness` check compares each `.vendor-source` recorded pin against
  the consumer's resolved version (`uv.lock`) and warns on divergence, and `vendor:constraints`
  keeps each `meta.toml` pin in lockstep with `constraints.txt`. Surfaced in **`vendomat doctor`**,
  not `repoman doctor` (per IMPLEMENTATION_PLAN issue #2 — vendomat is not a repoman manager).

**Scope:**
- **Decide if/when broad (B) is warranted** — revisit once wheels + knowledge are in use and you
  can see whether cross-repo auto-init is actually reached for, or whether per-repo
  `path:`/`wheel:` + usage-gated skills were always enough.

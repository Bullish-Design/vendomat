# KICKOFF — vendomat M0 bootstrap + Face B (knowledge layer)

> Build out **vendomat's second face** — per-dependency **knowledge** (notes + agent
> `SKILL.md`s installed into a repo, gated on the deps it actually uses: "devman, but per
> dependency") — on top of an **M0 bootstrap** that turns vendomat from a Nix-flake-only repo
> into a `*man`-shaped Python Typer package. Face A (native-wheel vending) is **already done
> and shipped**; this packet is everything that remains.

You are starting a FRESH session in `/home/andrew/Documents/Projects/vendomat`.
Read this packet, then `docs/DESIGN.md` (§7 is Face B) and `docs/IMPLEMENTATION_PLAN.md`
(M0, M2–M4), then **propose a step-by-step plan for approval before writing any code.**

---

## Role & where this fits

vendomat is the **vendor layer** for repoman's `*man` family, with two faces over one
`vendor/` data area:

- **Face A — artifacts (DONE, shipped):** build native deps (pyjutsu = Rust/maturin/PyO3) once
  into content-addressed wheels; consumers install a prebuilt wheel via a `wheel:` source kind
  in `repoman.lock`. **Milestone M1 landed:** `lib/mkArtifact.nix` dispatcher + `flake.nix`
  wiring (this repo, `main`); the `wheel:` resolver + `repoman.nativeBuild` Rust opt-out
  (repoman `main`, commit `c5b4071`); consumer-example flipped to `wheel:pyjutsu>=0.8`.
- **Face B — knowledge (THIS WORK):** per-dependency notes + agent `SKILL.md`s installed into
  a consuming repo, gated on its actual dependency set. Rollout is a deliberate **1 → 3 → 2**:
  knowledge first (M2), shared constraints next (M4), selective vendored source last (deferred).

**Master plan reference:** `docs/IMPLEMENTATION_PLAN.md` — milestones M0 (bootstrap), M2
(knowledge + `vendor-sync`), M3 (`vendor-add`), M4 (constraints + review-on-bump). M1 is the
only completed milestone.

---

## Current state (verified — do not re-derive)

**What exists:**
- `flake.nix` — inputs (`nixpkgs`, `pyjutsu` as `git+file`), outputs `lib.mkArtifact`
  (+ `mkMaturinWheel` alias), `packages.{pyjutsu-wheel,wheelhouse,default}`,
  `devenvModules.default`.
- `lib/mkArtifact.nix` — one-builder dispatcher (`builder ? "maturinWheel"`); `lib/mkMaturinWheel.nix`
  — the maturin→wheel derivation.
- `modules/devenv.nix` — the consumer module: `vendor.{enable,libs,self,sharedCargo}` options;
  sets `UV_FIND_LINKS` (wheelhouse) + `UV_NO_BUILD_PACKAGE` (the vended libs).
- `gitman.toml` + `.claude/skills/gitman/SKILL.md` — **vendomat is now gitman-colocated** (jj +
  colocated git). **Route ALL version control through `gitman`** (see Guardrails).

**What does NOT exist yet (the gap this packet fills):**
- **No Python package.** No `devenv.nix`, no `pyproject.toml`, no `src/vendomat/`, no `tests/`.
  vendomat ships zero Python today (M0 fixes this — it gates all of Face B).
- **No `vendor/` data area.** No `vendor/libs/<lib>/{meta.toml,notes.md,SKILL.md}`, no
  `constraints.txt`.
- **No CLI.** No `vendomat sync` / `vendomat add` / `vendomat doctor`.

---

## The shape this must take (grounded in the ecosystem)

The `*man` family contract (verified in repoman + its managers): **one Typer CLI per tool,
Pydantic-normalized output, `init`/`doctor`, a `0/1/2/3` exit-code contract, runs inside
`devenv shell`, distributed as a devenv module.** vendomat's Face B must mirror this.

**The precedent to copy is repoman's `devman` subsystem** (`src/repoman/devman/`), NOT the
manager roster. devman installs curated `SKILL.md`s into `.claude/skills/<name>/` gated on
context, writes a `.devman-source` drift manifest, and folds a `*_checks()` into doctor — it
has **no registry entry and no CLI of its own**. Read these before designing:
- `repoman/src/repoman/devman/install.py` — the install + manifest shape to mirror
  (`<skills_dir>/<name>/SKILL.md` + `.<tool>-source`).
- `repoman/src/repoman/devman/check.py` — the warn-only drift check folded into doctor.
- `repoman/src/repoman/checks.py` — `SelfCheck` model + `tomllib` usage.
- `repoman/src/repoman/aggregate.py` — `worst_exit` (the `0/1/2/3` aggregation).
- `repoman/src/repoman/cli.py` — the thin-Typer-app shape (imports logic from subpackages).
- An existing `*man` `pyproject.toml` (e.g. gitman/testee) — package + console-script layout.

**Three DESIGN issues already resolved (honor these — see IMPLEMENTATION_PLAN "issues"):**
1. **vendomat CLI delivery = Nix package on PATH** (the zelligate-provisions-zellij /
   gitman-via-pyjutsu pattern), **NOT** via the consumer venv and **NOT** a `repoman.lock`
   entry. vendomat's devenv module builds the `vendomat` CLI as a flake package and puts it on
   `PATH`. (DESIGN issue #3.)
2. **Drift surfacing lives in `vendomat doctor`**, not `repoman doctor` — vendomat is not a
   repoman manager and does not touch repoman's router. (issue #2.)
3. **`auto_trigger.keywords` is devman-compatible metadata, not native discovery.** Claude Code
   discovers skills by `name` + `description`; make `description` carry the real trigger text.
   (issue #4.)

---

## Work items (target paths in vendomat)

### M0 — bootstrap vendomat as a `*man`-shaped Python project (gates all of Face B)
- `devenv.nix` (new) — vendomat's own dev shell: Python 3.13, `uv`, ruff, pytest. (Matches the
  family stack; note `flake.nix` already pins `python313` for the wheel.) All in-repo commands
  run via `devenv shell -- …` from here on.
- `pyproject.toml` (new) — package `vendomat`, console script `vendomat`, deps `typer`,
  `pydantic`, stdlib `tomllib`. Mirror an existing `*man` pyproject.
- `src/vendomat/cli.py` (new) — thin Typer app with `sync` / `add` / `doctor` (stubs now),
  Pydantic-normalized output, `0/1/2/3` exit codes. **Copy** repoman's `checks.SelfCheck` /
  `aggregate.worst_exit` shape (don't import repoman).
- `flake.nix` — add a `packages.vendomat` (`buildPythonApplication`) output so the CLI can be
  delivered on PATH (issue #3); wire it into `modules/devenv.nix` later in M2.
- `tests/` (new) — pytest harness + a smoke test (`vendomat --help`, exit-code contract).
- **Acceptance:** `devenv shell -- pytest` green; `devenv shell -- vendomat doctor` returns the
  right exit code on an empty repo.

### M2 — Face B slice 1: knowledge, usage-gated (`vendor-sync` + first real dep skill)
- `vendor/libs/<lib>/{meta.toml,notes.md,SKILL.md}` (new) — seed **exactly one** real lib
  end-to-end (e.g. `pydantic` or `typer`) to validate the curation loop. `SKILL.md` uses devman
  frontmatter (`name` / `description` [/ `auto_trigger.keywords`]).
- `src/vendomat/deps.py` (new) — the **dep-reader**: parse the consuming repo's dependency set
  from `uv.lock` → `pyproject.toml` → `repoman.lock` (first that exists wins, in that
  precedence), normalize names, return a set. Pure function over file contents → unit-testable.
- `src/vendomat/install.py` (new) — mirror `devman/install.py`: intersect deps with
  `vendor/libs/`, copy each match to `<skills_dir>/dep-<lib>/SKILL.md` (**flat sibling**, not
  nested `deps/<lib>/`), write `.vendor-source` drift manifest (vendomat version + installed
  `dep-<lib>` list + the pin each skill is tied to).
- `src/vendomat/cli.py` — wire `vendomat sync` (= install gated on usage) and `vendomat doctor`
  (read `.vendor-source`; flag missing/stale — warn-only first, like devman's `check.py`).
- `modules/devenv.nix` — add a `vendor-sync` script (runs the **Nix-provided** `vendomat` CLI,
  issue #3) + an opt-in enterShell/task hook, run **after** deps resolve (mirror how repoman-sync
  runs install before `install-skills`). Add `knowledge.{enable,skillsDir}` options (default
  `.claude/skills`, matching `REPOMAN_SKILLS_DIR`).
- **Acceptance:** `deps.py` unit-tested with fixtures for each of uv.lock/pyproject/repoman.lock
  incl. precedence + name normalization; `install.py` installs only intersecting `dep-<lib>/`,
  writes `.vendor-source`, idempotent re-run; integration: a repo depending on the seeded lib
  gets exactly `dep-<lib>/`, an unrelated dep gets nothing; `vendomat doctor` exit codes on
  missing/stale/up-to-date.

### M3 — Face B tooling: `vendor-add <lib>` (agent-assisted draft)
- `src/vendomat/add.py` + `vendomat add <lib>` — scaffold `vendor/libs/<lib>/` and draft
  `notes.md` + `SKILL.md` (devman frontmatter) from the lib's docs/source/changelog, for
  **human curation** (never auto-published). Emit a **Pydantic-validated** frontmatter block so
  drafts can't ship malformed.
- **Acceptance:** golden test on generated frontmatter shape/required keys; `vendor-add` on a
  known lib produces a file `vendor-sync` installs and `doctor` accepts.

### M4 — Face B slice 2: shared `constraints.txt` + review-on-bump (adopt deliberately)
- `vendor/constraints.txt` (new) — unified external pins the personal libs reference.
- Tie every `dep-<lib>` skill to its pin in `.vendor-source`; `vendomat doctor` flags a skill
  **stale** when the lib's resolved version diverges from the pin its skill was written against
  (review-on-bump). Surface in `vendomat doctor` (issue #2), not repoman doctor.
- **Acceptance:** bump a pin in a fixture → `doctor` flags the matching skill stale; unchanged
  pins stay green.
- **NOTE:** introduces real cross-repo coupling (a breaking bump touches all consumers at once)
  — adopt only after M2 proves useful.

*(DESIGN rollout step 2 — selective vendored `src/` per library — is explicitly **deferred**:
lowest value, highest upkeep, gated on M2–M4 proving out.)*

---

## Sequencing

```
M0 (bootstrap) ─► M2 (knowledge + vendor-sync) ─► M3 (vendor-add) ─► M4 (constraints + review-on-bump)
```
M0 gates everything. M2 depends on M0. M3/M4 depend on M2. Land each milestone as its own
gitman lane → PR (see Guardrails). Seed exactly one real lib in M2 before scaling the curation.

---

## Open questions (surface during planning, don't block)

1. **`skills_dir` source of truth** — vendomat installs to `.claude/skills/dep-<lib>/`. Read
   `REPOMAN_SKILLS_DIR` if present, else default `.claude/skills`. Confirm interaction with
   repoman's own skill install (they're flat siblings; vendomat must not clobber repoman's).
2. **Where the `vendomat` CLI package is built** — a `packages.vendomat` flake output consumed
   by `modules/devenv.nix` (issue #3). Confirm the buildPythonApplication wiring mirrors how
   zelligate/alliman provision their binaries at the nix layer.
3. **Dep-reader precedence + name normalization** — uv.lock vs pyproject vs repoman.lock; PEP
   503 normalization (`_`↔`-`, case). Pin the precedence in one documented place.
4. **First seeded lib** — `pydantic` or `typer` (both are vendomat's own deps, so dogfoodable).
5. **abi3/interpreter floor** is a Face A concern only; Face B vendors no bytes (knowledge is
   text). Don't conflate.

---

## Source material (cite when implementing)
- `docs/DESIGN.md` — §2 (two faces), §7 (Face B: 7.1 vendor/ layout, 7.2 vendor-sync, 7.3
  rollout, 7.5 staleness), §8 decisions 5–6.
- `docs/IMPLEMENTATION_PLAN.md` — M0, M2, M3, M4; the 6 resolved DESIGN issues.
- `repoman/src/repoman/devman/{install,check,__init__}.py` — the subsystem precedent to mirror.
- `repoman/src/repoman/{checks,aggregate,cli,registry}.py` — `SelfCheck`, `worst_exit`, thin
  Typer app, the roster (what vendomat is NOT).
- vendomat `flake.nix`, `lib/mkArtifact.nix`, `modules/devenv.nix` — the Face A half to extend.
- A `*man` `pyproject.toml` (gitman/testee) — package/console-script layout.

## Guardrails
- **gitman for ALL version control.** vendomat is gitman-colocated (jj + colocated git). Use
  `gitman start <lane>` → edit → `gitman save -m …` → `gitman publish` → PR → merge → reconcile.
  **Never run raw `jj`/`git` mutations** (read-only `git log`/`status` is fine). One lane per
  milestone. Trunk `main` is frozen.
- **devenv for every in-repo command** once M0 lands: `devenv shell -- <cmd>` (pytest, ruff,
  vendomat). Before M0 there is no devenv — use `nix build`/`nix eval` for flake work.
- **No AI attribution** anywhere — commits, PR descriptions, comments, docs.
- **Copy, don't import, repoman** — replicate the small `SelfCheck`/`worst_exit` contract; do
  not add a dependency on the `repoman` package.
- Implement only M0 + Face B; do not touch Face A (`lib/`, the `wheel:` resolver) beyond adding
  the `packages.vendomat` output and `modules/devenv.nix` knowledge wiring.

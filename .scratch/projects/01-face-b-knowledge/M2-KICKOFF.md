# KICKOFF — vendomat M2: Face B slice 1 (knowledge, usage-gated)

> Build **Face B's first vertical slice**: per-dependency **knowledge** (`SKILL.md`s installed
> into a consuming repo, gated on the deps it actually uses — "devman, but per dependency").
> M0 (the `*man`-shaped Python package) is **done and merged**. M1 (Face A native wheels) shipped
> earlier. This packet is M2 only.

You are starting a FRESH session in `/home/andrew/Documents/Projects/vendomat`.
Read this packet, then `docs/DESIGN.md` §7 and `docs/IMPLEMENTATION_PLAN.md` M2, then **propose a
short step-by-step plan for approval before writing any code** (this project plans before coding).

---

## Where this fits

vendomat is the **vendor layer** for repoman's `*man` family — two faces over one `vendor/` data
area. Face A (native wheels) and **M0 bootstrap** are done. **M2 is Face B slice 1.** The master
packet `.scratch/projects/01-face-b-knowledge/KICKOFF.md` has the full multi-milestone context and
the verified ecosystem grounding — read it for the "why"; this file is the focused M2 "what/how".

Rollout is a deliberate **1 → 3 → 2**: knowledge (M2, this) → shared constraints (M4) → selective
vendored source (deferred). M3 (`vendor-add`) is tooling that comes after M2.

---

## Current state (verified post-M0 — do NOT re-derive)

**M0 merged to `main` @ `8d4c991`.** vendomat is now a `*man`-shaped Python Typer package. These
already exist — build on them, don't recreate:

- `pyproject.toml` — package `vendomat`, console script `vendomat = vendomat.cli:main`, runtime
  deps `typer` + `pydantic` (use stdlib `tomllib` for parsing — no new runtime deps). Dev dep is
  **`testee`** (path `../testee`), which brings ruff/ruff-format/ty/pytest. `[tool.ty.src]` scopes
  ty to `src`,`tests`.
- `src/vendomat/cli.py` — thin Typer app. `sync` and `add` are **no-op stubs to replace**;
  `doctor` is real (currently only checks for `.vendor-source` presence). Already has helpers:
  `_repo_root()` (→ `DEVENV_ROOT` or cwd), `_skills_dir()` (→ `REPOMAN_SKILLS_DIR` or
  `.claude/skills`), and `MANIFEST = ".vendor-source"`.
- `src/vendomat/checks.py` — Pydantic `SelfCheck(name, level, detail)` + `self_check_exit()` +
  `format_self_check()`. Levels map `ok`/`warn`/`fail` → `0`/`0`/`2` (the copied-not-imported
  repoman contract). **Extend this with the vendor checks; don't reinvent it.**
- `tests/test_cli.py`, `tests/test_checks.py` — pytest harness exists.
- `flake.nix` — `packages.vendomat` (`buildPythonApplication`, deps typer+pydantic) delivers the
  CLI **on PATH** for consumers (issue #3); plus Face A (`mkArtifact`, `wheelhouse`, `pyjutsu-wheel`).
- `modules/devenv.nix` — the **consumer module**. Today it wires Face A (`vendor.{enable,libs,…}`
  → `UV_FIND_LINKS`/`UV_NO_BUILD_PACKAGE`). **M2 adds Face B wiring here** (see work items).
- `devenv.nix`/`devenv.yaml` — vendomat's own shell (Python 3.13 + uv), imports `./nix/testee.nix`.
- `testee.toml` + `nix/testee.nix` — verification; `gitman.toml` (trunk `main`) — VCS.

**Does NOT exist yet (the M2 gap):** `vendor/` data area, `src/vendomat/deps.py`,
`src/vendomat/install.py`, the real `sync`/`doctor` logic, and the Face B half of `modules/devenv.nix`.

---

## Locked decisions (honor these — settled in planning)

1. **First seeded lib = `typer`** (a vendomat dep → dogfoodable). Seed exactly one lib end-to-end
   in M2 before scaling curation.
2. **Pure-core / wired-edges.** `deps.py` and `install.py` are **pure functions over explicit
   `Path` args** (fully unit-testable); the CLI and the devenv module supply the real locations.
3. **Vendor-data delivery.** The consumer's `vendomat sync` reads the knowledge tree from
   **`VENDOMAT_VENDOR_ROOT`**, which `modules/devenv.nix` sets to `${inputs.vendomat}/vendor` (the
   flake source already in the store). The CLI itself rides on PATH via `packages.vendomat`. **Do
   not** bundle `vendor/` into the wheel.
4. **`SelfCheck` is Pydantic** (already in `checks.py`) — keeps doctor output normalized per the
   `*man` contract while preserving the level→exit mapping.
5. **skills_dir = `REPOMAN_SKILLS_DIR` else `.claude/skills`; flat siblings.** vendomat writes
   `dep-<lib>/SKILL.md` + `.vendor-source`; repoman/devman write `<name>/SKILL.md` + `.devman-source`.
   Different names → they coexist without clobbering. Verify this.
6. **Drift lives in `vendomat doctor`**, never `repoman doctor` (vendomat is not a repoman manager).
7. **`auto_trigger.keywords` is devman-compatible metadata, not native discovery** — make the
   SKILL.md `description` carry the real trigger text (Claude Code discovers by name+description).
8. **Copy, don't import, repoman.** Mirror `devman/install.py`'s shape; add no `repoman` dependency.

---

## Work items (target paths)

### Data: seed `typer` end-to-end
- `vendor/libs/typer/meta.toml` — version range / docs URL / "why I use it, what I rejected" + the
  pin the skill is written against (the field `doctor` will later compare for staleness in M4).
- `vendor/libs/typer/notes.md` — freeform gotchas/patterns (the raw curation material).
- `vendor/libs/typer/SKILL.md` — curated skill with **devman frontmatter**: `name`, `description`
  (carry the real trigger text — decision 7), optional `auto_trigger.keywords`.

### `src/vendomat/deps.py` — the dep-reader (pure)
- `read_deps(repo_root: Path) -> set[str]`: parse the consuming repo's dependency set from
  **`uv.lock` → `pyproject.toml` → `repoman.lock`** — **first that exists wins, in that
  precedence** (document the precedence in ONE place: the module docstring).
- Per-format parsers (`tomllib`) so each is unit-testable with fixtures.
- **PEP 503 name normalization** (`re.sub(r"[-_.]+","-",name).lower()`) on both sides of the
  intersection. (`repoman.lock` entries carry `package = "<dist>"` — normalize that; note its
  `[managers.git-pyjutsu]` pseudo-entry shape.)

### `src/vendomat/install.py` — mirror `repoman/src/repoman/devman/install.py`
- `expected_libs(vendor_root: Path) -> list[str]` (mirror devman's `expected_skills()`): names
  under `vendor/libs/<lib>/` that have a `SKILL.md`.
- `install_knowledge(vendor_root, deps, skills_dir, repo_root) -> list[Path]`: intersect
  `expected_libs` with `deps`; copy each match `vendor/libs/<lib>/SKILL.md` →
  `<repo>/<skills_dir>/dep-<lib>/SKILL.md` (**flat sibling**, NOT nested `deps/<lib>/`); write the
  `.vendor-source` manifest under `skills_dir` (vendomat version via `importlib.metadata.version`,
  the installed `dep-<lib>` list, and each skill's pin from its `meta.toml`). **Idempotent** re-run.

### `src/vendomat/checks.py` — add the drift checks
- `vendor_checks(repo_root, skills_dir, vendor_root, deps) -> list[SelfCheck]` (mirror
  `repoman/src/repoman/devman/check.py`): are the **intersecting** skills installed? is the manifest
  version current? **warn-only first** (like devman) — flip to fail later if ever mandatory.

### `src/vendomat/cli.py` — wire the real commands
- `sync`: resolve `VENDOMAT_VENDOR_ROOT` (→ `--vendor-root` flag → env → error if unset), call
  `read_deps(_repo_root())` then `install_knowledge(...)`; print what was installed.
- `doctor`: read `.vendor-source`, run `vendor_checks(...)`, `format_self_check` + exit
  `self_check_exit(...)` (the 0/1/2/3 contract).

### `modules/devenv.nix` — the Face B consumer wiring
- Add `knowledge.{enable, skillsDir}` options (default `.claude/skills`, `REPOMAN_SKILLS_DIR`-aware).
- Put `inputs.vendomat.packages.${system}.vendomat` on PATH; set `VENDOMAT_VENDOR_ROOT =
  "${inputs.vendomat}/vendor"`.
- Add a `vendor-sync` task that runs the **Nix-provided** `vendomat sync`, **after** deps resolve
  (mirror how repoman-sync runs install before `install-skills`). Keep it opt-in (gated on
  `knowledge.enable`).

---

## Acceptance (what "done" means)

- `deps.py`: pytest fixtures for **each** of `uv.lock` / `pyproject.toml` / `repoman.lock`,
  including **precedence** (first-exists-wins) and **PEP 503 normalization** (`_`↔`-`, case).
- `install.py`: installs **only** intersecting `dep-<lib>/SKILL.md`; writes `.vendor-source`;
  **idempotent** re-run (no dupes, stable manifest). Integration fixture: a repo depending on
  `typer` gets exactly `dep-typer/`; an unrelated dep gets **nothing** (usage-gating).
- `vendomat doctor`: correct exit code + message on **missing / stale / up-to-date**.
- All of the above green through **`testee verify --mode quick`** (not bare pytest).

---

## Operating rules (READ — these are how this repo is driven)

### Verification → testee (never bare pytest/ruff)
```
devenv shell -- testee verify --mode quick     # ruff, ruff-format, ty, pytest → one report
devenv shell -- testee fix                     # auto-fix lint/format
```
`testee` is the `*man` verify interface; it's a dev dep here so it's already in the venv.

### Version control → gitman, run from gitman's devenv with `--repo`
`gitman` is **NOT on vendomat's PATH** (vendomat doesn't import repoman). Invoke it from gitman's
own devenv, targeting this repo, and silence zoxide noise:
```
cd /home/andrew/Documents/Projects/gitman && _ZO_DOCTOR=0 devenv shell -- \
    gitman --repo /home/andrew/Documents/Projects/vendomat <status|start|save|publish|...>
```
One lane for M2 (e.g. `gitman ... start m2-knowledge`). Flow: `start` → edit → `save -m` →
`publish` → `gh pr create` → review → merge.

### ⚠ After merging the PR — the reconcile dance (known gitman gap)
gitman has **no command** to advance local trunk to a forge-merged `origin/main` (filed:
`/home/andrew/Documents/Projects/gitman/.scratch/projects/07-forge-pr-trunk-reconcile/ISSUE.md`).
After `gh pr merge`, reconcile manually (raw git is the sanctioned exception here):
```
git push origin --delete <lane>; git branch -D <lane>
git fetch origin --prune
rm -rf .jj .gitman
git symbolic-ref HEAD refs/heads/main && git reset --hard origin/main
cd ../gitman && _ZO_DOCTOR=0 devenv shell -- gitman --repo <vendomat> init --colocate --trunk main
# then: gitman doctor → HEALTHY, status → CANONICAL · 0 lanes, local==origin
```
Before merging, **scope the lane**: ensure `__pycache__`/`.pyc` etc. are gitignored (they are now);
double-check the PR file list has no junk. Keep VC wiring (`gitman.toml`) on **trunk**, never in a
lane only.

### Other guardrails
- **No AI-authorship trailers/attributions** anywhere (commits, PRs, docs, comments).
- **Don't touch Face A** beyond the Face B wiring in `modules/devenv.nix`.
- Seed **only `typer`** in M2; prove the loop before scaling to more libs.

---

## Source material (cite when implementing)
- `docs/DESIGN.md` §7 (7.1 `vendor/` layout, 7.2 `vendor-sync`, 7.3 rollout, 7.5 staleness),
  §8 decisions 5–6.
- `docs/IMPLEMENTATION_PLAN.md` — M2 + the 6 resolved DESIGN issues.
- `.scratch/projects/01-face-b-knowledge/KICKOFF.md` — the master multi-milestone packet.
- `repoman/src/repoman/devman/{install,check,assets}.py` — the subsystem to mirror.
- `repoman/src/repoman/{checks,aggregate}.py` — `SelfCheck` / `worst_exit` (already copied into
  vendomat's `checks.py`; don't re-import).
- `repoman/tests/consumer-example/repoman.lock` — the lock shape (`package` + `source`; the
  `[managers.git-pyjutsu]` pseudo-entry) for the `repoman.lock` branch of `deps.py`.

## Open questions (surface during planning, don't block)
1. **Manifest pin source in M2** — `meta.toml` carries the pin the skill is written against; M2
   records it in `.vendor-source`, M4 uses it for staleness. Confirm the `meta.toml` key name now.
2. **`repoman.lock` granularity** — its entries are managers (`package = "<dist>"`), coarser than
   `uv.lock`'s full resolved set. Confirm normalization makes the intersection meaningful for it.
3. **`vendomat sync` invoked where in the consumer lifecycle** — task vs enterShell; must run
   **after** uv resolves deps (so `uv.lock` exists to read).

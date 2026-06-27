# KICKOFF — vendomat M3: Face B tooling (`vendor add <lib>` — agent-assisted draft)

> Build the **authoring** half of Face B: a `vendor add <lib>` command that **scaffolds and
> pre-drafts** a `vendor/libs/<lib>/` knowledge entry (`meta.toml` + `notes.md` + `SKILL.md`) for
> **human/agent curation** — never auto-published. M2 (knowledge install, usage-gated) is **done
> and merged**. This packet is M3 only.

You are starting a FRESH session in `/home/andrew/Documents/Projects/vendomat`.
Read this packet, then `docs/DESIGN.md` §7.5 + §9 (Face B) and `docs/IMPLEMENTATION_PLAN.md` M3,
then **propose a short step-by-step plan for approval before writing any code** (this project
plans before coding).

---

## Where this fits

vendomat is the **vendor layer** for repoman's `*man` family — two faces over one `vendor/` data
area. Face A (native wheels, M1) and **M0 bootstrap** are done. **M2 (Face B slice 1 — knowledge,
usage-gated) is merged to `main` @ `5847631`.** M3 is the **curation-time tooling** that *produces*
the entries M2 installs.

Rollout is a deliberate **1 → 3 → 2** (DESIGN's numbering): knowledge (M2, done) → shared
constraints (M4) → selective vendored source (deferred). In **milestone** numbering the order is
**M2 → M3 (this) → M4**: M3 is the drafting tool that feeds the curation loop M2 set up; M4 is the
`constraints.txt` + review-on-bump backbone that M3's `pin` metadata will hang on.

Master context (the "why"): `.scratch/projects/01-face-b-knowledge/KICKOFF.md`. The M2 packet next
to this one (`M2-KICKOFF.md`) is the template for *how this repo is driven* — same operating rules.

---

## Current state (verified post-M2 — do NOT re-derive)

**M2 merged to `main` @ `5847631`** (PR #4). These exist — **extend** them, don't recreate:

- `vendor/libs/typer/{meta.toml, notes.md, SKILL.md}` — the **one** seeded entry, and the golden
  shape M3 must generate a valid draft of. Study it: `meta.toml` has `[lib]` (`name`, `version`
  range, **`pin`** the skill is written against, `docs`) + `[curation]` (`why`, `rejected`);
  `SKILL.md` has devman frontmatter (`name: dep-typer`, `description` carrying the trigger text,
  optional `auto_trigger.keywords`).
- `src/vendomat/deps.py` — `read_deps(repo_root) -> set[str]` + `normalize()` (PEP 503). Pure.
- `src/vendomat/install.py` — `MANIFEST=".vendor-source"`, `LIB_PREFIX="dep-"`, `expected_libs`,
  `matched_libs`, `lib_pin(vendor_root, lib)` (reads `[lib].pin` from `meta.toml`),
  `install_knowledge(...)`. Pure functions over `Path`. **M3's output must be a valid input to
  `install_knowledge` and `lib_pin`** — that's the integration contract.
- `src/vendomat/checks.py` — `SelfCheck` (Pydantic), `self_check_exit`, `format_self_check`,
  `vendor_checks(...)` (warn-only drift).
- `src/vendomat/cli.py` — real `sync`/`doctor` (resolve `--vendor-root` → `VENDOMAT_VENDOR_ROOT`),
  helpers `_repo_root()`, `_skills_dir()`, `_vendor_root(flag)`. **`add(lib)` is the no-op stub to
  replace** (`@app.command()` named `add`; the devenv/script alias is `vendor-add`).
- `modules/devenv.nix` — `knowledge.{enable, skillsDir}` Face B wiring (CLI on PATH,
  `VENDOMAT_VENDOR_ROOT=${inputs.vendomat}/vendor`, opt-in `vendor-sync` script). **M3 likely needs
  NO change here** — `add` is a *maintainer* command run in vendomat's own repo, not consumer
  wiring (confirm during planning).
- `tests/{test_deps,test_install,test_checks,test_cli}.py` — pytest harness; verified via `testee`.

**Does NOT exist yet (the M3 gap):** `src/vendomat/add.py`, any **Pydantic models for the entry
formats** (`meta.toml` / SKILL.md frontmatter are currently written/read as raw text), the real
`add` command, and `tests/test_add.py`.

---

## The central design question (resolve in planning — don't assume)

**"Agent-assisted draft" must NOT mean vendomat embeds an LLM.** vendomat's runtime deps are only
`typer` + `pydantic` (stdlib `tomllib`); it has no model runtime and must not grow one. So decide
what "draft from the lib's docs/source/changelog" mechanically means. The **proposed** reading
(confirm or revise):

> `vendor add <lib>` **scaffolds** `vendor/libs/<lib>/`, **mechanically pre-fills** every field it
> can derive offline (installed `version` → `pin`; `docs` URL + one-line summary from the dist's
> metadata when the lib is introspectable), emits a **Pydantic-validated** frontmatter block, and
> leaves the prose sections (`notes.md` body, the SKILL.md how-to, `[curation].why/rejected`) as
> **clearly-marked TODO/`<!-- DRAFT -->` stubs**. The output is an *agent-curatable draft* — an
> agent (Claude Code / mypi-agent) or you fills the prose; the command itself stays offline and
> dependency-light. "Agent-assisted" = structured *for* an agent, not *calling* one.

This keeps M3 pure-core/wired-edges (like M2), fully testable offline, and honors §7.5's
"agent-assisted drafting + **human curation** — you approve."

---

## Verified constraint (grounds open question 2)

Metadata introspection is **environment-scoped**: `importlib.metadata` only sees dists installed in
the *same interpreter as the running vendomat CLI*. In vendomat's own devenv venv that set is
**typer/pydantic + their transitive deps — and not reliably even those** (probe found `typer`
discoverable but `click` not). So M3 **cannot assume the target lib is importable** and must
**degrade gracefully**: when metadata is unavailable, scaffold with `pin = "TODO"` / placeholder
`docs`/summary and a note recording *what could not be gathered*, rather than hard-failing. A
maintainer who wants richer auto-fill `uv add`s the lib first (or points at a source path — see
open Q2). Do not reach for the network in the pure core.

---

## Work items (target paths)

### `src/vendomat/models.py` — Pydantic models for the entry formats (new)
- `LibMeta` mirroring `meta.toml`: `[lib]` (`name: str`, `version: str`, `pin: str`, `docs: str`)
  + `[curation]` (`why: str`, `rejected: str`). Round-trips to/from TOML.
- `SkillFrontmatter`: `name: str` (must be `dep-<lib>`), `description: str` (the real trigger
  text), `auto_trigger: AutoTrigger | None` (`keywords: list[str]`). This is the "**Pydantic-
  validated frontmatter so drafts can't ship malformed**" requirement (DESIGN §9, plan M3).
- Keep models the single source of truth for the shapes; consider (optional, scope-permitting)
  having `doctor` warn on an entry whose frontmatter fails validation — high-value, low-cost.

### `src/vendomat/add.py` — the drafter (pure core)
- `gather(lib: str) -> DraftMaterial`: offline introspection via `importlib.metadata` (version,
  Summary, Project-URL/Home-page) with graceful "unavailable" fallbacks (see verified constraint).
  Pure over an injectable metadata-lookup so it's unit-testable **without** a real install.
- `render_meta / render_notes / render_skill(material) -> str`: produce the three files from the
  validated models + TODO-stubbed prose. `name` is always `dep-<lib>` (normalize via `deps.normalize`).
- `scaffold(vendor_root: Path, lib: str, material, *, force: bool=False) -> list[Path]`: write
  `vendor/libs/<lib>/{meta.toml,notes.md,SKILL.md}`. **No-clobber:** refuse if the entry already
  exists unless `force` (don't overwrite curated prose — open Q3). Return written paths.

### `src/vendomat/cli.py` — wire the real `add`
- Replace the stub: resolve `vendor_root` (reuse `_vendor_root`; `add` writes *into* the vendor
  tree, so default to the repo's local `vendor/` when run in vendomat's own repo — confirm the
  resolution order), call `gather` → `scaffold`, print what was written + a "now curate these
  TODOs" pointer. Honor the 0/1/2/3 contract (e.g. exit 1 when the entry already exists and
  `--force` was not given — a domain decision, not a crash).

### Tests — `tests/test_add.py` (+ `test_models.py` if models warrant their own)
- **Golden / shape:** generated `SKILL.md` frontmatter parses and validates against
  `SkillFrontmatter`; `meta.toml` validates against `LibMeta`; `name == dep-<lib>`.
- **Round-trip into M2:** a `vendor add`-produced entry is a valid input to `install_knowledge`
  (installs as `dep-<lib>/SKILL.md`) and `lib_pin` (reads its `pin`), and `vendor_checks` accepts
  it — i.e. M3 output feeds the M2 pipeline cleanly. Use an injected/fake metadata source so the
  test is offline and deterministic; **do not** target `typer` (already seeded) — use a fresh name.
- **Graceful degradation:** missing metadata → `pin`/`docs` become TODO placeholders, no crash.
- **No-clobber:** `add` on an existing entry without `--force` refuses (exit 1) and leaves files
  untouched; with `--force` it overwrites.

---

## Acceptance (what "done" means)

- `vendor add <lib>` scaffolds `vendor/libs/<lib>/` with all three files; frontmatter + meta
  **validate** (malformed drafts are impossible by construction).
- The produced entry **installs via M2** (`install_knowledge`) and is **accepted by `doctor`**.
- Offline + deterministic: drafting never hits the network; missing dist metadata degrades to
  clearly-marked TODOs rather than failing.
- No-clobber protects curated entries; `--force` is the explicit override.
- All green through **`testee verify --mode quick`** (not bare pytest).

---

## Operating rules (READ — how this repo is driven; identical to M2)

### Verification → testee (never bare pytest/ruff)
```
devenv shell -- testee verify --mode quick     # ruff, ruff-format, ty, pytest → one report
devenv shell -- testee fix                     # auto-fix lint/format
```

### Version control → gitman, from gitman's devenv with `--repo`
`gitman` is NOT on vendomat's PATH. Invoke it from gitman's own devenv, silencing zoxide noise:
```
cd /home/andrew/Documents/Projects/gitman && _ZO_DOCTOR=0 devenv shell -- \
    gitman --repo /home/andrew/Documents/Projects/vendomat <status|start|save|publish|...>
```
One lane for M3 (e.g. `gitman ... start m3-vendor-add`). Flow: `start` → edit → `save -m` →
`publish` → `gh pr create` → review → merge.

### ⚠ After merging the PR — the reconcile dance (known gitman gap)
gitman has no command to advance local trunk to a forge-merged `origin/main`. After `gh pr merge`,
reconcile manually (raw git is the sanctioned exception here). Lane = `m3-vendor-add`:
```
git push origin --delete <lane>; git branch -D <lane>
git fetch origin --prune
rm -rf .jj .gitman
git symbolic-ref HEAD refs/heads/main && git reset --hard origin/main
cd ../gitman && _ZO_DOCTOR=0 devenv shell -- gitman --repo <vendomat> init --colocate --trunk main
# then: gitman doctor → HEALTHY, status → CANONICAL · 0 lanes, local==origin
```
Before merging, scope the lane: `__pycache__`/`.pyc`/`.testee/` stay gitignored; check the PR file
list has no junk. Keep VC wiring (`gitman.toml`) on **trunk**, never a lane only. (Heads-up from
M2: never run `vendomat sync`/`add` through `devenv shell -- …` against a temp dir — devenv
overrides `DEVENV_ROOT` to *this* repo and you'll write into vendomat's own tree. Use
`env -u DEVENV_ROOT` or the `--vendor-root` flag for manual smoke tests.)

### Other guardrails
- **No AI-authorship trailers/attributions** anywhere (commits, PRs, docs, comments).
- **Don't touch Face A**; don't expand M2's install path beyond what M3's contract needs.
- **No LLM/agent runtime and no network in the core.** "Agent-assisted" means structured *for*
  an agent, not *calling* one — `add` must stay offline and deterministic, with no model/agent
  library (and nothing that reaches the network) pulled into the drafter. **Ordinary library deps
  are fine** where they make the code simpler or more reliable (e.g. a YAML/TOML parser): prefer
  small, well-established ones, add them deliberately, and keep typer + pydantic + stdlib as the
  lean default.
- This is the **tooling** slice — `constraints.txt` + review-on-bump staleness is **M4**, not here.

---

## Source material (cite when implementing)
- `vendor/libs/typer/{meta.toml,notes.md,SKILL.md}` — the golden target shape to generate.
- `docs/DESIGN.md` §7.5 (staleness defenses → "agent-assisted drafting + human curation"), §9
  Face B ("Build `vendor-add <lib>` … emit devman-style frontmatter").
- `docs/IMPLEMENTATION_PLAN.md` — **M3** (the `add.py` + `vendor add <lib>` spec, golden test).
- `src/vendomat/{install,deps,checks}.py` — the M2 patterns to extend + the integration contract.
- `repoman/src/repoman/devman/assets.py` — the devman frontmatter/skill-dir conventions to mirror.

## Open questions (surface during planning, don't block)
1. **Drafting mechanism** — confirm the "scaffold + mechanical pre-fill + agent curates the prose"
   reading above (vs. anything that would pull in a model/network dep). Settle exactly which fields
   are auto-filled vs. TODO-stubbed.
2. **Material source beyond installed metadata** — is an optional `--from-src <path>` (read a local
   checkout/sdist for a richer draft) in scope for M3, or deferred with rollout step 2 (vendored
   `src/`)? Default to **installed-metadata-only**, `--from-src` deferred unless cheap.
3. **No-clobber policy** — refuse-unless-`--force` (proposed) vs. fill-only-missing-files. Pick one.
4. **Validation reach** — introduce the Pydantic models in M3 and use them in `add`; optionally
   have `doctor` warn on an existing entry with invalid frontmatter. In scope, or M3-add-only?
5. **`vendor_root` resolution for `add`** — `add` authors *into* the vendor tree (vendomat's own
   repo), unlike `sync` which reads a store path. Confirm the default (local `./vendor`) and how
   `--vendor-root`/`VENDOMAT_VENDOR_ROOT` interact for the authoring case.

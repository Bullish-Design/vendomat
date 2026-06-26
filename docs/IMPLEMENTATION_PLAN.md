# vendomat implementation plan — the vendor layer (artifacts + knowledge) for the `*man` family

## Context

`vendomat` is the **vendor layer** for repoman's `*man` family. The design
(`docs/DESIGN.md`, scope **C — narrow now, broad-ready**) is written and verified against the
real sibling repos; this plan turns it into a sequenced build. vendomat has two faces sharing
one `vendor/` data area:

- **Face A — artifacts:** build native deps (pyjutsu = Rust/maturin/PyO3) once into
  content-addressed wheels, so a consuming repo installs a prebuilt wheel instead of running
  `cargo` per repo. This closes the *fleet path* gap repoman names verbatim
  (`repoman/CONCEPT.md` §8: "a fleet path (published pyjutsu wheel + `git+…` sources) so
  `path:` checkouts aren't required").
- **Face B — knowledge:** per-dependency notes + agent `SKILL.md`s installed into a repo,
  gated on the deps it actually uses ("devman, but per dependency").

**Current state (verified):** Face A's *Nix half* already works — `nix build .#wheelhouse`
builds the cp313-abi3 pyjutsu wheel into the store; vendomat's module sets `UV_FIND_LINKS` +
`UV_NO_BUILD_PACKAGE`; gitman installs it with zero compile. What does **not** exist yet: the
`wheel:` source kind in `repoman.lock`/`repoman-sync.sh` (so repoman-sync still
editable-compiles the `git-pyjutsu` entry — the README "proven" status is the UV_FIND_LINKS
path, not the lock path), the Rust-toolchain opt-out, and **all of Face B** (vendomat ships
zero Python today — no `devenv.nix`, no `src/`, no tests, no `vendor/` data).

**Settled this session:** (1) `vendor/` lives as a **subdir of the vendomat repo** (one repo =
one vendor layer); (2) Face B is a **Python Typer package** mirroring the `*man` CLI contract;
(3) Rust provisioning becomes an **explicit opt-out option** (`repoman.nativeBuild`, default
`false`) in gitman.nix.

---

## DESIGN.md issues to resolve before/while building (flagged per brief item 6)

1. **`wheel:` is inert without vendomat's module active — make the coupling explicit.**
   `repoman-sync.sh` runs one `uv pip install` for all targets (line 62). A `wheel:pyjutsu>=0.8`
   source resolves to a bare `pyjutsu>=0.8` requirement that **only** finds the personal wheel
   because vendomat's module exported `UV_FIND_LINKS`/`UV_NO_BUILD_PACKAGE`. If a repo has a
   `wheel:` source but hasn't imported+enabled vendomat, uv looks on PyPI (no personal pyjutsu →
   confusing failure). DESIGN implies this but doesn't guard it. **Resolution:** repoman-sync
   emits a clear error if any resolved target is a `wheel:` source while `UV_FIND_LINKS` is
   unset; `vendomat doctor` also checks it.

2. **Drift surfacing belongs in `vendomat doctor`, not `repoman doctor`.** DESIGN §9 says
   review-on-bump is "surfaced via the `.vendor-source` manifest in `repoman doctor`." But by
   decision 5 / §1.1 boundaries vendomat is **not** a repoman manager and does not touch the
   router; `repoman doctor` only aggregates its own managers + devman. **Resolution:** vendomat
   ships its own `vendomat doctor` (the `*man` 0/1/2/3 contract) that reads `.vendor-source`;
   optional later repoman integration is out of scope for now.

3. **vendomat CLI delivery to a consumer is unspecified.** devman rides inside the `repoman`
   package already in the venv; vendomat is not in `repoman.lock`. **Resolution:** vendomat's
   devenv module provides its CLI as a **Nix-built package on `PATH`** (the
   zelligate-provisions-zellij / alliman-provisions-allium pattern), not via the consumer venv —
   no `repoman.lock` entry, no venv coupling.

4. **`auto_trigger.keywords` is a devman convention, not guaranteed-native discovery.** Claude
   Code discovers skills by `name` + `description` frontmatter; treat `auto_trigger.keywords` as
   devman-compatible metadata, and make `description` carry the real trigger text. (No blocker.)

5. **`mkArtifact` should stay a one-builder dispatcher now (don't over-build §5's table).** The
   seam is a single attrset lookup keyed on `builder`; only `maturinWheel` is wired. The other
   three rows stay as comments/docs until evidence demands them.

6. **`source` pin is duplicated** between the lock (`wheel:pyjutsu>=0.8`) and the consumer's own
   `pyproject` dependency. Acceptable (matches the existing `path:`/`git+` duplication), but the
   plan keeps the wheel floor (`>=0.8`) defined in exactly one documented place per repo.

---

## Milestone M0 — bootstrap vendomat as a `*man`-shaped Python project (Face B prerequisite)

vendomat is Nix-only today; Face B needs a tested CLI. This milestone adds the scaffolding and
nothing user-facing.

**Files (new):**
- `devenv.nix` — vendomat's own dev shell (Python 3.13, `uv`, ruff, pytest), matching the family
  stack. All in-repo commands run via `devenv shell -- …`.
- `pyproject.toml` — package `vendomat`, console script `vendomat`, deps: `typer`, `pydantic`,
  `tomli`/stdlib `tomllib`. Mirror an existing `*man` `pyproject` (e.g. gitman/testee).
- `src/vendomat/cli.py` — thin Typer app: `sync`, `add`, `doctor` (stubs now), Pydantic-normalized
  output, `0/1/2/3` exit-code contract reusing the shape of `repoman`'s `checks.SelfCheck` /
  `aggregate.worst_exit` (copy the small contract, don't import repoman).
- `tests/` — pytest harness + one smoke test (`vendomat --help`, exit-code contract).

**Verification:** `devenv shell -- pytest` green; `devenv shell -- vendomat doctor` returns the
right exit code on an empty repo.

---

## Milestone M1 — Face A: the `wheel:` source kind end-to-end (the first vertical slice)

This is the recommended **first slice that proves end-to-end value**: pyjutsu wheel → gitman
consumer installs it from `repoman.lock` with **zero cargo and no Rust toolchain**, mirroring the
README's proven pyjutsu→gitman pair but completing the *lock* half.

### M1a — generalize the builder (vendomat repo)
- New `lib/mkArtifact.nix`: `mkArtifact { pname; src; version?; builder ? "maturinWheel"; }`
  dispatching via a `builders = { maturinWheel = import ./mkMaturinWheel.nix …; }` attrset. The
  maturin path is today's `mkMaturinWheel.nix` **unchanged**.
- `flake.nix`: expose `lib.mkArtifact` (keep `mkMaturinWheel` as a back-compat alias); build the
  wheelhouse through `mkArtifact { builder = "maturinWheel"; }`. No behavior change to outputs.

### M1b — the resolver + Rust opt-out (small PR to the **repoman** repo)
The script lives in repoman, so this lands as a focused repoman PR (coordinated, not in vendomat):
- `modules/scripts/repoman-sync.sh` — add one branch to the embedded `target()`:
  ```python
  if source.startswith("wheel:"):
      return source[len("wheel:"):]   # bare requirement, e.g. "pyjutsu>=0.8"
  ```
  Build the `wheel:` set as an **open vocabulary** (seam §4.1): a small prefix→handler map, not a
  pyjutsu special-case. Add the guard from issue #1: if any target came from a `wheel:` source and
  `UV_FIND_LINKS` is unset, fail with a clear "import + enable vendomat's module" message.
- `modules/managers/gitman.nix` — add `options.repoman.nativeBuild` (bool, default `false`); gate
  `pkgs.maturin` + `languages.rust.enable` on `enabled && cfg.nativeBuild`. Consumers using
  `wheel:` leave it `false` (zero Rust); pyjutsu's own repo and any wheel-less consumer set
  `nativeBuild = true`.
- `repoman.lock` header + `tests/consumer-example/repoman.lock` — document the new third `source`
  form and flip `[managers.git-pyjutsu]` to `source = "wheel:pyjutsu>=0.8"`.

### M1c — consumer module polish (vendomat repo)
- `modules/devenv.nix` is already correct for the wheel path; confirm `vendor.self`/`vendoredLibs`
  filtering and that `UV_NO_BUILD_PACKAGE` covers every `wheel:`-sourced lib. No structural change
  expected; add a `vendor:doctor`-style task echo if useful.

**Verification (M1):**
- vendomat: `nix build .#wheelhouse` (cache hit) + `nix eval` the wheelhouse path is stable.
- repoman PR: a unit test asserting `target()` maps `wheel:pyjutsu>=0.8` → `pyjutsu>=0.8`; a Nix
  eval test that `gitman.nix` contributes **no** `languages.rust` when `nativeBuild = false`; the
  unset-`UV_FIND_LINKS` guard test.
- Integration in `tests/consumer-example`: enable vendomat's module, set `nativeBuild = false`,
  run `repoman-sync`, assert no `rustc`/`cargo` ran (no `target/`, toolchain absent), `python -c
  "import pyjutsu"` works, and gitman's suite passes.

---

## Milestone M2 — Face B slice 1: knowledge, usage-gated (`vendor-sync` + first dep skill)

The cheap, certain-value slice from the 1→3→2 rollout. No byte-vendoring.

**`vendor/` skeleton (new, in vendomat repo):**
```
vendor/
  libs/<lib>/{meta.toml, notes.md, SKILL.md}     # SKILL.md uses devman frontmatter (name/description[/auto_trigger.keywords])
```
Seed exactly one real lib end-to-end (e.g. `pydantic` or `typer`) to validate the curation loop.

**`src/vendomat/`:**
- `deps.py` — the **dep-reader**: parse the consuming repo's dependency set from `uv.lock` →
  `pyproject.toml` → `repoman.lock` (first that exists wins, in that precedence), normalize names,
  return a set. Pure function over file contents → fully unit-testable.
- `install.py` — mirror `repoman/src/repoman/devman/install.py`: intersect deps with `vendor/libs/`,
  copy each match to `<skills_dir>/dep-<lib>/SKILL.md` (**flat sibling**, not nested `deps/<lib>/`),
  write `.vendor-source` drift manifest (vendomat version + installed `dep-<lib>` list + the pin each
  skill is tied to). Reuse devman's `expected_*`/manifest shape.
- `cli.py` — wire `vendomat sync` (= install gated on usage) and `vendomat doctor` (read
  `.vendor-source`; flag missing/stale → warn-only first, like devman's `check.py`).

**Consumer wiring:** vendomat's `modules/devenv.nix` gains a `vendor-sync` script (runs the
Nix-provided `vendomat` CLI, issue #3) + an opt-in enterShell/task hook, run **after** deps are
resolved (mirror how repoman-sync runs install before `install-skills`). Add `knowledge.enable` /
`knowledge.skillsDir` options (default `.claude/skills`, matching `REPOMAN_SKILLS_DIR`).

**Verification (M2):**
- `deps.py`: pytest with fixtures for each of uv.lock / pyproject.toml / repoman.lock incl.
  precedence + name normalization.
- `install.py`: installs only intersecting `dep-<lib>/SKILL.md`; writes `.vendor-source`; idempotent
  re-run. Integration fixture: a repo depending on the seeded lib gets exactly `dep-<lib>/`, an
  unrelated dep gets nothing (usage-gating).
- `vendomat doctor`: exit code + message on missing/stale/up-to-date.

---

## Milestone M3 — Face B slice (tooling): `vendor-add <lib>` (agent-assisted draft)

- `src/vendomat/add.py` + `vendomat add <lib>`: scaffold `vendor/libs/<lib>/` and draft
  `notes.md` + `SKILL.md` (devman-style frontmatter) from the lib's docs/source/changelog, for
  **human curation** (never auto-published). Emit a Pydantic-validated frontmatter block so drafts
  can't ship malformed.
- **Verification:** golden test on generated frontmatter shape/required keys; `vendor-add` on a
  known lib produces a file that `vendor-sync` can install and `doctor` accepts.

---

## Milestone M4 — Face B slice 2: shared `constraints.txt` + review-on-bump

The "fast follow" backbone; adopt deliberately (introduces real cross-repo coupling).
- `vendor/constraints.txt` — unified external pins the personal libs reference.
- Tie every `dep-<lib>` skill to its pin in `.vendor-source`; `vendomat doctor` flags a skill
  **stale** when the lib's resolved version diverges from the pin its skill was written against
  (review-on-bump). Surface in `vendomat doctor` (issue #2), not repoman doctor.
- **Verification:** bump a pin in a fixture → `doctor` flags the matching skill stale; unchanged
  pins stay green.

*(Rollout step 2 in DESIGN's numbering — selective vendored `src/` per library — is explicitly
deferred; it is the lowest-value, highest-upkeep slice and gated on M2–M4 proving out.)*

---

## Sequencing & dependencies

```
M1a (mkArtifact) ─┐
                  ├─► M1 first vertical slice (PROVE END-TO-END VALUE)  ──┐
M1b (repoman PR) ─┘   pyjutsu wheel → gitman zero-cargo via wheel: lock   │
                                                                          ▼
M0 (bootstrap) ─► M2 (knowledge + vendor-sync) ─► M3 (vendor-add) ─► M4 (constraints + review-on-bump)
```
- **M1 is independent of M0/Face B** (pure Nix + a repoman bash PR) and delivers the headline
  win first → do it first.
- **M0 gates all of Face B.** M2 depends on M0; M3/M4 depend on M2.
- **M1b is the only cross-repo coordination point** — a small, reviewable repoman PR. Land it with
  the consumer-example flip so the PR is self-proving.

---

## Cross-cutting open risks

- **abi3 / cp313 interpreter floor.** Wheels are `cp313-abi3`; a consumer off that interpreter
  floor gets "no compatible wheel," which `UV_NO_BUILD_PACKAGE` (correctly) turns into a hard
  error. Keep consumers pinned to the matching Python; document the floor next to `vendor.libs`.
- **repoman PR coordination (M1b).** The `wheel:` branch is inert/dangerous without vendomat's
  module (issue #1) — ship the guard + doctor check in the same change set, and land the
  consumer-example flip atomically with the resolver branch.
- **constraints.txt coupling (M4).** A breaking external bump touches all consumers at once; adopt
  step 2 only after knowledge (M2) proves useful, and keep the bump visible via review-on-bump.
- **Skill staleness.** A wrong skill is worse than none — defenses are usage-gating (M2),
  pin-tied review-on-bump (M4), and human-curated `vendor-add` drafts (M3), in that order of
  leverage.
- **vendomat CLI delivery (issue #3).** Provide the CLI as a Nix package on PATH; verify it
  resolves in a consumer shell that does **not** have vendomat in its venv.

---

## What is explicitly NOT built now (broad-ready seams kept open)

- No `vendomat.toml` manifest, no registry — `repoman.lock` is the manifest (decisions 1–2).
- No fleet/dev-root scan, clone-on-miss, or compose graph. Two cheap seams only: the **open
  `source`-kind vocabulary** (M1b) and **`VENDOMAT_DEV_ROOT`** indirection (already the flake's
  documented override convention; formalize the env lookup when first needed).
- No vendored library `src/` (DESIGN rollout step 2), no extra builders beyond `maturinWheel`.

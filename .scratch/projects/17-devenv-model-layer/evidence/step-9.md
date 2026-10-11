# Step 9 record: the `nix` output language in Templateer

**Date:** 2026-10-11. **Status:** Observed. Landed on `templateer_v2` `main` at `d3304db4`, pushed.
No release tag and no version bump yet.
**Raw report:** `~/.local/state/devenv-py/step-9/REPORT.md`.

## Changes

Workspace: `~/Documents/Projects/gitman-workspaces/tpl-nix-language`. Base: `main` at `70f13f57`.

| Order | jj change | Commit | Subject |
| --- | --- | --- | --- |
| 1 | `nxpvmkrwnpnw` | `03adf25a6e1a` | fix: read the expected version from pyproject.toml in the version test |
| 2 | `ukqwnmnnkqts` | `d3304db4bbcf` | feat: add the nix output language |

Nix: `nix-instantiate (Nix) 2.34.7`.

## Version test root cause

`tests/test_cli.py::TestHelp::test_version_flag` held the literal `0.4.0`. The release moved to
`0.4.1`. The package was right: `__version__` and `click.version_option()` read `importlib.metadata`,
which reads `pyproject.toml`. The fix reads the version from `pyproject.toml` in the test. Tag
`v0.4.2` is on the `v6-flake` branch and is not an ancestor of `main`.

## Commands and results

Run in the devenv shell of the workspace, after both changes.

| Command | Expected | Actual |
| --- | --- | --- |
| `pytest -q` | all pass | `659 passed, 9 skipped` in 7.96 s. The 9 skips are API-key skips. |
| `ruff check src/ tests/ templates/` | clean | `All checks passed!` |
| `ty check src/` | clean | `All checks passed!` |
| `tests/test_nix_language.py` | all pass | 213 tests pass. 58 carry the `needs_nix` marker. |
| same file without `nix-instantiate` on `PATH` | Nix tests skip | 155 passed, 58 skipped |
| `main` before the work | (baseline) | `1 failed, 444 passed, 9 skipped` |

## Design choices

- `nix` is a `ParsedLanguage`. It is not in `STRUCTURED_LANGUAGES` or `_QUOTED_STRING_LANGUAGES`.
  The finalizer passes strings unchanged, writes `true` and `false`, and raises on `None`.
- `escape_nix_string` follows the guide table. U+0000 raises `EscapeError`. A lone surrogate also
  raises, as in `escape_string`.
- The filters `nix` and `nix_attr` exist for `nix` templates only. They live in
  `src/templateer/nix_render.py`. `nix_attr` takes a string, or a list of strings joined with dots.
  It writes a bare identifier when valid, and a quoted name for other names and for keywords.
- Tagged forms: `$pkg` (with `$output`), `$path`, `$nix`, `$priority`. A tagged object with extra
  keys raises. `$path` allows safe relative paths only. `$nix` is raw Nix. The caller owns it.
- Parse validator: `nix-instantiate --parse -` with the artifact on standard input. A missing
  program is an error. A NUL byte in the artifact is an error.
- Lint: the last filter of every `{{ }}` site must be `nix` or `nix_attr`. `indent` may follow. A
  loose operator (`~`, `+`, `if`, `and`) outside the filter is a finding. Comments and
  `{% raw %}` blocks are ignored.
- Audit: `templateer check` renders each fixture and parses it with Nix. No injection probe runs.
  With no fixture it reports "nothing audited".
- Escape test: one test covers U+0001 to U+011F, U+2028, U+2029, U+FEFF, one astral character, and
  `${x}`, in one `nix-instantiate --eval --strict --json -` call. The `needs_nix` marker skips the
  Nix tests when `nix-instantiate` is missing.
- `tests/test_audit.py` used `nix` as an example of an unknown language. It now uses `nixx` and
  `Nix`.

## Corrections to the guide (observed)

1. `-` reads standard input on Nix 2.34.7 for `--parse` and for `--eval --strict --json`. No
   temporary file is needed. The guide claim holds.
2. `--parse` also binds variables. A fragment such as `pkgs.git` fails with "undefined variable".
   The module must start with `{ pkgs, lib, ... }:`. The validator tests wrap fragments in that head.
3. Atom parenthesis rules. A list element or function argument must be one atom.
   - `[ -1 ]` is a syntax error. The filter writes `[ (-1) ]`.
   - `[ lib.mkForce 1 ]` is two elements. The filter writes `[ (lib.mkForce 1) ]`.
   - `lib.mkDefault (lib.mkForce 1)` and `lib.mkOverride (-5) (-1)` need parentheses too.
   - At the top level and as an attribute value, the filter writes no parentheses:
     `lib.mkDefault 1`.
4. Float exponent form. `1e20` and `1e+20` are not Nix floats. Nix needs a decimal point. The filter
   writes `1.0e+20`. `1.5e-07` is already valid.
5. Integer range. Nix cannot write `-9223372036854775808` as a literal. `9223372036854775808` is an
   invalid integer. The filter accepts -(2^63-1) to 2^63-1 and raises outside it.

## Open items

- The guide asks for a release tag. None exists. The `v0.4.2` tag that Step 1 pins is on
  `v6-flake`. The harness cannot use the `nix` language until a tag points at `d3304db4` or a later
  commit on `main`. The owner decides the tag and the version.
- The harness pin of `templateer` must change when that tag exists.

## Gate GM6

The suite passes with the `nix` language. The tag part of the gate is open.

## Addendum, 2026-10-11: later state of the Templateer pin

1. `devenv-py` first pinned Templateer at `d3304db4bbcf` (Step 10, `74826b8d99b9`).
2. RT7 on `services.postgres` then showed `mismatch` cases: a float such as `0.0` came back as the
   integer `0`. Observation: the report `pg-after-s1` shows 22 mismatches of 554 cases; `pg-after-s2`
   shows 17 of 515. Cause (orchestrator, Templateer commit `ac02b48c`): MiniJinja 2.22 turns an
   integral float into an integer when a template reads a scalar. The `nix` templates now tag
   integral floats.
3. Templateer `main` is at `ac02b48c`. `devenv-py` pins it by revision `ac02b48c015d`
   (`8c24fb61f028`: build: pin templateer to ac02b48c015d, the integral-float fix). The tag `v0.4.2`
   is still on the `v6-flake` branch and lacks the `nix` language. No tag exists on `main`.
4. After the pin, RT7 on `services.postgres` passes 554 of 554 (seed 1) and 515 of 515 (seed 2).

The GM6 tag item stays open. The harness pins a revision, not a tag. The owner decides the tag and
the version.

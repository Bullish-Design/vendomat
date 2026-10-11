# Step 16 record: the agent skills

**Date:** 2026-10-11. **Status:** Closed by [step-16-final.md](./step-16-final.md): GM10 PASS. The text below is the state at
`0dd939d802d2`. The skills existed, the trial was IN PROGRESS, and no trial result existed.

## Inputs

| Item | Value |
| --- | --- |
| Commit | `028e7f774899`: docs: add the three Step 16 agent skills (harvest, author, roundtrip). It also edits `AGENTS.md` of `devenv-py`. |
| Files | `skills/devenv-py-harvest/SKILL.md` (83 lines), `skills/devenv-py-author/SKILL.md` (85 lines), `skills/devenv-py-roundtrip/SKILL.md` (78 lines) |
| Link | Devman links each skill into `.agents/skills/<name>` on a machine. Observation: the links on this host are symlinks to `~/Documents/Projects/devenv-py/skills/<name>`. Git ignores `.agents/`. |

The guide proposed `.agents/skills/<name>/SKILL.md` as the source. The source is `skills/<name>/SKILL.md`
(tracked). The Devman link plane supplies `.agents/skills/`. Edit the source only.

## What each skill does

| Skill | Input | Commands | Done when |
| --- | --- | --- | --- |
| `devenv-py-harvest` | a source: `devenv-examples`, `devenv-tests`, or `fleet` | `python -m devenv_py.corpus harvest <source>`, then `evaluate <source> --summary <file>` (also `all` and `bench`) | every fixture has a class; every `batch` and `alone` fixture has a truth that two runs reproduce byte for byte; every `fails` entry has a reason |
| `devenv-py-author` | a subtree | `dpy gen`, `dpy schema`, `dpy rt --subtree <s> --checks RT1,...,RT8 --seed 1 --run-id <id>`, `dpy report <id>`; write `narrowed/<subtree>.py` | the GM9 thresholds hold for the subtree under seeds 1 and 2 |
| `devenv-py-roundtrip` | a report run id | `dpy report <id> [--json]`; read `results.jsonl`; fix one failure; rerun with `--checks` and `--seed` | the failing case passes and no other case fails |

The author skill reads the devenv module source at `devenv_rev` of `pins/<pin-id>/pin.toml` and lists
every assertion, `apply` function, package use, guarded `throw`, and cross-option `mkDefault`, with
line numbers. It writes cross-field rules as `model_validator(mode="after")`, gated on `enable` when
the module sets its config under `mkIf cfg.enable`. It writes package and string lists as
`CHOICES`, and it requires a probe for each entry.

The roundtrip skill holds a table that maps each failure class to the fix place:

| Class | Fix place |
| --- | --- |
| RT7 `type-error` | narrow the model |
| RT7 `assertion` | add a validator |
| RT7 `mismatch` | report as a harness issue; do not narrow |
| RT7 `other-error` | add a `CHOICES` list |
| RT8 `accepted` | loosen the model or the generator; never tighten |
| RT8 `rejected-assertion`, `rejected-unknown-option`, `rejected-other` | read the log and classify first |
| RT1 | fix the model |
| RT2 to RT6 | fix the generator or reader with a unit test; a normalizer or compare cause is a report |

## Rules in all three skills (MDL-005)

1. Do not edit `nix/`, `normalize.py`, `compare.py`, or `driver.py`. Report a suspected harness
   error.
2. Do not change a golden fixture or a truth file to make a check pass.
3. Never run a bare `uv`. Use `env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV devenv shell -- uv ...`.
   This rule comes from the incident in [step-2-3.md](./step-2-3.md).
4. Open work with `gitman work <name>`. Use jj. Never run raw `git`.
5. Verify with `testee verify --full`. Do not call pytest, ruff, or ty directly.
6. Write a record under `~/.local/state/devenv-py/<skill>/<subtree or source>/<run-id>.md`. Label each
   line OBSERVATION or INFERENCE.

## Known gaps in the skills (inference)

- The skills name the `pname` comparison as a known harness gap. The package identity work in
  progress changes it. The skills need an update when that work lands.
- The skills have not run on a real task. Their commands match `cli.py` and `corpus.py` at
  `0dd939d802d2` by reading, not by execution.

## The trial (IN PROGRESS)

Per the guide: give an agent the author skill for `services.redis`, with no help, and record the
run. Status: not finished. This record has no result, no change list, and no harness change
request for it. The trial starts after the final GM9 gate run.

## Gate GM10

IN PROGRESS. Not met. See [GATES.md](./GATES.md).

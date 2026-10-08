# Evidence and result format

Use one result file per spike, named `results/PV-<number>.md`. Keep raw output outside the
repository under `~/.local/state/vendomat/v5/prelim-verification/<date>/`.

Do not create a result file that says “pass” before the stated fixture runs. Record a blocked
fixture as blocked, with the command and failure that establish the blocker.

## Required fields

```markdown
# PV-XX — short title

**Date and time:** YYYY-MM-DD HH:MM TZ
**Host or virtual machine:** name and system
**State:** passed | failed | blocked
**Related requirements:** exact IDs
**Tools:** exact versions and relevant configuration pins
**Fixture:** source paths, revision or digest, and any image identity
**Expected:** result stated before the run

## Commands

Exact commands, in order. Mask only secrets. State each masked value's role.

## Observations

Actual exit status and the decisive output for each command. Link raw log paths.
Record negative observations, including absent cache paths and unexpected lock nodes.

## Inference

State what the observations support. State what they do not prove.

## Decision

Keep | revise | supersede | block. Name affected documents and requirement IDs.

## Follow-up

Name the next command or owner choice, if any.
```

## Evidence rules

- Capture `nix --version`, `devenv version`, Attic versions, and the relevant flake pins where
  a result depends on them. Record a command failure if a tool is unavailable.
- Save command output and exit status. A truncated terminal view is not a raw log.
- Separate a native tool's documented behavior from a fixture result on the pinned version.
- For source portability, test a second path or a genuinely cold store. A warm local store can
  hide a missing source path.
- For cache substitution, record the source store, target store, `--max-jobs 0`, the store
  path, the network route, and the NAR hash. A path already in the target store is not cold.
- For a disk check, record the stable hardware ID, model, serial, size, mount ancestry, and
  signature output. Never put a destructive command in the result file as a test instruction.
- For a claimed conflict, record both definitions and the evaluated option type.
- For a claimed build result, record the derivation, closure path, command, and exit status.
- Keep secrets out of tracked files, raw logs, store paths, and terminal output.

## Readiness summary

Create `RESULTS.md` after the spikes. Give each spike one row with its state and result link.
List blockers separately. A blocked P0 spike means the project is not ready for the dependent
implementation step. A passed small fixture does not replace a later machine acceptance test.

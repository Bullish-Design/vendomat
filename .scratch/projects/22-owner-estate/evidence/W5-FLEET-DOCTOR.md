# W5: a read-only fleet doctor prototype and its baseline — 2026-10-13

<!-- Provenance: a subagent built and ran the prototype on 2026-10-13. Files:
~/.local/state/vendomat/p22/w5-fleet-doctor/ (doctor.py, baseline.json, baseline.txt,
baseline-d09-cleanpath.txt, REPORT.md). The orchestrator wrote this record from the subagent's report
and did not rerun the prototype. -->

This record backs `ESTATE-040` to `ESTATE-043` and open item OI-03.

## Inputs

- `doctor.py`: one file, Python standard library, run with `python3 -I`. Text output by default,
  `--json`, and `-v`. Exit codes follow mancore: 0 clean, 1 findings, 2 could not check.
- Scope: 70 repositories under `~/Documents/Projects`. Skipped: forgelab (archived set), 5
  directories without version control, 7 hidden directories, 7 plain files.
- Run time against the real fleet: 0.25 s. A built-in `--selftest` passes 32 of 32 fixture cases.
- A check that cannot read its input reports "unchecked" and exit 2, never clean. The selftest
  proves this for unreadable input, zero repositories, and a crash.

## Checks and baseline

| ID | Check | Severity | Checked | Findings (repositories) |
| --- | --- | --- | --- | --- |
| D01 | Personal-tool input or import in `devenv.yaml` (mancore and Vendomat reported as information only) | fail | 59 | 46 (22) |
| D02 | Personal-tool option in `devenv.nix` (`repoman.`, `testee.`, `devman = {`) | fail | 59 | 23 (23) |
| D03 | Retired file: `gitman.toml`, `.repoman/project.toml`, template answers with a tool `*_ref`, `.copier-answers*` | fail | 70 | 23 (23) |
| D04 | Real file where the overlay should link (`.agents`, `.claude/skills`, `devenv.local.nix`, `.envrc`) | fail | 60 | 0 |
| D05 | Overlay import that devenv cannot track (W9) | fail | 60 | 60 (60) |
| D06 | Standard tasks missing (R10) | fail | 70 | 70 (70) |
| D07 | `.devman/project.toml` missing, or schema not 1 | warn | 70 | 9 (9) |
| D08 | Two nodes for one family tool in nix-meta's committed `flake.lock` | fail | nix-meta | 1 |
| D09 | A personal tool on `PATH` from two sources; copies in repository virtual environments | fail; venv warn | fleet | 1 fail, 8 warn |
| D10 | Overlay directory with no repository; repository with no overlay directory | warn | 84 | 24 |

## Findings

- **D01, D02: Testee is the remaining pin.** 22 repositories hold the `testee` input, the
  `testee/nix/testee.nix` import, and `testee.` options: agentman, argentic, devenv-py, eventic,
  flora, flora-core, flora-qc, fornix, inferference, linkman, llgym, loci-core, mancore, poddantic,
  pyllij, pytuin, repoman, scopeman, shellij, talkee, templateer_v2, vendomat. The testee repository
  is the 23rd D02 finding.
- **The `repoman` input is gone from every repository except repoman's own.** The inventory earlier
  the same day found 18. Other sessions removed them during the day (open item OI-13).
- **D03:** 18 repositories keep `.repoman/project.toml`; 14 keep `.copyroom-local.json` answers with
  `testee_ref`; talkee keeps `.copier-answers.yml`; 4 keep `gitman.toml` (nix-meta-channel4,
  terminal-state, testee, webdantic). The inventory earlier the same day found 62 `gitman.toml`.
- **D04 is clean.** No repository holds a real `.agents`, `.claude/skills`, `devenv.local.nix`, or
  `.envrc` where the overlay should link.
- **D05:** all 60 overlay `devenv.local.nix` files import
  `/run/current-system/sw/share/devman/link-module.nix`, which devenv cannot track. A hand check of
  devman's cache found a row for the overlay file and none for the module, as W9 found. This is open
  item OI-08.
- **D06:** no repository defines the five standard tasks. 11 have no `devenv.nix` (open item OI-09).
- **D08:** nix-meta's committed lock holds `gitman` v0.13.1 and `gitman_2` v0.9.1.
- **D09:** the one fail came from running inside devman's devenv shell (`devman` from its store
  path and from `/run/current-system/sw/bin`). A clean `PATH` gives no fail. The 8 virtual-environment
  copies appear in both runs, for example in loci-core, testee, devman, and gitman.
- **D10:** 14 overlay directories have no repository; 10 repositories have no overlay directory.
- **D07:** 9 repositories have no `.devman/project.toml`; none has a schema other than 1.
- 34 repositories pass D01 to D04 and D07. No repository passes D05 or D06.
- nixvim's `.devenv/nix-eval-cache.db` is a text file with jj conflict markers, not a database. D05
  reports its symlink failure and an information line, so it does not pass falsely.

## A side effect, found and fixed

The first run opened live cache databases with SQLite `mode=ro`. The databases use write-ahead
logging, so the open created empty `-wal` and `-shm` files in 9 repositories and changed the `-shm`
modification time in others. The subagent removed the 18 files it had created, after it checked
their creation time, zero size, and that no process held them. The changed `-shm` times cannot be
restored; they are derived data. `doctor.py` now copies the database and its `-wal` file to a scratch
directory and opens the copy. A rerun left every database file unchanged. `immutable=1` was rejected,
because it misses rows still in the `-wal` file. **W9's `doctor_check.py` has the same defect.**

## Spot checks

Ten findings across D01 to D10 were checked by hand. All were true. The only false finding was the
shell-dependent D09 fail.

## Heuristic limits

- D01 reads `devenv.yaml` with a minimal reader; unsupported syntax makes the repository unchecked.
- D02 and D06 match text in comment-stripped `devenv.nix`; D06 follows `./*.nix` imports one level.
- D03 matches a `*_ref` answer for all eight personal tools.
- D04 counts a path as linked when any component is a symlink; it does not check the target.
- D05 reads only plain-path `imports` and cannot tell whether a cache is current.
- D08 counts nodes by name and URL, not by reachability from `root`.
- D09 depends on the caller's `PATH`.

## Unproved

The D05 "no cache row" branch on real data (every repository fails the symlink branch first); cache
currency; that `base:check` chains to the `check:*` tasks; the "tool refuses an unknown schema" half
of `ESTATE-020`; integration as `devman doctor --fleet`; `devenv.local.yaml`, `vendomat.toml`, and
`pyproject.toml`.

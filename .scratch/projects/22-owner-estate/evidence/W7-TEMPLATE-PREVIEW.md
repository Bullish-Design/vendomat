# W7: template-py and template-nix previews without tool pins — 2026-10-15

<!-- Provenance: a subagent ran the commands on 2026-10-15. Raw logs and scripts:
~/.local/state/vendomat/p22/w7/ (py-cand-render.log, nix-cand-render.log, pin-scan.sh, pin-scan*.log,
update-preview-*.log, update-diff-*.txt, py-release-check.log, nix-release-check.log,
nix-joined-layer.log, release-check-patched.sh). Scratch trees: /tmp/p22-proofs/w7/. The orchestrator
did not rerun the commands. -->

This record backs phase 1 of the concept ("stop new staleness") and the template items of
`ESTATE-` rows on template-py and template-nix. It is a preview only. No template repository
changed, and nothing was released or committed there.

## Question

If a person releases the current candidate of template-py and template-nix, do the projects they
render hold any personal-tool pin? Does an update of a managed project remove the old pins?

## Inputs

- CopyRoom 0.8.7, built from the local repository tag: `nix build
  "git+file:///home/andrew/Documents/Projects/copyroom?ref=refs/tags/v0.8.7"` gave
  `/nix/store/jdmzah9xpzwk47hz3xl1zxsl48pnll9i-copyroom-0.8.7`. `copyroom doctor`: `ok: true`,
  Templateer 0.6.0.
- Released baseline: template-py `v0.9.0` (`926d1b9a`) and template-nix `v0.5.0`
  (`435bc637`, `main@origin`).
- Candidate, template-py: jj change `upvtvyvu`, git `4a228ec5`, "Release template-py 0.10.0 with
  setup:sync", in the unlanded workspace `task-mode`. No tag `v0.10.0` exists yet.
- Candidate, template-nix: jj change `popopywu`, git `077d0e48`, "Adopt Testee task mode in Nix
  base template". It is local `main*`; `main@origin` is still `v0.5.0`.
- Each tree came from `git archive <commit>` into `/tmp/p22-proofs/w7/{py,nix}-{main,cand}`. The
  workshop ran there, so `generated/` and `.copyroom-workshop/` never touched a repository.
  The copyroom skill `copyroom-template-edit` describes the real route (`template-checkout`,
  `template-preview`). This record used the same engine on copies, because the rule of project 22
  allows no write into a project repository.

## Method and results

| # | Command (run in the scratch copy) | Result |
| --- | --- | --- |
| 1 | `copyroom render py basic` and `probe` | rendered, exit 0 |
| 2 | `python3 -I scripts/check_render.py` (the candidate's own rule list) | `ok` for both scenarios |
| 3 | `copyroom golden py basic` and `probe` | `match`, nothing added, changed, or removed |
| 4 | `copyroom render nix` for `basic custom home none probe`, then `copyroom golden nix` for each | rendered, five `match` results |
| 5 | `copyroom render module` and `golden module` for `basic home probe custom`, then `scripts/check_render.py` | four `match` results; `template-nix renders: ok` |
| 6 | `copyroom release-check py` (runs `devenv test` in each rendered scenario) | `ready`; `basic` and `probe` passed, exit 0 |
| 7 | `scripts/release-check.sh` for template-nix | The `nix` source passed all five scenarios. The script then stopped: "cannot find CopyRoom's Python interpreter". It reads the first line of the `copyroom` file as a Python shebang. The Nix wrapper has a Bash shebang. Cause: wrapper only. |
| 8 | The rest of step 7 by hand: `copyroom new source/base`, `copyroom layer add --source source/module --publish-unguarded`, `check_render.py <project>`, `devenv test` | all passed; the final `devenv test` printed `Running devenv:enterTest ... (no command)` and no error |
| 9 | `pin-scan.sh` over every rendered tree (script below) | candidates: 0 pin lines in 7 of 7 trees; released `py` baseline: 1 pin line in each of 2 trees |
| 10 | A managed-project update. `copyroom new` made a project from the released source. The source directory then received the candidate. `copyroom update --out ../preview` ran in the project. | `conflicts: []`, `journal_state: prepared` for both templates |

The scan (`pin-scan.sh`) flags, in `devenv.yaml`, any tool name (repoman, testee, devman, gitman,
linkman, copyroom, templateer, agentman, vendomat), `path:`, `git+file:`, or `Bullish-Design`; in
`devenv.nix`, any `repoman.`, `testee.` option, `devman = {`, `getFlake`, or a Testee import; and any
retired file (`.copier-answers*`, `gitman.toml`, `.repoman/`) or `*_ref` answer.

### What the pin scan found

- **template-nix:** no pin in `v0.5.0` and none in the candidate. The candidate adds the five
  standard task placeholders to `devenv.nix` (49 lines, "TESTEE_NOT_SET_UP" markers). The scan
  finds no pin in `v0.5.0`, which already dropped RepoMan.
- **template-py `v0.9.0`:** `devenv.yaml` pins no tool, but `devenv.nix` line 8 is `imports =
  [ ./nix/testee.nix ]`. That file imports `/run/current-system/sw/share/testee/module/testee.nix`
  when it exists, and sets `testee.prepare` and `testee.checks`. The project therefore depends on a
  machine path and on a Testee module that Testee 0.8 removed (R18).
- **template-py candidate:** no import, no `testee.*` option, no `nix/testee.nix`. `devenv.nix`
  grows from 30 to 82 lines: the `setup:sync` task, the five placeholders, and `base:check` and
  `base:test` chained to them.
- **The update preview** (step 10) deleted `nix/testee.nix` from the managed py project and
  rewrote `AGENTS.md`, `README.md`, `devenv.nix`, `devenv.yaml`, and `pyproject.toml`. Its scan:
  0 pins after, 1 pin before. For nix it rewrote `AGENTS.md`, `README.md`, and `devenv.nix`. No
  conflict arose in either project, and the project tree itself stayed unchanged until `--apply`.
- The legacy answer names (`managers`, `repoman_ref`, `testee_ref`, `repoman_dev_root`,
  `devman_ref`) stay accepted in every `schema.py` as `LEGACY_ANSWERS`. They are never rendered.
  An old project can still replay its saved answers.

### Commands for a rerun

```bash
export PATH=/nix/store/jdmzah9xpzwk47hz3xl1zxsl48pnll9i-copyroom-0.8.7/bin:$PATH
git -C ~/Documents/Projects/template-py archive 4a228ec5 | tar -x -C /tmp/p22-proofs/w7/py-cand
cd /tmp/p22-proofs/w7/py-cand && copyroom render py basic && copyroom golden py basic \
  && python3 -I scripts/check_render.py && copyroom release-check py
~/.local/state/vendomat/p22/w7/pin-scan.sh generated/py/*
```

## Observations

- The candidate's `check_render.py` already holds the rules "no pinned Testee input or import",
  "no local path input", "RepoMan is retired, so no rendered file mentions it", and "no 0.7
  module option". These rules fail if a careless golden refresh locks a regression.
- Rendered `AGENTS.md` still names Testee commands (9 lines in py, 6 in nix) and Devman paths. They
  are instructions, not pins. A cloner without Testee reads them as advice that needs a tool the
  clone test calls personal. The concept's phase 1 says "cut the personal tool workflow from the
  static `AGENTS.md`"; this part is not done.
- A `devenv test` with five placeholders passes with "no command" in `enterTest`. A repository
  built from the candidate therefore passes `devenv test` while testing nothing. Testee reports
  "not set up", but `devenv test` alone does not. This is the failure that project 22's rule 4
  names ("could it succeed while doing nothing?"). It sits outside W7's question.
- The `jj` workspace `template-py/.gitman/workspaces/task-mode` and the local template-nix `main`
  hold the candidates. Neither is released or pushed.

## Verdict

**Holds.** Both candidates render projects with no personal-tool pin. All goldens match, every
`check_render.py` rule passes, `release-check py` passes, and the template-nix base and module
layers join and pass `devenv test`. An update of a managed project removes the old Testee module
import with no conflict.

**Does not hold for the released tag of template-py.** `v0.9.0` still renders a project that
imports a machine-path Testee module. A person who releases the template-py candidate fixes it.

## Unproved

- A release: no tag, no push. The owner still reviews the candidates before release.
- `copyroom update --apply` on a real project; a project created from a tag with `--ref`.
- A rendered project's `testee verify` against Testee 0.8.1. No Testee run happened.
- The `AGENTS.md` prose cut named in phase 1.

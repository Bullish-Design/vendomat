# Project 22: open items

**Draft, 2026-10-13.** This file lists every question that still needs an owner ruling or a choice
before the migration of the [concept](CONCEPT.md) can finish. Each item states what it is, why it is
open, the options with their pros, cons, implications, and opportunities, and a recommendation.
Work that needs no decision (spikes and proofs) is in the [plan](PLAN.md). Rulings are in
[DECISIONS.md](DECISIONS.md). When the owner rules on an item, the ruling goes into `DECISIONS.md`
and the item here gets the ruling number. Do not renumber an item.

| # | Item | Blocks | Status |
| --- | --- | --- | --- |
| OI-01 | How personal inputs are pinned (A5) | Phase 2, the home lock | Recommendation ready |
| OI-02 | How the pointer path option reaches the overlay imports (R14) | Phase 5 | W10 done; recommendation ready |
| OI-03 | Where the fleet doctor lives (A6) | W5 to production, every phase gate | Recommendation ready |
| OI-04 | nix-meta's flake structure (A8) | W6, phase 4 | Recommendation ready |
| OI-05 | repoman's future (A9) | Phase 6 | Ruled (R15); partly done |
| OI-06 | devman's `agent` group (A10) | Phase 2 | Recommendation ready |
| OI-07 | The order of removing the old Vendomat module (A11) | Phase 2 | Recommendation ready |
| OI-08 | Today's stale import of devman's link module | Nothing; a live defect | Done and verified after the switch |
| OI-09 | Testee task-mode details | W4, phase 6 | Partly ruled (R16); D5 to D9 open in the Testee review |
| OI-10 | When the devenv binary moves to the machine (R13) | Phase 4, phase 7 | Recommendation ready |
| OI-11 | mancore's future | linkman, the doctor contract | Recommendation ready |
| OI-12 | Where shared values of machine and home pairs live | W8, phase 3 | Recommendation ready |
| OI-13 | Work in other sessions that changes the same repositories | Every phase | Needs the owner |
| OI-14 | Workspaces and worktrees not checked for unlanded work | Phase 2 | Needs the owner |
| OI-15 | Cleanup of the composed flakes | Phase 2 | Recommendation ready |
| OI-16 | Status of docman, siteman, scopeman, and agentman | Phase 2 | Recommendation ready |
| OI-17 | devman's link engine during the migration | Phase 4, phase 5 | Recommendation ready |
| OI-18 | A tool's own repository that imports its own module | Phase 6, the doctor | Recommendation ready |

---

## OI-01: how personal inputs are pinned (A5)

**What.** The rule for how the home lock refers to each personal tool (devman, gitman, linkman,
copyroom, testee, agentman, and the others).

**Why open.** Today nix-meta mixes every form: tags, a raw commit for Vendomat, `?ref=main` on
seven inputs, and `git+file://` on seven. The latest nix-meta commit pins CopyRoom to `main`.
Without one rule, "which version runs?" has no answer.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Release tag from the collection (`git://server`) | Same rule as project 21. Each tag is a deliberate release. No GitHub dependency. | Each tool needs release discipline: tag, then push the tag to the collection. A machine off the tailnet cannot fetch. | `--override-input` covers development. A check that rejects any other ref is easy. |
| b. Release tag from GitHub | Works anywhere | A second source of truth. Private repositories need a key or token. | A fine interim route; nix-systems uses it today. |
| c. A curated `release` branch per tool, fast-forward only | `nix flake update` takes each tool's newest release with no tag lookup. Vendomat uses this for itself. | The ref does not name a version; the lock does. Needs branch protection on the collection. | Recorded as an idea in `DECISIONS.md`. |
| d. A raw commit | Exact | Unreadable; it does not say that a release happened | What nix-meta does for Vendomat today |
| e. A branch such as `main` | Always current after an update | An update moves silently to whatever is on the branch | What the latest CopyRoom pin does |
| f. A local `git+file://` path | Instant development loop | Fails without the checkouts; not portable | Seven nix-meta inputs today |

**Recommendation:** (a), with (b) allowed until each tool's tags reach the collection. Third-party
inputs (nixpkgs, home-manager, devenv) keep their own pins. Add a check that fails on (d), (e), or
(f) for a personal tool.

---

## OI-02: how the pointer path option reaches the overlay imports (R14)

**What.** R14 makes the pointer path a Home Manager option, default
`~/.local/state/devlayer/current.nix`. Home Manager activation writes the pointer at that path. The
62 overlay `devenv.local.nix` files must import the same path.

**Why open.** An option in the home and a literal in 62 overlay files can disagree. A disagreement
must fail loudly, and a change of the option must not need 62 edits. W10 measures the candidates on
devenv 2.4.0.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. One shared overlay file (for example `~/.config/devman/common/devlayer.nix`) holds the path; each project file imports it by relative path | One edit changes every repository. All files are real and tracked by devenv. | The home option and the shared file are two places; the fleet doctor must compare them. | The chain is project file, shared file, pointer, store. W10 F4a. |
| b. `builtins.getEnv "DEVLAYER_POINTER"` with a default, set by the home | The home option is the only source | devenv may evaluate purely, or its cache may not track the variable; then a change goes unseen | W10 F4b decides it. |
| c. Each overlay file holds the literal; devman regenerates them | No extra file | 62 files change on each move; churn in the overlay history | devman's link plane already writes overlay state |
| d. A fixed path that never moves; the option only moves a symlink there | One literal forever | A symlink as the import's final component is exactly the untracked form W9 found | Rejected by W9 |

**W10 result ([W10](evidence/W10-POINTER.md)):** (a) works with no flag (F4a). An edit of the shared
file is caught too. (b) works, but every change of the variable costs a full evaluation, and the
layer then depends on the caller's environment (a shell, direnv, cron, Dagu). (d) is untracked by
W9's rule. W10 also found that a relative import resolves against the directory of the symlink's
target, the central overlay file.

**Recommendation:** (a). The details:

- The shared file is a regular file, tracked in the overlay repository. It is never a Home Manager
  `home.file` link, because a link into the store goes untracked.
- It holds the pointer path and a `builtins.pathExists` guard. Before the first switch, a repository
  then falls back cleanly instead of failing (W10 F5).
- A change of the option is one edit of the home option and one edit of the shared file. The fleet
  doctor fails when the two disagree. Home Manager exports the option's value at run time (for
  example in a session variable) so that the doctor can read it; the evaluation itself never reads
  the variable.

---

## OI-03: where the fleet doctor lives (A6)

**What.** The one command that checks every repository against the rules of the concept after
each switch.

**Why open.** Every migration phase uses it as its gate. W5 builds a prototype; it needs a
permanent home.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. A `devman doctor --fleet` mode | devman already knows every registered project and is the one check of the whole plane. No new tool. | devman grows. The rules release on devman's schedule. | W5's `doctor.py` moves into devman. |
| b. A separate command (`estate doctor`, or a Vendomat verb) | Clean separation | Another tool, against the goal of a smaller family. It still needs devman's project list. | Only if the estate outgrows devman |
| c. Each tool checks its own rules (`<tool> doctor --json`); one command collects them | Each tool owns its facts (mancore's capability idea). Checks stay correct as tools change. | Every tool must implement `doctor --json` first | The growth path for (a) |
| d. A scheduled Dagu workflow | Runs without the owner | A trigger, not a home | Use it with (a) |

**W5 result ([W5](evidence/W5-FLEET-DOCTOR.md)):** a 0.25 s prototype with ten checks and a
selftest. It must copy a live evaluation cache before it reads it (`ESTATE-044`): opening the live
database created files in 9 repositories. W9's `doctor_check.py` has the same defect.

**Recommendation:** (a) now as the collector, moving toward (c) tool by tool, run nightly by (d).

---

## OI-04: nix-meta's flake structure (A8)

**What.** The file layout and framework of nix-meta after it holds only homes (R9).

**Why open.** The current layout grew without a plan. The choice shapes W6 and phase 4.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. A plain flake | Smallest, no framework, easy to read and to move | Some per-system boilerplate | Fits a repository that holds only homes |
| b. Light flake-parts | Removes the boilerplate; widely used | One more concept and input | Reasonable if boilerplate grows |
| c. The dendritic pattern | Locality when one feature spans NixOS and Home Manager | Its main gain is gone: machine and home are separate repositories | Not a fit |
| d. snowfall-lib | Conventions out of the box | Its README says it is effectively unmaintained | Avoid |
| e. ez-configs, nixos-unified, blueprint | Less wiring | Single maintainer or thin documentation; lock-in | Avoid |
| f. A Vendomat workspace | One tool for both repositories | Project 21 R35 keeps homes outside Vendomat | Ruled out |

**Recommendation:** (a).

---

## OI-05: repoman's future (A9)

**What.** repoman's remaining work: environment variables from a per-project roster, one generated
router skill, the `git` and `gnupatch` packages, one `copyroom status` task, and a doctor for its
own wiring.

**Why open.** 18 repositories pin its module. The generated skill exists in 9 different versions.
Project 21 `VMT-112` and this concept both forbid the pins.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Fold it into devman | One fewer tool | devman takes on more | The roster becomes a field in `.devman/project.toml` |
| b. Keep it as a small tool delivered by the home | No code moves | A whole tool, repository, and release cycle for little work | Still needs the roster file |
| c. Retire it | Removes a tool, 18 inputs, 18 `.repoman/` directories, and the 9 skill versions | Loses per-project rosters | One static router skill in the central pool; its checks move to the fleet doctor; `git` and `gnupatch` move to the home |
| d. Generate the router skill from each tool's capability manifest (mancore) | Each tool describes itself | Needs capability support in each tool | A later step after (c) |

**Recommendation:** (c), then (d) later. **Check first:** that no repository uses a roster other than
the default.

**Ruled (R15), 2026-10-13. Done:** the central overlay no longer imports RepoMan's host module (18
files, overlay commit `da3a4f58`); mnemonix dropped its RepoMan files and text (`9af72666`). **Left:**
the RepoMan repository itself; the generated router skill in the overlay; the template-nix seed of
`.repoman/project.toml` (mnemonix's CopyRoom state still lists it, so a template update could create
it again); the `.repoman/` files in the other repositories (W5 D03).

---

## OI-06: devman's `agent` group (A10)

**What.** A devman workflow group that calls `agentman run --request` and the
`agentman.devman/v1` contract.

**Why open.** Agentman deleted both on 2026-09-18 (commit `072aed0`). The group looks alive and
cannot work.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Remove it | Deletes a dead path. No repository uses the group. | The capability is gone until it is rebuilt | Remove `groups/agent/`, `src/devman/agent.py`, the fake agentman fixture, and the mancore concept mention |
| b. Port it to agentman's current commands (`send`, `pipe`) | Keeps an LLM workflow in the plane | Agentman is pre-1.0 and its interface moves; effort for an unused feature | Better after agentman stabilizes |
| c. Leave it | No work | A path that reports nothing and looks alive | Not acceptable under devman's charter |

**Recommendation:** (a).

---

## OI-07: the order of removing the old Vendomat module (A11)

**What.** nix-meta imports the V4 Vendomat NixOS module (raw rev `d5a90f0`). It installs the
Vendomat 0.5.0 command, `share/vendomat` files that nothing reads, and the `repoman-toolchain-core`
closure.

**Why open.** Project 21 R36 confirms the direction. But the agentman user units point into the
toolchain closure (`profiles/developer.nix:184-211`), so the order matters.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Remove it now | Removes dead files and a stale pin | Breaks the agentman units | Not safe alone |
| b. Remove it in order: agentman gets its own tagged input; the `vendomat` launcher comes from the machine platform (R13); then the module and the closure go | Nothing breaks | Three steps | Fits phase 2 |
| c. Keep it until nix-systems takes the server | No work now | Keeps a stale command and lock nodes; conflicts with OI-01 | Delays the lock cleanup |

**Recommendation:** (b).

**mancore, done 2026-10-13:** mancore commit `16c7093a` drops `vendor.toolchain.enable`, the RepoMan
roster, and the RepoMan header text; Testee passed 4 of 4, and the repository evaluates without the
consumer module. The overlay still imports the consumer module for mancore, because mancore's main
checkout holds another session's uncommitted file on the old `main`, whose `devenv.nix` still sets
the option. Remove the import after that checkout moves to the new `main`.

**Found 2026-10-13:** mancore's overlay imports
`/run/current-system/sw/share/vendomat/consumer-module.nix`, and mancore's `devenv.nix` sets
`vendor.toolchain.enable = false`, an option from that module. So the module has one reader, and the
removal order of (b) needs one more step: drop that import and setting from mancore first.

---

## OI-08: today's stale import of devman's link module

**What.** All 62 overlay files import `/run/current-system/sw/share/devman/link-module.nix`. Its
final component is a symlink into the store, so devenv never tracks it (W9). After a devman-link
upgrade, a repository can keep the old module until `--refresh-eval-cache` runs.

**Why open.** It is a live defect today, before any migration. It can make the link plane act on
an old module with no error.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Write the pointer now. devman's link step (or a NixOS activation step) writes the pointer at the R14 default path, aimed at today's system path. The overlay imports the pointer. | Fixes the defect now. It is the final design, so phase 5 has no second move. | Needs the OI-02 mechanism and W10 first. Touches 62 overlay files once. | Phase 5 then only changes who writes the pointer. |
| b. Refresh the cache in every repository after each `nixos-rebuild` | No design change | About 60 repositories per switch; fragile; a missed repository stays stale | A stopgap only |
| c. Wait for the migration | No work now | The defect stays until phase 5 | The fleet doctor reports it meanwhile |
| d. A devenv binary patch that tracks symlinked imports | Fixes it at the source for all repositories | Needs a project 21 ruling (`VMT-105`); a patch carried forever | Optional extra safety |

**Recommendation:** (a). W10 passed, so this can start now.

**Done 2026-10-13 (option a):**

- The pointer `~/.local/state/devlayer/current.nix` exists. It names devman-link 0.6.0's module by
  its store path. `common/devlayer-pointer.sh` in the overlay rewrites it by hand when needed.
- The overlay holds `common/devlayer.nix` (a regular file with a `pathExists` guard), and all 64
  project `devenv.local.nix` files import it (overlay commit `d484e975`, on overlay `main` at
  `da3a4f58`).
- nix-meta commit `49bceb34` adds the option `nix-meta.devlayer.pointerPath` (R14) and an activation
  step that rewrites the pointer on each switch, only when its content changes.
- devman commit `cb16dd77` makes new projects' overlay files import `../../common/devlayer.nix`.
- Five repositories entered their shells; their caches now track the shared file and the pointer,
  and a pointer change was picked up with no flag. D05 dropped from 60 to 50 at once; each remaining
  repository clears on its next shell entry.
- `devman doctor` exits 0 after a cleanup: the nix-meta-channel4 worktree was archived and removed
  (OI-15), `devman doctor --prune` removed 14 records of missing repositories, and the overlay's
  unlanded commits were landed on its `main` (OI-13).

**Verified after the owner's switch (2026-10-13):** the running system is the generation that holds
the pointer step. The pointer names the live devman-link 0.6.0 module and was not rewritten (same
content, W10 F3). `devman doctor` exits 0. All 51 repositories with an overlay entered a shell: 38
entered cleanly; 13 failed in exactly the same way with the old import swapped back, so none of the
13 failures comes from this change (see the follow-ups). D05 fell from 60 findings to 7.

**Earlier note:** the owner's switch activated the pointer step. Before that switch, the overlay had to stop importing RepoMan's host
module (R15), because nix-meta commit `f173fd0` removes it from the system.

---

## OI-09: Testee task-mode details

**What.** R10 rules that Testee runs five standard tasks, with placeholders that exit 78. Some
details of the change stay open.

**Why open.** W4 needs them to build the release.

- **How Testee runs a task.** (a) `devenv tasks run <name>` per task: simple; each run enters the
  shell. (b) One `devenv shell` per verify, then each task inside it: faster; depends on devenv
  internals. **Recommendation:** (a), measured in W4; switch to (b) only if time is a problem.
- **Repositories with no devenv files** (11 today, for example template-nix, llama-infernal).
  (a) Testee reports "no devenv" as its own state. (b) Require devenv everywhere. (c) A plain-script
  fallback. **Recommendation:** (a): it is honest and needs no new format.
- **Per-check settings that the module carries today** (`testee.keep`, time limits). (a) Drop them
  and use devenv task attributes. (b) Keep a small overlay setting per project. **Recommendation:**
  (a); move a setting to the overlay only when a repository needs it.
- **Profiles.** `testee verify` runs `check:*` and `test:full`; `--profile quick` runs
  `check:lint`, `check:format`, and `test:quick`. No other profile until a need appears.

**Update 2026-10-13.** The W4 review (Testee `.scratch/projects/10-task-mode/` (`REVIEW.md`, `DECISIONS-NEEDED.md`)) measured devenv 2.4.0. Running a task
by `devenv tasks run` per task stays (option a). R16 rules the placeholder detection, opt-in tasks,
tree-only verdicts, and structured files. The per-check settings point stays open as D5 there: a
built-in time limit per task, plus an optional `input.testee.timeout_s` in the task.

---

## OI-10: when the devenv binary moves to the machine (R13)

**What.** R13 puts the devenv binary and the `vendomat` launcher in the machine layer. Project 21
slice S2 builds the patched binary (patches 0003 and 0005). Switching the host to it is an owner
gate.

**Why open.** Today devenv 2.4.0 comes from the per-user profile, through Home Manager as a NixOS
module. Phase 4 removes that module, so devenv must have a new place by then.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Move stock `pkgs.devenv` to the machine in phase 4; switch to the S2 binary when it exists | Phase 4 does not wait for project 21 | Two moves: stock first, patched later | Low risk; the same version as today |
| b. Wait for S2, then move once | One move | Phase 4 waits on project 21's slice | Couples the projects |
| c. Keep devenv in the home | No move | Contradicts R13 and project 21 R22 | Rejected |

**Recommendation:** (a).

---

## OI-11: mancore's future

**What.** mancore holds the family's exit codes, report shape, and capability manifest. linkman
and loci-core pin tag v0.1.0, 18 commits behind `main`. That tag imports `click` without declaring
it, which breaks the `linkman` command.

**Why open.** Rule 6 of the concept makes command contracts the interface between tools. mancore's
role under that rule is not decided.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Cut a new release and move linkman and loci-core to it | Fixes linkman now; mancore stays a normal project dependency | Release work | The clone test allows the pin |
| b. mancore becomes a written specification only; tools implement it themselves | No shared code to pin | Each tool re-implements the same small code | The capability manifest becomes a format, not a library |
| c. Both: a release now, and the specification as the authority | Fixes the defect and states the contract | Two artefacts to keep in step | The doctor contract (OI-03 c) uses the specification |

**Recommendation:** (c).

---

## OI-12: where shared values of machine and home pairs live

**What.** Four things have a machine half and a home half: atuin (server and client), agentman
(Postgres role and daemon), mnemonix (Hindsight service and agent wiring), and secrets (sops-nix
writes, tools read).

**Why open.** In two repositories, the two halves must agree on a version, a port, a role name, or
a path. W8 builds the check.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. The owning tool's flake exports the package or constants; both halves pin the same tag | One owner per fact; no new repository | Each tool needs a small export | pytuin owns atuin; mnemonix owns its ports |
| b. One shared constants flake for the estate | One place for every shared value | A new repository; every value changes in it | Couples unrelated pairs |
| c. nix-systems' inventory exports the values; nix-meta reads them | One place, already the source of host facts | The home depends on the machine repository | Breaks the separation of R9 |
| d. Duplicate the values; a check compares them | No coupling | Two places to edit | The check is required in any case |

**Recommendation:** (a), with the check of (d).

---

## OI-13: work in other sessions on the same repositories

**What.** Other sessions changed nix-meta on 2026-10-13: "Remove terminal tool pins from machine
flake", "install CopyRoom path omission support", and "pin latest CopyRoom main for toolbelt". A
project 21 workspace (`p21-dlist`) is open in vendomat.

**Why open.** Two plans for one repository diverge. The CopyRoom `main` pin conflicts with OI-01.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Point the other sessions at this project before they continue | One plan | Their work pauses | Their completed steps may count as phase 2 |
| b. Let them continue; reconcile in phase 2 | No pause | Rework; more lock nodes meanwhile | |
| c. Adopt their direction where it agrees, and correct only the conflicts | Keeps useful work | Needs a review of their commits | The "remove tool pins from the machine flake" step agrees with R8 and R9 |

W5 measured how fast this moves: during the day the `repoman` input left every repository except
repoman's own (18 found earlier), and `gitman.toml` fell from 62 files to 4.

**Recommendation:** (c), and give the other sessions this project's concept and open items.

**2026-10-13:** the overlay's unlanded commits from another session (`0633dbd8`, and `9df52a8b`, which
had no description) were landed with the OI-08 work, then corrected by R15. One undescribed overlay
change (`9f3038b6`, 2026-10-11) is left; it is probably superseded. devman's main checkout sits on
another session's unlanded stack (`step7-fix1-exit-codes`), so it does not show devman `main` yet.

---

## OI-14: workspaces and worktrees not checked for unlanded work

**What.** nix-meta has 23 `.worktrees` (2026-10-02 to 2026-10-09) and one Gitman workspace
(`mnemonix-memprojects`). `~/Documents/Projects/gitman-workspaces/` has 8 directories. devman has
2 `.worktrees`. siteman has 3, and its git HEAD is detached at an old commit. vendomat has 3 orphan
`.worktrees` (about 90 MB each) with no unlanded commits.

**Why open.** The owner's rule: no work may stay in a workspace that the owner does not know about.
Phase 2 deletes files in these repositories.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Audit each one: list the commits that `main` lacks, then land or delete | Nothing is lost | Time; some old lanes need judgement | A subagent can do the read-only listing |
| b. Archive each directory to a dated tarball, then delete | Fast; reversible | Unlanded work stays unseen in the archive | |
| c. Leave them | No work | Disk use; confusion; the rule is broken | Not acceptable |

**Recommendation:** (a) for repositories with registered workspaces; (b) for orphan directories
with no commits that `main` lacks (vendomat's three).

---

## OI-15: cleanup of the composed flakes

**What.** Decisions on flakes around nix-meta ([SUB-FLAKES](evidence/SUB-FLAKES.md)).

- **nixvim:** archive. nix-nvim supersedes it.
- **nix-meta-channel4:** delete. It is a worktree of nix-meta with no commits. **Done 2026-10-13:**
  archived to `~/.local/state/vendomat/p22/oi-15-channel4/` and removed with `git worktree remove`.
- **nix-desktop:** (a) keep as a home module for a future laptop home; (b) archive. It is clean Home
  Manager with no consumer. **Recommendation:** (a): it costs nothing while it sits.
- **nixbuild:** (a) a plain package installed by the home; (b) keep its NixOS module and
  nix-terminal wrapper. **Recommendation:** (a).
- **fornix-host:** (a) keep, disabled, until its boot-order cycle is fixed; (b) remove the input.
  **Recommendation:** (b) from nix-meta now; fornix's own repository keeps the module, and
  nix-systems adds it when it works.

---

## OI-16: status of docman, siteman, scopeman, and agentman

**What.** Their place in the estate ([TOOL-CLASSES](evidence/TOOL-CLASSES.md)).

- **docman:** archived. Remove the stale references (the repoman skill table, `AGENTS.md` that
  still says it is active, the comments that say the host installs it).
- **siteman:** a product with no consumers, outside the personal layer. A site repository may pin
  it. Separately, its detached HEAD and 3 workspaces are part of OI-14.
- **scopeman:** a consumer, not a family tool. It is the recommended pilot repository for phase 6,
  because it has no product code to break.
- **agentman:** a personal service: its daemon is in the home, its database on the machine.

**Recommendation:** accept the four classifications as written.

---

## OI-17: devman's link engine during the migration

**What.** devman has two link engines: the old `devman_link` (default) and linkman behind the
`DEVMAN_LINK_ENGINE` flag. devman project 044 decided (D23, D24) to call the linkman command and to
drop the flag. That work is half done.

**Why open.** The link module that the pointer imports belongs to the engine. Changing the engine
and the import path in the same phase doubles the risk.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Finish the linkman switch-over before phase 4 | The home ships the final engine | Delays phase 4 | linkman needs the OI-11 fix first |
| b. Ship the home with `devman_link`; switch to linkman after phase 5 | Phase 4 does not wait | Two moves of the engine | One variable at a time |
| c. Freeze the switch-over until the migration ends | No parallel work | Keeps two engines longer | |

**Recommendation:** (b). Change one thing at a time; the pointer makes the later engine switch a
one-line change in the layer.

---

## OI-18: a tool's own repository that imports its own module

**What.** The repoman repository imports its own module (`path:./modules`), and the testee
repository uses its own `testee.*` options. W5 reports both as findings of D01 and D02.

**Why open.** The clone test says a personal tool must not enter a repository. A tool's own
repository develops that tool, so someone who clones it does need it.

| Option | Pros | Cons | Implications and opportunities |
| --- | --- | --- | --- |
| a. Exempt a tool's own repository from D01 and D02 when the import is a local path to itself | Honest: the clone test passes for it | The doctor needs a list of tool repositories | A short list in the doctor's configuration |
| b. No exemption; the tool's repository also gets its module from the home | One rule everywhere | The repository then tests the installed version, not its own source | Wrong for development |
| c. Retire the module so the question disappears | Simplest | Only possible for repoman (OI-05) and Testee (task mode, R10) | Both are already planned |

**Recommendation:** (c) where it is planned (repoman, Testee), and (a) for any tool that keeps a
devenv module.

---

## Follow-ups found during the OI-08 work

These need no option analysis; each has one obvious fix.

- **mancore's overlay has no `devman.link` block.** Its shell prints a devman-link error
  ("attribute 'devman' missing") and still enters. **Done:** devman-link reads the file's top-level
  `devman.link` attribute, so the overlay now declares `devman.link = { };` (mancore keeps no
  central links). The shell enters with no error; overlay `main` is `eb4850f8`; `devman doctor`
  exits 0.
- **An undescribed overlay change, `9f3038b6` (2026-10-11),** adds devenv-py overlay content that
  `9df52a8b` probably supersedes. **Done:** ten of its eleven files equal `main`; the eleventh
  differs only in the import line that `main` changed on purpose. Abandoned.
- **forgelab's overlay file** (archived set) lost its RepoMan import line with the other 18. Keep the
  removal: the line named a path that the next switch removes.
- **W9's `doctor_check.py`** opens live caches in place (W5). **Done:** it now copies the database
  and its `-wal` file to a temporary directory and reads the copy. A test run on linkman left every
  cache file unchanged.

## Findings from the check after the switch (2026-10-13)

None of these comes from the OI-08 change: each failure was the same with the old import.

- **Six repositories fail shell entry with `The option 'dotenv.resolved' was accessed but has no
  value defined`:** PyGentic, clinch, parsedantic, pydantree, terminal-state, webdantic.
- **Five repositories need a secrets reason** (`SECRETSPEC_REASON`) when an agent enters the shell:
  browsee, fornix, templateer_v2, tyo3, zelligate. Their secretspec policy defaults to requiring one
  for agents. Not a defect; their D05 rows appear after the owner's next shell entry.
- **fsdantic fails:** `/nix/store/...-agentfs-src/cli/Cargo.toml` does not exist; an input changed
  shape.
- **nix-meta has an overlay `devenv.local.nix` but no `devenv.nix`,** so D05 can never pass for it.
  The doctor should skip a repository without devenv files.
- **nixvim's evaluation cache is a text file with jj conflict markers** (W5); delete it.
- **nix-meta still installs RepoMan's host module** (`machines/server.nix:74-76`, input `repoman`
  v0.14.1), added by another session after `f173fd0`. Nothing imports it now. Remove it under R15.

# Project 23 kickoff: Vendomat slices S1 (module-only devenv fork) and S2 (host devenv binary)

Run this session from `~/Documents/Projects/vendomat`. This file is the kickoff of project 23,
`.scratch/projects/23-vendomat-fork-and-binary/`. Project 21 stays the design authority, and its
`evidence/` directory holds the slice evidence. Project 24 (S3 and S4) runs at the same time. All slice work happens in the Vendomat
repository. Its outputs go to two places: a tag in the collection's `~/vendor/devenv`, and a built
binary in the local Nix store.

## Goal

1. **S1:** the collection serves one tag, `v2.4.0-vendomat-modules.1` (R44), that holds
   upstream devenv v2.4.0 plus module changes only. Any devenv 2.4.0 binary can use it as the
   workspace's `devenv` input.
2. **S2:** Vendomat's flake builds the host and ISO devenv binary: `pkgs.devenv` from Vendomat's
   pinned nixpkgs, plus patches 0003 and 0005. The change to switch the host to it is prepared and
   shown to the owner. It is not applied.
3. Each change passes `testee verify`, lands on `main`, and is pushed. The main checkout shows it.

## A new owner rule: no Attic, Harmonia in the initial install

The owner said on 2026-10-13: "I do *not* want to configure Attic from the beginning, lets make
sure harmonia is a part of the initial install though."

This overrides parts of the project 21 documents:

- **S2 does not push to Attic.** Skip step 7 of S2 in the guide and every Attic command. Keep the
  built binary in the local store under a GC root (S2 item 4 below).
- **The new system never configures Attic.** Machines share build outputs through Harmonia. A
  machine serves its own store with a signing key that it makes at first boot (project 19
  candidate A, project 20 keyless first boot).
- **Harmonia is part of the initial install.** An installed system runs Harmonia from first boot.
- **Every installed machine serves by default** (the owner ruled on this in the planning session,
  2026-10-13). Each installed machine runs Harmonia by default, and the YAML key `serve: false`
  turns it off. The signing key is made at first boot, and secrets never enter the store.
  Vendomat owns the sharing module (catalog key `serve`, Harmonia, and the substituter and key for
  clients) in slice S3. Basix turns it on in its core in S5. The two-machine VM proof goes in S3,
  and the real-machine proof stays in S7.
- **Leave the existing Attic on today's `server` alone.** It belongs to the current estate
  (nix-meta, project 22). Do not use it, change it, or remove it.
- **Section 2.3 of the implementation guide (Attic) is now history, not instructions.**

**This is already recorded.** Vendomat `main` `6b62dfc3` holds R39, and Basix `main` `03c0c433`
holds its Basix side. R39 supersedes `VMT-105` with `VMT-126`, which is S2's row now, and
`VMT-120` with `VMT-127`. It adds `VMT-128` (the sharing module, built in S3) and Basix `BSX-129`.
The guide's S2 step 7 now says "keep the binary; no Attic". Do not record R39 again.

## Read first

1. `~/.claude/CLAUDE.md`, `AGENTS.md`, and `.scratch/CURRENT.md`.
2. `.scratch/projects/21-vendomat-basix-split/IMPLEMENTATION-GUIDE.md`. Read it in full, because
   it is the main instruction set:
   - Section 1: the rules for every step (version control, verification, records, safety, subagents);
   - Section 2: the facts about the host, the collection, the repository, and the pins;
   - Section 3: the spike artifacts and their checksums;
   - Section 5: Phase 0;
   - Section 6: slices S1 and S2.

   This prompt changes the guide only where it says so.
3. `CONCEPT.md` (sections "Machines" and "The fork"), `DECISIONS.md` (R14, R17, R22, R31, R34, R39 to R45, and
   D2 and D7), and `REQUIREMENTS.md` in the same directory.
4. Evidence that S1 and S2 reuse: `evidence/W1-FORK-REVIEW.md`, `W2-MACHINES.md`, `W6-HOST-BINARY.md`, `W7-BUILD-OPTIONS.md`, and
   `W8-ISO-POLICY.md`.
5. Memory, in `~/.claude/projects/-home-andrew-Documents-Projects-vendomat/memory/`:
   - `no-attic-harmonia-initial-install.md`
   - `never-open-upstream-prs.md`
   - `host-btrfs-metadata.md`
   - `uv-env-leaks-into-subagents.md`
   - `delegate-to-background-subagents.md`
   - `testee-path-shadowing.md`

## Standing rules (short form; the guide has the full text)

- Use Gitman to open and close workspaces. Use native jj for describe, rebase, bookmark, and push.
  Never use raw `git`.
- The gate is `testee verify`. Do not call pytest, ruff, or ty directly.
- The machine supplies the Testee module and the `testee` command (Vendomat commit `538bc91c`).
  The project's checks live in `nix/testee.nix`, not in `devenv.nix`, and `devenv.yaml` has no
  `testee` input. Add the new opt-in checks there. Where the guide says "`testee.checks` in
  `devenv.nix`", read `nix/testee.nix`.
- Keep raw logs under `~/.local/state/vendomat/p21/<date>/s1/` and `.../s2/`. Put VM images and VM
  scratch files under `/mnt/shared/vendomat-p21/s1/` and `.../s2/`. Delete them at the end of the
  slice.
- Before each heavy build, run `btrfs filesystem usage /`. Stop when unallocated space is below
  15 GiB. If metadata use is above 90 %, wait 60 seconds and check again; stop if it stays above.
- Do not run garbage collection. Use sudo only through `/run/wrappers/bin/sudo`, and only when the
  owner approves it.
- Never open an upstream pull request (R34). Each patch header says
  `Upstream: none (Vendomat module fork; R34: no upstream pull request)`.
- Another session works on project 22 in this repository, and one works on S3 and S4 (see
  below). Rebase right before you land. Do not edit project 22 files. The main checkout may hold
  another session's unlanded commit. If `jj status` there is not clean, do not run `jj new main`;
  tell the owner.
- Never select a disk by its kernel device name.

## Steps

### 1. Phase 0

Run Phase 0 from the guide (Section 5): check the tools, list the workspaces and the work that
`main` lacks, check the spike artifact checksums, and archive the spike directories. Report a
checksum mismatch before you copy any file. Read R39 to R45 in `DECISIONS.md` and the guide's
Section 4.

### 2. The decisions (all ruled; do not ask again)

| # | Ruling | Outcome |
| --- | --- | --- |
| D2 | R41 | The module fork tag is Vendomat's second flake input `devenv` (`dir=src/modules`). The template writes `devenv: follows: vendomat/devenv`. S1 step 9 changes `flake.nix`, `tests/test_repo_shape.py` (root inputs `{nixpkgs, devenv}`), and the "one input" lines in `AGENTS.md`. |
| D7 | R44 | The tag is `v2.4.0-vendomat-modules.1`. |
| D1, D4, D6, D8 | R40, R42, R43, R45 | These are for S3 and S4. Read them so you do not contradict them. |

### Another session works on S3 and S4 at the same time

Each session owns its own files. Do not edit the other session's files.

| This session (S1, S2; project 23) | The S3/S4 session (project 24) |
| --- | --- |
| `devenv-dist/`, `nix/devenv-overlay.nix`, `flake.nix`, `tests/test_devenv_dist.py`, `tests/test_repo_shape.py`, `evidence/S1-*`, `evidence/S2-*` | `devenv/`, `templates/`, `src/vendomat/`, `launcher/`, the catalog and command tests, `evidence/S3-*`, `evidence/S4-*` |

- Both sessions add checks to `nix/testee.nix` and may touch `AGENTS.md`, the ledger, and
  `.scratch/CURRENT.md`. Keep each edit small, and rebase right before you land.
- One exception: the S3/S4 session edits the `MODULES` set in `tests/test_repo_shape.py` when it
  adds Python modules. You change only the root-input lines of that file. On a conflict, keep
  both edits.
- The S3/S4 session builds against the materialized S1 tree before the tag exists. When the tag
  is pushed and checked, and again when the S2 binary is built, write one line with the tag or
  the store path in `.scratch/CURRENT.md` (project 21 section), and land it.

### 3. S1: the module-only devenv fork

Follow the guide's S1 (steps 1 to 10) in a workspace named `s1-module-fork`. Notes:

- The patch series is m1 to m5 on upstream `b904dcb5`. The sources are `T4-patch.diff`,
  `patch1.diff`, `patch2.diff`, `0005-module-hunk.patch`, and the old patch 0002's
  `latest-version` content. Check the checksums from guide Section 3 first.
- No fixture has applied m5 on top of m3 and m4. Try that first. If it does not apply, rebase the
  hunk by hand and record the change.
- m1 changes `machines.NAME.nixos` only. Leave `home-manager` and `nix-darwin` as upstream has
  them (R35).
- Keep the old binary series in `devenv-dist/` as it is. S6 retires it.
- The checks are `modules-e2e` and `modules-vm`. Both are opt-in Testee checks. `testee verify`
  stays the required gate.
- **A pushed tag is permanent.** Push it into the collection only after every check passes, and
  only with the R44 name. Check it with
  `nix flake prefetch --json 'git://server/devenv?ref=refs/tags/<tag>&dir=src/modules'`.
- Record everything in `evidence/S1-MODULE-FORK.md`. Close the ledger rows that the guide names,
  with their evidence.

### 4. S2: the host devenv binary

Follow the guide's S2 in a workspace named `s2-host-binary`, with these changes:

1. Steps 1 to 4 are unchanged: the patches in `devenv-dist/binary/patches/` (0003 and the full
   0005, no 0008), the overlay `nix/devenv-overlay.nix` with its `filterdiff` step for
   `CHANGELOG.md`, and `packages.devenv` and `overlays.devenv` in `flake.nix`. Replace the
   hard-coded `defaultFork` store path with `self.packages.x86_64-linux.devenv`.
2. Step 5: build after the btrfs check. The build takes about 23 minutes without the cargo tests
   and 49 with them. Run the release build with the tests. Start it early and in the background,
   because it is the longest step of the session.
3. Step 6: the fixtures B2 (offline entry), B5 (install refusal; it needs the S1 tag), and B6
   (catalog entry), as the opt-in check `binary-e2e`. Use a free port, not 19418 (another
   daemon is there).
4. **Step 7 is replaced: no Attic.** Keep the binary as a release root. Make an indirect GC root
   outside the repository, for example:

   ```sh
   nix build .#devenv --out-link ~/.local/state/vendomat/roots/devenv-<vendomat-commit>
   ```

   Record the store path, its NAR hash (`nix path-info --json`), and its closure size. Write no
   Attic token, configuration, or push command anywhere: not in the repository, the evidence,
   or the tests.
5. **Step 8, the owner gate: switch the host binary.** Prepare the change and show it; do not
   apply it.
   - Today, nix-meta installs devenv in `profiles/developer.nix` (`pinnedDevenv`, from
     `github:cachix/devenv/v2.4.0`).
   - Project 22 ruling R13 puts the patched binary in the machine layer, and project 22 moves
     machines to nix-systems. Read project 22's `PLAN.md` and `DECISIONS.md` to see how far that
     move has gone. Choose nix-meta or nix-systems from that, and say why.
   - Show the owner the diff, the build command, and the rollback (the previous NixOS
     generation). Apply it only after a yes in this session.
   - Without a yes, record "prepared, not applied" in `CURRENT.md`.
6. Record everything in `evidence/S2-HOST-BINARY.md`.

### 5. Parallel work

- S1 and S2 are independent, except that fixture B5 of S2 needs the S1 tag. Run them in two
  workspaces at once. Start the S2 build first.
- Delegate heavy work to background Sonnet subagents: the S2 build and its fixtures, and the S1
  VM fixtures. The main agent writes the briefs, checks each result against its logs, records the
  evidence, and lands the change.
- Give every subagent these rules in its brief: the btrfs rule, the `/mnt/shared` rule, no
  garbage collection, no sudo, no Attic, no upstream contact. It must run `uv` only as
  `devenv shell -- uv`, because a bare `uv` writes into Vendomat's venv. It must write logs only
  under the slice's log directory.
- Land S1 and S2 as separate changes, each after a green `testee verify`.

## Stop and ask when

- A spike artifact checksum does not match.
- A patch in m1 to m5 does not apply, and the fix by hand changes behaviour, not only context.
- Any check fails, or `testee verify` is red, and the fix is not obvious.
- The host switch is ready (S2 item 5). This gate always needs the owner.
- The btrfs limits are hit.
- A rebase conflicts, or another session's work blocks a landing.
- Anything would touch Attic, a secret, or a real disk.

## Report at the end

Write the report to `.scratch/projects/23-vendomat-fork-and-binary/REPORT.md`, land it, and give
the owner the same text. Keep it short:

- for S1: the tag, its commit, the prefetch result, the check results, and the closed rows;
- for S2: the store path, the NAR hash, the closure size, the GC root, the check results, and
  the state of the host switch (applied, or prepared and not applied);
- the `main` commits, and the Testee result for each change;
- disk use before and after, and the files deleted from `/mnt/shared`;
- open items for the owner.

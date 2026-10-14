# Project 24 kickoff: Vendomat slices S3 (catalog, template, commands, sharing) and S4 (apply, rollback)

Run this session from `~/Documents/Projects/vendomat`. This file is the kickoff of project 24,
`.scratch/projects/24-vendomat-catalog-and-machines/`. Project 21 stays the design authority, and
its `evidence/` directory holds the slice evidence. Project 23 (S1 and S2) runs at the same time. Another session runs S1 (the module-only
devenv fork) and S2 (the host devenv binary) at the same time. This session builds S3 against
S1's work before S1 publishes its tag, then builds S4 on S3.

## Goal

1. **S3:** a workspace uses `vendomat.yaml`, read by the Nix parser, with every ruled key, on stock
   devenv 2.4.0 and the S1 module input. The commands `update` and `explain` exist. Errors show the
   `vendomat.yaml:` lines first. The shell prints the `advanced:` line. The Harmonia sharing
   module exists and passes a two-VM proof.
2. **S4:** `vendomat apply` activates a machine locally with no SSH. `vendomat rollback` returns to
   an earlier commit with a lasting result. Both are proved in VMs.
3. The old project 14 and V6 flow keeps working (R40).
4. Each change passes `testee verify`, lands on `main`, and is pushed. The main checkout shows it.

Do not apply anything to this host or any real machine. Every machine proof runs in a VM.

## Read first

1. `~/.claude/CLAUDE.md`, `AGENTS.md`, and `.scratch/CURRENT.md`.
2. `.scratch/projects/21-vendomat-basix-split/IMPLEMENTATION-GUIDE.md`. Read it in full, because
   it is the main instruction set:
   - Section 1: the rules for every step (version control, verification, records, safety, subagents);
   - Section 2: the facts (Section 2.3, Attic, is history now);
   - Section 3: the spike artifacts and their checksums;
   - Section 4: the decisions, all ruled;
   - Section 5: Phase 0;
   - Section 6: slices S3 and S4. S3 includes step 11b, the sharing module.

   This prompt changes the guide only where it says so.
3. In the same directory:
   - `CONCEPT.md`, all of it;
   - `DECISIONS.md`: R12, R19 to R21, R23, R25 to R27, R30, R35, R36, and R38 to R45;
   - `REQUIREMENTS.md`: every row the guide names for S3 and S4, plus `VMT-127` and `VMT-128`.
4. Evidence: `evidence/W4-CATALOG.md`, `YAML-SPIKE-2.md`, `W2-MACHINES.md`, `W9-ROLLBACK.md`, and
   `NIXOS-MERGE.md`. For sharing, read project 19's `CONCEPT.md` (Harmonia over the store) and
   project 20's `evidence/S7-keyless-secrets.md` (keyless first boot).
5. The slice 1 catalog in `devenv/devenv.nix`, the launcher in `launcher/vendomat`, the CLI in
   `src/vendomat/cli.py`, and `templates/workspace/`.
6. Memory, in `~/.claude/projects/-home-andrew-Documents-Projects-vendomat/memory/`:
   - `no-attic-harmonia-initial-install.md`
   - `simple-mental-model-over-capability.md`
   - `pure-nix-yaml-parser.md`
   - `host-btrfs-metadata.md`
   - `uv-env-leaks-into-subagents.md`
   - `delegate-to-background-subagents.md`
   - `testee-path-shadowing.md`

## The rulings this session applies

| Ruling | What it means for S3 and S4 |
| --- | --- |
| R39 | No Attic anywhere. `serve` is a Vendomat machine key in `vendomat.yaml`, on by default; `serve: false` turns it off. Every installed machine runs Harmonia from first boot and makes its signing key then. The other machines of the workspace get the substituter, the public key, `fallback = true`, and a short timeout. Secrets never enter the store. Rows `VMT-127` (two VMs here, real machines in S7) and `VMT-128`. |
| R40 (D1) | Keep the old verbs (`sync`, `path`, `check`, `push`, `bump`, `machine install`) and the `vendomat.toml` flow working. S8 removes them. The existing `front-door-e2e` and old-flow tests must stay green. |
| R41 (D2) | The template writes `devenv: follows: vendomat/devenv`. The S1 session adds the `devenv` input to Vendomat's flake. Do not edit `flake.nix` yourself. |
| R42 (D4) | A committed `.machines/NAME/facter.json` marks a machine installed, and the catalog sets `machines.NAME.vendomat.mode = "adopt-existing"`. The YAML key `mode: fresh-install` overrides it. Add a fixture for the remote `facter` phase, which writes the file before a remote install. |
| R43 (D6) | Each machine keeps `/var/lib/vendomat/generations.jsonl`, one line per apply: generation, toplevel, commit, dirty flag, and time. `apply` refuses uncommitted changes to `vendomat.yaml`, `devenv.lock`, and the hatch files unless `--dirty`. `rollback` uses clean entries only. |
| R45 (D8) | `VENDOMAT_HIDE_ADVANCED=1` hides the `advanced:` line. `explain` still shows every source. |
| R38 | Basix keys live in `basix.yaml`. The catalog builds no extension point for keys. Keep the parser a plain function that another module can import. |
| R35, R36 | No home key. No host-side module. |

New ledger rows start at 130. Rows 125 to 129 are used or skipped. Check the Vendomat and Basix
ledgers for the highest number before you add a row.

## Standing rules (short form; the guide has the full text)

- Use Gitman to open and close workspaces. Use native jj for describe, rebase, bookmark, and push.
  Never use raw `git`.
- The gate is `testee verify`. Do not call pytest, ruff, or ty directly. The machine supplies the
  Testee module. The project's checks live in `nix/testee.nix`. Add the opt-in checks
  `catalog-e2e`, `parser-fuzz`, `sharing-vm`, and `machines-vm` there.
- Run Python tools only as `devenv shell -- uv ...`. A bare `uv` writes into the wrong venv.
- Keep raw logs under `~/.local/state/vendomat/p21/<date>/s3/` and `.../s4/`. Put VM images and VM
  scratch files under `/mnt/shared/vendomat-p21/s3/` and `.../s4/`. Delete them at the end of the
  slice.
- Before each heavy build or VM run, run `btrfs filesystem usage /`. Stop when unallocated space is
  below 15 GiB. If metadata use is above 90 %, wait 60 seconds and check again; stop if it stays
  above.
- Do not run garbage collection. Use sudo only inside VMs; never use it on this host.
- Never open an upstream pull request (R34).
- Never select a disk by its kernel device name.
- The main checkout may hold another session's unlanded commit. If `jj status` there is not clean,
  do not run `jj new main`; tell the owner.

## Work beside the S1/S2 session

Each session owns its own files. Do not edit the other session's files.

| This session (S3, S4; project 24) | The S1/S2 session (project 23) |
| --- | --- |
| `devenv/`, `templates/`, `src/vendomat/`, `launcher/`, `direnv/`, the catalog, parser, command, and sharing tests, `tests/test_catalog_*`, `tests/nix/catalog.nix`, `evidence/S3-*`, `evidence/S4-*` | `devenv-dist/`, `nix/devenv-overlay.nix`, `flake.nix`, `tests/test_devenv_dist.py`, `tests/test_repo_shape.py`, `evidence/S1-*`, `evidence/S2-*` |

- Both sessions add checks to `nix/testee.nix` and may touch `AGENTS.md`, the ledger, and
  `.scratch/CURRENT.md`. Keep each edit small, and rebase right before you land.
- **One exception: the `MODULES` set in `tests/test_repo_shape.py`.** The test requires the set to
  match the module files exactly, so each new Python module and its `MODULES` entry land in the
  same commit. Edit only the lines of that set. S1 changes the root-input lines of the same file,
  so rebase right before you land, and resolve a conflict by keeping both edits.
- **The S1 module input.** S1 writes a line with the tag and its location in `.scratch/CURRENT.md`
  (project 21 section) when the tag is pushed. Until then:
  1. If the S1 session has materialized its tree (look under
     `~/.local/state/vendomat/p21/*/s1/devenv-modules`), use it as a `path:` input.
  2. Otherwise apply the S1 patch sources to a scratch copy of upstream `b904dcb5`. The sources
     are `T4-patch.diff`, `patch1.diff`, `patch2.diff`, and `0005-module-hunk.patch` (guide
     Section 3). Use the copy as a `path:` input. W4 worked the same way.
  3. Record which tree each fixture used. Rerun the fixtures on the published tag before the
     release step.
- The S2 binary is not needed for S3 or S4. Use the stock devenv 2.4.0 on `PATH`. The fixture
  that refuses a remote install (`VMT-099`, binary half) belongs to S2.

## Steps

### 0. Phase 0

Run Phase 0 from the guide (Section 5): check the tools, list the workspaces and the work that
`main` lacks, check the checksums of the S3 and S4 artifacts (parser v3, the W4 catalog, the W4
template, and the W9 apply script), and report a mismatch before you copy any file. The S1/S2
session archives the spike directories; do not archive them twice. If the archive does not exist,
make it.

### 1. S3: the catalog, the template, the commands, and sharing

Follow the guide's S3, steps 1 to 15, in a workspace named `s3-catalog`. Notes on top of the
guide:

- **Order.** Do steps 2 to 4 first: the parser, the catalog, and the template. Then do the hatch
  line, `explain`, error trimming, and `update` (steps 5 to 8). Run the `VMT-116` spike (step 9) in
  a background subagent as soon as the template exists.
- **Parser gaps.** Use a depth limit well below the measured overflow (about 800 levels), for
  example 64, and record the choice. Return value positions so that schema errors carry
  `LINE:COL` (`VMT-035`).
- **Keys.** Use the guide's key table, and add `machines.NAME.serve` (R39). The catalog sets
  `machines.NAME.vendomat.mode` from R42. It needs no `mode` value when the file is absent and no
  override is set.
- **Step 11b, the sharing module.** It is a Vendomat NixOS module, written as a plain module with
  no `specialArgs` (project 22 rule 4). It must:
  - run Harmonia;
  - make the signing key at first boot, in a systemd unit, under `/var/lib/`, never in the store;
  - publish the public key so that the other machines of the workspace can trust it. Design
    this step, record the choice, and keep it keyless at install time;
  - give clients the substituter, the key, `fallback = true`, and a short connect timeout.

  The `sharing-vm` check proves it with two VMs. Machine A makes its key at first boot and serves
  a path. Machine B substitutes the path from A and checks the signature. A machine with
  `serve: false` runs no Harmonia. If machine A is off, machine B falls back. Build the VMs with
  `build.vm` from the S1 tree, or with W2's `common/expose.nix` before then.
- **Error text.** Every error names `vendomat.yaml` and the key path, and puts the
  `vendomat.yaml:` lines first. Keep the full trace under `~/.local/state/vendomat/logs/`.
- **Step 14, the release, is an owner gate.** Pushing a tag and fast-forwarding `release` in the
  collection changes what nix-systems and vendomat-demo get on their next update, and a tag is
  permanent. Before you ask, rerun the fixtures on the published S1 tag and run
  `front-door-e2e`. Then show the owner the version, the diff since the last release, and the
  results. Push only after a yes in this session. Without a yes, land S3 on `main` and report
  "release prepared, not pushed".
- Record everything in `evidence/S3-CATALOG.md`. Close each row the guide names, with its
  evidence. Leave a row open when its proof is still missing.

Land S3 in parts if that keeps changes small: the parser and catalog first, then the commands,
then sharing. Each part needs a green `testee verify`.

### 2. S4: apply and rollback

Follow the guide's S4, steps 1 to 8, in a workspace named `s4-apply`, after S3's catalog has
landed. Notes:

- `apply` follows R43: refuse uncommitted changes unless `--dirty`, then append the record line
  after a successful switch. Write the record as root, inside the machine.
- `rollback` follows R30 and R43. The restore always ends in a commit named `rollback to REV`. A
  working-copy-only restore is refused.
- Use `/run/wrappers/bin/sudo` inside the VMs. Never run `apply` or `rollback` against this host.
- The VM fixtures (`machines-vm`) run W2 T1 and W9 R1 to R6 through the real commands, as the
  guide lists them. Also prove that `apply` records a line and that `rollback` skips dirty entries.
- Record everything in `evidence/S4-APPLY-ROLLBACK.md`.

### 3. Parallel work

- Delegate heavy work to background Sonnet subagents: the parser fuzz corpus, the `VMT-116`
  spike, `catalog-e2e`, `sharing-vm`, and `machines-vm`. The main agent writes the briefs, checks
  each result against its logs, records the evidence, and lands the change.
- Give every subagent these rules in its brief: the btrfs rule, the `/mnt/shared` rule, no
  garbage collection, no sudo on the host, no Attic, no upstream contact, `uv` only through
  `devenv shell -- uv`, logs only under the slice's log directory, and the file ownership table
  above.
- Run at most two VM fixtures at once.

## Stop and ask when

- An artifact checksum does not match.
- A ruling and the code disagree, or a key needs a type that no ruling covers.
- A change would break the old flow (R40) or `front-door-e2e`.
- `testee verify` is red, and the fix is not obvious.
- You are about to push a Vendomat tag or move `release` (S3 step 14).
- You would need to edit a file that the S1/S2 session owns, beyond the `MODULES` set.
- The btrfs limits are hit.
- A rebase conflicts, or another session's work blocks a landing.
- Anything would touch Attic, a secret, a real disk, or this host's system profile.

## Report at the end

Write the report to `.scratch/projects/24-vendomat-catalog-and-machines/REPORT.md`, land it, and
give the owner the same text. Keep it short:

- the `main` commits for S3 and S4, and the Testee result for each;
- the opt-in check results: `catalog-e2e`, `parser-fuzz`, `sharing-vm`, and `machines-vm`;
- which S1 tree each fixture used, and whether the fixtures were rerun on the published tag;
- the `VMT-116` answer;
- the release state: pushed, or prepared and not pushed;
- the ledger rows closed and still open, and any new rows (130 onward);
- disk use before and after, and the files deleted from `/mnt/shared`;
- open items for the owner.

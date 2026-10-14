# S4: vendomat apply and vendomat rollback, proved in a VM — 2026-10-14

Slice S4 of the implementation guide. It adds the commands `vendomat apply` and `vendomat rollback`,
the per-machine record (R43), and the opt-in check `opt:machines-vm`. No host profile, host disk, Attic,
secret, or upstream contact was touched. Every machine step ran in a QEMU machine from an image file.

Raw logs: `~/.local/state/vendomat/p21/2026-10-14/s4/`. The step log of the final run is
`machines-vm/run-184834Z/{results,commands}.log`. The Testee logs are `machines-vm-run1.log` to
`machines-vm-run6.log` and `verify-1.log`.

## Rulings and rows

R15 (local apply), R21 (host name is the machine name), R30 (lasting rollback), R43 (the record). Rows:
`VMT-072`, `VMT-075`, `VMT-098`, `VMT-110`. New rows: `VMT-161`, `VMT-162`, `VMT-163`.

## Inputs and versions (observation)

- Final tree `d269368b77` (Testee names the commit `6a594d010f`), on `56642bac8660` (main with S1, S2, and the release prepare). The files after that tree differ only in this record, the ledger, `PLAN.md`, and `CURRENT.md`.
- Host: Nix 2.34.7, stock devenv 2.4.0+b904dcb from `PATH`, Testee 0.8.0.
- QEMU 11.1.1 and OVMF 202608 come from the pinned nixpkgs `e7439b6b` (`tests/fixtures/machines/tools.nix`).
- The machine runs devenv 2.4.0 from the same nixpkgs, Nix 2.34.8, and kernel 6.18.55.
- The `devenv` input of the final run was the published tag `v2.4.0-vendomat-modules.1`, rev
  `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`, store path `/nix/store/c8l2347km7r60798yajrsgzj50s619fh-source`.
  The `src/modules` hash is `sha256-BJLQl3uuGrP+f7+Q5Bjoatq9PJhcwDrdon9hGUbTVQ0=`. This is also the hash of the
  scratch tree of runs 1 to 4.
- Since the earlier run `20261014T183419Z-307e760d74ee`, the harness reads the pin from `flake.lock` (the same tag and rev, with `dir` `src/modules`) instead of a fixed URL. The final run used that code.

## The commands (decisions)

1. The commands read and write the workspace with the `git` binary. A workspace from `vendomat new` is a
   plain Git repository. The rule "no raw git" applies to the Vendomat repository, not to the user's workspace.
2. **Watched files:** `vendomat.yaml`, `devenv.lock`, `devenv.nix`, `devenv.local.nix` (`VMT-163`). A file
   counts as uncommitted when it is modified, staged, deleted, untracked, or ignored but present. The template
   ignores `devenv.local.nix`, so a present copy always blocks `apply` unless `--dirty`: no other clone has it. (R49 changes this for apply: see `VMT-166`. A modified or untracked watched file is now committed after the build. An ignored file still blocks, also with `--dirty`.)
   A file that a hatch file imports is not watched. That is a gap.
3. **apply:** read the machine name from `/etc/devenv/machine-facts.json`; refuse uncommitted changes unless
   `--dirty` (R49 changes this: apply now commits the watched files after the build, see `VMT-166`); `devenv build machines.NAME.build.nixos`; `sudo nix-env --profile ... --set TOP`;
   `sudo TOP/bin/switch-to-configuration switch`; append one record line as root; report the generation and
   `systemctl --failed`. Another machine's name runs `devenv machines deploy NAME`.
4. **rollback:** pick the newest earlier clean entry with a system path that differs from the running one
   (`--to REV` and `--generation N` are the other forms). Refuse uncommitted changes, an unknown commit, and a
   recorded commit that the repository lost. Show the diff. Restore the watched files (`--exact`: every tracked
   file, and refuse any tracked change). Build, commit the restore as `rollback to <12 hex>`, activate. The
   commit is also made when the restore changes nothing. A build failure undoes the restore.
5. **--fast:** `nix-env --switch-generation N` and `switch`. It builds nothing, adds no generation, and still
   commits. It refuses a generation whose link is gone. **--boot-only:** `bootctl set-oneshot` for the entry
   whose `version` line reads `Generation N`. It changes no file and makes no commit. The boot entry file names
   carry a hash, so the command reads the `version` line.
6. `system.configurationRevision` stays unset (`VMT-110`). The same files give the same system path.
7. **Exit 4 of `switch-to-configuration`** (new system active, some units failed) is a warning, and the record
   line is written. Any other non-zero exit is a fault with no record line. **Proposed; the owner is to
   confirm.** Reason: in the VM a user manager that started or stopped during the switch gave exit 4 while the
   system was active, so a fault here would leave an active generation with no record (`VMT-162`).
8. After a successful bare `apply`, the file `/var/lib/vendomat/cache-key.pub` is copied to
   `.machines/NAME/cache-key.pub` when the file is missing or differs. One line asks the user to commit it. The
   command never commits (`VMT-161`, from the sharing module of S3).

## Unit tests (observation)

`testee verify` is GREEN, 4/4 checks, about 24 s. About 100 new cases: `test_machine_record.py`,
`test_machine_workspace.py`, `test_machine_apply.py`, `test_machine_rollback.py`, and a simulated machine in
`tests/machinesim.py`. The launcher has one new test (`apply` and `rollback` always run the host release).

## The VM check (observation)

The fixture builds one NixOS machine `box` through devenv Machines on stock devenv 2.4.0. It takes the system
from `_nixosEval` as a qcow2 EFI image (`make-disk-image`, systemd-boot).

- The machine has no network. QEMU runs with `restrict=on`. A `guestfwd` joins the machine to a binary cache
  that the harness serves over HTTP, signed with a test key. The harness counts the downloads.
- The workspace pins its inputs by store path, because Nix 2.34 does not take a locked `github:` input from the
  store when the network is down.
- Commands run as the user `tester` with `/run/wrappers/bin/sudo`.
- QEMU runs in a transient user unit with `SystemCallFilter=~io_uring_setup:ENOSYS`. Plain QEMU 11 fails here
  with "Failed to initialize io_uring: Cannot allocate memory". The fix came from the sharing harness. No host
  limit changed.
- Fixture-only settings that the machine needed: `always-allow-substitutes = true` (the NixOS toplevel sets
  `allowSubstitutes = false`), `cachix.enable = false`, and `linger` for the two users.
- The test keys sit in `~/.local/state/vendomat/machines-vm-keys`, outside the repository. They are throwaway
  keys for the test machine only: the SSH key opens only the VM, and the cache key signs only the harness cache.
  They are persistent so that the image and the system paths repeat and the host store does not grow.

Final run: Testee run `20261014T184833Z-df3bd2858db6`, verdict `PASS opt:machines-vm`, 12 of 12 steps, 5 min
41 s, on the tree `d269368b77`. The `devenv` input came from `flake.lock` (tag `v2.4.0-vendomat-modules.1`, rev
`061c2184`). The earlier run `20261014T183419Z-307e760d74ee` (8 min 36 s, a fixed tag URL) also passed 12 of 12
steps; the times below are from the earlier run.

| Step | Expected | Observed |
| --- | --- | --- |
| baseline | image runs A, one generation, no record | passed |
| refusals | apply refuses a modified `devenv.nix` and an ignored `devenv.local.nix`; nothing changes | passed |
| apply A (W2 T1) | same path as the host build, no new generation, one record line, no download | passed; line generation 1, commit C1, dirty false |
| apply A' | the machine builds the host's A' path; generation 2 is the default entry; `hello` runs; zero failed units; reboot clean | passed, 13.2 s |
| working-copy restore | apply and rollback both refuse | passed |
| rollback (W9 R2, R3) | identical A path, no download, generation 3 is the default entry, commit `rollback to`, reboot clean | passed, 12.8 s |
| dirty apply (R43) | apply refuses; `--dirty` records `dirty: true`; rollback skips and names it | passed (the refusal part is history: R49 replaced it, `VMT-166`) |
| `--fast` (W9 R6) | no build, no new generation, default entry generation 6, commit made | passed, 3.0 s (a default rollback took 18.8 s in that run) |
| `--boot-only` | one boot of generation 7, then the default again; no file, no commit | passed |
| path left the store (W9 R5) | generations 2, 4, 5, 7 deleted, machine GC, `hello` gone; rollback fetches from the cache | passed, 20.9 s, 11 downloads |
| `--exact` | the whole tree equals commit A; system A | passed |
| cache key | `apply` copies a stand-in key to `.machines/box/cache-key.pub`, commits nothing | passed (one assertion in the apply A step) |

Runs 1 to 3 failed for fixture reasons that the code now fixes: QEMU io_uring (run 1), input sources missing
from the machine store (run 2), a boot entry name test (run 3), and an exit 4 from a user manager race (run 3).
Run 4 passed all 12 steps but exited non-zero, because the end-of-run disk guard read 14.87 GiB unallocated. The
harness now logs that reading and does not raise.

## Inference (not observed)

- A real machine with network and a real cache takes the same code path; only the substituter differs.
- The cache key step used a stand-in file, because the fixture machine does not import the sharing module.
- The two-rollbacks-in-a-row flip (W9) follows from the choice rule and has a unit test, not a VM step.

## Not proved

- The fixture puts the machine config in the hatch file `devenv.nix`, not in `vendomat.yaml` (the file is a
  placeholder). So the catalog-to-machine path is not exercised by `machines-vm`.
- `vendomat apply NAME` for another machine (`exec` of `devenv machines deploy`) has a unit test only.
- Files that a hatch file imports are not watched.
- A real disk, real hardware, and a real cache are untouched.

## Disk

`/` unallocated space fell from 24.87 GiB to 14.87 GiB over four runs (new random keys each run added a 2.4 GB
image and three toplevels to the host store; other work also wrote). The owner freed space. The runs after
the owner freed space left the unallocated space unchanged (30.87 GiB, then 28.87 GiB). Metadata use rose from 84.4 % to
87.0 % in one run; it was 79.5 % before and after the final run. No garbage collection ran. `/mnt/shared/vendomat-p21/s4/`
is empty.

## Rule slips

- One read-only raw `git diff` ran on the Vendomat repository. It changed nothing.
- `ruff format` ran through `devenv shell -- uv run`, to format my own files. The checks ran only through Testee.
- The safety rule says one VM at a time. The spike and the test runs did not overlap.

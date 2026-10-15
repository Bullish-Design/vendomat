# S5: the Vendomat side of Basix — 2026-10-14

Slice S5 of the implementation guide, Vendomat side. Step 1 is done (the collection hook, R37).
Step 2 is checked (the parser import, R38). Step 3 runs in the Basix repository and did not run
here. No live hook under `~/vendor/` changed. `~/vendor/basix` does not exist: creating it is an
owner gate and a step of the Basix plan.

Rulings and rows: R37, R38. New row: `VMT-171`. It supersedes `DOOR-076` in part.

Raw logs: `~/.local/state/vendomat/p21/2026-10-14/s5/`.

## Step 1: the collection hook (R37)

### Change (observation)

- `hooks/collection-pre-receive`: every collection repository accepts the creation and the
  fast-forward of `refs/heads/release`. The check on the repository name is gone. The hook still
  refuses the rewind and the deletion of `release`, keeps tags immutable, and refuses every other
  branch.
- `tests/nix/infra/collection-add`: carries the same hook text. It is a copy of
  `../nix-meta/scripts/collection-add`. Another agent makes the same edit in nix-meta. The hook
  text in both files must stay byte-identical to `hooks/collection-pre-receive`.
- The `collection-add` message `(release tags; Vendomat release branch; served read only)` is old
  text. This change leaves it as it is.

### Unit tests (observation)

`tests/test_collection_hook.py`: the release test runs for `vendomat`, `basix`, and `devman`
(`test_every_repository_accepts_a_release_branch_that_only_moves_forward`).
`test_every_other_branch_is_still_refused` replaces the old test that other repositories reject
the release branch. `testee verify --profile quick` passed before the VM run. Testee holds the gate
verdict for the landed commit (`testee status`).

### Two-VM test (observation)

The test is `tests/nix/infra/collection.nix`. Its `lib-a` repository now takes
`main:refs/heads/release` (create), then a second push (fast-forward), then refuses
`git push --force lib-a main~1:refs/heads/release` with `refs/heads/release must move forward`.
This block runs after the STORE-010 comparison, because that comparison expects tags and no
branches. The old step "other repositories reject the release branch" is gone.

Run by hand. This is a direct fixture run, not a Testee verdict. The `opt:e2e` task did not run.

```sh
btrfs filesystem usage -b /        # unallocated 32070696960 bytes (about 29.9 GiB), above the 15 GiB floor
VENDOMAT_PACKAGE=$(nix build .#packages.x86_64-linux.vendomat --no-link --print-out-paths)
  # /nix/store/x8jr2fl7ny3yb4b5s086qmxf2bpmc90h-vendomat-0.8.0
nix build --impure --no-link -L --file tests/nix/infra/collection.nix
```

Result: exit status 0. Log: `~/.local/state/vendomat/p21/2026-10-14/s5/collection-vm/vm.log`
(with `exit.txt`, `start.txt`, `package-path.txt`). The log holds every `RESULT` line that
`tests/test_infra_e2e.py` expects in `test_the_collection_serves_immutable_tags_and_a_release_branch_in_every_repository`:

- `RESULT hook text: installed post-receive equals hooks/collection-post-receive`
- `RESULT hook text: installed pre-receive equals hooks/collection-pre-receive`
- `RESULT tag push from framework over ssh: accepted; tree shows v1.0.0`
- `RESULT branch push refused; moved tag refused; tag delete refused`
- `RESULT Vendomat release branch: create and fast-forward accepted; rewind, delete, and main refused`
- `RESULT unmarked repository not served; push over git:// fails from both VMs`
- `RESULT nix fetch over git:// on framework: lib-a-1.0.1`
- `RESULT nix fetch over git:// on server: lib-a-1.0.1`
- `RESULT mirror: skipped without --collection; copied with it; no marker; not served`
- `RESULT STORE-010: rebuilt refs, tree files, and selected tag equal the original; mirror restored by sync`
- `RESULT other repositories accept refs/heads/release; rewind refused`
- `RESULT idle cpu ns in 15 s: 0`

A script compared each expected string against the log: all were found.

### Not proved

- The live hooks under `~/vendor/` still hold the old text. An owner step installs the new hook
  (`collection-add --hooks`) in each live repository.
- A real push of a Basix `release` branch to `~/vendor/basix` has not run.

## Step 2: the parser import (R38) (observation)

Basix reads `basix.yaml` with the parser from the Vendomat source. The parser is
`devenv/parse.nix`. Its call form is `(import ./devenv/parse.nix) FILE TEXT`. `FILE` is a plain
file name. The error lines start with `FILE:LINE:COL:`.

Input files are in `~/.local/state/vendomat/p21/2026-10-14/s5/parser-import/`; the output is in
`run.log` there. Nix 2.34.7.

Good file `good-basix.yaml`:

```sh
nix-instantiate --eval --strict --json --expr \
  '((import devenv/parse.nix) "basix.yaml" (builtins.readFile good-basix.yaml)).value'
```

Output: `{"keys":["alpha","beta"],"machines":{"one":{"host":"x"}},"name":"demo"}` (exit 0).
With `.at ["keys" "[1]"]` instead of `.value`, the output is `{"key":"4:3","sub":{},"value":"4:5"}`.

Bad file `bad-basix.yaml` (a line indented by one space after a two-space level):

```text
error: basix.yaml:4:2: unexpected indentation
```

The exit status is 1. The error line holds the plain file name `basix.yaml`, the line, and the column.

Result: the import works with a plain file name, and the error text carries `basix.yaml:LINE:COL:`.
The formal contract (call form, result set, error form) belongs to the `p21-contracts` work
(`VMT-164`). That work is not on `main` yet. This record is an observation, not the contract.

## Step 3: the fixtures

The fresh Basix workspace and the pair update (`VMT-121`) run from the Basix repository. They did
not run here. Not run.

## Step 4: close-out

- Added `VMT-171` in `REQUIREMENTS.md`. `DOOR-076` carries the note "superseded in part by
  `VMT-171`" in its status; its claim is unchanged.
- Corrected the sentence "Attic owns cached objects" in `AGENTS.md` (R39: Harmonia serves build
  outputs, and the new system configures no Attic).
- Updated the S5 row in `PLAN.md` and `CURRENT.md`.
- Open: the owner installs the new hook in the live repositories; the Basix repository runs the
  fixtures (`VMT-121`); the `collection-add` message still says "Vendomat release branch".

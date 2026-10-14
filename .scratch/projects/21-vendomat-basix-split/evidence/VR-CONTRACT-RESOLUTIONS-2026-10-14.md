# Vendomat contracts for the Basix consumer — 2026-10-14

## Scope and inputs

This record covers VR1 to VR7 requested by Basix, except VR5. VR5: not done; Basix keeps its own hint
(`../basix/.scratch/projects/002-concept-review/VENDOMAT-REQUESTS.md`). It records fixture,
real-consumer, and disposable VM observations for the `p21-contracts` change. These results do not claim that this change
has been released, that Basix B5 has integrated the changes, or that S7 or
real-hardware acceptance has passed.

Vendomat `main` was at `c36cd071` before this change; S1 to S4 were already complete there, and
v0.8.0 was already published. The first audit runs used the source tree
`25bd25c793cd3ba0630fef89d844284e890c4f86` (Testee capture commit `447980a650`), except the first
passing `opt:machines-vm` run `20261015T010946Z-a99af20c00cc`, which used tree `af4016c8`
([RESEARCH-REPORT](RESEARCH-REPORT-2026-10-14.md) lists the tree of each run). The review of
2026-10-15 changed the code and the tests, so the run IDs below are the runs of the final tree
`888e61e5fe` (see "Review fixes"). Inputs recorded by the VM run:

- Testee 0.8.0; Nix 2.34.7; devenv 2.4.0; QEMU 11.1.1.
- Module input tag `v2.4.0-vendomat-modules.1`, revision
  `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`, source hash
  `sha256-BJLQl3uuGrP+f7+Q5Bjoatq9PJhcwDrdon9hGUbTVQ0=`.
- Nixpkgs revision `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`, narHash
  `sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=`.
- VM disks, state, and scratch were under `/mnt/shared/vendomat-p21/`.

Focused checks were run from this workspace root with `testee verify opt:machines-vm`,
`testee verify opt:sharing-vm`, `testee verify opt:catalog-eval`,
`testee verify opt:catalog-devenv`, `testee verify opt:catalog-e2e`,
`testee verify opt:parser-fuzz`, and `testee verify opt:front-door-e2e`. The passing Testee run IDs and reports are listed by contract below. An opt-in result is not the
required repository gate. The final required gate is `testee verify` run 20261015T020046Z-7cb37a27656d on tree
`888e61e5fe`: 4 of 4 required checks passed. Its raw report is
`/home/andrew/.local/state/testee/repos/e6fc47612c7a1650/slots/p21-contracts-63e0515c/runs/20261015T020046Z-7cb37a27656d/report.json`.

## Results

| Request | Expected | Observed | Limits and primary evidence |
| --- | --- | --- | --- |
| VR1 — parser consumer | Basix can import the published parser, parse `basix.yaml`, and read values and source positions. | PASS against published Vendomat `v0.8.0`, revision `e5923a8f5c0f0f81f3c0926dc2cf32887f6f6ba3`, prefetched with NAR hash `sha256-uMjKMWlHTnNFaW9oQBlyTsOU9+RqmLf4R8EWsCz7UtA=`. Evaluation returned profile `console` at key `3:5` / value `3:14`, and disk `/dev/disk/by-id/virtio-basix-demo` at key `4:5` / value `4:11`. | A real Basix-style consumer of the published parser, not B5 product integration. Exact commands and inputs: `/home/andrew/.local/state/basix/vr1/commands.log`; result: `/home/andrew/.local/state/basix/vr1/results.log`; fixture files are beside those logs. |
| VR2 — tracked template source | `vendomat new` and `vendomat update` use the tracked imported template; update retains authored lines and supplies required `follows` lines. | PASS. `tests/test_catalog_devenv.py::test_basix_consumer_uses_the_imported_template_for_new_and_update` exercises a Basix-style consumer, authored input lines, `new`, and `update`. `opt:catalog-devenv` run `20261015T020335Z-13edefd456aa`, `opt:catalog-e2e` run `20261015T020416Z-37c32e272bdb`, and `opt:front-door-e2e` run `20261015T020737Z-15573148247d` passed. | Consumer fixture uses a local source copy to exercise the imported tracked template; no Basix product workspace has adopted it yet. Testee reports are under `/home/andrew/.local/state/testee/repos/e6fc47612c7a1650/slots/p21-contracts-63e0515c/runs/`. |
| VR3 — apply configuration commit | Per R49, build first; commit only allowlisted watched configuration; refuse present ignored watched files unless force-added; `--dirty` skips the config commit and records dirty HEAD; build failure does not commit, activate, or record. | PASS. Unit coverage checks build → config commit → activation order, force-added ignored configuration, `--dirty`, preservation of unrelated staged files, the allowlist, untracked and deleted watched files, a subdirectory workspace, the committer check, and an edit during the build. `opt:machines-vm` run `20261015T021316Z-03a2e2c40bc2` passed all 12 cases. The VM observed a build failure with config uncommitted and the machine unchanged, ignored-config refusal without machine change, successful clean apply, dirty apply, and dirty-generation rollback skipping. | Owner ruling R49 is the policy. The proof is a disposable QEMU VM and unit tests, not a host-system activation. Raw VM evidence: `/home/andrew/.local/state/vendomat/p21/2026-10-15/s4/machines-vm/run-021316Z/{commands.log,results.log,serial.log}`. The harness deleted the VM files. An earlier passing run (tree `af4016c8`) left `run-010947Z`. |
| VR4 — trim workspace file errors | A failed real workspace evaluation with a `basix.yaml` fault shows the file and line before the Nix trace. | PASS. `tests/test_catalog_devenv.py::test_a_basix_yaml_fault_is_trimmed_after_a_real_devenv_evaluation` runs a real `devenv eval` against malformed `basix.yaml`; the leading fault is `basix.yaml:3:14: flow style is not accepted`. Unit and launcher fixtures cover the trim. | The eval is a disposable consumer workspace and not a production Basix command. Testee report: `/home/andrew/.local/state/testee/repos/e6fc47612c7a1650/slots/p21-contracts-63e0515c/runs/20261015T020335Z-13edefd456aa/report.json`; code and fixture: `tests/test_catalog_devenv.py`, `tests/fixtures/trim/basix-yaml-faults.txt`. |
| VR5 — generic hint lines | Any module can add hint lines to the shell and to `explain`. | Not done; Basix keeps its own hint. | No Vendomat change. Request: `../basix/.scratch/projects/002-concept-review/VENDOMAT-REQUESTS.md`, section VR5. |
| VR6 — machine programs | `machines.NAME.programs` validates nixpkgs package attributes and maps them to that machine's NixOS `environment.systemPackages`; top-level `programs` remains separate. | PASS. Schema tests accept `ripgrep` and `hello` under a machine while top-level `jq` remains a workspace package. The real devenv consumer reads `ripgrep` under `machines.learner`'s system packages and `jq` at workspace level; an unknown machine package fails with its YAML line and key path. `opt:catalog-eval` run `20261015T020244Z-a4906cc87cc4` and `opt:catalog-devenv` run `20261015T020335Z-13edefd456aa` passed. | Evaluation and real-consumer fixture coverage; no installed Basix system. Testee reports are under the state path listed for VR2; source tests are `tests/test_catalog_module_nix.py` and `tests/test_catalog_devenv.py`. |
| VR7 — sharing network boundary | Per R50, `trustedInterfaces` defaults to `[]`; serving opens TCP 5000 only on explicitly trusted interfaces; unmarked interfaces and `serve = false` stay closed. | PASS in the production `devenv/sharing.nix` module. In `opt:sharing-vm` run `20261015T020843Z-26a84e8478ee`, alpha opened loopback and trusted `eth1` while untrusted `eth2` stayed closed; beta (`serve = false`) ran no Harmonia/key service and refused port 5000; gamma (`serve = true` with no `trustedInterfaces` key) left `eth1` closed. | Owner ruling R50 selects explicit trust and closed unmarked interfaces. Disposable production-module VMs, not S7 or real-network proof. Raw logs: `/home/andrew/.local/state/vendomat/p21/2026-10-15/s3/sharing/run-020843Z/`. The harness deleted the VM files. An earlier audit run (`20261015T011750Z-9987df53bdc9`, tree `25bd25c7`) left `run-011751Z`. |

## Owner rulings

R49 records the apply-time configuration-commit policy that the owner selected as an option label. R50 records the
`trustedInterfaces` policy that the owner selected as an option label. The details that the question
did not state are implementer choices (see `DECISIONS.md`, R49 and R50). The scratch VR7 probe at
`~/.local/state/vendomat/p21/2026-10-14/vr7/` remains proposal evidence only; the production-module
VM above is the implementation proof. Neither ruling authorizes S7 or physical-disk writes.

## Recorded failure and recovery

The first five `opt:machines-vm` attempts failed and remain failures. Their diagnoses and fixes are
recorded in [RESEARCH-REPORT-2026-10-14](RESEARCH-REPORT-2026-10-14.md). The fresh run on tree `af4016c8`
passed all 12 cases, and the final run on tree `888e61e5fe` passed all 12 cases. Earlier red results
were not overwritten or counted as passes.

## Review fixes, 2026-10-15

Two reviews of the change found the faults below. Each was checked against the code before the fix.
Each fix has a test. The final runs on tree `888e61e5fe` are listed under "Final runs".

| Finding | Fix | Test |
| --- | --- | --- |
| `machines: foo` gave a raw Nix type error, not `vendomat.yaml:1:11: machines must be a map, found "foo"`, because `machineProgramFaults` mapped over `raw.machines` with no `isAttrs` guard. | `devenv/devenv.nix` walks `raw.machines` only when it is a map. | `test_machines_that_is_not_a_map_names_the_file_and_position` (`opt:catalog-eval`), `test_a_machines_key_that_is_not_a_map_fails_real_devenv_evaluation_with_the_yaml_position` (`opt:catalog-devenv`). |
| Staged content equal to HEAD (`MM` reverted, `AD`) made `git commit --only` exit 1 after the build. | `commit_watched` runs `git diff --cached --quiet HEAD -- PATHS` after the add. With no difference it returns HEAD and makes no commit. | `test_a_watched_path_that_equals_head_makes_no_commit`, `test_apply_makes_no_commit_when_the_staged_change_was_reverted`. |
| `git status --porcelain` names paths from the repository top. A workspace in a subdirectory saw no change, and apply recorded a clean commit for an unbuilt state (R43). A staged rename between watched files lost a name. | `watched_changes` reads `git status --porcelain -z`, strips `git rev-parse --show-prefix`, and reports both names of a rename. `tree_changes` (the `--exact` check of rollback) now lists only the workspace directory, the same scope as its restore. `commit_restore` uses `watched_changes`, so it has the fix. The old name of a staged rename is not staged again, because `git add` stops on a pathspec that matches nothing. | `test_a_workspace_in_a_subdirectory_sees_its_own_changes_and_not_those_of_the_top`, `test_a_subdirectory_workspace_commits_only_its_own_watched_files`, `test_a_staged_rename_between_watched_files_reports_both_names`, `test_a_subdirectory_rename_reports_both_names_without_the_prefix`, `test_exact_lists_only_the_tracked_changes_of_the_workspace_directory`, `test_apply_from_a_subdirectory_workspace_commits_the_change`. |
| A missing committer made the commit fail after the build. | `apply` runs `git var GIT_COMMITTER_IDENT` before the build when it will commit. It refuses with a clear message and builds nothing. Git hooks stay on (no `--no-verify`). A detached HEAD is not refused, because a jj-colocated checkout is always detached. | `test_apply_refuses_before_the_build_without_a_committer`, `test_apply_does_not_need_a_committer_when_it_commits_nothing`, `test_apply_works_on_a_detached_head`. |
| A watched file edited during the build was committed without being built. | `apply` hashes the watched files and HEAD before the build and compares just before the commit. A difference refuses: no commit, no activation, no record. | `test_a_watched_file_edited_during_the_build_is_not_committed_or_activated` (with and without `--dirty`), `test_the_fingerprint_changes_with_a_watched_file_and_with_head`. |
| `machines.NAME.programs` resolved against the workspace `pkgs`, not the machine's. | The machine `nixos` module is the function `{ pkgs, ... }:`. It resolves the names with the machine's `pkgs`. The workspace `pkgs` still validates the names for the error messages. | `test_machine_programs_resolve_with_the_package_set_of_the_machine` (`opt:catalog-eval`, with a stub overlay, and `opt:catalog-devenv`, with a real `nixpkgs.overlays` entry). The S1 `deferredModule` accepts the function form: `opt:catalog-devenv` passed. |
| With `networking.firewall.enable = false`, port 5000 is open on every interface and `trustedInterfaces` means nothing. | `devenv/sharing.nix` adds a NixOS warning for `serve && !firewall.enable`. | `test_a_serving_machine_with_the_firewall_off_gets_a_warning`, and the `noFirewall` fact of `test_a_key_that_is_not_committed_gives_no_peer_entry`. |
| `explain` had no mapping for `machines.NAME.programs`. | `devenv/explain.nix` maps it to `machines.NAME.nixos.environment.systemPackages` with `merge = true`, and lists `vendomat.yaml` as a source of every merged key. | `test_explain_maps_machine_programs_to_the_machine_system_packages`, and the extended `test_explain_reads_the_real_option_tree_and_names_the_files`. |
| `networking.firewall.allowedTCPPorts = lib.mkForce [ 22 ]` in the VM fixture hid any global 5000. The `untrustedPorts == []` asserts were vacuous, because nothing configures `eth2`. | The fixture no longer forces the list; the tests assert that 22 (from `services.openssh`) is present and 5000 is not. The `untrustedPorts` facts are gone. The VM curl probes of `eth2` stay as the proof. The docstring says three VMs. | `test_alpha_serves_only_on_its_marked_interface`, `test_unmarked_server_interface_stays_closed`. |

Other changes: the dead `commit = workspace.head(root)` before the build is now an explicit precondition
with a comment; the switch-failure text says "The configuration commit stays; apply again to retry."
(D9; `test_a_config_commit_stays_when_activation_fails_later`); apply commits an untracked and a deleted
watched file (`test_apply_commits_an_untracked_watched_file`, `test_apply_commits_a_deleted_watched_file`);
`tests/nix/infra/collection-add` is now a byte copy of `../nix-meta/scripts/collection-add` (nix-meta
`main` `ee768f74`).

Gap, not fixed: the catalog has no key for `trustedInterfaces` (`VMT-172`). No ruling covers it.

Limit of the committer check (inference): a Git hook that fails (for example `pre-commit`) still fails
the commit after the build. The check cannot see hooks, and the fix keeps hooks on by design. The
build is then wasted, apply activates nothing, and the configuration stays uncommitted.

## Final runs

The final runs on tree `888e61e5fe`:

| Check | Run | Result | Tree |
| --- | --- | --- | --- |
| `testee verify` (required gate, 4 checks) | `20261015T020046Z-7cb37a27656d` | GREEN, 4 of 4 | `888e61e5fe` |
| `opt:catalog-eval` | `20261015T020244Z-a4906cc87cc4` | passed, 113 tests | `888e61e5fe` |
| `opt:catalog-devenv` | `20261015T020335Z-13edefd456aa` | passed, 16 tests | `888e61e5fe` |
| `opt:catalog-e2e` | `20261015T020416Z-37c32e272bdb` | passed, 21 tests | `888e61e5fe` |
| `opt:front-door-e2e` | `20261015T020737Z-15573148247d` | passed, 1 test | `888e61e5fe` |
| `opt:sharing-vm` | `20261015T020843Z-26a84e8478ee` | passed, 12 tests (three VMs) | `888e61e5fe` |
| `opt:machines-vm` | `20261015T021316Z-03a2e2c40bc2` | passed, 12 tests | `888e61e5fe` |

Tree `888e61e5fe` holds the final code and tests. The final tree of the change differs from it only
in these records (the run IDs). A last `testee verify` ran on the final tree before the merge. Before
each VM check, `btrfs filesystem usage -b /` showed 32070696960 bytes unallocated (about 29.9 GiB;
the limit was 15 GiB). Raw VM logs: `~/.local/state/vendomat/p21/2026-10-15/s3/sharing/run-020843Z/`
and `~/.local/state/vendomat/p21/2026-10-15/s4/machines-vm/run-021316Z/`. The harnesses deleted the VM
images under `/mnt/shared/vendomat-p21/`. Raw Testee wrapper logs:
`~/.local/state/vendomat/p21/2026-10-15/contracts-merge/`.

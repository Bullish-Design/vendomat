# S3: the catalog, the template, the commands, and the sharing module — 2026-10-14

<!-- Written by a Sonnet subagent for the main agent, from the session facts the main agent supplied and from the raw logs and Testee records named below. Every log path in this file was checked with `ls`. Observations come from logs and Testee records. Inferences carry the word "inference". -->

Slice S3 of the [implementation guide](../IMPLEMENTATION-GUIDE.md), run as project 24
(`.scratch/projects/24-vendomat-catalog-and-machines/KICKOFF.md`). Raw logs are under
`~/.local/state/vendomat/p21/2026-10-14/` (`LOGS` below). Nothing in this file is a release. See
"Release state".

## Result

| Part | Commit on `main` | Required gate | Opt-in tasks |
| --- | --- | --- | --- |
| Testee 0.8 conversion | `bd7baeb06b1a` | GREEN 4/4, epoch 2 | none |
| S3 part 1: parser, catalog, template, curated corpus | `ccd419ddee93` | GREEN 4/4, epoch 2 | `opt:catalog-eval` PASS (85 tests) |
| S3 part 2: hatch line, `explain`, trim, `update`, launcher | `b43d23e6b9cb` | GREEN 4/4, epoch 2 | `opt:catalog-eval` PASS (85), `opt:catalog-devenv` PASS (7), `opt:front-door-e2e` PASS (1) |
| `opt:parser-fuzz` and `opt:catalog-e2e` | `b575e4f424b0` | GREEN 4/4, epoch 2 | `opt:parser-fuzz` PASS (16), `opt:catalog-e2e` PASS (21 of 21, no skips) |
| Sharing module and `opt:sharing-vm` | `845172f0768f` | GREEN 4/4, epoch 2 | `opt:sharing-vm` PASS (10 tests) |
| Catalog wiring of the sharing module | `79e46310ef30` | GREEN 4/4, epoch 2 | `opt:catalog-eval` PASS (93), `opt:catalog-devenv` PASS, `opt:catalog-e2e` PASS |

`testee status -r COMMIT` (Testee 0.8.0, run on 2026-10-14 for this record):

```
bd7baeb06b1a  GREEN  tree 9510a4265f (commit bd7baeb06b)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
ccd419ddee93  GREEN  tree eb852374fe (commit ccd419ddee)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
b43d23e6b9cb  GREEN  tree 4ccaf99f35 (commit b43d23e6b9)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
b575e4f424b0  GREEN  tree c5bfb89629 (commit b575e4f424)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
845172f0768f  GREEN  tree 56fd040e2d (commit 845172f076)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
79e46310ef30  GREEN  tree 54b47faf7b (commit 79e46310ef)  4/4 checks  epoch 2  testee 0.8.0 (kfhxs4c)
```

`testee show -r 845172f0768f` lists `check:lint`, `check:format`, `check:types` and `test:full` as
PASS (run `20261014T175348Z-cf8cc4dcb781`). Its `test:full` junit file reads 572 tests, 0 failures,
0 errors, 193 skipped (the skips are the opt-in tests). Time 15.3 s.

Later commit: `79e46310ef30` wires the sharing module into the catalog (section "Catalog wiring of
sharing"): GREEN 4/4, tree `54b47faf7b`.

Step of the guide not done in S3: step 14 (release, an owner gate).

## Inputs and tree

Observed on 2026-10-14.

| Input | Value |
| --- | --- |
| Repository base | `main` = `79e46310ef30` (this record is a child of it); the fixtures ran on the commits listed above |
| Testee | 0.7.0 at the start, 0.8.0 from the conversion on (`testee --version` read `testee 0.8.0` when this record was written) |
| devenv | stock `2.4.0+b904dcb`, `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0/bin/devenv` |
| Nix | 2.34.7 |
| nixpkgs for fixtures | NixOS/nixpkgs `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (the pin of `flake.lock`) |
| Pins in the front-door gate | `github:cachix/nixpkgs-python/4d2bd16c09baaa04f4045f16f6a5574654aaba16`, `github:oxalica/rust-overlay/8111d2b45adcbaeaff037f996643f1ac43f944e6` |
| QEMU (sharing VMs) | 11.1.1 from the pin |

**The S1 module tree.** The S1 tag does not exist yet. Every fixture used a scratch tree:

- Path: `LOGS/s3/devenv-modules` (the `devenv` input is `path:LOGS/s3/devenv-modules/src/modules`).
- Recipe: upstream devenv `b904dcb51fe48c30db250038241507f60752f222` from the local collection, with
  these patches in order: `T4-patch.diff`, the old `0002` content (`latest-version = "2.4.0"`),
  `patch1.diff`, `patch2.diff`, `0005-module-hunk.patch`. The last patch applied with offsets only
  (hunk 1 offset +21, hunks 2 and 3 offset +67), no fuzz, no `.orig` or `.rej` file.
- Patch checksums: `LOGS/s3/logs/patch-sha256.txt`. The recipe and commands: `LOGS/s3/devenv-modules.README`.
- Result hash: `nix hash path src/modules` = `sha256-BJLQl3uuGrP+f7+Q5Bjoatq9PJhcwDrdon9hGUbTVQ0=`
  (`LOGS/s3/logs/modules-hash.txt`). It equals the hash of the tree that the S1 session materialized
  (`LOGS/s1/devenv-modules`). Expected and actual agree.
- Checks of the tree (`LOGS/s3/logs/check-mode.log`, `check-build-vm.log`, `check-shell.log`):
  `machines.box.vendomat.mode` reads `"adopt-existing"` when set; `machines.bare.build.vm` and
  `build.iso` read `null`; a bogus `build.bogus` option fails.
- Fixtures that used this tree: `opt:catalog-devenv`, `opt:catalog-e2e`, `opt:front-door-e2e`, and
  the VMT-116 spike. `opt:catalog-eval` and `opt:parser-fuzz` use no devenv input. `opt:sharing-vm`
  needs no devenv at all (plain nixpkgs).
- **The fixtures have not run on the published S1 tag.** The tag does not exist. The guide and the
  kickoff require the rerun before step 14.

## Phase 0

The project 23 session ran Phase 0 and wrote `LOGS/phase0/phase0.md`. Observed there and in this
session:

- testee 0.7.0 at `/etc/profiles/per-user/andrew/bin/testee`; devenv 2.4.0+b904dcb first on `PATH`;
  Nix 2.34.7.
- btrfs `/`: unallocated 25.87 GiB; metadata 10.20 to 10.21 of 13.00 GiB at the start.
- All checksums matched (the Phase 0 file reads "all 15 match guide section 3"; the main agent
  reports that the eight S3 and S4 artifact checksums matched). Nothing was copied after a mismatch,
  because there was none.
- The archive exists: `/mnt/shared/vendomat-p21/archive/p21-spikes-2026-10-13.tar.zst`, 977 MB,
  100114 tar entries. S3 did not make it again.
- Disk at the last sharing run: unallocated 24.87 GiB, metadata 10.08 of 13.00 GiB (77.58 %)
  (`LOGS/s3/sharing/run-174945Z/results.log`). The disk never fell below the 15 GiB stop line.

## Testee 0.8 conversion (`bd7baeb06b1a`)

**Observation.** During the session the host `testee` became 0.8.0. It refused the repository with
`module_not_supported`. The owner chose that this session converts the repository (project 22 ruling
R18).

**Change.** The checks moved from the Testee module (`nix/testee.nix`, deleted) to devenv tasks in
`nix/tasks.nix`. Required tasks: `check:lint`, `check:format`, `check:types`, `test:full`.
`test:quick` is "n/a".

**Observation: task names.** devenv rejects a task name without a namespace. So the opt-in checks
are `opt:NAME`. The kickoff names map as follows: `catalog-e2e` is `opt:catalog-e2e`, `parser-fuzz` is
`opt:parser-fuzz`, `sharing-vm` is `opt:sharing-vm`, and `machines-vm` will be `opt:machines-vm`
(S4). Old `e2e` is `opt:e2e`.

**Result.** `testee status -r bd7baeb06b1a`: GREEN 4/4, epoch 2. `test:full` 12.2 s. Logs:
`LOGS/testee-tasks/verify.log` (RED on commit `3af9f8938f`: all four required tasks failed),
`LOGS/testee-tasks/verify2.log` (GREEN on commit `b1c7059959`, a workspace commit). The landed commit
`bd7baeb06b1a` has its own GREEN record (above).

**Observation: `opt:workspace-e2e` fails.** `/home/andrew/Documents/Projects/templateer_v2/.devenv/state/venv/bin/templateer`
is missing. This is an environment gap and not a result of the change. The task is not required for green.

**Observation: environment.** Testee 0.8 does not pass `VENDOMAT_*` variables into a task. A task
sets what it needs inside its script (`nix/tasks.nix`). See "Open items".

## Part 1: parser, catalog, template, corpus (`ccd419ddee93`)

Guide steps 2, 3, 4, and 11 (the catalog tests and the curated corpus).

**What changed.**

- `devenv/parse.nix`: parser v3 with three changes. (1) Depth limit 64. (2) A side table. The call
  `(import ./parse.nix) FILE TEXT` returns `{ value; positions; at; }`, so a schema fault carries
  `LINE:COL` (`VMT-035`). (3) The file name is a parameter, so a caller other than the catalog names its
  own file (R38). The parser stays plain Nix over builtins.
- `devenv/devenv.nix`: the catalog rewritten for the Nix parser (no primop). R42 mode logic
  (`machines.NAME.vendomat.mode` from `.machines/NAME/facter.json`, override by the key `mode`). The key
  `serve` is accepted.
- `templates/workspace/`: `devenv.yaml` with `devenv` following `vendomat/devenv` (R41),
  `nixpkgs-python` and `rust-overlay` each following `nixpkgs`, and no `require_version`.
- Curated corpus `tests/fixtures/yaml/` with expectations: `deep` 11, `edge` 152, `p4` 131, `rust` 27
  (321 files) and the `expected.json` of each group. The guide estimated about 365; the actual count is 321.
- Tests: `tests/test_catalog_parser_nix.py`, `tests/test_catalog_module_nix.py`,
  `tests/test_catalog_template.py`, `tests/nix/catalog.nix`.

**Depth limit choice (an S3 choice, no owner ruling).** The limit is 64 levels. Expected: a limit
well below the measured overflow. Observed in W4: overflow between 800 and 850 levels. Part 1
did not measure the overflow again. Its tests feed chains of 300 to 1500 levels and dash runs of 1000 and
3000 levels (`test_chains_far_past_the_old_stack_limit_fail_with_the_file_name`,
`test_dash_runs_far_past_the_old_stack_limit_fail_with_the_file_name`). All fail with the file name and
the limit text. The error reads `vendomat.yaml:LINE:COL: nesting deeper than 64 levels`.
A file at 64 levels parses and one level more fails (`test_a_file_at_the_limit_parses_and_one_level_more_fails`).

**Comparison with the spike parser.** `LOGS/s3/part1/logs-cmp.txt` ends with `same 324 diff 22`. The
differences are cases that the old parser accepted or overflowed on and the new parser rejects
at depth 64 (for example `deep_100` and `deep_1000`). Inference: these 22 differences are the depth
limit, as intended.

**Commands, expected, actual.**

| Command | Expected | Actual | Log |
| --- | --- | --- | --- |
| `testee verify opt:catalog-eval` | PASS | PASS, 85 tests | `LOGS/s3/part1/catalog-eval-3.log`; later record on main: run `20261014T164808Z-0c3108ce5018` |
| `testee verify` (Testee 0.7.0, epoch 1, before the conversion) | GREEN | GREEN 4/4 on `80aa775a32` | `LOGS/s3/part1/testee-verify-1.log` |
| `testee verify` (Testee 0.8.0, after the conversion) | GREEN | GREEN 4/4, epoch 2 on `ccd419ddee93` | `testee status -r ccd419ddee93` |
| Real-devenv smoke of the module | the mapped options read back | `machines.box.vendomat.mode` `"adopt-existing"`, `machines.vm.vendomat.mode` `"fresh-install"`, `machines.vm.hardware.facter` `null`, `vendomat.serve` `{vm=false, box=true}`, `languages.python.uv.sync.enable` `false` | `LOGS/s3/part1/real-smoke-1.log`, `real-smoke-2.log` |

`real-smoke-2.log` also holds three `command not found` lines from the smoke script and one JSON
parse error. Observation: the script ran a quoted `env -u ...` string as one command. The module
output in the same log is correct. Inference: this is a script slip and not a module fault.

## Part 2: hatch line, `explain`, trim, `update`, launcher (`b43d23e6b9cb`)

Guide steps 5 to 8, 10, and 11 (`front-door-e2e`).

**What changed.**

- `devenv/hatch.nix`: the `advanced:` line. It counts the leaves each hatch file wrote and says
  "settings". `devenv.local.nix` counts apart and says "(this checkout only)". `{ }` stubs and empty
  files print nothing. `VENDOMAT_HIDE_ADVANCED=1` hides the line (R45).
- `devenv/explain.nix` and `src/vendomat/explain.py`: `vendomat explain` (and `--json`) lists the YAML
  keys with native option, value, and source file, then the options only Nix sets.
- `src/vendomat/errortrim.py` and the launcher: the launcher runs one `devenv eval` before the shell.
  On failure it prints the `vendomat.yaml:` lines first, then the text after the last `error:`, exits
  2, and writes the full trace under `~/.local/state/vendomat/logs/`.
- `src/vendomat/update.py`: `vendomat update` adds the missing template lines to `devenv.yaml`,
  names each added line, and runs `devenv update`. `--check` reports missing lines and exits 1.
- `launcher/vendomat`: dispatch for `update` and `explain`; the old verbs stay (R40).
- `tests/test_front_door_e2e.py`: rewritten for stock devenv, the Nix parser, and the S1 tree. The
  project 20 slice 1 gate checked the primop catalog; the owner ruled in session that the check is
  updated for the new catalog. It runs an inner Testee 0.8 consumer gate.
- `tests/test_repo_shape.py`: `MODULES` gains `errortrim.py`, `explain.py`, `update.py`.

**Results.**

| Task | Expected | Actual | Testee run |
| --- | --- | --- | --- |
| `opt:catalog-eval` | PASS | PASS, 85 tests, 64.0 s | `20261014T170218Z-af8edd570bac` |
| `opt:catalog-devenv` | PASS | PASS, 7 tests, 13.4 s | `20261014T170324Z-baec8e424d8b` |
| `opt:front-door-e2e` | PASS | PASS, 1 test, 84.4 s | `20261014T170339Z-f5d0b77513c9` (commit `d7e627e807`, before the rebase) |

`LOGS/s3/part2/logs/testee-opt-1.log` holds the `opt:front-door-e2e` output. Raw fixture logs:
`LOGS/s3/part2/logs/front-door-1`, `front-door-2`, `front-door-3`, `catalog-devenv`, and
`LOGS/s3/front-door/` (one log per command, for example `fault-bad-used-build-shell.log`,
`channel-update.log`, `clone-shell.log`, `direnv-clone.log`).
Raw launcher trim logs: `LOGS/s3/part2/logs/launcher-trim-bad.log`, `LOGS/s3/part2/trim`.

**Observation: records on other trees.** The opt-in runs above ran on workspace commits before the
rebase onto `main`. `testee show -r b43d23e6b9cb` lists only the four required tasks. Inference: the
trees differ by rebase only, but no opt-in record exists for the exact `main` tree of this part.

## `opt:parser-fuzz` and `opt:catalog-e2e` (`b575e4f424b0`)

Guide step 11, the generated corpora and the W4 fixtures.

**`opt:parser-fuzz`.** The generators are in `tests/tools/` (`yamlgen_valid.py`, `yamlgen_variants.py`,
`yamlgen_fuzz.py`, `yamlgen_mutants.py`). The check generates nine corpora of about 38 000 files in
total, with the fixed seeds 20261101, 20261103, 20261102, 20261201, 20261202, 20261012, 20261014,
20261301, 20261302. Oracles: the generator trees, computed `LINE:COL` positions, and for the fuzz and
mutant corpora properties, a round trip, and a golden digest (`tests/fixtures/yaml/fuzz-golden.json`).

- Expected: the generators reproduce the spike corpora byte for byte; the parser returns each
  generator tree; indentation faults fail at the computed position; fuzz and mutant files give a tree
  or one error line.
- Actual: PASS, 16 tests, 130.7 s (`parser-fuzz.junit.xml`). `test_the_generators_reproduce_the_first_documents_of_the_spike_corpora`
  checks the digests in `tests/fixtures/yaml/corpus-digests.json`. Spike comparison: 9 differences, all
  the intended R10 change.
- Record: Testee run `20261014T172158Z-903a3908513e` on commit `5a9e7eb80d` (tree `0c58dfb603`, before the rebase).
  Log: `LOGS/s3/e2e/parser-fuzz-final.log`. Summaries: `LOGS/s3/e2e/parser-fuzz-final/`. Earlier runs:
  `parser-fuzz-run2.log` (FAIL, fixed), `parser-fuzz-run3.log`.
- Observation: no `opt:parser-fuzz` record exists for the rebased `main` commit
  (`testee show -r b575e4f424b0` lists `opt:catalog-e2e` only).

**`opt:catalog-e2e`.** W4 F1 to F14 and F4b, run on a real devenv 2.4.0 with the S1 tree and the pinned
nixpkgs `e7439b6b`. The generated documents and the curated corpus go through the catalog too.

- Expected: 21 tests pass with no skip.
- Actual, on the rebased commit: PASS, 21 tests, 0 skipped, 209.8 s. Record: Testee run
  `20261014T172536Z-91afc98a69c8`, commit `b575e4f424`, tree `c5bfb89629`. Log:
  `LOGS/s3/e2e/catalog-e2e-rebased.log`.
- An earlier run on the pre-rebase tree passed 21 tests with 2 skipped (F11 and F12 skip when the
  catalog has no `hatch.nix` or `explain.nix`; that tree still lacked them). Record: run
  `20261014T171831Z-f027a76cfc7e` (`LOGS/s3/e2e/catalog-e2e-final.log`). The rebased run replaces it.
- **VMT-036 (cost of the catalog on shell entry), warm entry, median of 7.** Run
  `20261014T170750Z-1d058f1a36f4` (`LOGS/s3/e2e/catalog-e2e-run2/cost.txt`): bare 0.46 s, catalog 0.39 s.
  Run `20261014T171831Z-f027a76cfc7e` (`LOGS/s3/e2e/catalog-e2e-final/cost.txt`): bare 0.48 s, catalog
  0.46 s. Inference: the catalog costs no more than noise. The catalog is not slower in either run.
- Per-fixture logs: `LOGS/s3/e2e/catalog-e2e-final/` (`f2.log`, `f3b.log`, `f4b-steps.txt`, `f5.log`,
  `f9.log`, `f10.log`, `f13.log`, `f14.log`, `trees.txt`).

## VMT-116: do unused template inputs cost a fetch?

**Answer: no.** Spike run on stock devenv `2.4.0+b904dcb`, Nix 2.34.7, with
`env -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV`. A Python-only workspace does not fetch `rust-overlay`,
`nixpkgs-python`, or `flake-compat` on shell entry. Nothing to propose to the owner.

- Mechanism (observation from the source and from the daemon log): devenv 2.4.0 resolves lock nodes
  lazily in `.devenv/bootstrap/resolve-lock.nix` (`mapAttrs` with `fetchTree`). Only an input that
  module code reads is fetched.
- Runs (`LOGS/s3/vmt116/RESULT.txt`, `LOGS/s3/vmt116/logs`, `runs`):
  - `A-lock`: locking clones every input once.
  - `A1-up-full-store`: network up, empty cache: only the github nixpkgs tarball and the git `vendomat` input.
  - `A2-blocked-full-store`: template shape, network blocked: fails on the github nixpkgs input, which is a
    used input (the W1 and W6 defect that patch 0003 repairs).
  - `P1`, `P2`, `P3`: blocked Python-only entries succeed with `rust-overlay` in the store, not in the
    store, and removed from the lock.
  - Positive controls: `P4` (`languages.rust` on) and `P5` (`languages.python.version` set), blocked, fail on
    exactly the fetch of `rust-overlay` and of `nixpkgs-python`. `Q1-up-eval-pyversion`: the daemon log
    requests `/nixpkgs-python.git` only when `python.version` is set.
- Limit: locking and `vendomat update` fetch every input once. The empty-cache offline entry fails on the
  used github nixpkgs input (patch 0003, `VMT-074`).

## Sharing module and `opt:sharing-vm` (`845172f0768f`)

Guide step 11b (R39, `VMT-127`, `VMT-128`). Files: `devenv/sharing.nix`, `tests/fixtures/sharing/default.nix`,
`tests/sharing_vm.py`, `tests/test_sharing_vm.py`, task `opt:sharing-vm`.

**Design.** A plain NixOS module with no `specialArgs`.

- Options: `vendomat.sharing.serve` (default true) and `vendomat.sharing.peers` (a list or a set of
  `{ url; publicKey; }`).
- Server side: the unit `vendomat-cache-key` makes a key named after the host with
  `nix key generate-secret --key-name HOSTNAME`. The secret goes to `/var/lib/vendomat/cache-key/secret`
  (mode 0600, directory 0700), the public key to `/var/lib/vendomat/cache-key.pub` (0644). The key unit
  runs before `sysinit.target`, `sockets.target`, and Harmonia. Harmonia (`services.harmonia.cache`) signs
  with the secret and listens on port 5000, which the firewall opens.
- Client side: `extra-substituters` and `extra-trusted-public-keys` per peer, `fallback = true`,
  `connect-timeout = 5` (both `mkDefault`). `cache.nixos.org` stays.
- A malformed peer key fails evaluation (`vendomat.sharing.peers: the public key of URL must read NAME:BASE64`).

**VM build.** The VMs use plain nixpkgs `system.build.vm` of the pinned nixpkgs. They do not use W2
`expose.nix` or the S1 tree, because the module needs no devenv. Direct kernel boot. QEMU 11.1.1. The VMs
join through two `eth1` cards (QEMU `dgram`). The files sit under `/mnt/shared/vendomat-p21/s3/sharing`.

**Expected and actual** (final record run, `LOGS/s3/sharing/run-174945Z/results.log`; Testee run
`20261014T174944Z-c6951f2093d9` on commit `b54e136536`, tree `1d57907e1a`, before the rebase; log
`LOGS/s3/sharing/testee-opt-sharing-vm-final2.log`): PASS, 10 tests, 189.7 s.

| Claim | Actual |
| --- | --- |
| Machine A makes its key at first boot | `vendomat-cache-key` result `success`; key name `alpha:7X0wF7brsETxOn5hWUhBz9S19CQBaWZtCDJ4e8U8gNk=`; secret mode 0600 root, directory 0700, public file 0644 |
| The secret never enters the store | search of the VM closure and `/nix/.rw-store`: "none" |
| B substitutes A's path and verifies the signature | `/nix/store/pggg2ygayn47j6nhj2jygdlqphl4fb2i-sharing-p1` substituted in 5.2 s |
| A path with an untrusted key is refused | refused, then accepted after the key was trusted |
| `serve = false` runs no Harmonia | on B: no `harmonia` unit, no key unit, port 5000 refused |
| A off: B falls back | with `fallback = false`: rc=1 after 32.7 s (Nix retries 5 times at about 5 s each); with the configured settings (`fallback = true`, `connect-timeout = 5`): builds locally, rc=0 in 25.1 s |
| A key that is not committed gives no peer entry | `peers = []` for both machines when `.machines/NAME/cache-key.pub` is absent |

Other full runs with the same result lines: `run-170108Z`, `run-171003Z`, `run-171704Z`, `run-172024Z`,
`run-172352Z`, `run-172716Z`, `run-174945Z` under `LOGS/s3/sharing/`. The main agent reports 3 of 3 full
runs plus a 15-boot loop passing. This record counted the logs: seven `results.log` files hold the
substitution line and the fallback line; `run-171534Z` (4 lines) stopped early. The boot loop log is
`LOGS/s3/sharing/bootloop/commands.log` (script `scripts/bootloop.py`); it holds 23 reads of the key unit
result, all `success`. The earlier tries `testee-opt-sharing-vm-try1.log` to `try5.log` and
`testee-opt-sharing-vm-final.log` (FAIL) show the failures that led to the final form.

**Open observation: a key-unit failure.** One key-unit failure occurred in about six early boots. It
used `nix-store --generate-binary-cache-key` while the boot registered the store paths
(`register-nix-paths`). The cause is not proved. Inference: the two steps raced. The unit changed to
`nix key generate-secret`, which needs no store, and passed 18 of 18 boots since. A passing count does not
prove the cause.

**Host fact.** QEMU `io_uring` fails for user `andrew`: the memlock budget is exhausted, cause unknown.
The VMs run in `systemd-run --user` units with `io_uring_setup` filtered.

**Key publication design (the main agent's choice; the kickoff asked to design and record).** Each
machine makes its key at first boot. The owner commits the public key as `.machines/NAME/cache-key.pub`,
the same pattern as R42's `facter.json`. The catalog gives the other machines a peer entry only when that
file exists. So an install is keyless, and an uncommitted key causes no error. The catalog applies the rule
since `79e46310ef30` (evaluation-level tests). It is new ledger row `VMT-157`. The fixture
`tests/fixtures/sharing/default.nix` applies the same rule in the VM harness; it does not run the catalog.

## Catalog wiring of sharing (`79e46310ef30`)

Landed after the commits above: "Wire the sharing module into the catalog (S3 step 11b)".

**What changed** (facts from the main agent; the logs are in `LOGS/s3/wire/`):

- The `nixos` of every YAML machine imports `devenv/sharing.nix`.
- `vendomat.sharing.serve` is a plain definition when the YAML machine has the key `serve`, else
  `lib.mkDefault true`.
- `vendomat.sharing.peers` is `lib.mkDefault`, so a `devenv.nix` can override it. A peer is another machine
  that serves and whose `.machines/NAME/cache-key.pub` exists. Its URL is `http://HOST:5000`, where HOST is the
  `host` key without any `user@` part, else the machine name. Its key is `lib.trim` of the file.

**Results** (`testee show -r 79e46310ef30`):

| Check | Expected | Actual | Testee run |
| --- | --- | --- | --- |
| `testee verify` | GREEN | GREEN 4/4, tree `54b47faf7b`, epoch 2, Testee 0.8.0 | `20261014T180104Z-8fa67323f9a3` |
| `opt:catalog-eval` | PASS | PASS, 93 tests (main agent's count) | `20261014T180124Z-56a510c61e5b` |
| `opt:catalog-devenv` | PASS | PASS | `20261014T180215Z-a1df7c58a9ed` |
| `opt:catalog-e2e` | PASS | PASS | `20261014T180257Z-9a418ed46a02` |

Stub tests (`tests/test_catalog_module_nix.py`): `test_every_machine_imports_the_sharing_module_and_serves_by_default`,
`test_serve_false_gives_the_module_with_serve_off`, `test_a_peer_needs_a_committed_key`,
`test_the_peer_url_drops_the_user_and_falls_back_to_the_name`, `test_the_key_is_trimmed`,
`test_a_machine_never_lists_itself`, `test_a_peer_with_serve_false_is_not_listed`,
`test_the_nix_files_can_override_the_sharing_values`. Tests on a real devenv (`tests/test_catalog_devenv.py`):
`test_alpha_serves_and_beta_with_serve_false_runs_no_harmonia`,
`test_beta_substitutes_from_alpha_only_after_the_key_is_committed`,
`test_a_beta_that_does_not_serve_gives_no_peer_entry`.

**Limit.** The two-VM proof (`opt:sharing-vm`) built its machines from plain NixOS evaluation with the same
rule in the harness. It did not go through the catalog. The path from `vendomat.yaml` to a machine is proved
at evaluation level only, by the tests above. Inference: the VM proof and the evaluation proof together cover
the claim, but no fixture boots a VM built through the catalog (see `VMT-121`).

## Owner rulings in the session

- Project 22 R18: this session converts the repository to the Testee 0.8 tasks.
- The opt-in `front-door-e2e` check is updated for the new catalog (it gated the slice 1 primop
  catalog). It was rewritten in part 2.
- No owner ruling covers: the depth limit 64, the key publication rule, and the `opt:` task names.
  They are S3 choices.

## Deviations and rule slips

- **Task names and file.** The kickoff names `nix/testee.nix` and the checks `catalog-e2e`,
  `parser-fuzz`, `sharing-vm`, `machines-vm`. They are `nix/tasks.nix` tasks named `opt:NAME`.
- **New row numbers.** The kickoff says new rows start at 130, and that rows 125 to 129 are used or
  skipped. The highest number across both ledgers is `BSX-156` (Basix ledger, `../basix/.scratch/projects/001-initial-concept/REQUIREMENTS.md`;
  this repository's highest is `VMT-128`). Numbers continue across prefixes, so new rows start at 157.
  Basix may add rows after this record; the next session must check both ledgers again.
- **Corpus size.** 321 files, not about 365.
- **Rule slips (agent, part 2).** Before the gate worked under Testee 0.8, the agent (1) ran
  `python -m pytest` once directly, (2) ran `ruff format --diff` once, read-only, and (3) used a script
  runner (`LOGS/s3/part2/bin/drive.py`, logs `LOGS/s3/part2/logs/drive-*.log`) for interim evidence. The
  rules say to verify through Testee only. The final verdicts of every part are Testee's.
- **Opt-in records on pre-rebase commits.** See the notes in each section.
- **Tree for fixtures.** A scratch S1 tree, not the published tag (see "Inputs and tree").

## Open items

1. **Machine with no key.** A machine entry needs at least one key, because the grammar rejects empty
   values (`VMT-012`). No ruling covers a machine without a key. Recorded as `VMT-160`.
2. **`explain` and Nix.** The Nix section covers hatch files and workspace imports only.
3. **`update` and style.** `vendomat update` handles block-style inputs and imports only. Flow style
   fails with an error that names the key (`test_flow_style_cannot_take_an_edit_and_the_error_names_the_key`).
4. **Launcher cost.** The launcher pre-check adds one `devenv eval` before the shell. Its cost is not measured.
5. **Testee 0.8 and environment variables.** Testee 0.8 does not pass `VENDOMAT_*` variables into tasks.
   `opt:front-door-e2e` defaults its module tree to the scratch path
   `~/.local/state/vendomat/p21/2026-10-14/s3/devenv-modules/src/modules` (`nix/tasks.nix`). A rerun on the published S1
   tag needs that default changed, or the test script run outside Testee.
6. **`VMT-045`.** Proved with a stub `nixpkgs-python` input only (`test_a_python_version_that_nixpkgs_python_lacks_fails`).
7. **`VMT-121`.** Not proved. No fixture builds an ISO or VM through the catalog; the sharing VMs use plain nixpkgs.
8. **Sharing key unit.** The cause of one early key-unit failure is not proved (see above).
9. **QEMU `io_uring`.** Cause of the exhausted memlock budget unknown.
10. **Concept text.** `CONCEPT.md` listed `serve` among the Basix keys. R39 makes it a Vendomat key.
    This record's commit fixes the bullet.
11. **`opt:workspace-e2e`.** Fails on the missing `templateer` binary (environment gap).
12. **Cleanup.** `/mnt/shared/vendomat-p21/s3` still exists when this record was written. The main agent decides when to delete it.

## Release state

**Not released. Step 14 (the release) is an owner gate.** Nobody tagged Vendomat or moved `release`
in the collection. Before the ask: rerun the fixtures on the published S1 tag and run `opt:front-door-e2e`,
then show the owner the version, the diff since the last release, and the results. The row
`VMT-020` ("pin through a published lock") stays open until then.

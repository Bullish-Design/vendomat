# R3: migration inventory and code-path disposition for project 20

**Date:** 2026-10-11 (`.scratch/CURRENT.md` "Updated: 2026-10-11").
**Main checkout:** `/home/andrew/Documents/Projects/vendomat`, commit `93f94329750bf9a0523f826e987b21ef03ed75bd`
(read from `.git/HEAD`; no VCS command ran).
**Status of this record:** observation plus inference. Nothing here passes a project 20 gate.

## Sources and method

- Read in full: `AGENTS.md`, `.scratch/CURRENT.md`, project 20 `CONCEPT.md`, `DECISIONS.md`,
  `REQUIREMENTS.md`, `PLAN.md`; every file in `src/vendomat/`; `launcher/vendomat`;
  `direnv/vendomat.sh`; `nix/devenv-module/*.nix`; `templates/**`; `hooks/collection-post-receive`;
  `flake.nix`; `devenv.nix`; `pyproject.toml`; `README.md`; `devenv-dist/{SERIES,UPSTREAM,RESULT}`;
  `.scratch/projects/16-vendomat-devenv-layer/evidence/fork-3-inheritance.md`.
- Read in part: test files (headers, test names, `rg` for TOML, sync, Attic), `tests/nix/infra/*`,
  `wrapper-spikes-2026-10-10.md`, project 19 `CONCEPT.md`.
- Outside the repo, read only: `~/Documents/Projects/{vendomat-demo,nix-systems,nix-meta}` and a
  `find` for `vendomat.toml`, `vendomat.yaml`, `.envrc`, and `inputs.vendomat` across
  `~/Documents/Projects`. Collection tags read from `/home/andrew/vendor/*/.git/refs/tags`.
- Scratch: `~/.local/state/vendomat/p20/2026-10-11/R3/` (`toml-files.txt`, `toml-dump.txt`,
  `classify.py`). `classify.py` ran with `python3 -I` and only parsed TOML.
- Not run: git, jj, gitman, pytest, ruff, ty, uv, sudo, Nix.
- Limit: I read the test files by name and header. A "retain" call for a test means the test
  protects behavior that survives. It does not mean I checked every assertion.

## Findings in short

1. The transitive input walk in `devenvgen.py` (`_Discovery`, lines 134-254) is replaced by fork patch
   0007. The shared-child `follows` pass (lines 256-288) is not replaced. Decide it before slice 2.
2. `yamlsubset.py` is a base for the strict linter, not the linter. Six gaps appear in table (a2).
3. Two live consumers hold a V5/V6 `vendomat.toml` (`nix-systems`, `vendomat-demo`). Both convert by
   hand in less time than a converter takes to write and test. Twenty-two other `vendomat.toml`
   files are V4 leftovers. They need deletion, not conversion.
4. The concept has no home for `[forge]`, the `repo` shorthand, `[passthrough]`, `[follows]`,
   `keep`, `mirror`, `backup`, or `vendomat sync --collection`. See "Dependencies the concept missed".

## (a) Repository code paths with disposition

Disposition words: **retain** (survives as is, wording edits only), **reuse-as-basis** (survives in
changed form), **replace** (a new file or function takes the role), **remove** (deleted at or before
cutover).

### (a1) Python modules (`src/vendomat/`, 2,939 lines)

| Path | Purpose (file:line) | Disposition | Why |
| --- | --- | --- | --- |
| `registry.py` (408) | Reads `vendomat.toml` with `tomllib` (`:24`, `:119`); seven tables (`:36`); `Source`, `Registry`; tag-pin rule `REG-017` (`:318-332`); `[settings]` (`:162-186`); `[imports]` (`:207-230`); `[follows]` (`:377-400`); `[forge]` (`:237-250`) | **replace** | TOML parsing ends at cutover. The URL, ref, rev, dir regexes (`:43-47`) and the tag-pin rule carry over to a new `inputs` validator. `forge`/`repo` have no YAML form yet (see missed dependencies). |
| `yamlsubset.py` (198) | Lenient reader for `devenv.yaml` (`parse :23`) | **reuse-as-basis** | See (a2). Keep line normalizing, indentation blocks, duplicate-key and anchor checks. Rewrite the scalar layer. Add positions and a strict mode. |
| `devenvgen.py` (559) | `sync_devenv :455`; fragment writer; digest; lock step | **split** | See (a3). |
| `nixio.py` (194) | `NixResolver.prefetch`, `direct_inputs` (`:44-88`); `canon_url`, `canon_original`, `same_source` (`:96-160`); `lock_problems` (`:166-194`) | **retain** the lock comparison (`:96-194`); **remove** `Resolver`/`NixResolver` (`:36-88`) unless owner keeps shared-child `follows` | `lock_problems` checks that the lock holds the requested inputs. `Resolver` serves only `_Discovery`. |
| `generate.py` (146) | `sync_flake`: writes `flake.nix` from the registry (`:88-128`); `load_registry :131`; `tool_version :45` | **remove** (flake target); move `tool_version` | No consumer uses the flake target (all 7 live V5/V6 files set `[targets] devenv = true`; none is flake-only). The concept names only devenv files. Owner call; I recommend removal. |
| `locate.py` (66) | `vendomat path` for a flake project: `nix flake archive` (`:27-66`) | **remove** | Serves the flake target only. |
| `lockpath.py` (118) | `vendomat path` for a devenv workspace, from `devenv.lock` with no network (`:103-118`) | **retain** | No TOML dependency. Error text names `vendomat sync` (`:32`, `:111`): edit wording. |
| `check.py` (151) | `pin_problems :39`, `fragment_problems :57`, `version_problems :80`, `check_workspace :115` | **reuse-as-basis** | Keep pin and version checks. Replace the fragment check (reads `vendomat.toml`, `:63`, `:119`). `devenv build` does not evaluate assertions (`push.py:3-5`), so the front door needs this check before `build`. |
| `push.py` (108) | Check, `devenv build`, `attic push --stdin` (`:61-108`) | **remove** | Attic ends; no push credential. `parse_paths :36` may help a release-root builder. |
| `bump.py` (169) | Edits `ref` of inline TOML tables by regex (`:66-84`), runs `sync`, runs a gate per workspace (`:118-156`) | **remove** (owner call) | A regex edit of YAML is fragile. Two consumers exist. Running a gate per workspace is workspace orchestration, which `AGENTS.md` excludes. |
| `store.py` (287) | `keep`/`mirror` clones (`sync_store :178`), `refresh_collection :252`, `clone_url :85` | **reuse-as-basis** | The git logic has no TOML dependency except `Registry`/`Source` types (`:27`). It needs a new entry point (`vendomat sync --collection` goes away) and a decision on where `keep`/`mirror`/`backup` live. No live `vendomat.toml` uses them. |
| `machine.py` (197) | `plan_install` (`:123-172`), `run_install` (`:175-197`); reads `vendomat.modes` and `vendomat.installTargets` through `devenv eval` (`:134`, `:167`) | **reuse-as-basis** | The guard logic survives. The option paths change when Basix names the inventory. It calls `check_workspace` (`:127`). Where it lives (Vendomat or Basix) is open. |
| `defaults.py` (11) | Release default `nixpkgs` revision (`:10-11`); a test compares it with `flake.nix` | **retain** | Needed if the generator still injects a `nixpkgs` default (`devenvgen.py:152-154`). Alternative: the template writes `nixpkgs` into `vendomat.yaml`. |
| `cli.py` (326) | Typer app; `sync :53`, `path :126`, `check :150`, `push :181`, `bump :209`, `machine install :277` | **replace** | The command set changes (`shell`, `build`, `test`, `machines`, pass-through). `_uses_devenv_lock :114` reads `vendomat.toml`. |

### (a2) `yamlsubset.py` as a base for the `vendomat.yaml` linter

Observed gaps against `DOOR-012` and `CONCEPT.md` section 3:

| # | Gap | Evidence | Effect |
| --- | --- | --- | --- |
| 1 | It accepts flow lists and maps | `_scalar_or_flow :139-157` | Concept rejects flow collections. Add a strict flag. |
| 2 | Every bare token is a string, including `12` and `1.5` | `_scalar :189-198` | Concept needs numbers and rejects implicit strings. Bare `yes`, `on`, `12` must fail with a reason. |
| 3 | Quoted strings take no escapes | `_scalar :190-191` returns `text[1:-1]` | `render_yaml` writes `json.dumps` strings (`devenvgen.py:297`). A `é` or `\"` would not round-trip. URLs are ASCII today, so nothing fails now. |
| 4 | The parse tree holds no positions | `parse` returns plain `dict` (`:23-35`) | A schema fault found after parsing cannot name its line. The linter needs a tree of `(value, line)`. |
| 5 | A block list may not hold maps | `_list :87-88` | Allowed by `DOOR-012` ("block lists") but undefined for `listOf submodule` options. Decide. |
| 6 | Errors name the line but often not the key | e.g. `:60`, `:66`, `:109` | `DOOR-011`/`CONCEPT.md` need file, line, key, reason. |

What already fits: tabs rejected (`:65-66`), duplicate keys rejected (`:110-111`), anchors, aliases,
tags, and block scalars rejected (`:68-69`, `:141-142`), multiple documents rejected (`:57-60`),
`github:owner/repo` colon handled (`:132-135`), no dependency. `test_repo_shape.py:50-53` fails if a
second dependency joins `typer`, so a third-party YAML library would break a standing guard.

Recommendation: write `vendomatyaml.py` beside it (strict, located, about 250 lines), copy the line
and block logic, and add an accepted/rejected corpus. Keep `yamlsubset.py` only while a lenient reader
is still needed for user `devenv.yaml` (`devenvgen.py:384`, template `devenv.yaml` uses a flow list).
Remove it at cutover if nothing reads a foreign YAML file.

### (a3) `devenvgen.py` split, and the transitive resolution judgment

| Function (line) | Disposition | Reason |
| --- | --- | --- |
| `_Discovery.run/_walk/_read_yaml/_read_relative/_add` (`:147-254`, about 110 lines) | **remove** | Fork patch 0007 inherits inputs from imported sources, imports their nested modules, handles local imports, and errors when two sources declare one input differently. `fork-3-inheritance.md` shows 9 of 9 fixture cases and a live collection proof. The cases cover: one-input inheritance, transitive import, local import, local import leaving the input, consumer entry wins, and the conflict error naming both imports. |
| `_Discovery.follows` (`:256-288`) | **owner decision** | Fork evidence says "Shared-child `follows` (`PRE-005`) stays a Vendomat job; the lock can hold duplicate nodes." `vendomat-demo` depends on it: its `vendomat.toml` has no `[follows]`, yet `.vendomat/devenv.yaml` has `vendomat.inputs.nixpkgs.follows`. It needs `nix flake metadata` per input, so it runs Nix before the lock. Options: (1) drop it and write `follows` in `vendomat.yaml` with devenv's own syntax, (2) keep it as a lock-step helper. I recommend (1). |
| `render_yaml :294-314`, `_replace :324-332`, `_restore :335-347`, `clear_eval_state :350-366` | **retain** | Deterministic output, newer mtime on replace, and eval-cache clearing do not depend on TOML. |
| `ensure_lock :408-449`, `requested_inputs :317` | **retain** | Exit status of `devenv update` is not a result (`:411`). The lock comparison stays valid. |
| `NIX_MODULE :76-109` and `_unchanged :546-559`, digest | **reuse-as-basis** | The stale guard (`DOOR-009`) stays. Its hash target changes from `vendomat.toml` to `vendomat.yaml` and `.vendomat/config.json`. The per-import NAR hash lines (`:509`) disappear with `_Discovery`. |
| `override_warnings :372-395` | **remove or keep lenient** | 0007 makes a consumer entry win and errors on conflict. The warning is a courtesy only. |
| `sync_devenv :455-543` | **replace** | Becomes "prepare": lint, render, write on change, lock, schema. |

Conclusion on need: transitive input resolution is **not needed** for correctness once the patched
devenv is the one that runs. Stock devenv fails on an inheriting consumer (`fork-3-inheritance.md`,
"stock | inheritance | cold | exit 1"), so the front door must guarantee the fork CLI. What 0007 does
not cover is the `follows` pass above and a nested `follows` deeper than one level (dropped, spike S3).

### (a4) Launcher, direnv, hook, flake

| Path | Purpose | Disposition | Why |
| --- | --- | --- | --- |
| `launcher/vendomat` (121) | Finds root by `vendomat.toml` (`:43`); inside a workspace serves `sync` only and refuses others with exit 3 (`:55-67`); finds the pinned build by NAR hash of lock node `vendomat` (`:75-121`); falls back to host release (`:26-29`, `:70-79`, `:115-119`) | **reuse-as-basis**, two edits | Root marker becomes `vendomat.yaml` (dual marker during transition). The sync-only rule flips to "serve every command". Pinned-build lookup stays. It requires the input to be named `vendomat`. |
| `direnv/vendomat.sh` (36) | `use_vendomat`: hash check, `vendomat sync`, `use devenv` (`:13-35`) | **replace** | Reads `vendomat.toml` (`:16`, `:25`) and calls `sync` (`:30`). A direnv hook still needs a prepare entry (see missed dependencies). |
| `hooks/collection-post-receive` (31) | Checks out the newest tag after a push | **retain** | No TOML dependency. Comments (`:4`, `:29`) name `vendomat sync --collection`: edit wording. |
| `flake.nix` (58) | One input `nixpkgs` (`:7`); outputs `devenvModules.default` (`:14`), `packages.vendomat` (`:18-40`), `packages.launcher` (`:48-56`) | **retain** outputs; edit `description` (`:2`) and `postInstall` (`:29-34`) | All three outputs survive. `test_repo_shape.py:44-46` pins a single input. Harmonia needs no new input if nixpkgs carries its module. |
| `devenv-dist/` (patches 0001-0008, `materialize`, fixtures) | The fork recipe, `v2.4.0-vendomat.3` (`UPSTREAM:5`) | **retain** | The concept relies on it. No file outside `patches/` names `vendomat.toml`, sync, or Attic (`rg` found none). |

### (a5) Nix module (`nix/devenv-module/`)

| Path | Purpose | Disposition | Why |
| --- | --- | --- | --- |
| `default.nix` (245) | Options `package`, `inventory`, `installTargets`, `modes`, `paths`, `inputPaths`, `cache`, `check`, `hosts`, `users`; guard wiring; tasks | **reuse-as-basis**, edit by option | Per option below. |
| `default.nix` `cache.*`, `pushScript`, task `vendomat:push` (`:21-28`, `:151-163`, `:217-233`) | Attic push route | **remove** | Attic ends (`CONCEPT.md` section 5). |
| `default.nix` `inventory`, `installTargets`, `modes` (`:86-123`), machine wiring (`:30-53`, `:186-194`) | Host inventory in Nix | **reuse-as-basis** for Basix | `CONCEPT.md` section 3 puts the data inventory under `basix.machines` (proposed). No Basix repository exists under `~/Documents/Projects`. Keep the module here until it does. |
| `default.nix` `paths`, `inputPaths`, `hosts`, `users` (`:125-181`) | Host paths, input store paths, profile defaults | **retain** (owner may prune `hosts`/`users` defaults `server`/`framework`/`andrew`, `:174`, `:179`) | Not tied to TOML or Attic. |
| `default.nix` `check` assertion text (`:240`) | Says "in vendomat.toml ... run 'vendomat sync'" | **retain**, edit wording | The pin rule survives. |
| `guard.nix` (96) | Disk guards, fresh and adopted modes | **reuse-as-basis** | `DOOR-015` needs the same guards. Moves to Basix when Basix exists. |
| `preflight.nix` (25) + `preflight/vendomat-preflight` (259) | Bakes target identity into the target-side preflight | **reuse-as-basis** | Same reason. Patches 0005/0006 read `machines.<host>.vendomat`. |
| `lock-pin.nix` (18) | Lock-pin check | **retain** | No dependency on TOML. |

### (a6) Templates

| Path | Disposition | Why |
| --- | --- | --- |
| `templates/workspace/devenv.nix` (9) | **replace** | Line 4 reads `vendomat.toml` with `fromTOML`; line 8 sets `vendomat.settings`. The new stub holds no data bridge (`DOOR-001`, `DOOR-006`). |
| `templates/workspace/devenv.yaml` (2) | **retain**; change `[ ./.vendomat ]` to a block list if the strict reader reads it | Stable import of `.vendomat/`. |
| `templates/workspace/init` (33) | **replace** | Names `vendomat.toml` (`:23`, `:31`). Needs Templateer (`:12-16`). |
| `templates/workspace-registry/{metadata.yml,schema.py,prompt.md,template.j2,examples/*}` | **replace** with a `vendomat.yaml` template | `metadata.yml:5-6` outputs `vendomat.toml` with language `toml`; `:19-20` trigger filename. Example output is `default.output.toml`. |

### (a7) Testee checks (`devenv.nix`) and tests

| Item | Disposition | Why |
| --- | --- | --- |
| `testee.checks.ruff`, `ruff-format`, `ty`, `pytest` (`devenv.nix:39-60`) | **retain** | Generic gate. |
| `e2e` (`:64-84`) | **retain**, repoint | Runs the opt-in suite. Sets machine-specific `VENDOMAT_TEMPLATEER` (`:74`), already an open item in `CURRENT.md`. |
| `workspace-e2e` (`:85-103`) | **replace** | Runs `tests/test_workspace_user_e2e.py`, which writes TOML. |
| `live-cache`, `live-cache-load`, helper `liveCache` (`:13-28`, `:110-111`) | **remove** | They push to the live Attic (`CACHE-012`). |
| Tasks `vendomat:lint`, `vendomat:test`, `base:*` (`:166-172`) | **retain** | Unrelated to the design. |

| Test file (lines, tests) | Disposition | Note |
| --- | --- | --- |
| `test_registry.py` (296, 39), `test_registry_v6.py` (94, 13) | **remove** with `registry.py` | Port the tag-pin, URL, ref, rev, dir cases to the new input validator first. |
| `test_generate.py` (210, 19), `test_sync_nix.py` (399, 17), `test_project_output_interface.py` (294, 13), `nixfixture.py` (300) | **remove** with the flake target | |
| `test_devenvgen.py` (504, 26) | **split** | Port: render determinism, unchanged no-op, digest, mtime, eval-cache, dry run, `ensure_lock` x4, `lock_problems`, `same_source`. Drop: three-level imports, cycle, two-import conflict, registry-wins, unreachable import, yaml below `dir`. The fork `inherit-fixture` must cover those first. |
| `test_yamlsubset.py` (69, 5) | **replace** | Grows into the accepted/rejected corpus. |
| `test_commands_v6.py` (358, 26) | **split** | Keep `path` (4 tests) and `check` (about 9). Remove `push` (5) and `bump` (6). |
| `test_cli.py` (45, 6) | **replace** | `BUILT` set (`:13`) is the old command list. |
| `test_machine_install.py` (190, 11) | **retain**, adapt | Imports helpers from `test_commands_v6`. |
| `test_store.py` (680, 44) | **retain**, adapt entry point | Pure git logic. |
| `test_collection_hook.py` (185, 8), `test_collection_vm.py` (45, 1), `tests/fixtures/collection-vm/` | **retain** | Source collection stays. |
| `test_launcher.py` (208, 12), `test_launcher_e2e.py` (157, 1) | **adapt** in two steps | Dual marker, then the new rule. |
| `test_use_vendomat.py` (94, 3) | **replace** | |
| `test_devenv_sync_e2e.py` (257, 1), `test_workspace_user_e2e.py` (204, 1) | **replace** | Same scenarios on `vendomat.yaml`. They write `vendomat.toml` (`:133`). |
| `test_devenv_module_e2e.py` (462, 10) | **split** | Keep machine, guard, pin, input-paths cases. Remove the push case (`:447-460`). Drop the `tomllib` read (`:16`, `:439`) for the version. |
| `test_devenv_dist.py` (187, 13), `test_fleet_shape.py` (56, 3) | **retain** | |
| `test_repo_shape.py` (53, 4) | **retain**, edit `MODULES` (`:18-34`) | It will fail until the module list matches. |
| `test_v6_ledger.py` (19, 1) | **retain** until the successor specification supersedes the V6 ledger | |
| `test_live_cache.py` (303, 16), `livecache.py` (466) | **remove** | |
| `test_infra_e2e.py` (157, 4) | **split** | Collection test stays. Cache test and builder test change. |
| `tests/nix/infra/collection.nix` (267), `collection-add` (76), `pin.nix` (19) | **retain**, adapt command text | `collection.nix` runs `vendomat sync` and `sync --collection` (`:173-255`) and writes `vendomat.toml` (`:167`, `:200`). |
| `tests/nix/infra/cache.nix` (315), `attic-server.nix` (50) | **remove** | Replace with a Harmonia two-VM test. |
| `tests/nix/infra/builder.nix` (278), `builder-vm.nix` (382) | **reuse-as-basis** | Per-tag build and scan (`builder.nix:5-13`) match `CONCEPT.md` section 5. Drop `attic watch-store` (`:12`, `:258-270`); add one GC root per built tag. |

## (b) External consumers

### (b1) `vendomat.toml` files under `~/Documents/Projects` (29 files, depth 9)

Raw list and content: `~/.local/state/vendomat/p20/2026-10-11/R3/toml-files.txt` and `toml-dump.txt`.

| Group | Count | Paths | Content |
| --- | --- | --- | --- |
| V5/V6, live consumer | 2 | `nix-systems/vendomat.toml` (48 lines); `vendomat-demo/vendomat.toml` (25 lines) | See (b2), (b3). |
| V5/V6, lane copies of `nix-systems` | 5 | `gitman-workspaces/v6-{server-role,services-rerun,services-vm,vm-core,vm-disk}/vendomat.toml` | Same keys. Two hashes. The `.1` copies differ from `nix-systems` only in the two `devenv` fork tags (`.1` vs `.2`). Disposable lanes. |
| V4 format, main checkouts | 4 | `flora-core`, `loci-core`, `loci.nvim`, `nix-nvim` | `[toolchain]`, `[knowledge]`, `[vendor.publish]` tables. |
| V4 format, other worktrees | 15 | `argentic/.worktrees/*`, `cutover-worktrees/{flora-core,loci-core,loci-core-docfix}`, `flora-core/.worktrees/*`, `flora/.worktrees/*` (2), `loci-core/.worktrees/*`, `loci.nvim/.worktrees/*`, `poddantic/.worktrees/*` (4), `repoman/.worktrees/*` (2) | Same V4 tables. |
| V4 format, stale examples inside the vendomat repo's `.worktrees` | 3 | `vendomat/.worktrees/{agentman-0-0-3-toolchain-release,remove-retired-layer-refs,v4-adversarial-review-11}/examples/publish-demo/vendomat.toml` | `[replacement]`. These are old workspaces of the vendomat repo, not part of `main`. |

Total 29 = 7 V5/V6 + 22 V4. A file counts V4 when it has no `[inputs]` table (`classify.py`).
The 22 V4 files are the `CURRENT.md` backlog item 5. V4 keys have no V5 meaning, so no converter applies.

### (b2) `nix-systems` (the machine roles)

| Fact | Evidence |
| --- | --- |
| Roles: `server` = `fresh-install` on the blank 4 TB drive; `framework` = `adopt-existing`, provisional | `inventory/default.nix:hosts.server`, `hosts.framework`; `README.md:8-9` |
| Inventory is native Nix: `vendomat.inventory.<host>` in `devenv.nix` and plain data in `inventory/default.nix` | `devenv.nix:33-44`, `:60-64` |
| Disks by `/dev/disk/by-id` with model, serial, size; `role` `install-target` or `keep` | `inventory/default.nix` |
| `devenv Machines` config: `machines.<host>` with `target.host`, `sshOpts`, `hardware.facter = null`, `deploy.healthCheck` | `devenv.nix:46-57`, `:66-70` |
| Registry file: `[forge]`, `[targets]`, `[inputs]` (9 entries: keys `repo`, `ref`, `dir`, `url`), `[passthrough]` (4 entries: keys `url`, `rev`), `[follows]` (9 entries, all `["nixpkgs"]`) | `vendomat.toml:5-48` |
| Pins `vendomat` at `v0.7.0` and the fork at `v2.4.0-vendomat.2` | `vendomat.toml:13-16`, `:28` |
| Attic server on the host: `services.atticd` on `/mnt/wd_green1/attic`, behind Tailscale Serve at `/attic`, signing key from sops | `nixos/server.nix:87-158` |
| Attic client on every host: substituter `https://server.tail770f47.ts.net/attic/vendomat`, public key `vendomat:SRJC...`, `netrc-file` | `nixos/core.nix:20-35` |
| Launcher and host release installed on `server` | `nixos/server.nix:181-199` (`launcher`, `VENDOMAT_HOST_RELEASE`) |
| Commands that name the old flow | `AGENTS.md:25,32`, `README.md:33,36`, `devenv.yaml:1-2`, `tests/core/{ws-prepare,vendomat-cli}`, `tests/services/ws-prepare` |
| No `devenv.lock` and no `.vendomat/` in the working tree | `find` listing |

### (b3) `vendomat-demo`

`vendomat.toml` holds `[forge]`, `[targets]`, 5 inputs (`vendomat`, `devenv`, `greeting`, `marker`,
`unused`; keys `ref`, `repo`, `dir`), `[imports]` (2), and `[settings]` (two tables, one key each).
`devenv.nix` is the template bridge (`fromTOML`). The generated `.vendomat/devenv.yaml` adds
`nixpkgs` (default injection) and `vendomat.inputs.nixpkgs.follows` (auto `follows`). The modules
declare `options.vendomat.settings.greeting.text` (`sources/greeting/devenv/devenv.nix:3`).
`scripts/smoke` runs `vendomat sync`, edits TOML with `sed`, and compares `devenv.nix` (`:12-33`).
Under the project 20 rule "every other top-level key is a declared option path", `[settings.X]` maps
one-to-one to `vendomat: settings: X:` with no module change.

### (b4) `nix-meta` pins and Attic config

- Working tree at `98d9f878...` on branch `vendomat-copyroom-0.8.0` (from `.git/HEAD`). Its
  `flake.nix:52` pins `vendomat` at `d5a90f0aff97224b34e9bc2647e56b44cbf790d5` (the V4 revision). Its
  `flake.lock` carries the same revision. `CURRENT.md` says `main` pins `a8bba69`. I did not read
  `main`, so the two statements do not conflict yet. Treat the pin on `main` as unverified here.
- `machines/server.nix:68` imports `inputs.vendomat.nixosModules.default` (V4); `profiles/developer.nix:16`
  takes `repoman-toolchain-core` from it. Backlog items 1 and 3 in `CURRENT.md`.
- Attic server config: `machines/server.nix:339-396` (`services.atticd`, storage setup, Tailscale
  Serve), `profiles/secrets.nix:11-92` (signing key, `atticd.env`).
- `scripts/collection-add` (comment lines 33 and 58) names `vendomat sync --collection`.
- `nix-meta-channel4` carries the same V4 pin shape (`profiles/developer.nix:16`, `machines/server.nix:68`).

### (b5) Direnv and other call sites

- `.envrc` files: 66 under `~/Documents/Projects` to depth 3. None contains the text `vendomat`. No
  consumer calls `use_vendomat` (searched `use_vendomat`, `vendomat.sh`). The hook has no live user;
  only `tests/test_use_vendomat.py` runs it.
- `inputs.vendomat` or `vendomat.{cache,settings,inventory}` appears in live code only in
  `nix-systems`, `vendomat-demo`, `nix-meta` and `nix-meta-channel4` (V4 form). Other `devenvModules.default`
  matches are Testee's module (12 repositories). `linkman` is the V4 consumer listed in backlog item 6.
- Collection tags (`/home/andrew/vendor/*/.git/refs/tags`, loose refs; no `packed-refs`): `vendomat`
  has only `v0.7.0-rc.1`; `devenv` has `v2.4.0-vendomat.2` and `.3`; `vendomat-demo` has `v0.2.0`.
  `nix-systems/vendomat.toml:16` pins `vendomat` `v0.7.0`, which the collection does not hold. That
  would block a fresh lock there.

## (c) Converter cost judgment

| Measure | Value |
| --- | --- |
| Live V5/V6 files to convert | 2 (73 lines in total) |
| Disposable lane copies of one of them | 5 (re-copy after the source converts) |
| Input entries to convert | 18 (`nix-systems` 9 in `[inputs]` + 4 in `[passthrough]`; `vendomat-demo` 5) |
| `[follows]` entries | 9 (`nix-systems` only) |
| `[imports]` entries | 2 (`vendomat-demo` only) |
| `[settings]` tables | 2, one key each (`vendomat-demo` only) |
| Input keys in use | `url`, `repo`, `ref`, `rev`, `dir` |
| Input keys never used | `flake`, `mirror`, `keep`, `backup` |
| Tables in use | `forge` (7 of 7 files), `targets` (7), `inputs` (7), `passthrough` (6), `follows` (6), `imports` (1), `settings` (1) |
| V4 files (no conversion path) | 22 (4 in main checkouts) |

Cost estimate (inference): a converter needs about 150 lines plus tests and a report format. Two manual
edits take less time. The harder part is the mapping, and a converter cannot settle it:
`repo` expands to `git://server/<repo>`; `[passthrough]` has no YAML counterpart; `[follows]` needs
devenv's nested syntax; `keep`, `mirror`, `backup` have no home. Those are design choices, not coding.

**Verdict: no converter.** Convert the two files by hand in slice 7 and record each moved value and
each value that needs native Nix in the evidence file. That report satisfies `DOOR-018` for the only two
consumers and passes `CONCEPT.md` gate 9. Revisit only if a third live consumer with many entries
appears. Delete the 22 V4 files under backlog item 5; do not convert them.

## Dependencies the concept missed

1. **`[forge]`, `repo`, `[passthrough]`, `[follows]`.** `CONCEPT.md` section 3 says `inputs` keep
   devenv's meaning. devenv has no forge base URL and no `repo` shorthand. Both live files use them
   (7 of 7 have `[forge]`). Decide: expand to full URLs, or define a `vendomat:` option block.
2. **`keep`, `mirror`, `backup`, and `sync --collection`.** Section 5 keeps mirrors and clones, but no
   key or command remains once `sync` goes. `store.py` has no other entry point. The server needs a
   command to refresh the collection (`store.py:252`; used in `tests/nix/infra/collection.nix:209-255`
   and named by `hooks/collection-post-receive:4,29`). Suggest `vendomat collection refresh`.
3. **A prepare entry for direnv and editors.** The concept removes `sync`. Direnv calls `use devenv`,
   which skips the front door. The stale guard (`DOOR-009`) would then fail on every edit. A hidden
   `vendomat prepare` is `sync` under a new name. State that openly.
4. **Which devenv CLI the front door runs.** `DOOR-010` pins the Vendomat build. The patched CLI is a
   separate build of the fork, and `check.version_problems` (`check.py:80-112`) compares its revision
   with the locked `devenv` input. The launcher does this for `vendomat` only (NAR hash lookup,
   `launcher:75-121`). Stock devenv fails inheritance, so the front door must find the fork CLI.
   Not proven.
5. **The `vendomat` input name.** The launcher finds the pinned build at `.nodes.vendomat`
   (`launcher:75`, `:105`). The template must keep an input of that name.
6. **Flake target removal.** The concept names no flake target, but code, tests, and a fixture family
   depend on it (about 1,200 test lines). Confirm removal.
7. **`bump`.** Not in the concept. It edits TOML and runs `sync`. Remove or rewrite.
8. **Shared-child `follows`.** Section 5 says Vendomat does not resolve a second transitive graph.
   `follows()` is the one place it still does. See (a3).
9. **Option name clash.** Existing options live under `vendomat.*` (`inventory`, `cache`, `paths`,
   `settings` by modules). Under "top-level key = option path", `vendomat:` is a legal key. The Basix
   rename to `basix.machines` leaves `vendomat.inventory` in `nix-systems/devenv.nix` to migrate.
10. **Templateer.** `templates/workspace/init:12-16` needs Templateer on `PATH`. The e2e checks hard
    code a machine path (`devenv.nix:74`).

## Code that already implements a project 20 idea

- `nix/devenv-module/default.nix:42-53` reads the machine mode and preflight program from the patched
  devenv (`machines.<host>.vendomat`). This is the Basix guard seam.
- `guard.nix` and `preflight.nix` already implement fresh-install and adopt-existing guards, by-id disks,
  and protected disks (`DOOR-015`).
- `devenvgen.py:324-332` (`_replace`) and `:546-559` (`_unchanged`) already write a file only on
  change (`DOOR-007`). `NIX_MODULE` is the stale guard (`DOOR-009`).
- `tests/nix/infra/builder.nix` already builds each release tag of each input and scans for new tags.
  Only the GC root and the Harmonia path are missing.
- `hooks/collection-post-receive` and `store.refresh_collection` already keep the collection on the
  newest tag.
- The launcher already finds the pinned build by NAR hash and caches it (`DOOR-010`, except the
  sync-only rule).

## (d) Proposed slices

Rules used: each slice is reviewable alone, gated by `testee verify` unless it names another check, and
reverts by one revert of its change. Slices 1-4 add files and expose nothing to a user. Slice 6 flips
the user surface and deletes the TOML runtime in the same release, so no two formats run in parallel.
Slice 5 is the only slice that touches the host release path.

| # | Slice | Depends on | Files touched | Gate | Rollback point |
| --- | --- | --- | --- | --- | --- |
| 0 | Authority and three open fixtures. Map V5/V6 IDs to retained or successor IDs. Run on pinned tools: neutral-data schema export; module priority matrix (`mkDefault`, `mkForce`, scalar, list, attrset); owner decision on shared-child `follows`, `forge`/`repo`, `keep`/`mirror`. | none | `.scratch/projects/20-*/` (new successor spec, evidence); fixtures outside `src/` | `testee verify`; `test_v6_ledger.py`; no reused or missing ID | Delete the new documents. No code changed. |
| 1 | Strict `vendomat.yaml` parser and linter, pure Python. Located tree, scalars with numbers and escapes, strict mode, secret-field list. Not wired to any command. | 0 | new `src/vendomat/vendomatyaml.py`; `tests/test_vendomatyaml.py`; `tests/fixtures/yaml/{accept,reject}/`; `test_repo_shape.py` `MODULES` | `testee verify` (ruff, ty, pytest); corpus accepts and rejects with file, line, key, reason | Delete the new files and the `MODULES` line. |
| 2 | Generator without Nix. `inputs` and `imports` to `.vendomat/devenv.yaml`; option data to `.vendomat/config.json`; digest on `vendomat.yaml`; write only on change. Reuse `render_yaml`, `_replace`. No transitive walk (0007 covers it). Input validator takes the tag-pin and URL rules from `registry.py`. | 1 | new `src/vendomat/prepare.py`; split shared helpers out of `devenvgen.py`; new tests | `testee verify`; unchanged input rewrites no file (byte and mtime check); deterministic output | Delete `prepare.py` and tests. `devenvgen.py` still serves `sync`. |
| 3 | Lock step and schema. Port `ensure_lock` and `lock_problems`. Export the option schema from pinned declarations with neutral data. Validate values. Report a missing schema offline. | 2, fork `.3` CLI | new `nix/devenv-module/schema.nix`; `src/vendomat/schema.py`; `nixio.py` (lock functions only); e2e fixture | `testee verify e2e` cases 1, 2, 3, 5 of `CONCEPT.md` section 8: fresh lock, changed tag with new option, pinned offline entry, unsupported type | Remove `schema.nix` and `schema.py`. No user surface yet. |
| 4 | Native config reader. The module reads `.vendomat/config.json` with `builtins.fromJSON`. Stale-guard assertion on the new digest. Priority matrix and secret canary. | 3 | `nix/devenv-module/default.nix` (additive options), new `nix/devenv-module/config.nix` | `testee verify e2e`: scalar, list, attrset, `mkDefault`, `mkForce`; canary absent from generated tree and store | Revert the module edit. Old options untouched. |
| 5 | Host-safe launcher. Accept `vendomat.yaml` or `vendomat.toml` as the root marker. Keep the sync-only rule for TOML workspaces. For a YAML workspace, serve every command with the pinned build. Release as a tag and repin on the hosts first. | 1 only (marker name); ship before 6 | `launcher/vendomat`; `tests/test_launcher.py`; `tests/test_launcher_e2e.py` | `testee verify`; `testee verify e2e`: old-tag workspace still runs `sync`; new-marker workspace runs any command; fall back to host release when the build is absent | Revert the launcher edit and repin the previous tag. Old workspaces never left the old rule. |
| 6 | Front door and cutover. New commands: `shell`, `build`, `test`, `machines`, pass-through, hidden `prepare`, `collection refresh`, `path`, `check`. Delete `sync`, `push`, `bump`, `registry.py`, `generate.py`, `locate.py`, `_Discovery`, the TOML template, `[settings]` bridge. New template and `init`. New direnv hook. README. Update `test_cli.py`, `test_repo_shape.py`. | 2, 3, 4, 5 and the tag from 5 live on both hosts | `src/vendomat/{cli,check,devenvgen,store,nixio}.py` and deletions; `templates/**`; `direnv/vendomat.sh`; `flake.nix` (`description`, `postInstall`); `nix/devenv-module/default.nix` message text; `hooks/collection-post-receive` comments; tests per (a7) | `testee verify`; `testee verify e2e` with a new `front-door-e2e`; grep guard test: no `vendomat.toml`, `vendomat sync`, `tomllib` in `src/`, `launcher/`, `direnv/`, `templates/`, `nix/` (the TOML-marker branch of the launcher is the one allowed exception until slice 7 ends) | One revert of the slice. The prior tag, with the slice 5 launcher, still serves old workspaces. |
| 7 | Consumer migration by hand. Convert `vendomat-demo`, then `nix-systems`; write the conversion report; delete the five lane copies; remove the launcher's TOML branch; repin; delete the 22 V4 files under backlog item 5. Record startup time and user steps (gate 9). | 6 | `vendomat-demo/*`, `nix-systems/{vendomat.yaml,devenv.yaml,AGENTS.md,README.md,tests/*}`; `launcher/vendomat` (final edit) | `vendomat-demo/scripts/smoke` rewritten for YAML; `nix-systems/tests/run`; `testee verify e2e` | Each consumer reverts alone. The old tag stays in the collection. |
| 8 | Remove Attic client side: `vendomat.cache.*`, `vendomat:push`, `live-cache` checks, `livecache.py`, `test_live_cache.py`, `cache.nix`, `attic-server.nix`, `builder.nix` `watch-store`. Hosts keep the Attic server until slice 9 passes. | 6 (can run beside 7) | `nix/devenv-module/default.nix`; `devenv.nix` checks; `tests/**`; `tests/nix/infra/*` | `testee verify`; `test_infra_e2e` collection and builder tests | Revert. The server side is untouched. |
| 9 | Harmonia and release roots. Builder writes one GC root per built tag. Add the serving module and client trust from inventory. | 8; project 19 gates | `tests/nix/infra/builder.nix`, new Harmonia VM test; later `nix-systems/nixos/{core,server}.nix` | Two-VM cold substitution; absent-path fallback; root survives GC (`CONCEPT.md` gates 7) | Revert the module. Hosts keep Attic until `nix-systems` moves. |
| 10 | Basix inventory. Move `inventory`, `guard.nix`, `preflight.nix`, and `machine.py` option paths under a Basix module and `basix.machines`. | 4; a Basix repository | `nix/devenv-module/{default,guard,preflight}.nix`, `machine.py`, `nix-systems/devenv.nix` | Fresh and adopted VM fixtures (`DOOR-015`, `DOOR-016`) | Keep the old option names as the shipped names until the VM fixtures pass. |

### Transition notes for slices 5-7 (keep the current host release working)

1. The host runs the launcher and the host release from one flake (`flake.nix:48-56`; `nix-systems/nixos/server.nix:183`, `:198`). One repin moves both. Release slice 5 as its own tag, repin both hosts, and only then create a `vendomat.yaml` workspace.
2. The old launcher looks only for `vendomat.toml` (`launcher:43`). In a YAML workspace it would call the host release outside any workspace. Any YAML workspace that the old launcher opens fails or runs the wrong build. Slice 5 prevents this.
3. A workspace pinned to an old tag keeps the old build, found by NAR hash. A new launcher must still pass `sync` to it, until slice 7 moves the last TOML workspace.
4. A new workspace has no lock. The launcher uses the host release for its first lock (`launcher:70-73`). The host release must therefore be at least the slice 6 tag before anyone runs `init`.
5. `nix-systems/vendomat.toml:16` pins `vendomat` `v0.7.0`, which the collection lacks. Tag the slice 6 release in the collection before slice 7, or the converted lock fails.

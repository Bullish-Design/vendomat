# Project 20 implementation plan

**Date:** 2026-10-11. [CONCEPT.md](CONCEPT.md) is the chosen future design.
[REQUIREMENTS.md](REQUIREMENTS.md) holds the proposed IDs. The
[research report](evidence/RESEARCH-2026-10-11.md) holds the evidence and the decision matrix.
This plan does not report a gate as passed until its recorded fixture passes on the pinned tools.
A spike fixture proves an interface. Only a slice that passes its gate proves an implementation.

## Slices

The order follows dependencies. Slices 1 to 4 add files and expose nothing to a user. Effort is
S (a day or less), M (a few days), or L (a week or more). Uncertainty is the chance that a fixture
changes the design.

| Slice | Deliverable | Requirement IDs | Depends on | Gate | Effort | Uncertainty | Rollback point |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Strict YAML reader. New stdlib module `src/vendomat/yamldata.py` (name proposed), ported from the S1 `hand.py`. It includes the secret-field recognizer. PyYAML is a `dev` oracle only. No CLI wiring. | DOOR-020, DOOR-035 (recognizer) | none | `testee verify --profile quick` while editing. Then `testee verify` and `testee verify --profile full`. S1 corpus: 53 accept, 115 reject with exact code, line, column. Fixed-seed fuzz: 0 divergence. Determinism test. | S | low | Delete the module, its tests, the `MODULES` line, and the `dev` dependency. |
| 2 | Canonical JSON and the generator in pure Python. Writes `.vendomat/devenv.yaml`, the data file, the digest, and a header. Writes a file only on change. Rejects input names that equal a module argument. Adds no `follows` edge. | DOOR-019, DOOR-021, DOOR-022, DOOR-036, DOOR-007 (kept), DOOR-028 (file set) | 1 | `testee verify` and `testee verify --profile full`. Equal data gives equal bytes across key order, comments, and quote style. An unchanged input leaves bytes, inode, and mtime alone. A template-bytes test runs after every command. | M | low | Delete the generator module and tests. `devenvgen.py` still serves `sync`. |
| 3 | Workspace Nix module. Reads the JSON with `_file`. Maps package and path strings from option types. Adds the module-wide stale guard with the escape variable. Adds the neutral schema-export module. Ports the S2, S3, and S5 Nix fixtures. | DOOR-023, DOOR-024, DOOR-025, DOOR-029, DOOR-035 (canary), DOOR-056 (module import) | 2, fork `.3` CLI | `testee verify`, `testee verify --profile full`, and `testee verify e2e`. Fixtures run the fork CLI and print `devenv version`. Scalar, list, attribute-set, `mkDefault`, `mkForce` matrix. Guard fires for build, eval, tasks, up, machines. Canary absent from the generated tree and the store. | L | high | Revert the module edit. The old options stay untouched. |
| 4 | Schema cache, Python validator, and the command sequence. Adds `vendomat prepare` and `vendomat prepare --check`. Fixes the exit codes 65 to 68. | DOOR-026, DOOR-027, DOOR-028, DOOR-033 (codes 65 to 68) | 3 | `testee verify e2e` runs concept proofs 2, 3, and 5 on fixtures: changed tag with a new option, offline entry from a warm store in a network namespace, missing schema exits 68. `prepare --check` exits 67 on a stale tree. | M | medium | Remove the schema module and validator. No user surface exists yet. |
| 5 | Launcher protocol release. Recognizes `vendomat.toml` (hands to the pinned V5 build) and `vendomat.yaml`. Reads `share/vendomat/launcher-protocol`. Exits 69 for a missing pinned build and 70 for a protocol mismatch. Fixes the `od -v` call. Release it and repin both hosts before any workspace switches. | DOOR-030 (launcher half), DOOR-053 | 1 (marker name). Can run beside 2 to 4. | `testee verify` and `testee verify e2e`. Cases (a) to (d) of S5. An old-tag workspace still runs `sync`. A new-marker workspace runs any command. Exits 69, 70, 71, 72. | M | medium | Repin the previous launcher in the host generation. |
| 6 | Front door and cutover. Commands `shell`, `build`, `test`, `tasks`, `up`, `update`, `machines`, `prepare`, `path`, `check`. Pass-through with `exec`. Pinned devenv lookup. `use vendomat`. Release report. Then delete the TOML reader, `sync`, `_Discovery` and `NixResolver`, `generate.py` (O1), `locate.py`, and the `bump` TOML path. Repoint `push` to the YAML check but keep it (rule below). Add the repo-shape test. Edit the `AGENTS.md` layout. | DOOR-030, DOOR-031, DOOR-032, DOOR-033, DOOR-034, DOOR-056, DOOR-054 (TOML and `sync` clauses) | 4, 5 released on both hosts | `testee verify` and `testee verify e2e` with a new front-door e2e check. A repo-shape test finds no TOML reader and no `sync`. A real `testee verify` runs on a project 20 workspace. Concept proofs 1 and 5 on a real template. | L | medium | One revert of the slice. The slice 5 launcher still serves old workspaces from their pinned build. |
| 7 | Hand migration of consumers. First `vendomat-demo`, then `nix-systems`. One conversion record each. Delete the 5 lane copies and the 22 V4 files. Tag the cutover release in the collection first. Drop the TOML marker from the launcher in the next release. | DOOR-052, DOOR-053 (marker drop) | 6 | `vendomat-demo` smoke script rewritten for YAML. `nix-systems/tests/run`. `testee verify e2e`. Startup time and user steps recorded (concept proof 9). A conversion activates no machine. | M | medium | Each consumer reverts alone. The old tag stays in the collection. |
| 8 | Harmonia. NixOS module in path-unit form. Client trust from the inventory mark with `fallback = true` and a short `connect-timeout`. Release roots written by the collection builder (`tests/nix/infra/builder.nix` basis). Two-VM test ported from S6. Then, after the live gate, remove `push`, `cache.*`, and the Attic checks. | DOOR-045, DOOR-046, DOOR-047, DOOR-048, DOOR-049, DOOR-051, DOOR-050 (after the live gate), DOOR-054 (Attic clause) | Module and VM test: none. Removal: 6. | Two-VM test as an opt-in Testee check (name proposed: `harmonia-vm`): keyless boot, key after boot, cold substitution, signature refusal, 404 fallback, root survives GC, fallback with a short timeout. Live gate on a real second machine (concept proof 7). `testee verify` after removal. | L | medium | Revert the module. Hosts keep Attic until the live gate passes. |
| 9 | Basix inventory and machines. Inventory options and guards, atomic secret receiver, `vendomat secret push`, host-key re-pin, admin key per host, adoption without disk tools, a forcing assertion for every declared option. | DOOR-037, DOOR-038, DOOR-039, DOOR-040, DOOR-041, DOOR-042, DOOR-043, DOOR-044 | 3, 8 | `testee verify e2e` plus opt-in VM checks ported from S4 (14 cases), S7 (43 checks, 20 fresh-install steps, 20 adoption checks). Concept proofs 6 and 8 on the real module. | L | high | Keep the old option names until the VM fixtures pass. |
| 10 | Real hardware review and cutover. The owner reviews the package. Run only the commands the owner authorizes. | Concept proof 10; DOOR-043 and DOOR-044 on real hardware | 9, owner authorization | No automatic gate. The `CUTOVER-REVIEW.md` package passes owner review. Every command stays NOT RUN until the owner approves it. | M | high | Do not write any disk. Each step in the package names its own undo. |

## Critical path

1 → 2 → 3 → 4 → 6 → 7. Release slice 5 before slice 6. Slice 5 needs only slice 1, so it can run
beside slices 2 to 4. Slice 8 can start after slice 1 for the module and the VM test. Its removal part
waits for slice 6. Slice 9 needs slices 3 and 8. Slice 10 needs slice 9 and the owner.

Uncertainty is highest in slice 3 (eval-cache effect of the guard, `either` package types, machine
options) and slice 9 (real installer route, foreign configurations).

## Owner decisions by slice

The research report lists the options. [DECISIONS.md](DECISIONS.md) holds the recommendations.

| Slice | Needs before it starts |
| --- | --- |
| 1 to 4 | None. Prefer O1 before slice 2, because it decides whether the generator emits a flake. |
| 5 | None of O1 to O9. Accept D7 and D10. Approve the host repin. |
| 6 | O1 (flake target), O3 (source modes and collection command), O4 (`path`, `check`, `bump`), O5 (Attic timing; slice 6 keeps `push`). |
| 7 | None new. The cutover release tag must exist in the collection. |
| 8 | O5 (removal timing). Approval to run the live gate on a real machine. |
| 9 | O2 (Basix name and repository), O8 (adopted-host report), O9 (fresh-install route), O10 (failed-unit gate before deploy). |
| 10 | O7 (disk and hardware authorization). The root-only scan (PV-02) and the `nixos-facter` report. |

## Implementation rules

- Build each new interface in one small vertical slice before you remove its old counterpart.
- Keep the current system bootable while a new host launcher or workspace pin arrives.
- Treat `vendomat.yaml`, the Basix inventory names, and every command name as proposed until a
  fixture proves them on the pinned tools.
- Every slice cites its DOOR IDs in its commit message and in its evidence note.
- A port from a spike fixture keeps the corpus and the matrix as tests. Do not shrink them.
  A long fuzz run may stay outside Testee if a fixed-seed subset runs inside it.
- Run every Nix fixture with the pinned fork CLI. Print `devenv version` in the log. The host `PATH`
  devenv is stock `2.4.0+b904dcb`. The `e2e` check falls back to it unless `VENDOMAT_DEVENV` is set.
- Keep Attic push and the Attic live checks until the Harmonia live gate passes. Then remove them
  (DOOR-050).
- Keep raw logs under `~/.local/state/vendomat/`. Record the command, the input revisions, the
  expected result, the actual result, and the inference in the repository.
- Verify with Testee. Use `testee verify --profile quick` during an edit. Run `testee verify` for
  each integrated change. Run `testee verify --profile full` when a slice names it. Run
  `testee verify e2e` when the module, the toolchain, or the consumer integration changes. Before
  integration, run `testee status -r REV` on the exact revision. Do not call pytest, ruff, or ty.
- Use Gitman for every version-control action. Land each slice on `main` after its gate passes.
- Before a VM gate, run `btrfs filesystem usage /`. Stop when unallocated space is under 2 GiB or
  metadata use is over 90%.
- Write no converter (DOOR-052). The transition launcher is the only place that reads both markers.
  It ends in the release after the last consumer migrates. After cutover no runtime path reads
  `vendomat.toml`.
- A failed fixture changes the concept, the requirements, and the implementation together. Do not
  claim a passed machine, cache, or recovery gate from a unit test.

## Status of the earlier open choices

The 2026-10-11 session settled four of the five choices that this plan once listed, at fixture level.
Each still needs an implementation proof. See the research report, sections 4 and 5.

| Earlier choice | Status | Where |
| --- | --- | --- |
| Basix machine option names | Shape settled by fixture (D15). The `basix` name stays proposed (O2). | S4, DOOR-037 |
| Priority of generated definitions | Settled: plain definitions (D2). | S2, DOOR-023 |
| Schema refresh when a new input defines an option | Settled: lock, key, export, validate (D4). | S3, DOOR-027 |
| Post-install secret route | Settled: controller push (D12). | S7, DOOR-040 |
| Converter or manual edit | Settled: manual edit (D14). | R3, DOOR-052 |

Still open: source modes (O3), the real Basix core, the installer route (O9), the offline
missing-schema message, the eval-cache effect of the guard, and `fallback = true` with a short timeout.

## First slice

Slice 1 is the strict YAML reader. It changes no runtime behavior.

1. List the existing Gitman workspaces. Report any work that `main` lacks. Then open one workspace
   with Gitman. The six older workspaces hold no such work (research report, section 10).
2. Read [S1](evidence/S1-yaml-subset.md) sections 3 and 6. Read the fixtures in
   `evidence/fixtures/s1-yaml/`: `hand.py`, `corpus.py`, `fuzz.py`, `determinism.py`, and
   `secrets_check.py`.
3. Create `src/vendomat/yamldata.py` from `hand.py`. Remove the spike header. Keep the standard
   library only. Keep the S1 function names until a caller exists. Slice 2 wires the reader.
4. Create the tests:
   - `tests/test_yamldata.py` runs every corpus case. An accepted case must match its tree in type
     and value. A rejected case must match its code, line, and column.
   - `tests/yamldata_corpus.py` holds the 53 accepted and 115 rejected cases from `corpus.py`.
   - An oracle test loads each accepted case with PyYAML and compares the tree.
   - A fixed-seed fuzz test uses a small budget. Run the S1 budget (4 seeds, 200,000 mutants each)
     by hand and log it.
   - A determinism test parses the same input in three processes with different `PYTHONHASHSEED`
     values and compares the trees.
   - A recognizer test ports the 27 flagged and 53 passing key names.
5. Add `yamldata.py` to `MODULES` in `tests/test_repo_shape.py`. The test that allows only `typer`
   reads `project.dependencies`, so a `dev` dependency passes.
6. Add `pyyaml` to the `dev` group in `pyproject.toml`. Update `uv.lock` through the project
   environment (`devenv shell -- uv lock`), not with bare `uv`. Testee runs `uv sync --locked`.
7. Run `testee verify --profile quick`. Fix ruff findings. Run `testee verify` and
   `testee verify --profile full`. Run `testee status -r REV` on the exact revision.
8. Record the Python version of the Testee venv. S1 ran Python 3.14.7. The project asks for 3.13 or
   newer. A 3.13 run closes an open S1 item.
9. Write an evidence note with the command, the versions, the expected result, and the actual
   result. Keep raw logs under `~/.local/state/vendomat/`. Do not mark DOOR-020 as a passed gate.
   State that the reader passes its corpus on the pinned tools.
10. Land the slice on `main` through Gitman after verify passes.

**Rollback:** delete the module, the tests, the `MODULES` line, the `dev` dependency, and the lock
change. No command uses the module yet.

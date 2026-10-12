# Requirement disposition map, project 20 (2026-10-11)

**Date:** 2026-10-11. **Task:** W1. **Status:** research evidence. It changes no original ledger, spec, or code. It allocates no ID beyond `DOOR-019` to `DOOR-056`.

## Header

**Sources.** Evidence records in this directory: R1 (V5 IDs), R2 (V6, project 17 to 19, DOOR IDs), and the spike records S1 to S9 (there is no S8). The orchestrator brief fixes the new IDs and decisions. The original ledgers, SPEC-V5, SPEC-V6, and LEDGER-V6 stay unedited.

**Method.** A script parsed the R1 and R2 tables. It resolved each R1 and R2 placeholder to its `DOOR-0nn` ID by the brief mapping. It translated each reference to an old `DOOR-001` to `DOOR-018` ID to its successor. A hand-written override replaced the translated text where the two records disagreed, where an owner decision applies, or where a spike changed the answer. A second script (`~/.local/state/vendomat/p20/2026-10-11/W1/check.py`) checked coverage; its output is in the final report.

**Rules.** Disposition words: `retained` (the claim holds; a rename may apply, see section 10), `superseded` (a successor ID holds the claim), `withdrawn` (no successor; a reason is given), `open` (an owner decision or a fixture must settle it), `closed earlier` (an earlier ledger already superseded or withdrew it; project 20 adds nothing). Where R1 and R2 disagree, spike evidence beats document reading. Where both are document reading, the row says which view won and why. A V6 draft successor counts as the V6 ID with its disposition in section 3.

## 1. Summary counts

| Source set | IDs | retained | superseded | withdrawn | open | closed earlier | new, proposed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V5 requirement IDs | 195 | 69 | 56 | 9 | 19 | 42 | 0 |
| V6 requirement IDs | 122 | 55 | 22 | 3 | 3 | 39 | 0 |
| V6 NAT facts | 31 | 31 | 0 | 0 | 0 | 0 | 0 |
| V5 NAT facts (apart from the 195) | 17 | 17 | 0 | 0 | 0 | 0 | 0 |
| P17 MDL rows judged | 12 | 12 | 0 | 0 | 0 | 0 | 0 |
| P18 proposed IDs | 11 | 0 | 4 | 7 | 0 | 0 | 0 |
| P19 decisions | 10 | 7 | 2 | 0 | 0 | 1 | 0 |
| DOOR original IDs (001 to 018) | 18 | 4 | 11 | 0 | 0 | 3 | 0 |
| DOOR research IDs (019 to 056) | 38 | 0 | 0 | 0 | 1 (`DOOR-055`) | 0 | 37 |

V5: 195 IDs are 153 judged (152 active and `BOOT-015`) plus 42 already closed. "closed earlier" for V5 is those 42. V6: 39 of 122 were already closed in V6 or V5. The V5 NAT facts are listed apart (section 2.2). DOOR "retained" means "kept" in the ledger; `DOOR-002`, `DOOR-005`, and `DOOR-006` count as closed earlier.

V5 final dispositions of the 153: retained 69, superseded 56, withdrawn 9, open 19. R1 had 69 retained, 53 superseded, 11 withdrawn, 20 open.

## 2. V5 requirement IDs (SPEC-V5: 195 IDs, 152 active, 32 superseded, 10 withdrawn, 1 narrowed)

R1 corrects the count of 194 and 151 in `CURRENT.md`. The 153 rows below are the 152 active IDs and the 1 narrowed ID `BOOT-015`. The 42 closed IDs of section 2.4 complete the 195.

### 2.1 Disposition table (153 IDs)

| ID | Disposition | Successor or reason | Evidence or fixture |
| --- | --- | --- | --- |
| `REG-001` | superseded | DOOR-022: `inputs` is one YAML map of named direct inputs. Duplicate keys fail (DOOR-020). | S1 (duplicate key at any depth fails, both lines named): PASS |
| `REG-002` | retained | Rename: applies to `inputs` keys in `vendomat.yaml`. The narrower input-name rule stays a separate lint beside the DOOR-020 key rule. | Linter unit test |
| `REG-006` | retained | Rename: YAML entry. The allowed entry keys are the DOOR-022 fields (`url`, `flake`, `follows`, `inputs`). DOOR-027 supplies file and line. | Accepted and rejected YAML corpus (S1 PASS) |
| `REG-007` | retained | Holds (CONCEPT section 5 keeps direct inputs only). DOOR-019 tests the bytes. | Front-door run leaves `vendomat.yaml` byte-identical (DOOR-019 test) |
| `REG-008` | superseded | DOOR-022: infrastructure inputs (`nixpkgs`, `devenv`) are ordinary `inputs` entries; no `passthrough` table. | Fixture with `nixpkgs` as an `inputs` entry on the pinned fork (not run as a separate fixture) |
| `REG-009` | superseded | V6 `REG-025` (retained: only `bump` writes `vendomat.yaml`) and DOOR-019 (every other command leaves it byte-identical). The one-time migrator that R1 names does not exist (DOOR-052). | Byte-compare after each command (DOOR-019 test) **R1/R2:** see 2.3. |
| `REG-010` | retained | Holds. CONCEPT.md:127-130 | Fixture: devenv input override on the fork leaves the lock unchanged |
| `REG-011` | superseded | DOOR-022 (native `follows` under `inputs`) and DOOR-036 (Vendomat writes no edge the user did not write). | S9: PASS (19 cases plus 2 stock controls) **R1/R2:** see 2.3. |
| `REG-012` | superseded | DOOR-020: a duplicate key at any depth fails and names both lines. One `inputs` map makes the two-table case impossible. | S1 duplicate-key cases: PASS **R1/R2:** see 2.3. |
| `REG-013` | superseded | DOOR-022: `inputs` entries use devenv input fields verbatim; `ref` and `rev` stay in the URL query and no separate key exists. | S9 and S3 fixtures write `url` with a query ref; NAT-010 (Nix rejects `ref`/`rev` beside a string `url`) **R1/R2:** see 2.3. |
| `REG-014` | superseded | DOOR-022 (a `follows` target must name an input that the file declares; report it before devenv) and DOOR-036. Native devenv rejects the other cases late. | S9: PASS (c3b target must be a consumer input; c8b) **R1/R2:** see 2.3. |
| `REG-016` | open | O3 (source modes, DOOR-055): the example writes the full `git://` URL; no forge shorthand exists. The brief recommends dropping the shorthand. | Owner decision O3 |
| `REG-017` | retained | Holds for Vendomat sources (CONCEPT section 5). The exemption for infrastructure inputs is a DOOR-022 detail (see section 11). | Existing pin unit tests rewritten for YAML |
| `REG-018` | open | O3 (source modes, DOOR-055): `mirror` moves to the option path `vendomat.sources.<input>.mode` if the owner accepts it. | Owner decision O3; store fixture unchanged |
| `REG-019` | open | O3 (source modes, DOOR-055): `keep` as for REG-018. | Owner decision O3 |
| `REG-020` | open | O3: `backup` has no home in P20. The brief recommends dropping it. | Owner decision O3 |
| `REG-021` | superseded | DOOR-003 (kept; reserved keys) with DOOR-022, and DOOR-027 (the fault names file, line, key path, reason). | Corpus with an unknown top-level key |
| `GEN-005` | open | O1 (flake target): the claim concerns a generated `flake.nix`. The header clause for `.vendomat/` files is in DOOR-028. Withdrawn if O1 withdraws the flake target. | Owner decision O1 **R1/R2:** see 2.3. |
| `GEN-006` | superseded | DOOR-007 (kept): write a generated file only when its content changes. The claim is the same (see section 12). | Run twice; compare mtime and bytes (S5 section 3: PASS for `.vendomat/`) **R1/R2:** see 2.3. |
| `GEN-007` | open | O1 (flake target): applies only if a generated `flake.nix` stays. | Owner decision O1 |
| `GEN-008` | superseded | DOOR-027: devenv alone writes `devenv.lock`; Vendomat never writes it. Reads stay allowed (`path`, `check`). | Lock byte-identical after every command except devenv's own write; S3 P5 (update is the only lock writer) **R1/R2:** see 2.3. |
| `GEN-015` | open | O1 (flake target). The devenv target already adds a default `nixpkgs`, so the claim fails there. | Owner decision O1 |
| `GEN-016` | open | O1 (flake target). | Owner decision O1 |
| `GEN-017` | retained | Holds for the fragment generator: `imports` is a user list (DOOR-022). V6 `VMOD-019` is the workspace analog. | Scan generated body for face names **R1/R2:** see 2.3. |
| `GEN-018` | open | O1 (flake target); the command name `sync` also ends. | Owner decision O1 |
| `GEN-019` | superseded | V6 `DEL-013` (retained): a library output builds with no Vendomat input and no Vendomat command. Reword "private cache" to shared cache. | Library output built with a PATH of nix and git only **R1/R2:** see 2.3. |
| `GEN-020` | retained | Holds; DOOR-036 strengthens it (no transitive input graph). The code walk in `devenvgen.py` goes at cutover. | Remove the walk after the fork inheritance fixture passes (S9 PASS) **R1/R2:** see 2.3. |
| `GEN-021` | superseded | DOOR-036 (no Vendomat-written `follows` edge) and DOOR-022 (user-written `follows` passes verbatim). | S9: PASS **R1/R2:** see 2.3. |
| `GEN-022` | open | O1 (flake target), through V6 `GEN-023` (open). | Owner decision O1 **R1/R2:** see 2.3. |
| `SYS-001` | superseded | DOOR-003 and DOOR-022 (nesting expresses the option path). NixOS and Home Manager option paths in YAML are not offered; the Basix inventory (DOOR-037) is the data route. | Corpus with a non-option key; S4 section 5 (option type audit) |
| `SYS-004` | superseded | DOOR-024: a missing nixpkgs attribute fails and names the YAML key path. | S2 sections 4.6: PASS **R1/R2:** see 2.3. |
| `SYS-006` | superseded | DOOR-024: an option type with no data form fails, names the key, and points to `devenv.nix`. Never coerced. | S2 section 4.8 PASS; S4 section 10 (47 NixOS options have no data form) |
| `SYS-007` | superseded | DOOR-023: a supported YAML data value evaluates to the same value as the native Nix definition. | S2: PASS |
| `SYS-008` | superseded | DOOR-023 (JSON reader module) and DOOR-021 (canonical JSON). `fromToml` is not in this repository. | S1 section 4.4 and S2: PASS |
| `SYS-009` | superseded | DOOR-024: package conversion applies only to package-typed options. | S2 section 4.6: PASS |
| `SYS-010` | superseded | DOOR-023 (native merge, no blanket duplicate rejection). | S2: PASS |
| `INP-003` | retained | Unchanged. Library-author rule | `nix build .#<name> --json` |
| `INP-004` | retained | Unchanged | `nix eval .#lib --apply builtins.isFunction` |
| `INP-005` | retained | Unchanged; matches CONCEPT.md:127 | `git tag --list` |
| `INP-006` | superseded | V6 `FACE-008` (retained): selected modules activate; no common `enable`. | V6 inertness fixture **R1/R2:** see 2.3. |
| `INP-007` | retained | Unchanged; CONCEPT.md:92-93 says module authors write native modules | Evaluate each exported face alone |
| `INP-008` | superseded | DOOR-036: an imported source declares its inputs; the pinned fork inherits them; Vendomat builds no second graph. | S9: PASS **R1/R2:** see 2.3. |
| `PATH-001` | retained | Built as `vendomat.paths` (nix/devenv-module/default.nix:131-137). The data source moves to `vendomat.yaml` | Fixture: two inputs read one name |
| `PATH-002` | retained | Unchanged (VENDOMAT_PATH_<NAME>, default.nix:210) | Existing module fixture |
| `PATH-003` | retained | Unchanged | Change a file; build inputs stay equal |
| `PATH-004` | retained | Unchanged | Evaluate an undeclared name |
| `DISK-001` | retained | Unchanged. CONCEPT.md:79-80, REQUIREMENTS.md DOOR-037 (inventory uses `byId`) | Resolve each entry through `/dev/disk/by-id/` |
| `DISK-002` | retained | Unchanged. Basix guard (DECISIONS.md decision 4) | Read-only preflight on the root drive |
| `DISK-003` | retained | Unchanged. Basix guard | Inject each mismatch (guard.nix, preflight.nix) |
| `DISK-004` | retained | Unchanged | Inspect evaluated `fileSystems` |
| `DISK-005` | superseded | V6 `DISK-009` (retained): declare UUIDs before format. DOOR-037 holds filesystems by UUID. | V6 disko fixture; adoption VM compares GPT and UUIDs **R1/R2:** see 2.3. |
| `DISK-006` | retained | Owner-installation cutover rule. P19 §9 keeps it | Inspect both drives after install. Blocked: PV-02 scan, owner action |
| `DISK-007` | retained | Unchanged | Unmount a test disk; service does not start |
| `STORE-001` | retained | Unchanged. Built (store.py) | Existing unit test |
| `STORE-003` | retained | Rename: the command name `sync` ends. The vehicle is DOOR-055 (open, O3). | Dirty a tree; exit status 1 for that input |
| `STORE-005` | retained | Unchanged | Resolved url names the sibling path |
| `STORE-006` | retained | Unchanged. CONCEPT.md:127 | Move the consumer; evaluate again |
| `STORE-007` | retained | Unchanged | Compare lock hashes with and without the variable |
| `STORE-008` | superseded | DOOR-038 (host, user, and path names from the inventory) and DOOR-055 (open; collection work). Tag-only and daemon text stays in `STORE-014` and `STORE-015`. | P19 removes owner-specific assumptions; NAT-016 (idle daemon cost) **R1/R2:** see 2.3. |
| `STORE-009` | open | O3 (source modes and collection commands, DOOR-055). | Owner decision O3; keep PV-20 fixture |
| `STORE-010` | retained | Holds. CONCEPT.md:135-136 (source and tags are the record). Not built today | Delete a collection repo, push tags again, compare tag lists |
| `STORE-012` | retained | Rename: "Attic" reads "the shared cache". DOOR-051 cites this ID. | Consumer locks and evaluates with only the collection configured **R1/R2:** see 2.3. |
| `STORE-014` | retained | Unchanged. CONCEPT.md:127 (immutable tags) | PV-18 two-machine test |
| `STORE-015` | retained | Rename: "tailnet interface" becomes the installation's named interface (19/DECISIONS.md network row) | PV-18 plus an interface-neutral NixOS test |
| `STORE-013` | retained | Rename: the hook carries it (`hooks/collection-post-receive`). Any `sync` route is DOOR-055 (open, O3). | PV-20, PV-22 fixtures |
| `STORE-016` | open | O3 (command) and O1 (the `flake.nix` write): both the command and the file change. | Owner decision O3 and O1 |
| `STORE-017` | retained | Holds for the path rule. The `repo` key and forge clone follow DOOR-055 (open, O3). | PV-20 unit tests **R1/R2:** see 2.3. |
| `STORE-018` | open | O3 (collection commands, DOOR-055). | Owner decision O3 |
| `STORE-019` | retained | Holds; the mode that makes the clone follows DOOR-055 (open, O3). | PV-20 **R1/R2:** see 2.3. |
| `STORE-020` | retained | Holds (`store.py` git rules). Independent of the command home. | PV-20 unit tests **R1/R2:** see 2.3. |
| `STORE-021` | open | O3 (collection commands, DOOR-055). | Owner decision O3 |
| `STORE-022` | open | O3 (collection commands, DOOR-055). The hook route (`STORE-023`) already works. | Owner decision O3 |
| `STORE-023` | retained | Unchanged. Built, installed on `devman` (PV-22) | PV-21, PV-22 |
| `CACHE-001` | superseded | DOOR-046: clients derive the substituter and public key from the inventory mark and set `fallback = true`. | S6 steps 4 and 5: PASS **R1/R2:** see 2.3. |
| `CACHE-002` | superseded | DOOR-049: the Harmonia signing key never appears in a tracked file, store path, or log. | S6 step 2: PASS (test layout); grep of tracked files and closure not run |
| `CACHE-003` | withdrawn | No push route and no credential exist (19/DECISIONS.md decision 3). Harmonia is read-only | None |
| `CACHE-005` | superseded | DOOR-048: a path absent from the serving store answers 404 and the client builds locally. | S6 steps 5 and 6: PASS |
| `CACHE-006` | withdrawn | No Attic and no watch-store. The serving host builds shared outputs (DOOR-051) | None |
| `CACHE-007` | retained | Holds for Harmonia. P20 gate 7 | Cold VM with a store image (V6 BOOT-027), `--max-jobs 0` |
| `CACHE-008` | retained | Holds. Observed for Harmonia (19/CONCEPT.md §10) | Compare both hashes in the two-VM run |
| `CACHE-009` | superseded | DOOR-046 (upstream caches stay first; `fallback = true`). The builder's upstream-skip report is withdrawn with Attic. | S6 step 5: PASS for `fallback = true` **R1/R2:** see 2.3. |
| `BUILD-001` | retained | Rename: each collection release tag (CONCEPT.md:132-133). Not built | P20 stage 6 builder fixture |
| `BUILD-002` | retained | Rename as BUILD-001. Not built | Tag one input; only it builds |
| `BUILD-003` | retained | Unchanged. Not built | Log check |
| `BUILD-004` | retained | Unchanged. Not built | Break one input; others build |
| `BUILD-005` | superseded | DOOR-050 (cutover removes `vendomat push`) and DOOR-051 (the serving host's store is the cache). | Check that `push` is removed; today `push` pipes to `attic push` **R1/R2:** see 2.3. |
| `BUILD-006` | superseded | DOOR-047: the record is the log, the exit status, and one GC root per built release tag. No receipt. | S6 step 3: PASS for root survival **R1/R2:** see 2.3. |
| `BUILD-007` | retained | Unchanged | Systems report |
| `BUILD-008` | superseded | DOOR-051: only outputs in the serving host's store are shared. | S6 step 4: PASS in a VM |
| `MOD-001` | superseded | V6 MOD-014 via DESC-002: native authored modules. P20 agrees (CONCEPT.md:92-93) | Native-module fixture, V6 evidence |
| `MOD-002` | superseded | V6 FACE-008 via FACE-005 | As MOD-001 |
| `MOD-003` | superseded | V6 FACE-008: no common `enable` | Inertness fixture |
| `MOD-004` | superseded | V6 MOD-014 via DESC-002 | As MOD-001 |
| `MOD-005` | superseded | V6 FACE-008 | As MOD-001 |
| `MOD-006` | superseded | V6 MOD-014 via DESC-002 | As MOD-001 |
| `MOD-008` | superseded | V6 MOD-014 | As MOD-001 |
| `MOD-009` | superseded | V6 MOD-014: all faces are native | As MOD-001 |
| `MOD-010` | superseded | V6 MOD-014; merge rules also under DOOR-023 | Priority matrix |
| `CORE-001` | retained | Unchanged | `nix eval .#lib` |
| `CORE-002` | retained | Unchanged | Remove an element; a variant breaks |
| `CORE-003` | retained | Unchanged | Check derivation references |
| `CORE-004` | retained | Unchanged | `nix-store -qR` on two variants |
| `CORE-005` | retained | Unchanged | Measure closure difference |
| `CORE-006` | retained | Unchanged (accepted cost) | Change the core; outputs change |
| `CORE-008` | retained | Unchanged | Inspect the lock of two variants |
| `ISO-001` | retained | Unchanged | `nvim` is not shadowed |
| `ISO-002` | retained | Unchanged | Conflicting `PATH` entry first |
| `ISO-003` | retained | Unchanged | Ignores the owner's config dir |
| `ISO-004` | retained | Unchanged | State under its own directory |
| `ISO-005` | retained | Unchanged | Run both |
| `ISO-007` | superseded | V6 `DEL-013` (retained): narrowed to library outputs. Reword "private cache" to shared cache. | Deny Vendomat and all substituters; a local build still works **R1/R2:** see 2.3. |
| `DEL-003` | superseded | V6 `MOD-014` (retained): no shared builder. | Library lock holds no Vendomat node **R1/R2:** see 2.3. |
| `DEL-004` | superseded | V6 `DEL-016` (retained). `fromToml` ends with the TOML runtime (DOOR-052, DOOR-054). | No machine file names a Vendomat path **R1/R2:** see 2.3. |
| `DEL-006` | retained | Unchanged. Matches DOOR-039 (keyless core). | Keyless VM boots with no `vendomat` command (S7: PASS on the fixture core) |
| `DEL-007` | retained | Unchanged (flake.nix:23-24). `launcher` is a second output | `nix flake show` |
| `DEL-008` | superseded | DOOR-056: a workspace carries the pinned Vendomat as the `vendomat` lock node and imports its module through the fragment. V6 `VMOD-001` stays retained. | Workspace lock holds a Vendomat node **R1/R2:** see 2.3. |
| `DEL-009` | superseded | V6 `DEL-013` (retained): narrowed to library outputs. | As GEN-019 **R1/R2:** see 2.3. |
| `DEL-010` | superseded | DOOR-030 and DOOR-031 (the launcher runs the pinned build for every command; `vendomat` in a pinned shell is the pinned build). V6 `VMOD-020` carries the shell part. | S5 section 5: PASS |
| `DEL-011` | superseded | DOOR-030 and DOOR-031. The pinned shell carries Vendomat; the host launcher is a small binary. | S5 section 5: PASS (in-shell case) |
| `DEL-012` | superseded | V6 `DEL-019` (retained) and DOOR-054 (after cutover no TOML reader, `sync`, or Attic path). | Rewrite `tests/test_repo_shape.py` and `tests/test_cli.py` **R1/R2:** see 2.3. |
| `CLI-001` | superseded | DOOR-033: the command surface and exit codes. `--help` lists exactly the built commands. | S5 sections 6 and 8: PASS on the prototype. Owner decision O4 for `path`, `check`, `bump` |
| `CLI-002` | retained | Unchanged. PLAN.md stage 4 exit-code fixtures | Failure-path tests |
| `CLI-003` | retained | Unchanged | JSON parses |
| `CLI-004` | retained | Unchanged | Byte-compare |
| `CLI-005` | open | O4 (command surface): not in DOOR-033. Recommend withdraw. | Owner decision O4 |
| `CLI-007` | retained | Unchanged. Built | Path exists |
| `CLI-008` | open | O4 (command surface): not in DOOR-033. Recommend withdraw. | Owner decision O4 |
| `CLI-009` | withdrawn | The host TOML ends (project 20 decision 7). `set` is not in DOOR-033. | None **R1/R2:** see 2.3. |
| `CLI-010` | withdrawn | Native `devenv machines plan` replaces it (V6 `MACH-005`). `diff` is not in DOOR-033. | None **R1/R2:** see 2.3. |
| `CLI-011` | superseded | V6 `MACH-005` (retained: forwarded native `devenv machines` commands) and DOOR-033 (`machines`). | Adopted-VM activation fixture (S7 task 5: PASS on the fixture) |
| `CLI-012` | superseded | V6 `MACH-005`. The dirty-tree refusal has no home yet; see V6 `MACH-022` (open) and section 11. | Decide the dirty-tree refusal |
| `CLI-013` | superseded | V6 `MACH-005`: `devenv machines rollback`. | VM rollback fixture |
| `CLI-014` | open | O4 (command surface), tied to `CLI-005`. | Owner decision O4 |
| `CLI-015` | withdrawn | The host TOML ends; as `CLI-009` and `CLI-010`. | None **R1/R2:** see 2.3. |
| `CLI-016` | open | O4 (`path` kept?) and O1 (flake archive route). A devenv workspace uses the lock NAR method (V6 `CLI-018`, retained). | Fixture in a devenv workspace with no network |
| `BOOT-001` | retained | Unchanged. DOOR-039 (keyless core). | Keyless QEMU boot (S7: PASS on the fixture core) |
| `BOOT-002` | superseded | DOOR-046: the core sets the shared-cache substituter and public key only when the inventory marks a cache host. A single-machine core sets none (DOOR-039). | S6 and S7: PASS **R1/R2:** see 2.3. |
| `BOOT-003` | retained | Unchanged | Remove an element; a machine fails |
| `BOOT-006` | retained | Unchanged. P20 gate 6 | QEMU boot |
| `BOOT-012` | retained | Unchanged. P20 gate 7; V6 BOOT-027 adds the store-image rule | Cold VM with a store image |
| `BOOT-015` | withdrawn | No laptop install exists; the Framework is adopted in place (V6 `BOOT-026`). | None **R1/R2:** see 2.3. |
| `BOOT-018` | superseded | DOOR-051: shared builds run on the serving host; no other host is a prerequisite. Names come from the inventory (DOOR-038). | Steps complete with the other host absent **R1/R2:** see 2.3. |
| `BOOT-019` | superseded | V6 `BOOT-026` (retained) and DOOR-051: an adopted host builds nothing locally. | Adoption VM log shows no compilation |
| `BOOT-020` | superseded | DOOR-051: no host except the serving host is a build prerequisite. | None **R1/R2:** see 2.3. |
| `BOOT-021` | retained | Owner-installation cutover rule. P19 §9, P20 gate 10 | Boot each drive from firmware. Blocked: owner action |
| `BOOT-022` | superseded | DOOR-043 (fresh install from a controller) and V6 `MACH-008` (retained). | S7 section 6: PASS (source VM) |
| `BOOT-023` | retained | Unchanged. CONCEPT.md:150-151 fresh mode | Old drive not written during install |
| `BOOT-024` | retained | Unchanged | Old ESP unchanged after install |
| `BOOT-016` | retained | Unchanged | Remove from core; both boot |
| `BOOT-017` | retained | Unchanged: a fan-out claim names the machines it covers. DOOR-051 states the one-direction rule. | Build on one, substitute on the other (S6 step 4 PASS) **R1/R2:** see 2.3. |
| `BOOT-008` | withdrawn | V6 withdrew it (blank slate). Framework adoption is not a conversion | None. Owner may want an adoption parity check (open item 7) |
| `BOOT-009` | withdrawn | V6 withdrew it. BOOT-001 and CONCEPT.md:150-151 cover the blank target | None |
| `BOOT-010` | withdrawn | V6 withdrew it (blank slate). Format migration is DOOR-052 | None |

### 2.2 The 17 NAT facts (V5)

A fact is an observation. It satisfies no requirement. Project 20 supersedes or withdraws none. Each stays as evidence.

| ID | Disposition | Note |
| --- | --- | --- |
| `NAT-001` | retained (fact) | retained as evidence |
| `NAT-002` | retained (fact) | retained as evidence; the TOML form ends (DOOR-004 keeps the package rule) |
| `NAT-003` | retained (fact) | retained as evidence |
| `NAT-004` | retained (fact) | history only: Attic is replaced |
| `NAT-005` | retained (fact) | retained as evidence |
| `NAT-006` | retained (fact) | V6 superseded it (NAT-018); fork inheritance (DVN-011) now matters |
| `NAT-007` | retained (fact) | retained as evidence |
| `NAT-008` | retained (fact) | retained and relied on: release roots (CONCEPT.md:133). Still marked "To observe"; P20 gate 7 must observe it |
| `NAT-009` | retained (fact) | retained as evidence; V6 NAT-019 supersedes. Harmonia changes the substitute route, not the copy route |
| `NAT-010` | retained (fact) | retained as evidence; bears on REG-013 |
| `NAT-011` | retained (fact) | retained as evidence; applies to the flake target only |
| `NAT-012` | retained (fact) | retained as evidence |
| `NAT-013` | retained (fact) | retained as evidence for the flake route; devenv behavior is closed by DOOR-036 (S9) |
| `NAT-014` | retained (fact) | retained as evidence |
| `NAT-015` | retained (fact) | retained as evidence |
| `NAT-016` | retained (fact) | retained as evidence (supports DOOR-055) |
| `NAT-017` | retained (fact) | retained as evidence |

### 2.3 Conflicts between R1 and R2, with the chosen view

Both records dispositioned these V5 IDs differently. The rule: spike evidence wins over document reading. When neither has a spike, the row gives the reason.

| ID | R1 view | R2 view | Chosen | Reason |
| --- | --- | --- | --- | --- |
| `REG-009` | superseded | closed in V6/V5 | superseded | R1 superseded (DOOR-019); R2 closed in V6 by `REG-025`. Both reach the same successors. Chosen: superseded. |
| `REG-011` | superseded | open | superseded | R1 superseded; R2 open (owner ruling, `PRE-005`). Chosen: superseded. S9 spike evidence beats document reading. |
| `REG-012` | withdrawn | superseded | superseded | R1 withdrawn; R2 superseded by DOOR-003 and DOOR-012. Chosen: superseded, because DOOR-020 keeps the duplicate-name intent. |
| `REG-013` | open | retained | superseded | R1 open (key set); R2 retained (lint rule). Chosen: superseded by DOOR-022 because S9 shows verbatim input fields. Judgment call; confirm with the owner. |
| `REG-021` | superseded | closed in V6/V5 | superseded | Both views reach the same successor; the chosen word follows the successor. |
| `GEN-005` | superseded | open | open | R1 superseded (header and digest); R2 open (flake target). Chosen: open, because DOOR-028 does not cover a generated `flake.nix`. |
| `GEN-006` | superseded | open | superseded | R1 superseded; R2 open (flake target). Chosen: superseded, because DOOR-007 covers every generated file. |
| `GEN-008` | superseded | retained | superseded | R1 superseded; R2 retained. Chosen: superseded, because DOOR-027 restates the clause for `devenv.lock`. |
| `GEN-017` | retained | open | retained | R1 retained; R2 open (flake target). Chosen: retained, because the rule also binds the fragment generator. |
| `GEN-019` | superseded | open | superseded | R1 superseded; R2 open (flake target). Chosen: superseded, because `DEL-013` covers the claim without the flake bridge. |
| `GEN-020` | retained | open | retained | R1 retained; R2 open (flake target). Chosen: retained. |
| `GEN-021` | superseded | open | superseded | R1 superseded; R2 open (flake target). Chosen: superseded (S9). |
| `GEN-022` | open | closed in V6/V5 | open | R1 open; R2 closed in V6 by `GEN-023`. `GEN-023` is itself open, so the row stays open. |
| `SYS-004` | retained | superseded | superseded | R1 retained; R2 superseded by DOOR-004. Chosen: superseded by DOOR-024 (S2). |
| `INP-006` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6. Same successor. |
| `INP-008` | superseded | open | superseded | R1 superseded; R2 open (flake target). Chosen: superseded (S9). The flake half follows O1. |
| `DISK-005` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6. Same successor. |
| `STORE-008` | superseded | retained | superseded | R1 superseded; R2 retained. Chosen: superseded, because the owner names must move to the inventory. |
| `STORE-012` | superseded | retained | retained | R1 superseded (clause of DOOR-051); R2 retained. Chosen: retained. |
| `STORE-017` | retained | open | retained | R1 retained; R2 open (command home). Chosen: retained. |
| `STORE-019` | retained | open | retained | R1 retained; R2 open. Chosen: retained. |
| `STORE-020` | retained | open | retained | R1 retained; R2 open. Chosen: retained. |
| `CACHE-001` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6 by `CACHE-010`. Same successor. |
| `CACHE-009` | superseded | withdrawn | superseded | R1 superseded; R2 withdrawn. Chosen: superseded, because the consumer clause survives in DOOR-046. |
| `BUILD-005` | superseded | withdrawn | superseded | R1 superseded; R2 withdrawn. Chosen: superseded; the intent lives in DOOR-050 and DOOR-051. |
| `BUILD-006` | superseded | retained | superseded | R1 superseded; R2 retained. Chosen: superseded, because the release roots change the scope text (SPEC-V5:612). |
| `ISO-007` | superseded | retained | superseded | R1 superseded; R2 retained (narrowed). Same successor. |
| `DEL-003` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6. Same successor. |
| `DEL-004` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6. Same successor. |
| `DEL-008` | superseded | closed in V6/V5 | superseded | R1 superseded (DOOR-056); R2 closed in V6 by `VMOD-001`. Chosen: superseded by DOOR-056. |
| `DEL-009` | superseded | retained | superseded | R1 superseded; R2 retained (narrowed). Same successor. |
| `DEL-012` | superseded | closed in V6/V5 | superseded | R1 superseded; R2 closed in V6 by `DEL-019`. Chosen: superseded by both. |
| `CLI-009` | withdrawn | open | withdrawn | R1 withdrawn; R2 open (owner ruling, recommends withdraw). Chosen: withdrawn, because the file it writes no longer exists. |
| `CLI-010` | withdrawn | open | withdrawn | R1 withdrawn; R2 open (recommends withdraw). Chosen: withdrawn. |
| `CLI-015` | withdrawn | open | withdrawn | R1 withdrawn; R2 open. Chosen: withdrawn. |
| `BOOT-015` | withdrawn | retained | withdrawn | R1 withdrawn; R2 retained (no P20 effect). Chosen: withdrawn. |
| `BOOT-018` | superseded | retained | superseded | R1 superseded; R2 retained (rename only). Chosen: superseded, because the owner name `server` moves to the inventory. |
| `BOOT-020` | withdrawn | retained | superseded | R1 withdrawn; R2 retained. Chosen: superseded by DOOR-051, which carries the independence clause. |
| `BOOT-017` | retained | superseded | retained | R1 retained; R2 superseded by DOOR-051. Chosen: retained, because DOOR-051 replaces `BUILD-008`, not this naming rule. |

Conflict rows: 39. The 18 IDs that only R1 dispositioned (the `MOD-*`, `CLI-001`, `CLI-011` to `CLI-013`, `BOOT-019`, `BOOT-022`, `BOOT-008` to `BOOT-010` rows) and the 4 that only R2 listed (`CACHE-004`, `SYS-002`, `SYS-003`, `SYS-005`, all closed earlier) have no conflict. R2 put the 18 in its closed groups; R1 judged each active V5 ID. The two views agree on the successor.

### 2.4 Unchanged history (37 rows, 42 IDs)

These IDs are already superseded or withdrawn. Project 20 changes none. The last column shows the final disposition of the existing successor.

| ID | V5 status | Existing successor | Successor disposition now |
| --- | --- | --- | --- |
| `REG-003` | superseded | REG-010 | `REG-010` retained |
| `REG-004` | withdrawn | (none) | none |
| `REG-005` | superseded | REG-013 | `REG-013` superseded |
| `REG-015` | superseded | REG-021 | `REG-021` superseded |
| `GEN-001` | superseded | GEN-015 | `GEN-015` open |
| `GEN-002` | superseded | GEN-013 then GEN-021 | `GEN-021` superseded |
| `GEN-003` | superseded | GEN-020 | `GEN-020` retained |
| `GEN-004` | superseded | GEN-016 | `GEN-016` open |
| `GEN-009` | superseded | GEN-014 then GEN-019 | `GEN-019` superseded |
| `GEN-010` | superseded | GEN-017 | `GEN-017` retained |
| `GEN-011` | superseded | GEN-017 | `GEN-017` retained |
| `GEN-012` | withdrawn | INP-006 and MOD-003 held the rule at the module boundary | `INP-006` superseded; `MOD-003` superseded |
| `GEN-013` | superseded | GEN-021 | `GEN-021` superseded |
| `GEN-014` | superseded | GEN-019 | `GEN-019` superseded |
| `SYS-002` | superseded | SYS-008 | `SYS-008` superseded |
| `SYS-003` | superseded | SYS-009 | `SYS-009` superseded |
| `SYS-005` | superseded | SYS-010 | `SYS-010` superseded |
| `INP-001` | superseded | INP-008 | `INP-008` superseded |
| `INP-002` | superseded | INP-007 | `INP-007` retained |
| `STORE-002` | superseded | STORE-009 | `STORE-009` open |
| `STORE-004` | superseded | STORE-010 | `STORE-010` retained |
| `STORE-011` | superseded | STORE-014 | `STORE-014` retained |
| `CACHE-004` | superseded | CACHE-009 | `CACHE-009` superseded |
| `MOD-007` | superseded | MOD-010 | `MOD-010` superseded |
| `PROJ-001 to PROJ-006` | withdrawn | GEN-016, GEN-017, GEN-019 hold the bridge rules | `GEN-016` open; `GEN-017` retained; `GEN-019` superseded |
| `CORE-007` | superseded | CORE-008 | `CORE-008` retained |
| `ISO-006` | superseded | ISO-007 | `ISO-007` superseded |
| `DEL-001` | superseded | DEL-006 | `DEL-006` retained |
| `DEL-002` | superseded | DEL-008 | `DEL-008` superseded |
| `DEL-005` | superseded | DEL-009 | `DEL-009` superseded |
| `CLI-006` | withdrawn | (none) `nix flake update` does the job | none |
| `BOOT-004` | superseded | BOOT-021 to BOOT-023 | `BOOT-021` retained; `BOOT-022` superseded; `BOOT-023` retained |
| `BOOT-005` | superseded | BOOT-021 | `BOOT-021` retained |
| `BOOT-007` | withdrawn | (none) one machine only | none |
| `BOOT-011` | superseded | BOOT-022 | `BOOT-022` superseded |
| `BOOT-013` | superseded | BOOT-014 then BOOT-018 | `BOOT-018` superseded |
| `BOOT-014` | superseded | BOOT-018 | `BOOT-018` superseded |

Also unchanged: the 19 withdrawn `RES-001` to `RES-012` and `EMIT-001` to `EMIT-007` (SPEC-V5 lines 288 to 300). Project 20 agrees: the concept refuses a second transitive resolver (DOOR-036).

## 3. V6 requirement IDs (122 IDs, from R2 section 1)

**ID collision.** Project 18 proposed `DVN-011` for "the cache holds the fork build". SPEC-V6 already defines `DVN-011` as fork inheritance (patch 0007). The project 18 proposal is withdrawn (section 6). The V6 meaning holds. Do not reuse the ID.

| ID | V6 status | Disposition | Successor or reason | Proof needed |
| --- | --- | --- | --- | --- |
| `BOOT-026` | proposed | retained | Applies to any adopted host; the builder is the serving host. Name stays owner-neutral in the successor. | Adoption VM: deploy log and builder log show no compile on the target. |
| `BOOT-027` | active | retained | DOOR-045 to DOOR-049 and P20 gate 7 need the same store-image rule. | Cold-substitution VM with useNixStoreImage. |
| `BOOT-028` | active | retained | Core still needs efibootmgr for the one-time boot entry. | Existing step-7 evidence; real firmware open. |
| `BUILD-009` | active | withdrawn | Its reason is attic watch-store, which P19 removes (P19 CONCEPT.md:135, :140). | None. |
| `CACHE-010` | active | superseded | DOOR-046: clients set the Harmonia substituter and public key from the inventory mark; no pull secret; none when no host is marked. | nix config show lists the key; nix.conf has no netrc-file for this cache. |
| `CACHE-011` | active | superseded | DOOR-048: a path absent from the serving store answers 404; `nix path-info` exits 1 with "is not valid"; the client falls back. | Absent-path fixture on Harmonia. |
| `CACHE-012` | proposed | superseded | DOOR-050: a live Harmonia check replaces the Attic live-cache checks. | testee check against the Harmonia route. |
| `CACHE-013` | active | withdrawn | No Attic database, so no pool keys or patch (P19 CONCEPT.md:135). | None. |
| `CLI-017` | superseded | closed earlier | Closed by CLI-021 in V6. | None. |
| `CLI-018` | active | retained | Holds: `path <name>` works in a devenv workspace from `devenv.lock` with no network. The command is in DOOR-033 (O4). | tests/test_commands_v6.py equivalent on vendomat.yaml workspace. |
| `CLI-019` | active | retained | Holds: `check` runs the pin, version, and fragment checks. The fragment check merges with DOOR-029. The command is in DOOR-033 (O4). | Injected-problem fixture on a yaml workspace. |
| `CLI-020` | active | retained | Holds: `bump` edits `vendomat.yaml` refs (DOOR-019 allows a named command to write it). Awaits O4. | Fleet fixture on yaml workspaces; comment-preserving edit. |
| `CLI-021` | active | superseded | DOOR-033: `shell`, `build`, `test`, `tasks`, `up`, `update`, `machines`, `prepare`, `path`, `check`, plus pass-through. `sync` and `push` end. `bump` awaits O4. | --help lists exactly the built commands. |
| `DEL-013` | active | retained | Library outputs build with no Vendomat; unaffected by the front door. | Existing check on a library. |
| `DEL-014` | decided | closed earlier | Decided in V6; chain ends at DEL-020, now DOOR-030 and DOOR-031. | None. |
| `DEL-015` | superseded | closed earlier | Closed in V6. | None. |
| `DEL-016` | active | retained | Basix installation reaches Vendomat through its own input. Basix/Vendomat split is open (P19 DECISIONS.md:45-48). | No machine file names a Vendomat path. |
| `DEL-017` | superseded | closed earlier | Closed by DEL-020 in V6. | None. |
| `DEL-018` | superseded | closed earlier | Closed in V6. | None. |
| `DEL-019` | active | retained | Flake still exports packages.vendomat and devenvModules.default. flake.nix also exports packages.launcher. | nix flake show; tests/test_repo_shape.py. |
| `DEL-020` | proposed | superseded | DOOR-030 (launcher routing; it restores the small-launcher, NAR-hash lookup, no-network, and host-release clauses) and DOOR-031. | Launcher fixtures for new workspace, pinned workspace, missing pin, outside workspace. |
| `DESC-001` | superseded | closed earlier | Closed in V6. | None. |
| `DESC-002` | superseded | closed earlier | Closed by MOD-014 in V6. | None. |
| `DESC-003` | superseded | closed earlier | Closed by MOD-014 in V6. | None. |
| `DISK-008` | superseded | closed earlier | Closed by DISK-009 in V6. | None. |
| `DISK-009` | proposed | retained | Guards stay (P20 CONCEPT.md:146-149). | Existing VM evidence; real hardware open. |
| `DVN-001` | active | retained | One pinned devenv. Fork tag moves to .3. | devenv version and command -v on a host. |
| `DVN-002` | active | retained | require_version enforced. | Existing fixture. |
| `DVN-003` | active | retained | Text is stale: it names six patches and tag .1; the series now holds 0001 to 0008 (fork .3). | devenv-dist/materialize --verify against the .3 commit. |
| `DVN-004` | active | retained | Holds, but where the pin lives is not settled. DOOR-019 forbids edits to `devenv.yaml`; `require_version` has no home in `vendomat.yaml` (R2 defect 4 on DOOR-001). See section 11. | Fleet pin check. |
| `DVN-005` | active | retained | No change. | Existing fixture. |
| `DVN-006` | active | superseded | DOOR-051 (open clause: the serving host's store holds the pinned devenv build; a cold host substitutes it). | nix build --dry-run on a cold host with Harmonia. |
| `DVN-007` | active | retained | Bump checklist gains patches 0007 and 0008 rebase items. | Bump log. |
| `DVN-008` | active | retained | Offline shell entry; P20 gate 3 relies on it. VMOD-008 inputPaths and release roots keep the sources. | dist-fixture offline case (10 of 10 on .3). |
| `DVN-009` | proposed | retained | Adopted-host refusal before contact, all phases and modes. DOOR-037 says 'preserve disk guards'. | devenv-dist/fixtures/cli-fixture; adoption VM. |
| `DVN-010` | active | retained | Fresh-install phase-set refusal. Unchanged by P20. | cli-fixture and VM step. |
| `DVN-011` | proposed | retained | Fork inheritance. It replaces PRE-003 and PRE-004. DOOR-036 builds on it and supersedes PRE-005. It does not replace VMOD-005. Fork-only until PR #3055 lands. A consumer entry wins silently. | inherit-fixture 9 of 9 passes; P20 gate 2 repeats it through the front door. |
| `DVN-012` | proposed | retained | Cold first entry without sync prefetch. P20 gate 1 (no lock) needs it. | Cold first-entry fixture through the front door. |
| `FACE-001` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-002` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-003` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-004` | decided | closed earlier | Decided in V6; closed. | None. |
| `FACE-005` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-006` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-007` | superseded | closed earlier | Closed in V6. | None. |
| `FACE-008` | proposed | retained | Per-target authored modules match P20 decision 3 and MDL-002. | Devenv-only and NixOS-only module fixtures. |
| `GEN-023` | active | open | O1 (flake target). The brief recommends withdrawing the flake target. | Owner ruling; then nix flake show. |
| `MACH-001` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-002` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-003` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-004` | active | retained | Deploy public key is data; no private key. | Loopback VM with pinned host key. |
| `MACH-005` | active | retained | Forwarding after preparation is not wrapping (DECISIONS.md:11). Tension with MACH-022 and DECISIONS.md:11 if the front door adds gates. | Fixture: forwarded command receives identical arguments. |
| `MACH-006` | active | retained | Conflicts with a keyless first boot unless DOOR-039 holds (step-7.md N1). | Keyless VM: systemctl --failed empty. |
| `MACH-007` | active | retained | install.secrets is an optional route (P20 CONCEPT.md:159). | VM steps install-fresh and payload-on-installed-disk. |
| `MACH-008` | active | retained | Owner-instance route (running server to localhost). P20 adds a controller or live installer (CONCEPT.md:150-152). Command name follows DOOR-033. | Real hardware stays open. |
| `MACH-009` | active | retained | Owner-instance firmware step. | Real firmware. |
| `MACH-010` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-011` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-012` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-013` | superseded | closed earlier | Closed in V6. | None. |
| `MACH-014` | proposed | retained | Adoption without disk phases; DOOR-037. | Adoption VM A1. |
| `MACH-015` | proposed | retained | disko input and facter report per host. | Direct NixOS builds. |
| `MACH-016` | proposed | retained | Target-bound preflight and adopted-host read-only comparison. | step-7 injection cases (25 + 10); adopted comparison fixture. |
| `MACH-017` | proposed | retained | Home Manager inside the NixOS role. | VM A10 and A11. |
| `MACH-018` | proposed | retained | Text says sync must report an override: read per the rename rule (section 10). | Override report fixture. |
| `MACH-019` | proposed | retained | Plain nixpkgs; DVN-008 offline. | Lock node check. |
| `MACH-020` | proposed | retained | Root SSH key and pinned host key before first apply to an adopted host. | VM A7. |
| `MACH-021` | active | retained | Patched CLI runs the preflight. Reads machines.<host>.vendomat, set by the module from the inventory. | cli-fixture; VM dirty and clean disk steps. |
| `MACH-022` | proposed | open | Owner ruling needed; the brief gives no O number (see section 9, item "MACH-022"). The front door would run the failed-unit gate before `deploy` and `apply`, which conflicts with `MACH-005`. | Gate fixture plus bypass fixture. |
| `MACH-023` | proposed | superseded | DOOR-037: the inventory path moves from `vendomat.inventory` to `basix.machines`; guards apply unchanged. | devenv machines info lists each host once. |
| `MACH-024` | active | retained | Preflight refuses wrong phases, disko-mode, and unresolved protected paths. | step-7 matrix. |
| `MACH-025` | active | retained | Wrapper passes sshOpts and port; command name follows DOOR-033. | tests/test_machine_install.py. |
| `MACH-026` | active | retained | Secret consumers fail loudly. Basis for DOOR-039. | Keyless VM. |
| `MOD-011` | superseded | closed earlier | Closed in V6. | None. |
| `MOD-012` | superseded | closed earlier | Closed in V6. | None. |
| `MOD-013` | superseded | closed earlier | Closed by MOD-014 in V6. | None. |
| `MOD-014` | proposed | retained | Native authored modules match P20 decision 3. | Authored module composes with no vendomat attribute in its flake. |
| `PRE-001` | active | open | O1 (flake target): `[targets]` disappears with TOML; the flake target needs the owner ruling. | Owner ruling. |
| `PRE-002` | active | superseded | DOOR-028 (the `.vendomat/` file set, header, digest) with DOOR-021 (canonical JSON data). | Fixture: generated set equals DOOR-028 and unchanged input rewrites no file. |
| `PRE-003` | active | superseded | V6 `DVN-011` (retained) and DOOR-036: the fork inherits input-style imports; Vendomat reads no input's inputs. | P20 gate 2 on pinned tools. |
| `PRE-004` | active | superseded | V6 `DVN-011` (retained) and DOOR-036: nested `follows` is native. | inherit-fixture. |
| `PRE-005` | active | superseded | DOOR-036: native `follows`; Vendomat adds no edge. Three limits do not carry over (no detection, no differing-child report, target and depth limits); the owner must accept them (S9). | Lock node count per source in a four-flake fixture. |
| `PRE-006` | active | superseded | DOOR-029: the module-wide stale guard covers every config-reading evaluation, including a hand-edited fragment. | Registry edit, hand edit, and build/machines fixtures. |
| `PRE-007` | active | retained | Warn when devenv.yaml or devenv.local.yaml redeclares a generated input. Read per the rename rule (section 10). | Redeclared-input fixture. |
| `PRE-008` | active | retained | Step 2 of CONCEPT.md:100 still must judge a lock update by contents, not devenv update's exit status (NAT-026). | Unreachable-input fixture. |
| `PRE-009` | active | superseded | DOOR-034 (`use vendomat` for direnv) with DOOR-028 (`prepare`). | Stale and failed-prepare cases. |
| `PRE-010` | active | retained | P20 gate 9 records startup time. Budget needs a number that includes schema load. | Timing on warm and full entry. |
| `PRE-011` | active | retained | Atomic replace, new mtime, clear eval cache. Agrees with DOOR-007. | Same-size swap fixture. |
| `PRE-012` | superseded | closed earlier | Closed by PRE-013 in V6. | None. |
| `PRE-013` | proposed | superseded | DOOR-023: the JSON reader replaces the `fromTOML` bridge. | Priority matrix; template-created workspace. |
| `REG-022` | superseded | closed earlier | Closed in V6. | None. |
| `REG-023` | active | superseded | DOOR-022: `dir=` is a native URL query on a devenv input; no `dir` key. The out-of-input check moves to the linter. | Lint fixture for dir= that leaves the input. |
| `REG-024` | active | superseded | DOOR-022 (reserved key `imports`; native `<input>/<dir>` list). | Accepted and rejected imports. |
| `REG-025` | active | retained | Only bump and the converter write vendomat.yaml. The front door writes .vendomat/ only. Read per the rename rule (section 10). | Byte-identical vendomat.yaml after every command. |
| `REG-026` | superseded | closed earlier | Closed in V6. | None. |
| `REG-027` | proposed | superseded | DOOR-003 (kept) and DOOR-022: `[settings.<module>]` becomes a real option path (`vendomat.settings.<module>` where a module declares it); DOOR-024 maps values. | Consumer fixture. |
| `SEC-001` | superseded | closed earlier | Closed in V6. | None. |
| `SEC-002` | proposed | retained | Proposed. SecretSpec SOPS provider for workspaces, only when a secret is needed. | Workspace fixture. |
| `SEC-003` | proposed | superseded | DOOR-042 (no mandatory host secret module; SecretSpec is controller-side) and DOOR-040 (the post-install delivery route). | VM: secret read after install, deploy, reboot; none in store. |
| `VMOD-001` | active | retained | Every workspace imports the module. Where inputs.vendomat is declared is open (vendomat.yaml or stub). | Lock node has refs/tags. |
| `VMOD-002` | superseded | closed earlier | Closed by WS-007 in V6. | None. |
| `VMOD-003` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-004` | active | retained | Hard checks are assertions. | Existing e2e. |
| `VMOD-005` | active | retained | Tag-pin assertion over every git node, direct or inherited. Needed more now: DVN-011 imports third-party pins. | Branch pin stops the shell. |
| `VMOD-006` | active | retained | Applies to build. The 'or pushes' part is withdrawn with push. | Branch pin builds nothing. |
| `VMOD-007` | superseded | closed earlier | Closed by VMOD-021 in V6. | None. |
| `VMOD-008` | active | retained | Keeps input sources in the output closure; supports offline entry (DVN-008) and release roots. | nix-store -qR lists the sources. |
| `VMOD-009` | active | retained | Host paths; independent of P20. | Shell shows variables; real host file open. |
| `VMOD-010` | active | superseded | DOOR-038: host and user names come from the inventory. | Defaults come from inventory. |
| `VMOD-011` | active | superseded | DOOR-037: the same single-definition guard at the new option path. | Direct definition refused naming the host. |
| `VMOD-012` | superseded | closed earlier | Closed by VMOD-016 in V6. | None. |
| `VMOD-013` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-014` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-015` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-016` | proposed | superseded | DOOR-037: mode and disk assertions move to the Basix option path; meaning unchanged. | 12 bad layouts fail, 2 good pass, both modes. |
| `VMOD-017` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-018` | superseded | closed earlier | Closed in V6. | None. |
| `VMOD-019` | proposed | retained | Import selected modules once; unresolved selection stops before shell entry (DOOR-027). | Two-module consumer; unknown selection fails. |
| `VMOD-020` | proposed | retained | Pinned vendomat on the shell PATH. vendomat:check runs 'vendomat check', which P20 does not list (DOOR-033). | command -v vendomat; tasks list. |
| `VMOD-021` | proposed | withdrawn | Attic push task and script leave with vendomat push (DOOR-050). | None. |
| `WS-007` | proposed | superseded | DOOR-019 (workspace file contract) and DOOR-033; no `sync` step; `vendomat.yaml` replaces TOML. | Template workspace through the front door. |
| `WS-008` | proposed | retained | Ownership labels and no overwrite of user edits. Needed for the devenv.nix escape hatch. | Generate, run twice, compare; edit user file. |

## 4. V6 NAT facts (31 facts, retained as facts)

A fact satisfies no requirement. Each fact stays as evidence. `NAT-039` and `NAT-040` are moot because the description format is withdrawn. `NAT-034` was superseded by `NAT-044` in V6.

| ID | Disposition | P20 effect |
| --- | --- | --- |
| `NAT-018` | retained (fact) | True for stock devenv. The fork (DVN-011) changes the behavior. |
| `NAT-019` | retained (fact) | Bears on BOOT-026 and cache fan-out. |
| `NAT-020` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-021` | retained (fact) | Bears on the flake target decision (GEN-005). |
| `NAT-022` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-023` | retained (fact) | Cachix-only substituters; why the core sets nix.settings. |
| `NAT-024` | retained (fact) | Basis for VMOD-004 and DOOR-029 (guard must be an assertion). |
| `NAT-025` | retained (fact) | Basis for DOOR-029 gap: build and eval do not run assertions. |
| `NAT-026` | retained (fact) | Basis for PRE-008. |
| `NAT-027` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-028` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-029` | retained (fact) | Basis for VMOD-011 and DOOR-037. |
| `NAT-030` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-031` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-032` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-033` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-034` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-035` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-036` | retained (fact) | Stock fact; the fork carries nested follows. |
| `NAT-037` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-038` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-039` | retained (fact) | Moot: the description format is withdrawn. |
| `NAT-040` | retained (fact) | Moot: the description builder is withdrawn. |
| `NAT-041` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-042` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-043` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-044` | retained (fact) | Basis for MACH-006 and DOOR-039. |
| `NAT-045` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-046` | retained (fact) | Observation about a tool; no P20 effect. |
| `NAT-047` | retained (fact) | Dagu fact; no P20 effect. |
| `NAT-048` | retained (fact) | Observation about a tool; no P20 effect. |

## 5. Project 17 MDL rows judged (12 rows, from R2 section 4)

The other 30 MDL rows concern the `devenv-py` oracle, normalizer, corpus, and writer. They have no project 20 effect and are not judged.

| ID | Disposition | Successor or note |
| --- | --- | --- |
| `MDL-001` | retained | Basis for DOOR-025 (schema export from declarations at the pins). S3 shows the neutral-data export. A YAML-facing validator is new work (DOOR-027). |
| `MDL-002` | retained | Same as project 20 decision 3 and DOOR-003. |
| `MDL-006` | retained | Basis for DOOR-026. The key hashes the lock, so it covers every imported input (R2 placeholder 07); S3 section 7 PASS. |
| `MDL-008` | retained | An unmapped type becomes a named unsupported-type fault (DOOR-024, DOOR-027). |
| `MDL-009` | retained | A narrowed model adds no field the option tree lacks. Keeps validation honest (DOOR-027). |
| `MDL-011` | retained | Only subtrees that pass RT1 to RT8 at the pin are supported. Other options validate as far as the type tree reaches. |
| `MDL-014` | retained | Curated layer for Basix learners; not needed for Vendomat itself. |
| `MDL-015` | retained | Type recognition rules (DOOR-025). |
| `MDL-016` | retained | The export fails on `depthCut`. At runtime a deep option could block the front door. Open sub-question: fail closed or report unsupported (no owner number; section 9). |
| `MDL-021` | retained | FnMarker for function-typed options matches "values with no safe data form use native Nix" (DOOR-024). |
| `MDL-029` | retained | Strict scalar types match Nix. DOOR-020 admits int64 only and rejects floats, so the float versus int question is closed at the lint (S1 PASS). |
| `MDL-035` | retained | Renamed and alias options have no field. A user may write one; the schema and Nix disagree. Open sub-question, no fixture (section 9). |

## 6. Project 18 proposed IDs (11 rows, never adopted)

The owner chose Harmonia in project 19. Project 18 recommended a static directory cache. The P18 `DVN-011` row is withdrawn and keeps its label only to mark the collision with V6 `DVN-011`.

| ID | Disposition | Successor or reason |
| --- | --- | --- |
| `CACHE-014` | withdrawn | Static directory cache (candidate B). The owner chose Harmonia (project 19). |
| `CACHE-015` | withdrawn | SSH-forced publish. Project 19 decision 3 forbids push from other hosts. |
| `CACHE-016` | superseded | DOOR-048: a path absent from the serving store answers 404 and the client builds locally. |
| `CACHE-017` | superseded | DOOR-048 (visibility). The read-only clause ("the read route accepts no write") is not in the brief text of DOOR-048; see section 11. |
| `CACHE-018` | withdrawn | Upstream filtering is removed (project 19). DOOR-046 keeps upstream caches first. |
| `CACHE-019` | superseded | DOOR-046: the core sets the URL and public key from the inventory mark; no pull secret. |
| `CACHE-020` | superseded | DOOR-050: the Harmonia live check replaces the publish live check. |
| `CACHE-021` | withdrawn | No publish step exists, so no killed publish. |
| `BUILD-010` | withdrawn | The builder publishes with `nix copy`; project 19 builds on the serving host. Intent lives in DOOR-047 and DOOR-051. |
| `DVN-011 (P18)` | withdrawn | ID collision with V6 `DVN-011` (fork inheritance). The P18 text "the cache holds the fork build" was never adopted. Intent: the open clause of DOOR-051. The V6 meaning of `DVN-011` holds. |
| `VMOD-022` | withdrawn | Task without the Attic variable. Project 19 removes the push task (DOOR-050). |

## 7. Project 19 decisions (10 decisions; no requirement IDs)

| # | Decision | Disposition | Successor or note |
| --- | --- | --- | --- |
| 1 | Basix is the minimal devenv configuration; Vendomat is its source, store, and cache layer | retained | Layer split in the concept. Which repository declares the inventory is owner decision O2. |
| 2 | No off-host or off-disk copy of the cache | retained | Carried in the concept; consistent with DOOR-048 and DOOR-051. |
| 3 | No push from other hosts | retained | DOOR-050 removes `push`; DOOR-051 states one-direction sharing. |
| 4 | Harmonia is the one store server; a signed, read-only binary cache | retained | DOOR-045 to DOOR-049. The "read-only" word is not in a DOOR row (section 11). |
| 5 | Cache wiring from the inventory; key made at setup; public key committed | closed earlier | Project 19 already superseded it by decisions 8 and 10. Wiring from the inventory: DOOR-046. |
| 6 | Each built release tag gets a GC root; GC only under disk pressure | retained | DOOR-047. |
| 7 | SecretSpec is required configuration from the first setup | superseded | DOOR-042: SecretSpec is never a host requirement. Project 19 had already superseded it by decisions 8 and 9. This replaces the stale memory entry "SecretSpec required at setup". |
| 8 | A fresh Basix install boots and works without private keys | retained | DOOR-039 (keyless boot) and DOOR-040 (later key). S7 PASS on the fixture core. |
| 9 | SecretSpec becomes required when the first secret is needed | superseded | DOOR-042 (judgment call): S7 route 1 needs no SecretSpec on the host. R2 marked it retained; spike evidence S7 wins. The orchestrator should confirm (section 11). |
| 10 | Generate and deliver the signing key before enabling the cache server; commit the public key first | retained | DOOR-045 (start only after the key), DOOR-049 (key outside the store), DOOR-046 (client trust). S6 PASS. |

The project 19 "open for planning" items: item 1 (secret delivery) is DOOR-040 (fixture-proved route 1); item 2 (code split) is owner decision O2; item 3 is outside this ledger. The listed defaults (listen interface, `min-free`, release-root limit) stay planning choices; the bind address is an inventory setting (DOOR-048).

## 8. DOOR-001 to DOOR-056

| ID | Disposition | Successor or status |
| --- | --- | --- |
| `DOOR-001` | superseded | DOOR-019 |
| `DOOR-002` | closed earlier | superseded by DOOR-011, which `DOOR-027` supersedes (chain DOOR-002, DOOR-011, DOOR-027) |
| `DOOR-003` | retained | kept; refined by DOOR-022 |
| `DOOR-004` | retained | kept; refined by DOOR-024 |
| `DOOR-005` | closed earlier | superseded by DOOR-012, which `DOOR-020` supersedes |
| `DOOR-006` | closed earlier | superseded by DOOR-013, which `DOOR-023` supersedes |
| `DOOR-007` | retained | kept |
| `DOOR-008` | retained | kept; refined by DOOR-025 |
| `DOOR-009` | superseded | DOOR-029 |
| `DOOR-010` | superseded | DOOR-030 and DOOR-031 |
| `DOOR-011` | superseded | DOOR-027 |
| `DOOR-012` | superseded | DOOR-020 |
| `DOOR-013` | superseded | DOOR-023 |
| `DOOR-014` | superseded | DOOR-035 |
| `DOOR-015` | superseded | DOOR-037 |
| `DOOR-016` | superseded | DOOR-039 (keyless boot) and DOOR-040 (later key) |
| `DOOR-017` | superseded | DOOR-045 to DOOR-049 |
| `DOOR-018` | superseded | DOOR-052 |
| `DOOR-019` | proposed | workspace file contract |
| `DOOR-020` | proposed | YAML grammar |
| `DOOR-021` | proposed | canonical JSON data |
| `DOOR-022` | proposed | reserved keys and inputs |
| `DOOR-023` | proposed | merge rule |
| `DOOR-024` | proposed | value mapping |
| `DOOR-025` | proposed | schema export |
| `DOOR-026` | proposed | schema cache |
| `DOOR-027` | proposed | command sequence |
| `DOOR-028` | proposed | committed `.vendomat/`, `prepare` |
| `DOOR-029` | proposed | stale guard |
| `DOOR-030` | proposed | launcher routing |
| `DOOR-031` | proposed | release report |
| `DOOR-032` | proposed | pinned devenv build and fragment pin |
| `DOOR-033` | proposed | command surface and exit codes |
| `DOOR-034` | proposed | direnv |
| `DOOR-035` | proposed | secret literals |
| `DOOR-036` | proposed | native follows |
| `DOOR-037` | proposed | Basix inventory |
| `DOOR-038` | proposed | no owner defaults |
| `DOOR-039` | proposed | keyless core |
| `DOOR-040` | proposed | post-install secret route |
| `DOOR-041` | proposed | admin key and host-key re-pin |
| `DOOR-042` | proposed | SecretSpec never a host requirement |
| `DOOR-043` | proposed | fresh install route |
| `DOOR-044` | proposed | adopted host runs no disk tool |
| `DOOR-045` | proposed | Harmonia activation |
| `DOOR-046` | proposed | client trust |
| `DOOR-047` | proposed | release roots |
| `DOOR-048` | proposed | visibility |
| `DOOR-049` | proposed | signing key location |
| `DOOR-050` | proposed | cutover removes push and Attic |
| `DOOR-051` | proposed | one-direction sharing |
| `DOOR-052` | proposed | migration by hand |
| `DOOR-053` | proposed | transition launcher |
| `DOOR-054` | proposed | no TOML, `sync`, Attic after cutover |
| `DOOR-055` | open | source modes and collection work. Owner decision O3. |
| `DOOR-056` | proposed | workspace carries pinned Vendomat |

## 9. Open items

Each row names the owner decision (O1 to O9 in the brief) or the fixture that closes it.

| ID or item | Why open | Closes with |
| --- | --- | --- |
| `REG-016` (V5) | O3 (source modes, DOOR-055): the example writes the full `git://` URL; no forge shorthand exists. The brief recommends dropping the shorthand. | Owner decision O3. |
| `REG-018` (V5) | O3 (source modes, DOOR-055): `mirror` moves to the option path `vendomat.sources.<input>.mode` if the owner accepts it. | Owner decision O3. |
| `REG-019` (V5) | O3 (source modes, DOOR-055): `keep` as for REG-018. | Owner decision O3. |
| `REG-020` (V5) | O3: `backup` has no home in P20. The brief recommends dropping it. | Owner decision O3. |
| `GEN-005` (V5) | O1 (flake target): the claim concerns a generated `flake.nix`. The header clause for `.vendomat/` files is in DOOR-028. Withdrawn if O1 withdraws the flake target. | Owner decision O1. |
| `GEN-007` (V5) | O1 (flake target): applies only if a generated `flake.nix` stays. | Owner decision O1. |
| `GEN-015` (V5) | O1 (flake target). The devenv target already adds a default `nixpkgs`, so the claim fails there. | Owner decision O1. |
| `GEN-016` (V5) | O1 (flake target). | Owner decision O1. |
| `GEN-018` (V5) | O1 (flake target); the command name `sync` also ends. | Owner decision O1. |
| `GEN-022` (V5) | O1 (flake target), through V6 `GEN-023` (open). | Owner decision O1. |
| `STORE-009` (V5) | O3 (source modes and collection commands, DOOR-055). | Owner decision O3. |
| `STORE-016` (V5) | O3 (command) and O1 (the `flake.nix` write): both the command and the file change. | Owner decision O1 and O3. |
| `STORE-018` (V5) | O3 (collection commands, DOOR-055). | Owner decision O3. |
| `STORE-021` (V5) | O3 (collection commands, DOOR-055). | Owner decision O3. |
| `STORE-022` (V5) | O3 (collection commands, DOOR-055). The hook route (`STORE-023`) already works. | Owner decision O3. |
| `CLI-005` (V5) | O4 (command surface): not in DOOR-033. Recommend withdraw. | Owner decision O4. |
| `CLI-008` (V5) | O4 (command surface): not in DOOR-033. Recommend withdraw. | Owner decision O4. |
| `CLI-014` (V5) | O4 (command surface), tied to `CLI-005`. | Owner decision O4. |
| `CLI-016` (V5) | O4 (`path` kept?) and O1 (flake archive route). A devenv workspace uses the lock NAR method (V6 `CLI-018`, retained). | Owner decision O1 and O4. |
| `GEN-023` (V6) | O1 (flake target). The brief recommends withdrawing the flake target. | Owner decision O1. |
| `MACH-022` (V6) | Owner ruling needed; the brief gives no O number (see section 9, item "MACH-022"). The front door would run the failed-unit gate before `deploy` and `apply`, which conflicts with `MACH-005`. | Owner ruling; the brief assigns no O number. |
| `PRE-001` (V6) | O1 (flake target): `[targets]` disappears with TOML; the flake target needs the owner ruling. | Owner decision O1. |
| `DOOR-055` | Source modes and collection work: proposed option `vendomat.sources.<input>.mode`. | Owner decision O3. |
| Fixture gaps with no owner number | V6 `MACH-022` (failed-unit gate before deploy; conflicts with `MACH-005`); P17 `MDL-016` (fail closed or report unsupported on `depthCut`); `MDL-035` (renamed options). | An owner ruling for `MACH-022`; a depth fixture and a renamed-option fixture. |
| O2 (basix name, declaring repository) | Affects `DOOR-037`, `DEL-016`, project 19 decision 1. | Owner decision O2. |
| O5 (Attic removal timing) | Affects `DOOR-050`. | Owner decision O5: keep Attic push and live checks until the Harmonia live gate passes. |
| O6 (disk space) | Blocker for more VM work. `btrfs balance` needs root. | The owner runs the balance. |
| O7 (real disk and hardware authorization) | Blocker for cutover gates and real adoption. | Owner authorization. |
| O8 (adopted-host capability comparison) | V5 `BOOT-008` parity was withdrawn for the blank slate; adoption is not blank. | Owner decision O8: a read-only service and unit comparison report before the first adopted switch. |
| O9 (fresh-install route for real devices) | `DOOR-043` proves only a source VM. | Owner decision O9: live installer image with a temporary key first, kexec later. |
| `DOOR-051` open clause | The serving host's store holds the pinned devenv build; unproved. | A cold-host fixture. |

## 10. Rename rule (R2 placeholder 27)

In retained V6 text, "vendomat sync" reads as the front door's generate step, and "vendomat.toml" reads as `vendomat.yaml`. This is a reading rule. It is not a requirement and has no ID. It applies to retained V6 rows such as `MACH-018`, `PRE-007`, `PRE-008`, and `REG-025`.

Retained V5 rows marked "Rename:" in section 2.1 follow the same rule: only a file or command name changes.

## 11. Unmapped spike claims and review items

The orchestrator should review these. Each claim fits no DOOR ID in the brief, or the brief text omits a clause that a source row needs.

- **Read-only cache clause.** P19 decision 4 and P18 `CACHE-017` say the cache accepts no write. No DOOR text says it. Suggest a clause in `DOOR-048`.
- **Tag-pin exemption.** R1 placeholder 2 says infrastructure inputs (`nixpkgs`, `devenv`) take no tag pin. `REG-017` and V6 `VMOD-005` assert tags on every git node. The brief does not say which rule wins for `nixpkgs`. `DOOR-022` records only that they are ordinary `inputs` entries.
- **`MACH-022` and `MACH-005`.** Whether the front door may run the failed-unit gate before `deploy` and `apply` has no owner number (R2 decision 15). It also touches V5 `CLI-012` (dirty-tree refusal).
- **Installer reach (R2 placeholder 28).** Mapped to `DOOR-043`, but `DOOR-043` does not state that the installer reaches source and cache with no secret. Project 19 closes this by design (Harmonia has no pull credential); no fixture runs it.
- **Secret removal verb (S7 recommendation 7).** `DOOR-040` states the rollback rule. The removal command has no name or ID.
- **Route 4 (sops-nix with a first-boot host key), S7 recommendation 5.** An evaluation item with no ID.
- **Project 19 decision 9** treated as superseded by `DOOR-042` (see section 7). R2 kept it. Confirm.
- **`REG-013` superseded by `DOOR-022`.** R1 left it open (key set) and R2 retained it. The brief mapping does not name `REG-013`. Confirm.
- **Spike facts that support a DOOR ID but state no requirement.** S4: NixOS has 26903 leaf options, 98.5 % of the 25093 settable ones have a data or reference form, 47 have none; Home Manager has 5896 leaf options, 31 with none; `imports` is not an option; a custom option type name is unknown to a schema generator (support `DOOR-024`, `DOOR-025`). S5: the assertion and `mkIf` coverage matrix; `devenv tasks run` captures the shell environment; a failed task before `enterShell` does not stop `shell`; the eval cache keys on content, not mtime; `imports: [./.vendomat]` fails when the directory is missing; Testee 0.6.1 evaluates before `testee.prepare`; stock devenv locks the inputs of a local import; `devenv gc` blocks with no output (incident 1) (support `DOOR-028`, `DOOR-029`). S6: the stock Harmonia module degrades the system on the first request without a key; Harmonia serves a `.drv` with no release root; Harmonia reads the key only at start (support `DOOR-045`, `DOOR-048`). S7: the fork `install.*` payloads are install-only (supports `DOOR-040`).
- **Pin location (`DVN-004`, `CLI-020`).** `require_version` and the `inputs.devenv` pin sit in `devenv.yaml` today. `DOOR-019` says Vendomat never edits `devenv.yaml`. Neither the brief nor `DOOR-022` says where `require_version` lives. R2 raised this as defect 4 on `DOOR-001`.
- **Exit-code collision in `DOOR-033`.** S5 notes that codes 64 to 72 can collide with a user command code. `DOOR-033` lists the proof need but no rule.

## 12. Duplicate check

Two IDs that make the same claim, with the one that holds.

| IDs | Shared claim | Holds |
| --- | --- | --- |
| `DOOR-007`, V5 `GEN-006`, V6 `PRE-011` | Write a generated file only when its content changes | `DOOR-007`. `GEN-006` is superseded by it. `PRE-011` adds atomic replace and a new mtime; it stays retained and does not conflict. |
| `DOOR-052`, `DOOR-054` | No runtime path reads `vendomat.toml` after cutover | `DOOR-054` (the repo-shape test). `DOOR-052` cites it for the migration records. |
| V6 `VMOD-020`, `DOOR-031` | In a pinned shell, `vendomat` is the pinned build | `VMOD-020` for the shell PATH install. `DOOR-031` adds the release report and keeps the in-shell clause by reference. |
| V6 `MACH-014`, `DOOR-044` | An adopted host runs no install, disko, or kexec step | `MACH-014` holds the rule. `DOOR-044` adds the executed-binaries proof. |
| V6 `VMOD-001`, `DOOR-056` | A workspace imports the Vendomat module; the pin is a release tag | `VMOD-001` holds the import and tag rule. `DOOR-056` decides where the pin lives (the `vendomat` lock node). |
| V6 `REG-025`, V5 `REG-007`, `DOOR-019` | Only a named command writes `vendomat.yaml` | `REG-025` names `bump` as the writer. `DOOR-019` holds the byte-identical rule for every other command. `REG-009` is superseded. |
| V5 `GEN-020`, `DOOR-036` | No transitive input in generated output | `DOOR-036` for the fragment; `GEN-020` for a generated `flake.nix` if O1 keeps it. |
| `DOOR-027`, V5 `GEN-008`, `DOOR-011` | Vendomat does not write the lock; devenv does | `DOOR-027`. |
| `DOOR-046`, V6 `CACHE-010`, P18 `CACHE-019`, V5 `CACHE-001`, `BOOT-002` | Client substituter and public key from the inventory mark | `DOOR-046`. |
| `DOOR-048`, V6 `CACHE-011`, P18 `CACHE-016`, V5 `CACHE-005` | An absent path answers 404 | `DOOR-048`. |
| `DOOR-049`, V5 `CACHE-002` | The signing key stays out of tracked files, the store, and logs | `DOOR-049`. |
| `DOOR-050`, V6 `CACHE-012`, P18 `CACHE-020`, V6 `VMOD-021`, P18 `VMOD-022` | Remove push and Attic checks; add a Harmonia live check | `DOOR-050`. |
| `DOOR-047`, V5 `BUILD-006`, P19 decision 6, P18 `BUILD-010` | Release roots and the build record | `DOOR-047`. |
| `DOOR-051`, V5 `BUILD-008`, `BOOT-018`, `BOOT-020`, V6 `DVN-006`, P18 `DVN-011` | Only the serving host shares; no host prerequisite; the fork build is in the cache | `DOOR-051`. It cites V5 `STORE-012`, which stays retained. |
| `DOOR-023`, V5 `SYS-010`, V6 `PRE-013` | Native merge; JSON reader | `DOOR-023`. |
| `DOOR-024`, V5 `SYS-004`, `SYS-009`, P17 `MDL-029` | Package-typed options take attribute names; missing names fail with the key | `DOOR-024`. |
| `DOOR-020`, `DOOR-012`, `DOOR-005` | The linter grammar | `DOOR-020`. |
| `DOOR-035`, `DOOR-014` | Reject secret literals | `DOOR-035`. |
| `DOOR-037`, V6 `VMOD-011`, `VMOD-016`, `MACH-023` | Inventory guards at the Basix option path | `DOOR-037`; the guard IDs `DVN-009`, `DVN-010`, `MACH-016`, `MACH-021`, `MACH-024` stay retained. |
| `DOOR-039`, V5 `BOOT-001`, `DEL-006` | The core boots without Vendomat and without a private key | Different claims (no Vendomat process; no private key). No conflict; both hold. |
| `DOOR-042`, P19 decisions 7 and 9, V6 `SEC-002` | SecretSpec requirement | `DOOR-042`. `SEC-002` (an optional SOPS provider for workspaces) stays retained. |
| `DOOR-033`, V6 `CLI-021`, V5 `CLI-001` | Command surface | `DOOR-033`. |
| `DOOR-030`, V6 `DEL-020`, V5 `DEL-010`, `DEL-011`, `DOOR-010` | Launcher routing | `DOOR-030`. |
| `DOOR-029`, V6 `PRE-006`, `DOOR-009` | Stale guard | `DOOR-029`. |
| `DOOR-028`, V6 `PRE-002`, V5 `GEN-005` (the `.vendomat/` header only) | Generated file set, header, digest | `DOOR-028`. |
| `DOOR-022`, `DOOR-003`, V5 `REG-021`, V6 `REG-023`, `REG-024`, `REG-027` | Reserved keys; native `dir=` and `imports` | `DOOR-003` keeps the reserved-key rule; `DOOR-022` refines it. |

### 11.1 Orchestrator resolution (2026-10-11)

- **Read-only cache.** Added to `DOOR-048`: the cache accepts no write. Harmonia has no upload route.
- **Tag-pin exemption.** The tag rule (`REG-017`, V6 `VMOD-005`) applies to inputs that the collection
  serves. `nixpkgs` and `devenv` are infrastructure inputs. They take no tag, and `devenv.lock` alone
  pins them. This keeps R1 placeholder 2.
- **`MACH-022` and `MACH-005`.** New owner decision O10 in [DECISIONS.md](../DECISIONS.md). The
  recommendation: the front door runs the failed-unit gate before `deploy` and `apply`, as a named
  exception to `MACH-005`.
- **Installer reach.** Added to `DOOR-043`: the installer reaches source and cache with no secret.
  No fixture proves it.
- **Secret removal command.** Slice 9 names it. No ID until a fixture exists.
- **Route 4 (sops-nix with a first-boot host key).** An optional slice 9 evaluation. No ID.
- **Project 19 decision 9 and `REG-013`.** Confirmed as written in this map.

## 12. Vendomat collection branch ruling (2026-10-12)

Project 20 decision R5 and `DOOR-076` add one exception to `STORE-014`: the `vendomat`
repository accepts fast-forward updates to `refs/heads/release`. It still refuses branch deletion,
rewind, and every other branch. All other collection repositories remain tag only. The V5 ledger
keeps its original wording as history.

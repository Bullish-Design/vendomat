# R1: V5 requirement dispositions under project 20

**Date:** 2026-10-11. **Task:** R1. **Status:** research input. It changes no requirement. It allocates no ID.

## 1. Sources and method

Paths are relative to `/home/andrew/Documents/Projects/vendomat`.

- `.scratch/projects/14-vendomat-local/SPEC-V5.md` (the 207 table rows, parsed by script).
- `.scratch/projects/14-vendomat-local/REFINEMENT-2026-10-08.md` (`PATH-*`, `DISK-*`).
- `.scratch/projects/14-vendomat-local/prelim-verification/DECISIONS.md` (supersession chains).
- `.scratch/projects/20-vendomat-front-door/{CONCEPT,DECISIONS,REQUIREMENTS,PLAN}.md`.
- `.scratch/projects/16-vendomat-devenv-layer/{SPEC-V6,LEDGER-V6}.md` (V6 is a draft; its supersessions count as evidence, not as accepted).
- `.scratch/projects/19-vendomat-foundation-layer/{CONCEPT,DECISIONS}.md` and `.scratch/projects/18-single-disk-cache-concept/REQUIREMENTS-DELTA.md`.
- Code read only to judge implementation: `src/vendomat/{cli,registry,devenvgen,push,check,lockpath}.py`, `nix/devenv-module/`, `launcher/vendomat`, `flake.nix`, `tests/test_cli.py`, `tests/test_repo_shape.py`.

**Method.** A script extracted every ID row of SPEC-V5. It classified each row as active, superseded, withdrawn, or narrowed from the row text. I wrote one disposition per active or narrowed ID by hand. A second script checked that every such ID has exactly one row here. Raw extraction: `~/.local/state/vendomat/p20/2026-10-11/R1/rows.txt`.

**Placeholders.** `NEW[Nn]` marks a successor claim that needs an ID. Section 6 defines each one once. `O-...` marks an open item. Section 5 defines each one. A successor named "V6 X (draft)" is a proposal of project 16. The V6 mapping agent decides whether project 20 adopts it.

**Disposition rule.** `retained` means the claim holds. `Rename:` in the successor column means only a file or command name in the text changes. The orchestrator may restate those IDs by reference. `superseded` needs a new or existing successor. `withdrawn` needs a reason. `open` names the fixture or decision.

**Count correction.** The task and `CURRENT.md:98` say 194 IDs and 151 active. SPEC-V5 tables give 195 and 152 (`SPEC-V5.md:42`, `KICKOFF-V5.md:15`). This report covers 152 active IDs plus the 1 narrowed ID `BOOT-015`: 153 IDs. It also lists 17 `NAT-*` facts apart.

## 2. Disposition table (153 active or narrowed IDs)

| ID | Original claim (short) | V5 status | P20 disposition | Successor or reason | Evidence or fixture needed |
| --- | --- | --- | --- | --- | --- |
| `REG-001` | One `[inputs]` table; each key is an input name | active | superseded | NEW[N1]: `inputs` is one YAML map of named direct inputs; duplicate keys fail | YAML corpus with duplicate-key case (DOOR-012 fixture). Today: built for TOML (registry.py) |
| `REG-002` | Input name matches `[a-z0-9][a-z0-9-]*` | active | retained | Rename: applies to `inputs` keys in `vendomat.yaml` | Linter unit test; check the rule against devenv-native input names |
| `REG-006` | Unknown key in an input entry is an error naming the key | active | retained | Rename: YAML entry. DOOR-011 adds file and line. The key set itself is O-KEYS | Accepted and rejected YAML corpus |
| `REG-007` | Registry lists only directly requested inputs; byte-identical after a run | active | retained | CONCEPT.md:127-129 keeps direct inputs only | Front-door run leaves `vendomat.yaml` byte-identical |
| `REG-008` | `[passthrough]` entries copied verbatim into generated inputs | active | superseded | NEW[N2]: infrastructure inputs (nixpkgs, devenv) are ordinary `inputs` entries with no tag pin | Fixture with `nixpkgs` as an `inputs` entry on the pinned fork |
| `REG-009` | Only `add` and `remove` write the registry | active | superseded | NEW[N3]: only named commands write `vendomat.yaml`; every other command leaves it byte-identical | Byte-compare after each command. `add`/`remove` are not built; `bump` writes today (V6 REG-025) |
| `REG-010` | Portable source URL; a local checkout uses an explicit Nix input override | active | retained | Holds. CONCEPT.md:127-130 | Fixture: devenv input override on the fork leaves the lock unchanged |
| `REG-011` | `[follows]` maps a direct input to root inputs; one edge per pair | active | superseded | NEW[N4]: follows edges use native devenv `follows` under `inputs` | Follows fixture on the pinned fork (see REG-014) |
| `REG-012` | A name must not sit in both `[inputs]` and `[passthrough]` | active | withdrawn | P20 has one `inputs` map, so the case cannot occur. Duplicate keys: NEW[N1] | None |
| `REG-013` | `url`/`flake` become input attributes; `ref`/`rev` become URL query parameters | active | open | O-KEYS: the CONCEPT example puts `?ref=` in the URL (CONCEPT.md:76); no separate `ref`/`rev` key is defined | Decide the key set; fixture on pinned fork (NAT-010 covers flake only) |
| `REG-014` | Reject a follows entry whose target or child is invalid | active | open | O-FOLLOWS: devenv follows behavior on non-flake and absent children is unproved | Fixture on the fork: follows on a `flake: false` input, an absent child, a missing target |
| `REG-016` | Entry with no `url` resolves to `<forge url>/<repo>` | active | open | O-KEYS: the P20 example writes the full `git://` URL; no `[forge]` equivalent exists | Owner decision on forge shorthand |
| `REG-017` | Every `inputs` entry pins a tag; branch, bare rev, or no pin is an error | active | retained | CONCEPT.md:127 (tag-pinned sources). The exemption for infrastructure inputs moves to NEW[N2] | Existing pin unit tests rewritten for YAML |
| `REG-018` | `mirror = true` only on an entry with its own `url`; never changes the URL | active | open | O-KEYS: CONCEPT.md:130 keeps mirroring but defines no key | Owner decision on the key location; store fixture unchanged |
| `REG-019` | `keep = true` asks each machine to hold a persistent clone | active | open | O-KEYS: CONCEPT.md:130 keeps clones but defines no key | As REG-018 |
| `REG-020` | `backup` is an optional URL, never in generated output | active | open | O-KEYS: P20 is silent. Recommend withdraw: the V5 doc says no command uses it | Owner decision |
| `REG-021` | A top-level table other than the four known ones is an error | active | superseded | DOOR-003 (reserved keys) and DOOR-011/DOOR-012 (fault with location) | Corpus with an unknown top-level key. V6 chain REG-022, REG-026, REG-027 is also moot |
| `GEN-005` | Generated file opens with a header naming tool version and registry digest | active | superseded | NEW[N5]: each generated file names the generator version and the digest of its inputs | Header check on `.vendomat/` files |
| `GEN-006` | Output is byte-identical for an unchanged registry; no rewrite | active | superseded | DOOR-007 (same claim for all generated files) | Run twice; compare mtime and bytes |
| `GEN-007` | Refuse to overwrite a `flake.nix` with no generated header | active | open | O-FLAKE: applies only if a generated `flake.nix` stays | Decide O-FLAKE |
| `GEN-008` | Never read or write `flake.lock` | active | superseded | NEW[N6]: Vendomat never writes `devenv.lock`; devenv writes it. Reads are allowed | Lock byte-identical after every command. Today `path` and `check` read `devenv.lock` (lockpath.py) |
| `GEN-015` | `inputs` has one entry per name; no `devenv`, `nixpkgs`, or Vendomat input of its own | active | open | O-FLAKE. The devenv target already adds a default nixpkgs (defaults.py:10-11), so the claim fails there | Decide O-FLAKE and the default-input rule |
| `GEN-016` | `outputs` is the fixed bridge to `flake-outputs.nix` | active | open | O-FLAKE | Decide O-FLAKE |
| `GEN-017` | Generator never scans or imports a module face of any input | active | retained | P20 `imports` is a user list (CONCEPT.md:61). V6 already keeps it | Scan generated body for face names |
| `GEN-018` | `sync` fails before any write when `flake-outputs.nix` is missing | active | open | O-FLAKE; the command name `sync` also ends | Decide O-FLAKE |
| `GEN-019` | A project output builds with no Vendomat input and no Vendomat command | active | superseded | V6 DEL-013 (draft) narrows it to library outputs. Reword "private cache" to shared cache | Library output built with a PATH of nix and git only |
| `GEN-020` | Generated file names no transitive input | active | retained | Holds, and P20 strengthens it (CONCEPT.md:128-129). Code still walks imports (devenvgen.py:167-208) | Remove the walk after the fork inheritance fixture (patch 0007) passes |
| `GEN-021` | Write `<child>.inputs.nixpkgs.follows` per `[follows]` pair | active | superseded | NEW[N4] | As REG-011 |
| `GEN-022` | Generator emits no `devShells`, `mkShell`, or `devenv` input | active | open | O-FLAKE (V6 GEN-023 draft restates it for `flake.nix`) | Decide O-FLAKE |
| `SYS-001` | Host file has one `[options]` table of dotted option paths; a bad path fails evaluation | active | superseded | DOOR-003 (every other key is a real option path) and DOOR-011 | Corpus with a non-option key |
| `SYS-004` | An unresolvable package name is an error naming key and name | active | retained | Holds; DOOR-004 adds file and line. Resolution happens in Nix | Fixture `["ripgrepp"]` on the pinned nixpkgs |
| `SYS-006` | TOML must not express a function, conditional, interpolation, or option reference | active | superseded | NEW[N7]: values with no safe data form are unsupported; Vendomat names the limit and never coerces | Rejected-value corpus (P20 gate 5) |
| `SYS-007` | Scalars, strings, booleans, integers, and scalar lists round-trip | active | superseded | NEW[N8]: YAML data values evaluate to the same value as native Nix | P20 gate 4 matrix across scalar, list, attribute-set options |
| `SYS-008` | `fromToml` returns a valid NixOS module with nested options | active | superseded | DOOR-013 and NEW[N8]: a JSON reader in each target. `fromToml` is not in this repository | Generated config evaluates in devenv, NixOS, and Home Manager |
| `SYS-009` | Package-name conversion only at package-valued option paths | active | superseded | DOOR-004 (package-typed options only) | Type-driven fixture: string list vs package list |
| `SYS-010` | TOML and Nix definitions merge by native option-type rules | active | superseded | DOOR-013 (native merge plus the priority matrix) | Priority matrix on pinned devenv and Nix |
| `INP-003` | A buildable input exports `packages.<system>.<name>` | active | retained | Unchanged. Library-author rule | `nix build .#<name> --json` |
| `INP-004` | A core input exports `lib`, a function | active | retained | Unchanged | `nix eval .#lib --apply builtins.isFunction` |
| `INP-005` | An input declares releases as `v<semver>` git tags | active | retained | Unchanged; matches CONCEPT.md:127 | `git tag --list` |
| `INP-006` | Importing a face activates nothing until `enable` is true | active | superseded | V6 FACE-008 (draft): selected modules activate; no common `enable` | V6 inertness fixture (derivations equal with and without import) |
| `INP-007` | An input may export only the faces it implements | active | retained | Unchanged; CONCEPT.md:92-93 says module authors write native modules | Evaluate each exported face alone |
| `INP-008` | Flake inputs declare dependencies in their own flake; Vendomat never requires `devenv.yaml` | active | superseded | NEW[N18]: an imported source declares its inputs; the pinned devenv fork inherits them; Vendomat parses neither | Fork inheritance fixture (patch 0007, DVN-011) with Vendomat's walk removed |
| `PATH-001` | A host declares one absolute path per logical path name | active | retained | Built as `vendomat.paths` (nix/devenv-module/default.nix:131-137). The data source moves to `vendomat.yaml` | Fixture: two inputs read one name |
| `PATH-002` | An input uses a named path at evaluation and at runtime | active | retained | Unchanged (VENDOMAT_PATH_<NAME>, default.nix:210) | Existing module fixture |
| `PATH-003` | A mutable path stays a string; no copy into the store | active | retained | Unchanged | Change a file; build inputs stay equal |
| `PATH-004` | A missing path name fails evaluation and names the requesting input | active | retained | Unchanged | Evaluate an undeclared name |
| `DISK-001` | A host records each drive by stable hardware identifier | active | retained | Unchanged. CONCEPT.md:79-80, REQUIREMENTS.md DOOR-015 (inventory uses `byId`) | Resolve each entry through `/dev/disk/by-id/` |
| `DISK-002` | Reject a format target that backs the running root or boot | active | retained | Unchanged. Basix guard (DECISIONS.md decision 4) | Read-only preflight on the root drive |
| `DISK-003` | Reject a missing identifier or any model, serial, size, mount, signature mismatch | active | retained | Unchanged. Basix guard | Inject each mismatch (guard.nix, preflight.nix) |
| `DISK-004` | Local mounts use filesystem or partition UUIDs | active | retained | Unchanged | Inspect evaluated `fileSystems` |
| `DISK-005` | After formatting, record actual UUIDs and check them against the drive | active | superseded | V6 DISK-009 (draft: declare UUIDs before format). Owner moves to Basix | V6 disko fixture; adoption VM compares GPT and UUIDs |
| `DISK-006` | The new server install has its own ESP and leaves the 512 GB drive intact | active | retained | Owner-installation cutover rule. P19 §9 keeps it | Inspect both drives after install. Blocked: PV-02 scan, owner action |
| `DISK-007` | A service with separate-mount data requires that mount | active | retained | Unchanged | Unmount a test disk; service does not start |
| `STORE-001` | Clones live at `~/vendor/<name>`, overridable by `VENDOMAT_SOURCE_ROOT` | active | retained | Unchanged. Built (store.py) | Existing unit test |
| `STORE-003` | The store step never changes a dirty working tree; it reports | active | retained | Rename: command name `sync` ends; the vehicle is O-STORECMD | Dirty a tree; exit status 1 for that input |
| `STORE-005` | A `rev` or path pin to a sibling checkout is used in place | active | retained | Unchanged | Resolved url names the sibling path |
| `STORE-006` | Generated inputs use a portable remote URL by default | active | retained | Unchanged. CONCEPT.md:127 | Move the consumer; evaluate again |
| `STORE-007` | A local checkout needs an explicit input override; the env variable alone changes nothing | active | retained | Unchanged | Compare lock hashes with and without the variable |
| `STORE-008` | One collection on `server` at `/home/andrew/vendor/<repo>`, served over `git://` to the tailnet; server sleeps when idle | active | superseded | NEW[N9]: one collection per installation; tag-only repositories; read-only `git://` daemon; host, path, and interface are inventory facts | P19 removes owner-specific assumptions (CONCEPT.md:139-143, 19/CONCEPT.md §8). Daemon idle-cost fact stays (NAT-016) |
| `STORE-009` | `sync` clones a missing `keep` or `mirror` entry and fetches an existing one | active | open | O-STORECMD (the command) and O-KEYS (the flags) | Decide the vehicle; keep PV-20 fixture |
| `STORE-010` | Collection rebuilds from authoring repos by pushing tags again; clones are caches | active | retained | Holds. CONCEPT.md:135-136 (source and tags are the record). Not built today | Delete a collection repo, push tags again, compare tag lists |
| `STORE-012` | No step requires a source path to be present in Attic | active | superseded | NEW[N10]: no step requires a source path in the shared cache | Consumer locks and evaluates with only the collection configured |
| `STORE-014` | Only new release tags enter the collection; `pre-receive` refuses the rest and any tag move | active | retained | Unchanged. CONCEPT.md:127 (immutable tags) | PV-18 two-machine test |
| `STORE-015` | Daemon serves only marked repositories; no push over `git://`; port 9418 open on the tailnet interface only | active | retained | Rename: "tailnet interface" becomes the installation's named interface (19/DECISIONS.md network row) | PV-18 plus an interface-neutral NixOS test |
| `STORE-013` | A collection working tree shows the newest release tag | active | retained | Rename: the hook carries it (`hooks/collection-post-receive`). The `sync` route is O-STORECMD | PV-20, PV-22 fixtures |
| `STORE-016` | `sync` writes `flake.nix` before store work; exit codes 0, 1, 2 | active | open | O-STORECMD, O-FLAKE: both the command and the file change | Decide the command; keep the exit-code contract |
| `STORE-017` | Clone directory is `$VENDOMAT_SOURCE_ROOT` (default `~/vendor`) plus repo name | active | retained | Unchanged. The `repo` key and forge clone follow O-KEYS | PV-20 unit tests |
| `STORE-018` | `mirror` acts only under `sync --collection` | active | open | O-STORECMD | Decide how the collection host runs the mirror step |
| `STORE-019` | A clean `keep` or `mirror` clone shows its pinned tag | active | retained | Unchanged | PV-20 |
| `STORE-020` | Git runs as a subprocess with explicit args, no prompt, a timeout, no credential in messages | active | retained | Unchanged (store.py) | PV-20 unit tests |
| `STORE-021` | `--dry-run` changes nothing and reports refusals | active | open | O-STORECMD | Decide whether the front door has a dry run |
| `STORE-022` | `sync --collection` checks out the newest tag in each marked repository | active | open | O-STORECMD | Decide vehicle; hook route (STORE-023) already works |
| `STORE-023` | A `post-receive` hook refreshes the tree after a tag push | active | retained | Unchanged. Built, installed on `devman` (PV-22) | PV-21, PV-22 |
| `CACHE-001` | Consumer module adds the cache as substituter and its public key as trusted | active | superseded | DOOR-017 (trust public key, keep fallback) and NEW[N11]: trust derives from the inventory mark | Two-machine cold substitution; `nix config show` on a client |
| `CACHE-002` | Push credential never in a tracked file, store path, or log | active | superseded | NEW[N12]: the Harmonia signing key never appears in a tracked file, store path, or log (DOOR-014 covers generated files only) | Grep tracked files, closure, and logs |
| `CACHE-003` | A pull-only credential is refused on push | active | withdrawn | No push route and no credential exist (19/DECISIONS.md decision 3). Harmonia is read-only | None |
| `CACHE-005` | A path never pushed reports absent, never success | active | superseded | NEW[N13]: Harmonia serves every valid path in the host store; a path not in that store answers 404 | Absent-path fixture (P20 gate 7); network reach must match store visibility |
| `CACHE-006` | `attic watch-store` runs on every builder | active | withdrawn | No Attic and no watch-store. The serving host builds shared outputs (NEW[N14]) | None |
| `CACHE-007` | A cold consumer obtains a cached output with no local build | active | retained | Holds for Harmonia. P20 gate 7 | Cold VM with a store image (V6 BOOT-027), `--max-jobs 0` |
| `CACHE-008` | NAR hash of a served output equals the build hash | active | retained | Holds. Observed for Harmonia (19/CONCEPT.md §10) | Compare both hashes in the two-VM run |
| `CACHE-009` | Builder reports an upstream skip; consumers keep the source cache as substituter | active | superseded | DOOR-017 (fallback kept). Upstream filtering is dropped (19/CONCEPT.md §8) | Cache failure fixture: absent path falls back to upstream |
| `BUILD-001` | The builder builds each registry input separately | active | retained | Rename: each collection release tag (CONCEPT.md:132-133). Not built | P20 stage 6 builder fixture |
| `BUILD-002` | A new tag triggers that input's build only | active | retained | Rename as BUILD-001. Not built | Tag one input; only it builds |
| `BUILD-003` | Builder logs command, exit status, and output paths per build | active | retained | Unchanged. Not built | Log check |
| `BUILD-004` | A failed build does not stop the others | active | retained | Unchanged. Not built | Break one input; others build |
| `BUILD-005` | Builder never pushes explicitly; `watch-store` moves paths | active | superseded | NEW[N14]: no Vendomat command publishes outputs; the serving host's store is the cache | Check that `push` is removed. Today `push` pipes to `attic push` (push.py:73-97) |
| `BUILD-006` | Build log and exit status are the only durable record; no receipt | active | superseded | NEW[N15]: the record is the log, the exit status, and one GC root per built release tag; no receipt | Release-root survives GC fixture (P20 gate 7). Conflicts with SPEC-V5.md:612 |
| `BUILD-007` | Every target is `x86_64-linux` while that holds | active | retained | Unchanged | Systems report |
| `BUILD-008` | A build on either machine becomes substitutable by the other | active | superseded | NEW[N14]: shared outputs build on the serving host; an output built only elsewhere is not shared | Two-VM fixture; the P18 delta (REQUIREMENTS-DELTA.md BUILD-008 "Keep") assumed push |
| `MOD-001` | `mkModules` takes `{ name, options, packages, extra }` and returns three faces | active | superseded | V6 MOD-014 via DESC-002 (draft): native authored modules. P20 agrees (CONCEPT.md:92-93) | Native-module fixture, V6 evidence |
| `MOD-002` | Options land at `<name>.*` and `programs.<name>.*` | active | superseded | V6 FACE-008 via FACE-005 (draft) | As MOD-001 |
| `MOD-003` | Every face declares `enable`, default false | active | superseded | V6 FACE-008 (draft): no common `enable` | Inertness fixture |
| `MOD-004` | `packages` is `cfg: pkgs: [ derivation ]` | active | superseded | V6 MOD-014 via DESC-002 (draft) | As MOD-001 |
| `MOD-005` | Three faces install to `packages`, `environment.systemPackages`, `home.packages` | active | superseded | V6 FACE-008 (draft) | As MOD-001 |
| `MOD-006` | `extra` is `cfg: pkgs: { <face> = <content>; }` | active | superseded | V6 MOD-014 via DESC-002 (draft) | As MOD-001 |
| `MOD-008` | An `extra` key for one face stays out of the others | active | superseded | V6 MOD-014 (draft) | As MOD-001 |
| `MOD-009` | A hand-written face stays possible beside a generated one | active | superseded | V6 MOD-014 (draft): all faces are native | As MOD-001 |
| `MOD-010` | Install paths and `extra` use native module merging | active | superseded | V6 MOD-014 (draft); merge rules also under DOOR-013 | Priority matrix |
| `CORE-001` | A core exports `lib`, a function returning a build | active | retained | Unchanged | `nix eval .#lib` |
| `CORE-002` | A core holds only what every consumer needs | active | retained | Unchanged | Remove an element; a variant breaks |
| `CORE-003` | A variant is produced by calling the core's `lib` | active | retained | Unchanged | Check derivation references |
| `CORE-004` | Variants of one core share all common store paths | active | retained | Unchanged | `nix-store -qR` on two variants |
| `CORE-005` | A variant's own content is wrapper, config, additions only | active | retained | Unchanged | Measure closure difference |
| `CORE-006` | A core change rebuilds every variant | active | retained | Unchanged (accepted cost) | Change the core; outputs change |
| `CORE-008` | A variant names its core in its own flake inputs | active | retained | Unchanged | Inspect the lock of two variants |
| `ISO-001` | A variant binary has a distinct name | active | retained | Unchanged | `nvim` is not shadowed |
| `ISO-002` | A caller reaches a variant by absolute store path | active | retained | Unchanged | Conflicting `PATH` entry first |
| `ISO-003` | An editor variant sets `wrapRc = true` | active | retained | Unchanged | Ignores the owner's config dir |
| `ISO-004` | An isolated editor variant sets `NVIM_APPNAME` | active | retained | Unchanged | State under its own directory |
| `ISO-005` | Enabling a variant changes no setting of the daily tool | active | retained | Unchanged | Run both |
| `ISO-007` | Executing an accepted output needs no Vendomat process and no private cache | active | superseded | V6 DEL-013 (draft) narrows it to library outputs. Reword "private cache" to shared cache | Deny Vendomat and all substituters; a local build still works |
| `DEL-003` | A module-authoring repo may declare Vendomat as a flake input for `mkModules` | active | superseded | V6 MOD-013 then MOD-014 (draft): no shared builder | Library lock holds no Vendomat node |
| `DEL-004` | `fromToml`/`fromInventory` come through `nix-meta`'s Vendomat input | active | superseded | V6 DEL-016 (draft: `nix-meta` retired). `fromToml` ends with the TOML runtime (DOOR-018) | No machine file names a Vendomat path |
| `DEL-006` | The shared machine core boots without the Vendomat CLI | active | retained | Unchanged. Matches DOOR-016 and CONCEPT.md:154-156 | Keyless VM boots with no `vendomat` command |
| `DEL-007` | CLI package is `packages.<system>.vendomat`; `.default` is not the CLI | active | retained | Unchanged (flake.nix:23-24). `launcher` is a second output | `nix flake show` |
| `DEL-008` | No consumer declares Vendomat as a flake input | active | superseded | NEW[N20]: how an ordinary workspace carries the pinned Vendomat (O-VMOD). V6 VMOD-001 (draft) said every workspace imports the module | Workspace lock holds a Vendomat node (CONCEPT.md:55-57 needs one) |
| `DEL-009` | Executing an accepted output needs no Vendomat process, package, or input | active | superseded | V6 DEL-013 (draft) narrows it to library outputs | As GEN-019 |
| `DEL-010` | A host with the CLI makes `vendomat` reachable from an existing project shell | active | superseded | DOOR-010 (launcher serves every command with the pinned build); supersedes V6 DEL-020 | Shell re-entry and bypass fixtures (P20 stage 4) |
| `DEL-011` | The CLI is not installed through devenv or the boot core | active | superseded | DOOR-010 and CONCEPT.md:120-123 (the pinned shell carries Vendomat) | Pinned-shell fixture without the host launcher |
| `DEL-012` | The repository holds V5 only; `sync` and `path` are the surface | active | superseded | V6 DEL-019 (draft) already; NEW[N19]: after cutover no TOML, `sync`, or Attic path remains in the runtime (PLAN.md stage 7) | Rewrite `tests/test_repo_shape.py` and `tests/test_cli.py` |
| `CLI-001` | Surface is exactly 13 named commands | active | superseded | NEW[N17]: P20 command surface (`shell`, `build`, `test`, `machines`, pass-through, kept utilities); `--help` lists exactly the built commands | Decide O-CLI. Built today: sync, path, check, push, bump, machine (tests/test_cli.py:12) |
| `CLI-002` | Every command exits non-zero on failure and names the cause | active | retained | Unchanged. PLAN.md stage 4 exit-code fixtures | Failure-path tests |
| `CLI-003` | Every read command supports `--json` | active | retained | Unchanged | JSON parses |
| `CLI-004` | A read command changes no lock, registry, or selection | active | retained | Unchanged | Byte-compare |
| `CLI-005` | `status` reports registry entry, lock revision, store revision, cache presence per input | active | open | O-CLI: V6 deferred it; P20 has no `status`. Recommend withdraw | Owner decision |
| `CLI-007` | `path <name>` prints the store path of that input | active | retained | Unchanged. Built | Path exists |
| `CLI-008` | `explore <name>` opens the editor in that repo | active | open | O-CLI: V6 deferred it; P20 is silent. Recommend withdraw | Owner decision |
| `CLI-009` | `set <path> <value>` writes only the host TOML | active | withdrawn | The host TOML ends (DECISIONS.md decision 7). V6 deferred it; P20 settles it | None |
| `CLI-010` | `diff` evaluates the host config before and after and reports the option delta | active | withdrawn | Native `devenv machines plan` replaces it (V6 MACH-005; DECISIONS.md decision 4) | None |
| `CLI-011` | `apply` drives `nixos-rebuild switch` and reports its status | active | superseded | V6 MACH-005 (draft): native `devenv machines` commands; CONCEPT.md:146-149 | Adopted-VM activation fixture (P20 gate 8) |
| `CLI-012` | `apply` refuses a host file with uncommitted changes unless forced | active | superseded | V6 MACH-005 (draft). The commit gate has no P20 home; see O-CLI | Decide whether Basix or the front door keeps a dirty-tree refusal |
| `CLI-013` | `rollback` selects the prior system generation | active | superseded | V6 MACH-005 (draft): `devenv machines rollback` | VM rollback fixture |
| `CLI-014` | `status` reports a store revision ahead of the locked one as drifted | active | open | O-CLI, tied to CLI-005 | Owner decision |
| `CLI-015` | `diff` compares the committed host TOML with the current one | active | withdrawn | Host TOML ends; as CLI-009 and CLI-010 | None |
| `CLI-016` | `path <name>` takes the path from `nix flake archive`, not from `flake.lock` | active | open | O-CLI and O-FLAKE: a devenv workspace uses the lock NAR method (V6 CLI-018, draft) | Fixture in a devenv workspace with no network |
| `BOOT-001` | A machine core boots with no Vendomat process or Python | active | retained | Unchanged. DOOR-016 | Keyless QEMU boot |
| `BOOT-002` | The core carries cache access so a fresh machine substitutes first | active | superseded | NEW[N11]: the core sets a shared-cache substituter and public key only when the inventory marks a cache host. A single-machine core sets none (DOOR-016) | Keyless boot with and without a cache mark |
| `BOOT-003` | The core holds only what every machine needs | active | retained | Unchanged | Remove an element; a machine fails |
| `BOOT-006` | The core boots in a VM before it reaches `server` | active | retained | Unchanged. P20 gate 6 | QEMU boot |
| `BOOT-012` | A cold-consumer claim is verified in a VM with an empty store | active | retained | Unchanged. P20 gate 7; V6 BOOT-027 adds the store-image rule | Cold VM with a store image |
| `BOOT-015` | Narrowed by BOOT-019: the laptop supplies the proof as a by-product | narrowed | withdrawn | No laptop install exists; framework is adopted in place (V6 BOOT-026) | None |
| `BOOT-018` | Every build step runs on `server`; the laptop is no prerequisite | active | superseded | NEW[N14]: shared builds run on the marked serving host; no other host is a prerequisite | Steps complete with the other host absent |
| `BOOT-019` | The laptop install requires no local build | active | superseded | V6 BOOT-026 (draft) and NEW[N16]: an adopted host builds nothing locally | Adoption VM log shows no compilation |
| `BOOT-020` | No guide verify command names the laptop before step 10 | active | withdrawn | GUIDE-V5 step order ends; PLAN.md stages replace it. NEW[N14] keeps the host independence | None |
| `BOOT-021` | The 512 GB install stays bootable with its own ESP until the new root runs reliably | active | retained | Owner-installation cutover rule. P19 §9, P20 gate 10 | Boot each drive from firmware. Blocked: owner action |
| `BOOT-022` | The new system is built on the old system and installed as a prebuilt closure | active | superseded | DOOR-015 (fresh install by controller) and V6 MACH-008 (draft) | Fresh-install VM log shows no build on the target |
| `BOOT-023` | `server` is converted by a fresh install on the new drive, never in place | active | retained | Unchanged. CONCEPT.md:150-151 fresh mode | Old drive not written during install |
| `BOOT-024` | Neither installation writes the other's boot entries | active | retained | Unchanged | Old ESP unchanged after install |
| `BOOT-016` | An element only one machine needs is a delta, never core | active | retained | Unchanged | Remove from core; both boot |
| `BOOT-017` | A fan-out claim names the machines it covers | active | retained | Unchanged | Build on one, substitute on the other |
| `BOOT-008` | A converted machine reaches every capability it had before | active | withdrawn | V6 withdrew it (blank slate). Framework adoption is not a conversion | None. Owner may want an adoption parity check (open item 7) |
| `BOOT-009` | No conversion step depends on Vendomat Python | active | withdrawn | V6 withdrew it. BOOT-001 and CONCEPT.md:150-151 cover the blank target | None |
| `BOOT-010` | A converted input produces the same result as the tree it replaces | active | withdrawn | V6 withdrew it (blank slate). Format migration is DOOR-018 | None |

### 2.1 The 17 `NAT-*` facts

A fact is an observation. It satisfies no requirement. None is superseded or withdrawn by project 20. Each stays as evidence.

| ID | Fact (short) | Disposition under P20 |
| --- | --- | --- |
| `NAT-001` | `git+file://?rev=` locks a real revision and NAR hash | retained as evidence |
| `NAT-002` | Dotted-path TOML converts to nested options; packages need option-specific resolution | retained as evidence; the TOML form ends (DOOR-004 keeps the package rule) |
| `NAT-003` | devenv has no `aliases`; scripts sort first on PATH | retained as evidence |
| `NAT-004` | Attic 0.1.0 skips a path present in an upstream cache | history only: Attic is replaced |
| `NAT-005` | Neovim wrappers default to `--suffix PATH` | retained as evidence |
| `NAT-006` | devenv merges an imported `devenv.yaml` only for local paths in the git root | V6 superseded it (NAT-018); fork inheritance (DVN-011) now matters |
| `NAT-007` | The flake delivery form evaluates impurely by default | retained as evidence |
| `NAT-008` | `nix build --out-link` creates an indirect GC root | retained and relied on: release roots (CONCEPT.md:133). Still marked "To observe"; P20 gate 7 must observe it |
| `NAT-009` | devenv Machines copies with `nix copy --to ssh://` and does not substitute through Attic | retained as evidence; V6 NAT-019 supersedes. Harmonia changes the substitute route, not the copy route |
| `NAT-010` | Nix 2.34.7 rejects `ref`/`rev` beside a string `url`; the query form locks both | retained as evidence; bears on REG-013 |
| `NAT-011` | `nix flake lock` does not evaluate `outputs` | retained as evidence; applies to the flake target only |
| `NAT-012` | Nix cannot see an untracked file in a Git-backed flake | retained as evidence |
| `NAT-013` | A `follows` override on a child with no such input warns; on a `flake = false` input it is ignored | retained as evidence for the flake route; devenv behavior is O-FOLLOWS |
| `NAT-014` | A read-only `git daemon` serves a tagged repo to Nix; the lock records URL, tag, and rev | retained as evidence |
| `NAT-015` | A fetched revision evaluates with the daemon stopped; a cold store fails | retained as evidence |
| `NAT-016` | An idle `git daemon` used 0 CPU ticks in 20 s | retained as evidence (supports NEW[N9]) |
| `NAT-017` | The source path is equal for `git://` and local `file://` fetch | retained as evidence |

### 2.2 Unchanged history (37 table rows)

These IDs are already superseded, withdrawn, or (for `PROJ-*`) a withdrawn range. P20 changes none. The last column flags a successor that P20 now affects.

| ID | V5 status | Existing successor | Successor affected by P20? |
| --- | --- | --- | --- |
| `REG-003` | superseded | REG-010 | none |
| `REG-004` | withdrawn | (none) | none |
| `REG-005` | superseded | REG-013 | REG-013 is open (O-KEYS) |
| `REG-015` | superseded | REG-021 | REG-021 is superseded (DOOR-003) |
| `GEN-001` | superseded | GEN-015 | GEN-015 is open (O-FLAKE) |
| `GEN-002` | superseded | GEN-013 then GEN-021 | GEN-021 is superseded (NEW[N4]) |
| `GEN-003` | superseded | GEN-020 | none (retained) |
| `GEN-004` | superseded | GEN-016 | GEN-016 is open (O-FLAKE) |
| `GEN-009` | superseded | GEN-014 then GEN-019 | GEN-019 is superseded (V6 DEL-013) |
| `GEN-010` | superseded | GEN-017 | none (retained) |
| `GEN-011` | superseded | GEN-017 | none (retained) |
| `GEN-012` | withdrawn | INP-006 and MOD-003 held the rule at the module boundary | both are superseded in V6 draft (FACE-008) |
| `GEN-013` | superseded | GEN-021 | GEN-021 is superseded (NEW[N4]) |
| `GEN-014` | superseded | GEN-019 | GEN-019 is superseded (V6 DEL-013) |
| `SYS-002` | superseded | SYS-008 | SYS-008 is superseded (DOOR-013, NEW[N8]) |
| `SYS-003` | superseded | SYS-009 | SYS-009 is superseded (DOOR-004) |
| `SYS-005` | superseded | SYS-010 | SYS-010 is superseded (DOOR-013) |
| `INP-001` | superseded | INP-008 | INP-008 is superseded (NEW[N18]) |
| `INP-002` | superseded | INP-007 | none (retained) |
| `STORE-002` | superseded | STORE-009 | STORE-009 is open (O-STORECMD) |
| `STORE-004` | superseded | STORE-010 | none (retained) |
| `STORE-011` | superseded | STORE-014 | none (retained) |
| `CACHE-004` | superseded | CACHE-009 | CACHE-009 is superseded (DOOR-017) |
| `MOD-007` | superseded | MOD-010 | MOD-010 is superseded (V6 MOD-014) |
| `PROJ-001 to PROJ-006` | withdrawn | GEN-016, GEN-017, GEN-019 hold the bridge rules | GEN-016 open, GEN-019 superseded |
| `CORE-007` | superseded | CORE-008 | none (retained) |
| `ISO-006` | superseded | ISO-007 | ISO-007 is superseded (V6 DEL-013) |
| `DEL-001` | superseded | DEL-006 | none (retained) |
| `DEL-002` | superseded | DEL-008 | DEL-008 is superseded (NEW[N20]) |
| `DEL-005` | superseded | DEL-009 | DEL-009 is superseded (V6 DEL-013) |
| `CLI-006` | withdrawn | (none) `nix flake update` does the job | none |
| `BOOT-004` | superseded | BOOT-021 to BOOT-023 | BOOT-022 is superseded (DOOR-015) |
| `BOOT-005` | superseded | BOOT-021 | none (retained) |
| `BOOT-007` | withdrawn | (none) one machine only | none |
| `BOOT-011` | superseded | BOOT-022 | BOOT-022 is superseded (DOOR-015) |
| `BOOT-013` | superseded | BOOT-014 then BOOT-018 | BOOT-018 is superseded (NEW[N14]) |
| `BOOT-014` | superseded | BOOT-018 | BOOT-018 is superseded (NEW[N14]) |

Also unchanged: the 19 withdrawn `RES-001` to `RES-012` and `EMIT-001` to `EMIT-007` (`SPEC-V5.md:288-300`). P20 agrees with that withdrawal. P20 CONCEPT.md:128-129 refuses a second transitive resolver, which is the same rule.

`BOOT-015`, the one narrowed ID, sits in the section 2 table.

## 3. Counts

| Disposition | IDs |
| --- | --- |
| retained | 69 |
| superseded | 53 |
| withdrawn | 11 |
| open | 20 |
| **Total (active + narrowed)** | **153** |

Of the 69 retained IDs, 7 are rename-only (`Rename:` in the successor column). 62 hold without any text change.

Superseded by an existing DOOR ID: BOOT-002, BOOT-022, CACHE-001, CACHE-002, CACHE-009, DEL-004, DEL-010, DEL-011, GEN-006, MOD-010, REG-021, SYS-001, SYS-008, SYS-009, SYS-010.

Superseded by a V6 draft ID only (P20 neither adds nor blocks it): CLI-011, CLI-012, CLI-013, DEL-003, DEL-009, DISK-005, GEN-019, INP-006, ISO-007, MOD-001, MOD-002, MOD-003, MOD-004, MOD-005, MOD-006, MOD-008, MOD-009.

Superseded by a `NEW:` placeholder: BOOT-002, BOOT-018, BOOT-019, BUILD-005, BUILD-006, BUILD-008, CACHE-001, CACHE-002, CACHE-005, CLI-001, DEL-008, DEL-012, GEN-005, GEN-008, GEN-021, INP-008, REG-001, REG-008, REG-009, REG-011, STORE-008, STORE-012, SYS-006, SYS-007, SYS-008.

Open, by item: 
- O-KEYS: REG-013, REG-016, REG-018, REG-019, REG-020, STORE-009
- O-FOLLOWS: REG-014
- O-FLAKE: GEN-007, GEN-015, GEN-016, GEN-018, GEN-022, STORE-016, CLI-016
- O-STORECMD: STORE-009, STORE-016, STORE-018, STORE-021, STORE-022
- O-CLI: CLI-005, CLI-008, CLI-014, CLI-016

Group view of what P20 touches most:

- Registry format (`REG-*`, `SYS-*`, host TOML): superseded by the YAML format and DOOR-003, DOOR-004, DOOR-011, DOOR-012, DOOR-013.
- Flake bridge (`GEN-*`, `PROJ-*`): P20 never mentions a generated `flake.nix`. This is O-FLAKE.
- Cache and builder (`CACHE-*`, `BUILD-*`): Attic and push go; Harmonia and release roots arrive (DOOR-017, NEW[N11] to NEW[N15]).
- Store (`STORE-*`): the source rules hold. The `sync` command goes, so the vehicle is open (O-STORECMD).
- Delivery (`DEL-*`) and CLI (`CLI-*`): superseded by DOOR-010 and the P20 command list.
- Disk, path, core, isolation (`DISK-*`, `PATH-*`, `CORE-*`, `ISO-*`, most `BOOT-*`, `INP-003/4/5/7`): unchanged.

## 4. Contradictions

1. **Requirement count differs by one.** `CURRENT.md:98` says 194 IDs, 151 active. `SPEC-V5.md:42` and `KICKOFF-V5.md:15` say 195 and 152. A table parse gives 152 active, 32 superseded, 10 withdrawn (the `PROJ-*` range is 6), 1 narrowed. `LEDGER-V6.md` counts 189 rows plus 25 range IDs plus 17 facts. Fix `CURRENT.md:98`.
2. **AGENTS.md describes a smaller repository than exists.** `AGENTS.md:61` lists 5 modules (`registry`, `generate`, `store`, `locate`, `cli`). `src/vendomat/` has 15 (`tests/test_repo_shape.py:17-33` lists them). `AGENTS.md:60` says the flake has one output. `flake.nix:14-46` exports `devenvModules.default`, `packages.vendomat`, and `packages.launcher`. The layout also omits `nix/`, `launcher/`, `templates/`, `direnv/`, `devenv-dist/`. `AGENTS.md:65` says "V5 and nothing else".
3. **CURRENT.md names V5 as the implementation contract, but the code implements V6 draft features.** `CURRENT.md:16-17` and `CURRENT.md:93-98`: project 14 is the contract. `SPEC-V6.md:3` says V6 is a draft. `cli.py:126-274` builds `check`, `push`, `bump`, `machine install`. `registry.py:36` accepts `imports`, `targets`, `settings`. `pyproject.toml:3` is `0.7.0-rc.1`. `tests/test_cli.py:12` calls them "built V5 commands". `DEL-012` itself says the surface is `sync` and `path` only.
4. **Project 20 refuses a second transitive input graph, but the code builds one.** `CONCEPT.md:127-129` says Vendomat "does not resolve a second transitive input graph". `devenvgen.py:167-208` walks each import's `devenv.yaml` recursively (V6 `PRE-003`). Fork patch 0007 (`CURRENT.md`, input inheritance) makes the walk redundant. It also conflicts with `GEN-020`, which stays retained.
5. **CONCEPT section 7 promises dispositions that REQUIREMENTS.md does not hold.** `CONCEPT.md:170-173` says the old IDs remain in `REQUIREMENTS.md` with their dispositions. `REQUIREMENTS.md:34-35` says they stay in their original ledgers and a successor specification will map them. The file holds only `DOOR-001` to `DOOR-018`. This report is the first map.
6. **Durable docs still say Attic owns the cache.** `AGENTS.md:16` ("Attic owns cached objects") and `SPEC-V5.md:73` conflict with `CONCEPT.md:138-143` (Harmonia, no push, no Attic). `push.py:1` and `push.py:73-97` still call `attic push`. Edit `AGENTS.md` at cutover.
7. **Release roots conflict with V5 scope text.** `SPEC-V5.md:612` says Vendomat is not a retention engine. `BUILD-006` says the log is the only durable record. `CONCEPT.md:133-136` and `19/CONCEPT.md §4` add one GC root per built tag and GC under disk pressure. See NEW[N15].
8. **Project 18 delta assumed a design that project 19 and 20 dropped.** `18/REQUIREMENTS-DELTA.md:7-9` assumes candidate B (a static directory cache, SSH publishing). It keeps `BUILD-008` and proposes `CACHE-014` to `CACHE-021`, `BUILD-010`, `VMOD-022`. Project 19 chose Harmonia with no publish (`19/DECISIONS.md:14-15` and `19/DECISIONS.md:50`). Do not adopt the P18 proposed rows.
9. **Project 19 text still names the TOML flow and a later `push` removal.** `19/CONCEPT.md:117-123` lists `vendomat.toml`, `[settings]`, and `sync` as kept. `19/DECISIONS.md:33` places a mark in `vendomat.toml`. `19/DECISIONS.md:36` removes `push` "in the next release". `CONCEPT.md:170-171` of P20 ends TOML and `sync` at cutover and ends `push` with Attic.
10. **V6 deferral on SYS and CLI IDs is settled by P20.** `SPEC-V6.md:57` defers `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015`, `SYS-001` to `SYS-010` and leans toward a TOML layer inside `nix-systems`. `DECISIONS.md:14` (decision 7) and `CONCEPT.md:170-172` allow no permanent TOML runtime path. This report applies P20.
11. **Command names differ.** `CONCEPT.md:54` lists `vendomat machines ...`. The code has `machine install` (`cli.py:274`). `CONCEPT.md:54` omits `path`, `check`, `bump`, which `SPEC-V6.md` `CLI-021` and `cli.py` keep. `PLAN.md:15` adds `tasks`, `up`, `update`. See O-CLI.
12. **P20 reserves two top-level keys, but V5/V6 need more.** `REQUIREMENTS.md:12` (`DOOR-003`) allows only `inputs` and `imports`. V5/V6 registries also hold `forge`, `passthrough`, `follows`, `targets`, `settings`, and per-input `keep`, `mirror`, `backup`, `dir`. `CONCEPT.md:130` keeps mirror and keep. No P20 text says where they go (O-KEYS, O-FLAKE).
13. **DOOR-001 and DOOR-009/DOOR-010 read stricter than the concept.** `REQUIREMENTS.md:10`: `devenv.nix` is a stub that routine work never changes. `CONCEPT.md:49` says "Template, then user if needed". `REQUIREMENTS.md:19` (`DOOR-010`) says the host launcher serves every command. `CONCEPT.md:120-123` says the front door must work from a pinned shell without it. `DOOR-009` guards plain `devenv shell`, but `CONCEPT.md:120-122` guards shell and test only.
14. **The concept is silent on how an ordinary workspace carries Vendomat.** `CONCEPT.md:38` says the Basix template imports the Basix module and an ordinary workspace does not. `CONCEPT.md:55-57` needs a Vendomat build pinned in the lock. `DEL-008` (V5) forbids a Vendomat input. V6 `VMOD-001` requires a module import. See O-VMOD.
15. **PLAN commands do not match the repository.** `PLAN.md:11,29` use `testee verify --full` and `testee check e2e`. `AGENTS.md` names `testee verify`, `testee verify e2e`, and `--profile quick`. `devenv.nix:34-62` defines profiles `quick` and `full` and runs e2e as `testee verify e2e`. I did not run Testee, so I cannot say whether `--full` is valid.
16. **The path source differs from the one-file rule.** `nix/devenv-module/default.nix:125-137` reads `vendomat.paths` from `/etc/vendomat/paths.json`. `CONCEPT.md:30-33` makes `vendomat.yaml` the one routine file. `PATH-*` stay retained, but the data source moves.

## 5. Open items needing an owner decision or a fixture

- **O-FLAKE.** Does project 20 keep a generated `flake.nix` bridge (`[targets] flake`) for library workspaces? P20 never mentions it, and `DOOR-003` leaves no key for `targets`. Recommendation: withdraw the flake target at cutover unless a real consumer needs it. Then withdraw `GEN-007`, `GEN-015`, `GEN-016`, `GEN-018`, `GEN-022`, `STORE-016` (flake half) and close `CLI-016`. Evidence: `tests/test_project_output_interface.py` shows what depends on it.
- **O-KEYS.** Where do `keep`, `mirror`, `backup`, `repo`, `dir`, the forge shorthand, and separate `ref`/`rev` live in `vendomat.yaml`, given that `inputs` keeps devenv's meaning (`CONCEPT.md:61`)? Affects `REG-013`, `REG-016`, `REG-018`, `REG-019`, `REG-020`, `STORE-009`. Recommendation: put source modes under a declared `vendomat.sources` option; keep full URLs in `inputs`; drop `backup` and the forge shorthand.
- **O-STORECMD.** Which command runs the `keep` clone, the `mirror` copy, the collection tree refresh, and a dry run, now that `sync` ends? Affects `STORE-009`, `STORE-016`, `STORE-018`, `STORE-021`, `STORE-022`. Recommendation: the hook keeps the tree refresh. Put clones in the front-door prep step. Keep a `--collection` flag only on the collection host.
- **O-CLI.** What stays of `path`, `check`, `bump`, `status`, `explore`, and `machine install` beside `shell`, `build`, `test`, `machines`? Affects `CLI-001`, `CLI-005`, `CLI-008`, `CLI-012`, `CLI-014`, `CLI-016`. Recommendation: keep `path`, `check`, `bump`; withdraw `status` and `explore`; decide the dirty-tree refusal for machine activation.
- **O-FOLLOWS.** Fixture: how the pinned devenv fork treats `follows` on a non-flake input, an absent child, and a missing target; and whether Vendomat still writes any `follows` once the fork inherits inputs (V6 `PRE-005`). Affects `REG-011`, `REG-014`, `GEN-021`.
- **O-VMOD.** Does an ordinary workspace import the Vendomat devenv module, or only pin a Vendomat lock node? Affects `DEL-008`, `DEL-011`, `DOOR-010`. Decide before the stage 4 front-door work.
- **Adoption parity.** V6 withdrew `BOOT-008` (capability parity) for a blank-slate install. Framework adoption in place is not blank. Decide whether an adopted host needs a capability comparison. Not covered by `DOOR-015`.
- **Retention scope.** Release roots and GC under disk pressure sit beside `SPEC-V5.md:612` (not a retention engine). Decide the wording of the successor scope text. Affects `BUILD-006`.
- **V6 successor audit.** Many V5 IDs name a V6 draft ID as the successor (`MOD-*`, `DEL-003`, `DEL-004`, `DEL-009`, `DEL-012`, `ISO-007`, `GEN-019`, `INP-006`, `CLI-011` to `CLI-013`, `DISK-005`, `BOOT-019`, `BOOT-022`). V6 is a draft. The V6 mapping agent must confirm that P20 adopts each, or each V5 ID stays active with its V5 text.

## 6. `NEW:` placeholders (deduplicated; no ID allocated)

| Key | Proposed claim | Used by |
| --- | --- | --- |
| NEW[N1] | `inputs` in `vendomat.yaml` is one map of named direct inputs. A key follows the V5 name rule. A duplicate key or an unknown entry key fails with file and line. | REG-001, REG-012 |
| NEW[N2] | Infrastructure inputs (`nixpkgs`, `devenv`) are ordinary `inputs` entries. They take no tag pin and are never mirrored or kept. No `[passthrough]` table exists. | REG-008, REG-017 |
| NEW[N3] | Only named commands (the one-time migrator, and `bump` if kept) write `vendomat.yaml`. Every other command leaves it byte-identical. | REG-009 |
| NEW[N4] | A follows edge is the native devenv `follows` under `inputs`. Vendomat passes it through and does not invent edges the user did not write (decide with O-FOLLOWS). | REG-011, GEN-021 |
| NEW[N5] | Each generated file names the generator version and the digest of the inputs it came from (`vendomat.yaml`, schema, pins). | GEN-005 |
| NEW[N6] | Vendomat never writes `devenv.lock`. devenv writes it. Vendomat may read it for `path` and `check`. | GEN-008 |
| NEW[N7] | A value with no safe data form (function, conditional, interpolation, option reference) is unsupported in `vendomat.yaml`. Vendomat names the limit and never coerces the value. | SYS-006 |
| NEW[N8] | Every supported YAML data value (scalar, string, boolean, integer, null, list, attribute set) evaluates to the same value as the same native Nix definition, in each target. | SYS-007, SYS-008 |
| NEW[N9] | One collection per installation is a set of Git repositories that accept new release tags only. A read-only `git://` daemon serves it. Host, path, and network interface are inventory facts. An idle daemon costs no CPU. | STORE-008 |
| NEW[N10] | No step requires a source path to be present in the shared cache. Evaluation takes source from the collection or from upstream. | STORE-012 |
| NEW[N11] | Cache client trust (substituter after upstream caches, public key, fallback on) derives from the inventory mark of the cache host. A core with no mark sets none. | CACHE-001, BOOT-002 |
| NEW[N12] | The Harmonia signing key never appears in a tracked file, a store path, or a log. | CACHE-002 |
| NEW[N13] | The serving host answers 404 for a path that is not valid in its store. It serves every valid store path, so network reach must match store visibility. | CACHE-005 |
| NEW[N14] | No Vendomat command publishes build outputs. Shared outputs are built on the serving host. An output built only on another host is not shared. No other host is a build prerequisite. | CACHE-006, BUILD-005, BUILD-008, BOOT-018, BOOT-020 |
| NEW[N15] | The durable build record is the build log, its exit status, and one GC root per built release tag. Vendomat writes no receipt. | BUILD-006 |
| NEW[N16] | An adopted host builds nothing locally. The controller or the serving host builds, and devenv Machines copies the closure. | BOOT-019 |
| NEW[N17] | The command surface is `shell`, `build`, `test`, `machines ...`, a devenv pass-through, and each kept utility command. `--help` lists exactly the built commands. | CLI-001 |
| NEW[N18] | An imported source declares its own inputs. The pinned devenv fork inherits them. Vendomat parses neither `devenv.yaml` of an import nor builds a second transitive graph. | INP-008 |
| NEW[N19] | After cutover the runtime contains no `vendomat.toml` reader, no `sync` command, and no Attic or `push` path. A repo-shape test enforces it. | DEL-012 |
| NEW[N20] | State how an ordinary workspace carries the pinned Vendomat build (a lock node plus a module import, or a lock node only). Decide with O-VMOD. | DEL-008 |

## 7. Code state notes used above

- Built: `sync` (flake and devenv targets), `path`, `check`, `push` (Attic), `bump`, `machine install` (`tests/test_cli.py:12`).
- Not built here: `add`, `remove`, `status`, `query`, `explore`, `set`, `get`, `unset`, `diff`, `apply`, `rollback`; `fromToml`, `fromInventory`, `mkModules` (no match in `src/`, `nix/`, `tests/`); any builder (`BUILD-001` to `BUILD-004`); `STORE-010`.
- Built in the devenv module: `vendomat.paths` (`default.nix:125-137`), inventory guards (`guard.nix`, `preflight.nix`), the `vendomat.cache` push task (`default.nix:221-225`).
- The launcher serves `sync` inside a workspace and finds a workspace by `vendomat.toml` (`launcher/vendomat:43`). P20 needs it to serve every command and to find `vendomat.yaml`.

# Current project

**Updated:** 2026-10-10. This file names the active project. `AGENTS.md` holds durable rules and
points here. When the active project changes, change this file and not `AGENTS.md`.

## Draft under owner review: project 16 — Vendomat V6, the devenv layer

`.scratch/projects/16-vendomat-devenv-layer/`: `CONCEPT-V6.md`, `SPEC-V6.md`, `GUIDE-V6.md`,
`CONCEPT-UPDATE-2026-10-10.md`, `LEDGER-V6.md` (generated),
`CUTOVER-REVIEW.md` (the Step 9 package, DRAFT), and
`RESEARCH-2026-10-09-MACHINE-PATHS.md`. Gate records: `evidence/GATES.md`.

Every workspace imports a pinned Vendomat devenv module. `vendomat sync` writes a `.vendomat/`
fragment. One patched devenv (`devenv-dist/`) runs everywhere. The `nix-systems` repository
(`Bullish-Design/nix-systems`, private) holds the machine roles: `server` is installed fresh on the
4 TB drive, then `framework` is adopted in place without a disk install.

**State on 2026-10-10.** Gates G0 to G4, G6, and G7 pass for their recorded interfaces (G7 in
QEMU). The revised no-Nix workspace gate G3A passes in a template-created local consumer
([evidence](projects/16-vendomat-devenv-layer/evidence/step-3a.md)). G1, G5, G8, and G9 are
BLOCKED by named items: the live Attic push (not permitted in the agent session), PV-09 (the
installer's pull credential), V4 removal in repositories that hold open work, `agentman`, and the
privileged scan with the `nixos-facter` report (they need root). No real disk, firmware entry, or boot
order changed. `CUTOVER-REVIEW.md` holds the verdict, the read-only facts, the built closure, and every
proposed command marked NOT RUN. The patched devenv is the fork `v2.4.0-vendomat.2`.

The 2026-10-10 concept revision makes no-Nix workspace use the first user goal. Module authors
may write native Nix. The existing description builder remains fixture evidence, but the revised
draft no longer requires it. Machine operator coverage follows this workspace proof.

The private `Bullish-Design/vendomat-demo` repository is the reusable live consumer. Its first
run passed two selected modules, inherited inputs, TOML setting changes, shell entry, and the
unselected-source check ([evidence](projects/16-vendomat-devenv-layer/evidence/demo-consumer.md)).
It found and led to fixes for `dir=` source discovery and a lock update with two changed inputs.
It uses stock devenv and a Vendomat module snapshot; it does not close the patched-fork or fleet
gate.

Until the owner accepts V6, project 14 below stays the authority, and V5 IDs are not yet marked
superseded in `SPEC-V5.md`. `SPEC-V6.md` section 0 and `LEDGER-V6.md` hold the dispositions.

## Active: project 14 — Vendomat V5

Authority, in reading order, all in `.scratch/projects/14-vendomat-local/`:

1. `CONCEPT-V5.md` — the shape and the worked examples.
2. `SPEC-V5.md` — normative. 194 requirement IDs in its tables, 151 active, 32 superseded, 10 withdrawn, 1 narrowed; 19 withdrawn resolver and emitter IDs are preserved.
3. `GUIDE-V5.md` — the commands. Steps 0 to 10.
4. `REFINEMENT-2026-10-08.md` — named paths and drive identity.

`KICKOFF-V5.md` in the same directory is the prompt for starting an implementation session.

### State

Updated 2026-10-08, fourth session (the store step). The V5 machine steps have not run. Step 8, the registry and
generator, ran in isolation under the owner's authorization, and its fixtures pass: the project-output
interface on pinned Nix ([PV-13](projects/14-vendomat-local/prelim-verification/results/PV-13.md)) and
the real `vendomat sync` output ([PV-14](projects/14-vendomat-local/prelim-verification/results/PV-14.md)).
This is not fleet acceptance.

The store step is built and passes its fixtures ([PV-20](projects/14-vendomat-local/prelim-verification/results/PV-20.md)):
`vendomat sync` handles `keep`, `mirror`, `--dry-run`, and `--collection`, and `vendomat path <name>`
prints a locked input's store path. A real run on `server` moved `devman` to `v0.7.0` and left the
other clones alone, and a `keep` clone of `devman` over the live daemon worked ([PV-21](projects/14-vendomat-local/prelim-verification/results/PV-21.md)). No `mirror` entry ran on
`server`. A push-time hook for the tree refresh exists in `hooks/collection-post-receive` and passes its
fixtures (`STORE-023`). It is installed on the live `devman` ([PV-22](projects/14-vendomat-local/prelim-verification/results/PV-22.md)). The `collection-add` change that installs it
for new repositories is landed and pushed in `nix-meta` `main` (`1629188`). `vendomat` 0.5.0 is released on `main` ([PV-23](projects/14-vendomat-local/prelim-verification/results/PV-23.md)), pinned in `nix-meta` `main` (`a8bba69`), and the owner switched
`server` to it on 2026-10-09. It is the system command there, and PV-24 checked the result ([PV-24](projects/14-vendomat-local/prelim-verification/results/PV-24.md)): no failed units, the closure changed only in `vendomat`, and the collection and hooks are unchanged. `STORE-010`, the release task, and the explicit use of `backup` are not built.

Owner decisions of 2026-10-08: Vendomat is a system-installed command, added by a host delta at
`packages.<system>.vendomat`. It generates no development shell and no `devenv` input. A generated
`flake.nix` bridges to a project-owned `flake-outputs.nix`. The laptop is `framework`. Nix owns
`flake.lock`. Vendomat tracks two things: build outputs, which Attic holds, and source, which one
collection on `server` holds. Nix reads personal inputs from that collection over `git://`, CI pushes
release tags to it, and every input pins a tag. Attic never needs to hold source. The library is
aligned to the V5 concept; V4 is removed, not kept. See
[DECISIONS.md](projects/14-vendomat-local/prelim-verification/DECISIONS.md). PV-05 stays as history.

Still blocked, each by evidence:

- **Step 0 and Step 7 (PV-02):** the 4 TB target's identity matches, but its partition table and
  signatures cannot be read without privilege. The owner runs the scan.
- **Step 2, 3, and 10 (PV-09):** a cold VM reaches the private route and meets HTTP 401 without a
  credential. The owner chooses how the installer gets the pull credential.
- **Step 8 acceptance:** Step 6.3 is done. The daemon settings were proved on two NixOS test machines
  (PV-18), landed in `nix-meta` (`6cfcba5`, not pushed to origin), and switched on `server`. The
  collection holds `devman` at `v0.7.0`. The owner reports from `framework` that `git ls-remote
  git://server/devman` works, that `nix flake lock` plus a build against the collection works, and
  that `ssh server true` works (PV-19). All three are owner-reported and not observed here. I did not
  verify that any output came from Attic. A tag push from `framework` is untested.
- **`DEL-010`:** proved on two fixture shapes on `server` ([PV-25](projects/14-vendomat-local/prelim-verification/results/PV-25.md)); not run in an existing repository's shell or on `framework`. The V4 consumer module prints an `install-hook` error on a V5 `vendomat.toml` (`DEL-011` open).

The Nix-only core booted in a disposable PV-11 VM without the Vendomat CLI. That fixture did not
prove production boot or tailnet reachability. See
[results](projects/14-vendomat-local/prelim-verification/RESULTS.md).

## V4 removal backlog (outside the `vendomat` repository)

The owner ruled on 2026-10-09: V4 stays nowhere, V5 gives no backward compatibility, and the rest of
the system is aligned to V5. `vendomat` `main` is purged ([PV-26](projects/14-vendomat-local/prelim-verification/results/PV-26.md)).
The `nix-meta` pin keeps the old code alive on the machine until the items below are done. Each item
names its V5 answer. None keeps V4 behavior.

| # | V4 leftover | V5 answer | Needs first |
| --- | --- | --- | --- |
| 1 | `nix-meta` pins `vendomat` at `d5a90f0`. `profiles/developer.nix:16` takes the login-shell tools from `repoman-toolchain-core`. `machines/server.nix:68` imports `nixosModules.default`, which installs the CLI and the V4 consumer module | Each tool is its own flake input of `nix-meta`, listed in its registry and enabled in the host TOML. A host delta installs `packages.<system>.vendomat` only. Repin to 0.6.0 or later | Items 2 and 3 |
| 2 | `gitman`, `copyroom`, `docman`, `templateer`, `agentman`, `pyjutsu` have no `flake.nix`. The old `vendomat` flake built them with a shared uv2nix builder | Each tool authors its own flake (`packages.<system>.default`, and a module through `mkModules` when it has one). The uv2nix builder becomes a Python core input that exports `lib` (the `nvim-core` pattern), outside `vendomat`. Compare each build with today's (`BOOT-010`). `pyjutsu` exports its own wheel. Only `copyroom` depends on `pyjutsu` (checked in `pyproject.toml` and `uv.lock` of 17 repositories), so the wheelhouse is nearly unused | The Python core |
| 3 | **The critical path.** `repoman`'s module requires `REPOMAN_TOOLCHAIN_BIN` (`modules/devenv.nix` fails with "import the vendomat toolchain module"). Its manager modules (`gitman`, `docman`, `copyroom`, and others) run `"${cfg.toolchainBin}"/<tool>`. `repoman-sync.sh` reads the toolchain manifest at `$REPOMAN_TOOLCHAIN_BIN/../share/vendomat/toolchain.json`. Only the V4 module sets these | `repoman` runs its managers by name from the host `PATH`, and needs no Vendomat manifest. The host puts the tools on `PATH` (item 1 today; item 2 later). The login shell has them on `PATH` now | A `repoman` change, tagged and repinned in `nix-meta`, then the owner switches |
| 4 | Eleven central overlays import the V4 consumer module: `eventic`, `llgym`, `loci-core`, `argentic`, `poddantic`, `flora`, `loci.nvim`, `flora-qc`, `shellij`, `nix-secrets`, `pyllij`. Removing the import now breaks every `repoman` task in these repositories (item 3) | Remove the import line. Keep the `devman` link lines. A project that needs a native wheel lists the owning repository as an input | **Item 3** |
| 5 | V4-format `vendomat.toml` files. **Done 2026-10-09 in four clean repositories:** `argentic`, `eventic`, `shellij`, `flora` (they held only `[vendor.publish] enable = false`, so the shell is unchanged; the no-file path of the V4 module was tested in a throwaway project). **Left:** `flora-core` and `nix-nvim` (`[toolchain] enable = false` opts out of the closure, so deleting the file turns it on until item 4), `repoman` (a stale `[vendor] libs = ["pyjutsu"]` and `mode = "editable"`), and `loci-core`, `loci.nvim`, `poddantic`, `pyllij`, which hold other work in progress (open lanes, unbookmarked work, or an unpushed commit) | Delete each. A repository gets a V5 `vendomat.toml` only when it becomes a flake-backed project or author | The owners of the open work, and item 4 for `flora-core` and `nix-nvim` |
| 6 | `linkman` declares `vendomat` as a devenv input at `v0.4.3`, and its `devenv.nix` takes `REPOMAN_TOOLCHAIN_BIN` from `inputs.vendomat.packages.<system>.repoman-toolchain-core` | Remove the input and the `vendomat/modules` import | **Item 3** |
| 7 | The machine plane. The Dagu service on `server` reads its registry from `~/.local/state/vendomat/devman/active` (generation 4), set in `nix-meta` `profiles/devman.nix` | Not part of V5. NixOS generations give the atomic switch and the rollback. `devman`'s flake supplies the renderer, Dagu, and the runtime, and already validates workflows in a Nix check. `devman` exports a function that renders a registry from project inputs; `nix-meta` sets `registryDir` to that store path. Workflows then follow released tags. A local checkout uses an explicit input override. Until then the live Dagu keeps reading generation 4, which is immutable | A `devman` change |
| 8 | Documents that name V4 commands: `repoman` README and changelog, `devman/USER.md` section 2.7, `mancore/CONCEPT.md`, `pyjutsu/nix/pyjutsu.nix` | Rewrite to V5 | Items 1 and 7 |
| 9 | `.scratch/projects/09-*` to `13-*`, which the V5 documents cite by name | Remove after the citations are inlined or dropped | Last |

Item 2 has no requirement IDs yet: the V5 documents name a Python core and do not specify it.

## Superseded

`.scratch/projects/09-*` through `13-*` and the `docs/V4_*.md` records are closed history. They
hold observations that the active documents cite by name. Do not read them for direction, and do
not follow any programme, gate, or requirement ID defined in them. Each closed directory carries
its own terminal note.

## Inherited facts that still hold

- `vendomat` `main` holds V5 only (0.6.0, `DEL-012`). The V4 code is in Git history and in the
  revision `nix-meta` still pins (`d5a90f0`). Nothing reads it for direction.
- Eleven central overlays, ten local-checkout overlays, and one flake-input consumer use the
  current paths. Every machine is reconfigured, so those paths are replaced. `BOOT-010` carries the
  one obligation: a converted input must produce the same result as the tree it replaces, or name
  the difference.
- `tests/fixtures/store-consumer/` is a real consumer fixture for the current pin.
- V5 logs go in `~/.local/state/vendomat/v5/<date>/`. Older logs sit beside it.

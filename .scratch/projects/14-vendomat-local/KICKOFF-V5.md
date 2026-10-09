# V5 implementation kickoff prompt

**Status on 2026-10-08: partly unblocked. Do not start steps 0 to 7 or step 10.** Step 8 (registry and generator) ran in isolation and its fixtures pass (PV-13, PV-14). Its acceptance still needs a fetch from `framework` to the source collection on `server` (PV-16, PV-17). The preliminary
verification is recorded in [prelim-verification/RESULTS.md](./prelim-verification/RESULTS.md).
This file is not a green light to start Step 0.

**Project-output contract (2026-10-08).** Vendomat is a system-installed command and generates no shell. The generated `flake.nix` bridges to a project-owned `flake-outputs.nix`; the project selects every module. Read [DECISIONS.md](prelim-verification/DECISIONS.md) for the superseding decision. PV-05 stays as dated history.

## Read first

All in `.scratch/projects/14-vendomat-local/`:

1. `../../CURRENT.md` — active state and blockers.
2. `prelim-verification/RESULTS.md` — all spike outcomes and remaining proof.
3. `SPEC-V5.md` — normative requirements. It lists 193 requirement IDs in its tables; 150 are active. The 19 withdrawn `RES-*` and `EMIT-*` IDs remain preserved.
4. `CONCEPT-V5.md` — design and examples.
5. `GUIDE-V5.md` — proposed commands. Step 8 may run in isolation; Step 0 and installer cache access stay blocked.
6. `REFINEMENT-2026-10-08.md` — drive identity and storage plan.

`AGENTS.md` points to `.scratch/CURRENT.md`. Closed projects and V4 records are history.

## Current blockers

- **PV-02, Step 0:** the target's stable ID, model, serial, and exact size matched the inventory. `lsblk` showed no partitions or mounts. `wipefs --no-act` was denied, so the partition-table and signature state is unknown. The target is not proven bare. Do not partition, format, install, or call Step 0 passed.
- **PV-09, cache bootstrap:** an empty alternate store on `server` fetched a 121-path closure from the host-local Attic endpoint. No cold installer VM ran. The cache is private and the Tailscale Serve route is tailnet-only under `/attic`; `attic use` drops that prefix. The host Nix configuration has no private key or pull credential.
- **PV-03, source paths:** a locked `git+file` URL needs a source Git repository at the same absolute path. Moving the consumer checkout alone works; moving or omitting the source fails, even with the public cache. An explicit Nix input override selects another path without changing the lock when writes are disabled. `VENDOMAT_SOURCE_ROOT` alone has no effect on an existing flake or lock. Fleetwide local URLs are not portable.

## Decisions supported by fixtures

- Nix declares and resolves flake inputs and owns `flake.lock`. Vendomat does not implement a resolver, manifest, `devenv.yaml` dependency list, or `fromManifest` loader.
- The one-`nixpkgs` result is a controlled-graph goal. A consumer follows edge alone left three nodes; each authored nested flake must follow its parent for the tested graph to use one node.
- The generated project flake bridges to a project-owned outputs file and defines no shell. PV-05's `--impure` finding applies to its old devenv shell only. No Vendomat check needs `--impure`.
- Vendomat tracks source and build outputs. Attic holds outputs only. One collection on `server` holds the owner's released tags; every `[inputs]` entry pins a tag (`REG-016`, `REG-017`, `STORE-008`).
- `ref` and `rev` reach Nix as URL query parameters. Nix rejects them as separate input attributes. `[follows]` edges are explicit, and the registry rejects a non-flake child.
- A TOML converter must return a valid NixOS module. Resolve package names only for explicit package-valued option paths. Native Nix option types merge equal scalars and lists; incompatible scalars fail.
- `mkModules` uses native module merging to preserve package lists. An authored flake exports only the module faces it supports.
- The host edit sequence is `set → diff → Gitman commit → apply`. `diff` compares the last committed host TOML with the current file. Switch, dirty-file refusal, force, and rollback still need a disposable VM test.
- The shared machine core boots in a disposable NixOS test VM without the Vendomat CLI. The VM had no external network, so the test did not prove tailnet reachability. Install the CLI only in a later host delta with `packages.<system>.vendomat`; `.default` is the wheelhouse.
- Production Attic reports retention 0. A disposable Attic 0.1.0 test showed that time-based GC with one-second retention removed an object; retention 0 excluded the fixture cache from time-based GC. `server` runs weekly Nix GC with a 14-day age rule. These are not promises of permanent cache availability.

## Conditions before implementation

1. Obtain an authorized read-only scan of the 4 TB target's partition table and signatures. Review a fail-closed checker against the real inventory and all injected mismatch cases.
2. Build the source collection on `server` and fetch from `framework` over the tailnet. The owner chose `git://` for reads and SSH for release pushes; PV-16 and PV-17 passed on loopback. The local override passed in PV-14.
3. Choose how an installer obtains the cache route, trust key, pull credential, and source before first boot. Prove the complete closure transfer in a cold disposable VM or image with local builds disabled.
4. Reconcile `.scratch/CURRENT.md` and this kickoff after those results. Keep each old requirement ID and add a new ID when its claim changes.

## Work rules

- Route every version-control action through Gitman. Do not run raw `git` or `jj`.
- Run `devenv shell -- testee verify --mode quick` as the normal repository gate. Use the opt-in end-to-end gate for Nix module, toolchain, or consumer integration changes.
- Do not call pytest, ruff, or ty directly.
- Keep raw logs under `~/.local/state/vendomat/v5/prelim-verification/<date>/` and secrets out of logs and tracked files.
- Do not change production cache settings, move Attic data, or write to a physical disk without a reviewed procedure and evidence that unblocks the specific step.
- A fixture, upstream document, or proposal is not an implementation pass.

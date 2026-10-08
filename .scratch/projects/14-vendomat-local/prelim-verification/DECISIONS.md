# Decisions from V5 preliminary verification

**State:** resolved from the recorded fixtures on 2026-10-08, except where marked open. These are
design decisions. They do not pass the implementation requirements.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| Source URLs | Use portable remote URLs as the fleet default. Use an explicit Nix input override for a local checkout. `VENDOMAT_SOURCE_ROOT` alone does not change a flake or lock. | [PV-03](results/PV-03.md) | Add `STORE-006`, `STORE-007`; keep `STORE-001` for the clone store only | Add a generator fixture and name the reachable remote for private repos |
| `nixpkgs` sharing | One node is a goal for controlled graphs where every authored nested flake follows its parent. | [PV-04](results/PV-04.md) | Supersede `GEN-002` with `GEN-013`; supersede `CORE-007` with `CORE-008` | Test actual project inputs for compatibility |
| Consumer shell | Use `nix develop --impure` with the pinned devenv integration. Pure root discovery failed. | [PV-05](results/PV-05.md) | Supersede `GEN-009` with `GEN-014` | Test the generated shell and a cold consumer after `sync` |
| Host TOML | Return a valid NixOS module. Resolve packages only at explicit package-valued option paths. Let native option types merge definitions. | [PV-06](results/PV-06.md) | Supersede `SYS-002`, `SYS-003`, `SYS-005` with `SYS-008` to `SYS-010` | Implement and test the allowlist and module wrapper |
| Module helper | Use native module merging to preserve lists. Let flakes export only the faces they implement. | [PV-07](results/PV-07.md) | Supersede `MOD-007` with `MOD-010`; supersede `INP-002` with `INP-007` | Test real authored inputs and consumer activation |
| Host edit sequence | Compare the committed host file with the current file. Run `set → diff → Gitman commit → apply`. | [PV-08](results/PV-08.md) | Add `CLI-015`; keep `CLI-012` | Prove dirty-file refusal, switch, force scope, and rollback in a disposable VM |
| Private cache bootstrap | Keep the production cache unchanged. An empty alternate store on `server` fetched a closure, but a cold installer route did not pass. | [PV-09](results/PV-09.md) | Keep `CACHE-007`, `BOOT-002`, and `BOOT-019` blocked | Choose credential and route delivery, then test a cold installer VM |
| Cache retention | Do not claim “nothing builds twice.” Retention 0 avoids time-based GC in the Attic 0.1.0 fixture, not every form of deletion. Keep upstream cache fallback when Attic skips an upstream path. | [PV-10](results/PV-10.md) | Supersede `CACHE-004` with `CACHE-009` | Decide policy for important closures and test cold upstream fallback |
| Machine core | Keep the Vendomat CLI out of the shared core. Add it through a later host delta at `.vendomat`, not `.default`. | [PV-11](results/PV-11.md) | Supersede `DEL-001` with `DEL-006`; add `DEL-007` | Prove production boot and tailnet reachability |
| Physical target | Step 0 is blocked. Do not call the 4 TB disk bare or write to it. | [PV-02](results/PV-02.md) | Keep `DISK-001` to `DISK-003` open | Obtain a read-only partition-table and signature scan; review the checker |

## Open choices

- Name a reachable remote source for each private flake before the generator is accepted.
- Choose how a fresh installer obtains the private cache route, trust key, pull credential, and source before first boot.
- Confirm that the owner accepts `nix develop --impure` as the generated consumer-shell command.
- Confirm the laptop name before Step 10.

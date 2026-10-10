# Vendomat V5 to V6 requirement ledger

**Generated** by `ledger/build_ledger.py` from `SPEC-V5.md` and `SPEC-V6.md`. Do not edit by hand.
Section 0 of `SPEC-V6.md` holds every V5 disposition. Change it there and regenerate.
`tests/test_v6_ledger.py` fails when this file differs from the tool's output.

V6 stays a **draft**. V5 stays authoritative until the owner accepts V6.

## Counts

| Set | Count |
| --- | --- |
| V5 requirement IDs in tables (active 152, superseded 32, withdrawn 4, narrowed 1) | 189 |
| V5 withdrawn IDs listed as ranges, not rows (`PROJ-*`, `RES-*`, `EMIT-*`) | 25 |
| V5 `NAT-*` facts | 17 |
| V6 IDs defined (active 67, proposed 15, to build 0, superseded 20, decided 2) | 104 |
| V6 `NAT-*` facts | 31 |
| V5 IDs that section 0 names | 51 |

## Checks

- PASS: no V5/V6 collision, no duplicate row, every successor exists.

### Active V6 rows that cite a closed ID

None.

## V5 IDs and their V6 disposition

`Kept` means the V5 text applies unchanged. `Closed in V5` means V5 already superseded or
withdrew it, and V6 adds nothing.

| V5 ID | V5 status | V6 disposition | Successor or note |
| --- | --- | --- | --- |
| `BOOT-001` | active | Kept | V5 text applies |
| `BOOT-002` | active | Kept | V5 text applies |
| `BOOT-003` | active | Kept | V5 text applies |
| `BOOT-004` | superseded | Closed in V5 |  |
| `BOOT-005` | superseded | Closed in V5 |  |
| `BOOT-006` | active | Kept | V5 text applies |
| `BOOT-007` | withdrawn | Closed in V5 |  |
| `BOOT-008` | active | Withdrawn 2026-10-09 | Blank slate: no capability parity and no tree comparison |
| `BOOT-009` | active | Withdrawn 2026-10-09 | No conversion step exists. `BOOT-001` keeps the core free of Vendomat |
| `BOOT-010` | active | Withdrawn 2026-10-09 | Blank slate: no capability parity and no tree comparison |
| `BOOT-011` | superseded | Closed in V5 |  |
| `BOOT-012` | active | Kept | V5 text applies |
| `BOOT-013` | superseded | Closed in V5 |  |
| `BOOT-014` | superseded | Closed in V5 |  |
| `BOOT-015` | narrowed | Kept | V5 text applies |
| `BOOT-016` | active | Kept | V5 text applies |
| `BOOT-017` | active | Kept | V5 text applies |
| `BOOT-018` | active | Kept | V5 text applies |
| `BOOT-019` | active | Superseded | `BOOT-026`: no laptop install exists; Framework is adopted in place |
| `BOOT-020` | active | Kept | V5 text applies |
| `BOOT-021` | active | Kept | V5 text applies |
| `BOOT-022` | active | Superseded | `MACH-008`: install with devenv Machines from the running `server` |
| `BOOT-023` | active | Kept | V5 text applies |
| `BOOT-024` | active | Kept | V5 text applies |
| `BUILD-001` | active | Kept | V5 text applies |
| `BUILD-002` | active | Kept | V5 text applies |
| `BUILD-003` | active | Kept | V5 text applies |
| `BUILD-004` | active | Kept | V5 text applies |
| `BUILD-005` | active | Kept | V5 text applies |
| `BUILD-006` | active | Kept | V5 text applies |
| `BUILD-007` | active | Kept | V5 text applies |
| `BUILD-008` | active | Kept | V5 text applies |
| `CACHE-001` | active | Superseded | `CACHE-010`: the host core sets the substituter |
| `CACHE-002` | active | Kept | V5 text applies |
| `CACHE-003` | active | Kept | V5 text applies |
| `CACHE-004` | superseded | Closed in V5 |  |
| `CACHE-005` | active | Kept | V5 text applies |
| `CACHE-006` | active | Kept | V5 text applies |
| `CACHE-007` | active | Kept | V5 text applies |
| `CACHE-008` | active | Kept | V5 text applies |
| `CACHE-009` | active | Kept | V5 text applies |
| `CLI-001` | active | Superseded | `CLI-021` (the chain is `CLI-017`, `CLI-021`) |
| `CLI-002` | active | Kept | V5 text applies |
| `CLI-003` | active | Kept | V5 text applies |
| `CLI-004` | active | Kept | V5 text applies |
| `CLI-005` | active | Deferred | Not built in V5 0.6.0 and not in `CLI-021`. Decide with `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015` |
| `CLI-006` | withdrawn | Closed in V5 |  |
| `CLI-007` | active | Kept | V5 text applies |
| `CLI-008` | active | Deferred | Not built in V5 0.6.0 and not in `CLI-021`. Decide with `CLI-009`, `CLI-010`, `CLI-014`, `CLI-015` |
| `CLI-009` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `CLI-010` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `CLI-011` | active | Superseded | `MACH-005`: activation and rollback through devenv Machines |
| `CLI-012` | active | Superseded | `MACH-005`: activation and rollback through devenv Machines |
| `CLI-013` | active | Superseded | `MACH-005`: activation and rollback through devenv Machines |
| `CLI-014` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `CLI-015` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `CLI-016` | active | Kept | V5 text applies |
| `CORE-001` | active | Kept | V5 text applies |
| `CORE-002` | active | Kept | V5 text applies |
| `CORE-003` | active | Kept | V5 text applies |
| `CORE-004` | active | Kept | V5 text applies |
| `CORE-005` | active | Kept | V5 text applies |
| `CORE-006` | active | Kept | V5 text applies |
| `CORE-007` | superseded | Closed in V5 |  |
| `CORE-008` | active | Kept | V5 text applies |
| `DEL-001` | superseded | Closed in V5 |  |
| `DEL-002` | superseded | Closed in V5 |  |
| `DEL-003` | active | Superseded | `MOD-013`: no `mkModules` helper exists, so no library needs a Vendomat input |
| `DEL-004` | active | Superseded | `DEL-016`: `nix-meta` is retired |
| `DEL-005` | superseded | Closed in V5 |  |
| `DEL-006` | active | Kept | V5 text applies |
| `DEL-007` | active | Kept | V5 text applies |
| `DEL-008` | active | Superseded | `VMOD-001`: every workspace imports the Vendomat module |
| `DEL-009` | active | Narrowed | `DEL-013`: they hold for library outputs, not for workspaces |
| `DEL-010` | active | Superseded | `DEL-017`: a host launcher runs each workspace's pinned Vendomat |
| `DEL-011` | active | Superseded | `DEL-017`: a host launcher runs each workspace's pinned Vendomat |
| `DEL-012` | active | Superseded | `DEL-019`: the Vendomat flake also exports the devenv module (the chain is `DEL-015`, `DEL-018`, `DEL-019`) |
| `DISK-001` | active | Kept | V5 text applies |
| `DISK-002` | active | Kept | V5 text applies |
| `DISK-003` | active | Kept | V5 text applies |
| `DISK-004` | active | Kept | V5 text applies |
| `DISK-005` | active | Superseded | `DISK-008`: UUIDs are declared before formatting |
| `DISK-006` | active | Kept | V5 text applies |
| `DISK-007` | active | Kept | V5 text applies |
| `EMIT-001` | withdrawn | Closed in V5 |  |
| `EMIT-002` | withdrawn | Closed in V5 |  |
| `EMIT-003` | withdrawn | Closed in V5 |  |
| `EMIT-004` | withdrawn | Closed in V5 |  |
| `EMIT-005` | withdrawn | Closed in V5 |  |
| `EMIT-006` | withdrawn | Closed in V5 |  |
| `EMIT-007` | withdrawn | Closed in V5 |  |
| `GEN-001` | superseded | Closed in V5 |  |
| `GEN-002` | superseded | Closed in V5 |  |
| `GEN-003` | superseded | Closed in V5 |  |
| `GEN-004` | superseded | Closed in V5 |  |
| `GEN-005` | active | Kept | V5 text applies |
| `GEN-006` | active | Kept | V5 text applies |
| `GEN-007` | active | Kept | V5 text applies |
| `GEN-008` | active | Kept | V5 text applies |
| `GEN-009` | superseded | Closed in V5 |  |
| `GEN-010` | superseded | Closed in V5 |  |
| `GEN-011` | superseded | Closed in V5 |  |
| `GEN-012` | withdrawn | Closed in V5 |  |
| `GEN-013` | superseded | Closed in V5 |  |
| `GEN-014` | superseded | Closed in V5 |  |
| `GEN-015` | active | Kept | V5 text applies |
| `GEN-016` | active | Kept | V5 text applies |
| `GEN-017` | active | Kept | It covers the flake target only. The module builds faces from descriptions (`VMOD-018`), not the generator |
| `GEN-018` | active | Kept | V5 text applies |
| `GEN-019` | active | Narrowed | `DEL-013`: they hold for library outputs, not for workspaces |
| `GEN-020` | active | Kept | V5 text applies |
| `GEN-021` | active | Kept | V5 text applies |
| `GEN-022` | active | Superseded | `GEN-023`: a workspace shell is a devenv project |
| `INP-001` | superseded | Closed in V5 |  |
| `INP-002` | superseded | Closed in V5 |  |
| `INP-003` | active | Kept | V5 text applies |
| `INP-004` | active | Kept | V5 text applies |
| `INP-005` | active | Kept | V5 text applies |
| `INP-006` | active | Kept | V5 text applies |
| `INP-007` | active | Kept | V5 text applies |
| `INP-008` | active | Kept | V5 text applies |
| `ISO-001` | active | Kept | V5 text applies |
| `ISO-002` | active | Kept | V5 text applies |
| `ISO-003` | active | Kept | V5 text applies |
| `ISO-004` | active | Kept | V5 text applies |
| `ISO-005` | active | Kept | V5 text applies |
| `ISO-006` | superseded | Closed in V5 |  |
| `ISO-007` | active | Narrowed | `DEL-013`: they hold for library outputs, not for workspaces |
| `MOD-001` | active | Superseded (owner 2026-10-09: Vendomat builds the modules from a library description) | `MOD-001` → `DESC-002` (through `DESC-001`); `MOD-002` → `FACE-005` |
| `MOD-002` | active | Superseded (owner 2026-10-09: Vendomat builds the modules from a library description) | `MOD-001` → `DESC-002` (through `DESC-001`); `MOD-002` → `FACE-005` |
| `MOD-003` | active | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `MOD-004` | active | Superseded | `DESC-002`: `packages` is `pkgs: [ derivation ]` and `extra` is `{ cfg, pkgs, lib }: { devenv; nixos; homeManager }` |
| `MOD-005` | active | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `MOD-006` | active | Superseded | `DESC-002`: `packages` is `pkgs: [ derivation ]` and `extra` is `{ cfg, pkgs, lib }: { devenv; nixos; homeManager }` |
| `MOD-007` | superseded | Closed in V5 |  |
| `MOD-008` | active | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `MOD-009` | active | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `MOD-010` | active | Kept | They apply to the modules Vendomat builds. `MOD-007` stays superseded by `MOD-010` |
| `NAT-001` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-002` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-003` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-004` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-005` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-006` | active | Superseded | `NAT-018` |
| `NAT-007` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-008` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-009` | active | Superseded | `NAT-019` |
| `NAT-010` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-011` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-012` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-013` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-014` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-015` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-016` | active | Fact | Observation. It satisfies no requirement. |
| `NAT-017` | active | Fact | Observation. It satisfies no requirement. |
| `PATH-001` | active | Kept | V5 text applies |
| `PATH-002` | active | Kept | V5 text applies |
| `PATH-003` | active | Kept | V5 text applies |
| `PATH-004` | active | Kept | V5 text applies |
| `PROJ-001` | withdrawn | Closed in V5 |  |
| `PROJ-002` | withdrawn | Closed in V5 |  |
| `PROJ-003` | withdrawn | Closed in V5 |  |
| `PROJ-004` | withdrawn | Closed in V5 |  |
| `PROJ-005` | withdrawn | Closed in V5 |  |
| `PROJ-006` | withdrawn | Closed in V5 |  |
| `REG-001` | active | Kept | V5 text applies |
| `REG-002` | active | Kept | V5 text applies |
| `REG-003` | superseded | Closed in V5 |  |
| `REG-004` | withdrawn | Closed in V5 |  |
| `REG-005` | superseded | Closed in V5 |  |
| `REG-006` | active | Kept | V5 text applies |
| `REG-007` | active | Kept | V5 text applies |
| `REG-008` | active | Kept | V5 text applies |
| `REG-009` | active | Superseded | `REG-025`: `bump` may write two `ref` values; no other command writes the registry |
| `REG-010` | active | Kept | V5 text applies |
| `REG-011` | active | Kept | V5 text applies |
| `REG-012` | active | Kept | V5 text applies |
| `REG-013` | active | Kept | V5 text applies |
| `REG-014` | active | Kept | V5 text applies |
| `REG-015` | superseded | Closed in V5 |  |
| `REG-016` | active | Kept | V5 text applies |
| `REG-017` | active | Kept | V5 text applies |
| `REG-018` | active | Kept | V5 text applies |
| `REG-019` | active | Kept | V5 text applies |
| `REG-020` | active | Kept | V5 text applies |
| `REG-021` | active | Superseded | `REG-022`: adds `[imports]` and `[targets]` |
| `RES-001` | withdrawn | Closed in V5 |  |
| `RES-002` | withdrawn | Closed in V5 |  |
| `RES-003` | withdrawn | Closed in V5 |  |
| `RES-004` | withdrawn | Closed in V5 |  |
| `RES-005` | withdrawn | Closed in V5 |  |
| `RES-006` | withdrawn | Closed in V5 |  |
| `RES-007` | withdrawn | Closed in V5 |  |
| `RES-008` | withdrawn | Closed in V5 |  |
| `RES-009` | withdrawn | Closed in V5 |  |
| `RES-010` | withdrawn | Closed in V5 |  |
| `RES-011` | withdrawn | Closed in V5 |  |
| `RES-012` | withdrawn | Closed in V5 |  |
| `STORE-001` | active | Kept | V5 text applies |
| `STORE-002` | superseded | Closed in V5 |  |
| `STORE-003` | active | Kept | V5 text applies |
| `STORE-004` | superseded | Closed in V5 |  |
| `STORE-005` | active | Kept | V5 text applies |
| `STORE-006` | active | Kept | V5 text applies |
| `STORE-007` | active | Kept | V5 text applies |
| `STORE-008` | active | Kept | V5 text applies |
| `STORE-009` | active | Kept | V5 text applies |
| `STORE-010` | active | Kept | V5 text applies |
| `STORE-011` | superseded | Closed in V5 |  |
| `STORE-012` | active | Kept | V5 text applies |
| `STORE-013` | active | Kept | V5 text applies |
| `STORE-014` | active | Kept | V5 text applies |
| `STORE-015` | active | Kept | V5 text applies |
| `STORE-016` | active | Kept | V5 text applies |
| `STORE-017` | active | Kept | V5 text applies |
| `STORE-018` | active | Kept | V5 text applies |
| `STORE-019` | active | Kept | V5 text applies |
| `STORE-020` | active | Kept | V5 text applies |
| `STORE-021` | active | Kept | V5 text applies |
| `STORE-022` | active | Kept | V5 text applies |
| `STORE-023` | active | Kept | V5 text applies |
| `SYS-001` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-002` | superseded | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-003` | superseded | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-004` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-005` | superseded | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-006` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-007` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-008` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-009` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |
| `SYS-010` | active | Deferred | Owner 2026-10-09: decide after `nix-systems` has run; leaning toward keeping TOML as a layer inside `nix-systems` |

## V6 IDs

| V6 ID | Status | Supersedes (V5 or V6) | Note |
| --- | --- | --- | --- |
| `BOOT-026` | proposed | `BOOT-019` |  |
| `BOOT-027` | active |  |  |
| `BUILD-009` | active |  |  |
| `CACHE-010` | active | `CACHE-001` |  |
| `CACHE-011` | active |  |  |
| `CLI-017` | superseded | `CLI-001` | by `CLI-021` |
| `CLI-018` | active |  |  |
| `CLI-019` | active |  |  |
| `CLI-020` | active |  |  |
| `CLI-021` | active | `CLI-001`, `CLI-001`, `CLI-005`, `CLI-008` |  |
| `DEL-013` | active | `DEL-009`, `GEN-019`, `ISO-007` |  |
| `DEL-014` | decided |  | by `DEL-017` |
| `DEL-015` | superseded | `DEL-012` | by `DEL-018` |
| `DEL-016` | active | `DEL-004` |  |
| `DEL-017` | active | `DEL-010`, `DEL-011` |  |
| `DEL-018` | superseded | `DEL-012` | by `DEL-019` |
| `DEL-019` | active | `DEL-012`, `DEL-012` |  |
| `DESC-001` | superseded | `MOD-001`, `MOD-002` | by `DESC-002` |
| `DESC-002` | active | `MOD-001`, `MOD-002`, `MOD-004`, `MOD-006` |  |
| `DESC-003` | active |  |  |
| `DISK-008` | superseded | `DISK-005` | by `DISK-009` |
| `DISK-009` | proposed |  |  |
| `DVN-001` | active |  |  |
| `DVN-002` | active |  |  |
| `DVN-003` | active |  |  |
| `DVN-004` | active |  |  |
| `DVN-005` | active |  |  |
| `DVN-006` | active |  |  |
| `DVN-007` | active |  |  |
| `DVN-008` | active |  |  |
| `DVN-009` | proposed |  |  |
| `DVN-010` | active |  |  |
| `FACE-001` | superseded |  | by `FACE-006` |
| `FACE-002` | active |  |  |
| `FACE-003` | active |  |  |
| `FACE-004` | decided |  | by `FACE-005` |
| `FACE-005` | active | `MOD-001`, `MOD-002` |  |
| `FACE-006` | active |  |  |
| `FACE-007` | active |  |  |
| `GEN-023` | active | `GEN-022` |  |
| `MACH-001` | superseded |  | by `MACH-023` |
| `MACH-002` | superseded |  | by `MACH-019` |
| `MACH-003` | superseded |  | by `MACH-015` |
| `MACH-004` | active |  |  |
| `MACH-005` | active | `CLI-011`, `CLI-012`, `CLI-013` |  |
| `MACH-006` | active |  |  |
| `MACH-007` | active |  |  |
| `MACH-008` | active | `BOOT-022` |  |
| `MACH-009` | active |  |  |
| `MACH-010` | superseded |  | by `MACH-016`, `DISK-002`, `DISK-003` |
| `MACH-011` | superseded |  | by `MACH-014` |
| `MACH-012` | superseded |  | by `MACH-017` |
| `MACH-013` | superseded |  | by `MACH-018` |
| `MACH-014` | proposed |  |  |
| `MACH-015` | proposed |  |  |
| `MACH-016` | proposed |  |  |
| `MACH-017` | proposed |  |  |
| `MACH-018` | proposed |  |  |
| `MACH-019` | proposed |  |  |
| `MACH-020` | proposed |  |  |
| `MACH-021` | active |  |  |
| `MACH-022` | proposed |  |  |
| `MACH-023` | proposed |  |  |
| `MACH-024` | active |  |  |
| `MACH-025` | active |  |  |
| `MOD-011` | superseded |  | by `MOD-013` |
| `MOD-012` | superseded |  | by `MOD-013` |
| `MOD-013` | active | `DEL-003` |  |
| `NAT-018` | fact | `NAT-006` |  |
| `NAT-019` | fact | `NAT-009` |  |
| `NAT-020` | fact |  |  |
| `NAT-021` | fact |  |  |
| `NAT-022` | fact |  |  |
| `NAT-023` | fact |  |  |
| `NAT-024` | fact |  |  |
| `NAT-025` | fact |  |  |
| `NAT-026` | fact |  |  |
| `NAT-027` | fact |  |  |
| `NAT-028` | fact |  |  |
| `NAT-029` | fact |  |  |
| `NAT-030` | fact |  |  |
| `NAT-031` | fact |  |  |
| `NAT-032` | fact |  |  |
| `NAT-033` | fact |  |  |
| `NAT-034` | fact |  |  |
| `NAT-035` | fact |  |  |
| `NAT-036` | fact |  |  |
| `NAT-037` | fact |  |  |
| `NAT-038` | fact |  |  |
| `NAT-039` | fact |  |  |
| `NAT-040` | fact |  |  |
| `NAT-041` | fact |  |  |
| `NAT-042` | fact |  |  |
| `NAT-043` | fact |  |  |
| `NAT-044` | fact |  |  |
| `NAT-045` | fact |  |  |
| `NAT-046` | fact |  |  |
| `NAT-047` | fact |  |  |
| `NAT-048` | fact |  |  |
| `PRE-001` | active |  |  |
| `PRE-002` | active |  |  |
| `PRE-003` | active |  |  |
| `PRE-004` | active |  |  |
| `PRE-005` | active |  |  |
| `PRE-006` | active |  |  |
| `PRE-007` | active |  |  |
| `PRE-008` | active |  |  |
| `PRE-009` | active |  |  |
| `PRE-010` | active |  |  |
| `PRE-011` | active |  |  |
| `REG-022` | active | `REG-021` |  |
| `REG-023` | active |  |  |
| `REG-024` | active |  |  |
| `REG-025` | active | `REG-009` |  |
| `SEC-001` | superseded |  | by `SEC-003`, `MACH-007` |
| `SEC-002` | proposed |  |  |
| `SEC-003` | proposed |  |  |
| `VMOD-001` | active | `DEL-008` |  |
| `VMOD-002` | active |  |  |
| `VMOD-003` | superseded |  | by `VMOD-013`, `VMOD-018` |
| `VMOD-004` | active |  |  |
| `VMOD-005` | active |  |  |
| `VMOD-006` | active |  |  |
| `VMOD-007` | active |  |  |
| `VMOD-008` | active |  |  |
| `VMOD-009` | active |  |  |
| `VMOD-010` | active |  |  |
| `VMOD-011` | active |  |  |
| `VMOD-012` | superseded |  | by `VMOD-016` |
| `VMOD-013` | superseded |  | by `VMOD-018`, `DESC-002` |
| `VMOD-014` | active |  |  |
| `VMOD-015` | superseded |  | by `VMOD-018` |
| `VMOD-016` | proposed |  |  |
| `VMOD-017` | active |  |  |
| `VMOD-018` | active | `GEN-017` |  |

## Reserved and never adopted

- Project 15 drafted `WS-001` to `WS-006`, `MOD-011`, `DISK-008`, `BOOT-025`, `CLI-017` to `CLI-019`,
  `GEN-023`, and `NAT-018` to `NAT-023`. The owner never adopted them. `SPEC-V6.md` defines its own
  text for each number it uses. `WS-*`, `BOOT-025`, and `CLI-018`/`CLI-019` are not V6 IDs unless the
  V6 table above lists them.

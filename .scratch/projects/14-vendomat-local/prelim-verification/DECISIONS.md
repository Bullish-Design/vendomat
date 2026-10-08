# Decisions from V5 preliminary verification

**State:** resolved from the recorded fixtures on 2026-10-08, except where marked open. These are
design decisions. They do not pass the implementation requirements.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| Source URLs | Use portable remote URLs as the fleet default. Use an explicit Nix input override for a local checkout. `VENDOMAT_SOURCE_ROOT` alone does not change a flake or lock. | [PV-03](results/PV-03.md) | Add `STORE-006`, `STORE-007`; keep `STORE-001` for the clone store only | Add a generator fixture and name the reachable remote for private repos |
| `nixpkgs` sharing | One node is a goal for controlled graphs where every authored nested flake follows its parent. | [PV-04](results/PV-04.md) | Supersede `GEN-002` with `GEN-013`; supersede `CORE-007` with `CORE-008` | Test actual project inputs for compatibility |
| Consumer shell | **Superseded 2026-10-08 (below).** Original text: use `nix develop --impure` with the pinned devenv integration; pure root discovery failed. Kept as history. | [PV-05](results/PV-05.md) | Supersede `GEN-009` with `GEN-014`, then `GEN-014` with `GEN-019` | None. The generated shell is gone |
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
- ~~Confirm that the owner accepts `nix develop --impure` as the generated consumer-shell command.~~ Closed 2026-10-08: Vendomat generates no shell.
- ~~Confirm the laptop name before Step 10.~~ Closed 2026-10-08: the name is `framework`.

## Decisions of 2026-10-08, second session

These are owner decisions plus design choices that follow from [PV-13](results/PV-13.md) and
[PV-14](results/PV-14.md). They keep PV-05 and its raw logs as dated history. PV-05 remains valid
evidence about its old devenv fixture and is not a reason to require `--impure` now.

| Topic | Decision | Evidence | Requirement changes | Remaining work |
| --- | --- | --- | --- | --- |
| CLI delivery | Vendomat is a system-installed command, added by a host delta at `packages.<system>.vendomat`. It is not installed through devenv or the shared boot core. | Owner; PV-11 | Keep `DEL-006`, `DEL-007`. Add `DEL-010`, `DEL-011` | Fixture F8: the CLI is reachable from an existing project shell |
| Generated shell | **Supersedes the consumer-shell row above.** Vendomat generates no development shell and no `devenv` input. A project may write its own shell and call the installed command. Remove `nix develop --impure` from every Vendomat gate. | Owner; PV-13 F2 | Supersede `GEN-014` with `GEN-019`. Add `GEN-022` | None |
| Output bridge | The generated `flake.nix` is `outputs = inputs: import ./flake-outputs.nix inputs;`. The project owns `flake-outputs.nix`. `sync` fails if the file is missing and never opens it. | PV-13 F1, F5, F6; PV-14 | Supersede `GEN-004` with `GEN-016`. Add `GEN-018` | None |
| Module selection | The generator never scans or imports a module face. A project output names each module it uses. | PV-13 F3, F4 | Supersede `GEN-010` and `GEN-011` with `GEN-017`. Withdraw `GEN-012` | None |
| Direct inputs | One input per registry entry; no implicit `devenv` or `nixpkgs`. A project lists the `nixpkgs` it needs. | PV-14 | Supersede `GEN-001` with `GEN-015`, `GEN-003` with `GEN-020` | None |
| Follows | An explicit `[follows]` table drives the edges. Registry checks reject a non-flake child, because Nix ignores that case silently. Nix itself warns for a child with no `nixpkgs`; the generator does not fetch to check. | PV-13 F7; PV-14 | Supersede `GEN-013` with `GEN-021`. Add `REG-011`, `REG-014` | Real-input compatibility with one `nixpkgs` |
| `ref` and `rev` | The draft claim that they pass through as separate attributes failed. Emit them as URL query parameters. | PV-13 | Supersede `REG-005` with `REG-013` | None |
| Name checks | A name in both `[inputs]` and `[passthrough]` is an error. An unknown top-level table is an error. | PV-14 | Add `REG-012`, `REG-015` | None |
| Verification of absence | Check parsed input names and the lock, never `rg vendomat flake.nix`. The header names the tool, and the Nixpkgs URL contains `devenv`. | PV-13 F2 | Supersede `DEL-002` with `DEL-008`, `DEL-005` with `DEL-009`, `ISO-006` with `ISO-007` | None |
| `sync` name | `vendomat sync` in a directory with `vendomat.toml` is the V5 generator. Without that file it keeps the earlier knowledge installer, because `modules/devenv.nix` still calls it. | PV-14 | None | Retire the fallback with the knowledge layer |
| Laptop name | The laptop is `framework`. | Owner | None | None |
| Step order | Isolated registry and generator work may run before the machine steps. Machine activation and fleet acceptance keep their gates. | Owner | None | See the guide's "Revised order" |

## Open owner choices (recommendation first)

1. **Private source host** (blocks Step 8 acceptance, [PV-15](results/PV-15.md)). Recommend a real Git remote that both machines reach, either Forgejo on the tailnet or `git+ssh` through `server`. Consequence: one new service or an SSH key setup. The alternative, cache-served sources, adds a publish step per deploy, ties source access to the cache credential, and is not a Git remote.
2. **Installer credential delivery** (blocks Step 10, [PV-09 addendum](results/PV-09.md)). Recommend a root-only, pull-only, short-lived credential file copied from the installer medium to `/run` and passed with `--option netrc-file`. Consequence: the medium holds a secret.
3. **Drive scan** (blocks Step 0, [PV-02 addendum](results/PV-02.md)). Recommend that the owner runs the read-only `wipefs --no-act`, `sfdisk --dump`, and `blkid -p` with their own sudo, and saves the output.

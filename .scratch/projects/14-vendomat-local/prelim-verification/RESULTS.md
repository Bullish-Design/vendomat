# V5 preliminary verification results

**State:** investigation complete on 2026-10-08; V5 implementation is **not ready**. No V5
implementation step has run. PV-12 reconciles the authority documents and records the repository
verification results.

| Spike | Outcome | Evidence | Representative raw output |
| --- | --- | --- | --- |
| PV-01 | Failed: active documents conflicted; reconciled in PV-12 | [Claim audit](results/PV-01.md) | [ID inventory](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-01-id-inventory.log) |
| PV-02 | Blocked: real partition-table and signature scan was denied | [Drive preflight](results/PV-02.md) | [Read-only signature scan](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-02-wipefs-no-act.log) |
| PV-03 | Failed: a locked local source URL requires the source at its recorded absolute path | [Source portability](results/PV-03.md) | [Missing source with public cache](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-03-missing-public-cache.log) |
| PV-04 | Passed controlled graph fixture: nested follows edges shared one nixpkgs node | [Graph fixture](results/PV-04.md) | [Followed graph summary](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-04-consumer-followed-graph-summary-final.log) |
| PV-05 | Failed pure shell entry; the pinned fixture passed with `nix develop --impure` | [Consumer independence](results/PV-05.md) | [Pure shell failure](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-05-shell-entry-pure-final.log) |
| PV-06 | Failed current converter shape and blanket package-list conversion | [Typed host TOML](results/PV-06.md) | [Direct converter failure](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-06-direct-converter-failure.log) |
| PV-07 | Failed `recursiveUpdate` package-list merge; native module merge preserved additions | [Module faces](results/PV-07.md) | [Evaluation](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-07-evaluation.log) |
| PV-08 | Failed the documented `set → diff → apply` sequence; a commit boundary is specified | [Host edit sequence](results/PV-08.md) | [Final host evaluation](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-08-after-commit-eval-final.log) |
| PV-09 | Blocked: host-local cold substitution passed; fresh installer access did not | [Cache bootstrap](results/PV-09.md) | [Cold store fetch](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-09-cold-store-fetch.log) |
| PV-10 | Passed isolated Attic publication and retention fixture; no permanence claim | [Cache retention](results/PV-10.md) | [Zero-retention collector](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-10-gc-zero-retention.log) |
| PV-11 | Passed disposable NixOS VM fixture without the Vendomat CLI | [Machine core](results/PV-11.md) | [VM build and boot](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-11-nix-build-boot-final.log) |
| PV-12 | Reconciled authority and readiness; repository gate results are recorded in its report | [Reconciliation](results/PV-12.md) | [Final ID inventory](/home/andrew/.local/state/vendomat/v5/prelim-verification/2026-10-08/PV-12-id-inventory.log) |

## Readiness and blockers

**Do not start Steps 0 to 10.** Step 0 is blocked because the 4 TB target's partition table and
signatures could not be read. Its stable ID, model, serial, and exact size matched the inventory;
`lsblk` showed no partition or mount. That is not proof that the target is bare. No physical disk
was written.

PV-09 also blocks a cold installer. An empty alternate store on `server` fetched 121 paths from
the host-local Attic endpoint, but no installer VM ran. The tailnet-only Serve route uses `/attic`;
`attic use` omits that prefix. The host Nix configuration has no private-cache trust key or pull
credential. The production cache was read-only throughout.

Other implementation contracts still need tracked fixtures: generator output and cold consumer
entry, typed TOML conversion, module helper activation, CLI dirty-file and rollback behavior, and
production boot and network acceptance. The disposable PV-11 test did not have external network
access and did not prove tailnet reachability.

## Changed requirement IDs

| Requirement change | Supporting fixture |
| --- | --- |
| Supersede `REG-003` with `REG-010`; require a portable source URL and explicit local override | PV-03 source relocation, missing-source, and override cases |
| Supersede `GEN-002` with `GEN-013`; constrain one-node sharing to controlled follows graphs | PV-04 direct versus nested follows graphs |
| Supersede `GEN-009` with `GEN-014`; use the pinned shell's required impure root discovery | PV-05 pure and impure shell cases |
| Supersede `SYS-002`, `SYS-003`, and `SYS-005` with `SYS-008` to `SYS-010` | PV-06 converter, option-type, and merge cases |
| Supersede `INP-001` with `INP-008`; supersede `INP-002` with `INP-007` | PV-04 native graph and PV-07 face census |
| Add `STORE-006` and `STORE-007` for remote defaults and explicit local overrides | PV-03 |
| Supersede `CACHE-004` with `CACHE-009` for upstream skips and fallback | PV-10 |
| Supersede `MOD-007` with `MOD-010` for native list merging | PV-07 |
| Supersede `CORE-007` with `CORE-008` for native flake inputs | PV-04 |
| Supersede `DEL-001` with `DEL-006`; add `DEL-007` for CLI package selection | PV-11 |
| Add `CLI-015` for committed diff baseline and apply sequencing | PV-08 |

The specification now defines 153 requirement IDs in its tables: 126 active, 9 withdrawn, 17
superseded, and 1 narrowed. It preserves the 19 withdrawn resolver and emitter IDs and 9 native
fact IDs. The final inventory found no duplicate requirement definitions.

## Limits of the evidence

- A locked `git+file` input depends on the source remaining at the same absolute path. The explicit
  override worked only with lock writes disabled. `VENDOMAT_SOURCE_ROOT` alone did not change an
  existing flake or lock.
- The one-node nixpkgs graph passed only when each authored nested input followed its parent. It
  was a controlled three-level fixture, not a survey of every fleet input.
- The cache fixture used Attic 0.1.0. Positive time retention removed its object; retention 0
  excluded the fixture cache from that version's time-based collection. This does not guarantee
  permanent availability or prove production cache internals.
- A passing fixture or repository verification does not pass an implementation requirement.

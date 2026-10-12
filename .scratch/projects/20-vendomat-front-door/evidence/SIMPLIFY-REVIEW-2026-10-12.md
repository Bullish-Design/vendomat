# Project 20 simplification review

**Date:** 2026-10-12. This is a design proposal, not an implementation result.
The owner asked for a simpler mental model, including lost capability. Project 20
research fixtures prove mechanisms only. No production code, consumer, machine, or
real disk changed in this review.

## The 90 % journeys

| Journey | Needs on the first path | Outside the first path |
| --- | --- | --- |
| Install Basix, then change programs and settings | Fresh install on one supported UEFI disk; stable disk identity and preflight; keyless core; data file for common options; native rollback | Adoption, custom disk layouts, remote secrets |
| Create a development workspace | Fixed template; program and language data; native inputs and imports when needed; shell and test through pinned devenv | Arbitrary options as data, direct stock devenv, offline first use |
| Update and recover | Explicit source ref and native lock change; version control restore; NixOS generation rollback | Vendomat version routing per workspace, automatic source mirroring |
| Add a second machine and share outputs | Repeat fresh install; optional signed Harmonia after key placement; client fallback; build and root selected outputs on server | Cache auto-selection, collection builder, automatic key delivery |

These boundaries follow [R4](R4-user-journeys.md) and the [research gate matrix](RESEARCH-2026-10-11.md).
S7 proves fresh and adopted *fixture* flows, not a real Basix installation. S6 proves
signed substitution in virtual machines, not a real second machine.

## New mental model

The user edits data for common programs, services, settings, and machine facts.
Vendomat opens a shell or passes a command to its pinned devenv fork.
Nix reads the data and the native lock directly, then NixOS applies or rolls back a machine.
A second machine may use a signed cache after its administrator configures the cache.

## Mechanism review

Each alternative names a capability that the proposal gives up. Evidence links name
fixture records; a fixture does not pass an implementation gate.

| Current mechanism | Why it exists | Simpler shape; machinery removed | Lost capability | Evidence | Verdict |
| --- | --- | --- | --- | --- | --- |
| `vendomat.yaml` with inputs, imports, and arbitrary option paths | One routine user file without Nix | Direct `vendomat.toml` data plus native `devenv.yaml` inputs and imports; remove YAML front door | One-file input edits and arbitrary option paths as data | [S1](S1-yaml-subset.md), [S9](S9-native-follows.md), [direct TOML fixture](#direct-toml-fixture) | simplify |
| 168-case YAML grammar and hand parser | Reject ambiguous YAML and locate errors | Nix `fromTOML`; remove custom grammar and parser | YAML block strings, null, exact YAML error contract | [S1](S1-yaml-subset.md), direct TOML fixture | cut |
| Canonical JSON generator and write-on-change | Stable output bytes for Nix | Read user data directly; remove copy and canonicalization | Stable generated JSON for other tools | [S1](S1-yaml-subset.md), direct TOML fixture | cut |
| Committed `.vendomat/` input fragment and data copy | Testee and clones work before `prepare` | Native `devenv.yaml` and direct data read; remove derived tree | Generated inputs from one file | [S5](S5-front-door.md) shows why a generated tree had to be committed | cut |
| Digest, stale guard, escape variable | Detect drift between YAML and generated files | No copy to drift; remove guard and bypass | Direct devenv drift warning | [S5](S5-front-door.md) | cut |
| `prepare` and `prepare --check` | Regenerate and verify copy | No preparation; Testee reads native files | Separate preflight command | [S5](S5-front-door.md) | cut |
| Neutral schema export and authoring rule | Let Python validate all declared options | Nix option types; remove exporter and special module-author rule | Early Python error before Nix starts | [S3](S3-schema-export.md) | cut |
| Schema cache key and missing-schema exit | Make export fast and work offline after warm-up | No schema export; remove cache and exit 68 | Cached Python validation while offline | [S3](S3-schema-export.md) | cut |
| Python validation and nine fault exits | Precise file, line, key, reason before operation | Nix type errors and native exit status; force set values at operation gate | Precise data line and single-pass error list | [S4](S4-machine-inventory.md) shows lazy type risk; direct TOML fixture | simplify |
| Secret-name recognizer | Catch likely secret strings in generated data | No generated data; document secret-free data contract and scan real outputs in gates | Heuristic early warning | [S1](S1-yaml-subset.md) reports incomplete recall | cut |
| Generic package and path coercion | Map strings onto every declared option type | Narrow data surface with explicit program mapping; native Nix for other types | Arbitrary package or path option as data | [S2](S2-merge-priority.md) | simplify |
| Plain generated definitions and priority matrix | Match native Nix merge | Keep native merge; libraries use `mkDefault` for overridable scalars | Guaranteed data override of a plain scalar | [S2](S2-merge-priority.md) | keep |
| Transitive input discovery and generated `follows` | Share imported child inputs | Native `follows`; remove resolver | Automatic shared-child discovery | [S9](S9-native-follows.md) | cut |
| Conditional lock update sequence | Repair a generated fragment's lock | User edits native inputs; devenv updates native lock | Automatic lock repair on shell entry | [S3](S3-schema-export.md), [S9](S9-native-follows.md) | cut |
| Ten named Vendomat commands | Place every operation behind one CLI | Bare `vendomat` for shell, `vendomat new`, other args pass through | Special `path`, `check`, `bump`, `prepare` behavior | [S5](S5-front-door.md) proves pass-through mechanics | simplify |
| Per-workspace pinned Vendomat launcher and protocol | Run each workspace's Vendomat release | One host Vendomat release with pinned devenv; remove NAR lookup, protocol, host override | Per-workspace Vendomat release routing | [S5](S5-front-door.md) proves protocol, not its need | cut |
| Pinned devenv fork | Inherited inputs and consistent operations | Keep one fork in host Vendomat release and matching module pin | Direct stock devenv compatibility | [S9](S9-native-follows.md); [S3](S3-schema-export.md) found pin mismatch | keep |
| `use vendomat` direnv hook | Prepare then enter and fail clearly | Defer hook until direct entry works; no prepare step | Automatic direnv entry in first release | [S5](S5-front-door.md) | defer |
| Two machine modes in one inventory | Fresh install and adoption | One typed fresh-install record; separate adoption later | Existing NixOS adoption | [S4](S4-machine-inventory.md), [S7](S7-keyless-secrets.md), [R4](R4-user-journeys.md) G06 | simplify |
| Wide inventory with disk, filesystem, hardware, user fields | Describe many routes | Required target, system, state version, admin key, stable disk ID; defaults for supported hardware | Custom layouts and foreign filesystem facts | [S4](S4-machine-inventory.md) | simplify |
| Disk guards and preflight | Prevent a wrong disk write | Keep real target and protected-disk checks | No safe reduction: types cannot inspect hardware | [S4](S4-machine-inventory.md); real proof open | keep |
| Installer key, admin key, host-key re-pin | Separate temporary access from installed access | Keep key separation and explicit re-pin | No safe reduction found | [S7](S7-keyless-secrets.md) | keep |
| Generic SSH secret receiver and path activation | Deliver keys after boot and rotate services | Administrator configures cache after key placement; remove receiver and path unit | Automatic post-boot delivery, rotation, recovery | [S6](S6-harmonia-two-vm.md), [S7](S7-keyless-secrets.md) | defer |
| SecretSpec host and controller routes | Supply future secrets | No provider on keyless core; native option later | Secret-managed service on day one | [S7](S7-keyless-secrets.md) | defer |
| Harmonia cache and signing key | Share outputs across two machines | Keep optional signed service after key placement | No automatic cache availability at first boot | [S6](S6-harmonia-two-vm.md) | simplify |
| Cache mark and derived client settings | Auto-wire trust from inventory | Explicit URL, public key, fallback, and timeout in client configuration | Automatic cache selection | [S6](S6-harmonia-two-vm.md) | simplify |
| Cache fallback and network restriction | Preserve builds when cache fails; limit store visibility | Keep both; prove timeout with fallback | No safe reduction found | [S6](S6-harmonia-two-vm.md) found default failure and whole-store visibility | keep |
| Collection mirror, keep clone, hook, source modes | Private source availability and local checkouts | Native tagged Git source URLs and lock | Offline source mirror and keep checkout | [R3](R3-migration-inventory.md): no live mode use | defer |
| Collection builder and root per tag | Retain every built release | Build on cache host; root selected outputs with native Nix links | Automatic release retention | [S6](S6-harmonia-two-vm.md) proves root survival only | simplify |
| Attic push and live check during transition | Preserve current cache until replacement works | Keep current route until real Harmonia gate passes, then remove | Temporary overlap remains during proof | [S6](S6-harmonia-two-vm.md); no live gate | keep |
| Two-marker transition launcher | Migrate TOML and YAML workspaces separately | Manual migration of two live consumers with host rollback | Mixed-format automatic routing | [R3](R3-migration-inventory.md) | cut |
| Converter and per-table migration record | Audit format change | Hand-edit two live consumers; keep a concise source-to-destination record | Automatic third-consumer conversion | [R3](R3-migration-inventory.md) | simplify |
| Ten slices and historical gate carry-forward | Track all possible interfaces | Three implementation slices plus release and hardware gates | Fine-grained schedule for deferred features | [research matrix](RESEARCH-2026-10-11.md) | simplify |

## Validation and format trade

TOML is a proposed change to the owner's 2026-10-11 YAML decision. It is data-only
for common options, but a module author edits native `devenv.yaml` for inputs.
The native file is a visible cost. The direct read removes the copy, guard, parser,
schema exporter, and validator. The data surface cannot accept every Nix value.
Nix errors lose the proposed `file:line:col:key:reason` contract. The direct fixture
showed a file and option in a type error; it did not show a TOML line number.

Nix checks some options lazily. [S4](S4-machine-inventory.md) L1 let an unused bad
value pass; L2 forced the machine record. A general force step remains unproved.
The first slice must show that a bad set value stops every relevant command before
the command performs work. The implementation may narrow the data surface further
if eager forcing creates a Nix evaluation cycle.

## Direct TOML fixture

Question: can a fixed Nix module read user TOML without a generated copy and cite
the file in a type error? Competing hypotheses were a direct `fromTOML` read
with `_file`, and a native Nix definition. On 2026-10-12, the isolated fixture
used Nix 2.34.7 and the S2 nixpkgs library path
`/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source/lib`. It ran
`./run.sh`, which invoked `nix-instantiate --eval --strict --show-trace --argstr caseName CASE eval.nix`
for five cases. The good TOML returned `"hello"` (exit 0). A numeric value for
a string option failed (exit 1), named `demo.message` and `config-bad.toml`,
and showed no TOML line. Invalid TOML failed (exit 1) and printed source line 2
under the `fromTOML` label. A native Nix numeric definition gave the same type
fault and cited its Nix file. The fixture proves direct parsing and file-level
location in `lib.evalModules`. It does not prove the pinned devenv fork, package
mapping, eager checks, or Basix. Raw log and exact inputs:
`~/.local/state/vendomat/p20/2026-10-12/direct-toml/` (`notes.md`, `run.log`).
The raw log stays outside the repository.

## User-facing count

These counts include required first-path items and exclude optional secrets and
native escape-hatch content. The explicit lists make the comparison reproducible.

| Measure | Before | Proposed first path |
| --- | --- | --- |
| Concepts | 20: YAML grammar, generated tree, digest, guard, prepare, schema, schema cache, Python validation, package coercion, merge priority, lock repair, launcher, protocol, command codes, source modes, collection, release roots, machine mode, secret route, cache mark | 9: data file, native inputs, native lock, Nix types, native merge, host command, fresh machine, disk preflight, optional cache |
| Files | 5: `vendomat.yaml`, `devenv.yaml`, `devenv.nix`, `devenv.lock`, `.vendomat/` | 4: `vendomat.toml`, `devenv.yaml`, `devenv.nix`, `devenv.lock` |
| Vendomat commands | 10 named: shell, build, test, tasks, up, update, machines, prepare, path, check; plus pass-through | 1 named: new; bare entry; all other args pass through |
| Machine modes | 2: fresh-install and adopt-existing | 1: fresh install |

## Owner questions and handoff

| Question | Proposed result |
| --- | --- |
| O1 flake target | Disappears: withdraw the unused target. |
| O2 Basix name and repository | Repository ownership remains; Basix owns its data options. |
| O3 source modes | Disappears from the first release; defer mirror and keep. |
| O4 path, check, bump | Disappears from the first release. |
| O5 Attic timing | Remains: remove only after a real Harmonia gate passes. |
| O6 disk space | Closed by the owner's 2026-10-12 cleanup. |
| O7 real disk authorization | Remains withheld. No real disk write is in this plan. |
| O8 adoption comparison | Deferred with adoption. |
| O9 installer route | Remains: use an installer ISO before a real device. |
| O10 failed-unit wrapper gate | Disappears from Vendomat command routing; test the native safety gate in the machine slice. |

This review asks the owner to rule on two design choices before implementation:
accept direct TOML with native input edits, and allow the V5 and V6 ledgers to close
as history. The second ruling is required by the kickoff. Until then, their
disposition maps remain live records. The next session starts with the direct-read
and eager-validation slice in [PLAN.md](../PLAN.md). No consumer migration or
hardware step starts from this review alone.

# Project 20 decisions

**Date:** 2026-10-11. The owner chose project 20 as the future Vendomat concept. This turn changes
concept and plan only. The current implementation remains in place until the new gates pass.

| # | Decision | Effect |
| --- | --- | --- |
| 1 | Vendomat is the user command and runs pinned devenv after preparing a workspace. | The host launcher expands beyond `sync`. |
| 2 | `vendomat.yaml` is the routine user file for workspaces and the Basix system workspace. | The TOML runtime and separate `sync` step end at cutover. |
| 3 | Vendomat uses real declared option paths and native Nix merging. | Data values need type checks; unsupported values use native Nix. |
| 4 | Basix owns machine defaults, inventory, guards, fresh install, and adoption. | Vendomat prepares configuration and forwards native machine commands. |
| 5 | The source, store, Harmonia cache, and keyless first install decisions of project 19 carry forward. | The first boot needs no secret provider or signing key. |
| 6 | A new pin may require Nix to produce its option schema. | Syntax lint runs first; schema validation finishes before the requested operation. |
| 7 | There is one new runtime format after cutover. | A one-time converter may help, but the runtime has no permanent TOML compatibility path. |

## Research results, 2026-10-11

Each row is a recommendation that a fixture backs. The owner may revise it. A fixture result proves
an interface; it does not pass an implementation gate. See the
[research report](evidence/RESEARCH-2026-10-11.md).

| # | Decision (recommendation backed by fixture) | Evidence | Effect |
| --- | --- | --- | --- |
| 8 | D1. Parse `vendomat.yaml` with a stdlib hand parser. Use S1 `hand.py` as the basis. PyYAML is a test oracle in the dev group only. Do not use `yamlsubset.py` (another grammar), ruamel, or StrictYAML. | [S1](evidence/S1-yaml-subset.md) | DOOR-020 and DOOR-021. First slice is the strict reader. |
| 9 | D2. Generated data are plain definitions. Native merging decides. R2 open decision 4 proposed `mkOverride 90`; S2 disproves it, because a priority below 100 beats plain `devenv.nix` definitions and drops devenv's own list values. | [S2](evidence/S2-merge-priority.md) | DOOR-023. The documents never say "YAML always wins". |
| 10 | D3. Accept block scalars `\|` and `\|-`. R2 decision 16 proposed to reject them; S1 found 43 `types.lines` options that need them. | [S1](evidence/S1-yaml-subset.md) | DOOR-020. |
| 11 | D4. Store the schema in the user cache, not in the repository. R2 decision 8 proposed a committed schema; S3 found that a committed schema does not make an offline fresh clone work. The exporter lives in Vendomat (a Nix module and a Python reader). `devenv-py` stays a reference. | [S3](evidence/S3-schema-export.md) | DOOR-025, DOOR-026, DOOR-027. |
| 12 | D5. Commit `.vendomat/`. Testee evaluates before `prepare`, and an ignored fragment fails with no Vendomat hint. | [S5](evidence/S5-front-door.md) | DOOR-028. |
| 13 | D6. The guard is a module-wide throw with the escape variable `VENDOMAT_ALLOW_STALE`. | [S5](evidence/S5-front-door.md) | DOOR-029. The effect of `getEnv` on the eval cache is unproved. |
| 14 | D7. The launcher follows the S5 protocol and exit codes (64 to 72). | [S5](evidence/S5-front-door.md) | DOOR-030, DOOR-031, DOOR-033. |
| 15 | D8. Unnamed commands pass through with `exec`. | [S5](evidence/S5-front-door.md) | DOOR-033. |
| 16 | D9. Input following is native. Drop `_Discovery` and `NixResolver` in `devenvgen.py`. | [S9](evidence/S9-native-follows.md) | DOOR-022 and DOOR-036. |
| 17 | D10. `vendomat.yaml` has no format version key. The pinned release defines the format, and the host release only creates the first lock. R2 decision 6 proposed a `version` key; reject it to keep two reserved keys. Open proof: a host release older than the pin must exit 65 with a "use the pinned release" hint. | [R2](evidence/R2-requirements-v6-door.md), [S5](evidence/S5-front-door.md) | DOOR-022, DOOR-030. |
| 18 | D11. Harmonia starts through a path unit, and clients set `fallback = true`. This corrects project 19 and the first concept: a down cache blocks a build under default Nix settings. | [S6](evidence/S6-harmonia-two-vm.md) | DOOR-045, DOOR-046. |
| 19 | D12. Secret route 1 is the controller push. `install.secrets` is an install-time convenience only. | [S7](evidence/S7-keyless-secrets.md) | DOOR-040. |
| 20 | D13. The installer key is separate from the admin key. The controller re-pins the host key after a first boot or a disk loss. | [S7](evidence/S7-keyless-secrets.md) | DOOR-041. |
| 21 | D14. Write no converter. The inventory found 29 TOML files, 2 live V5 or V6 consumers, and 22 V4 files to delete. | [R3](evidence/R3-migration-inventory.md) | DOOR-052, DOOR-053. Supersedes the "one-time converter" idea in decision 7. |
| 22 | D15. The inventory schema follows S4. Mode names follow the fork: `fresh-install` and `adopt-existing`. | [S4](evidence/S4-machine-inventory.md) | DOOR-037. The `basix` name stays proposed. |

## Open owner decisions

| # | Question | Options | Recommendation |
| --- | --- | --- | --- |
| O1 | Flake target (GEN-\*, PRE-001, CLI-016, INP-008) | Withdraw; port; keep the TOML reader | Withdraw. |
| O2 | The `basix` option name and the repository that declares the inventory | Basix declares `basix.*`; or Vendomat declares it | Basix declares `basix.*`. Vendomat ships the guards that it consumes. |
| O3 | Source modes and collection commands (DOOR-055) | A `vendomat.sources` option, the hook refresh, and `prepare` clones; or a separate `vendomat collection` command | The option, the hook refresh, and `prepare` clones. Drop `backup` and the forge shorthand. |
| O4 | `path`, `check`, `bump` | Keep `path` and `check`, and let `bump` edit only `vendomat.yaml`; or withdraw `bump` | Keep all three on that basis. |
| O5 | Attic removal timing (DOOR-050) | Remove at cutover; or keep Attic push and live checks until the Harmonia live gate passes | Keep them until the Harmonia live gate passes. |
| O6 | Disk space on `/` (btrfs unallocated 93 MiB) | Run `btrfs balance` as root before more VM work; or stop VM work | **Resolved 2026-10-12.** The owner cleaned and balanced the disk: 23.09 GiB unallocated, metadata 71.6 %. |
| O7 | Real disk and hardware authorization | Grant it for named disks; or keep it withheld | Not given. This blocks the cutover gates. |
| O8 | Adopted-host capability comparison (BOOT-008 parity) | A read-only report of services and units before the first adopted switch; or none | Write the report. |
| O9 | Fresh-install route for real devices | A live installer ISO with a temporary key; or kexec | The ISO first. Kexec later. |
| O10 | May the front door run the failed-unit gate before `machines deploy` and `apply` (`MACH-022` against `MACH-005`)? | Yes, as a named exception to `MACH-005`; or no, the user runs it | Yes. A degraded host should not receive a new generation silently. |

## Status of the earlier open choices

Decision 7 listed five choices that need fixtures. The 2026-10-11 session settled four at fixture
level. Each still needs an implementation proof.

- **Settled by fixtures:** the shape of the Basix machine options (D15, [S4](evidence/S4-machine-inventory.md);
  the `basix` name and child names stay proposed under O2),
  the generated module priority (D2, [S2](evidence/S2-merge-priority.md)), schema refresh after a
  pin change ([S3](evidence/S3-schema-export.md)), and the post-install secret route (D12,
  [S7](evidence/S7-keyless-secrets.md)).
- **Settled by evidence:** a one-time converter has no value (D14).
- **Still open:** the `basix` name and owner (O2), source modes (O3), the real Basix core and installer
  route (O9), the offline missing-schema message, and the eval-cache effect of the guard.

See [PLAN.md](PLAN.md).

## Simplification proposal, 2026-10-12

This section proposes changes to the 2026-10-11 decisions. The older rows remain
as dated history. The owner has not yet ruled on the proposed TOML surface.
[Review evidence](evidence/SIMPLIFY-REVIEW-2026-10-12.md) records the alternatives
and capability losses. A fixture proves a mechanism, not an implementation gate.

| Proposal | Earlier decision or question | Result |
| --- | --- | --- |
| S16. Read user-owned `vendomat.toml` in Nix; keep inputs and imports in native `devenv.yaml`. | Decision 2; D1, D3, D4, D5, D6, D10 | Supersede the YAML choice, parser, schema export, generated tree, guard, and format-version debate. The isolated direct-TOML fixture supports file-level type errors. Pinned-devenv proof remains. |
| S17. Use Nix types and native merge; force set values at the operation gate. | Decision 3; D2; O10 | Keep native priorities. Replace Python schema checks. The S4 lazy-value finding makes eager forcing a gate. No Vendomat failed-unit wrapper is proposed. |
| S18. Use one host Vendomat release and its pinned fork. Bare entry opens the shell; one named `new` command creates a workspace; other args pass through. | Decision 1; D7, D8; O4 | Remove per-workspace Vendomat routing, launcher protocol, ten named commands, and nine special exits. Keep the pinned fork and native lock. |
| S19. Install fresh Basix machines with one typed record and a real disk preflight. | Decision 4; D15; O2, O8, O9 | Basix owns the data options. Defer adoption and its comparison. Keep the installer ISO choice open. Keep key separation and host-key re-pin. |
| S20. Boot the core without secrets. Configure Harmonia only after an administrator places a key. | Decision 5; D11, D12, D13; O5 | Defer the generic receiver, path unit, and SecretSpec routes. Keep signed cache, explicit client fallback, and the real live gate before Attic removal. |
| S21. Use native tagged source URLs and selected Nix roots. | Decision 5; D9; O1, O3 | Withdraw the unused flake target from the first path. Defer collection modes, hook, and builder. Keep native `follows`. |
| S22. Migrate the two live consumers by hand without a two-marker launcher. | Decision 7; D14; O5 | Keep concise conversion records. Retain the current Attic route until the real Harmonia gate. |

The owner must decide whether S16 replaces the earlier YAML decision before an
implementation changes a user format. The owner must also decide whether the V5
and V6 ledgers may close as history. The [requirement ledger](REQUIREMENTS.md)
preserves every ID and keeps their existing disposition map active pending that
ruling. O6 is already closed by the disk cleanup. O7 remains withheld; no real
disk write is authorized. O2 still needs a Basix repository placement. O9 still
needs a real installer ISO proof.

## Layer correction, 2026-10-12

The owner reminded us that Vendomat may constrain workflows above devenv.
The [review correction](evidence/SIMPLIFY-REVIEW-2026-10-12.md#layer-correction)
records the effect. These rows supersede parts of S16 to S21. They remain
proposals until the owner rules on the data format and fixtures pass.

| Proposal | Earlier row | Effect |
| --- | --- | --- |
| S23. The routine surface is a bounded Vendomat catalog. Native files are an explicit advanced door. | S16, S17; O2 | Routine users need no input URL, import path, or merge priority. The template imports only the fixed catalog module. Basix owns its machine catalog. |
| S24. Vendomat owns new, test, build, update, and machine workflows. Other devenv commands use `vendomat devenv ...`. | S18; O4, O10 | Restore a small workflow layer. A machine workflow runs disk preflight and a failed-unit gate before native actions. The `path`, `check`, and `bump` question stays closed. |
| S25. Vendomat moves a supported release ref and native lock together. | S18, S21 | The user updates by one intent. Devenv still owns exact lock contents. The edit protocol needs a pinned-fork fixture. |
| S26. One optional cache host supplies client settings. | S20; O5 | Keep signing-key placement manual. Derive each client's URL, trust, and fallback from one host record. A two-machine fixture must prove the route. |

O10 remains open at the owner level: the proposal now answers **yes** to a
failed-unit gate in Vendomat's machine workflow. O5, O7, and O9 remain open
as described above. The owner still needs to rule on TOML and the V5/V6
ledger status. The correction does not authorize a machine or disk change.

# Project 20 implementation plan

**Date:** 2026-10-11. [CONCEPT.md](CONCEPT.md) is the chosen future design.
[REQUIREMENTS.md](REQUIREMENTS.md) preserves the proposed IDs. This plan does not report a gate as
passed until its recorded fixture passes on the pinned tools.

## Order

| Stage | Deliverable | Gate |
| --- | --- | --- |
| 0. Authority | Map affected V5 and V6 IDs to retained or successor claims. Record the pinned devenv, Nix, and nixpkgs inputs. | No missing or reused requirement ID; `testee verify --full` green |
| 1. Format | Build the `vendomat.yaml` parser, linter, and canonical generated files. Replace the old workspace template. | Accepted and rejected YAML corpus; unchanged input rewrites no file |
| 2. Pins and schema | Generate native inputs, resolve the lock through devenv, and validate option data against a schema for those pins. | Neutral-data schema export, fresh lock, changed tag with new option, pinned offline entry, and clear missing-schema fault |
| 3. Native config | Read generated JSON in a Nix module. Prove package references, unsupported types, and module priorities. | Scalar, list, attribute-set, `mkDefault`, `mkForce`, and secret canary fixtures |
| 4. Front door | Route shell, build, test, tasks, up, update, and machines through pinned Vendomat. Update the launcher and direnv. | New workspace, pinned workspace, shell re-entry, bypass, and command exit-code fixtures |
| 5. Basix machines | Express the data inventory in the Basix system workspace. Keep fresh-install and adopted-host guards. | Keyless first boot, protected-disk refusal, adopted-host activation, post-install secret delivery |
| 6. Source and cache | Build tags with release roots. Replace Attic with signed Harmonia and inventory-derived client trust. | Two-machine cold substitution, absent-path fallback, release root after garbage collection |
| 7. Migration | Convert a real consumer, report values needing native Nix, and remove old runtime routes. | Consumer shell and machine plan pass; no TOML, `sync`, or Attic path remains in the runtime |
| 8. Cutover | Review real hardware facts and run the required machine gates. | All named blockers closed with logs and owner review before disk writes |

## Implementation rules

- Build each new interface in one small vertical slice before removing its old counterpart.
- Keep the current system bootable while a new host launcher or workspace pin is introduced.
- Treat `vendomat.yaml`, the Basix inventory names, and every command name as proposed until a
  fixture proves them on pinned tools.
- Keep raw logs under `~/.local/state/vendomat/`. Record the command, input revisions, expected
  result, actual result, and inference in the repository.
- Run `testee verify --full` for each integrated change. Run `testee check e2e` when the module,
  toolchain, or consumer integration changes.
- Use a one-time migration tool when it earns its cost. Do not keep TOML and YAML runtime paths in
  parallel after the cutover.

## Decisions that a fixture must settle

1. The exact Basix machine option names and which options have a safe data form.
2. The priority of generated definitions and the behavior of native overrides.
3. The schema refresh sequence when a newly selected input defines an option.
   The fixture must prove that schema export works before validated user data exists.
4. The post-install SecretSpec delivery route for fresh and adopted machines.
5. The migration report format and whether a converter helps more than a manual edit.

A failed fixture changes the concept, requirements, and implementation together. Do not claim a
passed machine, cache, or recovery gate from a unit test.

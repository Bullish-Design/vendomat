# Project 20 requirement ledger

**Date:** 2026-10-11. These IDs preserve the first project 20 draft. A new interface remains
proposed until a fixture proves it on pinned tools. Do not reuse or renumber an ID.

## Original IDs

| ID | Original requirement | Disposition |
| --- | --- | --- |
| `DOOR-001` | A workspace MUST have one user file, `vendomat.yaml`. `devenv.yaml` and `devenv.nix` MUST be template stubs that routine work never changes. | Kept. Native Nix remains an explicit escape hatch. |
| `DOOR-002` | Every Vendomat command that starts devenv MUST lint `vendomat.yaml`, validate it against the schema, and regenerate `.vendomat/` before it starts devenv. A lint or schema fault MUST stop the command before Nix runs and MUST name the file, line, key, and reason. | Superseded by `DOOR-011`. A new pin can require Nix before its schema exists. |
| `DOOR-003` | `inputs` and `imports` MUST be the only reserved top-level keys. Every other key MUST be a real option path, with no translation table. | Kept. Basix must declare its data options. |
| `DOOR-004` | A string in a package-typed option MUST name a nixpkgs attribute. No other value encoding is allowed. | Kept for the data format. Unsupported values use native Nix. |
| `DOOR-005` | The linter MUST accept only the strict YAML subset of section 4. | Superseded by `DOOR-012`. The original example contradicted the stated subset. |
| `DOOR-006` | The Vendomat module MUST read `.vendomat/config.json` with `builtins.fromJSON`. A value from `vendomat.yaml` MUST win over a module's plain definition and lose to `devenv.nix`. | Superseded by `DOOR-013`. Native Nix merge and priority rules require a fixture. |
| `DOOR-007` | The generator MUST write a generated file only when its content changes. | Kept. |
| `DOOR-008` | The schema MUST be generated from option declarations at the workspace's pins. | Kept. |
| `DOOR-009` | Plain `devenv shell` after a change to `vendomat.yaml` MUST stop with a message that names the Vendomat command to run. | Kept. Vendomat remains the supported build and machine route. |
| `DOOR-010` | The host launcher MUST serve every command inside a workspace with the build that `devenv.lock` pins. Supersedes `DEL-020`. | Kept. First entry uses the host release when no lock exists. |

## Successor IDs, proposed until fixtures pass

| ID | Requirement | Proof |
| --- | --- | --- |
| `DOOR-011` | Vendomat MUST parse and lint before Nix. It MUST resolve or reuse input pins before schema validation. It MUST validate values before the requested devenv operation. It MUST report an unavailable pinned schema before an offline operation. | New-pin and offline workspace fixtures |
| `DOOR-012` | The linter MUST accept block maps, block lists, quoted strings, numbers, booleans, and null. It MUST reject anchors, aliases, tags, flow collections, and implicit strings with locations. | Accepted and rejected YAML corpus |
| `DOOR-013` | The config reader MUST retain native Nix module merging. It MUST report conflicting definitions with locations. Any claimed priority between YAML, imported modules, and `devenv.nix` MUST pass scalar, list, attribute-set, `mkDefault`, and `mkForce` fixtures. | Priority matrix on pinned devenv and Nix |
| `DOOR-014` | Vendomat MUST keep SecretSpec values out of generated files and the Nix store. The linter MUST reject values in recognized secret fields. | Secret canary and generated-tree scan |
| `DOOR-015` | The Basix system workspace MUST describe fresh and adopted hosts through data options in `vendomat.yaml`. It MUST preserve disk guards and native machine activation. | Fresh and adopted virtual machines |
| `DOOR-016` | A fresh Basix core MUST install, boot, and work without a private key, SecretSpec provider, or cache service. A later key MUST be deliverable before its dependent service starts. | Keyless boot and post-install secret fixture |
| `DOOR-017` | A marked host MUST serve its store through signed Harmonia after receiving a signing key. Other hosts MUST trust only its public key and retain cache fallback. | Two-machine cold substitution and cache failure fixture |
| `DOOR-018` | A format migration MUST report each converted and unsupported value. It MUST not activate a machine. The new runtime MUST use only `vendomat.yaml`. | Real consumer migration fixture |

The V5 and V6 requirement IDs remain in their original ledgers. A successor specification must map
each affected active ID to a new ID or an explicit retained claim before implementation cutover.

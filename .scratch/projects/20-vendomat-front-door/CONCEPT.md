# Project 20: Vendomat as the front door to devenv

**Date:** 2026-10-11. **Status:** Draft concept for owner review. Every file name, key, command,
and requirement ID here is proposed until a fixture proves it on the pinned tools.
**Builds on:** [project 16](../16-vendomat-devenv-layer/CONCEPT-V6.md) (V6),
[project 17](../17-devenv-model-layer/CONCEPT.md) (typed models and schema), and
[project 19](../19-vendomat-foundation-layer/CONCEPT.md) (source, store, and cache under Basix).
**Evidence:** [wrapper spikes](../16-vendomat-devenv-layer/evidence/wrapper-spikes-2026-10-10.md)
and [fork `v2.4.0-vendomat.3`](../16-vendomat-devenv-layer/evidence/fork-3-inheritance.md).

This draft changes no authority. It answers project 19's open question 2 (where the workspace
bridge lives) and replaces the V6 workspace flow (`[imports]`, `[settings]`, `vendomat sync`).

## 1. Decision in one paragraph

The user runs Vendomat, and Vendomat runs devenv. Each workspace has one user file,
`vendomat.yaml`. It names the sources, the modules to import, and values for real option names.
Every Vendomat command reads and lints that file, writes two generated files, and then starts
devenv. devenv composes, locks, and evaluates. The user never edits Nix for routine work, and
errors arrive in plain words before Nix runs.

## 2. How we got here

1. Spikes S1 and S2 showed that nothing inside devenv 2.4.0 can run before devenv resolves inputs.
   A task cannot repair a stale fragment, and a failing task does not stop the shell.
2. Fork `v2.4.0-vendomat.3` (patches 0007 and 0008) lets devenv inherit the inputs of an imported
   source's own `devenv.yaml`, and fixes a cold first entry that fails on `.2`. Vendomat therefore
   no longer resolves transitive inputs or prefetches sources.
3. Basix teaches general computing, not Nix. Hiding Nix at first is a feature. A curated
   vocabulary over devenv and nixpkgs would cost too much upkeep, so the user file uses the real
   option names, and a generated schema gives editor help.
4. Nix reads TOML and JSON natively and YAML not at all. That stops mattering when Vendomat is the
   front door: Python reads the YAML before devenv starts, and Nix reads generated JSON.
5. A step before devenv is a problem only when people run devenv directly. When Vendomat is the
   command people run, that step is simply the first thing it does.

## 3. The workspace files

| File | Content | Owner |
| --- | --- | --- |
| `vendomat.yaml` | Sources, imports, and values | User |
| `devenv.yaml` | `imports: [ ./.vendomat ]` and nothing else | Template; never changes |
| `devenv.nix` | `{ ... }: { }`; the opt-in door to Nix | Template; the user may edit it later |
| `devenv.lock` | Exact revisions | devenv |
| `.vendomat/devenv.yaml` | The `inputs` and `imports` of `vendomat.yaml` | Vendomat, generated |
| `.vendomat/config.json` | Every other key of `vendomat.yaml`, as data | Vendomat, generated |
| `.vendomat/digest` | Hashes of `vendomat.yaml` and the generated files | Vendomat, generated |

Example:

```yaml
# vendomat.yaml
# yaml-language-server: $schema=.vendomat/schema.json
inputs:
  greeting:
    url: git://myhost/modules?ref=refs/tags/v1.0.0&dir=greeting
imports:
  - greeting/devenv
packages: ["ripgrep", "jq"]
languages:
  python:
    enable: true
    version: "3.13"
services:
  postgres:
    enable: true
greeting:
  text: "Hello"
```

## 4. The `vendomat.yaml` format

- **Reserved top-level keys:** `inputs` and `imports`. They have devenv's own meaning and shape,
  and they go to `.vendomat/devenv.yaml` unchanged.
- **Every other key is a real option path.** `languages.python.version` sets the devenv option
  `languages.python.version`. There is no translation table and no Vendomat namespace.
- **One encoding rule.** A string in a package-typed option names a nixpkgs attribute: `"jq"` means
  `pkgs.jq`. This is project 17's `PkgRef`.
- **Data only.** Strings, numbers, booleans, lists, and maps. An option whose type is a function, a
  module, or raw Nix is not settable here; the user, or an author, sets it in `devenv.nix`.
- **A strict YAML subset.** Block maps and block lists, quoted strings, numbers, booleans, and
  comments. No anchors, tags, or implicit strings. The linter rejects everything else, so YAML's
  traps (`no` as `false`, bare strings, indentation slips) become lint errors.
- **Editor help.** The schema is generated from the option declarations at the workspace's pins
  (project 17, gates GM2 and GM5). It gives completion, hover documentation, and type checks in
  any editor that reads JSON Schema for YAML.

## 5. The front door

Every Vendomat command that starts devenv does the same three steps:

1. **Read and lint** `vendomat.yaml`, then validate it against the schema. A fault stops here with
   the file, the line, the key, and the reason.
2. **Generate** `.vendomat/devenv.yaml`, `.vendomat/config.json`, and `.vendomat/digest`. Write a
   file only when its content changes, so devenv's evaluation cache stays warm.
3. **Run devenv** with the user's command.

Proposed command surface: `vendomat shell`, `up`, `test`, `build`, `update`, `tasks`, and
`machines`, each with devenv's arguments, plus `vendomat -- <any devenv arguments>` as a pass
through. The existing `check`, `path`, `bump`, and `machine install` stay. `vendomat sync`
disappears as a separate step; `vendomat lock` may remain as "generate, then `devenv update`".

The Vendomat devenv module reads `.vendomat/config.json` with `builtins.fromJSON` and assigns each
key to its option path. Values from `vendomat.yaml` win over a module's plain definitions.
`devenv.nix` wins over `vendomat.yaml`, because it is the advanced escape hatch. The exact
priorities need a fixture.

## 6. Version, bootstrap, and integration

- **The pinned Vendomat.** The host launcher already finds the build that `devenv.lock` pins, by NAR
  hash, and uses the host release to bootstrap a workspace with no lock. Under this design it
  serves every command, not only `sync`.
- **direnv.** `use vendomat` runs the front door's first two steps and then loads devenv's
  environment.
- **CI and scripts** call `vendomat test` or `vendomat -- <args>`, never devenv directly.
- **Inside the shell,** the pinned `vendomat` is on `PATH` (`VMOD-020`), so tasks and scripts can
  call it.

## 7. Bypass protection

A user who edits `vendomat.yaml` and then runs plain `devenv shell` would get the old generated
files. The existing digest assertion in the generated module stops that shell entry and names the
fix: run Vendomat. A plain `devenv build` does not evaluate assertions (`NAT-025`), so `vendomat
build` is the supported route.

## 8. Ownership

| Part | Owner |
| --- | --- |
| Composition, locking, inheritance, evaluation, activation | devenv (the fork) |
| `vendomat.yaml` format, linter, generator, config reader, schema wiring, front door | Vendomat |
| Source, store, and cache | Vendomat (project 19) |
| Starter files (bundles), lessons, the choice to hide Nix at first | Basix |
| Option names, types, and documentation | devenv, NixOS, and Home Manager upstream |

This adjusts project 19: Vendomat is source, store, and cache, plus the configuration surface over
devenv. A Basix bundle is a starter `vendomat.yaml`.

## 9. Effect on V6 and on work landed on 2026-10-10 and 2026-10-11

| Item | Effect |
| --- | --- |
| `DEL-020` (launcher serves `sync` only) | Reverse: the launcher serves every command |
| `VMOD-020` (pinned `vendomat` in the shell) | Keep |
| `VMOD-021` (push task) | Decided by project 19, which removes `vendomat push` |
| `vendomat.toml` (`[forge]`, `[inputs]`, `[imports]`, `[settings]`) | Replaced by `vendomat.yaml` |
| `vendomat.settings.<module>` option namespace | Removed; modules declare normal options |
| `src/vendomat/devenvgen.py` transitive resolution and prefetch | Removed; `.3` inherits inputs |
| `src/vendomat/registry.py` | Replaced by the `vendomat.yaml` reader and linter |
| `src/vendomat/yamlsubset.py` | Becomes the base of the linter |
| Digest and its assertion | Kept, for bypass protection |
| Fork `.3` | Required |

## 10. Proposed requirements

| ID | Requirement |
| --- | --- |
| `DOOR-001` | A workspace MUST have one user file, `vendomat.yaml`. `devenv.yaml` and `devenv.nix` MUST be template stubs that routine work never changes. |
| `DOOR-002` | Every Vendomat command that starts devenv MUST lint `vendomat.yaml`, validate it against the schema, and regenerate `.vendomat/` before it starts devenv. A lint or schema fault MUST stop the command before Nix runs and MUST name the file, line, key, and reason. |
| `DOOR-003` | `inputs` and `imports` MUST be the only reserved top-level keys. Every other key MUST be a real option path, with no translation table. |
| `DOOR-004` | A string in a package-typed option MUST name a nixpkgs attribute. No other value encoding is allowed. |
| `DOOR-005` | The linter MUST accept only the strict YAML subset of section 4. |
| `DOOR-006` | The Vendomat module MUST read `.vendomat/config.json` with `builtins.fromJSON`. A value from `vendomat.yaml` MUST win over a module's plain definition and lose to `devenv.nix`. |
| `DOOR-007` | The generator MUST write a generated file only when its content changes. |
| `DOOR-008` | The schema MUST be generated from option declarations at the workspace's pins. |
| `DOOR-009` | Plain `devenv shell` after a change to `vendomat.yaml` MUST stop with a message that names the Vendomat command to run. |
| `DOOR-010` | The host launcher MUST serve every command inside a workspace with the build that `devenv.lock` pins. Supersedes `DEL-020`. |

## 11. Fixtures before acceptance

1. A template workspace: one module from the collection, two values, and a package, entered
   through `vendomat shell` on fork `.3`, with no Nix edit.
2. The priority rule: the same option in a module, `vendomat.yaml`, and `devenv.nix`.
3. The linter: a shared test set of accepted and rejected files, including `no`, bare strings,
   anchors, and tab indentation.
4. The schema: completion and a type error in an editor's YAML language server, from a schema
   generated at the pins.
5. Bypass: plain `devenv shell` after an edit stops with the named message.
6. The evaluation cache: an unchanged `vendomat.yaml` gives a warm entry.
7. Machines: whether `vendomat.yaml` also carries NixOS and Home Manager options for each host, or a
   second file does. The schema size for NixOS options needs a measurement.

## 12. Open questions

1. The command names, and whether every devenv command gets its own Vendomat command or only the
   pass-through.
2. How a Basix bundle combines with a user's file: copy once, or a reserved `extends` key.
3. Whether `devenv.nix` stays visible at the start, or the template hides it until the user asks.
4. The migration of existing `vendomat.toml` workspaces, including `vendomat-demo`.

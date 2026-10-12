# Project 20: Vendomat as the front door to Basix and devenv

**Decision:** The owner chose this direction on 2026-10-11. This document is the design authority
for future Vendomat work. The current code still implements earlier interfaces. Each new interface
needs a fixture before it becomes an implementation requirement.

**Evidence:** [project 16](../16-vendomat-devenv-layer/CONCEPT-V6.md) records the machine and wrapper
probes. [Project 17](../17-devenv-model-layer/CONCEPT.md) records option models and schemas.
[Project 18](../18-single-disk-cache-concept/CONCEPT.md) records the Harmonia experiment.
[Project 19](../19-vendomat-foundation-layer/CONCEPT.md) records the source, store, cache, and
keyless-install decisions. Those projects remain evidence, not competing designs.

## 1. Goal and boundary

Basix makes NixOS installable on a NixOS-supported device, either on a new disk or over an existing
NixOS installation. A user starts with a working system, then adds their own devenv modules. The
first install must boot and work without a private key, SecretSpec provider, or cache service.

Vendomat is the command the user runs. It prepares configuration and then invokes pinned devenv.
It also manages release-tagged source, retained build outputs, and a shared binary cache. Nix and
devenv still select and lock inputs. NixOS and Home Manager still activate systems. Vendomat is not
a dependency resolver, a second lock, a daemon, or a deployment engine.

| Layer | Responsibility |
| --- | --- |
| Vendomat | User configuration, validation, generated devenv inputs and option data, command entry, source, build roots, cache wiring |
| Basix | Starter configuration, machine inventory, install safety, adoption, lessons, core role |
| devenv and Nix | Input resolution, locks, module evaluation, builds, machine operations |
| NixOS and Home Manager | System and user activation, rollback |
| SecretSpec | Secret declarations and provider lookup when a secret is needed |

## 2. The user contract

A workspace has one file for routine configuration: `vendomat.yaml`. The Basix system workspace
uses the same file for its machine inventory and data options. Vendomat generates the devenv files
that implement that configuration. The user can add native Nix in `devenv.nix` when an option needs a
function, a module, or another value that the data format cannot express.
The Basix system template imports the Basix module; an ordinary workspace does not.

`secretspec.toml` is separate and appears only when the installation needs a secret. The user keeps
private values out of `vendomat.yaml`. The Nix lock stays a native `devenv.lock` file.
Vendomat never resolves a SecretSpec value into generated data. The linter rejects recognized
secret fields, but it cannot identify every arbitrary string that a user might treat as a secret.

| File | Owner | Purpose |
| --- | --- | --- |
| `vendomat.yaml` | User | Inputs, imports, and data values for declared options |
| `devenv.yaml` | Template | Stable import of `.vendomat/` and pinned devenv settings |
| `devenv.nix` | Template, then user if needed | Native modules and explicit overrides |
| `devenv.lock` | devenv | Exact input revisions |
| `.vendomat/` | Vendomat | Generated inputs, option data, schema, and content hashes |
| `secretspec.toml` | User, when needed | Secret declarations without values |

The user runs `vendomat shell`, `vendomat build`, `vendomat test`, and `vendomat machines ...`.
Vendomat also offers a pass-through for devenv commands that have no named Vendomat form. The host
launcher finds the Vendomat build pinned by the workspace lock. A new workspace uses the host
release to create its first lock. Every command reports which release it used.

## 3. The configuration format

`inputs` and `imports` keep devenv's meaning. Every other top-level key names a declared devenv
option. A Basix module declares its machine inventory as data options under `basix` (proposed name).
Vendomat does not create a second name for a native option.

The supported YAML form contains block maps, block lists, quoted strings, numbers, booleans, and
null. It excludes anchors, aliases, tags, implicit strings, and flow collections. The linter names
the file, line, key, and reason for a fault. One string in a package-typed option names a nixpkgs
attribute. Values with no safe data form use native Nix. Vendomat reports that limit; it does not
silently coerce a value.

Proposed system workspace example:

```yaml
inputs:
  tools:
    url: "git://collection.example/tools?ref=refs/tags/v1.0.0"
imports:
  - "tools/devenv"
packages:
  - "ripgrep"
basix:
  machines:
    laptop:
      mode: "adopt-existing"
      disks:
        system:
          byId: "/dev/disk/by-id/example-id"
          role: "existing-system"
```

The `basix` option path and its child names are proposed. The machine fixture must prove them.
Basix turns those facts into native devenv Machines and NixOS configuration. Module authors still
write native NixOS and Home Manager modules. The inventory never uses a raw kernel disk name.

## 4. The command sequence

Vendomat applies the same sequence to each command that needs a workspace:

1. Parse and lint `vendomat.yaml` without running Nix. Stop on an invalid YAML form or input shape.
2. Generate the native input and import fragment. Ask devenv to resolve or reuse the exact input
   revisions in `devenv.lock`.
3. Load the option schema for those revisions. Generate it from pinned option declarations when it
   is missing. Validate the data values and name unsupported option types.
4. Write the option data and content hashes only when content changes. Then run the requested devenv
   command. A validation fault stops before this command.

A first run or a changed pin may need Nix to obtain the option schema. Vendomat does not promise
full schema validation before Nix starts. It does promise that validation finishes before the
requested build, shell, or machine operation starts. An offline run uses the schema for its locked
revisions or stops with a clear missing-schema error.
The schema generator must read declarations before validated user values exist. The first fixture
must prove an export with neutral generated option data. If that export needs user values, revise
the command sequence before implementing it.

Native Nix module merge rules remain authoritative. Vendomat will not claim that all YAML values
always override imported modules. The implementation must prove the chosen priorities for scalars,
lists, attribute sets, `mkDefault`, and `mkForce`. Until then, conflicts stop with both definition
locations. `devenv.nix` remains the explicit way to use native priority operators.

Direct `devenv` use may read stale generated files. A digest guard stops supported shell and test
entries with a command to run. Vendomat is the supported route for build and machine commands,
which may not evaluate that guard. The front door must work without the host launcher after entering
a pinned shell.

## 5. Source, store, and cache

One installation keeps a collection of immutable release tags. Workspaces name tag-pinned sources;
`devenv.lock` records exact revisions. The pinned devenv fork inherits inputs from imported sources.
Vendomat generates direct inputs and imports, but does not resolve a second transitive input graph.
Third-party source can be mirrored or kept as a clone. A user changes a tag explicitly; normal
shell entry does not select a newer release.

The collection builder builds each release tag and writes one garbage-collection root per built
tag. NixOS keeps system generations through its native roots. The building host collects other
unrooted paths only under disk pressure. Built outputs remain derived data; source and tags are the
record.

A single machine uses its local Nix store with no cache service. When machines share outputs, one
marked host serves its store through Harmonia as a signed, read-only binary cache. Other hosts trust
its public key and keep normal cache fallback. The serving host builds shared outputs. Harmonia
serves every valid path in that host's store, so network access must match that visibility. There is
no push credential, cache database, second cache copy, or Vendomat cache protocol.

## 6. Machines and secrets

Basix uses one inventory for fresh installation and adoption. Each host records its mode and stable
disk identities. A fresh install must refuse an unexpected target disk or a protected disk. An
adopted NixOS host never runs disk installation. devenv Machines builds, plans, activates, and
rolls back through its native commands. Basix supplies guards and the core NixOS role.
The user launches a fresh install from a controller or live installer that has Vendomat and pinned
devenv. A blank target does not run Vendomat before its first boot. The same system workspace can
later manage the running target or adopt another NixOS host.

The core role boots without private keys. A user may create a key after first boot, deliver it, and
then enable a dependent service. The Harmonia server needs its signing key before it starts; cache
clients need only the public key. SecretSpec becomes required when the first secret is used.
An installer may use temporary credentials to reach a target. Those credentials do not become a
persistent Basix core requirement.
`install.secrets` is an optional route for a service enabled at fresh install. A post-install route
must deliver a later key to either a fresh or adopted host before activation. That route remains an
open interface until a fixture proves secure delivery and recovery.

A data-only YAML file cannot express every NixOS hardware or service module. Basix must provide a
working default for each supported installation route. A user can add a native module for device
needs that the default cannot cover. Neither Vendomat nor Basix claims support for hardware that
NixOS itself cannot run.

## 7. Release and migration

The new format replaces `vendomat.toml`, `[settings]`, and the separate `vendomat sync` command.
The new cache route replaces Attic and `vendomat push`. A release may provide a one-time migration
command, but it does not run two configuration formats indefinitely. The old requirement IDs remain
in [REQUIREMENTS.md](REQUIREMENTS.md) with their dispositions.

The transition must keep a working host release while the new launcher and workspace pin change.
A conversion report lists every value that moved and every value that needs native Nix. No machine
activation follows a format conversion without a reviewed plan.

## 8. Proof before acceptance of an implementation

1. A fresh template workspace enters through Vendomat with no lock and no Nix edits.
2. A changed imported tag resolves inputs, updates the schema, and validates a new option.
3. Pinned offline entry uses the exact schema and changes no generated file.
4. Values and priorities match native Nix evaluation across scalar, list, and attribute-set options.
5. Unsupported types, malformed YAML, recognized secret fields, and stale direct devenv entry fail
   clearly.
6. A controller installs a fresh virtual machine. It boots the Basix core without keys. Another run
   delivers a key after boot.
7. A second virtual machine substitutes a signed output from Harmonia. A release root survives
   garbage collection, and an absent cache path falls back to a normal build.
8. An adopted NixOS virtual machine receives a later secret and activates without disk writes.
9. A real consumer migrates from TOML, enters through Vendomat, and records the change in startup
   time and user steps.
10. The existing real-machine safety gates run before any hardware cutover.

A passed unit test does not replace a virtual-machine, cache, adoption, or real-machine proof.
V5 remains the running implementation until these gates support a release.

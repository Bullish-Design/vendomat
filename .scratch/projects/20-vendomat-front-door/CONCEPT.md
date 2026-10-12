# Project 20: Vendomat as the front door to Basix and devenv

**Decision:** The owner chose this direction on 2026-10-11. This document is the design authority
for future Vendomat work. The current code still implements earlier interfaces. Each new interface
needs a fixture before it becomes an implementation requirement.

**Revised 2026-10-11** after the research spikes; see
[evidence/RESEARCH-2026-10-11.md](evidence/RESEARCH-2026-10-11.md). A fixture result proves an
interface. It does not pass an implementation gate. Every name below stays proposed until an
implementation proves it on the pinned tools.

**Evidence:** [project 16](../16-vendomat-devenv-layer/CONCEPT-V6.md) records the machine and wrapper
probes. [Project 17](../17-devenv-model-layer/CONCEPT.md) records option models and schemas.
[Project 18](../18-single-disk-cache-concept/CONCEPT.md) records the Harmonia experiment.
[Project 19](../19-vendomat-foundation-layer/CONCEPT.md) records the source, store, cache, and
keyless-install decisions. Those projects remain evidence, not competing designs. The spike records
are in [evidence/](evidence/): S1 (YAML), S2 (merge), S3 (schema), S4 (inventory), S5 (front door),
S6 (Harmonia), S7 (keyless and secrets), S9 (follows).

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

A workspace has one file for routine configuration: `vendomat.yaml` (DOOR-019). The Basix system
workspace uses the same file for its machine inventory and data options. Vendomat generates the
files under `.vendomat/` that implement that configuration. Vendomat never edits `devenv.yaml` or
`devenv.nix`. The user can add native Nix in `devenv.nix` when an option needs a function, a
module, or another value that the data format cannot express.
The Basix system template imports the Basix module; an ordinary workspace does not.

One file does not mean YAML overrides everything. A plain definition in a library module cannot
be overridden from `vendomat.yaml`: Nix reports a conflict (see section 4). To change such a value,
set it with `lib.mkForce` in `devenv.nix`, or ask the library author to use `lib.mkDefault`.

`secretspec.toml` is separate and appears only when the installation needs a secret. The user keeps
private values out of `vendomat.yaml`. The Nix lock stays a native `devenv.lock` file.
Vendomat never resolves a SecretSpec value into generated data. The linter rejects a non-empty
string under a secret-named key (DOOR-035). It cannot identify every arbitrary string that a user
might treat as a secret.

| File | Owner | Purpose |
| --- | --- | --- |
| `vendomat.yaml` | User | Inputs, imports, and data values for declared options |
| `devenv.yaml` | Template | Stable import of `.vendomat/` and pinned devenv settings |
| `devenv.nix` | Template, then user if needed | Native modules and explicit overrides |
| `devenv.lock` | devenv | Exact input revisions |
| `.vendomat/` | Vendomat | Generated input fragment, option data, and content digest; committed (DOOR-028) |
| `secretspec.toml` | User, when needed | Secret declarations without values |

The user runs `vendomat shell`, `vendomat build`, `vendomat test`, and `vendomat machines ...`.
Vendomat also passes other devenv commands through with `exec`, which keeps the exit code, signals,
and terminal (DOOR-033). Inside a workspace with a pinned `vendomat` lock node, the host launcher
runs the pinned build. A new workspace uses the host release to create its first lock. A missing
pinned build stops the command; it does not fall back to the host release (DOOR-030). Every
command prints the Vendomat release and the devenv build it used (DOOR-031). A workspace carries
the pinned Vendomat as the `vendomat` lock node (DOOR-056).

## 3. The configuration format

`inputs` and `imports` are the only reserved keys (DOOR-022). Every other top-level key names a
declared devenv option. An `inputs` entry uses the `devenv.yaml` input fields as written,
including `follows` and `inputs.<name>.follows`. Vendomat rejects an input name that equals a module
argument, such as `lib`, `pkgs`, or `config`. A Basix module declares its machine inventory as
data options under `basix` (proposed name). Vendomat does not create a second name for a native
option.

The supported YAML form is a strict grammar (DOOR-020):

- Block maps and block lists only. `[]` and `{}` appear only as empty values.
- A plain key matches `[A-Za-z_][A-Za-z0-9_-]*` and is not a YAML boolean or null word.
  Quote any other key, such as `"/"` or a host name. A dot never separates an option path,
  even in a quoted key. Write nested maps for an option path.
- A plain value is `true`, `false`, `null`, or a decimal integer. Quote every other scalar.
  Floats have no data form.
- Block scalars `|` and `|-` are allowed. Comments are allowed.
- Anchors, aliases, tags, merge keys, directives, and second documents are errors.
- The file is UTF-8 with no byte order mark, LF line ends, no tabs, and a final LF. Depth is at most 64.
- A duplicate key at any depth is an error that names both lines.

The linter reports each fault as `file:line:col: key.path: reason`. Vendomat turns the file into
canonical JSON whose bytes do not depend on key order, comments, or quote style (DOOR-021).
A string in a package-typed option names a dotted nixpkgs attribute path. A string in a path-typed
option is relative to the workspace root (DOOR-024). Values with no safe data form use native Nix.
Vendomat reports that limit and names the key; it does not silently coerce a value.

Source modes (`keep` or `mirror`) are not input keys. Their form is an open owner decision
(DOOR-055). The proposal is a declared option, `vendomat.sources.<input>.mode`.

Proposed system workspace example. It shows both machine modes:

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
    box:
      mode: "fresh-install"
      stateVersion: "26.05"
      target:
        host: "root@192.0.2.10"
      disks:
        newsys:
          byId: "/dev/disk/by-id/nvme-EXAMPLE-NEW-0001"
          role: "install-target"
      users:
        owner:
          admin: true
          authorizedKeys:
            - "ssh-ed25519 AAAA... owner@example"
    laptop:
      mode: "adopt-existing"
      stateVersion: "23.11"
      disks:
        system:
          byId: "/dev/disk/by-id/nvme-EXAMPLE-LAPTOP-0003"
          role: "existing-system"
      filesystems:
        "/":
          device: "/dev/disk/by-uuid/11111111-2222-4333-8444-555555555555"
          fsType: "ext4"
```

The `basix` option path and its child names are proposed. Evaluation proved them
([S4](evidence/S4-machine-inventory.md), DOOR-037); no activation ran. A machine entry holds
`mode`, `system`, `hostName`, `stateVersion`, `target.host`, `disks.<id>`, `filesystems.<mount>`
(adopt only, by UUID), `boot.loader`, `hardware`, and `users` with public keys. The module maps
each entry onto native `machines.<name>` and keeps the existing guards. Basix turns those facts into
native devenv Machines and NixOS configuration. Module authors still write native NixOS and Home
Manager modules. The inventory never uses a raw kernel disk name. Host, user, and path names come
from the inventory; Basix has no owner-specific default (DOOR-038).

## 4. The command sequence

Vendomat applies the same sequence to each command that needs a workspace (DOOR-027):

1. Lint `vendomat.yaml` without running Nix. Stop on an invalid YAML form or input shape.
2. Generate the native input and import fragment.
3. Compare `devenv.lock` with the fragment. Run `devenv update <input>` only on a mismatch.
   devenv alone writes `devenv.lock`.
4. Compute the schema cache key. It hashes the devenv build path, the system, the export flags,
   the fragment, `devenv.lock`, and the workspace Nix files. It never hashes option data.
5. Load the option schema from `$XDG_CACHE_HOME/vendomat/schema/`, or export it. A cache hit
   starts no devenv process (DOOR-026).
6. Validate the data values in Python. Name the file, line, key path, and reason for a fault.
7. Write the option data only when content changes. Then run the requested devenv command.

A first run or a changed pin may need Nix to export the option schema. Vendomat does not promise
full schema validation before Nix starts. It does promise that validation finishes before the
requested build, shell, or machine operation starts. Nix checks an option type only when something
reads the option, so Vendomat validates every value eagerly. An offline run uses the schema for its
locked revisions. If the source is not fetched, it exits 68 with a missing-schema message
(message text is a draft).

The schema export reads declarations with neutral data and `_module.check = false`, one top-level
key at a time (DOOR-025). It needs no user value. The export fixture
proved this ([S3](evidence/S3-schema-export.md)). One rule follows for module authors: do not read
`config`, `pkgs`, or a data file in `imports` or in an option declaration.

Native Nix module merge rules stay authoritative (DOOR-023). The generated data are plain
definitions with no priority wrapper. Two different plain definitions stop with both locations,
and the YAML side cites `vendomat.yaml`. The fixture matrix on the fork
([S2](evidence/S2-merge-priority.md)) found these results:

- A library `mkDefault` yields to YAML.
- `lib.mkForce` in `devenv.nix` overrides YAML and libraries.
- A library `mkForce` overrides YAML without a message.
- Lists and attribute sets merge.

Vendomat will not claim that YAML always wins. A library author uses `mkDefault` for a value that
a user may override. `devenv.nix` stays the explicit way to use priority operators.

The generated `.vendomat/` directory is committed, so Testee and a fresh clone evaluate without a
prior Vendomat step (DOOR-028). `vendomat prepare` generates and validates without starting
devenv. `vendomat prepare --check` exits 67 when generated files are stale. CI and Testee use it.

Direct `devenv` use may read stale generated files. The generated module carries a guard
(DOOR-029). When the digest is stale, the guard stops every evaluation that reads config (shell,
test, build, eval, tasks, up, machines) and names `vendomat prepare`. `VENDOMAT_ALLOW_STALE=1`
bypasses it for Vendomat's own calls and for recovery. In a pinned shell, `vendomat` is the pinned
build and needs no launcher. The front door runs the devenv build that its Vendomat release pins,
which is the fork, and never the `devenv` on `PATH` (DOOR-032). Stock devenv entry is unsupported
and fails on inherited inputs. Vendomat writes no `follows` edge that the user did not write and
builds no transitive input graph (DOOR-036). The fork inherits imported inputs, and native
`follows` shares children.

## 5. Source, store, and cache

One installation keeps a collection of immutable release tags. Workspaces name tag-pinned sources;
`devenv.lock` records exact revisions. The pinned devenv fork inherits inputs from imported sources.
Vendomat generates direct inputs and imports, but does not resolve a second transitive input graph.
Third-party source can be mirrored or kept as a clone; the command form is open (DOOR-055). A user
changes a tag explicitly; normal shell entry does not select a newer release.

The collection builder builds each release tag. It writes one garbage-collection root per built tag
as a link under `/nix/var/nix/gcroots/vendomat/` (DOOR-047). NixOS keeps system generations through
its native roots. The building host collects other unrooted paths only under disk pressure. The
root survival fixture passed; the builder itself is unproved. Built outputs remain derived data;
source and tags are the record.

A single machine uses its local Nix store with no cache service. When machines share outputs, one
marked host serves its store through Harmonia as a signed, read-only binary cache. Only outputs in
that host's store are shared. A controller deploy substitutes from the cache and builds the rest
locally (DOOR-051). The serving host builds shared outputs. Harmonia serves every valid path in
that host's store, so the bind address and reachable networks are inventory settings (DOOR-048).
An absent path answers 404, and the client builds locally. The signing key lives outside the store,
owned by root with mode 0400, and never appears in a tracked file or log (DOOR-049). There is no
push credential, cache database, second cache copy, or Vendomat cache protocol.

Two corrections from the two-VM fixture ([S6](evidence/S6-harmonia-two-vm.md)):

- **A down cache blocks a build.** Under default Nix settings (`fallback = false`), a refused or
  silent cache makes the build fail. Earlier text said the opposite. Each client host sets
  `fallback = true` and a short `connect-timeout`, derived with the public key and substituter URL
  from the inventory mark (DOOR-046). A core with no mark sets none. The short timeout together with
  `fallback` is unproved.
- **Harmonia starts only after its key exists.** The stock module, enabled without a key, boots
  clean. The first request then fails the socket and the service and degrades the system. The core
  uses a path unit: the socket starts only when the signing key exists, and rotation restarts the
  service (DOOR-045).

## 6. Machines and secrets

Basix uses one inventory for fresh installation and adoption. Each host records its mode and stable
disk identities. A fresh install must refuse an unexpected target disk or a protected disk. An
adopted NixOS host never runs a disk installation tool, and its disk facts stay unchanged
(DOOR-044). devenv Machines builds, plans, activates, and rolls back through its native commands.
Basix supplies guards and the core NixOS role.

**Fresh install.** The target runs a NixOS environment that the controller reaches over SSH with a
temporary key. `vendomat machines install` runs the fork's native install (DOOR-043). A blank
target does not run Vendomat before its first boot. A source VM with a stand-in preflight
proved this route. The kexec route and a real installer ISO are unproved. The same system
workspace can later manage the running target or adopt another NixOS host.

**No private key.** The core role boots to zero failed units with no private key supplied by the
user. The host generates its own SSH host key. Every unit that needs a secret has a start condition
on that secret's file (DOOR-039). The core needs no SecretSpec provider and no signing key.

**Delivering a key later.** The controller sends the value over SSH standard input to a receiver in
the core. The receiver writes a temporary file in the target directory, renames it, and sets
owner root and mode 0400. A path unit then starts or restarts the dependent unit. The value never
appears in a command line, the store, or a log. This route works for fresh and adopted hosts
(DOOR-040). `install.secrets` is only an install-time convenience.

**Keys of the administrator and the installer.** The inventory holds an admin public key per host.
The installer's temporary key is separate and never becomes a permanent root key (DOOR-041).
After a keyless first boot or a disk loss, the host has a new SSH host key. The controller
re-pins that key before it delivers a secret or runs a Machines command. Project 16 gate G7 was
not a keyless proof: it carried `install.secrets`, `extraFiles`, `copyHostKeys`, and one failed unit
([S7](evidence/S7-keyless-secrets.md)).

**SecretSpec.** A host never needs SecretSpec (DOOR-042). SecretSpec may serve as the value source
on the controller. A host may opt in to it as a resolver. This replaces the project 19 rule that
SecretSpec is required at setup.

**Adoption.** An adopted host receives a core specialisation, a later secret, and a switch with no
disk write. The fixture proved this on a NixOS VM. Before the first adopted switch, the
owner should review a read-only comparison of the host's services and units (open decision O8 in [DECISIONS.md](DECISIONS.md)).

The fixtures for this section ran against a fixture core and a stand-in preflight. A real Basix core
and a real installer ISO have not run.

A data-only YAML file cannot express every NixOS hardware or service module. Basix must provide a
working default for each supported installation route. A user can add a native module for device
needs that the default cannot cover. Neither Vendomat nor Basix claims support for hardware that
NixOS itself cannot run.

## 7. Release and migration

The new format replaces `vendomat.toml`, `[settings]`, and the separate `vendomat sync` command.
The new cache route replaces Attic and `vendomat push` (DOOR-050). The release has no TOML
converter. The inventory found 2 live consumers and 22 V4 files to delete
([R3](evidence/R3-migration-inventory.md)). Each consumer migrates by hand. Each migration
writes a conversion record that lists every TOML table and its destination or its need for native
Nix (DOOR-052). A conversion activates no machine. The old requirement IDs remain in
[REQUIREMENTS.md](REQUIREMENTS.md) with their dispositions.

The transition must keep a working host release while the new launcher and workspace pin change.
One transition launcher release recognizes both markers: it hands a `vendomat.toml` workspace to
the pinned V5 build and runs a `vendomat.yaml` workspace (DOOR-053). The next release drops the
TOML marker. After cutover the repository has no TOML reader, no `sync`, and no Attic or `push`
path, and a repository-shape test enforces it (DOOR-054). The release keeps the Attic push and
live checks until the Harmonia live gate passes (open decision O5 in [DECISIONS.md](DECISIONS.md)).

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
V5 remains the running implementation until these gates support a release. The fixture results of
the 2026-10-11 session are interface proofs. They live in the gate matrix of
[the research report](evidence/RESEARCH-2026-10-11.md). None of them passes a gate in this list.

# Vendomat V5 specification and requirements

**Date:** 2026-10-07. **Status:** Normative for V5. **Concept:** [CONCEPT-V5.md](./CONCEPT-V5.md).
**Supersedes:** the earlier specification, requirements, and phase programme in closed history.

**2026-10-08 refinement:** [Named paths and drive identity](./REFINEMENT-2026-10-08.md) adds
`PATH-*` and `DISK-*` requirements. The in-place server conversion is replaced by a fresh install
on the 4 TB drive: see `BOOT-021` to `BOOT-024`.

**2026-10-08 project-output contract:** the owner decided that Vendomat is a system-installed command
and does not generate a consumer development shell. A generated flake bridges to a project-owned
outputs file. This adds `REG-011` to `REG-015`, `GEN-015` to `GEN-022`, `DEL-008` to `DEL-011`, and
`ISO-007`, and it supersedes or withdraws twelve earlier IDs. The evidence is
[PV-13](./prelim-verification/results/PV-13.md) (Nix interface) and
[PV-14](./prelim-verification/results/PV-14.md) (generator). PV-05 stays as dated history.

**2026-10-08 source collection decision:** one source collection on `server` holds the owner's
released tags. Nix fetches personal inputs from it over `git://`, and every input pins a tag. Attic
holds build outputs only. This adds `REG-016` to `REG-021` and `STORE-008` to `STORE-013`, and it
supersedes `REG-015`, `STORE-002`, and `STORE-004`. The evidence is
[PV-16](./prelim-verification/results/PV-16.md) (transport and idle cost) and
[PV-17](./prelim-verification/results/PV-17.md) (generator with the collection).

**Later on 2026-10-08:** a two-machine NixOS test ([PV-18](./prelim-verification/results/PV-18.md))
showed that Git alone does not keep branches out of the collection. `STORE-014` and `STORE-015` add
the hook and the per-repository export rule, and `STORE-014` supersedes `STORE-011`.

**Store step, fourth session of 2026-10-08:** `vendomat sync` now acts on `keep` and `mirror`, and
the collection host moves each collection repository to its newest tag. `vendomat path <name>` prints
a locked input's store path. This adds `STORE-016` to `STORE-022` and `CLI-016`. It supersedes
nothing: `STORE-009`, `STORE-013`, and `CLI-007` keep their claims, and the new IDs state the rules
that build them. The evidence is [PV-20](./prelim-verification/results/PV-20.md). A later change the same
day adds `STORE-023`, a push-time hook for the tree refresh ([PV-21](./prelim-verification/results/PV-21.md)).
The release task, `STORE-010`, and the explicit use of `backup` are not built.

**V4 removal, 2026-10-09:** the owner ruled that V4 stays nowhere. `DEL-012` adds the rule for this
repository, and [PV-26](./prelim-verification/results/PV-26.md) records the purge. V5 provides no
backward compatibility. The system is aligned to V5 instead.

**Earlier PV-12 update (superseded by the count below):** 153 requirement IDs were defined in the tables below; 126 were active.

**Current count:** 195 requirement IDs are defined in the tables below: 152 active, 32 superseded, 10
withdrawn, and 1 narrowed. The 19 withdrawn `RES-*` and `EMIT-*` IDs remain listed in section 2, so
214 IDs are preserved in all. Seventeen `NAT-*` entries are facts, not requirements. A preliminary
fixture result does not pass an implementation requirement.

## How to use this document

A requirement is satisfied when its **Verify** column runs and passes. Nothing else satisfies it.

- There are no phases and no gates. [CONCEPT-V5.md](./CONCEPT-V5.md) holds the build order.
- A document never satisfies a requirement. A passing command does.
- Every name here is proposed until a fixture exercises it. Record the fixture beside the
  requirement.
- **MUST** is normative. **SHOULD** states the default; a deviation needs a recorded reason.
- Preserve every ID. Never reuse or renumber one.

## Terms

| Term | Meaning |
| --- | --- |
| Input | A repository that exports modules, a core function, or both |
| Import | A consumer using an input |
| Core | An input that exports `lib`, a function a variant calls |
| Variant | A build produced by calling a core's `lib` with additions |
| Registry | `vendomat.toml`, the flat list of directly requested inputs |
| Resolution | The transitive input set with one exact revision per name |
| Collection | The one set of repositories on `server` at `/home/andrew/vendor/<repo>`: the owner's released tags, plus reference copies |
| Face | One of the three module targets: devenv, NixOS, Home Manager |

## Authority

Native declarations and locks select. devenv composes. Nix builds and substitutes. Attic stores and
signs. NixOS and Home Manager activate. Version control keeps history.

Vendomat writes the generated `flake.nix` from the registry, manages the collection's reference
copies, and reports. The owner writes the project outputs file. Nix resolves revisions and owns
`flake.lock`.

Vendomat owns no durable state. The cache belongs to Attic and holds build outputs only. The
collection holds release tags that CI pushed from the authoring repositories, which can push them
again. Reference copies and `keep` clones are caches. `.vend/` holds out-links. The build record
belongs to the builder.

---

# 1. Data formats

## 1.1 `vendomat.toml` — the registry

Hand-edited. One file per consumer.

```toml
[forge]
url = "git://server"

[inputs]
loci-nvim = { repo = "loci.nvim", ref = "refs/tags/v1.2.0", keep = true }
nvim-core = { ref = "refs/tags/v0.3.0" }
gitman    = { ref = "refs/tags/v0.10.0" }
telescope = { url = "git+https://<upstream-host>/telescope.nvim", ref = "refs/tags/v0.1.8", flake = false, mirror = true }

[passthrough]
nixpkgs = { url = "github:cachix/devenv-nixpkgs/rolling", backup = "https://<backup-host>/devenv-nixpkgs" }

[follows]
loci-nvim = ["nixpkgs"]
nvim-core = ["nixpkgs"]
gitman    = ["nixpkgs"]
```

`[forge]` names the one source collection, on `server`. An `[inputs]` entry without a `url` lives
there: its URL is `<forge url>/<repo>`, and `repo` defaults to the entry name. An entry with a `url`
is third-party code from upstream. Every `[inputs]` entry pins a tag (`REG-017`). The keys `url` and
`flake` become flake input attributes. `ref` and `rev` become URL query parameters, because Nix
2.34.7 rejects them as separate attributes beside `url` (`REG-013`, PV-13). Select a local checkout
with an explicit Nix input override.

`mirror`, `keep`, and `backup` never reach the generated flake. `mirror = true` keeps a reading copy
of a third-party repository in the collection and leaves the input URL alone. `sync --collection`,
run on `server`, makes the copy. `keep = true` keeps a persistent clone on each machine that runs
`sync`. Both clones show the tag the entry pins (`STORE-016` to `STORE-019`). `backup` records a second URL that the owner
applies by hand. nixpkgs and devenv are never mirrored or kept: they are huge.

`[passthrough]` holds infrastructure inputs such as `nixpkgs`. Each entry needs its own `url`, takes
no tag pin, and takes no `mirror` or `keep`. Vendomat adds no input of its own: a project that needs
`nixpkgs` lists it. `[follows]` lists, per direct flake input, the children that follow the root
`nixpkgs`. Vendomat cannot know whether an input declares `nixpkgs` without fetching it, so the owner
states the edge.

| ID | Requirement | Verify |
| --- | --- | --- |
| `REG-001` | The file MUST have one `[inputs]` table. Each key is an input name | Parse a valid file; parse a file with two `[inputs]` tables and get an error |
| `REG-002` | An input name MUST match `[a-z0-9][a-z0-9-]*` | `Nvim_Review` is rejected, naming the key |
| `REG-003` | *Superseded by `REG-010`.* An empty table used the clone at `~/vendor/<name>` at its default ref | — |
| `REG-004` | *Withdrawn 2026-10-08.* Version constraints are gone. Nix owns revision selection through `flake.lock` | — |
| `REG-005` | *Superseded by `REG-013`.* A table MAY carry `url`, `ref`, `rev`, or `flake`, each passed through as a separate flake input attribute | — |
| `REG-006` | An unknown key in an input table MUST be an error naming the key | `{ revision = "…" }` is rejected and names `revision` |
| `REG-007` | The file MUST list only directly requested inputs | After `sync`, the registry is byte-identical |
| `REG-008` | `[passthrough]` entries MUST be copied verbatim into the generated `inputs:` | `nixpkgs` appears in the output unchanged |
| `REG-009` | No command other than `add` and `remove` MUST write the registry | `sync`, `update`, `status` leave it byte-identical |
| `REG-010` | Each input MUST name a portable source URL; a local checkout MUST be selected by an explicit Nix input override | An empty input table fails; a remote URL is emitted; an override selects another source without rewriting the lock when lock writes are disabled |
| `REG-011` | `[follows]` MUST map a direct flake input name to a list of root input names. Today the only root name is `nixpkgs`. The generator emits one `follows` edge per listed pair and no other | PV-13 F7: one `nixpkgs` node for a child that declares `nixpkgs`, with no Nix warning. The unit test checks that an unlisted input gets no edge |
| `REG-012` | An input name MUST NOT appear in both `[inputs]` and `[passthrough]` | The registry is rejected and the message names the input and both tables |
| `REG-013` | `url` and `flake` MUST become flake input attributes. `ref` and `rev` MUST be appended to the URL as `ref=` and `rev=` query parameters. A `ref` or `rev` key beside the same query parameter in the URL MUST be an error | PV-13: Nix rejects `inputs.x.ref` beside `inputs.x.url` and locks both values from the query form. Unit tests cover the join with an existing query and the duplicate error |
| `REG-014` | A `[follows]` entry MUST be rejected when its key is not a direct input, names a `flake = false` input, names `nixpkgs` itself, lists a root other than `nixpkgs`, or when no `nixpkgs` input exists | PV-13: Nix ignores a follows edge on a non-flake input without any message, so only this check catches it. Each rejection names the entry |
| `REG-015` | *Superseded by `REG-021`.* A top-level table other than `[inputs]`, `[passthrough]`, and `[follows]` was an error. `[forge]` now exists | — |
| `REG-016` | An `[inputs]` entry with no `url` MUST resolve to `<forge url>/<repo>`, with `repo` defaulting to the entry name. An entry with no `url` and no `[forge]` table, a `[forge]` table with a query or an unknown key, an entry that sets both `repo` and `url`, and a `[passthrough]` entry with no `url` MUST each be an error | Unit tests. PV-17: `sync` writes `git://127.0.0.1:<port>/lib-a?ref=refs/tags/v1.0.0`, and Nix locks and evaluates it through a loopback `git daemon` |
| `REG-017` | Every `[inputs]` entry MUST pin a tag: `ref` is `refs/tags/<tag>`, or the URL query carries it. `rev` MAY be added as a second guard. A branch, a `rev` alone, or no pin MUST be an error. A `path:` URL and a `[passthrough]` entry are exempt | Unit tests name the entry. PV-16: Nix accepts a tag, a tag with a rev, and a rev alone over `git://`, so the rule is Vendomat policy; an unpinned URL did not resolve on the fixture repository |
| `REG-018` | `mirror = true` MUST be allowed only on an `[inputs]` entry that has its own `url`. It marks a reading copy in the collection and MUST NOT change the input URL. The registry MUST reject `mirror` on a `[passthrough]` entry, on a forge entry, and on `nixpkgs` or `devenv` | Unit tests: each rejection names the entry, and `flake.nix` is byte-identical with and without the flag. The copy is built: `sync --collection` makes it (`STORE-018`). Unit tests cover it. PV-20 ran no mirror on `server` |
| `REG-019` | `keep = true` MUST be allowed only on an `[inputs]` entry other than `nixpkgs` and `devenv`. It asks each machine that runs `sync` to hold a persistent clone | Unit tests for the shape and the rejections. The clone is built (`STORE-009`, `STORE-016` to `STORE-019`). Unit tests, and a Nix test over `git://`. PV-20 ran no `keep` on `server` |
| `REG-020` | `backup` MUST be an optional URL on any entry. It MUST NOT appear in the generated flake. Vendomat MUST use it only when the owner asks | Unit tests: the generated flake and its digest are identical with and without `backup`. **The explicit use is not yet built** |
| `REG-021` | A top-level table other than `[forge]`, `[inputs]`, `[passthrough]`, and `[follows]` MUST be an error naming it. `[inputs]` MUST be present | A `[follow]` typo is rejected instead of dropped |

## 1.2 Generated `flake.nix`

Written by `vendomat sync`. Never hand-edited. `flake.lock` is **not** generated: Nix owns it. The
project writes `flake-outputs.nix`; Vendomat never writes or reads it. Both files must be tracked in
Git before Nix evaluates a Git-backed flake: Nix cannot see an untracked file (PV-13 F5).

This is the real output of the generator for the registry in section 1.1:

```nix
# GENERATED by vendomat 0.5.0. Do not edit.
# registry-digest: sha256-c1ad43517b757db583cad1e0a67204a62eb3da652d4d8d375aed8668e36c7850
{
  inputs = {
    gitman.url = "git://server/gitman?ref=refs/tags/v0.10.0";
    gitman.inputs.nixpkgs.follows = "nixpkgs";
    loci-nvim.url = "git://server/loci.nvim?ref=refs/tags/v1.2.0";
    loci-nvim.inputs.nixpkgs.follows = "nixpkgs";
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    nvim-core.url = "git://server/nvim-core?ref=refs/tags/v0.3.0";
    nvim-core.inputs.nixpkgs.follows = "nixpkgs";
    telescope.url = "git+https://<upstream-host>/telescope.nvim?ref=refs/tags/v0.1.8";
    telescope.flake = false;
  };

  outputs = inputs: import ./flake-outputs.nix inputs;
}
```

The project file receives every declared input and `self`, and returns native flake outputs:

```nix
# flake-outputs.nix — written by the project
inputs@{ self, nixpkgs, nvim-core, ... }:
{
  packages.x86_64-linux.default = nvim-core.packages.x86_64-linux.default;
  # A module is used only when this file names it:
  # lib.shell = nixpkgs.lib.evalModules { modules = [ nvim-core.devenvModules.default ]; };
}
```

Input order is by name, so the file does not depend on the order in `vendomat.toml`. The digest hashes
what the generator writes (names, URLs, `flake`, and `follows`), so a change to a comment, to spacing,
or to `mirror`, `keep`, or `backup` leaves the file identical.

| ID | Requirement | Verify |
| --- | --- | --- |
| `GEN-001` | *Superseded by `GEN-015`.* `inputs` carried one entry per registry entry, plus `nixpkgs` and `devenv` | — |
| `GEN-002` | *Superseded by `GEN-013`, then by `GEN-021`.* Direct follows declarations alone do not guarantee one transitive `nixpkgs` node | — |
| `GEN-003` | *Superseded by `GEN-020`.* The generated file named only direct registry entries | — |
| `GEN-004` | *Superseded by `GEN-016`.* The `outputs` block was inline and had to omit Vendomat, checked with `rg -c vendomat flake.nix`. The required header contains that word, so the check could not pass | — |
| `GEN-009` | *Superseded by `GEN-014`, then by `GEN-019`.* The proposed pure shell command fails with pinned devenv when `devenv.root` is unset. PV-05 keeps this as dated history | — |
| `GEN-010` | *Superseded by `GEN-017`.* The inline `outputs` block imported `devenvModules.default` from every input that exposed one | — |
| `GEN-011` | *Superseded by `GEN-017`.* An input without `devenvModules.default` was skipped | — |
| `GEN-012` | *Withdrawn 2026-10-08.* It required an auto-imported module to activate nothing. The generator no longer imports a module. `INP-006` and `MOD-003` keep the rule at the module boundary | — |
| `GEN-005` | The file MUST open with a generated header naming the tool version and the registry digest | The first two lines match |
| `GEN-006` | Output MUST be byte-identical for an unchanged registry | Run `sync` twice; `cmp` reports no difference. The second run does not rewrite the file |
| `GEN-007` | `sync` MUST refuse to overwrite a `flake.nix` that has no generated header, and name the file | A hand-written flake is left untouched; the command exits non-zero |
| `GEN-008` | Vendomat MUST never read or write `flake.lock` | `flake.lock` is byte-identical after every Vendomat command, including when it is unreadable. `nix flake update <input>` works unchanged |
| `GEN-013` | *Superseded by `GEN-021`.* The generator wrote a follows edge for each authored input that declares `nixpkgs`. It cannot know that without fetching the input | — |
| `GEN-014` | *Superseded by `GEN-019`.* A consumer shell had to evaluate, build, and enter with Vendomat absent, using `--impure`. Vendomat no longer generates a shell | — |
| `GEN-015` | `inputs` MUST carry exactly one entry per distinct name in `[inputs]` and `[passthrough]`. The generator MUST add no input of its own: no `devenv`, no `nixpkgs`, and no Vendomat input | PV-14: Nix reads `inputs` from the generated file with `nix eval --file`; the names equal the registry names |
| `GEN-016` | `outputs` MUST be the fixed bridge `outputs = inputs: import ./flake-outputs.nix inputs;`. It MUST reference no Vendomat input, output, or library | PV-13 F1 and PV-14: the generated file equals the candidate that passed on Nix. The check reads input names, never the header text |
| `GEN-017` | The generator MUST NOT scan, filter, or import any module face of any input. A module is used only when the project file names it | The generated body has no `devenvModules`, `nixosModules`, `homeManagerModules`, or `filterAttrs`. PV-13 F3 and F4: an unselected face has no effect; a selected face is inactive until enabled |
| `GEN-018` | `sync` MUST fail, naming `flake-outputs.nix`, before any write when that file is missing. `sync` MUST NOT open, read, or write it | `sync` with the file missing writes nothing. With the file unreadable (mode 0), `sync` succeeds and the file is unchanged |
| `GEN-019` | A project output selected through the generated flake MUST evaluate and build with no Vendomat input and no Vendomat command on `PATH`. The gate needs no `--impure` and no generated shell | PV-14: with a `PATH` holding only `nix` and `git`, and `--option substituters ""`, the package builds and `nix flake show` lists no `devShells` |
| `GEN-020` | The generated file MUST NOT name any transitive input. A `follows` edge names a direct input as its child | PV-14: a source flake that declares its own `nixpkgs` adds no input to the generated file, and the lock still holds that node |
| `GEN-021` | The generator MUST write `<child>.inputs.nixpkgs.follows = "nixpkgs";` for each `[follows]` pair and no other edge. One shared `nixpkgs` node needs every authored flake in the chain to follow its parent; this holds for a controlled graph only | PV-13 F7: 4, 3, 1, and 2 nodes for the four chain shapes; PV-14: the generated edge gives one node and no warning. A child with no `nixpkgs` draws a Nix warning, which is the owner's cue to remove the entry |
| `GEN-022` | The generator MUST NOT emit `devShells`, `devenv.lib.mkShell`, or a `devenv` input. A project MAY define its own shell in its outputs file; it owns that shell and its `devenv.root` setting | PV-13 F2: `nix flake show` lists only the outputs the project file defines |

**Rationale for `GEN-021`.** `follows` is flake metadata, read before evaluation, so a Nix function cannot add it after locking. A direct edge controls only that input. Every authored transitive flake must follow its parent before one node is assured. PV-04 and PV-13 prove this rule for controlled three-level fixtures, not for arbitrary inputs. The registry states each edge because the generator does not fetch inputs. Nix warns about an edge on a child with no `nixpkgs`, is silent about an edge on a non-flake input, and fails on a missing target. `REG-014` covers the silent case.

**Rationale for `GEN-016` to `GEN-019`.** Flake evaluation is hermetic: a flake's `outputs` can reach only what its own `inputs` declare, so a system-installed command cannot supply a Nix library to a project. The owner decided that Vendomat is installed on the host (`DEL-006`, `DEL-007`) and generates no shell. The bridge hands the resolved inputs to a file the project owns. The project decides what to build and which modules to use. PV-05 tested an earlier generated devenv shell; its `--impure` finding applies to that shell only and stays as dated history. The superseding decision is in `prelim-verification/DECISIONS.md`.

**Rationale for `GEN-020` and `GEN-008`.** Everything below the direct inputs belongs to Nix: the
transitive walk, deduplication, cycle detection, and exact revisions, all recorded in `flake.lock`.
Vendomat selects nothing.

## 1.3 `<host>.toml` — system configuration

```toml
[options]
"services.tailscale.enable"  = true
"nix.settings.max-jobs"      = 8
"environment.systemPackages" = ["ripgrep", "fd"]
```

| ID | Requirement | Verify |
| --- | --- | --- |
| `SYS-001` | The file MUST have one `[options]` table. Each key is a dotted NixOS or Home Manager option path | A key that is not a real option path fails evaluation, naming the path |
| `SYS-002` | *Superseded by `SYS-008`.* A bare `lib.mkMerge` value is not a module item | — |
| `SYS-003` | *Superseded by `SYS-009`.* Resolving every string list as packages corrupts ordinary string-list options | — |
| `SYS-004` | An unresolvable package name MUST be an error naming the key and the name | `["ripgrepp"]` fails and names both |
| `SYS-005` | *Superseded by `SYS-010`.* Duplicate definitions follow each option type's native merge rules | — |
| `SYS-006` | The TOML MUST NOT express a function, a conditional, an interpolation, or a reference to another option | Those stay in a `.nix` file; the converter has no mechanism for them |
| `SYS-007` | A scalar, a string, a boolean, an integer, and a list of scalars MUST round-trip | Each type evaluates to the same value it was written as |
| `SYS-008` | `fromToml` MUST return a valid NixOS module and convert dotted keys to nested options | Import `{ config = fromToml file; }` with the PV-06 fixture; all supported values evaluate |
| `SYS-009` | Package-name conversion MUST apply only to explicit package-valued option paths; ordinary string lists MUST remain strings | Resolve `environment.systemPackages` names and preserve `users.users.*.extraGroups` in the PV-06 fixture |
| `SYS-010` | TOML and Nix definitions MUST use native option-type merge behavior; no blanket duplicate rejection is added | Equal scalar definitions merge, unequal scalar definitions fail, and list definitions merge as the option type specifies |

## 1.4 The input contract

| ID | Requirement | Verify |
| --- | --- | --- |
| `INP-001` | *Superseded by `INP-008`.* Flake-backed inputs declare dependencies in their own `flake.nix`; `devenv.yaml` is not the dependency contract | — |
| `INP-002` | *Superseded by `INP-007`.* An input need not export module faces it does not implement | — |
| `INP-003` | An input that exports a buildable output MUST export `packages.<system>.<name>` | `nix build .#<name> --json` returns `drvPath` and an output path |
| `INP-004` | A core input MUST export `lib`, a function | `nix eval .#lib --apply builtins.isFunction` returns true |
| `INP-005` | An input MUST declare its released versions as git tags of the form `v<semver>` | `git tag --list` shows them |
| `INP-006` | Importing any face MUST activate nothing until `enable` is true | Import with no options; no package is installed and no service runs |
| `INP-007` | An input MAY export only the supported subset of devenv, NixOS, and Home Manager module faces | PV-07's census and fixture show face-specific outputs; evaluate each exported face alone |
| `INP-008` | A flake-backed input MUST declare dependencies in its own flake inputs; Vendomat MUST NOT require `devenv.yaml` for dependency resolution | Inspect the A → B → C lock graph; transitive inputs appear through native flake declarations |

---

## 1.4 Named paths and drive identity

See [the 2026-10-08 refinement](./REFINEMENT-2026-10-08.md) for the proposed configuration
surface and the observed server inventory. The names below are proposed until tested.

| ID | Requirement | Verify |
| --- | --- | --- |
| `PATH-001` | A host MUST declare one absolute path for each logical path name | Two inputs request `notes`; both receive the host's declared path |
| `PATH-002` | An input MUST be able to use a named path during Nix evaluation and at runtime | Evaluate its Nix option and inspect its shell or service environment |
| `PATH-003` | A mutable path declaration MUST remain a string and MUST NOT copy directory contents into the Nix store | Change a file under the path; the build input set stays unchanged |
| `PATH-004` | A missing path name MUST fail evaluation and name the input that requested it | Evaluate an input that requests an undeclared name |
| `DISK-001` | A host MUST record each physical drive by a stable hardware identifier | Resolve each inventory entry through `/dev/disk/by-id/` and compare its model and serial |
| `DISK-002` | A partition or format operation MUST reject a target that backs the running root or boot filesystem | Run a read-only preflight against the current root drive; no write command runs |
| `DISK-003` | A partition or format operation MUST reject a missing identifier, unexpected model, serial, size, mount, or signature | Inject each mismatch; no write occurs |
| `DISK-004` | Local block-device mounts MUST use filesystem UUIDs or partition UUIDs | Inspect the evaluated `fileSystems` values for kernel-assigned device names |
| `DISK-005` | After formatting, Vendomat MUST record the actual UUIDs and check that they resolve to the declared drive | Reformat a test image; the old UUID fails until the inventory changes |
| `DISK-006` | The new server installation MUST have its own EFI System Partition and leave the 512 GB drive intact | Inspect both drives after installation; boot both systems separately |
| `DISK-007` | A service with data on a separate mount MUST require that mount before it starts | Unmount a test data disk; the service does not write into the underlying directory |

# 2. Resolution — withdrawn

**Withdrawn 2026-10-08.** `RES-001` to `RES-012` and `EMIT-001` to `EMIT-007` defined a Vendomat
resolver: version ranges to tags to revisions, a transitive walk, deduplication, cycle detection,
and a generated `devenv.yaml` lock.

None of it is built. Consumers are flake-backed, so Nix performs every one of those jobs and owns
`flake.lock`. The generator writes direct inputs only — see `GEN-005` to `GEN-008` and `GEN-015` to `GEN-022`.

Two consequences, both recorded so they are not rediscovered:

- Vendomat never selects a revision. The earlier draft accepted that it would, and treated the
  generated file as the control. That trade is no longer needed.
- A module reaches a transitive dependency through its **own** flake's lock, not through a name the
  consumer was obliged to supply. The `devenv.yaml` route could not offer that, and it was the
  reason the resolver existed.

# 3. Source collection

The owner's released source lives in one collection on `server`. Nix reads it at evaluation, and the
owner and agents read it for context. Attic never holds it. [CONCEPT-V5.md](./CONCEPT-V5.md) explains
the two phases.

| ID | Requirement | Verify |
| --- | --- | --- |
| `STORE-001` | Clones MUST live at `~/vendor/<name>`, overridable by `VENDOMAT_SOURCE_ROOT` | Both locations work |
| `STORE-002` | *Superseded by `STORE-009`.* `sync` cloned a missing input and fetched an existing one | — |
| `STORE-003` | `sync` MUST NOT change a working tree that has uncommitted changes. It MUST report instead | Dirty the tree; `sync` reports and exits non-zero for that input only |
| `STORE-004` | *Superseded by `STORE-010`.* The whole store was a cache of git remotes | — |
| `STORE-005` | A `rev` or path pin to a sibling checkout MUST be used in place and never copied | The resolved url names the sibling path |
| `STORE-006` | Generated inputs MUST use a portable remote URL by default; absolute `git+file` paths MUST NOT be the fleet default | Generate a consumer with remote source declarations and evaluate it after moving the consumer checkout |
| `STORE-007` | A local source checkout MUST be selected by an explicit input override; `VENDOMAT_SOURCE_ROOT` alone MUST NOT alter an existing flake or lock | Apply an input override and compare lock hashes; setting only the environment variable leaves both unchanged |
| `STORE-008` | The collection MUST be one set of repositories on the collection host (`server`), at `/home/andrew/vendor/<repo>`, served read-only to the tailnet over `git://`. The serving process MUST sleep when idle | PV-16: a loopback `git daemon` serves a tagged repository to Nix 2.34.7, and idle it used 0 CPU ticks in 20 seconds. The owner reports that `git ls-remote git://server/devman` works from `framework` ([PV-19](./prelim-verification/results/PV-19.md)); a Nix lock and build there are **not yet tested** |
| `STORE-009` | `sync` MUST clone a missing `keep` or `mirror` entry and fetch an existing one. It MUST NOT clone any other entry | Built. Unit tests list the clones after `sync`; an entry with neither flag leaves the source root absent. The rules are in `STORE-016` to `STORE-021`. `mirror` acts only under `--collection` (`STORE-018`) |
| `STORE-010` | The collection MUST be rebuildable from the authoring repositories by pushing their release tags again. A `mirror` copy and a `keep` clone MUST be caches: deleting one and re-running `sync` restores it | **Not yet built.** Delete a collection repository, push its tags again, and compare the tag lists |
| `STORE-011` | *Superseded by `STORE-014`.* Only release tags entered the collection, but nothing enforced it: Git refuses only a push to the checked-out branch | — |
| `STORE-012` | No Vendomat step MAY require a source path to be present in Attic. Evaluation takes source from the collection or from upstream | PV-17: a consumer locks and evaluates with only the collection configured and no Attic |
| `STORE-014` | Only new release tags MUST enter the collection. A `pre-receive` hook in each repository MUST refuse any ref outside `refs/tags/` and MUST refuse to update or delete an existing tag. CI pushes tags over SSH | PV-18, two NixOS machines: a tag push is accepted; a branch push and a moved tag are refused with a message; the repository ends with its tags and no branch. A real push from `framework` is **not yet tested** |
| `STORE-015` | The daemon MUST serve a repository only when it carries `.git/git-daemon-export-ok`. It MUST NOT accept a push over `git://`. Port 9418 MUST be open on the tailnet interface only | PV-18: an unmarked repository is not served and a marked one is; a push over `git://` fails; the firewall opens the port on the inner interface only. In nix-meta the evaluated `tailscale0` ports are `[22,8077,9418]`. **Not switched on `server`** |
| `STORE-013` | A collection repository's working tree MUST show its newest release tag by version order, so the owner and agents can read it. A hook or `sync` refreshes it and MUST NOT touch a tree with uncommitted changes (`STORE-003`) | Built for `sync --collection` (`STORE-022`) and as a push-time hook (`STORE-023`, installed on `devman`). Unit tests: a newer tag moves the files on disk. PV-20: `devman` on `server` went from no files to `v0.7.0` |
| `STORE-016` | `sync` MUST write `flake.nix` before any store work. A store problem MUST NOT stop or undo that write, and the other entries MUST continue. The exit status MUST be 0 when every entry is fine, 1 when an entry is refused (a dirty tree, a directory that is not a Git repository), and 2 when Git fails (an unreachable remote, a timeout, a missing tag) | Unit tests: one bad entry among three; the command writes `flake.nix`, exits 2 for a failed clone, and exits 1 for a dirty clone while it updates the next entry |
| `STORE-017` | The clone directory MUST be `$VENDOMAT_SOURCE_ROOT` (default `~/vendor`) plus the repository name: the `repo` key, else the input name. A `keep` forge entry MUST clone `<forge url>/<repo>`. A `keep` or `mirror` third-party entry MUST clone its own `url` without the query. A directory that is a Git repository with an `origin` MUST get a tag fetch. A Git repository with no `origin` is the collection's own repository: `sync` MUST skip it and say so. A directory that is not a Git repository MUST be refused and left untouched. A `path:` input and any URL scheme other than git, http, https, ssh, and file MUST NOT be cloned | Unit tests for each case. A `git://` clone of a repository that holds a tag and no branch works. PV-20 |
| `STORE-018` | `mirror` MUST act only with `sync --collection`. Without it, `sync` MUST print "mirror skipped: not the collection host" and copy nothing. A mirror MUST NOT receive the export marker or the `pre-receive` hook | Unit tests: the skipped message and no source root; with the flag, the clone holds neither file |
| `STORE-019` | The working tree of a `keep` or `mirror` clone MUST show the tag its entry pins, as a detached checkout, when the tree is clean. Known limit: two projects that pin different tags share one clone, and the last `sync` wins. `vendomat path` stays exact, because Nix selects the source by the lock | Unit tests: a first clone, a fetch of a newer tag, a branch checkout that becomes detached, and a no-op rerun. The Nix test checks the clone over `git://` |
| `STORE-020` | `sync` MUST run `git` as a subprocess with explicit arguments, `GIT_TERMINAL_PROMPT=0`, and a timeout. No message MAY carry a credential from a URL | Unit tests: the environment value, a reported timeout, and a URL with a password that does not appear in the message |
| `STORE-021` | `sync --dry-run` MUST print the planned actions and change nothing: no `flake.nix`, no clone, no fetch, no checkout. It MUST report a dirty tree or a non-Git directory that a real run would refuse | Unit tests and a command test. PV-20: the dry run on `server` left every file as it was |
| `STORE-022` | With `sync --collection`, `sync` MUST check out the newest tag by version order (`git for-each-ref --sort=-v:refname refs/tags`) as a detached checkout in each directory of the source root that has `.git/hooks/pre-receive` or `.git/git-daemon-export-ok`, when its tree is clean. It MUST work when the branch is unborn. It MUST leave every other directory and every tag alone | Unit tests: an unborn branch that holds a tag, `v0.10.0` ahead of `v0.9.0`, a dirty tree, a repository with neither file. PV-20: `devman` on `server`; `pydantic` and `silverbullet` unchanged |
| `STORE-023` | A `post-receive` hook in a collection repository MAY refresh the working tree after a tag push. It MUST follow `STORE-022`: newest tag by version order, detached checkout, clean tree only, unborn branch allowed, tags unchanged. It MUST NOT fail or delay the push on any problem, MUST ignore a bare repository, and MUST need only Git. The source is `hooks/collection-post-receive`; the `nix-meta` script `collection-add` installs it | `tests/test_collection_hook.py` pushes tags into a real non-bare repository over `file://` with the `pre-receive` rule beside it: a first push fills an unborn repository; a newer tag moves the tree; an older tag does not; a dirty tree and a held `index.lock` leave the push successful; a branch push is still refused; `sync --collection` then reports `unchanged`. PV-22: installed on the live `devman` by `collection-add --hooks`; a copy of `devman` with that hook took a new tag, refused a branch and a moved tag, and the live refs stayed as they were. `collection-add` on `nix-meta` `main` (`1629188`, landed and pushed) installs it for new repositories. No repository other than `devman` has it yet |

---

# 4. Cache and substitution

| ID | Requirement | Verify |
| --- | --- | --- |
| `CACHE-001` | The consumer module MUST add the cache as a substituter and its public key as trusted | `nix show-config` on a consumer lists both |
| `CACHE-002` | The push credential MUST NOT appear in a tracked file, a store path, or a log | Grep every tracked file, the closure, and the logs; none found |
| `CACHE-003` | A pull-only credential MUST be refused on push | The attempt reports a permission error |
| `CACHE-004` | *Superseded by `CACHE-009`.* Attic 0.1.0 skips upstream-sourced paths during push | — |
| `CACHE-005` | A path never pushed MUST report absent, never a false success | `nix path-info --store <cache>` returns null for it |
| `CACHE-006` | `attic watch-store` MUST run on every machine that builds | The unit is active on each builder |
| `CACHE-007` | A cold consumer MUST obtain a cached output with no local build | At step 10, on the newly installed laptop with `--max-jobs 0`, every path substitutes across Tailscale. This is collected, not gated: see `BOOT-019` |
| `CACHE-008` | The NAR hash of a cache-served output MUST equal the hash recorded at build | Compare both; they are equal |
| `CACHE-009` | The builder MUST report an upstream skip, and consumers MUST keep the source cache as a substituter when a path is absent from the private cache | PV-10 records `in upstream` and private-cache absence; a cold consumer confirms fallback through the upstream substituter |

---

# 5. Builder

| ID | Requirement | Verify |
| --- | --- | --- |
| `BUILD-001` | The builder MUST build each registry input separately | Each input has its own derivation and its own closure in the cache |
| `BUILD-002` | A new tag on an input MUST trigger that input's build | Tag an input; the next run builds it and no unrelated input |
| `BUILD-003` | The builder MUST record the command, the exit status, and the output paths for each build | The log carries all three per input |
| `BUILD-004` | A failed build MUST NOT stop the other inputs | Break one input; the others still build and the report names the failure |
| `BUILD-005` | The builder MUST NOT push explicitly | No push command appears; `watch-store` moves the paths |
| `BUILD-006` | The build log and its exit status MUST be the only durable record of a build | No receipt file is written anywhere |
| `BUILD-007` | Every target MUST be `x86_64-linux` while that remains true of the fleet | `server` and the laptop both report `x86_64-linux`; a third system is a recorded change |
| `BUILD-008` | A build on either machine MUST become substitutable by the other | Build on the laptop; `server` substitutes it with no local build, and the reverse |

---

# 6. `mkModules`

| ID | Requirement | Verify |
| --- | --- | --- |
| `MOD-001` | `mkModules` MUST take `{ name, options ? {}, packages, extra ? {} }` and return `{ devenv, nixos, homeManager }` | Call it; all three attributes evaluate as modules |
| `MOD-002` | Options MUST land at `<name>.*` for devenv and `programs.<name>.*` for NixOS and Home Manager | Evaluate each face and read the option path |
| `MOD-003` | Every face MUST declare `enable`, defaulting to false | `enable` exists and is false with no configuration |
| `MOD-004` | `packages` MUST be `cfg: pkgs: [ derivation ]` | A non-function value is rejected |
| `MOD-005` | The three faces MUST install to `packages`, `environment.systemPackages`, and `home.packages` | Each face writes only its own path |
| `MOD-006` | `extra` MUST be `cfg: pkgs: { <face> = <module content>; }` | A `nixos` key reaches only the NixOS face |
| `MOD-007` | *Superseded by `MOD-010`.* Recursive attribute update replaces package lists | — |
| `MOD-008` | An `extra` key for a face MUST NOT appear in the other faces | A devenv `tasks` entry is absent from the NixOS and Home Manager faces |
| `MOD-009` | A hand-written face MUST remain possible beside a generated one | An input may export a hand-written module for one face and generated modules for the others |
| `MOD-010` | Generated install paths and `extra` definitions MUST use native module merging so list additions are preserved | The PV-07 fixture retains both `hello` and `ripgrep` in each enabled face |

| `PROJ-001` to `PROJ-006` | *Withdrawn 2026-10-08.* `mkProject` was a Vendomat library function, which made every consumer depend on Vendomat as a flake input. The generated flake now bridges to a project-owned file: see `GEN-016`, `GEN-017`, and `GEN-019`. Cross-references repaired 2026-10-08 | — |

---

# 7. Cores and variants

| ID | Requirement | Verify |
| --- | --- | --- |
| `CORE-001` | A core MUST export `lib`, a function taking a variant's additions and returning a build | `nix eval .#lib --apply builtins.isFunction` is true |
| `CORE-002` | A core MUST hold only what every consumer of it needs | Remove any core element; at least one variant breaks |
| `CORE-003` | A variant MUST be produced by calling the core's `lib` | The variant's derivation references the core's inputs |
| `CORE-004` | Variants of one core MUST share every common store path | `nix-store -qR` on two variants; the shared set covers the core closure |
| `CORE-005` | A variant's own store content MUST be limited to its wrapper, its configuration, and its own additions | Measure the closure difference between the core and the variant; record the bytes |
| `CORE-006` | A core change rebuilds every variant | Change the core; every variant's output path changes. This is accepted, not avoided |
| `CORE-007` | *Superseded by `CORE-008`.* A core dependency belongs in a flake input, not `devenv.yaml` | — |
| `CORE-008` | A variant MUST name its core in its own flake inputs; Nix owns the transitive lock edges | Two variants name the same core input; inspect the resulting flake lock |

---

# 8. Isolation

| ID | Requirement | Verify |
| --- | --- | --- |
| `ISO-001` | A variant's binary MUST have a name distinct from the base tool | `nvim` is not shadowed |
| `ISO-002` | A caller MUST reach a variant by absolute store path, never a `PATH` lookup | Put a conflicting binary first on `PATH`; the variant still runs. The Neovim wrappers default to `--suffix PATH`, so a `PATH` entry would otherwise win |
| `ISO-003` | An editor variant MUST set `wrapRc = true` | The variant ignores the owner's configuration directory |
| `ISO-004` | An editor variant that must not share state MUST set `NVIM_APPNAME` | Its shada, swap, and undo files live under their own directory |
| `ISO-005` | Enabling a variant MUST change no setting of the daily tool | Run both; each keeps its own configuration and state |
| `ISO-006` | *Superseded by `ISO-007`.* Ordinary project entry and accepted output execution needed no Vendomat process and no cache. The check assumed a generated shell | — |
| `ISO-007` | Executing an accepted project output MUST need no Vendomat process and no private cache. A project shell, if any, owns its own entry command | Deny the Vendomat command and every substituter; a locally buildable output still evaluates and builds (PV-14) |

---

# 8a. How Vendomat is delivered

| ID | Requirement | Verify |
| --- | --- | --- |
| `DEL-001` | *Superseded by `DEL-006`.* The CLI is not part of the shared boot core | — |
| `DEL-002` | *Superseded by `DEL-008`.* No consumer declared Vendomat as a flake input. The check, `rg -c vendomat`, matched the required header | — |
| `DEL-003` | A repository that **authors** modules MAY declare Vendomat as a flake input, for `mkModules` | Its flake names the input; a consumer of it does not inherit that dependency |
| `DEL-004` | `fromToml` and `fromInventory` MUST be reached through `nix-meta`'s own Vendomat input, declared once | No machine file imports them by absolute path |
| `DEL-005` | *Superseded by `DEL-009`.* It pointed to `GEN-014` and `ISO-006`, which assumed a generated shell | — |
| `DEL-006` | The shared machine core MUST boot without the Vendomat CLI; a host MAY add the CLI in a later host delta | PV-11 core VM boots with no `vendomat` command; separate host-delta configuration evaluates the CLI package |
| `DEL-007` | The CLI package MUST be selected as `packages.<system>.vendomat`; `.default` MUST NOT be used as the CLI package | PV-11 resolves `.default` to `vendomat-wheelhouse` and `.vendomat` to `vendomat-0.4.6` |
| `DEL-008` | No consumer MUST declare Vendomat as a flake input | Read the `inputs` of every generated `flake.nix` with Nix and the root inputs of its `flake.lock`; neither holds `vendomat`. Do not search the header text |
| `DEL-009` | Executing an accepted project output MUST need no Vendomat process, package, or input | See `GEN-019` and `ISO-007` |
| `DEL-010` | A host that installs the CLI MUST make `vendomat` reachable from an existing project shell, and the project MUST NOT add Vendomat to its flake or devenv files to get it | PV-25, on `server` with the system `vendomat` 0.5.0: a bare devenv project shell and a shell that imports the central consumer module both resolve `vendomat` to the system command and to no other, with `path` and the new `sync` flags. `devenv shell --clean` drops the system `PATH`, so it finds none. **Not run in an existing repository's shell, and not on `framework`.** The V4 consumer module prints an `install-hook` error on a V5 `vendomat.toml` (`DEL-011` open) |
| `DEL-011` | The CLI MUST NOT be installed through devenv or the shared boot core. A host delta installs it | Inspect the V5 host and project configurations: no devenv module provides the CLI. `vendomat` 0.6.0 on `main` has no devenv module (PV-26). **Open:** `nix-meta` still pins `vendomat` `d5a90f0`, and the installed command (0.5.0) still comes with the V4 consumer module, which eleven overlays import |
| `DEL-012` | The `vendomat` repository MUST hold V5 only: its library holds only V5 modules, it has no V4 directory (`vendor/`, `modules/`, `lib/`, `docs/`, `examples/`), its flake has `nixpkgs` as its only input and `packages.<system>.vendomat` as its only output, and its package needs only `typer`. The command surface is the built subset of `CLI-001` | `tests/test_repo_shape.py` and `tests/test_cli.py` fail when any of these returns. PV-26: `vendomat` 0.6.0 builds, `--help` lists `sync` and `path` only, and `nix flake show` lists `packages` only |

**Rationale.** Three delivery paths because there are three different consumers: a person running a
command, a flake evaluating a function, and a generated file that must depend on nothing.

---

# 9. Command line

| ID | Requirement | Verify |
| --- | --- | --- |
| `CLI-001` | The surface MUST be `add`, `remove`, `sync`, `status`, `query`, `path`, `explore`, `set`, `get`, `unset`, `diff`, `apply`, `rollback` | `--help` lists exactly these |
| `CLI-002` | Every command MUST exit non-zero on failure and name the cause | Each failure path prints a cause and a non-zero status |
| `CLI-003` | Every read command MUST support `--json` | Output parses as JSON |
| `CLI-004` | A read command MUST NOT change a lock, a registry, or a selection | Files are byte-identical after every read command |
| `CLI-005` | `status` MUST report, per input: the registry entry, the revision in `flake.lock`, the store revision, and cache presence | All four fields appear for each input |
| `CLI-006` | *Withdrawn 2026-10-08.* `nix flake update <input>` performs this. Vendomat adds no wrapper | — |
| `CLI-007` | `path <name>` MUST print the store path of that input | The path exists. Built; see `CLI-016` |
| `CLI-008` | `explore <name>` MUST run the dedicated editor with that repo's root as the working directory | The editor opens there |
| `CLI-009` | `set <path> <value>` MUST write only the host TOML | No other file changes |
| `CLI-010` | `diff` MUST evaluate the host configuration before and after and report the option delta | A single changed option produces a one-entry delta |
| `CLI-011` | `apply` MUST drive `nixos-rebuild switch` and report its exit status | A failing rebuild exits non-zero and names the stage |
| `CLI-012` | `apply` MUST refuse when a host file has uncommitted changes, unless forced | Dirty the file; the command refuses and names it |
| `CLI-013` | `rollback` MUST select the prior system generation | The active generation changes to the previous one |
| `CLI-014` | `status` MUST report an input whose store revision is ahead of its locked revision as drifted | The drift is named. Nothing is updated automatically; the owner runs `nix flake update <input>` |
| `CLI-015` | `diff` MUST compare the last committed host TOML with the current host TOML; `apply` runs only after the host file is committed unless explicitly forced | In the PV-08 fixture, `set → diff → Gitman commit → apply` restores a clean tracked state; inspect the three changed evaluated values |
| `CLI-016` | `path <name>` MUST take the path from Nix: `nix flake archive --json --no-write-lock-file`, field `inputs.<name>.path`. It MUST NOT read `flake.lock`. It MUST accept `--json`. It MUST NOT change `flake.lock`, `vendomat.toml`, or `flake.nix`. An unknown name MUST be an error (exit 1) that names the input and lists the direct inputs. An input that Nix keeps inside the project source, such as a `path:` input, MUST be an error (exit 1) that says so | Nix tests on pinned Nix over `git://`: the path equals the `outPath` that Nix evaluates; the lock is byte-identical, or absent when it was absent; the unknown-input and `path:` cases. PV-20: `nix flake archive --dry-run` prints the same paths, so `--dry-run` hides nothing |

---

# 10. Error behaviour

Every failure names the input, the file, or the option path it concerns.

| Condition | Result |
| --- | --- |
| Unparseable registry | Non-zero; names the file and the line |
| Unknown input name requested | Non-zero; names the input and lists known names |
| Dependency cycle | Nix reports it during locking; Vendomat does not duplicate the check |
| Dirty store working tree | Non-zero (exit 1) for that input only; other inputs proceed |
| `keep` or `mirror` clone fails (unreachable remote, timeout, missing tag) | Non-zero (exit 2) for that entry; `flake.nix` is already written; other entries proceed |
| A directory in the source root is not a Git repository | Non-zero (exit 1); names the directory; leaves it untouched |
| `path` names an unknown input | Non-zero (exit 1); names the input and lists the direct inputs |
| Hand-written `flake.nix` present | Non-zero (exit 1); names the file; leaves it untouched |
| `[inputs]` entry without a tag pin | Non-zero (exit 2); names the entry and shows `ref = "refs/tags/<tag>"`; writes nothing |
| Entry with no `url` and no `[forge]` table | Non-zero (exit 2); names the entry; writes nothing |
| `mirror` or `keep` on `nixpkgs`, `devenv`, or a `[passthrough]` entry | Non-zero (exit 2); names the entry |
| `flake-outputs.nix` missing | Non-zero (exit 2); names the file; writes nothing |
| Invalid registry entry or `[follows]` pair | Non-zero (exit 2); names the file, the table, and the entry; writes nothing |
| `follows` edge on a child with no `nixpkgs` | Nix warns at lock time; Vendomat does not fetch the child to check |
| Unresolvable package name in a host TOML | Evaluation error; names the key and the name |
| Option defined in both TOML and Nix | Native option type merges equal scalars and lists; an incompatible scalar conflict names the option path |
| Build failure in one input | That input reports failed; others proceed |
| Cache path absent | Reports absent; never a success |

---

# 11. Observed native facts

Each was observed on the pinned tools. The design depends on them. None is a gate.

| ID | Fact | Evidence |
| --- | --- | --- |
| `NAT-001` | `git+file://…?rev=` locks a real revision and NAR hash | 2026-10-07, Nix 2.34.7 |
| `NAT-002` | Dotted-path TOML can convert to nested NixOS options; package values require option-specific resolution | PV-06, NixOS fixture |
| `NAT-003` | devenv has no `aliases` option. `scripts` sort first on `PATH` by `meta.priority` | devenv `fe20b5c`, `src/modules/top-level.nix:353` |
| `NAT-004` | Attic 0.1.0 skips a path present in an upstream cache during push | PV-10, disposable Attic 0.1.0 fixture |
| `NAT-005` | The Nixpkgs and Home Manager Neovim wrappers default to `--suffix PATH` | Observed 2026-10-06 |
| `NAT-006` | Historical observation: devenv merges an imported `devenv.yaml` only for local paths inside the git root. This is not part of the V5 dependency contract. | Observed 2026-10-06 |
| `NAT-007` | The flake delivery form evaluates impurely by default | Observed 2026-10-06 |
| `NAT-008` | `nix build --out-link` creates an indirect garbage-collection root | To observe |
| `NAT-009` | devenv Machines transfers with `nix copy --to ssh://` and does not substitute through Attic | Upstream documentation |
| `NAT-010` | Nix 2.34.7 rejects `ref` and `rev` as input attributes beside a string `url` (`unexpected flake input attribute 'ref'`). The query form `?ref=…&rev=…` locks both values | PV-13 |
| `NAT-011` | `nix flake lock` does not evaluate `outputs`. A missing project file fails at evaluation | PV-13 F6 |
| `NAT-012` | Nix cannot see an untracked file in a Git-backed flake and says so. A new `flake.lock` is added as intent-to-add, and the tree reads dirty until it is recorded | PV-13 F5 |
| `NAT-013` | A `follows` override on a child with no such input draws a warning. The same override on a `flake = false` input is ignored with no message. A missing target is an error | PV-13 F7 |
| `NAT-014` | A read-only `git daemon` serves a tagged repository to Nix 2.34.7. The lock records the `git://` URL, the tag, and the revision. A tag, a tag with a rev, and a rev alone all lock | PV-16 |
| `NAT-015` | A revision Nix already fetched evaluates with the daemon stopped. A cold store with an empty fetcher cache fails | PV-16 |
| `NAT-016` | An idle `git daemon` used 0 CPU ticks in 20 seconds, 1.8 MB of memory, one thread, and no child process | PV-16 |
| `NAT-017` | The source path is the same whether Nix fetches a tag by `git://` or by a local `file://` URL | PV-17 |

`NAT-009` is why system activation runs through `nixos-rebuild`, which substitutes normally.

---

# 11a. Acceptance

Two tests. Both run on one machine.

**A. An input reaches a project output with no local build.**

1. In a project that has never used Vendomat, write `flake-outputs.nix` and add one entry that names a tag to `vendomat.toml`.
2. Run `vendomat sync`, and track both Nix files in Git.
3. Lock the flake and build the selected output: `nix build .#packages.<system>.default`.

Pass: the generated `flake.nix` names only the direct inputs and no `devenv`, `flake.lock` carries
every transitive input at an exact revision, and the output builds with Vendomat absent from the
flake and from `PATH`. The source arrives from the collection on `server` over the tailnet, from
`framework`, and the built outputs arrive from Attic. Record the graph's `nixpkgs` nodes. Require
one node only when every authored input in the tested graph follows its parent. A project that wants
a shell defines it in its own outputs file and owns its entry command.

**B. A setting reaches a machine from TOML.**

1. `vendomat set programs.nvimReview.enable true`
2. `vendomat diff` reports the delta from the last committed host file to the current file.
3. Commit the host TOML through Gitman.
4. `vendomat apply`.

Pass: the delta names only that option, the rebuild succeeds, and the command is on the machine.

**C. A variant does not disturb its base.**

1. Enable an editor variant beside the daily editor.
2. Run both.

Pass: each keeps its own configuration and state, and the variant's closure difference from the
core is recorded.

---

# 12. Bootstrap and conversion

Vendomat starts from a bare repository. Every machine is reconfigured. The existing trees are
replaced, not extended.

| ID | Requirement | Verify |
| --- | --- | --- |
| `BOOT-001` | A machine core MUST evaluate and boot with no Vendomat process and no Vendomat Python | PV-11 test VM boots, accepts a user login, and has no Vendomat command |
| `BOOT-002` | The core MUST carry cache access, so a freshly installed machine substitutes before anything else runs | `nix show-config` on first boot lists the substituter and the trusted key |
| `BOOT-003` | The core MUST hold only what every machine needs | Remove any core element; at least one machine fails to boot or becomes unreachable |
| `BOOT-004` | *Superseded by `BOOT-021` to `BOOT-023`.* `nixos-rebuild test` was the in-place mechanism. The fallback is now a second bootable drive | — |
| `BOOT-005` | *Superseded by `BOOT-021`.* Written for an in-place conversion with generation rollback | — |
| `BOOT-006` | The core MUST boot in a virtual machine before it reaches `server` | PV-11 QEMU test VM boots and passes its user and service checks |
| `BOOT-007` | *Withdrawn 2026-10-07.* A blast-radius conversion order assumed several machines. `nixosConfigurations` holds only `server` | — |
| `BOOT-011` | *Superseded by `BOOT-022`.* Written for an in-place conversion | — |
| `BOOT-012` | A cold-consumer claim MUST be verified in a virtual machine with an empty store, not an isolated store on the build host | Every closure path substitutes in the virtual machine with local builds disabled |
| `BOOT-013` | *Superseded by `BOOT-014`.* Written when `server` was the only machine | — |
| `BOOT-014` | *Superseded by `BOOT-018`.* Written when the laptop was the proving ground | — |
| `BOOT-015` | *Narrowed by `BOOT-019`.* The laptop still supplies the proof, but as a by-product | — |
| `BOOT-018` | Every build step MUST run on `server`. The laptop MUST NOT be a prerequisite for any step | Steps 1 to 9 complete with the laptop absent |
| `BOOT-019` | The laptop install MUST require no local build | A cold installer VM with its real route, trust key, credential, and source obtains every closure path with `--max-jobs 0`; the install log shows no compilation |
| `BOOT-020` | A step MUST NOT depend on the laptop's reachability | No verify command in the guide names the laptop before step 10 |
| `BOOT-021` | The 512 GB installation MUST stay independently bootable, with its own EFI System Partition, until the new root has run reliably | Boot each drive from the firmware menu in turn; each reports its own root filesystem UUID |
| `BOOT-022` | The new system MUST be built on the running old system and installed as a prebuilt closure | The install log shows no build. `nixos-install` is given `--system`, `--closure`, or `--store-path` |
| `BOOT-023` | `server` MUST be converted by a fresh install on the new drive, never in place | The running system's drive is not written during the install |
| `BOOT-024` | Neither installation MUST write the other's boot entries | After installing the new system, the old EFI System Partition is unchanged |
| `BOOT-016` | An element that only one machine needs MUST be a delta, never part of the core | Remove it from the core; both machines still boot and stay reachable |
| `BOOT-017` | A fan-out claim MUST name the machines it covers | A build on either machine is shown present in the cache and substitutable by the other |
| `BOOT-008` | A converted machine MUST reach every capability it had before conversion | Compare the installed command set and the active services before and after; name every removal |
| `BOOT-009` | No conversion step MUST depend on Vendomat Python | Steps 1 to 6 of the build order run with the CLI absent; PV-11 is only the VM fixture |
| `BOOT-010` | A converted input MUST produce the same result as the tree it replaces, or name the difference | Build both; compare the output set. `nv` is the first case |

**`BOOT-018` rationale.** `framework` has been unreachable since 2026-10-07. An earlier attempt at
this proof stalled for exactly that reason: its gate required a host nobody could reach. No V5 step
may inherit that dependency. `server` builds everything; a virtual machine is the pre-flight check (`BOOT-006`).

**`BOOT-021` to `BOOT-024` rationale.** The 4 TB drive is planned as a fresh installation with its own
 EFI System Partition. Two separate EFI System Partitions keep the installations independent: a
 failed install cannot damage the running system's bootloader, and a generation rollback is no
 longer the fallback — a whole second drive is. `atticd` runs only on the old system, so the new
 system could be built there and installed as a prebuilt closure, but PV-09 has not proved that the
 installer can reach the private cache or obtain that closure. This part remains blocked.

**`BOOT-019` rationale.** A warm host store or cache listing does not prove a cold installer route.
PV-09 fetched a canary into an isolated store on `server`, but the cold VM or installer test remains
required.

**`BOOT-016` rationale.** `server` is headless and the laptop is graphical. That difference is what
keeps the core honest: `atticd` and the builder are `server` deltas; Hyprland, power management, and
wifi are laptop deltas.

**`BOOT-010` rationale.** `nix-nvim` splits into a core and a daily variant. That is a refactor of
a working tree, so the daily editor needs a before-and-after comparison rather than an assumption.

---

# 14. Out of scope

Vendomat is not and MUST NOT become: a daemon, a deployment engine, a retention engine, a cache
protocol, an audit system, a second lock, a package manager, a workspace orchestrator, or a
configuration language.

It writes no receipt. It makes no machine-generation claim. It does not replace the NixOS module
system; it feeds it.

Deferred with no requirement here: off-host copies of Vendomat state, signing-key rotation,
a second target system, build-from-source proof for a package dependency, and suggesting scripts
from shell history.

## The preserved surface is withdrawn

An earlier rule required that eleven central overlays and ten local checkouts keep their current
paths until a replacement passed a before-and-after fixture. That constraint is withdrawn. Every machine is
reconfigured, so those paths are replaced rather than preserved.

One obligation survives from it, as `BOOT-010`: a converted input must produce the same result as
the tree it replaces, or name the difference. Replacement is permitted. Silent loss is not.

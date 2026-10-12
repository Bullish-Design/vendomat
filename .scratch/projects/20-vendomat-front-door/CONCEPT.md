# Project 20: Vendomat and Basix

**Design proposal, 2026-10-12.** The owner chose Vendomat as the user entry point on
2026-10-11. This review simplifies that direction. It does not change the current runtime.
Names and interfaces below remain proposed until a fixture proves them on the pinned tools.
See the [review](evidence/SIMPLIFY-REVIEW-2026-10-12.md) for evidence and capability losses.

## The user path

Basix installs a small NixOS system on a selected disk. A learner then adds programs,
services, and settings as data. Vendomat owns the supported user workflow and calls
the pinned devenv fork for locks, evaluation, builds, and machine operations.
NixOS and Home Manager own activation and rollback.

The proposed routine data file is `vendomat.toml`. Nix reads it directly with
`builtins.fromTOML`. Vendomat defines a small catalog of programs, languages,
services, settings, and fresh machine facts. A fixed module maps those entries
to native options. Routine use needs no Nix syntax, input URL, import path, or
merge priority. The template owns `devenv.yaml` and `devenv.nix`. An advanced
user may edit them to add a module or a value outside the catalog.
`devenv.lock` holds exact revisions. There is no generated `.vendomat/` tree.

This changes the earlier YAML choice. TOML loses YAML block strings, null, and
arbitrary option paths. It lets Nix read user data without a parser, generator,
digest, stale guard, or schema cache. An isolated Nix fixture proved direct
reading and file-level type errors. The pinned-fork workspace still needs proof.
The catalog's exact entries and version workflow remain fixture decisions.

Vendomat owns each catalog option. An imported library cannot define that
user-facing field. The routine template imports only the fixed catalog module.
This constraint removes routine priority conflicts. Native Nix merge rules
still apply to advanced modules. Nix option types check
catalog values. Vendomat must force every set value before a requested action.
Errors may name an option and file without a precise TOML line or column.

## Commands and updates

`vendomat` with no argument enters the shell. Vendomat exposes the few routine
intents: `new`, `test`, `build`, `update`, and `machine`. It checks catalog
data before it calls devenv. `update` moves a selected supported release and
its native lock together; its exact edit protocol needs a fixture. The
`machine` workflow runs preflight and a failed-unit check at the relevant
steps before it calls native Machines. `vendomat devenv ...` is the explicit
advanced door for other native commands. The host Vendomat release carries
the pinned fork. It does not route each workspace to another Vendomat binary.
A workspace restores earlier data and lock through version control. There is
no `prepare`, `sync`, `path`, `check`, `bump`, or special exit-code protocol.

Vendomat does not resolve imported inputs or create a second lock. Advanced
modules use native `follows`; the pinned fork inherits their inputs. Supported
updates use normal Git or forge release refs in the native lock. The first
release has no collection mirror, keep clone, backup mode, or release builder.
An offline first use requires the source and build paths to be present already.

## Basix machines

The first release installs a fresh Basix system on one standard UEFI disk. The same
flow adds a second machine. Each machine needs a name, system, state version, target
address, admin public key, and stable `/dev/disk/by-id/` target. A fixed fresh-install
type has no user mode field or adoption fields. A disk preflight still checks the
actual target and protected disks before a write. Nix types cannot prove hardware
identity. The controller uses a temporary installer key; the installed system gets
the separate admin key. The controller re-pins the new host key after first boot.
The core boots without a user private key or secret provider. Adoption of an
existing NixOS installation is deferred as a distinct, disk-free flow.

The first machine needs only its local Nix store. For two machines, an administrator
can enable signed Harmonia sharing after placing a signing key outside the store.
The data selects one cache host and declares its address and public key once.
Vendomat derives client trust and Nix fallback from that selection. The cache
host serves its own store to a restricted network. A down cache does not stop a build.
Build shared outputs on the cache host and retain selected outputs with native Nix
roots. The first release does not automate key delivery, rotation, or collection builds.
A real two-machine gate must prove substitution, fallback,
and key handling before replacing the current Attic route.

## Proof and limits

The first implementation slice proves direct data reading and eager option checks
in an isolated workspace. Later slices prove a real workspace, fresh virtual-machine
install, keyless boot, rollback, and two-machine cache sharing. A real disk write
requires the owner's separate authorization and a read-only hardware review.
Fixture success is evidence about a mechanism, not acceptance of a runtime or machine.

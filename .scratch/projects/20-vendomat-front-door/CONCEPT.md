# Project 20: Vendomat and Basix

**Design proposal, 2026-10-12.** The owner chose Vendomat as the user entry point on
2026-10-11. This review simplifies that direction. It does not change the current runtime.
Names and interfaces below remain proposed until a fixture proves them on the pinned tools.
See the [review](evidence/SIMPLIFY-REVIEW-2026-10-12.md) for evidence and capability losses.

## The user path

Basix installs a small NixOS system on a selected disk. A learner then adds programs,
services, and settings as data. Vendomat opens a development shell and passes other
operations to the pinned devenv fork. Nix and devenv own dependency locks and builds.
NixOS and Home Manager own activation and rollback.

The proposed routine data file is `vendomat.toml`. Nix reads it directly with
`builtins.fromTOML`. A fixed module maps its supported data options to native devenv,
NixOS, and Home Manager options. A user does not need Nix syntax for those options.
`devenv.yaml` holds native inputs and imports when the user adds a module. `devenv.nix`
is the escape hatch for functions and options outside the data surface. `devenv.lock`
holds exact revisions. There is no generated `.vendomat/` tree.

This changes the earlier YAML choice. TOML loses YAML block strings, null, and the
single-file input and import surface. It lets Nix read user data without a parser,
generator, digest, stale guard, or schema cache. The first fixture must confirm the
direct read and source location on the pinned Nix. The data surface stays narrow:
programs, common languages and services, ordinary settings, and Basix machine facts.
The exact option names remain a fixture decision. Unsupported values use native Nix.

Library authors use `mkDefault` for scalar settings that users may replace. Native
Nix merge rules decide the result. Two different plain scalar definitions fail;
lists and attribute sets merge by their native rules. Vendomat does not promise that
data always wins. Nix option types are the validator. A fixture must prove that the
entry command forces every data value needed for the requested operation. Errors may
name an option and file without a precise TOML line or column.

## Commands and updates

`vendomat` with no argument enters the shell. `vendomat new` creates a workspace
from a fixed template. Other arguments pass to the pinned devenv fork, including
`test`, `build`, `update`, and `machines`. The host Vendomat release carries that
fork. It does not route each workspace to a different Vendomat binary. Users update
the host release explicitly. A workspace keeps its native `devenv.lock` and can
restore an earlier configuration and lock through version control. There is no
`prepare`, `sync`, `path`, `check`, `bump`, or Vendomat exit-code protocol.

Vendomat does not resolve imported inputs. Users write native `follows` where they
need one shared input. The pinned fork inherits imported inputs. Source URLs use
normal Git or forge routes with explicit release refs. The first release has no
collection mirror, keep clone, backup mode, or release builder. An offline first
use requires the source and build paths to be present already.

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
The cache host serves its own store to a restricted network. Each client names the
cache URL and public key and sets Nix fallback so a down cache does not stop a build.
Build shared outputs on the cache host and retain selected outputs with native Nix
roots. The first release does not automate key delivery, rotation, collection builds,
or cache-host selection. A real two-machine gate must prove substitution, fallback,
and key handling before replacing the current Attic route.

## Proof and limits

The first implementation slice proves direct data reading and eager option checks
in an isolated workspace. Later slices prove a real workspace, fresh virtual-machine
install, keyless boot, rollback, and two-machine cache sharing. A real disk write
requires the owner's separate authorization and a read-only hardware review.
Fixture success is evidence about a mechanism, not acceptance of a runtime or machine.

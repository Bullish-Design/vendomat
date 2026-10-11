# Project 19: Vendomat as the source, store, and cache layer of Basix

**Date:** 2026-10-11. **Status:** Draft concept for owner review. A refined and simplified V6.
**Base:** [project 16](../16-vendomat-devenv-layer/CONCEPT-V6.md) (V6 concept and its gates) and
[project 18](../18-single-disk-cache-concept/CONCEPT.md) (cache experiments).
**Decisions:** [DECISIONS.md](DECISIONS.md).

This draft changes no authority. Project 14 stays the authority, and project 16 stays the V6 draft,
until the owner accepts this concept. `.scratch/CURRENT.md` is unchanged.

## 1. Purpose

**Basix** is the foundational, minimal devenv configuration that defines an entire system. A user
installs it on their own machines. Then the user defines their actual system, everything they use,
as devenv modules on top of it.

**Vendomat** is the Nix layer under Basix. It has three parts:

| Part | Question it answers | Native mechanism |
| --- | --- | --- |
| Source | Which code, at which release? | A local collection of release tags; every input pins a tag |
| Store | What was built, and what stays? | `nix build` of each tag, a GC root per tag, collection under disk pressure |
| Cache | How do my other machines get it? | One host serves its store, signed; the others substitute from it |

The owner's `server` and `framework` are one installation of Basix. They are an example, not the
design target.

## 2. Principles

1. **One installation, one owner.** Nothing is shared between installations.
2. **It starts on one machine.** Every part works on a single machine with no extra service. A
   second machine adds one thing: a cache to read.
3. **Native first.** Nix, devenv, devenv Machines, NixOS, Home Manager, disko, and SecretSpec do the
   work. Vendomat configures them. It runs no daemon of its own and holds no state of its own.
4. **Derived data is disposable.** The store and the cache can be rebuilt from source. No backup,
   no migration, no retention engine.
5. **Tags are the record.** Release tags are immutable. Pins name tags. Built tags are kept.
6. **Smallest maintainable system.** A feature stays only while its value exceeds its upkeep.

## 3. The layers

| Layer | Owner | Holds |
| --- | --- | --- |
| Native | Nix, devenv (pinned fork), NixOS, Home Manager, disko, SecretSpec | Evaluation, locks, shells, activation, rollback, partitions, secret resolution |
| Vendomat | This repository | Source, store, and cache: the collection, tag pins and input resolution, the builder, release roots, cache serving and trust |
| Basix | The Basix configuration | The machine inventory, the core role, install and adoption, required setup (section 6) |
| User system | The user's devenv modules | Everything the user runs and uses |

## 4. The three parts

### Source

- **One collection per installation.** A directory of Git repositories that accept release tags only
  and never move a tag. A read-only `git://` daemon serves it to the installation's machines.
- **Every input pins a tag.** `vendomat sync` resolves a workspace's selected modules into a
  `.vendomat/` fragment of tag-pinned inputs, because devenv drops nested inputs and deep `follows`.
  The lock records the commit.
- **Third-party code** enters as a mirror or a kept clone, by choice per entry.
- **On one machine**, the collection is local. Nothing else changes.

### Store

- **The builder** builds each release tag of each collection input, one at a time, and logs the
  command, the exit status, and the output paths.
- **Every built tag is kept.** The builder writes one GC root per built tag
  (`nix build --out-link <roots>/<input>/<tag>`). Deleting a root releases that tag.
- **System generations are kept** by their own native roots.
- **Everything else is collected under disk pressure only** (`min-free` / `max-free`). The building
  host runs no scheduled GC. The default keeps every tag. A later setting may keep the newest N per
  input.
- Effect: an old pin, an old workspace, and a rollback all find their outputs, with no rebuild.

### Cache

- **One host per installation serves its store** as a signed, read-only binary cache. Harmonia does
  this through its NixOS module, socket-activated and sandboxed. Whatever is in that host's store is
  in the cache. There is no push, no push credential, and no second copy.
- **Every other host** lists the cache after the upstream caches, with its public key, and with
  fallback on. A missing cache or a missing path never blocks a build.
- **Shared work is built on the serving host.** An output built only on another host is not shared.
- **Wiring comes from the inventory.** One host is marked as the cache server. Every other host
  derives the cache address and the public key from that mark.
- **On one machine**, nothing runs. The local store is the cache.

## 5. Secrets: SecretSpec is required

Basix requires devenv's SecretSpec from the first setup. The user names a provider and a profile.
`secretspec.toml` declares every secret the installation needs.

- **Install-time secrets** reach a fresh host through `machines.<host>.install.secrets`. That option
  writes a named SecretSpec value to a path, owner, and mode in the installed system. The value never
  enters the Nix store (upstream documentation of the pinned fork, `docs/.../machines.md` lines
  301-357; evidence about the tool, not a passed gate).
- **The cache signing key** is the first such secret. The setup creates it, stores it through
  SecretSpec, and commits only the public key into the inventory.
- **Runtime secrets** use a NixOS secret module (sops-nix or agenix) when an installation wants one.
  Its key arrives the same way. This is an installation's choice, not a Basix requirement.
- **Two limits are known.** `install.secrets` runs only at install; a later deploy does not refresh
  it. An adopted host never runs install, so it needs another first delivery.

## 6. What Basix requires at setup

1. The pinned devenv fork.
2. SecretSpec with a provider and a profile.
3. An inventory with at least one host, its mode (`fresh-install` or `adopt-existing`), and its disks
   with roles.
4. A collection location.

Every other value has a default and can change later (see [DECISIONS.md](DECISIONS.md)).

## 7. Kept from V6

- **One pinned devenv:** upstream `v2.4.0` plus the patch series, built from the collection. Every
  workspace sets `require_version` and pins the fork.
- **Workspace flow:** the template creates `devenv.yaml` and `devenv.nix`; the user edits
  `vendomat.toml` (`[imports]`, `[settings.<module>]`); `vendomat sync` writes `.vendomat/`. No Nix
  edits for routine changes.
- **Native authored modules** for devenv, NixOS, and Home Manager. No shared description format.
- **Machines:** `devenv machines plan`, `deploy`, `apply`, `status`, `rollback`, unwrapped. Home
  Manager inside the NixOS role.
- **Install safety:** the two modes, disk roles, module assertions, the target-side preflight, and the
  fork's refusals.
- **Commands:** `sync`, `path`, `check`, `bump`, `machine install`.

## 8. Removed from V6

| Removed | Replaced by |
| --- | --- |
| Attic, its database, and its pool patch (`CACHE-013`) | The serving host's store and harmonia |
| `vendomat push`, the push task, `attic watch-store` | Building on the serving host |
| Push and pull credentials; PV-09 | No secret for reads; network reach is the installation's choice |
| The second data disk for the cache | The root disk |
| Retention, backup, and migration of cache data | Release roots and GC under disk pressure |
| Upstream filtering and the load and kill tests | Nothing; cache.nixos.org keeps its priority |
| Owner-specific assumptions (`server`, the tailnet, sops as a requirement) | Inventory facts and SecretSpec |

## 9. The owner's installation

- `server` serves the cache, builds the collection's tags, and keeps release roots. Tailscale Serve
  can publish harmonia on the tailnet. sops-nix stays for runtime secrets; its age key arrives through
  `install.secrets`.
- `framework` is adopted in place. It trusts `server`'s key from the inventory. Its first secret
  delivery needs the adopted-host route (section 5).
- Cutover step 8 stays: the old system mounts its data disks under `/mnt`, and the preflight refuses
  that. The new role needs no data disk.

## 10. Evidence and status

| Claim | Status |
| --- | --- |
| Pinned fork, sync, workspace flow, Machines flow, install route in QEMU | Passed in project 16 (gates G0, G2-G4, G3A, G6, G7) |
| Harmonia serves the host store; signed cold substitution; NAR hashes equal; absent path 404; reads 1-3 ms during writes | Passed on loopback, as the owner's user ([project 18 evidence](../18-single-disk-cache-concept/evidence/exp-A-harmonia.md)) |
| `install.secrets` writes SecretSpec values at install | Documented upstream; not run here |
| The harmonia NixOS module, a second VM, release roots, GC under disk pressure, inventory wiring | Not proven |
| Real hardware, firmware, and network | Not proven |

The first proofs in planning: a two-VM test (serving host and a cold host with a store image, per
`BOOT-027`) with the harmonia module, inventory wiring, a release root that survives GC, and a signing
key delivered by `install.secrets`.

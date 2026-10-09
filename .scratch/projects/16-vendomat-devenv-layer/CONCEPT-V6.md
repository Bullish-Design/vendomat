# Vendomat V6 concept: the devenv layer

**Date:** 2026-10-09. **Status:** Draft for owner review. **Spec:** [SPEC-V6.md](./SPEC-V6.md).
**Evidence:** [project 15](../15-devenv-alignment/) — `REPORT.md`, `FOLLOWUP-2026-10-09.md`, eleven agent
reports in `raw/`, and working prototypes in `prototypes/`.
**Builds on:** [V5](../14-vendomat-local/CONCEPT-V5.md). V5 parts that V6 does not change stay in force:
the source collection, the registry, the flake generator for libraries, `vendomat path`, the Attic
cache, the builder, cores and variants, and named paths.

## Purpose

One owner runs two machines and many small repositories. The goal has three layers:

1. A minimal NixOS core boots each machine.
2. devenv modules open on top of it, per application and per workspace.
3. Vendomat holds the source and the cache, and fills the gaps in devenv.

V5 kept Vendomat out of devenv: it generated no shell, and no project imported it. V6 reverses that.
**Vendomat is the owner's layer on top of devenv.** Every workspace imports one pinned Vendomat devenv
module. Where devenv cannot be fixed from inside a module, Vendomat acts before devenv runs, or ships
a patched devenv.

## What changes from V5

| Area | V5 | V6 | Why |
| --- | --- | --- | --- |
| Project shell | The project may write a shell in `flake-outputs.nix` (`GEN-022`), which is devenv's reduced flake mode | Every workspace is a devenv project (`devenv.nix`, `devenv.yaml`, `devenv.lock`) | The flake mode has no SecretSpec, no evaluation cache, an impure root, and a four-command shim (`NAT-021`) |
| Vendomat in projects | No project imports Vendomat (`DEL-008`) | Every workspace imports the Vendomat devenv module (`VMOD-001`) | The module gives checks, commands, paths, cache export, and machine guards inside the shell |
| Inputs | Hand-written `devenv.yaml`, or a generated `flake.nix` | `vendomat sync` also writes a `.vendomat/` inputs fragment that the workspace imports (`PRE-*`) | devenv ignores an imported repo's `devenv.yaml` and drops nested `follows` (`NAT-018`, `NAT-036`) |
| devenv | Whatever each lock pins: 26 revisions in 56 locks | One patched release build, pinned everywhere (`DVN-*`) | Offline shells, the Machines install fix, and an enforced `require_version` |
| Machines | `nix-meta` with `nixos-rebuild`; `systemcfg` planned | A new `nix-systems` repository with devenv Machines (`MACH-*`) | Reviewed plans, a watchdog rollback, and one interface for both hosts |
| New system | Convert `server`, keep capability parity (`BOOT-008`, `BOOT-010`) | Blank slate on the 4 TB drive; the 512 GB system is a fallback and a reference only | Owner decision, 2026-10-09 |

## The layers

| Layer | Owner | Holds |
| --- | --- | --- |
| Native | Nix, devenv, NixOS, Home Manager, disko | Evaluation, locking, shells, activation, rollback, partitioning |
| Vendomat | This repository | The devenv module, the pre-resolver, the command line, the devenv fork and its build |
| Source | The collection on `server` (V5, unchanged) | Release tags of every personal repository, read over `git://` |
| Cache | Attic on `server` (V5, unchanged) | Build outputs |
| Configuration | Each repository | `vendomat.toml`, `devenv.nix`, and for machines the `nix-systems` repository |

## 1. One pinned devenv

Vendomat ships a fork of devenv in the collection: upstream `v2.4.0` plus a short patch series, tagged
`v2.4.0-vendomat.1`. The builder on `server` builds it and Attic holds it. The host core installs it.

| Patch | Upstream | Kept until |
| --- | --- | --- |
| Machines install no longer hangs with install payloads | `a5fd551a` (PR #3255, on `main`) | The next release |
| `src/modules/latest-version` says `2.4.0` | `a5c34429` (on `main`) | The next release |
| A shell reuses locked inputs already in the store, so it enters with the collection down | PR #3244 (open) | Upstream merges it |
| `isRelease = true`, so `require_version: true` is enforced | none; fork-only | Always |

Every devenv project sets `require_version: "2.4.0"` and pins `inputs.devenv` to the fork revision. A
fleet check reports any project that differs. On each upstream bump, a fixed checklist runs (SPEC
`DVN-007`).

Evidence: the series builds in about six minutes; only devenv's own crates build locally. The patched
CLI entered a shell offline where the stock CLI failed (agent J).

## 2. The Vendomat devenv module

A workspace adds one input and one import:

```yaml
# devenv.yaml
imports: [ ./.vendomat ]          # written by `vendomat sync`; declares every input
```

```nix
# devenv.nix
{ inputs, ... }: {
  imports = [ inputs.vendomat.devenvModules.default ];
  vendomat.cache = { push = true; name = "vendomat"; };
  knappy.enable = true;            # a library face, imported automatically
}
```

The module does this:

| Function | How | Evidence |
| --- | --- | --- |
| Imports every library's devenv face | Each flake input's `devenvModules.default`, except Vendomat itself, `devenv`, `nixpkgs`, and non-flake inputs. A face does nothing until `enable = true` | Agent K Q1: identical shell derivation with nothing enabled |
| Refuses an unpinned input | An **assertion** reads `devenv.lock`: every git node must name `refs/tags/…`. A task cannot stop shell entry | Agents I Q5, K Q2 |
| Pushes outputs to Attic | `vendomat.cache.push` adds a `vendomat:push` task and a `vendomat-push` script | Agent K Q3 (stand-in `attic`) |
| Exposes input store paths | `vendomat.inputPaths`, and a JSON output whose closure holds every input source | Agent K Q4 |
| Exports host paths | `vendomat.paths` from `/etc/vendomat/paths.json`, as `VENDOMAT_PATH_<NAME>` | Agent K Q5 |
| Sets host and user defaults | `profiles.hostname.<host>` and `profiles.user.<user>` with `lib.mkDefault` | Agent K Q6 |
| Guards machine disks | Owns `machines.<host>.nixos`; the owner writes `vendomat.inventory.<host>`; assertions reject unsafe layouts | Agent K Q7 |

Four rules follow from the fixtures:

1. Hard checks are assertions. A failing task only logs a warning (`NAT-024`).
2. Assertions run for `devenv shell`, `test`, and `up`, not for `devenv build` or `eval` (`NAT-025`). So
   `vendomat push` runs the check itself.
3. Under `outputs`, only derivations. A string or a flake input breaks `devenv build`.
4. The module owns `machines.<host>.nixos`. Two definitions silently drop modules (`NAT-029`).

## 3. The pre-resolver

devenv resolves and fetches inputs before any module runs. So a module cannot fix three gaps:

- An input-style import (`imports: [lib-b/devenv]`) ignores that repository's `devenv.yaml`.
- A `follows` deeper than one level is dropped without a message.
- With a cold fetcher cache and the collection down, the stock shell fails.

The pre-resolver closes the first two. The devenv fork closes the third.

`vendomat sync` reads `vendomat.toml` and writes three files:

| File | Contents |
| --- | --- |
| `.vendomat/devenv.yaml` | Every input as a top-level input, tag-pinned, with one-level `follows` so each source has one lock node; the `imports` the registry names |
| `.vendomat/devenv.nix` | Assertions that stop the shell when the registry or the fragment changed since the last sync |
| `.vendomat/digest` | Hashes of the registry, the resolved imports, and the fragment |

A direnv function, `use_vendomat`, re-syncs only when the digest is stale, then calls `use devenv`.
With nothing changed it costs about 0.35 s. The fragment adds no measurable time to a warm shell
(agent I).

One rule needs care: a workspace `devenv.yaml` or `devenv.local.yaml` entry for the same input replaces
the generated entry entirely, including its `follows`. `vendomat sync` warns about it.

## 4. Library faces

A **face** is a library's module for one target: devenv (`devenvModules.default`), NixOS
(`nixosModules.default`), or Home Manager (`homeManagerModules.default`). A library exports only the
faces it supports. Each face declares `<name>.enable`, default false, and changes nothing until enabled.
Each face must evaluate alone, and its options must not collide with another face.

The `mkModules` helper (V5 `MOD-*`) is deferred. Write faces by hand to the convention, and build the
helper when three libraries repeat the same shape.

## 5. Source and cache

The V5 source collection is unchanged: release tags only, served read-only over `git://` on the
tailnet, every input pinned to a tag. The V5 Attic cache and builder are unchanged.

Two additions:

- `vendomat push` builds a workspace's outputs or a machine and pipes the store paths to
  `attic push <cache> --stdin`. Nothing in devenv runs after `devenv build`, so the push is explicit.
- The host core sets the Attic substituter and key in `nix.settings`. devenv's `cachix.*` options
  reach only `*.cachix.org` (`NAT-023`).

## 6. The `nix-systems` repository

A new repository, written from nothing. It is a devenv project with the Vendomat module.

```text
nix-systems/
  vendomat.toml            nixpkgs, devenv fork, disko, home-manager, vendomat, libraries
  devenv.yaml              imports: [ ./.vendomat ]
  devenv.nix               machines and inventory
  nixos/core.nix           what every machine needs to boot and be reachable
  nixos/server.nix         server delta
  nixos/framework.nix      framework delta
  home/andrew.nix          Home Manager
  .machines/<host>/facter.json
```

```nix
# devenv.nix (sketch)
{ inputs, ... }: {
  imports = [ inputs.vendomat.devenvModules.default ];

  vendomat.inventory.server = {
    nixos.imports = [ ./nixos/core.nix ./nixos/server.nix ];
    disks.newsys  = { byId = "/dev/disk/by-id/nvme-eui.e8238fa6bf530001001b448b4fbe837d"; role = "install-target"; };
    disks.oldsys  = { byId = "/dev/disk/by-id/nvme-NX-512_2280_0040141310300"; role = "keep"; };
  };

  machines.server = {
    target.host = "root@localhost";
    home-manager = import ./home/andrew.nix;
  };
}
```

- **nixpkgs:** a plain `github:NixOS/nixpkgs/<rev>` of nixos-unstable for machines and workspaces. A
  shell that uses `devenv-nixpkgs` still fails offline, because that repository fetches its own nixpkgs.
- **Activation:** `devenv machines plan`, `deploy`, `apply`, `status`, `rollback`. Vendomat does not wrap
  them. A failed health check rolls back after `deploy.rollbackTimeout` (agent G).
- **Access:** root accepts the owner's deploy key, key-only. devenv runs as `andrew`, not root.
- **Services:** every service must start cleanly. One failed unit fails the whole deploy, and a unit
  that failed before the deploy makes the rollback fail (`NAT-034`).
- **Home Manager** is not rolled back by `devenv machines rollback`.

## 7. Installing `server` on the 4 TB drive

The 512 GB drive and its EFI System Partition stay untouched. They remain the fallback, chosen in the
firmware boot menu.

1. The disko layout names the 4 TB drive by `by-id`, uses a disk name unique to the host, presets the
   partition GUIDs and filesystem UUIDs, and mounts by UUID.
2. The first install sets `boot.loader.efi.canTouchEfiVariables = false`, so NVRAM stays as it is.
3. `vendomat machine install server` runs the preflight, then
   `devenv machines install server --phases disko,install` against `root@localhost`, from the running
   `server`. Services keep running.
4. The owner creates a one-time boot entry (`efibootmgr -C`) and reboots into it with `efibootmgr -n`.
   A failure needs only a power cycle.
5. After the new system has run reliably, it sets `canTouchEfiVariables = true` and runs
   `bootctl install` once.

**Two guards, so a bypass still fails:**

| Guard | When | Checks |
| --- | --- | --- |
| Module assertions | At build, before disko runs (devenv builds first) | Every disko disk is a `by-id` path with role `install-target`; no mount uses a partition label or a kernel name; no second definition of `machines.<host>.nixos` |
| Preflight | At runtime, on the target, before disko | The `by-id` path resolves; model, serial, and size match; no signature; not the running root or `/boot`; nothing under `/mnt`; a committed facter report |

All of this ran in a QEMU VM with two NVMe disks and persistent NVRAM: the old disk's partition table,
ESP files, and NVRAM entries stayed unchanged, and the new disk booted alone (agents E, F). The real
firmware's handling of NVRAM entries and one-time boot is not yet proven.

## Authority

devenv composes, locks, and activates. Nix builds and substitutes. disko partitions. Attic stores.
The collection holds source. Vendomat pins devenv, writes the inputs fragment, ships the module, guards
the disks, and pushes outputs. It owns no durable state.

## Boundaries

Vendomat is not a deployment engine: devenv Machines deploys. It is not a second lock: `devenv.lock` and
`flake.lock` belong to Nix. It is not a workspace orchestrator: each workspace is a plain devenv project
that imports one module.

## Build order

| Step | Work | Proven so far |
| --- | --- | --- |
| 1 | Put the devenv fork in the collection; build it; push it to Attic | Built and tested in fixtures (agent J) |
| 2 | Vendomat: the module, `vendomat sync` with the `.vendomat/` target, `use_vendomat`, `check`, `push`, `path` for devenv locks, `machine install` with the preflight; tests in Testee; release a tag | Prototypes (agents H, I, K) |
| 3 | `nix-systems`: core, `server` and `framework` deltas, Home Manager, inventory, disko layout; prove it in VMs (disko test, a Machines deploy to a VM) | Layout and deploy in a VM (agent G) |
| 4 | Install `server` on the 4 TB drive; boot it once; make it the default after it runs reliably | Route proven in a VM (agent F) |
| 5 | Convert workspaces: module, registry, pinned devenv | Pin scan written (agent G) |
| 6 | Install `framework` from `server` | Not started |

## Open decisions

1. ~~Where the Vendomat command runs from.~~ Decided 2026-10-09: a host launcher runs the version each
   workspace pins, or the host release outside a workspace (SPEC `DEL-017`).
2. **`mkModules`:** the convention now and the helper later is recommended (`FACE-*`, `MOD-*` deferred).
3. **Host settings in TOML** (V5 `SYS-*`, `fromToml`, `vendomat set` and `diff`). Not discussed since the
   move to Machines. Deferred.
4. **Face option paths:** `<name>.*` under devenv and `programs.<name>.*` under NixOS and Home Manager,
   or one path everywhere.

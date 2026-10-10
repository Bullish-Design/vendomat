# Vendomat V6 concept: the devenv layer

**Date:** 2026-10-09. **Updated:** 2026-10-10. **Status:** Draft for owner review.
**Spec:** [SPEC-V6.md](./SPEC-V6.md). **Update record:**
[CONCEPT-UPDATE-2026-10-10.md](./CONCEPT-UPDATE-2026-10-10.md).
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

The first user goal is a workspace that needs no Nix edits for routine setup and changes. A workspace
user selects authored modules and supplies their supported values in `vendomat.toml`. A module author
may write Nix. The bundled template generator creates the initial workspace files. `vendomat sync`
updates only Vendomat-owned files when the user's choices change. Machine composition follows this
workspace flow. Machine operators may use authored machine roles without Nix later; this draft does
not yet define that interface. New machine capabilities remain work for module authors.

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
| Configuration | Each repository | Workspace users edit `vendomat.toml`; templates create stable workspace files; Vendomat owns generated fragments. Machine authors configure `nix-systems` in Nix until an operator interface is proved |

## 1. One pinned devenv

Vendomat ships a fork of devenv in the collection: upstream `v2.4.0` plus a short patch series.
The current fixture tag is `v2.4.0-vendomat.2`. The builder on `server` builds it. The host core
installs it after the live distribution and cache gates pass.

| Patch | Upstream | Kept until |
| --- | --- | --- |
| Machines install no longer hangs with install payloads | `a5fd551a` (PR #3255, on `main`) | The next release |
| `src/modules/latest-version` says `2.4.0` | `a5c34429` (on `main`) | The next release |
| A shell reuses locked inputs already in the store, so it enters with the collection down | PR #3244 (open) | Upstream merges it |
| `isRelease = true`, so `require_version: true` is enforced | none; fork-only | Always |
| `machines install` refuses an `adopt-existing` machine before any contact (patch 0005) | none; fork-only | Always |
| `machines install` runs the target-side preflight of a `fresh-install` machine before disko (patch 0006) | none; fork-only | Always |

Every devenv project sets `require_version: "2.4.0"` and pins `inputs.devenv` to the fork revision. A
fleet check reports any project that differs. On each upstream bump, a fixed checklist runs (SPEC
`DVN-007`).

Evidence: the series builds in about six minutes; only devenv's own crates build locally. The patched
CLI entered a shell offline where the stock CLI failed (agent J). The recipe is `devenv-dist/`, and
`devenv-dist/materialize` reproduces the fork commit. V6 fixtures: 67 Rust unit tests, a 29-case CLI
fixture with a tripwire target, and a QEMU install with payloads (`evidence/01-devenv-distribution.md`).

## 2. The Vendomat devenv module and the workspace user

The template generator creates the workspace's `devenv.yaml` and `devenv.nix`. The user does not
edit either file for routine changes. The following files show the generated wiring, not user steps:

```yaml
# devenv.yaml
imports: [ ./.vendomat ]
```

```nix
# devenv.nix (template-owned wiring; exact imports remain proposed)
{ inputs, ... }: {
  imports = [ inputs.vendomat.devenvModules.default ./.vendomat/modules.nix ];
}
```

The user selects `knappy` and its supported values in `vendomat.toml`. `vendomat sync` resolves the
module's inputs and writes its import and settings into Vendomat-owned files. The exact registry
syntax and generated file path need a fixture on the pinned tools. The user's choice has one source
of truth. A module may provide its own `devenv.yaml`; its consumers inherit those inputs.

The workspace integration does this:

| Function | How | Evidence |
| --- | --- | --- |
| Imports selected workspace modules | The generated workspace wiring names authored devenv modules. An unselected source changes no shell output | Existing face fixtures prove inertness for the current builder; the selected-module flow still needs a consumer fixture |
| Refuses an unpinned input | An **assertion** reads `devenv.lock`: every git node must name `refs/tags/…`. A task cannot stop shell entry | Agents I Q5, K Q2 |
| Pushes outputs to Attic | `vendomat.cache.push` adds a `vendomat:push` task and a `vendomat-push` script | Agent K Q3 (stand-in `attic`) |
| Exposes input store paths | `vendomat.inputPaths`, and a JSON output whose closure holds every input source | Agent K Q4 |
| Exports host paths | `vendomat.paths` from `/etc/vendomat/paths.json`, as `VENDOMAT_PATH_<NAME>` | Agent K Q5 |
| Sets host and user defaults | `profiles.hostname.<host>` and `profiles.user.<user>` with `lib.mkDefault` | Agent K Q6 |
| Guards machine disks | The existing machine adapter owns `machines.<host>.nixos`; its inventory and assertions reject unsafe layouts | Agent K Q7 |

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

The current `vendomat sync` reads `vendomat.toml` and writes three files:

| File | Contents |
| --- | --- |
| `.vendomat/devenv.yaml` | Every input as a top-level input, tag-pinned, with one-level `follows` so each source has one lock node; the `imports` the registry names |
| `.vendomat/devenv.nix` | Assertions that stop the shell when the registry or the fragment changed since the last sync |
| `.vendomat/digest` | Hashes of the registry, the resolved imports, and the fragment |

The proposed workspace flow also needs generated Nix wiring for selected modules and supported
values. The sketch names `.vendomat/modules.nix`; its path and content remain unproved. The digest
must cover that wiring once the fixture selects its final form.

A direnv function, `use_vendomat`, re-syncs only when the digest is stale, then calls `use devenv`.
With nothing changed it costs about 0.35 s. The fragment adds no measurable time to a warm shell
(agent I).

One rule needs care: a workspace `devenv.yaml` or `devenv.local.yaml` entry for the same input replaces
the generated entry entirely, including its `follows`. `vendomat sync` warns about it.

## 4. Module authors write native modules

A module author may write `devenv.nix` and `devenv.yaml` in a reusable source. The module's
`devenv.yaml` declares the inputs that consumers inherit. The module author may also export a
`devenvModules.default` flake output when that suits the source. Vendomat selects and imports the
authored module; it does not build three target modules from one Vendomat description.

The module author defines the supported user values. The workspace bridge passes only values that
its tested format can express. A module that needs a package, function, or other Nix expression
keeps that expression in the authored module. The template generator may scaffold such a module.

NixOS and Home Manager modules remain native, target-specific modules. A source may provide one,
both, or neither. Sharing an option path across targets is a choice for that source, not a Vendomat
rule. The existing description builder and its three-target fixtures remain research evidence;
they are not the proposed authoring contract.

## 5. Source and cache

The V5 source collection is unchanged: release tags only, served read-only over `git://` on the
tailnet, every input pinned to a tag. The V5 Attic cache and builder are unchanged.

Two additions:

- `vendomat push` builds a workspace's outputs or a machine and pipes the store paths to
  `attic push <cache> --stdin`. Nothing in devenv runs after `devenv build`, so the push is explicit.
- The host core sets the Attic substituter and key in `nix.settings`. devenv's `cachix.*` options
  reach only `*.cachix.org` (`NAT-023`).

## 6. The `nix-systems` repository

A new repository, written from nothing. It is a devenv project with the Vendomat module. Machine
authors may write the Nix inventory in this phase. A later operator interface may generate wiring
for known roles and host facts. It must keep disk identity and installation review explicit.

```text
nix-systems/
  vendomat.toml            nixpkgs, devenv fork, disko, home-manager, vendomat, libraries
  devenv.yaml              imports: [ ./.vendomat ]
  devenv.nix               machine wiring and inventory, authored in this phase
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
    mode = "fresh-install";          # or "adopt-existing" (SPEC VMOD-016)
    nixos.imports = [ ./nixos/core.nix ./nixos/server.nix ];  # Home Manager runs inside the NixOS role
    disks.newsys  = { byId = "/dev/disk/by-id/nvme-eui.e8238fa6bf530001001b448b4fbe837d"; role = "install-target"; };
    disks.oldsys  = { byId = "/dev/disk/by-id/nvme-NX-512_2280_0040141310300"; role = "keep"; };
  };

  machines.server.target.host = "root@localhost";
}
```

- **nixpkgs:** a plain `github:NixOS/nixpkgs/<rev>` of nixos-unstable for machines and workspaces. A
  shell that uses `devenv-nixpkgs` still fails offline, because that repository fetches its own nixpkgs.
- **Activation:** `devenv machines plan`, `deploy`, `apply`, `status`, `rollback`. Vendomat does not wrap
  them. A failed health check rolls back after `deploy.rollbackTimeout` (agent G).
- **Access:** root accepts the owner's deploy key, key-only. devenv runs as `andrew`, not root.
- **Services:** every service must start cleanly. One failed unit fails the whole deploy, and a unit
  that failed before the deploy makes the rollback fail (`NAT-034`).
- **Home Manager** inside the NixOS role rolls back with the system. A standalone `machines.<host>.home-manager`
  role does not. Mutable user data never rolls back.

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

The patched `devenv machines install` also runs the preflight program itself (`MACH-021`), so a direct
`devenv machines install server` fails without a current, target-bound pass.

**Two guards, so a bypass still fails:**

| Guard | When | Checks |
| --- | --- | --- |
| Module assertions | At build, before disko runs (devenv builds first) | Every disko disk is a `by-id` path with role `install-target`; no mount uses a partition label or a kernel name; no second definition of `machines.<host>.nixos` |
| Preflight | At runtime, on the target, before disko | The `by-id` path resolves; model, serial, and size match; no signature; not the running root or `/boot`; nothing under `/mnt`; a committed facter report |

All of this ran in a QEMU VM with two NVMe disks and persistent NVRAM: the old disk's partition table,
ESP files, and NVRAM entries stayed unchanged, and the new disk booted alone (agents E, F). The real
firmware's handling of NVRAM entries and one-time boot is not yet proven.

## 8. Two machine modes

Each inventory host has one `mode`. It decides the lifecycle, and no module infers it from an empty
disk layout.

| Mode | Host | Disk install | Native commands that run |
| --- | --- | --- | --- |
| `fresh-install` | `server` | Yes, on the `install-target` disk only, after the preflight | `machines install` through `vendomat machine install`, then `plan`, `apply`, `status`, `rollback` |
| `adopt-existing` | `framework` | Never | `info`, `check`, `plan`, `apply`, `deploy <host>`, `status`, `rollback` |

A disk has a role: `install-target` (fresh hosts only), `keep` (a protected disk on either host), or
`existing-system` (the disk that holds an adopted host's root or boot filesystem).

- The patched devenv refuses `machines install` for an adopted host before any SSH contact, for every
  `--phases` selection and every `--disko-mode` (`DVN-009`). The Vendomat wrapper is a second guard.
- The patched devenv refuses `machines install` for a fresh host unless a target-bound preflight has
  just passed (`MACH-021`).
- The first `framework` generation keeps the host's exact nixpkgs revision, Home Manager revision, and
  state versions. It lives in a temporary workspace with its own lock when the pin differs from
  `server`'s (`MACH-018`, `MACH-019`, `MACH-023`).
- Root and a sudo-capable operator can still run `disko` or `nixos-install` by hand. No evaluation
  check stops that. The guards cover the supported patched command.

## Authority

devenv composes, locks, and activates. Nix builds and substitutes. disko partitions. Attic stores.
The collection holds source. Vendomat pins devenv, writes the inputs fragment, ships the module, guards
the disks, and pushes outputs. It owns no durable state.

## Boundaries

Vendomat is not a deployment engine: devenv Machines deploys. It is not a second lock: `devenv.lock` and
`flake.lock` belong to Nix. It is not a workspace orchestrator: each workspace is a plain devenv project
that imports one module.

## Build order

First prove the no-Nix workspace flow. Reuse the input resolver and source collection. Then compose
machines with authored Nix modules and the existing safety plan. A future no-Nix operator flow can
add a machine adapter without changing workspace selection or input resolution.

| Step | Work | Proven so far |
| --- | --- | --- |
| 1 | Put the devenv fork in the collection; build it; push it to Attic | Built and tested in fixtures (agent J) |
| 2 | Prove a workspace user can select two composable modules, inherit their inputs, change a supported value, and enter the shell without Nix edits. Keep generated files under clear ownership | Input resolution and existing module fixtures pass; this user flow is open |
| 3 | `nix-systems`: core, `server` and `framework` deltas, authored NixOS and Home Manager modules, inventory, disko layout; prove it in VMs | Layout and deploy in a VM (agent G) |
| 4 | Install `server` on the 4 TB drive; boot it once; make it the default after it runs reliably | Route proven in a VM (agent F) |
| 5 | Convert workspaces: module, registry, pinned devenv | Pin scan written (agent G) |
| 6 | Adopt `framework` in place with `plan` and `apply`; no disk install (`MACH-014`, `MACH-023`) | Research only; no adoption VM has run |

## Open decisions

1. ~~Where the Vendomat command runs from.~~ Decided 2026-10-09: a host launcher runs the version each
   workspace pins, or the host release outside a workspace (SPEC `DEL-017`).
2. **Module authoring.** Revised 2026-10-10: module authors may write native Nix modules. The
   description builder and required three-target face are superseded as the concept contract.
3. **Machine host settings in TOML** (V5 `SYS-*`, `fromToml`, `vendomat set` and `diff`). Still deferred.
   Workspace user choices in `vendomat.toml` are a separate, narrower need.
4. **Face option paths.** Revised 2026-10-10: no required common path across devenv, NixOS, and
   Home Manager. The workspace user format and bridge need a consumer fixture.
5. ~~Home Manager placement.~~ Decided 2026-10-09: inside the NixOS role (SPEC `MACH-017`, which supersedes `MACH-012`).
6. ~~nixpkgs channel and pin owner.~~ Decided 2026-10-09: plain nixos-unstable; each Vendomat release
   carries one tested revision (SPEC `MACH-018` and `MACH-019`, which supersede `MACH-013` and `MACH-002`).

Decided 2026-10-09 and written into the spec: runtime secrets with sops-nix (`SEC-001`); a
`vendomat bump` fleet command (`CLI-020`).

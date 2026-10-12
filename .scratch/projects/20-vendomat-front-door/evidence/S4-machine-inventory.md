# S4: machine inventory in `vendomat.yaml` and the data form of NixOS and Home Manager values

**Date:** 2026-10-11. **Spike:** S4 of project 20. **Status:** evaluation only. No system was built,
booted, installed, or activated. Every new name below is **proposed** until a fixture on the pinned
tools passes. This file records observations first and inferences second.

## 1. Questions and hypotheses

| ID | Question | Hypothesis |
| --- | --- | --- |
| Q1 | Can `vendomat.yaml` hold the Basix machine inventory as declared options that map to native devenv Machines? | Yes. Key names equal option paths. A small module maps them. |
| Q2 | Does the disk guard survive the move to data? | Yes. A kernel name fails at the type. The V6 guard stays as a backstop. |
| Q3 | Does the adopt guard (fork patch 0005) hold for a data-defined host? | Yes. The CLI reads `machines.<n>.vendomat.mode` and refuses every install phase. |
| Q4 | Which NixOS and Home Manager option types have a safe data form? | Most. A few percent do not. |
| Q5 | Can the Basix inventory plus a core role run from data alone for a typical device? | Yes for a UEFI one-disk device. Some hardware and services need a native module. |
| Q6 | Does project 17 coverage prove machine coverage? | No. |

## 2. Pins and tools

| Item | Value |
| --- | --- |
| Fork CLI | `devenv 2.4.0+fb5d382`, `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv` |
| Fork modules | tag `v2.4.0-vendomat.3`, `src/modules` of `~/.local/state/vendomat/v7/2026-10-11/devenv-v2.4.0-vendomat.3` (`path:` input) |
| Nix | 2.34.7 |
| nixpkgs | `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8` (`nixos-system-*-26.11.20261008.e7439b6`) |
| Home Manager | `6b88c12cc6d234de4888f5d21076fb11199d0844` |
| disko | `de5708739256238fb912c62f03988815db89ec9a` |
| nixos-facter-modules | `139dcef4dfc97009629c445806f197883351ab4a` (resolved at run time; not pinned by nix-systems) |
| Source of the nixpkgs, Home Manager, and disko pins | `nix-systems` `main`, `vendomat.toml`. `main` holds no committed `devenv.lock`, so the pins come from the registry file, not from a lock. |
| Disk guard before heavy runs | `btrfs filesystem usage /`: first check unallocated 6.09 GiB, metadata 84.5%. Last check unallocated 4.09 GiB, metadata 85.6%. Limits (stop at metadata over 90% or unallocated under 2 GiB) were not reached. |

One full-tree NixOS walk grew to 53 GB of memory and I stopped it. The shipped walker runs per
namespace with `ulimit -v 16000000`.

## 3. Task 1: the fork's `machines.<name>.*` option tree

Command (workspace `ws/optdump`, a throwaway module that walks
`options.machines.type.getSubOptions`): `devenv eval env.S4_OPTS`. Raw output:
`~/.local/state/vendomat/p20/2026-10-11/S4/fork-machine-options.raw`.

Fork-only options (patches 0005 and 0006) are marked **F**. Internal and `_module.*` options are
omitted. `build.*` and `installCheck.*` are read-only outputs.

| Path under `machines.<name>` | Type | Data form |
| --- | --- | --- |
| `system` | string | data |
| `target.host` | null or string | data |
| `target.sshOpts` | list of string | data |
| `hardware.facter` | null or (absolute path or string). Default `.machines/<name>/facter.json` | data (path reference) |
| `nixos` | null or unspecified | **none** (module) |
| `home-manager` | null or unspecified | **none** (module) |
| `nix-darwin` | null or unspecified | **none** (module) |
| `deploy.healthCheck` | lines | data (shell text) |
| `deploy.rollbackTimeout` | integer 30 to 600 | data |
| `install.copyHostKeys` | boolean | data |
| `install.encryptionKeys` | attrsOf string | data (run-time paths) |
| `install.extraFiles.<f>.{source,owner,mode}` | attrsOf submodule of strings | data |
| `install.kexec.image` | null or string | data |
| `install.kexec.postSshPort` | null or port | data |
| `install.secrets.<s>.{secret,owner,mode}` | attrsOf submodule of strings | data (names only) |
| `install.secretspec.execution` | enum `local`, `target` | data |
| `install.secretspec.{provider,profile}` | null or string | data |
| `install.secretspec.extraPackages` | functionTo (listOf package) | **none** (function) |
| `vendomat.mode` **F** | null or enum `fresh-install`, `adopt-existing` | data |
| `vendomat.preflight.program` **F** | null or package | derived (built by the module) |
| `vendomat.preflight.ttlSeconds` **F** | integer 1 to 900 | data |
| `build.{nixos,deployer,diskoScript,diskoFormatScript,diskoMountScript,home-manager,nix-darwin,vendomatPreflight}` | output | read-only |
| `installCheck.{diskoDevices,hasRootAuth}` | list of string, boolean | read-only |

**Observation.** The native tree has no disk field. Disk identity lives in disko (`disko.devices`)
inside `machines.<n>.nixos`. The V6 module (`nix/devenv-module/default.nix`) adds
`vendomat.inventory.<host>.{mode,disks,nixos}`. The fresh-install flow needs both.

## 4. Task 2: the fixture and the guard runs

### 4.1 Fixture (non-production)

`.scratch/projects/20-vendomat-front-door/evidence/fixtures/s4-inventory/`

| File | Role |
| --- | --- |
| `devenv.nix` | Generic data reader: `config = removeAttrs (fromJSON ./.vendomat/config.json) ["inputs" "imports"]`. A top-level key is an option path. No translation table. |
| `basix-machines.nix` | Declares `options.basix.machines`. Maps each host to `vendomat.inventory.<h>` (existing guard) and `machines.<h>` (native). Builds the core-role NixOS module from data. |
| `devenv.yaml` | Fork modules, nixpkgs, disko, nixos-facter-modules at the pins above. |
| `devenv.local.nix` | Read-only probe: `devenv eval env.S4_PROBE`. |
| `cases/*.json` | 14 simulated `.vendomat/config.json` files. JSON allows no comment, so these carry no header. |
| `tools/` | The type walker, `jq` filters, and run scripts. |

`tools/mkws.sh` copies `nix/devenv-module/` and `preflight/` from the repository into a disposable
workspace under `~/.local/state/vendomat/p20/2026-10-11/S4/ws/<case>/`. It writes the case as
`.vendomat/config.json`. It uses the upstream sample report
`nixos-facter-modules/hosts/basic/report.json` as the test facter report.

Host names in the cases are `box` (fresh install) and `laptop` (adopt). Ids and keys are examples.

### 4.2 Commands and results

All evaluation uses the fork CLI: `devenv eval machines.<h>.build.nixos` (forces the toplevel
`.drv` and the assertions; builds nothing) unless noted. Logs: `S4/logs/<case>.{out,err,rc}`.

| # | Case | Expected | Actual |
| --- | --- | --- | --- |
| V1 | `valid` (box fresh-install, laptop adopt-existing) | Both evaluate | rc 0. `box` `/nix/store/yrzzns3093dyqz7x7a7li5c0pn63c05n-nixos-system-box-26.11.20261008.e7439b6`. `laptop` `/nix/store/bylwj34pkaak76lhnsblxazwfj8xv70x-nixos-system-laptop-26.11.20261008.e7439b6`. Log `valid-final.out`. |
| V2 | probe of V1 | Data reaches native options | `box`: mode `fresh-install`, preflight program `.drv` present, disko device `/dev/disk/by-id/nvme-EXAMPLE-NEW-0001`, `installCheck.diskoDevices` the same single path, root and boot mounted by derived `/dev/disk/by-uuid/...`, swap by uuid, `failedAssertions` empty, facter report resolved to `.machines/box/facter.json`, firmware flag true (from the referenced `not-detected.nix`). `laptop`: mode `adopt-existing`, preflight program null, no disko disk, root `/dev/disk/by-uuid/11111111-...`, firmware flag false. `machines info` lists both. |
| E1 | `rawname-nvme`: `byId = "/dev/nvme0n1"` | Reject | `error: A definition for option \`basix.machines.box.disks.newsys.byId' is not of type \`an absolute /dev/disk/by-id/<id> path (never a kernel name such as /dev/sda or /dev/nvme0n1)'. Definition values: - In \`.../ws/rawname-nvme/devenv.nix': "/dev/nvme0n1"` |
| E2 | `rawname-sda`: `byId = "/dev/sda"` | Reject | Same message, value `"/dev/sda"`. |
| E3 | `missing-byid`: disk entry without `byId` | Fail | `error: The option \`basix.machines.box.disks.newsys.byId' was accessed but has no value defined. Try setting the option.` |
| E4 | `fs-kernel-name`: adopted `/` device `/dev/sda2` | Reject | `... \`basix.machines.laptop.filesystems."/".device' is not of type \`string matching the pattern /dev/disk/by-(uuid\|partuuid)/[A-Za-z0-9-]+'.` |
| E5 | `bad-mode`: `mode = "adopt"` | Reject | `... \`basix.machines.laptop.mode' is not of type \`one of "fresh-install", "adopt-existing"'.` |
| E6 | `missing-stateversion` | Fail | `The option \`basix.machines.box.stateVersion' was accessed but has no value defined.` |
| E7 | `bypass-guard-kernel-name`: native `vendomat.inventory.raw` with `/dev/sda`, no `basix` data | V6 guard fires | `Failed assertions: - vendomat guard (raw): inventory disks must be /dev/disk/by-id/ paths: t.` (plus two unrelated core assertions) |
| E8 | `adopt-with-target`: adopted disk with role `install-target` | Guard fires | `- vendomat guard (laptop): an adopt-existing host cannot have an install-target disk: system.` and `... needs a disk with role "existing-system" ...` |
| E9 | `target-equals-keep`: install target equals a `keep` disk | Guard fires | `- vendomat guard (box): an install-target has the same by-id path as a keep or existing-system disk: /dev/disk/by-id/nvme-EXAMPLE-OLD-0002.` |
| E10 | `unknown-input`: module reference to an undeclared input | Clear error | `error: basix.machines.box.hardware.modules: input "nixos-hardware" is not declared in devenv.yaml` (first run, before the fix: `attribute 'nixos-hardware' missing`). |
| E11 | `report-dotdot`: `hardware.report = "../outside/facter.json"` | Reject | `... \`basix.machines.box.hardware.report' is not of type \`null or a relative path without ..'.` |
| E12 | `report-missing`: report file absent | Fail | `error: path '.../ws/report-missing/.machines/box/missing.json' does not exist` |
| L1 | `lazy-noforce`: malformed `target.host`, forcing assertion removed | (test of laziness) | **rc 0**. The bad value passes `build.nixos`. Same store path as V1. |
| L2 | `lazy-bad-target`: same value, forcing assertion present | Reject | `... \`basix.machines.box.target.host' is not of type \`null or string matching the pattern [a-z_][a-z0-9_-]*@[A-Za-z0-9._-]+(:[0-9]+)?'.` |
| N1 | `native-ext`: native `vendomat.inventory.box.nixos = { services.tailscale.enable = true; ... }` | Merges with the data module | rc 0. `{"hostName":"box","ports":[22,9418],"tailscale":true}` |
| N2 | `native-conflict`: native `networking.hostName = "other"` | Conflict stops | `The option \`networking.hostName' has conflicting definition values: - In \`.../ext.nix, via option vendomat.inventory.box.nixos': "other" - In \`.../basix-machines.nix, via option vendomat.inventory.box.nixos': "box"  Use \`lib.mkForce value\` or \`lib.mkDefault value\`...` |
| N3 | `native-force`: `mkForce "forced"` | Native wins | rc 0. `"forced"` |

### 4.3 Adopt guard and fresh default phases (fork patches 0005 and 0006)

Workspace `ws/valid`. `PATH` starts with a mock `ssh`, `nix`, `nix-store`, and `nixos-install`.
Each mock appends to `ssh.log` and exits 98. Logs: `S4/logs/cli-*.{err,rc}`.

| Command | Expected | Actual |
| --- | --- | --- |
| `devenv machines install laptop` | Refuse, no contact | rc 1. `Refusing to install: machines.laptop set \`vendomat.mode = "adopt-existing"\`. An adopted machine already runs a system, and \`devenv machines install\` can erase its disks or rewrite its boot files. devenv made no connection to the target. Use \`devenv machines plan\`, \`apply\`, or \`deploy\` for an adopted machine.` |
| `... laptop --phases disko,install` | Refuse | rc 1, same text |
| `... laptop --stop-after-disko` | Refuse | rc 1, same text |
| `... laptop --disko-mode format` | Refuse | rc 1, same text |
| `... laptop --phases disko,install --stop-after-disko` | n/a | rc 2: clap rejects the flag pair (not the policy) |
| `devenv machines install box` (fresh-install, default phases) | Refuse (0006) | rc 1. `... the phase set (kexec,facter,disko,install,reboot) joins kexec or reboot with disko or install, or is empty. ... use \`--phases disko,install\`. devenv made no connection to the target.` |
| `ssh.log` after all runs | Empty | Empty. No mock was called. |

I did not run `devenv machines install box --phases disko,install`. It would build the system and
contact the target. Patch 0006 behavior on that path stays on the project 16 record (Step 7, G7, in
QEMU).

## 5. Task 3: option type audit

### 5.1 Method

`tools/audit.nix` walks the `options` tree of a NixOS evaluation (`eval-config.nix`, nixpkgs pin
above) and of Home Manager (`modules/default.nix`, `check = false`, Home Manager pin above). It
descends into `getSubOptions` (the `<name>` placeholder stands for an attribute key). It classifies
the **type** of every option, recursing through `nestedTypes` (depth limit 4 for recursive JSON
types):

| Class | Types |
| --- | --- |
| `data` | bool, int and `ints.*`, float, str and its variants, `strMatching`, lines, `separatedString`, enum, port, and `nullOr`, `listOf`, `attrsOf`, `either`, `coercedTo`, `uniq` of data. Submodules and freeform submodules of data. |
| `reference` | `package` (a string names a nixpkgs attribute, DOOR-004), `path` (a string), `shellPackage`, `secret<absolutePath>`, and wrappers of them |
| `untyped` | `unspecified`, `anything`, `raw`, `attrs` (arbitrary values; JSON may carry them but nothing checks them) |
| `nodata` | `functionTo`, `deferredModule`, `optionType`, `pkgs`, overlay and nixpkgs-config types, `Toplevel NixOS config` |

Counts use **leaf** options (a submodule container is not counted; its children are). "Settable"
means not `internal`, not `readOnly`, and `visible` not false. The settable count drops removed
and renamed option stubs. Skipped on purpose: `_module`, `specialisation`, `specialization`,
`vmVariant`, `vmVariantWithBootLoader` (each embeds a whole system and recurses). Walk depth limit 7.
Services are walked in chunks of 60.

The raw rows are in `S4/nixos-entries.json` (29021 rows) and `S4/hm-entries.json` (6495 rows). The
summaries are `S4/nixos-stats.json` and `S4/hm-stats.json`.

### 5.2 Counts

| Tree | Leaf options | data | reference | untyped | nodata |
| --- | --- | --- | --- | --- | --- |
| NixOS, all | 26903 | 21039 (78.2%) | 4441 (16.5%) | 1375 (5.1%) | 48 (0.2%) |
| NixOS, settable | 25093 | 20522 (81.8%) | 4201 (16.7%) | 323 (1.3%) | 47 (0.2%) |
| Home Manager, all | 5896 | 4147 (70.3%) | 1486 (25.2%) | 232 (3.9%) | 31 (0.5%) |
| Home Manager, settable | 5319 | 3825 (71.9%) | 1371 (25.8%) | 92 (1.7%) | 31 (0.6%) |

Containers (submodules) walked: NixOS 2118, Home Manager 599.

Cause of the settable `untyped` and `nodata` options:

| Cause | NixOS | Home Manager |
| --- | --- | --- |
| `attrs` (untyped attribute set) | 180 | 20 |
| `unspecified` | 65 | 7 |
| `anything` | 57 | 24 |
| `raw` | 19 | 36 |
| function types | 28 | 15 |
| `deferredModule` | 15 | 14 |
| module, config, overlay | 3 | 2 |
| other | 2 (`attrTag` tags with no name) | 4 (percent and yubikey list types, overlay and selector functions) |

Of the 1375 untyped options in NixOS, 1052 are not settable: removed and renamed option stubs
with type `unspecified` and `visible = false`. A user cannot set them, so they do not count.

disko (`module.nix` at the pin) adds 149 leaf options: 103 data, 18 reference, 21 untyped, 7 nodata.
The untyped and nodata ones are `_config`, `_meta`, `_pkgs`, `_scripts`, `_parent`, and the
`absolutePath` type name that my map did not know (a path string). `nixos-facter-modules` adds 24
leaf options: 20 data, 3 reference, 1 untyped (`facter.report`, `attrsOf anything`).

### 5.3 Machine-critical NixOS options

Counts are leaf options under the prefix: data / reference / untyped / nodata.

| Prefix | Leaves | d / r / u / n | Type of the option itself, and notes |
| --- | --- | --- | --- |
| `boot.loader` | 145 | 124 / 14 / 7 / 0 | `systemd-boot.enable` and `efi.canTouchEfiVariables` are `bool`. Untyped: `grub.bootDevice`, `grub.extraInitrd`, `grub.trustedBoot`, `raspberryPi`, `systemd-boot.installDeviceTree`, two `entryFilename`. |
| `boot.loader.systemd-boot` | 25 | 21 / 1 / 3 / 0 | `extraFiles` is `attrsOf path`. |
| `boot.loader.grub` | 54 | 45 / 6 / 3 / 0 | `theme`, `font`, `splashImage` are paths. |
| `fileSystems` | 21 | 19 / 1 / 1 / 0 | `attrsOf submodule`. Untyped: `formatOptions` (removed stub). `device`, `fsType`, `options` are data. |
| `swapDevices` | 20 | 18 / 1 / 1 / 0 | `listOf submodule`. |
| `boot.initrd.availableKernelModules` | 1 | 1 / 0 / 0 / 0 | `coercedTo (listOf str) (attrsOf bool)`. |
| `boot.kernelModules` | 1 | 1 / 0 / 0 / 0 | same |
| `boot.initrd.luks` | 41 | 37 / 3 / 1 / 0 | `devices.<n>.device` is a data string. Not exercised here. |
| `boot.kernelParams` | 1 | 1 / 0 / 0 / 0 | `listOf kernelParam` |
| `hardware` | 385 | 319 / 52 / 14 / 0 | `enableRedistributableFirmware` is `bool`. `hardware.facter.reportPath` is `nullOr path`. `hardware.facter.report` is `attrsOf anything`. `hardware.firmware` is `listOf package`. |
| `networking.hostName` | 1 | 1 / 0 / 0 / 0 | `strMatching` |
| `networking.interfaces` | 37 | 30 / 0 / 7 / 0 | The 7 untyped are removed stubs. |
| `networking.firewall` | 33 | 31 / 2 / 0 / 0 | |
| `networking.networkmanager` | 40 | 27 / 7 / 6 / 0 | |
| `networking.wireless` | 29 | 22 / 4 / 3 / 0 | `environmentFile` and secrets are run-time paths. |
| `networking` (all) | 404 | 351 / 32 / 21 / 0 | |
| `users.users` | 33 | 29 / 4 / 0 / 0 | `attrsOf submodule`. `shell`, `packages`, `home` are references. |
| `services.openssh` | 45 | 39 / 4 / 2 / 0 | `settings` is a freeform submodule of data. Untyped: `banner`, `hostKeys` (`listOf attrs`). |
| `nix.settings` | 13 | 13 / 0 / 0 / 0 | freeform submodule of JSON values |
| `system.stateVersion` | 1 | 1 / 0 / 0 / 0 | `str` |
| `nixpkgs.hostPlatform` | 1 | 0 / 0 / 1 / 0 | `either str attrs`. A string such as `"x86_64-linux"` works. |
| `environment.systemPackages` | 1 | 0 / 1 / 0 / 0 | `listOf package` |
| `services.tailscale` | 28 | 24 / 4 / 0 / 0 | |
| `services.harmonia` | 26 | 19 / 7 / 0 / 0 | the signing key option is a run-time path |
| `imports` | not an option | none | The module system reads `imports`. It is absent from the option tree. A hardware module from a flake input (for example from `nixos-hardware`) has **no data form** as a value. |

Result: no machine-critical option above has class `nodata`. The only machine-relevant value with no
data form is `imports` (a module reference) and the function-typed options in 5.2.

**Limit of this audit.** The class says that a plain value fits the type. It does not say that a
plain value is enough. A `str` option such as `systemd.services.<n>.serviceConfig.ExecStart` usually
needs `"${pkgs.x}/bin/y"`. That value carries a store path and a string context, and the data format
cannot express it. Priorities (`mkIf`, `mkForce`, `mkDefault`) and values computed from `config` also
have no data form. Treat the counts as an upper bound on data coverage.

### 5.4 Home Manager (not blocked)

Home Manager at the pin evaluated. Counts are in 5.2. Selected options:

| Prefix | Leaves | d / r / u / n | Notes |
| --- | --- | --- | --- |
| `home.username` | 1 | 1 / 0 / 0 / 0 | `nonEmptyStr` |
| `home.homeDirectory` | 1 | 0 / 1 / 0 / 0 | `path` |
| `home.stateVersion` | 1 | 1 / 0 / 0 / 0 | `enum` |
| `home.packages` | 1 | 0 / 1 / 0 / 0 | `listOf package` |
| `home.file` | 9 | 8 / 1 / 0 / 0 | |
| `programs.git` | 41 | 30 / 8 / 3 / 0 | |
| `programs.zsh` | 119 | 107 / 11 / 1 / 0 | |
| `programs.ssh` | 46 | 43 / 2 / 1 / 0 | |
| `programs.neovim` | 29 | 21 / 6 / 0 / 2 | `extraLuaPackages` and `extraPython3Packages` are functions |
| `xdg` | 98 | 65 / 30 / 3 / 0 | |
| `systemd.user` | 30 | 24 / 6 / 0 / 0 | |
| `nixpkgs` | 3 | 1 / 0 / 2 / 0 | `config` and `overlays` |

## 6. Task 4: can data alone run a typical device?

**Observation.** V1 and V2 show that data alone defines a complete evaluable core role for two
devices: a UEFI one-disk fresh install (systemd-boot, ext4, optional swap, derived ids) and an
adopted host with explicit UUID mounts and module lists. The role has host name, state version, SSH
(key-only, public keys), users, time zone, hardware report path, and a by-reference hardware module.
Both evaluate to a NixOS toplevel on the pins. No system was built or booted.

**Data path for a hardware report: yes.** `machines.<n>.hardware.facter` takes a string path
relative to the project root (default `.machines/<name>/facter.json`). V2 resolved
`.machines/box/facter.json` to the file and evaluated with `nixos-facter-modules` 139dcef. The
report was the upstream sample, not a report of real hardware. A missing file fails at once with
the path (E12). At the nixpkgs pin, `hardware.facter.reportPath` (`nullOr path`) also exists;
I did not evaluate that route. The fork's route needs the `nixos-facter-modules` input; the
nixpkgs route would not.

**What must stay native or needs a new reference form:**

| Need | Why | Data route found |
| --- | --- | --- |
| Module from a flake input (nixos-hardware, a service module) | `imports` has no data form | `{input, path}` reference resolved to `"${inputs.<input>}/<path>"`. Proved with `nixpkgs` and `nixos/modules/installer/scan/not-detected.nix` (effect visible in the probe). Not proved with `nixos-hardware`: not an input of this fixture. |
| `hardware-configuration.nix` | A Nix module; imports use `modulesPath` | Replace it with the report path, or list kernel modules and mounts as data (laptop case). A tool could convert the simple attributes; not tried. |
| Encrypted root, RAID, btrfs subvolumes, other disk layouts | The fixture presets one layout | Native disko in `devenv.nix` (N1 shows a native module merges). `boot.initrd.luks.devices` is data-typed, but no fixture ran it. |
| Services with secrets (Harmonia key, Tailscale key) | A path to a run-time file, or SecretSpec | Declare the path as data; delivery stays outside the data (DOOR-014). Not exercised. |
| Values with store paths, `mkIf`, `mkForce`, `config` references, overlays, functions | No data form | Native `devenv.nix` (N1, N3). |
| Real firmware, real disks, real boot | Out of scope for evaluation | Project 20 gates 6 to 10. |

**Observations on the data-to-native boundary:**

1. Native and data definitions of the same scalar conflict (N2). The message lists both locations,
   but the data location is the Nix module (`basix-machines.nix`), not a line of `vendomat.yaml`.
   To let a native module override without `mkForce`, the generated module would need `mkDefault`.
   That choice is not made here (DOOR-013).
2. Type checks are lazy (L1). A malformed value in an option that nothing reads passes
   `devenv eval machines.<h>.build.nixos`. The fixture forces each machine record with
   `builtins.toJSON` inside a NixOS assertion (L2). The front door needs an explicit
   "force every declared option" step, or it needs its own schema check, before it reports valid.
3. Evaluation errors name the option path and the value. They name the reader file, not the YAML
   line. The pre-Nix linter (DOOR-012) must own file and line.
4. The V6 guard refuses `by-partlabel` mounts. disko writes them by default. A fresh install
   therefore needs preset partition and filesystem ids. The fixture derives them from
   `sha256("<host>/<disk>/<part>")`, so the user supplies none. The derivation formula is a choice
   and is not proved against a real `mkfs`.
5. `machines.<n>.hardware.facter` defaults to a path, not to `null`. A host without a report must
   say `null` (the fixture's `report = null` does this).
6. NixOS `fileSystems.<m>.options` has a non-empty default `["defaults"]`. A data `[]` fails
   (`non-empty (list of string)`). A mapping module must keep the native default.
7. A custom `mkOptionType` (`diskById`) gives the best message but has an unknown type name. A
   schema generator (project 17) would map an unknown name to `NixExpr`. `types.strMatching "/dev/disk/by-id/.+"`
   keeps a schema pattern at the cost of a plainer message. Extra checks added with `addCheck`
   (the `..` ban in `relPath`) are invisible to such a schema.

**Verdict.** Yes for the narrow case: a UEFI device, one install disk or an adopted system with known
UUID mounts, standard NixOS hardware support (through a facter report or listed modules). No for
anything that needs a module from outside nixpkgs without a reference, a non-preset disk layout, or
computed values. Those use a native module next to the data.

## 7. Task 5: project 17 coverage is not machine coverage

Project 17 (`.scratch/projects/17-devenv-model-layer/CONCEPT.md`) proves model generation for five
devenv subtrees: `languages.python`, `services.postgres`, `services.redis`,
`languages.javascript`, `languages.rust` (gates GM9, GM10). The gap:

1. The export reads `devenv.project.options`. At the project 17 pin it holds 1330 records. In that
   tree `machines.<n>.nixos`, `home-manager`, and `nix-darwin` are `unspecified` (section 3). The
   NixOS options live in a separate `evalModules` inside `machines.<n>._nixosEval`, which depends on
   the machine's modules, disko, and the facter input. That export does not exist.
2. This spike walked 26903 NixOS and 5896 Home Manager leaf options. The devenv export is about
   twenty times smaller than the NixOS tree alone.
3. Project 17 lists "the same pipeline for NixOS and Home Manager option trees, for Machines" as an
   opportunity, not as a result. No gate runs it.
4. The project 17 oracle reads only the options that a fixture mentions. L1 shows why this matters
   for machines: unread options pass.
5. Disk safety, the V6 guard, fork patches 0005 and 0006, and the preflight are outside every GM
   gate. A model that accepts `/dev/sda` is a project 17 "opportunity", not a result.
6. Project 17 maps an unknown type name to `NixExpr` (a coverage miss). The machine-critical custom
   types of this spike would count as misses unless built from `strMatching` and `enum`.

## 8. Proves, inference, unproved

**Proved (observed on the pins).**

- A JSON file with the key path `basix.machines.<n>...` defines declared options with no
  translation table (V1).
- Both modes evaluate to a NixOS toplevel `.drv` through native `machines.<h>` and
  `vendomat.inventory.<h>` (V1, V2).
- A kernel name in `disks.*.byId` fails at the data layer (E1, E2); in a native inventory it fails at
  the V6 guard (E7). A kernel name in an adopted mount fails (E4). A missing `byId` fails (E3).
- The adopt guard refuses `machines install` for four flag shapes with no SSH, build, or store call
  (section 4.3). The fresh-install default phase set is refused.
- A hardware report path and a `{input,path}` module reference evaluate (V2).
- A native module merges with the data module (N1). A conflicting scalar stops with both locations
  (N2). `mkForce` wins (N3).
- Type checks are lazy (L1) and one forcing assertion fixes it for a machine record (L2).
- Type audit counts for NixOS and Home Manager at the pins (section 5).

**Inference (not run).**

- The fresh path works end to end (`--phases facter`, then `--phases disko,install`): follows from the
  project 16 Step 7 VM record and the patch text.
- Stock devenv on `PATH` does not enforce the adopt guard: the stock CLI reads no `vendomat`
  metadata. I did not run it, because it would start a build.
- Home Manager data would map the same way; I audited types only.
- The nixpkgs-native `hardware.facter.reportPath` works without the extra input.

**Unproved.**

- Any build, boot, install, activation, or secret delivery. The report used a sample, not a real
  device report. `nixos-hardware` was not an input. LUKS, RAID, and btrfs were not exercised.
- The derived partition and filesystem ids against a real `mkfs`, `sgdisk`, and boot.
- A real adopted host (the framework laptop). Its disk, mounts, and unlock path stay unrecorded.
- The first-boot keyless access path of the core role (DOOR-016). The fixture has public SSH keys only.
- A reader for `vendomat.yaml` itself. I used JSON.

## 9. Proposed inventory schema (PROPOSED, fixture-proved only as stated)

Option declarations are in `fixtures/s4-inventory/basix-machines.nix`. Excerpt of the shape:

```nix
options.basix.machines = attrsOf (submodule ({ name, ... }: { options = {
  mode         = enum [ "fresh-install" "adopt-existing" ];     # same values as the fork
  system       = enum [ "x86_64-linux" "aarch64-linux" ];       # default x86_64-linux
  hostName     = strMatching "[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?";  # default: the key
  stateVersion = strMatching "[0-9]{2}\\.(05|11)";              # required, no default
  target.host  = nullOr (strMatching "[a-z_][a-z0-9_-]*@[A-Za-z0-9._-]+(:[0-9]+)?");
  disks.<id> = { byId = diskById; role = enum [ "install-target" "keep" "existing-system" ];
                 model = nullOr str; serial = nullOr str; sizeBytes = nullOr positiveInt; };
  layout.swapSize = nullOr (strMatching "[0-9]+[MG]");          # fresh-install only
  filesystems.<mount> = { device = strMatching "/dev/disk/by-(uuid|partuuid)/..."; fsType = str;
                          options = listOf str; };              # adopt-existing only
  boot.loader  = enum [ "systemd-boot" ];
  hardware = { report = nullOr relativePath; initrdModules = listOf str; kernelModules = listOf str;
               modules = listOf { input = str; path = relativePath; }; };
  users.<name> = { admin = bool; authorizedKeys = listOf str; };  # public keys only
  timeZone     = nullOr str;
}; }));
```

YAML form (what the user writes; the fixture feeds the same data as JSON):

```yaml
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
          model: "Example SSD 1TB"
          serial: "EX0001"
          sizeBytes: 1000204886016
        oldsys:
          byId: "/dev/disk/by-id/nvme-EXAMPLE-OLD-0002"
          role: "keep"
      layout:
        swapSize: "8G"
      hardware:
        report: ".machines/box/facter.json"
        modules:
          - input: "nixpkgs"
            path: "nixos/modules/installer/scan/not-detected.nix"
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
        "/boot":
          device: "/dev/disk/by-uuid/ABCD-1234"
          fsType: "vfat"
      hardware:
        initrdModules: ["xhci_pci", "nvme", "usb_storage", "sd_mod"]
        kernelModules: ["kvm-amd"]
```

Rules the schema keeps:

1. The enum values equal the fork's `vendomat.mode` values. No translation.
2. No field holds a secret. `users.*.authorizedKeys` holds public keys. The linter rejects private key text.
3. The generated NixOS module and the V6 guard stay the only writers of `vendomat.inventory.<h>.nixos`
   for generated parts. A user adds native parts to the same option; they merge.
4. A pre-Nix check and the Nix type check both exist. Nix stays the authority.
5. The fixture names `server` and `framework` nowhere.

## 10. `NEW:` claims (no ID allocated)

- NEW: A data inventory declared as `options.basix.machines` can drive `vendomat.inventory.<h>` and
  `machines.<h>` for a fresh-install and an adopt-existing host, with the V6 guard intact (V1, V2, E7 to E9).
- NEW: A kernel disk name in the inventory fails at evaluation with the option path and value (E1, E2).
- NEW: Nix option type checks are lazy, so "valid" needs an explicit force of every declared option
  before the front door reports success (L1, L2).
- NEW: An evaluation error names the option path and the generic reader file, never the YAML line.
  The linter must carry file and line.
- NEW: Native `machines.<n>.hardware.facter` accepts a project-relative path string. A missing
  file fails with the path (E12).
- NEW: A module in a flake input can be named as `{input, path}` data and resolved to an import.
- NEW: A fresh install under the V6 guard needs preset by-uuid mounts. The inventory can derive the
  ids from host, disk, and partition names.
- NEW: NixOS at the pin has 26903 leaf options; 98.5% of the 25093 settable ones have a data or
  reference type. 47 have no data form. Home Manager: 5896 leaf options, 5319 settable, 31 with none.
- NEW: `imports` is not an option. A module value has no data form.
- NEW: A custom option type name is unknown to a schema generator; `strMatching` and `enum` are not.

## 11. Concept changes (proposed)

1. CONCEPT section 3: replace the single-disk example. Add `stateVersion`, `layout`, `filesystems`,
   `hardware`, and `users`. Keep `mode` values `fresh-install` and `adopt-existing`.
2. CONCEPT section 4, step 3: "validate the data values" must say that Vendomat forces every declared
   option (a `deepSeq` or an assertion over the record) before it reports valid. Add the lazy-check finding.
3. CONCEPT section 3 and DOOR-012: state that an evaluation error gives an option path, not a line.
   File and line come from the pre-Nix linter.
4. CONCEPT section 6: add a data route for a hardware report (`hardware.report`) and for a module from an
   input (`hardware.modules`). State that `imports` and function values need native Nix.
5. DOOR-013: record that data and native scalar definitions conflict by default (N2). Decide whether
   generated values use `mkDefault`.
6. DOOR-015: say that the disk guard has two layers, the data type and the V6 guard assertions. Keep both.
7. Project 17 gap: add a machine option export (NixOS and Home Manager) as new work. Do not cite GM9 or GM10
   as machine coverage.
8. Add a rule for option authors: build a schema-visible type from `strMatching` or `enum`, not from a bare `mkOptionType`.

## 12. Files and logs

| Item | Path |
| --- | --- |
| Fixture | `.scratch/projects/20-vendomat-front-door/evidence/fixtures/s4-inventory/` |
| Logs, runs, raw rows | `~/.local/state/vendomat/p20/2026-10-11/S4/` (`logs/`, `logs-r1/` first run, `nixos-entries.json`, `hm-entries.json`, `nixos-stats.json`, `hm-stats.json`, `critical/`, `fork-machine-options.raw`, `fork-options-table.md`, `probe-valid-final.json`, `eval-valid.out`, `ws/<case>/`) |
| Walker scripts | `.../S4/scripts/` (copies in the fixture `tools/`) |

Run-time notes: the first valid run passed while `target.host` had a malformed pattern. The probe
then failed on it, which is how I found the laziness. First-run logs of `unknown-input` are in `logs-r1/`.

Process note: I ran `jj log -r @` once to read the workspace state. It may snapshot the working copy of
`p20-research`. No other `jj` or `git` command ran, and I changed no repository outside the two paths
named in the task.

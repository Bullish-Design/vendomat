# Vendomat V5 implementation guide

**Date:** 2026-10-07. **Status:** Superseded for server bootstrap. Do not execute this guide. **Authority:** [SPEC-V5.md](./SPEC-V5.md) is
normative. [CONCEPT-V5.md](./CONCEPT-V5.md) holds the shape. This file holds the commands.

## How to use this guide

Each step states its goal, the requirement IDs it satisfies, the files to write, the commands to
run, how to verify, how to undo, and when to stop.

- **Stop if** names the one condition that must not be carried into the next step.
- Open one Gitman lane per step. Never run raw `git` or `jj`.
- `sudo` is at `/run/wrappers/bin/sudo`. The copy first on `PATH` is not setuid.
- **All work happens on `server`.** No step before 10 may depend on the laptop (`BOOT-018`, `BOOT-020`).
- Steps 1 to 7 need no Python. Do not start step 8 before step 7 passes.
- Record each step's date, commands, and result. Keep raw logs in
  `~/.local/state/vendomat/v5/<date>/`.

## Fleet and pins

| Item | Value |
| --- | --- |
| `server` | Dell Precision 5820, headless, `x86_64-linux`. Runs `atticd` and the builder |
| Laptop | `framework`, `x86_64-linux`. Installed last, in step 10. Unreachable as of 2026-10-07 |
| Nix | 2.34.7 |
| devenv | 2.4.0+b904dcb |
| Attic | server and client `attic-0-unstable-2026-06-26` |
| Cache | `vendomat`, private, priority 20, retention 0 |
| Cache key | `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=` |
| Attic listen | `127.0.0.1:8089`, published by Tailscale Serve at `/attic` |

---

# Step 0 — drive identity preflight

**Goal:** prove every declared drive identity resolves, and prove the target is safe, **without
writing to any disk.** **IDs:** `DISK-001` to `DISK-005`.

**History.** The original Step 0 partitioned `/dev/nvme0n1`. On 2026-10-08 that kernel name belongs
to the running 512 GB system. Its commands are withdrawn.
[The storage refinement](./REFINEMENT-2026-10-08.md) holds the rule: identify hardware by a stable
identifier, never by a kernel-assigned name.

## 0.1 The declared inventory

| Logical name | Hardware identifier | Expected filesystem UUID |
| --- | --- | --- |
| `new-system` (WD Blue SN5100 4 TB) | `nvme-eui.e8238fa6bf530001001b448b4fbe837d` | none yet |
| `previous-system` (NX-512 512 GB) | `nvme-NX-512_2280_0040141310300` | root `e6b180fa-534a-4b71-aff8-f9fe2e6d0834`, EFI `0086-EC69` |
| `backup` (WD Green, Attic and restic) | `wwn-0x50014ee2adca73d5` | `21488349-01cb-4efe-9d21-a72f74a908e0` |
| `shared` (TEAM SSD) | `ata-TEAM_TM8PS7002T_TPBF2308070030300443` | `C24C954D4C953CDB` |

## 0.2 The preflight

Read-only. It writes nothing and needs no root.

```sh
#!/bin/sh
# Resolve each declared identity and refuse an unsafe target. Writes nothing.
set -u
TARGET_ID=nvme-eui.e8238fa6bf530001001b448b4fbe837d
fail=0

# Every declared identity must resolve.
for id in nvme-eui.e8238fa6bf530001001b448b4fbe837d \
          nvme-NX-512_2280_0040141310300 \
          wwn-0x50014ee2adca73d5 \
          ata-TEAM_TM8PS7002T_TPBF2308070030300443; do
  dev=$(readlink -f "/dev/disk/by-id/$id" 2>/dev/null) || dev=
  [ -b "$dev" ] || { echo "FAIL missing identity: $id"; fail=1; continue; }
  printf 'ok   %s -> %s (%s, %s)\n' "$id" "$dev" \
    "$(lsblk -dno MODEL "$dev")" "$(lsblk -dno SIZE "$dev")"
done

# Every declared filesystem UUID must resolve.
for uuid in e6b180fa-534a-4b71-aff8-f9fe2e6d0834 0086-EC69 \
            21488349-01cb-4efe-9d21-a72f74a908e0 C24C954D4C953CDB; do
  [ -e "/dev/disk/by-uuid/$uuid" ] \
    && echo "ok   uuid $uuid -> $(readlink -f /dev/disk/by-uuid/$uuid)" \
    || { echo "FAIL missing uuid: $uuid"; fail=1; }
done

target=$(readlink -f "/dev/disk/by-id/$TARGET_ID")
tname=${target#/dev/}

# The target must not back the running root or boot filesystem (DISK-002).
for mp in / /boot /nix /home; do
  src=$(findmnt -n -o SOURCE "$mp" 2>/dev/null | sed 's/\[.*//') || continue
  [ -n "$src" ] || continue
  disk=$(lsblk -no PKNAME "$src" 2>/dev/null | head -1)
  [ "$disk" = "$tname" ] && { echo "FAIL target $tname backs $mp"; fail=1; }
done

# The target must carry no partition table, signature, or mount (DISK-003).
[ -n "$(lsblk -no FSTYPE,PARTTYPE "$target" | tr -d ' \n')" ] \
  && { echo "FAIL target $tname has a filesystem or partition table"; fail=1; } \
  || echo "ok   target $tname is bare"
[ -n "$(lsblk -no MOUNTPOINTS "$target" | tr -d ' \n')" ] \
  && { echo "FAIL target $tname has a mount"; fail=1; } \
  || echo "ok   target $tname has no mount"

[ "$fail" = 0 ] && echo "PREFLIGHT PASS" || { echo "PREFLIGHT FAIL"; exit 1; }
```

**Verify:** every line reports `ok` and the script prints `PREFLIGHT PASS`. Observed on
2026-10-08: all four identities and all four UUIDs resolve, the target is `/dev/nvme1n1`, and it is
bare.

**Verify `DISK-002` deliberately:** set `TARGET_ID=nvme-NX-512_2280_0040141310300` and run again.
It must fail, naming the mount point the target backs. Restore the correct value afterwards.

**Verify `DISK-003`:** set `TARGET_ID` to the WD Green identifier. It must fail on the existing
filesystem.

**Stop if:** any identity fails to resolve, or the target reports a filesystem, partition table, or
mount. Nothing in step 7 may run before this passes.

---

# Step 1 — the machine core

**Goal:** one module both machines share. **IDs:** `BOOT-001`, `BOOT-003`, `BOOT-016`.

**Rule:** the core holds only what **both** machines need to boot and be reachable. `atticd`, the
builder, and restic are `server` deltas. Hyprland, power management, and wifi are laptop deltas.

## 1.1 Write `core/default.nix`

```nix
# The minimum both machines need to boot and be reachable.
# Nothing here may be specific to one machine.
{ config, lib, pkgs, ... }:
{
  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    auto-optimise-store = true;
    trusted-users = [ "root" "andrew" ];
  };
  nix.gc = {
    automatic = true;
    options = "--delete-older-than 30d";
  };

  time.timeZone = lib.mkDefault "America/New_York";
  i18n.defaultLocale = lib.mkDefault "en_US.UTF-8";

  users.users.andrew = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    shell = pkgs.zsh;
  };
  programs.zsh.enable = true;
  security.sudo.wheelNeedsPassword = true;

  services.openssh = {
    enable = true;
    settings.PasswordAuthentication = false;
    settings.PermitRootLogin = "no";
  };

  services.tailscale.enable = true;

  environment.systemPackages = with pkgs; [ git ripgrep fd jq ];
}
```

The Vendomat command line is system-installed through the core (`DEL-001`). `nix-meta` declares
Vendomat as a flake input **once**, and the core installs its package:

```nix
  environment.systemPackages = [ inputs.vendomat.packages.${pkgs.system}.default ];
```

That is the only place the input appears for machine configuration. `fromToml` and `fromInventory`
come from the same input (`DEL-004`). No consumer ever declares it (`DEL-002`).

Every `mkDefault` marks a value a host delta may override. A value without it is a core decision.

**Verify:**

```sh
nix eval --json .#nixosConfigurations.server.config.services.openssh.enable
nix eval --json .#nixosConfigurations.server.config.nix.settings.trusted-users
```

**Stop if:** the core references a hostname, a disk UUID, a graphical package, or `atticd`.

---

# Step 2 — cache access inside the core

**Goal:** a freshly installed machine substitutes before anything else runs. **IDs:**
`BOOT-002`, `CACHE-001`, `CACHE-002`.

## 2.1 Confirm the substituter URL

The Tailscale route is `/attic` and `atticd` listens on `127.0.0.1:8089`. The cache is `vendomat`.
The expected URL is therefore `https://server.tail770f47.ts.net/attic/vendomat`. **It is unverified.**

```sh
nix path-info --store 'https://server.tail770f47.ts.net/attic/vendomat' --json \
  /nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor
```

**Stop if:** this returns an error rather than metadata or null. Find the working URL before
writing it into the core.

## 2.2 Add to `core/default.nix`

```nix
  nix.settings = {
    substituters = [
      "https://cache.nixos.org/"
      "https://server.tail770f47.ts.net/attic/vendomat"
    ];
    trusted-public-keys = [
      "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      "vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA="
    ];
    netrc-file = "/etc/nix/netrc";
  };
```

The cache is private, so Nix needs the pull token in a netrc. Render it with sops, root-only, mode
`0400`. It must never enter a tracked file or a store path.

**Verify:**

```sh
nix show-config | rg '^(substituters|trusted-public-keys|netrc-file|trusted-users) ='
nix build --rebuild /nix/store/…-nvim-review-editor 2>&1 | rg -c 'substituted|copying'
```

**Verify the credential is clean:**

```sh
rg -i 'attic.*token|atticd.*secret' $(git -C ~/Documents/Projects/nix-meta ls-files) | rg -v netrc-file
```

Expect no output.

**Stop if:** a token string appears in any tracked file.

---

# Step 3 — prove the core in a virtual machine

**Goal:** the core boots with an empty store before either machine is touched. **IDs:**
`BOOT-001`, `BOOT-006`.

## 3.1 Add a throwaway host

```nix
# nix-meta/flake.nix, inside nixosConfigurations
vmtest = nixpkgs.lib.nixosSystem {
  system = "x86_64-linux";
  modules = [
    ../core
    { networking.hostName = "vmtest"; system.stateVersion = "26.11"; }
    { users.users.andrew.initialPassword = "vmtest"; }
  ];
};
```

## 3.2 Build and boot

```sh
nixos-rebuild build-vm --flake .#vmtest
./result/bin/run-vmtest-vm
```

**Verify:** the virtual machine boots to a login prompt and `andrew` logs in. Inside it:

```sh
nix show-config | rg '^substituters ='
systemctl is-active sshd tailscaled
```

**Stop if:** the virtual machine does not reach a login prompt. Fix the core, not the host.

---

# Step 4 — `mkModules`, `mkProject`, and `fromToml`

**Goal:** the two Nix functions the rest depends on. **IDs:** `MOD-001` to `MOD-009`,
`SYS-001` to `SYS-007`.

## 4.1 `lib/mkModules.nix`

```nix
{ lib }:
leaf:                       # { name, options ? {}, packages, extra ? {} }
let
  targets = {
    devenv      = { prefix = [ ];            install = [ "packages" ]; };
    nixos       = { prefix = [ "programs" ]; install = [ "environment" "systemPackages" ]; };
    homeManager = { prefix = [ "programs" ]; install = [ "home" "packages" ]; };
  };

  adapter = tname: t: { config, pkgs, ... }:
    let
      path = t.prefix ++ [ leaf.name ];
      cfg = lib.getAttrFromPath path config;
      extras = (leaf.extra or (_: _: { })) cfg pkgs;
    in {
      options = lib.setAttrByPath path
        ({ enable = lib.mkEnableOption leaf.name; } // (leaf.options or { }));

      config = lib.mkIf cfg.enable (lib.recursiveUpdate
        (lib.setAttrByPath t.install (leaf.packages cfg pkgs))
        (extras.${tname} or { }));
    };
in
lib.mapAttrs adapter targets
```

## 4.2 The consumer `outputs` template

This is **not** a library function. It is a template `generate.py` inlines into each consumer's
`flake.nix` in step 8. Write it here so step 5 can use it, and keep it beside `mkModules.nix` for
review, but do not export it from the flake.

```nix
  outputs = { nixpkgs, devenv, ... }@inputs:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      auto = lib.mapAttrsToList (_: v: v.devenvModules.default)
        (lib.filterAttrs (_: v: v ? devenvModules.default) inputs);
    in {
      devShells.${system}.default = devenv.lib.mkShell {
        inherit inputs;
        pkgs = nixpkgs.legacyPackages.${system};
        modules = [ ./devenv.nix ] ++ auto;
      };
    };
```

Why inline rather than a function: flake evaluation reaches only what the evaluating flake's own
`inputs` declare. A library function would force every consumer to declare Vendomat as an input.
Inlining is what makes `GEN-009` true — a consumer evaluates with Vendomat absent.

Auto-import is safe because importing a module activates nothing until `enable` is true
(`MOD-003`, `GEN-012`).

## 4.3 `lib/fromToml.nix`

```nix
{ lib, pkgs }: file:
let
  toml = builtins.fromTOML (builtins.readFile file);
  resolve = v:
    if builtins.isList v && builtins.all builtins.isString v
    then map (n: pkgs.${n} or n) v else v;
in
lib.mkMerge (lib.mapAttrsToList
  (path: value: lib.setAttrByPath (lib.splitString "." path) (resolve value))
  toml.options)
```

## 4.4 Fixtures

Write `tests/mkModules/` with one input declaring `options.maxLength` and an `extra.devenv.tasks`
entry. Assert:

| Assertion | ID |
| --- | --- |
| All three faces evaluate | `MOD-001` |
| Options at `x.*` for devenv and `programs.x.*` for the others | `MOD-002` |
| `enable` defaults to false and installs nothing | `MOD-003`, `INP-006` |
| Each face writes only its own install path | `MOD-005` |
| `extra.devenv.tasks` is absent from the NixOS face | `MOD-008` |
| An `extra.nixos` setting under `environment` does not clobber `systemPackages` | `MOD-007` |

Write `tests/fromToml/` with a TOML covering a bool, a string, an integer, and a package list.
Assert each round-trips (`SYS-007`), an unknown package name fails naming the key (`SYS-004`), and
a value defined in both TOML and Nix is an evaluation error (`SYS-005`).

## 4.5 `vendomat.paths`

A host declares each named path once. Inputs refer to the name.

```nix
# lib/paths.nix — the option, and the environment it exports
{ lib }: {
  options.vendomat.paths = lib.mkOption {
    type = lib.types.attrsOf lib.types.str;      # strings, never Nix paths
    default = { };
    description = "Named mutable locations. Inputs refer to these by name.";
  };
}
```

A string type is the whole safety mechanism. A `lib.types.path` would copy the directory contents
into the store on evaluation, which `PATH-003` forbids.

A lookup for inputs, which fails loudly on an undeclared name:

```nix
pathOf = name:
  config.vendomat.paths.${name} or (throw
    "vendomat: input '${leaf.name}' requested undeclared path '${name}'");
```

Export the same values to shells and services as `VENDOMAT_PATH_<NAME>`. A service receives its own
`Environment=` setting; it does not inherit a devenv shell's environment.

Fixtures in `tests/paths/` assert:

| Assertion | ID |
| --- | --- |
| Two inputs requesting `notes` both receive the host's declared value | `PATH-001` |
| The value is readable in Nix evaluation and present in the shell environment | `PATH-002` |
| Changing a file under a declared path leaves the build input set unchanged | `PATH-003` |
| An undeclared name fails evaluation and names the requesting input | `PATH-004` |

**Verify `PATH-003` concretely:**

```sh
nix path-info --json .#<output> | jq -r '.[].path' > /tmp/p1
echo scratch >> "$(nix eval --raw .#config.vendomat.paths.notes)/probe.txt"
nix path-info --json .#<output> | jq -r '.[].path' > /tmp/p2
cmp /tmp/p1 /tmp/p2        # must be identical
```

**Verify:** `devenv shell -- testee verify --mode quick` passes.

**Stop if:** `MOD-007` fails. A shallow merge silently drops the installed packages.

---

# Step 5 — split `nvim-core` out of `nix-nvim`

**Goal:** prove core-and-delta on a real tree. **IDs:** `CORE-001` to `CORE-007`, `BOOT-010`,
`ISO-001` to `ISO-005`.

## 5.1 Record the before state

```sh
cd ~/Documents/Projects/nix-nvim
nix build .#default --no-link --print-out-paths | tee /tmp/nv-before.path
nix-store -qR $(cat /tmp/nv-before.path) | sort > /tmp/nv-before.closure
ls $(cat /tmp/nv-before.path)/bin
```

## 5.2 Extract the core function

`nvim-core/lib/default.nix` holds only what **every** variant needs. No colour scheme, no finder,
no language server configuration.

```nix
pkgs: { appName, plugins ? [ ], lua ? "" }:
pkgs.wrapNeovimUnstable pkgs.neovim-unwrapped {
  wrapRc = true;
  luaRcContent = (builtins.readFile ../lua/core.lua) + lua;
  plugins = corePlugins ++ plugins;
}
```

Export it as `lib` (`CORE-001`, `INP-004`).

## 5.3 Rebuild `nv` as a variant

```nix
nvim-core.lib pkgs {
  appName = "nv";
  plugins = [ … the full daily set … ];
  lua = builtins.readFile ./lua/daily.lua;
}
```

**Verify `BOOT-010`:**

```sh
nix build .#default --no-link --print-out-paths | tee /tmp/nv-after.path
nix-store -qR $(cat /tmp/nv-after.path) | sort > /tmp/nv-after.closure
diff /tmp/nv-before.closure /tmp/nv-after.closure
```

A non-empty diff is permitted. An unexplained one is not. Name every removal.

## 5.4 Add a second variant and measure the delta

```sh
comm -13 /tmp/core.closure /tmp/variant.closure | xargs nix path-info -S | awk '{s+=$2} END {print s}'
```

Record the bytes (`CORE-005`).

**Verify `ISO-002`:**

```sh
mkdir -p /tmp/shadow && printf '#!/bin/sh\necho WRONG\n' > /tmp/shadow/nvim
chmod +x /tmp/shadow/nvim
PATH=/tmp/shadow:$PATH <variant>/bin/<variant-name> --headless -c 'qa!' && echo ok
```

The variant must still run its own editor. The Neovim wrappers default to `--suffix PATH`, so a
`PATH` entry would otherwise win.

**Verify `ISO-004`:** run the variant, then confirm its shada is under its own `NVIM_APPNAME`
directory and the daily editor's is untouched.

**Stop if:** `nv`'s command set shrank without a recorded reason.

---

# Step 6 — `watch-store` and the builder on `server`

**Goal:** every build on `server` reaches the cache. **IDs:** `CACHE-004`, `CACHE-006`,
`BUILD-001` to `BUILD-007`.

## 6.1 `attic watch-store`

```nix
systemd.services.attic-watch-store = {
  description = "Push new store paths to the vendomat cache";
  wantedBy = [ "multi-user.target" ];
  after = [ "network-online.target" ];
  wants = [ "network-online.target" ];
  serviceConfig = {
    ExecStart = "${pkgs.attic-client}/bin/attic watch-store vendomat";
    Restart = "always";
    User = "andrew";
  };
};
```

The push token stays outside every tracked file and store path (`CACHE-002`). Clear the cache's
upstream filter, or pass `--ignore-upstream-cache-filter`: its default entry `cache.nixos.org-1`
otherwise drops paths that came from a public cache (`CACHE-004`).

**Verify:**

```sh
systemctl is-active attic-watch-store
nix build nixpkgs#cowsay --no-link --print-out-paths            # something not yet cached
sleep 20
nix path-info --store 'http://127.0.0.1:8089/vendomat' <that path>
```

**Stop if:** the push log reports paths "in upstream". The filter is not cleared, and the cache will
have holes the laptop discovers at step 10.

## 6.2 The builder

A timer that, per input, fetches, finds the newest `v<semver>` tag, and builds its declared outputs
if that tag is unbuilt.

```sh
#!/bin/sh
# A failure in one input must not stop the others (BUILD-004).
set -u
for name in $(cat "$INPUTS"); do            # a hand-written list until step 8
  rev=$(git -C "$HOME/vendor/$name" rev-list -n1 "$(git -C "$HOME/vendor/$name" \
        tag --list 'v*' --sort=-v:refname | head -1)")
  for out in $(cat "$HOME/vendor/$name/.outputs"); do
    log="$STATE/$name-$out-$rev.log"
    if nix build "git+file://$HOME/vendor/$name?rev=$rev#$out" \
         --no-link --print-out-paths > "$log" 2>&1
    then echo "ok   $name#$out $rev"
    else echo "FAIL $name#$out $rev (see $log)"
    fi
  done
done
```

**Verify `BUILD-003`:** each log carries the command, the exit status, and the output paths.

**Verify `BUILD-004`:** break one input; the run reports it failed and the others still build.

**Stop if:** a failing input aborts the run.

---

# Step 7 — install `server` fresh on the 4 TB drive

**Goal:** `server` boots from the 4 TB drive on the new core. The 512 GB installation stays
independently bootable. **IDs:** `BOOT-008`, `BOOT-016`, `BOOT-021`, `BOOT-022`, `DISK-004`,
`DISK-006`, `DISK-007`.

**This replaces the in-place conversion.** An earlier draft used `nixos-rebuild test` and generation
rollback. The fallback is now a separate drive with its own EFI System Partition, which is stronger:
a failed install cannot touch the running system's bootloader.

**Entry condition:** step 0's preflight prints `PREFLIGHT PASS`.

## 7.1 The layout

One EFI System Partition and one root partition. Attic's data stays on the WD Green disk through
first boot and moves afterwards, so the root takes the remainder.

| Partition | Size | Type | Purpose |
| --- | --- | --- | --- |
| `p1` | 1 GiB | EFI System | the new system's `/boot` |
| `p2` | rest | Linux filesystem | root, including `/nix/store` |

Each system keeps its own EFI System Partition. Neither writes the other's boot entries, so you
choose between them in the firmware boot menu (`DISK-006`).

## 7.2 Split `server.nix`

Most of its 36 system blocks are declarative settings that move to `machines/server.toml`. These
stay in `machines/server.nix`:

- hardware, boot, and `fileSystems` — UUIDs and generated configuration
- sops secrets and templates — function calls
- `atticd`, `atticd-storage-setup`, `atticd-tailscale-serve` — unit bodies and conditionals
- the restic units — script bodies
- `attic-watch-store` from step 6
- anything conditional on another option

Record the line count before and after.

## 7.3 Build the new system **on the running old system**

This is the ordering that matters. `atticd` runs on the 512 GB system, so the cache and a warm
store are only available there. Build first, install second, and the install copies locally with no
substitution at all (`BOOT-022`).

```sh
cd ~/Documents/Projects/nix-meta
nix build .#nixosConfigurations.server.config.system.build.toplevel \
  --no-link --print-out-paths | tee /tmp/server-new.path
nix-store -qR "$(cat /tmp/server-new.path)" | wc -l
```

## 7.4 Record the before state

```sh
systemctl list-units --state=active --type=service --no-legend | awk '{print $1}' | sort > /tmp/svc-before
ls /run/current-system/sw/bin | sort > /tmp/bin-before
```

## 7.5 Partition and format

Re-run the step 0 preflight immediately before this. Use the stable identifier throughout.

```sh
T=/dev/disk/by-id/nvme-eui.e8238fa6bf530001001b448b4fbe837d
/run/wrappers/bin/sudo parted "$T" -- mklabel gpt
/run/wrappers/bin/sudo parted "$T" -- mkpart ESP fat32 1MiB 1GiB
/run/wrappers/bin/sudo parted "$T" -- set 1 esp on
/run/wrappers/bin/sudo parted "$T" -- mkpart root ext4 1GiB 100%
/run/wrappers/bin/sudo mkfs.fat -F32 -n BOOT-NEW "$T-part1"
/run/wrappers/bin/sudo mkfs.ext4 -L nixos-new "$T-part2"
blkid "$T-part1" "$T-part2"            # record both UUIDs (DISK-005)
```

**Record the new UUIDs in the inventory before generating `fileSystems`.** A format changes the
filesystem UUID, so a stale inventory entry points at nothing.

```nix
# machines/server/hardware.nix — by-uuid only, never a kernel name (DISK-004)
fileSystems."/"     = { device = "/dev/disk/by-uuid/<p2 UUID>"; fsType = "ext4"; };
fileSystems."/boot" = { device = "/dev/disk/by-uuid/<p1 UUID>"; fsType = "vfat"; };
```

## 7.6 Install the prebuilt closure

```sh
/run/wrappers/bin/sudo mount /dev/disk/by-uuid/<p2 UUID> /mnt
/run/wrappers/bin/sudo mkdir -p /mnt/boot
/run/wrappers/bin/sudo mount /dev/disk/by-uuid/<p1 UUID> /mnt/boot
/run/wrappers/bin/sudo nixos-install --root /mnt \
  --system "$(cat /tmp/server-new.path)" --no-channel-copy 2>&1 | tee /tmp/install.log
rg -c 'building|will be built' /tmp/install.log      # expect 0
```

**Verify `BOOT-022`:** the install log shows no build. `nixos-install` accepts
`--system | --closure | --store-path`, so the prebuilt toplevel is copied, not rebuilt.

## 7.7 First boot

Select the new drive in the firmware boot menu. Do not change the boot order yet.

```sh
findmnt -n -o SOURCE,UUID / /boot
systemctl list-units --state=active --type=service --no-legend | awk '{print $1}' | sort > /tmp/svc-after
ls /run/current-system/sw/bin | sort > /tmp/bin-after
diff /tmp/svc-before /tmp/svc-after     # name every removal
diff /tmp/bin-before /tmp/bin-after     # name every removal
systemctl is-active sshd tailscaled
```

**Verify `BOOT-008`:** a removal is permitted; an unexplained one is not.

**Verify `BOOT-021`:** reboot into the 512 GB system from the firmware menu. It boots unchanged, and
`findmnt / ` reports `e6b180fa-534a-4b71-aff8-f9fe2e6d0834`. Both systems are independently
bootable.

**Verify `BOOT-016`:** grep `core/` for `atticd`, `restic`, and `hypr`. Expect no match.

**Undo:** boot the 512 GB drive from the firmware menu. Nothing on it was written.

## 7.8 Attic, afterwards

Attic keeps `/mnt/wd_green1/attic` through first boot. Only once the new root has run reliably:
declare `vendomat.paths.attic`, stop `atticd`, copy the data, and repoint the service.

`atticd` must require its mount, so a missing disk cannot redirect writes into the root filesystem
(`DISK-007`):

```nix
systemd.services.atticd.unitConfig.RequiresMountsFor = [ config.vendomat.paths.attic ];
```

**Verify:**

```sh
nix path-info --store 'http://127.0.0.1:8089/vendomat' \
  /nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor
```

Metadata, not null. The old data stays in place until the moved cache has served for a week.

**Stop if:** `atticd` does not answer after the move. The laptop then has no substituter.

---

# Step 8 — the registry and the flake generator

**Goal:** `vendomat sync` writes `flake.nix`. **IDs:** `REG-*`, `GEN-001` to `GEN-008`, `STORE-*`.

Start a bare source tree. The existing `src/vendomat/` is provenance.

There is no resolver. Nix walks the transitive graph and owns `flake.lock`. The generator writes
direct inputs only, and the `follows` lines no Nix function can produce.

| File | Contents | IDs |
| --- | --- | --- |
| `registry.py` | Pydantic models for `[inputs]` and `[passthrough]`; `add`, `remove`, `read`, `write` | `REG-001` to `REG-009` |
| `store.py` | Clone and fetch under `~/vendor`; refuse a dirty tree | `STORE-001` to `STORE-005` |
| `generate.py` | Registry to `flake.nix`: header, digest, `follows` lines, and the inline `outputs` block from §4.2 | `GEN-001` to `GEN-012` |
| `cache.py` | `nix path-info --store` presence per input | `CACHE-005` |
| `cli.py` | `add`, `remove`, `sync`, `status`, `query`, `path`, `explore` | `CLI-001` to `CLI-008`, `CLI-014` |

About 190 lines. There is no `update` command: `nix flake update <input>` already does it
(`CLI-006` withdrawn).

## 8.1 Order within the step

1. `registry.py` and its fixtures. **Verify:** every rejection in `REG-002`, `REG-003`, `REG-006`
   names its key. A string or integer value is rejected (`REG-003`).
2. `store.py`. **Verify:** `rm -rf ~/vendor && vendomat sync` reproduces the same `flake.nix`
   (`STORE-004`).
3. `generate.py`. **Verify:**

```sh
vendomat sync && cp flake.nix /tmp/a && vendomat sync && cmp /tmp/a flake.nix   # GEN-006
head -2 flake.nix | rg 'GENERATED by vendomat|registry-digest'                  # GEN-005
rg -c 'follows = "nixpkgs"' flake.nix                                           # GEN-002
rg -c vendomat flake.nix                                                        # GEN-004: expect 0
```

**Verify `GEN-009` — the independence check.** This is the one that justifies inlining:

```sh
nix develop --no-write-lock-file -c true                   # works normally
env PATH=$(echo "$PATH" | tr ':' '\n' | grep -v vendomat | paste -sd:) \
  nix develop -c true                                      # still works
nix build .#devShells.x86_64-linux.default --no-link       # still works
```

A consumer must evaluate, enter its shell, and build with no Vendomat package on `PATH` and no
Vendomat input in its flake.

4. **Verify `GEN-003`:** add one input whose repo needs two others. `flake.nix` gains exactly one
   entry; `flake.lock` gains three.
5. **Verify `GEN-008`:** record `sha256sum flake.lock`, run every Vendomat command, and confirm the
   sum is unchanged. Then run `nix flake update loci-nvim` and confirm it works.
6. **Verify `GEN-007`:** hand-write a `flake.nix` with no header. `sync` refuses and names it.
7. **Verify `GEN-010` to `GEN-012`:** add one registry entry and run `sync`. Its options appear with
   no other edit, nothing is installed until `enable` is true, and a `flake = false` entry is
   skipped rather than failing.
8. `cache.py` and `cli.py`. **Verify:** `status --json` carries all four fields per input
   (`CLI-005`).

## 8.2 Point the builder at the registry

Step 6 read `$INPUTS` from a hand-written file. Read the registry instead.

## 8.3 Acceptance test A

```sh
vendomat add loci-nvim
vendomat sync
nix flake metadata --json | jq '[.locks.nodes | keys[]] | length'
nix flake metadata --json | jq -r '[.locks.nodes | to_entries[] | select(.key|test("nixpkgs"))] | length'
devenv shell -- <the library's command>
```

**Pass:** `flake.nix` names only `loci-nvim` plus the three fixed inputs; `flake.lock` holds every
transitive input at an exact revision; exactly one `nixpkgs` node exists; the command runs; and the
log shows no local compilation.

**Stop if:** more than one `nixpkgs` node appears. A `follows` line is missing and the closure has
split.

---

# Step 9 — system configuration from TOML

**Goal:** `server` configured from TOML. **IDs:** `SYS-007` to `SYS-011`, `CLI-009` to `CLI-013`.

`systemcfg.py` provides `set`, `get`, `unset` over `<host>.toml`, plus `diff`, `apply`, `rollback`.

`diff` evaluates `nixosConfigurations.<host>.config.<path>` before and after and compares the JSON.
Build this one carefully: it reports what a change does before activation, which is the whole
advantage over editing Nix by hand.

## 9.1 Acceptance test B

```sh
vendomat set programs.nvimReview.enable true
vendomat diff
vendomat apply
```

**Pass:** the delta names only that option, the rebuild succeeds, and the command is on the machine.

**Verify `CLI-012`:** dirty a host file; `apply` refuses and names it.

**Verify `CLI-004`:** every read command leaves all files byte-identical.

---

# Step 10 — install `framework`

**Goal:** the laptop joins with no local build. **IDs:** `BOOT-019`, `CACHE-007`, `BUILD-008`.

By now `server` has built and pushed every closure the laptop needs. This step is a download.

## 10.1 Add the host

```nix
framework = nixpkgs.lib.nixosSystem {
  system = "x86_64-linux";
  modules = [
    ../core
    ../machines/framework/hardware.nix              # nixos-generate-config on the metal
    (vendomat.lib.fromToml ../machines/framework.toml)
    { networking.hostName = "framework"; system.stateVersion = "26.11"; }
  ];
};
```

```toml
# machines/framework.toml — the laptop deltas
[options]
"networking.networkmanager.enable" = true
"services.logind.lidSwitch" = "suspend"
"programs.hyprland.enable" = true
"environment.systemPackages" = ["kitty", "zellij"]
"programs.atuin.enable" = true
"programs.atuin.settings.sync_address" = "https://server.tail770f47.ts.net/atuin"
```

## 10.2 Warm the cache first — on `server`

```sh
nix build .#nixosConfigurations.framework.config.system.build.toplevel \
  --no-link --print-out-paths | tee /tmp/fw.path
nix-store -qR $(cat /tmp/fw.path) | wc -l
sleep 60                                            # let watch-store drain
nix-store -qR $(cat /tmp/fw.path) \
  | xargs nix path-info --store 'http://127.0.0.1:8089/vendomat' --json \
  | jq -r 'to_entries[] | select(.value == null) | .key'
```

**Verify `BOOT-019`:** the last command prints nothing. Every path the laptop needs is cached.

**Stop if:** it prints any path. Push those before installing, or the install compiles.

## 10.3 Install

Boot the installer, partition, then:

```sh
nixos-generate-config --root /mnt        # keep hardware-configuration.nix only
nixos-install --flake /mnt/etc/nixos#framework 2>&1 | tee /tmp/install.log
rg -c 'building|will be built' /tmp/install.log
```

**Verify `CACHE-007`:** the install log shows paths copied, not built. On first boot:

```sh
nix build --max-jobs 0 \
  /nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor 2>&1 | tee ~/cold.log
nix path-info --json /nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor \
  | jq -r '.[].narHash'
```

`--max-jobs 0` must succeed and the NAR hash must equal the one recorded at build. This is the
proof an earlier attempt could not obtain, because it required an unreachable host — collected
here as a by-product.

**Verify `BUILD-008`:** build something new on the laptop; confirm `server` substitutes it.

---

# Acceptance checklist

- [ ] Step 0: the new 4 TB system boots from its own EFI and root filesystems; the 512 GB system still boots.
- [ ] Steps 1 to 3: the core boots in a virtual machine with an empty store.
- [ ] Step 4: `mkModules`, `fromToml`, and `paths` fixtures pass, including `MOD-007`, `SYS-005`, and `PATH-003`.
- [ ] Step 5: `nv`'s closure diff is explained; the variant delta bytes are recorded.
- [ ] Step 6: a path built on `server` appears in the cache; no "in upstream" report.
- [ ] Step 7: `server` boots from the 4 TB drive; the 512 GB drive boots independently; every removal named.
- [ ] Step 8: acceptance test A passes, and `GEN-009` passes — a consumer builds with Vendomat absent.
- [ ] Step 9: acceptance test B passes.
- [ ] Step 10: the laptop installs with no compilation; `CACHE-007` and `BUILD-008` pass.
- [ ] `devenv shell -- testee verify --mode quick` passes.
- [ ] Each of the 141 requirement IDs has a recorded result.

# Open questions

| Question | Blocks |
| --- | --- |
| Is the substituter URL `https://server.tail770f47.ts.net/attic/vendomat`? | Step 2 |
| New repository, or this one with a bare source tree? | Step 8 |
| What `attic gc` policy, given retention 0, an eager builder, and `/nix/store` sharing the 4 TB root? | Step 7.8 |
| Does the laptop keep the name `framework`? | Step 10 |

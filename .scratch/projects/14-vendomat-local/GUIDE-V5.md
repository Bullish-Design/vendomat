# Vendomat V5 implementation guide

**Date:** 2026-10-07. **Status:** Superseded and blocked. Do not execute this guide. PV-02 blocks Step 0; PV-09 blocks installer cache access. **Authority:** [SPEC-V5.md](./SPEC-V5.md) is
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
| Cache | `vendomat`, private, priority 20, retention 0; the fresh-installer route is blocked by PV-09 |
| Cache key | `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=` |
| Attic listen | `127.0.0.1:8089`, tailnet-only Serve route at `/attic`; `attic use` drops this prefix |

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

## 0.2 Preflight status

**Blocked by PV-02. Do not run a preflight or continue to Step 7.** The existing checker was removed
because it could print `PREFLIGHT PASS` without checking model, serial, exact size, UUID ownership,
partition-table signatures, or all root/boot ancestry. PV-02's synthetic checker rejected its ten
injected unsafe cases, but `wipefs --no-act` could not read the physical target without a password.
Its partition-table and signature state is unknown.

The observed target is WD Blue SN5100, stable ID
`nvme-eui.e8238fa6bf530001001b448b4fbe837d`, serial `25459R800917`, 4,000,787,030,016 bytes.
`lsblk` showed no partition, mount, or filesystem UUID. That does not establish that the target is
bare. A reviewed checker must compare stable identity, model, serial, exact size, UUID ownership,
root and boot ancestry, mounts, partition table, and signatures, and fail closed on unknown results.

**Stop if:** the read-only signature scan remains unavailable, the checker reports an unknown value,
or any identity differs. No disk-writing command may run until this section is replaced by a reviewed
procedure and PV-02 is unblocked.

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
    options = "--delete-older-than 14d"; # PV-09 observed this on server
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

The shared core does not install the Vendomat CLI. PV-11 showed that the core VM boots without
it, and that adding a failing package to `environment.systemPackages` blocks the system build.
Install the CLI only through a later host delta, using
`inputs.vendomat.packages.${pkgs.system}.vendomat` (`DEL-006`, `DEL-007`). Keep the package out of
the core.

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

## 2.1 Cache route status

PV-09 confirmed that Tailscale Serve exposes a tailnet-only `/attic` prefix. A request to the API
under `/attic/vendomat` worked; the same request without `/attic` returned 404. The host-local Nix
endpoint is `http://127.0.0.1:8089/vendomat`. `attic use` given the Serve URL emits a binary-cache
endpoint without `/attic`, so that command does not configure the working route.

PV-09 fetched a known 121-path closure into an empty alternate store on `server`. It did not run a
cold installer VM. The host Nix config has no private cache key or pull credential. A fresh
installer cannot use the private tailnet route yet. **Do not add this cache configuration to the
core until the installer route, trust key, credential path, and source are proven in a cold VM.**

## 2.2 Installer route

**Blocked by PV-09.** Do not add the private cache to the core until a cold installer can reach the
cache and obtain its trust key, pull credential, and source flake. The Tailscale Serve route is
tailnet-only. The host Nix config has no private Attic key or credential, and `attic use` omits the
`/attic` prefix when given the Serve URL.

Keep the pull credential out of tracked files, store paths, and logs (`CACHE-002`). Decide whether
the installer joins the tailnet with a short-lived credential or receives a verified prebuilt
closure. Test the selected method in a disposable VM before changing the machine core.

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

# Step 4 — `mkModules` and `fromToml`

**Goal:** test face-specific modules and typed host TOML. **IDs:** `MOD-001` to `MOD-010`,
`INP-006` to `INP-007`, `SYS-001` to `SYS-010`.

PV-07 showed that `lib.recursiveUpdate` replaces package lists. Compose definitions with native
module merging. `mkModules` may return all three faces for convenience, but an authored flake exports
only the faces it implements. Each face remains disabled by default.

```nix
config = lib.mkIf cfg.enable (lib.mkMerge [
  (lib.setAttrByPath t.install (leaf.packages cfg pkgs))
  (extras.${tname} or { })
]);
```

The PV-07 fixture retained both `hello` and `ripgrep` in enabled module faces. Its candidate scan
found 14 of 18 providers with one face and one provider with all three.

## 4.1 Consumer outputs

Inline the `outputs` block in the generated consumer `flake.nix`. Do not import Vendomat from a
consumer. PV-05 showed that the standalone package and the shell work with Vendomat absent from a
sanitized `PATH`. The pinned devenv shell failed under pure root discovery and passed with
`--impure`.

```sh
nix develop --impure --no-write-lock-file -c true
nix build --impure --no-link .#devShells.x86_64-linux.default
```

A fixture must still prove the generated output after `vendomat sync` and with a genuinely cold
store.

## 4.2 Typed TOML module

`fromToml` returns a valid module. Resolve strings as packages only for option paths in an explicit
package allowlist. PV-06 tested `environment.systemPackages`; it also showed that
`users.users.<name>.extraGroups` must stay a list of strings. Unknown package names fail.

```nix
{ lib, pkgs }: file:
let
  toml = builtins.fromTOML (builtins.readFile file);
  packageOptions = [ "environment.systemPackages" ];
  resolve = path: value:
    if builtins.elem path packageOptions
       && builtins.isList value
       && builtins.all builtins.isString value
    then map (name: pkgs.${name} or (throw "unknown package ${name} at ${path}")) value
    else value;
in
{ config = lib.mkMerge (lib.mapAttrsToList
  (path: value: lib.setAttrByPath (lib.splitString "." path) (resolve path value))
  toml.options); }
```

The PV-06 wrapper fixture showed native option merge behavior: equal scalar definitions coalesced,
unequal scalar definitions failed with both values, and list definitions merged. Do not add a
blanket duplicate-definition error. A future converter must preserve values according to the option
type and report the path and package name on an unknown package.

## 4.3 Fixtures

The fixture must assert: each exported face evaluates alone; disabled faces install no package;
enabled faces preserve both the base package and extra package; target-specific options stay on
their face; ordinary string lists remain strings; package conversion applies only to listed paths;
and equal, unequal, and list definitions follow native merge rules. Link results to `MOD-010`,
`INP-007`, and `SYS-008` to `SYS-010`.

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

**Stop if:** `MOD-010` fails. Native module merging must preserve both package lists.

---

# Step 5 — split `nvim-core` out of `nix-nvim`

**Goal:** prove core-and-delta on a real tree. **IDs:** `CORE-001` to `CORE-008`, `BOOT-010`,
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

**Goal:** publish eligible outputs and record skips; cache availability is not guaranteed. **IDs:** `CACHE-006`, `CACHE-009`,
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

The push token stays outside every tracked file and store path (`CACHE-002`). Attic 0.1.0 reports
an upstream-signed path as `in upstream` and leaves it absent from the private cache. Keep the
public cache configured for consumer fallback; private-cache absence is not a false success. The
builder must record the skip (`CACHE-009`).

**Verify:**

```sh
systemctl is-active attic-watch-store
nix build nixpkgs#cowsay --no-link --print-out-paths            # something not yet cached
sleep 20
nix path-info --store 'http://127.0.0.1:8089/vendomat' <that path>
```

**Stop if:** a path reports absent from every configured substituter, or the builder hides an upstream skip.

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

**Blocked. Do not run this step.** PV-02 could not verify the target signature and partition-table
state. PV-09 did not prove a cold installer can obtain the prebuilt system closure. No install
command, partition layout, or Attic data move is approved by this guide.

The intended design keeps the 512 GB installation and its EFI partition intact, and uses stable
`/dev/disk/by-id/` identities before partitioning and `/dev/disk/by-uuid/` for mounts. Replace this
section with a reviewed procedure only after PV-02's real scan passes and PV-09's cold installer
fixture passes. The implementation session must not use the old partition or install commands.

**Related requirements:** `DISK-001` to `DISK-007`, `BOOT-021` to `BOOT-024`.

---

# Step 8 — the registry and the flake generator

**Goal:** `vendomat sync` writes `flake.nix`; Nix owns `flake.lock`. **IDs:** `REG-*`,
`GEN-001` to `GEN-014`, `STORE-*`.

The generator declares direct inputs only. Use a portable remote URL by default. A local checkout
needs an explicit input override; `VENDOMAT_SOURCE_ROOT` alone does not alter an existing flake or
lock (`STORE-006`, `STORE-007`). Nix follows the transitive graph. The PV-04 fixture showed that
a direct `nixpkgs.follows` edge leaves nested nodes separate unless each authored flake follows
its parent. Require one node only for a controlled graph that meets that condition (`GEN-013`).

The consumer shell passed with the pinned devenv only when invoked using `--impure`; the pure
command failed during root discovery (`GEN-014`). Preserve that flag in generated-consumer checks.
A cold-store generated consumer remains untested.

```sh
vendomat sync
nix flake metadata --json
nix develop --impure --no-write-lock-file -c true
nix build --impure --no-link .#devShells.x86_64-linux.default
```

Do not use `devenv.yaml` as a second dependency declaration. Do not claim the generator or a future
`vendomat sync` has passed until its fixture runs.

# Step 9 — system configuration from TOML

**Goal:** define host settings with typed TOML and Nix modules. **IDs:** `SYS-001` to `SYS-010`,
`CLI-009` to `CLI-015`.

`fromToml` must return a valid module. Resolve package names only for explicitly listed
package-valued option paths. Keep ordinary string lists as strings. Let NixOS option types merge
definitions: equal scalars can coalesce, unequal scalars fail, and list values follow their option
type. Do not apply a blanket duplicate-definition error.

The supported state sequence is:

1. `vendomat set <path> <value>` edits only the host TOML.
2. `vendomat diff` compares the last committed host file with the current file.
3. Commit the host TOML through Gitman.
4. `vendomat apply` runs only when the host file is clean.

PV-08 measured three changed values in its disposable NixOS fixture. A function could not be
serialized as JSON. The future `diff` command must report unsupported values clearly or restrict its
serialized output to supported values. PV-08 did not test a live switch, dirty-file refusal, force,
or generation rollback.

# Step 10 — install `framework`

**Blocked by PV-09.** Do not describe this as a download or run an installer until a cold installer
VM obtains the full closure with `--max-jobs 0` using its actual source, trust key, credential, and
network route. The host-local alternate-store result does not satisfy this requirement. Keep
`CACHE-007`, `BOOT-002`, `BOOT-019`, and `BUILD-008` open.

# Preliminary verification status

See [preliminary verification results](./prelim-verification/RESULTS.md). No V5 implementation
step has run. The current guide is blocked at Step 0 and at the private-cache installer route.

| Area | Result |
| --- | --- |
| Step 0 and physical target | Blocked: partition-table and signature scans were not available |
| Consumer source portability | Failed for absolute `git+file` paths; remote-default generator fixture remains required |
| Consumer shell | Impure fixture passed; pure root discovery failed |
| TOML and module merge | Current examples failed; successor contracts are recorded in `SPEC-V5.md` |
| Cache and retention | Isolated fixture passed; cold installer remains blocked |
| Machine core | Disposable VM passed without Vendomat CLI; production boot remains open |

# Open questions

| Question | Blocks |
| --- | --- |
| Which reachable remote host will serve private source flakes, and how will local overrides work in the generator? | Step 8 acceptance |
| How does a fresh installer obtain the private cache credential and route before first boot? | Steps 2, 3, and 10 |
| Will the owner accept `nix develop --impure` as the consumer shell contract? | Step 8 acceptance |
| Does the laptop keep the name `framework`? | Step 10 |
| When can an authorized read-only signature scan unblock PV-02? | Step 0 |

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

# Step 0 — withdrawn on 2026-10-08

The server will boot from the new 4 TB drive. The existing 512 GB installation remains intact
as a fallback. [The storage refinement](./REFINEMENT-2026-10-08.md) records the observed drive
identities and the new rule for partition and mount references.

The previous Step 0 contained a partition command for a kernel-assigned device name. That name
now belongs to the running system. Its commands are removed. Write and review a new install
procedure that identifies the target by hardware ID before any disk operation.

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

# Step 4 — `mkModules` and `fromToml`

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

## 4.2 `lib/fromToml.nix`

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

## 4.3 Fixtures

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

# Step 7 — convert `server`

**Goal:** `server` on the new core, with its settings in TOML. **IDs:** `BOOT-005`, `BOOT-008`,
`BOOT-011`, `BOOT-016`.

## 7.1 Split `server.nix`

Of its 36 system blocks, most are declarative settings that move to `machines/server.toml`. These
stay in `machines/server.nix`:

- hardware, boot, and `fileSystems` — UUIDs and generated configuration
- sops secrets and templates — function calls
- `atticd`, `atticd-storage-setup`, `atticd-tailscale-serve` — unit bodies and conditionals
- the restic units — script bodies
- `attic-watch-store` from step 6
- anything conditional on another option

Record the line count before and after.

## 7.2 Record the before state

```sh
systemctl list-units --state=active --type=service --no-legend | awk '{print $1}' | sort > /tmp/svc-before
ls /run/current-system/sw/bin | sort > /tmp/bin-before
nixos-rebuild list-generations | head -3
```

## 7.3 Activate

```sh
cd ~/Documents/Projects/nix-meta
/run/wrappers/bin/sudo nixos-rebuild test --flake .#server
```

**Verify `BOOT-008`:**

```sh
systemctl list-units --state=active --type=service --no-legend | awk '{print $1}' | sort > /tmp/svc-after
ls /run/current-system/sw/bin | sort > /tmp/bin-after
diff /tmp/svc-before /tmp/svc-after     # name every removal
diff /tmp/bin-before /tmp/bin-after     # name every removal
systemctl is-active atticd attic-watch-store tailscaled sshd
nix path-info --store 'http://127.0.0.1:8089/vendomat' <a known path>
```

A removal is permitted. An unexplained one is not.

**Verify `BOOT-005`:** `nixos-rebuild list-generations` still lists the prior entry, and the boot
default still names it after `test`.

**Verify `BOOT-016`:** nothing `server`-only appears in `core/`. Grep it for `atticd`, `restic`, and
`hypr`; expect no match.

Promote with `switch` after a week.

**Undo:** reboot. `test` never changed the boot default.

**Stop if:** `atticd` is not active or the cache does not answer.

---

# Step 8 — the resolver

**Goal:** `vendomat sync` writes `devenv.yaml`. **IDs:** `REG-*`, `RES-*`, `EMIT-*`, `STORE-*`.

Start a bare source tree. The existing `src/vendomat/` is provenance.

| File | Contents | IDs |
| --- | --- | --- |
| `registry.py` | Pydantic models for `[inputs]` and `[passthrough]`; `add`, `remove`, `read`, `write` | `REG-001` to `REG-009` |
| `store.py` | Clone and fetch under `~/vendor`; refuse a dirty tree; read tags | `STORE-001` to `STORE-005` |
| `resolve.py` | Constraint to tag to revision; read each input's `devenv.yaml`; walk; dedupe; detect cycles | `RES-001` to `RES-012` |
| `emit.py` | Write the generated `devenv.yaml` with its header and a stable key order | `EMIT-001` to `EMIT-007` |
| `cache.py` | `nix path-info --store` presence per input | `CACHE-005` |
| `cli.py` | `add`, `remove`, `sync`, `update`, `status`, `query`, `path`, `explore` | `CLI-001` to `CLI-008`, `CLI-014` |

## 8.1 Order within the step

1. `registry.py` and its fixtures. **Verify:** every rejection in `REG-002` to `REG-006` names its key.
2. `store.py`. **Verify:** `rm -rf ~/vendor && vendomat sync` reproduces the same resolution (`STORE-004`).
3. `resolve.py`. **Verify:** a depth-three chain resolves; a cycle names both inputs; `^0.3` against
   `^0.4` names all five facts; two runs produce identical output (`RES-009`).
4. `emit.py`. **Verify:** `sync` twice, then `cmp` — no difference (`EMIT-005`). A hand-written
   `devenv.yaml` is left untouched and the command exits non-zero (`EMIT-006`).
5. `cache.py` and `cli.py`. **Verify:** `status --json` carries all four fields per input (`CLI-005`).

## 8.2 Replace the builder's hand-written list

Step 6 read `$INPUTS` from a file. Point it at the registry instead.

## 8.3 Acceptance test A

```sh
vendomat add knappy '^0.3'
vendomat sync
devenv shell -- <the library's command>
```

**Pass:** the generated file carries every transitive input at an exact revision, the command runs,
and no local compilation appears in the log.

**Stop if:** `EMIT-003` fails. A transitive input under `imports:` double-imports its parent's
modules.

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
proof V4 P5 could not obtain — collected here as a by-product.

**Verify `BUILD-008`:** build something new on the laptop; confirm `server` substitutes it.

---

# Acceptance checklist

- [ ] Step 0: the new 4 TB system boots from its own EFI and root filesystems; the 512 GB system still boots.
- [ ] Steps 1 to 3: the core boots in a virtual machine with an empty store.
- [ ] Step 4: `mkModules` and `fromToml` fixtures pass, including `MOD-007` and `SYS-005`.
- [ ] Step 5: `nv`'s closure diff is explained; the variant delta bytes are recorded.
- [ ] Step 6: a path built on `server` appears in the cache; no "in upstream" report.
- [ ] Step 7: `server` converted; every service and command removal named; the prior generation intact.
- [ ] Step 8: acceptance test A passes.
- [ ] Step 9: acceptance test B passes.
- [ ] Step 10: the laptop installs with no compilation; `CACHE-007` and `BUILD-008` pass.
- [ ] `devenv shell -- testee verify --mode quick` passes.
- [ ] Each of the 127 requirement IDs has a recorded result.

# Open questions

| Question | Blocks |
| --- | --- |
| Is the substituter URL `https://server.tail770f47.ts.net/attic/vendomat`? | Step 2 |
| New repository, or this one with a bare source tree? | Step 8 |
| What `attic gc` policy, given retention 0 and an eager builder? | Step 6 |
| Does the laptop keep the name `framework`? | Step 10 |

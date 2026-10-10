# The Vendomat devenv module (SPEC-V6 section 2). Import it as `inputs.vendomat.devenvModules.default`.
#
#   imports = [ inputs.vendomat.devenvModules.default ];
#   vendomat.cache = { push = true; name = "vendomat"; };
#
# Every part is inert until a workspace uses it: a face does nothing until `enable = true`, the
# inventory builds nothing until a host is listed, and the pin check reads `devenv.lock` only.
_self:
{ inputs, config, options, lib, pkgs, ... }:
let
  cfg = config.vendomat;
  guard = import ./guard.nix { inherit lib; };
  lockPin = import ./lock-pin.nix { inherit lib; };
  mkPreflight = import ./preflight.nix { inherit lib pkgs; };

  # --- Lock-pin check (VMOD-005, VMOD-006) ---------------------------------------------------
  lockPath = "${config.devenv.root}/devenv.lock";
  unpinned = lockPin.unpinned lockPath;

  # The same rule, for a command that builds or pushes. `devenv build` does not evaluate assertions
  # (NAT-025), so a push runs this first (VMOD-006).
  checkScript = pkgs.writeShellScript "vendomat-check-lock" ''
    set -euo pipefail
    lock="''${DEVENV_ROOT:-$PWD}/devenv.lock"
    if [ ! -f "$lock" ]; then
      echo "vendomat: no devenv.lock at $lock; run 'vendomat sync'" >&2
      exit 1
    fi
    bad=$(${pkgs.jq}/bin/jq -r '
      .nodes | to_entries[]
      | select(.value.original.type? == "git")
      | select((((.value.original.ref // "") | startswith("refs/tags/")) and ((.value.locked.rev // "") | test("^[0-9a-f]{40}$"))) | not)
      | "  input node \(.key): \(.value.original.url) ref=\(.value.original.ref // "<none>")"
    ' "$lock")
    if [ -n "$bad" ]; then
      echo "vendomat: these git inputs are not pinned to a tag and a 40-hex revision:" >&2
      echo "$bad" >&2
      exit 1
    fi
  '';

  pushScript = pkgs.writeShellScriptBin "vendomat-push" ''
    set -euo pipefail
    cache="''${1:-${toString cfg.cache.name}}"
    ${checkScript}
    roots=$(devenv build | ${pkgs.jq}/bin/jq -r '.[]')
    if [ -z "$roots" ]; then
      echo "vendomat-push: devenv build produced no store paths" >&2
      exit 1
    fi
    echo "vendomat-push: pushing to cache '$cache':" >&2
    echo "$roots" >&2
    printf '%s\n' "$roots" | ${cfg.cache.attic} push "$cache" --stdin
  '';

  # --- Machines (VMOD-011, VMOD-016) ---------------------------------------------------------
  guardKey = host: "vendomat-guard:${host}";
  directDefs = host: lib.filter
    (d: builtins.isAttrs d.value && d.value ? ${host} && (d.value.${host}.nixos or null) != null
      && (d.value.${host}.nixos.key or null) != guardKey host)
    options.machines.definitionsWithLocations;

  hostModule = host: h: {
    key = guardKey host;
    imports = [ (guard.mk { inherit host; inventory = h; direct = directDefs host; }) h.nixos ];
  };

  # The patched devenv (devenv-dist patches 0005 and 0006) reads the mode and the preflight program
  # from `machines.<host>.vendomat`. Stock devenv has no such option, so write it only where it exists.
  patchedMachines =
    let sub = options.machines.type.getSubOptions [ "machines" "<name>" ];
    in sub ? vendomat;
  machineMeta = host: h: lib.optionalAttrs patchedMachines {
    vendomat = {
      mode = h.mode;
      preflight.program =
        if h.mode == "fresh-install" then mkPreflight { inherit host; disks = h.disks; } else null;
    };
  };

  diskType = lib.types.submodule {
    options = {
      byId = lib.mkOption {
        type = lib.types.str;
        description = "Full /dev/disk/by-id/ path of the drive.";
      };
      role = lib.mkOption {
        type = lib.types.enum [ "install-target" "keep" "existing-system" ];
        description = ''
          install-target: a blank drive that a fresh-install host may format.
          keep: a drive that no command may write (the old system's disk, for example).
          existing-system: the drive that holds an adopted host's root or boot filesystem.
        '';
      };
      model = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
      serial = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
      sizeBytes = lib.mkOption { type = lib.types.nullOr lib.types.ints.positive; default = null; };
    };
  };
in
{
  options.vendomat = {
    inventory = lib.mkOption {
      default = { };
      description = "Hosts. A host listed here gets the guard in machines.<host>.nixos.";
      type = lib.types.attrsOf (lib.types.submodule {
        options = {
          mode = lib.mkOption {
            type = lib.types.enum [ "fresh-install" "adopt-existing" ];
            description = "fresh-install: the host may be installed on its install-target. adopt-existing: devenv never installs it.";
          };
          nixos = lib.mkOption {
            type = lib.types.deferredModule;
            default = { };
            description = "The NixOS module of the host. Write it here, not in machines.<host>.nixos.";
          };
          disks = lib.mkOption {
            type = lib.types.attrsOf diskType;
            default = { };
            description = "The host's drives, by stable identity.";
          };
        };
      });
    };

    installTargets = lib.mkOption {
      type = lib.types.attrsOf (lib.types.listOf lib.types.str);
      readOnly = true;
      default = lib.mapAttrs
        (_: h: lib.mapAttrsToList (_: d: d.byId) (lib.filterAttrs (_: d: d.role == "install-target") h.disks))
        cfg.inventory;
      description = "The by-id paths of each host's install-target disks. `vendomat machine install` reads them.";
    };

    modes = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      readOnly = true;
      default = lib.mapAttrs (_: h: h.mode) cfg.inventory;
      description = "The mode of each inventory host. `vendomat machine install` and `check` read it.";
    };

    # VMOD-009: host paths, exported as VENDOMAT_PATH_<NAME>.
    pathsFile = lib.mkOption {
      type = lib.types.str;
      default = "/etc/vendomat/paths.json";
      description = "JSON object (name to path) that supplies the default for vendomat.paths. A missing file gives {}.";
    };
    paths = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default =
        if builtins.pathExists cfg.pathsFile
        then builtins.fromJSON (builtins.readFile cfg.pathsFile)
        else { };
      description = "Host paths by name. Each entry becomes env.VENDOMAT_PATH_<NAME>.";
    };

    # VMOD-008: the store path of every flake input except self.
    exportInputPaths = lib.mkEnableOption "outputs.vendomat.inputPaths, a derivation that lists and references every input source";
    inputPaths = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      readOnly = true;
      # Interpolation turns a live `path:` input into a store path, and keeps the string context.
      default = lib.mapAttrs (_: i: "${i.sourceInfo.outPath or i.outPath}")
        (lib.filterAttrs (n: i: n != "self" && i ? outPath) inputs);
      description = "Store path of each flake input, by input name.";
    };

    cache = {
      push = lib.mkEnableOption "the vendomat-push script and the vendomat:push task";
      name = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Attic cache name for vendomat-push.";
      };
      attic = lib.mkOption {
        type = lib.types.str;
        default = "attic";
        description = "Attic client command, looked up on PATH at run time.";
      };
    };

    check.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Fail shell entry when a git input in devenv.lock is not pinned to a tag. It does not reach the machine guard.";
    };

    # VMOD-010: profile defaults. A workspace value wins because these use mkDefault.
    hosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "server" "framework" ];
      description = "Host names. On each, env.VENDOMAT_HOST defaults to the name.";
    };
    users = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "andrew" ];
      description = "User names. For each, env.VENDOMAT_USER defaults to the name.";
    };
  };

  config = lib.mkMerge [
    {
      machines = lib.mapAttrs (host: h: { nixos = hostModule host h; } // machineMeta host h) cfg.inventory;
      # Any other definition of machines.<host>.nixos can drop the guard without an error, because the
      # option type merges attribute sets shallowly (NAT-029). Refuse it at shell entry as well.
      assertions = lib.mapAttrsToList
        (host: _: {
          assertion = directDefs host == [ ];
          message = "vendomat: machines.${host}.nixos is defined outside vendomat.inventory.${host}.nixos (in ${toString (map (d: d.file) (directDefs host))}). Move the module to vendomat.inventory.${host}.nixos.";
        })
        cfg.inventory;
    }
    {
      profiles.hostname = lib.genAttrs cfg.hosts (h: { module = { env.VENDOMAT_HOST = lib.mkDefault h; }; });
      profiles.user = lib.genAttrs cfg.users (u: { module = { env.VENDOMAT_USER = lib.mkDefault u; }; });
    }
    {
      env = lib.mapAttrs'
        (n: v: lib.nameValuePair "VENDOMAT_PATH_${lib.toUpper (builtins.replaceStrings [ "-" "." ] [ "_" "_" ] n)}" v)
        cfg.paths;
    }
    (lib.mkIf cfg.exportInputPaths {
      # A plain string or a flake input under `outputs` breaks `devenv build`; a derivation works.
      outputs.vendomat.inputPaths = pkgs.writeText "vendomat-input-paths.json" (builtins.toJSON cfg.inputPaths);
    })
    (lib.mkIf cfg.cache.push {
      assertions = [{
        assertion = cfg.cache.name != null;
        message = "vendomat.cache.push = true needs vendomat.cache.name.";
      }];
      packages = [ pushScript ];
      tasks."vendomat:push" = {
        description = "Check the lock, then push the roots of `devenv build` to the Attic cache";
        exec = "${pushScript}/bin/vendomat-push";
      };
    })
    {
      assertions = lib.optional cfg.check.enable {
        assertion = unpinned == { };
        message = ''
          vendomat: these git inputs are not pinned to a tag and a 40-hex revision:
          ${lockPin.describe unpinned}
          Set '?ref=refs/tags/<tag>' on each url in vendomat.toml, then run 'vendomat sync'.
          To turn this check off, set vendomat.check.enable = false in devenv.nix.'';
      };
    }
  ];
}

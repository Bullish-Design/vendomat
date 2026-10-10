# The Vendomat build-host module (V6 Step 5; BUILD-001 to BUILD-008, CACHE-006).
#
# Import it from a NixOS configuration. It does three things on a host that builds:
#
#   1. `vendomat-build`: builds one registry input per release tag. One run is one `nix build` of
#      `<url>?ref=refs/tags/<tag>#<attr>`. It prints the command, the exit status, and the output
#      paths to the journal. The journal and the unit exit status are the only record (BUILD-006).
#   2. `vendomat-build@<input>:<tag>.service`: builds that one input at that one tag.
#      `vendomat-build-scan.service` lists the tags of every registry input and builds each tag whose
#      output path is not yet in the local Nix store. A failed input never stops the others
#      (BUILD-004). `vendomat.builder.scan.onCalendar` adds a timer for the scan.
#   3. `vendomat-watch-store.service`: runs `attic watch-store <cache>`. It is the only path that
#      moves outputs to the cache. The builder never calls `attic push` (BUILD-005, CACHE-006).
#
# The push credential is a file on the host, outside the Nix store. The module writes an Attic
# client configuration that names the file (`token-file`) and holds no token. The watch-store unit
# starts only when that file exists.
#
# Options (all under `vendomat.builder`):
#   enable                     bool, default false
#   inputs.<name>.url          str: the collection URL of the input, for example git://server/knappy
#   inputs.<name>.attr         str: flake attribute to build, default packages.x86_64-linux.default
#   cache.name                 str: Attic cache name, default "vendomat"
#   cache.endpoint             str: Attic server endpoint, for example http://server:8080
#   cache.tokenFile            str: absolute run-time path of the push credential
#   cache.package              package: the Attic client, default pkgs.attic-client
#   cache.upstreamKeyNames     list of str: upstream signing key names, default [ "cache.nixos.org-1" ]
#   watchStore.enable          bool, default true
#   buildArgs                  list of str: extra `nix build` arguments, default []
#   scan.onCalendar            null or str: systemd calendar expression for the scan timer
{ config, lib, pkgs, ... }:
let
  cfg = config.vendomat.builder;
  inherit (lib) mkOption mkEnableOption mkIf types;

  registry = pkgs.writeText "vendomat-builder-registry.json" (builtins.toJSON
    (lib.mapAttrs (_: input: { inherit (input) url attr; }) cfg.inputs));

  runtimePath = lib.makeBinPath [ config.nix.package pkgs.git pkgs.jq pkgs.coreutils pkgs.gnugrep pkgs.gnused ];

  buildScript = pkgs.writeShellScriptBin "vendomat-build" ''
    export PATH=${runtimePath}
    export NIX_CONFIG="experimental-features = nix-command flakes"
    registry=${registry}
    extra=(${lib.escapeShellArgs cfg.buildArgs})
    upstream=(${lib.escapeShellArgs cfg.cache.upstreamKeyNames})

    field() { jq -r --arg n "$1" --arg f "$2" '.[$n][$f] // empty' "$registry"; }

    # report_upstream <path>: name an output that an upstream cache signed. Attic skips such a path
    # (CACHE-009), so the Vendomat cache will not hold it and consumers keep the upstream substituter.
    report_upstream() {
      local path=$1 sig key u
      for sig in $(nix path-info --json --json-format 1 "$path" | jq -r '.[] | (.signatures // [])[]'); do
        key=''${sig%%:*}
        for u in "''${upstream[@]}"; do
          if [ "$key" = "$u" ]; then
            echo "vendomat-build: upstream: $path is signed by $key; Attic skips it and the Vendomat cache will not hold it"
          fi
        done
      done
    }

    # build_one <input> <tag>. Print the command, the status, and the outputs. Return the status.
    build_one() {
      local name=$1 tag=$2 url attr installable out status path
      url=$(field "$name" url)
      attr=$(field "$name" attr)
      if [ -z "$url" ]; then
        echo "vendomat-build: FAILED input=$name tag=$tag: not in the registry"
        return 2
      fi
      installable="$url?ref=refs/tags/$tag#$attr"
      echo "vendomat-build: input=$name tag=$tag"
      local cmd=(nix build --no-link --print-out-paths "''${extra[@]}" "$installable")
      echo "vendomat-build: command: ''${cmd[*]}"
      out=$("''${cmd[@]}")
      status=$?
      echo "vendomat-build: status: $status input=$name tag=$tag"
      if [ "$status" -eq 0 ]; then
        while IFS= read -r path; do
          [ -n "$path" ] || continue
          echo "vendomat-build: output: $path input=$name tag=$tag"
          report_upstream "$path"
        done <<<"$out"
      else
        echo "vendomat-build: FAILED input=$name tag=$tag"
      fi
      return "$status"
    }

    # scan: build each release tag of each registry input whose output is not in the local store.
    scan() {
      local built=0 skipped=0 failed=0 failures="" name url attr tag out
      for name in $(jq -r 'keys[]' "$registry"); do
        url=$(field "$name" url)
        attr=$(field "$name" attr)
        local tags listing
        if ! listing=$(git ls-remote --tags --refs "$url"); then
          echo "vendomat-build: FAILED input=$name: cannot list tags of $url"
          failed=$((failed + 1)); failures="$failures $name"
          continue
        fi
        tags=$(printf '%s\n' "$listing" | sed 's|.*refs/tags/||' | sort -V)
        for tag in $tags; do
          if ! out=$(nix eval --raw "$url?ref=refs/tags/$tag#$attr.outPath"); then
            echo "vendomat-build: FAILED input=$name tag=$tag: evaluation failed"
            failed=$((failed + 1)); failures="$failures $name:$tag"
            continue
          fi
          if nix path-info "$out" >/dev/null 2>&1; then
            echo "vendomat-build: skip input=$name tag=$tag: $out is already in the store"
            skipped=$((skipped + 1))
            continue
          fi
          if build_one "$name" "$tag"; then
            built=$((built + 1))
          else
            failed=$((failed + 1)); failures="$failures $name:$tag"
          fi
        done
      done
      echo "vendomat-build: summary built=$built skipped=$skipped failed=$failed:$failures"
      [ "$failed" -eq 0 ]
    }

    case "''${1:-}" in
      "")
        echo "usage: vendomat-build --scan | --list | <input>:<tag>..." >&2
        exit 3 ;;
      --list) jq -r 'keys[]' "$registry" ;;
      --scan) scan ;;
      *)
        rc=0
        for spec in "$@"; do
          case "$spec" in
            *:*) build_one "''${spec%%:*}" "''${spec#*:}" || rc=1 ;;
            *) echo "vendomat-build: FAILED $spec: expected <input>:<tag>"; rc=1 ;;
          esac
        done
        exit "$rc" ;;
    esac
  '';

  # The Attic client reads the token from a file. This configuration holds only the file name.
  atticConfig = pkgs.writeText "vendomat-attic-config.toml" ''
    default-server = "vendomat"

    [servers.vendomat]
    endpoint = "${cfg.cache.endpoint}"
    token-file = "${cfg.cache.tokenFile}"
  '';
in
{
  options.vendomat.builder = {
    enable = mkEnableOption "the Vendomat build host: per-tag builds and attic watch-store";

    inputs = mkOption {
      default = { };
      description = "The registry inputs this host builds, by name.";
      type = types.attrsOf (types.submodule {
        options = {
          url = mkOption {
            type = types.str;
            description = "The collection URL of the input (git://host/name).";
          };
          attr = mkOption {
            type = types.str;
            default = "packages.x86_64-linux.default";
            description = "The flake output attribute that the build produces.";
          };
        };
      });
    };

    cache = {
      name = mkOption { type = types.str; default = "vendomat"; description = "The Attic cache name."; };
      endpoint = mkOption { type = types.str; description = "The Attic server endpoint."; };
      tokenFile = mkOption {
        type = types.str;
        description = "Absolute run-time path of the push credential. Never a store path.";
      };
      package = mkOption {
        type = types.package;
        default = pkgs.attic-client;
        description = "The Attic client package.";
      };
      upstreamKeyNames = mkOption {
        type = types.listOf types.str;
        default = [ "cache.nixos.org-1" ];
        description = ''
          Signing key names of upstream caches. The Attic cache must list the same names. The
          builder reports each output that carries one of these signatures.
        '';
      };
    };

    watchStore.enable = mkOption {
      type = types.bool;
      default = true;
      description = "Run attic watch-store, so every build output reaches the cache.";
    };

    buildArgs = mkOption {
      type = types.listOf types.str;
      default = [ ];
      description = "Extra arguments for each nix build.";
    };

    scan.onCalendar = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "systemd calendar expression that runs the tag scan. Null leaves it manual.";
    };
  };

  config = mkIf cfg.enable {
    assertions = [
      {
        assertion = !(lib.hasPrefix "/nix/store" cfg.cache.tokenFile);
        message = "vendomat.builder.cache.tokenFile must be a run-time path, never a store path.";
      }
    ];

    environment.systemPackages = [ buildScript cfg.cache.package ];

    systemd.services."vendomat-build@" = {
      description = "Vendomat build of one registry input at one tag (%I)";
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${buildScript}/bin/vendomat-build %I";
        CacheDirectory = "vendomat-builder";
        Environment = [ "HOME=/var/cache/vendomat-builder" "NIX_REMOTE=daemon" ];
        # The journal is the record. The unit has no state directory and no writable path.
        ProtectSystem = "strict";
        ReadWritePaths = [ "/var/cache/vendomat-builder" ];
      };
    };

    systemd.services.vendomat-build-scan = {
      description = "Vendomat build of every new release tag of every registry input";
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${buildScript}/bin/vendomat-build --scan";
        CacheDirectory = "vendomat-builder";
        Environment = [ "HOME=/var/cache/vendomat-builder" "NIX_REMOTE=daemon" ];
        ProtectSystem = "strict";
        ReadWritePaths = [ "/var/cache/vendomat-builder" ];
      };
    };

    systemd.timers.vendomat-build-scan = mkIf (cfg.scan.onCalendar != null) {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnCalendar = cfg.scan.onCalendar; Persistent = true; };
    };

    systemd.services.vendomat-watch-store = mkIf cfg.watchStore.enable {
      description = "Attic watch-store for the ${cfg.cache.name} cache";
      wantedBy = [ "multi-user.target" ];
      wants = [ "network-online.target" ];
      after = [ "network-online.target" "nix-daemon.service" ];
      path = [ config.nix.package cfg.cache.package ];
      environment.XDG_CONFIG_HOME = "/run/vendomat-builder";
      unitConfig.ConditionPathExists = cfg.cache.tokenFile;
      preStart = ''
        mkdir -p /run/vendomat-builder/attic
        install -m 600 ${atticConfig} /run/vendomat-builder/attic/config.toml
      '';
      serviceConfig = {
        ExecStart = "${cfg.cache.package}/bin/attic watch-store ${lib.escapeShellArg cfg.cache.name}";
        RuntimeDirectory = "vendomat-builder";
        RuntimeDirectoryPreserve = true;
        Restart = "on-failure";
        RestartSec = 5;
      };
    };
  };
}

self:
{ inputs, config, options, lib, pkgs, ... }:
let
  cfg = config.vendomat;

  # ---- V6 builder (DESC-001, VMOD-013, VMOD-014) -------------------------------------------------
  # Everything in this block depends on `inputs` and `self` only, never on `config`, so `imports` can use it.
  # Candidates: every flake input except self, `devenv`, `nixpkgs`, Vendomat itself (by outPath), and non-flakes
  # (a `flake = false` input has no `vendomat` or `devenvModules` attribute, so it falls out below).
  candidates = lib.filterAttrs
    (n: i: !(lib.elem n [ "self" "devenv" "nixpkgs" ]) && (i.outPath or null) != self.outPath)
    inputs;
  hasDesc = i: i ? vendomat;
  hasHand = i: (i ? devenvModules) && (i.devenvModules ? default);

  describedAll = lib.filterAttrs (_: hasDesc) candidates;
  bothInputs = lib.attrNames (lib.filterAttrs (_: i: hasDesc i && hasHand i) candidates);
  handWritten = lib.filterAttrs (_: i: hasHand i && !hasDesc i) candidates;

  nameOf = n: d: d.name or (throw "vendomat: input '${n}' exports a vendomat description with no `name`.");
  byName = lib.groupBy (x: x.name) (lib.mapAttrsToList (n: i: { input = n; name = nameOf n i.vendomat; }) describedAll);
  clashes = lib.filterAttrs (_: l: lib.length l > 1) byName;

  described =
    if bothInputs != [ ] then
      throw "vendomat: input(s) ${lib.concatMapStringsSep ", " (n: "'${n}'") bothInputs} export both a `vendomat` description and `devenvModules.default`. Export one."
    else if clashes != { } then
      throw "vendomat: two inputs use the same library name:\n${lib.concatStringsSep "\n" (lib.mapAttrsToList (name: l: "  name '${name}': inputs ${lib.concatMapStringsSep ", " (x: "'${x.input}'") l}") clashes)}"
    else describedAll;

  # Build the three modules of one described library. Options live at `vendomat.libs.<name>` in all three targets.
  mkLibModules = inputName: d:
    let
      name = nameOf inputName d;
      hasService = d ? service;
      optionsFor = lib': withService:
        let own = (d.options or (_: { })) lib'; in
        if own ? enable || own ? service
        then throw "vendomat: input '${inputName}': description options must not define `enable` or `service`. Vendomat defines them."
        else own
          // { enable = lib'.mkEnableOption "the ${name} library"; }
          // lib'.optionalAttrs (withService && hasService) { service.enable = lib'.mkEnableOption "the ${name} service"; };
      extraFor = args: (d.extra or (_: { })) args;
      # systemd runs one script: it puts the library packages on PATH, then runs `exec` from the description.
      launcher = pkgs: cfg: pkgs.writeShellScript "${name}-start" ''
        export PATH=${lib.makeBinPath (d.packages pkgs)}:$PATH
        exec ${(d.service { inherit pkgs cfg; }).exec}
      '';

      hmModule = { config, lib, pkgs, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
        {
          options.vendomat.libs.${name} = optionsFor lib true;
          config = lib.mkIf cfg.enable (lib.mkMerge [
            { home.packages = d.packages pkgs; }
            (lib.optionalAttrs hasService (lib.mkIf cfg.service.enable {
              systemd.user.services.${name} = {
                Unit.Description = "${name} (Vendomat)";
                Service.ExecStart = "${launcher pkgs cfg}";
                Install.WantedBy = [ "default.target" ];
              };
            }))
            (ex.homeManager or { })
          ]);
        };

      nixosModule = { config, lib, pkgs, options, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
        {
          options.vendomat.libs.${name} = optionsFor lib true;
          config = lib.mkMerge [
            (lib.mkIf cfg.enable (lib.mkMerge [
              { environment.systemPackages = d.packages pkgs; }
              (lib.optionalAttrs hasService (lib.mkIf cfg.service.enable {
                systemd.services.${name} = {
                  description = "${name} (Vendomat)";
                  wantedBy = [ "multi-user.target" ];
                  serviceConfig.ExecStart = "${launcher pkgs cfg}";
                };
              }))
              (ex.nixos or { })
            ]))
            # The Home Manager face rides along only when the host imports the Home Manager NixOS module.
            (lib.optionalAttrs (options ? home-manager) { home-manager.sharedModules = [ hmModule ]; })
          ];
        };

      devenvModule = { config, lib, pkgs, ... }:
        let cfg = config.vendomat.libs.${name}; ex = extraFor { inherit cfg pkgs lib; }; in
        {
          options.vendomat.libs.${name} = optionsFor lib false;
          config = lib.mkIf cfg.enable (lib.mkMerge [
            { packages = d.packages pkgs; }
            (lib.optionalAttrs hasService { processes.${name}.exec = (d.service { inherit pkgs cfg; }).exec; })
            (ex.devenv or { })
          ]);
        };
    in
    { devenv = devenvModule; nixos = nixosModule; homeManager = hmModule; };

  built = lib.mapAttrs (n: i: mkLibModules n i.vendomat) described;
  libNixosModules = lib.mapAttrsToList
    (n: m: lib.setDefaultModuleLocation "inputs.${n}.vendomat (nixos)" m.nixos)
    built;
  # ---- end builder ---------------------------------------------------------------------------------

  # Q2: pin check against devenv.lock.
  checkScript = pkgs.writeShellScript "vendomat-check" ''
    set -euo pipefail
    lock="''${DEVENV_ROOT:-$PWD}/devenv.lock"
    if [ ! -f "$lock" ]; then
      echo "vendomat: no devenv.lock at $lock; run 'devenv update'" >&2
      exit 1
    fi
    bad=$(${pkgs.jq}/bin/jq -r '
      .nodes | to_entries[]
      | select(.value.original.type? == "git")
      | select(((.value.original.ref // "") | startswith("refs/tags/")) | not)
      | "  input node \(.key): \(.value.original.url) ref=\(.value.original.ref // "<none>")"
    ' "$lock")
    if [ -n "$bad" ]; then
      echo "vendomat: refusing to enter the shell. These git inputs are not pinned to a tag:" >&2
      echo "$bad" >&2
      echo "vendomat: set '?ref=refs/tags/<tag>' on each url in devenv.yaml, then run 'devenv update'." >&2
      echo "vendomat: to turn this check off, set vendomat.check.enable = false in devenv.nix." >&2
      exit 1
    fi
    echo "vendomat: all git inputs are pinned to tags"
  '';

  # Q2: the same check in Nix. Evaluation reads devenv.lock from the workspace (`config.devenv.root` is the workspace path).
  lockPath = "${config.devenv.root}/devenv.lock";
  unpinned =
    if builtins.pathExists lockPath
    then
      lib.filterAttrs
        (_: node:
          (node.original.type or "") == "git"
          && !(lib.hasPrefix "refs/tags/" (node.original.ref or "")))
        (builtins.fromJSON (builtins.readFile lockPath)).nodes
    else { };
  unpinnedText = lib.concatStringsSep "\n" (lib.mapAttrsToList
    (k: n: "  input node ${k}: ${n.original.url} ref=${n.original.ref or "<none>"}") unpinned);

  # Q3: push the roots that `devenv build` prints to an Attic cache.
  pushScript = pkgs.writeShellScriptBin "vendomat-push" ''
    set -euo pipefail
    cache="''${1:-${toString cfg.cache.name}}"
    roots=$(devenv build | ${pkgs.jq}/bin/jq -r '.[]')
    if [ -z "$roots" ]; then
      echo "vendomat-push: devenv build produced no store paths" >&2
      exit 1
    fi
    echo "vendomat-push: pushing to cache '$cache':" >&2
    echo "$roots" >&2
    printf '%s\n' "$roots" | ${cfg.cache.attic} push "$cache" --stdin
  '';

  guardKey = host: "vendomat-guard:${host}";
  directDefs = host: lib.filter
    (d: builtins.isAttrs d.value && d.value ? ${host} && (d.value.${host}.nixos or null) != null
      && (d.value.${host}.nixos.key or null) != guardKey host)
    options.machines.definitionsWithLocations;

  # Q7: NixOS module that checks disk and filesystem devices against the inventory for one host.
  # It lives in `assertions`, so `devenv build machines.<host>.build.nixos` fails at evaluation.
  guardModule = host: { config, lib, ... }:
    let
      disks = cfg.inventory.${host}.disks or { };
      targets = lib.mapAttrsToList (_: d: d.byId) (lib.filterAttrs (_: d: d.role == "install-target") disks);
      diskDevices = lib.mapAttrsToList (n: d: { name = n; device = d.device or null; }) config.disko.devices.disk;
      badDisks = lib.filter (d: d.device == null || !(lib.elem d.device targets)) diskDevices;
      isBadFsDevice = dev:
        dev != null
        && (lib.hasPrefix "/dev/disk/by-partlabel/" dev
            || builtins.match "/dev/sd[a-z]+[0-9]*" dev != null
            || builtins.match "/dev/nvme[0-9]+n[0-9]+(p[0-9]+)?" dev != null);
      badFs = lib.filterAttrs (_: fs: isBadFsDevice (fs.device or null)) config.fileSystems;
    in
    {
      assertions = [
        {
          assertion = directDefs host == [ ];
          message = "vendomat guard (${host}): machines.${host}.nixos is also defined outside vendomat.inventory.${host}.nixos. Move that module to vendomat.inventory.${host}.nixos.";
        }
        {
          assertion = badDisks == [ ];
          message = ''
            vendomat guard (${host}): disko disk device is not a by-id path listed with role "install-target" in vendomat.inventory.${host}.disks:
            ${lib.concatMapStringsSep "\n" (d: "  disko.devices.disk.${d.name}.device = ${toString d.device}") badDisks}
            allowed: ${toString targets}'';
        }
        {
          assertion = badFs == { };
          message = ''
            vendomat guard (${host}): fileSystems device uses by-partlabel or a kernel name (/dev/sd*, /dev/nvme*). Use by-uuid:
            ${lib.concatStringsSep "\n" (lib.mapAttrsToList (mp: fs: "  fileSystems.\"${mp}\".device = ${fs.device}") badFs)}'';
        }
      ];
    };
in
{
  imports =
    (lib.mapAttrsToList
      (n: i: lib.setDefaultModuleLocation "inputs.${n}.devenvModules.default" i.devenvModules.default)
      handWritten)
    ++ (lib.mapAttrsToList
      (n: m: lib.setDefaultModuleLocation "inputs.${n}.vendomat (devenv)" m.devenv)
      built);

  options.vendomat = {
    inventory = lib.mkOption {
      default = { };
      description = "Per host disk inventory. A host listed here gets the guard in machines.<host>.nixos.";
      type = lib.types.attrsOf (lib.types.submodule {
        options.nixos = lib.mkOption {
          type = lib.types.deferredModule;
          default = { };
          description = "The NixOS module of the host. Write it here, not in machines.<host>.nixos, so the guard and the module combine.";
        };
        options.disks = lib.mkOption {
          default = { };
          type = lib.types.attrsOf (lib.types.submodule {
            options = {
              byId = lib.mkOption { type = lib.types.str; description = "Full /dev/disk/by-id/ path."; };
              role = lib.mkOption { type = lib.types.enum [ "install-target" "keep" ]; };
            };
          });
        };
      });
    };

    # Q5: host paths, exported as VENDOMAT_PATH_<NAME>.
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

    # Q4: store path of every flake input except self (self is the workspace directory, not a store path).
    exportInputPaths = lib.mkEnableOption "outputs.vendomat.inputPaths, a derivation that lists and references every input source";
    inputPaths = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      readOnly = true;
      default = lib.mapAttrs (_: i: i.sourceInfo.outPath or "${i}") (lib.filterAttrs (n: i: n != "self" && i ? outPath) inputs);
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
      description = "Fail shell entry when a git input in devenv.lock is not pinned to a tag.";
    };
  };

  config = lib.mkMerge [ {
    machines = lib.mapAttrs (host: h: { nixos = { key = guardKey host; imports = [ (guardModule host) ] ++ libNixosModules ++ [ h.nixos ]; }; }) cfg.inventory;
    # Any other definition of machines.<host>.nixos can drop the guard without an error, because the option type
    # merges attribute sets shallowly. Refuse it.
    assertions = lib.mapAttrsToList
      (host: _: {
        assertion = directDefs host == [ ];
        message = "vendomat: machines.${host}.nixos is defined outside vendomat.inventory.${host}.nixos (in ${toString (map (d: d.file) (directDefs host))}). That can remove the guard. Move the module to vendomat.inventory.${host}.nixos.";
      })
      cfg.inventory;
  } {
    # Q6: automatic profiles. devenv activates hostname.<name> and user.<name> for the current host and user.
    # mkDefault lets a workspace override the values.
    profiles.hostname.server.module = { env.VENDOMAT_HOST = lib.mkDefault "server"; };
    profiles.hostname.laptop.module = { env.VENDOMAT_HOST = lib.mkDefault "laptop"; };
    profiles.user.andrew.module = { env.VENDOMAT_USER = lib.mkDefault "andrew"; };
    profiles.user.nobody-else.module = { env.VENDOMAT_USER = lib.mkDefault "nobody-else"; };
  } {
    env = lib.mapAttrs'
      (n: v: lib.nameValuePair "VENDOMAT_PATH_${lib.toUpper (builtins.replaceStrings [ "-" "." ] [ "_" "_" ] n)}" v)
      cfg.paths;
  } (lib.mkIf cfg.exportInputPaths {
    # A plain string or a flake input under `outputs` breaks `devenv build`; a derivation works.
    outputs.vendomat.inputPaths =
      pkgs.writeText "vendomat-input-paths.json" (builtins.toJSON cfg.inputPaths);
  }) (lib.mkIf cfg.cache.push {
    assertions = [{
      assertion = cfg.cache.name != null;
      message = "vendomat.cache.push = true needs vendomat.cache.name.";
    }];
    packages = [ pushScript ];
    tasks."vendomat:push" = {
      description = "Push the roots of `devenv build` to the Attic cache";
      exec = "${pushScript}/bin/vendomat-push";
    };
  }) {
    assertions = lib.optional cfg.check.enable {
      assertion = unpinned == { };
      message = ''
        vendomat: these git inputs are not pinned to a tag:
        ${unpinnedText}
        Set '?ref=refs/tags/<tag>' on each url in devenv.yaml, then run 'devenv update'.
        To turn this check off, set vendomat.check.enable = false in devenv.nix.'';
    };

    tasks."vendomat:check" = lib.mkIf cfg.check.enable {
      description = "Fail when a git input is not pinned to a tag";
      exec = "${checkScript}";
      before = [ "devenv:enterShell" ];
    };
  } ];
}

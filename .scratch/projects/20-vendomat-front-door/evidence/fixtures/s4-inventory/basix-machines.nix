# NON-PRODUCTION spike fixture (project 20, spike S4). All names are PROPOSED, not accepted.
#
# `basix.machines` is a data inventory. This module maps it to two native things:
#   1. `vendomat.inventory.<host>`  (the existing V6 guard, nix/devenv-module/guard.nix)
#   2. `machines.<host>`            (native devenv Machines options of the pinned fork)
# It also builds the NixOS module of the core-role stub from the data alone.
{ config, lib, pkgs, inputs, ... }:
let
  inherit (lib) types mkOption;
  cfg = config.basix.machines;

  # --- value types with a safe data form -------------------------------------------------------
  diskById = lib.mkOptionType {
    name = "diskById";
    description = "an absolute /dev/disk/by-id/<id> path (never a kernel name such as /dev/sda or /dev/nvme0n1)";
    descriptionClass = "noun";
    check = x: builtins.isString x && lib.hasPrefix "/dev/disk/by-id/" x
      && builtins.stringLength x > builtins.stringLength "/dev/disk/by-id/" && !(lib.hasInfix ".." x);
    merge = lib.mergeEqualOption;
  };
  byUuidPath = types.strMatching "/dev/disk/by-(uuid|partuuid)/[A-Za-z0-9-]+";
  hostName = types.strMatching "[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?";
  relPath = (types.addCheck (types.strMatching "[A-Za-z0-9_.][A-Za-z0-9_./-]*") (x: !(lib.hasInfix ".." x)))
    // { description = "a relative path without .."; };

  diskType = types.submodule {
    options = {
      byId = mkOption { type = diskById; description = "Stable identity of the drive."; };
      role = mkOption { type = types.enum [ "install-target" "keep" "existing-system" ]; };
      model = mkOption { type = types.nullOr types.str; default = null; };
      serial = mkOption { type = types.nullOr types.str; default = null; };
      sizeBytes = mkOption { type = types.nullOr types.ints.positive; default = null; };
    };
  };

  moduleRef = types.submodule {
    options = {
      input = mkOption { type = types.str; description = "Name of a devenv input."; };
      path = mkOption { type = relPath; description = "Module file inside that input, for example nixos/modules/....nix"; };
    };
  };

  machineType = types.submodule ({ name, ... }: {
    options = {
      mode = mkOption { type = types.enum [ "fresh-install" "adopt-existing" ]; };
      system = mkOption { type = types.enum [ "x86_64-linux" "aarch64-linux" ]; default = "x86_64-linux"; };
      hostName = mkOption { type = hostName; default = name; };
      stateVersion = mkOption { type = types.strMatching "[0-9]{2}\\.(05|11)"; };
      target.host = mkOption {
        type = types.nullOr (types.strMatching "[a-z_][a-z0-9_-]*@[A-Za-z0-9._-]+(:[0-9]+)?");
        default = null;
        description = "user@host[:port] the controller reaches. Null means no command can reach the machine.";
      };
      disks = mkOption { type = types.attrsOf diskType; default = { }; };
      layout = {
        swapSize = mkOption { type = types.nullOr (types.strMatching "[0-9]+[MG]"); default = null; };
      };
      filesystems = mkOption {
        description = "Adopted host only: the mounts of the running system, by UUID.";
        default = { };
        type = types.attrsOf (types.submodule {
          options = {
            device = mkOption { type = byUuidPath; };
            fsType = mkOption { type = types.str; };
            options = mkOption { type = types.listOf types.str; default = [ "defaults" ]; };
          };
        });
      };
      boot.loader = mkOption { type = types.enum [ "systemd-boot" ]; default = "systemd-boot"; };
      hardware = {
        report = mkOption {
          type = types.nullOr relPath;
          default = null;
          description = "nixos-facter JSON report, a path relative to the project root.";
        };
        initrdModules = mkOption { type = types.listOf types.str; default = [ ]; };
        kernelModules = mkOption { type = types.listOf types.str; default = [ ]; };
        modules = mkOption { type = types.listOf moduleRef; default = [ ]; };
      };
      users = mkOption {
        default = { };
        type = types.attrsOf (types.submodule {
          options = {
            admin = mkOption { type = types.bool; default = false; };
            authorizedKeys = mkOption { type = types.listOf types.str; default = [ ]; };
          };
        });
      };
      timeZone = mkOption { type = types.nullOr types.str; default = null; };
    };
  });

  # --- derived identifiers (stable per host and disk, so the guard accepts by-uuid mounts) --------
  h = s: builtins.hashString "sha256" s;
  sub = lib.substring;
  uuidOf = s: let x = h s; in "${sub 0 8 x}-${sub 8 4 x}-4${sub 13 3 x}-a${sub 17 3 x}-${sub 20 12 x}";
  volIdOf = s: let x = lib.toUpper (h s); in "${sub 0 4 x}-${sub 4 4 x}";

  installTarget = m: lib.filterAttrs (_: d: d.role == "install-target") m.disks;

  # --- the NixOS module of the core-role stub, built from data only -----------------------------
  nixosFor = hostN: m:
    let
      refs = map
        (r: "${inputs.${r.input} or (throw "basix.machines.${hostN}.hardware.modules: input \"${r.input}\" is not declared in devenv.yaml")}/${r.path}")
        m.hardware.modules;
      fresh = m.mode == "fresh-install";
      targets = installTarget m;
      layoutOf = dn: d:
        let
          pid = p: uuidOf "${hostN}/${dn}/${p}";
          rootFs = uuidOf "${hostN}/${dn}/rootfs";
          espFs = volIdOf "${hostN}/${dn}/esp";
          swapFs = uuidOf "${hostN}/${dn}/swapfs";
        in
        {
          disko.devices.disk.${dn} = {
            type = "disk";
            device = d.byId;
            content = {
              type = "gpt";
              partitions = {
                ESP = {
                  size = "1G"; type = "EF00"; uuid = pid "esp";
                  content = {
                    type = "filesystem"; format = "vfat"; mountpoint = "/boot";
                    mountOptions = [ "fmask=0022" "dmask=0022" ];
                    extraArgs = [ "-i" (lib.replaceStrings [ "-" ] [ "" ] espFs) ];
                  };
                };
              } // lib.optionalAttrs (m.layout.swapSize != null) {
                swap = {
                  size = m.layout.swapSize; uuid = pid "swap";
                  content = { type = "swap"; extraArgs = [ "-U" swapFs ]; };
                };
              } // {
                root = {
                  size = "100%"; uuid = pid "root";
                  content = { type = "filesystem"; format = "ext4"; mountpoint = "/"; extraArgs = [ "-U" rootFs ]; };
                };
              };
            };
          };
          fileSystems."/".device = lib.mkForce "/dev/disk/by-uuid/${rootFs}";
          fileSystems."/boot".device = lib.mkForce "/dev/disk/by-uuid/${espFs}";
          swapDevices = lib.mkIf (m.layout.swapSize != null) (lib.mkForce [ { device = "/dev/disk/by-uuid/${swapFs}"; } ]);
        };
    in
    {
      imports = refs ++ lib.mapAttrsToList layoutOf (lib.optionalAttrs fresh targets);
      config = {
        # Type checks are lazy. This forces every value of the machine record, so a bad value in an
        # option that nothing else reads still stops the build of the system.
        assertions = [{
          assertion = builtins.isString (builtins.toJSON m);
          message = "basix.machines.${hostN}: unreachable";
        }];
        nixpkgs.hostPlatform = m.system;
        networking.hostName = m.hostName;
        system.stateVersion = m.stateVersion;
        boot.loader.systemd-boot.enable = m.boot.loader == "systemd-boot";
        boot.loader.efi.canTouchEfiVariables = false;
        boot.initrd.availableKernelModules = m.hardware.initrdModules;
        boot.kernelModules = m.hardware.kernelModules;
        fileSystems = lib.mapAttrs (_: f: { inherit (f) device fsType options; }) m.filesystems;
        services.openssh = {
          enable = true;
          settings = { PermitRootLogin = "no"; PasswordAuthentication = false; KbdInteractiveAuthentication = false; };
        };
        users.users = lib.mapAttrs
          (_: u: { isNormalUser = true; extraGroups = lib.optional u.admin "wheel"; openssh.authorizedKeys.keys = u.authorizedKeys; })
          m.users;
        time.timeZone = m.timeZone;
      };
    };
in
{
  options.basix.machines = mkOption {
    type = types.attrsOf machineType;
    default = { };
    description = "PROPOSED. The machine inventory of a Basix system workspace.";
  };

  config = {
    assertions = lib.concatLists (lib.mapAttrsToList
      (n: m: [
        {
          assertion = lib.all (r: inputs ? ${r.input}) m.hardware.modules;
          message = "basix.machines.${n}.hardware.modules names an input that devenv.yaml does not declare.";
        }
        {
          assertion = m.mode != "adopt-existing" || m.layout.swapSize == null;
          message = "basix.machines.${n}: layout applies to a fresh-install host only.";
        }
        {
          assertion = m.mode != "fresh-install" || m.filesystems == { };
          message = "basix.machines.${n}: filesystems applies to an adopt-existing host only. A fresh install derives its mounts from its install-target disk.";
        }
      ])
      cfg);

    vendomat.inventory = lib.mapAttrs
      (n: m: { inherit (m) mode disks; nixos = nixosFor n m; })
      cfg;

    machines = lib.mapAttrs
      (n: m: {
        inherit (m) system;
        target.host = m.target.host;
        # null opts out of the nixos-facter input. A string is a path relative to the project root.
        hardware.facter = m.hardware.report;
      })
      cfg;
  };
}

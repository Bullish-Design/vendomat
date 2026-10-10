# Per-host assertions for `machines.<host>.nixos` (VMOD-011, VMOD-016, DISK-009, MACH-015).
#
# The guard is a NixOS module. Its assertions run when `devenv build machines.<host>.build.nixos`
# evaluates the system, before disko or an install can run. `vendomat.check.enable` does not reach
# this file: the opt-out turns off the lock-pin check only.
{ lib }:
let
  kernelName = "/dev/(sd[a-z]+|vd[a-z]+|xvd[a-z]+|hd[a-z]+|nvme[0-9]+n[0-9]+|mmcblk[0-9]+|loop[0-9]+)(p?[0-9]+)?";

  isBadFsDevice = dev:
    dev != null
    && (lib.hasPrefix "/dev/disk/by-partlabel/" dev || builtins.match kernelName dev != null);
in
{
  # `inventory`: the host's entry of `vendomat.inventory`. `direct`: definitions of
  # machines.<host>.nixos outside the inventory.
  mk = { host, inventory, direct }:
    { config, lib, ... }:
    let
      mode = inventory.mode;
      disks = inventory.disks;
      withRole = role: lib.filterAttrs (_: d: d.role == role) disks;
      targets = withRole "install-target";
      existing = withRole "existing-system";
      diskoDisks = config.disko.devices.disk or { };
      targetIds = lib.mapAttrsToList (_: d: d.byId) targets;

      # Each disko disk must be the inventory entry of the same name, with the install-target role.
      badDisks = lib.filterAttrs
        (n: d: !(targets ? ${n} && (d.device or null) == targets.${n}.byId))
        diskoDisks;
      badFs = lib.filterAttrs (_: fs: isBadFsDevice (fs.device or null)) config.fileSystems;
      incomplete = lib.filterAttrs
        (_: d: d.model == null || d.serial == null || d.sizeBytes == null) targets;
      notById = lib.filterAttrs (_: d: !(lib.hasPrefix "/dev/disk/by-id/" d.byId)) disks;
      protectedIds = lib.mapAttrsToList (_: d: d.byId) (lib.filterAttrs (_: d: d.role != "install-target") disks);
      sharedIds = lib.filter (id: lib.elem id protectedIds) targetIds;
      bullet = lib.concatMapStringsSep "\n" (s: "  " + s);
    in
    {
      assertions = [
        {
          assertion = direct == [ ];
          message = "vendomat guard (${host}): machines.${host}.nixos is also defined outside vendomat.inventory.${host}.nixos (in ${toString (map (d: d.file) direct)}). That can drop the guard. Move the module to vendomat.inventory.${host}.nixos.";
        }
        {
          assertion = notById == { };
          message = "vendomat guard (${host}): inventory disks must be /dev/disk/by-id/ paths: ${toString (lib.attrNames notById)}.";
        }
        {
          assertion = sharedIds == [ ];
          message = "vendomat guard (${host}): an install-target has the same by-id path as a keep or existing-system disk: ${toString sharedIds}.";
        }
        # --- fresh-install ---------------------------------------------------------------------
        {
          assertion = mode != "fresh-install" || targets != { };
          message = "vendomat guard (${host}): a fresh-install host needs a disk with role \"install-target\" in vendomat.inventory.${host}.disks.";
        }
        {
          assertion = mode != "fresh-install" || existing == { };
          message = "vendomat guard (${host}): a fresh-install host cannot have a disk with role \"existing-system\": ${toString (lib.attrNames existing)}.";
        }
        {
          assertion = mode != "fresh-install" || badDisks == { };
          message = ''
            vendomat guard (${host}): a disko disk is not an install-target of the inventory. Each disko disk name must equal an inventory disk name, and its device must equal that disk's byId:
            ${bullet (lib.mapAttrsToList (n: d: "disko.devices.disk.${n}.device = ${toString (d.device or null)}") badDisks)}
            install-target disks: ${toString (lib.attrNames targets)}'';
        }
        {
          assertion = mode != "fresh-install" || incomplete == { };
          message = "vendomat guard (${host}): an install-target needs model, serial, and sizeBytes in the inventory (the preflight checks them): ${toString (lib.attrNames incomplete)}.";
        }
        # --- adopt-existing --------------------------------------------------------------------
        {
          assertion = mode != "adopt-existing" || diskoDisks == { };
          message = "vendomat guard (${host}): an adopt-existing host must declare no disko.devices.disk. Found: ${toString (lib.attrNames diskoDisks)}.";
        }
        {
          assertion = mode != "adopt-existing" || targets == { };
          message = "vendomat guard (${host}): an adopt-existing host cannot have an install-target disk: ${toString (lib.attrNames targets)}.";
        }
        {
          assertion = mode != "adopt-existing" || existing != { };
          message = "vendomat guard (${host}): an adopt-existing host needs a disk with role \"existing-system\" in vendomat.inventory.${host}.disks.";
        }
        # --- both ------------------------------------------------------------------------------
        {
          assertion = badFs == { };
          message = ''
            vendomat guard (${host}): a fileSystems device uses by-partlabel or a kernel name (/dev/sd*, /dev/nvme*, ...). Use /dev/disk/by-uuid/, /dev/disk/by-partuuid/, or a mapped device:
            ${bullet (lib.mapAttrsToList (mp: fs: "fileSystems.\"${mp}\".device = ${fs.device}") badFs)}'';
        }
      ];
    };
}

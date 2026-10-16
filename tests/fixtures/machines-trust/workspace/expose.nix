# Fixture only. It exposes a bootable EFI disk image for each machine, built from the machine's own
# NixOS evaluation. `devenv build outputs.diskAlpha` makes the image of `alpha`.
{ config, lib, ... }:
let
  image = name:
    let ev = config.machines.${name}._nixosEval; in
    import (ev.pkgs.path + "/nixos/lib/make-disk-image.nix") {
      inherit lib;
      inherit (ev) pkgs config;
      format = "qcow2";
      partitionTableType = "efi";
      diskSize = "auto";
      additionalSpace = "4096M";
      touchEFIVars = false;
      installBootLoader = true;
      copyChannel = false;
      label = "nixos";
    };
in
{
  outputs.diskAlpha = image "alpha";
  outputs.diskBeta = image "beta";
}

# Fixture only. It exposes a bootable EFI disk image of machine `box`, built from the machine's
# own NixOS evaluation (W2 common/expose.nix). `devenv build outputs.disk` makes it.
{ config, lib, ... }:
let
  ev = config.machines.box._nixosEval;
in
{
  outputs.disk = import (ev.pkgs.path + "/nixos/lib/make-disk-image.nix") {
    inherit lib;
    inherit (ev) pkgs config;
    format = "qcow2";
    partitionTableType = "efi";
    diskSize = "auto";
    additionalSpace = "6144M";
    touchEFIVars = false;
    installBootLoader = true;
    copyChannel = false;
    label = "nixos";
  };
}

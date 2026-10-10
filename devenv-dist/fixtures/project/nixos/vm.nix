# NixOS module of the disposable fixture VM. It names the VM's own target
# disk by its virtio serial. It never names a host disk.
{ lib, ... }:
{
  networking.hostName = "vmfresh";
  disko.devices.disk.main = {
    device = "/dev/disk/by-id/virtio-TARGETDISK";
    type = "disk";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "512M";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
        };
        root = {
          size = "100%";
          content = { type = "filesystem"; format = "ext4"; mountpoint = "/"; };
        };
      };
    };
  };
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = false;
  boot.loader.timeout = 1;
  boot.kernelParams = [ "console=ttyS0" ];
  boot.initrd.availableKernelModules = [ "virtio_pci" "virtio_blk" "nvme" "xhci_pci" "ahci" ];
  services.openssh = {
    enable = true;
    settings.PermitRootLogin = "prohibit-password";
    settings.PasswordAuthentication = false;
  };
  users.users.root.openssh.authorizedKeys.keyFiles = [ ../vm/id_ed25519.pub ];
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nix.settings.trusted-users = [ "root" ];
  environment.etc."vendomat-fixture-marker".text = "GENERATION-1\n";
  services.getty.autologinUser = "root";
  system.stateVersion = "26.05";
}

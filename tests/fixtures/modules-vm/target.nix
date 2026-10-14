# Machine with a disko layout for the `build.iso` boot check. The disk is selected by id.
# The check attaches a blank image file with this serial. Nothing runs disko against it.
{ lib, ... }: {
  disko.devices.disk.main = {
    device = "/dev/disk/by-id/virtio-vd-target";
    type = "disk";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "512M";
          type = "EF00";
          content = { type = "filesystem"; format = "vfat"; mountpoint = "/boot"; mountOptions = [ "umask=0077" ]; };
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
  boot.loader.timeout = 3;
  boot.kernelParams = [ "console=ttyS0" ];
  networking.hostName = "target";
  services.openssh.enable = true;
  services.openssh.settings.PermitRootLogin = "prohibit-password";
  system.stateVersion = "26.11";
}

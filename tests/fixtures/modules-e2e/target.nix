# T3 target machine. The disk is selected by by-id. Test-only public key (no private key, no secret).
{ pkgs, lib, ... }: {
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
  users.users.root.openssh.authorizedKeys.keys = [ "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFWN7LCZBX1Eh9oguUjtwZO60fTkDhYOddDlDMF/yomD w2-test-only" ];
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  system.stateVersion = "26.11";
}

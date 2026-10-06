{ inputs, ... }:

{
  machines.v4P0 = {
    system = "x86_64-linux";
    target.host = "root@v4-p0.invalid";
    hardware.facter = null;
    nixos = { pkgs, ... }: {
      imports = [ inputs.disko.nixosModules.disko ];

      boot.loader.grub.devices = [ "nodev" ];
      fileSystems."/" = {
        device = "/dev/disk/by-label/v4-p0-root";
        fsType = "ext4";
      };

      networking.hostName = "v4-p0";
      system.stateVersion = "24.11";
      environment.systemPackages = [ pkgs.hello ];
    };
  };

  machines.v4P0User = {
    home-manager = {
      home.username = "andrew";
      home.homeDirectory = "/home/andrew";
      home.stateVersion = "24.11";
      programs.git.enable = true;
    };
  };
}

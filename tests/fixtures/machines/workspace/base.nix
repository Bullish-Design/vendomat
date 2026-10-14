# Fixture only. The base of the test machine `box`: boot, network, SSH, a user for the commands,
# and a local binary cache. The hatch file `devenv.nix` holds the part that each test changes.
{ pkgs, lib, modulesPath, ... }:
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  boot.loader.timeout = 3;
  boot.kernelParams = [ "console=ttyS0" ];
  fileSystems."/" = { device = "/dev/disk/by-label/nixos"; fsType = "ext4"; };
  fileSystems."/boot" = { device = "/dev/disk/by-label/ESP"; fsType = "vfat"; };
  networking.hostName = "box";
  networking.useDHCP = lib.mkDefault true;

  # The test harness drives the machine over SSH. The keys are one-run keys of the harness.
  services.openssh.enable = true;
  services.openssh.settings.PermitRootLogin = "prohibit-password";
  users.users.root.openssh.authorizedKeys.keys = [ (lib.removeSuffix "\n" (builtins.readFile ./ssh-key.pub)) ];
  # The user who runs `vendomat apply`. Activation goes through /run/wrappers/bin/sudo.
  users.users.tester = {
    isNormalUser = true;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [ (lib.removeSuffix "\n" (builtins.readFile ./ssh-key.pub)) ];
  };
  security.sudo.wheelNeedsPassword = false;

  # No network leaves the machine. The only cache is the harness cache, reached at 10.0.2.100.
  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    substituters = lib.mkForce [ "http://10.0.2.100:5000" ];
    trusted-public-keys = lib.mkForce [ (lib.removeSuffix "\n" (builtins.readFile ./cache-key.pub)) ];
    connect-timeout = 3;
    # The NixOS toplevel sets allowSubstitutes = false. The harness cache holds it, so use it.
    always-allow-substitutes = true;
  };
  environment.systemPackages = [ pkgs.devenv pkgs.git pkgs.jq pkgs.curl ];
  system.stateVersion = "26.11";
}

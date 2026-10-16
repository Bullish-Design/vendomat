# Fixture only. The base of both test machines: boot, SSH, a user for the commands, a local binary
# cache on the user-mode network, and a private link `lan0` between the two machines. The catalog sets
# the host name and the sharing module (Harmonia, the key unit, the peers, the firewall).
{ pkgs, lib, config, modulesPath, ... }:
let
  # The two machines of the link: name, address, and the MAC address of the link card.
  lan = {
    alpha = { ip = "10.77.0.1"; mac = "52:54:00:77:00:01"; };
    beta = { ip = "10.77.0.2"; mac = "52:54:00:77:00:02"; };
  };
  me = lan.${config.networking.hostName};
in
{
  imports = [ (modulesPath + "/profiles/qemu-guest.nix") ];
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  boot.loader.timeout = 3;
  boot.kernelParams = [ "console=ttyS0" ];
  fileSystems."/" = { device = "/dev/disk/by-label/nixos"; fsType = "ext4"; };
  fileSystems."/boot" = { device = "/dev/disk/by-label/ESP"; fsType = "vfat"; };
  networking.useDHCP = lib.mkDefault true;

  # The private link. QEMU joins the two second cards. The card gets the stable name `lan0`, and the
  # catalog key `trustedInterfaces` names it. A name resolves through /etc/hosts, as a DNS name or a
  # tailnet name would on a real network.
  services.udev.extraRules = ''
    SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="${me.mac}", NAME="lan0"
  '';
  networking.interfaces.lan0.ipv4.addresses = [ { address = me.ip; prefixLength = 24; } ];
  networking.hosts = lib.mapAttrs' (name: v: lib.nameValuePair v.ip [ name ]) lan;

  # The test harness drives the machines over SSH. The keys are keys of the harness.
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

  # No network leaves the machines. The only outside cache is the harness cache, reached at
  # 10.0.2.100. The sharing module adds the peer cache with `extra-substituters` and
  # `extra-trusted-public-keys`, so these two lists must not hold a peer.
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

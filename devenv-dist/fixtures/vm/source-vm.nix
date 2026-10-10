# Disposable source VM for the install fixture. The patched devenv installs
# the fixture machine onto the second virtio disk of this VM (serial
# TARGETDISK). The VM never sees a host disk.
{ modulesPath, lib, pkgs, ... }:
let
  pubkey = lib.removeSuffix "\n" (builtins.readFile (builtins.getEnv "VM_PUBKEY_FILE"));
  port = lib.toInt (builtins.getEnv "VM_SSH_PORT");
in
{
  imports = [ "${modulesPath}/virtualisation/qemu-vm.nix" ];
  networking.hostName = "vmsource";
  virtualisation = {
    memorySize = 4096;
    cores = 4;
    diskSize = 20480;
    graphics = false;
    useNixStoreImage = true;
    writableStore = true;
    forwardPorts = [{
      from = "host";
      host.address = "127.0.0.1";
      host.port = port;
      guest.port = 22;
    }];
  };
  services.openssh = {
    enable = true;
    settings.PermitRootLogin = "prohibit-password";
    settings.PasswordAuthentication = false;
  };
  users.users.root.openssh.authorizedKeys.keys = [ pubkey ];
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nix.settings.trusted-users = [ "root" ];
  environment.systemPackages = with pkgs; [ efibootmgr util-linux ];
  system.stateVersion = "26.05";
}

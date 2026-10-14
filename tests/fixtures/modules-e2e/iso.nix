# T2 installer ISO machine (test-only public key).
{ pkgs, lib, modulesPath, ... }: {
  imports = [ (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix") ];
  boot.kernelParams = [ "console=ttyS0" ];
  services.openssh.enable = true;
  users.users.root.openssh.authorizedKeys.keys = [ "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFWN7LCZBX1Eh9oguUjtwZO60fTkDhYOddDlDMF/yomD w2-test-only" ];
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  isoImage.isoName = lib.mkForce "w2-installer.iso";
  system.stateVersion = "26.11";
}

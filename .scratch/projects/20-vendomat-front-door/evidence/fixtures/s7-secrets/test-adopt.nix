# NON-PRODUCTION fixture for spike S7. Task 5: an adopted host. A running NixOS node with no
# Basix receives a Basix core closure from a controller, then a later secret. Test-only keys.
# The Basix closure is a specialisation of the node, so it carries the test backdoor. The node
# store is shared with the host, so `nix copy` of that closure is a no-op here. A second,
# controller-only path proves that the copy route moves new paths.
{ keys, spkgs, ... }:
let
  marker = spkgs.writeText "s7-controller-only-marker" "s7 marker, not in any node closure\n";
in
{
  name = "s7-adopted-host";
  nodes.controller = { pkgs, nodes, ... }: {
    environment.systemPackages = [ pkgs.openssh ];
    virtualisation.additionalPaths = [
      marker
      nodes.adopted.specialisation.basix.configuration.system.build.toplevel
    ];
    nix.settings.experimental-features = [ "nix-command" ];
  };
  nodes.adopted = { pkgs, ... }: {
    # Baseline: a plain NixOS host. It has sshd and the admin key. It has no Basix.
    services.openssh = {
      enable = true;
      settings = { PasswordAuthentication = false; PermitRootLogin = "prohibit-password"; };
    };
    users.users.root.openssh.authorizedKeys.keys = [ (builtins.readFile "${keys}/admin.pub") ];
    nix.settings.trusted-users = [ "root" ];
    nix.settings.experimental-features = [ "nix-command" ];
    virtualisation.emptyDiskImages = [ 64 64 ]; # vdb: formatted, never mounted. vdc: blank.
    environment.systemPackages = [ pkgs.util-linux pkgs.e2fsprogs pkgs.audit ];
    security.audit = {
      enable = true;
      rules = [ "-a always,exit -F arch=b64 -S execve -k s7exec" ];
    };
    security.auditd.enable = true;
    specialisation.basix.configuration = {
      imports = [ ./basix-core.nix ./basix-dep.nix ];
      basix.adminKeys = [ (builtins.readFile "${keys}/admin.pub") ];
    };
  };
  testScript = builtins.replaceStrings [ "@KEYS@" "@MARKER@" ] [ "${keys}" "${marker}" ]
    (builtins.readFile ./test-adopt.py);
}

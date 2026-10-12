# NON-PRODUCTION fixture for spike S7. Spike A: keyless core boot, route 1 delivery,
# rotation, recovery, and route 3 (SecretSpec on the host). Test-only keys.
{ lib, keys, ... }:
{
  name = "s7-keyless-secrets";
  # The driver cannot talk to a node through ssh. Plain consoles stay on the backdoor.
  nodes.controller = { pkgs, ... }: {
    environment.systemPackages = [ pkgs.openssh ];
  };
  nodes.target = { pkgs, ... }: {
    imports = [ ./basix-core.nix ./basix-dep.nix ];
    basix.adminKeys = [ (builtins.readFile "${keys}/admin.pub") ];
    # Route 3 arrives as a later configuration. The core does not hold SecretSpec.
    specialisation.route3.configuration = { imports = [ ./basix-route3.nix ]; };
  };
  testScript = builtins.replaceStrings [ "@KEYS@" ] [ "${keys}" ] (builtins.readFile ./test-a.py);
}

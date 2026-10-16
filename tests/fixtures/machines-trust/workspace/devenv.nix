# The hatch file of the fixture workspace. The catalog (`vendomat/devenv`) makes the machines from
# vendomat.yaml and wires the sharing module. This file adds only what a test VM needs.
{ inputs, ... }:
let
  box = {
    system = "x86_64-linux";
    nixos = {
      imports = [ ./base.nix ];
      # The test machines build offline, so they keep the input sources in their own store. A path
      # input is a plain string without context, so storePath adds the context.
      system.extraDependencies = map (i: builtins.storePath (toString i)) [
        inputs.nixpkgs
        inputs.disko
        inputs.nixos-facter-modules
      ];
    };
  };
in
{
  imports = [ ./expose.nix ];
  cachix.enable = false; # the test machines have no network
  machines.alpha = box;
  machines.beta = box;
}

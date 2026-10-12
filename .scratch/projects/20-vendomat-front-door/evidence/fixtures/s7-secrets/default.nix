# NON-PRODUCTION fixture for spike S7 (project 20). Test-only keys and values. Never deploy.
# Entry: nix build --no-link --print-out-paths -f default.nix <attr>.driver
# Attributes: a (keyless core, route 1, route 3), adopt (adopted host).
let
  nixpkgs = builtins.getFlake "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
  pkgs = nixpkgs.legacyPackages.x86_64-linux;
  keys = import ./keys.nix pkgs;
  mk = file: pkgs.testers.runNixOSTest {
    imports = [ file ];
    _module.args = { inherit keys; spkgs = pkgs; };
  };
in
{
  inherit keys;
  a = mk ./test-a.nix;
  adopt = mk ./test-adopt.nix;
}

{
  description = "knappy: a demo library with a Vendomat description. It has no Vendomat input.";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";

  outputs = { self, nixpkgs }:
    let
      forAll = nixpkgs.lib.genAttrs [ "x86_64-linux" ];
    in
    {
      packages = forAll (system: {
        default = nixpkgs.legacyPackages.${system}.writeShellScriptBin "knappy" ''
          echo "knappy $*"
          [ "$1" = serve ] && exec sleep 3600
        '';
      });

      vendomat = {
        name = "knappy";
        packages = pkgs: [ self.packages.${pkgs.stdenv.hostPlatform.system}.default ];
        options = lib: {
          port = lib.mkOption { type = lib.types.port; default = 8080; description = "Listen port."; };
        };
        service = { pkgs, cfg }: { exec = "knappy serve --port ${toString cfg.port}"; };
        extra = { cfg, pkgs, lib }: {
          devenv.env.KNAPPY_EXTRA = "devenv";
          nixos.networking.firewall.allowedTCPPorts = [ cfg.port ];
          homeManager.home.sessionVariables.KNAPPY_EXTRA = "home-manager";
        };
      };
    };
}

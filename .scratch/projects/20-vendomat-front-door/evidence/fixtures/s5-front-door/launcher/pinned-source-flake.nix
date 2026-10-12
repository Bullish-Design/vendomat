# S5 fixture, NON-PRODUCTION. A fake "Vendomat source" whose package is a one-line script.
{
  inputs.nixpkgs.url = "github:cachix/devenv-nixpkgs/256551e45f6303e142ab4a98be1bf243feb77dc0";
  outputs = { self, nixpkgs }:
    let pkgs = nixpkgs.legacyPackages.x86_64-linux; in {
      packages.x86_64-linux.vendomat = pkgs.writeShellScriptBin "vendomat" ''
        echo "PINNED-BUILD ran: $* (protocol=''${VENDOMAT_LAUNCHER_PROTOCOL:-unset})"
      '';
    };
}

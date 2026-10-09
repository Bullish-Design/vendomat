{
  description = "Vendomat core: pinned, patched devenv CLI";

  # Fork = cachix/devenv v2.4.0 + a5fd551a (machines install) + latest-version 2.4.0
  #        + PR 3244 (reuse locked inputs) + isRelease = true.
  # Production URL: git://server/devenv?ref=refs/tags/v2.4.0-vendomat.1
  inputs.devenv-fork.url = "git+git://127.0.0.1:29418/devenv?ref=refs/tags/v2.4.0-vendomat.1";

  # Do NOT add `follows` for nixpkgs or nix: the fork's own flake.lock pins
  # the toolchain, and Attic holds the build for exactly that lock.

  outputs = { self, devenv-fork }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: builtins.listToAttrs (map (s: { name = s; value = f s; }) systems);
    in
    {
      packages = forAll (system: {
        devenv = devenv-fork.packages.${system}.devenv;
        default = devenv-fork.packages.${system}.devenv;
      });

      overlays.default = final: prev: {
        devenv = devenv-fork.packages.${final.stdenv.hostPlatform.system}.devenv;
      };

      nixosModules.default = { pkgs, ... }: {
        environment.systemPackages = [ devenv-fork.packages.${pkgs.stdenv.hostPlatform.system}.devenv ];
        # Let the builder pull the fork's closure from the owner's Attic.
        # nix.settings.extra-substituters = [ "https://attic.example/vendomat" ];
      };
    };
}

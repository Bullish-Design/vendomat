{
  description = "vendomat — vend personal native (maturin/PyO3) libraries: build once, share the wheels via the Nix store";

  inputs = {
    # Match the devenv stack the consuming repos use.
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";

    # Personal native libraries, as plain source trees (flake = false). git+file is used so
    # only git-tracked files are copied into the store — crucially this excludes Pyjutsu's
    # multi-GB `target/` (untracked) that a `path:` input would eagerly copy. Working-tree
    # edits to tracked files are still picked up (a dirty source just builds a fresh wheel).
    #
    # Paths follow the repoman `repoman_dev_root` convention (~/Documents/Projects). On
    # another machine, override with `--override-input pyjutsu git+file:///path/to/Pyjutsu`.
    pyjutsu = {
      url = "git+file:///home/andrew/Documents/Projects/Pyjutsu";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, ... }@inputs:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      # The build recipe, per system.
      lib = forAllSystems (pkgs: {
        mkMaturinWheel = import ./lib/mkMaturinWheel.nix {
          inherit pkgs;
          python = pkgs.python313;
        };
      });

      # The built artifacts: one wheel per lib, plus a combined wheelhouse dir.
      packages = forAllSystems (pkgs:
        let
          system = pkgs.stdenv.system;
          mkWheel = self.lib.${system}.mkMaturinWheel;

          pyjutsu-wheel = mkWheel {
            pname = "pyjutsu";
            src = inputs.pyjutsu;
          };
        in
        {
          inherit pyjutsu-wheel;

          # A single directory of every vendored wheel — this is what UV_FIND_LINKS points at.
          wheelhouse = pkgs.symlinkJoin {
            name = "vendomat-wheelhouse";
            paths = [ pyjutsu-wheel ];
          };

          default = self.packages.${system}.wheelhouse;
        });

      # The devenv module any repo imports to consume the wheelhouse. Consumers import it
      # path-wise via `imports: [ vendomat/modules ]` (devenv resolves that to
      # modules/devenv.nix); this output is kept for flake-level discoverability.
      devenvModules.default = import ./modules/devenv.nix;
    };
}

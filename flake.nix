{
  description = "Vendomat: write a project flake from vendomat.toml, and keep source clones.";

  # The only input. Vendomat packages no one else's tools: every tool is its own flake input of
  # the machine or project that wants it.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      # The devenv module (DEL-019). A workspace imports `inputs.vendomat.devenvModules.default`.
      devenvModules.default = import ./nix/devenv-module self;

      # The command line. A host delta installs it as `packages.<system>.vendomat` (DEL-006, DEL-007).
      # There is no `default`: `.default` must not name the CLI package.
      packages = forAllSystems (pkgs: {
        vendomat = pkgs.python313.pkgs.buildPythonApplication {
          pname = "vendomat";
          # Read from pyproject.toml, so the package name and the generated-flake header agree.
          version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
          pyproject = true;
          # Flake source = git-tracked files only.
          src = ./.;
          build-system = [ pkgs.python313.pkgs.hatchling ];
          dependencies = [ pkgs.python313.pkgs.typer ];
          # Tests run through Testee in the devenv shell, not at build time.
          doCheck = false;
          meta.mainProgram = "vendomat";
        };
      });
    };
}

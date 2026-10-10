{
  description = "Vendomat: write project inputs from vendomat.toml, check pins, push outputs, and keep source clones.";

  # The only input. Vendomat packages no one else's tools: every tool is its own flake input of
  # the machine or project that wants it. The revision is the plain nixpkgs that this release tests
  # (MACH-018). `src/vendomat/defaults.py` names the same revision, and a check compares them.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      # The devenv module (DEL-019). A workspace imports `inputs.vendomat.devenvModules.default`.
      devenvModules.default = import ./nix/devenv-module self;

      packages = forAllSystems (pkgs:
        let
          # The command line (DEL-006, DEL-007). There is no `default`: `.default` must not name it.
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
            # The direnv function `use_vendomat` ships with the command (PRE-009).
            postInstall = ''
              install -Dm644 direnv/vendomat.sh $out/share/vendomat/direnv/vendomat.sh
            '';
            meta.mainProgram = "vendomat";
          };
        in
        {
          inherit vendomat;

          # The host launcher (DEL-017). A host installs it as its `vendomat` command, and the
          # command above as the host release. The launcher runs the Vendomat that each workspace's
          # lock pins, and the host release elsewhere. It holds no Vendomat logic of its own.
          launcher = pkgs.runCommand "vendomat-launcher-${vendomat.version}"
            { nativeBuildInputs = [ pkgs.makeWrapper ]; }
            ''
              install -Dm755 ${./launcher/vendomat} $out/bin/vendomat
              substituteInPlace $out/bin/vendomat --replace-fail '@HOST_RELEASE@' '${vendomat}/bin/vendomat'
              wrapProgram $out/bin/vendomat --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.jq pkgs.coreutils ]}
            '';
        });
    };
}

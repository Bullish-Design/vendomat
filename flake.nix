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

      # The pinned fork today: `devenv 2.4.0+fb5d382`, tag `v2.4.0-vendomat.3` (devenv-dist/RESULT).
      # This fixed path holds no store reference.
      defaultFork = "/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv";

      perSystem = forAllSystems (pkgs:
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
              mkdir -p $out/share/vendomat/templates
              cp -r templates/workspace templates/workspace-v6 templates/workspace-registry $out/share/vendomat/templates/
              install -Dm755 templates/workspace-v6/init $out/bin/vendomat-workspace-init
            '';
            meta.mainProgram = "vendomat";
          };

          # The host launcher (DEL-020, DOOR-071). A host installs it as its `vendomat` command, and
          # the command above as the host release. No argument enters the shell of the pinned devenv
          # fork, `new` copies the workspace template, and every other argument passes to the fork.
          # The fork is one value: the path of its bin/devenv.
          mkLauncher = { devenvFork }:
            pkgs.runCommand "vendomat-launcher-${vendomat.version}"
              { nativeBuildInputs = [ pkgs.makeWrapper ]; }
              ''
                install -Dm755 ${./launcher/vendomat} $out/bin/vendomat
                substituteInPlace $out/bin/vendomat \
                  --replace-fail '@HOST_RELEASE@' '${vendomat}/bin/vendomat' \
                  --replace-fail '@DEVENV_FORK@' '${devenvFork}'
                # --suffix: the fork and the host release keep the caller's PATH order.
                wrapProgram $out/bin/vendomat --suffix PATH : ${pkgs.lib.makeBinPath [ pkgs.jq pkgs.coreutils pkgs.findutils ]}
              '';
        in
        { inherit vendomat mkLauncher; });
    in
    {
      # The devenv module (DEL-019). A workspace imports `inputs.vendomat.devenvModules.default`.
      devenvModules.default = import ./nix/devenv-module self;

      packages = nixpkgs.lib.mapAttrs
        (_: built: {
          inherit (built) vendomat;
          # The host launcher with the fork that this release pins by default.
          launcher = built.mkLauncher { devenvFork = defaultFork; };
        })
        perSystem;

      # `lib.<system>.mkLauncher { devenvFork = "${fork}/bin/devenv"; }` builds the launcher for
      # another fork. A host that builds the fork passes its own path, so the store keeps the fork alive.
      lib = nixpkgs.lib.mapAttrs (_: built: { inherit (built) mkLauncher; }) perSystem;
    };
}

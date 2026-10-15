{
  description = "Vendomat: manage workspaces and their devenv catalog.";

  # Two inputs. Vendomat packages no one else's tools: every tool is its own flake input of the
  # machine or project that wants it. `nixpkgs` is the plain revision that this release tests
  # (MACH-018). `src/vendomat/defaults.py` names the same revision, and a check compares them.
  # `devenv` is the module-only devenv fork tag (R41). Workspaces follow it as `vendomat/devenv`.
  # No output of this flake uses it. Its tag and its locked revision are the published pin.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
  inputs.devenv.url = "git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules";

  outputs = { self, nixpkgs, ... }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));

      # The host devenv: `pkgs.devenv` from the pinned nixpkgs, plus the patches in
      # `devenv-dist/binary/patches` (overlay `nix/devenv-overlay.nix`).
      devenvOverlay = import ./nix/devenv-overlay.nix { patchDir = ./devenv-dist/binary/patches; };
      devenvFor = system: (import nixpkgs { inherit system; overlays = [ devenvOverlay ]; }).devenv;

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
            # The workspace template ships with the command; `vendomat new` copies it.
            postInstall = ''
              mkdir -p $out/share/vendomat/templates
              cp -r templates/workspace $out/share/vendomat/templates/
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
      # The overlay that patches `pkgs.devenv`. A host that wants the same binary applies it.
      overlays.devenv = devenvOverlay;

      packages = nixpkgs.lib.mapAttrs
        (system: built: rec {
          inherit (built) vendomat;
          # The patched host devenv binary.
          devenv = devenvFor system;
          # The host launcher with the devenv that this release builds.
          launcher = built.mkLauncher { devenvFork = "${devenv}/bin/devenv"; };
        })
        perSystem;

      # `lib.<system>.mkLauncher { devenvFork = "${fork}/bin/devenv"; }` builds the launcher for
      # another fork. A host that builds the fork passes its own path, so the store keeps the fork alive.
      lib = nixpkgs.lib.mapAttrs (_: built: { inherit (built) mkLauncher; }) perSystem;
    };
}

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
    # Published tags keep the source tracked-files-only while making the flake portable.
    # For local iteration, override this input with `--override-input pyjutsu
    # git+file:///path/to/Pyjutsu`.
    pyjutsu = {
      url = "git+https://github.com/Bullish-Design/Pyjutsu?ref=refs/tags/v0.21.1";
      flake = false;
    };

    # Face D — the shared command closure. Each first-party CLI is a source input, built
    # once as a Nix Python application. THIS LOCK IS AUTHORITATIVE for the toolchain
    # revision in store mode (CONCEPT 03 §8.2, decided 2026-09-07): `repoman.lock` gains
    # no `toolchain:` kind, and a consumer that still names a manager by `path:` fails.
    repoman = {
      url = "git+https://github.com/Bullish-Design/repoman?ref=refs/tags/v0.7.3";
      flake = false;
    };
    copyroom = {
      url = "git+https://github.com/Bullish-Design/copyroom?ref=refs/tags/v0.7.4";
      flake = false;
    };
    docman = {
      url = "git+https://github.com/Bullish-Design/docman?ref=refs/tags/v0.2.0";
      flake = false;
    };
    gitman = {
      url = "git+https://github.com/Bullish-Design/gitman?ref=refs/tags/v0.6.1";
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
        mkArtifact = import ./lib/mkArtifact.nix {
          inherit pkgs;
          python = pkgs.python313;
        };
        # Back-compat alias: the original single-builder entry point (unchanged).
        mkMaturinWheel = import ./lib/mkMaturinWheel.nix {
          inherit pkgs;
          python = pkgs.python313;
        };
        # Face D: build one first-party CLI, and compose a roster of them.
        mkPythonCli = import ./lib/mkPythonCli.nix {
          inherit pkgs;
          python = pkgs.python313;
        };
        mkToolchain = import ./lib/mkToolchain.nix {
          inherit pkgs;
          python = pkgs.python313;
        };
      });

      # The built artifacts: one wheel per lib, plus a combined wheelhouse dir.
      packages = forAllSystems (pkgs:
        let
          system = pkgs.stdenv.system;
          mkArtifact = self.lib.${system}.mkArtifact;
          mkPythonCli = self.lib.${system}.mkPythonCli;
          mkToolchain = self.lib.${system}.mkToolchain;

          pyjutsu-wheel = mkArtifact {
            pname = "pyjutsu";
            src = inputs.pyjutsu;
            builder = "maturinWheel";
          };

          # Face B: the vendomat CLI, delivered to a consumer repo as a package on PATH
          # (DESIGN issue #3 — the zelligate-provisions-zellij pattern), never via the
          # consumer's venv. `modules/devenv.nix` puts this on PATH and runs `vendomat sync`.
          vendomat = pkgs.python313.pkgs.buildPythonApplication {
            pname = "vendomat";
            # Read from pyproject.toml: a hand-written literal here drifted to 0.2.3 while
            # the source was 0.3.1, so every installed pre-push hook named a wrong version.
            version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
            pyproject = true;
            # Flake source = git-tracked files only (excludes .jj/.gitman/.devenv/result).
            src = ./.;
            build-system = [ pkgs.python313.pkgs.hatchling ];
            dependencies = [
              pkgs.python313.pkgs.typer
              pkgs.python313.pkgs.pydantic
              pkgs.python313.pkgs.pyyaml
              pkgs.python313.pkgs.tomli-w
            ];
            # Tests run in the devenv (pytest), not at nix-build time.
            doCheck = false;
          };
          # gitman's native dependency, as a PYTHON PACKAGE built from the wheel this flake
          # already vends. The wheel is the artifact of record; this only installs it. That
          # is what makes gitman's package a pure-Python build for every consumer: the Rust
          # compile happened once, here, and no consumer repeats it.
          pyjutsu-version = (builtins.fromTOML (builtins.readFile "${inputs.pyjutsu}/pyproject.toml")).project.version;
          pyjutsu-package = pkgs.python313.pkgs.buildPythonPackage {
            pname = "pyjutsu";
            version = pyjutsu-version;
            format = "other";
            src = pyjutsu-wheel;
            # The wheel is copied into dist/ under its OWN name and installed from there.
            # A wheel cannot be handed over as `src` directly: the installer parses the
            # file's basename for the distribution metadata, and a store path prefixes
            # that name with a hash, which is not a valid wheel filename.
            dontUnpack = true;
            nativeBuildInputs = [ pkgs.python313.pkgs.pypaInstallHook ];
            installPhase = ''
              runHook preInstall
              mkdir -p dist
              cp ${pyjutsu-wheel}/*.whl dist/
              pypaInstallPhase
              runHook postInstall
            '';
            dependencies = [ pkgs.python313.pkgs.pydantic ];
            doCheck = false;
          };

          # Face D — the roster. Added one tool at a time (CONCEPT 03 §6): a tool is
          # supported only once its package builds, its command resolves to /nix/store,
          # and its doctor runs. Evaluating is not supporting.
          repoman-cli = mkPythonCli {
            pname = "repoman";
            src = inputs.repoman;
          };
          copyroom-cli = mkPythonCli {
            pname = "copyroom";
            src = inputs.copyroom;
            # `demo` (copyroom's `demo:main`) is a generic name and no part of the manager
            # contract. Left in, it would be the roster's first command collision.
            excludeScripts = [ "demo" ];
          };

          docman-cli = mkPythonCli {
            pname = "docman";
            src = inputs.docman;
          };
          gitman-cli = mkPythonCli {
            pname = "gitman";
            src = inputs.gitman;
            # Resolved to the vended wheel, never to an editable sibling checkout
            # (CONCEPT 03 §3.3).
            depMap = { pyjutsu = pyjutsu-package; };
          };

          toolchain = mkToolchain {
            name = "core";
            tools = {
              repoman = repoman-cli;
              copyroom = copyroom-cli;
              docman = docman-cli;
              gitman = gitman-cli;
            };
          };
        in
        {
          inherit pyjutsu-wheel vendomat;

          # Individual command packages, for `nix build` and for the build tests.
          repoman = repoman-cli;
          copyroom = copyroom-cli;
          docman = docman-cli;
          gitman = gitman-cli;
          pyjutsu = pyjutsu-package;
          # The composed closure the devenv module puts on PATH.
          repoman-toolchain-core = toolchain;

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

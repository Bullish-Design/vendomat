{
  description = "vendomat — vend personal native (maturin/PyO3) libraries: build once, share the wheels via the Nix store";

  inputs = {
    # Match the devenv stack the consuming repos use.
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";

    # uv2nix resolves each workspace from its own uv.lock. Keep all three inputs
    # on this flake's nixpkgs and pyproject-nix revisions to avoid a split closure.
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:adisbladis/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };

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
      url = "git+https://github.com/Bullish-Design/repoman?ref=refs/tags/v0.7.5";
      flake = false;
    };
    copyroom = {
      url = "git+https://github.com/Bullish-Design/copyroom?ref=refs/tags/v0.7.7";
      flake = false;
    };
    docman = {
      url = "git+https://github.com/Bullish-Design/docman?ref=refs/tags/v0.2.1";
      flake = false;
    };
    gitman = {
      url = "git+https://github.com/Bullish-Design/gitman?ref=refs/tags/v0.6.2";
      flake = false;
    };
    # templateer is on the roster because devman's changelog group calls
    # `templateer generate` as a COMMAND, never as an import. It was the one roster
    # tool still coming from the mutable shelf venv, so a login shell got four
    # commands from the store and this one from nowhere.
    templateer = {
      url = "git+https://github.com/Bullish-Design/templateer_v2?ref=refs/tags/v0.4.1";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }@inputs:
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
        # For a dependency nixpkgs cannot supply: install the published PyPI wheel.
        # Bound to a package SET by its caller, because every use is inside an overlay.
        mkPypiWheel = py: import ./lib/mkPypiWheel.nix { inherit pkgs py; };
      });

      # The built artifacts: one wheel per lib, plus a combined wheelhouse dir.
      packages = forAllSystems (pkgs:
        let
          system = pkgs.stdenv.system;
          mkArtifact = self.lib.${system}.mkArtifact;
          mkPythonCli = self.lib.${system}.mkPythonCli;
          mkToolchain = self.lib.${system}.mkToolchain;

          # templateer's dependency closure, for the parts nixpkgs cannot supply. Every
          # entry states why; see the file header before assuming one is still needed.
          #
          # A SEPARATE interpreter, not a global override: the pydantic-ai 2.x line this
          # needs would otherwise rebuild every other roster tool and every consumer of
          # pkgs.python313 for no reason. The roster is a closure of independent
          # applications, so one tool may sit on a different package set — what the
          # closure joins on is command names, not a shared site-packages.
          pythonTemplateer = pkgs.python313.override {
            self = pythonTemplateer;
            packageOverrides = import ./pkgs/templateer-deps.nix {
              inherit pkgs;
              mkPypiWheel = self.lib.${system}.mkPypiWheel;
            };
          };
          mkTemplateerCli = import ./lib/mkPythonCli.nix {
            inherit pkgs;
            python = pythonTemplateer;
          };

          templateerWorkspace = uv2nix.lib.workspace.loadWorkspace {
            workspaceRoot = inputs.templateer;
          };
          templateerPythonSet = (pkgs.callPackage pyproject-nix.build.packages {
            python = pkgs.python313;
          }).overrideScope (pkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            (templateerWorkspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
          ]);
          templateerUv2nix = templateerPythonSet.mkVirtualEnv "templateer-uv2nix" templateerWorkspace.deps.default;
          templateerVersion = (builtins.fromTOML (builtins.readFile "${inputs.templateer}/pyproject.toml")).project.version;

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

          # The `[openai]` extra is folded into the pydantic-ai-slim entry itself:
          # mkPythonCli resolves a PEP 508 head and drops the extra, so an extra's
          # dependencies must be named by the derivation that stands for the head.
          templateer-cli = mkTemplateerCli {
            pname = "templateer";
            src = inputs.templateer;
            depMap = {
              minijinja = pythonTemplateer.pkgs.minijinja;
              pydantic-ai-slim = pythonTemplateer.pkgs.pydantic-ai-slim;
            };
          };

          templateer-uv2nix-cli = templateerUv2nix.overrideAttrs (old: {
            pname = "templateer";
            version = templateerVersion;
            passthru = (old.passthru or { }) // {
              commands = [ "templateer" ];
              pythonVersion = pkgs.python313.pythonVersion;
            };
          });

          mkUv2nixCli = { pname, src, excludeScripts ? [ ] }:
            let
              workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = src; };
              pythonSet = (pkgs.callPackage pyproject-nix.build.packages {
                python = pkgs.python313;
              }).overrideScope (pkgs.lib.composeManyExtensions [
                pyproject-build-systems.overlays.default
                (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
              ]);
              virtualEnv = pythonSet.mkVirtualEnv "${pname}-uv2nix" workspace.deps.default;
              project = (builtins.fromTOML (builtins.readFile "${src}/pyproject.toml")).project;
              commands = pkgs.lib.subtractLists excludeScripts (builtins.attrNames (project.scripts or { }));
            in
            virtualEnv.overrideAttrs (old: {
              inherit pname;
              version = project.version;
              passthru = (old.passthru or { }) // {
                inherit commands;
                pythonVersion = pkgs.python313.pythonVersion;
              };
            });

          repoman-uv2nix-cli = mkUv2nixCli { pname = "repoman"; src = inputs.repoman; };
          copyroom-uv2nix-cli = mkUv2nixCli {
            pname = "copyroom";
            src = inputs.copyroom;
            excludeScripts = [ "demo" ];
          };
          docman-uv2nix-cli = mkUv2nixCli { pname = "docman"; src = inputs.docman; };
          gitman-uv2nix-cli = mkUv2nixCli { pname = "gitman"; src = inputs.gitman; };

          toolchain = mkToolchain {
            name = "core";
            tools = {
              repoman = repoman-uv2nix-cli;
              copyroom = copyroom-uv2nix-cli;
              docman = docman-uv2nix-cli;
              gitman = gitman-uv2nix-cli;
              templateer = templateer-uv2nix-cli;
            };
          };
        in
        {
          inherit pyjutsu-wheel vendomat;

          # Individual command packages, for `nix build` and for the build tests.
          repoman = repoman-uv2nix-cli;
          copyroom = copyroom-uv2nix-cli;
          docman = docman-uv2nix-cli;
          gitman = gitman-uv2nix-cli;
          repoman-hand-pinned = repoman-cli;
          copyroom-hand-pinned = copyroom-cli;
          docman-hand-pinned = docman-cli;
          gitman-hand-pinned = gitman-cli;
            # Prototype decision: the public templateer package now exercises uv.lock.
            # Keep the hand-pinned derivation available for an apples-to-apples build.
            templateer = templateer-uv2nix-cli;
            templateer-hand-pinned = templateer-cli;
            templateer-uv2nix = templateer-uv2nix-cli;
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

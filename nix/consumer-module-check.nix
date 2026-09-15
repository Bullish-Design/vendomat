# The consumer-module check (project 039, phase 1).
#
# Two claims must hold before a consumer migration can start:
#
#   1. the installed module is a well-formed devenv module — `builtins.functionArgs`
#      resolves and the file imports;
#   2. the module evaluates against a repository that declares no `vendomat.toml`,
#      and the defaults resolve. A repository with no manifest must still get a
#      working shell, because the central overlay imports this module everywhere.
#
# The check evaluates the real module with `lib.evalModules` and a stub of the
# devenv option surface the module writes to. It uses the flake-input fallback:
# a build sandbox has no `/run/current-system/sw/share/vendomat/machine.json`.
{ pkgs, lib, vendomatModule, vendomatPackage }:

let
  system = pkgs.stdenv.system;

  fakePackages = {
    wheelhouse = pkgs.runCommand "fake-wheelhouse" { } "mkdir -p $out";
    vendomat = pkgs.runCommand "fake-vendomat" { } ''
      mkdir -p $out/bin
      touch $out/bin/vendomat
      chmod +x $out/bin/vendomat
    '';
    "repoman-toolchain-core" = pkgs.runCommand "fake-toolchain" { } ''
      mkdir -p $out/bin $out/share/vendomat
      echo '{"roster":"core"}' > $out/share/vendomat/toolchain.json
    '';
  };

  fakeInputs = {
    vendomat = fakeSource // {
      packages = { ${system} = fakePackages; };
    };
  };

  fakeSource = pkgs.runCommand "fake-vendomat-source" { } "mkdir -p $out/vendor";

  # The devenv option surface this module writes to. `devenv.root` is the only
  # input the module reads back.
  devenvStub = root: { lib, ... }: {
    options.assertions = lib.mkOption {
      type = lib.types.listOf (lib.types.submodule {
        options.assertion = lib.mkOption { type = lib.types.bool; };
        options.message = lib.mkOption { type = lib.types.str; };
      });
      default = [ ];
    };
    options.devenv.root = lib.mkOption {
      type = lib.types.str;
      default = root;
    };
    options.env = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
    };
    options.packages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
    };
    options.tasks = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule {
        options.exec = lib.mkOption { type = lib.types.str; };
      });
      default = { };
    };
    options.scripts = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule {
        options.description = lib.mkOption { type = lib.types.str; default = ""; };
        options.exec = lib.mkOption { type = lib.types.str; };
      });
      default = { };
    };
    options.enterShell = lib.mkOption {
      type = lib.types.lines;
      default = "";
    };
    config.devenv.root = root;
  };

  evaluate = root: lib.evalModules {
    modules = [
      vendomatModule
      (devenvStub root)
      {
        _module.args.pkgs = pkgs;
        _module.args.inputs = fakeInputs;
      }
    ];
  };

  # A repository with no manifest. Every option falls back to its default.
  noManifestRoot = pkgs.runCommand "fixture-no-manifest" { } "mkdir -p $out";
  noManifest = (evaluate (toString noManifestRoot)).config;

  # A repository that opts in to the knowledge face only. This proves the module
  # reads `vendomat.toml` and not only its own option defaults.
  optInRoot = pkgs.runCommand "fixture-knowledge" { } ''
    mkdir -p $out
    cat > $out/vendomat.toml <<'EOF'
    [knowledge]
    enable = true
    skillsDir = ".claude/skills"
    EOF
  '';
  optIn = (evaluate (toString optInRoot)).config;

  # The claims, decided in Nix so a failure names the claim instead of breaking a
  # shell script with an unbalanced quote.
  expectedToolchainBin = "${fakePackages."repoman-toolchain-core"}/bin";
  claims = [
    (lib.assertMsg (noManifest.env.REPOMAN_TOOLCHAIN_BIN == expectedToolchainBin)
      "default config must resolve the toolchain bin from the flake input")
    (lib.assertMsg (noManifest.tasks ? "vendor:toolchain:status")
      "default config must define the toolchain status task")
    (lib.assertMsg (noManifest.packages != [ ])
      "default config must deliver the toolchain package")
    (lib.assertMsg ((optIn.env.VENDOMAT_VENDOR_ROOT or "") == "${fakeSource}/vendor")
      "vendomat.toml [knowledge] enable = true must set the vendor root")
    (lib.assertMsg (!(optIn.env ? UV_FIND_LINKS))
      "the knowledge fixture must not enable Face A")
  ];
  checked = builtins.all (claim: claim) claims;
in
assert checked;
pkgs.runCommand "vendomat-consumer-module-check" { nativeBuildInputs = [ pkgs.nix ]; } ''
  set -euo pipefail
  export HOME=$TMPDIR

  test -f ${vendomatPackage}/share/vendomat/consumer-module.nix
  test -f ${vendomatPackage}/share/vendomat/machine.json

  # The installed file is a well-formed module: `builtins.functionArgs` resolves.
  nix-instantiate --eval --strict --expr \
    "builtins.functionArgs (import ${vendomatPackage}/share/vendomat/consumer-module.nix)" \
    > /dev/null


  # A repository that declares no manifest still evaluates. This is the property
  # the central overlay depends on.
  mkdir -p $out
  echo "consumer module: functionArgs and fixture evaluation ok" > $out/report.txt
''

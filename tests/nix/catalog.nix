# Evaluate the catalog module (devenv/devenv.nix) with stub devenv options and the real Nix parser.
#
# The module reads `vendomat.yaml` in `root` and parses it with devenv/parse.nix. The stub options hold the
# devenv options that the module sets. They stand in for devenv's own modules. A separate check
# (catalog-e2e) runs the module on a real devenv. Run through `tests/test_catalog_module_nix.py`.
#
#   nix-instantiate --extra-experimental-features flakes --eval --strict --json tests/nix/catalog.nix \
#     --argstr root DIR --argstr repo REPO --argstr nixpkgs REV --argstr read summary
#
# `read` picks one of: summary, shell (the text of `enterShell`), explain (the data of `vendomat explain`), root.
#
# Optional arguments:
#   pythons  Comma-separated Python versions of a stub `nixpkgs-python` input. Empty means no such input.
#   extra    Comma-separated Nix files, each one more module (the user's `devenv.nix` in a real workspace).
{ root, repo, nixpkgs, read, pythons ? "", extra ? "" }:
let
  pkgs = import (builtins.getFlake "github:NixOS/nixpkgs/${nixpkgs}") { system = "x86_64-linux"; };
  inherit (pkgs) lib;
  t = lib.types;
  opt = type: default: lib.mkOption { inherit type default; };

  # The devenv options that the module sets.
  stub = {
    options = {
      devenv.root = opt t.str "";
      packages = opt (t.listOf t.package) [ ];
      enterShell = opt t.lines "";
      env = opt (t.attrsOf t.str) { };
      languages.python.enable = opt t.bool false;
      languages.python.version = opt (t.nullOr t.str) null;
      languages.python.uv.enable = opt t.bool false;
      languages.python.uv.sync.enable = opt t.bool false;
      languages.javascript.enable = opt t.bool false;
      languages.javascript.package = opt (t.nullOr t.package) null;
      languages.rust.enable = opt t.bool false;
      languages.rust.channel = opt t.str "nixpkgs";
      languages.rust.version = opt t.str "latest";
      services.postgres.enable = opt t.bool false;
      services.redis.enable = opt t.bool false;
      # The machine options of devenv's machines.nix, as far as the module sets them. `vendomat.mode`
      # is the module half of fork patch 0005.
      machines = opt
        (t.attrsOf (t.submodule ({ name, ... }: {
          options = {
            target.host = opt (t.nullOr t.str) null;
            nixos = opt (t.nullOr t.deferredModule) null;
            hardware.facter = opt (t.nullOr t.str) ".machines/${name}/facter.json";
            vendomat.mode = opt (t.nullOr (t.enum [ "fresh-install" "adopt-existing" ])) null;
          };
        })))
        { };
    };
  };

  # The NixOS options that the machine module sets: the host name, and what the sharing module
  # (devenv/sharing.nix) sets. The stub reads the sharing facts back. A separate check (sharing-vm)
  # builds the real machines.
  sharingFacts = nixos:
    let
      evaluated = lib.evalModules {
        modules = [
          {
            options = {
              networking.hostName = opt t.str "unset";
              networking.firewall.allowedTCPPorts = opt (t.listOf t.int) [ ];
              assertions = opt (t.listOf t.raw) [ ];
              nix.package = opt t.raw null;
              nix.settings = opt (t.attrsOf t.raw) { };
              systemd.tmpfiles.rules = opt (t.listOf t.str) [ ];
              systemd.services = opt (t.attrsOf t.raw) { };
              systemd.sockets = opt (t.attrsOf t.raw) { };
              services.harmonia.cache.enable = opt t.bool false;
              services.harmonia.cache.signKeyPaths = opt (t.listOf t.str) [ ];
            };
            config._module.args = { inherit pkgs; };
          }
          nixos
        ];
      };
      c = evaluated.config;
    in
    {
      hostName = c.networking.hostName;
      serve = c.vendomat.sharing.serve;
      peers = c.vendomat.sharing.peers;
      substituters = c.nix.settings.extra-substituters or [ ];
      keys = c.nix.settings.extra-trusted-public-keys or [ ];
      harmonia = c.services.harmonia.cache.enable;
      keyUnit = c.systemd.services ? vendomat-cache-key;
    };

  inputs =
    if pythons == "" then { }
    else {
      nixpkgs-python.packages.x86_64-linux = lib.genAttrs (lib.splitString "," pythons) (v: v);
    };

  evaluated = lib.evalModules {
    modules = [
      stub
      (import (repo + "/devenv/devenv.nix"))
      {
        config = {
          devenv.root = root;
          _module.args = { inherit pkgs inputs; };
        };
      }
    ] ++ lib.filter (m: m != "") (lib.splitString "," extra);
  };
  config = evaluated.config;

  summary = {
    packages = map (p: p.pname) config.packages;
    inherit (config) env;
    python = config.languages.python;
    javascript = {
      inherit (config.languages.javascript) enable;
      package = if config.languages.javascript.package == null then null else config.languages.javascript.package.name;
    };
    rust = config.languages.rust;
    services = config.services;
    machines = lib.mapAttrs
      (_: m: {
        hostName = if m.nixos == null then null else (sharingFacts m.nixos).hostName;
        host = m.target.host;
        facter = m.hardware.facter;
        mode = m.vendomat.mode;
      })
      config.machines;
    serve = config.vendomat.serve;
    sharing = lib.mapAttrs (_: m: sharingFacts m.nixos) config.machines;
  };
in
{
  # Read the whole summary, the shell entry text, the data of `vendomat explain`, or only `devenv.root`,
  # which no catalog value feeds.
  inherit summary;
  shell = config.enterShell;
  explain = config.vendomat.explain;
  root = config.devenv.root;
}.${read}

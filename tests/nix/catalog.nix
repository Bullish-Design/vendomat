# Evaluate the catalog module (devenv/devenv.nix) with stub devenv options and a stub primop.
#
# The stub primop reads JSON, so the fixture file holds JSON text. This tests the module, not the
# parser: the fork's Rust tests and the fork gates test the parser. Run through
# `tests/test_catalog_module_nix.py`.
#
#   nix-instantiate --extra-experimental-features flakes --eval --strict --json tests/nix/catalog.nix \
#     --argstr root DIR --argstr repo REPO --argstr nixpkgs REV --argstr read summary
{ root, repo, nixpkgs, read }:
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
      env = opt (t.attrsOf t.str) { };
      languages.python.enable = opt t.bool false;
      languages.python.version = opt (t.nullOr t.str) null;
      languages.javascript.enable = opt t.bool false;
      languages.javascript.package = opt (t.nullOr t.package) null;
      languages.rust.enable = opt t.bool false;
      languages.rust.channel = opt t.str "nixpkgs";
      languages.rust.version = opt t.str "latest";
      services.postgres.enable = opt t.bool false;
      services.redis.enable = opt t.bool false;
    };
  };

  evaluated = lib.evalModules {
    modules = [
      stub
      (import (repo + "/devenv/devenv.nix"))
      {
        config = {
          devenv.root = root;
          _module.args = {
            inherit pkgs;
            inputs = { };
            devenvPrimops.vendomatFromYAML = _name: builtins.fromJSON;
          };
        };
      }
    ];
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
  };
in
{
  # Read the whole summary, or only `devenv.root`, which no catalog value feeds.
  inherit summary;
  root = config.devenv.root;
}.${read}

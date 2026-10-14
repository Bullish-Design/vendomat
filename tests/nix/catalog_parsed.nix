# Read `vendomat.yaml` through the catalog module and print the parsed tree as JSON (fixture F1 of the
# `catalog-e2e` check).
#
# The module is called as a function with stub arguments. It reads the file itself with builtins.readFile and
# parses it once, inside the module. The module system is not used: it reads `_module.check`, and that check stops
# on a schema fault that a parser corpus case holds on purpose.
#
#   nix-instantiate --extra-experimental-features flakes --eval --strict --json tests/nix/catalog_parsed.nix \
#     --argstr dir WORKSPACE --argstr catalog DIR_OF_devenv.nix --argstr nixpkgs REV
{ dir, catalog, nixpkgs }:
let
  lib = (builtins.getFlake "github:NixOS/nixpkgs/${nixpkgs}").lib;
  module = import (catalog + "/devenv.nix") {
    inherit lib;
    config.devenv.root = dir;
    options = { };
    pkgs = { stdenv.hostPlatform.system = "x86_64-linux"; };
    inputs = { };
  };
in
module.options.vendomat.parsed.default

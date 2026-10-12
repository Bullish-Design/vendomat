# NON-PRODUCTION spike fixture (project 20, spike S4).
# Simulates the template devenv.nix plus the generic Vendomat data reader.
#
# `.vendomat/config.json` stands in for the file that Vendomat would generate from vendomat.yaml.
# Each top-level key is an option path. There is no translation table.
{ lib, ... }:
let
  data = builtins.fromJSON (builtins.readFile ./.vendomat/config.json);
in
{
  imports = [
    (import ./nix/devenv-module/default.nix { })   # the existing V6 module (guard), copied by the run script with ../../preflight
    ./basix-machines.nix
  ];
  config = builtins.removeAttrs data [ "inputs" "imports" ];
}

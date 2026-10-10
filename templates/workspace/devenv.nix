# Template-owned workspace wiring. Change routine module values in vendomat.toml.
{ inputs, ... }:
let
  registry = builtins.fromTOML (builtins.readFile ./vendomat.toml);
in
{
  imports = [ inputs.vendomat.devenvModules.default ];
  vendomat.settings = registry.settings or { };
}

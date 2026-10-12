# S2 location test (NON-PRODUCTION): _file vs lib.setDefaultModuleLocation vs none vs imports+_file.
{ case }:
let
  nixpkgsPath = "/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source";
  lib = import (nixpkgsPath + "/lib");
  optionsModule = { options.t.str = lib.mkOption { type = lib.types.str; }; };
  libm = { _file = "/store/lib/module.nix"; config.t.str = "lib"; };
  mods = {
    file = { _file = "vendomat.yaml"; config.t.str = "yaml"; };
    setdefault = lib.setDefaultModuleLocation "vendomat.yaml" { config.t.str = "yaml"; };
    setdefault-fn = lib.setDefaultModuleLocation "vendomat.yaml" ({ ... }: { config.t.str = "yaml"; });
    none = { config.t.str = "yaml"; };
    nested = { _file = "vendomat.yaml"; imports = [ { config.t.str = "yaml"; } ]; };
    perkey = { imports = [ { _file = "vendomat.yaml:12 (key t.str)"; config.t.str = "yaml"; } ]; };
    unsafe-file = { _file = "/home/u/ws/vendomat.yaml"; config.t.str = "yaml"; };
    relfile = { _file = ./misc.nix; config.t.str = "yaml"; };
  };
in (lib.evalModules { modules = [ optionsModule libm mods.${case} ]; }).config.t.str

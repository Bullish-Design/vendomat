# Catalog module fixture (NON-PRODUCTION). Reads ./vendomat.toml via config.devenv.root.
{ lib, config, options, pkgs, ... }:
let
  t = lib.types;
  cfg = config.vendomat;
  # Eager check: names every option whose value fails its type (tryEval per option).
  bad = lib.filter (o: !(builtins.tryEval (builtins.deepSeq o.value true)).success)
    (lib.collect lib.isOption options.vendomat);
  describe = o:
    let d = lib.head o.definitionsWithLocations; in
    "vendomat.toml: `${lib.showOption (lib.tail o.loc)}' must be ${o.type.description}, found ${builtins.typeOf d.value} ${builtins.toJSON d.value}";
  guard = v: if bad != [ ] then throw ("\n" + lib.concatMapStringsSep "\n" describe bad) else v;
  lookup = name: lib.attrByPath (lib.splitString "." name) null pkgs;
in {
  options.vendomat = {
    programs = lib.mkOption { type = t.listOf t.str; default = [ ]; };
    languages.python.enable = lib.mkOption { type = t.bool; default = false; };
    languages.python.version = lib.mkOption { type = t.nullOr t.str; default = null; };
    services.postgres.enable = lib.mkOption { type = t.bool; default = false; };
    env = lib.mkOption { type = t.attrsOf t.str; default = { }; };
  };

  imports = [
    ({ config, ... }: {
      _file = "vendomat.toml";
      config.vendomat = builtins.fromTOML (builtins.readFile (config.devenv.root + "/vendomat.toml"));
    })
  ];

  config = {
    packages = guard (map (n: lookup n) cfg.programs);
    env = guard cfg.env;
    languages.python.enable = guard cfg.languages.python.enable;
    services.postgres.enable = guard cfg.services.postgres.enable;
  };
}

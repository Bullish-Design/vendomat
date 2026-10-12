# Catalog module fixture (NON-PRODUCTION), F2 spike. Data arrives as strings only; types give meaning.
{ lib, config, options, pkgs, devenvPrimops, ... }:
let
  t = lib.types;
  cfg = config.vendomat;
  # "true"/"false" text becomes a bool. Anything else fails the bool type.
  boolText = t.coercedTo (t.enum [ "true" "false" ]) (s: s == "true") t.bool;
  bad = lib.filter (o: !(builtins.tryEval (builtins.deepSeq o.value true)).success)
    (lib.collect lib.isOption options.vendomat);
  describe = o:
    let d = lib.head o.definitionsWithLocations; in
    "vendomat.yaml: `${lib.showOption (lib.tail o.loc)}' must be ${o.type.description}, found ${builtins.typeOf d.value} ${builtins.toJSON d.value}";
  guard = v: if bad != [ ] then throw ("\n" + lib.concatMapStringsSep "\n" describe bad) else v;
  lookup = name: lib.attrByPath (lib.splitString "." name) null pkgs;
in {
  options.vendomat = {
    programs = lib.mkOption { type = t.listOf t.str; default = [ ]; };
    languages.python.enable = lib.mkOption { type = boolText; default = false; };
    languages.python.version = lib.mkOption { type = t.nullOr t.str; default = null; };
    services.postgres.enable = lib.mkOption { type = boolText; default = false; };
    env = lib.mkOption { type = t.attrsOf t.str; default = { }; };
    name = lib.mkOption { type = t.nullOr t.str; default = null; };
  };

  imports = [
    ({ config, ... }: {
      _file = "vendomat.yaml";
      config.vendomat = let p = config.devenv.root + "/vendomat.yaml"; in if builtins.pathExists p then devenvPrimops.vendomatFromYAML "vendomat.yaml" (builtins.readFile p) else {};
    })
  ];

  config = {
    packages = guard (map (n: lookup n) cfg.programs);
    # The shell prints these so a test can see the current data.
    env = guard (cfg.env // {
      VM_PY_VERSION = if cfg.languages.python.version == null then "unset" else cfg.languages.python.version;
      VM_PY_ENABLE = lib.boolToString cfg.languages.python.enable;
      VM_NAME = if cfg.name == null then "unset" else cfg.name;
      VM_PROGRAMS = lib.concatStringsSep "," cfg.programs;
    });
    languages.python.enable = guard cfg.languages.python.enable;
    services.postgres.enable = guard cfg.services.postgres.enable;
  };
}

# S2 probe module (NON-PRODUCTION): declares custom options and a JSON-safe probe.
{ pkgs, lib, config, ... }: {
  options.vtest = {
    path = lib.mkOption { type = lib.types.path; default = "/dflt"; };
    pathstr = lib.mkOption { type = lib.types.str; default = "dflt"; };
    nul = lib.mkOption { type = lib.types.nullOr lib.types.str; default = "dflt"; };
    str = lib.mkOption { type = lib.types.str; default = "dflt"; };
    apps = lib.mkOption { type = lib.types.attrsOf (lib.types.submodule { options.pkg = lib.mkOption { type = lib.types.package; }; }); default = { }; };
    settings = lib.mkOption { type = (pkgs.formats.json { }).type; default = { }; };
    fn = lib.mkOption { type = lib.types.functionTo lib.types.str; default = _: "dflt"; };
    probe = lib.mkOption { type = lib.types.raw; readOnly = true; };
  };
  config.vtest.probe = {
    packages = lib.filter (n: lib.any (x: lib.hasPrefix x n) [ "hello" "jq" "cowsay" "python3.14-requests" ]) (map (p: p.name) config.packages);
    pyname = config.languages.python.package.name;
    pyenable = config.languages.python.enable;
    env = config.env.FOO;
    path = toString config.vtest.path;
    pathstr = config.vtest.pathstr;
    nul = config.vtest.nul;
    str = config.vtest.str;
    apps = lib.mapAttrs (_: a: a.pkg.name) config.vtest.apps;
    settings = config.vtest.settings;
    fn = config.vtest.fn "x";
  };
}

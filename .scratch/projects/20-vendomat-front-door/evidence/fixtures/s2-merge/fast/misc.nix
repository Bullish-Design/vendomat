# S2 misc fast tests (NON-PRODUCTION): nix-instantiate --eval --strict --json misc.nix --argstr case NAME
{ case }:
let
  nixpkgsPath = "/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source";
  lib = import (nixpkgsPath + "/lib");
  pkgs = import nixpkgsPath { system = "x86_64-linux"; };
  inherit (lib) mkOption types;
  fmt = pkgs.formats.json { };
  optionsModule = {
    _file = "lib-options.nix";
    options.t = {
      str = mkOption { type = types.str; };
      path = mkOption { type = types.path; };
      nul = mkOption { type = types.nullOr types.str; default = "dflt"; };
      nulpkg = mkOption { type = types.nullOr types.package; default = null; };
      fn = mkOption { type = types.functionTo types.str; };
      apps = mkOption { type = types.attrsOf (types.submodule { options.pkg = mkOption { type = types.package; }; options.args = mkOption { type = types.listOf types.str; default = [ ]; }; }); default = { }; };
      lsub = mkOption { type = types.listOf (types.submodule { options.pkg = mkOption { type = types.package; }; }); default = [ ]; };
      settings = mkOption { type = fmt.type; default = { }; };
      svc = mkOption { type = types.submodule { freeformType = fmt.type; options.enable = mkOption { type = types.bool; default = false; }; }; default = { }; };
      shellpkg = mkOption { type = types.shellPackage; };
      coerced = mkOption { type = types.coercedTo types.str (s: [ s ]) (types.listOf types.str); default = [ ]; };
      listnull = mkOption { type = types.listOf (types.nullOr types.str); default = [ ]; };
      either = mkOption { type = types.either types.str types.int; };
      port = mkOption { type = types.port; };
    };
  };
  conv = ty: v:
    let n = ty.name; in
    if v == null then v
    else if n == "package" then lib.getAttrFromPath (lib.splitString "." v) pkgs
    else if n == "listOf" then map (conv ty.nestedTypes.elemType) v
    else if n == "attrsOf" then lib.mapAttrs (_: conv ty.nestedTypes.elemType) v
    else if n == "nullOr" then conv ty.nestedTypes.elemType v
    else if n == "submodule" then
      let so = ty.getSubOptions [ ]; in
      lib.mapAttrs (k: x: if so ? ${k} && lib.isOption so.${k} then conv so.${k}.type x else x) v
    else v;
  walk = options: path: d:
    let o = lib.attrByPath path null options; in
    if o != null && lib.isOption o then conv o.type d
    else if builtins.isAttrs d then lib.mapAttrs (k: x: walk options (path ++ [ k ]) x) d
    else d;
  gen = json: { options, ... }: { _file = "vendomat.yaml"; config = walk options [ ] (builtins.fromJSON json); };
  ev = mods: (lib.evalModules { modules = [ optionsModule ] ++ mods; }).config.t;
  libm = c: { _file = "lib-defs.nix"; config.t = c; };
  cases = {
    # package mechanism
    pkg-nested = (ev [ (gen ''{"t":{"apps":{"a":{"pkg":"jq","args":["x"]},"b":{"pkg":"python3Packages.requests"}},"lsub":[{"pkg":"hello"}],"nulpkg":"cowsay"}}'') ]);
    pkg-nested-names = let c = ev [ (gen ''{"t":{"apps":{"a":{"pkg":"jq"},"b":{"pkg":"python3Packages.requests"}},"lsub":[{"pkg":"hello"}],"nulpkg":"cowsay"}}'') ]; in
      { apps = lib.mapAttrs (_: a: a.pkg.name) c.apps; lsub = map (a: a.pkg.name) c.lsub; nulpkg = c.nulpkg.name; };
    pkg-null = (ev [ (gen ''{"t":{"nulpkg":null}}'') ]).nulpkg;
    pkg-missing = (ev [ (gen ''{"t":{"apps":{"a":{"pkg":"nosuchpkg"}}}}'') ]).apps.a.pkg.name;
    pkg-missing-dotted = (ev [ (gen ''{"t":{"apps":{"a":{"pkg":"python3Packages.nosuch"}}}}'') ]).apps.a.pkg.name;
    pkg-nonpackage-attr = (ev [ (gen ''{"t":{"apps":{"a":{"pkg":"lib"}}}}'') ]).apps.a.pkg.name;
    pkg-number = (ev [ (gen ''{"t":{"apps":{"a":{"pkg":5}}}}'') ]).apps.a.pkg.name;
    shellpkg-name = types.shellPackage.name;
    shellpkg = (ev [ (gen ''{"t":{"shellpkg":"bash"}}'') ]).shellpkg.name;
    # paths
    path-rel = (ev [ (gen ''{"t":{"path":"./src"}}'') ]).path;
    path-abs = (ev [ (gen ''{"t":{"path":"/etc/src"}}'') ]).path;
    path-nixpath = toString (ev [ { config.t.path = ./misc.nix; } ]).path;
    path-name = types.path.name;
    str-rel = (ev [ (gen ''{"t":{"str":"./src"}}'') ]).str;
    # null
    null-nullable = (ev [ (gen ''{"t":{"nul":null}}'') ]).nul;
    null-nonnull = (ev [ (gen ''{"t":{"str":null}}'') ]).str;
    null-in-list = (ev [ (gen ''{"t":{"listnull":["a",null]}}'') ]).listnull;
    # nonexistent
    nope-leaf = (ev [ (gen ''{"t":{"nope":1,"str":"x"}}'') ]).str;
    nope-top = (lib.evalModules { modules = [ optionsModule (gen ''{"nope":{"x":1},"t":{"str":"x"}}'') ]; }).config.t.str;
    nope-nested = (ev [ (gen ''{"t":{"str":{"deeper":1}}}'') ]).str;
    nope-type-mismatch-attrs = (ev [ (gen ''{"t":{"svc":"notattrs"}}'') ]).svc;
    # freeform
    free-settings = (ev [ (gen ''{"t":{"settings":{"a":1,"b":{"c":[1,2],"d":null},"e":"s"}}}'') ]).settings;
    free-svc = (ev [ (gen ''{"t":{"svc":{"enable":true,"extra":{"a":[1,2]},"n":1.5}}}'') ]).svc;
    free-merge-lib = (ev [ (libm { settings = { a = 0; b.c = [ 0 ]; z = "lib"; }; }) (gen ''{"t":{"settings":{"b":{"c":[1,2]},"e":"s"}}}'') ]).settings;
    free-conflict = (ev [ (libm { settings = { a = 0; }; }) (gen ''{"t":{"settings":{"a":1}}}'') ]).settings;
    free-svc-conflict = (ev [ (libm { svc.extra = "x"; }) (gen ''{"t":{"svc":{"extra":"y"}}}'') ]).svc;
    free-typo = (ev [ (gen ''{"t":{"svc":{"enabel":true}}}'') ]).svc.enable;
    # function and other unsupported
    fn-string = (ev [ (gen ''{"t":{"fn":"x"}}'') ]).fn "a";
    fn-attrs = (ev [ (gen ''{"t":{"fn":{"a":"x"}}}'') ]).fn "a";
    # type mismatch texts
    str-int = (ev [ (gen ''{"t":{"str":5}}'') ]).str;
    port-big = (ev [ (gen ''{"t":{"port":70000}}'') ]).port;
    either-ok = (ev [ (gen ''{"t":{"either":5}}'') ]).either;
    either-bad = (ev [ (gen ''{"t":{"either":true}}'') ]).either;
    coerced = (ev [ (gen ''{"t":{"coerced":"x"}}'') ]).coerced;
    float-int = (ev [ (gen ''{"t":{"port":8080.0}}'') ]).port;
  };
in
cases.${case}

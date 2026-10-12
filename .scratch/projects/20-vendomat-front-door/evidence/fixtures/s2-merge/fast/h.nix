# S2 fast matrix harness (NON-PRODUCTION). Plain lib.evalModules on the pinned nixpkgs lib.
# Usage: nix eval --impure --json --file h.nix --argstr mode matrix --argstr type str
{ mode ? "matrix", type ? "str", L ? "p", G ? "p", U ? "0", genMode ? "whole", order ? "lgu" }:
let
  nixpkgsPath = "/nix/store/n9vyi4yygxdfdmjimmfzqsg802m16s0a-source";
  lib = import (nixpkgsPath + "/lib");
  pkgs = import nixpkgsPath { system = "x86_64-linux"; };
  inherit (lib) mkOption types;

  # ---- option declarations (the "library" declares; also includes real-ish types)
  optionsModule = {
    _file = "lib-options.nix";
    options.t = {
      str = mkOption { type = types.str; };
      int = mkOption { type = types.int; };
      bool = mkOption { type = types.bool; };
      enum = mkOption { type = types.enum [ "a" "b" "c" ]; };
      lstr = mkOption { type = types.listOf types.str; };
      lpkg = mkOption { type = types.listOf types.package; };
      astr = mkOption { type = types.attrsOf types.str; };
      sub = mkOption { type = types.submodule { options = { a = mkOption { type = types.int; default = 0; }; b = mkOption { type = types.str; default = "d"; }; }; }; default = { }; };
      nul = mkOption { type = types.nullOr types.str; };
      lines = mkOption { type = types.lines; };
      sep = mkOption { type = types.separatedString ":"; };
      pkg = mkOption { type = types.package; };
    };
  };

  vals = {
    str = { L = "lib"; G = "yaml"; U = "user"; };
    int = { L = 1; G = 2; U = 3; };
    bool = { L = true; G = false; U = true; };
    enum = { L = "a"; G = "b"; U = "c"; };
    lstr = { L = [ "lib" ]; G = [ "yaml" ]; U = [ "user" ]; };
    lpkg = { L = [ pkgs.hello ]; G = [ "jq" ]; U = [ pkgs.cowsay ]; };
    astr = { L = { k = "lib"; l = "L"; }; G = { k = "yaml"; y = "Y"; }; U = { k = "user"; u = "U"; }; };
    sub = { L = { a = 1; b = "lib"; }; G = { a = 2; }; U = { b = "user"; }; };
    nul = { L = "lib"; G = null; U = "user"; };
    lines = { L = "lib"; G = "yaml"; U = "user"; };
    sep = { L = "lib"; G = "yaml"; U = "user"; };
    pkg = { L = pkgs.hello; G = "jq"; U = pkgs.cowsay; };
  };

  wrap = spec: v:
    if spec == "p" then v
    else if spec == "d" then lib.mkDefault v
    else if spec == "f" then lib.mkForce v
    else if spec == "b" then lib.mkBefore v
    else if spec == "a" then lib.mkAfter v
    else if lib.hasPrefix "o" spec then lib.mkOverride (lib.toInt (lib.removePrefix "o" spec)) v
    else throw "bad spec ${spec}";

  # ---- generated module: JSON data, package strings converted via the options tree
  conv = ty: v:
    let n = ty.name; in
    if v == null then v
    else if n == "package" then
      (let p = lib.getAttrFromPath (lib.splitString "." v) pkgs; in p)
    else if n == "listOf" || n == "nonEmptyListOf" then map (conv ty.nestedTypes.elemType) v
    else if n == "attrsOf" || n == "lazyAttrsOf" then lib.mapAttrs (_: conv ty.nestedTypes.elemType) v
    else if n == "nullOr" then conv ty.nestedTypes.elemType v
    else if n == "submodule" then
      let so = ty.getSubOptions [ ]; in
      lib.mapAttrs (k: x: if so ? ${k} && lib.isOption so.${k} then conv so.${k}.type x else x) v
    else v;

  # genMode "leaf": the priority wraps each key of an attrsOf and each field of a submodule.
  wrapDeep = specW: ty: v:
    let n = ty.name; in
    if genMode != "leaf" || v == null then wrap specW v
    else if n == "attrsOf" || n == "lazyAttrsOf" then lib.mapAttrs (_: wrapDeep specW ty.nestedTypes.elemType) v
    else if n == "nullOr" then wrapDeep specW ty.nestedTypes.elemType v
    else if n == "submodule" then
      let so = ty.getSubOptions [ ]; in
      lib.mapAttrs (k: x: if so ? ${k} && lib.isOption so.${k} then wrapDeep specW so.${k}.type x else wrap specW x) v
    else wrap specW v;

  walk = specW: options: path: data:
    let o = lib.attrByPath path null options; in
    if o != null && lib.isOption o then wrapDeep specW o.type (conv o.type data)
    else if builtins.isAttrs data then lib.mapAttrs (k: d: walk specW options (path ++ [ k ]) d) data
    else wrap specW data;

  genModule = specW: jsonText: { options, ... }: {
    _file = "vendomat.yaml";
    config = if specW == "0" then { } else walk specW options [ ] (builtins.fromJSON jsonText);
  };

  userModule = specU: v: { _file = "devenv.nix"; config.t.${type} = if specU == "0" then lib.mkMerge [ ] else wrap specU v; };
  libModule = specL: v: { _file = "lib-defs.nix"; config.t.${type} = if specL == "0" then lib.mkMerge [ ] else wrap specL v; };

  jsonFor = ty: builtins.toJSON { t.${ty} = vals.${ty}.G; };

  show = ty: v:
    if ty == "lpkg" then map (p: p.name) v else if ty == "pkg" then v.name else v;

  evalCase = ty: l: g: u:
    let
      ev = lib.evalModules { modules = [ optionsModule ] ++ map (c: { l = libModule l vals.${ty}.L; g = genModule g (jsonFor ty); u = userModule u vals.${ty}.U; }.${c}) (lib.stringToCharacters order); };
    in show ty ev.config.t.${ty};

  specsL = [ "0" "p" "d" "f" ] ++ lib.optionals (builtins.elem type [ "lstr" "lpkg" "lines" "sep" ]) [ "b" "a" ];
  specsG = [ "0" "p" "o100" "o90" "o75" "o60" "d" "f" ];
  specsU = [ "0" "p" "f" ];
  combos = lib.concatMap (l: lib.concatMap (g: map (u: { inherit l g u; }) specsU) specsG) specsL;
  # Make type-aware: evalModules defines t.${type} only (userModule/libModule use `type`).
in
if mode == "matrix" then
  builtins.listToAttrs (map (c:
    let name = "L${c.l}_G${c.g}_U${c.u}";
        r = builtins.tryEval (builtins.deepSeq (evalCase type c.l c.g c.u) (evalCase type c.l c.g c.u));
    in { inherit name; value = if r.success then r.value else "ERROR"; }) (lib.filter (c: !(c.l == "0" && c.g == "0" && c.u == "0")) combos))
else
  evalCase type L G U

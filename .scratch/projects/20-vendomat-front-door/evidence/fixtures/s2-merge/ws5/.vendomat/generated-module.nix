# S2 prototype of the generated module (NON-PRODUCTION). Reads ./config.json (and optional ./lines.json).
# - package-typed options: a string names a nixpkgs attribute, found with the options tree (no table).
# - _file per top-level key so an error cites vendomat.yaml:<line> and the key.
{ lib, pkgs, options, config, ... }:
let
  data = builtins.fromJSON (builtins.readFile ./config.json);
  lines = if builtins.pathExists ./lines.json then builtins.fromJSON (builtins.readFile ./lines.json) else { };
  fail = keyPath: msg: throw "vendomat.yaml: key `${keyPath}': ${msg}";
  conv = keyPath: ty: v:
    let n = ty.name; in
    if v == null then v
    else if n == "package" then
      (if !builtins.isString v then fail keyPath "a package must be a string that names a nixpkgs attribute"
       else
         let p = lib.attrByPath (lib.splitString "." v) null pkgs; in
         if p == null then fail keyPath "nixpkgs has no attribute `${v}'"
         else if !lib.isDerivation p then fail keyPath "nixpkgs attribute `${v}' is not a package"
         else p)
    else if n == "path" then
      (if builtins.isString v && !lib.hasPrefix "/" v then "${config.devenv.root}/${v}" else v)
    else if n == "listOf" then
      (if builtins.isList v then lib.imap0 (i: conv "${keyPath}[${toString i}]" ty.nestedTypes.elemType) v else v)
    else if n == "attrsOf" || n == "lazyAttrsOf" then
      (if builtins.isAttrs v then lib.mapAttrs (k: conv "${keyPath}.${k}" ty.nestedTypes.elemType) v else v)
    else if n == "nullOr" then conv keyPath ty.nestedTypes.elemType v
    else if n == "submodule" then
      (if builtins.isAttrs v then
        let so = ty.getSubOptions [ ]; in
        lib.mapAttrs (k: x: if so ? ${k} && lib.isOption so.${k} then conv "${keyPath}.${k}" so.${k}.type x else x) v
       else v)
    else v;
  walk = keyPath: path: d:
    let o = lib.attrByPath path null options; in
    if o != null && lib.isOption o then conv keyPath o.type d
    else if builtins.isAttrs d then lib.mapAttrs (k: x: walk (if keyPath == "" then k else "${keyPath}.${k}") (path ++ [ k ]) x) d
    else d;
  top = k: v: {
    _file = "vendomat.yaml" + (if lines ? ${k} then ":${toString lines.${k}}" else "") + " (key ${k})";
    config = walk "" [ ] { ${k} = v; };
  };
in {
  imports = lib.mapAttrsToList top data;
}

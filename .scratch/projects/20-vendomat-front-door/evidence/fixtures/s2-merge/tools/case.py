#!/usr/bin/env python3
"""S2 case writer (NON-PRODUCTION). Writes one real-devenv case into a workspace dir.
usage: case.py WS L G U [fileMode]   (spec tokens: 0 p d f b a oNN) ; fileMode: none|yaml|key
"""
import json, os, sys
ws, L, G, U = sys.argv[1:5]
fm = sys.argv[5] if len(sys.argv) > 5 else "yaml"
opt = sys.argv[6] if len(sys.argv) > 6 else "all"
KEYS = {"env_FOO": "env.FOO", "packages": "packages", "py": "languages.python.enable", "shell": "enterShell", "str": "vtest.str", "int": "vtest.int", "lstr": "vtest.lstr"}

def w(spec, v):
    if spec == "0": return "(lib.mkMerge [ ])"
    f = {"p": "%s", "d": "(lib.mkDefault %s)", "f": "(lib.mkForce %s)", "b": "(lib.mkBefore %s)", "a": "(lib.mkAfter %s)"}.get(spec)
    if f is None:
        f = "(lib.mkOverride %s %%s)" % spec[1:]
    return f % v

TYPES = '''
    str = lib.mkOption { type = lib.types.str; };
    int = lib.mkOption { type = lib.types.int; };
    lstr = lib.mkOption { type = lib.types.listOf lib.types.str; };
    probe = lib.mkOption { type = lib.types.raw; readOnly = true; };
'''
def vals(who):
    # who: lib | user
    return {
        "env.FOO": '"%s"' % who,
        "packages": "[ pkgs.%s ]" % ("hello" if who == "lib" else "cowsay"),
        "languages.python.enable": "true",
        "enterShell": '"echo %s"' % who,
        "vtest.str": '"%s"' % who,
        "vtest.int": "1" if who == "lib" else "3",
        "vtest.lstr": '[ "%s" ]' % who,
    }
def block(spec, who):
    return "\n".join("    %s = %s;" % (k, w(spec, v)) for k, v in vals(who).items() if opt == "all" or KEYS[opt] == k)

os.makedirs(ws + "/lib", exist_ok=True)
os.makedirs(ws + "/.vendomat", exist_ok=True)
open(ws + "/lib/module.nix", "w").write('''# S2 library module (NON-PRODUCTION). Case L=%s
{ pkgs, lib, config, ... }: {
  options.vtest = {%s  };
  config = {
    vtest.probe = {
      env_FOO = config.env.FOO;
      packages = lib.filter (n: lib.any (x: lib.hasPrefix x n) [ "hello" "jq" "cowsay" ]) (map (p: p.name) config.packages);
      py = config.languages.python.enable;
      shell = lib.filter (l: lib.hasPrefix "echo " l && builtins.stringLength l < 12) (lib.splitString "\\n" config.enterShell);
      str = config.vtest.str;
      int = config.vtest.int;
      lstr = config.vtest.lstr;
    };
%s
  };
}
''' % (L, TYPES, block(L, "lib")))

data = {
    "env": {"FOO": "yaml"},
    "packages": ["jq"],
    "languages": {"python": {"enable": False}},
    "enterShell": "echo yaml",
    "vtest": {"str": "yaml", "int": 2, "lstr": ["yaml"]},
}
if opt != "all":
    data = {k: v for k, v in data.items() if k == KEYS[opt].split(".")[0]}
open(ws + "/.vendomat/config.json", "w").write(json.dumps(data, indent=1))
file_attr = {"none": "", "yaml": '_file = "vendomat.yaml";', "key": ""}[fm]
gen_head = '''# S2 generated module (NON-PRODUCTION). Case G=%s fileMode=%s
{ lib, pkgs, options, ... }:
let
  data = builtins.fromJSON (builtins.readFile ./config.json);
  conv = ty: v:
    let n = ty.name; in
    if v == null then v
    else if n == "package" then lib.getAttrFromPath (lib.splitString "." v) pkgs
    else if n == "listOf" then map (conv ty.nestedTypes.elemType) v
    else if n == "attrsOf" then lib.mapAttrs (_: conv ty.nestedTypes.elemType) v
    else if n == "nullOr" then conv ty.nestedTypes.elemType v
    else v;
  wrap = v: %s;
  walk = path: d:
    let o = lib.attrByPath path null options; in
    if o != null && lib.isOption o then wrap (conv o.type d)
    else if builtins.isAttrs d then lib.mapAttrs (k: x: walk (path ++ [ k ]) x) d
    else wrap d;
''' % (G, fm, {"p": "v", "d": "lib.mkDefault v", "f": "lib.mkForce v", "0": "v"}.get(G) or "lib.mkOverride %s v" % G[1:])
if fm == "key":
    body = '''in {
  imports = lib.mapAttrsToList (k: v: {
    _file = "vendomat.yaml#" + k;
    config = walk [ ] { ${k} = v; };
  }) data;
}
'''
else:
    body = '''in {
  %s
  config = %s;
}
''' % (file_attr, "{ }" if G == "0" else "walk [ ] data")
open(ws + "/.vendomat/devenv.nix", "w").write(gen_head + body)

open(ws + "/devenv.nix", "w").write('''# S2 user devenv.nix (NON-PRODUCTION). Case U=%s
{ pkgs, lib, ... }: {
  config = {
%s
  };
}
''' % (U, block(U, "user")))

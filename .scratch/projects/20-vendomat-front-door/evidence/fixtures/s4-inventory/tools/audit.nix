# NON-PRODUCTION spike fixture (project 20, spike S4). Type audit walker. Usage:
#   nix eval --json --impure --expr 'import ./audit.nix { which = "nixos"; }'
{ which, only ? null, onlyPath ? null, serviceChunk ? null }:
let
  nixpkgsSrc = builtins.fetchTree {
    type = "github"; owner = "NixOS"; repo = "nixpkgs";
    rev = "e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
    narHash = "sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=";
  };
  hmSrc = builtins.fetchTree {
    type = "github"; owner = "nix-community"; repo = "home-manager";
    rev = "6b88c12cc6d234de4888f5d21076fb11199d0844";
    narHash = "sha256-5sViLmjhTCtBTvhjSXXvd5LDrAFMydFFKZQisjE8Vds=";
  };
  lib = import (nixpkgsSrc + "/lib");
  pkgs = import nixpkgsSrc { system = "x86_64-linux"; };

  options =
    if which == "nixos-disko-facter" then
      (import (nixpkgsSrc + "/nixos/lib/eval-config.nix") {
        system = "x86_64-linux";
        modules = [
          { nixpkgs.hostPlatform = "x86_64-linux"; }
          "/nix/store/z2bsz1xw44k3gbkb4ks4ds8p0gyspvwb-source/module.nix"
          "/nix/store/4v4gqlpwx3vlp9l104rcgj5632ljr2dd-source/modules/nixos/facter.nix"
        ];
      }).options
    else if which == "nixos" then
      (import (nixpkgsSrc + "/nixos/lib/eval-config.nix") {
        system = "x86_64-linux";
        modules = [ { nixpkgs.hostPlatform = "x86_64-linux"; } ];
      }).options
    else
      (import (hmSrc + "/modules") {
        inherit pkgs lib;
        configuration = { home.username = "u"; home.homeDirectory = "/home/u"; home.stateVersion = "24.05"; };
        check = false;
      }).options;

  rank = { data = 0; reference = 1; untyped = 2; nodata = 3; };
  names = [ "data" "reference" "untyped" "nodata" ];
  rk = c: if c == "container" then (-1) else if lib.hasPrefix "untyped:" c then 2 else rank.${c};
  worst = a: b: if rk a >= rk b then a else b;
  worstOf = l: lib.foldl' worst "data" l;

  # A string that names the cause when not data.
  dataNames = [ "bool" "int" "float" "number" "str" "nonEmptyStr" "singleLineStr" "lines" "commas" "envVar"
    "separatedString" "enum" "port" "unsignedInt" "positiveInt" "signedInt" "intBetween" "ints.between"
    "ints.u8" "ints.u16" "ints.u32" "ints.s8" "ints.s16" "ints.s32" "ints.positive" "ints.unsigned"
    "ints.nonnegative" "null" "unsignedInt8" "unsignedInt16" "unsignedInt32" "signedInt8" "signedInt16" "signedInt32" "nonEmptyString" "string"
    "systemd option" "elixirTuple" "rawElixir" "goDuration" "ipAddress" "kernelParam" "LDAP" "matrixOf" "nonnegativeFloat" "nonzeroInt" "passwdEntry str" "pkcs11" "tuple" "udevValue" ];
  nodataNames = [ "functionTo" "deferredModule" "optionType" "pkgs" "luaInline" "function" "nixpkgs-overlay" "nixpkgs-config" "Toplevel NixOS config" ];
  untypedNames = [ "raw" "unspecified" "anything" "attrs" "lazyAttrsOf-anything" ];
  refNames = [ "path" "pathInStore" "externalPath" "package" "shellPackage" "absolutePath" "passwdEntry path" "home-assistant-component" "home-assistant-theme" "ibus-engine" "navidrome plugin" ];

  classify = classifyD 0;
  classifyD = d: t:
    if d > 4 then "data" else
    let
      n = t.name or "unknown";
      nt = t.nestedTypes or { };
      kids = lib.attrValues nt;
    in
    if lib.elem n nodataNames then "nodata"
    else if lib.elem n untypedNames then "untyped"
    else if lib.elem n refNames then "reference"
    else if n == "submodule" then "container"
    else if kids != [ ] then
      let c = map (classifyD (d + 1)) kids; in
      if lib.elem "container" c then
        # A container inside a wrapper: the children decide. Wrap-level class is the other kids.
        (let rest = lib.filter (x: x != "container") c; in if rest == [ ] then "container" else worstOf rest)
      else worstOf c
    else if lib.elem n dataNames || lib.hasPrefix "strMatching" n || lib.hasPrefix "ints." n || lib.hasPrefix "int" n
      || lib.hasPrefix "enum" n || lib.hasPrefix "str" n || lib.hasInfix "integer" n || lib.hasInfix "string" n then "data"
    else "untyped:${n}";

  # Resolve unknown names to rank 2 later; keep raw name for review.
  normClass = c: if lib.hasPrefix "untyped:" c then "untyped" else c;

  # Shallow type-name chain, for the histogram.
  chain = chainD 0;
  chainD = d: t:
    let n = t.name or "unknown"; kids = lib.attrValues (t.nestedTypes or { }); in
    if d > 3 then n else
    if kids == [ ] then n else "${n}<${lib.concatStringsSep "," (map (chainD (d + 1)) kids)}>";

  walk = depth: prefix: opts:
    if depth > 7 then [ ] else
    lib.concatLists (lib.mapAttrsToList
      (name: v:
        let r = builtins.tryEval (
          if name == "_module" || name == "specialisation" || name == "specialization" || name == "vmVariant" || name == "vmVariantWithBootLoader" then [ ]
          else if lib.isOption v then entry depth (prefix ++ [ name ]) v
          else if builtins.isAttrs v then walk depth (prefix ++ [ name ]) v
          else [ ]);
        in if r.success then r.value else [ ])
      opts);

  entry = depth: path: o:
    let
      t = o.type;
      c = classify t;
      sub = (builtins.tryEval (t.getSubOptions path)).value or { };
      kids = if c == "container" || (builtins.isAttrs sub && sub != { }) then walk (depth + 1) path sub else [ ];
    in
    [{
      path = lib.concatStringsSep "." path;
      cls = normClass c;
      raw = if lib.hasPrefix "untyped:" c then c else null;
      chain = chain t;
      internal = o.internal or false;
      readOnly = o.readOnly or false;
      visible = o.visible or true;
      depth = depth;
    }] ++ kids;
in
walk 0 [ ] (if serviceChunk != null then { services = lib.getAttrs serviceChunk options.services; } else if onlyPath != null then lib.setAttrByPath onlyPath (lib.getAttrFromPath onlyPath options) else if only == null then options else { ${only} = options.${only}; })

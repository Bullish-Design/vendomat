# NON-PRODUCTION spike fixture (project 20, S3). Copy of devenv-py nix/options.nix (read-only source).
# Not part of Vendomat. Do not import into src/, nix/, or templates/.
# nix/options.nix: export the option tree with structured types.
#
# Arguments:
#   options    the option tree (the harness's own options already removed)
#   maxDepth   how many submodule levels to expand (the export marks each cut)
#   normalize  list of { from; to; } string replacements for project-bound
#              text (project root, runtime directory); store hashes are
#              always rewritten to "<store>/"
{ lib, options, maxDepth, normalize ? [ ] }:
let
  isType = v: builtins.isAttrs v && (v._type or null) == "option-type";

  # Remove text that depends on the project directory or the store hash.
  norm = s:
    let
      s0 = builtins.unsafeDiscardStringContext s;
      s1 = builtins.replaceStrings (map (x: x.from) normalize) (map (x: x.to) normalize) s0;
    in lib.concatStrings (map
      (x: if builtins.isList x then "<store>/" else x)
      (builtins.split "/nix/store/[0-9a-z]{32}-" s1));

  # Safe tagged conversion. builtins.toJSON throws an error that tryEval
  # cannot catch when it meets a function, so walk the value by hand.
  ser = d: v:
    if d > 6 then { "$deep" = true; }
    else if isType v then { "$type" = v.name; }
    else if lib.isDerivation v then { "$pkg" = v.name or null; }
    else if builtins.isFunction v then { "$fn" = true; }
    else if builtins.isPath v then { "$path" = norm (toString v); }
    else if builtins.isString v then norm v
    else if builtins.isAttrs v then
      (if v ? _type then { "$type" = v._type; } else lib.mapAttrs (_: ser (d + 1)) v)
    else if builtins.isList v then map (ser (d + 1)) v
    else v;
  # tryEval catches throw and assert only. That is enough here: no other
  # failure occurred at the pinned tools (see REPORT.md).
  safe = v:
    let r = builtins.tryEval (let s = ser 0 v; in builtins.deepSeq s s);
    in if r.success then { ok = true; value = r.value; } else { ok = false; value = null; };

  text = d:
    if d == null then null
    else if builtins.isString d then norm d
    else if builtins.isAttrs d then (if d ? text then norm d.text else null)
    else null;

  # Members of a payload that hold modules, not data.
  skipPayload = [ "modules" "staticModules" "specialArgs" ];
  payloadOf = t:
    let p = t.functor.payload or null;
    in if builtins.isAttrs p
       then (safe (removeAttrs p skipPayload)).value
       else (safe p).value;

  # The location prefix that a container type adds for its element type.
  elemLoc = t: loc:
    let p = t.functor.payload or null;
        ph = if builtins.isAttrs p then p.placeholder or null else null;
    in if ph != null then loc ++ [ "<${ph}>" ]
       else if t.name == "listOf" || t.name == "nonEmptyListOf" then loc ++ [ "*" ]
       else if t.name == "functionTo" then loc ++ [ "<function body>" ]
       else loc;

  # Some types are recursive (JSON value, YAML value). A node whose
  # description repeats an ancestor's description ends the walk.
  maxTypeDepth = 12;

  typeTree = depth: loc: t: typeNode depth [ ] loc t;

  typeNode = depth: seen: loc: t:
    let desc = t.description or null;
    in
    if desc != null && builtins.elem desc seen
    then { name = t.name; description = desc; recursive = true; }
    else if builtins.length seen > maxTypeDepth
    then { name = t.name; description = desc; truncated = true; }
    else {
      name = t.name;
      description = desc;
      payload = payloadOf t;
      nested = lib.mapAttrs
        (_: n: typeNode depth (seen ++ [ desc ]) (elemLoc t loc) (if lib.isOption n then n.type else n))
        (t.nestedTypes or { });
      # The freeform sub-options appear again under nested.freeformType.
      options =
        if t.name == "submodule" && depth < maxDepth
        then walk (depth + 1) (removeAttrs (t.getSubOptions loc) [ "_freeformOptions" ])
        else null;
      depthCut = t.name == "submodule" && depth >= maxDepth;
    };

  leaf = depth: o:
    let
    # An option with defaultText documents a default that depends on other
    # config. Evaluating `default` then costs time and ties the export to the
    # project directory (containers.<name>.copyToRoot copies the project into
    # the store and defeats the evaluation cache). Skip it.
    skip = o ? default && o ? defaultText;
    d = if o ? default && !skip then safe o.default else { ok = true; value = null; };
    in {
      loc = o.loc;
      type = typeTree depth o.loc o.type;
      hasDefault = o ? default;
      default = d.value;
      defaultError = !d.ok;
      defaultSkipped = skip;
      defaultText = text (o.defaultText or null);
      description = text (o.description or null);
      readOnly = o.readOnly or false;
      internal = o.internal or false;
      visible = o.visible or true;
      declarations = map toString (o.declarations or [ ]);
    };

  walk = depth: attrs:
    lib.concatLists (lib.mapAttrsToList (_: v:
      if lib.isOption v then [ (leaf depth v) ]
      else if builtins.isAttrs v then walk depth v
      else [ ]) (removeAttrs attrs [ "_module" ]));
in walk 0 options

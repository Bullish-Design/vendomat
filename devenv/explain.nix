# The data behind `vendomat explain` (R27, VMT-057). `devenv eval vendomat.explain` prints it as JSON.
#
# The report has two lists:
#   yaml   One entry for each key of vendomat.yaml, in file order: the key, its position, the native
#          option it sets, the value, and the files that set that option.
#   nix    One entry for each option that a hatch file sets and no key of vendomat.yaml covers.
#
# Nothing runs until a field is read, so a plain shell entry pays nothing. The module system keeps only the
# definitions of the highest priority. So the files of an entry are the files that win: a `mkForce` in
# `devenv.nix` replaces `vendomat.yaml` in the list.
#
# Limits:
#   - A key that devenv merges (`programs`, a machine) shows the value that vendomat.yaml wrote and lists
#     every workspace file that also sets the option.
#   - The list of Nix-only options comes from the hatch files and the workspace files they import (see
#     ./hatch.nix). Options that a module of an input sets stay out.
#   - A definition that is a function or a condition shows its file with "(may be)".
#   - A key that has no effect, because devenv keeps its default, shows "(devenv default)" as its file.
{ lib, config, options, root, raw, parsed, hatch }:
let
  # --- Native option of each key ---------------------------------------------------------------
  # `native KEYPATH` gives { option; merge; } or null. `merge` marks an option that devenv merges from
  # several definitions: the entry then shows the value of vendomat.yaml alone.
  native = p:
    let
      n = builtins.length p;
      at = builtins.elemAt p;
      dotted = lib.concatStringsSep "." p;
      fixed = {
        "languages.python.enable" = [ "languages" "python" "enable" ];
        "languages.python.version" = [ "languages" "python" "version" ];
        "languages.python.uv.enable" = [ "languages" "python" "uv" "enable" ];
        "languages.python.uv.sync" = [ "languages" "python" "uv" "sync" "enable" ];
        "languages.javascript.enable" = [ "languages" "javascript" "enable" ];
        "languages.javascript.version" = [ "languages" "javascript" "package" ];
        "languages.rust.enable" = [ "languages" "rust" "enable" ];
        "languages.rust.version" = [ "languages" "rust" "version" ];
        "services.postgres.enable" = [ "services" "postgres" "enable" ];
        "services.redis.enable" = [ "services" "redis" "enable" ];
      };
      machineKeys = {
        host = [ "target" "host" ];
        virtual = [ "hardware" "facter" ];
        mode = [ "vendomat" "mode" ];
      };
    in
    if p == [ "programs" ] then { option = [ "packages" ]; merge = true; }
    else if n == 2 && at 0 == "env" then { option = p; merge = false; }
    else if fixed ? ${dotted} then { option = fixed.${dotted}; merge = false; }
    else if n == 3 && at 0 == "machines" && at 2 == "serve" then { option = [ "vendomat" "serve" (at 1) ]; merge = false; }
    else if n == 3 && at 0 == "machines" && at 2 == "programs" then
      { option = [ "machines" (at 1) "nixos" "environment" "systemPackages" ]; merge = true; }
    else if n == 3 && at 0 == "machines" && at 2 == "trustedInterfaces" then
      { option = [ "machines" (at 1) "nixos" "vendomat" "sharing" "trustedInterfaces" ]; merge = true; }
    else if n == 3 && at 0 == "machines" && machineKeys ? ${at 2} then
      { option = [ "machines" (at 1) ] ++ machineKeys.${at 2}; merge = false; }
    else null;

  # --- The keys of the file, in file order -----------------------------------------------------
  # A leaf is a text or a list. Every machine also has the key `machines.NAME` itself: the catalog
  # sets its host name (R21).
  yamlLeaves = p: v:
    if builtins.isAttrs v then lib.concatLists (lib.mapAttrsToList (n: x: yamlLeaves (p ++ [ n ]) x) v)
    else [ p ];
  machineKeys = map (name: [ "machines" name ]) (lib.attrNames (raw.machines or { }));
  keyPaths = yamlLeaves [ ] raw ++ machineKeys;

  posOf = p:
    let e = parsed.at p; in
    if e == null then [ 0 0 ] else map lib.toInt (lib.splitString ":" e.key);
  ordered = lib.sort (a: b: a.pos < b.pos) (map (p: { inherit p; pos = posOf p; }) keyPaths);

  # --- Values ----------------------------------------------------------------------------------
  render = d: v:
    if d == 0 then "..."
    else if lib.isDerivation v then "<package ${v.name or "?"}>"
    else if builtins.isFunction v then "<function>"
    else if builtins.isPath v then toString v
    else if builtins.isAttrs v then lib.mapAttrs (_: render (d - 1)) v
    else if builtins.isList v then map (render (d - 1)) v
    else v;
  valueAt = p: render 4 (lib.attrByPath p null config);

  # --- Files -----------------------------------------------------------------------------------
  # Find the option that holds a path. Inside a map option (`env`, `machines`) `rest` is the path in the map.
  findOption = p:
    let
      go = node: done: rest:
        if lib.isOption node then { o = node; inherit rest; }
        else if rest == [ ] || !(builtins.isAttrs node) || !(node ? ${builtins.head rest}) then null
        else go node.${builtins.head rest} (done ++ [ (builtins.head rest) ]) (builtins.tail rest);
    in
    go options [ ] p;

  clean = f: lib.removePrefix "${root}/" (builtins.head (lib.splitString ", via " f));
  isPlain = v: builtins.isAttrs v && !(v ? _type) && !(lib.isDerivation v);
  # Inside a map option the priority sits on the key, so the module system keeps every definition of
  # the option. Read the priority of the key itself and keep the lowest number.
  prio = v: if builtins.isAttrs v && (v._type or "") == "override" then v.priority else 100;
  definitions = p:
    let found = findOption p; in
    if found == null then [ ]
    else
      lib.concatMap
        (d:
          if found.rest == [ ] then [{ file = clean d.file; p = 0; }]
          else if isPlain d.value then
            lib.optional (lib.hasAttrByPath found.rest d.value)
              { file = clean d.file; p = prio (lib.attrByPath found.rest null d.value); }
          else [{ file = "${clean d.file} (may be)"; p = 0; }])
        found.o.definitionsWithLocations;

  # The files that win for an option.
  winners = p:
    let
      defs = definitions p;
      best = lib.foldl' (a: x: if x.p < a then x.p else a) 1000000 defs;
    in
    mine (lib.unique (map (x: x.file) (lib.filter (x: x.p == best || lib.hasSuffix "(may be)" x.file) defs)));
  # Only a devenv module (a path outside the workspace) holds the option: nothing in the workspace sets it,
  # for example `languages.python.version` while Python is off. The entry then reads "(devenv default)".
  mine = fs:
    let own = lib.filter (f: !(lib.hasPrefix "/" f)) fs; in
    if own == [ ] then [ "(devenv default)" ] else own;
  # The workspace files that set a merged option.
  workspaceFiles = p:
    lib.unique (lib.filter (f: f == "vendomat.yaml" || !(lib.hasPrefix "/" f)) (map (x: x.file) (definitions p)));

  # --- The yaml list ---------------------------------------------------------------------------
  entry = k:
    let
      p = k.p;
      nat = native p;
      isMachine = builtins.length p == 2 && builtins.head p == "machines";
      machineName = builtins.elemAt p 1;
      option =
        if isMachine then [ "machines" machineName "nixos" ]
        else if nat == null then null
        else nat.option;
      merged = isMachine || (nat != null && nat.merge);
      files =
        # `vendomat.serve` is a Vendomat option that the catalog derives from the key, so the key's file is the source.
        if option == null || builtins.head option == "vendomat" then [ "vendomat.yaml" ]
        else
          # The catalog's own definition of a machine's `nixos` is a function, so a path inside it is not
          # visible as a definition. A merged key is set by vendomat.yaml by definition.
          let f = if merged then lib.unique ([ "vendomat.yaml" ] ++ workspaceFiles option) else winners option; in
          # A key that the catalog reads and devenv has no option for (`serve`) has no definitions.
          if f == [ ] then [ "vendomat.yaml" ] else f;
      value =
        if isMachine then { networking.hostName = machineName; }
        else if merged then lib.attrByPath p null raw
        else if option == null then lib.attrByPath p null raw
        else valueAt option;
    in
    {
      key = lib.concatStringsSep "." p;
      line = builtins.elemAt k.pos 0;
      column = builtins.elemAt k.pos 1;
      option = if option == null then null else lib.concatStringsSep "." option;
      inherit value files;
    };

  yamlEntries = map entry ordered;
  yamlOptions = lib.filter (o: o != null) (map (e: e.option) yamlEntries);

  # --- The nix list ----------------------------------------------------------------------------
  # The longest prefix of a setting path that config holds. A setting inside `machines.NAME.nixos` is
  # not an option path of config; the prefix ends at the option.
  prefix = p:
    let
      go = acc: rest: v:
        if rest == [ ] then acc
        else if builtins.isAttrs v && v ? ${builtins.head rest} then
          go (acc ++ [ (builtins.head rest) ]) (builtins.tail rest) v.${builtins.head rest}
        else acc;
    in
    go [ ] p config;

  covered = o: lib.any (y: y == o || lib.hasPrefix "${y}." o || lib.hasPrefix "${o}." y) yamlOptions;
  all = lib.concatLists (lib.attrValues hatch.settings);
  tagged = map (s: { option = lib.concatStringsSep "." (prefix s.path); path = prefix s.path; inherit (s) file; }) all;
  byOption = lib.groupBy (s: s.option) (lib.filter (s: s.path != [ ]) tagged);
  nixEntries = lib.mapAttrsToList
    (option: ss: {
      inherit option;
      value = valueAt (builtins.head ss).path;
      files = lib.unique (map (s: s.file) ss);
    })
    (lib.filterAttrs (o: _: !(covered o)) byOption);
in
{
  yaml = yamlEntries;
  nix = nixEntries;
}

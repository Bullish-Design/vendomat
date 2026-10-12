# The Vendomat catalog module (DOOR-074, DOOR-075). A workspace imports it as `vendomat/devenv`.
#
# The module reads `vendomat.yaml` in the workspace root, parses it once, and maps the typed
# values to native devenv options. A missing file is an empty catalog. It needs the Vendomat devenv
# fork, because only the fork has the primop `vendomatFromYAML`.
#
# Every scalar of the file arrives as text. The option types give the text its meaning:
# `"3.10"` stays a version, `no` is not a boolean, and only `true` and `false` become booleans.
#
# One error lists every bad field. Each line reads `vendomat.yaml: <field> ...`. A syntax fault
# reads `vendomat.yaml:LINE:COL: reason` and comes from the primop. The error stops every command:
#   1. Every mapping to a native option reads the checked values only, through `guard`.
#   2. `_module.check` is `guard true`. The module system reads it on each read of the final
#      config, so even a command that reads no mapped value stops (DOOR-075).
{ lib, config, options, pkgs, inputs, devenvPrimops ? { }, ... }:
let
  t = lib.types;
  file = "vendomat.yaml";
  path = config.devenv.root + "/${file}";

  # --- Parse once ----------------------------------------------------------------------------
  # A missing file is an empty catalog (DOOR-074).
  raw =
    if !(devenvPrimops ? vendomatFromYAML)
    then throw "${file}: this devenv has no vendomatFromYAML primop. Put the Vendomat devenv fork first on PATH."
    else if builtins.pathExists path
    then devenvPrimops.vendomatFromYAML file (builtins.readFile path)
    else { };

  # --- Types ---------------------------------------------------------------------------------
  described = description: type: type // { inherit description; };
  # `true` and `false` text become booleans. Any other text, such as `no`, fails.
  boolText = described ''"true" or "false"''
    (t.coercedTo (t.enum [ "true" "false" ]) (s: s == "true") t.bool);
  enableType = described ''"true" or "false"'' (t.nullOr boolText);
  versionType = described ''a version such as "3.12"'' (t.nullOr (t.strMatching "[0-9]+(\\.[0-9]+){1,2}"));
  majorType = described ''a major version such as "22"'' (t.nullOr (t.strMatching "[0-9]+"));
  rustType = described ''"latest", a version such as "1.81.0", or a date such as "2025-01-31"''
    (t.nullOr (t.strMatching "latest|[0-9]+\\.[0-9]+\\.[0-9]+|[0-9]{4}-[0-9]{2}-[0-9]{2}"));

  # An entry that is present turns the item on, unless it says `enable: false`.
  enableOption = lib.mkOption {
    type = enableType;
    default = null;
    description = "Whether the item is on. A present entry is on unless this is false.";
  };
  versionOption = type: lib.mkOption { inherit type; default = null; description = "The version."; };

  # --- Option tree ---------------------------------------------------------------------------
  # The tree is also the list of known keys: the unknown-key check reads it.
  catalog = options.vendomat.catalog;
  leaves = lib.collect lib.isOption catalog;
  # The parsed and checked values, read from the options, not from `config`.
  values = lib.mapAttrsRecursiveCond (x: !lib.isOption x) (_: o: o.value) catalog;

  # --- Faults --------------------------------------------------------------------------------
  show = lib.concatStringsSep ".";
  # The found value: text shows as itself, a list or a map shows its kind first.
  found = v:
    if builtins.isAttrs v then "a map ${builtins.toJSON v}"
    else if builtins.isList v then "a list ${builtins.toJSON v}"
    else builtins.toJSON v;

  # Keep the known keys only. The unknown keys go to the error, not to the module system, so they
  # join the one listing.
  prune = node: val:
    if !builtins.isAttrs val then { }
    else lib.mapAttrs
      (k: v: if lib.isOption node.${k} then v else prune node.${k} v)
      (lib.filterAttrs (k: _: node ? ${k}) val);

  structure = p: node: val:
    if !builtins.isAttrs val
    then [ "${file}: ${show p} must be a map, found ${found val}" ]
    else lib.concatLists (lib.mapAttrsToList
      (k: v:
        let q = p ++ [ k ]; in
        if !(node ? ${k})
        then [ "${file}: ${show q}: unknown key (known: ${lib.concatStringsSep ", " (lib.attrNames node)})" ]
        else if lib.isOption node.${k} then [ ]
        else structure q node.${k} v)
      val);

  structureFaults =
    if builtins.isAttrs raw then structure [ ] catalog raw
    else [ "${file}: the file must hold a map" ];

  failed = o: !(builtins.tryEval (builtins.deepSeq o.value true)).success;
  typeFaults = map
    (o:
      let d = lib.head o.definitionsWithLocations; in
      "${file}: ${show (lib.drop 2 o.loc)} must be ${o.type.description}, found ${found d.value}")
    (lib.filter failed leaves);

  # Semantic faults read a value only when its type check passed.
  valid = o: !(failed o);
  isProgram = name:
    let
      v = lib.attrByPath (lib.splitString "." name) null pkgs;
      r = builtins.tryEval (lib.isDerivation v);
    in
    r.success && r.value;
  programFaults = lib.optionals (valid catalog.programs)
    (map (n: "${file}: programs: unknown program \"${n}\" (nixpkgs has no package with this name)")
      (lib.filter (n: !(isProgram n)) values.programs));

  nodeVersions = lib.sort lib.lessThan
    (map (n: lib.removePrefix "nodejs_" n) (lib.filter (n: builtins.match "nodejs_[0-9]+" n != null) (lib.attrNames pkgs)));
  jsVersion = values.languages.javascript.version;
  jsFaults = lib.optionals (valid catalog.languages.javascript.version && jsVersion != null && !(pkgs ? "nodejs_${jsVersion}"))
    [ "${file}: languages.javascript.version: nixpkgs has no Node.js ${jsVersion} (known: ${lib.concatStringsSep ", " nodeVersions})" ];

  pyVersion = values.languages.python.version;
  pyFaults = lib.optionals (valid catalog.languages.python.version && pyVersion != null
    && (inputs.nixpkgs-python.packages.${pkgs.stdenv.hostPlatform.system} or { }) != { }
    && !(inputs.nixpkgs-python.packages.${pkgs.stdenv.hostPlatform.system} ? ${pyVersion}))
    [ "${file}: languages.python.version: nixpkgs-python has no Python ${pyVersion}" ];

  faults = structureFaults ++ typeFaults ++ programFaults ++ jsFaults ++ pyFaults;
  guard = v: if faults != [ ] then throw ("\n" + lib.concatStringsSep "\n" faults) else v;

  # --- Mapping -------------------------------------------------------------------------------
  # A present entry turns the item on, unless it says `enable: false`.
  on = p:
    let e = lib.attrByPath (p ++ [ "enable" ]) null values;
    in if e != null then e else lib.hasAttrByPath p (prune catalog raw);
  # Define a native option only when the item is on, so a definition in `devenv.nix` merges natively.
  when = condition: value: lib.mkIf (guard condition) value;

  js = values.languages.javascript;
  rust = values.languages.rust;
in
{
  options.vendomat.catalog = {
    programs = lib.mkOption {
      type = described "a list of nixpkgs attribute names" (t.listOf t.str);
      default = [ ];
      description = "Programs for the shell. Each is a nixpkgs attribute; a dotted path is allowed.";
    };
    languages = {
      python = { enable = enableOption; version = versionOption versionType; };
      javascript = { enable = enableOption; version = versionOption majorType; };
      rust = { enable = enableOption; version = versionOption rustType; };
    };
    services = {
      postgres.enable = enableOption;
      redis.enable = enableOption;
    };
    env = lib.mkOption {
      type = described "a map of text values" (t.attrsOf t.str);
      default = { };
      description = "Environment variables for the shell.";
    };
  };

  # The file is the only definition of the catalog. The inner module names it for the module system.
  imports = [{ _file = file; config.vendomat.catalog = prune catalog raw; }];

  config = {
    _module.check = guard true;

    packages = guard (map (n: lib.attrByPath (lib.splitString "." n) null pkgs) values.programs);
    env = guard values.env;

    languages.python.enable = when (on [ "languages" "python" ]) true;
    languages.python.version = when (on [ "languages" "python" ] && pyVersion != null) pyVersion;

    languages.javascript.enable = when (on [ "languages" "javascript" ]) true;
    languages.javascript.package = when (on [ "languages" "javascript" ] && js.version != null) pkgs."nodejs_${js.version}";

    # A version needs the rust-overlay toolchain, so it selects the stable channel.
    languages.rust.enable = when (on [ "languages" "rust" ]) true;
    languages.rust.channel = when (on [ "languages" "rust" ] && rust.version != null) "stable";
    languages.rust.version = when (on [ "languages" "rust" ] && rust.version != null) rust.version;

    services.postgres.enable = when (on [ "services" "postgres" ]) true;
    services.redis.enable = when (on [ "services" "redis" ]) true;
  };
}

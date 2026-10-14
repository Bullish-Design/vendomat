# The Vendomat catalog module. A workspace imports it as `vendomat/devenv`.
#
# The module reads `vendomat.yaml` in the workspace root. It parses the file once with ./parse.nix
# (plain Nix, builtins only), checks every field, and maps the typed values to native devenv options.
# A missing file is an empty catalog (VMT-021). It needs no devenv fork binary and no unsafe Nix setting.
#
# Every scalar of the file arrives as text. A check gives the text its meaning:
# `"3.10"` stays a version, `no` is not a boolean, and only `true` and `false` become booleans.
#
# One error lists every bad field, in file order. Each line reads `vendomat.yaml:LINE:COL: <path> ...`.
# A syntax fault reads `vendomat.yaml:LINE:COL: reason` and comes from the parser. The error stops every
# command:
#   1. Every mapping to a native option reads its value through `guard`.
#   2. `_module.check` is `guard true`. The module system reads it on each read of the final
#      config, so even a command that reads no mapped value stops (VMT-031).
#
# The mappings sit in an inner module with `_file = "vendomat.yaml"`, so a conflict error names the
# file. YAML values are plain definitions. Catalog defaults use `lib.mkDefault` (R23).
#
# The escape hatch stays visible. ./hatch.nix counts the settings of `devenv.nix` and `devenv.local.nix`
# for the `advanced:` line of the shell entry. ./explain.nix builds the data of `vendomat explain`.
{ lib, config, options, pkgs, inputs, ... }:
let
  file = "vendomat.yaml";
  root = toString config.devenv.root;
  path = root + "/${file}";

  # --- Parse once ----------------------------------------------------------------------------
  # `parsed.value` is the tree. `parsed.at PATH` gives the position of a key path.
  parsed =
    if builtins.pathExists path
    then (import ./parse.nix) file (builtins.readFile path)
    else { value = { }; at = _: null; };
  raw = parsed.value;

  # --- Schema --------------------------------------------------------------------------------
  # A scalar has a check. A map has fields. An `each` map has any key (checked) and one child schema.
  # A list holds scalars. Every value of the file is text, so a check reads text.
  scalar = what: ok: { kind = "scalar"; inherit what ok; };
  map' = fields: { kind = "map"; inherit fields; };
  each = what: keyOk: child: { kind = "each"; inherit what keyOk child; };
  list = what: ok: { kind = "list"; inherit what ok; };

  bool = scalar ''"true" or "false"'' (s: s == "true" || s == "false");
  text = scalar "text" (_: true);
  oneOf = values: scalar (lib.concatMapStringsSep " or " (v: ''"${v}"'') values) (s: lib.elem s values);
  version = scalar ''a version such as "3.12"'' (s: builtins.match "[0-9]+(\\.[0-9]+){1,2}" s != null);
  major = scalar ''a major version such as "22"'' (s: builtins.match "[0-9]+" s != null);
  rustVersion = scalar ''"latest", a version such as "1.81.0", or a date such as "2025-01-31"''
    (s: builtins.match "latest|[0-9]+\\.[0-9]+\\.[0-9]+|[0-9]{4}-[0-9]{2}-[0-9]{2}" s != null);
  hostName = "[a-z0-9]([a-z0-9-]*[a-z0-9])?";

  schema = map' {
    programs = list "a nixpkgs attribute name" (s: s != "");
    env = each "an environment variable name" (k: builtins.match "[A-Za-z_][A-Za-z0-9_]*" k != null) text;
    languages = map' {
      python = map' {
        enable = bool;
        inherit version;
        uv = map' { enable = bool; sync = oneOf [ "auto" "true" "false" ]; };
      };
      javascript = map' { enable = bool; version = major; };
      rust = map' { enable = bool; version = rustVersion; };
    };
    services = map' {
      postgres = map' { enable = bool; };
      redis = map' { enable = bool; };
    };
    machines = each "a host name (lower case letters, digits, '-')"
      (k: builtins.match hostName k != null)
      (map' {
        host = scalar "a host name or address" (s: s != "");
        virtual = bool;
        mode = oneOf [ "fresh-install" "adopt-existing" ];
        serve = bool;
      });
  };

  # --- Faults --------------------------------------------------------------------------------
  # A fault is { pos; text }. `pos` is [ LINE COL ], and the final list sorts by it, so the error
  # reads in file order. `kind` picks the key position ("key") or the value position ("value"),
  # see parse.nix. A path with no position (it should not happen) gets [ 0 0 ].
  show = p: lib.foldl'
    (acc: s: if acc == "" then s else if lib.hasPrefix "[" s then acc + s else acc + "." + s)
    ""
    p;
  found = v:
    if builtins.isAttrs v then "a map ${builtins.toJSON v}"
    else if builtins.isList v then "a list ${builtins.toJSON v}"
    else builtins.toJSON v;
  posOf = p: kind:
    let e = parsed.at p;
    in if e == null then [ 0 0 ] else map lib.toInt (lib.splitString ":" e.${kind});
  fault = p: kind: text:
    let pos = posOf p kind; in
    { inherit pos; text = "${file}:${lib.concatMapStringsSep ":" toString pos}: ${text}"; };

  check = p: s: v:
    if s.kind == "scalar" then
      (if !builtins.isString v then [ (fault p "value" "${show p} must be ${s.what}, found ${found v}") ]
      else if s.ok v then [ ]
      else [ (fault p "value" "${show p} must be ${s.what}, found ${builtins.toJSON v}") ])
    else if s.kind == "list" then
      (if !builtins.isList v then [ (fault p "value" "${show p} must be a list, found ${found v}") ]
      else lib.concatLists (lib.imap0
        (i: x: check (p ++ [ "[${toString i}]" ]) (scalar s.what s.ok) x) v))
    else if !builtins.isAttrs v then [ (fault p "value" "${show p} must be a map, found ${found v}") ]
    else if s.kind == "map" then
      lib.concatLists (lib.mapAttrsToList
        (k: x:
          if s.fields ? ${k} then check (p ++ [ k ]) s.fields.${k} x
          else [ (fault (p ++ [ k ]) "key" "${show (p ++ [ k ])}: unknown key (known: ${lib.concatStringsSep ", " (lib.attrNames s.fields)})") ])
        v)
    else
      lib.concatLists (lib.mapAttrsToList
        (k: x:
          (lib.optional (!s.keyOk k) (fault (p ++ [ k ]) "key" "${show (p ++ [ k ])}: the name is not ${s.what}"))
          ++ check (p ++ [ k ]) s.child x)
        v);

  # Semantic faults read a value only when its shape check passed.
  get = p: lib.attrByPath p null raw;
  shapeOk = p: s: get p != null && check p s (get p) == [ ];

  asPackage = n: lib.attrByPath (lib.splitString "." n) null pkgs;
  isProgram = n: let r = builtins.tryEval (lib.isDerivation (asPackage n)); in r.success && r.value;
  programs = if get [ "programs" ] == null then [ ] else get [ "programs" ];
  programFaults = lib.optionals (shapeOk [ "programs" ] schema.fields.programs)
    (lib.concatLists (lib.imap0
      (i: n: lib.optional (!isProgram n)
        (fault [ "programs" "[${toString i}]" ] "value"
          "programs[${toString i}]: unknown program \"${n}\" (nixpkgs has no package with this name)"))
      programs));

  jsPath = [ "languages" "javascript" "version" ];
  jsVersion = get jsPath;
  nodeVersions = lib.sort lib.lessThan
    (map (n: lib.removePrefix "nodejs_" n) (lib.filter (n: builtins.match "nodejs_[0-9]+" n != null) (lib.attrNames pkgs)));
  jsFaults = lib.optionals (shapeOk jsPath major && !(pkgs ? "nodejs_${jsVersion}"))
    [ (fault jsPath "value" "${show jsPath}: nixpkgs has no Node.js ${jsVersion} (known: ${lib.concatStringsSep ", " nodeVersions})") ];

  pyPath = [ "languages" "python" "version" ];
  pyVersion = get pyPath;
  pyPackages = (inputs.nixpkgs-python or { }).packages.${pkgs.stdenv.hostPlatform.system} or { };
  pyFaults = lib.optionals (shapeOk pyPath version && pyPackages != { } && !(pyPackages ? ${pyVersion}))
    [ (fault pyPath "value" "${show pyPath}: nixpkgs-python has no Python ${pyVersion}") ];

  faultList = check [ ] schema raw ++ programFaults ++ jsFaults ++ pyFaults;
  faults = map (f: f.text) (lib.sort (a: b: a.pos < b.pos) faultList);
  guard = v: if faults != [ ] then throw ("\n" + lib.concatStringsSep "\n" faults) else v;

  # --- The escape hatch -----------------------------------------------------------------------
  hatch = import ./hatch.nix { inherit lib root; args = { inherit lib config options pkgs inputs; }; };

  # --- Mapping -------------------------------------------------------------------------------
  # A present entry turns the item on, unless it says `enable: "false"`.
  on = p: let e = get p; in e != null && (e.enable or "true") != "false";
  # uv.sync turns on only when pyproject.toml exists (VMT-041). devenv warns on every shell entry otherwise.
  # `builtins.pathExists` makes the eval cache follow the file (VMT-042).
  hasPyproject = builtins.pathExists (root + "/pyproject.toml");

  py = get [ "languages" "python" ];
  uv = (py.uv or { });
  js = get [ "languages" "javascript" ];
  rs = get [ "languages" "rust" ];
  machines = raw.machines or { };

  # The mode of a machine. A committed `.machines/NAME/facter.json` marks it installed (R42). The key
  # `mode` in the file overrides that. With neither, no mode is set and devenv keeps its default.
  installed = name: builtins.pathExists (root + "/.machines/${name}/facter.json");
  machine = name: m:
    {
      # The facts file holds networking.hostName, so the machine name must equal it (R21).
      nixos = { networking.hostName = name; };
    }
    // lib.optionalAttrs (m ? host) { target.host = m.host; }
    // lib.optionalAttrs ((m.virtual or "false") == "true") { hardware.facter = null; }
    // lib.optionalAttrs (m ? mode) { vendomat.mode = m.mode; }
    // lib.optionalAttrs (!(m ? mode) && installed name) { vendomat.mode = lib.mkDefault "adopt-existing"; };

  # The config shape stays a literal attribute set. Each value carries its own `guard`: a guard
  # on the whole set gave infinite recursion (W4).
  mapping = {
    packages = guard (map asPackage programs);
    env = guard (raw.env or { });

    languages.python = lib.mkIf (guard (on [ "languages" "python" ])) ({
      enable = true;
      uv.enable = if uv ? enable then uv.enable == "true" else lib.mkDefault true;
      uv.sync.enable =
        if (uv.sync or "auto") == "auto" then lib.mkDefault hasPyproject else uv.sync == "true";
    } // lib.optionalAttrs (pyVersion != null) { version = pyVersion; });

    languages.javascript = lib.mkIf (guard (on [ "languages" "javascript" ])) ({ enable = true; }
      // lib.optionalAttrs ((js.version or null) != null) { package = pkgs."nodejs_${js.version}"; });

    # A version needs the rust-overlay toolchain, so it selects the stable channel.
    languages.rust = lib.mkIf (guard (on [ "languages" "rust" ])) ({ enable = true; }
      // lib.optionalAttrs ((rs.version or null) != null) { channel = "stable"; version = rs.version; });

    services.postgres = lib.mkIf (guard (on [ "services" "postgres" ])) { enable = true; };
    services.redis = lib.mkIf (guard (on [ "services" "redis" ])) { enable = true; };

    machines = guard (lib.mapAttrs machine machines);
  };
in
{
  # The inner module names the file for the module system.
  imports = [{ _file = file; config = mapping; }];

  options.vendomat = {
    parsed = lib.mkOption {
      type = lib.types.raw;
      internal = true;
      readOnly = true;
      default = raw;
      description = "The parsed vendomat.yaml.";
    };
    # Read by the sharing wiring: a machine runs Harmonia unless it says `serve: "false"` (R39).
    serve = lib.mkOption {
      type = lib.types.attrsOf lib.types.bool;
      internal = true;
      readOnly = true;
      default = guard (lib.mapAttrs (_: m: (m.serve or "true") == "true") machines);
      description = "For each machine of vendomat.yaml, whether it serves its store (the key `serve`, on by default).";
    };
    explain = lib.mkOption {
      type = lib.types.raw;
      internal = true;
      readOnly = true;
      default = guard (import ./explain.nix { inherit lib config options root parsed hatch raw; });
      description = "What `vendomat explain` prints: each key of vendomat.yaml with its option, value, and files, and the options that only Nix sets.";
    };
  };

  config = {
    _module.check = guard true;

    # The `advanced:` line (VMT-054 to VMT-056). `VENDOMAT_HIDE_ADVANCED=1` hides it (R45, VMT-093). The
    # shell reads the variable, so the evaluation does not depend on it. `vendomat explain` still shows every source.
    enterShell = lib.mkAfter (lib.optionalString (hatch.line != "")
      "[ \"\${VENDOMAT_HIDE_ADVANCED:-}\" = 1 ] || echo ${lib.escapeShellArg hatch.line}");
  };
}

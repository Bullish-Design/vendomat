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
  vendomatSource = inputs.vendomat or null;
  vendomatTemplate =
    if vendomatSource != null
      && builtins.pathExists "${toString vendomatSource}/templates/workspace/devenv.yaml"
    then "${toString vendomatSource}/templates/workspace"
    else null;

  # --- Parse once ----------------------------------------------------------------------------
  # `parsed.value` is the tree. `parsed.at PATH` gives the position of a key path.
  # A machine entry with no value (`laptop:`) is an empty map: every machine key has a default (R51).
  emptyMapAt = p: builtins.length p == 2 && builtins.head p == "machines";
  parsed =
    if builtins.pathExists path
    then (import ./parse.nix) { inherit file emptyMapAt; } (builtins.readFile path)
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
  # A Linux interface name: 1 to 15 characters of letters, digits, '.', '-', '_', '@', ':' (R52).
  interfaceName = scalar "an interface name (1 to 15 letters, digits, '.', '-', '_', '@', ':')"
    (s: builtins.match "[A-Za-z0-9._@:-]{1,15}" s != null);

  # A module name and a field name of `settings` (R60): a Nix identifier, with '-' allowed after the first character.
  settingName = "[A-Za-z_][A-Za-z0-9_-]*";

  schema = map' {
    programs = list "a nixpkgs attribute name" (s: s != "");
    env = each "an environment variable name" (k: builtins.match "[A-Za-z_][A-Za-z0-9_]*" k != null) text;
    # The settings of an authored module (R60): `settings: MODULE: FIELD: text`. The catalog declares no option.
    settings = each "a module name (letters, digits, '_', '-'; no digit first)"
      (k: builtins.match settingName k != null)
      (each "a field name (letters, digits, '_', '-'; no digit first)"
        (k: builtins.match settingName k != null)
        text);
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
        programs = list "a nixpkgs package attribute name" (s: s != "");
        trustedInterfaces = list interfaceName.what interfaceName.ok;
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

  # A name resolves against a package set. The workspace validates names with its own `pkgs`. A machine
  # resolves them with the `pkgs` of its own NixOS evaluation (see `machine`).
  asPackageIn = set: n: lib.attrByPath (lib.splitString "." n) null set;
  asPackage = asPackageIn pkgs;
  isProgram = n: let r = builtins.tryEval (lib.isDerivation (asPackage n)); in r.success && r.value;
  programs = if get [ "programs" ] == null then [ ] else get [ "programs" ];
  checkPrograms = path: names: lib.concatLists (lib.imap0
    (i: n: lib.optional (!isProgram n)
      (fault (path ++ [ "[${toString i}]" ]) "value"
        "${show path}[${toString i}]: unknown program \"${n}\" (nixpkgs has no package with this name)"))
    names);
  programFaults = lib.optionals (shapeOk [ "programs" ] schema.fields.programs)
    (checkPrograms [ "programs" ] programs);
  # `machines` may have the wrong shape (`machines: foo`). `check` reports that. Walk it only when it is a map.
  machineProgramFaults = lib.optionals (builtins.isAttrs (raw.machines or { })) (lib.concatLists
    (lib.mapAttrsToList
      (name: _: let path = [ "machines" name "programs" ]; in
        lib.optionals (shapeOk path schema.fields.machines.child.fields.programs)
          (checkPrograms path (get path)))
      (raw.machines or { })));

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

  # A setting needs an option. Some module must declare `vendomat.settings.MODULE.FIELD`, or an option above it
  # (a `submodule` or `attrsOf` option). The module system would also reject an undeclared option, but its
  # text gives no line. A path that the check cannot read (a bad shape) gives no fault here: `check` reports it.
  declared = m: f:
    let
      go = node: rest:
        if lib.isOption node then true
        else if rest == [ ] || !builtins.isAttrs node || !(node ? ${builtins.head rest}) then false
        else go node.${builtins.head rest} (builtins.tail rest);
    in
    go options [ "vendomat" "settings" m f ];
  settingsRaw = raw.settings or { };
  settingFaults =
    if !builtins.isAttrs settingsRaw then [ ]
    else lib.concatLists (lib.mapAttrsToList
      (m: fields:
        if !builtins.isAttrs fields then [ ]
        else lib.concatLists (lib.mapAttrsToList
          (f: _:
            let p = [ "settings" m f ]; in
            lib.optional (builtins.match settingName m != null && builtins.match settingName f != null && shapeOk p text && !(declared m f))
              (fault p "key" "${show p}: no module declares the option vendomat.settings.${m}.${f} (an authored module declares it with mkOption)"))
          fields))
      settingsRaw);

  faultList = check [ ] schema raw ++ programFaults ++ machineProgramFaults ++ jsFaults ++ pyFaults ++ settingFaults;
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
  # The sharing wiring (R39, VMT-127, VMT-128). A machine serves unless it says `serve: "false"`.
  serves = m: (m.serve or "true") == "true";
  # The peers of a machine: each other machine that serves and has a committed key. A key that is not
  # committed yet gives no entry, so an install needs no key. The URL names the `host` without a `user@`
  # prefix, else the machine name. The public key is the content of `.machines/NAME/cache-key.pub`.
  keyFile = name: root + "/.machines/${name}/cache-key.pub";
  peerHost = name: m: if m ? host then lib.last (lib.splitString "@" m.host) else name;
  peersOf = self:
    lib.concatLists (lib.mapAttrsToList
      (name: m:
        lib.optional (name != self && serves m && builtins.pathExists (keyFile name))
          { url = "http://${peerHost name m}:5000"; publicKey = lib.trim (builtins.readFile (keyFile name)); })
      machines);

  # A path that `vendomat.watch` accepts (R62). Keep in step with `workspace.check_watch_path` in the Python code.
  watchPathOk = p:
    let parts = lib.splitString "/" p; in
    p != ""
    && !(lib.hasPrefix "/" p)
    && !(lib.hasPrefix ":" p)
    && !(lib.hasSuffix "/" p)
    && builtins.match ".*[*?[\\].*" p == null
    && !(lib.hasInfix "\n" p)
    && !(lib.elem "" parts)
    && !(lib.elem "." parts)
    && !(lib.elem ".." parts)
    && !(lib.elem ".git" parts);

  machine = name: m:
    {
      # The facts file holds networking.hostName, so the machine name must equal it (R21).
      # The module is a function so that `machines.NAME.programs` resolves with the `pkgs` of the machine's
      # own NixOS evaluation, not with the workspace `pkgs`. The workspace `pkgs` only validates the names.
      nixos = { pkgs, ... }: {
        imports = [ ./sharing.nix ];
        networking.hostName = name;
        environment.systemPackages = guard (map (asPackageIn pkgs) (m.programs or [ ]));
        # A present `serve` key is a YAML value. Without it, the catalog default applies (R23).
        vendomat.sharing.serve = if m ? serve then serves m else lib.mkDefault true;
        vendomat.sharing.peers = lib.mkDefault (peersOf name);
        # The interfaces that may reach the cache port (R52). The key is a plain definition (R23). A Nix file can
        # add more, since lists merge. The module opens nothing under `serve: "false"` (R50).
        vendomat.sharing.trustedInterfaces = guard (m.trustedInterfaces or [ ]);
      };
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

    # The settings of authored modules (R60). Each value is text and a plain definition (R23). The authored
    # module declares the options. An option of another type must accept text (see the README). The catalog
    # defines `vendomat.settings` only when the file has the key, because the module system rejects a
    # definition without an option, even an empty map. The condition sits below `vendomat`, so that the read
    # of `devenv.root` does not need `raw` (W4: the top-level names of this set cannot depend on `raw`).
    vendomat = lib.optionalAttrs (raw ? settings) { settings = guard raw.settings; };
  };
in
{
  # The inner module names the file for the module system.
  imports = [{ _file = file; config = mapping; }];

  options.vendomat = {
    # The files that `vendomat apply` and `vendomat rollback` watch, beyond the four fixed ones (R62, VMT-280). A
    # module that keeps its settings in its own file adds that file here. The commands read this option with
    # `devenv eval vendomat.watch`. A path is relative to the workspace root, with no `..` and no leading `/`.
    # The Python commands check the same rule again and also refuse a symlink that leaves the workspace.
    watch = lib.mkOption {
      type = lib.types.listOf ((lib.types.addCheck lib.types.str watchPathOk) // {
        description = "a file path below the workspace root (no leading /, no .. part, no glob character)";
      });
      default = [ ];
      example = [ "extra.yaml" ];
      description = ''
        Workspace files, besides vendomat.yaml, devenv.lock, devenv.nix, and devenv.local.nix, that
        `vendomat apply` commits and `vendomat rollback` restores. They also count in the refusal of
        uncommitted changes. Lists from several modules merge.
      '';
    };
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
      default = guard (lib.mapAttrs (_: serves) machines);
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
  } // lib.optionalAttrs (vendomatTemplate != null) {
    # Commands inside the consumer's pinned shell use the tracked template from that same Vendomat
    # input. The launcher honors this path inside the shell. The host launcher's own `update` path
    # still exports the bundled template; the tests prove `new` and `update` only inside the pinned
    # shell. The bundled template is the fallback when no imported source is present.
    env.VENDOMAT_TEMPLATE = lib.mkDefault vendomatTemplate;
  };
}

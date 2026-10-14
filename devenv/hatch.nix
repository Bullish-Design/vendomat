# The escape hatch files (R12): `devenv.nix` and `devenv.local.nix`.
#
# `definitionsWithLocations` cannot count what one file wrote: it forces the values of the other
# definitions of every option, and one devenv option throws then (W4). So this function calls the hatch
# file itself, as a module, and lists the settings it wrote. A setting is a leaf of the attribute tree.
# A list, a function, a derivation, and a text count as one leaf. `mkIf`, `mkMerge`, and `mkForce`
# count their content. A file that the hatch file imports by a path inside the workspace counts too.
# Other imports do not.
#
# Use: `(import ./hatch.nix) { inherit lib root args; }`. `args` are the module arguments that a hatch
# file may ask for. The result:
#   settings   For each hatch file, a list of { path; file; }. `path` is the option path as a list of
#              text. `file` is the file that wrote it, relative to the workspace.
#   line       The `advanced:` line of the shell entry (VMT-054 to VMT-056), or "".
{ lib, root, args }:
let
  leaves = path: v:
    if lib.isDerivation v then [ path ]
    else if builtins.isAttrs v then
      (if (v._type or "") == "merge" then lib.concatMap (leaves path) v.contents
      else if v ? _type then leaves path (v.content or null)
      else lib.concatLists (lib.mapAttrsToList (n: x: leaves (path ++ [ n ]) x) v))
    else [ path ];

  relative = file: lib.removePrefix "${root}/" (toString file);

  # The settings of a module value. `file` is the name that the entries carry.
  settingsOf = file: m0:
    let
      m = if builtins.isFunction m0 then m0 (builtins.intersectAttrs (builtins.functionArgs m0) args) else m0;
      explicit = m ? config || m ? options;
      cfg =
        if explicit then m.config or { }
        else removeAttrs m [ "imports" "_file" "key" "meta" "disabledModules" "_class" ];
    in
    map (path: { inherit path file; }) (leaves [ ] cfg)
    ++ lib.concatMap (importSettings file) (m.imports or [ ]);

  inWorkspace = i: (builtins.isPath i || builtins.isString i) && lib.hasPrefix "${root}/" (toString i);
  importSettings = file: i:
    if inWorkspace i then settingsOf (relative i) (import i)
    else if builtins.isFunction i || (builtins.isAttrs i && !(i ? _type)) then settingsOf file i
    else [ ];

  of = name:
    let p = "${root}/${name}"; in
    if builtins.pathExists p then settingsOf name (import p) else [ ];

  settings = {
    "devenv.nix" = of "devenv.nix";
    "devenv.local.nix" = of "devenv.local.nix";
  };

  plural = n: "${toString n} setting${if n == 1 then "" else "s"}";
  count = name: builtins.length settings.${name};
  parts =
    lib.optional (count "devenv.nix" > 0) "devenv.nix sets ${plural (count "devenv.nix")}"
    ++ lib.optional (count "devenv.local.nix" > 0)
      "devenv.local.nix sets ${plural (count "devenv.local.nix")} (this checkout only)";
in
{
  inherit settings;
  line = if parts == [ ] then "" else "advanced: " + lib.concatStringsSep "; " parts;
}

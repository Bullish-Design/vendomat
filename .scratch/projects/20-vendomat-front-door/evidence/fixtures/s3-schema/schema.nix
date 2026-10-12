# NON-PRODUCTION spike fixture (project 20, S3).
# Exposes `vendomat.schema.json`: the option tree as JSON. The value is lazy, so a normal
# shell entry never evaluates it. Read it with: devenv eval vendomat.schema.json
{ lib, pkgs, options, config, ... }:
let
  cfg = config.vendomat.schema;
  own = opts: removeAttrs opts [ "vendomat" ];
  normalize = [
    { from = config.devenv.root; to = "<root>"; }
    { from = config.devenv.runtime; to = "<runtime>"; }
  ];
  # Optional subtree filter: a JSON list of top-level keys. Empty list means all.
  keys = builtins.fromJSON cfg.keys;
  pick = opts: if keys == [ ] then opts else lib.filterAttrs (n: _: builtins.elem n keys) opts;
in
{
  options.vendomat.schema = {
    keys = lib.mkOption {
      type = lib.types.str;
      default = "[]";
      description = "JSON list of top-level option keys to export. [] exports all.";
    };
    drv = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = "The schema JSON as a store file (Q4 comparison only).";
    };
    doc = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = "The nixosOptionsDoc JSON (Q7 comparison only).";
    };
    json = lib.mkOption {
      type = lib.types.str;
      readOnly = true;
      description = "The option schema as a JSON string.";
    };
  };
  config.vendomat.schema.json = builtins.toJSON (import ./options-tree.nix {
    inherit lib normalize;
    options = pick (own options);
    maxDepth = 8;
  });
  config.vendomat.schema.drv = pkgs.writeText "vendomat-schema.json" config.vendomat.schema.json;
  config.vendomat.schema.doc = (pkgs.nixosOptionsDoc {
    options = removeAttrs (own options) [ "_module" ];
    warningsAreErrors = false;
  }).optionsJSON;
}

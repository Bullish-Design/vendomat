# mkArtifact — one-builder dispatcher over the per-kind artifact builders (DESIGN §3.1/§5).
#
# Today only `maturinWheel` is wired: native-python wheels via ./mkMaturinWheel.nix, used
# UNCHANGED. The `builders` attrset is the open seam — future kinds (pythonEditable, rustCli,
# service) slot in as new entries without touching callers. Issue #5: stays a single lookup
# keyed on `builder`; the other rows in DESIGN §5 remain docs until evidence demands them.
#
#   mkArtifact { pname = "pyjutsu"; src = inputs.pyjutsu; }                      # builder defaults
#   mkArtifact { pname = "pyjutsu"; src = inputs.pyjutsu; builder = "maturinWheel"; }
{ pkgs, python }:

let
  inherit (pkgs) lib;

  builders = {
    maturinWheel = import ./mkMaturinWheel.nix { inherit pkgs python; };
  };
in
{ pname
, src
, version ? null
, builder ? "maturinWheel"
}:

let
  build = builders.${builder} or (throw
    "mkArtifact: unknown builder \"${builder}\" (known: ${lib.concatStringsSep ", " (builtins.attrNames builders)})");
in
# Pass `version` through only when given, so maturinWheel keeps parsing it from Cargo.toml.
build ({ inherit pname src; } // lib.optionalAttrs (version != null) { inherit version; })

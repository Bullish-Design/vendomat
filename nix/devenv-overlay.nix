# Overlay: pkgs.devenv from the pinned nixpkgs, plus the Vendomat patches.
#   0003  bootstrap reuses locked inputs already in the store (upstream PR #3244)
#   0005  `machines install` refuses a machine marked as already running
#
# Use: pkgs = import nixpkgs { overlays = [ (import ./nix/devenv-overlay.nix { patchDir = ./devenv-dist/binary/patches; }) ]; };
#      pkgs.devenv
#
# patchDir holds 0003.patch and 0005.patch.
# The CHANGELOG.md hunk of 0003 needs patch 0001, which this binary lacks.
# filterdiff drops that hunk; the code hunks apply unchanged.
{ patchDir, skipChecks ? false }:
final: prev:
let
  filtered = name: final.runCommand "${name}-nochangelog.patch"
    { nativeBuildInputs = [ final.patchutils ]; }
    ''filterdiff -x '*/CHANGELOG.md' ${patchDir}/${name}.patch > $out'';
in
{
  devenv = prev.devenv.overrideAttrs (old: {
    patches = (old.patches or [ ])
      ++ [ (filtered "0003") (filtered "0005") ];
  } // final.lib.optionalAttrs skipChecks { doCheck = false; });
}

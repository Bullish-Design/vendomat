# The fresh-install preflight program of one host (MACH-010, MACH-016).
#
# `machines.<host>.vendomat.preflight.program` takes one executable file. The patched
# `devenv machines install` copies it to the target and runs it before disko. The expected identity
# of each install-target and the protected disks are baked into a copy of `preflight/vendomat-preflight`.
{ lib, pkgs }:
{ host, disks }:
let
  targets = lib.filterAttrs (_: d: d.role == "install-target") disks;
  protected = lib.filterAttrs (_: d: d.role == "keep" || d.role == "existing-system") disks;
  quote = s: "'" + lib.replaceStrings [ "'" ] [ "'\\''" ] s + "'";
  targetLines = lib.mapAttrsToList
    (_: d: quote "${d.byId}|${toString d.model}|${toString d.serial}|${toString d.sizeBytes}")
    targets;
  protectedLines = lib.mapAttrsToList (_: d: quote d.byId) protected;
  template = builtins.readFile ../../preflight/vendomat-preflight;
in
pkgs.writeTextFile {
  name = "vendomat-preflight-${host}";
  executable = true;
  text = lib.replaceStrings
    [ "@TARGETS@" "@PROTECTED@" ]
    [ (lib.concatStringsSep "\n" targetLines) (lib.concatStringsSep "\n" protectedLines) ]
    template;
}

# Reusable devenv module: Testee verification entrypoints.
#
# The tasks call the host `testee` wrapper (Testee 0.5.0). The wrapper starts before devenv, then
# opens one clean devenv shell and runs the checks that the project declares in `testee.checks`.
#
# This module declares no checks and does not import the Testee devenv module. The consumer pins
# the Testee module and `testee.package` from one tag, and declares its own `testee.checks`:
#
#   let
#     testeeFlake = builtins.getFlake "git+https://github.com/Bullish-Design/testee?ref=refs/tags/v0.5.0";
#   in
#   {
#     imports = [ testeeFlake.devenvModules.default ./nix/testee.nix ];
#     testee.package = testeeFlake.packages.${pkgs.stdenv.hostPlatform.system}.testee;
#     testee.checks = { ... };
#   }
#
# Set VENDOMAT_TESTEE_HOST_BIN to use a wrapper other than `~/.nix-profile/bin/testee`.
{ lib, options, ... }:

let
  testeeBin = ''"''${VENDOMAT_TESTEE_HOST_BIN:-$HOME/.nix-profile/bin/testee}"'';
in
{
  # Tasks run from devenv's own CWD, so cd to the project root first.
  tasks = {
    "testee:quick".exec = ''cd "$DEVENV_ROOT" && ${testeeBin} verify'';
    "testee:full".exec = ''cd "$DEVENV_ROOT" && ${testeeBin} verify --full'';
    "testee:doctor".exec = ''cd "$DEVENV_ROOT" && ${testeeBin} doctor'';
    "testee:report".exec = ''cd "$DEVENV_ROOT" && ${testeeBin} report'';
  };

  # The Testee module already sets `enterTest` to the full gate. Add it here only when that
  # module is absent, so `devenv test` runs the full gate once.
  enterTest = lib.mkIf (!(options ? testee)) ''
    cd "$DEVENV_ROOT" && ${testeeBin} verify --full
  '';
}

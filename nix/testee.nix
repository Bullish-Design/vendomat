# Reusable devenv module: Testee verification entrypoints.
#
# Assumes `testee` and the tools it orchestrates (ruff, ty, pytest) are provided by
# the project's devenv Python venv. Import it from your devenv.nix:
#
#   imports = [ ./nix/testee.nix ];
{ config, ... }:

let
  venvBin = "${config.devenv.state}/venv/bin";
in
{
  # Tasks run from devenv's own CWD, so cd to the project root first.
  tasks = {
    "testee:quick".exec = ''cd "$DEVENV_ROOT" && ${venvBin}/testee verify --mode quick'';
    "testee:detailed".exec = ''cd "$DEVENV_ROOT" && ${venvBin}/testee verify --mode detailed'';
    "testee:ci".exec = ''cd "$DEVENV_ROOT" && ${venvBin}/testee verify --mode ci'';
    "testee:doctor".exec = ''cd "$DEVENV_ROOT" && ${venvBin}/testee doctor'';
  };

  enterTest = ''
    cd "$DEVENV_ROOT" && ${venvBin}/testee verify --mode ci
  '';
}

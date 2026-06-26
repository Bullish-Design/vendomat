# vendomat's own dev shell — a *man-shaped Python project (Typer CLI + pytest + ruff).
#
# vendomat ships two faces over one vendor/ data area: Face A (native-wheel artifacts, the
# flake.nix half) and Face B (per-dependency knowledge skills, this Python package). This shell
# is for developing the package itself; it imports nothing from vendomat's own consumer module
# (vendor.*) because vendomat has no native dependencies of its own.
#
# Run every in-repo command through here: `devenv shell -- pytest`, `devenv shell -- ruff …`,
# `devenv shell -- vendomat doctor`.
{ pkgs, lib, config, inputs, ... }:

{
  # Verification entrypoints (testee:quick/detailed/ci + enterTest) — the *man-family
  # verify interface. Route checks through `testee verify`, not pytest/ruff directly.
  imports = [ ./nix/testee.nix ];

  # https://devenv.sh/basics/
  env.PROJ = "vendomat";

  # No .env needed; silence the integration hint.
  dotenv.disableHint = true;

  # https://devenv.sh/packages/
  packages = [
    pkgs.uv
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv = {
      enable = true;
      # Install vendomat (editable) + deps + the dev group (pytest, ruff) on shell entry.
      sync.enable = true;
    };
  };

  enterShell = ''
    # Only announce in an interactive terminal; stay silent when a command captures stdout
    # (e.g. an agent running `devenv shell -- vendomat doctor`).
    if [ -t 1 ]; then
      echo "vendomat devenv"
      python --version
    fi
  '';

  # See full reference at https://devenv.sh/reference/options/
}

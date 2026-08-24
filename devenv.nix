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

  # devman — the automation plane (CONCEPT.md §5). `base` alone: this repository
  # ships no scheduled work and writes none of its own files.
  devman = {
    enable = true;
    project = "vendomat";
    groups = [ "base" ];
  };

  # https://devenv.sh/tasks/
  #
  # The two task names the `base` group calls (groups/base/README.md). devenv
  # owns each implementation; Dagu owns the composition (§6). `uv run --group
  # dev` rather than bare names: the venv bin is on the interactive shell's PATH
  # but not on the task runner's PATH (STAGE_7_LOG.md, wave 2b); dev deps are a
  # uv `[dependency-groups]`. `ruff check src` matches the repo's own scope.
  tasks = {
    "vendomat:lint".exec = "uv run --group dev ruff check src";
    "vendomat:test".exec = "uv run --group dev pytest";

    "base:check".after = [ "vendomat:lint" ];
    "base:test".after = [ "vendomat:test" ];
  };
}

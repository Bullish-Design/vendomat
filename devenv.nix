# vendomat's own dev shell: a Python project (Typer CLI, pytest, ruff, ty).
#
# This shell is for developing the command. The installed `vendomat` is a host program; a project
# never imports it (DEL-006, DEL-007).
#
# Run every in-repo command through here: `devenv shell -- testee verify --mode quick`.
{ pkgs, lib, config, inputs, ... }:

{
  # Verification entrypoints (testee:quick/detailed/ci + enterTest) — the *man-family
  # verify interface. Route checks through `testee verify`, not pytest/ruff directly.
  imports = [
    ./nix/testee.nix
  ];

  # https://devenv.sh/basics/
  env.PROJ = "vendomat";

  # No .env needed; silence the integration hint.
  dotenv.disableHint = true;

  # https://devenv.sh/packages/
  packages = [
    pkgs.uv
  ];

  # Local gitman checkout, a sibling of this repository. It runs in its own .venv.
  # UV_PROJECT_ENVIRONMENT overrides the inherited vendomat venv. --no-sync leaves
  # gitman's .venv unchanged. A devenv input would copy the tree into the read-only
  # store, which uv cannot use for its venv.
  scripts.gitman.exec = ''
    UV_PROJECT_ENVIRONMENT="$DEVENV_ROOT/../gitman/.venv" exec uv run --no-sync --project "$DEVENV_ROOT/../gitman" gitman "$@"
  '';

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
    # (e.g. an agent running `devenv shell -- vendomat path <name>`).
    if [ -t 1 ]; then
      echo "vendomat devenv"
      python --version
    fi
  '';

  # See full reference at https://devenv.sh/reference/options/

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

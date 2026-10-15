# vendomat's own dev shell: a Python project (Typer CLI, pytest, ruff, ty).
#
# This shell is for developing the command. The installed `vendomat` is a host program; a project
# never imports it (DEL-006, DEL-007).
#
# Run the gate from the repository root with the host command: `testee verify`.
# Run other in-repo commands through here: `devenv shell -- <command>`.
{ pkgs, lib, config, inputs, ... }:

{
  imports = [ ./nix/tasks.nix ];

  # https://devenv.sh/basics/
  env.PROJ = "vendomat";

  # No .env needed; silence the integration hint.
  dotenv.disableHint = true;

  # https://devenv.sh/packages/
  # The Testee shell drops the host PATH, so the tests need git (and `git daemon`) here.
  packages = [
    pkgs.uv
    pkgs.git
    pkgs.direnv
    pkgs.jq # the launcher tests run the launcher, which reads devenv.lock with jq
  ];

  # Local gitman checkout, a sibling of this repository. It runs in its own .venv.
  # UV_PROJECT_ENVIRONMENT overrides the inherited vendomat venv. --no-sync leaves
  # gitman's .venv unchanged. A devenv input would copy the tree into the read-only
  # store, which uv cannot use for its venv.
  scripts.gitman.exec = ''
    UV_PROJECT_ENVIRONMENT="$DEVENV_ROOT/../gitman/.venv" exec uv run --no-sync --project "$DEVENV_ROOT/../gitman" gitman "$@"
  '';

  # `cleanup` deletes the regenerable leftovers of this repository: Testee venvs, stale Testee slots,
  # and caches. It prints a dry run unless you add --yes. The logic lives in scripts/cleanup.py.
  scripts.cleanup.exec = ''
    exec python "$DEVENV_ROOT/scripts/cleanup.py" --root "$DEVENV_ROOT" "$@"
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
    # (e.g. an agent running `devenv shell -- vendomat explain --json`).
    if [ -t 1 ]; then
      echo "vendomat devenv"
      python --version
    fi
  '';

  # See full reference at https://devenv.sh/reference/options/

  # The tasks live in nix/tasks.nix: the five Testee tasks, the opt-in tasks, and base:check/base:test.
}

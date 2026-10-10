# vendomat's own dev shell: a Python project (Typer CLI, pytest, ruff, ty).
#
# This shell is for developing the command. The installed `vendomat` is a host program; a project
# never imports it (DEL-006, DEL-007).
#
# Run the gate from the repository root with the host wrapper: `testee verify --full`.
# Run other in-repo commands through here: `devenv shell -- <command>`.
{ pkgs, lib, config, inputs, ... }:

let
  # The Testee module and the Testee package come from the same pinned tag. Keep this tag equal
  # to the host `testee` wrapper version. The uv venv does not carry Testee.
  testeeFlake = builtins.getFlake "git+https://github.com/Bullish-Design/testee?ref=refs/tags/v0.5.0";
  venvBin = "${config.devenv.state}/venv/bin";
in
{
  # Verification entrypoints (testee:quick, testee:full, testee:doctor, testee:report, and
  # enterTest). They call the host `testee` wrapper. Route checks through `testee verify`, not
  # pytest/ruff directly.
  imports = [
    testeeFlake.devenvModules.default
    ./nix/testee.nix
  ];

  testee.package = testeeFlake.packages.${pkgs.stdenv.hostPlatform.system}.testee;

  # The checks. `quick` is ruff and ruff-format; `full` adds ty and pytest. Tools come from the
  # uv venv (the `dev` group in pyproject.toml), so each argv holds an absolute path.
  testee.checks = {
    ruff = {
      argv = [ "${venvBin}/ruff" "check" "--output-format" "json" "." ];
      profiles = [ "quick" "full" ];
      structured = { parser = "ruff-json"; file = "ruff.stdout.log"; };
    };
    ruff-format = {
      argv = [ "${venvBin}/ruff" "format" "--check" "." ];
      profiles = [ "quick" "full" ];
    };
    ty = {
      argv = [ "${venvBin}/ty" "check" "--python" "${venvBin}/python" "src" "tests" ];
      profiles = [ "full" ];
    };
    pytest = {
      argv = [
        "${pkgs.bash}/bin/bash"
        "-c"
        ''${venvBin}/python -m pytest -q tests --junitxml="$TESTEE_RUN_DIR/pytest.junit.xml"''
      ];
      profiles = [ "full" ];
      structured = { parser = "junit-xml"; file = "pytest.junit.xml"; };
    };
    # Opt-in end-to-end check. It builds real consumer shells with Nix, so no profile selects it
    # and it is not required. Run it with `testee check e2e`. The Testee shell drops the host
    # PATH and HOME, so the argv sets VENDOMAT_E2E, HOME, and a nix on PATH itself.
    e2e = {
      argv = [
        "${pkgs.bash}/bin/bash"
        "-c"
        ''
          export HOME="$(eval echo "~$(id -un)")" VENDOMAT_E2E=1
          export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
          # The sync fixture runs a real devenv. Use the host's, which is the pinned release build.
          export VENDOMAT_DEVENV="''${VENDOMAT_DEVENV:-$(command -v devenv || true)}"
          # Keep every fixture command, exit status, and output outside the repository.
          export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/v6/fixture-logs/$(date -u +%Y%m%dT%H%M%SZ)}"
          ${venvBin}/python -m pytest -q tests --junitxml="$TESTEE_RUN_DIR/e2e.junit.xml"
        ''
      ];
      profiles = [ "e2e" ];
      required = false;
      timeout_s = 1800;
      structured = { parser = "junit-xml"; file = "e2e.junit.xml"; };
    };
  };

  # https://devenv.sh/basics/
  env.PROJ = "vendomat";

  # No .env needed; silence the integration hint.
  dotenv.disableHint = true;

  # https://devenv.sh/packages/
  # The Testee shell drops the host PATH, so the tests need git (and `git daemon`) here.
  packages = [
    pkgs.uv
    pkgs.git
    pkgs.jq # the launcher tests run the launcher, which reads devenv.lock with jq
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

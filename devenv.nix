# vendomat's own dev shell: a Python project (Typer CLI, pytest, ruff, ty).
#
# This shell is for developing the command. The installed `vendomat` is a host program; a project
# never imports it (DEL-006, DEL-007).
#
# Run the gate from the repository root with the host command: `testee verify`.
# Run other in-repo commands through here: `devenv shell -- <command>`.
{ pkgs, lib, config, inputs, ... }:

let
  venvBin = "${config.devenv.state}/venv/bin";
  # One live cache check. The Testee shell drops host variables, so the size is set here.
  liveCache = size: {
    argv = [
      "${pkgs.bash}/bin/bash"
      "-c"
      ''
        export HOME="$(eval echo "~$(id -un)")" VENDOMAT_LIVE_CACHE=1 VENDOMAT_LIVE_CACHE_SIZE=${toString size}
        export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
        export VENDOMAT_LIVE_CACHE_LOGS="$HOME/.local/state/vendomat/v6/live-cache/$(date -u +%Y%m%dT%H%M%SZ)"
        ${venvBin}/python -m pytest -q -s tests/test_live_cache.py --junitxml="$TESTEE_RUN_DIR/live-cache.junit.xml"
      ''
    ];
    profiles = [ "live-cache" ];
    required = false;
    timeout_s = 3600;
    structured = { parser = "junit-xml"; file = "live-cache.junit.xml"; };
  };
in
{
  # The host `testee` (0.6) checks the commit in its own workspace. The module comes from the
  # locked `testee` input in devenv.yaml. `testee.prepare` fills the workspace venv from
  # `uv.lock`, so the checks keep naming tools by their absolute venv path.
  # The checks. `testee verify --profile quick` runs ruff and ruff-format; `full` adds ty and pytest,
  # and `testee verify` runs every required check. Tools come from the
  # uv venv (the `dev` group in pyproject.toml), so each argv holds an absolute path.
  testee.prepare = [ [ "uv" "sync" "--locked" ] ];
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
    # and it is not required. Run it with `testee verify e2e`. The Testee shell drops the host
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
          # The workspace runs in Testee's own directory, so the sibling Templateer checkout is out of reach.
          export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.venv/bin/templateer}"
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
    workspace-e2e = {
      argv = [
        "${pkgs.bash}/bin/bash"
        "-c"
        ''
          export HOME="$(eval echo "~$(id -un)")" VENDOMAT_E2E=1
          export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
          export VENDOMAT_DEVENV="''${VENDOMAT_DEVENV:-$(command -v devenv || true)}"
          # The workspace runs in Testee's own directory, so the sibling Templateer checkout is out of reach.
          export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.venv/bin/templateer}"
          export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/v6/fixture-logs/$(date -u +%Y%m%dT%H%M%SZ)}"
          ${venvBin}/python -m pytest -q tests/test_workspace_user_e2e.py --junitxml="$TESTEE_RUN_DIR/workspace-e2e.junit.xml"
        ''
      ];
      profiles = [ "workspace-e2e" ];
      required = false;
      timeout_s = 900;
      structured = { parser = "junit-xml"; file = "workspace-e2e.junit.xml"; };
    };
    # Opt-in live cache checks (CACHE-012). They push to the host Attic with the push credential,
    # ask for every path with the pull credential, and copy cold into an empty store. They write
    # real objects to the live cache, so no profile selects them. Run `testee verify live-cache`
    # (a 1 MiB unique object) or `testee verify live-cache-load` (a 64 MiB unique object, about
    # 1000 chunks). They read ~/.config/attic/config.toml and print no token. The report goes
    # under ~/.local/state/vendomat/v6/live-cache/<UTC time>/.
    live-cache = liveCache 1048576;
    live-cache-load = liveCache 67108864;
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

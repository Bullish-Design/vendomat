# Testee checks for this project.
#
# The machine (nix-meta) supplies the Testee module at the `machine` path.
# On a host without that module, the checks are skipped and the shell still
# evaluates. This project owns its checks here. It never pins Testee itself.
# Use `lib.optionalAttrs` for the settings. A module-system condition fails
# when the option is absent.
{ lib, options, pkgs, config, ... }:

let
  machine = /run/current-system/sw/share/testee/module/testee.nix;
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
  imports = lib.optional (builtins.pathExists machine) machine;

  config = lib.optionalAttrs (options ? testee) {
    # The host `testee` checks the commit in its own workspace. The machine supplies the module.
    # `testee.prepare` fills the workspace venv from
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
            # The default is the live devenv environment. The old .venv is stale.
            export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.devenv/state/venv/bin/templateer}"
            # Keep every fixture command, exit status, and output outside the repository.
            export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/p20/$(date -u +%Y%m%dT%H%M%SZ)/slice-1/F-infra}"
            ${venvBin}/python -m pytest -q tests --junitxml="$TESTEE_RUN_DIR/e2e.junit.xml"
          ''
        ];
        profiles = [ "e2e" ];
        required = false;
        # This check runs three NixOS VM builds. Each child build may need 3,000 seconds.
        timeout_s = 10800;
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
            # The default is the live devenv environment. The old .venv is stale.
            export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.devenv/state/venv/bin/templateer}"
            export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/v6/fixture-logs/$(date -u +%Y%m%dT%H%M%SZ)}"
            ${venvBin}/python -m pytest -q tests/test_workspace_user_e2e.py --junitxml="$TESTEE_RUN_DIR/workspace-e2e.junit.xml"
          ''
        ];
        profiles = [ "workspace-e2e" ];
        required = false;
        timeout_s = 900;
        structured = { parser = "junit-xml"; file = "workspace-e2e.junit.xml"; };
      };
      # Project 20 slice 1. This gate builds a workspace from the host launcher and exercises the
      # catalog against the patched fork. Run it with the fork first on Testee's inherited PATH:
      # `PATH=/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin:$PATH testee verify front-door-e2e`.
      front-door-e2e = {
        argv = [
          "${pkgs.bash}/bin/bash"
          "-c"
          ''
            export HOME="$(eval echo "~$(id -un)")" VENDOMAT_FRONT_DOOR_E2E=1
            export PATH="/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin:${pkgs.nix}/bin:${pkgs.git}/bin:${pkgs.direnv}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
            export VENDOMAT_FRONT_DOOR_FORK="/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin/devenv"
            export VENDOMAT_FRONT_DOOR_TESTEE="$HOME/.nix-profile/bin/testee"
            export VENDOMAT_FRONT_DOOR_LOGS="$HOME/.local/state/vendomat/p20/$(date -u +%F)/slice-1/F-front-door"
            ${venvBin}/python -m pytest -q tests/test_front_door_e2e.py --junitxml="$TESTEE_RUN_DIR/front-door-e2e.junit.xml"
          ''
        ];
        profiles = [ "front-door-e2e" ];
        required = false;
        timeout_s = 3600;
        structured = { parser = "junit-xml"; file = "front-door-e2e.junit.xml"; };
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
  };
}

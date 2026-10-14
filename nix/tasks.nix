# Testee 0.8 tasks for this project.
#
# devenv names a task `namespace:name`. An opt-in task takes the namespace `opt`, so the old
# check ID `e2e` is now `opt:e2e`.
#
# Testee runs devenv tasks by name. `testee verify` runs the four required tasks:
# check:lint, check:format, check:types, and test:full. test:quick is for
# `testee verify --profile quick`. The opt-in tasks never count for green.
# Run one with `testee verify <task>`. Raw logs go outside the repository.
{ pkgs, config, ... }:

let
  venvBin = "${config.devenv.state}/venv/bin";
  # The Testee shell drops the host PATH and HOME. Each opt-in task sets what it needs.
  hostEnv = ''
    export HOME="$(eval echo "~$(id -un)")"
  '';
  # Where the task writes its junit file. A cloner has no TESTEE_RUN_DIR, so the default applies.
  runDir = ''
    out="''${TESTEE_RUN_DIR:-.devenv/state}"
    mkdir -p "$out"
  '';
  # One opt-in task. `timeout_s` is the limit in seconds.
  optIn = { timeout_s, script }: {
    after = [ "setup:sync" ];
    input.testee.timeout_s = timeout_s;
    exec = ''
      set -o pipefail
      ${runDir}
      ${script}
    '';
  };
  # One live cache task. It writes real objects to the live cache.
  liveCache = size: optIn {
    timeout_s = 3600;
    script = ''
      ${hostEnv}
      export VENDOMAT_LIVE_CACHE=1 VENDOMAT_LIVE_CACHE_SIZE=${toString size}
      export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
      export VENDOMAT_LIVE_CACHE_LOGS="$HOME/.local/state/vendomat/v6/live-cache/$(date -u +%Y%m%dT%H%M%SZ)"
      ${venvBin}/python -m pytest -q -s tests/test_live_cache.py --junitxml="$out/live-cache.junit.xml"
    '';
  };
in
{
  # Replaces testee.prepare. Each task that needs the venv names it in `after`.
  tasks."setup:sync".exec = ''
    uv sync --locked
  '';

  tasks."check:lint" = {
    after = [ "setup:sync" ];
    exec = ''
      set -o pipefail
      ${runDir}
      uv run --no-sync ruff check . --output-format json | tee "$out/check:lint.ruff.json"
    '';
  };

  tasks."check:format" = {
    after = [ "setup:sync" ];
    exec = ''
      set -o pipefail
      uv run --no-sync ruff format --check .
    '';
  };

  tasks."check:types" = {
    after = [ "setup:sync" ];
    exec = ''
      set -o pipefail
      uv run --no-sync ty check --python ${venvBin}/python src tests
    '';
  };

  # No fast subset exists. The suite has no slow marker.
  tasks."test:quick".exec = ''
    echo "n/a: no quick subset"
    exit 0
  '';

  tasks."test:full" = {
    after = [ "setup:sync" ];
    exec = ''
      set -o pipefail
      ${runDir}
      uv run --no-sync pytest -q tests --junitxml="$out/test:full.junit.xml"
    '';
  };

  # Opt-in end-to-end task. It builds real consumer shells with Nix.
  # Run it with `testee verify opt:e2e`. It runs three NixOS VM builds.
  # Each child build may need 3,000 seconds.
  tasks."opt:e2e" = optIn {
    timeout_s = 10800;
    script = ''
      ${hostEnv}
      export VENDOMAT_E2E=1
      export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
      # The sync fixture runs a real devenv. Use the host's, which is the pinned release build.
      export VENDOMAT_DEVENV="''${VENDOMAT_DEVENV:-$(command -v devenv || true)}"
      # The workspace runs in Testee's own directory, so the sibling Templateer checkout is out of reach.
      # The default is the live devenv environment. The old .venv is stale.
      export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.devenv/state/venv/bin/templateer}"
      # Keep every fixture command, exit status, and output outside the repository.
      export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/p20/$(date -u +%Y%m%dT%H%M%SZ)/slice-1/F-infra}"
      ${venvBin}/python -m pytest -q tests --junitxml="$out/e2e.junit.xml"
    '';
  };

  tasks."opt:workspace-e2e" = optIn {
    timeout_s = 900;
    script = ''
      ${hostEnv}
      export VENDOMAT_E2E=1
      export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
      export VENDOMAT_DEVENV="''${VENDOMAT_DEVENV:-$(command -v devenv || true)}"
      # The workspace runs in Testee's own directory, so the sibling Templateer checkout is out of reach.
      # The default is the live devenv environment. The old .venv is stale.
      export VENDOMAT_TEMPLATEER="''${VENDOMAT_TEMPLATEER:-$HOME/Documents/Projects/templateer_v2/.devenv/state/venv/bin/templateer}"
      export VENDOMAT_FIXTURE_LOGS="''${VENDOMAT_FIXTURE_LOGS:-$HOME/.local/state/vendomat/v6/fixture-logs/$(date -u +%Y%m%dT%H%M%SZ)}"
      ${venvBin}/python -m pytest -q tests/test_workspace_user_e2e.py --junitxml="$out/workspace-e2e.junit.xml"
    '';
  };

  # Opt-in Nix evaluation of the catalog and the parser (project 24, S3). It runs the parser corpus
  # and the catalog module on stub devenv options. It needs `nix-instantiate` and the pinned
  # nixpkgs (the fetcher cache is enough once it holds the revision). Run `testee verify opt:catalog-eval`.
  tasks."opt:catalog-eval" = optIn {
    timeout_s = 1800;
    script = ''
      ${hostEnv}
      export VENDOMAT_E2E=1
      export PATH="/run/current-system/sw/bin:${pkgs.nix}/bin:${pkgs.git}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
      ${venvBin}/python -m pytest -q tests/test_catalog_parser_nix.py tests/test_catalog_module_nix.py --junitxml="$out/catalog-eval.junit.xml"
    '';
  };

  # Project 20 slice 1. This task builds a workspace from the host launcher and exercises the
  # catalog against the patched fork. Run it with the fork first on Testee's inherited PATH:
  # `PATH=/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin:$PATH testee verify opt:front-door-e2e`.
  tasks."opt:front-door-e2e" = optIn {
    timeout_s = 3600;
    script = ''
      ${hostEnv}
      export VENDOMAT_FRONT_DOOR_E2E=1
      export PATH="/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin:${pkgs.nix}/bin:${pkgs.git}/bin:${pkgs.direnv}/bin:$PATH:/etc/profiles/per-user/$(id -un)/bin"
      export VENDOMAT_FRONT_DOOR_FORK="/nix/store/1bqfcc56bc1xgkfaihfz7kdjiqx8qbqg-devenv-wrapped-2.4.0/bin/devenv"
      export VENDOMAT_FRONT_DOOR_TESTEE="$(command -v testee || echo /etc/profiles/per-user/$(id -un)/bin/testee)"
      export VENDOMAT_FRONT_DOOR_LOGS="$HOME/.local/state/vendomat/p20/$(date -u +%F)/slice-1/F-front-door"
      ${venvBin}/python -m pytest -q tests/test_front_door_e2e.py --junitxml="$out/front-door-e2e.junit.xml"
    '';
  };

  # Opt-in live cache tasks (CACHE-012). They push to the host Attic with the push credential,
  # ask for every path with the pull credential, and copy cold into an empty store. They write
  # real objects to the live cache. Run `testee verify opt:live-cache` (a 1 MiB unique object) or
  # `testee verify opt:live-cache-load` (a 64 MiB unique object, about 1000 chunks). They read
  # ~/.config/attic/config.toml and print no token. The report goes under
  # ~/.local/state/vendomat/v6/live-cache/<UTC time>/.
  tasks."opt:live-cache" = liveCache 1048576;
  tasks."opt:live-cache-load" = liveCache 67108864;

  # devman contract names. They run the standard tasks and need no `exec`.
  tasks."base:check".after = [ "check:lint" "check:format" "check:types" ];
  tasks."base:test".after = [ "test:full" ];
}

#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, S3). Builds a library repo with tags v1 and v2.
# Usage: lib-setup.sh REPOS_DIR   (creates REPOS_DIR/lib with tags v1, v2)
set -euo pipefail
repos=$1
mkdir -p "$repos/lib/devenv"
cd "$repos/lib"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
git init -q -b main
cat > devenv/devenv.nix <<'NIX'
{ lib, config, pkgs, ... }:
let cfg = config.demo; in
{
  options.demo = {
    enable = lib.mkEnableOption "the demo";
    greeting = lib.mkOption { type = lib.types.str; default = "hello"; description = "A greeting."; };
    mode = lib.mkOption { type = lib.types.enum [ "fast" "slow" ]; default = "fast"; description = "Speed."; };
    count = lib.mkOption { type = lib.types.nullOr lib.types.int; default = null; description = "A count."; };
    tags = lib.mkOption { type = lib.types.listOf lib.types.str; default = [ ]; description = "Tags."; };
    users = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule {
        options = {
          uid = lib.mkOption { type = lib.types.int; description = "User id."; };
          shell = lib.mkOption { type = lib.types.str; default = "bash"; description = "Shell."; };
        };
      });
      default = { };
      description = "Users.";
    };
    settings = lib.mkOption {
      type = lib.types.submodule {
        freeformType = lib.types.attrsOf lib.types.str;
        options.level = lib.mkOption { type = lib.types.int; default = 1; description = "Level."; };
      };
      default = { };
      description = "Free-form settings.";
    };
    package = lib.mkOption { type = lib.types.package; default = pkgs.hello; defaultText = lib.literalExpression "pkgs.hello"; description = "A package."; };
  };
  config = lib.mkIf cfg.enable {
    env.DEMO_GREETING = cfg.greeting;
  };
}
NIX
git add -A; git commit -q -m v1; git tag v1
# v2: adds demo.newOption
python3 -I - <<'PY'
import pathlib
p = pathlib.Path("devenv/devenv.nix")
t = p.read_text()
t = t.replace('    package = lib.mkOption', '    newOption = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; description = "Added in v2."; };\n    package = lib.mkOption')
t = t.replace('env.DEMO_GREETING = cfg.greeting;', 'env.DEMO_GREETING = cfg.greeting;\n    env.DEMO_NEW = if cfg.newOption == null then "unset" else cfg.newOption;')
p.write_text(t)
PY
git add -A; git commit -q -m v2; git tag v2

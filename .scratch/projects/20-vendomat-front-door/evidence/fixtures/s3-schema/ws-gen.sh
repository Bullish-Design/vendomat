#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, S3). Writes the workspace stubs and the .vendomat/
# fragment for a given tag. Mimics `vendomat` step 2 (generate input fragment).
# Usage: ws-gen.sh WS PORT TAG [DATA_JSON]   DATA_JSON defaults to {} (neutral data).
set -euo pipefail
ws=$1; port=$2; tag=$3; data=${4:-'{}'}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$ws/.vendomat"
[ -f "$ws/devenv.yaml" ] || printf 'imports:\n  - ./.vendomat\n' > "$ws/devenv.yaml"
[ -f "$ws/devenv.nix" ] || printf '{ ... }: { }\n' > "$ws/devenv.nix"
cat > "$ws/.vendomat/devenv.yaml" <<YAML
# GENERATED (spike). Do not edit.
imports:
  - "demolib/devenv"
inputs:
  demolib:
    url: "git://127.0.0.1:$port/lib?ref=refs/tags/$tag"
    flake: false
  nixpkgs:
    url: "github:cachix/devenv-nixpkgs/256551e45f6303e142ab4a98be1bf243feb77dc0"
YAML
cat > "$ws/.vendomat/devenv.nix" <<'NIX'
# GENERATED (spike). Reads the data file unless the neutral switch is on. The switch lets the
# schema export run before validated user values exist. The switch is set with
#   devenv -O vendomat.neutral:bool true eval vendomat.schema.json
{ lib, config, ... }:
{
  imports = [ ./schema.nix ];
  options.vendomat.neutral = lib.mkOption {
    type = lib.types.bool;
    default = false;
    description = "Ignore .vendomat/config.json. Used by the schema export.";
  };
  config = lib.mkIf (!config.vendomat.neutral) (builtins.fromJSON (builtins.readFile ./config.json));
}
NIX
cp "$here/schema.nix" "$here/options-tree.nix" "$ws/.vendomat/"
printf '%s\n' "$data" > "$ws/.vendomat/config.json"

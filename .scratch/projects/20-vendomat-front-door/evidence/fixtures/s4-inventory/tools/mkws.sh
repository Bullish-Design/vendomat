#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, spike S4). Paths assume ~/.local/state/vendomat/p20/2026-10-11/S4.
# usage: mkws.sh <case> ; builds ws/<case> from the fixture, the repo module copy, and cases/<case>.json
set -euo pipefail
case=$1
R=/home/andrew/Documents/Projects/vendomat
FX=$R/.scratch/projects/20-vendomat-front-door/evidence/fixtures/s4-inventory
W=$HOME/.local/state/vendomat/p20/2026-10-11/S4/ws/$case
mkdir -p "$W/.vendomat" "$W/nix" "$W/.machines/box"
cp "$FX/basix-machines.nix" "$FX/devenv.nix" "$W/"; sed "s#@FORK@#$HOME/.local/state/vendomat/v7/2026-10-11/devenv-v2.4.0-vendomat.3#" "$FX/devenv.yaml" > "$W/devenv.yaml"
cp -r "$R/nix/devenv-module" "$W/nix/"
mkdir -p "$W/preflight" && cp "$R/preflight/vendomat-preflight" "$W/preflight/"
cp "$FX/cases/$case.json" "$W/.vendomat/config.json"
cp /nix/store/4v4gqlpwx3vlp9l104rcgj5632ljr2dd-source/hosts/basic/report.json "$W/.machines/box/facter.json"
chmod -R u+w "$W"
if [ -f "$HOME/.local/state/vendomat/p20/2026-10-11/S4/ws/valid/devenv.lock" ] && [ "$case" != valid ]; then
  cp "$HOME/.local/state/vendomat/p20/2026-10-11/S4/ws/valid/devenv.lock" "$W/"
fi
echo "$W"

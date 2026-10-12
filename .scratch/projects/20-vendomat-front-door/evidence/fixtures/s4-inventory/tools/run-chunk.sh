#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, spike S4). Paths assume ~/.local/state/vendomat/p20/2026-10-11/S4.
f=$1; base=${f%.in}
ulimit -v 16000000
start=$(date +%s)
timeout 600 nix eval --json --impure --expr "import $PWD/scripts/audit.nix { which = \"nixos\"; serviceChunk = builtins.fromJSON ''$(cat $f)''; }" > "$base.json" 2> "$base.err"
echo "$base rc=$? secs=$(( $(date +%s) - start ))" >> svc/_status.txt

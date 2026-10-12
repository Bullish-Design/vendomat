#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, spike S4). Paths assume ~/.local/state/vendomat/p20/2026-10-11/S4.
# usage: run-ns.sh <which> <dir> <dotted.path>
which=$1; dir=$2; path=$3
IFS=. read -ra parts <<< "$path"
nixlist="[$(for p in "${parts[@]}"; do printf '"%s" ' "$p"; done)]"
ulimit -v 16000000
start=$(date +%s)
timeout 300 nix eval --json --impure --expr "import $PWD/scripts/audit.nix { which = \"$which\"; onlyPath = $nixlist; }" > "$dir/$path.json" 2> "$dir/$path.err"
rc=$?
echo "$path rc=$rc secs=$(( $(date +%s) - start ))" >> "$dir/_status.txt"

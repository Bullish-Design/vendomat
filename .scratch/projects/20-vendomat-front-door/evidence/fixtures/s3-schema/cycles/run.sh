#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, S3). Runs each cycle case with neutral and user data.
# Usage: run.sh WS DEVENV LOGDIR   (WS holds a v1 lock and .vendomat/)
set -uo pipefail
ws=$1; dv=$2; L=$3; here=$(cd "$(dirname "$0")" && pwd)
cd "$ws"
user='{"demo":{"enable":true,"mode":"slow","greeting":"hi","users":{"bob":{"uid":1}}}}'
for c in "$here"/c[0-9]*.nix; do
  n=$(basename "$c" .nix); cp "$c" devenv.nix; cp "$here/c-extra.nix" ./c-extra.nix
  for d in neutral user; do
    if [ $d = neutral ]; then echo '{}' > .vendomat/config.json; else echo "$user" > .vendomat/config.json; fi
    timeout 300 "$dv" --no-eval-cache eval vendomat.schema.json > "$L/q2-$n-$d.out" 2> "$L/q2-$n-$d.err"
    echo "$n $d exit=$? bytes=$(wc -c < "$L/q2-$n-$d.out")"
  done
done
printf '{ ... }: { }\n' > devenv.nix; rm -f c-extra.nix; echo '{}' > .vendomat/config.json

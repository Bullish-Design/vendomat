#!/usr/bin/env bash
# S2 driver (NON-PRODUCTION): runcase.sh WS L G U [fileMode] -> per-key result from the pinned fork devenv.
WS=$1; L=$2; G=$3; U=$4; FM=${5:-yaml}
DV=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
LOGDIR=${LOGDIR:-$HOME/.local/state/vendomat/p20/2026-10-11/S2/logs/real}
HERE=$(dirname "$(readlink -f "$0")")
cd "$WS" || exit 3
echo "## CASE L=$L G=$G U=$U file=$FM  [$($DV version)]"
for k in ${KEYS:-env_FOO packages py shell str int lstr}; do
  python3 -I "$HERE/case.py" "$WS" "$L" "$G" "$U" "$FM" $k || exit 3
  mkdir -p "$LOGDIR"
  out=$(NO_COLOR=1 timeout 300 $DV eval vtest.probe.$k 2>&1 | sed 's/\x1b\[[0-9;]*m//g'; exit ${PIPESTATUS[0]})
  rc=$?
  printf '%s\n' "$out" > "$LOGDIR/L${L}_G${G}_U${U}_${FM}.$k.log"
  if [ $rc -eq 0 ]; then echo "$k => $(echo "$out" | tr -d '\n ' | sed 's/^{"vtest.probe.[a-zA-Z_]*"://; s/}$//')"; else echo "$k => ERROR rc=$rc"; printf '%s\n' "$out" | awk '/^ *error: /{f=1} f' | sed 's/^/    /' | head -${ERRLINES:-12}; fi
done

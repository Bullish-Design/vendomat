#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
# Usage: timing.sh  — warm-eval timings on ws/ for identical rewrite, skip, touch, content change.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5
F=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
cd "$S5/ws" || exit 9
N=${N:-7}
now() { echo $EPOCHREALTIME; }
shell() { local a=$EPOCHREALTIME; "$S5/cleanenv.sh" $F "$@" </dev/null >/dev/null 2>&1; local rc=$?; local b=$EPOCHREALTIME; awk -v a=$a -v b=$b -v rc=$rc 'BEGIN{printf "%.3f %d\n", b-a, rc}'; }
stat_line() { # label, file of "secs rc"
  sort -n "$2" | awk -v l="$1" '{v[NR]=$1; rc[NR]=$2} END{printf "%-34s n=%d min=%.3f median=%.3f max=%.3f rc_nonzero=%d\n", l, NR, v[1], v[int((NR+1)/2)], v[NR], 0}'
}
run_variant() { # label, pre-command
  local label=$1; shift; local out=$S5/logs/timing-$label.txt; : > $out
  for i in $(seq 1 $N); do
    eval "$1" >/dev/null 2>&1
    shell shell -- true >> $out
  done
  stat_line "$label" $out
}
PREP="python3 -I $S5/prep.py ."
$S5/cleanenv.sh $F shell -- true >/dev/null 2>&1   # warm up
run_variant V0-warm-nochange "true"
run_variant V2-prep-skip-write "$PREP"
run_variant V1-prep-identical-rewrite "$PREP --force-rewrite"
run_variant V3-touch-mtime-only "touch .vendomat/* vendomat.yaml"
run_variant V5-touch-devenv.yaml-only "touch .vendomat/devenv.yaml"
# content change: alternate GREETING each iteration
i=0; out=$S5/logs/timing-V4-content-change.txt; : > $out
for k in $(seq 1 $N); do
  i=$((i+1)); sed -i "s/GREETING: \".*\"/GREETING: \"v$i\"/" vendomat.yaml
  python3 -I $S5/prep.py . 2>/dev/null
  shell shell -- true >> $out
done
stat_line "V4-content-change(env value)" $out
sed -i 's/GREETING: ".*"/GREETING: "hi"/' vendomat.yaml; python3 -I $S5/prep.py . 2>/dev/null
out=$S5/logs/timing-V6-no-eval-cache.txt; : > $out
for k in $(seq 1 3); do shell --no-eval-cache shell -- true >> $out; done
stat_line "V6-no-eval-cache" $out
$S5/cleanenv.sh $F shell -- true >/dev/null 2>&1

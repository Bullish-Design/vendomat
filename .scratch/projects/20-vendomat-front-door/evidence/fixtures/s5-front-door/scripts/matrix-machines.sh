#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
# Usage: matrix-machines.sh FORM|none   (fxm/ fixture: guard forms + a preview machine)
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5
F=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
form=$1; cd "$S5/fxm" || exit 9
logs=$S5/logs/machines; mkdir -p "$logs"
[ "$form" != none ] && touch "stale-$form"
run() {
  name=$1; shift; t0=$EPOCHREALTIME
  timeout -k 5 ${TMO:-240} "$S5/cleanenv.sh" "$@" </dev/null > "$logs/$form-$name.log" 2>&1; rc=$?
  t1=$EPOCHREALTIME
  fired=$(grep -o -E 'GUARD-[A-Z0-9]+( |-FIRED)' "$logs/$form-$name.log" | sort -u | tr '\n' ',')
  printf '%s | %s | rc=%s | %.2fs | fired=%s\n' "$form" "$name" "$rc" "$(awk -v a="$t0" -v b="$t1" 'BEGIN{print b-a}')" "${fired:-no}" | tee -a "$logs/summary.txt"
}
run machines-info "$F" machines info
run build-machine "$F" build machines.server.build.nixos
run machines-plan "$F" machines plan server
run machines-check "$F" machines check server
run machines-status "$F" machines status server
run shell-true "$F" shell -- true
rm -f "stale-$form"

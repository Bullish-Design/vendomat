#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
# Usage: matrix.sh FORM|none
# Runs every devenv command in fx/ with the marker file stale-FORM present. Logs in logs/FORM-NAME.log.
# Summary line: FORM | NAME | rc | seconds | fired(GUARD-x seen) | cmd
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5
F=${DEVENV:-/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv}
form=$1
cd "$S5/fx" || exit 9
logs=$S5/logs/${TAG:-run}; mkdir -p "$logs"
[ "$form" != none ] && touch "stale-$form"
run() { # name, then command words
  name=$1; shift
  local t0 t1 rc
  t0=$EPOCHREALTIME
  timeout -k 5 "${TMO:-180}" "$S5/cleanenv.sh" "$@" </dev/null > "$logs/$form-$name.log" 2>&1
  rc=$?
  t1=$EPOCHREALTIME
  fired=$(grep -o -E 'GUARD-[A-Z0-9]+( |-FIRED)' "$logs/$form-$name.log" | sort -u | tr '\n' ',')
  printf '%s | %s | rc=%s | %.2fs | fired=%s | %s\n' "$form" "$name" "$rc" "$(awk -v a="$t0" -v b="$t1" 'BEGIN{print b-a}')" "${fired:-no}" "$*" | tee -a "$logs/summary.txt"
}
run shell-true "$F" shell -- true
run test "$F" test
run build "$F" build
run build-shell "$F" build shell
run eval-env "$F" eval env
run tasks-run "$F" tasks run s5:hello
run tasks-list "$F" tasks list
run info "$F" info
run search "$F" search hello
run repl bash -c "echo ':q' | $F repl"
run print-dev-env "$F" print-dev-env
run direnv-export env _DEVENV_CALLER=direnv "$F" direnv-export
run direnvrc "$F" direnvrc
run container-build "$F" container build s5
run machines-info "$F" machines info
# gc omitted: devenv gc hung 185 s twice and may run a store GC (rule: no nix GC)
run up-timeout timeout -s INT 25 "$F" up
run processes-up timeout -s INT 25 "$F" processes up
run update "$F" update
rm -f "stale-$form"

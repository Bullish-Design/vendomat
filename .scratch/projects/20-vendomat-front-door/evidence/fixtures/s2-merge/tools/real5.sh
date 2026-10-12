#!/usr/bin/env bash
# S2 (NON-PRODUCTION): real5.sh 'JSON' [lines-json] [attr...]  -> eval probe attrs in ws5 with the pinned fork.
S=$HOME/.local/state/vendomat/p20/2026-10-11/S2
DV=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
cd $S/ws5 || exit 3
printf '%s' "$1" > .vendomat/config.json
if [ -n "$2" ]; then printf '%s' "$2" > .vendomat/lines.json; else rm -f .vendomat/lines.json; fi
shift; shift
for a in "${@:-vtest.probe}"; do
  out=$(NO_COLOR=1 timeout 300 $DV eval "$a" 2>&1 | sed 's/\x1b\[[0-9;]*m//g'; exit ${PIPESTATUS[0]}); rc=$?
  echo "## $a rc=$rc"
  if [ $rc -eq 0 ]; then echo "$out" | tr -d '\n ' ; echo; else printf '%s\n' "$out" | awk '/^ *error: /{f=1} f' | head -${ERRLINES:-10}; fi
done

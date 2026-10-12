#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/q3b/B-committed
F=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
sed -i 's/GREETING: "hi"/GREETING: "edited"/' vendomat.yaml
for cmd in "eval shell.drvPath" "shell -- true" "build shell" "test" "tasks run devenv:enterShell"; do
  $S5/cleanenv.sh timeout 100 $F $cmd </dev/null >$S5/logs/q3-stale.log 2>&1; rc=$?
  echo "hand-edited vendomat.yaml: devenv $cmd -> rc=$rc | $(sed 's/\x1b\[[0-9;]*m//g' $S5/logs/q3-stale.log | grep -m1 'vendomat:' | cut -c1-120)"
done
git checkout -q vendomat.yaml
echo "# hand edit" >> .vendomat/devenv.yaml
$S5/cleanenv.sh timeout 100 $F shell -- true </dev/null 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -m1 "vendomat:" | sed 's/^/hand-edited .vendomat\/devenv.yaml: /'
git checkout -q .vendomat

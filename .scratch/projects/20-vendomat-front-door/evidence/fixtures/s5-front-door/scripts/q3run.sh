#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/q3b
F=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
ST=/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0/bin/devenv
for c in B-committed A-ignored C-emptydir D-nixonly E-yamlonly; do for tool in fork stock; do
  bin=$F; [ $tool = stock ] && bin=$ST
  s=$EPOCHREALTIME
  (cd $c && $S5/cleanenv.sh timeout 250 $bin eval shell.drvPath env.S5_TOOLS_MOD </dev/null >../$c-$tool.log 2>&1; echo "rc=$?" >> ../$c-$tool.log)
  e=$EPOCHREALTIME
  echo "== $c / $tool $(tail -1 $c-$tool.log) $(awk -v a=$s -v b=$e 'BEGIN{printf "%.1fs",b-a}')"
  sed 's/\x1b\[[0-9;]*m//g' $c-$tool.log | grep -E "error:|S5_TOOLS_MOD|× " | head -3 | cut -c1-230
done; done

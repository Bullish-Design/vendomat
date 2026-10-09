#!/usr/bin/env bash
# face-check.sh <workspace> <input-name> [host=test] [user=alice]
# FACE-002 / MOD-013 inertness check. Evaluates the workspace WITH the library input (modules built, all disabled)
# and WITHOUT it, in the same absolute path, then compares three derivation paths:
#   devenv shell, the NixOS toplevel of <host>, the Home Manager activation package of <user> on <host>.
# Exit 0 when all three are equal. Exit 1 and print the differing target otherwise.
set -uo pipefail
src=$(realpath "$1"); lib=$2; host=${3:-test}; user=${4:-alice}
tmp=$(mktemp -d); ws=$tmp/ws; mkdir -p $ws
declare -A attr=(
  [shell]='shell.drvPath'
  [nixos]="machines.$host._nixosEval.config.system.build.toplevel.drvPath"
  [home-manager]="machines.$host._nixosEval.config.home-manager.users.$user.home.activationPackage.drvPath"
)
evalall() {  # $1 = label ; prints "<target> <drvPath>" lines
  rm -rf $ws/.devenv
  for t in shell nixos home-manager; do
    p=$(cd $ws && devenv --no-eval-cache eval "${attr[$t]}" 2>$tmp/err.$1.$t | jq -r '.[]') || { echo "$t EVAL-FAILED:$(tail -n 3 $tmp/err.$1.$t | tr '\n' ' ')"; continue; }
    echo "$t $p"
  done
}
cp -r $src/. $ws/; rm -rf $ws/.devenv
evalall with > $tmp/with.txt
# drop the library block from devenv.yaml and from devenv.lock inputs (devenv relocks)
awk -v n="$lib" '$0 ~ "^  "n":" {skip=1; next} skip && /^    / {next} {skip=0; print}' $src/devenv.yaml > $ws/devenv.yaml
# keep devenv.lock: devenv drops the unused node and does not bump the others
evalall without > $tmp/without.txt
status=0
while read -r t w; do
  wo=$(awk -v t="$t" '$1==t{print $2}' $tmp/without.txt)
  if [ "$w" = "$wo" ] && [[ $w != EVAL-FAILED* ]]; then echo "PASS  $t  $w"; else echo "FAIL  $t  with=$w without=$wo"; status=1; fi
done < $tmp/with.txt
rm -rf $tmp
exit $status

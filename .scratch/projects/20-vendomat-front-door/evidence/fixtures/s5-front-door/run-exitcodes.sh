#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION. Verifies the proposed exit code table on the prototype front door.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5
HERE="$(cd "$(dirname "$0")" && pwd)"
W=$S5/exitws; [ -d $W ] || git clone -q $S5/ws $W
cd $W
export VENDOMAT_DEVENV=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
V="$S5/cleanenv.sh env VENDOMAT_DEVENV=$VENDOMAT_DEVENV python3 -I $HERE/vendomat-proto.py"
cp vendomat.yaml vendomat.yaml.good
t() { label=$1; shift; "$@" >$S5/logs/exit-last.log 2>&1; rc=$?; echo "$label -> rc=$rc | $(sed 's/\x1b\[[0-9;]*m//g' $S5/logs/exit-last.log | grep -m1 -E 'vendomat:|error|×' | cut -c1-110)"; }
t "ok: shell -- true"                      $V shell -- true
t "command code passthrough: sh -c 'exit 7'" $V shell -- sh -c 'exit 7'
t "devenv failure: tasks run no:such"       $V tasks run no:such
t "devenv usage error: frobnicate"          $V frobnicate
t "no command"                              $V
printf 'packages:\n\t- "hello"\n' > vendomat.yaml
t "lint fault (tab)"                        $V shell -- true
printf 'packages: "hello"\n' > vendomat.yaml
t "schema fault (string for list)"          $V shell -- true
cp vendomat.yaml.good vendomat.yaml
t "recovered: shell -- true"                $V shell -- true
# launcher codes
S=$S5/launcher
L="$HERE/launcher-proto.sh"
export VENDOMAT_HOST_RELEASE=$S/host-release VENDOMAT_LAUNCHER_CACHE=$S/cache-proto2; mkdir -p $S/cache-proto2
( cd $S/wsC && t "launcher: pinned build missing" $L shell )
( cd $S/wsB && t "launcher: pinned build, protocol mismatch (pre-protocol build)" $L shell )
( cd $S/wsB && VENDOMAT_HOST_RELEASE=/nonexistent t "launcher: no host release (no lock case via wsA)" bash -c "cd $S/wsA && command rm -f devenv.lock && $L shell" )
echo "{bad" > $S/wsD/devenv.lock; echo "packages:" > $S/wsD/vendomat.yaml; ( cd $S/wsD && t "launcher: lock unreadable" $L shell )

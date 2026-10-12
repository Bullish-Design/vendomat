#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION. Drives launcher-proto.sh in the disposable dirs of the S5 run.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5/launcher
HERE="$(cd "$(dirname "$0")" && pwd)"
L=$HERE/launcher-proto.sh
export VENDOMAT_HOST_RELEASE=$S5/host-release VENDOMAT_LAUNCHER_CACHE=$S5/cache-proto
mkdir -p "$S5/cache-proto" "$S5/outP1/bin" "$S5/outP1/share/vendomat" "$S5/outP23/bin" "$S5/outP23/share/vendomat"
for o in outP1 outP23; do printf '#!/usr/bin/env bash\necho "PINNED-%s ran: $* kind=$VENDOMAT_RELEASE_KIND proto=$VENDOMAT_LAUNCHER_PROTOCOL by=$VENDOMAT_LAUNCHED_BY"\n' $o > $S5/$o/bin/vendomat; chmod +x $S5/$o/bin/vendomat; done
echo "1 1" > $S5/outP1/share/vendomat/launcher-protocol
echo "2 3" > $S5/outP23/share/vendomat/launcher-protocol
HEXB=$(printf '%s' "2y7q9sVoebLWsSNbaDEgPYFtZUevwL1PvYUv2aav54Y=" | base64 -d | od -v -An -tx1 | tr -d ' \n')
for ws in wsA wsB wsC; do [ -f $S5/$ws/vendomat.yaml ] || echo 'packages:' > $S5/$ws/vendomat.yaml; done
case_() { # label, ws, env-assignments..., -- args
  label=$1; ws=$2; envs=$3; shift 3
  echo "### $label"
  ( cd "$S5/$ws" && env $envs "$L" "$@"; echo "rc=$?" ) 2>&1 | sed 's/^/    /'
}
echo -n "$S5/outP1" > $S5/cache-proto/$HEXB
case_ "(b) valid pin, protocol 1 accepted: shell"      wsB "VENDOMAT_X=1" shell
case_ "(b) valid pin: arbitrary devenv command"        wsB "VENDOMAT_X=1" tasks run foo
echo -n "$S5/outP23" > $S5/cache-proto/$HEXB
case_ "(d) pinned build needs 2..3, launcher speaks 1" wsB "VENDOMAT_X=1" shell
case_ "(d) same, launcher newer (max 2)"               wsB "VENDOMAT_LAUNCHER_PROTOCOL_MAX=2" shell
echo -n "$S5/drs42hqs56pwwa3vw0r21r5cqgn8q0hn-vendomat" > $S5/cache-proto/$HEXB   # real pre-protocol build, no file
case_ "(d') pre-protocol pinned build (no file)"       wsB "VENDOMAT_X=1" shell
command rm -f $S5/cache-proto/$HEXB
case_ "(b') valid pin, no cache file: offline build"   wsB "VENDOMAT_X=1" shell
case_ "(a) no lock, host release"                      wsA "VENDOMAT_X=1" shell
case_ "(c) pin absent from store"                      wsC "VENDOMAT_X=1" shell
case_ "(c') pin absent, explicit host"                 wsC "VENDOMAT_USE_HOST=1" sync

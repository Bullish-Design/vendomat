#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
L=/home/andrew/Documents/Projects/vendomat/launcher/vendomat
cd "$(dirname "$0")"; export VENDOMAT_HOST_RELEASE=$PWD/host-release VENDOMAT_LAUNCHER_CACHE=$PWD/cache
for c in "wsC sync" "wsC --version" "wsB sync"; do set -- $c; ws=$1; shift; echo "### $ws $*"; ( cd "$ws" && s=$EPOCHREALTIME; ../../cleanenv.sh "$L" "$@"; echo "rc=$?"; awk -v a=$s -v b=$EPOCHREALTIME 'BEGIN{printf "time=%.2fs\n", b-a}' ); done
echo "### VENDOMAT_USE_HOST=1 in wsB"; ( cd wsB && VENDOMAT_USE_HOST=1 ../../cleanenv.sh "$L" sync; echo "rc=$?" )
echo "### no host release + missing pin"; ( cd wsC && VENDOMAT_HOST_RELEASE=/nonexistent ../../cleanenv.sh "$L" sync; echo "rc=$?" )
echo "### outside workspace"; ( cd /tmp && ../home/andrew/.local/state/vendomat/p20/2026-10-11/S5/cleanenv.sh "$L" sync; echo "rc=$?" )

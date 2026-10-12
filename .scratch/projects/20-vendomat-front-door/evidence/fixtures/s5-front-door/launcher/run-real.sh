#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
L=/home/andrew/Documents/Projects/vendomat/launcher/vendomat
cd "$(dirname "$0")"
export VENDOMAT_HOST_RELEASE=$PWD/host-release VENDOMAT_LAUNCHER_CACHE=$PWD/cache
mkdir -p cache
for c in "wsA sync" "wsA shell" "wsB sync" "wsB sync" "wsB shell" "wsC sync" "wsC shell"; do
  set -- $c; ws=$1; shift
  echo "### $ws $*"
  ( cd "$ws" && s=$EPOCHREALTIME && ../../cleanenv.sh "$L" "$@"; echo "rc=$?"; awk -v a=$s -v b=$EPOCHREALTIME 'BEGIN{printf "time=%.2fs\n", b-a}' )
done
echo "### cache dir:"; ls cache

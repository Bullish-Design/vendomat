#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, spike S4). Paths assume ~/.local/state/vendomat/p20/2026-10-11/S4.
# usage: run-cases.sh  (runs each negative case; writes logs/<case>.{out,err,rc})
S=$HOME/.local/state/vendomat/p20/2026-10-11/S4
D=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
mkdir -p $S/logs
declare -A HOSTS=( [rawname-nvme]=box [rawname-sda]=box [missing-byid]=box [adopt-with-target]=laptop [target-equals-keep]=box [unknown-input]=box [fs-kernel-name]=laptop [bad-mode]=laptop [missing-stateversion]=box [bypass-guard-kernel-name]=raw [lazy-bad-target]=box [report-dotdot]=box [report-missing]=box )
for c in "${!HOSTS[@]}"; do
  h=${HOSTS[$c]}
  $S/scripts/mkws.sh $c > /dev/null
  cp "$(dirname "$(readlink -f "$0")")/../probe.local-template.nix" $S/ws/$c/devenv.local.nix 
  # the probe is not needed for a failing case; remove it so the failure is the build.nixos path
  rm -f $S/ws/$c/devenv.local.nix
  (cd $S/ws/$c && timeout 300 $D eval machines.$h.build.nixos > $S/logs/$c.out 2> $S/logs/$c.err; echo $? > $S/logs/$c.rc)
  echo "$c host=$h rc=$(cat $S/logs/$c.rc)"
done

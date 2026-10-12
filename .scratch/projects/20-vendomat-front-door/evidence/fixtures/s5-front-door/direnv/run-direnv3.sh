#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/dr/wsd
export XDG_CONFIG_HOME=$S5/dr/cfg XDG_DATA_HOME=$S5/dr/data XDG_CACHE_HOME=$S5/dr/state
export DEVENV_BIN=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv VENDOMAT_PREP=$S5/dr/prepwrap.sh
unset DIRENV_DIR DIRENV_FILE DIRENV_WATCHES DIRENV_DIFF DIRENV_ACTIVE IN_NIX_SHELL VIRTUAL_ENV NIX_PYTHONPATH PYTHONPATH
for v in $(compgen -e | grep -E '^DEVENV_' | grep -v '^DEVENV_BIN$'); do unset $v; done
cp vendomat.yaml.good vendomat.yaml; python3 -I $S5/prep.py . 2>/dev/null
for variant in devenv vendomat devenv vendomat; do
  cp .envrc.$variant .envrc; direnv allow .
  direnv exec . true >/dev/null 2>&1   # warm
  arr=(); for i in 1 2 3 4 5 6 7; do a=$EPOCHREALTIME; direnv exec . true >/dev/null 2>&1; b=$EPOCHREALTIME; arr+=("$(awk -v a=$a -v b=$b 'BEGIN{printf "%.3f",b-a}')"); done
  printf 'use %-8s warm direnv exec: ' $variant; printf '%s\n' "${arr[@]}" | sort -n | awk '{v[NR]=$1} END{printf "min=%.3f median=%.3f max=%.3f s\n", v[1], v[4], v[7]}'
done

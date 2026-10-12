#!/usr/bin/env bash
# S2 batch (NON-PRODUCTION): real-devenv matrix on the pinned fork. Output: logs/real-matrix.txt
S=$HOME/.local/state/vendomat/p20/2026-10-11/S2
for c in "0 p 0" "p p 0" "d p 0" "p d 0" "f p 0" "p o90 0" "p o100 0" "0 p p" "0 p f" "0 o90 p" "p o90 p" "d p f" "f f 0" "0 f f" "p p p" "d d 0" "p o60 0" "p o75 0"; do
  set -- $c
  ERRLINES=6 "$S/tools/runcase.sh" "$S/ws2" "$1" "$2" "$3" yaml
done
for c in "b p 0" "a p 0" "p p 0" "b p p" "a p p"; do
  set -- $c
  KEYS="packages shell lstr" ERRLINES=6 "$S/tools/runcase.sh" "$S/ws2" "$1" "$2" "$3" yaml
done
echo BATCH-DONE

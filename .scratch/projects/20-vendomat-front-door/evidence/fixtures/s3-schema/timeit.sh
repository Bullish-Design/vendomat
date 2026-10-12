#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, S3). Times one command; appends a line to $L/timings.tsv.
# Needs DEVENV and L in the environment. Usage: timeit.sh LABEL CMD...
label=$1; shift
s=$(date +%s%N)
"$@" > "$L/$label.out" 2> "$L/$label.err"; rc=$?
e=$(date +%s%N)
printf '%s\t%s s\texit %s\t%s\n' "$label" "$(python3 -c "print(round(($e-$s)/1e9,2))")" "$rc" "$($DEVENV version)" | tee -a "$L/timings.tsv"

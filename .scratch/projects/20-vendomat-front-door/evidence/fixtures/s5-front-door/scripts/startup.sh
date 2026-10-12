#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5
V=/home/andrew/Documents/Projects/vendomat/.devenv/state/venv/bin/python3
t() { local label=$1; shift; local arr=(); for i in 1 2 3 4 5 6 7 8 9 10; do a=$EPOCHREALTIME; "$@" >/dev/null 2>&1; b=$EPOCHREALTIME; arr+=("$(awk -v a=$a -v b=$b 'BEGIN{printf "%.1f", (b-a)*1000}')"); done; printf '%-48s ' "$label"; printf '%s\n' "${arr[@]}" | sort -n | awk '{v[NR]=$1} END{printf "min=%.1f median=%.1f max=%.1f ms\n", v[1], v[int((NR+1)/2)], v[NR]}'; }
t "python3 -I -c pass (host python)" python3 -I -c pass
t "prep.py incl. python start, no write" python3 -I $S5/prep.py $S5/ws
t "prep.py incl. python start, force rewrite" python3 -I $S5/prep.py $S5/ws --force-rewrite
t "venv python -c pass" $V -c pass
t "venv python import vendomat.cli" $V -c "import vendomat.cli"
t "venv vendomat --version" /home/andrew/Documents/Projects/vendomat/.devenv/state/venv/bin/vendomat --version
t "devenv version (fork)" /nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv version
t "sha256sum + cmp style shell check (sha256sum x2)" bash -c "sha256sum $S5/ws/vendomat.yaml $S5/ws/.vendomat/digest"

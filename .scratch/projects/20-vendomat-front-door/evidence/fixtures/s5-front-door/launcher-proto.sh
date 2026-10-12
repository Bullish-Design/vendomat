#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION. Prototype of the project 20 host launcher (proposed protocol 1).
# Differences from launcher/vendomat (V5): it serves EVERY command, it reads vendomat.yaml,
# it never falls back to the host release for a pinned workspace, and it speaks a protocol.
#
# Env in:  VENDOMAT_HOST_RELEASE (bin/vendomat of the host release), VENDOMAT_LAUNCHER_CACHE,
#          VENDOMAT_USE_HOST=1 (explicit), VENDOMAT_LAUNCHER_PROTOCOL_MAX (test knob, default 1).
# Env out: VENDOMAT_LAUNCHER_PROTOCOL=<n>, VENDOMAT_LAUNCHED_BY=launcher, VENDOMAT_RELEASE_KIND=pinned|host
# File:    a Vendomat build declares the protocols it accepts in $out/share/vendomat/launcher-protocol
#          as "MIN MAX". A build without the file is treated as "0 0" (pre-protocol).
# Exit:    69 pinned build unavailable, 70 launcher protocol mismatch, 71 no host release,
#          72 lock unreadable. Any other code is the command's own.
set -euo pipefail
PROTO=${VENDOMAT_LAUNCHER_PROTOCOL_MAX:-1}
host_release="${VENDOMAT_HOST_RELEASE:-@HOST_RELEASE@}"
say() { printf 'vendomat: %s\n' "$*" >&2; }
export VENDOMAT_LAUNCHER_PROTOCOL=$PROTO VENDOMAT_LAUNCHED_BY=launcher

run_host() {
  [ -x "$host_release" ] || { say "no host release at $host_release"; exit 71; }
  export VENDOMAT_RELEASE_KIND=host
  exec "$host_release" "$@"
}

root=""; dir="$PWD"
while [ "$dir" != "/" ]; do
  if [ -f "$dir/vendomat.yaml" ]; then root="$dir"; break; fi
  dir="$(dirname "$dir")"
done
[ "${VENDOMAT_USE_HOST:-}" = 1 ] && { say "VENDOMAT_USE_HOST=1: using the host release"; run_host "$@"; }
[ -n "$root" ] || run_host "$@"                       # outside a workspace: host release

lock="$root/devenv.lock"
if [ ! -f "$lock" ]; then
  say "$root has no devenv.lock; the host release creates the first lock"
  run_host "$@"
fi
nar="$(jq -r '.nodes.vendomat.locked.narHash // empty' "$lock" 2>/dev/null)" || { say "cannot read $lock"; exit 72; }
if [ -z "$nar" ]; then
  say "$lock pins no vendomat input; the host release creates the pin"
  run_host "$@"
fi
hex="$(printf '%s' "${nar#sha256-}" | base64 -d | od -v -An -tx1 | tr -d ' \n')"   # od -v: no '*' for repeats
cache="${VENDOMAT_LAUNCHER_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/vendomat/launcher}"; mkdir -p "$cache"
out=""
[ -f "$cache/$hex" ] && { out="$(cat "$cache/$hex")"; [ -x "$out/bin/vendomat" ] || out=""; }
if [ -z "$out" ]; then
  store="$(nix-store --print-fixed-path --recursive sha256 "$hex" source)"
  if [ -d "$store" ]; then
    out="$(nix build --offline --no-link --print-out-paths "path:$store#packages.$(uname -m)-linux.vendomat" 2>/dev/null || true)"
  fi
  [ -n "$out" ] && printf '%s' "$out" > "$cache/$hex"
fi
if [ -z "$out" ] || [ ! -x "$out/bin/vendomat" ]; then
  say "the Vendomat build pinned by $lock ($nar) is not in the store, and offline entry cannot build it"
  say "reconnect, then run: VENDOMAT_USE_HOST=1 vendomat sync"
  exit 69
fi
# Protocol handshake, before the pinned build runs.
range="$(cat "$out/share/vendomat/launcher-protocol" 2>/dev/null || echo "0 0")"
read -r pmin pmax <<<"$range"
if [ "$PROTO" -lt "$pmin" ] || [ "$PROTO" -gt "$pmax" ]; then
  say "the pinned Vendomat accepts launcher protocol $pmin..$pmax; this host launcher speaks $PROTO"
  say "update the host release, or run the pinned build directly: $out/bin/vendomat"
  exit 70
fi
export VENDOMAT_RELEASE_KIND=pinned VENDOMAT_PINNED_BUILD=$out
exec "$out/bin/vendomat" "$@"

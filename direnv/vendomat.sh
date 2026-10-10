# Source this file from a direnv library, then call `use_vendomat` in `.envrc`.
#
#   source_url ... or: source "$(dirname "$(command -v vendomat)")/../share/vendomat/direnv/vendomat.sh"
#
# `use_vendomat` re-runs `vendomat sync` only when the digest is stale, then calls `use devenv`
# (PRE-009). It needs `vendomat` (the host launcher), `sha256sum`, and `awk` on PATH. With nothing
# changed it runs two hashes and no Nix command.

_vendomat_sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
_vendomat_recorded() { awk -v k="$1" '$1 == k { print $2 }' "$2" 2>/dev/null; }

# Print why the workspace in $1 needs a sync, or nothing when it is current.
_vendomat_stale() {
  local root="$1" digest="$1/.vendomat/digest"
  [ -f "$digest" ] || { echo "no digest"; return; }
  [ "$(_vendomat_sha "$root/vendomat.toml")" = "$(_vendomat_recorded registry "$digest")" ] || { echo "registry changed"; return; }
  [ "$(_vendomat_sha "$root/.vendomat/devenv.yaml")" = "$(_vendomat_recorded fragment "$digest")" ] || { echo "fragment edited"; return; }
  [ "$(_vendomat_sha "$root/.vendomat/devenv.nix")" = "$(_vendomat_recorded module "$digest")" ] || { echo "module edited"; return; }
  [ -f "$root/devenv.lock" ] || { echo "no lock"; return; }
}

use_vendomat() {
  local root="${1:-$PWD}"
  # Make direnv reload when the registry or the digest changes.
  watch_file "$root/vendomat.toml" "$root/.vendomat/digest"
  local why
  why="$(_vendomat_stale "$root")"
  if [ -n "$why" ]; then
    log_status "vendomat: $why; running sync"
    if ! vendomat sync --root "$root"; then
      log_error "vendomat: sync failed; the shell is not entered"
      return 1
    fi
  fi
  use devenv
}

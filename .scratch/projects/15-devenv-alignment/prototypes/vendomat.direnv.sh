# Sourced by .envrc. Defines use_vendomat.
# Needs: VENDOMAT_SYNC (command that syncs one workspace dir), sha256sum, awk.
_vendomat_sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }
_vendomat_recorded() { awk -v k="$1" '$1 == k { print $2 }' "$2" 2>/dev/null; }

use_vendomat() {
  local root="${1:-$PWD}"
  local digest="$root/.vendomat/digest"
  # Make direnv reload when the registry or the digest changes.
  watch_file "$root/vendomat.json" "$digest"
  local stale=""
  [ -f "$digest" ] || stale="no digest"
  [ -z "$stale" ] && [ "$(_vendomat_sha "$root/vendomat.json")" != "$(_vendomat_recorded registry "$digest")" ] && stale="registry changed"
  [ -z "$stale" ] && [ "$(_vendomat_sha "$root/.vendomat/devenv.yaml")" != "$(_vendomat_recorded fragment "$digest")" ] && stale="fragment edited"
  if [ -n "$stale" ]; then
    log_status "vendomat: $stale; running sync"
    if ! $VENDOMAT_SYNC "$root"; then
      log_error "vendomat: sync failed"
      return 1
    fi
  fi
  use devenv
}

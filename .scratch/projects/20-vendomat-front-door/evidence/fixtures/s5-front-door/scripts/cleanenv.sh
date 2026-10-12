#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
# Run a command with DEVENV_*, DIRENV_*, nix-shell and venv variables unset.
args=()
while IFS= read -r v; do args+=(-u "$v"); done < <(compgen -e | grep -E '^(DEVENV_|DIRENV_)')
exec env "${args[@]}" -u IN_NIX_SHELL -u VIRTUAL_ENV -u NIX_PYTHONPATH -u PYTHONPATH "$@"

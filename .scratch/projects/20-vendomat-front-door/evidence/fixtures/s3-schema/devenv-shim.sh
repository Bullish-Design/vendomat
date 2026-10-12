#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, S3). Logs each call, then runs the real devenv.
# Needs REAL_DEVENV and SHIM_LOG in the environment.
echo "$(date +%s.%N) $*" >> "$SHIM_LOG"
exec "$REAL_DEVENV" "$@"

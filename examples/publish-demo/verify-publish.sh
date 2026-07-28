#!/usr/bin/env bash
set -euo pipefail

demo_root=$(cd "$(dirname "$0")" && pwd)
workspace=$(mktemp -d)
trap 'rm -rf "$workspace"' EXIT

consumer="$workspace/consumer"
remote="$workspace/remote.git"
cp -R "$demo_root" "$consumer"

git init --bare "$remote" >/dev/null
git -C "$consumer" init -b main >/dev/null
git -C "$consumer" config user.name "Vendomat Demo"
git -C "$consumer" config user.email "vendomat-demo@example.invalid"

# Seed the remote with the public form, then create one local-vendor commit to publish.
vendomat materialize github --repo-root "$consumer" >/dev/null
git -C "$consumer" add .
git -C "$consumer" commit -m "Initial public dependency source" >/dev/null
git -C "$consumer" remote add origin "$remote"
git -C "$consumer" push origin main >/dev/null

vendomat materialize local --repo-root "$consumer" >/dev/null
git -C "$consumer" add pyproject.toml
git -C "$consumer" commit -m "Develop against the local vendor" >/dev/null
vendomat install-hook --repo-root "$consumer" >/dev/null

if git -C "$consumer" push origin main >/dev/null 2>&1; then
  echo "expected Vendomat to abort the outer push after publishing" >&2
  exit 1
fi

remote_source=$(git --git-dir="$remote" show main:pyproject.toml)
local_source=$(<"$consumer/pyproject.toml")
[[ "$remote_source" == *'git = "https://github.com/acme/acme-widget", tag = "v0.1.0"'* ]]
[[ "$local_source" == *'path = "vendor/acme-widget", editable = true'* ]]
echo "PASS: remote has the GitHub source; local checkout retains the editable vendor path."

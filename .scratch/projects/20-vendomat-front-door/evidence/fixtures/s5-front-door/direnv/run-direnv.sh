#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/dr/wsd
export XDG_CONFIG_HOME=$S5/dr/cfg XDG_DATA_HOME=$S5/dr/data XDG_CACHE_HOME=$S5/dr/state
export DEVENV_BIN=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
export VENDOMAT_PREP=$S5/dr/prepwrap.sh
unset DIRENV_DIR DIRENV_FILE DIRENV_WATCHES DIRENV_DIFF DIRENV_ACTIVE
for v in $(compgen -e | grep -E '^DEVENV_' | grep -v '^DEVENV_BIN$'); do unset $v; done; unset IN_NIX_SHELL VIRTUAL_ENV NIX_PYTHONPATH PYTHONPATH
tm() { local a=$EPOCHREALTIME; "$@"; local rc=$?; awk -v a=$a -v b=$EPOCHREALTIME -v rc=$rc 'BEGIN{printf "  [rc=%d time=%.2fs]\n", rc, b-a}'; }
setg() { sed -i "s/GREETING: \".*\"/GREETING: \"$1\"/" vendomat.yaml; }
direnv version
echo "## 1. use vendomat, clean tree (cold then warm)"
cp .envrc.vendomat .envrc; direnv allow .
tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -4
tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -4
echo "## 2. hand edit vendomat.yaml (v2), use vendomat"
setg v2; tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -4
echo "## 3. hand edit (v3), use devenv (bypass)"
cp .envrc.devenv .envrc; direnv allow .; setg v3
tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -v '^\s*$' | tail -6 | cut -c1-200
echo "## 4. same, direnv export json (what a shell hook sees)"
direnv export json 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -v '^\s*$' | tail -3 | cut -c1-200; echo "  [export rc=${PIPESTATUS[0]}]"
echo "## 5. lint fault in vendomat.yaml, use vendomat"
cp .envrc.vendomat .envrc; direnv allow .; setg v3; printf 'packages: &a\n  - "hello"\n' >> vendomat.yaml.bad; cp vendomat.yaml vendomat.yaml.good; printf 'packages:\n\t- "hello"\n' > vendomat.yaml
tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -v '^\s*$' | tail -6 | cut -c1-200
cp vendomat.yaml.good vendomat.yaml
echo "## 6. recovered, use vendomat"
tm direnv exec . sh -c 'echo "GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -3
echo "## 7. watch list"
direnv status 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | head -12

#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/dr/wsd
export XDG_CONFIG_HOME=$S5/dr/cfg XDG_DATA_HOME=$S5/dr/data XDG_CACHE_HOME=$S5/dr/state
export DEVENV_BIN=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv VENDOMAT_PREP=$S5/dr/prepwrap.sh
unset DIRENV_DIR DIRENV_FILE DIRENV_WATCHES DIRENV_DIFF DIRENV_ACTIVE IN_NIX_SHELL VIRTUAL_ENV NIX_PYTHONPATH PYTHONPATH
for v in $(compgen -e | grep -E '^DEVENV_' | grep -v '^DEVENV_BIN$'); do unset $v; done
# variant: use_vendomat that calls exit 1 on prep failure
sed -i 's/    return 1/    exit 1/' $S5/dr/cfg/direnv/direnvrc
cp .envrc.vendomat .envrc; direnv allow .
cp vendomat.yaml vendomat.yaml.good; printf 'packages:\n\t- "hello"\n' > vendomat.yaml
echo "## exec, prep fails, exit 1 in use_vendomat"
direnv exec . sh -c 'echo "RAN-COMMAND GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "direnv:|RAN-COMMAND"; echo "  [direnv exec rc=${PIPESTATUS[0]}]"
echo "## export json, prep fails (hook path)"
direnv export json >/dev/null 2>$S5/logs/direnv-export-err.txt; echo "  [export rc=$?]"; sed 's/\x1b\[[0-9;]*m//g' $S5/logs/direnv-export-err.txt | grep "direnv:" | head -3
cp vendomat.yaml.good vendomat.yaml
echo "## exec, stale + use devenv (bypass): exit code of devenv failure inside use_devenv"
cp .envrc.devenv .envrc; direnv allow .; sed -i 's/GREETING: ".*"/GREETING: "v9"/' vendomat.yaml
direnv exec . sh -c 'echo "RAN-COMMAND GREETING=$GREETING"' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "direnv:|RAN-COMMAND"; echo "  [direnv exec rc=${PIPESTATUS[0]}]"

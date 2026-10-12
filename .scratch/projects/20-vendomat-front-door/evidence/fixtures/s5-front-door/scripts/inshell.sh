#!/usr/bin/env bash
# S5 fixture, NON-PRODUCTION.
S5=$HOME/.local/state/vendomat/p20/2026-10-11/S5; cd $S5/exitws
cat > devenv.nix <<'NIX'
# S5 fixture, NON-PRODUCTION. The pinned build rides in the shell (VMOD-020 model).
{ pkgs, ... }: { packages = [ (pkgs.writeShellScriptBin "vendomat" ''echo "IN-SHELL pinned vendomat ran: $* launched_by=''${VENDOMAT_LAUNCHED_BY:-none}"'') ]; }
NIX
mkdir -p $S5/hostbin; printf '#!/usr/bin/env bash\necho "HOST LAUNCHER ran: $*"\n' > $S5/hostbin/vendomat; chmod +x $S5/hostbin/vendomat
F=/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv
echo "outside the shell:"; PATH=$S5/hostbin:$PATH vendomat build
echo "inside the shell:"
PATH=$S5/hostbin:$PATH $S5/cleanenv.sh $F shell -- bash -c 'command -v vendomat; vendomat build' 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "IN-SHELL|HOST|/vendomat"
git checkout -q devenv.nix

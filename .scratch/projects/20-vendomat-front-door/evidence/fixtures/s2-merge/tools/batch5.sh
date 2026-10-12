#!/usr/bin/env bash
# S2 batch (NON-PRODUCTION): error and mechanism cases on ws5 with the pinned fork devenv.
S=$HOME/.local/state/vendomat/p20/2026-10-11/S2
R=$S/tools/real5.sh
export ERRLINES=12
t(){ echo "=== $1  lines=$2  attr=$3"; $R "$1" "$2" "$3"; }
t '{"packages":["nosuchpkg"]}' '' vtest.probe.packages
t '{"packages":["python3Packages.nosuch"]}' '' vtest.probe.packages
t '{"packages":["lib"]}' '' vtest.probe.packages
t '{"packages":[5]}' '' vtest.probe.packages
t '{"packages":"jq"}' '' vtest.probe.packages
t '{"vtest":{"nope":1}}' '' vtest.probe.str
t '{"languages":{"pythn":{"enable":true}}}' '' vtest.probe.str
t '{"nope":{"x":1}}' '{"nope":9}' vtest.probe.str
t '{"vtest":{"str":null}}' '{"vtest":4}' vtest.probe.str
t '{"vtest":{"nul":null}}' '' vtest.probe.nul
t '{"vtest":{"fn":"x"}}' '{"vtest":5}' vtest.probe.fn
t '{"env":{"FOO":5}}' '{"env":6}' vtest.probe.env
t '{"languages":{"python":{"enable":"yes"}}}' '{"languages":8}' vtest.probe.pyenable
t '{"vtest":{"apps":{"a":{"pkg":"nosuch"}}}}' '' vtest.probe.apps
t '{"vtest":{"settings":{"a":{"b":[1,null,"s"]}}}}' '' vtest.probe.settings
t '{"vtest":{"path":"src/a","pathstr":"src/a"}}' '' vtest.probe.path
echo BATCH5-DONE

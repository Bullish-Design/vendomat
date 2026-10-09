# usage: nix eval --impure --raw --expr 'import /tmp/agent-h-scripts/lockpath.nix { lock = ./devenv.lock; node = "lib-a"; }'
{ lock, node }:
let
  locked = (builtins.fromJSON (builtins.readFile lock)).nodes.${node}.locked;
in
builtins.unsafeDiscardStringContext (derivation {
  name = "source";
  system = "builtin";
  builder = "builtin:fetchurl";
  outputHashMode = "recursive";
  outputHash = locked.narHash;
}).outPath

# The lock-pin check (VMOD-005). Reads devenv.lock as data, and returns the nodes that break the rule:
# every git node, direct or transitive, has `original.ref` under refs/tags/ and a 40-hex `locked.rev`.
{ lib }:
{
  unpinned = lockPath:
    if builtins.pathExists lockPath then
      let
        nodes = (builtins.fromJSON (builtins.readFile lockPath)).nodes;
        isGit = n: (n.original.type or "") == "git";
        tagged = n: lib.hasPrefix "refs/tags/" (n.original.ref or "");
        hexRev = n: builtins.match "[0-9a-f]{40}" (n.locked.rev or "") != null;
      in
      lib.filterAttrs (_: n: isGit n && !(tagged n && hexRev n)) nodes
    else { };

  describe = nodes: lib.concatStringsSep "\n" (lib.mapAttrsToList
    (k: n: "  input node ${k}: ${n.original.url or "?"} ref=${n.original.ref or "<none>"} rev=${n.locked.rev or "<none>"}") nodes);
}

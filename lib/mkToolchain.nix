# mkToolchain — compose selected first-party CLIs into ONE command closure (Face D).
#
# CONCEPT 03 §3.2: the join must FAIL EVALUATION on duplicate executable names rather than
# silently shadow one. Silent shadowing is the exact defect this project exists to remove —
# today PATH order decides between duplicate command names, and nobody is told.
#
# Each command package is independently content-addressed, so changing one tool rebuilds
# that tool and the join, not the other five.
#
#   mkToolchain { name = "core"; tools = { inherit repoman copyroom; }; }
{ pkgs, python }:

let
  inherit (pkgs) lib;
in

{ name
  # Attribute set of tool-name -> package built by the roster builder.
, tools
}:

let
  toolNames = builtins.attrNames tools;

  # command -> the tools that provide it.
  providersOf = command:
    lib.filter (t: builtins.elem command tools.${t}.passthru.commands) toolNames;

  allCommands = lib.unique (lib.concatMap (t: tools.${t}.passthru.commands) toolNames);
  collisions = lib.filter (c: builtins.length (providersOf c) > 1) allCommands;

  # One interpreter for the whole closure (CONCEPT 03 §8.3). Two Pythons in one roster
  # means two copies of every shared dependency and an ABI question at every boundary.
  pythons = lib.unique (map (t: tools.${t}.passthru.pythonVersion) toolNames);

  manifest = {
    roster = name;
    python = python.pythonVersion;
    tools = lib.mapAttrs (n: p: {
      inherit (p) version;
      store = "${p}";
      commands = p.passthru.commands;
    }) tools;
  };
in

if collisions != [ ] then
  throw ''
    mkToolchain: roster "${name}" has duplicate command name(s):
    ${lib.concatMapStringsSep "\n" (c: "  ${c} <- ${lib.concatStringsSep ", " (providersOf c)}") collisions}
    Exclude the command in the losing tool, or drop a tool
    from the roster. Shadowing by PATH order is what this closure replaces.
  ''
else if builtins.length pythons > 1 then
  throw ''
    mkToolchain: roster "${name}" mixes Python versions: ${lib.concatStringsSep ", " pythons}.
    The shared toolchain has one interpreter baseline (CONCEPT 03 §8.3).
  ''
else
  pkgs.symlinkJoin {
    name = "repoman-toolchain-${name}";
    paths = lib.attrValues tools;

    # Machine-readable provenance (CONCEPT 03 §5.6). `repoman-sync` reads this to report
    # where a command came from and to fail on a source mismatch, instead of guessing.
    postBuild = ''
      mkdir -p $out/share/vendomat
      cat > $out/share/vendomat/toolchain.json <<'EOF'
      ${builtins.toJSON manifest}
      EOF
    '';

    passthru = {
      inherit manifest;
      commands = allCommands;
    };

    meta.description = "Shared RepoMan command closure (roster: ${name})";
  }

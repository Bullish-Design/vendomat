#!/usr/bin/env bash
# NON-PRODUCTION spike fixture (project 20, spike S1).
# Nix-side checks of the syntax layer output. usage: nix_checks.sh CANON_DIR
set -u
CANON="$1"
REV=c8f90650c15282fa8656a041bfbbd2403997a9a7   # nixpkgs-src in vendomat devenv.lock
NIX="nix --extra-experimental-features nix-command --extra-experimental-features flakes"
echo "nix: $(nix --version)"
echo "== 1. every canonical file: fromJSON then toJSON must equal the file bytes (minus the final LF)"
$NIX eval --impure --json --expr "
let d = $CANON; names = builtins.attrNames (builtins.readDir d);
in builtins.listToAttrs (map (f: { name = f; value = builtins.toJSON (builtins.fromJSON (builtins.readFile (d + \"/\${f}\"))); }) names)
" > "$CANON/../nix-roundtrip.json"
echo "exit $?"
echo "== 2. integer boundaries through builtins.fromJSON"
for n in 9223372036854775807 -9223372036854775808 9223372036854775808 -9223372036854775809; do
  printf '%s -> ' "$n"; $NIX eval --impure --raw --expr "let v = builtins.fromJSON ''{\"a\": $n}''; in builtins.typeOf v.a + \" \" + builtins.toJSON v.a" 2>&1 | tail -1; echo
done
echo "== 3. interpolation text and non-ASCII stay literal"
$NIX eval --impure --json --expr 'let v = builtins.fromJSON (builtins.toJSON { a = "\${HOME}/x"; b = "é 😀"; }); in v' 2>&1 | tail -1
echo "== 4. lib.types.path and a relative string (syntax layer keeps strings)"
$NIX eval --impure --json --expr "
let pkgs = import (builtins.getFlake \"github:NixOS/nixpkgs/$REV\").outPath {}; t = pkgs.lib.types;
in {
  path_check_relative_string = t.path.check \"./scripts/x.sh\";
  path_check_absolute_string = t.path.check \"/abs/x.sh\";
  path_check_nix_path = t.path.check ./.;
  str_check_nix_path = t.str.check ./.;
  merged_oneOf_str_path_for_string = (pkgs.lib.evalModules { modules = [ { options.exec = pkgs.lib.mkOption { type = t.oneOf [ t.str t.path ]; }; config.exec = \"./scripts/x.sh\"; } ]; }).config.exec;
}" 2>&1 | tail -1
echo "== 5. package attribute strings resolve with lib.attrByPath on the pinned nixpkgs (tryEval, a removed alias throws)"
$NIX eval --impure --json --expr "
let pkgs = import (builtins.getFlake \"github:NixOS/nixpkgs/$REV\").outPath {}; l = pkgs.lib;
    r = s: let v = builtins.tryEval (let p = l.attrByPath (l.splitString \".\" s) null pkgs; in if p == null then \"MISSING\" else (p.name or \"no-name\")); in if v.success then v.value else \"THROWS\";
in l.genAttrs [ \"ripgrep\" \"python313Packages.requests\" \"nodePackages.typescript-language-server\" \"gnome-terminal\" \"pkgs.ripgrep\" \"no-such-package\" \"python313Packages.no-such\" \"python313Packages.\" \"\" ] r
" 2>&1 | tail -3

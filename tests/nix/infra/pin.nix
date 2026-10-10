# Shared pins for the Step 5 infrastructure VM tests (tests/nix/infra/*.nix).
#
# The pinned nixpkgs is the V6 release revision (`DEL-019`). The test needs `--impure` because
# `builtins.getFlake` of a github reference reads the fetcher cache, and because the wrapper passes
# the built Vendomat package as a store path in VENDOMAT_PACKAGE.
let
  nixpkgs = builtins.getFlake "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
  system = "x86_64-linux";
  pkgs = import nixpkgs { inherit system; };
  package = builtins.getEnv "VENDOMAT_PACKAGE";
in
{
  inherit nixpkgs pkgs system;
  lib = pkgs.lib;
  # `.#packages.x86_64-linux.vendomat` of this repository, built by the caller.
  vendomat = if package == "" then null else builtins.storePath package;
  # Public test keys from nixpkgs. They are not secrets and serve only SSH between the VMs.
  keys = import "${nixpkgs}/nixos/tests/ssh-keys.nix" pkgs;
}

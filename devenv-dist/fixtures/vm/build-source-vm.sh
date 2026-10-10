#!/usr/bin/env bash
# usage: build-source-vm.sh NIXPKGS_REV PUBKEY_FILE SSH_PORT
# Print the store path of the source VM runner script directory.
set -eu
rev=$1; export VM_PUBKEY_FILE=$2 VM_SSH_PORT=$3
here=$(cd "$(dirname "$0")" && pwd)
exec nix build --impure --no-link --print-out-paths --expr "
  let nixpkgs = builtins.getFlake \"github:NixOS/nixpkgs/$rev\";
  in (nixpkgs.lib.nixosSystem {
    system = \"x86_64-linux\";
    modules = [ $here/source-vm.nix ];
  }).config.system.build.vm"

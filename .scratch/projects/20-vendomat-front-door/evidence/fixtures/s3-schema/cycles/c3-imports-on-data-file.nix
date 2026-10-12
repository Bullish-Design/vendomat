# NON-PRODUCTION spike fixture (project 20, S3). Case C3: `imports` read the data file, not config.
{ lib, ... }:
let data = builtins.fromJSON (builtins.readFile ./.vendomat/config.json); in {
  imports = lib.optional ((data.demo or { }).enable or false) ./c-extra.nix;
}

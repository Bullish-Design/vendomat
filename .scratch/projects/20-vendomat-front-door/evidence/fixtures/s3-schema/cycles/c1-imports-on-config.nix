# NON-PRODUCTION spike fixture (project 20, S3). Case C1: `imports` depends on a config value.
{ lib, config, ... }: {
  imports = lib.optional config.demo.enable ./c-extra.nix;
}

# NON-PRODUCTION spike fixture (project 20, S3). Case C4: `imports` use the `pkgs` module argument.
{ lib, pkgs, ... }: {
  imports = lib.optional (pkgs ? hello) ./c-extra.nix;
}

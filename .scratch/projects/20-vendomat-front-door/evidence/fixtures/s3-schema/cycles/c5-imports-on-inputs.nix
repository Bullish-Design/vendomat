# NON-PRODUCTION spike fixture (project 20, S3). Case C5: `imports` use the `inputs` module argument.
{ lib, inputs, ... }: {
  imports = lib.optional (inputs ? demolib) ./c-extra.nix;
}

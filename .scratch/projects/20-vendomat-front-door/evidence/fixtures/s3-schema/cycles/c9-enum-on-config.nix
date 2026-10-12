# NON-PRODUCTION spike fixture (project 20, S3). Case C9: enum values come from a config value.
{ lib, config, ... }: {
  options.demo.pick = lib.mkOption {
    type = lib.types.enum (builtins.attrNames config.demo.users);
    default = "none";
    description = "One of the user names.";
  };
}

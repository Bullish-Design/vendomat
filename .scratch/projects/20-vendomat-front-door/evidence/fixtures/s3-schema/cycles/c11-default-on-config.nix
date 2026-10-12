# NON-PRODUCTION spike fixture (project 20, S3). Case C11: a default depends on a config value.
{ lib, config, ... }: {
  options.demo.derived = lib.mkOption {
    type = lib.types.str;
    default = "${config.demo.greeting}!";
    description = "Default follows demo.greeting.";
  };
}

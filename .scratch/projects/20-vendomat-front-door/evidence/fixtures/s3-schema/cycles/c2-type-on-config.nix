# NON-PRODUCTION spike fixture (project 20, S3). Case C2: an option TYPE depends on a config value.
{ lib, config, ... }: {
  options.demo.dyn = lib.mkOption {
    type = if config.demo.mode == "slow" then lib.types.int else lib.types.str;
    default = if config.demo.mode == "slow" then 0 else "x";
    description = "Type follows demo.mode.";
  };
}

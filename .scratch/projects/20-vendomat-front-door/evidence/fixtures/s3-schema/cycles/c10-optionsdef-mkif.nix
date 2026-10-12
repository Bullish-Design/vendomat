# NON-PRODUCTION spike fixture (project 20, S3). Case C10: `options` declared under mkIf on config.
{ lib, config, ... }: {
  options = lib.mkIf config.demo.enable {
    demo.cond = lib.mkOption { type = lib.types.str; default = "c"; description = "Conditional."; };
  };
}

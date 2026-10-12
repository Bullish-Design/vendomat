# NON-PRODUCTION spike fixture (project 20, S3). Module that a gated import loads.
{ lib, ... }: { options.demo.gated = lib.mkOption { type = lib.types.str; default = "g"; description = "Gated."; }; }

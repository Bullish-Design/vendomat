# S5 guard coverage fixture. NON-PRODUCTION.
# Each guard form fires only when its own marker file exists in the workspace root.
{ pkgs, lib, config, ... }:
let
  root = config.devenv.root;
  has = n: builtins.pathExists "${root}/stale-${n}";
in
{
  config = lib.mkIf (if has "b2" then throw "GUARD-B2 module-wide throw" else true) {
  # (a) assertions entry
  assertions = [{ assertion = !(has "a"); message = "GUARD-A assertion: stale digest"; }];

  # (b1) lazy throw in one option value
  env.S5_B1 = if has "b1" then throw "GUARD-B1 lazy throw in env value" else "ok";

  # (b2) module-wide throw: the mkIf condition above; any read of any option of this module fires it

  # (c) enterShell check
  enterShell = ''
    if [ -e "$DEVENV_ROOT/stale-c" ]; then m=FIRED; echo "GUARD-C-$m enterShell stale" >&2; exit 1; fi
  '';

  # (d) task before enterShell
  tasks."s5:guard-d" = {
    before = [ "devenv:enterShell" ];
    exec = ''if [ -e "$DEVENV_ROOT/stale-d" ]; then m=FIRED; echo "GUARD-D-$m task stale" >&2; exit 1; fi'';
  };

  # (e) check inside enterTest
  enterTest = ''
    if [ -e "$DEVENV_ROOT/stale-e" ]; then m=FIRED; echo "GUARD-E-$m enterTest stale" >&2; exit 1; fi
    echo ENTERTEST-RAN
  '';

  tasks."s5:hello".exec = "echo HELLO-TASK";
  processes.s5-sleep.exec = "echo PROC-STARTED; sleep 600";
  packages = [ pkgs.hello ];

  # machines: a cheap preview build, so no NixOS closure is built (pattern of devenv core test machines-plan)
  machines.server = {
    target.host = "reader@preview.invalid";
    hardware.facter = null;
    nixos = {
      boot.loader.grub.devices = [ "nodev" ];
      fileSystems."/" = { device = "/dev/disk/by-label/root"; fsType = "ext4"; };
      system.stateVersion = "25.11";
    };
    build.nixos = lib.mkForce (pkgs.runCommand "preview-system" { } "mkdir -p $out/bin; touch $out/bin/switch-to-configuration");
    build.deployer = lib.mkForce (pkgs.runCommand "preview-executor" { } "mkdir -p $out/bin; touch $out/bin/devenv-machine-deploy");
  };
  };
}

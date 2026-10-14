# B5 machines. The test replaces @VM_PORT@, @CLOSED_PORT@, and @SSH_KEY@ before it uses this file.
#
# `box` builds the VM. `running` is the machine that the VM stands for: the catalog marks it as
# adopted. `unmarked`, `fresh`, and `adopted-closed` point at a closed port, so an install that passes the refusal
# step stops at the SSH preflight.
{ ... }:
let
  machine = port: extra: {
    system = "x86_64-linux";
    hardware.facter = null;
    target.host = "root@127.0.0.1:${toString port}";
    target.sshOpts = [
      "-i" "@SSH_KEY@"
      "-F" "/dev/null"
      "-o" "IdentitiesOnly=yes"
      "-o" "UserKnownHostsFile=/dev/null"
      "-o" "StrictHostKeyChecking=no"
      "-o" "LogLevel=ERROR"
    ];
    nixos = { imports = [ ./box.nix ./key.nix ]; };
  } // extra;
in
{
  machines.box = {
    system = "x86_64-linux";
    hardware.facter = null;
    nixos = { imports = [ ./box.nix ./key.nix ]; };
  };
  machines.running = machine @VM_PORT@ { vendomat.mode = "adopt-existing"; };
  machines.unmarked = machine @CLOSED_PORT@ { };
  machines.fresh = machine @CLOSED_PORT@ { vendomat.mode = "fresh-install"; };
  # Control: the stock binary ignores the mark, so it contacts this closed port. The patched one refuses.
  machines.adopted-closed = machine @CLOSED_PORT@ { vendomat.mode = "adopt-existing"; };
}

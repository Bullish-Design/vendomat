# Fixture for the opt-in check `sharing-vm` (R39, VMT-127, VMT-128).
#
# It builds two NixOS machines with the pinned nixpkgs of Vendomat's flake.lock and the sharing
# module in `devenv/sharing.nix`. `alpha` serves. `beta` sets `serve = false` and takes `alpha`
# as a peer. The fixture reads peers from the files `.machines/NAME/cache-key.pub` in `workspace`.
# That is the rule the catalog applies: a machine whose key is not committed has no peer entry.
#
# Use:  nix-build default.nix --argstr workspace DIR --argstr sshPublicKey 'ssh-ed25519 ...' -A alpha.vm
#
# The machines are for virtual machines only. The SSH key is a throwaway key of one test run.
{ workspace, sshPublicKey }:
let
  lock = (builtins.fromJSON (builtins.readFile ../../../flake.lock)).nodes.nixpkgs.locked;
  src = builtins.fetchTree {
    type = "github";
    inherit (lock) owner repo rev narHash;
  };
  system = "x86_64-linux";
  pkgs = import src { inherit system; };
  lib = pkgs.lib;

  # The link between the two machines. The harness joins the two `eth1` cards (QEMU `dgram`).
  machines = {
    alpha = { lan = "192.168.77.1"; mac = "52:54:00:77:00:01"; serve = true; };
    beta = { lan = "192.168.77.2"; mac = "52:54:00:77:00:02"; serve = false; };
  };

  keyFile = name: workspace + "/.machines/${name}/cache-key.pub";
  peersFor =
    self:
    lib.concatMap (
      name:
      lib.optional (name != self && builtins.pathExists (keyFile name)) {
        url = "http://${machines.${name}.lan}:5000";
        publicKey = lib.removeSuffix "\n" (builtins.readFile (keyFile name));
      }
    ) (lib.attrNames machines);

  machine =
    name: extra:
    import (src + "/nixos") {
      inherit system;
      configuration = {
        imports = [
          ../../../devenv/sharing.nix
          extra
        ];
        networking.hostName = name;
        vendomat.sharing = {
          serve = machines.${name}.serve;
          peers = peersFor name;
        };

        # The test uses SSH to drive the machine. The key is a throwaway key.
        services.openssh.enable = true;
        services.openssh.settings.PermitRootLogin = "prohibit-password";
        users.users.root.openssh.authorizedKeys.keys = [ sshPublicKey ];
        nix.settings.experimental-features = [ "nix-command" ];
        # The VMs have no internet. Let cache.nixos.org fail at once, so the timings show the peers.
        networking.extraHosts = "127.0.0.1 cache.nixos.org";
        # The unique test derivations use this bash as builder.
        environment.systemPackages = [ pkgs.bash pkgs.curl ];

        # The second card joins the other machine. The first card (user mode) carries SSH.
        networking.useDHCP = lib.mkDefault true;
        systemd.network.enable = true;
        systemd.network.networks."30-lan" = {
          matchConfig.MACAddress = machines.${name}.mac;
          address = [ "${machines.${name}.lan}/24" ];
        };

        virtualisation.vmVariant.virtualisation = {
          memorySize = 1536;
          cores = 2;
          graphics = false;
          restrictNetwork = true;
          forwardPorts = [ ]; # the harness adds the SSH forward through QEMU_NET_OPTS
        };
        system.stateVersion = "26.11";
      };
    };

  alpha = machine "alpha" { };
  beta = machine "beta" { };

  # The attribute-set form of `peers` reaches the same settings as the list form.
  attrsForm =
    (import (src + "/nixos") {
      inherit system;
      configuration = {
        imports = [ ../../../devenv/sharing.nix ];
        vendomat.sharing.peers.one = {
          url = "http://one:5000";
          publicKey = "one:AAAA";
        };
      };
    }).config;
in
{
  inherit alpha beta;
  bash = pkgs.bash;
  # The host side tools of the harness: SSH client, key generator, and ext4 maker.
  tools = pkgs.buildEnv {
    name = "sharing-vm-tools";
    paths = [ pkgs.openssh pkgs.e2fsprogs ];
  };
  # Evaluation facts for tests that need no machine.
  facts = {
    attrsForm = {
      extraSubstituters = attrsForm.nix.settings.extra-substituters;
      extraKeys = attrsForm.nix.settings.extra-trusted-public-keys;
      fallback = attrsForm.nix.settings.fallback;
      connectTimeout = attrsForm.nix.settings.connect-timeout;
    };
    alpha = {
      serve = alpha.config.vendomat.sharing.serve;
      peers = alpha.config.vendomat.sharing.peers;
      extraSubstituters = alpha.config.nix.settings.extra-substituters or [ ];
      harmonia = alpha.config.services.harmonia.cache.enable;
    };
    beta = {
      serve = beta.config.vendomat.sharing.serve;
      peers = beta.config.vendomat.sharing.peers;
      extraSubstituters = beta.config.nix.settings.extra-substituters or [ ];
      harmonia = beta.config.services.harmonia.cache.enable;
      keyUnit = beta.config.systemd.services ? vendomat-cache-key;
    };
  };
}

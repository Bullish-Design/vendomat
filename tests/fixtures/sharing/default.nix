# Fixture for the opt-in check `sharing-vm` (R39, VMT-127, VMT-128).
#
# It builds NixOS machines with the pinned nixpkgs of Vendomat's flake.lock and the production
# sharing module in `devenv/sharing.nix`. `alpha` trusts only eth1; eth2 is untrusted. `beta` sets
# `serve = false`. `gamma` (the "unmarked" facts) has no trusted interface. The fixture reads peers from committed
# `.machines/NAME/cache-key.pub` files in `workspace`.
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
    alpha = { lan = "192.168.77.1"; untrusted = "192.168.78.1"; mac = "52:54:00:77:00:01"; macUntrusted = "52:54:00:78:00:01"; serve = true; };
    beta = { lan = "192.168.77.2"; untrusted = "192.168.78.2"; mac = "52:54:00:77:00:02"; macUntrusted = "52:54:00:78:00:02"; probeMac = "52:54:00:79:00:02"; serve = false; };
    gamma = { lan = "192.168.79.3"; untrusted = "192.168.78.3"; mac = "52:54:00:79:00:03"; macUntrusted = "52:54:00:78:00:03"; serve = true; };
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
    name: trusted: extra:
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
        } // lib.optionalAttrs trusted {
          trustedInterfaces = [ "eth1" ];
        };
        # The firewall keeps its defaults. The harness's SSH port comes from `services.openssh` below.
        # The fixture does not force the global list, so a 5000 that the production module adds to it
        # shows in `globalPorts`. The module opens 5000 on the marked interface only.

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
        systemd.network.networks."31-untrusted" = {
          matchConfig.MACAddress = machines.${name}.macUntrusted;
          address = [ "${machines.${name}.untrusted}/24" ];
        };
        systemd.network.networks."32-gamma-probe" = lib.mkIf (name == "beta") {
          matchConfig.MACAddress = machines.beta.probeMac;
          address = [ "192.168.79.2/24" ];
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

  alpha = machine "alpha" true { };
  beta = machine "beta" false { };
  gamma = machine "gamma" false { };

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
  # A serving machine with the firewall off. The fixture evaluates it and does not boot it.
  noFirewall =
    (import (src + "/nixos") {
      inherit system;
      configuration = {
        imports = [ ../../../devenv/sharing.nix ];
        networking.firewall.enable = false;
        vendomat.sharing.trustedInterfaces = [ "eth1" ];
      };
    }).config;
in
{
  inherit alpha beta gamma;
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
      globalPorts = alpha.config.networking.firewall.allowedTCPPorts;
      trustedPorts = alpha.config.networking.firewall.interfaces.eth1.allowedTCPPorts or [ ];
    };
    beta = {
      serve = beta.config.vendomat.sharing.serve;
      peers = beta.config.vendomat.sharing.peers;
      extraSubstituters = beta.config.nix.settings.extra-substituters or [ ];
      harmonia = beta.config.services.harmonia.cache.enable;
      keyUnit = beta.config.systemd.services ? vendomat-cache-key;
    };
    noFirewall.warnings = noFirewall.warnings;
    unmarked = {
      serve = gamma.config.vendomat.sharing.serve;
      globalPorts = gamma.config.networking.firewall.allowedTCPPorts;
      trustedPorts = gamma.config.networking.firewall.interfaces.eth1.allowedTCPPorts or [ ];
    };
  };
}

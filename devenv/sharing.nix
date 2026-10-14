# The Vendomat sharing module (R39, VMT-127, VMT-128).
#
# A plain NixOS module. It takes no `specialArgs`. The catalog turns it on for every machine.
#
# A machine that serves (`vendomat.sharing.serve`, on by default):
#   1. makes its own signing key at first boot, in the unit `vendomat-cache-key`;
#   2. publishes the public key in a world-readable file;
#   3. runs Harmonia with that key, on port 5000.
# The secret key never enters the Nix store. It lives under `/var/lib/vendomat/cache-key/`.
#
# A machine with peers (`vendomat.sharing.peers`) substitutes from them. It keeps cache.nixos.org.
# It sets `fallback = true` and a short connect timeout, so a peer that is off never blocks a build.
#
# Publication of the public key: the workspace commits the file `.machines/NAME/cache-key.pub`.
# The catalog reads that file and gives every other machine a peer entry. A machine whose key is
# not committed yet gets no peer entry. An install needs no key.
{ config, lib, pkgs, ... }:
let
  cfg = config.vendomat.sharing;
  t = lib.types;

  port = 5000;
  stateDir = "/var/lib/vendomat";
  keyDir = "${stateDir}/cache-key";
  secretKey = "${keyDir}/secret";
  publicKey = "${stateDir}/cache-key.pub";
  keyUnit = "vendomat-cache-key.service";

  peerType = t.submodule {
    options = {
      url = lib.mkOption {
        type = t.str;
        example = "http://alpha:5000";
        description = "The URL of the peer's Harmonia cache.";
      };
      publicKey = lib.mkOption {
        type = t.str;
        example = "alpha:AbCd...=";
        description = "The peer's cache public key, as NAME:BASE64.";
      };
    };
  };

  peers = if builtins.isAttrs cfg.peers then builtins.attrValues cfg.peers else cfg.peers;
  validKey = key: builtins.match "[^:[:space:]]+:[A-Za-z0-9+/]+=*" key != null;
in
{
  options.vendomat.sharing = {
    serve = lib.mkOption {
      type = t.bool;
      default = true;
      description = ''
        Serve this machine's Nix store through Harmonia, signed with a key that the machine makes
        at first boot. Set to false to run no Harmonia and make no key.
      '';
    };
    peers = lib.mkOption {
      type = t.either (t.listOf peerType) (t.attrsOf peerType);
      default = [ ];
      description = "The other machines of the workspace. This machine substitutes from them.";
    };
  };

  config = lib.mkMerge [
    {
      assertions = map (peer: {
        assertion = validKey peer.publicKey;
        message = "vendomat.sharing.peers: the public key of ${peer.url} must read NAME:BASE64, not \"${peer.publicKey}\".";
      }) peers;
    }

    # Client side: one entry per peer.
    (lib.mkIf (peers != [ ]) {
      nix.settings = {
        extra-substituters = map (peer: peer.url) peers;
        extra-trusted-public-keys = map (peer: peer.publicKey) peers;
        fallback = lib.mkDefault true;
        connect-timeout = lib.mkDefault 5;
      };
    })

    # Server side: the key unit, then Harmonia.
    (lib.mkIf cfg.serve {
      systemd.tmpfiles.rules = [
        "d ${stateDir} 0755 root root -"
        "d ${keyDir} 0700 root root -"
      ];

      systemd.services.vendomat-cache-key = {
        description = "Make the Vendomat cache signing key";
        # The unit runs early, before the sockets. A default dependency on basic.target would
        # make a cycle: the key unit after sockets.target, and harmonia.socket after the key unit.
        wantedBy = [ "sysinit.target" ];
        before = [ "sysinit.target" "sockets.target" "harmonia.socket" "harmonia.service" ];
        after = [ "systemd-tmpfiles-setup.service" ];
        unitConfig.DefaultDependencies = false;
        path = [ config.nix.package pkgs.coreutils ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
        };
        # Only `nix key` runs here. It needs no store. An earlier form (`nix-store
        # --generate-binary-cache-key`) failed once in six VM boots, while the boot registered the
        # store paths (register-nix-paths) at the same time. The cause is not proved.
        script = ''
          umask 077
          if [ ! -s ${secretKey} ]; then
            work=$(mktemp -d -p ${keyDir})
            nix --extra-experimental-features nix-command key generate-secret --key-name ${lib.escapeShellArg config.networking.hostName} > "$work/secret"
            mv "$work/secret" ${secretKey}
            rm -rf "$work"
          fi
          if [ ! -s ${publicKey} ]; then
            nix --extra-experimental-features nix-command key convert-secret-to-public < ${secretKey} > ${publicKey}.new
            chmod 0644 ${publicKey}.new
            mv ${publicKey}.new ${publicKey}
          fi
        '';
      };

      services.harmonia.cache = {
        enable = true;
        signKeyPaths = [ secretKey ];
      };
      systemd.sockets.harmonia = {
        requires = [ keyUnit ];
        after = [ keyUnit ];
      };
      systemd.services.harmonia = {
        requires = [ keyUnit ];
        after = [ keyUnit ];
      };

      networking.firewall.allowedTCPPorts = [ port ];
    })
  ];
}

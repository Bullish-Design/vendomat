# NON-PRODUCTION fixture for spike S7. A minimal "Basix core" role: key-only sshd, an admin
# PUBLIC key, and a receiver script for later secrets. It holds no secret, no SecretSpec,
# and no cache client setting.
{ config, lib, pkgs, ... }:
let
  cfg = config.basix;
  put = pkgs.writeShellApplication {
    name = "basix-secret-put";
    runtimeInputs = [ pkgs.coreutils ];
    text = ''
      # usage: basix-secret-put put NAME   (value on stdin)
      #        basix-secret-put rm NAME
      dir=/var/lib/basix/secrets
      stage=/var/lib/basix/.staging
      verb=''${1:-}
      name=''${2:-}
      case "$name" in
        ""|*/*|.*) echo "bad secret name" >&2; exit 2 ;;
      esac
      case "$verb" in
        put)
          umask 077
          tmp=$(mktemp "$stage/put.XXXXXX")
          trap 'rm -f "$tmp"' EXIT
          cat > "$tmp"
          if [ ! -s "$tmp" ]; then echo "empty value" >&2; exit 3; fi
          chown root:root "$tmp"
          chmod 0400 "$tmp"
          mv -f "$tmp" "$dir/$name"
          trap - EXIT
          ;;
        rm) rm -f "$dir/$name" ;;
        *) echo "usage: basix-secret-put put|rm NAME" >&2; exit 2 ;;
      esac
    '';
  };
in
{
  options.basix.adminKeys = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    default = [ ];
    description = "Public keys that may log in as root. Public keys are not secret.";
  };
  config = {
    services.openssh = {
      enable = true;
      settings = {
        PasswordAuthentication = false;
        KbdInteractiveAuthentication = false;
        PermitRootLogin = "prohibit-password";
      };
    };
    users.users.root.openssh.authorizedKeys.keys = cfg.adminKeys;
    systemd.tmpfiles.rules = [
      "d /var/lib/basix 0700 root root -"
      "d /var/lib/basix/secrets 0700 root root -"
      "d /var/lib/basix/.staging 0700 root root -"
    ];
    environment.systemPackages = [ put ];
  };
}

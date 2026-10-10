# NixOS module for the test cache host (V6 Step 5 fixtures).
#
# It runs the real `atticd` from nixpkgs with a sqlite database and a signing secret that the VM
# makes at first boot. It also serves a small HTTP binary cache on port 8081 that stands in for an
# upstream cache. The secret never enters the Nix store.
{ pkgs, lib, ... }:
{
  virtualisation = {
    diskSize = 8192;
    memorySize = 2048;
    writableStoreUseTmpfs = false;
  };
  networking.firewall.allowedTCPPorts = [ 8080 8081 ];
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  systemd.services.atticd-env = {
    wantedBy = [ "multi-user.target" ];
    requiredBy = [ "atticd.service" ];
    before = [ "atticd.service" ];
    path = [ pkgs.openssl pkgs.coreutils ];
    serviceConfig = { Type = "oneshot"; RemainAfterExit = true; };
    script = ''
      umask 077
      mkdir -p /var/lib/vendomat-test
      if [ ! -e /var/lib/vendomat-test/atticd.env ]; then
        echo "ATTIC_SERVER_TOKEN_RS256_SECRET_BASE64=$(openssl genrsa -traditional 4096 | base64 -w0)" \
          > /var/lib/vendomat-test/atticd.env
      fi
    '';
  };
  services.atticd = {
    enable = true;
    environmentFile = "/var/lib/vendomat-test/atticd.env";
    settings = {
      listen = "[::]:8080";
      api-endpoint = "http://server:8080/";
    };
  };

  systemd.tmpfiles.rules = [ "d /srv/upstream-cache 0755 root root -" ];
  systemd.services.upstream-cache = {
    wantedBy = [ "multi-user.target" ];
    preStart = ''
      printf 'StoreDir: /nix/store\nWantMassQuery: 1\nPriority: 50\n' > /srv/upstream-cache/nix-cache-info
    '';
    serviceConfig.ExecStart = "${pkgs.python3}/bin/python3 -m http.server 8081 --directory /srv/upstream-cache";
  };

  environment.systemPackages = [ pkgs.attic-client pkgs.curl ];
}

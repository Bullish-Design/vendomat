# NON-PRODUCTION fixture for spike S7. A dependent service that needs a key file.
# The service is skipped (not failed) while the key is absent or empty.
# A path unit restarts it when the key appears, changes, or goes away.
{ pkgs, ... }:
let
  keyPath = "/var/lib/basix/secrets/dep-key";
  app = pkgs.writeShellScript "basix-dep-app" ''
    set -eu
    k="$CREDENTIALS_DIRECTORY/dep-key"
    ${pkgs.coreutils}/bin/sha256sum < "$k" | ${pkgs.coreutils}/bin/cut -d' ' -f1 > /run/basix-dep/key-sha256
    echo started > /run/basix-dep/state
    exec ${pkgs.coreutils}/bin/sleep infinity
  '';
in
{
  systemd.services.basix-dep = {
    description = "S7 dependent service (needs dep-key)";
    wantedBy = [ "multi-user.target" ];
    unitConfig.ConditionFileNotEmpty = keyPath;
    serviceConfig = {
      LoadCredential = "dep-key:${keyPath}";
      RuntimeDirectory = "basix-dep";
      ExecStart = app;
    };
  };
  systemd.paths.basix-dep-key = {
    wantedBy = [ "multi-user.target" ];
    pathConfig = {
      PathChanged = keyPath;
      Unit = "basix-dep-apply.service";
    };
  };
  systemd.services.basix-dep-apply = {
    description = "S7 apply a changed dep-key";
    serviceConfig.Type = "oneshot";
    script = "systemctl restart basix-dep.service";
    path = [ pkgs.systemd ];
  };
  # Negative control: no condition. It fails without the key.
  systemd.services.basix-dep-unguarded = {
    description = "S7 control: unguarded service";
    serviceConfig = {
      LoadCredential = "dep-key:${keyPath}";
      ExecStart = "${pkgs.coreutils}/bin/true";
    };
  };
}

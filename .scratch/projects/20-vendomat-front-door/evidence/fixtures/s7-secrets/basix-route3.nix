# NON-PRODUCTION fixture for spike S7. Route 3: host-side resolution with SecretSpec.
# The dotenv provider file is the one bootstrap credential. It arrives by route 1.
{ pkgs, ... }:
let
  provider = "/var/lib/basix/secrets/provider.env";
  app3 = pkgs.writeShellScript "basix-dep3-app" ''
    set -eu
    printf %s "$DEP3_KEY" | ${pkgs.coreutils}/bin/sha256sum | ${pkgs.coreutils}/bin/cut -d' ' -f1 > /run/basix-dep3/key-sha256
    exec ${pkgs.coreutils}/bin/sleep infinity
  '';
  ss = "${pkgs.secretspec}/bin/secretspec";
  common = "-f /etc/basix/secretspec.toml --provider dotenv://${provider} --profile default";
in
{
  environment.systemPackages = [ pkgs.secretspec ];
  environment.etc."basix/secretspec.toml".text = ''
    [project]
    name = "basix-s7"
    revision = "1.0"
    require_reason = false

    [profiles.default]
    DEP3_KEY = { description = "S7 test-only key for the route 3 service" }
  '';
  systemd.services.basix-dep3 = {
    description = "S7 route 3 service (SecretSpec at start)";
    wantedBy = [ "multi-user.target" ];
    unitConfig.ConditionFileNotEmpty = provider;
    serviceConfig = {
      RuntimeDirectory = "basix-dep3";
      # Skip, do not fail, while the provider cannot resolve the secret.
      ExecCondition = "${ss} check ${common}";
      ExecStart = "${ss} run ${common} -- ${app3}";
    };
  };
  systemd.paths.basix-dep3 = {
    wantedBy = [ "multi-user.target" ];
    pathConfig = {
      PathChanged = provider;
      Unit = "basix-dep3-apply.service";
    };
  };
  systemd.services.basix-dep3-apply = {
    serviceConfig.Type = "oneshot";
    script = "systemctl restart basix-dep3.service";
    path = [ pkgs.systemd ];
  };
}

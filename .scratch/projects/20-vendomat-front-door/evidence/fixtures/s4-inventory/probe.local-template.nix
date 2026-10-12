# NON-PRODUCTION spike fixture (project 20, spike S4). Read-only probe of the evaluated machines.
# `devenv eval env.S4_PROBE` prints what the data inventory produced. It builds nothing.
{ config, lib, ... }:
let
  probe = n:
    let
      m = config.machines.${n};
      c = m._nixosEval.config;
    in
    {
      mode = m.vendomat.mode;
      preflightProgram = if m.vendomat.preflight.program == null then null else m.vendomat.preflight.program.drvPath;
      targetHost = m.target.host;
      facter = m.hardware.facter;
      hostName = c.networking.hostName;
      stateVersion = c.system.stateVersion;
      rootDevice = c.fileSystems."/".device;
      bootDevice = c.fileSystems."/boot".device;
      swap = map (s: s.device) c.swapDevices;
      systemdBoot = c.boot.loader.systemd-boot.enable;
      canTouchEfi = c.boot.loader.efi.canTouchEfiVariables;
      initrdModules = c.boot.initrd.availableKernelModules;
      redistFirmware = c.hardware.enableRedistributableFirmware;
      sshRootLogin = c.services.openssh.settings.PermitRootLogin;
      ownerKeys = c.users.users.owner.openssh.authorizedKeys.keys;
      diskoDisks = lib.mapAttrs (_: d: d.device) (c.disko.devices.disk or { });
      facterReportPath = toString (c.facter.reportPath or "<none>");
      installCheck = m.installCheck.diskoDevices;
      failedAssertions = map (a: a.message) (lib.filter (a: !a.assertion) c.assertions);
    };
in
{
  env.S4_PROBE = builtins.toJSON (lib.genAttrs (builtins.attrNames config.machines) probe);
}

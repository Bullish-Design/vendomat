# A NixOS VM test of the described-library faces (Step 3: enabled packages, units, start-script PATH).
#
# It imports the builder from this repository with one in-memory library, enables the NixOS face
# with its service, and enables the Home Manager face for a user. The test script then checks that
# both units run, that the package is on the system PATH, and that the start script put the package
# on the unit's PATH (a NixOS unit's default PATH has no systemPackages).
#
# Run (needs /dev/kvm and the `nixos-test` system feature):
#   nix build --impure --no-link --print-out-paths --file tests/nix/faces-vm.nix
let
  nixpkgs = builtins.getFlake "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";
  homeManager = builtins.getFlake "github:nix-community/home-manager/6b88c12cc6d234de4888f5d21076fb11199d0844";
  system = "x86_64-linux";
  pkgs = import nixpkgs { inherit system; };
  lib = pkgs.lib;

  # A library, in the shape of a flake's outputs: no Vendomat input, only a description.
  knappy = {
    outPath = "/nonexistent/knappy";
    packages.${system}.default = pkgs.writeShellScriptBin "knappy" ''
      case "$1" in
        serve) echo "knappy serving on $3" ; exec ${pkgs.coreutils}/bin/sleep 100000 ;;
        *) echo "knappy $*" ;;
      esac
    '';
    vendomat = {
      name = "knappy";
      packages = p: [ knappy.packages.${p.stdenv.hostPlatform.system}.default ];
      options = l: { port = l.mkOption { type = l.types.port; default = 8080; }; };
      service = { pkgs, cfg }: { exec = "knappy serve --port ${toString cfg.port}"; };
    };
  };

  builder = import ../../nix/devenv-module/builder.nix {
    inherit lib;
    self = { outPath = "/nonexistent/vendomat"; };
    inputs = { inherit knappy; };
  };
in
pkgs.testers.runNixOSTest {
  name = "vendomat-faces";
  nodes.machine = { ... }: {
    imports = [ homeManager.nixosModules.home-manager ] ++ builder.nixosImports;
    users.users.alice = { isNormalUser = true; };
    home-manager.users.alice = { ... }: {
      home.stateVersion = "24.11";
      vendomat.libs.knappy = { enable = true; port = 7071; service.enable = true; };
    };
    vendomat.libs.knappy = { enable = true; port = 7070; service.enable = true; };
    system.stateVersion = "24.11";
  };
  testScript = ''
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_unit("knappy.service")
    # The package is on the system PATH.
    machine.succeed("knappy hello | grep -q 'knappy hello'")
    # The unit runs the start script, and the start script found `knappy` without systemPackages on the unit PATH.
    machine.succeed("systemctl cat knappy.service | grep -q 'knappy-start'")
    machine.succeed("systemctl show -p ExecMainPID --value knappy.service | grep -qv '^0$'")
    machine.succeed("journalctl -u knappy.service --no-pager | grep -q 'knappy serving on 7070'")
    # The user unit runs under alice.
    machine.succeed("loginctl enable-linger alice")
    machine.wait_until_succeeds("systemctl --user --machine=alice@.host is-active knappy.service", timeout=60)
    # The user unit's start script ran `knappy serve` as alice, and the root unit's ran it as root.
    machine.succeed("pgrep -u alice -f 'sleep 100000'")
    machine.succeed("pgrep -u root -f 'sleep 100000'")
  '';
}

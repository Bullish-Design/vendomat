# Host tools and input sources for the opt-in check `machines-vm`, from the pinned nixpkgs of
# Vendomat's flake.lock.
#
# Use:  nix-build tools.nix -A tools -o OUT   (OUT/bin: qemu-system-x86_64, qemu-img, ssh, ssh-keygen, git, nc)
#       nix-build tools.nix -A ovmf -o OUT2   (OUT2-fd/FV/OVMF_CODE.fd, OVMF_VARS.fd)
#       nix-instantiate --eval --strict --json tools.nix -A sources   (store paths of the input sources)
let
  lock = (builtins.fromJSON (builtins.readFile ../../../flake.lock)).nodes.nixpkgs.locked;
  nixpkgs = builtins.fetchTree {
    type = "github";
    inherit (lock) owner repo rev narHash;
  };
  pkgs = import nixpkgs { system = "x86_64-linux"; };
  # The other two pins are the W2 pins (disko and nixos-facter-modules).
  disko = builtins.fetchTree {
    type = "github";
    owner = "nix-community";
    repo = "disko";
    rev = "de5708739256238fb912c62f03988815db89ec9a";
    narHash = "sha256-CNzzBsRhq7gg4BMBuTDObiWDH/rFYHEuDRVOwCcwXw4=";
  };
  facter = builtins.fetchTree {
    type = "github";
    owner = "nix-community";
    repo = "nixos-facter-modules";
    rev = "139dcef4dfc97009629c445806f197883351ab4a";
    narHash = "sha256-oW0/lC0oRG5H5LaK6Rmh9L1wmkn9TbenM4bXwnIEDKA=";
  };
  vendomat = pkgs.python313.pkgs.buildPythonApplication {
    pname = "vendomat";
    version = "fixture";
    pyproject = true;
    src = pkgs.lib.fileset.toSource {
      root = ../../..;
      fileset = pkgs.lib.fileset.unions [
        ../../../pyproject.toml
        ../../../README.md
        ../../../src
      ];
    };
    build-system = [ pkgs.python313.pkgs.hatchling ];
    dependencies = [ pkgs.python313.pkgs.typer ];
    doCheck = false;
  };
in
{
  ovmf = pkgs.OVMF.fd;
  tools = pkgs.buildEnv {
    name = "machines-vm-tools";
    paths = [ pkgs.qemu_kvm pkgs.openssh pkgs.git pkgs.devenv pkgs.netcat-openbsd ];
  };
  # The Vendomat of this checkout, built from the working tree (not only from Git-tracked files), and the
  # host launcher that runs it. The launcher is built as `mkLauncher` in flake.nix builds it.
  vendomat = vendomat;
  launcher =
    pkgs.runCommand "vendomat-launcher-fixture" { nativeBuildInputs = [ pkgs.makeWrapper ]; } ''
      install -Dm755 ${../../../launcher/vendomat} $out/bin/vendomat
      substituteInPlace $out/bin/vendomat \
        --replace-fail '@HOST_RELEASE@' '${vendomat}/bin/vendomat' \
        --replace-fail '@DEVENV_FORK@' '${pkgs.devenv}/bin/devenv'
      wrapProgram $out/bin/vendomat --suffix PATH : ${pkgs.lib.makeBinPath [ pkgs.jq pkgs.coreutils pkgs.findutils ]}
    '';

  # The VM has no network, so the workspace pins these sources by their store paths.
  sources = {
    nixpkgs = { path = nixpkgs.outPath; rev = nixpkgs.rev; lastModified = nixpkgs.lastModified; };
    disko = { path = disko.outPath; rev = disko.rev; lastModified = disko.lastModified; };
    nixos-facter-modules = { path = facter.outPath; rev = facter.rev; lastModified = facter.lastModified; };
  };
}

# NON-PRODUCTION experiment E (project 20): self-generated Harmonia signing key (H1).
# One node. Checks: key made on first start, Harmonia after it, Sig line, key name,
# unsigned-substituter behaviour (H3), derived client settings.
{
  nixpkgsRev ? "e7439b6b14ad3cc35d05608ebca9bce01a25f5f8",
  nixpkgsHash ? "sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=",
}:
let
  src = builtins.fetchTree {
    type = "github";
    owner = "NixOS";
    repo = "nixpkgs";
    rev = nixpkgsRev;
    narHash = nixpkgsHash;
  };
  pkgs = import src { system = "x86_64-linux"; };
  lib = pkgs.lib;

  keyDir = "/var/lib/vendomat-cache";
  keyPath = "${keyDir}/harmonia.secret";
  pubPath = "${keyDir}/harmonia.pub";

  mkExpr =
    name: payload:
    pkgs.writeText "${name}.nix" ''
      let bash = builtins.storePath "${pkgs.bash}"; in
      derivation {
        name = "e-${name}";
        system = builtins.currentSystem;
        builder = "''${bash}/bin/bash";
        args = [ "-c" "echo ${payload} > $out" ];
      }
    '';
  exprA = mkExpr "a" "PAYLOAD-A";
  exprB = mkExpr "b" "PAYLOAD-B";
in
pkgs.testers.runNixOSTest {
  name = "e-cache-key-selfgen";
  nodes.cachehost =
    { config, ... }:
    {
      nix.enable = true;
      nix.settings.experimental-features = [ "nix-command" ];
      nix.settings.substituters = lib.mkForce [ ];
      networking.firewall.allowedTCPPorts = [ 5000 ];

      # H1: a oneshot makes the key when the file is absent. It writes a temp file, then renames.
      systemd.services.harmonia-keygen = {
        description = "Make the Harmonia signing key on first start";
        before = [ "harmonia.service" ];
        path = [ config.nix.package pkgs.coreutils ];
        serviceConfig = {
          Type = "oneshot";
          RemainAfterExit = true;
          StateDirectory = "vendomat-cache";
          StateDirectoryMode = "0700";
          UMask = "0077";
        };
        script = ''
          if [ ! -s ${keyPath} ]; then
            nix key generate-secret --key-name ${config.networking.hostName}-cache-1 > ${keyPath}.tmp
            nix key convert-secret-to-public < ${keyPath}.tmp > ${pubPath}.tmp
            chmod 0644 ${pubPath}.tmp
            mv ${pubPath}.tmp ${pubPath}
            mv ${keyPath}.tmp ${keyPath}
          fi
        '';
      };
      # Harmonia stays socket-activated. The service needs the key unit.
      systemd.services.harmonia = {
        requires = [ "harmonia-keygen.service" ];
        after = [ "harmonia-keygen.service" ];
      };
      services.harmonia.cache = {
        enable = true;
        signKeyPaths = [ keyPath ];
      };
    };

  testScript = ''
    def sh(cmd, check=True):
        rc, out = machine.execute(cmd)
        print(f"$ {cmd}\n(rc={rc})\n{out}")
        if check:
            assert rc == 0, f"failed: {cmd}"
        return out

    machine = cachehost
    machine.start()
    machine.wait_for_unit("multi-user.target")

    print("=== T1 boot, no request yet ===")
    sh("systemctl is-system-running")
    sh("systemctl --failed --no-legend --plain")
    sh("test ! -e ${keyPath} && echo KEY-ABSENT-BEFORE-FIRST-REQUEST")
    sh("ss -ltn | grep ':5000'")

    print("=== T2 first request ===")
    info = sh("curl -sS -m 15 http://localhost:5000/nix-cache-info")
    assert "StoreDir: /nix/store" in info
    sh("ls -l ${keyPath} ${pubPath}")
    mode = sh("stat -c '%a %U:%G' ${keyPath}").strip()
    assert mode == "600 root:root", mode
    sh("systemctl show harmonia-keygen.service harmonia.service -p Id -p ActiveState -p SubState -p Result -p ExecMainStartTimestamp --no-pager")
    sh("systemctl is-system-running")
    sh("systemctl --failed --no-legend --plain")
    pub = sh("cat ${pubPath}").strip()
    print("PUBLIC KEY LINE:", pub)
    assert pub.startswith("cachehost-cache-1:")
    h1 = sh("sha256sum ${keyPath}").strip()

    print("=== T3 narinfo carries Sig ===")
    drv = sh("nix-instantiate ${exprA} 2>/dev/null").strip()
    out = sh(f"nix-store -r {drv} 2>/dev/null").strip()
    base = out.split("/")[-1].split("-")[0]
    narinfo = sh(f"curl -sS -m 15 http://localhost:5000/{base}.narinfo")
    sigs = [l for l in narinfo.splitlines() if l.startswith("Sig:")]
    print("SIG LINES:", sigs)
    assert len(sigs) == 1 and sigs[0].startswith("Sig: cachehost-cache-1:")
    # local path is unsigned (ultimate only)
    sh(f"nix path-info --sigs {out}")

    print("=== T4 client verification with the public key (chroot store) ===")
    sh(f"nix-store --store /tmp/c1 -r {out} --option substituters http://localhost:5000 --option trusted-public-keys '{pub}' --option connect-timeout 3")
    sh(f"nix path-info --store /tmp/c1 --sigs {out}")
    sh(f"nix store verify --store /tmp/c1 --sigs-needed 1 --trusted-public-keys '{pub}' {out}")
    # wrong trusted key: refuse
    rc, o = machine.execute(
        f"nix-store --store /tmp/c2 -r {out} --option substituters http://localhost:5000 "
        f"--option trusted-public-keys 'other-1:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' 2>&1"
    )
    print(f"$ wrong-key substitution\n(rc={rc})\n{o}")
    assert rc != 0 and "not signed by any of the keys" in o

    print("=== T5 key survives service restart; not regenerated ===")
    sh("systemctl restart harmonia-keygen.service harmonia.service")
    h2 = sh("sha256sum ${keyPath}").strip()
    assert h1 == h2, "key changed"
    print("RESULT key unchanged after restart")
    sh("curl -sS -m 15 http://localhost:5000/nix-cache-info")
    sh("systemctl is-system-running")

    print("=== T6 H3: unsigned path from a substituter ===")
    drvb = sh("nix-instantiate ${exprB} 2>/dev/null").strip()
    outb = sh(f"nix-store -r {drvb} 2>/dev/null").strip()
    sh("rm -rf /tmp/ucache")
    sh(f"nix copy --to file:///tmp/ucache {outb}")
    rc, o = machine.execute(
        f"nix-store --store /tmp/c3 -r {outb} --option substituters file:///tmp/ucache "
        f"--option trusted-public-keys '{pub}' 2>&1"
    )
    print(f"$ unsigned substitute, require-sigs default\n(rc={rc})\n{o}")
    assert rc != 0
    rc, o = machine.execute(
        f"nix-store --store /tmp/c4 -r {outb} --option substituters file:///tmp/ucache "
        f"--option require-sigs false 2>&1"
    )
    print(f"$ unsigned substitute, require-sigs false\n(rc={rc})\n{o}")
    assert rc == 0
    # Same unsigned path through Harmonia: Harmonia signs it on the fly.
    baseb = outb.split("/")[-1].split("-")[0]
    nb = sh(f"curl -sS -m 15 http://localhost:5000/{baseb}.narinfo")
    assert "Sig: cachehost-cache-1:" in nb
    print("RESULT all checks passed")
  '';
}

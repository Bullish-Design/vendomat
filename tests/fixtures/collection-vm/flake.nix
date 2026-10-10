{
  # Disposable proof of Step 6.3: the module settings in nix-meta's machines/server.nix, a release
  # push over SSH, per-repository export, and a Nix fetch from a second machine. The pin is the V6
  # release nixpkgs (it was the revision that `server` built with on 2026-10-08; V6 Step 5 moved it).
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8";

  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      keys = import "${nixpkgs}/nixos/tests/ssh-keys.nix" pkgs;
      # The rule for the collection (STORE-011): only new release tags enter, and a tag never moves.
      hook = pkgs.writeScript "pre-receive" ''
        #!${pkgs.runtimeShell}
        zero=0000000000000000000000000000000000000000
        while read old new ref; do
          case "$ref" in
            refs/tags/*)
              [ "$old" = "$zero" ] || { echo "collection: $ref exists; releases are immutable" >&2; exit 1; } ;;
            *)
              echo "collection: only release tags are accepted, not $ref" >&2; exit 1 ;;
          esac
        done
      '';
    in {
      checks.${system}.collection = pkgs.testers.runNixOSTest {
        name = "collection";
        nodes = {
          server = { ... }: {
            users.users.andrew = {
              isNormalUser = true;
              openssh.authorizedKeys.keys = [ keys.snakeOilPublicKey ];
            };
            services.openssh.enable = true;
            systemd.tmpfiles.rules = [ "d /home/andrew/vendor 0755 andrew users -" ];

            # The settings proposed for nix-meta's machines/server.nix.
            services.gitDaemon = {
              enable = true;
              basePath = "/home/andrew/vendor";
              repositories = [ "/home/andrew/vendor" ];
              user = "andrew";
              group = "users";
            };
            networking.firewall.interfaces.eth1.allowedTCPPorts = [ 22 9418 ];

            environment.systemPackages = [ pkgs.git ];
            systemd.services.git-daemon.serviceConfig.CPUAccounting = true;
          };
          client = { ... }: {
            environment.systemPackages = [ pkgs.git pkgs.openssh ];
            nix.settings.experimental-features = [ "nix-command" "flakes" ];
          };
        };

        testScript = ''
          start_all()
          server.wait_for_unit("git-daemon.service")
          server.wait_for_unit("sshd.service")
          server.wait_for_open_port(9418)

          # The collection: repositories are created once on the server.
          server.succeed("su - andrew -c 'git init -q ~/vendor/lib-a && git init -q ~/vendor/unmarked'")
          server.succeed("install -o andrew -g users -m 755 ${hook} /home/andrew/vendor/lib-a/.git/hooks/pre-receive")

          # The authoring repository on the client, with a release tag.
          client.succeed(
              "mkdir -p /root/lib-a && cd /root/lib-a && git init -q -b main"
              " && echo '{ outputs = _: { marker = \"lib-a-v1\"; }; }' > flake.nix && git add flake.nix"
              " && git -c user.name=t -c user.email=t@t commit -qm release && git tag v1.0.0"
          )
          client.succeed("install -m 600 ${keys.snakeOilPrivateKey} /root/key")
          ssh = "GIT_SSH_COMMAND='ssh -i /root/key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes'"
          dest = "ssh://andrew@server/home/andrew/vendor/lib-a"

          # STORE-011: a release tag is accepted over SSH. A branch is refused. A tag never moves.
          client.succeed(f"cd /root/lib-a && {ssh} git push {dest} v1.0.0")
          client.fail(f"cd /root/lib-a && {ssh} git push {dest} main")
          client.succeed("cd /root/lib-a && git -c user.name=t -c user.email=t@t commit -q --allow-empty -m next && git tag -f v1.0.0")
          client.fail(f"cd /root/lib-a && {ssh} git push -f {dest} v1.0.0")
          client.succeed("cd /root/lib-a && git tag v1.0.1")
          client.succeed(f"cd /root/lib-a && {ssh} git push {dest} v1.0.1")
          tags = server.succeed("su - andrew -c 'git -C ~/vendor/lib-a tag --list'")
          assert tags.split() == ["v1.0.0", "v1.0.1"], tags
          heads = server.succeed("su - andrew -c 'git -C ~/vendor/lib-a for-each-ref refs/heads | wc -l'")
          assert heads.strip() == "0", heads

          # Export is per repository: nothing is served until the marker file exists.
          client.fail("git ls-remote git://server/lib-a")
          server.succeed("su - andrew -c 'touch ~/vendor/lib-a/.git/git-daemon-export-ok'")
          client.succeed("git ls-remote git://server/lib-a | grep refs/tags/v1.0.0")
          client.fail("git ls-remote git://server/unmarked")

          # git:// is read only.
          client.fail("cd /root/lib-a && git push git://server/lib-a main")

          # STORE-008: Nix on the second machine fetches the tagged release.
          client.succeed(
              "mkdir -p /root/consumer && cd /root/consumer"
              " && echo '{ inputs.lib.url = \"git://server/lib-a?ref=refs/tags/v1.0.0\";"
              " outputs = { lib, ... }: { marker = lib.marker; }; }' > flake.nix"
              " && nix flake lock"
          )
          out = client.succeed("cd /root/consumer && nix eval --raw .#marker")
          assert out == "lib-a-v1", out
          lock = client.succeed("cat /root/consumer/flake.lock")
          assert "git://server/lib-a" in lock and "refs/tags/v1.0.0" in lock, lock

          # Idle cost of the daemon.
          read = "systemctl show -p CPUUsageNSec --value git-daemon.service"
          t0 = int(server.succeed(read).strip())
          server.sleep(15)
          t1 = int(server.succeed(read).strip())
          print(f"RESULT idle cpu ns in 15 s: {t1 - t0}")
          assert t1 - t0 < 50_000_000, t1 - t0
        '';
      };
    };
}

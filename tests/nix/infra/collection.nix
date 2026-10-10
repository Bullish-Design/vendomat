# A two-VM proof of the source collection (V6 Step 5, STORE-008 to STORE-023).
#
# `server` holds the collection under /home/andrew/vendor and serves it with `git daemon`, with the
# settings of nix-meta's machines/server.nix. `framework` pushes release tags over SSH and fetches
# over git://. The repositories come from `collection-add` (a copy of the nix-meta script) and the
# `hooks/collection-post-receive` of this repository.
#
# Run (needs /dev/kvm and the `nixos-test` system feature):
#   VENDOMAT_PACKAGE=$(nix build .#packages.x86_64-linux.vendomat --no-link --print-out-paths) \
#     nix build --impure --no-link -L --file tests/nix/infra/collection.nix
let
  p = import ./pin.nix;
  inherit (p) pkgs keys vendomat;
  collectionAdd = pkgs.writeShellScriptBin "collection-add" (builtins.readFile ./collection-add);
  repoHook = ../../../hooks/collection-post-receive;
in
pkgs.testers.runNixOSTest {
  name = "vendomat-collection";
  nodes = {
    server = { ... }: {
      users.users.andrew = {
        isNormalUser = true;
        openssh.authorizedKeys.keys = [ keys.snakeOilPublicKey ];
      };
      services.openssh.enable = true;
      systemd.tmpfiles.rules = [
        "d /home/andrew/vendor 0755 andrew users -"
        "d /srv/upstream 0755 andrew users -"
      ];

      # The settings of nix-meta machines/server.nix (STORE-008, STORE-015).
      services.gitDaemon = {
        enable = true;
        basePath = "/home/andrew/vendor";
        repositories = [ "/home/andrew/vendor" ];
        user = "andrew";
        group = "users";
      };
      # The real host opens 9418 on tailscale0 only. The inner test interface is the stand-in.
      networking.firewall.interfaces.eth1.allowedTCPPorts = [ 22 9418 ];

      environment.systemPackages = [ pkgs.git collectionAdd vendomat ];
      nix.settings.experimental-features = [ "nix-command" "flakes" ];
      systemd.services.git-daemon.serviceConfig.CPUAccounting = true;
    };
    framework = { ... }: {
      environment.systemPackages = [ pkgs.git pkgs.openssh vendomat ];
      nix.settings.experimental-features = [ "nix-command" "flakes" ];
    };
  };

  testScript = ''
    import shlex

    start_all()
    server.wait_for_unit("git-daemon.service")
    server.wait_for_unit("sshd.service")
    server.wait_for_open_port(9418)
    framework.wait_for_unit("multi-user.target")


    def andrew(cmd):
        return server.succeed("su - andrew -c " + shlex.quote(cmd))


    def andrew_status(cmd):
        return server.execute("su - andrew -c " + shlex.quote(cmd))


    def write(machine, path, text):
        machine.succeed("mkdir -p $(dirname " + path + ") && cat > " + path + " <<'EOT'\n" + text + "\nEOT")


    COL = "VENDOMAT_COLLECTION=/home/andrew/vendor "
    SSH = "GIT_SSH_COMMAND='ssh -i /root/key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes' "
    DEST = "ssh://andrew@server/home/andrew/vendor/"

    # ---- STORE-023, STORE-014, STORE-015: the hooks install on a new repository ----
    print("RESULT collection-add: " + andrew(COL + "collection-add lib-a").strip())
    andrew(COL + "collection-add lib-b")
    andrew("git init -q ~/vendor/unmarked")
    for repo in ("lib-a", "lib-b"):
        for name in ("pre-receive", "post-receive"):
            andrew("test -x ~/vendor/" + repo + "/.git/hooks/" + name)
        andrew("test -e ~/vendor/" + repo + "/.git/git-daemon-export-ok")
        # The installed text equals the file in this repository (it was a copy in nix-meta).
        server.succeed("cmp ${repoHook} /home/andrew/vendor/" + repo + "/.git/hooks/post-receive")
    print("RESULT hook text: installed post-receive equals hooks/collection-post-receive")
    status, out = andrew_status(COL + "collection-add lib-a")
    assert status != 0, "collection-add must refuse an existing repository"
    status, out = andrew_status(COL + "collection-add --hooks unmarked")
    assert status != 0, "collection-add --hooks must refuse a directory with no export marker"
    status, out = andrew_status(COL + "collection-add ../x")
    assert status != 0, "collection-add must refuse a path"

    # ---- The authoring repository on framework: three release tags ----
    framework.succeed("install -m 600 ${keys.snakeOilPrivateKey} /root/key")
    framework.succeed(
        "mkdir -p /root/lib-a && cd /root/lib-a && git init -q -b main"
        " && git config user.name t && git config user.email t@example.invalid"
        " && for v in 0.9.0 1.0.0 1.0.1; do"
        "   printf '{ outputs = _: { marker = \"lib-a-%s\"; }; }\\n' $v > flake.nix"
        "   && git add flake.nix && git commit -qm \"release $v\" && git tag -a v$v -m v$v; done"
    )

    # ---- STORE-014: a tag push over SSH is accepted; the hook refreshes the working tree ----
    out = framework.succeed("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-a v1.0.0 2>&1")
    assert "collection: working tree now shows v1.0.0" in out, out
    assert andrew("git -C ~/vendor/lib-a describe --tags --exact-match HEAD").strip() == "v1.0.0"
    assert "lib-a-1.0.0" in andrew("cat ~/vendor/lib-a/flake.nix")
    print("RESULT tag push from framework over ssh: accepted; tree shows v1.0.0")

    # ---- STORE-014: a branch push, a moved tag, and a tag deletion are refused ----
    out = framework.fail("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-a main 2>&1")
    assert "collection: only release tags are accepted, not refs/heads/main" in out, out
    framework.succeed("rm -rf /root/lib-a-moved && git clone -q /root/lib-a /root/lib-a-moved")
    framework.succeed(
        "cd /root/lib-a-moved && git config user.name t && git config user.email t@example.invalid"
        " && git commit -q --allow-empty -m moved && git tag -f v1.0.0 HEAD"
    )
    out = framework.fail("cd /root/lib-a-moved && " + SSH + "git push -f " + DEST + "lib-a v1.0.0 2>&1")
    assert "collection: refs/tags/v1.0.0 exists; releases are immutable" in out, out
    out = framework.fail("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-a :refs/tags/v1.0.0 2>&1")
    assert "collection: refs/tags/v1.0.0 exists; releases are immutable" in out, out
    refs = andrew("git -C ~/vendor/lib-a for-each-ref --format='%(refname)'").split()
    assert refs == ["refs/tags/v1.0.0"], refs
    print("RESULT branch push refused; moved tag refused; tag delete refused; refs: " + " ".join(refs))

    # ---- STORE-023: version order, not push order ----
    out = framework.succeed("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-a v1.0.1 2>&1")
    assert "collection: working tree now shows v1.0.1" in out, out
    out = framework.succeed("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-a v0.9.0 2>&1")
    assert "working tree now shows" not in out, out
    assert andrew("git -C ~/vendor/lib-a describe --tags --exact-match HEAD").strip() == "v1.0.1"
    heads = andrew("git -C ~/vendor/lib-a for-each-ref refs/heads | wc -l").strip()
    assert heads == "0", heads
    print("RESULT older tag pushed last leaves the tree at v1.0.1; branches: 0")

    # ---- STORE-015: only a marked repository is served; git:// is read only ----
    framework.fail("git ls-remote git://server/unmarked")
    framework.succeed("git ls-remote git://server/lib-a | grep refs/tags/v1.0.1")
    server.succeed("git ls-remote git://server/lib-a | grep refs/tags/v1.0.1")
    framework.succeed("cd /root/lib-a && git tag v9.9.9")
    framework.fail("cd /root/lib-a && git push git://server/lib-a v9.9.9")
    framework.fail("cd /root/lib-a && git push git://server/lib-a main")
    server.fail("cd /root/lib-a-moved && git push git://server/lib-a main")
    assert "v9.9.9" not in andrew("git -C ~/vendor/lib-a tag --list")
    framework.succeed("cd /root/lib-a && git tag -d v9.9.9")
    print("RESULT unmarked repository not served; push over git:// fails from both VMs")

    # ---- STORE-008, STORE-012: Nix on both VMs fetches the tagged release ----
    flake = (
        '{ inputs.lib.url = "git://server/lib-a?ref=refs/tags/v1.0.1";'
        ' outputs = { lib, ... }: { marker = lib.marker; }; }'
    )
    for machine in (framework, server):
        write(machine, "/root/consumer/flake.nix", flake)
        machine.succeed("cd /root/consumer && nix flake lock 2>&1")
        marker = machine.succeed("cd /root/consumer && nix eval --raw .#marker").strip()
        assert marker == "lib-a-1.0.1", marker
        lock = machine.succeed("cat /root/consumer/flake.lock")
        assert "git://server/lib-a" in lock and "refs/tags/v1.0.1" in lock, lock
        print("RESULT nix fetch over git:// on " + machine.name + ": " + marker)

    # ---- STORE-009, STORE-016 to STORE-019: keep on framework ----
    def project(machine, home, entries):
        write(machine, home + "/proj/vendomat.toml", '[forge]\nurl = "git://server"\n\n[inputs]\n' + entries)
        write(machine, home + "/proj/flake-outputs.nix", "inputs: { lib.src = inputs.lib-a.outPath; }")
        machine.succeed("cd " + home + "/proj && git init -q 2>/dev/null; git -C " + home + "/proj add -A")

    project(framework, "/root", 'lib-a = { ref = "refs/tags/v1.0.0", keep = true }\n')
    env = "VENDOMAT_SOURCE_ROOT=/root/clones "
    out = framework.succeed("cd /root/proj && " + env + "vendomat sync --root . 2>&1")
    assert "lib-a: cloned" in out, out
    assert framework.succeed("git -C /root/clones/lib-a describe --tags --exact-match HEAD").strip() == "v1.0.0"
    framework.fail("git -C /root/clones/lib-a symbolic-ref -q HEAD")
    out = framework.succeed("cd /root/proj && " + env + "vendomat sync --root . 2>&1")
    assert "lib-a: unchanged" in out, out
    framework.succeed("sed -i s/v1.0.0/v1.0.1/ /root/proj/vendomat.toml")
    out = framework.succeed("cd /root/proj && " + env + "vendomat sync --root . 2>&1")
    assert framework.succeed("git -C /root/clones/lib-a describe --tags --exact-match HEAD").strip() == "v1.0.1"
    framework.succeed("echo x >> /root/clones/lib-a/flake.nix")
    status, out = framework.execute("cd /root/proj && " + env + "vendomat sync --root . 2>&1")
    assert status == 1 and "uncommitted changes" in out, (status, out)
    framework.succeed("git -C /root/clones/lib-a checkout -- flake.nix")
    # STORE-010: a keep clone is a cache. Delete it and sync restores it.
    framework.succeed("rm -rf /root/clones/lib-a")
    out = framework.succeed("cd /root/proj && " + env + "vendomat sync --root . 2>&1")
    assert "lib-a: cloned" in out, out
    assert framework.succeed("git -C /root/clones/lib-a describe --tags --exact-match HEAD").strip() == "v1.0.1"
    print("RESULT keep: cloned at tag, unchanged on rerun, moved to v1.0.1, dirty tree refused (exit 1), restored after delete")

    # ---- STORE-018: mirror acts only with --collection and gets no marker and no hook ----
    andrew(
        "rm -rf /tmp/tw && git init -q -b main /tmp/tw && cd /tmp/tw"
        " && git config user.name t && git config user.email t@example.invalid"
        " && echo third > README && git add README && git commit -qm c && git tag -a v0.1.8 -m v0.1.8"
        " && git init -q --bare -b main /srv/upstream/third.git && git push -q /srv/upstream/third.git v0.1.8 main"
    )
    write(server, "/home/andrew/proj/vendomat.toml",
          '[inputs]\nthird = { url = "git+file:///srv/upstream/third.git", ref = "refs/tags/v0.1.8", mirror = true }\n')
    write(server, "/home/andrew/proj/flake-outputs.nix", "inputs: { lib.src = inputs.third.outPath; }")
    server.succeed("chown -R andrew:users /home/andrew/proj")
    andrew("cd ~/proj && git init -q && git add -A")
    senv = "VENDOMAT_SOURCE_ROOT=/home/andrew/vendor "
    out = andrew("cd ~/proj && " + senv + "vendomat sync --root . 2>&1")
    assert "mirror skipped: not the collection host" in out, out
    andrew("test ! -e ~/vendor/third")
    out = andrew("cd ~/proj && " + senv + "vendomat sync --root . --collection 2>&1")
    print("RESULT sync --collection output:\n" + out)
    assert andrew("git -C ~/vendor/third describe --tags --exact-match HEAD").strip() == "v0.1.8"
    andrew("test ! -e ~/vendor/third/.git/git-daemon-export-ok && test ! -e ~/vendor/third/.git/hooks/pre-receive")
    framework.fail("git ls-remote git://server/third")
    print("RESULT mirror: skipped without --collection; copied with it; no marker; not served")

    # ---- STORE-022: sync --collection checks out the newest tag where no hook ran ----
    andrew("rm ~/vendor/lib-b/.git/hooks/post-receive")
    framework.succeed("cd /root/lib-a && " + SSH + "git push " + DEST + "lib-b v0.9.0 v1.0.0 v1.0.1 2>&1")
    assert andrew("ls ~/vendor/lib-b | wc -l").strip() == "0"
    out = andrew("cd ~/proj && " + senv + "vendomat sync --root . --collection 2>&1")
    assert "lib-b" in out, out
    assert andrew("git -C ~/vendor/lib-b describe --tags --exact-match HEAD").strip() == "v1.0.1"
    andrew(COL + "collection-add --hooks lib-b")
    andrew("cmp ${repoHook} ~/vendor/lib-b/.git/hooks/post-receive")
    print("RESULT collection refresh: lib-b tree filled by sync --collection; hook reinstalled with --hooks")

    # ---- STORE-010: delete a disposable copy, push the release tags again, compare ----
    def listing(root, repo):
        cmd = (
            "cd " + root + "/" + repo + " && echo refs && git for-each-ref --format='%(refname) %(objectname)'"
            " && echo tree && git describe --tags --exact-match HEAD && git rev-parse HEAD"
            " && git ls-files && echo status && git status --porcelain"
            " && (git symbolic-ref -q HEAD || echo detached)"
        )
        return andrew(cmd)

    original = {repo: listing("~/vendor", repo) for repo in ("lib-a", "lib-b")}
    andrew("rm -rf ~/vendor-copy && cp -a ~/vendor ~/vendor-copy")
    copied = {repo: listing("~/vendor-copy", repo) for repo in ("lib-a", "lib-b")}
    assert copied == original, "the copy must equal the original before the deletion"
    andrew("rm -rf ~/vendor-copy/lib-a ~/vendor-copy/lib-b ~/vendor-copy/third")
    andrew("VENDOMAT_COLLECTION=/home/andrew/vendor-copy collection-add lib-a")
    andrew("VENDOMAT_COLLECTION=/home/andrew/vendor-copy collection-add lib-b")
    for repo in ("lib-a", "lib-b"):
        out = framework.succeed(
            "cd /root/lib-a && " + SSH + "git push " + "ssh://andrew@server/home/andrew/vendor-copy/" + repo + " --tags 2>&1"
        )
        assert "working tree now shows v1.0.1" in out, out
    rebuilt = {repo: listing("~/vendor-copy", repo) for repo in ("lib-a", "lib-b")}
    for repo in ("lib-a", "lib-b"):
        print("RESULT STORE-010 original " + repo + ":\n" + original[repo])
        print("RESULT STORE-010 rebuilt " + repo + ":\n" + rebuilt[repo])
    assert rebuilt == original, "the rebuilt collection must equal the original"
    # A mirror is a cache too: delete the copy and sync restores it.
    out = andrew("cd ~/proj && VENDOMAT_SOURCE_ROOT=/home/andrew/vendor-copy vendomat sync --root . --collection 2>&1")
    assert andrew("git -C ~/vendor-copy/third describe --tags --exact-match HEAD").strip() == "v0.1.8"
    print("RESULT STORE-010: rebuilt refs, tree files, and selected tag equal the original; mirror restored by sync")

    # ---- Idle cost of the daemon (STORE-008) ----
    read = "systemctl show -p CPUUsageNSec --value git-daemon.service"
    t0 = int(server.succeed(read).strip())
    server.sleep(15)
    t1 = int(server.succeed(read).strip())
    print("RESULT idle cpu ns in 15 s: " + str(t1 - t0))
    assert t1 - t0 < 50_000_000, t1 - t0
  '';
}

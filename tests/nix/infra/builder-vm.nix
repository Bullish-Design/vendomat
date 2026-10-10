# A two-VM proof of the build host (V6 Step 5; BUILD-001 to BUILD-008, CACHE-006, CACHE-009, BOOT-017).
#
# `server` holds the collection (git://server/<input>) and the Attic cache. `framework` is a second
# build host. Both import tests/nix/infra/builder.nix, so both run `attic watch-store`. The inputs are
# tiny flakes whose package is a `derivation` that the NixOS sandbox shell builds. One input fails
# on purpose. The test builds on one host and substitutes on the other with local builds off.
#
# Run (needs /dev/kvm and the `nixos-test` system feature):
#   VENDOMAT_PACKAGE=$(nix build .#packages.x86_64-linux.vendomat --no-link --print-out-paths) \
#     nix build --impure --no-link -L --file tests/nix/infra/builder-vm.nix
let
  p = import ./pin.nix;
  inherit (p) pkgs keys lib;
  collectionAdd = pkgs.writeShellScriptBin "collection-add" (builtins.readFile ./collection-add);

  names = [ "alpha" "bravo" "broken" "charlie" "delta" ];
  builderConfig = {
    imports = [ ./builder.nix ];
    nix.settings.experimental-features = [ "nix-command" "flakes" ];
    nix.settings.substituters = lib.mkForce [ ];
    # The public keys and the netrc path are written at run time (the cache key is made in the VM).
    nix.extraOptions = "!include /etc/nix/vendomat-cache.conf";
    vendomat.builder = {
      enable = true;
      inputs = lib.genAttrs names (name: { url = "git://server/${name}"; });
      cache = {
        endpoint = "http://server:8080";
        tokenFile = "/root/secrets/push-token";
        upstreamKeyNames = [ "upstream-test-1" "cache.nixos.org-1" ];
      };
    };
    environment.systemPackages = [ pkgs.git pkgs.openssh pkgs.curl ];
  };
in
pkgs.testers.runNixOSTest {
  name = "vendomat-builder";
  nodes = {
    server = { ... }: {
      imports = [ builderConfig ./attic-server.nix ];
      users.users.andrew = {
        isNormalUser = true;
        openssh.authorizedKeys.keys = [ keys.snakeOilPublicKey ];
      };
      services.openssh.enable = true;
      systemd.tmpfiles.rules = [ "d /home/andrew/vendor 0755 andrew users -" ];
      services.gitDaemon = {
        enable = true;
        basePath = "/home/andrew/vendor";
        repositories = [ "/home/andrew/vendor" ];
        user = "andrew";
        group = "users";
      };
      networking.firewall.allowedTCPPorts = [ 22 9418 ];
      environment.systemPackages = [ collectionAdd ];
    };
    framework = { ... }: {
      imports = [ builderConfig ];
      virtualisation = {
        diskSize = 8192;
        memorySize = 2048;
        writableStoreUseTmpfs = false;
      };
    };
  };

  testScript = ''
    import json
    import os
    import re
    import shlex
    import tempfile
    from datetime import timedelta

    NAMES = ["alpha", "bravo", "broken", "charlie", "delta"]
    ATTR = "packages.x86_64-linux.default"
    CACHE = "http://server:8080/vendomat"
    SSH = "GIT_SSH_COMMAND='ssh -i /root/key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o BatchMode=yes' "


    def write(machine, path, text):
        machine.succeed("mkdir -p $(dirname " + path + ") && cat > " + path + " <<'EOT'\n" + text + "\nEOT")


    def carry(source_file, target, transform=None):
        """Move a credential from a file on the server to a file on framework. The value passes
        through driver memory and a temporary file, never a command line or a log line."""
        data = server.succeed("cat " + source_file).strip()
        if transform is not None:
            data = transform(data)
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(data + "\n")
            name = handle.name
        framework.succeed("install -d -m 700 $(dirname " + target + ")")
        framework.copy_from_host(name, target)
        framework.succeed("chmod 600 " + target)
        os.unlink(name)


    def installable(name, tag):
        return "'git://server/" + name + "?ref=refs/tags/" + tag + "#" + ATTR + "'"


    def out_path(machine, name, tag):
        return machine.succeed("nix eval --raw 'git://server/" + name + "?ref=refs/tags/" + tag + "#" + ATTR + ".outPath'").strip()


    def narinfo_code(machine, path):
        part = path.split("/")[-1].split("-")[0]
        return machine.succeed(
            "curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc " + CACHE + "/" + part + ".narinfo"
        ).strip()


    def run_unit(machine, unit):
        """Start a oneshot unit, wait for it, and return its exit status and its new journal lines."""
        q = shlex.quote(unit)
        machine.succeed("journalctl --sync")
        before = int(machine.succeed("journalctl -u " + q + " -o cat --no-pager | wc -l").strip())
        status, _ = machine.execute("systemctl start " + q)
        machine.succeed("journalctl --sync")
        text = machine.succeed("journalctl -u " + q + " -o cat --no-pager | tail -n +" + str(before + 1))
        return status, text


    start_all()
    server.wait_for_unit("atticd.service")
    server.wait_for_unit("git-daemon.service")
    server.wait_for_unit("sshd.service")
    server.wait_for_open_port(8080)
    server.wait_for_open_port(9418)
    framework.wait_for_unit("multi-user.target")

    # ---- Credentials and cache, made inside the VMs ----
    server.succeed("install -d -m 700 /root/secrets")
    mint = "(umask 077; atticd-atticadm make-token --sub {sub} --validity 1d {flags} > /root/secrets/{file})"
    server.succeed(mint.format(sub="admin", flags="--create-cache vendomat --configure-cache vendomat --pull vendomat --push vendomat", file="admin-token"))
    server.succeed(mint.format(sub="builder", flags="--push vendomat --pull vendomat", file="push-token"))
    server.succeed(mint.format(sub="reader", flags="--pull vendomat", file="pull-token"))
    write(server, "/root/admin.toml",
          'default-server = "local"\n\n[servers.local]\nendpoint = "http://server:8080"\ntoken-file = "/root/secrets/admin-token"')
    admin = "XDG_CONFIG_HOME=/root/admin-config "
    server.succeed("mkdir -p /root/admin-config/attic && install -m 600 /root/admin.toml /root/admin-config/attic/config.toml")
    server.succeed(admin + "attic cache create vendomat --upstream-cache-key-name upstream-test-1 --upstream-cache-key-name cache.nixos.org-1 2>&1")
    info = server.succeed(admin + "attic cache info vendomat 2>&1")
    found = re.search(r"Public Key:\s*(\S+)", info)
    assert found is not None, info
    pubkey = found.group(1)
    server.succeed("nix-store --generate-binary-cache-key upstream-test-1 /root/secrets/up.sec /root/secrets/up.pub")
    upstream_pub = server.succeed("cat /root/secrets/up.pub").strip()
    # A second key, not listed as an upstream key. It signs the control path of the CACHE-009 check.
    server.succeed("nix-store --generate-binary-cache-key other-test-1 /root/secrets/other.sec /root/secrets/other.pub")
    other_pub = server.succeed("cat /root/secrets/other.pub").strip()

    # Nix on both hosts: the substituter, the keys, and the pull credential as a run-time netrc file.
    conf = (
        "extra-substituters = " + CACHE + " http://server:8081\n"
        "extra-trusted-public-keys = " + pubkey + " " + upstream_pub + " " + other_pub + "\n"
        "netrc-file = /root/secrets/netrc\n"
    )
    server.succeed(
        "umask 077; printf 'machine server\\nlogin vendomat\\npassword %s\\n' \"$(cat /root/secrets/pull-token)\" > /root/secrets/netrc"
    )
    carry("/root/secrets/push-token", "/root/secrets/push-token")
    carry("/root/secrets/pull-token", "/root/secrets/netrc",
          transform=lambda token: "machine server\nlogin vendomat\npassword " + token)
    for machine in (server, framework):
        write(machine, "/etc/nix/vendomat-cache.conf", conf)
        machine.succeed("systemctl restart nix-daemon.service")
    framework.succeed("install -m 600 ${keys.snakeOilPrivateKey} /root/key")

    # ---- CACHE-006: watch-store runs on each builder ----
    for machine in (server, framework):
        machine.succeed("systemctl start vendomat-watch-store.service")
        machine.wait_for_unit("vendomat-watch-store.service")
        assert machine.succeed("systemctl is-active vendomat-watch-store.service").strip() == "active"
        assert "attic watch-store" in machine.succeed("systemctl cat vendomat-watch-store.service")
        cfgtext = machine.succeed("cat /run/vendomat-builder/attic/config.toml")
        assert "token-file" in cfgtext and "eyJ" not in cfgtext
    print("RESULT CACHE-006: vendomat-watch-store.service is active on server and framework; the config names a token file only")

    # ---- The collection and the authoring repositories ----
    for name in NAMES:
        server.succeed("su - andrew -c " + shlex.quote("VENDOMAT_COLLECTION=/home/andrew/vendor collection-add " + name))


    def release(name, version, ok=True):
        body = "echo " + name + "-" + version + " > $out" if ok else "echo " + name + " is broken >&2; exit 1"
        flake = (
            '{ outputs = _: { packages.x86_64-linux.default = derivation {'
            ' name = "' + name + '-' + version + '"; system = "x86_64-linux"; builder = "/bin/sh";'
            ' args = [ "-c" "' + body + '" ]; }; }; }'
        )
        directory = "/root/src/" + name
        framework.succeed("test -d " + directory + " || (mkdir -p " + directory + " && git -C " + directory
                          + " init -q -b main && git -C " + directory + " config user.name t && git -C "
                          + directory + " config user.email t@example.invalid)")
        write(framework, directory + "/flake.nix", flake)
        framework.succeed("cd " + directory + " && git add flake.nix && git commit -qm 'release " + version
                          + "' && git tag v" + version)
        framework.succeed("cd " + directory + " && " + SSH + "git push ssh://andrew@server/home/andrew/vendor/"
                          + name + " v" + version + " 2>&1")

    # ---- BUILD-002: one tag triggers one input ----
    release("alpha", "1.0.0")
    release("bravo", "1.0.0")
    alpha100 = out_path(server, "alpha", "v1.0.0")
    bravo100 = out_path(server, "bravo", "v1.0.0")
    assert alpha100 != bravo100
    status, text = run_unit(server, "vendomat-build@alpha:v1.0.0.service")
    print("RESULT build of alpha:v1.0.0, systemd exit " + str(status) + ":\n" + text)
    assert status == 0, text
    assert "command: nix build --no-link --print-out-paths git://server/alpha?ref=refs/tags/v1.0.0#" + ATTR in text, text
    assert "status: 0 input=alpha tag=v1.0.0" in text, text
    assert "output: " + alpha100 in text, text
    server.succeed("nix path-info " + alpha100)
    server.fail("nix path-info " + bravo100)
    print("RESULT BUILD-002: tag alpha:v1.0.0 built alpha only; the bravo output is absent from the store")

    # ---- BUILD-005: watch-store, not a push command, moves the path ----
    server.wait_until_succeeds("test $(curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc "
                               + CACHE + "/" + alpha100.split("/")[-1].split("-")[0] + ".narinfo) = 200", timeout=timedelta(seconds=120))
    unit_text = server.succeed("systemctl cat vendomat-build@.service vendomat-build-scan.service")
    script_text = server.succeed("cat $(readlink -f $(command -v vendomat-build))")
    assert "attic push" not in unit_text and "attic push" not in script_text
    assert "Pushing" not in text
    watch = server.succeed("journalctl -u vendomat-watch-store.service -o cat --no-pager")
    print("RESULT watch-store journal on server:\n" + watch)
    print("RESULT BUILD-005: no push command in the units or the script; alpha reached the cache with the build unit stopped")

    # ---- BUILD-008 direction A: built on server, substituted on framework with no local build ----
    framework.fail("nix path-info " + alpha100)
    status, text = framework.execute("nix build --max-jobs 0 --no-link -v " + installable("alpha", "v1.0.0") + " 2>&1")
    print("RESULT framework substitutes the server build, exit " + str(status) + ":\n" + text)
    assert status == 0, text
    assert re.search(r"copying path '" + alpha100 + r"' from '" + CACHE, text), text
    assert "building '" not in text
    framework.succeed("nix path-info " + alpha100)
    print("RESULT BUILD-008 A: server -> framework substituted with --max-jobs 0")

    # ---- Scan: only new tags build; a rerun builds nothing ----
    status, text = run_unit(server, "vendomat-build-scan.service")
    print("RESULT scan after bravo:v1.0.0, exit " + str(status) + ":\n" + text)
    assert status == 0 and "summary built=1 skipped=1 failed=0" in text, text
    assert "output: " + bravo100 in text
    release("alpha", "1.0.1")
    alpha101 = out_path(server, "alpha", "v1.0.1")
    status, text = run_unit(server, "vendomat-build-scan.service")
    print("RESULT scan after the new tag alpha:v1.0.1, exit " + str(status) + ":\n" + text)
    assert status == 0 and "summary built=1 skipped=2 failed=0" in text, text
    assert text.count("command: nix build") == 1 and "input=alpha tag=v1.0.1" in text, text
    assert "output: " + alpha101 in text
    status, text = run_unit(server, "vendomat-build-scan.service")
    assert status == 0 and "summary built=0 skipped=3 failed=0" in text and "command: nix build" not in text, text
    print("RESULT BUILD-002: a new tag on alpha built alpha:v1.0.1 and no other input; a rerun built nothing")

    # ---- BUILD-004: a failing input does not stop the others; BUILD-003: the log has the record ----
    release("broken", "1.0.0", ok=False)
    release("charlie", "1.0.0")
    charlie100 = out_path(server, "charlie", "v1.0.0")
    status, text = run_unit(server, "vendomat-build-scan.service")
    print("RESULT scan with a broken input, systemd exit " + str(status) + ":\n" + text)
    assert status != 0, "the scan unit must report the failure"
    assert "status: 1 input=broken tag=v1.0.0" in text and "FAILED input=broken tag=v1.0.0" in text, text
    assert "status: 0 input=charlie tag=v1.0.0" in text and "output: " + charlie100 in text, text
    assert text.index("input=broken") < text.index("input=charlie"), "broken must run before charlie"
    assert "summary built=1 skipped=3 failed=1: broken:v1.0.0" in text, text
    assert "command: nix build" in text
    server.succeed("nix path-info " + charlie100)
    print("RESULT BUILD-003/BUILD-004: broken failed with status 1, charlie still built, the log names command, status, outputs")
    # The failed unit's own journal is the record. No receipt file exists.
    server.fail("test -e /var/lib/vendomat-builder")
    # The only writable path of a build unit is its cache directory (HOME). It holds the Nix fetcher
    # and evaluation caches. List what lies outside them.
    listing = server.succeed("cd /var/cache/vendomat-builder && ls -A; find . -type f -not -path './.cache/nix/*' | head -20 || true")
    print("RESULT build unit cache directory outside .cache/nix:\n" + listing)
    assert not re.search(r"receipt|result|status|build\.log", listing), listing

    # ---- BUILD-008 direction B: built on framework, substituted on server with no local build ----
    release("bravo", "1.0.1")
    bravo101 = out_path(framework, "bravo", "v1.0.1")
    status, text = run_unit(framework, "vendomat-build@bravo:v1.0.1.service")
    print("RESULT build of bravo:v1.0.1 on framework, exit " + str(status) + ":\n" + text)
    assert status == 0 and "output: " + bravo101 in text, text
    framework.wait_until_succeeds("test $(curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc "
                                  + CACHE + "/" + bravo101.split("/")[-1].split("-")[0] + ".narinfo) = 200", timeout=timedelta(seconds=120))
    print("RESULT watch-store journal on framework (it pushed bravo:v1.0.1):\n"
          + framework.succeed("journalctl -u vendomat-watch-store.service -o cat --no-pager"))
    server.fail("nix path-info " + bravo101)
    status, text = server.execute("nix build --max-jobs 0 --no-link -v " + installable("bravo", "v1.0.1") + " 2>&1")
    print("RESULT server substitutes the framework build, exit " + str(status) + ":\n" + text)
    assert status == 0, text
    assert re.search(r"copying path '" + bravo101 + r"' from '" + CACHE, text), text
    assert "building '" not in text
    print("RESULT BUILD-008 B / BOOT-017: framework -> server substituted with --max-jobs 0")

    # ---- CACHE-008: the hash recorded at build equals the hash the cache serves ----
    def nar(machine, path, store=""):
        data = json.loads(machine.succeed("nix path-info --json --json-format 1 " + store + " " + path))
        info = data[0] if isinstance(data, list) else (data[path] if path in data else next(iter(data.values())))
        return info["narHash"]
    built_here = nar(framework, bravo101)
    served = nar(server, bravo101, "--store " + CACHE + " --option netrc-file /root/secrets/netrc")
    after = nar(server, bravo101)
    assert built_here == served == after, (built_here, served, after)
    print("RESULT CACHE-008: bravo:v1.0.1 NAR hash equal at build on framework, in the cache, and on server: " + built_here)

    # ---- BUILD-001: each input has its own output and its own cache object ----
    outs = [alpha100, alpha101, bravo100, bravo101, charlie100]
    assert len(set(outs)) == len(outs)
    for path in outs:
        assert narinfo_code(server, path) == "200", path
    print("RESULT BUILD-001: five distinct outputs of four inputs, each served by the cache")

    # ---- CACHE-009: the builder reports an upstream-signed output; Attic skips it ----
    # Build the output in a throwaway chroot store, sign it with the stand-in upstream key, and put
    # it in the stand-in upstream cache. `delta` is a flake whose derivation has the same output path.
    # A second path, signed by a key that is not an upstream key, is the control: watch-store must
    # push it, which shows that watch-store sees substituted paths at all.
    mk = (
        'let mk = name: derivation { inherit name; system = "x86_64-linux"; builder = "/bin/sh";'
        ' args = [ "-c" ("echo " + name + " > $out") ]; }; in { upstreamed = mk "vendomat-builder-upstream-sourced";'
        ' control = mk "vendomat-builder-control-other-key"; }'
    )
    write(server, "/root/drvs.nix", mk)
    up = server.succeed("nix-build /root/drvs.nix -A upstreamed --no-out-link --store /root/other-store --option substitute false").strip()
    control = server.succeed("nix-build /root/drvs.nix -A control --no-out-link --store /root/other-store --option substitute false").strip()
    server.succeed("nix store sign --store /root/other-store --key-file /root/secrets/up.sec " + up)
    server.succeed("nix store sign --store /root/other-store --key-file /root/secrets/other.sec " + control)
    server.succeed("nix copy --from /root/other-store --to file:///srv/upstream-cache " + up + " " + control)
    server.fail("nix path-info " + up)
    server.fail("nix path-info " + control)

    # The control path: substituted from the stand-in, signed by a non-upstream key.
    cpart = control.split("/")[-1].split("-")[0]
    print("RESULT narinfo of the control path at the stand-in upstream:\n" + server.succeed("curl -sS http://server:8081/" + cpart + ".narinfo"))
    status, dbg = server.execute("nix-store --realise -vv " + control + " 2>&1")
    print("RESULT realise of the control path, exit " + str(status) + ":\n" + dbg[-3000:])
    assert status == 0, dbg[-1500:]
    server.wait_until_succeeds("test $(curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc "
                               + CACHE + "/" + control.split("/")[-1].split("-")[0] + ".narinfo) = 200", timeout=timedelta(seconds=120))
    print("RESULT control: a substituted path with a non-upstream signature reached the cache through watch-store")

    # The input: `delta` at v1.0.0 builds to the upstream-signed path. Nix substitutes it, it does not build.
    delta_flake = (
        '{ outputs = _: { packages.x86_64-linux.default = derivation { name = "vendomat-builder-upstream-sourced";'
        ' system = "x86_64-linux"; builder = "/bin/sh"; args = [ "-c" "echo vendomat-builder-upstream-sourced > $out" ]; }; }; }'
    )
    framework.succeed("mkdir -p /root/src/delta && git -C /root/src/delta init -q -b main && git -C /root/src/delta config user.name t"
                      " && git -C /root/src/delta config user.email t@example.invalid")
    write(framework, "/root/src/delta/flake.nix", delta_flake)
    framework.succeed("cd /root/src/delta && git add flake.nix && git commit -qm release && git tag v1.0.0"
                      " && " + SSH + "git push ssh://andrew@server/home/andrew/vendor/delta v1.0.0 2>&1")
    assert out_path(server, "delta", "v1.0.0") == up
    status, text = run_unit(server, "vendomat-build@delta:v1.0.0.service")
    print("RESULT build of delta:v1.0.0 (an upstream-signed output), exit " + str(status) + ":\n" + text)
    assert status == 0, text
    assert "output: " + up in text, text
    assert "upstream: " + up + " is signed by upstream-test-1" in text, text
    assert "building '" not in text, "the builder substitutes the upstream path and builds nothing"
    server.sleep(10)
    code = narinfo_code(server, up)
    watch = server.succeed("journalctl -u vendomat-watch-store.service -o cat --no-pager | tail -n 12")
    print("RESULT upstream-signed output: cache narinfo HTTP " + code + "; watch-store journal tail:\n" + watch)
    assert code == "404", "Attic must skip an upstream-sourced path, got HTTP " + code
    # An explicit push, outside the builder, names the skip too.
    skip = server.succeed("XDG_CONFIG_HOME=/run/vendomat-builder attic push vendomat " + up + " 2>&1")
    print("RESULT explicit attic push of the same path (for comparison):\n" + skip)
    assert "1 in upstream" in skip, skip
    print("RESULT CACHE-009: the build log reports the upstream-signed output; Attic skipped it; the cache lacks it")

    # ---- CACHE-002: no credential in the store, the units, the journals, or the configs ----
    server.succeed("(cat /root/secrets/admin-token /root/secrets/push-token /root/secrets/pull-token;"
                   " sed 's/^[^=]*=//' /var/lib/vendomat-test/atticd.env) | grep -v '^$' > /root/secrets/patterns")
    carry("/root/secrets/patterns", "/root/secrets/patterns")
    for machine in (server, framework):
        hits = machine.succeed("grep -rlF -f /root/secrets/patterns /nix/store /etc /var/log 2>/dev/null || true").strip()
        assert hits == "", machine.name + ": " + hits
        count = machine.succeed("journalctl --no-pager -a | grep -cF -f /root/secrets/patterns || true").strip()
        assert count == "0", machine.name + " journal holds a credential"
    print("RESULT CACHE-002: no token or signing secret in the store, /etc, /var/log, or the journals of either builder")
  '';
}

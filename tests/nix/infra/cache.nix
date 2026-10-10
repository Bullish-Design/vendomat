# A two-VM proof of the private cache (V6 Step 5, CACHE-001 to CACHE-009, BOOT-012, BOOT-019).
#
# `server` runs the real `atticd` (the nixpkgs module, a sqlite database, a signing secret made at
# boot inside the VM). It also serves a small HTTP binary cache that stands in for an upstream
# cache with its own signing key. The test pushes the real Vendomat package and its closure with the
# real `attic` client. `cold` is a VM whose Nix store is an image of its own closure only, so the
# Vendomat package is absent. It substitutes with local builds off.
#
# Every token and key is made inside a VM at run time. Nothing secret enters the Nix store or a log.
# The cold VM receives its pull credential as a netrc file that the test driver writes at run time.
#
# Run (needs /dev/kvm and the `nixos-test` system feature):
#   export VENDOMAT_PACKAGE=$(nix build .#packages.x86_64-linux.vendomat --no-link --print-out-paths)
#   export VENDOMAT_PACKAGE_NARHASH=$(nix path-info --json "$VENDOMAT_PACKAGE" | jq -r '.[]|.narHash')
#   nix build --impure --no-link -L --file tests/nix/infra/cache.nix
let
  p = import ./pin.nix;
  inherit (p) pkgs vendomat lib;
  recordedHash = builtins.getEnv "VENDOMAT_PACKAGE_NARHASH";

  nixSettings = {
    nix.settings.experimental-features = [ "nix-command" "flakes" ];
    nix.settings.substituters = lib.mkForce [ ];
  };
in
pkgs.testers.runNixOSTest {
  name = "vendomat-cache";
  nodes = {
    server = { ... }: {
      imports = [ nixSettings ./attic-server.nix ];
      environment.systemPackages = [ vendomat ];
    };

    cold = { ... }: {
      imports = [ nixSettings ];
      virtualisation = {
        # The store is an image of this VM's own closure. The Vendomat package is not in it.
        useNixStoreImage = true;
        writableStore = true;
        writableStoreUseTmpfs = false;
        diskSize = 6144;
        memorySize = 2048;
      };
      # The host core's cache settings (CACHE-010) land here. The public keys are made at run time
      # in this fixture, so a file written after boot supplies them.
      nix.settings.substituters = lib.mkForce [ "https://cache.nixos.org" ];
      nix.extraOptions = "!include /etc/nix/vendomat-cache.conf";
      environment.systemPackages = [ pkgs.attic-client pkgs.curl ];
    };
  };

  testScript = ''
    import json
    import os
    import re
    import tempfile

    # No string context: the test script must not pull the package into the cold VM store image.
    VP = "${builtins.unsafeDiscardStringContext vendomat}"
    RECORDED = "${recordedHash}"
    CACHE = "http://server:8080/vendomat"
    NETRC = "--option netrc-file /root/secrets/netrc "


    def nar_hash(machine, path, store=""):
        out = machine.succeed("nix path-info --json " + store + " " + path)
        data = json.loads(out)
        if isinstance(data, list):
            info = data[0]
        else:
            info = data[path] if path in data else next(iter(data.values()))
        return info["narHash"]


    def narinfo_code(path):
        part = path.split("/")[-1].split("-")[0]
        return server.succeed(
            "curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc " + CACHE + "/" + part + ".narinfo"
        ).strip()


    def write(machine, path, text):
        machine.succeed("mkdir -p $(dirname " + path + ") && cat > " + path + " <<'EOT'\n" + text + "\nEOT")


    def carry_netrc(source_token_file, target):
        """Write a netrc file for the cold VM from a token that lives on the server. The token
        passes through driver memory and a temporary file, never a command line."""
        token = server.succeed("cat " + source_token_file).strip()
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("machine server\nlogin vendomat\npassword " + token + "\n")
            name = handle.name
        cold.succeed("install -d -m 700 /run/vendomat")
        cold.copy_from_host(name, target)
        cold.succeed("chmod 600 " + target)
        os.unlink(name)
        return token


    def carry_token(source_token_file, target):
        token = server.succeed("cat " + source_token_file).strip()
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(token + "\n")
            name = handle.name
        cold.succeed("install -d -m 700 $(dirname " + target + ")")
        cold.copy_from_host(name, target)
        cold.succeed("chmod 600 " + target)
        os.unlink(name)


    start_all()
    server.wait_for_unit("atticd.service")
    server.wait_for_unit("upstream-cache.service")
    server.wait_for_open_port(8080)
    server.wait_for_open_port(8081)
    cold.wait_for_unit("multi-user.target")

    # ---- Credentials, made inside the VM. The files hold the only copy. ----
    server.succeed("install -d -m 700 /root/secrets")
    mint = "(umask 077; atticd-atticadm make-token --sub {sub} --validity 1d {flags} > /root/secrets/{file})"
    server.succeed(mint.format(sub="admin", flags="--create-cache vendomat --configure-cache vendomat --pull vendomat --push vendomat", file="admin-token"))
    server.succeed(mint.format(sub="builder", flags="--push vendomat --pull vendomat", file="push-token"))
    server.succeed(mint.format(sub="reader", flags="--pull vendomat", file="pull-token"))
    server.succeed("test -s /root/secrets/admin-token && test -s /root/secrets/push-token && test -s /root/secrets/pull-token")

    # The attic client reads the token from a file. The config holds the file name only.
    def attic_config(machine, token_file):
        write(machine, "/root/.config/attic/config.toml",
              'default-server = "local"\n\n[servers.local]\nendpoint = "http://server:8080"\ntoken-file = "' + token_file + '"')
        machine.succeed("chmod 600 /root/.config/attic/config.toml")

    attic_config(server, "/root/secrets/admin-token")
    server.succeed("attic cache create vendomat --upstream-cache-key-name upstream-test-1 --upstream-cache-key-name cache.nixos.org-1 2>&1")
    info = server.succeed("attic cache info vendomat 2>&1")
    print("RESULT attic cache info:\n" + info)
    found = re.search(r"Public Key:\s*(\S+)", info)
    assert found is not None, info
    pubkey = found.group(1)
    assert pubkey.startswith("vendomat:"), pubkey
    server.succeed("sed -i 's|admin-token|push-token|' /root/.config/attic/config.toml")
    assert "push-token" in server.succeed("cat /root/.config/attic/config.toml")

    # ---- The pull credential for Nix on the server (a netrc file at run time) ----
    server.succeed("umask 077; printf 'machine server\\nlogin vendomat\\npassword %s\\n' \"$(cat /root/secrets/pull-token)\" > /root/secrets/netrc")

    # ---- Build in the VM and record the hash at build (CACHE-008) ----
    # Small outputs, built by the VM's own Nix. The builder `/bin/sh` is the NixOS sandbox shell.
    write(server, "/root/drvs.nix",
          'let mk = name: derivation { inherit name; system = "x86_64-linux"; builder = "/bin/sh";'
          ' args = [ "-c" ("echo " + name + " > $out") ]; };\n'
          'in { own = mk "vendomat-cache-own"; never = mk "vendomat-cache-never-pushed";'
          ' upstreamed = mk "vendomat-cache-upstream-sourced"; piped = mk "vendomat-cache-pushed-by-stdin"; }')
    OWN = server.succeed("nix-build /root/drvs.nix -A own --no-out-link").strip()
    NEVER = server.succeed("nix-build /root/drvs.nix -A never --no-out-link").strip()
    UP = server.succeed("nix-build /root/drvs.nix -A upstreamed --no-out-link").strip()
    PIPED = server.succeed("nix-build /root/drvs.nix -A piped --no-out-link").strip()
    recorded_own = nar_hash(server, OWN)
    print("RESULT recorded at build: own " + OWN + " " + recorded_own)

    # ---- CACHE-005: a path never pushed is absent, not a false success ----
    status, out = server.execute("nix path-info --store " + CACHE + " " + NETRC + NEVER + " 2>&1")
    print("RESULT absent path query, exit " + str(status) + ":\n" + out)
    assert status != 0, "a never-pushed path must not report success"
    status, out = server.execute("nix path-info --json --json-format 1 --store " + CACHE + " " + NETRC + NEVER + " 2>&1")
    print("RESULT absent path query as JSON, exit " + str(status) + ":\n" + out)
    # The same route with a pushed path would succeed, so the failure is absence, not a dead route.
    # Compare the raw narinfo answers: 404 for the absent path, and 200 once it is pushed (below).
    hash_part = NEVER.split("/")[-1].split("-")[0]
    code = server.succeed("curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc " + CACHE + "/" + hash_part + ".narinfo").strip()
    print("RESULT narinfo of the never-pushed path: HTTP " + code)
    assert code == "404", code

    # ---- A pull-only credential is refused on push (CACHE-003) ----
    attic_config(server, "/root/secrets/pull-token")
    status, out = server.execute("attic push vendomat " + OWN + " 2>&1")
    print("RESULT push with the pull-only token, exit " + str(status) + ":\n" + out)
    assert status != 0, "a pull-only token must be refused on push"
    assert "401" in out or "403" in out or "nauthor" in out or "ermission" in out or "orbidden" in out, out
    server.succeed("sed -i 's|pull-token|push-token|' /root/.config/attic/config.toml")

    # ---- Push a real Vendomat output and its closure with the real attic client ----
    out = server.succeed("attic push vendomat " + VP + " 2>&1")
    print("RESULT attic push of the Vendomat package closure:\n" + out)
    closure = server.succeed("nix-store -qR " + VP).split()
    print("RESULT closure paths: " + str(len(closure)))
    out = server.succeed("attic push vendomat " + OWN + " 2>&1")
    print("RESULT attic push of an in-VM output:\n" + out)
    own_part = OWN.split("/")[-1].split("-")[0]
    code = server.succeed("curl -sS -o /dev/null -w '%{http_code}' --netrc-file /root/secrets/netrc " + CACHE + "/" + own_part + ".narinfo").strip()
    print("RESULT narinfo of the pushed path: HTTP " + code)
    assert code == "200", code
    # A second push finds every path cached.
    again = server.succeed("attic push vendomat " + VP + " 2>&1")
    print("RESULT second push:\n" + again)

    # The shape that the module's `vendomat-push` script uses (VMOD-007): paths on stdin.
    out = server.succeed("printf '%s\\n' " + PIPED + " | attic push vendomat --stdin 2>&1")
    print("RESULT attic push --stdin (the vendomat-push shape):\n" + out)
    assert narinfo_code(PIPED) == "200"

    # ---- CACHE-009: an upstream-sourced path is skipped, and the skip is reported ----
    server.succeed("nix-store --generate-binary-cache-key upstream-test-1 /root/secrets/up.sec /root/secrets/up.pub")
    server.succeed("nix store sign --key-file /root/secrets/up.sec " + UP)
    server.succeed("nix copy --to file:///srv/upstream-cache " + UP)
    upstream_pub = server.succeed("cat /root/secrets/up.pub").strip()
    out = server.succeed("attic push vendomat " + UP + " 2>&1")
    print("RESULT attic push of an upstream-signed path:\n" + out)
    assert "upstream" in out.lower(), out
    status, out = server.execute("nix path-info --store " + CACHE + " " + NETRC + UP + " 2>&1")
    assert status != 0, "an upstream-sourced path must not be in the Vendomat cache"
    server.succeed("nix path-info --store http://server:8081 " + UP)
    print("RESULT upstream-signed path: skipped by Attic, absent from the Vendomat cache, present upstream")

    # ---- Cold VM: empty store, route, key, credential at run time ----
    cold.fail("test -e " + VP)
    cold.fail("nix path-info " + VP)
    write(cold, "/etc/nix/vendomat-cache.conf",
          "extra-substituters = " + CACHE + " http://server:8081\n"
          "extra-trusted-public-keys = " + pubkey + " " + upstream_pub + "\n"
          "netrc-file = /run/vendomat/netrc\n")
    cold.succeed("systemctl restart nix-daemon.service")
    cfg = cold.succeed("nix config show | grep -E '^(substituters|trusted-public-keys|netrc-file) '")
    print("RESULT cold nix config:\n" + cfg)
    assert CACHE in cfg and pubkey in cfg

    # No credential: the private route refuses (the PV-09 addendum, again, with the real route shape).
    status, out = cold.execute("nix build --max-jobs 0 --no-link " + VP + " 2>&1")
    print("RESULT cold build without a credential, exit " + str(status) + ":\n" + out[-1200:])
    assert status != 0
    assert "401" in out or "403" in out or "no substituter" in out.lower() or "cannot build" in out.lower(), out
    cold.fail("test -e " + VP)

    token = carry_netrc("/root/secrets/pull-token", "/run/vendomat/netrc")
    out = cold.succeed("curl -sS -o /dev/null -w '%{http_code}' " + CACHE + "/nix-cache-info").strip()
    assert out in ("401", "403"), out
    cold.succeed("nix path-info --store " + CACHE + " " + VP)

    # CACHE-007, BOOT-012, BOOT-019: substitute with local builds off.
    write(server, "/root/closure", "\n".join(closure))
    carry_token("/root/closure", "/root/closure")
    states = cold.succeed(
        "for p in $(cat /root/closure); do if nix path-info $p >/dev/null 2>&1; then echo valid $p; else echo absent $p; fi; done"
    ).split("\n")
    present = {l.split()[1] for l in states if l.startswith("valid")}
    absent = {l.split()[1] for l in states if l.startswith("absent")}
    print("RESULT cold store before: closure " + str(len(closure)) + " paths, " + str(len(present)) + " already valid (its own system), " + str(len(absent)) + " absent")
    assert VP in absent
    status, logtext = cold.execute("nix build --max-jobs 0 --no-link -v --print-out-paths " + VP + " 2>&1")
    print("RESULT cold substitution, exit " + str(status) + " (tail):\n" + logtext[-2500:])
    assert status == 0, logtext[-3000:]
    assert "building '" not in logtext, "no local build may run"
    fetched = re.findall(r"copying path '(/nix/store/[^']+)' from '([^']+)'", logtext)
    from_attic = {p for p, src in fetched if src.startswith(CACHE)}
    other_sources = {src for _, src in fetched if not src.startswith(CACHE)}
    print("RESULT substituted from the Vendomat cache: " + str(len(from_attic)) + " paths; other sources: " + str(other_sources))
    cold_closure = cold.succeed("nix-store -qR " + VP).split()
    assert set(cold_closure) == set(closure), "the cold closure must equal the pushed closure"
    assert absent <= from_attic, sorted(absent - from_attic)
    print("RESULT closure " + str(len(cold_closure)) + " paths; " + str(len(absent)) + " were absent in the cold store; all " + str(len(from_attic)) + " fetched came from the Vendomat cache")

    # CACHE-008: the hash recorded at build, the hash the cache serves, and the hash in the cold store.
    served = nar_hash(cold, VP, "--store " + CACHE)
    local = nar_hash(cold, VP)
    print("RESULT NAR hash of the Vendomat package: recorded " + RECORDED + ", served " + served + ", cold store " + local)
    assert RECORDED == served == local, (RECORDED, served, local)
    cold.succeed("nix-store --verify-path " + VP)
    # A second proof with an empty chroot store inside the VM: every one of the closure paths must come
    # from the cache, because nothing else is there. The VM store image above is the BOOT-012 proof.
    status, empty = cold.execute("nix build --store /root/empty-store --max-jobs 0 --no-link -v " + VP + " 2>&1")
    assert status == 0, empty[-3000:]
    copied_in = set(re.findall(r"copying path '(/nix/store/[^']+)' from '" + CACHE + "'", empty))
    assert copied_in == set(closure), sorted(set(closure) - copied_in)
    assert "building '" not in empty
    print("RESULT empty chroot store in the cold VM: all " + str(len(copied_in)) + " closure paths from the Vendomat cache, no build")
    # The in-VM output: recorded on server at build, served by the cache, substituted on cold.
    cold.succeed("nix build --max-jobs 0 --no-link " + OWN + " 2>&1")
    served_own = nar_hash(cold, OWN, "--store " + CACHE)
    assert recorded_own == served_own == nar_hash(cold, OWN), (recorded_own, served_own)
    cold.succeed("nix-store --verify-path " + OWN)
    print("RESULT NAR hash of the in-VM output equal at build, in the cache, and after substitution: " + recorded_own)
    cold.succeed(VP + "/bin/vendomat --help")

    # The upstream-sourced path comes from the upstream substituter, not from the Vendomat cache.
    status, logtext = cold.execute("nix build --max-jobs 0 --no-link -v " + UP + " 2>&1")
    print("RESULT cold substitution of the upstream-sourced path, exit " + str(status) + ":\n" + logtext)
    assert status == 0, logtext
    assert re.search(r"copying path '" + UP + r"' from 'http://server:8081", logtext), logtext
    assert not re.search(r"copying path '" + UP + r"' from '" + CACHE, logtext), logtext
    print("RESULT upstream-sourced path substituted from http://server:8081; the Vendomat cache did not serve it")

    # ---- CACHE-003 from the consumer: its pull credential cannot push ----
    carry_token("/root/secrets/pull-token", "/root/secrets/pull-token")
    attic_config(cold, "/root/secrets/pull-token")
    status, out = cold.execute("attic push vendomat " + VP + " 2>&1")
    print("RESULT push from the cold VM with the pull token, exit " + str(status) + ":\n" + out)
    assert status != 0

    # ---- CACHE-002: no credential in a store path, a config, or a journal ----
    patterns = "/root/secrets/patterns"
    server.succeed(
        "(cat /root/secrets/admin-token /root/secrets/push-token /root/secrets/pull-token;"
        " sed 's/^[^=]*=//' /var/lib/vendomat-test/atticd.env) | grep -v '^$' > " + patterns
    )
    carry_token("/root/secrets/pull-token", "/root/secrets/patterns")
    for machine in (server, cold):
        hits = machine.succeed("grep -rlF -f /root/secrets/patterns /nix/store /etc /var/log 2>/dev/null || true").strip()
        assert hits == "", machine.name + " store or etc holds a credential: " + hits
        hits = machine.succeed("journalctl --no-pager -a | grep -cF -f /root/secrets/patterns || true").strip()
        assert hits == "0", machine.name + " journal holds a credential"
        cfgs = machine.succeed("cat /root/.config/attic/config.toml")
        assert "token-file" in cfgs and "eyJ" not in cfgs
    print("RESULT no token or signing secret in /nix/store, /etc, /var/log, the journals, or the attic client config on both VMs")
    # The raw driver log must hold no JWT either. The wrapper scans for the JWT shape too.
  '';
}

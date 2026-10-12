# NON-PRODUCTION spike fixture (project 20, spike S6).
#
# Two-machine NixOS test for the stock `services.harmonia` module: keyless boot, key delivery
# after boot, release GC roots, cold substitution, missing-path fallback, whole-store visibility.
#
# The two signing keys below are TEST-ONLY keys. They protect nothing. Never reuse them.
#
# Status: run 6 of this file passed (all steps, 284 s test time). Run 4 put
# `writableStoreUseTmpfs = false` on every node; it drove host btrfs unallocated space to 1 MiB and
# the run was stopped. The setting now applies to `cachehost` only.
#
# Run:  nix build -L --file <this file> --out-link <path>        (nixpkgs pin: see `nixpkgsRev`)
# Nodes: cachehost (path-unit form), condhost (ConditionPathExists form), plainhost (stock
#        module), client.
{
  nixpkgsRev ? "e7439b6b14ad3cc35d05608ebca9bce01a25f5f8",
  nixpkgsHash ? "sha256-H83yz/do+hjOO0uujHyH8RgtIQP2v7Mw+cLwcZK/xKc=",
  # Seconds that the black-hole step waits at most (0 skips it).
  blackholeLimit ? 300,
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

  keyDir = "/var/lib/vendomat/keys";
  keyPath = "${keyDir}/harmonia.secret";

  goodPub = "vendomat-s6-good-1:Ns5j6FXOuIOCjNwtD+56aXgGbKIm/buKp4R6BPe0cLU=";
  goodSecret = pkgs.writeText "s6-good.secret" (builtins.readFile ./s6-good.secret); # REDACTED: the run used an inline test-only key. Regenerate: nix key generate-secret --key-name vendomat-s6-good-1 > s6-good.secret, then set goodPub from nix key convert-secret-to-public.
  badSecret = pkgs.writeText "s6-bad.secret" (builtins.readFile ./s6-bad.secret); # REDACTED test-only key. Regenerate: nix key generate-secret --key-name vendomat-s6-bad-1 > s6-bad.secret.

  # A Nix expression for a tiny derivation. The builder is a store path with context, so the
  # build sandbox includes it.
  mkExpr =
    name: payload:
    pkgs.writeText "${name}.nix" ''
      let bash = builtins.storePath "${pkgs.bash}"; in
      derivation {
        name = "s6-${name}";
        system = builtins.currentSystem;
        builder = "''${bash}/bin/bash";
        args = [ "-c" "echo ${payload} > $out" ];
      }
    '';
  exprs = lib.genAttrs (map (i: "l${toString i}") (lib.range 1 12)) (n: mkExpr n "LOCAL-ONLY-${n}") // {
    release = mkExpr "release" "RELEASE-OUTPUT-1";
    unrooted = mkExpr "unrooted" "UNROOTED-OUTPUT-1";
    private = mkExpr "private" "PRIVATE-CANARY-1";
    badsig = mkExpr "badsig" "BADSIG-OUTPUT-1";
  };
  exprsPy = lib.concatStringsSep ", " (lib.mapAttrsToList (n: v: ''"${n}": "${v}"'') exprs);

  # Common to every cache node.
  cacheNode =
    { ... }:
    {
      nix.enable = true;
      nix.settings.experimental-features = [ "nix-command" ];
      nix.settings.substituters = lib.mkForce [ ];
      networking.firewall.allowedTCPPorts = [ 5000 ];
      systemd.tmpfiles.rules = [
        "d /var/lib/vendomat 0755 root root -"
        "d ${keyDir} 0700 root root -"
        "d /nix/var/nix/gcroots/vendomat 0755 root root -"
      ];
      services.harmonia.cache = {
        enable = true;
        signKeyPaths = [ keyPath ];
      };
    };
in
pkgs.testers.runNixOSTest {
  name = "s6-harmonia-two-vm";

  nodes = {
    # Form (a): the stock module, no guard.
    plainhost = {
      imports = [ cacheNode ];
    };

    # Form (b1): the service skips its start while the key is absent.
    condhost = {
      imports = [ cacheNode ];
      systemd.services.harmonia.unitConfig.ConditionPathExists = keyPath;
    };

    # Form (b2): the socket does not start until a path unit sees the key.
    cachehost = {
      imports = [ cacheNode ];
      # Keep the writable store layer on the disk image so it survives the reboot step.
      virtualisation.writableStoreUseTmpfs = false;
      systemd.sockets.harmonia = {
        wantedBy = lib.mkForce [ ];
        unitConfig.ConditionPathExists = keyPath;
      };
      systemd.paths.harmonia-key = {
        wantedBy = [ "multi-user.target" ];
        pathConfig = {
          PathExists = keyPath;
          Unit = "harmonia.socket";
        };
      };
    };

    client =
      { ... }:
      {
        nix.enable = true;
        nix.settings.experimental-features = [ "nix-command" ];
        nix.settings.substituters = lib.mkForce [
          "http://cachehost:5000"
          "http://plainhost:5000"
        ];
        nix.settings.trusted-public-keys = lib.mkForce [ goodPub ];
      };
  };

  testScript = ''
    import time

    EXPR = {${exprsPy}}
    KEY = "${keyPath}"
    HOSTS = [plainhost, condhost, cachehost]

    def step(msg):
        print(f"\n=== {msg} ===")

    def sh(m, cmd, check=False):
        rc, out = m.execute(cmd)
        print(f"[{m.name}] $ {cmd}\n(rc={rc})\n{out}")
        if check:
            assert rc == 0, f"command failed: {cmd}"
        return rc, out

    def report(m, label):
        print(f"\n--- state of {m.name}: {label} ---")
        for cmd in [
            "systemctl is-system-running",
            "systemctl --failed --no-legend --plain",
            "systemctl show harmonia.socket harmonia.service harmonia-key.path -p Id -p ActiveState -p SubState -p Result -p ConditionResult -p NRestarts --no-pager",
            "ss -ltn | grep ':5000' || echo 'no listener on port 5000'",
            "journalctl -u harmonia.service -u harmonia.socket -u harmonia-key.path --no-pager -o cat | tail -n 12",
        ]:
            sh(m, cmd)

    def instantiate(m, name):
        m.copy_from_host(EXPR[name], f"/tmp/{name}.nix")
        return m.succeed(f"nix-instantiate /tmp/{name}.nix 2>/dev/null").strip()

    def deliver(m, secret_path):
        # Simulate a controller transfer: stage, set mode, rename into place (atomic).
        m.copy_from_host(secret_path, "/root/key.in")
        m.succeed(
            f"install -m 0400 -o root -g root /root/key.in {KEY}.tmp && mv {KEY}.tmp {KEY} && rm -f /root/key.in"
        )
        print(m.succeed(f"ls -l {KEY}"))

    def code(m, url):
        return m.execute(f"curl -s -m 15 -o /dev/null -w '%{{http_code}}' {url}")[1].strip()

    # ---------------------------------------------------------------- step 1
    step("STEP 1: keyless boot")
    t0 = time.time()
    start_all()
    for m in HOSTS + [client]:
        m.wait_for_unit("multi-user.target")
    print(f"RESULT step1 all four nodes reached multi-user.target in {time.time() - t0:.1f}s")
    for m in HOSTS:
        sh(m, f"test -e {KEY} && echo KEY-PRESENT || echo KEY-ABSENT")
        sh(m, "systemd-analyze time 2>&1 | head -n 3")
        report(m, "after boot, before any request, no key")

    step("STEP 1b: early request from client before key")
    for m in HOSTS:
        t = time.time()
        rc, out = client.execute(f"curl -sS -m 15 -o /dev/null -w '%{{http_code}}' http://{m.name}:5000/nix-cache-info")
        print(f"RESULT step1b early request to {m.name}: rc={rc} out={out!r} in {time.time() - t:.1f}s")
        report(m, "after early request, no key")

    # ---------------------------------------------------------------- step 2
    step("STEP 2: key delivery after boot")
    bash_hash = "${pkgs.bash}".split("/")[-1].split("-")[0]
    for m in HOSTS:
        t = time.time()
        deliver(m, "${goodSecret}")
        served = False
        for i in range(15):
            if code(client, f"http://{m.name}:5000/nix-cache-info") == "200":
                served = True
                break
            time.sleep(1)
        print(f"RESULT step2 {m.name}: served without intervention={served} after {time.time() - t:.1f}s")
        if not served:
            print(f"RESULT step2 {m.name}: needs recovery; running reset-failed + restart socket")
            sh(m, "systemctl reset-failed; systemctl restart harmonia.socket; sleep 1")
            print("RESULT step2 recovered code:", code(client, f"http://{m.name}:5000/nix-cache-info"))
        report(m, "after key delivery")
        sh(client, f"curl -s http://{m.name}:5000/nix-cache-info")
        sh(client, f"curl -s http://{m.name}:5000/{bash_hash}.narinfo | grep -E '^(StorePath|Sig):'")
        sh(client, f"curl -s http://{m.name}:5000/version")
        sh(m, f"stat -c '%a %U:%G %n' {KEY}")
    sh(client, "nix --version")
    sh(cachehost, "nix --version; systemctl cat harmonia.service | grep -E '^(LoadCredential|Environment|User|PrivateNetwork)'")
    sh(cachehost, "ls -l /run/harmonia 2>&1 | head; ps -o user,args -C harmonia-cache 2>&1")

    # ---------------------------------------------------------------- step 3
    step("STEP 3: release root and garbage collection on cachehost")
    cachehost.succeed("mkdir -p /nix/var/nix/gcroots/vendomat")
    rel_drv = instantiate(cachehost, "release")
    ROOT = "/nix/var/nix/gcroots/vendomat/release-1"
    rc, o = sh(cachehost, f"nix-store --add-root {ROOT} -r {rel_drv} 2>&1")
    print(f"RESULT step3 form 'nix-store --add-root ROOT -r DRV': rc={rc}")
    if rc != 0:
        rc, o = sh(cachehost, f"nix-store -r --add-root {ROOT} {rel_drv} 2>&1")
        print(f"RESULT step3 form 'nix-store -r --add-root ROOT DRV': rc={rc}")
    rel_out = cachehost.succeed(f"nix-store -q --outputs {rel_drv}").strip()
    assert cachehost.execute(f"test -e {rel_out}")[0] == 0
    unr_drv = instantiate(cachehost, "unrooted")
    unr_out = cachehost.succeed(f"nix-store -r {unr_drv} 2>/dev/null").strip()
    print("release out:", rel_out, " unrooted out:", unr_out)
    sh(cachehost, "ls -l /nix/var/nix/gcroots/vendomat/")
    rel_h = rel_out.split("/")[-1].split("-")[0]
    unr_h = unr_out.split("/")[-1].split("-")[0]
    print("RESULT step3 narinfo before GC: release", code(client, f"http://cachehost:5000/{rel_h}.narinfo"),
          "unrooted", code(client, f"http://cachehost:5000/{unr_h}.narinfo"))
    t = time.time()
    sh(cachehost, "nix-collect-garbage 2>&1 | tail -n 5")
    print(f"RESULT step3 nix-collect-garbage took {time.time() - t:.1f}s")
    rc_rel = cachehost.execute(f"test -e {rel_out}")[0]
    rc_unr = cachehost.execute(f"test -e {unr_out}")[0]
    print(f"RESULT step3 after GC: release exists={rc_rel == 0}, unrooted exists={rc_unr == 0}")
    print("RESULT step3 narinfo after GC: release", code(client, f"http://cachehost:5000/{rel_h}.narinfo"),
          "unrooted", code(client, f"http://cachehost:5000/{unr_h}.narinfo"))
    assert rc_rel == 0 and rc_unr != 0
    sh(cachehost, "nix-store --gc --print-roots 2>&1 | grep vendomat")

    # ---------------------------------------------------------------- step 4
    step("STEP 4: cold substitution on client")
    sh(client, f"test -e {rel_out} && echo PRESENT || echo ABSENT-COLD")
    t = time.time()
    sh(client, f"nix-store -r {rel_out} 2>&1", check=True)
    print(f"RESULT step4 cold substitution of release path took {time.time() - t:.1f}s")
    sh(client, f"cat {rel_out}")
    sh(client, f"nix path-info --sigs {rel_out}", check=True)
    sh(client, f"nix store verify --sigs-needed 1 {rel_out}", check=True)
    sh(client, "grep -c connect-timeout /etc/nix/nix.conf || echo 'connect-timeout not set in nix.conf'")
    sh(client, "nix config show | grep -E '^(substituters|trusted-public-keys|fallback|connect-timeout|require-sigs|download-attempts) '")

    # wrong key: rotate plainhost to the bad key, build a path there, let client try it.
    step("STEP 4b: path signed by a different key is refused")
    bad_drv = instantiate(plainhost, "badsig")
    bad_out = plainhost.succeed(f"nix-store -r {bad_drv} 2>/dev/null").strip()
    bad_h = bad_out.split("/")[-1].split("-")[0]
    sh(client, f"curl -s http://plainhost:5000/{bad_h}.narinfo | grep '^Sig'")
    deliver(plainhost, "${badSecret}")
    sh(client, f"curl -s http://plainhost:5000/{bad_h}.narinfo | grep '^Sig'")
    print("RESULT step4b (above) narinfo still signed by the old key after file replace: no restart yet")
    sh(plainhost, "systemctl restart harmonia.service; sleep 1; true")
    sh(client, f"curl -s http://plainhost:5000/{bad_h}.narinfo | grep '^Sig'")
    # path-only: no deriver known to the client
    rc, out = sh(client, f"nix-store -r {bad_out} 2>&1")
    print(f"RESULT step4b bad-key path-only realise rc={rc}")
    sh(client, f"test -e {bad_out} && echo PRESENT || echo ABSENT")
    # with the derivation: refuse the substitute, fall back to a local build
    client_bad_drv = instantiate(client, "badsig")
    assert client_bad_drv == bad_drv, (client_bad_drv, bad_drv)
    t = time.time()
    rc, out = sh(client, f"nix-store -r {bad_drv} 2>&1")
    print(f"RESULT step4b bad-key with drv rc={rc} in {time.time() - t:.1f}s")
    sh(client, f"nix path-info --sigs {bad_out}")

    # ---------------------------------------------------------------- step 5
    step("STEP 5a: path absent from the cache; substituter up")
    d = instantiate(client, "l9")
    t = time.time()
    rc, out = sh(client, f"nix-store -r {d} 2>&1")
    print(f"RESULT step5a absent path, cache up: rc={rc} in {time.time() - t:.1f}s")
    sh(client, f"cat $(nix-store -q --outputs {d})")
    sh(client, f"nix path-info --sigs $(nix-store -q --outputs {d})")

    # ---------------------------------------------------------------- step 6
    step("STEP 6: whole-store visibility")
    sh(cachehost, "systemctl start harmonia.socket")
    priv_drv = instantiate(cachehost, "private")
    priv_out = cachehost.succeed(f"nix-store -r {priv_drv} 2>/dev/null").strip()
    priv_h = priv_out.split("/")[-1].split("-")[0]
    drv_h = priv_drv.split("/")[-1].split("-")[0]
    sh(cachehost, "ls -l /nix/var/nix/gcroots/vendomat/; nix-store --gc --print-roots | grep -c s6-private || true")
    print("RESULT step6 private output narinfo", code(client, f"http://cachehost:5000/{priv_h}.narinfo"),
          " its .drv narinfo", code(client, f"http://cachehost:5000/{drv_h}.narinfo"))
    t = time.time()
    sh(client, f"nix-store -r {priv_out} 2>&1", check=True)
    sh(client, f"cat {priv_out}")
    print(f"RESULT step6 client substituted the never-released private path in {time.time() - t:.1f}s")
    sh(client, f"nix path-info --sigs {priv_out}")

    # ---------------------------------------------------------------- reboot
    step("STEP 2c: key persists across reboot; zero failed units")
    cachehost.shutdown()
    t = time.time()
    cachehost.start()
    cachehost.wait_for_unit("multi-user.target")
    cachehost.wait_for_unit("harmonia.socket")
    print(f"RESULT reboot cachehost back at multi-user in {time.time() - t:.1f}s")
    report(cachehost, "after reboot with key present")
    print("RESULT reboot serves:", code(client, "http://cachehost:5000/nix-cache-info"),
          "release root still there:", cachehost.execute(f"test -e {rel_out}")[0] == 0)

    step("STEP 3b: release root and GC again after reboot")
    print("RESULT step3b after reboot: release exists=", cachehost.execute(f"test -e {rel_out}")[0] == 0,
          " private exists=", cachehost.execute(f"test -e {priv_out}")[0] == 0)
    sh(cachehost, "nix-collect-garbage 2>&1 | tail -n 3")
    print("RESULT step3b after 2nd GC: release exists=", cachehost.execute(f"test -e {rel_out}")[0] == 0,
          " private (never rooted) exists=", cachehost.execute(f"test -e {priv_out}")[0] == 0)
    print("RESULT step3b narinfo after 2nd GC: release", code(client, f"http://cachehost:5000/{rel_h}.narinfo"),
          "private", code(client, f"http://cachehost:5000/{priv_h}.narinfo"))

    LIMIT = ${toString blackholeLimit}

    def attempt(label, name, flags="", tool="store"):
        m = client
        m.copy_from_host(EXPR[name], f"/tmp/{name}.nix")
        drv = m.succeed(f"nix-instantiate /tmp/{name}.nix 2>/dev/null").strip()
        out = m.succeed(f"nix-store -q --outputs {drv}").strip()
        cmd = {
            "store": f"nix-store -r {drv} {flags}",
            "classic": f"nix-build /tmp/{name}.nix --no-out-link {flags}",
            "nix": f"nix build --no-link {drv}^'*' {flags}",
        }[tool]
        t = time.time()
        rc, o = sh(m, f"timeout {LIMIT} {cmd} 2>&1")
        dt = time.time() - t
        built = m.execute(f"test -e {out}")[0] == 0
        print(f"RESULT {label}: tool={tool} flags={flags!r} rc={rc} output-built={built} in {dt:.1f}s")

    step("STEP 5b: cachehost harmonia stopped (connection refused)")
    sh(cachehost, "systemctl stop harmonia-key.path harmonia.socket harmonia.service; ss -ltn | grep ':5000' || echo 'no listener'")
    ONLY = "--option substituters http://cachehost:5000"
    attempt("step5b refused, defaults", "l1", ONLY)
    attempt("step5b refused, fallback=true", "l2", ONLY + " --option fallback true")
    attempt("step5b refused, classic nix-build", "l3", ONLY, "classic")
    attempt("step5b refused, nix build", "l4", ONLY, "nix")
    sh(cachehost, "systemctl start harmonia-key.path; sleep 1; ss -ltn | grep ':5000' || echo 'no listener'")

    if LIMIT > 0:
        step("STEP 5c: cachehost frozen (VM stopped; packets get no answer)")
        print("RESULT step5c control: serves before freeze:", code(client, "http://cachehost:5000/nix-cache-info"))
        cachehost.send_monitor_command("stop")
        attempt("step5c frozen, fresh ARP, defaults", "l5", ONLY)
        attempt("step5c frozen, fallback=true", "l6", ONLY + " --option fallback true")
        attempt("step5c frozen, connect-timeout=3", "l7", ONLY + " --option connect-timeout 3")
        attempt("step5c frozen, nix build", "l8", ONLY, "nix")
        cachehost.send_monitor_command("cont")
        time.sleep(3)
        print("RESULT step5c control: serves after thaw:", code(client, "http://cachehost:5000/nix-cache-info"))

    print("\nS6 TEST COMPLETE")
  '';
}

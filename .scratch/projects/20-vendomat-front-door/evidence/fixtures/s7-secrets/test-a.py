# NON-PRODUCTION fixture for spike S7. Python test script for test-a.nix. Test-only keys.
import hashlib
import json
import os

KEYS = "@KEYS@"
SSH = ("ssh -i /root/.ssh/admin -o IdentitiesOnly=yes -o BatchMode=yes "
       "-o UserKnownHostsFile=/root/known_hosts -o StrictHostKeyChecking=yes -o LogLevel=ERROR")
RESULTS = []


def rec(name, ok, **info):
    RESULTS.append({"check": name, "ok": bool(ok), **info})
    print("RESULT " + json.dumps(RESULTS[-1]), flush=True)
    assert ok, f"check failed: {name} {info}"


def failed_units(m):
    return m.succeed("systemctl --failed --no-legend --plain").strip()


def prop(m, unit, p):
    return m.succeed(f"systemctl show -P {p} {unit}").strip()


def put(name, local):
    return controller.succeed(f"{SSH} root@target 'basix-secret-put put {name}' < {local}")


start_all()
controller.wait_for_unit("multi-user.target")
target.wait_for_unit("multi-user.target")

controller.succeed("mkdir -p /root/.ssh && chmod 700 /root/.ssh")
for k in ("admin", "installer", "wrong"):
    controller.succeed(f"install -m 0600 {KEYS}/{k} /root/.ssh/{k}")

# ---------------------------------------------------------------- T1 keyless core boot
with subtest("T1 keyless core boot"):
    state = target.succeed("systemctl is-system-running --wait").strip()
    rec("T1-running", state == "running", state=state)
    rec("T1-zero-failed-units", failed_units(target) == "", failed=failed_units(target))
    rec("T1-dep-condition-skipped",
        prop(target, "basix-dep.service", "ActiveState") == "inactive"
        and prop(target, "basix-dep.service", "Result") == "success"
        and prop(target, "basix-dep.service", "ConditionResult") == "no",
        active=prop(target, "basix-dep.service", "ActiveState"),
        result=prop(target, "basix-dep.service", "Result"),
        cond=prop(target, "basix-dep.service", "ConditionResult"))
    rec("T1-path-unit-waiting", prop(target, "basix-dep-key.path", "ActiveState") == "active",
        sub=prop(target, "basix-dep-key.path", "SubState"))
    rec("T1-no-secrets-on-disk", target.succeed("ls -A /var/lib/basix/secrets").strip() == "")
    rec("T1-no-secretspec", target.execute("command -v secretspec")[0] != 0
        and target.execute("test -e /etc/basix/secretspec.toml")[0] != 0)
    keyfiles = target.succeed(
        "find / -xdev \\( -path /nix -o -path /proc -o -path /sys \\) -prune -o "
        "\\( -name 'id_*' -o -name '*.pem' -o -name '*_key' -o -name '*.key' \\) -print 2>/dev/null || true").split()
    rec("T1-only-ssh-host-keys-on-disk",
        all(p.startswith("/etc/ssh/ssh_host_") for p in keyfiles), files=keyfiles)
    nixcfg = target.succeed("nix --extra-experimental-features nix-command config show | grep -E '^(substituters|trusted-public-keys) ' || true").strip()
    rec("T1-default-nix-cache-config", "substituters" in nixcfg and "harmonia" not in nixcfg and "attic" not in nixcfg and "vendomat" not in nixcfg,
        nixconf=nixcfg)
    sshd = target.succeed("grep -iE '^(PasswordAuthentication|PermitRootLogin|KbdInteractiveAuthentication)' /etc/ssh/sshd_config").lower()
    rec("T1-sshd-key-only", "passwordauthentication no" in sshd and "permitrootlogin prohibit-password" in sshd, sshd=sshd)
    # host key made on first boot, pinned by the controller
    hostpub = target.succeed("cat /etc/ssh/ssh_host_ed25519_key.pub").split()[:2]
    controller.succeed("ssh-keyscan -t ed25519 target 2>/dev/null | grep -v '^#' > /root/known_hosts")
    scanned = controller.succeed("cut -d' ' -f2,3 /root/known_hosts").split()
    rec("T1-host-key-pinned", scanned == hostpub, note="first contact is trust on first use", scanned=scanned, hostpub=hostpub)
    auth = target.succeed("cat /etc/ssh/authorized_keys.d/root").strip().splitlines()
    rec("T1-authorized-keys-are-public-only", all(l.startswith("ssh-ed25519 ") for l in auth), n=len(auth))
    rec("T1-wrong-key-refused",
        controller.execute("ssh -i /root/.ssh/wrong -o IdentitiesOnly=yes -o BatchMode=yes "
                           "-o UserKnownHostsFile=/root/known_hosts -o LogLevel=ERROR root@target true")[0] != 0)
    rec("T1-password-login-refused",
        controller.execute("ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password -o BatchMode=yes "
                           "-o UserKnownHostsFile=/root/known_hosts -o LogLevel=ERROR root@target true")[0] != 0)
    rec("T1-admin-key-accepted", controller.succeed(f"{SSH} -n root@target 'hostname'").strip() == "target")

# ---------------------------------------------------------------- T2 route 1 delivery
with subtest("T2 route 1 first delivery"):
    controller.succeed("head -c 32 /dev/urandom | base64 -w0 > /root/dep-key.v1")
    v1 = controller.succeed("cat /root/dep-key.v1").strip()
    sha1 = hashlib.sha256(v1.encode()).hexdigest()
    put("dep-key", "/root/dep-key.v1")
    target.wait_for_unit("basix-dep.service")
    target.wait_until_succeeds("test -s /run/basix-dep/key-sha256")
    rec("T2-service-started-with-key", target.succeed("cat /run/basix-dep/key-sha256").strip() == sha1)
    st = target.succeed("stat -c '%a %U:%G' /var/lib/basix/secrets/dep-key").strip()
    rec("T2-mode-0400-root", st == "400 root:root", stat=st)
    rec("T2-zero-failed-units", failed_units(target) == "", failed=failed_units(target))
    cred = target.succeed("findmnt -no FSTYPE -T /run/credentials/basix-dep.service/dep-key").strip()
    rec("T2-credential-copy-on-tmpfs", cred in ("tmpfs", "ramfs"), fstype=cred)
    envleak = target.succeed(f"cat /proc/$(systemctl show -P MainPID basix-dep.service)/environ | tr '\\0' '\\n' | grep -cF -- '{v1}' || true").strip()
    rec("T2-key-not-in-service-environ", envleak == "0")
    leak = target.succeed(
        f"nix-store -qR /run/current-system | xargs grep -rlaF -- '{v1}' 2>/dev/null | head -3 || true; echo done").strip()
    rec("T2-key-not-in-system-closure", leak == "done", out=leak)
    jl = target.succeed(f"journalctl --no-pager | grep -cF -- '{v1}' || true").strip()
    rec("T2-key-not-in-journal", jl == "0")
    stage = target.succeed("ls -A /var/lib/basix/.staging").strip()
    rec("T2-staging-empty", stage == "", staging=stage)
    n_restarts = prop(target, "basix-dep.service", "NRestarts")
    rec("T2-restarts", True, nrestarts=n_restarts, apply_runs=prop(target, "basix-dep-apply.service", "InvocationID") != "")

# ---------------------------------------------------------------- T3 rotation
with subtest("T3 rotation"):
    pid1 = prop(target, "basix-dep.service", "MainPID")
    controller.succeed("head -c 32 /dev/urandom | base64 -w0 > /root/dep-key.v2")
    sha2 = hashlib.sha256(controller.succeed("cat /root/dep-key.v2").strip().encode()).hexdigest()
    put("dep-key", "/root/dep-key.v2")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep/key-sha256 2>/dev/null)\" = {sha2}")
    pid2 = prop(target, "basix-dep.service", "MainPID")
    rec("T3-rotated-and-restarted", pid1 != pid2 and prop(target, "basix-dep.service", "ActiveState") == "active",
        pid_before=pid1, pid_after=pid2)
    rec("T3-zero-failed-units", failed_units(target) == "")

# ---------------------------------------------------------------- T4 recovery
with subtest("T4a key deleted"):
    controller.succeed(f"{SSH} -n root@target 'basix-secret-put rm dep-key'")
    target.wait_until_succeeds("test \"$(systemctl show -P ActiveState basix-dep.service)\" = inactive")
    rec("T4a-stops-cleanly",
        prop(target, "basix-dep.service", "Result") == "success"
        and target.execute("test -e /run/basix-dep/state")[0] != 0
        and failed_units(target) == "",
        result=prop(target, "basix-dep.service", "Result"), failed=failed_units(target))

with subtest("T4b redeliver after deletion"):
    controller.succeed("head -c 32 /dev/urandom | base64 -w0 > /root/dep-key.v3")
    sha3 = hashlib.sha256(controller.succeed("cat /root/dep-key.v3").strip().encode()).hexdigest()
    put("dep-key", "/root/dep-key.v3")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep/key-sha256 2>/dev/null)\" = {sha3}")
    rec("T4b-active-again", prop(target, "basix-dep.service", "ActiveState") == "active")

with subtest("T4c reboot with key on disk"):
    target.shutdown()
    target.start()
    target.wait_for_unit("multi-user.target")
    target.wait_for_unit("basix-dep.service")
    rec("T4c-key-persisted-service-active",
        target.succeed("cat /run/basix-dep/key-sha256").strip() == sha3 and failed_units(target) == "",
        failed=failed_units(target))
    rec("T4c-host-key-stable", controller.execute(f"{SSH} -n root@target true")[0] == 0)

with subtest("T4d reboot with key removed (keyless boot again)"):
    controller.succeed(f"{SSH} -n root@target 'basix-secret-put rm dep-key'")
    target.shutdown()
    target.start()
    target.wait_for_unit("multi-user.target")
    rec("T4d-boots-clean-without-key",
        failed_units(target) == "" and prop(target, "basix-dep.service", "ActiveState") == "inactive",
        failed=failed_units(target))

with subtest("T4e total disk loss (fresh disk image, same configuration)"):
    target.shutdown()
    image = os.path.join(target.state_dir, "target.qcow2")
    print("deleting", image, os.path.exists(image), flush=True)
    os.remove(image)
    target.start()
    target.wait_for_unit("multi-user.target")
    rec("T4e-fresh-disk-boots-clean", failed_units(target) == "", failed=failed_units(target))
    rec("T4e-secrets-gone", target.succeed("ls -A /var/lib/basix/secrets").strip() == "")
    code, out = controller.execute(f"{SSH} -n root@target true 2>&1")
    rec("T4e-pinned-host-key-now-refused", code != 0 and "HOST IDENTIFICATION HAS CHANGED" in out,
        exit=code, out=out.strip()[:200])
    controller.succeed("ssh-keyscan -t ed25519 target 2>/dev/null | grep -v '^#' > /root/known_hosts")
    controller.succeed("head -c 32 /dev/urandom | base64 -w0 > /root/dep-key.v4")
    sha4 = hashlib.sha256(controller.succeed("cat /root/dep-key.v4").strip().encode()).hexdigest()
    put("dep-key", "/root/dep-key.v4")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep/key-sha256 2>/dev/null)\" = {sha4}")
    rec("T4e-recovered-by-redelivery", True)

with subtest("T4f controls"):
    controller.succeed(f"{SSH} -n root@target 'basix-secret-put rm dep-key'")
    target.wait_until_succeeds("test \"$(systemctl show -P ActiveState basix-dep.service)\" = inactive")
    target.fail("systemctl start basix-dep-unguarded.service")
    f = failed_units(target)
    rec("T4f-control-unguarded-unit-fails-and-is-detected", "basix-dep-unguarded" in f, failed=f)
    target.succeed("systemctl reset-failed")
    rec("T4f-after-reset-zero-failed", failed_units(target) == "")
    # scp (non-atomic) write straight into the secrets directory: observation only
    controller.succeed("head -c 4096 /dev/urandom | base64 -w0 > /root/dep-key.big")
    shab = hashlib.sha256(controller.succeed("cat /root/dep-key.big").strip().encode()).hexdigest()
    controller.succeed("scp -i /root/.ssh/admin -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/known_hosts "
                       "-o LogLevel=ERROR /root/dep-key.big root@target:/var/lib/basix/secrets/dep-key")
    target.sleep(3)
    got = target.succeed("cat /run/basix-dep/key-sha256 2>/dev/null || echo none").strip()
    mode = target.succeed("stat -c '%a' /var/lib/basix/secrets/dep-key").strip()
    print("OBSERVATION scp: service sha matches full file:", got == shab, "file mode", mode, flush=True)
    rec("T4f-scp-observation", True, sha_matches_full_file=(got == shab), mode=mode,
        failed=failed_units(target))
    # restore through the atomic receiver
    put("dep-key", "/root/dep-key.v4")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep/key-sha256 2>/dev/null)\" = {sha4}")

# ---------------------------------------------------------------- T5 route 3
with subtest("T5 route 3: SecretSpec resolves on the host"):
    spec = "/run/current-system/specialisation/route3/bin/switch-to-configuration"
    out = controller.succeed(f"{SSH} -n root@target '{spec} test' 2>&1")
    print("switch route3:", out[-400:], flush=True)
    target.wait_for_unit("multi-user.target")
    rec("T5-secretspec-now-present", target.succeed("secretspec --version").strip().startswith("secretspec"))
    rec("T5-dep3-skipped-without-provider-file",
        prop(target, "basix-dep3.service", "ActiveState") == "inactive"
        and prop(target, "basix-dep3.service", "Result") == "success" and failed_units(target) == "",
        failed=failed_units(target))
    # Deliver the single bootstrap credential: a dotenv provider file. Here it holds the value itself.
    controller.succeed("printf 'DEP3_KEY=%s\\n' \"$(head -c 24 /dev/urandom | base64 -w0)\" > /root/provider.env.1")
    v = controller.succeed("sed 's/^DEP3_KEY=//' /root/provider.env.1").strip()
    s1 = hashlib.sha256(v.encode()).hexdigest()
    put("provider.env", "/root/provider.env.1")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep3/key-sha256 2>/dev/null)\" = {s1}")
    rec("T5-dep3-started-secretspec-resolved", True)
    # rotation: new provider content
    controller.succeed("printf 'DEP3_KEY=%s\\n' \"$(head -c 24 /dev/urandom | base64 -w0)\" > /root/provider.env.2")
    v2 = controller.succeed("sed 's/^DEP3_KEY=//' /root/provider.env.2").strip()
    s2 = hashlib.sha256(v2.encode()).hexdigest()
    put("provider.env", "/root/provider.env.2")
    target.wait_until_succeeds(f"test \"$(cat /run/basix-dep3/key-sha256 2>/dev/null)\" = {s2}")
    rec("T5-rotation", True)
    # provider file present but lacks the secret: service must be skipped, not failed
    controller.succeed("printf 'OTHER=x\\n' > /root/provider.env.3")
    put("provider.env", "/root/provider.env.3")
    target.wait_until_succeeds("test \"$(systemctl show -P ActiveState basix-dep3.service)\" = inactive")
    rec("T5-missing-secret-skips-cleanly",
        prop(target, "basix-dep3.service", "Result") in ("success", "exec-condition") and failed_units(target) == "",
        failed=failed_units(target), result=prop(target, "basix-dep3.service", "Result"),
        active=prop(target, "basix-dep3.service", "ActiveState"))
    # does the provider file stay in the store? it must not
    pf = target.succeed("stat -c '%a %U:%G' /var/lib/basix/secrets/provider.env").strip()
    rec("T5-provider-file-mode", pf == "400 root:root", stat=pf)

print("SUMMARY " + json.dumps({"checks": len(RESULTS), "failed": [r for r in RESULTS if not r["ok"]]}), flush=True)

# NON-PRODUCTION fixture for spike S7. Python test script for test-adopt.nix. Test-only keys.
import hashlib
import json

KEYS = "@KEYS@"
MARKER = "@MARKER@"
SSH = ("ssh -n -i /root/.ssh/admin -o IdentitiesOnly=yes -o BatchMode=yes "
       "-o UserKnownHostsFile=/root/known_hosts -o StrictHostKeyChecking=yes -o LogLevel=ERROR")
SSH_IN = SSH.replace("ssh -n ", "ssh ", 1)  # a stdin-fed call must not use -n
RESULTS = []
PART_TOOLS = r"(sfdisk|fdisk|cfdisk|parted|sgdisk|gdisk|wipefs|mkfs[.a-z0-9]*|mke2fs|mkswap|disko|nixos-install|blkdiscard|partprobe|cryptsetup|dmsetup|lvm|losetup)"


def rec(name, ok, **info):
    RESULTS.append({"check": name, "ok": bool(ok), **info})
    print("RESULT " + json.dumps(RESULTS[-1]), flush=True)
    assert ok, f"check failed: {name} {info}"


def failed_units(m):
    return m.succeed("systemctl --failed --no-legend --plain").strip()


def disk_facts():
    return adopted.succeed(
        "set -e; lsblk -J -o NAME,FSTYPE,UUID,PTTYPE,SIZE | tr -d ' \\n'; echo; "
        "blkid -o export /dev/vda /dev/vdb 2>&1 || true; "
        "lsblk -rn -o NAME,MOUNTPOINTS | sort; "
        "sfdisk -d /dev/vda 2>&1 || true; sfdisk -d /dev/vdb 2>&1 || true; sfdisk -d /dev/vdc 2>&1 || true; "
        "cat /proc/swaps")


def whole_hash(dev):
    return adopted.succeed(f"sha256sum < {dev}").split()[0]


start_all()
controller.wait_for_unit("multi-user.target")
adopted.wait_for_unit("multi-user.target")
controller.succeed("mkdir -p /root/.ssh && chmod 700 /root/.ssh")
controller.succeed(f"install -m 0600 {KEYS}/admin /root/.ssh/admin")
controller.succeed("ssh-keyscan -t ed25519 adopted 2>/dev/null | grep -v '^#' > /root/known_hosts")

with subtest("A0 baseline is a plain NixOS host"):
    rec("A0-no-basix", adopted.execute("command -v basix-secret-put")[0] != 0
        and adopted.execute("systemctl cat basix-dep.service")[0] != 0)
    rec("A0-zero-failed", failed_units(adopted) == "", failed=failed_units(adopted))
    rec("A0-audit-running", adopted.succeed("systemctl is-active auditd").strip() == "active")
    adopted.succeed("mkfs.ext4 -q -L s7data /dev/vdb")  # setup, before the audit window
    adopted.succeed("sync")
    base = {"vdb": whole_hash("/dev/vdb"), "vdc": whole_hash("/dev/vdc")}
    facts_before = disk_facts()
    print("FACTS-BEFORE\n" + facts_before, flush=True)
    rec("A0-vdc-blank", base["vdc"] == hashlib.sha256(b"\0" * 64 * 1024 * 1024).hexdigest(), vdc=base["vdc"])
    n_before = int(adopted.succeed("wc -l < /var/log/audit/audit.log").strip())

with subtest("A1 control: the audit trail sees a partition tool"):
    adopted.succeed("sfdisk --version >/dev/null")
    seen = adopted.succeed(
        f"tail -n +{n_before + 1} /var/log/audit/audit.log | grep -a 'type=SYSCALL' | grep -ao 'exe=\"[^\"]*\"' | sort | uniq -c")
    rec("A1-control-sfdisk-visible", "sfdisk" in seen, sample=seen[-300:])
    n_before = int(adopted.succeed("wc -l < /var/log/audit/audit.log").strip())

with subtest("A2 transport: a controller-only path moves over ssh-ng"):
    code, out = controller.execute(f"NIX_SSHOPTS='-i /root/.ssh/admin -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/known_hosts -o StrictHostKeyChecking=yes -o LogLevel=ERROR' nix copy --no-check-sigs --to ssh-ng://root@adopted {MARKER} 2>&1")
    print("NIXCOPY exit", code, out, flush=True)
    rec("A2-marker-path-arrived", code == 0 and adopted.succeed(f"test -e {MARKER} && echo yes").strip() == "yes", out=out[-200:])

with subtest("A3 push the Basix core closure and switch"):
    top = adopted.succeed("readlink -f /run/current-system/specialisation/basix").strip()
    print("basix toplevel", top, flush=True)
    out = controller.succeed(
        "NIX_SSHOPTS='-i /root/.ssh/admin -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/known_hosts -o StrictHostKeyChecking=yes -o LogLevel=ERROR' "
        f"nix copy --no-check-sigs --to ssh-ng://root@adopted {top} 2>&1 || true")
    print("nix copy of toplevel:", out[-300:], flush=True)
    controller.succeed(f"{SSH} root@adopted 'nix-env -p /nix/var/nix/profiles/system --set {top}'")
    sw = controller.succeed(f"{SSH} root@adopted '{top}/bin/switch-to-configuration test' 2>&1")
    print("switch:", sw[-400:], flush=True)
    adopted.wait_for_unit("multi-user.target")
    rec("A3-basix-receiver-present", adopted.succeed("command -v basix-secret-put").strip() != "")
    rec("A3-current-system-is-basix", adopted.succeed("readlink -f /run/current-system").strip() == top)
    rec("A3-zero-failed-after-switch", failed_units(adopted) == "", failed=failed_units(adopted))
    rec("A3-dep-skipped-no-key",
        adopted.succeed("systemctl show -P ActiveState basix-dep.service").strip() == "inactive"
        and adopted.succeed("systemctl show -P Result basix-dep.service").strip() == "success")
    rec("A3-no-secret-material", adopted.succeed("ls -A /var/lib/basix/secrets").strip() == "")

with subtest("A4 later secret delivery on the adopted host"):
    controller.succeed("head -c 32 /dev/urandom | base64 -w0 > /root/dep-key.v1")
    sha1 = hashlib.sha256(controller.succeed("cat /root/dep-key.v1").strip().encode()).hexdigest()
    controller.succeed(f"{SSH_IN} root@adopted 'basix-secret-put put dep-key' < /root/dep-key.v1")
    adopted.wait_until_succeeds(f"test \"$(cat /run/basix-dep/key-sha256 2>/dev/null)\" = {sha1}")
    st = adopted.succeed("stat -c '%a %U:%G' /var/lib/basix/secrets/dep-key").strip()
    rec("A4-service-active-key-0400", st == "400 root:root", stat=st)
    rec("A4-zero-failed", failed_units(adopted) == "", failed=failed_units(adopted))

with subtest("A5 no disk installation step ran"):
    n_end = int(adopted.succeed("wc -l < /var/log/audit/audit.log").strip())  # window ends before our own checks
    facts_after = disk_facts()
    rec("A5-disk-facts-equal", facts_after == facts_before, diff_len=len(facts_after) - len(facts_before))
    rec("A5-vdb-hash-equal", whole_hash("/dev/vdb") == base["vdb"])
    rec("A5-vdc-hash-equal", whole_hash("/dev/vdc") == base["vdc"])
    exes = adopted.succeed(
        f"sed -n '{n_before + 1},{n_end}p' /var/log/audit/audit.log | grep -a 'type=SYSCALL' | grep -ao 'exe=\"[^\"]*\"' | sort | uniq -c")
    print("EXES\n" + exes, flush=True)
    n_exec = len([ln for ln in exes.splitlines() if ln.strip()])
    hits = adopted.succeed(
        f"sed -n '{n_before + 1},{n_end}p' /var/log/audit/audit.log | grep -a 'type=SYSCALL' | grep -aoE 'exe=\"[^\"]*/{PART_TOOLS}\"' | sort | uniq -c || true").strip()
    rec("A5-no-partition-tool-executed", hits == "", distinct_executables=n_exec, hits=hits)
    rec("A5-no-mnt-mount", adopted.execute("findmnt /mnt")[0] != 0)

with subtest("A6 rollback leaves the delivered key on disk"):
    old = adopted.succeed("readlink -f /nix/var/nix/profiles/system").strip()
    # roll back: the previous toplevel is the baseline system the node booted
    base_top = adopted.succeed("readlink -f /run/booted-system").strip()
    controller.succeed(f"{SSH} root@adopted '{base_top}/bin/switch-to-configuration test' 2>&1")
    cat_code = adopted.execute("systemctl cat basix-dep.service")[0]
    active = adopted.execute("systemctl is-active basix-dep.service")[1].strip()
    recv = adopted.execute("command -v basix-secret-put")[0]
    rec("A6-rolled-back-no-basix-units", cat_code != 0 and active != "active" and recv != 0,
        cat_code=cat_code, active=active, receiver_code=recv)
    left = adopted.succeed("ls -A /var/lib/basix/secrets").strip()
    rec("A6-key-file-remains-after-rollback", left == "dep-key", left=left, profile_before=old)

print("SUMMARY " + json.dumps({"checks": len(RESULTS), "failed": [r for r in RESULTS if not r["ok"]]}), flush=True)

#!/usr/bin/env python3
"""NON-PRODUCTION spike S7 fixture (disposable QEMU only, test-only keys).

Keyless fresh install with the fork's devenv Machines, derived from vm-fixture.
Differences: two keys (installer key A reaches the source VM; admin key B is the only
key in the installed configuration); no install.secrets, no install.extraFiles, no
copyHostKeys, no SecretSpec. After the first boot it delivers a key by route 1.

usage: python3 -I vm-keyless DEVENV_BIN MODULES_URL RUNDIR LOGDIR QEMU_DIR OVMF_DIR NIXPKGS_REV
"""
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
from importlib.machinery import SourceFileLoader  # noqa: E402
from importlib.util import module_from_spec, spec_from_loader  # noqa: E402

_loader = SourceFileLoader("fixture_common", str(HERE / "fixture-common"))
_common = module_from_spec(spec_from_loader("fixture_common", _loader))
_loader.exec_module(_common)
prepare_project = _common.prepare_project

PORT = 22861
steps = []


def main():
    devenv, modules_url, rundir, logdir, qemu_dir, ovmf_dir, rev = sys.argv[1:8]
    rundir, logdir = Path(rundir), Path(logdir)
    rundir.mkdir(parents=True)
    logdir.mkdir(parents=True, exist_ok=True)
    qemu = Path(qemu_dir) / "bin" / "qemu-system-x86_64"
    qemu_img = Path(qemu_dir) / "bin" / "qemu-img"
    keys = rundir / "keys"
    keys.mkdir()
    base_env = dict(os.environ, NO_COLOR="1")
    base_env.pop("BOOTSTRAP_TOKEN", None)

    def record(name, ok, **info):
        entry = {"step": name, "result": "PASS" if ok else "FAIL", **info}
        steps.append(entry)
        print(json.dumps(entry), flush=True)
        (logdir / "steps.json").write_text(json.dumps(steps, indent=2))
        if not ok:
            raise SystemExit(f"step failed: {name}")

    def run(cmd, name, check=True, **kw):
        proc = subprocess.run(cmd, text=True, capture_output=True, **kw)
        (logdir / f"{len(steps):02d}-{name}.log").write_text(
            f"$ {' '.join(map(str, cmd))}\n[exit {proc.returncode}]\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}\n"
        )
        if check and proc.returncode != 0:
            record(name, False, exit=proc.returncode)
        return proc

    for n in ("installer", "admin"):
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"s7-test-only-{n}", "-f", str(keys / n)], f"keygen-{n}")
    pub_a = (keys / "installer.pub").read_text()
    pub_b = (keys / "admin.pub").read_text()
    blob_a = pub_a.split()[1]
    project = rundir / "project"
    prepare_project(project, modules_url, PORT, pub_b)
    # devenv reaches the source VM with the installer key A.
    shutil.copy(keys / "installer", project / "keys" / "id_ed25519")
    os.chmod(project / "keys" / "id_ed25519", 0o600)

    out = run([str(HERE / "vm" / "build-source-vm.sh"), rev, str(keys / "installer.pub"), str(PORT)], "build-source-vm")
    runner = next((Path(out.stdout.split()[0]) / "bin").glob("run-*-vm"))
    target = rundir / "target.qcow2"
    run([str(qemu_img), "create", "-q", "-f", "qcow2", str(target), "12G"], "create-target-disk")
    vm_env = dict(os.environ, NIX_DISK_IMAGE=str(rundir / "source.qcow2"),
                  PATH=f"{Path(qemu_dir) / 'bin'}:{os.environ['PATH']}",
                  QEMU_OPTS=f"-drive file={target},if=none,id=tgt,format=qcow2 "
                            f"-device virtio-blk-pci,drive=tgt,serial=TARGETDISK")
    console = open(logdir / "source-console.log", "w")
    source_vm = subprocess.Popen([str(runner)], env=vm_env, stdin=subprocess.DEVNULL,
                                 stdout=console, stderr=subprocess.STDOUT, start_new_session=True)

    def cleanup():
        if source_vm.poll() is None:
            source_vm.kill()
        pid_file = rundir / "installed.pid"
        if pid_file.exists():
            subprocess.run(["kill", pid_file.read_text().strip()], capture_output=True)

    atexit.register(cleanup)

    def ssh_cmd(key):
        return ["ssh", "-n", "-i", str(keys / key), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=5", "-p", str(PORT), "root@127.0.0.1"]

    def vm(cmd, name="vm", key="installer", check=True, timeout=600):
        return run([*ssh_cmd(key), cmd], name, check=check, timeout=timeout)

    def wait_ssh(key, limit=200):
        for _ in range(limit):
            if subprocess.run([*ssh_cmd(key), "true"], capture_output=True).returncode == 0:
                return True
            time.sleep(3)
        return False

    def scan_host_key():
        scan = subprocess.run(["ssh-keyscan", "-p", str(PORT), "-t", "ed25519", "127.0.0.1"],
                              text=True, capture_output=True)
        lines = [ln for ln in scan.stdout.splitlines() if not ln.startswith("#")]
        return lines[0].split()[-1] if lines else None

    record("source-vm-ssh", wait_ssh("installer"), port=PORT)
    source_host_key = scan_host_key()
    (project / "keys" / "known_hosts").write_text(
        subprocess.run(["ssh-keyscan", "-p", str(PORT), "-t", "ed25519", "127.0.0.1"], text=True, capture_output=True).stdout)
    record("source-host-key", bool(source_host_key), key=source_host_key)
    src_auth = vm("cat /root/.ssh/authorized_keys /etc/ssh/authorized_keys.d/root 2>/dev/null; true", "source-authorized-keys").stdout
    record("source-vm-accepts-installer-key-only", blob_a in src_auth and pub_b.split()[1] not in src_auth)

    proc = run([devenv, "machines", "install", "fresh", "--phases", "disko,install"], "install-fresh",
               check=False, cwd=project, env=base_env, timeout=3600)
    record("install-fresh", proc.returncode == 0, exit=proc.returncode)
    vm("umount -R /mnt 2>&1; findmnt /mnt || echo unmounted", "unmount-mnt", check=False)
    vm("poweroff", "poweroff-source", check=False)
    try:
        source_vm.wait(timeout=120)
    except subprocess.TimeoutExpired:
        source_vm.kill()

    vars_fd = rundir / "OVMF_VARS.fd"
    shutil.copy(Path(ovmf_dir) / "FV" / "OVMF_VARS.fd", vars_fd)
    os.chmod(vars_fd, 0o644)
    boot = [str(qemu), "-machine", "q35,accel=kvm", "-cpu", "host", "-smp", "2", "-m", "3072",
            "-drive", f"if=pflash,format=raw,readonly=on,file={Path(ovmf_dir) / 'FV' / 'OVMF_CODE.fd'}",
            "-drive", f"if=pflash,format=raw,file={vars_fd}",
            "-drive", f"file={target},if=none,id=tgt,format=qcow2",
            "-device", "virtio-blk-pci,drive=tgt,serial=TARGETDISK",
            "-netdev", f"user,id=n0,hostfwd=tcp:127.0.0.1:{PORT}-:22", "-device", "virtio-net-pci,netdev=n0",
            "-display", "none", "-serial", f"file:{logdir / 'installed-serial.log'}",
            "-pidfile", str(rundir / "installed.pid"), "-daemonize"]
    run(boot, "boot-installed-disk")
    record("installed-ssh-with-admin-key", wait_ssh("admin", 100), port=PORT)

    # --- findings on the installed system -------------------------------------------------
    rc_a = subprocess.run([*ssh_cmd("installer"), "true"], capture_output=True, text=True)
    record("installer-key-refused-on-installed", rc_a.returncode == 255 and "Permission denied" in rc_a.stderr,
           exit=rc_a.returncode, stderr=rc_a.stderr.strip()[:120])
    installed_host_key = scan_host_key()
    record("host-key-differs-from-source", installed_host_key and installed_host_key != source_host_key,
           source=source_host_key, installed=installed_host_key)
    state = vm("systemctl is-system-running --wait", "is-system-running", key="admin", check=False).stdout.strip()
    failed = vm("systemctl --failed --no-legend --plain", "failed-units", key="admin").stdout.strip()
    record("zero-failed-units-keyless-first-boot", state == "running" and failed == "", state=state, failed=failed)
    auth = vm("cat /etc/ssh/authorized_keys.d/root; ls -A /root/.ssh 2>&1 || true", "installed-authorized", key="admin").stdout
    record("installed-authorized-keys-admin-only", pub_b.split()[1] in auth and blob_a not in auth, listing=auth.strip()[:300])
    hit = vm(f"grep -rIlF -- {blob_a} /etc /root /var /home /boot 2>/dev/null | head -5; echo done", "grep-installer-key-disk", key="admin", check=False).stdout.strip()
    record("installer-public-key-not-on-installed-disk", hit == "done", out=hit)
    hit2 = vm(f"nix-store -qR /run/current-system | xargs grep -rlaF -- {blob_a} 2>/dev/null | head -3 || true; echo done", "grep-installer-key-store", key="admin", check=False, timeout=900).stdout.strip()
    record("installer-public-key-not-in-system-closure", hit2 == "done", out=hit2)
    privs = vm("find / -xdev \\( -path /nix -o -path /proc -o -path /sys \\) -prune -o \\( -name 'id_*' -o -name '*.pem' -o -name '*_key' -o -name '*.key' \\) -print 2>/dev/null; true",
               "private-key-files", key="admin").stdout.split()
    record("only-ssh-host-keys-on-disk", all(p.startswith("/etc/ssh/ssh_host_") for p in privs), files=privs)
    host_key_age = vm("stat -c '%n %y' /etc/ssh/ssh_host_ed25519_key; date '+now %F %T'; cut -d' ' -f1 /proc/uptime", "host-key-time", key="admin").stdout
    record("host-key-created-at-first-boot", True, stat=host_key_age.strip())
    record("no-secretspec-no-bootstrap-dir",
           vm("command -v secretspec; test -e /var/lib/bootstrap && echo present; echo ok", "no-secretspec", key="admin", check=False).stdout.strip() == "ok")
    nixcfg = vm("nix config show 2>/dev/null | grep -E '^(substituters|trusted-public-keys) '; true", "nix-config", key="admin", check=False).stdout.strip()
    record("default-cache-config", "harmonia" not in nixcfg and "attic" not in nixcfg, nixconf=nixcfg)
    dep = vm("systemctl show -P ActiveState basix-dep.service; systemctl show -P Result basix-dep.service; ls -A /var/lib/basix/secrets", "dep-before", key="admin").stdout.split("\n")
    record("dependent-service-skipped-before-key", dep[0] == "inactive" and dep[1] == "success" and dep[2] == "", dep=dep)

    # --- post-install secret delivery, route 1 --------------------------------------------
    value = os.urandom(24).hex()
    expect = hashlib.sha256(value.encode()).hexdigest()
    run([c for c in ssh_cmd("admin") if c != "-n"] + ["basix-secret-put put dep-key"], "route1-put", input=value, check=True)
    ok = False
    for _ in range(30):
        got = subprocess.run([*ssh_cmd("admin"), "cat /run/basix-dep/key-sha256 2>/dev/null"], capture_output=True, text=True).stdout.strip()
        if got == expect:
            ok = True
            break
        time.sleep(2)
    record("route1-dependent-service-started", ok)
    st = vm("stat -c '%a %U:%G' /var/lib/basix/secrets/dep-key", "route1-stat", key="admin").stdout.strip()
    record("route1-key-mode", st == "400 root:root", stat=st)

    # --- reboot: key persists, host key stable, still zero failed units --------------------
    hk1 = scan_host_key()
    vm("systemctl reboot", "reboot", key="admin", check=False)
    time.sleep(15)
    record("ssh-after-reboot", wait_ssh("admin", 100))
    hk2 = scan_host_key()
    vm("systemctl is-system-running --wait", "is-system-running-2", key="admin", check=False)
    failed2 = vm("systemctl --failed --no-legend --plain", "failed-units-2", key="admin").stdout.strip()
    got2 = vm("cat /run/basix-dep/key-sha256", "sha-after-reboot", key="admin", check=False).stdout.strip()
    record("reboot-keeps-key-and-host-key", hk1 == hk2 and failed2 == "" and got2 == expect, failed=failed2)

    vm("poweroff", "poweroff-installed", key="admin", check=False)
    time.sleep(10)
    pid = (rundir / "installed.pid").read_text().strip() if (rundir / "installed.pid").exists() else None
    if pid:
        subprocess.run(["kill", pid], capture_output=True)
    failed_steps = [s for s in steps if s["result"] == "FAIL"]
    print(f"summary: {len(steps) - len(failed_steps)} pass, {len(failed_steps)} fail")
    sys.exit(1 if failed_steps else 0)


if __name__ == "__main__":
    main()

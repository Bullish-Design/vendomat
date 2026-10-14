"""Boot proof for the module-only devenv fork (project 23 slice S1; W7 H2, W8 Q4).

Opt in with `testee verify modules-vm`. The check materializes a fresh copy of the module series,
uses it as the `devenv` input of a small workspace, and boots two images under QEMU with KVM:

- `machines.box.build.vm` of a plain machine, and
- `machines.target.build.iso` of a machine with a facter report and a disko layout, under OVMF
  (UEFI) with a blank qcow2 disk image attached.

Each guest must reach the multi-user target and report zero failed units. The check reads the
state over SSH with a throwaway key and then powers the guest off. It never runs an installer or
disko. The only disk it attaches is an image file. QEMU and OVMF come from the pinned Nixpkgs.
Images, disks, variable stores, and scratch space go under `/mnt/shared/vendomat-p21/s1/`.
Logs go to `$VENDOMAT_FIXTURE_LOGS`.
"""

from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "modules-vm"
ENABLED = os.environ.get("VENDOMAT_MODULES_VM") == "1"
pytestmark = pytest.mark.skipif(not ENABLED, reason="VM fixture; run through testee verify modules-vm")

NIXPKGS = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8"
#: Owner rule: every VM image, disk, variable store, and scratch directory lives here.
STATE = Path(os.environ.get("VENDOMAT_MODULES_VM_STATE", "/mnt/shared/vendomat-p21/s1/modules-vm"))
UPSTREAM = Path(os.environ.get("VENDOMAT_DEVENV_SOURCE", str(Path.home() / "vendor" / "devenv")))
FORBIDDEN_PORT = 19418
#: `-F /dev/null` also skips the system ssh_config. Inside the Testee sandbox its systemd include has an
#: owner that ssh rejects ("Bad owner or permissions").
SSH_OPTIONS = [
    "-F",
    "/dev/null",
    "-o",
    "IdentitiesOnly=yes",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "-o",
    "LogLevel=ERROR",
    "-o",
    "ConnectTimeout=5",
]
MIN_UNALLOCATED_GIB = 15.0
MAX_METADATA_PERCENT = 90.0

#: QEMU 11 fails at start with "Failed to initialize io_uring: Cannot allocate memory" on this host when
#: the locked-memory limit is 8 MiB or unlimited. A 64 KiB limit makes it skip io_uring and start.
MEMLOCK_BYTES = 64 * 1024

_UNITS = {"B": 1 / 2**30, "KiB": 1 / 2**20, "MiB": 1 / 2**10, "GiB": 1.0, "TiB": 2**10}


# --- Records ----------------------------------------------------------------------------------


@dataclass
class Logs:
    """Keeps every command, its exit status, and its output outside the repository."""

    root: Path
    count: int = 0
    timings: dict[str, float] = field(default_factory=dict)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.write_text(text)
        return path

    def note(self, line: str) -> None:
        with (self.root / "notes.log").open("a") as handle:
            stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
            handle.write(f"{stamp} {line}\n")

    def run(
        self,
        name: str,
        argv: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int = 600,
        qemu: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.count += 1
        stem = f"{self.count:03d}-{name}"
        started = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                preexec_fn=limit_memlock if qemu else None,
            )
        except subprocess.TimeoutExpired as error:
            self.write(f"{stem}.cmd", json.dumps({"argv": argv, "cwd": str(cwd), "timeout": timeout}) + "\n")
            self.write(f"{stem}.stdout", _text(error.stdout))
            self.write(f"{stem}.stderr", _text(error.stderr))
            raise
        elapsed = time.monotonic() - started
        record = {"argv": argv, "cwd": str(cwd), "returncode": proc.returncode, "seconds": round(elapsed, 1)}
        self.write(f"{stem}.cmd", json.dumps(record, indent=1) + "\n")
        self.write(f"{stem}.stdout", proc.stdout)
        self.write(f"{stem}.stderr", proc.stderr)
        self.timings[name] = elapsed
        return proc


def limit_memlock() -> None:
    """Run in a child before exec: lower the locked-memory limit so QEMU skips io_uring."""
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (MEMLOCK_BYTES, MEMLOCK_BYTES))


def _text(value: object) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def _log_root() -> Path:
    given = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if given:
        return Path(given)
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path.home() / ".local/state/vendomat/p21/2026-10-14/s1/modules-vm" / stamp


# --- Disk guard -------------------------------------------------------------------------------


def _gib(number: str, unit: str) -> float:
    return float(number) * _UNITS[unit]


def root_usage(logs: Logs) -> tuple[float, float]:
    """Return unallocated GiB and the metadata use in percent of the root file system."""
    proc = logs.run("btrfs-usage", ["btrfs", "filesystem", "usage", "/"])
    unallocated = re.search(r"Device unallocated:\s+([\d.]+)(\w+)", proc.stdout)
    metadata = re.search(r"Metadata,\w+: Size:[\d.]+\w+, Used:[\d.]+\w+ \(([\d.]+)%\)", proc.stdout)
    assert unallocated and metadata, f"cannot read btrfs usage:\n{proc.stdout}\n{proc.stderr}"
    return _gib(*unallocated.groups()), float(metadata.group(1))


def disk_guard(logs: Logs, label: str) -> None:
    """Stop before an image build when the root file system is short of space (guide 1.4)."""
    for attempt in (1, 2):
        free, meta = root_usage(logs)
        logs.note(f"disk-guard {label} try {attempt}: unallocated {free:.2f} GiB, metadata {meta:.1f} %")
        if free < MIN_UNALLOCATED_GIB:
            pytest.fail(f"stop: only {free:.2f} GiB unallocated on / before {label}", pytrace=False)
        if meta <= MAX_METADATA_PERCENT:
            return
        if attempt == 1:
            time.sleep(60)
    pytest.fail(f"stop: metadata use {meta:.1f} % on / before {label}", pytrace=False)


# --- Environment ------------------------------------------------------------------------------


@dataclass
class Env:
    logs: Logs
    env: dict[str, str]
    qemu: Path
    ovmf: Path
    ssh_key: Path
    workspace: Path
    modules: Path


@pytest.fixture(scope="session")
def lab() -> Env:
    for tool in ("nix", "devenv", "ssh", "ssh-keygen", "btrfs", "git"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not on PATH")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("/dev/kvm is not usable")
    if not UPSTREAM.is_dir():
        pytest.skip(f"no devenv source at {UPSTREAM}")

    logs = Logs(_log_root())
    logs.root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(STATE, ignore_errors=True)
    for sub in ("tmp", "vm", "iso"):
        (STATE / sub).mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k != "UV_PROJECT_ENVIRONMENT"}
    env["TMPDIR"] = str(STATE / "tmp")
    logs.note(f"state {STATE}; logs {logs.root}")

    tools = ["nix", "build", "--no-link", "--print-out-paths", f"{NIXPKGS}#qemu_kvm", f"{NIXPKGS}#OVMF.fd"]
    built = logs.run("nix-build-tools", tools, env=env)
    assert built.returncode == 0, built.stderr[-2000:]
    paths = [Path(p) for p in built.stdout.split()]
    qemu = next(p for p in paths if (p / "bin/qemu-system-x86_64").exists())
    ovmf = next(p for p in paths if (p / "FV/OVMF_CODE.fd").exists())

    # A fresh copy of the module series, with no network use.
    modules = STATE / "devenv-modules"
    materialize = [
        sys.executable,
        "-I",
        str(ROOT / "devenv-dist/materialize"),
        str(modules),
        "--series",
        "modules",
        "--source",
        str(UPSTREAM),
        "--verify",
    ]
    made = logs.run("materialize", materialize, cwd=ROOT, env=env, timeout=900)
    assert made.returncode == 0, made.stderr[-2000:]

    # A throwaway key pair. The public half goes into the machines through the generated key.nix.
    key = STATE / "key"
    keygen = ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "modules-vm-test-only", "-f", str(key)]
    gen = logs.run("ssh-keygen", keygen)
    assert gen.returncode == 0, gen.stderr
    public = key.with_suffix(".pub").read_text().strip()

    workspace = STATE / "ws"
    shutil.copytree(FIXTURE, workspace)
    template = (workspace / "devenv.yaml.in").read_text()
    (workspace / "devenv.yaml").write_text(template.replace("@MODULES@", f"{modules}/src/modules"))
    (workspace / "devenv.yaml.in").unlink()
    (workspace / ".machines").mkdir()
    shutil.move(workspace / "machines" / "target", workspace / ".machines" / "target")
    (workspace / "machines").rmdir()
    (workspace / "key.nix").write_text(f'{{ users.users.root.openssh.authorizedKeys.keys = [ "{public}" ]; }}\n')
    return Env(logs, env, qemu, ovmf, key, workspace, modules)


def build(lab: Env, attr: str) -> Path:
    """Build one machine image with `devenv build` and return its store path."""
    disk_guard(lab.logs, attr)
    before = root_usage(lab.logs)
    proc = lab.logs.run(f"devenv-build-{attr}", ["devenv", "build", attr], cwd=lab.workspace, env=lab.env, timeout=3600)
    after = root_usage(lab.logs)
    space = f"unallocated {before[0]:.2f} -> {after[0]:.2f} GiB; metadata {before[1]:.1f} -> {after[1]:.1f} %"
    lab.logs.note(f"build {attr}: rc {proc.returncode}; {space}")
    assert proc.returncode == 0, proc.stderr[-3000:]
    found = re.search(rf'"{re.escape(attr)}":\s*"(/nix/store/[^"]+)"', proc.stdout)
    assert found, f"no store path for {attr}:\n{proc.stdout}\n{proc.stderr[-1000:]}"
    path = Path(found.group(1))
    assert path.exists()
    lab.logs.note(f"image {attr} = {path}")
    return path


# --- Guests -----------------------------------------------------------------------------------


def free_port() -> int:
    while True:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port != FORBIDDEN_PORT:
            return port


@dataclass
class Guest:
    lab: Env
    name: str
    port: int
    serial: Path
    proc: subprocess.Popen[bytes] | None = None

    def ssh(self, command: str, *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        argv = ["ssh", "-n", "-i", str(self.lab.ssh_key), *SSH_OPTIONS, "-p", str(self.port), "root@127.0.0.1", command]
        return self.lab.logs.run(f"{self.name}-ssh", argv, env=self.lab.env, timeout=timeout)

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def wait_ssh(self, seconds: int) -> float:
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            assert self.alive(), f"{self.name}: QEMU exited early; see {self.serial}"
            if self.ssh("true", timeout=30).returncode == 0:
                return time.monotonic() - started
            time.sleep(5)
        pytest.fail(f"{self.name}: no SSH after {seconds} s; see {self.serial}", pytrace=False)

    def stop(self) -> None:
        """Power the guest off, then kill the QEMU process group whatever happens."""
        if self.proc is None:
            return
        try:
            if self.alive():
                with contextlib.suppress(Exception):
                    self.ssh("poweroff", timeout=30)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    self.proc.wait(timeout=90)
        finally:
            if self.proc.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait()
            self.lab.logs.note(f"{self.name}: QEMU exit status {self.proc.returncode}")


@contextlib.contextmanager
def booted(guest: Guest, argv: list[str], env: dict[str, str]) -> Iterator[Guest]:
    run_log = guest.lab.logs.root / f"{guest.name}-run.log"
    guest.lab.logs.write(f"{guest.name}-argv.json", json.dumps({"argv": argv, "port": guest.port}, indent=1) + "\n")
    with run_log.open("wb") as out:
        guest.proc = subprocess.Popen(
            argv,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=limit_memlock,
        )
        try:
            yield guest
        finally:
            guest.stop()
            if guest.serial.exists():
                shutil.copyfile(guest.serial, guest.lab.logs.root / f"{guest.name}-serial.log")


def check_clean(guest: Guest, extra: str) -> dict[str, object]:
    """Wait for boot, read the system state, and return the facts. Assertions stay with the caller."""
    reach = guest.wait_ssh(480)
    state = guest.ssh("systemctl is-system-running --wait", timeout=420)
    failed = guest.ssh("systemctl --failed --no-legend --plain")
    target = guest.ssh("systemctl is-active multi-user.target")
    more = guest.ssh(extra)
    facts = {
        "ssh_seconds": round(reach, 1),
        "state": state.stdout.strip(),
        "failed_units": [line for line in failed.stdout.splitlines() if line.strip()],
        "multi_user": target.stdout.strip(),
        "extra": more.stdout,
        "extra_rc": more.returncode,
    }
    guest.lab.logs.write(f"{guest.name}-facts.json", json.dumps(facts, indent=1) + "\n")
    guest.lab.logs.note(f"{guest.name}: {json.dumps(facts)}")
    return facts


# --- Fixtures ---------------------------------------------------------------------------------


def test_build_vm_of_a_plain_machine_boots_with_no_failed_units(lab: Env):
    started = time.monotonic()
    image = build(lab, "machines.box.build.vm")
    built_s = time.monotonic() - started
    script = next((image / "bin").glob("run-*-vm"))

    disk = STATE / "vm" / "box.qcow2"
    port = free_port()
    serial = STATE / "vm" / "box-serial.log"
    env = dict(lab.env)
    env.update(
        NIX_DISK_IMAGE=str(disk),
        QEMU_OPTS=f"-display none -serial file:{serial} -monitor none",
        QEMU_NET_OPTS=f"hostfwd=tcp:127.0.0.1:{port}-:22",
        PATH=f"{lab.qemu}/bin:{env['PATH']}",
    )
    guest = Guest(lab, "vm", port, serial)
    with booted(guest, [str(script)], env) as running:
        facts = check_clean(running, "hostname; findmnt / -no SOURCE,FSTYPE")
    lab.logs.note(f"vm: build {built_s:.0f} s, ssh {facts['ssh_seconds']} s")
    assert facts["state"] == "running", facts
    assert facts["failed_units"] == [], facts
    assert facts["multi_user"] == "active", facts
    assert str(facts["extra"]).startswith("box\n"), facts


def test_build_iso_of_a_disko_machine_boots_with_no_failed_units(lab: Env):
    started = time.monotonic()
    image = build(lab, "machines.target.build.iso")
    built_s = time.monotonic() - started
    iso = next((image / "iso").glob("*.iso"))

    blank = STATE / "iso" / "target-disk.qcow2"
    create = [str(lab.qemu / "bin/qemu-img"), "create", "-q", "-f", "qcow2", str(blank), "4G"]
    made = lab.logs.run("qemu-img", create, env=lab.env, qemu=True)
    assert made.returncode == 0, made.stderr
    variables = STATE / "iso" / "target-vars.fd"
    shutil.copyfile(lab.ovmf / "FV/OVMF_VARS.fd", variables)
    variables.chmod(0o600)
    serial = STATE / "iso" / "target-serial.log"
    port = free_port()
    argv = [
        str(lab.qemu / "bin/qemu-system-x86_64"),
        *["-enable-kvm", "-cpu", "host", "-machine", "q35", "-m", "3072", "-smp", "4"],
        *["-drive", f"if=pflash,format=raw,readonly=on,file={lab.ovmf}/FV/OVMF_CODE.fd"],
        *["-drive", f"if=pflash,format=raw,file={variables}"],
        *["-drive", f"file={iso},media=cdrom,readonly=on,if=ide"],
        *["-drive", f"file={blank},if=none,id=target,format=qcow2"],
        *["-device", "virtio-blk-pci,drive=target,serial=vd-target"],
        *["-nic", f"user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:{port}-:22"],
        *["-display", "none", "-serial", f"file:{serial}", "-monitor", "none"],
    ]
    disk_path = "/dev/disk/by-id/virtio-vd-target"
    probe = "; ".join(
        [
            "hostname",
            "findmnt / -no FSTYPE",
            "test -d /sys/firmware/efi && echo EFI-boot",
            f"ls {disk_path}",
            f"lsblk -nr -o NAME,TYPE,FSTYPE {disk_path}",
        ]
    )
    guest = Guest(lab, "iso", port, serial)
    with booted(guest, argv, lab.env) as running:
        facts = check_clean(running, probe)
    lab.logs.note(f"iso: build {built_s:.0f} s, ssh {facts['ssh_seconds']} s")
    assert facts["state"] == "running", facts
    assert facts["failed_units"] == [], facts
    assert facts["multi_user"] == "active", facts
    lines = str(facts["extra"]).splitlines()
    assert lines[:3] == ["target", "tmpfs", "EFI-boot"], facts
    # The attached disk is present and still blank: one disk line, no partitions, no file system.
    assert lines[3] == "/dev/disk/by-id/virtio-vd-target", facts
    assert len(lines) == 5 and lines[4].split()[1] == "disk" and len(lines[4].split()) == 2, facts

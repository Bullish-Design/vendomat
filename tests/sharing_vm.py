"""Helpers for the two-VM sharing proof (`test_sharing_vm.py`).

A `Vm` starts the run script that Nix builds for one machine. It uses an image file and a TMPDIR
under one work directory. It never passes a host block device to QEMU. The harness reaches the
machine over SSH on a forwarded loopback port with a throwaway key. A second network card joins the
two machines (QEMU `dgram` netdev over loopback UDP).
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

DISK_BYTES = 1024 * 1024 * 1024
STARTUP_SETTLE_S = 4.0
MIN_UNALLOCATED_GIB = 15.0
MAX_METADATA_PERCENT = 90.0


def free_port(kind: int = socket.SOCK_STREAM) -> int:
    """Return a port that is free now on 127.0.0.1."""
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _gib(text: str) -> float:
    match = re.fullmatch(r"([\d.]+)(B|KiB|MiB|GiB|TiB)", text)
    assert match, text
    scale = {"B": 1 / 2**30, "KiB": 1 / 2**20, "MiB": 1 / 2**10, "GiB": 1.0, "TiB": 1024.0}
    return float(match.group(1)) * scale[match.group(2)]


def disk_guard(sleep: float = 60.0) -> str:
    """Return the btrfs numbers, or raise when the owner's limits are hit.

    Unallocated space under 15 GiB stops the run. Metadata use over 90 % stops the run when it
    stays over 90 % after one wait.
    """

    def read() -> tuple[float, float, str]:
        out = subprocess.run(["btrfs", "filesystem", "usage", "/"], capture_output=True, text=True).stdout
        free = re.search(r"Device unallocated:\s+(\S+)", out)
        meta = re.search(r"Metadata,\w+: Size:(\S+), Used:(\S+) \(([\d.]+)%\)", out)
        if free is None or meta is None:
            return 1e9, 0.0, "btrfs usage unavailable"
        line = f"unallocated {free.group(1)}; metadata {meta.group(2)} of {meta.group(1)} ({meta.group(3)} %)"
        return _gib(free.group(1)), float(meta.group(3)), line

    free, meta, line = read()
    if meta > MAX_METADATA_PERCENT:
        time.sleep(sleep)
        free, meta, line = read()
    if free < MIN_UNALLOCATED_GIB or meta > MAX_METADATA_PERCENT:
        raise RuntimeError(f"disk guard: {line}")
    return line


@dataclass
class Logger:
    """Append every command and result to files outside the repository."""

    directory: Path
    started: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)

    def command(self, who: str, cmd: str, rc: int, out: str, seconds: float) -> None:
        with (self.directory / "commands.log").open("a") as handle:
            handle.write(f"[{who}] $ {cmd}\n(rc={rc}, {seconds:.1f}s)\n{out}\n")

    def result(self, text: str) -> None:
        with (self.directory / "results.log").open("a") as handle:
            handle.write(f"{time.time() - self.started:7.1f}s {text}\n")


class Vm:
    """One machine, started from its Nix-built run script."""

    def __init__(
        self,
        name: str,
        run_script: Path,
        work: Path,
        mac: str,
        ssh_key: Path,
        ssh: Path,
        mkfs: Path,
        log: Logger,
        udp_local: int,
        udp_remote: int,
    ):
        self.name = name
        self.run_script = run_script
        self.work = work
        self.mac = mac
        self.ssh_key = ssh_key
        self.ssh_bin = ssh
        self.mkfs = mkfs
        self.log = log
        self.ssh_port = free_port()
        self.udp_local = udp_local
        self.udp_remote = udp_remote
        self.process: subprocess.Popen[bytes] | None = None
        self.unit = ""
        self.sysenv: dict[str, str] = {}
        self.extra_qemu = ""

    def start(self) -> None:
        tmp = self.work / f"tmp-{self.name}"
        tmp.mkdir(parents=True, exist_ok=True)
        # Make the root disk here. The run script makes a qcow2 image with qemu-img, which fails
        # to start io_uring inside the Testee containment. A raw ext4 image file does the same job.
        image = self.work / f"{self.name}.img"
        with image.open("wb") as handle:
            handle.truncate(DISK_BYTES)
        subprocess.run([str(self.mkfs), "-q", "-F", "-L", "nixos", str(image)], check=True, capture_output=True)
        qemu_opts = (
            f"-netdev dgram,id=lan,local.type=inet,local.host=127.0.0.1,local.port={self.udp_local},"
            f"remote.type=inet,remote.host=127.0.0.1,remote.port={self.udp_remote} "
            f"-device virtio-net-pci,netdev=lan,mac={self.mac} {self.extra_qemu}"
        ).strip()
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "TMPDIR": str(tmp),
            "USE_TMPDIR": "1",
            "NIX_DISK_IMAGE": str(image),
            "QEMU_NET_OPTS": f"hostfwd=tcp:127.0.0.1:{self.ssh_port}-:22",
            "QEMU_OPTS": qemu_opts,
        }
        # QEMU 11 makes an io_uring ring at start, and it stops when the kernel refuses the ring.
        # The kernel counts the ring against the memory-lock limit of the whole user (8 MiB on
        # this host), and other processes of the user can use all of it ("Cannot allocate
        # memory"). So run the machine in a transient user unit whose system-call filter answers
        # ENOSYS to io_uring_setup. QEMU then falls back to epoll. The filter needs no privilege.
        serial_path = self.work / f"{self.name}-serial.log"
        self.unit = f"vendomat-sharing-{self.name}-{secrets.token_hex(4)}"
        runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        self.sysenv = {**os.environ, "XDG_RUNTIME_DIR": runtime}
        argv = [
            "systemd-run", "--user", "--wait", "--collect", "--quiet",
            f"--unit={self.unit}",
            "-p", "SystemCallFilter=~io_uring_setup:ENOSYS",
            "-p", f"WorkingDirectory={self.work}",
            "-p", f"StandardOutput=append:{serial_path}",
            "-p", f"StandardError=append:{serial_path}",
            *[f"--setenv={key}={value}" for key, value in env.items()],
            str(self.run_script),
        ]  # fmt: skip
        serial_path.touch()
        with (self.work / f"{self.name}-systemd-run.log").open("wb") as launcher:
            self.process = subprocess.Popen(
                argv, env=self.sysenv, stdin=subprocess.DEVNULL, stdout=launcher, stderr=subprocess.STDOUT
            )
        time.sleep(STARTUP_SETTLE_S)

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _ssh_argv(self) -> list[str]:
        return [
            str(self.ssh_bin),
            "-F", "/dev/null",
            "-i", str(self.ssh_key),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", "ConnectTimeout=5",
            "-p", str(self.ssh_port),
            "root@127.0.0.1",
        ]  # fmt: skip

    def run(self, cmd: str, *, stdin: str | None = None, timeout: float = 300.0) -> tuple[int, str]:
        """Run a shell command in the machine. Return the exit code and the merged output."""
        began = time.time()
        proc = subprocess.run(
            [*self._ssh_argv(), cmd],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=None if stdin is not None else subprocess.DEVNULL,
        )
        out = proc.stdout + proc.stderr
        self.log.command(self.name, cmd, proc.returncode, out, time.time() - began)
        return proc.returncode, out

    def ok(self, cmd: str, *, stdin: str | None = None, timeout: float = 300.0) -> str:
        rc, out = self.run(cmd, stdin=stdin, timeout=timeout)
        assert rc == 0, f"[{self.name}] failed (rc={rc}): {cmd}\n{out}"
        return out

    def wait_ssh(self, timeout: float = 240.0) -> float:
        began = time.time()
        while time.time() - began < timeout:
            if not self.alive():
                tail = ""
                for suffix in ("systemd-run", "serial"):
                    path = self.work / f"{self.name}-{suffix}.log"
                    tail += f"--- {suffix}\n" + (path.read_text(errors="replace")[-1500:] if path.exists() else "")
                raise AssertionError(f"{self.name}: QEMU exited early:\n{tail}")
            try:
                rc, _ = self.run("true", timeout=15)
            except subprocess.TimeoutExpired:
                continue
            if rc == 0:
                return time.time() - began
            time.sleep(1)
        raise TimeoutError(f"{self.name}: no SSH after {timeout} s")

    def wait_unit(self, unit: str, timeout: float = 120.0) -> None:
        began = time.time()
        while time.time() - began < timeout:
            rc, out = self.run(f"systemctl is-active {unit}")
            if rc == 0:
                return
            time.sleep(1)
        raise TimeoutError(f"{self.name}: {unit} not active: {out}")

    def power_off(self, timeout: float = 90.0) -> None:
        if self.process is None:
            return
        if self.alive():
            try:
                self.run("poweroff", timeout=20)
            except subprocess.TimeoutExpired:
                pass
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.kill()

    def kill(self) -> None:
        if self.process is None or not self.unit:
            return
        for _ in range(3):
            subprocess.run(["systemctl", "--user", "stop", self.unit], env=self.sysenv, capture_output=True)
            if self.process.poll() is not None:
                return
            try:
                self.process.wait(timeout=30)
                return
            except subprocess.TimeoutExpired:
                continue
        self.process.kill()
        self.process.wait()


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)

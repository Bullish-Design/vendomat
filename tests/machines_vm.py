"""The harness of the opt-in check `machines-vm` (project 24, S4).

It builds one NixOS machine as an EFI disk image, serves a local binary cache to it, boots it in
QEMU, and runs shell commands in it over SSH. The machine has no network. The tools come from the
pinned nixpkgs of `flake.lock` (see `tests/fixtures/machines/tools.nix`). Nothing here touches a
host block device or the host's system profile: the machine is an image file under
`VENDOMAT_MACHINES_VM_DIR`.
"""

from __future__ import annotations

import functools
import http.server
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "machines"
#: A limit from the safety rules. The root file system needs this much unallocated space.
MIN_UNALLOCATED_GIB = 15.0
MAX_METADATA_PERCENT = 90.0


def disk_state() -> tuple[float, float]:
    """``btrfs filesystem usage /``: unallocated GiB and metadata use in percent."""

    text = subprocess.run(["btrfs", "filesystem", "usage", "/"], capture_output=True, text=True).stdout
    unallocated = re.search(r"Device unallocated:\s+([\d.]+)(GiB|TiB|MiB)", text)
    metadata = re.search(r"Metadata,\w+: Size:[\d.]+\w+, Used:[\d.]+\w+ \(([\d.]+)%\)", text)
    if not unallocated or not metadata:
        raise RuntimeError("cannot read `btrfs filesystem usage /`")
    scale = {"MiB": 1 / 1024, "GiB": 1.0, "TiB": 1024.0}[unallocated.group(2)]
    return float(unallocated.group(1)) * scale, float(metadata.group(1))


def disk_guard(wait: Callable[[float], None] = time.sleep) -> str:
    """Return a one-line reading, or raise when a limit is hit. Metadata gets one 60 s wait."""

    unallocated, metadata = disk_state()
    if metadata > MAX_METADATA_PERCENT and unallocated >= 10.0:
        wait(60)
        unallocated, metadata = disk_state()
    if unallocated < MIN_UNALLOCATED_GIB or metadata > MAX_METADATA_PERCENT:
        raise RuntimeError(f"stop: unallocated {unallocated:.2f} GiB, metadata {metadata:.1f} %")
    return f"unallocated {unallocated:.2f} GiB, metadata {metadata:.1f} %"


def disk_line() -> str:
    """The same reading as ``disk_guard``, without the limits. For the end of a run."""

    unallocated, metadata = disk_state()
    return f"unallocated {unallocated:.2f} GiB, metadata {metadata:.1f} %"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Logger:
    """Commands and results go to two files under one directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def command(self, who: str, cmd: str, rc: int, out: str, seconds: float) -> None:
        with open(self.directory / "commands.log", "a") as handle:
            handle.write(f"$ [{who}] {cmd}\n{out.rstrip()}\n(rc={rc}, {seconds:.1f} s)\n\n")

    def result(self, text: str) -> None:
        print(text, flush=True)
        with open(self.directory / "results.log", "a") as handle:
            handle.write(text + "\n")


class CacheServer:
    """A binary cache over HTTP, on a directory made by `nix copy --to file://`. It counts downloads."""

    def __init__(self, directory: Path, port: int) -> None:
        self.nar_downloads = 0
        self.narinfo_hits = 0
        self.misses = 0
        outer = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = self.translate_path(self.path)
                if not os.path.isfile(path):
                    outer.misses += 1
                elif self.path.startswith("/nar/"):
                    outer.nar_downloads += 1
                elif self.path.endswith(".narinfo"):
                    outer.narinfo_hits += 1
                super().do_GET()

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        handler = functools.partial(Handler, directory=str(directory))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@dataclass
class Vm:
    """One QEMU machine from an image file, with SSH on a loopback port."""

    work: Path
    qemu: Path
    ovmf: Path
    ssh: Path
    key: Path
    ssh_port: int
    cache_port: int
    nc: Path
    log: Logger
    memory_mb: int = 3072
    process: subprocess.Popen[bytes] | None = None
    unit: str = ""
    sysenv: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)

    def start(self) -> None:
        netdev = (
            f"user,id=n0,restrict=on,hostfwd=tcp:127.0.0.1:{self.ssh_port}-:22,"
            f"guestfwd=tcp:10.0.2.100:5000-cmd:{self.nc} 127.0.0.1 {self.cache_port}"
        )
        qemu = [
            str(self.qemu), "-enable-kvm", "-cpu", "host", "-machine", "q35", "-m", str(self.memory_mb), "-smp", "2",
            "-drive", f"if=pflash,format=raw,readonly=on,file={self.ovmf}/OVMF_CODE.fd",
            "-drive", f"if=pflash,format=raw,file={self.work}/vars.fd",
            "-drive", f"file={self.work}/box.qcow2,if=virtio,format=qcow2,aio=threads",
            "-netdev", netdev, "-device", "virtio-net-pci,netdev=n0",
            "-display", "none", "-serial", "stdio", "-monitor", "none",
        ]  # fmt: skip
        # QEMU 11 makes an io_uring ring at start. On this host the kernel refuses the ring ("Cannot
        # allocate memory": the memory-lock budget of the user is used up). So run QEMU in a transient
        # user unit whose system-call filter answers ENOSYS to io_uring_setup. QEMU falls back to
        # epoll. The filter needs no privilege and changes no host limit.
        serial = self.work / "serial.log"
        serial.touch()
        self.unit = f"vendomat-machines-{secrets.token_hex(4)}"
        runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        self.sysenv = {**os.environ, "XDG_RUNTIME_DIR": runtime}
        argv = [
            "systemd-run", "--user", "--wait", "--collect", "--quiet", f"--unit={self.unit}",
            "-p", "SystemCallFilter=~io_uring_setup:ENOSYS",
            "-p", f"WorkingDirectory={self.work}",
            "-p", f"StandardOutput=append:{serial}", "-p", f"StandardError=append:{serial}",
            *qemu,
        ]  # fmt: skip
        self.log.command("host", " ".join(argv), 0, "", 0.0)
        with (self.work / "systemd-run.log").open("wb") as launcher:
            self.process = subprocess.Popen(
                argv, env=self.sysenv, stdin=subprocess.DEVNULL, stdout=launcher, stderr=subprocess.STDOUT
            )
        time.sleep(4.0)

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _ssh_argv(self, user: str, cmd: str) -> list[str]:
        return [
            str(self.ssh),
            "-F",
            "/dev/null",
            "-i",
            str(self.key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-o",
            "ConnectTimeout=5",
            "-p",
            str(self.ssh_port),
            f"{user}@127.0.0.1",
            cmd,
        ]

    def run(self, user: str, cmd: str, *, stdin: str | bytes | None = None, timeout: float = 600) -> tuple[int, str]:
        """Run a command in the machine. Return the exit status and the output (both streams)."""

        began = time.time()
        data = stdin.encode() if isinstance(stdin, str) else stdin
        try:
            done = subprocess.run(
                self._ssh_argv(user, cmd),
                input=data if data is not None else b"",
                capture_output=True,
                timeout=timeout,
                env=self.env or None,
            )
            rc, out = done.returncode, done.stdout.decode(errors="replace") + done.stderr.decode(errors="replace")
        except subprocess.TimeoutExpired:
            rc, out = 124, f"timed out after {timeout} s"
        self.log.command(user, cmd, rc, out, time.time() - began)
        return rc, out

    def ok(self, user: str, cmd: str, **kw) -> str:
        rc, out = self.run(user, cmd, **kw)
        assert rc == 0, f"{cmd!r} in the machine exited {rc}:\n{out[-3000:]}"
        return out

    def wait_ssh(self, timeout: float = 300) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.alive():
                tail = (self.work / "serial.log").read_text(errors="replace")[-1500:]
                raise RuntimeError(f"QEMU exited early:\n{tail}")
            rc, out = self.run("root", "systemctl is-system-running --wait", timeout=120)
            if rc == 0 or "running" in out or "degraded" in out:
                return
            time.sleep(3)
        raise RuntimeError("the machine did not come up over SSH")

    def boot_id(self) -> str:
        return self.ok("root", "cat /proc/sys/kernel/random/boot_id").strip()

    def reboot(self, timeout: float = 400) -> None:
        """Restart the guest inside the same QEMU process. Wait for a new boot."""

        before = self.boot_id()
        self.run("root", "systemctl reboot", timeout=30)
        deadline = time.time() + timeout
        time.sleep(5)
        while time.time() < deadline:
            rc, out = self.run("root", "cat /proc/sys/kernel/random/boot_id", timeout=20)
            if rc == 0 and out.strip() and out.strip() != before:
                self.wait_ssh()
                return
            time.sleep(4)
        raise RuntimeError("the machine did not reboot")

    def power_off(self, timeout: float = 90.0) -> None:
        if self.process is not None and self.alive():
            self.run("root", "systemctl poweroff", timeout=20)
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.kill()

    def kill(self) -> None:
        if self.process is None or not self.unit:
            return
        for _ in range(3):
            subprocess.run(["systemctl", "--user", "stop", self.unit], env=self.sysenv, capture_output=True)
            try:
                self.process.wait(timeout=30)
                return
            except subprocess.TimeoutExpired:
                continue
        self.process.kill()
        self.process.wait()


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)

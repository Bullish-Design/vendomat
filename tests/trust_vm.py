"""The harness of the opt-in check `machines-trust` (R61, R65).

It reuses the helpers of `machines_vm.py` (read only) and adds one thing: a machine that has a
second network card on a private link. The link joins two QEMU processes through UDP on the loopback
address of the host. It is no host bridge, no host interface, and no host block device.
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import time
from dataclasses import dataclass

from machines_vm import Vm


def udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class LinkVm(Vm):
    """A `Vm` with a second card. The two ends of the link name each other's UDP port."""

    mac: str = ""
    udp_local: int = 0
    udp_remote: int = 0

    def start(self) -> None:
        netdev = (
            f"user,id=n0,restrict=on,hostfwd=tcp:127.0.0.1:{self.ssh_port}-:22,"
            f"guestfwd=tcp:10.0.2.100:5000-cmd:{self.nc} 127.0.0.1 {self.cache_port}"
        )
        link = (
            f"dgram,id=lan,local.type=inet,local.host=127.0.0.1,local.port={self.udp_local},"
            f"remote.type=inet,remote.host=127.0.0.1,remote.port={self.udp_remote}"
        )
        qemu = [
            str(self.qemu), "-enable-kvm", "-cpu", "host", "-machine", "q35", "-m", str(self.memory_mb), "-smp", "2",
            "-drive", f"if=pflash,format=raw,readonly=on,file={self.ovmf}/OVMF_CODE.fd",
            "-drive", f"if=pflash,format=raw,file={self.work}/vars.fd",
            "-drive", f"file={self.work}/box.qcow2,if=virtio,format=qcow2,aio=threads",
            "-netdev", netdev, "-device", "virtio-net-pci,netdev=n0",
            "-netdev", link, "-device", f"virtio-net-pci,netdev=lan,mac={self.mac}",
            "-display", "none", "-serial", "stdio", "-monitor", "none",
        ]  # fmt: skip
        # The same io_uring workaround as `Vm.start`: a transient user unit whose system-call filter
        # answers ENOSYS to io_uring_setup.
        serial = self.work / "serial.log"
        serial.touch()
        self.unit = f"vendomat-trust-{secrets.token_hex(4)}"
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

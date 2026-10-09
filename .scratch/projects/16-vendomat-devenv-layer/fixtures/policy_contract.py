#!/usr/bin/env python3
"""Research-only predicate fixture, NOT a safety gate for live systems."""
from __future__ import annotations
import json
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, model_validator


class HostMode(StrEnum):
    FRESH_INSTALL = "fresh-install"
    ADOPT_EXISTING = "adopt-existing"


class DiskRole(StrEnum):
    INSTALL_TARGET = "install-target"
    KEEP = "keep"
    EXISTING_SYSTEM = "existing-system"


class Disk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    by_id: str
    role: DiskRole
    model: str | None = None
    serial: str | None = None
    size_bytes: int | None = None

    @model_validator(mode="after")
    def check_id(self) -> "Disk":
        if not self.by_id.startswith("/dev/disk/by-id/"):
            raise ValueError("disk must use by-id")
        return self


class Host(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: HostMode
    disks: dict[str, Disk]
    disko_devices: dict[str, str] = {}
    mount_devices: dict[str, str] = {}

    @model_validator(mode="after")
    def check_policy(self) -> "Host":
        identities = [d.by_id for d in self.disks.values()]
        if len(identities) != len(set(identities)):
            raise ValueError("one physical disk cannot have conflicting inventory roles")
        targets = {d.by_id for d in self.disks.values() if d.role == DiskRole.INSTALL_TARGET}
        system_disks = [d for d in self.disks.values() if d.role == DiskRole.EXISTING_SYSTEM]
        disko_paths = set(self.disko_devices.values())
        if self.mode == HostMode.ADOPT_EXISTING:
            if not system_disks or targets or disko_paths:
                raise ValueError("adopted machine must have existing-system, no install-target, no disko")
        elif not targets or disko_paths != targets:
            raise ValueError("fresh install must declare exactly the protected install targets in disko")
        for mount, path in self.mount_devices.items():
            if not path.startswith(("/dev/disk/by-uuid/", "/dev/disk/by-partuuid/")):
                raise ValueError(f"unstable mount identifier at {mount}: {path}")
        return self


def allowed(host: Host, action: str, runtime_blank: bool = False) -> bool:
    """Conservative intended policy; upstream CLI does not enforce this."""
    if action == "install":
        return host.mode == HostMode.FRESH_INSTALL and runtime_blank
    if action in {"info", "check", "build", "plan", "status", "apply", "deploy", "rollback"}:
        return True
    return False


def main() -> None:
    original = {"mode":"adopt-existing","disks":{"system":{"by_id":"/dev/disk/by-id/virtio-ADOPT01","role":"existing-system"}},"mount_devices":{"/":"/dev/disk/by-uuid/22222222-2222-2222-2222-222222222222"}}
    fresh = {"mode":"fresh-install","disks":{"new":{"by_id":"/dev/disk/by-id/virtio-NEW01","role":"install-target"},"old":{"by_id":"/dev/disk/by-id/virtio-OLD01","role":"keep"}},"disko_devices":{"new":"/dev/disk/by-id/virtio-NEW01"}}
    tests = []
    def case(name: str, input_data: dict, action: str | None, blank: bool, expected: bool) -> None:
        try:
            target = Host.model_validate(input_data)
            actual = allowed(target, action, blank) if action else True
        except ValueError:
            actual = False
        tests.append({"name":name,"expected":expected,"actual":actual,"pass":actual==expected})
    case("adoption-plan",original,"plan",False,True)
    case("adoption-deploy",original,"deploy",False,True)
    case("adoption-install-denied",original,"install",True,False)
    case("fresh-install-blank",fresh,"install",True,True)
    case("fresh-install-signed",fresh,"install",False,False)
    case("fresh-keep-device-protected",fresh|{"disko_devices":{"old":"/dev/disk/by-id/virtio-OLD01"}},None,False,False)
    case("adoption-disko-denied",original|{"disko_devices":{"system":"/dev/disk/by-id/virtio-ADOPT01"}},None,False,False)
    case("adoption-install-role-denied",original|{"disks":{"system":{"by_id":"/dev/disk/by-id/virtio-ADOPT01","role":"install-target"}}},None,False,False)
    case("adoption-kernel-mount-denied",original|{"mount_devices":{"/":"/dev/nvme0n1p2"}},None,False,False)
    case("fresh-no-target-denied",fresh|{"disko_devices":{}},None,False,False)
    case("duplicate-disk-role-denied",fresh|{"disks":{"new":{"by_id":"/dev/disk/by-id/virtio-NEW01","role":"install-target"},"old":{"by_id":"/dev/disk/by-id/virtio-NEW01","role":"keep"}}},None,False,False)
    print(json.dumps({"kind":"synthetic policy model; NOT a real devenv or VM test","cases":tests,"passed":sum(t["pass"] for t in tests),"total":len(tests)},indent=2))
    if not all(t["pass"] for t in tests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

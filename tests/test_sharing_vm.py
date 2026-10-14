"""The sharing module on two cache machines and an unmarked probe (R39, VMT-127, VMT-128).

Opt-in: `testee verify opt:sharing-vm` (it sets VENDOMAT_SHARING_VM=1). The proof runs three NixOS VMs
(`alpha`, `beta`, and `gamma`) built from the pinned nixpkgs of `flake.lock` and `devenv/sharing.nix`:

1. `alpha` makes its signing key at first boot, publishes the public key, and serves a path only
   on the marked trusted link. Its untrusted link and beta's unmarked gamma probe stay closed.
2. The harness writes the public key as `.machines/alpha/cache-key.pub` in a scratch workspace.
   The fixture reads that file and gives `beta` a peer entry. Before it, `beta` has none.
3. `beta` sets `serve = false`. It runs no Harmonia and opens no port. It substitutes the path
   from `alpha` and checks the signature. It refuses a path when the key is not trusted.
4. `gamma` serves on loopback but has no trusted interface marker, so beta cannot reach it.
5. With `alpha` off, `beta` still builds, because `fallback = true`. The same step fails without it.
6. The secret key is in no store path.

The VMs use image files under VENDOMAT_SHARING_VM_DIR (default /mnt/shared/vendomat-p21/s3/sharing).
The harness deletes them at the end. Raw logs go to VENDOMAT_SHARING_VM_LOGS. QEMU comes from the
pinned nixpkgs, through the run script that Nix builds. The VMs boot by direct kernel boot, so no
OVMF is needed.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from sharing_vm import Logger, Vm, disk_guard, free_port, remove_tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sharing" / "default.nix"
ENABLED = os.environ.get("VENDOMAT_SHARING_VM") == "1"
BASE = Path(os.environ.get("VENDOMAT_SHARING_VM_DIR", "/mnt/shared/vendomat-p21/s3/sharing"))
LOGS = Path(os.environ.get("VENDOMAT_SHARING_VM_LOGS", "/tmp/vendomat-sharing-vm-logs"))
KEEP = os.environ.get("VENDOMAT_SHARING_VM_KEEP") == "1"

pytestmark = pytest.mark.skipif(not ENABLED, reason="run through testee verify sharing-vm")

DGRAM = socket.SOCK_DGRAM
LAN_ALPHA = "192.168.77.1"
LAN_BETA = "192.168.77.2"
UNTRUSTED_ALPHA = "192.168.78.1"
CACHE_NIXOS_KEY = "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
#: A bound for the fallback build with `alpha` off. The measured time is far below it.
FALLBACK_LIMIT_S = 60.0


@dataclass
class World:
    work: Path
    workspace: Path
    log: Logger
    tools: Path
    bash: str
    ssh_key: Path
    ssh_pub: str
    udp: tuple[int, int] = (0, 0)
    untrusted_udp: tuple[int, int] = (0, 0)
    gamma_udp: tuple[int, int] = (0, 0)
    alpha: Vm | None = None
    beta: Vm | None = None
    extra_servers: list[Vm] = field(default_factory=list)
    alpha_path: str = ""
    alpha_payload: str = ""

    def nix_build(self, attr: str, link: str) -> Path:
        out = self.work / link
        self.nix(["nix-build", str(FIXTURE), "-A", attr, "-o", str(out)])
        return out

    def nix(self, argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [*argv, "--argstr", "workspace", str(self.workspace), "--argstr", "sshPublicKey", self.ssh_pub]
        began = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=self.work, env=_env(self.work))
        self.log.command("host", " ".join(cmd), proc.returncode, proc.stdout + proc.stderr, time.time() - began)
        if check:
            assert proc.returncode == 0, proc.stderr[-3000:]
        return proc

    def facts(self) -> dict:
        proc = self.nix(["nix-instantiate", "--eval", "--strict", "--json", str(FIXTURE), "-A", "facts"])
        return json.loads(proc.stdout)

    def expr(self, name: str, payload: str) -> str:
        """A unique derivation. Its builder is the pinned bash, which both machines hold."""
        return (
            f'let bash = builtins.storePath "{self.bash}"; in derivation {{\n'
            f'  name = "sharing-{name}"; system = "x86_64-linux"; builder = "${{bash}}/bin/bash";\n'
            f'  args = [ "-c" "echo {payload} > $out" ];\n}}\n'
        )

    def instantiate(self, vm: Vm, name: str, payload: str) -> tuple[str, str]:
        """Write the expression into the machine. Return the .drv path and the output path."""
        vm.ok(f"cat > /tmp/{name}.nix", stdin=self.expr(name, payload))
        drv = vm.ok(f"nix-instantiate /tmp/{name}.nix 2>/dev/null").strip()
        out = vm.ok(f"nix-store -q --outputs {drv}").strip()
        return drv, out


def _env(work: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "NIX_REMOTE", "NIX_SSL_CERT_FILE"}}
    env["TMPDIR"] = str(work)
    return env


@pytest.fixture(scope="module")
def world() -> Iterator[World]:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log = Logger(LOGS / stamp if "VENDOMAT_SHARING_VM_LOGS" not in os.environ else LOGS)
    log.result(f"disk before: {disk_guard()}")
    work = BASE / f"run-{stamp}"
    work.mkdir(parents=True)
    workspace = work / "workspace"
    (workspace / ".machines").mkdir(parents=True)
    w = World(
        work,
        workspace,
        log,
        work / "tools",
        "",
        work / "ssh-key",
        "",
        (free_port(DGRAM), free_port(DGRAM)),
        (free_port(DGRAM), free_port(DGRAM)),
        (free_port(DGRAM), free_port(DGRAM)),
    )
    w.nix(["nix-build", str(FIXTURE), "-A", "tools", "-o", str(w.tools)])
    keygen = [str(w.tools / "bin" / "ssh-keygen"), "-q", "-t", "ed25519", "-N", "", "-f", str(w.ssh_key)]
    subprocess.run(keygen, check=True)
    w.ssh_pub = (work / "ssh-key.pub").read_text().strip()
    w.bash = w.nix(["nix-build", str(FIXTURE), "-A", "bash", "--no-out-link"]).stdout.strip()
    try:
        yield w
    finally:
        for vm in (w.beta, w.alpha, *w.extra_servers):
            if vm is not None:
                vm.power_off()
                vm.kill()
        for serial in [*work.glob("*-serial.log"), *work.glob("*-systemd-run.log")]:
            shutil.copy(serial, log.directory / serial.name)
        if not KEEP:
            remove_tree(work)
        log.result(f"disk after: {disk_guard()}")


def _vm(w: World, name: str, mac: str, local: int, remote: int, *, attr: str | None = None) -> Vm:
    """Build the machine and return it, not started. `local` and `remote` are the link ports."""
    attr = attr or f"{name}.vm"
    run_script = next((w.nix_build(attr, f"{name}-vm") / "bin").glob("run-*-vm"))
    vm = Vm(
        name,
        run_script,
        w.work,
        mac,
        w.ssh_key,
        w.tools / "bin" / "ssh",
        w.tools / "bin" / "mkfs.ext4",
        w.log,
        local,
        remote,
    )
    if name != "gamma":
        untrusted_local, untrusted_remote = w.untrusted_udp
        suffix = "01" if name == "alpha" else "02"
        vm.extra_qemu = (
            f"-netdev dgram,id=untrusted,local.type=inet,local.host=127.0.0.1,local.port={untrusted_local},"
            f"remote.type=inet,remote.host=127.0.0.1,remote.port={untrusted_remote} "
            f"-device virtio-net-pci,netdev=untrusted,mac=52:54:00:78:00:{suffix}"
        )
    if name == "beta":
        local, remote = w.gamma_udp
        vm.extra_qemu += (
            f" -netdev dgram,id=gamma,local.type=inet,local.host=127.0.0.1,local.port={local},"
            f"remote.type=inet,remote.host=127.0.0.1,remote.port={remote} "
            "-device virtio-net-pci,netdev=gamma,mac=52:54:00:79:00:02"
        )
    return vm


def test_a_key_that_is_not_committed_gives_no_peer_entry(world: World) -> None:
    facts = world.facts()
    assert facts["beta"]["peers"] == []
    assert facts["beta"]["extraSubstituters"] == []
    assert facts["alpha"]["peers"] == []
    # serve defaults to on; serve = false has no Harmonia and no key unit.
    assert facts["alpha"]["harmonia"] is True
    assert facts["beta"]["harmonia"] is False
    assert facts["beta"]["keyUnit"] is False
    # The attribute-set form of `peers` reaches the same client settings as the list form.
    attrs = facts["attrsForm"]
    assert attrs["extraSubstituters"] == ["http://one:5000"]
    assert attrs["extraKeys"] == ["one:AAAA"]
    assert attrs["fallback"] is True
    assert attrs["connectTimeout"] == 5
    # A serving machine with the firewall off gets the warning (eval only; the fixture boots no such VM).
    [warning] = facts["noFirewall"]["warnings"]
    assert "networking.firewall.enable is false" in warning


def test_a_malformed_public_key_is_refused(world: World, tmp_path: Path) -> None:
    bad = tmp_path / "bad-ws"
    (bad / ".machines" / "alpha").mkdir(parents=True)
    (bad / ".machines" / "alpha" / "cache-key.pub").write_text("not a key\n")
    cmd = ["nix-instantiate", str(FIXTURE), "-A", "beta.vm", "--argstr", "workspace", str(bad)]
    cmd += ["--argstr", "sshPublicKey", world.ssh_pub]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=_env(world.work))
    assert proc.returncode != 0
    assert "must read NAME:BASE64" in proc.stderr


@pytest.fixture(scope="module")
def alpha(world: World) -> Vm:
    log_line = disk_guard()
    world.log.result(f"disk before alpha: {log_line}")
    vm = _vm(world, "alpha", "52:54:00:77:00:01", world.udp[0], world.udp[1])
    world.alpha = vm
    began = time.time()
    vm.start()
    vm.wait_ssh()
    vm.wait_unit("multi-user.target")
    world.log.result(f"alpha reached multi-user in {time.time() - began:.1f} s")
    vm.run("journalctl -b -u vendomat-cache-key -u harmonia --no-pager; systemctl --failed --no-pager")
    return vm


def test_alpha_makes_its_key_at_first_boot(world: World, alpha: Vm) -> None:
    assert alpha.ok("systemctl show -p Result --value vendomat-cache-key.service").strip() == "success"
    assert alpha.ok("stat -c '%a %U:%G' /var/lib/vendomat/cache-key/secret").strip() == "600 root:root"
    assert alpha.ok("stat -c '%a %U:%G' /var/lib/vendomat/cache-key").strip() == "700 root:root"
    assert alpha.ok("stat -c '%a' /var/lib/vendomat/cache-key.pub").strip() == "644"
    pub = alpha.ok("cat /var/lib/vendomat/cache-key.pub").strip()
    secret_name = alpha.ok("cut -d: -f1 /var/lib/vendomat/cache-key/secret").strip()
    assert pub.startswith("alpha:") and secret_name == "alpha", (pub, secret_name)
    # The key unit is idempotent: a second run keeps the same key.
    before = alpha.ok("sha256sum /var/lib/vendomat/cache-key/secret /var/lib/vendomat/cache-key.pub")
    alpha.ok("systemctl restart vendomat-cache-key.service")
    assert alpha.ok("sha256sum /var/lib/vendomat/cache-key/secret /var/lib/vendomat/cache-key.pub") == before
    world.log.result(f"alpha key unit made {pub}")
    # Harmonia runs, as an unprivileged user, and serves over the network.
    alpha.wait_unit("harmonia.socket")
    assert "StoreDir: /nix/store" in alpha.ok("curl -s -m 10 http://127.0.0.1:5000/nix-cache-info")
    assert alpha.ok("systemctl show -p User --value harmonia.service").strip() != "root"


def test_the_secret_key_is_in_no_store_path(world: World, alpha: Vm) -> None:
    secret = alpha.ok("cut -d: -f2 /var/lib/vendomat/cache-key/secret").strip()
    assert len(secret) > 40
    closure = "nix-store -qR /run/current-system"
    # Control: the same search finds the key where it lives.
    found = alpha.ok(f"grep -rlF -- '{secret}' /var/lib/vendomat; true")
    assert "/var/lib/vendomat/cache-key/secret" in found
    in_closure = alpha.ok(f"{closure} | xargs grep -rlF -- '{secret}' 2>/dev/null; true")
    in_rw_store = alpha.ok(f"grep -rlF -- '{secret}' /nix/.rw-store 2>/dev/null; true")
    assert in_closure.strip() == "", in_closure
    assert in_rw_store.strip() == "", in_rw_store
    # The Harmonia unit names the key path. It does not hold the key.
    unit = alpha.ok("systemctl cat harmonia.service")
    assert "/var/lib/vendomat/cache-key/secret" in unit and secret not in unit
    world.log.result("secret key found in the closure and the writable store: none")


def test_alpha_serves_a_path_that_it_built(world: World, alpha: Vm) -> None:
    payload = secrets.token_hex(8)
    drv, out = world.instantiate(alpha, "p1", payload)
    alpha.ok(f"nix-store -r {drv}")
    assert alpha.ok(f"cat {out}").strip() == payload
    name = out.split("/")[-1]
    narinfo = alpha.ok(f"curl -s -m 10 http://127.0.0.1:5000/{name.split('-')[0]}.narinfo")
    assert f"StorePath: {out}" in narinfo
    assert "Sig: alpha:" in narinfo
    world.alpha_path = out
    world.alpha_payload = payload


@pytest.fixture(scope="module")
def beta(world: World, alpha: Vm) -> Vm:
    """Publish alpha's key in the workspace, then boot beta, which the fixture gives a peer."""
    pub = alpha.ok("cat /var/lib/vendomat/cache-key.pub").strip()
    key_file = world.workspace / ".machines" / "alpha" / "cache-key.pub"
    key_file.parent.mkdir(parents=True)
    key_file.write_text(pub + "\n")
    facts = world.facts()["beta"]
    assert facts["extraSubstituters"] == [f"http://{LAN_ALPHA}:5000"]
    assert facts["peers"] == [{"url": f"http://{LAN_ALPHA}:5000", "publicKey": pub}]
    world.log.result(f"disk before beta: {disk_guard()}")
    vm = _vm(world, "beta", "52:54:00:77:00:02", world.udp[1], world.udp[0])
    world.beta = vm
    began = time.time()
    vm.start()
    vm.wait_ssh()
    vm.wait_unit("multi-user.target")
    world.log.result(f"beta reached multi-user in {time.time() - began:.1f} s")
    return vm


def test_serve_false_runs_no_harmonia_and_opens_no_port(world: World, alpha: Vm, beta: Vm) -> None:
    assert beta.run("systemctl cat harmonia.service")[0] != 0
    assert beta.run("systemctl cat vendomat-cache-key.service")[0] != 0
    assert "5000" not in beta.ok("ss -ltn")
    beta.ok("test ! -e /var/lib/vendomat/cache-key")
    beta.ok("test ! -e /var/lib/vendomat/cache-key.pub")
    # From alpha, over the link: nothing answers on port 5000. The firewall drops the packets, so
    # curl ends with 28 (timeout) or 7 (refused); it never gets a cache answer.
    rc, out = alpha.run(f"curl -sS -m 10 http://{LAN_BETA}:5000/nix-cache-info")
    assert rc in (7, 28) and "StoreDir" not in out, (rc, out)
    world.log.result("beta (serve=false): no harmonia unit, no key unit, port 5000 refused")


def test_alpha_serves_only_on_its_marked_interface(world: World, alpha: Vm, beta: Vm) -> None:
    facts = world.facts()
    # The list is not forced: it holds the SSH port that `services.openssh` adds, so a 5000 would show.
    assert 22 in facts["alpha"]["globalPorts"] and 5000 not in facts["alpha"]["globalPorts"]
    assert facts["alpha"]["trustedPorts"] == [5000]
    assert "StoreDir: /nix/store" in alpha.ok("curl -sS -m 10 http://127.0.0.1:5000/nix-cache-info")
    assert "StoreDir: /nix/store" in beta.ok(f"curl -sS -m 10 http://{LAN_ALPHA}:5000/nix-cache-info")
    rc, out = beta.run(f"curl -sS -m 5 http://{UNTRUSTED_ALPHA}:5000/nix-cache-info")
    assert rc in (7, 28) and "StoreDir" not in out, (rc, out)
    world.log.result("alpha serve=true: loopback and trusted eth1 open; untrusted eth2 closed")


@pytest.fixture(scope="module")
def gamma(world: World, beta: Vm) -> Vm:
    facts = world.facts()["unmarked"]
    assert facts["serve"] is True
    assert 22 in facts["globalPorts"] and 5000 not in facts["globalPorts"]
    assert facts["trustedPorts"] == []
    local, remote = world.gamma_udp
    vm = _vm(world, "gamma", "52:54:00:79:00:03", local, remote)
    world.extra_servers.append(vm)
    vm.start()
    vm.wait_ssh()
    vm.wait_unit("multi-user.target")
    return vm


def test_unmarked_server_interface_stays_closed(world: World, beta: Vm, gamma: Vm) -> None:
    gamma.wait_unit("harmonia.socket")
    assert "StoreDir: /nix/store" in gamma.ok("curl -sS -m 10 http://127.0.0.1:5000/nix-cache-info")
    rc, out = beta.run("curl -sS -m 5 http://192.168.79.3:5000/nix-cache-info")
    assert rc in (7, 28) and "StoreDir" not in out, (rc, out)
    world.log.result("gamma serve=true without trustedInterfaces: loopback open; eth1 closed")


def test_the_client_settings_keep_cache_nixos_org(world: World, alpha: Vm, beta: Vm) -> None:
    cfg = beta.ok("nix config show")
    settings = dict(line.split(" = ", 1) for line in cfg.splitlines() if " = " in line)
    assert "https://cache.nixos.org" in settings["substituters"]
    assert f"http://{LAN_ALPHA}:5000" in settings["substituters"]
    assert CACHE_NIXOS_KEY in settings["trusted-public-keys"]
    pub = alpha.ok("cat /var/lib/vendomat/cache-key.pub").strip()
    assert pub in settings["trusted-public-keys"]
    assert settings["fallback"] == "true"
    assert settings["connect-timeout"] == "5"
    assert beta.ok(f"curl -sS -m 10 http://{LAN_ALPHA}:5000/nix-cache-info").startswith("StoreDir")


def test_beta_substitutes_from_alpha_and_checks_the_signature(world: World, alpha: Vm, beta: Vm) -> None:
    out, payload = world.alpha_path, world.alpha_payload
    beta.ok(f"test ! -e {out}")
    began = time.time()
    log = beta.ok(f"nix-store -r {out} 2>&1")
    world.log.result(f"beta substituted {out} from alpha in {time.time() - began:.1f} s")
    assert f"from 'http://{LAN_ALPHA}:5000'" in log, log
    assert beta.ok(f"cat {out}").strip() == payload
    assert "alpha:" in beta.ok(f"nix path-info --sigs {out}")
    beta.ok(f"nix store verify --sigs-needed 1 {out}")


def test_beta_refuses_a_path_when_the_key_is_not_trusted(world: World, alpha: Vm, beta: Vm) -> None:
    drv, out = world.instantiate(alpha, "p2", secrets.token_hex(8))
    alpha.ok(f"nix-store -r {drv}")
    only_nixos_key = f"--option trusted-public-keys '{CACHE_NIXOS_KEY}' --option extra-trusted-public-keys '' "
    rc, log = beta.run(f"nix-store -r {only_nixos_key} --option fallback false {out} 2>&1")
    assert rc != 0, log
    assert "not signed by any of the keys" in log, log
    assert beta.run(f"test -e {out}")[0] != 0
    # Control: the same path with the configured key comes in.
    beta.ok(f"nix-store -r {out}")
    assert beta.run(f"test -e {out}")[0] == 0
    world.log.result("beta refused a path signed by an untrusted key, then took it with the key")


def test_beta_falls_back_when_alpha_is_off(world: World, alpha: Vm, beta: Vm) -> None:
    alpha.power_off()
    assert not alpha.alive()
    # Control: without `fallback`, the dead peer stops the build.
    drv, out = world.instantiate(beta, "f1", secrets.token_hex(8))
    began = time.time()
    rc, log = beta.run(f"nix-store -r --option fallback false {drv} 2>&1", timeout=300)
    control = time.time() - began
    world.log.result(f"beta, alpha off, fallback=false: rc={rc} in {control:.1f} s")
    assert rc != 0, log
    assert beta.run(f"test -e {out}")[0] != 0
    # The configured settings (fallback = true, connect-timeout = 5) build locally.
    drv, out = world.instantiate(beta, "f2", secrets.token_hex(8))
    began = time.time()
    rc, log = beta.run(f"nix-store -r {drv} 2>&1", timeout=300)
    elapsed = time.time() - began
    world.log.result(f"beta, alpha off, configured settings: rc={rc} in {elapsed:.1f} s")
    assert rc == 0, log
    assert elapsed < FALLBACK_LIMIT_S, elapsed
    assert beta.run(f"test -e {out}")[0] == 0
    assert "ultimate" in beta.ok(f"nix path-info --sigs {out}")

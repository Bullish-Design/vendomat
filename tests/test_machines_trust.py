"""Cache-key trust between two machines on a private link (R61, R65; VMT-127, VMT-161, VMT-173, VMT-282).

Opt-in: `testee verify opt:machines-trust` (it sets VENDOMAT_MACHINES_TRUST=1). The proof builds two
NixOS machines, `alpha` and `beta`, through the real catalog (`vendomat/devenv`) and devenv Machines. It
boots both from EFI disk images in QEMU. A second card in each joins them on one private link `lan0`. The
catalog key `trustedInterfaces` opens the Harmonia port on that link only.

The proof follows what a user does:

1. Both machines run Harmonia from first boot. Each makes its own signing key. Beta reaches the cache of
   alpha over the link.
2. Alpha runs `vendomat apply`. The command writes `.machines/alpha/cache-key.pub` and commits it (VMT-282).
3. Alpha builds a store path that only alpha has. Beta does not hold it, and beta has not got alpha's key
   yet, so beta refuses to substitute it.
4. The workspace repository carries the commit to beta (the harness plays the shared remote: a Git bundle
   of alpha's repository, and `git pull` on beta). Beta runs `vendomat apply`. The catalog reads the
   committed key and gives beta a peer entry for alpha (`extra-substituters` and
   `extra-trusted-public-keys`).
5. Beta substitutes the path of alpha from the Harmonia of alpha, and the signature check passes.
6. Negative control: with a wrong key, or with no key for alpha, beta refuses a second path of alpha. The same
   path then comes in with the key that the module wrote.

The machines have no outside network. A local binary cache on the user-mode network (the harness cache)
serves the system paths that the VMs cannot build. The harness adds the new system of beta to it. Files go
under VENDOMAT_MACHINES_TRUST_DIR (default /mnt/shared/vendomat-p21/trust). Raw logs go to
VENDOMAT_MACHINES_TRUST_LOGS. QEMU and OVMF come from the pinned nixpkgs. The tests run in order and share
the two machines.
"""

from __future__ import annotations

import io
import json
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from machines_vm import ROOT, CacheServer, Logger, disk_guard, disk_line, free_port, remove_tree
from trust_vm import LinkVm, udp_port

ENABLED = os.environ.get("VENDOMAT_MACHINES_TRUST") == "1"
BASE = Path(os.environ.get("VENDOMAT_MACHINES_TRUST_DIR", "/mnt/shared/vendomat-p21/trust"))
LOGS = Path(os.environ.get("VENDOMAT_MACHINES_TRUST_LOGS", "/tmp/vendomat-machines-trust-logs"))
KEEP = os.environ.get("VENDOMAT_MACHINES_TRUST_KEEP") == "1"
MEMORY_MB = int(os.environ.get("VENDOMAT_MACHINES_TRUST_MEMORY", "3072"))
KEYS = Path(
    os.environ.get("VENDOMAT_MACHINES_TRUST_KEYS", str(Path.home() / ".local/state/vendomat/machines-trust-keys"))
)
#: The tools and pins of the `machines-vm` check. Read only.
TOOLS_NIX = ROOT / "tests" / "fixtures" / "machines" / "tools.nix"
FIXTURE = ROOT / "tests" / "fixtures" / "machines-trust" / "workspace"
DEVENV_TREE_OVERRIDE = os.environ.get("VENDOMAT_MACHINES_VM_DEVENV")

pytestmark = pytest.mark.skipif(not ENABLED, reason="run through testee verify opt:machines-trust")

MACS = {"alpha": "52:54:00:77:00:01", "beta": "52:54:00:77:00:02"}
KEY_RE = re.compile(r"^[^:\s]+:[A-Za-z0-9+/]+=*$")


@dataclass
class World:
    work: Path
    log: Logger
    env: dict[str, str]
    tools: Path = Path()
    launcher: Path = Path()
    vms: dict[str, LinkVm] = field(default_factory=dict)
    cache: CacheServer | None = None
    cache_dir: Path = Path()
    cache_port: int = 0
    cache_secret: Path = Path()
    tops: dict[str, str] = field(default_factory=dict)
    facts: dict[str, str] = field(default_factory=dict)

    def sh(self, argv: list[str], *, cwd: Path | None = None, check: bool = True, timeout: float = 3600, env=None):
        began = time.time()
        done = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=env or self.env, timeout=timeout)
        self.log.command("host", " ".join(argv), done.returncode, done.stdout + done.stderr, time.time() - began)
        if check:
            assert done.returncode == 0, f"{argv[0]} failed:\n{done.stderr[-3000:]}"
        return done

    def nix_build(self, attr: str) -> Path:
        done = self.sh(["nix-build", str(TOOLS_NIX), "-A", attr, "--no-out-link"])
        return Path(done.stdout.strip().splitlines()[-1])

    def devenv_build(self, attr: str, cwd: Path) -> str:
        done = self.sh(["devenv", "build", attr], cwd=cwd)
        return next(iter(json.loads(done.stdout).values()))

    def vm(self, name: str) -> LinkVm:
        return self.vms[name]

    def vendomat(self, name: str, args: str, *, timeout: float = 1800) -> tuple[int, str]:
        return self.vm(name).run("tester", f"cd ws && {self.launcher}/bin/vendomat {args} 2>&1", timeout=timeout)

    def git(self, name: str, args: str) -> str:
        return self.vm(name).ok("tester", f"cd ws && git {args}").rstrip()

    def state(self, name: str) -> dict[str, str]:
        script = (
            "echo current=$(readlink -f /run/current-system); "
            "echo profile=$(readlink -f /nix/var/nix/profiles/system); "
            "echo hostname=$(hostname); "
            "echo failed=[$(systemctl --failed --no-legend --plain | awk '{print $1}' | tr '\\n' ' ')]; "
            "echo system=$(systemctl is-system-running)"
        )
        out = self.vm(name).ok("root", script)
        return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)

    def nix_conf(self, name: str) -> str:
        return self.vm(name).ok("root", "cat /etc/nix/nix.conf")


def tar_bytes(source: Path, *, exclude: tuple[str, ...] = (".devenv",)) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if relative.parts and relative.parts[0] in exclude:
                continue
            archive.add(path, arcname=str(relative), recursive=False)
    return buffer.getvalue()


def dir_tar(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        archive.add(directory, arcname=directory.name)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def world() -> Iterator[World]:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log = Logger(LOGS if "VENDOMAT_MACHINES_TRUST_LOGS" in os.environ else LOGS / stamp)
    log.result(f"run {stamp}")
    log.result(f"disk before: {disk_guard()}")
    work = BASE / f"run-{stamp}"
    (work / "tmp").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "NIX_REMOTE", "NIX_SSL_CERT_FILE"}}
    env["TMPDIR"] = str(work / "tmp")
    w = World(work, log, env)
    try:
        yield from _setup(w, work)
    finally:
        for vm in w.vms.values():
            vm.power_off()
            vm.kill()
        if w.cache is not None:
            w.cache.stop()
        for name in w.vms:
            serial = work / name / "serial.log"
            if serial.exists():
                shutil.copy(serial, log.directory / f"{name}-serial.log")
        if not KEEP:
            remove_tree(work)
        log.result(f"disk after: {disk_line()}")


def _setup(w: World, work: Path) -> Iterator[World]:
    log = w.log
    w.tools = w.nix_build("tools")
    ovmf = w.nix_build("ovmf") / "FV"
    w.launcher = w.nix_build("launcher")
    w.env["PATH"] = f"{w.tools}/bin:{w.env['PATH']}"
    log.result(f"tools {w.tools}; launcher {w.launcher}; ovmf {ovmf}")
    for argv in (["devenv", "--version"], ["nix", "--version"], ["qemu-system-x86_64", "--version"]):
        log.result(f"{argv[0]}: {w.sh(argv).stdout.splitlines()[0]}")
    sources = json.loads(
        w.sh(["nix-instantiate", "--eval", "--strict", "--json", str(TOOLS_NIX), "-A", "sources"]).stdout
    )

    # The module tree of the devenv input: a copy at a fixed path. The machines get the same copy at the same path.
    modules = work / "modules"
    if DEVENV_TREE_OVERRIDE:
        tree, origin = Path(DEVENV_TREE_OVERRIDE), f"override {DEVENV_TREE_OVERRIDE}"
    else:
        locked = json.loads((ROOT / "flake.lock").read_text())["nodes"]["devenv"]["locked"]
        url = f"{locked['url']}?ref={locked['ref']}&rev={locked['rev']}"
        fetched = json.loads(w.sh(["nix", "flake", "prefetch", "--json", url]).stdout)
        tree = Path(fetched["storePath"]) / locked["dir"]
        origin = f"{locked['ref']} rev {locked['rev']} ({url}) at {fetched['storePath']}"
    shutil.copytree(tree, modules, symlinks=True)
    subprocess.run(["chmod", "-R", "u+w", str(modules)], check=True)
    log.result(f"devenv input: {origin}; src/modules {w.sh(['nix', 'hash', 'path', str(modules)]).stdout.strip()}")

    # The catalog of this checkout: a copy at a fixed path, the input `vendomat` of the workspace.
    modsrc = work / "modsrc"
    shutil.copytree(ROOT / "devenv", modsrc / "devenv")
    shutil.copytree(ROOT / "templates" / "workspace", modsrc / "templates" / "workspace")
    log.result(f"catalog: copy of {ROOT / 'devenv'}; hash {w.sh(['nix', 'hash', 'path', str(modsrc)]).stdout.strip()}")

    # Keys of the harness: the SSH key, and the signing key of the harness cache. They stay between runs,
    # so the images are the same in every run and the host store does not grow. They are one-purpose keys.
    KEYS.mkdir(parents=True, exist_ok=True)
    if not (KEYS / "key").exists():
        w.sh(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(KEYS / "key")])
        (KEYS / "cache.sec").write_text(
            w.sh(["nix", "key", "generate-secret", "--key-name", "trust-cache-1"]).stdout.strip()
        )
    shutil.copy(KEYS / "key", work / "key")
    (work / "key").chmod(0o600)
    shutil.copy(KEYS / "key.pub", work / "key.pub")
    shutil.copy(KEYS / "cache.sec", work / "cache.sec")
    w.cache_secret = work / "cache.sec"
    public = subprocess.run(
        ["nix", "key", "convert-secret-to-public"],
        input=(KEYS / "cache.sec").read_text(),
        capture_output=True,
        text=True,
        env=w.env,
        check=True,
    ).stdout.strip()

    # The workspace on the host (state C0: no cache key of any machine). It builds both images.
    ws = work / "ws"
    ws.mkdir()
    for name in ("base.nix", "expose.nix", "vendomat.yaml", "devenv.nix"):
        shutil.copy(FIXTURE / name, ws / name)
    (ws / ".gitignore").write_text(".devenv*\ndevenv.local.nix\n")
    (ws / "ssh-key.pub").write_text((work / "key.pub").read_text())
    (ws / "cache-key.pub").write_text(public + "\n")
    yaml = (FIXTURE / "devenv.yaml.in").read_text()
    for mark, value in {
        "@VENDOMAT@": str(modsrc),
        "@DEVENV@": str(modules),
        "@NIXPKGS@": sources["nixpkgs"]["path"],
        "@DISKO@": sources["disko"]["path"],
        "@FACTER@": sources["nixos-facter-modules"]["path"],
    }.items():
        yaml = yaml.replace(mark, value)
    (ws / "devenv.yaml").write_text(yaml)
    log.result(f"disk before builds: {disk_guard()}")
    for name in ("alpha", "beta"):
        w.tops[f"{name}0"] = w.devenv_build(f"machines.{name}.build.nixos", ws)
    log.result("host system paths (C0): " + json.dumps(w.tops))
    images = {}
    for name in ("alpha", "beta"):
        image = w.devenv_build(f"outputs.disk{name.capitalize()}", ws)
        (work / name).mkdir()
        shutil.copyfile(Path(image) / "nixos.qcow2", work / name / "box.qcow2")
        shutil.copyfile(ovmf / "OVMF_VARS.fd", work / name / "vars.fd")
        for file in ("box.qcow2", "vars.fd"):
            (work / name / file).chmod(0o644)
        images[name] = image
    log.result("images: " + json.dumps(images))

    # The harness cache. It holds the system paths of C0 now. It gets the new system of beta later.
    w.cache_dir = work / "cache"
    store = f"file://{w.cache_dir}?secret-key={w.cache_secret}&compression=none"
    w.sh(["nix", "copy", "--no-check-sigs", "--to", store, w.tops["alpha0"], w.tops["beta0"]])
    w.cache_port = free_port()
    w.cache = CacheServer(w.cache_dir, w.cache_port)
    w.cache.start()

    # The two machines, joined by one private link.
    ports = {"alpha": udp_port(), "beta": udp_port()}
    log.result(f"disk before the machines: {disk_guard()}")
    for name, peer in (("alpha", "beta"), ("beta", "alpha")):
        w.vms[name] = LinkVm(
            work / name,
            w.tools / "bin" / "qemu-system-x86_64",
            ovmf,
            w.tools / "bin" / "ssh",
            work / "key",
            free_port(),
            w.cache_port,
            w.tools / "bin" / "nc",
            log,
            memory_mb=MEMORY_MB,
            mac=MACS[name],
            udp_local=ports[name],
            udp_remote=ports[peer],
        )
    began = time.time()
    for vm in w.vms.values():
        vm.start()
    for name, vm in w.vms.items():
        vm.wait_ssh()
        log.result(f"{name} reached multi-user at {time.time() - began:.1f} s")
    for vm in w.vms.values():
        vm.ok("root", "loginctl enable-linger tester root")
        vm.ok("root", f"mkdir -p {work}")
        vm.ok("root", f"tar -C {work} -xf -", stdin=dir_tar(modules))
        vm.ok("root", f"tar -C {work} -xf -", stdin=dir_tar(modsrc))
        vm.ok("tester", "git config --global user.name tester && git config --global user.email tester@example.invalid")
        nix_sshopts = (
            f"-F /dev/null -i {work / 'key'} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p {vm.ssh_port}"
        )
        copy_env = {**w.env, "NIX_SSHOPTS": nix_sshopts}
        w.sh(["nix", "copy", "--no-check-sigs", "--to", "ssh-ng://root@127.0.0.1", str(w.launcher)], env=copy_env)
        vm.ok("root", f"nix-store --add-root /nix/var/nix/gcroots/vendomat-launcher -r {w.launcher}")
    # The workspace repository is born on alpha. Beta gets a clone of its first commit.
    alpha = w.vm("alpha")
    alpha.ok("tester", "mkdir -p ws && tar -C ws -xf -", stdin=tar_bytes(ws))
    alpha.ok("tester", "cd ws && git init -q -b main && git add -A && git commit -q -m 'workspace C0'")
    w.facts["C0"] = w.git("alpha", "rev-parse HEAD")
    bundle = alpha.ok("tester", "cd ws && git bundle create - main 2>/dev/null | base64 -w0")
    beta = w.vm("beta")
    beta.ok("tester", "base64 -d > /tmp/ws0.bundle", stdin=bundle)
    beta.ok("tester", "git clone -q -b main /tmp/ws0.bundle ws")
    assert w.git("beta", "rev-parse HEAD") == w.facts["C0"]
    log.result(f"workspace C0 {w.facts['C0']} is on alpha and beta")
    yield w


# 1. Both machines serve, and the link works --------------------------------------------------------


def test_both_machines_make_a_key_and_beta_reaches_the_cache_of_alpha_on_the_link(world: World) -> None:
    for name in ("alpha", "beta"):
        state = world.state(name)
        assert state["hostname"] == name and state["current"] == world.tops[f"{name}0"], state
        key = world.vm(name).ok("root", "cat /var/lib/vendomat/cache-key.pub").strip()
        assert KEY_RE.match(key) and key.startswith(f"{name}:"), key
        assert world.vm(name).ok("root", "stat -c %a /var/lib/vendomat/cache-key/secret").strip() == "600"
        world.facts[f"key-{name}"] = key
    assert world.facts["key-alpha"] != world.facts["key-beta"]
    world.log.result(f"keys made at first boot: alpha {world.facts['key-alpha']}, beta {world.facts['key-beta']}")
    beta = world.vm("beta")
    assert beta.ok("root", "ip -4 -o addr show dev lan0").count("10.77.0.2/24") == 1
    beta.ok("root", "ping -c 2 -W 3 alpha")
    info = beta.ok("root", "curl -sS --max-time 10 http://alpha:5000/nix-cache-info")
    assert "StoreDir: /nix/store" in info, info
    # The catalog opened the port on lan0 only.
    rules = world.vm("alpha").ok("root", "iptables -S nixos-fw 2>&1 || nft list ruleset 2>&1")
    assert "lan0" in rules and "5000" in rules, rules
    world.log.result("beta reaches http://alpha:5000 over lan0; the firewall of alpha names lan0 and port 5000")
    # Before the key is committed, beta has no peer entry for alpha.
    conf = world.nix_conf("beta")
    assert "alpha" not in conf and "extra-trusted-public-keys" not in conf, conf


# 2. Alpha applies and commits its key --------------------------------------------------------------


def test_alpha_apply_makes_and_commits_its_key(world: World) -> None:
    rc, out = world.vendomat("alpha", "apply")
    assert rc == 0, out
    assert "wrote .machines/alpha/cache-key.pub and put it in the commit" in out, out
    assert world.git("alpha", "status --porcelain") == ""
    assert world.git("alpha", "show --format= --name-only HEAD") == ".machines/alpha/cache-key.pub"
    assert world.git("alpha", "rev-parse HEAD^") == world.facts["C0"]
    committed = world.git("alpha", "show HEAD:.machines/alpha/cache-key.pub").strip()
    assert committed == world.facts["key-alpha"], (committed, world.facts["key-alpha"])
    state = world.state("alpha")
    assert state["current"] == world.tops["alpha0"], "alpha's configuration did not change (no peer has a key yet)"
    world.facts["C1"] = world.git("alpha", "rev-parse HEAD")
    world.log.result(f"alpha apply: commit {world.facts['C1']} holds .machines/alpha/cache-key.pub = {committed}")


# 3. Paths that only alpha has -----------------------------------------------------------------------


def test_alpha_builds_two_paths_that_beta_does_not_have_and_beta_refuses_them_without_the_key(world: World) -> None:
    alpha, beta = world.vm("alpha"), world.vm("beta")
    bash = alpha.ok("root", "readlink -f /run/current-system/sw/bin/bash").strip()
    assert bash.endswith("/bin/bash")
    bash_dir = bash[: -len("/bin/bash")]
    paths = []
    for index in (1, 2):
        nonce = f"{index}-{secrets.token_hex(8)}"
        expression = (
            (
                'builtins.derivation { name = "alpha-only-NONCE"; system = "x86_64-linux"; '
                'builder = "${builtins.storePath "BASH"}/bin/bash"; '
                'args = [ "-c" "echo alpha-only-NONCE > $out" ]; }'
            )
            .replace("NONCE", nonce)
            .replace("BASH", bash_dir)
        )
        built = alpha.ok("root", f"nix-build --no-out-link -E '{expression}'").splitlines()
        out = [line for line in built if line.startswith("/nix/store/") and not line.endswith(".drv'...")][-1].strip()
        assert out.startswith("/nix/store/") and out.endswith(f"-alpha-only-{nonce}"), out
        assert alpha.ok("root", f"cat {out}").strip() == f"alpha-only-{nonce}"
        paths.append(out)
        # The path is on alpha only: not on beta, not in the harness cache.
        assert beta.run("root", f"test -e {out}")[0] != 0
        assert not (world.cache_dir / f"{Path(out).name.split('-')[0]}.narinfo").exists()
    world.facts["path1"], world.facts["path2"] = paths
    world.log.result(f"built on alpha, absent from beta and from the harness cache: {paths}")
    # Control 0: beta has no key of alpha yet, so it trusts no signature of alpha and has no peer entry.
    cache = world.cache
    assert cache is not None
    downloads = cache.nar_downloads
    rc, out = beta.run("root", f"nix-store -r {paths[0]} 2>&1")
    assert rc != 0 and beta.run("root", f"test -e {paths[0]}")[0] != 0, out
    assert cache.nar_downloads == downloads
    world.facts["refusal-before"] = out.strip().splitlines()[-1]
    world.log.result(f"control 0, beta before the key: rc={rc}; last line: {world.facts['refusal-before']}")
    # Even with the cache of alpha named by hand, beta refuses: the signature needs a key that beta lacks.
    rc, out = beta.run("root", f"nix-store -r {paths[0]} --option extra-substituters http://alpha:5000 2>&1")
    assert rc != 0 and beta.run("root", f"test -e {paths[0]}")[0] != 0, out
    world.facts["refusal-unkeyed"] = out.strip()
    world.log.result(
        f"control 0b, cache of alpha named but no key: rc={rc}; "
        f"output tail: {' | '.join(out.strip().splitlines()[-3:])}"
    )


# 4. The commit reaches beta; beta applies -------------------------------------------------------------


def test_beta_gets_the_commit_and_apply_gives_it_the_peer_entry_of_alpha(world: World) -> None:
    alpha, beta = world.vm("alpha"), world.vm("beta")
    # The harness plays the shared remote of the workspace repository. The user-visible step is one pull.
    bundle = alpha.ok("tester", "cd ws && git bundle create - main 2>/dev/null | base64 -w0")
    beta.ok("tester", "base64 -d > /tmp/ws1.bundle", stdin=bundle)
    world.git("beta", "pull -q --ff-only /tmp/ws1.bundle main")
    assert world.git("beta", "rev-parse HEAD") == world.facts["C1"]
    committed = world.git("beta", "show HEAD:.machines/alpha/cache-key.pub").strip()
    assert committed == world.facts["key-alpha"]
    # The VM has no network, so the harness builds the new system of beta on the host from the same tree
    # and offers the new store paths through the harness cache. The machine evaluates the same tree.
    work = world.work
    ws1 = work / "ws-C1"
    shutil.copytree(work / "ws", ws1, ignore=shutil.ignore_patterns(".devenv"))
    (ws1 / ".machines" / "alpha").mkdir(parents=True)
    (ws1 / ".machines" / "alpha" / "cache-key.pub").write_text(
        beta.ok("tester", "cd ws && cat .machines/alpha/cache-key.pub")
    )
    world.tops["beta1"] = world.devenv_build("machines.beta.build.nixos", ws1)
    assert world.tops["beta1"] != world.tops["beta0"], "the key must change the system of beta"
    old = set(world.sh(["nix", "path-info", "-r", world.tops["beta0"]]).stdout.split())
    new = set(world.sh(["nix", "path-info", "-r", world.tops["beta1"]]).stdout.split()) - old
    store = f"file://{world.cache_dir}?secret-key={world.cache_secret}&compression=none"
    world.sh(["nix", "copy", "--no-check-sigs", "--no-recursive", "--to", store, *sorted(new)])
    world.log.result(f"host built beta's system with alpha's key: {world.tops['beta1']} ({len(new)} new paths)")
    cache = world.cache
    assert cache is not None
    rc, out = world.vendomat("beta", "apply")
    assert rc == 0, out
    assert "wrote .machines/beta/cache-key.pub and put it in the commit" in out, out
    state = world.state("beta")
    assert state["current"] == world.tops["beta1"] == state["profile"], (state, world.tops)
    assert state["failed"].strip("[] ") == "", state
    assert world.git("beta", "status --porcelain") == ""
    assert world.git("beta", "show --format= --name-only HEAD") == ".machines/beta/cache-key.pub"
    world.log.result(f"beta apply: system {state['current']}; failed units none")


def test_beta_writes_the_key_of_alpha_into_its_nix_settings(world: World) -> None:
    conf = world.nix_conf("beta")
    lines = {line.split(" = ", 1)[0]: line.split(" = ", 1)[1] for line in conf.splitlines() if " = " in line}
    assert lines["extra-substituters"].split() == ["http://alpha:5000"], conf
    assert lines["extra-trusted-public-keys"].split() == [world.facts["key-alpha"]], conf
    assert world.facts["key-alpha"] not in lines["trusted-public-keys"]
    assert lines["fallback"] == "true"
    world.log.result(
        f"beta nix.conf: extra-substituters = {lines['extra-substituters']}; "
        f"extra-trusted-public-keys = {lines['extra-trusted-public-keys']}; fallback = {lines['fallback']}"
    )
    # The daemon of beta reads the same values.
    shown = world.vm("beta").ok(
        "root", "nix show-config 2>/dev/null | grep -E '^(extra-)?(substituters|trusted-public-keys) '"
    )
    assert "http://alpha:5000" in shown and world.facts["key-alpha"] in shown, shown


# 5. Beta substitutes from alpha ------------------------------------------------------------------------


def test_beta_substitutes_the_path_of_alpha_and_the_signature_check_passes(world: World) -> None:
    beta = world.vm("beta")
    cache = world.cache
    assert cache is not None
    path = world.facts["path1"]
    assert beta.run("root", f"test -e {path}")[0] != 0
    downloads = cache.nar_downloads
    out = beta.ok("root", f"nix-store -r {path} -v 2>&1")
    assert beta.ok("root", f"cat {path}").strip() == f"alpha-only-{path.split('alpha-only-')[1]}"
    assert f"copying path '{path}' from 'http://alpha:5000" in out, out
    assert cache.nar_downloads == downloads, "the harness cache did not serve the path"
    sigs = beta.ok("root", f"nix path-info --sigs {path}")
    assert "\talpha:" in sigs, sigs
    beta.ok("root", f"nix store verify --sigs-needed 1 {path} 2>&1")
    world.log.result(
        f"beta substituted {path} from alpha: {[ln for ln in out.splitlines() if 'copying path' in ln][0].strip()}; "
        f"path-info sigs: {sigs.strip().split(chr(9))[-1]}; nix store verify --sigs-needed 1: ok"
    )


# 6. Negative control ------------------------------------------------------------------------------------


def test_beta_refuses_the_second_path_with_a_wrong_key_or_no_key_and_takes_it_with_the_module_key(
    world: World,
) -> None:
    beta, host = world.vm("beta"), world.sh
    path = world.facts["path2"]
    wrong_secret = host(["nix", "key", "generate-secret", "--key-name", "alpha"]).stdout.strip()
    wrong_public = subprocess.run(
        ["nix", "key", "convert-secret-to-public"],
        input=wrong_secret,
        capture_output=True,
        text=True,
        env=world.env,
        check=True,
    ).stdout.strip()
    assert wrong_public.startswith("alpha:") and wrong_public != world.facts["key-alpha"]
    assert beta.run("root", f"test -e {path}")[0] != 0
    # `--option extra-trusted-public-keys` would add to the list from nix.conf, so each control sets
    # `trusted-public-keys` itself. A value on the command line replaces the file value and the extras
    # of the file. The base list keeps only the key of the harness cache.
    conf = dict(line.split(" = ", 1) for line in world.nix_conf("beta").splitlines() if " = " in line)
    base = conf["trusted-public-keys"].strip()
    assert (
        world.facts["key-alpha"] not in base and conf["extra-trusted-public-keys"].strip() == world.facts["key-alpha"]
    )
    # 1. A wrong key under the right name.
    rc, out = beta.run("root", f"nix-store -r {path} --option trusted-public-keys '{base} {wrong_public}' 2>&1")
    assert rc != 0 and beta.run("root", f"test -e {path}")[0] != 0, out
    world.log.result(f"control 1, wrong key {wrong_public}: rc={rc}; tail: {' | '.join(out.strip().splitlines()[-3:])}")
    assert "not signed by any of the keys" in out, out
    # 2. No key of alpha at all, with the cache of alpha still named by the module.
    rc, out = beta.run("root", f"nix-store -r {path} --option trusted-public-keys '{base}' 2>&1")
    assert rc != 0 and beta.run("root", f"test -e {path}")[0] != 0, out
    world.log.result(f"control 2, no key of alpha: rc={rc}; tail: {' | '.join(out.strip().splitlines()[-3:])}")
    assert "not signed by any of the keys" in out, out
    # 3. The settings that the module wrote: the same path comes in.
    out = beta.ok("root", f"nix-store -r {path} -v 2>&1")
    assert f"copying path '{path}' from 'http://alpha:5000" in out, out
    assert beta.run("root", f"test -e {path}")[0] == 0
    world.log.result("control 3, the key that the module wrote: the same path is substituted from alpha")


def test_both_machines_are_clean_at_the_end(world: World) -> None:
    for name in ("alpha", "beta"):
        state = world.state(name)
        assert state["failed"].strip("[] ") == "" and state["system"] == "running", (name, state)
    world.log.result("end state: alpha and beta run with zero failed units")

"""`vendomat apply` and `vendomat rollback` on a virtual machine (R15, R30, R43; project 24, S4).

Opt-in: `testee verify opt:machines-vm` (it sets VENDOMAT_MACHINES_VM=1). The proof builds one NixOS
machine `box` through devenv Machines on stock devenv 2.4.0 and the S1 module tree, boots it from an
EFI disk image, and runs the real commands inside it, as an unprivileged user with sudo:

1. W2 T1: apply system A and then A'; the machine boots A' with zero failed units.
2. W9 R1 to R6: the default rollback gives the identical path of A, copies nothing, adds a generation
   that is the default boot entry, and boots clean; a working-copy-only restore is refused; a rollback
   works after the path left the store (the cache supplies it); `--fast`; `--boot-only`.
3. R43 and VR3: apply commits allowlisted configuration after build and before activation, leaves
   unrelated staged files alone, refuses ignored configuration, and `--dirty` skips the commit;
   rollback skips dirty entries.

The machine has no network. A local binary cache serves the system paths over HTTP (the harness counts
the downloads), and the workspace pins its inputs by store path. See tests/fixtures/machines/. The
image, the cache, and the state go under VENDOMAT_MACHINES_VM_DIR (default /mnt/shared/vendomat-p21/s4).
The harness deletes them at the end. Raw logs go to VENDOMAT_MACHINES_VM_LOGS. QEMU and OVMF come from
the pinned nixpkgs. The tests run in order and share one machine.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from machines_vm import FIXTURE, ROOT, CacheServer, Logger, Vm, disk_guard, disk_line, free_port, remove_tree

ENABLED = os.environ.get("VENDOMAT_MACHINES_VM") == "1"
BASE = Path(os.environ.get("VENDOMAT_MACHINES_VM_DIR", "/mnt/shared/vendomat-p21/s4"))
LOGS = Path(os.environ.get("VENDOMAT_MACHINES_VM_LOGS", "/tmp/vendomat-machines-vm-logs"))
KEEP = os.environ.get("VENDOMAT_MACHINES_VM_KEEP") == "1"
#: The `devenv` input is the module tree that `flake.lock` pins: the published S1 tag (R41, R44).
#: VENDOMAT_MACHINES_VM_DEVENV names another `src/modules` directory instead.
DEVENV_TREE_OVERRIDE = os.environ.get("VENDOMAT_MACHINES_VM_DEVENV")

KEYS = Path(os.environ.get("VENDOMAT_MACHINES_VM_KEYS", str(Path.home() / ".local/state/vendomat/machines-vm-keys")))

pytestmark = pytest.mark.skipif(not ENABLED, reason="run through testee verify opt:machines-vm")

#: The hatch file of each system: the marker in /etc/t1-marker and the extra packages.
SYSTEMS = {
    "A": ("A", ""),
    "A-prime": ("A-prime", "pkgs.hello"),
    "D": ("D", "pkgs.hello pkgs.jq"),
}
PROFILES = "/nix/var/nix/profiles"
RECORD = "/var/lib/vendomat/generations.jsonl"


def hatch(system: str) -> str:
    marker, packages = SYSTEMS[system]
    text = (FIXTURE / "workspace" / "devenv.nix.in").read_text()
    return text.replace("@MARKER@", marker).replace("@PACKAGES@", packages)


@dataclass
class World:
    work: Path
    log: Logger
    env: dict[str, str]
    tools: Path = Path()
    launcher: Path = Path()
    vm: Vm | None = None
    cache: CacheServer | None = None
    tops: dict[str, str] = field(default_factory=dict)
    commits: dict[str, str] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    def sh(self, argv: list[str], *, cwd: Path | None = None, check: bool = True, timeout: float = 1800):
        began = time.time()
        done = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=self.env, timeout=timeout)
        self.log.command("host", " ".join(argv), done.returncode, done.stdout + done.stderr, time.time() - began)
        if check:
            assert done.returncode == 0, f"{argv[0]} failed:\n{done.stderr[-3000:]}"
        return done

    def nix_build(self, attr: str) -> Path:
        done = self.sh(["nix-build", str(FIXTURE / "tools.nix"), "-A", attr, "--no-out-link"])
        return Path(done.stdout.strip().splitlines()[-1])

    def devenv_build(self, attr: str, cwd: Path) -> str:
        done = self.sh(["devenv", "build", attr], cwd=cwd)
        return next(iter(json.loads(done.stdout).values()))

    # In the machine.
    @property
    def machine(self) -> Vm:
        assert self.vm is not None
        return self.vm

    def vendomat(self, args: str, *, timeout: float = 1200) -> tuple[int, str]:
        began = time.time()
        rc, out = self.machine.run("tester", f"cd ws && {self.launcher}/bin/vendomat {args} 2>&1", timeout=timeout)
        self.timings[f"vendomat {args}"] = time.time() - began
        return rc, out

    def git(self, args: str) -> str:
        # Preserve leading columns from porcelain status; they distinguish staged from unstaged.
        return self.machine.ok("tester", f"cd ws && git {args}").rstrip()

    def write_hatch(self, system: str) -> None:
        self.machine.ok("tester", "cd ws && cat > devenv.nix", stdin=hatch(system))

    def commit(self, message: str, *paths: str) -> str:
        self.git("add -A " + " ".join(paths) if paths else "add -A")
        self.git(f"commit -q -m '{message}'")
        return self.git("rev-parse HEAD")

    def state(self) -> dict[str, str]:
        script = (
            f"echo current=$(readlink -f /run/current-system); echo booted=$(readlink -f /run/booted-system); "
            f"echo profile=$(readlink -f {PROFILES}/system); echo pointer=$(readlink {PROFILES}/system); "
            f"echo gens=$(ls {PROFILES} | sed -n 's/^system-\\([0-9]*\\)-link$/\\1/p' | sort -n | tr '\\n' ' '); "
            "entry=$(awk '/^default/ {print $2}' /boot/loader/loader.conf); "
            "echo default=$entry; "
            "echo default_generation=$(grep -o '^version Generation [0-9]*' "
            "/boot/loader/entries/$entry | awk '{print $3}'); "
            "echo marker=$(cat /etc/t1-marker); "
            "echo hello=$(test -x /run/current-system/sw/bin/hello && echo yes || echo no); "
            "echo failed=[$(systemctl --failed --no-legend --plain | awk '{print $1}' | tr '\\n' ' ')]; "
            "echo system=$(systemctl is-system-running)"
        )
        out = self.machine.ok("root", script)
        return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)

    def record(self) -> list[dict]:
        rc, out = self.machine.run("root", f"cat {RECORD}")
        return [json.loads(line) for line in out.splitlines() if line.strip()] if rc == 0 else []

    def downloads(self) -> int:
        assert self.cache is not None
        return self.cache.nar_downloads


def tar_bytes(source: Path, *, exclude: tuple[str, ...] = (".devenv",)) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if relative.parts and relative.parts[0] in exclude:
                continue
            archive.add(path, arcname=str(relative), recursive=False)
    return buffer.getvalue()


def default_generation(state: dict[str, str]) -> int:
    """The generation of the default boot entry (the entry file names carry a hash, not a number)."""

    return int(state["default_generation"])


@pytest.fixture(scope="module")
def world() -> Iterator[World]:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log = Logger(LOGS if "VENDOMAT_MACHINES_VM_LOGS" in os.environ else LOGS / stamp)
    log.result(f"disk before: {disk_guard()}")
    work = BASE / f"run-{stamp}"
    (work / "tmp").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "NIX_REMOTE", "NIX_SSL_CERT_FILE"}}
    env["TMPDIR"] = str(work / "tmp")
    w = World(work, log, env)
    try:
        yield from _setup(w, work)
    finally:
        if w.vm is not None:
            w.vm.power_off()
            w.vm.kill()
        if w.cache is not None:
            w.cache.stop()
        for name in ("serial.log",):
            if (work / name).exists():
                shutil.copy(work / name, log.directory / name)
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
        out = w.sh(argv).stdout.splitlines()[0]
        log.result(f"{argv[0]}: {out}")
    sources = json.loads(
        w.sh(["nix-instantiate", "--eval", "--strict", "--json", str(FIXTURE / "tools.nix"), "-A", "sources"]).stdout
    )

    # The module tree: a copy at a fixed path. The machine gets the same copy at the same path.
    modules = work / "modules"
    if DEVENV_TREE_OVERRIDE:
        tree, origin = Path(DEVENV_TREE_OVERRIDE), f"override {DEVENV_TREE_OVERRIDE}"
    else:
        # The store copy of the input that flake.lock pins. The machine is offline, so the workspace pins a
        # copy of its src/modules.
        locked = json.loads((ROOT / "flake.lock").read_text())["nodes"]["devenv"]["locked"]
        url = f"{locked['url']}?ref={locked['ref']}&rev={locked['rev']}"
        fetched = json.loads(w.sh(["nix", "flake", "prefetch", "--json", url]).stdout)
        tree = Path(fetched["storePath"]) / locked["dir"]
        origin = f"{locked['ref']} rev {locked['rev']} ({url}) at {fetched['storePath']}"
    shutil.copytree(tree, modules, symlinks=True)
    subprocess.run(["chmod", "-R", "u+w", str(modules)], check=True)
    log.result(f"devenv input: {origin}; src/modules {w.sh(['nix', 'hash', 'path', str(modules)]).stdout.strip()}")

    # Keys: SSH for the harness, and the signing key of the harness cache.
    # The keys live outside the run directory and stay between runs. Then the image and the system paths
    # are the same in every run, and the host store does not grow with each run. They are one-purpose
    # keys of this test: the SSH key opens only the test machine, and the cache key signs only its cache.
    KEYS.mkdir(parents=True, exist_ok=True)
    if not (KEYS / "key").exists():
        w.sh(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(KEYS / "key")])
        (KEYS / "cache.sec").write_text(
            w.sh(["nix", "key", "generate-secret", "--key-name", "vm-cache-1"]).stdout.strip()
        )
    shutil.copy(KEYS / "key", work / "key")
    (work / "key").chmod(0o600)
    shutil.copy(KEYS / "key.pub", work / "key.pub")
    shutil.copy(KEYS / "cache.sec", work / "cache.sec")
    public = subprocess.run(
        ["nix", "key", "convert-secret-to-public"],
        input=(KEYS / "cache.sec").read_text(),
        capture_output=True,
        text=True,
        env=w.env,
        check=True,
    ).stdout.strip()

    # The workspace on the host. It builds the expected system paths and the disk image.
    ws = work / "ws"
    ws.mkdir()
    fixture = FIXTURE / "workspace"
    for name in ("base.nix", "expose.nix", "vendomat.yaml"):
        shutil.copy(fixture / name, ws / name)
    (ws / ".gitignore").write_text(".devenv*\ndevenv.local.nix\n")
    (ws / "ssh-key.pub").write_text((work / "key.pub").read_text())
    (ws / "cache-key.pub").write_text(public + "\n")
    yaml = (fixture / "devenv.yaml.in").read_text()
    for mark, value in {
        "@DEVENV@": str(modules),
        "@NIXPKGS@": sources["nixpkgs"]["path"],
        "@DISKO@": sources["disko"]["path"],
        "@FACTER@": sources["nixos-facter-modules"]["path"],
    }.items():
        yaml = yaml.replace(mark, value)
    (ws / "devenv.yaml").write_text(yaml)
    (ws / "devenv.nix").write_text(hatch("A"))
    log.result(f"disk before builds: {disk_guard()}")
    w.tops["A"] = w.devenv_build("machines.box.build.nixos", ws)
    for name in ("A-prime", "D"):
        variant = work / f"ws-{name}"
        shutil.copytree(ws, variant, ignore=shutil.ignore_patterns(".devenv"))
        (variant / "devenv.nix").write_text(hatch(name))
        w.tops[name] = w.devenv_build("machines.box.build.nixos", variant)
    log.result("host system paths: " + json.dumps(w.tops))
    image = w.devenv_build("outputs.disk", ws)
    shutil.copyfile(Path(image) / "nixos.qcow2", work / "box.qcow2")
    shutil.copyfile(ovmf / "OVMF_VARS.fd", work / "vars.fd")
    for name in ("box.qcow2", "vars.fd"):
        (work / name).chmod(0o644)

    # The cache. `nix copy` signs the paths with the harness key. The toplevel sets allowSubstitutes
    # to false, and base.nix turns always-allow-substitutes on, so the cache serves it too.
    cache_dir = work / "cache"
    store = f"file://{cache_dir}?secret-key={work / 'cache.sec'}&compression=none"
    w.sh(["nix", "copy", "--no-check-sigs", "--to", store, *w.tops.values()])
    log.result(f"cache: {sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) / 1e9:.2f} GB")
    cache_port = free_port()
    w.cache = CacheServer(cache_dir, cache_port)
    w.cache.start()

    # The machine.
    ssh_port = free_port()
    w.vm = Vm(
        work,
        w.tools / "bin" / "qemu-system-x86_64",
        ovmf,
        w.tools / "bin" / "ssh",
        work / "key",
        ssh_port,
        cache_port,
        w.tools / "bin" / "nc",
        log,
    )
    log.result(f"disk before the machine: {disk_guard()}")
    began = time.time()
    w.vm.start()
    w.vm.wait_ssh()
    log.result(f"the machine reached multi-user in {time.time() - began:.1f} s")
    vm = w.machine
    # A user manager that starts or stops during a switch makes switch-to-configuration exit 4. Keep
    # the managers of both users up for the whole run.
    vm.ok("root", "loginctl enable-linger tester root")
    vm.ok("root", f"mkdir -p {work}")
    vm.ok("root", f"tar -C {work} -xf -", stdin=_modules_tar(modules))
    vm.ok("tester", "mkdir -p ws && tar -C ws -xf -", stdin=tar_bytes(ws))
    vm.ok("tester", "git config --global user.name tester && git config --global user.email tester@example.invalid")
    vm.ok("tester", "cd ws && git init -q -b main && git add -A && git commit -q -m 'system A'")
    w.env["NIX_SSHOPTS"] = (
        f"-F /dev/null -i {work / 'key'} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "
        f"-o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p {ssh_port}"
    )
    w.sh(["nix", "copy", "--no-check-sigs", "--to", "ssh-ng://root@127.0.0.1", str(w.launcher)])
    vm.ok("root", f"nix-store --add-root /nix/var/nix/gcroots/vendomat-launcher -r {w.launcher}")
    w.commits["A"] = w.git("rev-parse HEAD")
    yield w


def _modules_tar(modules: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        archive.add(modules, arcname="modules")
    return buffer.getvalue()


# W2 T1 and the base state ---------------------------------------------------------------------


def test_the_machine_runs_system_a_before_any_command(world: World) -> None:
    state = world.state()
    assert state["current"] == world.tops["A"], "the image holds the system that the host built"
    assert state["marker"] == "A" and state["hello"] == "no"
    assert state["failed"].strip("[] ") == "" and state["system"] == "running"
    assert state["gens"].split() == ["1"]
    facts = json.loads(world.machine.ok("tester", "cat /etc/devenv/machine-facts.json"))
    assert facts["hostname"] == "box"
    assert world.record() == []
    world.log.result(f"baseline: {state}")


def test_apply_build_failure_and_ignored_config_do_not_change_the_machine(world: World) -> None:
    before = world.state()
    world.write_hatch("A-prime")
    world.machine.ok("tester", "cd ws && printf '{ invalid = ' > devenv.nix")
    rc, out = world.vendomat("apply")
    assert rc != 0 and "build machines.box.build.nixos failed" in out, out
    assert world.git("status --porcelain") == " M devenv.nix"
    assert world.state() == before and world.record() == []
    world.git("checkout -- devenv.nix")
    # A hatch file that is ignored by Git still counts: no other clone has it.
    world.machine.ok("tester", "cd ws && echo '{ }' > devenv.local.nix")
    rc, out = world.vendomat("apply")
    assert rc == 1 and "Force-add them with `git add -f`" in out, out
    world.machine.ok("tester", "cd ws && rm devenv.local.nix")
    assert world.state() == before and world.record() == []
    world.log.result("build failure left config uncommitted and machine unchanged; apply refused ignored config")


def test_apply_a_gives_the_same_path_adds_no_generation_and_records_a_line(world: World) -> None:
    began = world.downloads()
    # The sharing module makes this file at first boot. The fixture machine has no such module, so
    # the harness writes a stand-in key and checks that apply copies it into the workspace.
    world.machine.ok("root", "install -d /var/lib/vendomat && echo 'box:AAAA=' > /var/lib/vendomat/cache-key.pub")
    rc, out = world.vendomat("apply")
    assert rc == 0, out
    assert "wrote .machines/box/cache-key.pub; commit it" in out, out
    assert world.machine.ok("tester", "cd ws && cat .machines/box/cache-key.pub").strip() == "box:AAAA="
    assert world.git("status --porcelain") == "?? .machines/", "apply copies the key and never commits it"
    state = world.state()
    assert state["profile"] == world.tops["A"] and state["gens"].split() == ["1"]
    assert world.downloads() == began, "system A is in the store: nothing to fetch"
    [line] = world.record()
    assert line["generation"] == 1 and line["toplevel"] == world.tops["A"]
    assert line["commit"] == world.commits["A"] and line["dirty"] is False
    assert "failed units: none" in out and "generation 1 is active" in out
    world.machine.ok("tester", "cd ws && rm -rf .machines")
    world.log.result(f"apply A: record {line}")


def test_apply_a_prime_builds_in_the_machine_and_boots_clean(world: World) -> None:
    world.write_hatch("A-prime")
    world.machine.ok("tester", "cd ws && echo two > notes.txt && git add notes.txt")  # staged addition, not watched
    began = world.downloads()
    rc, out = world.vendomat("apply")
    assert rc == 0, out
    world.commits["A-prime"] = world.git("rev-parse HEAD")
    assert world.git("log -1 --format=%s") == "vendomat apply configuration"
    assert world.git("show --format= --name-only HEAD") == "devenv.nix"
    assert world.git("status --porcelain") == "A  notes.txt\n?? .machines/", (
        "apply preserves unrelated staged work and leaves its trust key outside the config commit"
    )
    world.machine.ok("tester", "cd ws && rm -rf .machines")
    assert world.downloads() > began, "A-prime needs paths from the cache (hello)"
    state = world.state()
    # The machine builds the same system path as the host, although the workspace path differs.
    assert state["current"] == world.tops["A-prime"] == state["profile"]
    assert state["gens"].split() == ["1", "2"] and state["marker"] == "A-prime" and state["hello"] == "yes"
    assert default_generation(state) == 2 and state["failed"].strip("[] ") == ""
    line = world.record()[-1]
    assert line["generation"] == 2 and line["toplevel"] == world.tops["A-prime"]
    assert line["commit"] == world.commits["A-prime"] and line["dirty"] is False
    world.log.result(f"apply A-prime: {world.timings['vendomat apply']:.1f} s, {line}")
    world.machine.reboot()
    state = world.state()
    assert state["booted"] == world.tops["A-prime"] and state["marker"] == "A-prime"
    assert state["failed"].strip("[] ") == "" and state["system"] == "running"
    world.log.result("reboot: A-prime boots with zero failed units")


# W9 R2 and R3: the lasting rollback ----------------------------------------------------------------


def test_ignored_configuration_is_refused_by_apply_and_rollback(world: World) -> None:
    before = world.state()
    world.machine.ok("tester", "cd ws && echo '{ }' > devenv.local.nix")
    rc, out = world.vendomat("apply")
    assert rc == 1 and "Force-add them with `git add -f`" in out, out
    rc, out = world.vendomat("rollback")
    assert rc == 1 and "uncommitted changes to watched files" in out, out
    assert world.state() == before and len(world.record()) == 2
    world.machine.ok("tester", "cd ws && rm devenv.local.nix")
    assert world.git("status --porcelain") == "A  notes.txt", "the unrelated staged addition stays staged"
    world.log.result("apply and rollback refused a present ignored config file without changing the machine")


def test_rollback_gives_the_identical_path_copies_nothing_and_boots_clean(world: World) -> None:
    began = world.downloads()
    rc, out = world.vendomat("rollback")
    assert rc == 0, out
    # The diff comes first, before any build output.
    assert out.index("target: generation 1") < out.index("diff --git") < out.index("built ")
    assert world.downloads() == began, "the target is in the store: nothing is fetched"
    state = world.state()
    assert state["current"] == world.tops["A"] == state["profile"], "the identical store path of A"
    assert state["gens"].split() == ["1", "2", "3"] and state["pointer"] == "system-3-link"
    assert default_generation(state) == 3 and state["marker"] == "A" and state["hello"] == "no"
    assert state["failed"].strip("[] ") == ""
    # The restore is a commit. Another clone sees it, while unrelated staged work stays staged.
    short = world.commits["A"][:12]
    assert world.git("log -1 --format=%s") == f"rollback to {short}"
    assert world.git("show --format= --name-only HEAD") == "devenv.nix"
    assert world.git("status --porcelain") == "A  notes.txt"
    assert world.git(f"diff {world.commits['A']} HEAD -- vendomat.yaml devenv.lock devenv.nix") == ""
    assert world.machine.ok("tester", "cd ws && cat notes.txt").strip() == "two", "an unwatched file stays"
    world.commits["R1"] = world.git("rev-parse HEAD")
    line = world.record()[-1]
    assert line["generation"] == 3 and line["toplevel"] == world.tops["A"]
    assert line["commit"] == world.commits["R1"] and line["dirty"] is False
    world.log.result(f"rollback: {world.timings['vendomat rollback']:.1f} s, 0 downloads, record {line}")
    world.git("reset -- notes.txt")
    world.machine.ok("tester", "cd ws && rm notes.txt")
    assert world.git("status --porcelain") == ""
    world.machine.reboot()
    state = world.state()
    assert state["booted"] == world.tops["A"] and state["marker"] == "A" and state["hello"] == "no"
    assert state["failed"].strip("[] ") == "" and state["system"] == "running"
    assert default_generation(state) == 3
    world.log.result("reboot: the rollback is lasting, system A, generation 3 is the default entry, no failed units")


# R43: the dirty flag --------------------------------------------------------------------------------


def test_dirty_apply_is_recorded_and_rollback_skips_it(world: World) -> None:
    world.write_hatch("D")
    rc, out = world.vendomat("apply --dirty")
    assert rc == 0 and "warning: applying uncommitted changes" in out, out
    line = world.record()[-1]
    assert line["generation"] == 4 and line["toplevel"] == world.tops["D"] and line["dirty"] is True
    assert line["commit"] == world.commits["R1"]
    assert world.state()["current"] == world.tops["D"] and world.state()["marker"] == "D"
    world.git("checkout -- devenv.nix")
    # A prime again, from a new commit.
    world.write_hatch("A-prime")
    world.commits["C3"] = world.commit("system A prime again")
    rc, out = world.vendomat("apply")
    assert rc == 0, out
    assert world.record()[-1]["generation"] == 5 and world.state()["current"] == world.tops["A-prime"]
    began = world.downloads()
    rc, out = world.vendomat("rollback")
    assert rc == 0, out
    assert "skipped generation 4: applied with uncommitted changes" in out, out
    assert "target: generation 3" in out
    state = world.state()
    assert state["current"] == world.tops["A"] and state["gens"].split() == ["1", "2", "3", "4", "5", "6"]
    assert world.downloads() == began
    world.commits["R2"] = world.git("rev-parse HEAD")
    assert world.record()[-1]["commit"] == world.commits["R2"]
    world.log.result("rollback skipped the dirty generation 4 and returned to generation 3's system A")


# W9 R6: the profile rollback -----------------------------------------------------------------------


def test_fast_moves_the_profile_builds_nothing_and_still_commits(world: World) -> None:
    world.write_hatch("A-prime")
    world.commits["C4"] = world.commit("system A prime a third time")
    rc, out = world.vendomat("apply")
    assert rc == 0, out
    assert world.state()["gens"].split()[-1] == "7"
    began = world.downloads()
    head = world.git("rev-parse HEAD")
    rc, out = world.vendomat("rollback --fast")
    assert rc == 0, out
    assert "built " not in out, "--fast builds nothing"
    assert world.downloads() == began
    state = world.state()
    assert state["current"] == world.tops["A"] and state["pointer"] == "system-6-link"
    assert state["gens"].split() == [str(n) for n in range(1, 8)], "no new generation"
    assert default_generation(state) == 6 and state["failed"].strip("[] ") == ""
    assert world.git("log -1 --format=%s") == f"rollback to {world.commits['R2'][:12]}"
    assert world.git("rev-parse HEAD") != head and world.git("status --porcelain") == ""
    assert world.git(f"diff {world.commits['R2']} HEAD -- vendomat.yaml devenv.lock devenv.nix") == "", (
        "the files match the system"
    )
    line = world.record()[-1]
    assert line["generation"] == 6 and line["commit"] == world.git("rev-parse HEAD") and line["dirty"] is False
    world.commits["R3"] = world.git("rev-parse HEAD")
    normal = world.timings["vendomat rollback"]
    world.log.result(
        f"rollback --fast: {world.timings['vendomat rollback --fast']:.1f} s (default rollback: {normal:.1f} s)"
    )


def test_fast_refuses_a_generation_that_is_gone(world: World) -> None:
    # Generation 2 holds A-prime. Make its link disappear, then ask for it.
    head = world.git("rev-parse HEAD")
    world.machine.ok("root", f"cp -P {PROFILES}/system-2-link /root/system-2-link.saved && rm {PROFILES}/system-2-link")
    rc, out = world.vendomat("rollback --fast --generation 2")
    assert rc == 1 and "gone from this machine" in out, out
    assert world.git("rev-parse HEAD") == head and world.git("status --porcelain") == ""
    world.machine.ok("root", f"mv /root/system-2-link.saved {PROFILES}/system-2-link")


# W2 T1 and W9: the boot menu is for recovery -------------------------------------------------------


def test_boot_only_sets_the_next_boot_and_nothing_else(world: World) -> None:
    head = world.git("rev-parse HEAD")
    before = world.state()
    rc, out = world.vendomat("rollback --boot-only --generation 7")
    assert rc == 0, out
    assert re.search(r"next boot only: nixos-\w+\.conf \(generation 7\)", out), out
    assert "No file changed; no commit made." in out, out
    assert world.git("rev-parse HEAD") == head and world.git("status --porcelain") == ""
    assert world.state() == before, "the profile and the machine are untouched"
    oneshot = world.machine.ok(
        "root",
        "tr -cd '[:print:]' < /sys/firmware/efi/efivars/LoaderEntryOneShot-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"
        " || true",
    )
    world.log.result(f"LoaderEntryOneShot: {oneshot.strip()}")
    world.machine.reboot()
    once = world.state()
    assert once["booted"] == world.tops["A-prime"], "generation 7 booted once"
    assert once["pointer"] == "system-6-link", "the profile still points at generation 6"
    world.machine.reboot()
    again = world.state()
    assert again["booted"] == world.tops["A"] and default_generation(again) == 6
    assert again["failed"].strip("[] ") == "" and again["system"] == "running"
    world.log.result("--boot-only: one boot of generation 7, then the default (generation 6) again")


# W9 R5: the path left the target ---------------------------------------------------------------------


def test_rollback_works_after_the_target_path_left_the_store(world: World) -> None:
    top = world.tops["A-prime"]
    # Remove every generation that holds hello (A-prime and D), every root, and the paths, with the
    # machine's own collector.
    world.machine.ok("root", f"nix-env --profile {PROFILES}/system --delete-generations 2 4 5 7")
    world.machine.ok("root", "rm -rf /home/tester/ws/.devenv/gc; rm -f /nix/var/nix/gcroots/auto/*")
    world.machine.ok("root", "nix-store --add-root /nix/var/nix/gcroots/vendomat-launcher -r " + str(world.launcher))
    world.machine.ok("root", "nix-collect-garbage")
    rc, _ = world.machine.run("root", f"test -e {top}")
    assert rc != 0, "A-prime is gone from the machine"
    closure = world.sh(["nix-store", "-qR", top]).stdout.split()
    hello = [path for path in closure if "-hello-" in path]
    assert hello, "the closure of A-prime holds hello"
    rc, left = world.machine.run("root", "ls -d " + " ".join(hello) + " 2>/dev/null")
    assert not left.strip(), f"hello is still in the machine: {left}"
    began = world.downloads()
    rc, out = world.vendomat("rollback")
    assert rc == 0, out
    assert "target: generation 7" in out, out
    assert world.downloads() > began, "the cache supplied the missing paths"
    state = world.state()
    assert state["current"] == top == state["profile"] and state["marker"] == "A-prime" and state["hello"] == "yes"
    assert state["failed"].strip("[] ") == ""
    world.commits["R4"] = world.git("rev-parse HEAD")
    world.log.result(
        f"rollback after the path left the store: {world.timings['vendomat rollback']:.1f} s, "
        f"{world.downloads() - began} downloads"
    )


def test_exact_restores_every_tracked_file(world: World) -> None:
    rc, out = world.vendomat(f"rollback --exact --to {world.commits['A']}")
    assert rc == 0, out
    assert world.git(f"diff {world.commits['A']} HEAD") == "", "the whole tree equals commit A"
    rc, _ = world.machine.run("tester", "cd ws && test -e notes.txt")
    assert rc != 0, "notes.txt did not exist at commit A"
    state = world.state()
    assert state["current"] == world.tops["A"] and state["marker"] == "A"
    assert world.git("log -1 --format=%s") == f"rollback to {world.commits['A'][:12]}"
    assert state["failed"].strip("[] ") == ""
    world.log.result("rollback --exact: the whole tree equals commit A, system A")

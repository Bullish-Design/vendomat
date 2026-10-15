"""Fixtures B2, B5, and B6 for the patched host devenv binary (project 23 slice S2).

Opt in with `VENDOMAT_BINARY_E2E=1`. The binary under test is `VENDOMAT_BINARY_E2E_DEVENV` (the path of
its `bin/devenv`); the default is `devenv` on `PATH`. The control is the stock nixpkgs `pkgs.devenv` of the
pinned Nixpkgs (`VENDOMAT_BINARY_E2E_STOCK` names another stock binary).

- B2 offline entry (VMT-074, patch 0003): a locked git input is in the store, the fetcher cache is empty,
  and the remote is stopped. Stock fails to fetch. The patched binary enters.
- B2b missing store path (VMT-184, patch 0003): two locked git inputs share one source. The store path of the
  source is deleted, and the remote is up. Stock and patched enter. With the remote down, both fail to fetch.
  `VENDOMAT_BINARY_E2E_PREVIOUS` may name a binary from before the fix. That control must fail.
- B5 refusal (VMT-099, patch 0005): `devenv machines install` refuses a machine marked
  `vendomat.mode = "adopt-existing"` before it contacts the target. The target is a running VM. The VM keeps
  its boot id, its `/root`, and its store, and sshd sees no login from devenv.
- B6 catalog: the binary enters a workspace made from the Vendomat workspace template and the catalog, reads
  `vendomat.yaml`, and the catalog marks a machine as adopted.

B5 and B6 need the module-only devenv fork as the workspace's `devenv` input.
`VENDOMAT_BINARY_E2E_MODULES` names it as a devenv input URL. The default is the published tag.
`VENDOMAT_BINARY_E2E_VENDOMAT_TREE` names the Vendomat tree that B6 copies (default: this repository).

VM images, disks, and QEMU scratch go under `/mnt/shared/vendomat-p21/s2/` (`VENDOMAT_BINARY_E2E_STATE`).
Logs go to `$VENDOMAT_FIXTURE_LOGS`. No fixture runs an installer or disko, uses sudo, or selects a host
disk. QEMU comes from the pinned Nixpkgs. The VM boots from direct kernel boot, so it needs no OVMF.
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
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "binary-e2e"
ENABLED = os.environ.get("VENDOMAT_BINARY_E2E") == "1"
pytestmark = pytest.mark.skipif(not ENABLED, reason="opt-in fixture; set VENDOMAT_BINARY_E2E=1")

NIXPKGS = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8"
DEFAULT_MODULES = "git://server/devenv?ref=refs/tags/v2.4.0-vendomat-modules.1&dir=src/modules"
MODULES = os.environ.get("VENDOMAT_BINARY_E2E_MODULES", DEFAULT_MODULES)
VENDOMAT_TREE = Path(os.environ.get("VENDOMAT_BINARY_E2E_VENDOMAT_TREE", str(ROOT)))
#: Owner rule: every VM image, disk, and scratch directory lives here.
STATE = Path(os.environ.get("VENDOMAT_BINARY_E2E_STATE", "/mnt/shared/vendomat-p21/s2/binary-e2e"))
FORBIDDEN_PORT = 19418
MIN_UNALLOCATED_GIB = 15.0
MAX_METADATA_PERCENT = 90.0
DISKO = "github:nix-community/disko/de5708739256238fb912c62f03988815db89ec9a"
FACTER = "github:nix-community/nixos-facter-modules/139dcef4dfc97009629c445806f197883351ab4a"

#: `-F /dev/null` also skips the system ssh_config, which some sandboxes make unreadable.
SSH_OPTIONS = [
    *["-F", "/dev/null", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=no"],
    *["-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=5"],
]
#: QEMU 11 fails at start with "Failed to initialize io_uring" on this host when the locked-memory limit is
#: 8 MiB or unlimited. A 64 KiB limit makes it skip io_uring and start.
MEMLOCK_BYTES = 64 * 1024
_UNITS = {"B": 1 / 2**30, "KiB": 1 / 2**20, "MiB": 1 / 2**10, "GiB": 1.0, "TiB": 2**10}
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_IGNORED_TREE_ENTRIES = {
    ".jj", ".git", ".gitman", ".scratch", ".worktrees", ".devenv", ".direnv", ".venv", ".claude", ".agents",
    "tests", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache",
}  # fmt: skip
# Variables that steer a nested devenv, uv, or Nix. A fixture must not inherit them.
_DROPPED_ENV = {"IN_NIX_SHELL", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "NIX_CONFIG", "NIX_USER_CONF_FILES"}


# --- Records ----------------------------------------------------------------------------------


def _log_root() -> Path:
    given = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if given:
        return Path(given)
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path.home() / ".local/state/vendomat/p21/2026-10-14/s2/binary-e2e" / stamp


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        """Both streams, with terminal colour codes removed."""
        return _ANSI.sub("", self.stdout + self.stderr)


@dataclass
class Logs:
    """Keeps every command, its exit code, and its output outside the repository."""

    root: Path
    count: int = 0
    timings: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Continue the numbering when the directory already holds records, so no run overwrites another.
        self.count = len(list(self.root.glob("*.cmd"))) if self.root.is_dir() else 0

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
        timeout: int = 900,
        qemu: bool = False,
    ) -> Result:
        self.count += 1
        stem = self.root / f"{self.count:03d}-{name}"
        started = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                env=env if env is not None else clean_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                preexec_fn=limit_memlock if qemu else None,
            )
        except subprocess.TimeoutExpired as error:
            stem.with_suffix(".cmd").write_text(json.dumps({"argv": argv, "cwd": str(cwd), "timeout": timeout}) + "\n")
            stem.with_suffix(".stdout").write_text(_text(error.stdout))
            stem.with_suffix(".stderr").write_text(_text(error.stderr))
            raise
        elapsed = time.monotonic() - started
        record = {"argv": argv, "cwd": str(cwd), "returncode": proc.returncode, "seconds": round(elapsed, 1)}
        stem.with_suffix(".cmd").write_text(json.dumps(record, indent=1) + "\n")
        stem.with_suffix(".stdout").write_text(proc.stdout)
        stem.with_suffix(".stderr").write_text(proc.stderr)
        self.timings[name] = elapsed
        return Result(proc.returncode, proc.stdout, proc.stderr)


def _text(value: object) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def limit_memlock() -> None:
    """Run in a child before exec: lower the locked-memory limit so QEMU skips io_uring."""
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (MEMLOCK_BYTES, MEMLOCK_BYTES))


def clean_env(**extra: str) -> dict[str, str]:
    """The caller's environment without the variables that steer a nested devenv, plus `extra`."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("DEVENV_") and key not in _DROPPED_ENV}
    env.update({"NO_COLOR": "1", "TERM": "dumb"})
    env.update(extra)
    return env


# --- Disk guard -------------------------------------------------------------------------------


def root_usage(logs: Logs) -> tuple[float, float]:
    """Return unallocated GiB and the metadata use in percent of the root file system."""
    proc = logs.run("btrfs-usage", ["btrfs", "filesystem", "usage", "/"])
    unallocated = re.search(r"Device unallocated:\s+([\d.]+)(\w+)", proc.stdout)
    metadata = re.search(r"Metadata,\w+: Size:[\d.]+\w+, Used:[\d.]+\w+ \(([\d.]+)%\)", proc.stdout)
    assert unallocated and metadata, f"cannot read btrfs usage:\n{proc.stdout}\n{proc.stderr}"
    return float(unallocated.group(1)) * _UNITS[unallocated.group(2)], float(metadata.group(1))


def disk_guard(logs: Logs, label: str) -> None:
    """Stop before a heavy build when the root file system is short of space (guide 1.4)."""
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


# --- Shared helpers ---------------------------------------------------------------------------


def free_port() -> int:
    while True:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port != FORBIDDEN_PORT:
            return port


def port_is_closed(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


@dataclass
class Lab:
    logs: Logs
    binary: Path
    stock: Path

    def devenv(self, name: str, which: Path, cwd: Path, *args: str, env: dict[str, str] | None = None) -> Result:
        return self.logs.run(name, [str(which), *args], cwd=cwd, env=env, timeout=1800)


@pytest.fixture(scope="session")
def lab() -> Lab:
    given = os.environ.get("VENDOMAT_BINARY_E2E_DEVENV") or shutil.which("devenv")
    if not given:
        pytest.skip("no devenv: set VENDOMAT_BINARY_E2E_DEVENV or put devenv on PATH")
    binary = Path(given)
    assert binary.is_file(), f"VENDOMAT_BINARY_E2E_DEVENV is not a file: {binary}"
    for tool in ("nix", "git"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not on PATH")

    logs = Logs(_log_root())
    logs.root.mkdir(parents=True, exist_ok=True)
    version = logs.run("binary-version", [str(binary), "version"])
    assert version.returncode == 0 and version.stdout.startswith("devenv 2.4.0"), version.stdout + version.stderr
    logs.note(f"binary {binary}: {version.stdout.strip()}")

    stock_given = os.environ.get("VENDOMAT_BINARY_E2E_STOCK")
    if stock_given:
        stock = Path(stock_given)
    else:
        built = logs.run("nix-build-stock", ["nix", "build", "--no-link", "--print-out-paths", f"{NIXPKGS}#devenv"])
        assert built.returncode == 0, built.stderr[-2000:]
        stock = Path(built.stdout.split()[0]) / "bin" / "devenv"
    assert stock.is_file(), f"no stock binary at {stock}"
    stock_version = logs.run("stock-version", [str(stock), "version"])
    logs.note(f"stock {stock}: {stock_version.stdout.strip()}")
    assert stock.resolve() != binary.resolve(), "the binary under test is the stock binary"
    return Lab(logs, binary, stock)


@contextlib.contextmanager
def serve_git(lab: Lab, name: str, srv: Path, port: int, git_env: dict[str, str]) -> Iterator[str]:
    """Serve every bare repository under `srv` with `git daemon` and yield the base URL."""
    url = f"git://127.0.0.1:{port}"
    daemon_log = (lab.logs.root / f"{name}-git-daemon.log").open("w")
    daemon = subprocess.Popen(
        ["git", "daemon", "--reuseaddr", "--export-all", f"--base-path={srv}", "--listen=127.0.0.1"]
        + [f"--port={port}", "--verbose"],
        stdout=daemon_log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        for _ in range(50):
            assert daemon.poll() is None, "git daemon exited"
            listing = lab.logs.run(f"{name}-ls-remote", ["git", "ls-remote", f"{url}/extra.git"], env=git_env)
            if listing.returncode == 0 and "refs/heads/main" in listing.stdout:
                break
            time.sleep(0.2)
        else:
            pytest.fail("git daemon did not serve the repository", pytrace=False)
        yield url
    finally:
        os.killpg(daemon.pid, signal.SIGTERM)
        daemon.wait(timeout=30)
        daemon_log.close()
    assert port_is_closed(port), f"port {port} still accepts connections"


def seed_repo(lab: Lab, name: str, base: Path, files: dict[str, str], *, tag: str | None = None) -> dict[str, str]:
    """Make `base/srv/extra.git` from `files` on branch main. Return the Git environment."""
    srv, work = base / "srv", base / "work"
    for directory in (srv, work):
        directory.mkdir(parents=True)
    git_env = clean_env(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid")
    git_env.update(GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    for relative, text in files.items():
        (work / relative).parent.mkdir(parents=True, exist_ok=True)
        (work / relative).write_text(text)
    steps = [
        ("init", ["git", "init", "-q", "-b", "main", str(work)]),
        ("add", ["git", "-C", str(work), "add", "."]),
        ("commit", ["git", "-C", str(work), "commit", "-q", "-m", "seed"]),
    ]
    if tag:
        steps.append(("tag", ["git", "-C", str(work), "tag", tag]))
    steps.append(("bare", ["git", "clone", "-q", "--bare", str(work), str(srv / "extra.git")]))
    for step, argv in steps:
        made = lab.logs.run(f"{name}-git-{step}", argv, env=git_env)
        assert made.returncode == 0, made.stderr
    (srv / "extra.git" / "git-daemon-export-ok").touch()
    return git_env


# --- B2: offline entry ------------------------------------------------------------------------


def test_b2_patched_binary_enters_offline_with_a_locked_git_input(lab: Lab, tmp_path: Path):
    """VMT-074: source in the store, empty fetcher cache, remote stopped. Stock fails. The patched binary enters."""
    seed = tmp_path / "seed"
    seed.mkdir()
    git_env = seed_repo(lab, "b2", tmp_path, {"data.txt": "b2 data\n"})
    port = free_port()
    url = f"git://127.0.0.1:{port}/extra.git"
    (seed / "devenv.yaml").write_text(
        f"inputs:\n  nixpkgs:\n    url: {NIXPKGS}\n  extra:\n    url: git+{url}\n    flake: false\n"
    )
    shutil.copyfile(FIXTURES / "b2-devenv.nix", seed / "devenv.nix")
    probe = ["shell", "--", "sh", "-c", "echo EXTRA=$EXTRA; cat $EXTRA/data.txt"]

    with serve_git(lab, "b2", tmp_path / "srv", port, git_env):
        # The patched binary locks the input and puts the source in the store while the remote is up.
        warm = tmp_path / "cache-warm"
        warm.mkdir()
        online = lab.devenv(
            "b2-seed", lab.binary, seed, "--no-eval-cache", *probe, env=clean_env(XDG_CACHE_HOME=str(warm))
        )
        assert online.returncode == 0 and "b2 data" in online.output, online.output[-3000:]
        assert (seed / "devenv.lock").is_file()

    # The remote is stopped now.
    assert port_is_closed(port), f"port {port} still accepts connections"

    results: dict[str, Result] = {}
    for label, which in (("stock", lab.stock), ("patched", lab.binary)):
        workspace = tmp_path / f"ws-{label}"
        cache = tmp_path / f"cache-empty-{label}"
        workspace.mkdir()
        cache.mkdir()
        for name in ("devenv.yaml", "devenv.nix", "devenv.lock"):
            shutil.copyfile(seed / name, workspace / name)
        env = clean_env(XDG_CACHE_HOME=str(cache))
        enter = lab.devenv(f"b2-{label}-true", which, workspace, "--no-eval-cache", "shell", "--", "true", env=env)
        results[label] = enter
        if label == "patched":
            see = lab.devenv(f"b2-{label}-probe", which, workspace, "--no-eval-cache", *probe, env=env)
            assert see.returncode == 0, see.output[-3000:]
            assert re.search(r"EXTRA=/nix/store/\S+-source", see.output) and "b2 data" in see.output, see.output

    stock = results["stock"]
    assert stock.returncode != 0, "the stock binary entered with the remote down; the control does not hold"
    assert "Failed to fetch git repository" in stock.output, stock.output[-3000:]
    assert "Connection refused" in stock.output, stock.output[-3000:]
    patched = results["patched"]
    assert patched.returncode == 0, patched.output[-3000:]


# --- B2b: missing store path ------------------------------------------------------------------


def test_b2b_entry_falls_back_to_a_fetch_when_the_store_path_is_gone(lab: Lab, tmp_path: Path):
    """VMT-184: two locked inputs share one source. The store path is deleted and the remote is up. Both enter."""
    seed = tmp_path / "seed"
    seed.mkdir()
    flake = "{ outputs = { self }: { }; }\n"
    files = {"a/flake.nix": flake, "a/data.txt": "b2b data a\n", "b/flake.nix": flake, "b/data.txt": "b2b data b\n"}
    git_env = seed_repo(lab, "b2b", tmp_path, files, tag="v1")
    port = free_port()
    base = f"git+git://127.0.0.1:{port}/extra.git?ref=refs/tags/v1"
    (seed / "devenv.yaml").write_text(
        f"inputs:\n  nixpkgs:\n    url: {NIXPKGS}\n  a:\n    url: {base}&dir=a\n  b:\n    url: {base}&dir=b\n"
    )
    shutil.copyfile(FIXTURES / "b2b-devenv.nix", seed / "devenv.nix")
    probe = ["shell", "--", "sh", "-c", "echo A=$A_DATA; echo B=$B_DATA"]

    def enter(label: str, which: Path, workspace: Path, cache: Path, *flags: str) -> Result:
        return lab.devenv(f"b2b-{label}", which, workspace, *flags, *probe, env=clean_env(XDG_CACHE_HOME=str(cache)))

    def workspace_for(label: str) -> Path:
        workspace = tmp_path / f"ws-{label}"
        workspace.mkdir()
        for name in ("devenv.yaml", "devenv.nix", "devenv.lock"):
            shutil.copyfile(seed / name, workspace / name)
        return workspace

    warm = tmp_path / "cache-warm"
    warm.mkdir()
    with serve_git(lab, "b2b", tmp_path / "srv", port, git_env):
        # Lock the inputs with the stock binary, which leaves the source out of the store. Prefetch puts it in.
        warm_env = clean_env(XDG_CACHE_HOME=str(warm))
        locked = lab.devenv("b2b-lock", lab.stock, seed, "--no-eval-cache", *probe, env=warm_env)
        assert locked.returncode == 0, locked.output[-3000:]
        nodes = json.loads((seed / "devenv.lock").read_text())["nodes"]
        assert nodes["a"]["locked"]["narHash"] == nodes["b"]["locked"]["narHash"], "the inputs do not share a source"
        rev = nodes["a"]["locked"]["rev"]
        prefetch = lab.logs.run(
            "b2b-prefetch",
            ["nix", "flake", "prefetch", "--json", f"git+git://127.0.0.1:{port}/extra.git?rev={rev}"],
            env=warm_env,
        )
        assert prefetch.returncode == 0, prefetch.stderr[-2000:]
        info = json.loads(prefetch.stdout)
        source = info["storePath"]
        assert info["hash"] == nodes["a"]["locked"]["narHash"], "prefetch made another source than the lock names"

        # The source is in the store and the patched binary reuses it.
        present = enter("patched-present", lab.binary, workspace_for("present"), warm)
        assert present.returncode == 0 and "A=b2b data a" in present.output, present.output[-3000:]
        assert Path(source).is_dir()

        # Delete that one fixture path. Nothing roots it and no store path refers to it.
        gone = lab.logs.run("b2b-delete", ["nix", "store", "delete", source])
        assert gone.returncode == 0 and not Path(source).exists(), gone.output
        results = {}
        for label, which in (("stock", lab.stock), ("patched", lab.binary)):
            for flags in ((), ("--no-eval-cache",), ("--refresh-eval-cache",)):
                key = f"{label}-{flags[0].removeprefix('--') if flags else 'cache'}"
                workspace = workspace_for(key)
                if Path(source).exists():
                    lab.logs.run(f"b2b-delete-{key}", ["nix", "store", "delete", source])
                results[key] = enter(key, which, workspace, warm, *flags)
        previous = os.environ.get("VENDOMAT_BINARY_E2E_PREVIOUS")
        if previous:
            if Path(source).exists():
                lab.logs.run("b2b-delete-previous", ["nix", "store", "delete", source])
            results["previous"] = enter("previous", Path(previous), workspace_for("previous"), warm, "--no-eval-cache")

    for key, result in results.items():
        if key == "previous":
            assert result.returncode != 0, "the binary from before the fix entered; the control does not hold"
            assert "is required, but there is no substituter that can build it" in result.output, result.output[-2000:]
        else:
            assert result.returncode == 0, f"{key}: {result.output[-3000:]}"
            assert "A=b2b data a" in result.output and "B=b2b data b" in result.output, result.output

    # The remote is down and the store lacks the source: both binaries fail with the fetch error.
    for label, which in (("stock", lab.stock), ("patched", lab.binary)):
        if Path(source).exists():
            lab.logs.run(f"b2b-delete-down-{label}", ["nix", "store", "delete", source])
        empty = tmp_path / f"cache-empty-{label}"
        empty.mkdir()
        down = enter(f"{label}-down", which, workspace_for(f"{label}-down"), empty, "--no-eval-cache")
        assert down.returncode != 0, f"{label}: entered with the remote down and the source gone"
        assert "Failed to fetch git repository" in down.output, down.output[-2000:]
        assert "Connection refused" in down.output, down.output[-2000:]


# --- B5: install refusal ----------------------------------------------------------------------


@dataclass
class Guest:
    logs: Logs
    ssh_key: Path
    port: int
    serial: Path
    env: dict[str, str]
    proc: subprocess.Popen[bytes] | None = None

    def ssh(self, name: str, command: str, *, timeout: int = 60) -> Result:
        argv = ["ssh", "-n", "-i", str(self.ssh_key), *SSH_OPTIONS, "-p", str(self.port), "root@127.0.0.1", command]
        return self.logs.run(name, argv, env=self.env, timeout=timeout)

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def wait_ssh(self, seconds: int) -> None:
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            assert self.alive(), f"QEMU exited early; see {self.serial}"
            if self.ssh("vm-wait-ssh", "true", timeout=30).returncode == 0:
                return
            time.sleep(5)
        pytest.fail(f"no SSH after {seconds} s; see {self.serial}", pytrace=False)

    def probe(self, label: str) -> dict[str, str]:
        """Read the facts that a refused install must leave alone."""
        command = " ; ".join(
            [
                "echo boot_id=$(cat /proc/sys/kernel/random/boot_id)",
                "echo uptime=$(cut -d' ' -f1 /proc/uptime)",
                "echo root_ls=$(ls -A /root | tr '\\n' ' ')",
                "echo closure_n=$(nix-store -q --requisites /run/current-system | wc -l)",
                "echo rwstore_n=$(ls /nix/.rw-store/store 2>/dev/null | wc -l)",
                "echo sshd_accepted=$(journalctl -u sshd --no-pager | grep -c 'Accepted publickey')",
                "echo kexec=$(test -e /root/kexec && echo present || echo absent)",
            ]
        )
        proc = self.ssh(f"vm-probe-{label}", command)
        assert proc.returncode == 0, proc.output
        facts = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
        self.logs.note(f"vm-probe {label}: {json.dumps(facts)}")
        return facts

    def stop(self) -> None:
        """Power the guest off, then kill the QEMU process group whatever happens."""
        if self.proc is None:
            return
        try:
            if self.alive():
                with contextlib.suppress(Exception):
                    self.ssh("vm-poweroff", "poweroff", timeout=30)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    self.proc.wait(timeout=60)
        finally:
            if self.proc.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait()
            self.logs.note(f"QEMU exit status {self.proc.returncode}")


@contextlib.contextmanager
def booted(guest: Guest, argv: list[str]) -> Iterator[Guest]:
    run_log = guest.logs.root / "vm-run.log"
    (guest.logs.root / "vm-argv.json").write_text(json.dumps({"argv": argv, "port": guest.port}, indent=1) + "\n")
    with run_log.open("wb") as out:
        guest.proc = subprocess.Popen(
            argv,
            env=guest.env,
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
                shutil.copyfile(guest.serial, guest.logs.root / "vm-serial.log")


def write_devenv_yaml(path: Path, *, with_machine_inputs: bool) -> None:
    text = f"inputs:\n  devenv:\n    url: {MODULES}\n  nixpkgs:\n    url: {NIXPKGS}\n"
    if with_machine_inputs:
        text += f"  disko:\n    url: {DISKO}\n    inputs:\n      nixpkgs:\n        follows: nixpkgs\n"
        text += f"  nixos-facter-modules:\n    url: {FACTER}\n"
    path.write_text(text)


def install(lab: Lab, name: str, which: Path, workspace: Path, *machines: str, extra: tuple[str, ...] = ()) -> Result:
    return lab.devenv(name, which, workspace, "machines", "install", *machines, *extra)


def test_b5_install_of_an_adopted_machine_is_refused_before_any_contact(lab: Lab):
    """VMT-099: an adopt-existing machine is refused. The VM keeps its boot id, /root, store, and sshd log."""
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("/dev/kvm is not usable")
    for tool in ("ssh", "ssh-keygen", "btrfs"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} is not on PATH")

    shutil.rmtree(STATE, ignore_errors=True)
    for sub in ("tmp", "vm", "ws"):
        (STATE / sub).mkdir(parents=True)
    env = clean_env(TMPDIR=str(STATE / "tmp"))
    lab.logs.note(f"b5 state {STATE}; modules {MODULES}")

    tools = lab.logs.run("nix-build-qemu", ["nix", "build", "--no-link", "--print-out-paths", f"{NIXPKGS}#qemu_kvm"])
    assert tools.returncode == 0, tools.stderr[-2000:]
    qemu = Path(tools.stdout.split()[0])

    key = STATE / "key"
    keygen = ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "binary-e2e-test-only", "-f", str(key)]
    assert lab.logs.run("ssh-keygen", keygen).returncode == 0
    public = key.with_suffix(".pub").read_text().strip()

    vm_port, closed_port = free_port(), free_port()
    while closed_port == vm_port or not port_is_closed(closed_port):
        closed_port = free_port()
    workspace = STATE / "ws"
    shutil.copyfile(FIXTURES / "box.nix", workspace / "box.nix")
    (workspace / "key.nix").write_text(f'{{ users.users.root.openssh.authorizedKeys.keys = [ "{public}" ]; }}\n')
    template = (FIXTURES / "b5-devenv.nix").read_text()
    for marker, value in (("@VM_PORT@", vm_port), ("@CLOSED_PORT@", closed_port), ("@SSH_KEY@", key)):
        template = template.replace(marker, str(value))
    (workspace / "devenv.nix").write_text(template)
    write_devenv_yaml(workspace / "devenv.yaml", with_machine_inputs=True)

    disk_guard(lab.logs, "machines.box.build.vm")
    built = lab.logs.run(
        "devenv-build-vm",
        [str(lab.binary), "build", "machines.box.build.vm"],
        cwd=workspace,
        env=env,
        timeout=3600,
    )
    assert built.returncode == 0, built.output[-3000:]
    found = re.search(r'"machines.box.build.vm":\s*"(/nix/store/[^"]+)"', built.stdout)
    assert found, built.stdout + built.stderr[-1000:]
    script = next((Path(found.group(1)) / "bin").glob("run-*-vm"))

    serial = STATE / "vm" / "serial.log"
    vm_env = dict(env)
    vm_env.update(
        NIX_DISK_IMAGE=str(STATE / "vm" / "box.qcow2"),
        QEMU_OPTS=f"-display none -serial file:{serial} -monitor none",
        QEMU_NET_OPTS=f"hostfwd=tcp:127.0.0.1:{vm_port}-:22",
        PATH=f"{qemu}/bin:{env['PATH']}",
    )
    guest = Guest(lab.logs, key, vm_port, serial, vm_env)
    with booted(guest, [str(script)]):
        guest.wait_ssh(480)
        state = guest.ssh("vm-system-state", "systemctl is-system-running --wait", timeout=420)
        assert state.stdout.strip() == "running", state.output

        before = guest.probe("before")
        refused_text = 'Refusing to install: machines.running set `vendomat.mode = "adopt-existing"`'
        for label, machines, extra in (
            ("running", ("running",), ()),
            ("running-reboot", ("running",), ("--phases", "reboot")),
            ("unmarked-and-running", ("unmarked", "running"), ()),
        ):
            result = install(lab, f"b5-patched-{label}", lab.binary, workspace, *machines, extra=extra)
            assert result.returncode != 0, f"{label}: the install was not refused"
            assert refused_text in result.output, f"{label}:\n{result.output[-2000:]}"
            assert "made no connection to the target" in result.output, result.output
            assert "machines.unmarked" not in result.output, f"{label} named the unmarked machine"
        after = guest.probe("after")

        # An unmarked machine and a fresh-install machine pass the refusal step. A closed port stops them
        # at the SSH preflight. The control: the stock binary ignores the mark and goes on to the preflight.
        for label, machine in (("unmarked", "unmarked"), ("fresh", "fresh")):
            result = install(lab, f"b5-patched-{label}", lab.binary, workspace, machine)
            assert result.returncode != 0
            assert f"Preflight probe failed on machines.{machine}" in result.output, result.output[-2000:]
            assert "Refusing to install" not in result.output, result.output
        adopted = install(lab, "b5-patched-adopted-closed", lab.binary, workspace, "adopted-closed")
        assert adopted.returncode != 0 and "Refusing to install: machines.adopted-closed" in adopted.output
        control = install(lab, "b5-stock-adopted-closed", lab.stock, workspace, "adopted-closed")
        assert control.returncode != 0, control.output
        assert "Preflight probe failed on machines.adopted-closed" in control.output, control.output[-2000:]
        assert "Refusing to install" not in control.output, control.output
        final = guest.probe("final")

    facts = {"before": before, "after": after, "final": final}
    lab.logs.note(f"b5 facts: {json.dumps(facts)}")
    for label, later in (("after", after), ("final", final)):
        for key_name in ("boot_id", "root_ls", "closure_n", "rwstore_n", "kexec"):
            assert later[key_name] == before[key_name], f"{label}: {key_name} changed: {before} -> {later}"
        assert float(later["uptime"]) > float(before["uptime"]), f"{label}: uptime did not grow"
    assert before["kexec"] == "absent"
    # Each probe is one login. Any other login would be a contact by devenv.
    accepted = [int(point["sshd_accepted"]) for point in (before, after, final)]
    assert accepted == [accepted[0], accepted[0] + 1, accepted[0] + 2], f"unexpected sshd logins: {accepted}"
    assert float(final["uptime"]) > float(after["uptime"])


# --- B6: catalog ------------------------------------------------------------------------------


def copy_vendomat_tree(destination: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in _IGNORED_TREE_ENTRIES or name.startswith("result")}

    shutil.copytree(VENDOMAT_TREE, destination, ignore=ignore, symlinks=True)


def test_b6_patched_binary_enters_a_catalog_workspace(lab: Lab, tmp_path: Path):
    """The workspace template and the catalog work with the patched binary and no fork primop."""
    template_dir = VENDOMAT_TREE / "templates" / "workspace"
    assert (template_dir / "devenv.yaml").is_file(), f"no workspace template in {VENDOMAT_TREE}"
    tree = tmp_path / "vendomat"
    copy_vendomat_tree(tree)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    for name in ("devenv.nix", "vendomat.yaml", ".gitignore"):
        shutil.copyfile(template_dir / name, workspace / name)

    # The template points `vendomat` at the collection. B6 points it at the copy of the tree. It sets the
    # `devenv` input to the module fork. The two inputs that need the network are left out.
    text = (template_dir / "devenv.yaml").read_text()
    assert "git://server/vendomat?ref=release" in text and "follows: vendomat/devenv" in text, text
    text = text.replace("git://server/vendomat?ref=release", f"path:{tree}")
    text = text.replace("    follows: vendomat/devenv", f"    url: {MODULES}")
    text = re.sub(r"  # Python versions.*?(?=imports:)", "", text, flags=re.DOTALL)
    assert "nixpkgs-python" not in text and "rust-overlay" not in text, text
    (workspace / "devenv.yaml").write_text(text)

    closed_port = free_port()
    (workspace / "vendomat.yaml").write_text("programs:\n  - ripgrep\nenv:\n  GREETING: hello-b6\n")
    entered = lab.devenv("b6-shell-true", lab.binary, workspace, "shell", "--", "true")
    if entered.returncode != 0 and "vendomatFromYAML" in entered.output:
        pytest.fail(
            "the catalog needs the fork primop vendomatFromYAML, which the S2 binary lacks:\n" + entered.output[-1500:],
            pytrace=False,
        )
    assert entered.returncode == 0, entered.output[-3000:]
    show = "echo GREETING=$GREETING; command -v rg"
    effect = lab.devenv("b6-effect", lab.binary, workspace, "shell", "--", "bash", "-c", show)
    assert effect.returncode == 0, effect.output[-3000:]
    assert "GREETING=hello-b6" in effect.output, effect.output
    assert re.search(r"^/nix/store/\S+-ripgrep-\S+/bin/rg$", effect.output, re.MULTILINE), effect.output

    # A bad entry stops the shell with a message that names the file, the line, and the field.
    (workspace / "vendomat.yaml").write_text("programs:\n  - vendomat-no-such-package-7319\n")
    bad = lab.devenv("b6-bad-program", lab.binary, workspace, "shell", "--", "true")
    assert bad.returncode != 0
    assert re.search(r"vendomat\.yaml:2:\d+: programs\[0\]: unknown program", bad.output), bad.output[-2000:]

    # The catalog marks a machine as adopted. The patched binary refuses it. The stock binary does not.
    document = f"machines:\n  demo:\n    host: root@127.0.0.1:{closed_port}\n    mode: adopt-existing\n"
    (workspace / "vendomat.yaml").write_text(document)
    refused = install(lab, "b6-patched-install-demo", lab.binary, workspace, "demo")
    assert refused.returncode != 0
    assert 'Refusing to install: machines.demo set `vendomat.mode = "adopt-existing"`' in refused.output
    control = install(lab, "b6-stock-install-demo", lab.stock, workspace, "demo")
    assert control.returncode != 0
    assert "Preflight probe failed on machines.demo" in control.output, control.output[-2000:]

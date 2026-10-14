"""The module-only devenv fork against stock devenv 2.4.0 (project 23, slice S1).

Opt in with `testee verify modules-e2e`. The check materializes the module series into a scratch
tree (`devenv-dist/materialize --series modules`), reads the stock `src/modules` of the upstream pin
from a local mirror, and uses each tree as the `devenv` input of small fixture workspaces. The
`devenv` binary is stock 2.4.0 from `PATH`. Every fixture evaluates; none boots an image (the
`modules-vm` check boots them).

The cases need the network once, to fetch the pinned nixpkgs, disko, and nixos-facter-modules.
They write only under the temporary directory and the log directory.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "modules-e2e"
DEVENV = shutil.which("devenv")
ENABLED = os.environ.get("VENDOMAT_MODULES_E2E") == "1" and all(shutil.which(t) for t in ("nix", "git", "devenv"))
pytestmark = pytest.mark.skipif(
    not ENABLED, reason="Nix and devenv fixture; set VENDOMAT_MODULES_E2E=1 to opt in (testee verify modules-e2e)"
)

NIXPKGS = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8"
DISKO = "github:nix-community/disko/de5708739256238fb912c62f03988815db89ec9a"
FACTER_MODULES = "github:nix-community/nixos-facter-modules/139dcef4dfc97009629c445806f197883351ab4a"

#: The local mirror of upstream devenv. Read only: the fixtures only run `git archive` and `fetch`.
SOURCE = Path(os.environ.get("VENDOMAT_DEVENV_SOURCE") or Path.home() / "vendor" / "devenv")

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# --- Command log ------------------------------------------------------------------------------


def _log_dir() -> Path:
    given = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if given:
        return Path(given)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path.home() / ".local" / "state" / "vendomat" / "p21" / "2026-10-14" / "s1" / "modules-e2e" / stamp


@dataclass
class Proc:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def text(self) -> str:
        return ANSI.sub("", self.stdout + self.stderr)


class Recorder:
    """Keep each command (argv, exit code, output) and each observed value outside the repository."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.count = 0

    def run(self, label: str, argv: list[str], cwd: Path, *, timeout: int = 3600) -> Proc:
        env = {k: v for k, v in os.environ.items() if k != "UV_PROJECT_ENVIRONMENT"}
        env["NO_COLOR"] = "1"
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env, check=False)
        self.count += 1
        stem = f"{self.count:03d}-{label}"
        header = f"$ {' '.join(argv)}\n# cwd: {cwd}\n# exit: {proc.returncode}\n"
        body = f"{header}--- stdout\n{proc.stdout}\n--- stderr\n{proc.stderr}\n"
        (self.directory / f"{stem}.log").write_text(body)
        return Proc(argv, proc.returncode, proc.stdout, proc.stderr)

    def note(self, name: str, value: object) -> None:
        with (self.directory / "observations.txt").open("a") as handle:
            handle.write(f"{name} = {value}\n")


@pytest.fixture(scope="module")
def rec() -> Recorder:
    return Recorder(_log_dir())


# --- Trees ------------------------------------------------------------------------------------


def _upstream_pin() -> str:
    for line in (ROOT / "devenv-dist" / "UPSTREAM").read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "commit":
            return value.strip()
    raise AssertionError("devenv-dist/UPSTREAM has no commit line")


@pytest.fixture(scope="module")
def trees(tmp_path_factory: pytest.TempPathFactory, rec: Recorder) -> dict[str, Path]:
    """Return the `src/modules` directory of the module tree and of the stock tree."""
    if not (SOURCE / ".git").exists() and not (SOURCE / "HEAD").exists():
        pytest.fail(f"no local devenv mirror at {SOURCE}; set VENDOMAT_DEVENV_SOURCE")
    base = tmp_path_factory.mktemp("trees")
    forked = base / "modules"
    forked.mkdir()
    made = rec.run(
        "materialize-modules",
        [
            sys.executable,
            "-I",
            str(ROOT / "devenv-dist" / "materialize"),
            str(forked),
            "--series",
            "modules",
            "--source",
            str(SOURCE),
            "--verify",
        ],
        base,
    )
    assert made.returncode == 0, made.text
    stock = base / "stock"
    stock.mkdir()
    pin = _upstream_pin()
    archive = subprocess.run(
        ["git", "-C", str(SOURCE), "archive", pin, "src/modules"], capture_output=True, check=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(stock, filter="data")
    rec.note("fork tree", forked)
    rec.note("stock tree", f"{stock} (upstream {pin})")
    return {"modules": forked / "src" / "modules", "stock": stock / "src" / "modules"}


# --- Workspaces -------------------------------------------------------------------------------


class Workspace:
    def __init__(
        self,
        base: Path,
        name: str,
        tree: Path,
        rec: Recorder,
        nix_text: str,
        *,
        files: tuple[str, ...] = (),
        extra: dict[str, str] | None = None,
        inputs: bool = True,
    ) -> None:
        self.root = base / name
        self.root.mkdir()
        self.name = name
        self.rec = rec
        yaml = [
            "inputs:",
            f"  devenv:\n    url: path:{tree}",
            f"  nixpkgs:\n    url: {NIXPKGS}",
        ]
        if inputs:
            yaml += [
                f"  disko:\n    url: {DISKO}\n    inputs:\n      nixpkgs:\n        follows: nixpkgs",
                f"  nixos-facter-modules:\n    url: {FACTER_MODULES}",
            ]
        (self.root / "devenv.yaml").write_text("\n".join(yaml) + "\n")
        (self.root / "devenv.nix").write_text(nix_text)
        for fixture in files:
            if fixture == "facter.json":
                target = self.root / ".machines" / "target"
                target.mkdir(parents=True)
                shutil.copy2(FIXTURES / fixture, target / fixture)
            else:
                shutil.copy2(FIXTURES / fixture, self.root / fixture)
        for filename, text in (extra or {}).items():
            (self.root / filename).write_text(text)

    def devenv(self, label: str, *args: str, binary: str | None = None) -> Proc:
        argv = [binary or DEVENV or "devenv", "--no-tui", *args]
        return self.rec.run(f"{self.name}-{label}", argv, self.root)

    def eval(self, label: str, *attrs: str) -> dict[str, object]:
        """Evaluate attributes with `devenv eval` and return the JSON object."""
        proc = self.devenv(label, "eval", *attrs)
        assert proc.returncode == 0, proc.text
        start = proc.stdout.index("{")
        value, _ = json.JSONDecoder().raw_decode(proc.stdout[start:])
        assert isinstance(value, dict)
        return value


PLAIN_NIX = """\
{ ... }: {
  machines.box = { system = "x86_64-linux"; hardware.facter = null; nixos = ./box.nix; };
  machines.iso = { system = "x86_64-linux"; hardware.facter = null; nixos = ./iso.nix; };
  machines.target = { system = "x86_64-linux"; nixos = ./target.nix; };
}
"""

#: Machines for the fork-only options. Each `iso.modules` entry changes only the loader timeout.
FORK_NIX = """\
{ ... }: {
  machines.box = { system = "x86_64-linux"; hardware.facter = null; nixos = ./box.nix; };
  machines.boxplain = {
    system = "x86_64-linux"; hardware.facter = null; nixos = ./box.nix;
    iso.modules = [ { boot.loader.timeout = 5; } ];
  };
  machines.boxforce = {
    system = "x86_64-linux"; hardware.facter = null; nixos = ./box.nix;
    iso.modules = [ ({ lib, ... }: { boot.loader.timeout = lib.mkForce 5; }) ];
  };
  machines.isomachine = { system = "x86_64-linux"; hardware.facter = null; nixos = ./iso.nix; };
  machines.modefresh = { system = "x86_64-linux"; hardware.facter = null; vendomat.mode = "fresh-install"; };
  machines.modeadopt = { system = "x86_64-linux"; hardware.facter = null; vendomat.mode = "adopt-existing"; };
  machines.modenone = { system = "x86_64-linux"; hardware.facter = null; };
}
"""

MERGE_NIX = """\
{ ... }: {
  imports = [ ./m1.nix ./m2.nix ./defaults.nix ];
  machines.box.system = "x86_64-linux";
  machines.box.hardware.facter = null;
}
"""

#: An attribute set.
MERGE_M1 = """\
{ ... }: {
  machines.box.nixos = {
    boot.loader.systemd-boot.enable = true;
    boot.loader.efi.canTouchEfiVariables = true;
    fileSystems."/" = { device = "/dev/vda1"; fsType = "ext4"; };
    services.openssh.enable = true;
    environment.etc."t4-m1".text = "from m1\\n";
    system.stateVersion = "26.11";
  };
}
"""

#: A function.
MERGE_M2 = """\
{ ... }: {
  machines.box.nixos = { pkgs, ... }: {
    environment.systemPackages = [ pkgs.hello ];
    environment.etc."t4-m2".text = "from m2\\n";
  };
}
"""

#: A default module for every machine.
MERGE_DEFAULTS = """\
{ lib, ... }: {
  options.machines = lib.mkOption {
    type = lib.types.attrsOf (lib.types.submodule {
      nixos = { pkgs, ... }: {
        environment.etc."t4-default".text = "default for every machine\\n";
        environment.systemPackages = [ pkgs.jq ];
      };
    });
  };
}
"""

MACHINE_FILES = ("box.nix", "iso.nix", "target.nix", "facter.json")


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("workspaces")


@pytest.fixture(scope="module")
def plain(base: Path, trees: dict[str, Path], rec: Recorder) -> dict[str, Workspace]:
    """The same plain machines on both trees: a box, an ISO machine, and a facter plus disko target."""
    return {
        key: Workspace(base, f"plain-{key}", trees[key], rec, PLAIN_NIX, files=MACHINE_FILES)
        for key in ("modules", "stock")
    }


@pytest.fixture(scope="module")
def fork(base: Path, trees: dict[str, Path], rec: Recorder) -> Workspace:
    return Workspace(base, "fork", trees["modules"], rec, FORK_NIX, files=MACHINE_FILES)


# --- Fixture 1: merge (W2 T4) -----------------------------------------------------------------


def test_merge_nixos_definitions(base: Path, trees: dict[str, Path], rec: Recorder) -> None:
    """An attribute set, a function, and a default module all reach /etc of `build.nixos`."""
    files = {"m1.nix": MERGE_M1, "m2.nix": MERGE_M2, "defaults.nix": MERGE_DEFAULTS}
    fork = Workspace(base, "merge-modules", trees["modules"], rec, MERGE_NIX, extra=files)
    got = fork.eval(
        "eval",
        "machines.box._nixosEval.config.environment.etc.t4-m1.text",
        "machines.box._nixosEval.config.environment.etc.t4-m2.text",
        "machines.box._nixosEval.config.environment.etc.t4-default.text",
        "machines.box._nixosEval.config.services.openssh.enable",
        "machines.box.build.nixos.drvPath",
        "machines.box._nixosEval.config.system.build.toplevel.drvPath",
    )
    prefix = "machines.box._nixosEval.config."
    assert got[prefix + "environment.etc.t4-m1.text"] == "from m1\n"
    assert got[prefix + "environment.etc.t4-m2.text"] == "from m2\n"
    assert got[prefix + "environment.etc.t4-default.text"] == "default for every machine\n"
    assert got[prefix + "services.openssh.enable"] is True
    # `build.nixos` is the same toplevel that holds those /etc entries.
    assert got["machines.box.build.nixos.drvPath"] == got[prefix + "system.build.toplevel.drvPath"]
    rec.note("merge: fork build.nixos drvPath", got["machines.box.build.nixos.drvPath"])

    stock = Workspace(base, "merge-stock", trees["stock"], rec, MERGE_NIX, extra=files)
    control = stock.devenv("eval", "eval", "machines.box.build.nixos.drvPath")
    assert control.returncode != 0
    assert "Cannot merge definitions of `machines.box.nixos'" in control.text
    rec.note("merge: stock control", f"rc={control.returncode}, Cannot merge definitions of `machines.box.nixos'")


# --- Fixture 2: build.nixos unchanged (W7 H1) -------------------------------------------------


def test_build_nixos_is_unchanged(plain: dict[str, Workspace], rec: Recorder) -> None:
    """The fork and stock evaluate the same toplevel for a plain machine and for a facter plus disko machine."""
    attrs = [f"machines.{name}.build.nixos.outPath" for name in ("box", "iso", "target")]
    forked = plain["modules"].eval("eval", *attrs)
    stock = plain["stock"].eval("eval", *attrs)
    for attr in attrs:
        assert str(forked[attr]).startswith("/nix/store/")
        assert forked[attr] == stock[attr], attr
        rec.note(f"build.nixos unchanged: {attr}", forked[attr])


# --- Fixture 3: no images by default (W7, W8 Q6) ----------------------------------------------


def test_no_images_by_default(plain: dict[str, Workspace], rec: Recorder) -> None:
    """`devenv build machines.NAME` returns the stock outputs and no VM or ISO."""
    results = {}
    for key in ("modules", "stock"):
        proc = plain[key].devenv("build", "build", "machines.target")
        assert proc.returncode == 0, proc.text
        start = proc.stdout.index("{")
        value, _ = json.JSONDecoder().raw_decode(proc.stdout[start:])
        results[key] = value
    forked, stock = results["modules"], results["stock"]
    assert forked == stock
    names = sorted(forked)
    assert names == [
        "machines.target.build.deployer",
        "machines.target.build.diskoFormatScript",
        "machines.target.build.diskoMountScript",
        "machines.target.build.diskoScript",
        "machines.target.build.nixos",
    ]
    for name, path in forked.items():
        assert not name.endswith((".vm", ".iso")), name
        assert not path.endswith(".iso") and "-vm" not in path.rsplit("/", 1)[-1], path
    rec.note("no images: devenv build machines.target outputs", json.dumps(forked, indent=1))


# --- Fixture 4: ISO policy (W7 H6, W8 Q2, VMT-107) --------------------------------------------


def test_iso_policy(fork: Workspace, rec: Recorder) -> None:
    """The ISO machine keeps its own image; `iso.modules` changes the image only with `mkForce`."""
    own = "machines.isomachine._nixosEval.config.system.build.isoImage.drvPath"
    got = fork.eval(
        "eval",
        "machines.isomachine.build.iso.drvPath",
        own,
        "machines.box.build.iso.drvPath",
        "machines.boxplain.build.iso.drvPath",
        "machines.boxforce.build.iso.drvPath",
        "machines.box.build.nixos.drvPath",
        "machines.boxplain.build.nixos.drvPath",
        "machines.boxforce.build.nixos.drvPath",
    )
    for key, value in got.items():
        rec.note(f"iso: {key}", value)
    assert got["machines.isomachine.build.iso.drvPath"] == got[own]
    # A plain value loses to the six overrides at priority 60, so the image stays the same.
    assert got["machines.boxplain.build.iso.drvPath"] == got["machines.box.build.iso.drvPath"]
    # `lib.mkForce` (priority 50) wins, so the image changes.
    assert got["machines.boxforce.build.iso.drvPath"] != got["machines.box.build.iso.drvPath"]
    # The machine's own system never depends on `iso.modules`.
    assert got["machines.boxplain.build.nixos.drvPath"] == got["machines.box.build.nixos.drvPath"]
    assert got["machines.boxforce.build.nixos.drvPath"] == got["machines.box.build.nixos.drvPath"]


# --- Fixture 5: the mode option (m5) ----------------------------------------------------------


def test_mode_option(fork: Workspace, rec: Recorder) -> None:
    """`machines.NAME.vendomat.mode` returns the set value, null by default, and reaches `machinesMeta`."""
    got = fork.eval(
        "eval",
        "machines.modefresh.vendomat.mode",
        "machines.modeadopt.vendomat.mode",
        "machines.modenone.vendomat.mode",
        "machinesMeta.modefresh.vendomat.mode",
        "machinesMeta.modeadopt.vendomat.mode",
        "machinesMeta.modenone.vendomat.mode",
    )
    for key, value in got.items():
        rec.note(f"mode: {key}", value)
    assert got["machines.modefresh.vendomat.mode"] == "fresh-install"
    assert got["machines.modeadopt.vendomat.mode"] == "adopt-existing"
    assert got["machines.modenone.vendomat.mode"] is None
    assert got["machinesMeta.modefresh.vendomat.mode"] == "fresh-install"
    assert got["machinesMeta.modeadopt.vendomat.mode"] == "adopt-existing"
    assert got["machinesMeta.modenone.vendomat.mode"] is None


# --- Fixture 6: no version warning (VMT-118) --------------------------------------------------

WARNING = "is newer than devenv input"


def _release_devenv(rec: Recorder, cwd: Path) -> str:
    """Return the devenv 2.4.0 package of the pinned nixpkgs.

    The `devenv` on `PATH` may be a development build (version `2.4.0+<commit>`). Such a build never
    prints the warning, so it cannot prove the fix. The nixpkgs package reports plain `2.4.0`.
    """
    built = rec.run("nix-build-devenv", ["nix", "build", "--no-link", "--print-out-paths", f"{NIXPKGS}#devenv"], cwd)
    assert built.returncode == 0, built.text
    binary = built.stdout.strip().splitlines()[-1] + "/bin/devenv"
    version = rec.run("release-devenv-version", [binary, "--version"], cwd)
    assert version.stdout.strip().startswith("devenv 2.4.0") and "+" not in version.stdout, version.text
    return binary


def test_no_version_warning(base: Path, trees: dict[str, Path], rec: Recorder) -> None:
    """Shell entry on the module tree prints no `newer than devenv input` line; stock does."""
    spaces = {
        key: Workspace(base, f"shell-{key}", trees[key], rec, "{ ... }: { }\n", inputs=False)
        for key in ("modules", "stock")
    }
    release = _release_devenv(rec, base)
    forked = spaces["modules"].devenv("release", "shell", "--", "true", binary=release)
    assert forked.returncode == 0, forked.text
    assert WARNING not in forked.text
    # Control: stock modules say 2.3.1, so a plain 2.4.0 binary warns.
    stock = spaces["stock"].devenv("release", "shell", "--", "true", binary=release)
    assert stock.returncode == 0, stock.text
    rec.note("version warning: stock control prints it", WARNING in stock.text)
    assert WARNING in stock.text, stock.text
    # The `devenv` on PATH too (it may be a development build, so only the positive assertion holds).
    on_path = spaces["modules"].devenv("path", "shell", "--", "true")
    assert on_path.returncode == 0, on_path.text
    assert WARNING not in on_path.text


@pytest.fixture(autouse=True, scope="module")
def _announce(rec: Recorder) -> Iterator[None]:
    rec.note("devenv on PATH", DEVENV)
    yield

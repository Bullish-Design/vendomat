"""The Vendomat devenv module against a real `devenv` (Step 3, `VMOD-*`, `FACE-*`, `DESC-*`).

Opt in with `testee check e2e`. Each case writes a small devenv workspace that imports
`inputs.vendomat.devenvModules.default` from this repository, plus library flakes in a temporary
directory, then evaluates with the host `devenv`. The cases need the network once, to fetch the
pinned nixpkgs, disko, and Home Manager. They never write outside the temporary directory.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEVENV = os.environ.get("VENDOMAT_DEVENV") or shutil.which("devenv")
ENABLED = os.environ.get("VENDOMAT_E2E") == "1" and all(shutil.which(t) for t in ("nix", "git")) and bool(DEVENV)
pytestmark = pytest.mark.skipif(not ENABLED, reason="Nix and devenv fixture; set VENDOMAT_E2E=1 to opt in")

NIXPKGS = "github:NixOS/nixpkgs/e7439b6b14ad3cc35d05608ebca9bce01a25f5f8"
DISKO = "github:nix-community/disko/de5708739256238fb912c62f03988815db89ec9a"
HOME_MANAGER = "github:nix-community/home-manager/6b88c12cc6d234de4888f5d21076fb11199d0844"

GIT = ["git", "-c", "user.email=fixture@example.invalid", "-c", "user.name=fixture", "-c", "commit.gpgsign=false"]

# --- Library fixtures -------------------------------------------------------------------------

KNAPPY = """\
{
  inputs.nixpkgs.url = "%(nixpkgs)s";
  outputs = { self, nixpkgs }:
    let forAll = nixpkgs.lib.genAttrs [ "x86_64-linux" ];
    in {
      packages = forAll (system: {
        default = nixpkgs.legacyPackages.${system}.writeShellScriptBin "knappy" ''
          case "$1" in
            serve) echo "knappy serving on $3"; exec sleep 3600 ;;
            *) echo "knappy $*" ;;
          esac
        '';
      });
      vendomat = {
        name = "knappy";
        packages = pkgs: [ self.packages.${pkgs.stdenv.hostPlatform.system}.default ];
        options = lib: {
          port = lib.mkOption { type = lib.types.port; default = 8080; };
        };
        service = { pkgs, cfg }: { exec = "knappy serve --port ${toString cfg.port}"; };
        extra = { cfg, pkgs, lib }: {
          devenv.env.KNAPPY_EXTRA = "devenv";
          nixos.networking.firewall.allowedTCPPorts = [ cfg.port ];
          homeManager.home.sessionVariables.KNAPPY_EXTRA = "home-manager";
        };
      };
    };
}
"""

#: A library that writes its faces by hand, with no description.
HAND = """\
{
  outputs = { self }: {
    devenvModules.default = { config, lib, ... }: {
      options.vendomat.libs.hand.enable = lib.mkEnableOption "hand";
      config = lib.mkIf config.vendomat.libs.hand.enable { env.HAND_FACE = "devenv"; };
    };
    nixosModules.default = { config, lib, ... }: {
      options.vendomat.libs.hand.enable = lib.mkEnableOption "hand";
      config = lib.mkIf config.vendomat.libs.hand.enable { environment.sessionVariables.HAND_FACE = "nixos"; };
    };
  };
}
"""

#: Same library name as knappy.
CLASH = """\
{ outputs = { self }: { vendomat = { name = "knappy"; packages = pkgs: [ ]; }; }; }
"""

#: Both a description and a hand-written face.
BOTH = """\
{ outputs = { self }: {
  vendomat = { name = "both"; packages = pkgs: [ ]; };
  devenvModules.default = { ... }: { };
}; }
"""

NONAME = "{ outputs = { self }: { vendomat = { packages = pkgs: [ ]; }; }; }\n"
BADKEY = '{ outputs = { self }: { vendomat = { name = "badkey"; packages = pkgs: [ ]; colour = "red"; }; }; }\n'
OWNENABLE = """\
{ outputs = { self }: { vendomat = {
  name = "own";
  packages = pkgs: [ ];
  options = lib: { enable = lib.mkOption { default = true; }; };
}; }; }
"""

LIBRARIES = {
    "knappy": KNAPPY % {"nixpkgs": NIXPKGS},
    "hand": HAND,
    "clash": CLASH,
    "both": BOTH,
    "noname": NONAME,
    "badkey": BADKEY,
    "ownenable": OWNENABLE,
}

# --- Host fixtures ----------------------------------------------------------------------------

#: Each body chunk is its own module, so two chunks may both set one option without a syntax error.
BASE_NIXOS = """\
{ config, lib, pkgs, ... }: {
  imports = [
    inputs.home-manager.nixosModules.home-manager
%(chunks)s
  ];
  boot.loader.systemd-boot.enable = true;
  users.users.alice = { isNormalUser = true; };
  home-manager.users.alice.home.stateVersion = "24.11";
  system.stateVersion = "24.11";
}
"""

ADOPT_FS = """\
fileSystems."/" = { device = "/dev/disk/by-uuid/11111111-2222-3333-4444-555555555555"; fsType = "ext4"; };
fileSystems."/boot" = { device = "/dev/disk/by-uuid/AAAA-BBBB"; fsType = "vfat"; };
"""

DISKO_MAIN = """\
disko.devices.disk.%(name)s = {
  type = "disk";
  device = "%(device)s";
  content = { type = "gpt"; partitions = {
    ESP = { size = "512M"; type = "EF00"; uuid = "aaaaaaaa-0000-4000-8000-000000000001";
      content = { type = "filesystem"; format = "vfat"; mountpoint = "/boot"; extraArgs = [ "-i" "AAAABBBB" ]; }; };
    root = { size = "100%%"; uuid = "aaaaaaaa-0000-4000-8000-000000000002";
      content = {
        type = "filesystem"; format = "ext4"; mountpoint = "/";
        extraArgs = [ "-U" "11111111-2222-3333-4444-555555555555" ];
      }; };
  }; };
};
fileSystems."/".device = lib.mkForce "/dev/disk/by-uuid/11111111-2222-3333-4444-555555555555";
fileSystems."/boot".device = lib.mkForce "/dev/disk/by-uuid/AAAA-BBBB";
"""

TARGET = "/dev/disk/by-id/nvme-FAKE_TARGET_0001"


def disk(role: str, by_id: str, full: bool = True) -> str:
    extra = (
        ' model = "FAKE"; serial = "0001"; sizeBytes = 1000000000000;' if (full and role == "install-target") else ""
    )
    return f'{{ byId = "{by_id}"; role = "{role}";{extra} }}'


def fresh(body: str = "", disks: str | None = None, name: str = "main", device: str = TARGET) -> dict:
    return {
        "mode": "fresh-install",
        "disks": disks
        or f"main = {disk('install-target', TARGET)}; old = {disk('keep', '/dev/disk/by-id/nvme-FAKE_OLD_0002')};",
        "chunks": [DISKO_MAIN % {"name": name, "device": device}] + ([body] if body else []),
    }


def adopt(body: str = "", disks: str | None = None, extra_chunks: list[str] | None = None) -> dict:
    return {
        "mode": "adopt-existing",
        "disks": disks or f"sys = {disk('existing-system', '/dev/disk/by-id/nvme-FAKE_SYS_0003')};",
        "chunks": [ADOPT_FS] + ([body] if body else []) + (extra_chunks or []),
    }


class Workspace:
    def __init__(self, tmp: Path, libs: list[str]) -> None:
        self.root = tmp / "ws"
        self.root.mkdir()
        # A curated copy: a `path:` input would otherwise take the whole checkout, venv included.
        self.vendomat = tmp / "vendomat"
        self.vendomat.mkdir()
        for name in ("flake.nix", "flake.lock", "pyproject.toml", "README.md"):
            if (ROOT / name).exists():
                shutil.copy2(ROOT / name, self.vendomat / name)
        for name in ("src", "nix"):
            shutil.copytree(ROOT / name, self.vendomat / name, ignore=shutil.ignore_patterns("__pycache__"))
        self.libs = libs
        self.env = {"HOME": os.environ["HOME"], "PATH": os.environ["PATH"]}
        for name in libs:
            repo = tmp / "libs" / name
            repo.mkdir(parents=True)
            (repo / "flake.nix").write_text(LIBRARIES[name])
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run([*GIT, "commit", "-q", "-m", "init"], cwd=repo, check=True)
        self.libdir = tmp / "libs"
        self.write_yaml()

    def write_yaml(self) -> None:
        lines = [
            "inputs:",
            f"  nixpkgs:\n    url: {NIXPKGS}",
            f"  vendomat:\n    url: path:{self.vendomat}",
            f"  disko:\n    url: {DISKO}\n    inputs:\n      nixpkgs:\n        follows: nixpkgs",
            f"  home-manager:\n    url: {HOME_MANAGER}\n    inputs:\n      nixpkgs:\n        follows: nixpkgs",
        ]
        for name in self.libs:
            lines.append(f"  {name}:\n    url: git+file://{self.libdir}/{name}")
        (self.root / "devenv.yaml").write_text("\n".join(lines) + "\n")

    def write_nix(self, host: dict | None, workspace_extra: str = "", libs_on: str = "") -> None:
        inv = ""
        if host is not None:
            chunks = list(host["chunks"]) + ([libs_on] if libs_on else [])
            rendered = "\n".join("    { " + c.replace("\n", "\n      ") + " }" for c in chunks)
            inv = textwrap.dedent(
                f"""
                vendomat.inventory.test = {{
                  mode = "{host["mode"]}";
                  disks = {{ {host["disks"]} }};
                  nixos = {BASE_NIXOS % {"chunks": rendered}};
                }};
                machines.test = {{ system = "x86_64-linux"; target.host = "root@localhost"; hardware.facter = null; }};
                """
            )
        (self.root / "devenv.nix").write_text(
            "{ inputs, lib, ... }: {\n"
            "  imports = [ inputs.vendomat.devenvModules.default ];\n"
            "  vendomat.check.enable = false;\n" + inv + workspace_extra + "\n}\n"
        )

    def eval(self, attr: str):
        shutil.rmtree(self.root / ".devenv", ignore_errors=True)
        done = subprocess.run(
            [str(DEVENV), "--no-eval-cache", "eval", attr],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=1200,
        )
        return done

    def value(self, attr: str):
        done = self.eval(attr)
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)[attr]


TOPLEVEL = "machines.test._nixosEval.config.system.build.toplevel.drvPath"
HM = "machines.test._nixosEval.config.home-manager.users.alice.home.activationPackage.drvPath"
SHELL = "shell.drvPath"


@pytest.fixture
def ws_factory(tmp_path):
    def make(libs: list[str]) -> Workspace:
        return Workspace(tmp_path, libs)

    return make


# --- Inertness (FACE-002, FACE-007, VMOD-002) ---------------------------------------------------


def test_a_disabled_described_library_changes_no_derivation(ws_factory):
    ws = ws_factory(["knappy"])
    ws.write_nix(adopt())
    with_lib = {a: ws.value(a) for a in (SHELL, TOPLEVEL, HM)}
    # Remove the library input and rebuild in the same directory (the shell derivation names its path).
    ws.libs = []
    ws.write_yaml()
    (ws.root / "devenv.lock").unlink(missing_ok=True)
    without = {a: ws.value(a) for a in (SHELL, TOPLEVEL, HM)}
    assert with_lib == without


# --- Enabled faces (DESC-003, FACE-005) ----------------------------------------------------------


def test_enabled_faces_install_packages_and_units(ws_factory):
    ws = ws_factory(["knappy"])
    on = "vendomat.libs.knappy = { enable = true; port = 7070; service.enable = true; };\n"
    hm = "home-manager.users.alice.vendomat.libs.knappy = { enable = true; port = 7071; service.enable = true; };\n"
    ws.write_nix(adopt(), workspace_extra="  vendomat.libs.knappy.enable = true;\n", libs_on=on + hm)
    cfg = "machines.test._nixosEval.config"
    # devenv
    assert ws.value("env.KNAPPY_EXTRA") == "devenv"
    assert "knappy" in ws.value("processes.knappy.exec")
    # NixOS
    exec_start = ws.value(f"{cfg}.systemd.services.knappy.serviceConfig.ExecStart")
    assert exec_start.endswith("-knappy-start")
    assert ws.value(f"{cfg}.networking.firewall.allowedTCPPorts") == [7070]
    # Home Manager
    user_exec = ws.value(f"{cfg}.home-manager.users.alice.systemd.user.services.knappy.Service.ExecStart")
    user_exec = user_exec[0] if isinstance(user_exec, list) else user_exec
    assert user_exec.endswith("-knappy-start")
    assert ws.value(f"{cfg}.home-manager.users.alice.home.sessionVariables.KNAPPY_EXTRA") == "home-manager"


def test_options_exist_only_under_vendomat_libs(ws_factory):
    ws = ws_factory(["knappy"])
    ws.write_nix(adopt(), workspace_extra="  programs.knappy.enable = true;\n")
    done = ws.eval("shell.drvPath")
    assert done.returncode != 0  # no programs.knappy option exists


def test_a_hand_written_face_works_without_a_description(ws_factory):
    ws = ws_factory(["hand"])
    ws.write_nix(
        adopt(), workspace_extra="  vendomat.libs.hand.enable = true;\n", libs_on="vendomat.libs.hand.enable = true;\n"
    )
    assert ws.value("env.HAND_FACE") == "devenv"
    cfg = "machines.test._nixosEval.config"
    assert ws.value(f"{cfg}.environment.sessionVariables.HAND_FACE") == "nixos"


# --- Description errors (VMOD-013, DESC-002) -----------------------------------------------------


@pytest.mark.parametrize(
    "libs, message",
    [
        (["knappy", "clash"], "two inputs use the same library name"),
        (["both"], "export both a `vendomat` description and a hand-written face"),
        (["noname"], "exports a vendomat description with no `name`"),
        (["badkey"], "unknown description key(s) colour"),
        (["ownenable"], "must not define `enable` or `service`"),
    ],
)
def test_a_bad_description_stops_evaluation_and_names_the_input(ws_factory, libs, message):
    ws = ws_factory(libs)
    ws.write_nix(None, workspace_extra="  vendomat.libs.own.enable = false;\n" if "ownenable" in libs else "")
    done = ws.eval("shell.drvPath")
    assert done.returncode != 0
    assert message in done.stderr, done.stderr[-1500:]


# --- Machine guard (VMOD-011, VMOD-016) ----------------------------------------------------------


def test_a_good_fresh_and_a_good_adopted_host_evaluate(ws_factory):
    fresh_ws = ws_factory([])
    fresh_ws.write_nix(fresh())
    assert fresh_ws.value(TOPLEVEL).endswith(".drv")


def test_a_good_adopted_host_evaluates(ws_factory):
    ws = ws_factory([])
    ws.write_nix(adopt())
    assert ws.value(TOPLEVEL).endswith(".drv")


BAD = [
    (
        "fresh disko disk is a kernel name",
        fresh(name="main", device="/dev/nvme0n1"),
        "not an install-target of the inventory",
    ),
    (
        "fresh disko disk name is not in the inventory",
        fresh(name="other"),
        "not an install-target of the inventory",
    ),
    (
        "fresh disko disk is the keep disk",
        fresh(name="old", device="/dev/disk/by-id/nvme-FAKE_OLD_0002"),
        "not an install-target of the inventory",
    ),
    (
        "fresh target lacks model and serial",
        fresh(disks=f"main = {disk('install-target', TARGET, full=False)};"),
        "needs model, serial, and sizeBytes",
    ),
    (
        "fresh host has no install-target",
        fresh(disks=f"old = {disk('keep', '/dev/disk/by-id/nvme-FAKE_OLD_0002')};"),
        'needs a disk with role "install-target"',
    ),
    (
        "fresh mount uses a kernel name",
        fresh(body='fileSystems."/data" = { device = "/dev/sda1"; fsType = "ext4"; };'),
        "by-partlabel or a kernel name",
    ),
    (
        "fresh mount uses by-partlabel",
        fresh(body='fileSystems."/boot".device = lib.mkOverride 40 "/dev/disk/by-partlabel/disk-main-ESP";'),
        "by-partlabel or a kernel name",
    ),
    (
        "adopted host declares a disko disk",
        adopt(extra_chunks=[DISKO_MAIN % {"name": "main", "device": TARGET}]),
        "must declare no disko.devices.disk",
    ),
    (
        "adopted host has an install-target",
        adopt(
            disks=(
                f"sys = {disk('existing-system', '/dev/disk/by-id/nvme-FAKE_SYS_0003')}; "
                f"t = {disk('install-target', TARGET)};"
            )
        ),
        "cannot have an install-target disk",
    ),
    (
        "adopted host has no existing-system disk",
        adopt(disks=f"old = {disk('keep', '/dev/disk/by-id/nvme-FAKE_OLD_0002')};"),
        'needs a disk with role "existing-system"',
    ),
    (
        "adopted mount uses a kernel name",
        adopt(body='fileSystems."/data" = { device = "/dev/nvme0n1p4"; fsType = "ext4"; };'),
        "by-partlabel or a kernel name",
    ),
    (
        "inventory disk is not a by-id path",
        adopt(disks='sys = { byId = "/dev/sda"; role = "existing-system"; };'),
        "must be /dev/disk/by-id/ paths",
    ),
]


@pytest.mark.parametrize("label, host, message", BAD, ids=[b[0] for b in BAD])
def test_a_bad_machine_layout_fails_a_direct_nixos_build(ws_factory, label, host, message):
    ws = ws_factory([])
    ws.write_nix(host)
    done = ws.eval(TOPLEVEL)
    assert done.returncode != 0
    assert message in done.stderr, done.stderr[-2000:]


def test_the_pin_check_opt_out_does_not_reach_the_machine_guard(ws_factory):
    ws = ws_factory([])
    ws.write_nix(adopt(extra_chunks=[DISKO_MAIN % {"name": "main", "device": TARGET}]))  # check.enable is false
    done = ws.eval(TOPLEVEL)
    assert done.returncode != 0
    assert "must declare no disko.devices.disk" in done.stderr


def test_a_second_definition_of_the_host_module_is_refused(ws_factory):
    ws = ws_factory([])
    ws.write_nix(adopt(), workspace_extra='  machines.test.nixos = { networking.hostName = "x"; };\n')
    done = ws.eval(TOPLEVEL)
    assert done.returncode != 0
    assert "defined outside vendomat.inventory.test.nixos" in done.stderr


# --- Pins, paths, profiles (VMOD-005, VMOD-008, VMOD-009, VMOD-010) ---------------------------------


def _daemon(tmp: Path, name: str):
    """Serve one repository with a branch and a tag over `git://` on loopback."""
    import socket
    import time

    repos = tmp / "daemon"
    repo = repos / name
    repo.mkdir(parents=True)
    (repo / "flake.nix").write_text("{ outputs = { self }: { }; }\n")
    for argv in (["init", "-q", "-b", "main"], ["add", "-A"]):
        subprocess.run(["git", *argv], cwd=repo, check=True)
    subprocess.run([*GIT, "commit", "-q", "-m", "init"], cwd=repo, check=True)
    subprocess.run([*GIT, "tag", "v1"], cwd=repo, check=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    proc = subprocess.Popen(
        [
            "git",
            "daemon",
            "--reuseaddr",
            "--export-all",
            f"--base-path={repos}",
            "--listen=127.0.0.1",
            f"--port={port}",
            str(repos),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if subprocess.run(["git", "ls-remote", f"git://127.0.0.1:{port}/{name}"], capture_output=True).returncode == 0:
            return proc, port
        time.sleep(0.2)
    proc.terminate()
    raise AssertionError("git daemon did not start")


@pytest.mark.parametrize("ref, passes", [("refs/tags/v1", True), ("refs/heads/main", False)])
def test_a_branch_pin_stops_the_shell_and_a_tag_pin_does_not(tmp_path, ref, passes):
    proc, port = _daemon(tmp_path, "pinned")
    try:
        ws = Workspace(tmp_path, [])
        yaml = (ws.root / "devenv.yaml").read_text()
        yaml += f"  pinned:\n    url: git://127.0.0.1:{port}/pinned?ref={ref}\n"
        (ws.root / "devenv.yaml").write_text(yaml)
        (ws.root / "devenv.nix").write_text(
            "{ inputs, ... }: { imports = [ inputs.vendomat.devenvModules.default ]; }\n"
        )
        done = subprocess.run(
            [str(DEVENV), "--no-eval-cache", "shell", "--", "true"],
            cwd=ws.root,
            capture_output=True,
            text=True,
            env=ws.env,
            timeout=900,
        )
        if passes:
            assert done.returncode == 0, done.stderr[-2000:]
        else:
            assert done.returncode != 0
            assert "not pinned to a tag" in done.stderr and "pinned" in done.stderr
    finally:
        proc.terminate()


def test_paths_profiles_and_input_paths(tmp_path):
    ws = Workspace(tmp_path, ["knappy"])
    paths = tmp_path / "paths.json"
    paths.write_text(json.dumps({"state-dir": "/var/lib/x", "cache.root": "/mnt/c"}))
    ws.write_nix(
        None,
        workspace_extra=f'  vendomat.pathsFile = "{paths}";\n  vendomat.exportInputPaths = true;\n',
    )
    assert ws.value("env.VENDOMAT_PATH_STATE_DIR") == "/var/lib/x"
    assert ws.value("env.VENDOMAT_PATH_CACHE_ROOT") == "/mnt/c"
    assert ws.value("env.VENDOMAT_HOST") == "server"  # the profile of this host; the test host is `server`
    sources = ws.value("vendomat.inputPaths")
    assert set(sources) >= {"knappy", "nixpkgs", "vendomat", "disko", "home-manager"}
    assert all(p.startswith("/nix/store/") for p in sources.values())
    # A workspace value wins over the profile default.
    ws.write_nix(None, workspace_extra='  env.VENDOMAT_HOST = "override";\n')
    assert ws.value("env.VENDOMAT_HOST") == "override"
    # A missing paths file gives {}.
    ws.write_nix(None, workspace_extra='  vendomat.pathsFile = "/no/such/file.json";\n')
    assert ws.value("vendomat.paths") == {}


def test_the_input_paths_output_carries_every_source_in_its_closure(tmp_path):
    ws = Workspace(tmp_path, ["knappy"])
    ws.write_nix(None, workspace_extra="  vendomat.exportInputPaths = true;\n")
    done = subprocess.run(
        [str(DEVENV), "--no-eval-cache", "build", "outputs.vendomat.inputPaths"],
        cwd=ws.root,
        capture_output=True,
        text=True,
        env=ws.env,
        timeout=900,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout)
    path = str(next(iter(out.values())) if isinstance(out, dict) else out[0])
    closure = subprocess.run(["nix-store", "-qR", path], capture_output=True, text=True, check=True).stdout
    sources = ws.value("vendomat.inputPaths")
    for name, source in sources.items():
        assert source in closure, name


def test_the_devenv_process_runs_under_devenv_up(tmp_path):
    ws = Workspace(tmp_path, ["knappy"])
    ws.write_nix(None, workspace_extra="  vendomat.libs.knappy = { enable = true; port = 7099; };\n")
    up = subprocess.run([str(DEVENV), "up", "-d"], cwd=ws.root, capture_output=True, text=True, env=ws.env, timeout=300)
    try:
        assert up.returncode == 0, up.stderr[-2000:]
        import time

        found = False
        for _ in range(60):
            seen = subprocess.run(["pgrep", "-af", "sleep 3600"], capture_output=True, text=True).stdout
            if "sleep 3600" in seen:
                found = True
                break
            time.sleep(0.5)
        assert found, "the knappy process did not start under devenv up"
    finally:
        subprocess.run([str(DEVENV), "processes", "down"], cwd=ws.root, capture_output=True, timeout=120, env=ws.env)

"""Helpers for the project-output Nix fixtures.

The fixtures run pinned Nix against a disposable consumer. They need the network once to
fetch the pinned Nixpkgs, then use the local fetcher cache. They are opt-in:

    VENDOMAT_E2E=1 devenv shell -- testee verify --mode quick

Set ``VENDOMAT_FIXTURE_LOGS`` to a directory outside the repository to keep every command,
its exit status, and its output. A fixture never writes a credential.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

#: The pinned Nixpkgs that PV-05 and PV-04 already used. Do not change it silently.
NIXPKGS_URL = "github:cachix/devenv-nixpkgs/12866ae2dddbc0ab8b329915f8072bb9c75bde89"
SYSTEM = "x86_64-linux"

needs_nix_fixture = pytest.mark.skipif(
    os.environ.get("VENDOMAT_E2E") != "1" or shutil.which("nix") is None or shutil.which("gitman") is None,
    reason="Nix fixture; set VENDOMAT_E2E=1 and provide nix and gitman to opt in",
)

_LOG_COUNTER = {"n": 0}


@dataclass
class Result:
    argv: list[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    @property
    def warnings(self) -> list[str]:
        """Nix warnings, minus the expected notice that Nix created a lock file."""
        found = [ln for ln in self.stderr.splitlines() if ln.startswith("warning:")]
        return [ln for ln in found if "creating lock file" not in ln]

    @property
    def error_text(self) -> str:
        return self.stderr


def run(argv: list[str], cwd: Path, *, timeout: int = 900, env: dict[str, str] | None = None) -> Result:
    """Run a command and, when asked, keep its raw record outside the repository."""
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    result = Result(argv, cwd, proc.returncode, proc.stdout, proc.stderr)
    log_dir = os.environ.get("VENDOMAT_FIXTURE_LOGS")
    if log_dir:
        _LOG_COUNTER["n"] += 1
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        record = {"argv": argv, "cwd": str(cwd), "returncode": proc.returncode}
        stem = f"{os.getpid()}-{_LOG_COUNTER['n']:04d}"
        (directory / f"{stem}.json").write_text(json.dumps(record, indent=1) + "\n")
        (directory / f"{stem}.stdout").write_text(proc.stdout)
        (directory / f"{stem}.stderr").write_text(proc.stderr)
    return result


def nix(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> Result:
    return run(["nix", *args], cwd, env=env)


def eval_json(attr: str, cwd: Path, *, apply: str | None = None, env: dict[str, str] | None = None) -> Result:
    args = ["eval", "--json", attr]
    if apply is not None:
        args += ["--apply", apply]
    return nix(args, cwd, env=env)


def declared_inputs(flake_file: Path) -> dict:
    """The ``inputs`` attribute set of a flake file, read by Nix rather than by text search."""
    result = nix(["eval", "--json", "--file", flake_file.name, "inputs"], flake_file.parent)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def sanitized_env(tmp: Path) -> dict[str, str]:
    """An environment whose PATH holds only `nix` and `git`, so no Vendomat command can be found."""
    bin_dir = tmp / "sanitized-bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in ("nix", "git"):
        found = shutil.which(tool)
        assert found, tool
        link = bin_dir / tool
        if not link.exists():
            link.symlink_to(found)
    env = {"PATH": str(bin_dir), "HOME": os.environ["HOME"]}
    assert shutil.which("vendomat", path=env["PATH"]) is None
    return env


def lock_root_inputs(consumer: Path) -> dict[str, str]:
    """Read the root input names from ``flake.lock`` with a structured reader."""
    data = json.loads((consumer / "flake.lock").read_text())
    return dict(data["nodes"]["root"]["inputs"])


def nixpkgs_nodes(lock: dict) -> list[str]:
    """Lock nodes that came from the pinned Nixpkgs repository."""
    return sorted(
        name for name, node in lock["nodes"].items() if node.get("original", {}).get("repo") == "devenv-nixpkgs"
    )


# --- Gitman helpers -------------------------------------------------------------------


def gitman(args: list[str], cwd: Path) -> Result:
    result = run(["gitman", *args], cwd)
    assert result.returncode == 0, f"gitman {' '.join(args)} failed: {result.stdout}{result.stderr}"
    return result


def init_repo(root: Path, message: str = "fixture seed") -> None:
    gitman(["init", "--colocate", "--trunk", "main"], root)
    gitman(["seed", "-m", message], root)
    gitman(["repair"], root)


def save(root: Path, lane: str, message: str) -> None:
    """Record the working tree through Gitman so Nix sees every file as tracked.

    A remote-less fixture leaves the colocated git ref behind after ``land``, so the Git
    tree reads as dirty until ``repair`` re-points it.
    """
    gitman(["start", lane], root)
    gitman(["describe", "-m", message], root)
    gitman(["land"], root)
    gitman(["repair"], root)


def tag_release(root: Path, version: str) -> str:
    """Tag trunk and return its commit id, using Gitman only."""
    gitman(["release", "--version", version], root)
    return str(json.loads(gitman(["trunk", "show", "--json"], root).stdout)["commit_id"])


# --- Source files ---------------------------------------------------------------------


def _sibling_flake(name: str, body: str) -> str:
    return f"""{{
  inputs.nixpkgs.url = "{NIXPKGS_URL}";
  outputs = {{ self, nixpkgs }}:
    let
      system = "{SYSTEM}";
      pkgs = nixpkgs.legacyPackages.${{system}};
    in {{
{body.replace("@NAME@", name)}
    }};
}}
"""


MOD_PKG_FLAKE = _sibling_flake(
    "mod-pkg",
    """      packages.${system}.default = pkgs.writeText "@NAME@-marker" "@NAME@-marker\\n";
      devenvModules.default = { config, lib, ... }: {
        options.fixture = {
          enable = lib.mkEnableOption "fixture module";
          effect = lib.mkOption { type = lib.types.str; default = "inactive"; };
          packages = lib.mkOption { type = lib.types.listOf lib.types.package; default = [ ]; };
        };
        config = lib.mkIf config.fixture.enable {
          fixture.effect = "active";
          fixture.packages = [ self.packages.${system}.default ];
        };
      };""",
)

PLAIN_FLAKE = _sibling_flake(
    "plain",
    """      packages.${system}.default = pkgs.writeText "@NAME@-marker" "@NAME@-marker\\n";""",
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def write_sources(root: Path) -> None:
    """A module-bearing flake, a plain flake, and a non-flake data source."""
    write(root / "inputs/mod-pkg/flake.nix", MOD_PKG_FLAKE)
    write(root / "inputs/plain/flake.nix", PLAIN_FLAKE)
    write(root / "inputs/data/marker.txt", "data-marker\n")


# --- Candidate project files ----------------------------------------------------------

CANDIDATE_REGISTRY = f"""[inputs]
mod-pkg = {{ url = "path:./inputs/mod-pkg" }}
plain = {{ url = "path:./inputs/plain" }}
data = {{ url = "path:./inputs/data", flake = false }}

[passthrough]
nixpkgs = {{ url = "{NIXPKGS_URL}" }}
"""

#: What the generator is expected to emit for ``CANDIDATE_REGISTRY``, apart from the digest.
CANDIDATE_FLAKE = f"""# GENERATED by vendomat @VERSION@. Do not edit.
# registry-digest: @DIGEST@
{{
  inputs = {{
    data.url = "path:./inputs/data";
    data.flake = false;
    mod-pkg.url = "path:./inputs/mod-pkg";
    nixpkgs.url = "{NIXPKGS_URL}";
    plain.url = "path:./inputs/plain";
  }};

  outputs = inputs: import ./flake-outputs.nix inputs;
}}
"""

OUTPUTS_PACKAGES_ONLY = """inputs@{ self, nixpkgs, mod-pkg, plain, data, ... }:
let
  system = "x86_64-linux";
  pkgs = nixpkgs.legacyPackages.${system};
in {
  packages.${system} = {
    default = mod-pkg.packages.${system}.default;
    plain = plain.packages.${system}.default;
    data-marker = pkgs.runCommand "data-marker" { } "cp ${data}/marker.txt $out";
  };
  lib.inputNames = builtins.attrNames inputs;
  lib.moduleOptionNames = builtins.attrNames
    (nixpkgs.lib.evalModules { modules = [ { options.base = nixpkgs.lib.mkOption { default = 1; }; } ]; }).options;
}
"""

OUTPUTS_SELECT_MODULE = """inputs@{ self, nixpkgs, mod-pkg, plain, data, ... }:
let
  system = "x86_64-linux";
  evalWith = extra: (nixpkgs.lib.evalModules { modules = [ mod-pkg.devenvModules.default extra ]; }).config;
in {
  packages.${system}.default = mod-pkg.packages.${system}.default;
  lib.disabledEffect = (evalWith { }).fixture.effect;
  lib.enabledEffect = (evalWith { fixture.enable = true; }).fixture.effect;
  lib.disabledPackages = builtins.length (evalWith { }).fixture.packages;
  lib.enabledPackages = builtins.length (evalWith { fixture.enable = true; }).fixture.packages;
}
"""


def candidate_flake(version: str = "0.5.0", digest: str = "sha256-candidate") -> str:
    return CANDIDATE_FLAKE.replace("@VERSION@", version).replace("@DIGEST@", digest)


_DIGEST_LINE = re.compile(r"^# registry-digest: .*$", re.MULTILINE)


def without_digest(text: str) -> str:
    return _DIGEST_LINE.sub("# registry-digest: <digest>", text)


def check_bridge(consumer: Path, *, env: dict[str, str] | None = None, offline: bool = False) -> None:
    """The F1 and F2 assertions, shared by the hand-written candidate and the generated flake.

    ``offline`` denies every substituter, so the check shows that no cache is needed.
    """
    lock = nix(["flake", "lock"], consumer, env=env)
    assert lock.returncode == 0, lock.stderr
    assert lock.warnings == []
    assert set(lock_root_inputs(consumer)) == {"data", "mod-pkg", "nixpkgs", "plain"}
    # Nix adds the new lock file as intent-to-add; record it so the tree reads clean.
    save(consumer, "lock", "record the lock Nix wrote")

    names = eval_json(".#lib.inputNames", consumer, env=env)
    assert names.returncode == 0, names.stderr
    assert names.warnings == []
    assert json.loads(names.stdout) == ["data", "mod-pkg", "nixpkgs", "plain", "self"]

    flags = ["--option", "substituters", ""] if offline else []
    for attr, content in (("default", "mod-pkg-marker\n"), ("data-marker", "data-marker\n")):
        built = nix(
            ["build", *flags, "--no-link", "--print-out-paths", f".#packages.{SYSTEM}.{attr}"], consumer, env=env
        )
        assert built.returncode == 0, built.stderr
        assert Path(built.stdout.strip()).read_text() == content

    shown = nix(["flake", "show", "--json"], consumer, env=env)
    assert shown.returncode == 0, shown.stderr
    assert sorted(json.loads(shown.stdout)) == ["lib", "packages"]
    roots = set(json.loads((consumer / "flake.lock").read_text())["nodes"]["root"]["inputs"])
    assert not {"devenv", "vendomat"} & roots

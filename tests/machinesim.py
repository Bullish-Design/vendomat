"""A simulated machine for the unit tests of `vendomat apply` and `vendomat rollback`.

The simulation replaces every command that the two modules run. It keeps the system profile, the
boot entries, and the record in a temporary directory, and it builds a system path from the content
of the watched files. So a restore of the files gives the same system path, as on a real machine
(`VMT-110`: the commit is not part of the system).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from vendomat import workspace
from vendomat.apply import SUDO, Result

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env)
    return done.stdout.strip()


def make_workspace(root: Path, files: dict[str, str] | None = None) -> Path:
    """A Git workspace with one commit."""

    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "--quiet", "--initial-branch=main")
    content = {
        "vendomat.yaml": "machines:\n  box: {}\n",
        "devenv.lock": '{"nodes": {}}\n',
        "devenv.nix": "{ }\n",
        ".gitignore": ".devenv*\ndevenv.local.nix\n",
        "notes.txt": "one\n",
    }
    content.update(files or {})
    for name, text in content.items():
        (root / name).write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "--quiet", "-m", "first")
    return root


def fake_devenv(base: Path, watch: list[str] | None = None) -> str:
    """The path of a script that stands for ``devenv`` where a CLI test cannot inject a runner.

    It answers ``devenv eval vendomat.watch`` and fails on any other call.
    """

    script = base / "fake-devenv"
    answer = json.dumps({"vendomat.watch": watch or []})
    script.write_text(f'#!/bin/sh\n[ "$1 $2" = "eval vendomat.watch" ] && {{ echo \'{answer}\'; exit 0; }}\nexit 9\n')
    script.chmod(0o755)
    return str(script)


def commit_file(root: Path, name: str, text: str, message: str) -> str:
    (root / name).write_text(text)
    git(root, "add", name)
    git(root, "commit", "--quiet", "-m", message)
    return git(root, "rev-parse", "HEAD")


@dataclass
class Machine:
    """The state that the commands change, and the log of the commands that ran."""

    base: Path
    name: str = "box"
    calls: list[list[str]] = field(default_factory=list)
    inputs: list[str | None] = field(default_factory=list)
    fail: set[str] = field(default_factory=set)
    failed_units: str = ""
    codes: dict[str, int] = field(default_factory=dict)
    #: The value of ``vendomat.watch`` that ``devenv eval vendomat.watch`` prints. The eval calls go to ``evals``.
    watch: list[str] = field(default_factory=list)
    evals: list[list[str]] = field(default_factory=list)
    eval_result: Result | None = None

    def __post_init__(self) -> None:
        self.profiles = self.base / "profiles"
        self.profiles.mkdir(parents=True)
        self.profile = self.profiles / "system"
        self.record = self.base / "var" / "generations.jsonl"
        self.facts = self.base / "machine-facts.json"
        self.facts.write_text(json.dumps({"hostname": self.name}))
        self.cache_key = self.base / "cache-key.pub"  # absent until a test writes it
        self.boot = self.base / "boot-entries"
        self.boot.mkdir()
        self.generations: dict[int, str] = {}

    # The state of the profile.
    def set_generation(self, top: str) -> int:
        current = os.path.realpath(self.profile) if self.profile.is_symlink() else None
        if current == top:
            return self.number()
        number = max(self.generations, default=0) + 1
        self.generations[number] = top
        link = self.profiles / f"system-{number}-link"
        link.symlink_to(top)
        self._point(number)
        (self.boot / f"nixos-generation-{number}.conf").write_text(
            f"title NixOS\nversion Generation {number} NixOS 26.11, Linux 6.18\n"
        )
        return number

    def _point(self, number: int) -> None:
        if self.profile.is_symlink():
            self.profile.unlink()
        self.profile.symlink_to(f"system-{number}-link")

    def number(self) -> int:
        return int(os.readlink(self.profile).split("-")[1])

    def current(self) -> str:
        return os.path.realpath(self.profile)

    # The commands.
    def build_path(self, root: Path) -> str:
        digest = hashlib.sha256()
        for name in (*workspace.WATCHED, *self.watch):
            file = root / name
            digest.update(file.read_bytes() if file.is_file() else b"-")
        return f"/nix/store/{digest.hexdigest()[:32]}-nixos-system-{self.name}"

    def run(self, argv, *, cwd=None, input=None, capture=True, timeout=None) -> Result:  # noqa: A002
        argv = list(argv)
        if argv[0].endswith("devenv") and argv[1:] == ["eval", "vendomat.watch"]:
            self.evals.append(argv)  # the watch list is read apart from the commands that change the machine
            return self.eval_result or Result(0, json.dumps({"vendomat.watch": self.watch}) + "\n")
        self.calls.append(argv)
        self.inputs.append(input)
        key = " ".join(argv[1:3]) if argv[0] == SUDO else " ".join(argv[:2])
        for item, code in self.codes.items():
            if item in key:
                return Result(code, "", f"simulated exit {code} of {key}")
        if any(item in key for item in self.fail):
            return Result(1, "", f"simulated failure of {key}")
        if argv[0].endswith("devenv") and argv[1] == "build":
            assert cwd is not None
            top = self.build_path(Path(cwd))
            return Result(0, json.dumps({argv[2]: top}, indent=2) + "\n")
        if argv[0] == "systemctl":
            return Result(0, self.failed_units)
        if argv[0] == SUDO:
            return self._sudo(argv[1:], input)
        return Result(127, "", f"unexpected command {argv}")

    def _sudo(self, argv: list[str], input: str | None) -> Result:  # noqa: A002
        if argv[0] == "nix-env":
            if argv[3] == "--set":
                self.set_generation(argv[4])
            elif argv[3] == "--switch-generation":
                self._point(int(argv[4]))
            return Result(0)
        if argv[0].endswith("/bin/switch-to-configuration"):
            return Result(0)
        if argv[0] == "install":
            Path(argv[-1]).mkdir(parents=True, exist_ok=True)
            return Result(0)
        if argv[0] == "tee":
            Path(argv[2]).parent.mkdir(parents=True, exist_ok=True)
            with open(argv[2], "a") as handle:
                handle.write(input or "")
            return Result(0, input or "")
        if argv[0] == "bootctl":
            return Result(0)
        return Result(127, "", f"unexpected sudo command {argv}")

    def kwargs(self) -> dict:
        return {
            "run": self.run,
            "facts": self.facts,
            "profile": self.profile,
            "record": self.record,
        }

    def names(self) -> list[str]:
        """The commands that ran, as short labels."""

        out = []
        for argv in self.calls:
            if argv[0] == SUDO:
                out.append("sudo " + " ".join(argv[1:3]).replace(argv[1], os.path.basename(argv[1])))
            else:
                out.append(" ".join(argv[:2]))
        return out

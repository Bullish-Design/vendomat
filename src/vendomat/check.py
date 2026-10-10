"""``vendomat check``: the pin check, the devenv version check, and the fragment check (``CLI-019``).

The check reads files and runs ``devenv version``. It never writes. It names every problem it
finds, so one run shows the whole list.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import yamlsubset
from .devenvgen import DIGEST_FILE, FRAGMENT_DIR, NIX_FILE, YAML_FILE, read_digest, sha256_hex
from .nixio import lock_problems
from .registry import RegistryError, read_registry

TAG_PREFIX = "refs/tags/"
HEX40 = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"(\d+\.\d+\.\d+)(?:\+([0-9a-f]+))?")


@dataclass(frozen=True)
class Problem:
    """One finding. ``kind`` is ``registry``, ``fragment``, ``lock``, ``pin``, or ``version``."""

    kind: str
    name: str
    message: str

    def line(self) -> str:
        return f"{self.kind}: {self.name}: {self.message}" if self.name else f"{self.kind}: {self.message}"


def pin_problems(lock: dict[str, Any]) -> list[Problem]:
    """Every git node, direct or transitive, names a tag and a 40-hex revision (``VMOD-005``)."""

    out: list[Problem] = []
    for key, node in sorted(lock.get("nodes", {}).items()):
        original = node.get("original", {})
        if original.get("type") != "git":
            continue
        ref = str(original.get("ref", ""))
        rev = str(node.get("locked", {}).get("rev", ""))
        url = original.get("url", "?")
        if not ref.startswith(TAG_PREFIX) or ref == TAG_PREFIX:
            out.append(Problem("pin", key, f"{url} is not pinned to a tag (ref={ref or '<none>'})"))
        elif not HEX40.fullmatch(rev):
            out.append(Problem("pin", key, f"{url} has no 40-hex locked revision"))
    return out


def fragment_problems(root: Path) -> list[Problem]:
    fragment = root / FRAGMENT_DIR
    digest = read_digest(fragment / DIGEST_FILE)
    out: list[Problem] = []
    if not digest:
        return [Problem("fragment", "", f"{FRAGMENT_DIR}/{DIGEST_FILE} is missing; run `vendomat sync`")]
    registry = root / "vendomat.toml"
    pairs = [
        ("registry", registry, "vendomat.toml changed since the last sync"),
        ("fragment", fragment / YAML_FILE, f"{FRAGMENT_DIR}/{YAML_FILE} was edited by hand"),
        ("module", fragment / NIX_FILE, f"{FRAGMENT_DIR}/{NIX_FILE} was edited by hand"),
    ]
    for key, path, why in pairs:
        try:
            current = sha256_hex(path.read_bytes())
        except OSError:
            out.append(Problem("fragment", "", f"{path.name} is missing; run `vendomat sync`"))
            continue
        if digest.get(key) != current:
            out.append(Problem("fragment", "", f"{why}; run `vendomat sync`"))
    return out


def version_problems(lock: dict[str, Any], devenv_cmd: str) -> list[Problem]:
    """The CLI and the modules come from one source revision (``DVN-001``, ``DVN-004``)."""

    try:
        done = subprocess.run(
            [devenv_cmd, "version"], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [Problem("version", "devenv", f"cannot run `{devenv_cmd} version`: {exc}")]
    match = VERSION.search(done.stdout + done.stderr)
    if done.returncode != 0 or not match:
        return [Problem("version", "devenv", f"`{devenv_cmd} version` printed no version: {done.stdout.strip()!r}")]
    cli_rev = match.group(2) or ""
    node = lock.get("nodes", {}).get("devenv")
    if node is None:
        return [
            Problem("version", "devenv", "the lock has no `devenv` input; pin the patched modules in vendomat.toml")
        ]
    out: list[Problem] = []
    original, locked = node.get("original", {}), node.get("locked", {})
    if original.get("dir") != "src/modules" and locked.get("dir") != "src/modules":
        out.append(Problem("version", "devenv", "the `devenv` input must select `dir=src/modules`"))
    mod_rev = str(locked.get("rev", ""))
    if cli_rev and mod_rev and not mod_rev.startswith(cli_rev):
        out.append(
            Problem(
                "version",
                "devenv",
                f"the CLI was built from {cli_rev} but the locked modules are {mod_rev[:12]}; "
                "install the CLI that matches the pinned modules",
            )
        )
    return out


def check_workspace(root: Path, devenv_cmd: str | None = None, check_version: bool = True) -> list[Problem]:
    """Return every problem in the workspace at ``root``. An empty list means a clean workspace."""

    problems: list[Problem] = []
    registry_path = root / "vendomat.toml"
    try:
        registry = read_registry(registry_path)
    except RegistryError as exc:
        return [Problem("registry", "", str(exc))]
    if not registry.targets.devenv:
        return [
            Problem("registry", "", "this registry does not select the devenv target; `check` covers devenv workspaces")
        ]

    problems.extend(fragment_problems(root))
    lock_path = root / "devenv.lock"
    try:
        lock = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        problems.append(Problem("lock", "", f"cannot read devenv.lock: {exc}; run `vendomat sync`"))
        return problems
    problems.extend(pin_problems(lock))

    fragment_yaml = root / FRAGMENT_DIR / YAML_FILE
    if fragment_yaml.is_file():
        try:
            doc = yamlsubset.parse(fragment_yaml.read_text(), str(fragment_yaml))
        except (OSError, yamlsubset.YamlError) as exc:
            problems.append(Problem("fragment", "", f"cannot read the fragment: {exc}"))
        else:
            requested = {
                name: body["url"] for name, body in (doc.get("inputs") or {}).items() if isinstance(body, dict)
            }
            problems.extend(Problem("lock", name, why) for name, why in lock_problems(lock, requested))
    if check_version:
        problems.extend(version_problems(lock, devenv_cmd or os.environ.get("VENDOMAT_DEVENV", "devenv")))
    return problems

"""Find the store path of a locked input from ``devenv.lock``, with no network (``CLI-018``).

``devenv.lock`` records each source's NAR hash. For a fixed-output source, the store path follows
from that hash alone, so ``nix-store --print-fixed-path`` names it without a fetch. This module
never writes the lock.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import subprocess
from pathlib import Path
from typing import Any


class LockPathError(Exception):
    """A refusal. ``code`` is the CLI exit status: 1 needs a decision, 2 is a fault."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def read_lock(root: Path) -> dict[str, Any]:
    path = root / "devenv.lock"
    try:
        data = json.loads(path.read_text())
    except OSError as exc:
        raise LockPathError(f"{path}: cannot read the lock: {exc.strerror or exc}; run `vendomat sync`", 2) from exc
    except json.JSONDecodeError as exc:
        raise LockPathError(f"{path}: the lock is not JSON: {exc}", 2) from exc
    if not isinstance(data, dict) or "nodes" not in data:
        raise LockPathError(f"{path}: the lock has no nodes", 2)
    return data


def node_of(lock: dict[str, Any], name: str) -> tuple[str, dict[str, Any]]:
    """Resolve a root input name to its node, following ``follows`` paths."""

    nodes = lock["nodes"]
    root_inputs = nodes.get("root", {}).get("inputs", {})
    if name not in root_inputs:
        known = ", ".join(sorted(root_inputs)) or "none"
        raise LockPathError(f"unknown input '{name}'; known inputs: {known}")
    target = root_inputs[name]
    seen = 0
    while isinstance(target, list):
        # A follows path: walk it from the root, one input name at a time.
        key = "root"
        for part in target:
            step = nodes.get(key, {}).get("inputs", {}).get(part)
            if step is None:
                raise LockPathError(f"input '{name}': its follows path {target} does not resolve")
            key = step if isinstance(step, str) else key
            if isinstance(step, list):
                target = step
                break
        else:
            target = key
        seen += 1
        if seen > 16:
            raise LockPathError(f"input '{name}': its follows path loops")
    node = nodes.get(target)
    if node is None:
        raise LockPathError(f"input '{name}': lock node '{target}' is missing", 2)
    return str(target), node


def sri_to_hex(sri: str) -> str:
    """``sha256-<base64>`` to lowercase hexadecimal."""

    algo, _, body = sri.partition("-")
    if algo != "sha256" or not body:
        raise LockPathError(f"unsupported NAR hash {sri!r}", 2)
    try:
        return base64.b64decode(body, validate=True).hex()
    except (binascii.Error, ValueError) as exc:
        raise LockPathError(f"NAR hash {sri!r} is not base64", 2) from exc


def store_path_for(nar_hash: str, nix_store: str = "nix-store") -> str:
    """The store path of a source with this NAR hash. It does not check that the path exists."""

    hex_hash = sri_to_hex(nar_hash)
    try:
        done = subprocess.run(
            [nix_store, "--print-fixed-path", "--recursive", "sha256", hex_hash, "source"],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LockPathError(f"cannot run {nix_store}: {exc}", 2) from exc
    if done.returncode != 0:
        raise LockPathError(f"{nix_store} failed: {done.stderr.strip()}", 2)
    return done.stdout.strip()


def input_path_from_lock(root: Path, name: str, nix_store: str = "nix-store") -> str:
    """The store path of the locked source of the root input ``name``."""

    lock = read_lock(root)
    key, node = node_of(lock, name)
    locked = node.get("locked", {})
    nar_hash = locked.get("narHash")
    if not nar_hash:
        raise LockPathError(f"input '{name}' (node '{key}') has no narHash in the lock; run `vendomat sync` to lock it")
    path = store_path_for(nar_hash, nix_store)
    if not os.path.exists(path):
        raise LockPathError(
            f"input '{name}' is locked, but {path} is not in the store; "
            "run `devenv shell` once with the source reachable"
        )
    return path

"""Ask Nix about sources, and compare a lock with the inputs a fragment requests.

The pre-resolver needs two answers from Nix: where an input's source is in the store, and which
direct inputs that source's flake declares. ``Resolver`` names those two questions so a test can
answer them without a network. ``NixResolver`` asks the real ``nix``.

The lock functions never write ``devenv.lock``. They only read it and compare (``PRE-008``).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlsplit

#: Seconds. Nix may have to fetch an input that is not in the store yet.
NIX_TIMEOUT = 600


class NixError(Exception):
    """A Nix command failed or printed something unexpected. The message names the input."""


@dataclass(frozen=True)
class Fetched:
    """The result of fetching one input source."""

    store_path: str
    nar_hash: str
    rev: str | None = None


class Resolver(Protocol):
    def prefetch(self, url: str) -> Fetched:
        """Fetch the source at ``url`` into the store and name it."""

    def direct_inputs(self, url: str) -> dict[str, dict[str, Any]]:
        """Return the ``original`` reference of each direct input of the flake at ``url``."""


class NixResolver:
    """Answer from the real ``nix`` command."""

    def __init__(self, nix: str = "nix") -> None:
        self.nix = nix

    def _json(self, args: list[str], what: str) -> Any:
        try:
            done = subprocess.run(
                [self.nix, *args], capture_output=True, text=True, timeout=NIX_TIMEOUT, stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired as exc:
            raise NixError(f"{what}: nix timed out after {exc.timeout:.0f} s") from exc
        except OSError as exc:
            raise NixError(f"{what}: cannot run nix: {exc.strerror or exc}") from exc
        if done.returncode != 0:
            tail = "\n".join(done.stderr.strip().splitlines()[-4:])
            raise NixError(f"{what}: nix failed (status {done.returncode}):\n{tail}")
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise NixError(f"{what}: nix printed no JSON") from exc

    def prefetch(self, url: str) -> Fetched:
        data = self._json(["flake", "prefetch", "--json", url], f"fetch {url}")
        try:
            locked = data.get("locked", {})
            return Fetched(store_path=data["storePath"], nar_hash=data["hash"], rev=locked.get("rev"))
        except (KeyError, AttributeError) as exc:
            raise NixError(f"fetch {url}: nix printed no store path") from exc

    def direct_inputs(self, url: str) -> dict[str, dict[str, Any]]:
        data = self._json(["flake", "metadata", "--json", "--no-write-lock-file", url], f"read inputs of {url}")
        try:
            locks = data["locks"]
            nodes = locks["nodes"]
            root = nodes[locks["root"]]
        except (KeyError, TypeError) as exc:
            raise NixError(f"read inputs of {url}: nix printed no lock") from exc
        out: dict[str, dict[str, Any]] = {}
        for name, target in root.get("inputs", {}).items():
            if isinstance(target, list):  # a follows edge inside the flake's own lock
                continue
            out[name] = nodes[target].get("original", {})
        return out


# --- Source comparison -----------------------------------------------------------------------

Canon = tuple[str, ...]


def canon_url(url: str) -> Canon | None:
    """A comparable form of an input URL, or ``None`` when the form is not understood."""

    if url.startswith("github:"):
        head, _, query = url[len("github:") :].partition("?")
        parts = head.split("/")
        if len(parts) < 2:
            return None
        params = dict(parse_qsl(query))
        ref = params.get("ref", "")
        rev = params.get("rev", "")
        if len(parts) > 2:
            # Nix reads a 40-character hexadecimal third component as a revision, else as a ref.
            if re.fullmatch(r"[0-9a-f]{40}", parts[2]):
                rev = parts[2]
            else:
                ref = "/".join(parts[2:])
        return ("github", parts[0].lower(), parts[1].lower(), ref, rev, params.get("dir", ""))
    if url.startswith("path:"):
        return ("path", url[len("path:") :].partition("?")[0])
    scheme_url = url[len("git+") :] if url.startswith("git+") else url
    split = urlsplit(scheme_url)
    known_scheme = split.scheme in {"git", "https", "http", "ssh", "file"}
    if known_scheme and (url.startswith("git") or scheme_url.endswith(".git")):
        params = dict(parse_qsl(split.query))
        base = f"{split.scheme}://{split.netloc}{split.path}"
        return ("git", base, params.get("ref", ""), params.get("rev", ""), params.get("dir", ""))
    return None


def canon_original(original: dict[str, Any]) -> Canon | None:
    """A comparable form of a lock ``original`` attribute set."""

    kind = original.get("type")
    if kind == "github":
        return (
            "github",
            str(original.get("owner", "")).lower(),
            str(original.get("repo", "")).lower(),
            str(original.get("ref", "")),
            str(original.get("rev", "")),
            str(original.get("dir", "")),
        )
    if kind == "git":
        split = urlsplit(str(original.get("url", "")))
        base = f"{split.scheme}://{split.netloc}{split.path}"
        return (
            "git",
            base,
            str(original.get("ref", "")),
            str(original.get("rev", "")),
            str(original.get("dir", "")),
        )
    if kind == "path":
        return ("path", str(original.get("path", "")))
    return None


def same_source(url: str, original: dict[str, Any]) -> bool | None:
    """``True`` or ``False`` when both sides are understood, else ``None``."""

    left, right = canon_url(url), canon_original(original)
    if left is None or right is None or left[0] != right[0]:
        return None if (left is None or right is None) else False
    return left == right


# --- Lock comparison -------------------------------------------------------------------------


def lock_problems(lock: dict[str, Any] | None, requested: dict[str, str]) -> list[tuple[str, str]]:
    """Compare a parsed ``devenv.lock`` with the requested ``{input: url}``.

    Return ``(input, problem)`` pairs. An empty list means the lock holds every requested input at
    the requested source. A lock node whose ``original`` cannot be compared passes if it has a
    locked revision or hash.
    """

    problems: list[tuple[str, str]] = []
    if lock is None:
        return [(name, "no devenv.lock") for name in sorted(requested)]
    nodes = lock.get("nodes", {})
    root_inputs = nodes.get("root", {}).get("inputs", {})
    for name, url in sorted(requested.items()):
        target = root_inputs.get(name)
        if target is None:
            problems.append((name, "not in the lock"))
            continue
        if isinstance(target, list):
            continue  # a follows edge at the root is not generated by Vendomat
        node = nodes.get(target, {})
        locked = node.get("locked", {})
        if not (locked.get("rev") or locked.get("narHash")):
            problems.append((name, "locked without a revision or hash"))
            continue
        same = same_source(url, node.get("original", {}))
        if same is False:
            problems.append((name, f"locked from a different source than {url}"))
    return problems

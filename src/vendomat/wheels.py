"""Publish the wheel the Nix store already built.

Vendomat performs the single hermetic build of a native library and emits that artifact into
two indexes: the Nix store and a GitHub release. The two cannot disagree, because the file
uploaded here **is** the store file — hash equality with a consumer's ``[tool.uv.sources]``
URL is by construction, not by luck.

One rule keeps the invariant intact: **one version, one artifact.** A version that has been
published is frozen. An iteration build — a store wheel produced ahead of a release — takes
its own version (``0.21.0.dev0+<rev>``) and is never uploaded. Both halves are enforced
below, so the rule fails a command rather than living only in prose.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# name-version-pythontag-abitag-platformtag.whl (PEP 427). A build tag would add a field;
# maturin does not emit one, and vendomat refuses what it cannot name exactly.
WHEEL_NAME = re.compile(
    r"^(?P<name>[^-]+)-(?P<version>[^-]+)-(?P<python>[^-]+)-(?P<abi>[^-]+)-(?P<platform>[^-]+)\.whl$"
)

DEFAULT_OWNER = "Bullish-Design"


class WheelError(RuntimeError):
    """A wheel, a version, or a release state prevents a safe publication."""


@dataclass(frozen=True)
class Wheel:
    """A built wheel in the Nix store, named by its own filename."""

    path: Path
    name: str
    version: str
    python_tag: str
    abi_tag: str
    platform_tag: str

    @property
    def filename(self) -> str:
        return self.path.name


def parse_wheel(path: Path) -> Wheel:
    """Read a wheel's identity out of its filename."""

    match = WHEEL_NAME.match(path.name)
    if not match:
        raise WheelError(f"not a wheel filename vendomat can read: {path.name}")
    return Wheel(
        path=path,
        name=match["name"],
        version=match["version"],
        python_tag=match["python"],
        abi_tag=match["abi"],
        platform_tag=match["platform"],
    )


def is_iteration_version(version: str) -> bool:
    """True for a version that names a build ahead of a release (``.dev``/``+local``)."""

    return ".dev" in version or "+" in version


def iteration_version(base: str, rev: str) -> str:
    """The version an iteration build takes: ``<next release>.dev0+<rev>``.

    ``rev`` is the source revision the build came from, so two iteration builds of different
    trees can never carry one version.
    """

    if is_iteration_version(base):
        raise WheelError(f"base version must be a plain release version, got {base!r}")
    cleaned = re.sub(r"[^0-9a-zA-Z]+", ".", rev).strip(".")
    if not cleaned:
        raise WheelError("iteration version needs a source revision")
    return f"{base}.dev0+{cleaned}"


def check_portable(wheel: Wheel) -> list[str]:
    """Reasons this wheel must not be published. Empty means it is portable."""

    problems: list[str] = []
    if not wheel.platform_tag.startswith("manylinux"):
        problems.append(
            f"platform tag {wheel.platform_tag!r} is not a manylinux tag — "
            "the builder must pass `--compatibility` (lib/mkMaturinWheel.nix)"
        )
    return problems


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise WheelError(f"{command[0]} {' '.join(command[1:2])} failed: {detail}")
    return result.stdout


def store_wheel(lib: str, flake_root: Path) -> Wheel:
    """Build ``.#<lib>-wheel`` and return the single wheel in its output path."""

    out = _run(
        ["nix", "build", f".#{lib}-wheel", "--no-link", "--print-out-paths"],
        cwd=flake_root,
    ).split()
    if not out:
        raise WheelError(f"nix build .#{lib}-wheel produced no output path")
    wheels = sorted(Path(out[-1]).glob("*.whl"))
    if len(wheels) != 1:
        raise WheelError(f"expected exactly one wheel in {out[-1]}, found {len(wheels)}")
    return parse_wheel(wheels[0])


def release_tag(version: str) -> str:
    """The release tag a version publishes under. Derived, so the two cannot disagree."""

    return f"v{version}"


def _release_assets(repo: str, tag: str) -> list[str] | None:
    """Asset names on an existing release, or None when the release does not exist yet."""

    result = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo, "--json", "assets"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        if "release not found" in result.stderr.lower() or "not found" in result.stderr.lower():
            return None
        raise WheelError(f"gh release view {tag} failed: {result.stderr.strip()}")
    try:
        assets = json.loads(result.stdout).get("assets", [])
    except json.JSONDecodeError as exc:
        raise WheelError(f"could not read the asset list for {tag}: {exc}") from exc
    return [str(asset["name"]) for asset in assets if isinstance(asset, dict) and "name" in asset]


def _published_sha256(repo: str, tag: str, filename: str) -> str:
    with tempfile.TemporaryDirectory(prefix="vendomat-release-") as temp:
        _run(["gh", "release", "download", tag, "--repo", repo, "--pattern", filename, "--dir", temp])
        return sha256(Path(temp) / filename)


def check_version_discipline(wheel: Wheel, repo: str, published: list[str] | None) -> None:
    """Apply the one-version-one-artifact rule to a wheel about to be uploaded.

    ``published`` is the asset list of the matching release, or None when no such release
    exists. Raises when the upload would give one version a second artifact.
    """

    if is_iteration_version(wheel.version):
        raise WheelError(
            f"{wheel.filename} is an iteration build ({wheel.version}); iteration builds stay "
            "in the Nix store and are never published. Cut a release version first."
        )
    if published is None:
        return
    if wheel.filename not in published:
        return
    tag = release_tag(wheel.version)
    if _published_sha256(repo, tag, wheel.filename) == sha256(wheel.path):
        return
    raise WheelError(
        f"{tag} already publishes a different {wheel.filename}. One version means one artifact: "
        f"bump the version, or build an iteration wheel with "
        f"`{iteration_version(wheel.version.split('.dev')[0], '<rev>')}`."
    )


def publish_wheel(lib: str, flake_root: Path, repo: str | None = None, dry_run: bool = False) -> list[str]:
    """Upload the store wheel for ``lib`` to its GitHub release. Returns a report."""

    target = repo or f"{DEFAULT_OWNER}/{lib}"
    wheel = store_wheel(lib, flake_root)
    problems = check_portable(wheel)
    if problems:
        raise WheelError("; ".join(problems))

    tag = release_tag(wheel.version)
    published = _release_assets(target, tag)
    check_version_discipline(wheel, target, published)

    report = [
        f"lib:     {wheel.name} {wheel.version}",
        f"wheel:   {wheel.path}",
        f"sha256:  {sha256(wheel.path)}",
        f"release: {target} {tag}",
    ]
    if published is None:
        raise WheelError(f"{target} has no release {tag}; create the release, then publish the wheel")
    if wheel.filename in published:
        report.append("upload:  already published, identical bytes — nothing to do")
        return report
    if dry_run:
        report.append("upload:  skipped (--dry-run)")
        return report
    _run(["gh", "release", "upload", tag, str(wheel.path), "--repo", target])
    report.append(f"upload:  uploaded {wheel.filename}")
    return report

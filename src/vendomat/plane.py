"""Machine-level Devman plane generations.

Vendomat owns this lifecycle. Devman supplies the renderer and workflow
semantics through ``devman project render``. This module only transports the
renderer bundle, validates staged Dagu files, and swaps an immutable active
generation.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


class PlaneError(Exception):
    """A plane operation failed without changing the active generation."""


@dataclass(frozen=True)
class PlaneProject:
    """Machine-local inputs for one registered repository."""

    name: str
    root: Path
    policy_root: Path
    overlay_root: Path


@dataclass(frozen=True)
class RenderedBundle:
    """The public JSON bundle emitted by Devman's renderer."""

    project: str
    generation: dict[str, object]
    record: dict[str, object]
    files: dict[str, bytes]
    links: dict[str, str]
    sources: dict[str, str]

    @classmethod
    def from_json(cls, text: str) -> RenderedBundle:
        try:
            raw = json.loads(text)
            if raw.get("schema") != 1:
                raise PlaneError(f"unsupported Devman projection bundle schema: {raw.get('schema')!r}")
            files = {name: base64.b64decode(value, validate=True) for name, value in raw["files"].items()}
            bundle = cls(
                project=raw["project"],
                generation=raw["generation"],
                record=raw["record"],
                files=files,
                links=dict(raw.get("links", {})),
                sources=dict(raw.get("sources", {})),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PlaneError(f"invalid Devman projection bundle: {exc}") from exc
        _validate_bundle(bundle)
        return bundle


@dataclass(frozen=True)
class InspectedProject:
    """The identity-only result from Devman's public inspection boundary."""

    project: str
    generation: dict[str, object]
    record: dict[str, object]
    sources: dict[str, str]

    @classmethod
    def from_json(cls, text: str) -> InspectedProject:
        try:
            raw = json.loads(text)
            if raw.get("schema") != 1:
                raise PlaneError(f"unsupported Devman projection inspection schema: {raw.get('schema')!r}")
            inspection = cls(
                project=raw["project"],
                generation=raw["generation"],
                record=raw["record"],
                sources=dict(raw.get("sources", {})),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PlaneError(f"invalid Devman projection inspection: {exc}") from exc
        _validate_inspection(inspection)
        return inspection


@dataclass(frozen=True)
class PlaneBuild:
    """The result of one rendered and validated generation build."""

    generation: dict[str, object]
    projects: tuple[str, ...]
    changed: tuple[str, ...]
    noop: bool
    activated: bool


def digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def digest_file(path: Path) -> str:
    try:
        return digest_bytes(path.read_bytes())
    except OSError as exc:
        raise PlaneError(f"cannot read identity file {path}: {exc}") from exc


def read_plane_config(path: Path | None = None) -> dict[str, object]:
    """Read optional machine-local defaults without requiring the file."""

    config_path = path or Path("~/.config/vendomat/plane.toml").expanduser()
    if not config_path.is_file():
        return {}
    try:
        raw = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PlaneError(f"cannot read plane config {config_path}: {exc}") from exc
    section = raw.get("devman", raw)
    if not isinstance(section, dict):
        raise PlaneError(f"plane config {config_path}: [devman] must be a table")
    return section


class GenerationStore:
    """Immutable generation storage with an atomic ``active`` symlink."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.generations = self.root / "generations"
        self.active = self.root / "active"

    def _prepare(self) -> None:
        self.generations.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def operation_lock(self):
        """Serialize update, activation, rollback, and recovery operations."""

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / ".lock"
        with path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def next_generation(self) -> int:
        if not self.generations.is_dir():
            return 1
        numbers = [int(path.name) for path in self.generations.iterdir() if path.name.isdigit() and path.is_dir()]
        return max(numbers, default=0) + 1

    def current_generation(self) -> int | None:
        if not self.active.is_symlink():
            return None
        target = os.readlink(self.active)
        name = Path(target).name
        return int(name) if name.isdigit() else None

    def current_path(self) -> Path | None:
        number = self.current_generation()
        return None if number is None else self.generations / str(number)

    def read_generation(self, generation: int | None = None) -> dict[str, object]:
        """Read one generation identity, defaulting to the active generation."""

        number = self.current_generation() if generation is None else generation
        if number is None:
            raise PlaneError("no active plane generation")
        path = self.generations / str(number) / "generation.json"
        try:
            raw = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise PlaneError(f"cannot read generation {number}: {path}") from exc
        if not isinstance(raw, dict):
            raise PlaneError(f"generation {number} is not an object: {path}")
        return raw

    def read_project_records(self, generation: int | None = None) -> list[dict[str, object]]:
        """Read project result records from one generation in stable order."""

        number = self.current_generation() if generation is None else generation
        if number is None:
            raise PlaneError("no active plane generation")
        root = self.generations / str(number) / "projects"
        if not root.is_dir():
            raise PlaneError(f"generation {number} has no project directory: {root}")
        records: list[dict[str, object]] = []
        for path in sorted(root.glob("*/projection.json")):
            try:
                raw = json.loads(path.read_text())
            except (OSError, ValueError) as exc:
                raise PlaneError(f"cannot read project record {path}") from exc
            if not isinstance(raw, dict):
                raise PlaneError(f"project record is not an object: {path}")
            records.append(raw)
        return records

    def recover(self) -> list[Path]:
        """Move abandoned staging directories aside without deleting them."""

        self._prepare()
        abandoned = sorted(self.generations.glob(".staging-*"))
        abandoned.extend(sorted(self.root.glob(".active-*.new")))
        if not abandoned:
            return []
        recovered = self.root / "recovered"
        recovered.mkdir(parents=True, exist_ok=True)
        moved: list[Path] = []
        for path in abandoned:
            name = path.name.removeprefix(".staging-").removesuffix(".new")
            target = recovered / name
            suffix = 1
            while target.exists():
                target = recovered / f"{name}-{suffix}"
                suffix += 1
            os.replace(path, target)
            moved.append(target)
        return moved

    def build(
        self,
        bundles: list[RenderedBundle],
        *,
        dagu: str,
        activate: bool,
    ) -> PlaneBuild:
        """Stage, validate, and optionally activate one generation."""

        if not bundles:
            raise PlaneError("cannot build a plane generation with no projects")
        _validate_generation_set(bundles)
        generation = bundles[0].generation
        generation_number = _generation_number(generation)
        if activate:
            self._prepare()

        changed = tuple(bundle.project for bundle in bundles if not self._project_matches_active(bundle))
        if activate and not changed and self._generation_inputs_match_active(generation):
            return PlaneBuild(
                generation=generation,
                projects=tuple(bundle.project for bundle in bundles),
                changed=(),
                noop=True,
                activated=False,
            )

        staging = Path(
            tempfile.mkdtemp(
                prefix=".staging-",
                dir=self.generations if activate else None,
            )
        )
        cleanup_staging = True
        try:
            (staging / "generation.json").write_text(json.dumps(generation, sort_keys=True, indent=2) + "\n")
            for bundle in bundles:
                for relative, body in bundle.files.items():
                    target = _safe_child(staging, relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(body)
            _validate_dags(staging, dagu)
            for bundle in bundles:
                for relative, target in bundle.links.items():
                    link = _safe_child(staging, relative)
                    if link.exists() or link.is_symlink():
                        raise PlaneError(f"projection link collides with a file: {relative}")
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(target)

            final = self.generations / str(generation_number)
            if activate and final.exists():
                raise PlaneError(f"generation {generation_number} already exists and is immutable")
            if not activate:
                shutil.rmtree(staging)
                cleanup_staging = False
                return PlaneBuild(
                    generation=generation,
                    projects=tuple(bundle.project for bundle in bundles),
                    changed=changed,
                    noop=False,
                    activated=False,
                )
            os.replace(staging, final)
            cleanup_staging = False
            activated = False
            if activate:
                self._activate_number(generation_number)
                activated = True
            return PlaneBuild(
                generation=generation,
                projects=tuple(bundle.project for bundle in bundles),
                changed=changed,
                noop=False,
                activated=activated,
            )
        except Exception:
            if cleanup_staging:
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def generation_inputs_match_active(self, generation: dict[str, object]) -> bool:
        """Return whether the active generation has the same non-number inputs."""

        return self._generation_inputs_match_active(generation)

    def project_record_matches_active(self, project: str, record: dict[str, object]) -> bool:
        """Return whether an inspected record matches the active projection."""

        current = self.current_path()
        if current is None:
            return False
        return self._record_matches_active(current, project, record)

    def copy_active_bundle(self, project: str, generation: dict[str, object]) -> RenderedBundle:
        """Copy one valid active project into a new generation identity."""

        current = self.current_path()
        if current is None:
            raise PlaneError(f"cannot copy project '{project}': no active generation")
        project_root = _safe_child(current, f"projects/{project}")
        if not project_root.is_dir():
            raise PlaneError(f"cannot copy project '{project}': active generation has no project")
        generation_number = _generation_number(generation)
        files: dict[str, bytes] = {}
        record: dict[str, object] | None = None
        for source in sorted(project_root.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(current).as_posix()
            body = source.read_bytes()
            if relative == f"projects/{project}/projection.json":
                try:
                    raw_record = json.loads(body)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise PlaneError(f"cannot copy project '{project}': invalid projection record") from exc
                if not isinstance(raw_record, dict):
                    raise PlaneError(f"cannot copy project '{project}': projection record is not an object")
                record = dict(raw_record)
                record["plane_generation"] = generation_number
                body = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
            elif relative == f"projects/{project}/metadata.json":
                body = _update_metadata_generation(body, generation_number)
            files[relative] = body
        if record is None:
            raise PlaneError(f"cannot copy project '{project}': active generation has no projection record")
        links: dict[str, str] = {}
        dag_root = current / "dags"
        for link in sorted(dag_root.glob(f"{project}.*.yaml")):
            if not link.is_symlink():
                raise PlaneError(f"active Dagu entry is not a symlink: {link}")
            links[link.relative_to(current).as_posix()] = os.readlink(link)
        bundle = RenderedBundle(
            project=project,
            generation=generation,
            record=record,
            files=files,
            links=links,
            sources={},
        )
        _validate_bundle(bundle)
        return bundle

    def rollback(self, generation: int) -> None:
        self._prepare()
        target = self.generations / str(generation)
        if not target.is_dir() or not (target / "generation.json").is_file():
            raise PlaneError(f"generation {generation} does not exist")
        self._activate_number(generation)

    def _activate_number(self, generation: int) -> None:
        if self.active.exists() and not self.active.is_symlink():
            raise PlaneError(f"active pointer exists and is not a symlink: {self.active}")
        temporary = self.root / f".active-{generation}.new"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(Path("generations") / str(generation))
        os.replace(temporary, self.active)

    def _project_matches_active(self, bundle: RenderedBundle) -> bool:
        current = self.current_path()
        if current is None:
            return False
        return self._record_matches_active(current, bundle.project, bundle.record)

    @staticmethod
    def _record_matches_active(current: Path, project: str, record: dict[str, object]) -> bool:
        record_path = current / f"projects/{project}/projection.json"
        try:
            old = json.loads(record_path.read_text())
        except (OSError, ValueError):
            return False
        fields = (
            "project",
            "manifest_digest",
            "policy_digest",
            "renderer_digest",
            "source_digest",
            "overlay_digest",
        )
        return all(old.get(field) == record.get(field) for field in fields)

    def _generation_inputs_match_active(self, generation: dict[str, object]) -> bool:
        current = self.current_path()
        if current is None:
            return False
        try:
            old = json.loads((current / "generation.json").read_text())
        except (OSError, ValueError):
            return False
        return all(old.get(key) == value for key, value in generation.items() if key != "generation")


def render_project(
    project: PlaneProject,
    *,
    generation: int,
    renderer: str,
    runtime: str,
    dagu_digest: str,
    toolchain_digest: str,
) -> RenderedBundle:
    """Call Devman's public renderer boundary for one project."""

    with tempfile.TemporaryDirectory(prefix="vendomat-render-") as temporary:
        output = Path(temporary) / "projection.json"
        command = [
            renderer,
            "project",
            "render",
            "--root",
            str(project.root),
            "--policy-root",
            str(project.policy_root),
            "--overlay-root",
            str(project.overlay_root),
            "--generation",
            str(generation),
            "--devman-runtime",
            runtime,
            "--dagu-digest",
            dagu_digest,
            "--toolchain-digest",
            toolchain_digest,
            "--output",
            str(output),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise PlaneError(f"Devman could not render project '{project.name}'" + (f":\n{detail}" if detail else ""))
        try:
            bundle = RenderedBundle.from_json(output.read_text())
        except OSError as exc:
            raise PlaneError(f"Devman produced no projection bundle for '{project.name}'") from exc
        if bundle.project != project.name:
            raise PlaneError(f"Devman rendered '{bundle.project}' for requested project '{project.name}'")
        return bundle


def inspect_project(
    project: PlaneProject,
    *,
    generation: int,
    renderer: str,
    runtime: str,
    dagu_digest: str,
    toolchain_digest: str,
) -> InspectedProject:
    """Call Devman's identity-only inspection boundary for one project."""

    with tempfile.TemporaryDirectory(prefix="vendomat-inspect-") as temporary:
        output = Path(temporary) / "inspection.json"
        command = [
            renderer,
            "project",
            "inspect",
            "--root",
            str(project.root),
            "--policy-root",
            str(project.policy_root),
            "--overlay-root",
            str(project.overlay_root),
            "--generation",
            str(generation),
            "--devman-runtime",
            runtime,
            "--dagu-digest",
            dagu_digest,
            "--toolchain-digest",
            toolchain_digest,
            "--output",
            str(output),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise PlaneError(f"Devman could not inspect project '{project.name}'" + (f":\n{detail}" if detail else ""))
        try:
            inspection = InspectedProject.from_json(output.read_text())
        except OSError as exc:
            raise PlaneError(f"Devman produced no projection inspection for '{project.name}'") from exc
        if inspection.project != project.name:
            raise PlaneError(f"Devman inspected '{inspection.project}' for requested project '{project.name}'")
        return inspection


def plan_or_update(
    projects: list[PlaneProject],
    *,
    store: GenerationStore,
    renderer: str,
    runtime: str,
    dagu: str,
    toolchain_digest: str,
    activate: bool,
) -> PlaneBuild:
    """Inspect a fleet, render changed projects, then activate if requested."""

    generation = store.next_generation()
    dagu_path = shutil.which(dagu) or dagu
    dagu_identity = digest_file(Path(dagu_path)) if Path(dagu_path).is_file() else digest_bytes(dagu.encode())
    inspections = [
        inspect_project(
            project,
            generation=generation,
            renderer=renderer,
            runtime=runtime,
            dagu_digest=dagu_identity,
            toolchain_digest=toolchain_digest,
        )
        for project in projects
    ]
    _validate_inspection_set(inspections)
    target_generation = inspections[0].generation
    generation_inputs_match = store.generation_inputs_match_active(target_generation)
    if (
        activate
        and generation_inputs_match
        and all(store.project_record_matches_active(item.project, item.record) for item in inspections)
    ):
        return PlaneBuild(
            generation=target_generation,
            projects=tuple(item.project for item in inspections),
            changed=(),
            noop=True,
            activated=False,
        )

    bundles: list[RenderedBundle] = []
    for project, inspection in zip(projects, inspections, strict=True):
        can_copy = generation_inputs_match and store.project_record_matches_active(
            inspection.project, inspection.record
        )
        if can_copy:
            bundles.append(store.copy_active_bundle(inspection.project, target_generation))
            continue
        bundles.append(
            render_project(
                project,
                generation=generation,
                renderer=renderer,
                runtime=runtime,
                dagu_digest=dagu_identity,
                toolchain_digest=toolchain_digest,
            )
        )
    return store.build(bundles, dagu=dagu, activate=activate)


def discover_project(
    name: str,
    *,
    devman_state: Path,
    policy_root: Path,
    overlay_root: Path,
    root_override: Path | None = None,
) -> PlaneProject:
    """Resolve a registered project path without scanning arbitrary disk paths."""

    metadata = devman_state.expanduser() / "projects" / name / "metadata.json"
    if root_override is None:
        try:
            raw = json.loads(metadata.read_text())
            root = Path(raw["path"]).expanduser().resolve()
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise PlaneError(f"cannot resolve registered project '{name}': {metadata}") from exc
    else:
        root = root_override.expanduser().resolve()
    if not root.is_dir():
        raise PlaneError(f"registered project '{name}' is not a directory: {root}")
    return PlaneProject(name, root, policy_root.expanduser().resolve(), overlay_root.expanduser().resolve())


def manifest_project_name(root: Path) -> str:
    """Read only the identity field needed to name an explicit root."""

    path = root.expanduser().resolve() / ".devman" / "project.toml"
    try:
        raw = tomllib.loads(path.read_text())
        name = raw["project"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PlaneError(f"cannot read project identity from {path}") from exc
    if not isinstance(name, str) or not name:
        raise PlaneError(f"project identity is missing from {path}")
    return name


def _validate_inspection(inspection: InspectedProject) -> None:
    if not isinstance(inspection.project, str) or not inspection.project:
        raise PlaneError("projection inspection has no project name")
    if not isinstance(inspection.generation, dict):
        raise PlaneError("projection inspection has no generation object")
    if not isinstance(inspection.record, dict):
        raise PlaneError("projection inspection has no record object")
    if inspection.record.get("project") != inspection.project:
        raise PlaneError(f"projection inspection record names a different project: {inspection.project}")
    if inspection.record.get("plane_generation") != inspection.generation.get("generation"):
        raise PlaneError(f"projection inspection has a different generation: {inspection.project}")
    _generation_number(inspection.generation)
    for field in ("renderer_digest", "policy_digest", "dagu_digest", "toolchain_digest"):
        value = inspection.generation.get(field)
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise PlaneError(f"generation field {field} is not a digest")


def _validate_inspection_set(inspections: list[InspectedProject]) -> None:
    if not inspections:
        raise PlaneError("cannot inspect a plane generation with no projects")
    first = inspections[0].generation
    projects: set[str] = set()
    for inspection in inspections:
        _validate_inspection(inspection)
        if inspection.generation != first:
            raise PlaneError("projects in one plane inspection returned different generation identities")
        if inspection.project in projects:
            raise PlaneError(f"duplicate project identity in one plane inspection: {inspection.project}")
        projects.add(inspection.project)


def _update_metadata_generation(body: bytes, generation: int) -> bytes:
    """Move the compatibility metadata marker with a copied projection."""

    try:
        raw = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PlaneError("active project metadata is not valid JSON") from exc
    if not isinstance(raw, dict) or "plan" not in raw:
        return body
    raw = dict(raw)
    raw["plan"] = f"plane:{generation}"
    return (json.dumps(raw, sort_keys=True, indent=2) + "\n").encode()


def _validate_bundle(bundle: RenderedBundle) -> None:
    if not isinstance(bundle.project, str) or not bundle.project:
        raise PlaneError("projection bundle has no project name")
    if bundle.record.get("project") != bundle.project:
        raise PlaneError(f"projection record names a different project: {bundle.project}")
    if bundle.record.get("plane_generation") != bundle.generation.get("generation"):
        raise PlaneError(f"projection record has a different generation: {bundle.project}")
    for field in (
        "renderer_digest",
        "policy_digest",
        "dagu_digest",
        "toolchain_digest",
    ):
        value = bundle.generation.get(field)
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise PlaneError(f"generation field {field} is not a digest")
    for relative in bundle.files:
        _safe_relative(relative)
    for relative, target in bundle.links.items():
        _safe_relative(relative)
        if not target or not _safe_link_target(relative, target):
            raise PlaneError(f"projection link target is unsafe: {target!r}")


def _validate_generation_set(bundles: list[RenderedBundle]) -> None:
    first = bundles[0].generation
    projects: set[str] = set()
    links: set[str] = set()
    for bundle in bundles:
        if bundle.generation != first:
            raise PlaneError("projects in one plane build returned different generation identities")
        if bundle.project in projects:
            raise PlaneError(f"duplicate project identity in one plane build: {bundle.project}")
        projects.add(bundle.project)
        overlap = links.intersection(bundle.links)
        if overlap:
            raise PlaneError(f"Dagu link collision: {sorted(overlap)}")
        links.update(bundle.links)


def _generation_number(generation: dict[str, object]) -> int:
    value = generation.get("generation")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PlaneError(f"invalid plane generation number: {value!r}")
    return value


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise PlaneError(f"projection path is unsafe: {value!r}")
    return path


def _safe_child(root: Path, relative: str) -> Path:
    path = _safe_relative(relative)
    child = root / path
    if child != child.resolve(strict=False) and not child.is_symlink():
        raise PlaneError(f"projection path escapes its generation: {relative!r}")
    return child


def _safe_link_target(relative: str, target: str) -> bool:
    """Allow ``../projects`` links while refusing links outside a generation."""

    target_path = Path(target)
    if target_path.is_absolute():
        return False
    parts: list[str] = []
    for part in (*Path(relative).parent.parts, *target_path.parts):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return False
            parts.pop()
        else:
            parts.append(part)
    return bool(parts)


def _validate_dags(root: Path, dagu: str) -> None:
    binary = shutil.which(dagu) or dagu
    workflow_files = sorted((root / "projects").glob("*/workflows/*.yaml"))
    if not workflow_files:
        return
    for workflow in workflow_files:
        result = subprocess.run(
            [binary, "validate", str(workflow)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            raise PlaneError(
                f"Dagu rejected staged workflow {workflow.relative_to(root)}" + (f":\n{detail}" if detail else "")
            )

"""Generation, validation, activation, and rollback tests for the plane owner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vendomat.plane import (
    GenerationStore,
    PlaneBuild,
    PlaneError,
    PlanePackages,
    PlaneProject,
    RenderedBundle,
    _project_failure,
    load_plane_packages,
    manifest_project_name,
    plan_or_update,
    resolve_projects,
)
from vendomat.plane import digest_bytes as plane_digest

_FAKE_RENDERER = '''#!/usr/bin/env python3
"""A stand-in for `devman project render`/`inspect` used only by plane tests."""
import base64, json, sys
from pathlib import Path

mode = sys.argv[2]
args = {}
rest = sys.argv[3:]
for i in range(0, len(rest), 2):
    args[rest[i].lstrip("-")] = rest[i + 1]

root = Path(args["root"])
output = Path(args["output"])
marker = root / "FAULT"
if marker.is_file():
    sys.stderr.write(marker.read_text())
    raise SystemExit(1)

name = root.name
generation = {
    "generation": int(args["generation"]),
    "devman_runtime": args["devman-runtime"],
    "renderer_digest": "sha256:" + "0" * 64,
    "policy_digest": "sha256:" + "1" * 64,
    "dagu_digest": args["dagu-digest"],
    "toolchain_digest": args["toolchain-digest"],
    "contract_schema": 1,
}
record = {
    "project": name,
    "manifest_digest": "sha256:" + "2" * 64,
    "policy_digest": generation["policy_digest"],
    "plane_generation": generation["generation"],
    "renderer_digest": generation["renderer_digest"],
    "source_digest": "sha256:" + "3" * 64,
    "overlay_digest": None,
    "contract_schema": 1,
}
if mode == "inspect":
    body = {"schema": 1, "project": name, "generation": generation, "record": record, "sources": {}}
else:
    body = {
        "schema": 1,
        "project": name,
        "generation": generation,
        "record": record,
        "files": {
            f"projects/{name}/workflows/check.yaml": base64.b64encode(b"steps: []\\n").decode(),
            f"projects/{name}/projection.json": base64.b64encode((json.dumps(record) + "\\n").encode()).decode(),
        },
        "links": {f"dags/{name}.check.yaml": f"../projects/{name}/workflows/check.yaml"},
        "sources": {},
    }
output.write_text(json.dumps(body))
'''


def _renderer_script(tmp_path: Path) -> str:
    """Write the fake renderer once per test and return its executable path."""

    script = tmp_path / "fake-devman-project"
    script.write_text(_FAKE_RENDERER)
    script.chmod(0o755)
    return str(script)


def _generation(number: int) -> dict[str, object]:
    return {
        "generation": number,
        "devman_runtime": "test-runtime",
        "renderer_digest": plane_digest(b"renderer"),
        "policy_digest": plane_digest(b"policy"),
        "dagu_digest": plane_digest(b"dagu"),
        "toolchain_digest": plane_digest(b"toolchain"),
        "contract_schema": 1,
    }


def _bundle(number: int, body: bytes = b"steps: []\n") -> RenderedBundle:
    generation = _generation(number)
    record = {
        "project": "fixture",
        "manifest_digest": plane_digest(b"manifest"),
        "policy_digest": generation["policy_digest"],
        "plane_generation": number,
        "renderer_digest": generation["renderer_digest"],
        "source_digest": plane_digest(body),
        "overlay_digest": None,
        "contract_schema": 1,
    }
    files = {
        "projects/fixture/workflows/check.yaml": body,
        "projects/fixture/projection.json": (json.dumps(record) + "\n").encode(),
    }
    return RenderedBundle(
        project="fixture",
        generation=generation,
        record=record,
        files=files,
        links={"dags/fixture.check.yaml": "../projects/fixture/workflows/check.yaml"},
        sources={"check": "groups/base/workflows/check.yaml"},
    )


def test_update_activates_one_immutable_generation_and_rolls_back(tmp_path):
    store = GenerationStore(tmp_path / "plane")

    first = store.build([_bundle(1)], dagu="true", activate=True)
    second = store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True)

    assert first.activated
    assert second.activated
    assert store.current_generation() == 2
    assert store.active.resolve() == store.generations / "2"
    assert (store.generations / "1").is_dir()
    assert (store.generations / "2").is_dir()
    assert store.read_generation()["generation"] == 2
    assert store.read_project_records()[0]["project"] == "fixture"

    store.rollback(1)

    assert store.current_generation() == 1
    assert (store.generations / "2").is_dir()


def test_failed_validation_keeps_the_active_generation(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)
    reject = tmp_path / "reject-dagu"
    reject.write_text("#!/bin/sh\nexit 1\n")
    reject.chmod(0o755)

    with pytest.raises(PlaneError, match="Dagu rejected"):
        store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu=str(reject), activate=True)

    assert store.current_generation() == 1
    assert not (store.generations / "2").exists()


def test_plan_validates_without_creating_plane_state(tmp_path):
    root = tmp_path / "plane"
    store = GenerationStore(root)

    result = store.build([_bundle(1)], dagu="true", activate=False)

    assert not result.activated
    assert not root.exists()


def test_unchanged_inputs_are_a_noop(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)

    result = store.build([_bundle(2)], dagu="true", activate=True)

    assert result.noop
    assert store.current_generation() == 1
    assert not (store.generations / "2").exists()


def test_copying_an_unchanged_project_updates_only_generation_identity(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    original = _bundle(1)
    store.build([original], dagu="true", activate=True)
    target = _generation(2)

    copied = store.copy_active_bundle("fixture", target)

    assert copied.generation == target
    assert copied.files["projects/fixture/workflows/check.yaml"] == b"steps: []\n"
    assert copied.record["plane_generation"] == 2
    assert copied.links == original.links


def test_operation_lock_has_one_machine_state_file(tmp_path):
    store = GenerationStore(tmp_path / "plane")

    with store.operation_lock():
        assert (store.root / ".lock").is_file()


def test_recover_moves_interrupted_staging_without_touching_active(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)
    abandoned = store.generations / ".staging-interrupted"
    abandoned.mkdir()
    (abandoned / "partial").write_text("evidence")

    recovered = store.recover()

    assert store.current_generation() == 1
    assert len(recovered) == 1
    assert recovered[0].joinpath("partial").read_text() == "evidence"


def test_recover_preserves_an_interrupted_activation_pointer(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)
    interrupted = store.root / ".active-2.new"
    interrupted.symlink_to(Path("generations") / "1")

    recovered = store.recover()

    assert len(recovered) == 1
    assert recovered[0].name == ".active-2"
    assert recovered[0].is_symlink()
    assert store.current_generation() == 1


def test_manifest_project_name_reads_only_the_portable_identity(tmp_path):
    manifest = tmp_path / ".devman" / "project.toml"
    manifest.parent.mkdir()
    manifest.write_text('schema = 1\nproject = "fixture"\ngroups = ["base"]\npolicy = "stable"\n')

    assert manifest_project_name(tmp_path) == "fixture"


def test_package_closure_requires_known_paths_and_derives_toolchain_identity(tmp_path):
    renderer = tmp_path / "devman-project"
    runtime = tmp_path / "devman"
    dagu = tmp_path / "dagu"
    for path in (renderer, runtime, dagu):
        path.write_text("binary")
    toolchain = tmp_path / "toolchain"
    (toolchain / "share/vendomat").mkdir(parents=True)
    (toolchain / "share/vendomat/toolchain.json").write_text('{"roster":"core"}\n')
    manifest = tmp_path / "plane.json"
    manifest.write_text(
        json.dumps(
            {
                "renderer": str(renderer),
                "runtime": str(runtime),
                "dagu": str(dagu),
                "toolchain": str(toolchain),
            }
        )
    )

    packages = load_plane_packages(manifest)

    assert isinstance(packages, PlanePackages)
    assert packages.renderer == str(renderer)
    assert packages.toolchain_digest == plane_digest(b'{"roster":"core"}\n')


def test_package_closure_rejects_a_missing_renderer(tmp_path):
    manifest = tmp_path / "plane.json"
    manifest.write_text(
        json.dumps(
            {
                "renderer": str(tmp_path / "missing"),
                "runtime": str(tmp_path / "runtime"),
                "dagu": str(tmp_path / "dagu"),
                "toolchain": str(tmp_path / "toolchain"),
            }
        )
    )

    with pytest.raises(PlaneError, match="renderer"):
        load_plane_packages(manifest)


def test_package_closure_requires_a_selected_manifest(monkeypatch):
    monkeypatch.delenv("VENDOMAT_DEVMAN_PLANE_MANIFEST", raising=False)

    with pytest.raises(PlaneError, match="package closure is not selected"):
        load_plane_packages()


def test_project_failure_result_retains_identity_and_blocks_activation(tmp_path):
    project = PlaneProject("broken", tmp_path / "broken", tmp_path, tmp_path)
    result = _project_failure(
        project,
        "update",
        PlaneError("cannot read project identity from .devman/project.toml"),
        {"generation": 3},
    )
    build = PlaneBuild({"generation": 3}, ("broken",), (), False, False, (result,))

    assert result["project"] == "broken"
    assert result["operation"] == "update"
    assert result["status"] == "missing manifest"
    assert result["retained_old_projection"] is True
    assert build.failed


@pytest.mark.parametrize(
    ("detail", "expected_status"),
    [
        ("registered project 'x' is not a directory: /nope", "unreadable project"),
        ("cannot resolve registered project 'x': /nope/metadata.json", "unreadable project"),
        (".devman/project.toml is unreadable for project 'x'", "missing manifest"),
        ("Devman rejected policy 'stable': unknown group", "invalid policy"),
        (
            "Devman could not inspect project 'x':\n"
            "devman: cannot resolve policy 'stable'\n"
            "  group root is not a directory: /policy/groups",
            "invalid policy",
        ),
        ("Dagu rejected staged workflow projects/x/workflows/check.yaml", "invalid workflow"),
        ("Devman could not render project 'x':\nsomething else entirely", "failed render"),
    ],
)
def test_project_failure_classifies_every_known_detail(tmp_path, detail, expected_status):
    project = PlaneProject("x", tmp_path, tmp_path, tmp_path)

    result = _project_failure(project, "update", PlaneError(detail))

    assert result["status"] == expected_status


def test_project_failure_classifies_a_permission_error():
    project = PlaneProject("x", Path("/tmp/x"), Path("/tmp"), Path("/tmp"))
    error = PlaneError("cannot read identity file /var/lib/secrets: [Errno 13] Permission denied")
    error.__cause__ = PermissionError("denied")

    result = _project_failure(project, "update", error)

    assert result["status"] == "permission failure"


def test_resolve_projects_keeps_a_healthy_project_independent_of_a_missing_one(tmp_path):
    healthy_root = tmp_path / "healthy"
    healthy_root.mkdir()

    projects, failures = resolve_projects(
        [("healthy", healthy_root), ("missing", tmp_path / "does-not-exist")],
        devman_state=tmp_path,
        policy_root=tmp_path,
        overlay_root=tmp_path,
    )

    assert [project.name for project in projects] == ["healthy"]
    assert len(failures) == 1
    assert failures[0]["project"] == "missing"
    assert failures[0]["status"] == "unreadable project"
    assert failures[0]["retained_old_projection"] is True


def test_fault_at_renderer_start_touches_no_state(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    project = PlaneProject("fixture", tmp_path / "fixture", tmp_path, tmp_path)

    def fault(boundary):
        if boundary == "renderer-start":
            raise PlaneError("boom: injected at renderer start")

    with pytest.raises(PlaneError, match="renderer start"):
        plan_or_update(
            [project],
            store=store,
            renderer="/nonexistent/devman-project",
            runtime="test-runtime",
            dagu="true",
            toolchain_digest=plane_digest(b"toolchain"),
            activate=True,
            fault=fault,
        )

    assert not store.root.exists()


def test_one_failed_project_beside_one_healthy_project_blocks_activation(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    renderer = _renderer_script(tmp_path)
    healthy_root = tmp_path / "healthy"
    healthy_root.mkdir()
    broken_root = tmp_path / "broken"
    broken_root.mkdir()
    healthy = PlaneProject("healthy", healthy_root, tmp_path, tmp_path)
    broken = PlaneProject("broken", broken_root, tmp_path, tmp_path)

    def fault(boundary):
        if boundary == "project-render:broken":
            raise PlaneError("boom: injected mid-fleet render")

    result = plan_or_update(
        [healthy, broken],
        store=store,
        renderer=renderer,
        runtime="test-runtime",
        dagu="true",
        toolchain_digest=plane_digest(b"toolchain"),
        activate=True,
        fault=fault,
    )

    assert result.failed
    assert not result.activated
    assert store.current_generation() is None
    statuses = {item["project"]: item["status"] for item in result.results}
    assert statuses["healthy"] == "successful render"
    assert statuses["broken"] == "failed render"
    assert all(item["project"] and item["path"] and item["operation"] for item in result.results)


def test_fault_after_staging_completes_cleans_up_and_keeps_active(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)

    def fault(boundary):
        if boundary == "staging-complete":
            raise PlaneError("boom: injected after staging completed")

    with pytest.raises(PlaneError, match="staging completed"):
        store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True, fault=fault)

    assert store.current_generation() == 1
    assert not (store.generations / "2").exists()
    assert not list(store.generations.glob(".staging-*"))
    assert store.recover() == []


def test_fault_after_temporary_pointer_created_recovers_without_disturbing_active(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)

    def fault(boundary):
        if boundary == "after-temp-pointer":
            raise PlaneError("boom: injected after the temporary pointer was created")

    with pytest.raises(PlaneError, match="temporary pointer"):
        store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True, fault=fault)

    assert store.current_generation() == 1
    assert (store.generations / "2").is_dir()

    recovered = store.recover()

    assert len(recovered) == 1
    assert recovered[0].name == ".active-2"
    assert store.current_generation() == 1


def test_fault_before_active_pointer_replacement_recovers_without_disturbing_active(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)

    def fault(boundary):
        if boundary == "before-activate":
            raise PlaneError("boom: injected before the active pointer replacement")

    with pytest.raises(PlaneError, match="active pointer replacement"):
        store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True, fault=fault)

    assert store.current_generation() == 1

    recovered = store.recover()

    assert len(recovered) == 1
    assert store.current_generation() == 1


def test_fault_during_rollback_leaves_the_active_generation_untouched(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)
    store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True)
    assert store.current_generation() == 2

    def fault(boundary):
        if boundary == "rollback":
            raise PlaneError("boom: injected during rollback")

    with pytest.raises(PlaneError, match="during rollback"):
        store.rollback(1, fault=fault)

    assert store.current_generation() == 2
    assert store.recover() == []


def test_failed_rollback_activation_recovers_without_losing_the_active_generation(tmp_path):
    store = GenerationStore(tmp_path / "plane")
    store.build([_bundle(1)], dagu="true", activate=True)
    store.build([_bundle(2, b"steps:\n  - name: changed\n")], dagu="true", activate=True)
    assert store.current_generation() == 2

    def fault(boundary):
        if boundary == "after-temp-pointer":
            raise PlaneError("boom: injected mid-rollback activation")

    with pytest.raises(PlaneError, match="mid-rollback"):
        store.rollback(1, fault=fault)

    assert store.current_generation() == 2

    recovered = store.recover()

    assert len(recovered) == 1
    assert store.current_generation() == 2

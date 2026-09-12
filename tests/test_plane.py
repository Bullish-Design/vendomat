"""Generation, validation, activation, and rollback tests for the plane owner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vendomat.plane import GenerationStore, PlaneError, RenderedBundle, manifest_project_name
from vendomat.plane import digest_bytes as plane_digest


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

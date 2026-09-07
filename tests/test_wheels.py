from __future__ import annotations

from pathlib import Path

import pytest

from vendomat import wheels
from vendomat.wheels import (
    WheelError,
    check_portable,
    check_version_discipline,
    is_iteration_version,
    iteration_version,
    parse_wheel,
    publish_wheel,
    release_tag,
)

PORTABLE = "pyjutsu-0.20.0-cp313-abi3-manylinux_2_39_x86_64.whl"
BARE = "pyjutsu-0.20.0-cp313-abi3-linux_x86_64.whl"


def _wheel(tmp_path, filename=PORTABLE, content=b"wheel bytes"):
    path = tmp_path / filename
    path.write_bytes(content)
    return parse_wheel(path)


def test_parse_wheel_reads_the_identity_out_of_the_filename(tmp_path):
    wheel = _wheel(tmp_path)
    assert (wheel.name, wheel.version) == ("pyjutsu", "0.20.0")
    assert (wheel.python_tag, wheel.abi_tag) == ("cp313", "abi3")
    assert wheel.platform_tag == "manylinux_2_39_x86_64"


def test_parse_wheel_refuses_a_name_it_cannot_read(tmp_path):
    with pytest.raises(WheelError, match="not a wheel filename"):
        parse_wheel(tmp_path / "pyjutsu.whl")


def test_check_portable_rejects_a_bare_linux_tag(tmp_path):
    assert check_portable(_wheel(tmp_path)) == []
    problems = check_portable(_wheel(tmp_path, BARE))
    assert problems and "manylinux" in problems[0]


def test_release_tag_is_derived_from_the_version():
    assert release_tag("0.20.0") == "v0.20.0"


def test_iteration_version_carries_the_source_revision():
    assert iteration_version("0.21.0", "617cca8") == "0.21.0.dev0+617cca8"
    assert is_iteration_version("0.21.0.dev0+617cca8")
    assert not is_iteration_version("0.21.0")


def test_iteration_version_refuses_a_version_that_already_iterates():
    with pytest.raises(WheelError, match="plain release version"):
        iteration_version("0.21.0.dev0+abc", "def")


def test_iteration_builds_are_never_published(tmp_path):
    wheel = _wheel(tmp_path, "pyjutsu-0.21.0.dev0+617cca8-cp313-abi3-manylinux_2_39_x86_64.whl")
    with pytest.raises(WheelError, match="iteration build"):
        check_version_discipline(wheel, "acme/pyjutsu", None)


def test_a_first_upload_of_a_release_version_passes(tmp_path):
    check_version_discipline(_wheel(tmp_path), "acme/pyjutsu", [])


def test_republishing_identical_bytes_passes(tmp_path, monkeypatch):
    wheel = _wheel(tmp_path)
    monkeypatch.setattr(wheels, "_published_sha256", lambda *_: wheels.sha256(wheel.path))
    check_version_discipline(wheel, "acme/pyjutsu", [wheel.filename])


def test_one_version_may_not_gain_a_second_artifact(tmp_path, monkeypatch):
    wheel = _wheel(tmp_path)
    monkeypatch.setattr(wheels, "_published_sha256", lambda *_: "0" * 64)
    with pytest.raises(WheelError, match="One version means one artifact"):
        check_version_discipline(wheel, "acme/pyjutsu", [wheel.filename])


def test_publish_refuses_a_non_portable_store_wheel(tmp_path, monkeypatch):
    monkeypatch.setattr(wheels, "store_wheel", lambda *_: _wheel(tmp_path, BARE))
    with pytest.raises(WheelError, match="not a manylinux tag"):
        publish_wheel("pyjutsu", tmp_path)


def test_publish_refuses_when_the_release_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(wheels, "store_wheel", lambda *_: _wheel(tmp_path))
    monkeypatch.setattr(wheels, "_release_assets", lambda *_: None)
    with pytest.raises(WheelError, match="no release v0.20.0"):
        publish_wheel("pyjutsu", tmp_path)


def test_publish_uploads_the_exact_store_file(tmp_path, monkeypatch):
    wheel = _wheel(tmp_path)
    commands: list[list[str]] = []
    monkeypatch.setattr(wheels, "store_wheel", lambda *_: wheel)
    monkeypatch.setattr(wheels, "_release_assets", lambda *_: ["pyjutsu-0.20.0.tar.gz"])
    monkeypatch.setattr(wheels, "_run", lambda command, cwd=None: commands.append(command) or "")
    report = publish_wheel("pyjutsu", tmp_path)
    assert commands == [["gh", "release", "upload", "v0.20.0", str(wheel.path), "--repo", "Bullish-Design/pyjutsu"]]
    assert f"sha256:  {wheels.sha256(wheel.path)}" in report


def test_publish_dry_run_uploads_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(wheels, "store_wheel", lambda *_: _wheel(tmp_path))
    monkeypatch.setattr(wheels, "_release_assets", lambda *_: [])
    monkeypatch.setattr(wheels, "_run", lambda *_, **__: pytest.fail("dry run must not upload"))
    assert "upload:  skipped (--dry-run)" in publish_wheel("pyjutsu", tmp_path, dry_run=True)


def test_store_wheel_reads_the_single_wheel_out_of_the_build_output(tmp_path, monkeypatch):
    out = tmp_path / "store"
    out.mkdir()
    (out / PORTABLE).write_bytes(b"x")
    monkeypatch.setattr(wheels, "_run", lambda *_, **__: f"{out}\n")
    assert wheels.store_wheel("pyjutsu", Path(".")).filename == PORTABLE

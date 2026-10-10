"""The live cache check: its procedure under fakes, and the live run itself.

The fake tests run in every `testee verify`. They prove the retry, report, and cleanup rules.
`test_live_cache_against_the_host_attic` talks to the real cache. It is opt-in:

    testee check live-cache

A passing fake test does not replace the live run (`CACHE-012`).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from livecache import (
    Blocked,
    Server,
    Settings,
    force_remove,
    load_server,
    narinfo_url,
    netrc_text,
    public_key,
    run_check,
)

ROOT = Path(__file__).resolve().parents[1]
TOKEN_PUSH = "push-secret-token-value"
TOKEN_PULL = "pull-secret-token-value"
KEY = "vendomat:FAKEKEYFAKEKEY="
DEP = "/fake/store/" + "d" * 32 + "-dependency-1.0"
FIXED = "/fake/store/" + "f" * 32 + "-vendomat-0.7.0-rc.1"

CONFIG = f"""
default-server = "push"

[servers.push]
endpoint = "http://127.0.0.1:8089"
token = "{TOKEN_PUSH}"

[servers.pull]
endpoint = "http://127.0.0.1:8089"
token = "{TOKEN_PULL}"
"""


class World:
    """A fake cache, store, and client. `push_ok_from` is the first push attempt that uploads."""

    def __init__(self, tmp: Path, *, push_ok_from: int = 1, corrupt_copy: bool = False, narinfo_500: int = 0) -> None:
        self.tmp = tmp
        self.narinfo_500 = narinfo_500  # the first N narinfo lookups answer HTTP 500
        self.push_ok_from = push_ok_from
        self.corrupt_copy = corrupt_copy
        self.pushes = 0
        self.cached: set[str] = set()
        self.unique: str | None = None
        self.calls: list[list[str]] = []
        self.netrc_modes: list[int] = []
        self.pull_token_seen: list[str | None] = []

    def run(self, argv: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
        argv = list(argv)
        self.calls.append(argv)
        tool = Path(argv[0]).name
        ok = subprocess.CompletedProcess(argv, 0, "", "")
        if tool == "attic" and argv[1] == "--version":
            return subprocess.CompletedProcess(argv, 0, "attic-client 0.1.0\n", "")
        if tool == "nix" and argv[1] == "--version":
            return subprocess.CompletedProcess(argv, 0, "nix (Nix) 2.34.7\n", "")
        if tool == "attic" and argv[1:3] == ["cache", "info"]:
            # The real client prints this on stderr and leaves stdout empty.
            return subprocess.CompletedProcess(argv, 0, "", f"  Public: false\n  Public Key: {KEY}\n")
        if tool == "nix-store" and argv[1] == "--add":
            source = Path(argv[2])
            name = hashlib.sha256(source.read_bytes()).hexdigest()[:32] + "-" + source.name
            target = self.tmp / "store" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)
            self.unique = str(target)
            return subprocess.CompletedProcess(argv, 0, str(target) + "\n", "")
        if tool == "nix-store" and argv[1] == "--query":
            return subprocess.CompletedProcess(argv, 0, "\n".join([*argv[3:], DEP]) + "\n", "")
        if tool == "attic" and argv[1] == "push":
            self.pushes += 1
            if self.pushes < self.push_ok_from:
                return subprocess.CompletedProcess(argv, 1, "❌ some-path: InternalServerError\n", "upload failed")
            for path in [*argv[5:], DEP]:
                self.cached.add(Path(path).name[:32])
            return ok
        if tool == "nix" and argv[1] == "copy":
            netrc = Path(argv[argv.index("netrc-file") + 1])
            self.netrc_modes.append(stat.S_IMODE(netrc.stat().st_mode))
            assert argv[argv.index("substituters") + 1] == ""
            assert argv[argv.index("trusted-public-keys") + 1] == KEY
            root = Path(argv[argv.index("--to") + 1].removeprefix("local?root="))
            destination = root / "nix/store"
            destination.mkdir(parents=True)
            assert self.unique is not None
            content = Path(self.unique).read_bytes()
            (destination / Path(self.unique).name).write_bytes(b"corrupt" if self.corrupt_copy else content)
            readonly = destination / "readonly"
            readonly.mkdir()
            (readonly / "file").write_text("x")
            readonly.chmod(0o555)  # like a store directory
            return ok
        raise AssertionError(f"unexpected command: {argv}")

    def fetch(self, url: str, token: str | None) -> int:
        self.pull_token_seen.append(token)
        if url.endswith("/nix-cache-info"):
            return 200 if token == TOKEN_PULL else 401
        assert token == TOKEN_PULL, "narinfo must use the pull credential"
        if self.narinfo_500 > 0:
            self.narinfo_500 -= 1
            return 500
        return 200 if url.rsplit("/", 1)[1].removesuffix(".narinfo") in self.cached else 404


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    config = tmp_path / "config.toml"
    config.write_text(CONFIG)
    return Settings(
        config=config,
        push_server="push",
        pull_server="pull",
        attic="/fake/bin/attic",
        fixed_path=FIXED,
        size=4096,
        attempts=3,
        pause=7.0,
        logs=tmp_path / "logs",
    )


def run(settings: Settings, world: World, monkeypatch: pytest.MonkeyPatch):
    def pause(seconds: float) -> None:
        world.calls.append(["sleep", str(seconds)])

    return run_check(settings, world.run, world.fetch, sleep=pause)


def test_a_clean_run_passes_with_one_attempt_and_records_the_report(settings, tmp_path, monkeypatch):
    world = World(tmp_path)
    report = run(settings, world, monkeypatch)
    assert report.result == "pass", report.blocker
    assert [a["attempt"] for a in report.push_attempts] == [1]
    assert [s.name for s in report.steps] == [
        "credentials", "tools", "reach", "cache-info", "paths", "push", "narinfo", "cold-substitution",
    ]  # fmt: skip
    assert report.steps[2].detail == {"anonymous_status": 401, "pull_status": 200}
    assert report.versions == {"attic": "attic-client 0.1.0", "nix": "nix (Nix) 2.34.7"}
    saved = json.loads((settings.logs / "report.json").read_text())
    assert saved["result"] == "pass"
    # the push used the push server, one job, and both roots
    push = next(c for c in world.calls if c[:2] == ["/fake/bin/attic", "push"])
    assert push[2:5] == ["-j", "1", "push:vendomat"]
    assert FIXED in push and world.unique in push


def test_no_credential_reaches_the_report_logs_or_arguments(settings, tmp_path, monkeypatch):
    world = World(tmp_path)
    run(settings, world, monkeypatch)
    for secret in (TOKEN_PUSH, TOKEN_PULL):
        assert secret not in (settings.logs / "report.json").read_text()
        assert all(secret not in part for call in world.calls for part in call)
    assert TOKEN_PULL not in repr(load_server(settings.config, "pull"))


def test_the_pull_credential_signs_the_copy_and_the_netrc_is_private_and_removed(settings, tmp_path, monkeypatch):
    world = World(tmp_path)
    run(settings, world, monkeypatch)
    assert world.netrc_modes == [0o600]
    assert not list(settings.logs.glob("work-*")), "the scratch directory must be deleted"


def test_a_push_that_fails_twice_then_passes_reports_three_attempts_and_pauses_between(settings, tmp_path, monkeypatch):
    world = World(tmp_path, push_ok_from=3)
    report = run(settings, world, monkeypatch)
    assert report.result == "pass"
    assert [a["attempt"] for a in report.push_attempts] == [1, 2, 3]
    assert [a["exit"] for a in report.push_attempts] == [1, 1, 0]
    assert report.push_attempts[0]["errors"] == ["❌ some-path: InternalServerError"]
    assert [c for c in world.calls if c[0] == "sleep"] == [["sleep", "7.0"], ["sleep", "7.0"]]


def test_a_push_that_never_uploads_fails_after_the_attempt_limit_and_does_not_copy(settings, tmp_path, monkeypatch):
    world = World(tmp_path, push_ok_from=99)
    report = run(settings, world, monkeypatch)
    assert report.result == "fail"
    assert world.pushes == settings.attempts
    assert not any(c[:2] == ["nix", "copy"] for c in world.calls)
    push_step = next(s for s in report.steps if s.name == "push")
    assert push_step.ok is False and push_step.detail["attempts"] == 3


def test_a_server_error_on_narinfo_fails_the_attempt_and_is_retried_not_blocked(settings, tmp_path, monkeypatch):
    world = World(tmp_path, narinfo_500=3)
    report = run(settings, world, monkeypatch)
    assert report.result == "pass", report.blocker
    first, second = report.push_attempts
    assert [e["status"] for e in first["narinfo_errors"]] == [500, 500, 500]
    assert second["narinfo_errors"] == []
    assert world.pushes == 2


def test_a_server_that_keeps_erroring_ends_as_a_failure_with_the_errors_in_the_report(settings, tmp_path, monkeypatch):
    world = World(tmp_path, narinfo_500=10_000)
    report = run(settings, world, monkeypatch)
    assert report.result == "fail" and report.blocker is None
    assert all(len(a["narinfo_errors"]) == 3 for a in report.push_attempts)  # the survey stops early
    assert not any(c[:2] == ["nix", "copy"] for c in world.calls)


def test_content_that_differs_after_the_cold_copy_fails(settings, tmp_path, monkeypatch):
    world = World(tmp_path, corrupt_copy=True)
    report = run(settings, world, monkeypatch)
    assert report.result == "fail"
    assert report.steps[-1].name == "cold-substitution" and report.steps[-1].ok is False


def test_each_run_adds_a_different_unique_path(settings, tmp_path, monkeypatch):
    first, second = World(tmp_path / "a"), World(tmp_path / "b")
    run(settings, first, monkeypatch)
    run(settings, second, monkeypatch)
    assert first.unique and second.unique
    assert Path(first.unique).name != Path(second.unique).name


def test_a_missing_server_entry_is_a_named_blocker_not_a_pass(settings, tmp_path, monkeypatch):
    world = World(tmp_path)
    broken = replace(settings, pull_server="absent")
    report = run(broken, world, monkeypatch)
    assert report.result == "blocked"
    assert report.blocker and "absent" in report.blocker
    assert world.calls == []


def test_a_pull_credential_the_cache_refuses_is_a_blocker(settings, tmp_path, monkeypatch):
    world = World(tmp_path)
    monkeypatch.setattr(world, "fetch", lambda url, token: 401)
    report = run_check(settings, world.run, world.fetch)
    assert report.result == "blocked" and "HTTP 401" in (report.blocker or "")


def test_missing_configuration_is_a_blocker(tmp_path):
    with pytest.raises(Blocked, match="missing"):
        load_server(tmp_path / "nope.toml", "push")


def test_settings_read_the_environment(tmp_path):
    env = {
        "HOME": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path / "cfg"),
        "VENDOMAT_ATTIC_CACHE": "other",
        "VENDOMAT_LIVE_CACHE_ATTEMPTS": "5",
        "VENDOMAT_LIVE_CACHE_LOGS": str(tmp_path / "out"),
    }
    s = Settings.from_env(env, flake="path:/x")
    assert s.config == tmp_path / "cfg/attic/config.toml"
    assert (s.cache, s.attempts, s.logs, s.flake) == ("other", 5, tmp_path / "out", "path:/x")
    assert (s.push_server, s.pull_server, s.jobs) == ("vendomat-server", "vendomat-pull-check", 1)


def test_pure_helpers():
    server = Server("pull", "http://127.0.0.1:8089", "t")
    expected = "http://127.0.0.1:8089/vendomat/" + "a" * 32 + ".narinfo"
    assert narinfo_url(server, "vendomat", "/nix/store/" + "a" * 32 + "-x") == expected
    netrc = netrc_text(Server("p", "http://127.0.0.1:8089", "tok"))
    assert netrc == "machine 127.0.0.1\nlogin vendomat\npassword tok\n"
    assert public_key("  Public: false\n  Public Key: vendomat:abc=\n") == "vendomat:abc="
    assert public_key("nothing") is None


def test_force_remove_deletes_a_read_only_tree(tmp_path):
    tree = tmp_path / "t" / "d"
    tree.mkdir(parents=True)
    (tree / "f").write_text("x")
    tree.chmod(0o555)
    force_remove(tmp_path / "t")
    assert not (tmp_path / "t").exists()


LIVE = os.environ.get("VENDOMAT_LIVE_CACHE") == "1"


@pytest.mark.skipif(not LIVE, reason="live cache; run `testee check live-cache` (sets VENDOMAT_LIVE_CACHE=1)")
def test_live_cache_against_the_host_attic():
    settings = Settings.from_env(os.environ, flake=f"path:{ROOT}")
    report = run_check(settings)
    print(f"live-cache report: {settings.logs / 'report.json'}")
    print(f"live-cache result: {report.result}; push attempts: {len(report.push_attempts)}")
    assert report.result == "pass", report.blocker or f"failed; see {settings.logs / 'report.json'}"

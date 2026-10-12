"""The catalog module on pinned Nixpkgs, with a stub primop (DOOR-074, DOOR-075).

The stub parses JSON, so each fixture writes JSON text into `vendomat.yaml`. The checks cover the
module: the mapping, the missing file, and the one error that lists every bad field. They do not
cover the YAML parser, which the fork gates cover. Opt in with `testee verify e2e`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture, run

ROOT = Path(__file__).resolve().parents[1]

pytestmark = needs_nix_fixture


def nixpkgs_rev() -> str:
    lock = json.loads((ROOT / "flake.lock").read_text())
    return lock["nodes"]["nixpkgs"]["locked"]["rev"]


def evaluate(workspace: Path, text: str | None, read: str = "summary"):
    """Evaluate the module for a workspace. ``text`` is the file content, or None for no file."""
    file = workspace / "vendomat.yaml"
    if text is not None:
        file.write_text(text)
    argv = ["nix-instantiate", "--extra-experimental-features", "flakes", "--eval", "--strict", "--json"]
    argv += [str(ROOT / "tests/nix/catalog.nix"), "--argstr", "root", str(workspace)]
    argv += ["--argstr", "repo", str(ROOT), "--argstr", "nixpkgs", nixpkgs_rev(), "--argstr", "read", read]
    return run(argv, workspace)


def fault_lines(stderr: str) -> list[str]:
    return [line.strip() for line in stderr.splitlines() if line.strip().startswith("vendomat.yaml:")]


def test_a_valid_file_maps_to_native_options(tmp_path: Path):
    text = json.dumps(
        {
            "programs": ["ripgrep", "python3Packages.requests"],
            "languages": {"javascript": {"version": "22"}, "python": {"enable": "false", "version": "3.10"}},
            "services": {"postgres": {"enable": "true"}, "redis": {"enable": "false"}},
            "env": {"VERSION": "3.10", "NAME": "no"},
        }
    )
    result = evaluate(tmp_path, text)
    assert result.returncode == 0, result.stderr[-3000:]
    out = json.loads(result.stdout)
    assert out["packages"] == ["ripgrep", "requests"]
    # Text stays text: `3.10` is not a number and `no` is not a boolean.
    assert out["env"] == {"VERSION": "3.10", "NAME": "no"}
    # `enable: "false"` turns python off even with a version; its version is not mapped.
    assert out["python"]["enable"] is False
    assert out["python"]["version"] is None
    assert out["javascript"]["enable"] is True
    assert out["javascript"]["package"].startswith("nodejs-22")
    assert out["services"] == {"postgres": {"enable": True}, "redis": {"enable": False}}
    # A rust entry with a version selects the rust-overlay channel.
    rust = evaluate(tmp_path, json.dumps({"languages": {"rust": {"version": "1.81.0"}}}))
    assert json.loads(rust.stdout)["rust"] == {"channel": "stable", "enable": True, "version": "1.81.0"}


def test_a_missing_file_is_an_empty_catalog(tmp_path: Path):
    result = evaluate(tmp_path, None)
    assert result.returncode == 0, result.stderr[-3000:]
    out = json.loads(result.stdout)
    assert out["packages"] == [] and out["env"] == {}
    assert out["python"]["enable"] is False


def test_one_error_lists_every_bad_field(tmp_path: Path):
    text = json.dumps(
        {
            "programs": ["ripgrep", "nosuchpkg", "alsomissing"],
            "languages": {"python": {"enable": "no", "enabled": "true"}, "javascript": {"version": "99"}},
            "services": {"postgres": {"enable": "maybe"}},
            "env": {"GREETING": ["hello"]},
            "bogus": "x",
        }
    )
    result = evaluate(tmp_path, text)
    assert result.returncode != 0
    lines = fault_lines(result.stderr)
    fields = [line.split(" ", 2)[1].rstrip(":") for line in lines]
    assert sorted(fields) == sorted(
        [
            "bogus",
            "languages.python.enabled",
            "env",
            "languages.python.enable",
            "services.postgres.enable",
            "programs",  # nosuchpkg
            "programs",  # alsomissing
            "languages.javascript.version",
        ]
    ), lines
    assert any('"nosuchpkg"' in line for line in lines)
    assert any('"alsomissing"' in line for line in lines)
    assert any("unknown key" in line and "bogus" in line for line in lines)


@pytest.mark.parametrize(
    "document",
    [
        {"languages": {"rust": {"enable": "false", "version": "not-a-version"}}},  # a bad value in an unused field
        {"languages": {"gleam": {"enable": "true"}}},  # an unknown key
    ],
)
def test_a_bad_file_stops_a_read_that_uses_no_catalog_value(tmp_path: Path, document: dict):
    # `devenv.root` feeds from no catalog value. The module system still reads `_module.check`.
    result = evaluate(tmp_path, json.dumps(document), read="root")
    assert result.returncode != 0
    assert fault_lines(result.stderr)


def test_a_catalog_that_is_not_a_map_fails(tmp_path: Path):
    result = evaluate(tmp_path, json.dumps({"languages": "python", "services": ["redis"]}))
    assert result.returncode != 0
    lines = fault_lines(result.stderr)
    assert any(line.startswith("vendomat.yaml: languages must be a map") for line in lines)
    assert any(line.startswith("vendomat.yaml: services must be a map") for line in lines)

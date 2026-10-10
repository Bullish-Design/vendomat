"""`path`, `check`, `push`, and `bump` for devenv workspaces (`CLI-018` to `CLI-021`, `VMOD-006`)."""

from __future__ import annotations

import base64
import json
import stat
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vendomat.bump import bump, set_ref, summary
from vendomat.check import check_workspace, pin_problems
from vendomat.cli import app
from vendomat.devenvgen import sync_devenv
from vendomat.lockpath import LockPathError, input_path_from_lock, sri_to_hex
from vendomat.push import PushError, parse_paths, push
from vendomat.registry import parse_registry

runner = CliRunner()
REV = "1" * 40
TOML = """\
[targets]
devenv = true

[passthrough]
nixpkgs = { url = "path:/x/nixpkgs", flake = false }

[inputs]
data = { url = "path:/x/data", flake = false }
vendomat = { url = "git://s/vendomat", ref = "refs/tags/v0.6.0", flake = false }
"""


def sri(text: str) -> str:
    return "sha256-" + base64.b64encode(bytes.fromhex(text.ljust(64, "0"))).decode()


def stub(tmp: Path, name: str, body: str) -> str:
    path = tmp / name
    path.write_text("#!/bin/sh\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def workspace(tmp: Path, toml: str = TOML, name: str = "ws") -> Path:
    root = tmp / name
    root.mkdir()
    (root / "vendomat.toml").write_text(toml)
    return root


def locked(root: Path, **overrides) -> dict:
    nodes = {
        "root": {"inputs": {"data": "data", "vendomat": "vendomat", "nixpkgs": "nixpkgs"}},
        "nixpkgs": {
            "locked": {"narHash": sri("dd"), "type": "path"},
            "original": {"type": "path", "path": "/x/nixpkgs"},
        },
        "data": {"locked": {"narHash": sri("aa"), "type": "path"}, "original": {"type": "path", "path": "/x/data"}},
        "vendomat": {
            "locked": {
                "rev": REV,
                "narHash": sri("bb"),
                "type": "git",
                "ref": "refs/tags/v0.6.0",
                "url": "git://s/vendomat",
            },
            "original": {"type": "git", "url": "git://s/vendomat", "ref": "refs/tags/v0.6.0"},
        },
    }
    nodes.update(overrides)
    (root / "devenv.lock").write_text(json.dumps({"nodes": nodes, "root": "root", "version": 7}))
    return nodes


def synced(tmp: Path, toml: str = TOML, name: str = "ws") -> Path:
    root = workspace(tmp, toml, name)
    sync_devenv(root, parse_registry(toml), "0.7.0", update_lock=False)
    locked(root)
    return root


# --- path ------------------------------------------------------------------------------------


def test_sri_converts_to_hex():
    assert sri_to_hex(sri("ab")) == "ab" + "00" * 31


def test_path_comes_from_the_lock_with_no_network(tmp_path):
    root = synced(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    # The stub prints the path that `nix-store --print-fixed-path` would name for this hash.
    nix_store = stub(tmp_path, "nix-store", f'echo "{store}/$(echo "$4" | cut -c1-8)-source"\n')
    (store / f"{sri_to_hex(sri('bb'))[:8]}-source").mkdir()
    assert input_path_from_lock(root, "vendomat", nix_store).endswith("-source")


def test_path_names_an_input_that_is_locked_but_absent_from_the_store(tmp_path):
    root = synced(tmp_path)
    nix_store = stub(tmp_path, "nix-store", f'echo "{tmp_path}/missing-source"\n')
    with pytest.raises(LockPathError, match="not in the store"):
        input_path_from_lock(root, "vendomat", nix_store)


def test_path_of_an_unknown_input_lists_the_known_ones(tmp_path):
    root = synced(tmp_path)
    with pytest.raises(LockPathError, match="known inputs: data, nixpkgs, vendomat"):
        input_path_from_lock(root, "ghost", "nix-store")


def test_path_follows_a_follows_edge(tmp_path):
    root = synced(tmp_path)
    nodes = json.loads((root / "devenv.lock").read_text())
    nodes["nodes"]["root"]["inputs"]["alias"] = ["vendomat"]
    (root / "devenv.lock").write_text(json.dumps(nodes))
    nix_store = stub(tmp_path, "nix-store", f'echo "{tmp_path}/x-source"\n')
    (tmp_path / "x-source").mkdir()
    assert input_path_from_lock(root, "alias", nix_store) == f"{tmp_path}/x-source"


# --- check -----------------------------------------------------------------------------------


def test_a_clean_workspace_has_no_problem(tmp_path):
    root = synced(tmp_path)
    assert check_workspace(root, check_version=False) == []


def test_a_branch_pin_is_named(tmp_path):
    root = synced(tmp_path)
    locked(
        root,
        vendomat={
            "locked": {"rev": REV, "narHash": sri("bb"), "type": "git"},
            "original": {"type": "git", "url": "git://s/vendomat", "ref": "main"},
        },
    )
    problems = check_workspace(root, check_version=False)
    assert any(p.kind == "pin" and p.name == "vendomat" and "not pinned to a tag" in p.message for p in problems)


def test_a_transitive_unpinned_node_is_named():
    lock = {"nodes": {"deep": {"original": {"type": "git", "url": "git://s/deep"}, "locked": {"rev": REV}}}}
    assert [p.name for p in pin_problems(lock)] == ["deep"]


def test_a_git_node_without_a_revision_is_named():
    lock = {
        "nodes": {
            "a": {"original": {"type": "git", "url": "u", "ref": "refs/tags/v1"}, "locked": {"ref": "refs/tags/v1"}}
        }
    }
    assert "40-hex" in pin_problems(lock)[0].message


def test_a_stale_registry_and_a_hand_edit_are_named(tmp_path):
    root = synced(tmp_path)
    (root / "vendomat.toml").write_text(TOML + "# edit\n")
    (root / ".vendomat" / "devenv.yaml").write_text("# hand\n")
    messages = [p.message for p in check_workspace(root, check_version=False)]
    assert any("vendomat.toml changed" in m for m in messages)
    assert any("edited by hand" in m for m in messages)


def test_an_input_missing_from_the_lock_is_named(tmp_path):
    root = synced(tmp_path)
    nodes = json.loads((root / "devenv.lock").read_text())
    del nodes["nodes"]["root"]["inputs"]["data"]
    (root / "devenv.lock").write_text(json.dumps(nodes))
    assert any(p.kind == "lock" and p.name == "data" for p in check_workspace(root, check_version=False))


def devenv_node(rev: str, directory: str = "src/modules") -> dict:
    return {
        "devenv": {
            "locked": {
                "rev": rev,
                "dir": directory,
                "type": "git",
                "narHash": sri("cc"),
                "ref": "refs/tags/v2.4.0-vendomat.2",
            },
            "original": {
                "type": "git",
                "url": "git://s/devenv",
                "ref": "refs/tags/v2.4.0-vendomat.2",
                "dir": directory,
            },
        }
    }


def test_the_version_check_compares_the_cli_with_the_locked_modules(tmp_path):
    root = synced(tmp_path)
    locked(root, **devenv_node("b904dcb" + "0" * 33))
    good = stub(tmp_path, "devenv-good", 'echo "devenv 2.4.0+b904dcb (x86_64-linux)"\n')
    bad = stub(tmp_path, "devenv-bad", 'echo "devenv 2.4.0+aaaaaaa (x86_64-linux)"\n')
    assert check_workspace(root, devenv_cmd=good) == []
    problems = check_workspace(root, devenv_cmd=bad)
    assert any(p.kind == "version" and "built from aaaaaaa" in p.message for p in problems)


def test_the_version_check_requires_the_modules_directory(tmp_path):
    root = synced(tmp_path)
    locked(root, **devenv_node("b904dcb" + "0" * 33, directory="src"))
    good = stub(tmp_path, "devenv-good", 'echo "devenv 2.4.0+b904dcb"\n')
    assert any("dir=src/modules" in p.message for p in check_workspace(root, devenv_cmd=good))


def test_check_command_exit_codes(tmp_path):
    root = synced(tmp_path)
    ok = runner.invoke(app, ["check", "--root", str(root), "--no-version"])
    assert ok.exit_code == 0 and "clean" in ok.output
    (root / "vendomat.toml").write_text(TOML + "# edit\n")
    bad = runner.invoke(app, ["check", "--root", str(root), "--no-version", "--json"])
    assert bad.exit_code == 1
    assert json.loads(bad.output)["ok"] is False


# --- push ------------------------------------------------------------------------------------


def test_parse_paths_reads_json_and_lines():
    assert parse_paths('["/nix/store/a", "/nix/store/b"]') == ["/nix/store/a", "/nix/store/b"]
    assert parse_paths('{"shell": "/nix/store/a"}') == ["/nix/store/a"]
    assert parse_paths("noise\n/nix/store/a\n") == ["/nix/store/a"]


def test_push_sends_exactly_the_built_paths_to_attic(tmp_path):
    root = synced(tmp_path)
    log = tmp_path / "attic.log"
    devenv = stub(tmp_path, "devenv", 'echo \'["/nix/store/aaa-x", "/nix/store/bbb-y"]\'\n')
    attic = stub(tmp_path, "attic", f'echo "$@" > {log}\ncat >> {log}\n')
    result = push(root, "vendomat", devenv_cmd=devenv, attic_cmd=attic, check_version=False)
    assert result.pushed and result.paths == ("/nix/store/aaa-x", "/nix/store/bbb-y")
    assert log.read_text().splitlines() == ["push vendomat --stdin", "/nix/store/aaa-x", "/nix/store/bbb-y"]


def test_a_bad_pin_prevents_the_build_and_the_push(tmp_path):
    root = synced(tmp_path)
    locked(
        root,
        vendomat={
            "locked": {"rev": REV, "narHash": sri("bb"), "type": "git"},
            "original": {"type": "git", "url": "git://s/vendomat", "ref": "main"},
        },
    )
    marker = tmp_path / "ran"
    devenv = stub(tmp_path, "devenv", f"touch {marker}\necho '[\"/nix/store/a\"]'\n")
    attic = stub(tmp_path, "attic", f"touch {marker}\n")
    with pytest.raises(PushError) as info:
        push(root, "vendomat", devenv_cmd=devenv, attic_cmd=attic, check_version=False)
    assert info.value.code == 1 and "not pinned to a tag" in str(info.value)
    assert not marker.exists()


def test_a_failed_build_pushes_nothing(tmp_path):
    root = synced(tmp_path)
    marker = tmp_path / "attic-ran"
    devenv = stub(tmp_path, "devenv", "echo 'error: boom' >&2\nexit 1\n")
    attic = stub(tmp_path, "attic", f"touch {marker}\n")
    with pytest.raises(PushError, match="failed"):
        push(root, "vendomat", devenv_cmd=devenv, attic_cmd=attic, check_version=False)
    assert not marker.exists()


def test_a_failed_attic_push_is_an_error(tmp_path):
    root = synced(tmp_path)
    devenv = stub(tmp_path, "devenv", "echo '[\"/nix/store/a\"]'\n")
    attic = stub(tmp_path, "attic", "echo denied >&2\nexit 3\n")
    with pytest.raises(PushError, match="exit 3"):
        push(root, "vendomat", devenv_cmd=devenv, attic_cmd=attic, check_version=False)


def test_push_builds_a_machine_attribute(tmp_path):
    root = synced(tmp_path)
    log = tmp_path / "devenv.log"
    devenv = stub(tmp_path, "devenv", f'echo "$@" > {log}\necho \'["/nix/store/a"]\'\n')
    push(root, "c", machine="server", dry_run=True, devenv_cmd=devenv, check_version=False)
    assert log.read_text().strip() == "build machines.server.build.nixos"


# --- bump ------------------------------------------------------------------------------------


def fleet(tmp: Path) -> Path:
    base = tmp / "fleet"
    base.mkdir()
    for name in ("alpha", "beta", "gamma"):
        sub = base / name
        sub.mkdir()
        (sub / "vendomat.toml").write_text(TOML)
    (base / "noise").mkdir()
    (base / "noise" / "vendomat.toml").write_text('[inputs]\nx = { url = "path:/x" }\n')  # a flake workspace
    return base


def test_set_ref_edits_one_inline_entry():
    text, old = set_ref(TOML, "vendomat", "refs/tags/v0.7.0")
    assert old == "refs/tags/v0.6.0"
    assert 'ref = "refs/tags/v0.7.0"' in text
    assert text.replace("v0.7.0", "v0.6.0") == TOML
    with pytest.raises(ValueError, match="not a single inline table"):
        set_ref(TOML, "missing", "x")


def test_a_dry_run_changes_nothing_and_reports_each_workspace(tmp_path):
    base = fleet(tmp_path)
    before = {p: p.read_bytes() for p in base.rglob("vendomat.toml")}
    entries = bump(base, "v0.7.0")
    assert sorted(e.path.name for e in entries) == ["alpha", "beta", "gamma"]
    assert all(e.status == "would-change" for e in entries)
    assert before == {p: p.read_bytes() for p in base.rglob("vendomat.toml")}
    assert not any((base / n / ".vendomat").exists() for n in ("alpha", "beta", "gamma"))


def test_apply_moves_each_pin_and_reports_one_failing_gate(tmp_path):
    base = fleet(tmp_path)
    (base / "beta" / "FAILGATE").write_text("x")
    entries = bump(base, "v0.7.0", apply=True, gate=["sh", "-c", "test ! -e FAILGATE"], update_lock=False)
    by_name = {e.path.name: e for e in entries}
    assert by_name["alpha"].status == "changed" and by_name["alpha"].gate == "passed"
    assert by_name["beta"].gate == "failed"
    for name in ("alpha", "beta", "gamma"):
        assert 'ref = "refs/tags/v0.7.0"' in (base / name / "vendomat.toml").read_text()
        assert (base / name / ".vendomat" / "digest").is_file()
    verdict, good = summary(entries, applied=True)
    assert good is False and "1 of 3 workspace(s) incomplete: beta" in verdict


def test_a_clean_fleet_run_says_so(tmp_path):
    base = fleet(tmp_path)
    entries = bump(base, "v0.7.0", apply=True, gate=["true"], update_lock=False)
    assert summary(entries, applied=True) == ("all 3 workspace(s) bumped", True)


def test_a_workspace_that_cannot_be_edited_is_skipped_and_named(tmp_path):
    base = tmp_path / "fleet"
    (base / "odd").mkdir(parents=True)
    (base / "odd" / "vendomat.toml").write_text(
        '[targets]\ndevenv = true\n[inputs.vendomat]\nurl = "git://s/v"\nref = "refs/tags/v0.6.0"\n'
    )
    [entry] = bump(base, "v0.7.0")
    assert entry.status == "skipped" and "edit it by hand" in entry.detail
    assert summary([entry], applied=False)[1] is False


def test_bump_cli_is_a_dry_run_by_default(tmp_path):
    base = fleet(tmp_path)
    result = runner.invoke(app, ["bump", "v0.7.0", "--root", str(base)])
    assert result.exit_code == 0, result.output
    assert "dry run" in result.output
    assert 'ref = "refs/tags/v0.6.0"' in (base / "alpha" / "vendomat.toml").read_text()

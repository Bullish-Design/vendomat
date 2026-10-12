"""The project 20 slice 1 gates on the patched fork and the host launcher."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORK = Path(os.environ.get("VENDOMAT_FRONT_DOOR_FORK", ""))
TESTEE = Path(os.environ.get("VENDOMAT_FRONT_DOOR_TESTEE", ""))
LOGS = Path(os.environ.get("VENDOMAT_FRONT_DOOR_LOGS", "/tmp/vendomat-front-door-logs"))
ENABLED = os.environ.get("VENDOMAT_FRONT_DOOR_E2E") == "1"
FORK_VERSION = "devenv 2.4.0+c66ba87"

pytestmark = pytest.mark.skipif(not ENABLED, reason="run through testee verify front-door-e2e")


def command(
    name: str,
    cwd: Path,
    *argv: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one command and save its output outside the repository."""
    LOGS.mkdir(parents=True, exist_ok=True)
    clean = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DEVENV_")
        and key
        not in {
            "IN_NIX_SHELL",
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "NIX_CONFIG",
            "NIX_USER_CONF_FILES",
        }
    }
    clean.update(
        {
            "HOME": os.environ.get("HOME", ""),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "PATH": f"{FORK.parent}:{os.environ.get('PATH', '')}",
        }
    )
    if env:
        clean.update(env)
    result = subprocess.run(argv, cwd=cwd, env=clean, capture_output=True, text=True, check=False)
    text = (
        f"{FORK_VERSION} (x86_64-linux)\n"
        f"$ cd {cwd} && {' '.join(argv)}\n"
        f"exit={result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n"
    )
    (LOGS / f"{name}.log").write_text(text)
    return result


def require_ok(result: subprocess.CompletedProcess[str], label: str) -> str:
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"{label} exited {result.returncode}:\n{output[-5000:]}"
    return output


def nix_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def git(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return command(name, cwd, "git", *args)


def fork_command(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return command(name, cwd, str(FORK), "--no-tui", *args)


def make_release_remote(tmp_path: Path) -> tuple[Path, subprocess.Popen[str], str, str]:
    """Serve a throwaway Vendomat copy with a movable release branch."""
    source = tmp_path / "release-source"
    clone = subprocess.run(
        ["git", "clone", "--shared", "--quiet", str(ROOT), str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert clone.returncode == 0, clone.stderr
    require_ok(git("release-git-config", source, "config", "user.name", "Vendomat gate"), "git config")
    require_ok(git("release-git-email", source, "config", "user.email", "gate@example.invalid"), "git config")
    require_ok(git("release-branch", source, "switch", "-c", "release"), "create release branch")

    module = source / "devenv" / "devenv.nix"
    text = module.read_text()
    old = "    env = guard values.env;"
    assert old in text
    release_env = '    env = (guard values.env) // { VENDOMAT_RELEASE_MARK = "one"; };'
    module.write_text(text.replace(old, release_env, 1))
    require_ok(git("release-v1-add", source, "add", "devenv/devenv.nix"), "stage release one")
    require_ok(git("release-v1-commit", source, "commit", "-m", "fixture release one"), "commit release one")
    first = require_ok(git("release-v1-rev", source, "rev-parse", "HEAD"), "read release one").strip()

    remote_root = tmp_path / "git-daemon"
    remote_root.mkdir()
    remote = remote_root / "vendomat.git"
    bare_clone = command(
        "release-bare-clone",
        tmp_path,
        "git",
        "clone",
        "--bare",
        "--quiet",
        str(source),
        str(remote),
    )
    require_ok(bare_clone, "create release remote")
    (remote / "git-daemon-export-ok").touch()

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    daemon_log = LOGS / "git-daemon.log"
    daemon_stream = daemon_log.open("w")
    daemon = subprocess.Popen(
        [
            "git",
            "daemon",
            "--reuseaddr",
            "--export-all",
            f"--base-path={remote_root}",
            "--listen=127.0.0.1",
            f"--port={port}",
            "--verbose",
            str(remote_root),
        ],
        stdout=daemon_stream,
        stderr=subprocess.STDOUT,
        text=True,
    )
    url = f"git://127.0.0.1:{port}/vendomat?ref=release"
    for _ in range(40):
        if daemon.poll() is not None:
            raise AssertionError(f"git daemon exited: {daemon_log.read_text()}")
        probe = subprocess.run(
            ["git", "ls-remote", url.removesuffix("?ref=release"), "refs/heads/release"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0 and first in probe.stdout:
            break
        time.sleep(0.1)
    else:
        daemon.terminate()
        raise AssertionError(f"git daemon did not serve release: {daemon_log.read_text()}")
    return source, daemon, url, first


def set_fixture_url(workspace: Path, url: str, *, with_testee: bool = False) -> None:
    path = workspace / "devenv.yaml"
    text = path.read_text().replace("git://server/vendomat?ref=release", url)
    if with_testee:
        marker = "  nixpkgs:\n    follows: vendomat/nixpkgs\nimports:\n  - vendomat/devenv\n"
        replacement = (
            "  nixpkgs:\n"
            "    follows: vendomat/nixpkgs\n"
            "  testee:\n"
            "    url: git+https://github.com/Bullish-Design/testee?ref=refs/tags/v0.6.1\n"
            "    flake: false\n"
            "imports:\n"
            "  - vendomat/devenv\n"
            "  - testee/nix/testee.nix\n"
        )
        assert marker in text
        text = text.replace(marker, replacement, 1)
    path.write_text(text)


def set_probe_nix(workspace: Path) -> None:
    enter_test = nix_quote(f"touch {workspace / 'ran-test.marker'}")
    task = nix_quote(f"touch {workspace / 'ran-task.marker'}")
    catalog_check = r"""
  testee.checks.catalog-value.argv = [
    "${pkgs.bash}/bin/bash"
    "-c"
    "test \"$CATALOG_VALUE\" = 3.10"
  ];
"""
    (workspace / "devenv.nix").write_text(
        "{ pkgs, ... }: {\n"
        '  outputs.hello = pkgs.runCommand "front-door-unmapped" { } "printf hello > $out";\n'
        f"  enterTest = {enter_test};\n"
        f'  tasks."frontdoor:mark".exec = {task};\n'
        f"{catalog_check}"
        "}\n"
    )


def env_probe(name: str, workspace: Path) -> str:
    result = fork_command(
        name,
        workspace,
        "shell",
        "--",
        "bash",
        "-c",
        (
            'printf "VALUES=%s,%s,%s\n" "${VERSION_TEXT-unset}" "${NAME-unset}" '
            '"${CATALOG_VALUE-unset}"; '
            'printf "RELEASE=%s\n" "${VENDOMAT_RELEASE_MARK-unset}"'
        ),
    )
    return require_ok(result, name)


def commit_workspace(workspace: Path, name: str) -> None:
    if not (workspace / ".git").exists():
        require_ok(git(f"{name}-git-init", workspace, "init", "-b", "main"), f"{name} git init")
        require_ok(git(f"{name}-git-name", workspace, "config", "user.name", "Vendomat gate"), "git user name")
        user_email = git(
            f"{name}-git-email",
            workspace,
            "config",
            "user.email",
            "gate@example.invalid",
        )
        require_ok(user_email, "git user email")
    require_ok(git(f"{name}-git-add", workspace, "add", "-A"), f"{name} git add")
    require_ok(git(f"{name}-git-commit", workspace, "commit", "-m", name), f"{name} git commit")


def test_slice_one_front_door_and_catalog_gates(tmp_path: Path):
    assert FORK.is_file(), f"missing patched fork: {FORK}"
    assert TESTEE.is_file(), f"missing host Testee: {TESTEE}"
    LOGS.mkdir(parents=True, exist_ok=True)
    version = require_ok(command("fork-version", tmp_path, str(FORK), "version"), "fork version")
    assert version.startswith(FORK_VERSION), version

    nix_config = require_ok(command("nix-config", ROOT, "nix", "show-config"), "nix config")
    unsafe = re.search(r"^allow-unsafe-native-code-during-evaluation = (\w+)", nix_config, re.MULTILINE)
    assert unsafe and unsafe.group(1) == "false", nix_config

    build_result = command(
        "build-launcher",
        ROOT,
        "nix",
        "build",
        "--no-link",
        "--print-out-paths",
        ".#launcher",
    )
    require_ok(build_result, "build launcher")
    launcher_dir = Path(build_result.stdout.strip().splitlines()[-1])
    launcher = launcher_dir / "bin" / "vendomat"
    assert launcher.is_file(), launcher
    wrapper = (launcher_dir / "bin" / ".vendomat-wrapped").read_text()
    assert str(FORK) in wrapper

    source, daemon, release_url, release_one = make_release_remote(tmp_path)
    try:
        workspace = tmp_path / "new-workspace"
        require_ok(command("vendomat-new", tmp_path, str(launcher), "new", str(workspace)), "vendomat new")
        expected_files = {"vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore"}
        assert {path.name for path in workspace.iterdir()} == expected_files
        set_fixture_url(workspace, release_url, with_testee=True)
        set_probe_nix(workspace)
        (workspace / ".envrc").write_text('eval "$(devenv direnvrc)"\nuse devenv\n')

        # A new workspace enters through the actual host launcher and the patched fork.
        require_ok(command("vendomat-bare-entry", workspace, str(launcher)), "bare vendomat")
        shell_created = fork_command(
            "shell-created",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            "printf SHELL=ready\\n",
        )
        require_ok(shell_created, "new workspace shell")
        assert "SHELL=ready" in (LOGS / "shell-created.log").read_text()
        assert (workspace / "devenv.lock").exists()
        lock = json.loads((workspace / "devenv.lock").read_text())
        assert lock["nodes"]["vendomat"]["locked"]["rev"] == release_one

        # The launcher passes native devenv commands to the fork and preserves its status.
        pass_through = command("vendomat-pass-through", workspace, str(launcher), "version")
        assert pass_through.returncode == 0 and "2.4.0+c66ba87" in pass_through.stdout
        missing_command = command(
            "vendomat-unknown-command",
            workspace,
            str(launcher),
            "front-door-unknown-command",
        )
        assert missing_command.returncode == 2, missing_command.stdout + missing_command.stderr

        # The file is a live input. Create, edit, and delete it without another setup command.
        absent = env_probe("file-missing", workspace)
        assert "VALUES=unset,unset,unset" in absent
        (workspace / "vendomat.yaml").write_text("programs:\n  - ripgrep\nenv:\n  GREETING: one\n")
        create_result = fork_command(
            "file-create",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'printf "GREETING=%s\\n" "$GREETING"; command -v rg',
        )
        created = require_ok(create_result, "create catalog")
        assert "GREETING=one" in created and "-ripgrep-" in created
        (workspace / "vendomat.yaml").write_text("env:\n  GREETING: two\n")
        edit_result = fork_command(
            "file-edit",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'printf "GREETING=%s\\n" "$GREETING"',
        )
        edited = require_ok(edit_result, "edit catalog")
        assert "GREETING=two" in edited
        (workspace / "vendomat.yaml").unlink()
        deleted = env_probe("file-delete", workspace)
        assert "VALUES=unset,unset,unset" in deleted

        # The YAML parser keeps scalar text and the option type rejects `enable: no`.
        text_yaml = (
            "languages:\n  python:\n    enable: false\n    version: 3.10\n"
            "env:\n  VERSION_TEXT: 3.10\n  NAME: no\n  CATALOG_VALUE: 3.10\n"
        )
        (workspace / "vendomat.yaml").write_text(text_yaml)
        text_values = env_probe("text-values", workspace)
        assert "VALUES=3.10,no,3.10" in text_values
        (workspace / "vendomat.yaml").write_text("services:\n  redis:\n    enable: no\n")
        enable_no = fork_command("enable-no", workspace, "shell", "--", "true")
        assert enable_no.returncode != 0 and "services.redis.enable" in enable_no.stderr

        # Every catalog fault stops shell, test, both build forms, and tasks before user work.
        (workspace / "vendomat.yaml").write_text(text_yaml)
        set_probe_nix(workspace)
        build_unmapped = fork_command("build-unmapped-valid", workspace, "build", "outputs.hello")
        require_ok(build_unmapped, "build unmapped output")
        faults = {
            "unknown-key": "unknown:\n  value: yes\n",
            "bad-used": "services:\n  redis:\n    enable: maybe\n",
            "bad-unused": "languages:\n  rust:\n    enable: false\n    version: not-a-version\n",
            "unknown-program": "programs:\n  - vendomat-no-such-package-7319\n",
        }
        for case, document in faults.items():
            (workspace / "vendomat.yaml").write_text(document)
            for label, args in (
                ("shell", ("shell", "--", "touch", str(workspace / "ran-shell.marker"))),
                ("test", ("test",)),
                ("build-shell", ("build", "shell")),
                ("build-unmapped", ("build", "outputs.hello")),
                ("tasks", ("tasks", "run", "frontdoor:mark")),
            ):
                for marker in workspace.glob("ran-*.marker"):
                    marker.unlink()
                result = fork_command(f"fault-{case}-{label}", workspace, *args)
                assert result.returncode != 0, f"{case}/{label} unexpectedly passed"
                assert "vendomat.yaml:" in result.stderr, result.stderr[-3000:]
                assert not list(workspace.glob("ran-*.marker")), f"{case}/{label} ran user work"

        combined = (
            "programs:\n  - vendomat-no-such-package-7319\n"
            "languages:\n  python:\n    enable: no\n    enabled: true\n"
            "  javascript:\n    version: 999\n"
            "services:\n  postgres:\n    enable: maybe\n"
            "env:\n  GREETING:\n    - hello\n"
            "unknown:\n  value: x\n"
        )
        (workspace / "vendomat.yaml").write_text(combined)
        all_faults = fork_command("all-faults", workspace, "shell", "--", "true")
        assert all_faults.returncode != 0
        fields = (
            "programs",
            "languages.python.enable",
            "languages.python.enabled",
            "languages.javascript.version",
            "services.postgres.enable",
            "env",
            "unknown",
        )
        for field in fields:
            assert field in all_faults.stderr, f"missing {field}:\n{all_faults.stderr}"

        (workspace / "vendomat.yaml").write_text("languages:\n  python:\n\tenable: true\n")
        syntax = fork_command("syntax-line-column", workspace, "shell", "--", "true")
        assert syntax.returncode != 0 and "vendomat.yaml:3:1:" in syntax.stderr, syntax.stderr

        # Update follows the release branch. Restoring the old lock restores the old shell.
        (workspace / "vendomat.yaml").write_text(text_yaml)
        before_result = fork_command(
            "channel-before",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'echo RELEASE="$VENDOMAT_RELEASE_MARK"',
        )
        before = require_ok(before_result, "read release one")
        assert "RELEASE=one" in before
        old_lock = (workspace / "devenv.lock").read_bytes()
        module = source / "devenv" / "devenv.nix"
        text = module.read_text()
        assert 'VENDOMAT_RELEASE_MARK = "one";' in text
        changed_module = text.replace(
            'VENDOMAT_RELEASE_MARK = "one";',
            'VENDOMAT_RELEASE_MARK = "two";',
            1,
        )
        module.write_text(changed_module)
        require_ok(git("release-v2-add", source, "add", "devenv/devenv.nix"), "stage release two")
        require_ok(git("release-v2-commit", source, "commit", "-m", "fixture release two"), "commit release two")
        second = require_ok(git("release-v2-rev", source, "rev-parse", "HEAD"), "read release two").strip()
        remote = tmp_path / "git-daemon" / "vendomat.git"
        move_ref = command(
            "release-v2-push",
            source,
            "git",
            "push",
            "--quiet",
            str(remote),
            "HEAD:refs/heads/release",
        )
        require_ok(move_ref, "move release ref")
        remote_head = require_ok(
            git("release-v2-remote-head", remote, "rev-parse", "refs/heads/release"),
            "read moved release ref",
        ).strip()
        assert remote_head == second
        still_one_result = fork_command(
            "channel-still-locked",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'echo RELEASE="$VENDOMAT_RELEASE_MARK"',
        )
        still_one = require_ok(still_one_result, "check old lock")
        assert "RELEASE=one" in still_one
        require_ok(fork_command("channel-update", workspace, "update", "vendomat"), "update release")
        moved_result = fork_command(
            "channel-after-update",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'echo RELEASE="$VENDOMAT_RELEASE_MARK"',
        )
        moved = require_ok(moved_result, "read release two")
        assert "RELEASE=two" in moved
        (workspace / "devenv.lock").write_bytes(old_lock)
        restore_result = fork_command(
            "channel-restore",
            workspace,
            "shell",
            "--",
            "bash",
            "-c",
            'echo RELEASE="$VENDOMAT_RELEASE_MARK"',
        )
        restored = require_ok(restore_result, "restore old lock")
        assert "RELEASE=one" in restored
        assert (workspace / "devenv.lock").read_bytes() == old_lock

        # Direnv and a fresh clone use the same release lock and catalog.
        direnv_env = {
            "XDG_CONFIG_HOME": str(LOGS / "direnv-config"),
            "XDG_DATA_HOME": str(LOGS / "direnv-data"),
        }
        allow_new = command("direnv-allow-new", workspace, "direnv", "allow", env=direnv_env)
        require_ok(allow_new, "allow workspace")
        direnv_result = command(
            "direnv-new",
            workspace,
            "direnv",
            "exec",
            str(workspace),
            "bash",
            "-c",
            'echo DIRENV="$VENDOMAT_RELEASE_MARK:$CATALOG_VALUE"',
            env=direnv_env,
        )
        direnv_result = require_ok(direnv_result, "direnv workspace")
        assert "DIRENV=one:3.10" in direnv_result
        commit_workspace(workspace, "workspace-before-clone")
        clone = tmp_path / "fresh-clone"
        clone_result = command("workspace-clone", tmp_path, "git", "clone", "--quiet", str(workspace), str(clone))
        require_ok(clone_result, "clone workspace")
        allow_clone = command("direnv-allow-clone", clone, "direnv", "allow", env=direnv_env)
        require_ok(allow_clone, "allow clone")
        clone_shell = command(
            "clone-shell",
            clone,
            str(FORK),
            "--no-tui",
            "shell",
            "--",
            "bash",
            "-c",
            'echo CLONE="$VENDOMAT_RELEASE_MARK:$CATALOG_VALUE"',
        )
        cloned = require_ok(clone_shell, "clone shell")
        assert "CLONE=one:3.10" in cloned
        clone_direnv_result = command(
            "direnv-clone",
            clone,
            "direnv",
            "exec",
            str(clone),
            "bash",
            "-c",
            'echo CLONE_DIRENV="$VENDOMAT_RELEASE_MARK:$CATALOG_VALUE"',
            env=direnv_env,
        )
        clone_direnv = require_ok(clone_direnv_result, "direnv clone")
        assert "CLONE_DIRENV=one:3.10" in clone_direnv

        # Testee verifies a consumer, reports RED for a valid changed value, and returns GREEN after restore.
        testee_env = {
            "PATH": f"{FORK.parent}:{os.environ.get('PATH', '')}",
            "TESTEE_STATE_DIR": str(LOGS / "testee-state"),
        }
        initial = command(
            "testee-green",
            workspace,
            str(TESTEE),
            "--root",
            str(workspace),
            "verify",
            env=testee_env,
        )
        require_ok(initial, "Testee initial green")
        assert "GREEN" in initial.stdout

        changed_yaml = text_yaml.replace("CATALOG_VALUE: 3.10", "CATALOG_VALUE: 3.11")
        (workspace / "vendomat.yaml").write_text(changed_yaml)
        commit_workspace(workspace, "workspace-value-red")
        red = command(
            "testee-red",
            workspace,
            str(TESTEE),
            "--root",
            str(workspace),
            "verify",
            env=testee_env,
        )
        assert red.returncode == 1 and "RED" in red.stdout, red.stdout + red.stderr

        (workspace / "vendomat.yaml").write_text("services:\n  redis:\n    enable: no\n")
        commit_workspace(workspace, "workspace-invalid-refusal")
        refused = command(
            "testee-invalid-refusal",
            workspace,
            str(TESTEE),
            "--root",
            str(workspace),
            "verify",
            env=testee_env,
        )
        assert refused.returncode == 2 and "vendomat.yaml" in refused.stdout + refused.stderr

        (workspace / "vendomat.yaml").write_text(text_yaml)
        commit_workspace(workspace, "workspace-restored-green")
        green = command(
            "testee-green-again",
            workspace,
            str(TESTEE),
            "--root",
            str(workspace),
            "verify",
            env=testee_env,
        )
        require_ok(green, "Testee restored green")
        assert "GREEN" in green.stdout
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)

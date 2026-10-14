"""The front-door gates on stock devenv, the host launcher, and the catalog with the Nix parser.

Project 24, slice S3. The gates (the project 20 slice 1 list, rewritten for the new catalog):

- the host launcher builds from this repository and enters a new workspace;
- `vendomat new` writes the template, and the shell of a fresh workspace starts;
- `vendomat.yaml` is a live input: create, edit, and delete need no other command;
- every catalog fault stops shell, test, both build forms, and tasks before user work;
- the launcher prints the trimmed error, and `explain` and `update` run through it;
- an update moves the release, and the old lock restores the old shell;
- direnv and a fresh clone use the same release lock and catalog;
- Testee 0.8 verifies the consumer through its devenv tasks: GREEN, RED for a changed value, a refusal for an
  invalid file, GREEN after the restore.

It runs stock devenv from `PATH` and a scratch copy of this repository as the `vendomat` release. The `devenv`
input is the one that the lock of the copied repository pins (the published S1 tag), through the template line
`devenv: follows: vendomat/devenv`. Environment:

    VENDOMAT_FRONT_DOOR_E2E=1         opt in (run through `testee verify front-door-e2e`).
    VENDOMAT_FRONT_DOOR_DEVENV=PATH   the devenv command (default: `devenv` on PATH).
    VENDOMAT_FRONT_DOOR_MODULES=DIR   a `src/modules` tree that replaces the `follows` line with a `path:` input.
    VENDOMAT_FRONT_DOOR_TESTEE=PATH   the testee command (default: `testee` on PATH).
    VENDOMAT_FRONT_DOOR_LOGS=DIR      the log directory, outside the repository.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from nixfixture import s1_devenv_input

ROOT = Path(__file__).resolve().parents[1]
DEVENV = Path(os.environ.get("VENDOMAT_FRONT_DOOR_DEVENV") or shutil.which("devenv") or "")
MODULES = os.environ.get("VENDOMAT_FRONT_DOOR_MODULES", "")
DEVENV_LABEL = s1_devenv_input(MODULES)[1] if MODULES else "follows: vendomat/devenv, " + s1_devenv_input()[1]
LOGS = Path(os.environ.get("VENDOMAT_FRONT_DOOR_LOGS", "/tmp/vendomat-front-door-logs"))
TESTEE = Path(os.environ.get("VENDOMAT_FRONT_DOOR_TESTEE") or shutil.which("testee") or "")
ENABLED = os.environ.get("VENDOMAT_FRONT_DOOR_E2E") == "1"
DEVENV_VERSION = "devenv 2.4.0"
#: The pins of the inputs that the template does not pin, so the gate needs no GitHub API call.
PINS = {
    "github:cachix/nixpkgs-python": "github:cachix/nixpkgs-python/4d2bd16c09baaa04f4045f16f6a5574654aaba16",
    "github:oxalica/rust-overlay": "github:oxalica/rust-overlay/8111d2b45adcbaeaff037f996643f1ac43f944e6",
}

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
            "VENDOMAT_HIDE_ADVANCED",
        }
    }
    clean.update(
        {
            "HOME": os.environ.get("HOME", ""),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "PATH": f"{DEVENV.parent}:{os.environ.get('PATH', '')}",
            "VENDOMAT_DEVENV_FORK": str(DEVENV),
            "XDG_STATE_HOME": str(LOGS / "state"),
        }
    )
    if env:
        clean.update(env)
    result = subprocess.run(
        argv, cwd=cwd, env=clean, capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL
    )
    text = (
        f"{DEVENV_VERSION} (x86_64-linux), devenv input {DEVENV_LABEL}\n"
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


def devenv_command(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return command(name, cwd, str(DEVENV), "--no-tui", *args)


def copy_repository(target: Path) -> None:
    """Copy the files of this repository into `target`. The copy does not depend on the version control in use."""
    ignore = shutil.ignore_patterns(
        ".git", ".jj", ".gitman", ".devenv", ".direnv", ".scratch", ".venv", "__pycache__", ".pytest_cache", "result"
    )
    shutil.copytree(ROOT, target, ignore=ignore)


def make_release_remote(tmp_path: Path) -> tuple[Path, subprocess.Popen[str], str, str]:
    """Serve a throwaway Vendomat copy with a movable release branch."""
    source = tmp_path / "release-source"
    copy_repository(source)
    require_ok(git("release-git-init", source, "init", "-q", "-b", "release"), "git init")
    require_ok(git("release-git-config", source, "config", "user.name", "Vendomat gate"), "git config")
    require_ok(git("release-git-email", source, "config", "user.email", "gate@example.invalid"), "git config")
    require_ok(git("release-v0-add", source, "add", "-A"), "stage release zero")
    require_ok(git("release-v0-commit", source, "commit", "-q", "-m", "fixture release zero"), "commit release zero")
    # The host launcher comes from this copy, before the release marks change the catalog.
    build_result = command(
        "build-launcher", source, "nix", "build", "--no-link", "--print-out-paths", f"path:{source}#launcher"
    )
    require_ok(build_result, "build launcher")
    (tmp_path / "launcher-path").write_text(build_result.stdout.strip().splitlines()[-1])

    module = source / "devenv" / "devenv.nix"
    text = module.read_text()
    old = "    env = guard (raw.env or { });"
    assert old in text
    release_env = '    env = (guard (raw.env or { })) // { VENDOMAT_RELEASE_MARK = "one"; };'
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


def set_fixture_inputs(workspace: Path, url: str) -> None:
    """Point `vendomat` at the throwaway release, and pin the language inputs.

    `devenv` keeps the template line `follows: vendomat/devenv`, so the lock of the release copy pins it.
    An override replaces the line with a `path:` input.
    """
    path = workspace / "devenv.yaml"
    text = path.read_text().replace("git://server/vendomat?ref=release", url)
    follows = "  devenv:\n    follows: vendomat/devenv\n"
    assert follows in text
    if MODULES:
        text = text.replace(follows, f"  devenv:\n    url: {s1_devenv_input(MODULES)[0]}\n", 1)
    for old, pinned in PINS.items():
        assert f"url: {old}\n" in text, old
        text = text.replace(f"url: {old}\n", f"url: {pinned}\n", 1)
    path.write_text(text)


def set_probe_nix(workspace: Path) -> None:
    """The user's `devenv.nix`: user work that a catalog fault must stop, and the five Testee 0.8 tasks.

    Four tasks are the "not applicable" form. `test:full` checks the catalog value, so a changed value is RED.
    """
    enter_test = nix_quote(f"touch {workspace / 'ran-test.marker'}")
    task = nix_quote(f"touch {workspace / 'ran-task.marker'}")
    not_applicable = "".join(
        f'  tasks."{name}".exec = "echo \'n/a: front-door fixture\'; exit 0";\n'
        for name in ("check:lint", "check:format", "check:types", "test:quick")
    )
    (workspace / "devenv.nix").write_text(
        "{ pkgs, ... }: {\n"
        '  outputs.hello = pkgs.runCommand "front-door-unmapped" { } "printf hello > $out";\n'
        f"  enterTest = {enter_test};\n"
        f'  tasks."frontdoor:mark".exec = {task};\n'
        f"{not_applicable}"
        '  tasks."test:full".exec = "test \\"$CATALOG_VALUE\\" = 3.10";\n'
        "}\n"
    )


def env_probe(name: str, workspace: Path) -> str:
    result = devenv_command(
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


def release_mark(name: str, workspace: Path) -> str:
    result = devenv_command(name, workspace, "shell", "--", "bash", "-c", 'echo RELEASE="$VENDOMAT_RELEASE_MARK"')
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
    require_ok(git(f"{name}-git-commit", workspace, "commit", "--allow-empty", "-m", name), f"{name} git commit")


def test_front_door_and_catalog_gates(tmp_path: Path):
    assert DEVENV.is_file(), f"missing devenv: {DEVENV}"
    assert not MODULES or Path(MODULES).is_dir(), f"missing devenv module tree: {MODULES}"
    LOGS.mkdir(parents=True, exist_ok=True)
    version = require_ok(command("devenv-version", tmp_path, str(DEVENV), "version"), "devenv version")
    assert version.startswith(DEVENV_VERSION), version

    nix_config = require_ok(command("nix-config", ROOT, "nix", "show-config"), "nix config")
    unsafe = re.search(r"^allow-unsafe-native-code-during-evaluation = (\w+)", nix_config, re.MULTILINE)
    assert unsafe and unsafe.group(1) == "false", nix_config

    source, daemon, release_url, release_one = make_release_remote(tmp_path)
    try:
        launcher_dir = Path((tmp_path / "launcher-path").read_text())
        launcher = launcher_dir / "bin" / "vendomat"
        assert launcher.is_file(), launcher

        workspace = tmp_path / "new-workspace"
        require_ok(command("vendomat-new", tmp_path, str(launcher), "new", str(workspace)), "vendomat new")
        expected_files = {"vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore"}
        assert {path.name for path in workspace.iterdir()} == expected_files
        set_fixture_inputs(workspace, release_url)
        set_probe_nix(workspace)
        (workspace / ".envrc").write_text('eval "$(devenv direnvrc)"\nuse devenv\n')

        # A new workspace enters through the actual host launcher and stock devenv.
        require_ok(command("vendomat-bare-entry", workspace, str(launcher)), "bare vendomat")
        shell_created = devenv_command("shell-created", workspace, "shell", "--", "bash", "-c", "printf SHELL=ready\\n")
        require_ok(shell_created, "new workspace shell")
        assert "SHELL=ready" in (LOGS / "shell-created.log").read_text()
        assert (workspace / "devenv.lock").exists()
        lock = json.loads((workspace / "devenv.lock").read_text())
        assert lock["nodes"]["vendomat"]["locked"]["rev"] == release_one
        # The workspace lock pins the S1 tag of the release lock (VMT-020, "pin through a published lock").
        pinned = json.loads((ROOT / "flake.lock").read_text())["nodes"]["devenv"]["locked"]["rev"]
        if not MODULES:
            assert pinned in {n.get("locked", {}).get("rev") for n in lock["nodes"].values()}, "S1 rev not in lock"

        # The launcher passes native devenv commands to devenv and preserves its status.
        pass_through = command("vendomat-pass-through", workspace, str(launcher), "version")
        assert pass_through.returncode == 0 and DEVENV_VERSION in pass_through.stdout
        missing_command = command("vendomat-unknown-command", workspace, str(launcher), "front-door-unknown-command")
        assert missing_command.returncode == 2, missing_command.stdout + missing_command.stderr

        # The file is a live input. Create, edit, and delete it without another setup command.
        absent = env_probe("file-missing", workspace)
        assert "VALUES=unset,unset,unset" in absent
        (workspace / "vendomat.yaml").write_text("programs:\n  - ripgrep\nenv:\n  GREETING: one\n")
        create_result = devenv_command(
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
        edit_result = devenv_command(
            "file-edit", workspace, "shell", "--", "bash", "-c", 'printf "GREETING=%s\\n" "$GREETING"'
        )
        edited = require_ok(edit_result, "edit catalog")
        assert "GREETING=two" in edited
        (workspace / "vendomat.yaml").unlink()
        deleted = env_probe("file-delete", workspace)
        assert "VALUES=unset,unset,unset" in deleted

        # The Nix parser keeps scalar text and the option type rejects `enable: no`.
        text_yaml = (
            "languages:\n  python:\n    enable: false\n    version: 3.12\n"
            "env:\n  VERSION_TEXT: 3.10\n  NAME: no\n  CATALOG_VALUE: 3.10\n"
        )
        (workspace / "vendomat.yaml").write_text(text_yaml)
        text_values = env_probe("text-values", workspace)
        assert "VALUES=3.10,no,3.10" in text_values
        (workspace / "vendomat.yaml").write_text("services:\n  redis:\n    enable: no\n")
        enable_no = devenv_command("enable-no", workspace, "shell", "--", "true")
        assert enable_no.returncode != 0 and "services.redis.enable" in enable_no.stderr

        # Every catalog fault stops shell, test, both build forms, and tasks before user work.
        (workspace / "vendomat.yaml").write_text(text_yaml)
        set_probe_nix(workspace)
        build_unmapped = devenv_command("build-unmapped-valid", workspace, "build", "outputs.hello")
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
                result = devenv_command(f"fault-{case}-{label}", workspace, *args)
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
        all_faults = devenv_command("all-faults", workspace, "shell", "--", "true")
        assert all_faults.returncode != 0
        fields = (
            "programs",
            "languages.python.enable",
            "languages.python.enabled",
            "languages.javascript.version",
            "services.postgres.enable",
            "env.GREETING",
            "unknown",
        )
        for field in fields:
            assert field in all_faults.stderr, f"missing {field}:\n{all_faults.stderr}"

        (workspace / "vendomat.yaml").write_text("languages:\n  python:\n\tenable: true\n")
        syntax = devenv_command("syntax-line-column", workspace, "shell", "--", "true")
        assert syntax.returncode != 0 and "vendomat.yaml:3:" in syntax.stderr, syntax.stderr

        # The launcher trims the error (VMT-117) and keeps the full trace.
        (workspace / "vendomat.yaml").write_text(combined)
        trimmed = command("launcher-trimmed-error", workspace, str(launcher))
        assert trimmed.returncode == 2 and trimmed.stdout == "", trimmed.stdout + trimmed.stderr
        lines = trimmed.stderr.splitlines()
        assert lines[0].startswith("vendomat: the workspace does not evaluate")
        assert lines[1].startswith("vendomat.yaml:1:") or lines[1].startswith("vendomat.yaml:2:"), lines[:3]
        assert len(lines) < 15, trimmed.stderr
        log = Path(lines[-1].removeprefix("vendomat: the full trace is in "))
        assert log.parent == LOGS / "state" / "vendomat" / "logs" and len(log.read_text().splitlines()) > 100

        # `explain` and `update` run through the launcher.
        (workspace / "vendomat.yaml").write_text(text_yaml)
        explained = command("launcher-explain", workspace, str(launcher), "explain", "--json")
        require_ok(explained, "vendomat explain")
        report = json.loads(explained.stdout)
        assert {entry["key"] for entry in report["yaml"]} >= {"languages.python.version", "env.CATALOG_VALUE"}
        checked = command("launcher-update-check", workspace, str(launcher), "update", "--check")
        require_ok(checked, "vendomat update --check")

        # Update follows the release branch. Restoring the old lock restores the old shell.
        before = release_mark("channel-before", workspace)
        assert "RELEASE=one" in before
        old_lock = (workspace / "devenv.lock").read_bytes()
        module = source / "devenv" / "devenv.nix"
        text = module.read_text()
        assert 'VENDOMAT_RELEASE_MARK = "one";' in text
        module.write_text(text.replace('VENDOMAT_RELEASE_MARK = "one";', 'VENDOMAT_RELEASE_MARK = "two";', 1))
        require_ok(git("release-v2-add", source, "add", "devenv/devenv.nix"), "stage release two")
        require_ok(git("release-v2-commit", source, "commit", "-m", "fixture release two"), "commit release two")
        second = require_ok(git("release-v2-rev", source, "rev-parse", "HEAD"), "read release two").strip()
        remote = tmp_path / "git-daemon" / "vendomat.git"
        move_ref = command("release-v2-push", source, "git", "push", "--quiet", str(remote), "HEAD:refs/heads/release")
        require_ok(move_ref, "move release ref")
        remote_head = require_ok(
            git("release-v2-remote-head", remote, "rev-parse", "refs/heads/release"), "read moved release ref"
        ).strip()
        assert remote_head == second
        assert "RELEASE=one" in release_mark("channel-still-locked", workspace)
        require_ok(command("channel-update", workspace, str(launcher), "update", "vendomat"), "update release")
        assert "RELEASE=two" in release_mark("channel-after-update", workspace)
        (workspace / "devenv.lock").write_bytes(old_lock)
        assert "RELEASE=one" in release_mark("channel-restore", workspace)
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
        clone_shell = devenv_command(
            "clone-shell", clone, "shell", "--", "bash", "-c", 'echo CLONE="$VENDOMAT_RELEASE_MARK:$CATALOG_VALUE"'
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

        # Testee 0.8 verifies the consumer through its devenv tasks: GREEN, RED for a changed value, a refusal
        # for an invalid file, and GREEN again after the restore.
        assert TESTEE.is_file(), f"missing testee: {TESTEE}"
        testee_env = {"TESTEE_STATE_DIR": str(LOGS / "testee-state")}

        def verify(name: str) -> subprocess.CompletedProcess[str]:
            return command(name, workspace, str(TESTEE), "--root", str(workspace), "verify", env=testee_env)

        (workspace / "vendomat.yaml").write_text(text_yaml)
        commit_workspace(workspace, "workspace-testee-base")
        initial = verify("testee-green")
        require_ok(initial, "Testee initial green")
        assert "GREEN" in initial.stdout

        (workspace / "vendomat.yaml").write_text(text_yaml.replace("CATALOG_VALUE: 3.10", "CATALOG_VALUE: 3.11"))
        commit_workspace(workspace, "workspace-value-red")
        red = verify("testee-red")
        assert red.returncode == 1 and "RED" in red.stdout, red.stdout + red.stderr

        (workspace / "vendomat.yaml").write_text("services:\n  redis:\n    enable: no\n")
        commit_workspace(workspace, "workspace-invalid-refusal")
        refused = verify("testee-invalid-refusal")
        assert refused.returncode != 0 and "vendomat.yaml" in refused.stdout + refused.stderr, refused.stdout

        (workspace / "vendomat.yaml").write_text(text_yaml)
        commit_workspace(workspace, "workspace-restored-green")
        green = verify("testee-green-again")
        require_ok(green, "Testee restored green")
        assert "GREEN" in green.stdout
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)

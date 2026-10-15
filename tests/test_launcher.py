"""The host launcher (`DEL-020`, `DOOR-071`).

It enters the pinned devenv shell, copies the workspace template, runs the host release for the Vendomat
commands, and passes every other argument to the pinned devenv fork. A fake fork stands in for the real one.
"""

from __future__ import annotations

import shutil
import signal
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "launcher" / "vendomat"
JQ = shutil.which("jq")
pytestmark = pytest.mark.skipif(JQ is None or shutil.which("bash") is None, reason="needs bash and jq")


def script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class Env:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.bin = tmp / "bin"
        self.bin.mkdir()
        script(tmp / "host" / "bin" / "vendomat", 'echo "HOST $*"\n')
        # The fork prints its argv, one argument per line, and exits with $FAKE_FORK_EXIT (default 0).
        self.fork = script(
            tmp / "fork" / "bin" / "devenv",
            'echo "FORK $#"; for a in "$@"; do echo "[$a]"; done; exit "${FAKE_FORK_EXIT:-0}"\n',
        )
        # The workspace template sits beside the host release: ../share/vendomat/templates/workspace.
        template = tmp / "host" / "share" / "vendomat" / "templates" / "workspace"
        template.mkdir(parents=True)
        for name in ("vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore"):
            (template / name).write_text(f"# {name}\n")
            (template / name).chmod(0o444)  # a store file is read-only
        (template / "sub").mkdir()
        (template / "sub" / "file").write_text("x\n")
        (template / "sub" / "file").chmod(0o444)
        self.env = {
            "PATH": f"{self.bin}:{Path(JQ or '/').parent}:/run/current-system/sw/bin:/usr/bin:/bin",
            "HOME": str(tmp / "home"),
            "VENDOMAT_HOST_RELEASE": str(tmp / "host" / "bin" / "vendomat"),
            "VENDOMAT_DEVENV_FORK": str(self.fork),
        }

    def run(self, cwd: Path, *args: str, extra_env: dict[str, str] | None = None):
        return subprocess.run(
            ["bash", str(LAUNCHER), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={**self.env, **(extra_env or {})},
        )


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


# DOOR-071: the pinned devenv fork.


def fork_args(done) -> list[str]:
    """The arguments that the fake fork received."""

    lines = done.stdout.splitlines()
    assert lines and lines[0].startswith("FORK "), done.stdout + done.stderr
    return [line[1:-1] for line in lines[1:]]


def test_no_argument_enters_the_shell_of_the_fork_anywhere(env, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert fork_args(env.run(elsewhere)) == ["shell"]
    root = tmp_path / "ws"
    root.mkdir()
    assert fork_args(env.run(root)) == ["shell"]


@pytest.mark.parametrize(
    "argv",
    [
        ("test",),
        ("shell", "--", "ls", "-l"),
        ("--verbose", "test"),
        ("tasks", "run", "x y"),
    ],
)
def test_every_other_argument_goes_to_the_fork_unchanged(env, tmp_path, argv):
    root = tmp_path / "ws"
    root.mkdir()
    for cwd in (tmp_path, root):
        done = env.run(cwd, *argv)
        assert fork_args(done) == list(argv)
        assert done.stderr == ""


def test_the_exit_status_of_the_fork_passes_through(env, tmp_path):
    done = env.run(tmp_path, "test", extra_env={"FAKE_FORK_EXIT": "7"})
    assert done.returncode == 7
    assert fork_args(done) == ["test"]


def test_a_missing_fork_stops_with_one_line(env, tmp_path):
    done = env.run(tmp_path, "test", extra_env={"VENDOMAT_DEVENV_FORK": str(tmp_path / "none")})
    assert done.returncode == 2
    assert done.stderr.strip() == f"vendomat: no devenv fork at {tmp_path / 'none'}"


def test_a_signal_reaches_the_fork_and_its_status_comes_back(env, tmp_path):
    ready = tmp_path / "ready"
    script(
        tmp_path / "slow" / "devenv",
        f"""
        trap 'echo got-TERM; exit 42' TERM
        touch {ready}
        while :; do sleep 0.1; done
        """,
    )
    proc = subprocess.Popen(
        ["bash", str(LAUNCHER), "test"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        text=True,
        env={**env.env, "VENDOMAT_DEVENV_FORK": str(tmp_path / "slow" / "devenv")},
    )
    for _ in range(100):
        if ready.exists():
            break
        subprocess.run(["sleep", "0.1"])
    assert ready.exists()
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=10)
    assert proc.returncode == 42
    assert "got-TERM" in out


@pytest.mark.parametrize("argv", [("push", "--cache", "c"), ("--version",), ("--help",)])
def test_push_and_the_flags_run_the_host_release(env, tmp_path, argv):
    assert env.run(tmp_path, *argv).stdout.strip() == "HOST " + " ".join(argv)


@pytest.mark.parametrize("verb", ["sync", "path", "check", "bump", "machine"])
def test_a_removed_verb_is_refused_with_one_line(env, tmp_path, verb):
    done = env.run(tmp_path, verb, "x")
    assert done.returncode == 3
    assert done.stdout == ""
    assert f"'{verb}' was removed" in done.stderr


@pytest.mark.parametrize("argv", [("apply",), ("apply", "--dirty"), ("rollback",), ("rollback", "--fast")])
def test_apply_and_rollback_always_run_the_host_release(env, tmp_path, argv):
    # They act on this machine. They need neither a pinned build nor the workspace shell (R15, R30).
    elsewhere = tmp_path / "machine"
    elsewhere.mkdir()
    assert env.run(elsewhere, *argv).stdout.strip() == "HOST " + " ".join(argv)
    # A workspace of the old flow does not send them to the shell either.
    root = tmp_path / "ws"
    root.mkdir()
    done = env.run(root, *argv)
    assert done.stdout.strip() == "HOST " + " ".join(argv)
    assert done.returncode == 0 and "runs in the workspace shell" not in done.stderr


TEMPLATE_FILES = {"vendomat.yaml", "devenv.yaml", "devenv.nix", ".gitignore", "sub/file"}


def files_under(path: Path) -> set[str]:
    return {str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()}


def test_new_copies_the_template_into_the_current_directory(env, tmp_path):
    target = tmp_path / "ws"
    target.mkdir()
    done = env.run(target, "new")
    assert done.returncode == 0, done.stderr
    assert files_under(target) == TEMPLATE_FILES
    assert (target / "devenv.nix").read_text() == "# devenv.nix\n"
    assert done.stdout.count("\n") == 1 and "vendomat.yaml" in done.stdout


def test_new_uses_the_imported_template_source(env, tmp_path):
    template = tmp_path / "imported-template"
    template.mkdir()
    (template / "devenv.yaml").write_text("# tracked imported template\n")
    (template / "vendomat.yaml").write_text("# tracked catalog template\n")
    target = tmp_path / "basix-workspace"
    target.mkdir()
    done = env.run(target, "new", extra_env={"VENDOMAT_TEMPLATE": str(template)})
    assert done.returncode == 0, done.stderr
    assert (target / "devenv.yaml").read_text() == "# tracked imported template\n"
    assert (target / "vendomat.yaml").read_text() == "# tracked catalog template\n"
    assert files_under(target) == {"devenv.yaml", "vendomat.yaml"}


def test_new_makes_the_files_writable_and_creates_the_directory(env, tmp_path):
    done = env.run(tmp_path, "new", "made/here")
    assert done.returncode == 0, done.stderr
    target = tmp_path / "made" / "here"
    assert files_under(target) == TEMPLATE_FILES
    for name in TEMPLATE_FILES:
        assert (target / name).stat().st_mode & stat.S_IWUSR
    (target / "vendomat.yaml").write_text("programs: []\n")


def test_new_refuses_when_a_template_file_exists_and_writes_nothing(env, tmp_path):
    target = tmp_path / "ws"
    target.mkdir()
    (target / "devenv.nix").write_text("mine\n")
    (target / "other").write_text("keep\n")
    done = env.run(target, "new")
    assert done.returncode == 1
    assert done.stdout == ""
    assert len(done.stderr.strip().splitlines()) == 1 and "devenv.nix" in done.stderr
    assert (target / "devenv.nix").read_text() == "mine\n"
    assert files_under(target) == {"devenv.nix", "other"}


def test_new_takes_at_most_one_directory(env, tmp_path):
    done = env.run(tmp_path, "new", "a", "b")
    assert done.returncode == 3 and "usage: vendomat new [DIR]" in done.stderr


# --- update, explain, and the check before the shell (S3 part 2) -----------------------------------

TRACE = Path(__file__).parent / "fixtures" / "trim" / "yaml-faults.txt"
TRACE_BASIX = Path(__file__).parent / "fixtures" / "trim" / "basix-yaml-faults.txt"


@pytest.mark.parametrize("argv", [("update",), ("update", "vendomat"), ("update", "--check"), ("explain", "--json")])
def test_update_and_explain_run_the_host_release_with_the_fork_and_the_template(env, tmp_path, argv):
    host = script(
        tmp_path / "host2" / "bin" / "vendomat",
        'echo "HOST $*"; echo "DEVENV=$VENDOMAT_DEVENV"; echo "TEMPLATE=$VENDOMAT_TEMPLATE"\n',
    )
    root = tmp_path / "ws"
    root.mkdir()
    for cwd in (tmp_path, root):
        done = env.run(cwd, *argv, extra_env={"VENDOMAT_HOST_RELEASE": str(host)})
        assert done.returncode == 0, done.stderr
        assert done.stdout.splitlines() == [
            f"HOST {' '.join(argv)}",
            f"DEVENV={env.fork}",
            f"TEMPLATE={host.parent}/../share/vendomat/templates/workspace",
        ]


def test_a_set_devenv_command_wins_over_the_fork_for_update(env, tmp_path):
    host = script(tmp_path / "host2" / "bin" / "vendomat", 'echo "DEVENV=$VENDOMAT_DEVENV"\n')
    done = env.run(
        tmp_path, "update", extra_env={"VENDOMAT_HOST_RELEASE": str(host), "VENDOMAT_DEVENV": "/chosen/devenv"}
    )
    assert done.stdout.strip() == "DEVENV=/chosen/devenv"


def precheck_workspace(env, tmp_path, *, evaluates: bool, trace: Path = TRACE) -> tuple[Path, Path]:
    """A workspace with a vendomat.yaml and a fork whose `eval` passes or prints the real trace of a bad file."""
    work = tmp_path / "yamlws"
    work.mkdir()
    (work / "vendomat.yaml").write_text("programs:\n  - jq\n")
    calls = tmp_path / "fork-calls"
    fork = script(
        tmp_path / "pre" / "devenv",
        f"""
        echo "$*" >> {calls}
        if [ "$1" = eval ]; then
          {"exit 0" if evaluates else f"cat {trace} >&2; exit 1"}
        fi
        echo "SHELL $*"
        """,
    )
    env.env["VENDOMAT_DEVENV_FORK"] = str(fork)
    env.env["XDG_STATE_HOME"] = str(tmp_path / "state")
    return work, calls


def test_a_workspace_that_evaluates_enters_the_shell(env, tmp_path):
    work, calls = precheck_workspace(env, tmp_path, evaluates=True)
    done = env.run(work)
    assert done.returncode == 0
    assert done.stdout.strip() == "SHELL shell"
    assert done.stderr == ""
    assert calls.read_text().splitlines() == ["eval devenv.root", "shell"]


def test_a_workspace_that_fails_prints_the_yaml_lines_first_and_keeps_the_trace(env, tmp_path):
    # VMT-117.
    work, calls = precheck_workspace(env, tmp_path, evaluates=False)
    done = env.run(work)
    assert done.returncode == 2
    assert done.stdout == ""  # the shell did not start
    assert calls.read_text().splitlines() == ["eval devenv.root"]
    lines = done.stderr.splitlines()
    assert lines[0] == "vendomat: the workspace does not evaluate (devenv exit 1)"
    assert [line.split(" ", 1)[0] for line in lines[1:5]] == [
        "vendomat.yaml:3:5:",
        "vendomat.yaml:6:14:",
        "vendomat.yaml:9:11:",
        "vendomat.yaml:10:1:",
    ]
    assert len(lines) == 6
    assert lines[5].startswith("vendomat: the full trace is in ")
    log = Path(lines[5].removeprefix("vendomat: the full trace is in "))
    assert log.parent == tmp_path / "state" / "vendomat" / "logs"
    assert log.read_text() == TRACE.read_text()


def test_a_workspace_fault_in_basix_yaml_is_trimmed_and_keeps_the_trace(env, tmp_path):
    work, calls = precheck_workspace(env, tmp_path, evaluates=False, trace=TRACE_BASIX)
    (work / "basix.yaml").write_text("machines:\n  learner:\n    profile: [\n")
    done = env.run(work)
    assert done.returncode == 2
    assert calls.read_text().splitlines() == ["eval devenv.root"]
    lines = done.stderr.splitlines()
    assert lines[1:4] == [
        "basix.yaml:3:14: flow style is not accepted",
        "malformed Basix machine catalog",
        "at /ws/devenv.nix:4:7",
    ]
    assert lines[-1].startswith("vendomat: the full trace is in ")


def test_a_directory_without_vendomat_yaml_runs_no_check(env, tmp_path):
    work, calls = precheck_workspace(env, tmp_path, evaluates=False)
    (work / "vendomat.yaml").unlink()
    done = env.run(work)
    assert done.returncode == 0
    assert calls.read_text().splitlines() == ["shell"]

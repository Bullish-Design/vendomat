"""Trim a devenv failure so the lines of `vendomat.yaml` come first (VMT-117).

The samples in `tests/fixtures/trim/` are real devenv 2.4.0 stderr, with the workspace path rewritten to `/ws`.
The launcher trims in Bash and `vendomat explain` trims in Python. Both must give the same text.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vendomat import errortrim

FIXTURES = Path(__file__).parent / "fixtures" / "trim"
LAUNCHER = Path(__file__).resolve().parents[1] / "launcher" / "vendomat"

FAULTS = [
    'vendomat.yaml:3:5: programs[1]: unknown program "nosuchprog" (nixpkgs has no package with this name)',
    'vendomat.yaml:6:14: languages.python.version must be a version such as "3.12", found "x"',
    'vendomat.yaml:9:11: machines.box.mode must be "fresh-install" or "adopt-existing", found "nope"',
    "vendomat.yaml:10:1: home: unknown key (known: env, languages, machines, programs, services)",
]


def sample(name: str) -> str:
    return (FIXTURES / name).read_text()


def bash_trim(path: Path) -> str:
    """Run the `trim_error` function of the launcher on a file."""
    program = f"set -euo pipefail\nsource <(sed -n '/^trim_error() {{/,/^}}/p' {LAUNCHER})\ntrim_error {path}\n"
    done = subprocess.run(["bash", "-c", program], capture_output=True, text=True, check=True)
    return done.stdout.rstrip("\n")


def test_a_real_trace_shrinks_to_the_fault_lines():
    raw = sample("yaml-faults.txt")
    assert len(raw.splitlines()) > 300
    assert errortrim.trim(raw).splitlines() == FAULTS


def test_a_fault_line_that_sits_in_the_trace_still_comes_first():
    text = "\n".join(
        [
            "  vendomat.yaml:2:1: home: unknown key (known: env)",
            "  … while evaluating something",
            "  error: a later message",
            "  details of the message",
        ]
    )
    assert errortrim.trim(text).splitlines() == [
        "vendomat.yaml:2:1: home: unknown key (known: env)",
        "a later message",
        "details of the message",
    ]


def test_a_basix_yaml_fault_line_is_kept_first():
    raw = sample("basix-yaml-faults.txt")
    expected = [
        "basix.yaml:3:14: flow style is not accepted",
        "malformed Basix machine catalog",
        "at /ws/devenv.nix:4:7",
    ]
    assert errortrim.trim(raw).splitlines() == expected
    assert bash_trim(FIXTURES / "basix-yaml-faults.txt").splitlines() == expected


def test_a_failure_without_yaml_lines_shows_the_message_and_its_place():
    assert errortrim.trim(sample("nix-syntax.txt")).splitlines() == [
        "syntax error, unexpected ';'",
        "at /ws/devenv.nix:1:11",
    ]


def test_text_without_an_error_line_comes_back_whole():
    assert errortrim.trim("something\nelse\n") == "something\nelse"


def test_color_codes_do_not_reach_the_user():
    assert "\x1b" not in errortrim.trim("\x1b[31;1merror:\x1b[0m bad \x1b[1mthing\x1b[0m")
    assert errortrim.trim("\x1b[31;1merror:\x1b[0m bad") == "bad"


def test_the_full_trace_goes_to_the_state_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    path = errortrim.save_log("explain", "the whole trace\n")
    assert path is not None and path.parent == tmp_path / "vendomat" / "logs"
    assert path.read_text() == "the whole trace\n"


def test_a_log_directory_that_cannot_be_written_gives_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")
    monkeypatch.setenv("XDG_STATE_HOME", str(blocker))
    assert errortrim.save_log("explain", "x") is None


@pytest.mark.parametrize("name", ["yaml-faults.txt", "basix-yaml-faults.txt", "nix-syntax.txt"])
def test_the_launcher_and_the_python_command_trim_the_same_way(name: str):
    assert bash_trim(FIXTURES / name) == errortrim.trim(sample(name))


def test_the_bash_trim_handles_a_text_without_an_error_line(tmp_path: Path):
    path = tmp_path / "plain.txt"
    path.write_text("something\nelse\n")
    assert bash_trim(path) == "something\nelse"

"""`vendomat update`: add the missing template lines to `devenv.yaml`, then run `devenv update`.

(R25, VMT-094, VMT-058.)
"""

from __future__ import annotations

import stat
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vendomat import update
from vendomat.cli import app
from vendomat.yamlsubset import parse

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace"

OLD = """\
# my workspace
inputs:
  vendomat:
    url: git://server/vendomat?ref=release
  nixpkgs:
    follows: vendomat/nixpkgs
  # my own input
  mytool:
    url: github:me/tool

# end of inputs
imports:
  - vendomat/devenv
  - ./local.nix
"""


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "devenv.yaml").write_text(OLD)
    log = tmp_path / "calls"
    fake = tmp_path / "devenv"
    fake.write_text(f'#!/usr/bin/env bash\necho "$PWD $*" >> {log}\nexit "${{FAKE_EXIT:-0}}"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("VENDOMAT_DEVENV", str(fake))
    monkeypatch.setenv("VENDOMAT_TEMPLATE", str(TEMPLATE))
    return root


def calls(workspace: Path) -> list[str]:
    log = workspace.parent / "calls"
    return log.read_text().splitlines() if log.exists() else []


def test_check_names_each_missing_line_and_exits_one(workspace: Path):
    result = runner.invoke(app, ["update", "--check", "--root", str(workspace)])
    assert result.exit_code == 1
    lines = result.output.splitlines()
    assert lines[0] == "vendomat update: devenv.yaml lacks these lines of the template:"
    assert lines[1:-1] == [
        "  inputs.devenv.follows: vendomat/devenv",
        "  inputs.nixpkgs-python.url: github:cachix/nixpkgs-python",
        "  inputs.nixpkgs-python.inputs.nixpkgs.follows: nixpkgs",
        "  inputs.rust-overlay.url: github:oxalica/rust-overlay",
        "  inputs.rust-overlay.inputs.nixpkgs.follows: nixpkgs",
    ]
    assert (workspace / "devenv.yaml").read_text() == OLD  # --check writes nothing
    assert calls(workspace) == []  # and runs no devenv


def test_update_adds_the_lines_keeps_the_users_lines_and_runs_devenv_update(workspace: Path):
    result = runner.invoke(app, ["update", "--root", str(workspace)])
    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines()[0] == "vendomat update: added to devenv.yaml:"
    assert "  inputs.rust-overlay.url: github:oxalica/rust-overlay" in result.stdout
    text = (workspace / "devenv.yaml").read_text()
    # Every line the user wrote is still there, in order.
    kept = [line for line in OLD.splitlines() if line.strip()]
    position = 0
    for line in kept:
        position = text.index(line, position) + len(line)
    # The new lines carry the template comments and sit inside `inputs`.
    assert "  # Python versions (`languages.python.version`).\n  nixpkgs-python:\n    url:" in text
    assert text.index("rust-overlay:") < text.index("# end of inputs")
    data = parse(text)
    assert data["inputs"]["devenv"] == {"follows": "vendomat/devenv"}
    assert data["inputs"]["mytool"] == {"url": "github:me/tool"}
    assert data["imports"] == ["vendomat/devenv", "./local.nix"]
    assert calls(workspace) == [f"{workspace} update"]


def test_a_second_run_changes_nothing_and_check_passes(workspace: Path):
    runner.invoke(app, ["update", "--root", str(workspace)])
    once = (workspace / "devenv.yaml").read_text()
    again = runner.invoke(app, ["update", "--root", str(workspace)])
    assert again.exit_code == 0
    assert "has every line of the template" in again.stdout
    assert (workspace / "devenv.yaml").read_text() == once
    checked = runner.invoke(app, ["update", "--check", "--root", str(workspace)])
    assert checked.exit_code == 0
    assert len(calls(workspace)) == 2  # devenv update still runs each time


def test_input_names_go_to_devenv_update(workspace: Path):
    runner.invoke(app, ["update", "vendomat", "--root", str(workspace)])
    assert calls(workspace)[-1] == f"{workspace} update vendomat"


def test_the_template_alone_needs_no_change(tmp_path: Path):
    root = tmp_path / "fresh"
    root.mkdir()
    (root / "devenv.yaml").write_text((TEMPLATE / "devenv.yaml").read_text())
    assert update.check_lines(root, TEMPLATE) == []


def test_an_input_that_the_user_defined_differently_stays_theirs(tmp_path: Path):
    (tmp_path / "devenv.yaml").write_text(
        textwrap.dedent(
            """\
            inputs:
              vendomat:
                url: git://elsewhere/vendomat?ref=pinned
              nixpkgs:
                url: github:NixOS/nixpkgs/abc
              devenv:
                url: github:me/devenv
            imports:
              - vendomat/devenv
            """
        )
    )
    missing = {a.name for a in update.check_lines(tmp_path, TEMPLATE)}
    assert missing == {"nixpkgs-python", "rust-overlay"}
    update.run_update(tmp_path, TEMPLATE)
    data = parse((tmp_path / "devenv.yaml").read_text())
    assert data["inputs"]["nixpkgs"] == {"url": "github:NixOS/nixpkgs/abc"}
    assert data["inputs"]["devenv"] == {"url": "github:me/devenv"}


def test_a_file_with_four_space_indentation_gets_lines_in_its_own_indentation(tmp_path: Path):
    (tmp_path / "devenv.yaml").write_text(
        "inputs:\n    vendomat:\n        url: git://server/vendomat?ref=release\nimports:\n    - vendomat/devenv\n"
    )
    update.run_update(tmp_path, TEMPLATE)
    text = (tmp_path / "devenv.yaml").read_text()
    data = parse(text)
    assert set(data["inputs"]) == {"vendomat", "nixpkgs", "devenv", "nixpkgs-python", "rust-overlay"}
    assert "\n    devenv:\n      follows: vendomat/devenv\n" in text
    assert data["inputs"]["rust-overlay"]["inputs"] == {"nixpkgs": {"follows": "nixpkgs"}}


def test_a_missing_import_joins_the_list(tmp_path: Path):
    (tmp_path / "devenv.yaml").write_text(
        "imports:\n  - ./mine.nix\ninputs:\n  vendomat:\n    url: u\n  nixpkgs:\n    follows: vendomat/nixpkgs\n"
        "  devenv:\n    follows: vendomat/devenv\n  nixpkgs-python:\n    url: p\n  rust-overlay:\n    url: r\n"
    )
    added = update.run_update(tmp_path, TEMPLATE)
    assert [(a.kind, a.name) for a in added] == [("import", "vendomat/devenv")]
    assert parse((tmp_path / "devenv.yaml").read_text())["imports"] == ["./mine.nix", "vendomat/devenv"]


def test_a_missing_top_level_key_is_added_whole(tmp_path: Path):
    (tmp_path / "devenv.yaml").write_text("# only a comment\n")
    added = update.run_update(tmp_path, TEMPLATE)
    assert {a.name for a in added} == {"inputs", "imports"}
    assert parse((tmp_path / "devenv.yaml").read_text()) == parse((TEMPLATE / "devenv.yaml").read_text())


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("inputs: {}\nimports:\n  - vendomat/devenv\n", "inputs"),
        ("inputs:\n  vendomat:\n    url: u\nimports: []\n", "imports"),
    ],
)
def test_flow_style_cannot_take_an_edit_and_the_error_names_the_key(tmp_path: Path, text: str, key: str):
    (tmp_path / "devenv.yaml").write_text(text)
    with pytest.raises(update.UpdateError) as caught:
        update.run_update(tmp_path, TEMPLATE)
    assert f"`{key}`" in str(caught.value)
    assert (tmp_path / "devenv.yaml").read_text() == text


def test_an_unreadable_file_names_the_line(tmp_path: Path):
    (tmp_path / "devenv.yaml").write_text("inputs:\n  a: &x 1\n")
    with pytest.raises(update.UpdateError, match=r"devenv\.yaml:2"):
        update.check_lines(tmp_path, TEMPLATE)


def test_no_devenv_yaml_is_a_fault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VENDOMAT_TEMPLATE", str(TEMPLATE))
    result = runner.invoke(app, ["update", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "devenv.yaml" in result.output


def test_a_failed_devenv_update_is_exit_two_after_the_lines_are_written(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("FAKE_EXIT", "5")
    result = runner.invoke(app, ["update", "--root", str(workspace)])
    assert result.exit_code == 2
    assert "devenv update` failed (exit 5)" in result.output
    assert "rust-overlay" in (workspace / "devenv.yaml").read_text()


def test_the_template_is_found_from_the_source_tree(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VENDOMAT_TEMPLATE", raising=False)
    assert update.template_dir().resolve() == TEMPLATE.resolve()

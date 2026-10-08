"""Candidate project-output interface on pinned Nix (V5 fixtures F1 to F7).

These checks use a hand-written candidate ``flake.nix``, not the generator. A pass here
shows only that Nix accepts the bridge and the ``follows`` shape. It does not pass any
generator requirement, a private source host, a cache, or a cold store.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from nixfixture import (
    CANDIDATE_REGISTRY,
    NIXPKGS_URL,
    OUTPUTS_PACKAGES_ONLY,
    OUTPUTS_SELECT_MODULE,
    SYSTEM,
    Result,
    candidate_flake,
    eval_json,
    init_repo,
    lock_root_inputs,
    needs_nix_fixture,
    nix,
    nixpkgs_nodes,
    run,
    save,
    tag_release,
    write,
    write_sources,
)

pytestmark = needs_nix_fixture

EXPECTED_ROOT_INPUTS = {"data", "mod-pkg", "nixpkgs", "plain"}


@pytest.fixture(scope="module")
def seeded(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A Gitman-tracked consumer with the candidate flake and no project-owned outputs file."""
    root = tmp_path_factory.mktemp("consumer-seed")
    write(root / "flake.nix", candidate_flake())
    write(root / "vendomat.toml", CANDIDATE_REGISTRY)
    write_sources(root)
    init_repo(root, "fixture seed without project outputs file")
    return root


@pytest.fixture
def consumer(seeded: Path, tmp_path: Path) -> Path:
    target = tmp_path / "consumer"
    shutil.copytree(seeded, target, symlinks=True)
    return target


def with_project_file(consumer: Path, text: str, lane: str = "project-file") -> None:
    write(consumer / "flake-outputs.nix", text)
    save(consumer, lane, "add project-owned outputs file")


def test_f6_missing_project_file_fails_at_the_named_import(consumer: Path):
    assert nix(["flake", "lock"], consumer).returncode == 0
    result = eval_json(f".#packages.{SYSTEM}", consumer, apply="builtins.attrNames")
    assert result.returncode != 0
    assert "flake-outputs.nix" in result.stderr
    assert "does not exist" in result.stderr


def test_f5_untracked_project_file_is_invisible_until_tracked(consumer: Path):
    write(consumer / "flake-outputs.nix", OUTPUTS_PACKAGES_ONLY)
    untracked = eval_json(f".#packages.{SYSTEM}", consumer, apply="builtins.attrNames")
    assert untracked.returncode != 0
    assert "is not tracked by Git" in untracked.stderr
    assert "flake-outputs.nix" in untracked.stderr

    save(consumer, "project-file", "add project-owned outputs file")
    tracked = eval_json(f".#packages.{SYSTEM}", consumer, apply="builtins.attrNames")
    assert tracked.returncode == 0, tracked.stderr
    assert json.loads(tracked.stdout) == ["data-marker", "default", "plain"]
    assert tracked.warnings == []


def test_f1_bridge_passes_resolved_inputs_to_the_project_file(consumer: Path):
    with_project_file(consumer, OUTPUTS_PACKAGES_ONLY)
    lock = nix(["flake", "lock"], consumer)
    assert lock.returncode == 0, lock.stderr
    assert lock.warnings == []
    assert set(lock_root_inputs(consumer)) == EXPECTED_ROOT_INPUTS
    # Nix adds the new lock file as intent-to-add; record it so the tree reads clean.
    save(consumer, "lock", "record the lock Nix wrote")

    names = eval_json(".#lib.inputNames", consumer)
    assert names.returncode == 0, names.stderr
    assert names.warnings == []
    # The bridge hands over every declared input and `self`, and nothing else.
    assert json.loads(names.stdout) == sorted(EXPECTED_ROOT_INPUTS | {"self"})

    built = nix(["build", "--no-link", "--print-out-paths", f".#packages.{SYSTEM}.default"], consumer)
    assert built.returncode == 0, built.stderr
    assert Path(built.stdout.strip()).read_text() == "mod-pkg-marker\n"

    data = nix(["build", "--no-link", "--print-out-paths", f".#packages.{SYSTEM}.data-marker"], consumer)
    assert data.returncode == 0, data.stderr
    assert Path(data.stdout.strip()).read_text() == "data-marker\n"


def test_f2_no_shell_and_no_implicit_input(consumer: Path):
    with_project_file(consumer, OUTPUTS_PACKAGES_ONLY)
    assert nix(["flake", "lock"], consumer).returncode == 0

    shown = nix(["flake", "show", "--json"], consumer)
    assert shown.returncode == 0, shown.stderr
    assert sorted(json.loads(shown.stdout)) == ["lib", "packages"]

    # Check input names, never the text: the pinned Nixpkgs URL contains "devenv".
    lock = json.loads((consumer / "flake.lock").read_text())
    assert not {"devenv", "vendomat"} & set(lock["nodes"]["root"]["inputs"])
    text = (consumer / "flake.nix").read_text()
    assert "devShells" not in text
    assert "mkShell" not in text
    assert "filterAttrs" not in text


def test_f3_unused_module_face_has_no_effect(consumer: Path):
    with_project_file(consumer, OUTPUTS_PACKAGES_ONLY)
    options = eval_json(".#lib.moduleOptionNames", consumer)
    assert options.returncode == 0, options.stderr
    assert "fixture" not in json.loads(options.stdout)


def test_f4_explicit_module_selection_is_inactive_until_enabled(consumer: Path):
    with_project_file(consumer, OUTPUTS_SELECT_MODULE)
    expected = {
        "disabledEffect": "inactive",
        "enabledEffect": "active",
        "disabledPackages": 0,
        "enabledPackages": 1,
    }
    for name, value in expected.items():
        result = eval_json(f".#lib.{name}", consumer)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == value, name


# --- F7: the proposed [follows] shape ---------------------------------------------------


def _flake(inputs: str) -> str:
    return f"{{\n  inputs = {{\n{inputs}\n  }};\n  outputs = _inputs: {{ }};\n}}\n"


def _np() -> str:
    return f'    nixpkgs.url = "{NIXPKGS_URL}";'


def _lock(root: Path) -> tuple[Result, dict | None]:
    (root / "flake.lock").unlink(missing_ok=True)
    result = nix(["flake", "lock"], root)
    lock_file = root / "flake.lock"
    return result, json.loads(lock_file.read_text()) if lock_file.exists() else None


@pytest.fixture
def children(tmp_path: Path) -> Path:
    write(tmp_path / "c/with-np/flake.nix", _flake(_np()))
    write(tmp_path / "c/without-np/flake.nix", _flake(""))
    write(tmp_path / "c/data/marker.txt", "x\n")
    return tmp_path


BASE_INPUTS = (
    f"{_np()}\n"
    '    with-np.url = "path:./c/with-np";\n'
    '    without-np.url = "path:./c/without-np";\n'
    '    data.url = "path:./c/data";\n'
    "    data.flake = false;"
)


def test_f7_child_that_declares_nixpkgs_shares_one_node(children: Path):
    write(children / "flake.nix", _flake(BASE_INPUTS))
    baseline, lock = _lock(children)
    assert lock is not None
    assert len(nixpkgs_nodes(lock)) == 2  # no follows edge: root and the child each hold a node

    write(children / "flake.nix", _flake(BASE_INPUTS + '\n    with-np.inputs.nixpkgs.follows = "nixpkgs";'))
    result, lock = _lock(children)
    assert result.returncode == 0, result.stderr
    assert result.warnings == []
    assert lock is not None
    assert len(nixpkgs_nodes(lock)) == 1


def test_f7_child_without_nixpkgs_draws_a_nix_warning(children: Path):
    write(children / "flake.nix", _flake(BASE_INPUTS + '\n    without-np.inputs.nixpkgs.follows = "nixpkgs";'))
    result, _ = _lock(children)
    assert result.returncode == 0
    assert result.warnings == ["warning: input 'without-np' has an override for a non-existent input 'nixpkgs'"]


def test_f7_nix_ignores_follows_on_a_non_flake_input_silently(children: Path):
    """Nix gives no warning, so the registry check must reject this case."""
    write(children / "flake.nix", _flake(BASE_INPUTS + '\n    data.inputs.nixpkgs.follows = "nixpkgs";'))
    result, lock = _lock(children)
    assert result.returncode == 0
    assert result.warnings == []
    assert lock is not None
    assert len(nixpkgs_nodes(lock)) == 2


@pytest.mark.parametrize(
    ("label", "inputs"),
    [
        ("missing-root", BASE_INPUTS + '\n    with-np.inputs.nixpkgs.follows = "missing";'),
        (
            "no-root-nixpkgs",
            BASE_INPUTS.replace(_np() + "\n", "") + '\n    with-np.inputs.nixpkgs.follows = "nixpkgs";',
        ),
    ],
)
def test_f7_follows_target_that_does_not_exist_is_a_nix_error(children: Path, label: str, inputs: str):
    write(children / "flake.nix", _flake(inputs))
    result, _ = _lock(children)
    assert result.returncode != 0, label
    assert "follows a non-existent input" in result.stderr


def _chain(root: Path, *, each_follows_parent: bool, direct_edge: bool) -> None:
    b_follow = '\n    b.inputs.nixpkgs.follows = "nixpkgs";' if each_follows_parent else ""
    c_follow = '\n    c.inputs.nixpkgs.follows = "nixpkgs";' if each_follows_parent else ""
    edge = '\n    a.inputs.nixpkgs.follows = "nixpkgs";' if direct_edge else ""
    write(root / "chain/c/flake.nix", _flake(_np()))
    write(root / "chain/b/flake.nix", _flake(f'{_np()}\n    c.url = "path:../c";{c_follow}'))
    write(root / "chain/a/flake.nix", _flake(f'{_np()}\n    b.url = "path:../b";{b_follow}'))
    write(root / "flake.nix", _flake(f'{_np()}\n    a.url = "path:./chain/a";{edge}'))


@pytest.mark.parametrize(
    ("each_follows_parent", "direct_edge", "expected_nodes"),
    [
        (False, False, 4),  # no edge anywhere: root, a, b, c each hold a node
        (False, True, 3),  # consumer edge alone does not reach b or c
        (True, True, 1),  # every authored flake follows its parent
        (True, False, 2),  # links follow, but the consumer edge is missing
    ],
)
def test_f7_three_level_chain_node_counts(
    tmp_path: Path, each_follows_parent: bool, direct_edge: bool, expected_nodes: int
):
    _chain(tmp_path, each_follows_parent=each_follows_parent, direct_edge=direct_edge)
    result, lock = _lock(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.warnings == []
    assert lock is not None
    assert len(nixpkgs_nodes(lock)) == expected_nodes


# --- REG-005 successor evidence: how `ref` and `rev` reach Nix -----------------------------


@pytest.fixture(scope="module")
def tagged_source(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    root = tmp_path_factory.mktemp("tagged-source")
    write(root / "flake.nix", "{ outputs = _: { }; }\n")
    init_repo(root, "tagged source")
    return root, tag_release(root, "1.0.0")


def test_ref_and_rev_are_rejected_as_attributes_and_accepted_as_url_query(
    tagged_source: tuple[Path, str], tmp_path: Path
):
    source, rev = tagged_source
    url = f"git+file://{source}"
    attr_form = f'{{ inputs.src.url = "{url}"; inputs.src.ref = "refs/tags/v1.0.0"; outputs = _: {{ }}; }}\n'
    write(tmp_path / "attr/flake.nix", attr_form)
    rejected = nix(["flake", "lock"], tmp_path / "attr")
    assert rejected.returncode != 0
    assert "unexpected flake input attribute 'ref'" in rejected.stderr

    query = f'{{ inputs.src.url = "{url}?ref=refs/tags/v1.0.0&rev={rev}"; outputs = _: {{ }}; }}\n'
    write(tmp_path / "query/flake.nix", query)
    accepted = nix(["flake", "lock"], tmp_path / "query")
    assert accepted.returncode == 0, accepted.stderr
    locked = json.loads((tmp_path / "query/flake.lock").read_text())["nodes"]["src"]["locked"]
    assert locked["ref"] == "refs/tags/v1.0.0"
    assert locked["rev"] == rev


def test_nix_version_is_the_pinned_one():
    result = run(["nix", "--version"], Path.cwd())
    assert result.stdout.strip() == "nix (Nix) 2.34.7"

"""The Nix YAML parser (`devenv/parse.nix`) on the curated corpus (VMT-010 to VMT-013, VMT-020, VMT-035).

The corpus lives in `tests/fixtures/yaml/`. It holds four groups of hand cases from the project 21
parser spike: `p4` (rejects and grammar edges), `edge` (byte and layout edges), `deep` (nesting), and `rust`
(the cases of the old Rust primop). Each group has an `expected.json` that maps a case name to
`{"ok": TREE}` or `{"err": "vendomat.yaml:LINE:COL: reason"}`. The field `source` says where the expectation
comes from:

- `hand`: the hand-written expectation of the spike (`p4_hand.py`);
- `primop`: the result of the old Rust primop, kept in the spike logs;
- `golden`: the result of this parser, reviewed once.

A `note` marks a case where this parser differs on purpose from the primop: tabs (R9), compact list
maps (R8), a plain value that starts with a dash (R10), and the depth limit (VMT-013).

Cases larger than 16 KB are not files. The tests below generate them with the same shapes.

The structure check needs no Nix. The parser checks need Nix; opt in with `testee verify catalog-eval`.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from nixfixture import needs_nix_fixture, run

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "devenv" / "parse.nix"
CORPUS = ROOT / "tests" / "fixtures" / "yaml"
GROUPS = ("p4", "edge", "deep", "rust")
NAME = "vendomat.yaml"
LIMIT = 64

EVAL = "{ parser, name, f }: (import parser name (builtins.readFile f))"  # the caller appends a selection
# The catalog's call (R51): a key with no value under `machines` is an empty map.
MACHINES = 'p: builtins.length p == 2 && builtins.head p == "machines"'
EVAL_EMPTY_MACHINES = (
    "{ parser, name, f }: (import parser { file = name; emptyMapAt = " + MACHINES + "; } (builtins.readFile f))"
)


def expected(group: str) -> dict[str, dict]:
    return json.loads((CORPUS / group / "expected.json").read_text())


def error_text(stderr: str) -> str:
    """The first line of the message after the last `error:`."""
    tail = stderr.rsplit("error:", 1)[-1]
    return next((line.strip() for line in tail.splitlines() if line.strip()), "NO-ERROR-TEXT: " + stderr[-300:])


def parse_file(path: Path, *, name: str = NAME, select: str = ".value", expr: str = EVAL) -> dict:
    """Parse a file with the parser. Result: {"ok": JSON} or {"err": FIRST_ERROR_LINE}."""
    argv = ["nix-instantiate", "--eval", "--strict", "--json", "--expr", f"{expr}{select}"]
    argv += ["--arg", "parser", str(PARSER), "--argstr", "name", name, "--argstr", "f", str(path)]
    result = run(argv, path.parent)
    if result.returncode == 0:
        return {"ok": json.loads(result.stdout)}
    return {"err": error_text(result.stderr)}


def parse_text(tmp: Path, text: str, **kwargs) -> dict:
    file = tmp / "case.yaml"
    file.write_text(text)
    return parse_file(file, **kwargs)


# --- Structure (no Nix) ---------------------------------------------------------------------------


@pytest.mark.parametrize("group", GROUPS)
def test_every_case_file_has_an_expectation_and_the_other_way_round(group: str):
    files = {p.stem for p in (CORPUS / group).glob("*.yaml")}
    table = expected(group)
    assert files == set(table)
    for case in table.values():
        assert ("ok" in case) != ("err" in case)
        assert case["source"] in {"hand", "primop", "golden"}


def test_the_corpus_holds_the_curated_hand_cases():
    counts = {g: len(expected(g)) for g in GROUPS}
    # 131 p4 + 163 edge + 17 deep + 27 rust = 338 cases. Seventeen larger than 16 KB are generated below.
    assert counts["p4"] == 131 and counts["rust"] == 27
    assert counts["edge"] + 11 == 163 and counts["deep"] + 6 == 17


def test_the_parser_is_plain_nix_over_builtins():
    # VMT-020. The file is the spike parser v3 plus the depth limit and the positions.
    text = PARSER.read_text()
    assert text.startswith("# Strict YAML subset parser in pure Nix (builtins only).")
    assert "maxDepth = 64;" in text
    for banned in ("allow-unsafe-native-code", "builtins.exec", "fromTOML", "getEnv", "--impure", "import <"):
        assert banned not in text


# --- The corpus -----------------------------------------------------------------------------------


@needs_nix_fixture
@pytest.mark.parametrize("group", GROUPS)
def test_the_parser_matches_every_expectation_of_the_group(group: str):
    table = expected(group)
    names = sorted(table)
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda n: parse_file(CORPUS / group / f"{n}.yaml"), names))
    wrong = []
    for name, got in zip(names, results, strict=True):
        want = {k: v for k, v in table[name].items() if k in ("ok", "err")}
        if want != got:
            wrong.append(f"{name}: want {str(want)[:200]} got {str(got)[:200]}")
    assert not wrong, "\n".join(wrong)


def nested_maps(levels: int) -> str:
    """A file that nests maps `levels` deep: the top map is level 1."""
    return "".join("  " * i + f"k{i}:\n" for i in range(levels - 1)) + "  " * (levels - 1) + "leaf: x\n"


def long_cases() -> dict[str, tuple[str, dict]]:
    """The edge cases larger than 16 KB, with the same shapes as the spike (edge_cases.py)."""
    too_deep = {"err": f"{NAME}:65:129: nesting deeper than {LIMIT} levels"}
    return {
        "long_value": ("a: " + "x" * 100000 + "\n", {"ok": {"a": "x" * 100000}}),
        "long_comment": ("a: 1 # " + "x" * 100000 + "\n", {"ok": {"a": "1"}}),
        "long_quoted": ('a: "' + "ab\\n" * 20000 + '"\n', {"ok": {"a": "ab\n" * 20000}}),
        "long_quoted_sq": ("a: '" + "it''s " * 20000 + "'\n", {"ok": {"a": "it's " * 20000}}),
        "long_list": (
            "l:\n" + "".join(f"  - item{i}\n" for i in range(2000)),
            {"ok": {"l": [f"item{i}" for i in range(2000)]}},
        ),
        "long_map": (
            "".join(f"k{i}: v{i}\n" for i in range(2000)),
            {"ok": {f"k{i}": f"v{i}" for i in range(2000)}},
        ),
        # The primop and the old parser read these. The limit rejects them (VMT-013).
        "deep_200": (nested_maps(201), too_deep),
        "deep_500": (nested_maps(501), too_deep),
        "deep_1000": (nested_maps(1001), too_deep),
        # The error that comes first in the file wins: the limit is reached on line 65, before line 201.
        "deep_bad_last_200": (nested_maps(201).replace("leaf: x", "leaf: *x"), too_deep),
        # A bare dash first is not a map: the file must be a map.
        "deep_list_nested_500": (
            "".join("  " * i + "-\n" for i in range(500)) + "  " * 500 + "- x\n",
            {"err": f"{NAME}:1:1: the file must be a map"},
        ),
    }


@needs_nix_fixture
@pytest.mark.parametrize("case", sorted(long_cases()))
def test_the_parser_reads_the_large_edge_cases(tmp_path: Path, case: str):
    text, want = long_cases()[case]
    got = parse_text(tmp_path, text)
    assert got == want


# --- The depth limit (VMT-013) --------------------------------------------------------------------


@needs_nix_fixture
def test_a_file_at_the_limit_parses_and_one_level_more_fails(tmp_path: Path):
    assert "ok" in parse_text(tmp_path, nested_maps(LIMIT))
    # Level 65 starts on line 65. Its indentation is 2 * 64 = 128 spaces, so the column is 129.
    assert parse_text(tmp_path, nested_maps(LIMIT + 1)) == {"err": f"{NAME}:65:129: nesting deeper than {LIMIT} levels"}


@needs_nix_fixture
def test_nested_lists_and_chains_count_their_levels(tmp_path: Path):
    # `l:` then n dashes on one line: the top map is level 1, each dash opens one more list.
    at_limit = "l:\n  " + "- " * (LIMIT - 1) + "x\n"
    over = "l:\n  " + "- " * LIMIT + "x\n"
    assert "ok" in parse_text(tmp_path, at_limit)
    # The 64th dash opens level 65. It sits at column 3 + 2 * 63 = 129 of line 2.
    assert parse_text(tmp_path, over) == {"err": f"{NAME}:2:129: nesting deeper than {LIMIT} levels"}


@needs_nix_fixture
@pytest.mark.parametrize("n", [300, 500, 800, 1000, 1200, 1500])
def test_chains_far_past_the_old_stack_limit_fail_with_the_file_name(tmp_path: Path, n: int):
    # The spike saw `stack overflow; max-call-depth exceeded` between 800 and 1000 levels (no file name).
    m = n // 2
    text = "l:\n" + "".join(" " * (4 * (i + 1)) + "- k:\n" for i in range(m)) + " " * (4 * (m + 1)) + "v: x\n"
    # Level 65 is the map of item 32, on line 33. The key sits after the dash and a space: 128 + 3.
    assert parse_text(tmp_path, text) == {"err": f"{NAME}:33:131: nesting deeper than {LIMIT} levels"}


@needs_nix_fixture
@pytest.mark.parametrize("n", [1000, 3000])
def test_dash_runs_far_past_the_old_stack_limit_fail_with_the_file_name(tmp_path: Path, n: int):
    assert parse_text(tmp_path, "l:\n  " + "- " * n + "x\n") == {
        "err": f"{NAME}:2:129: nesting deeper than {LIMIT} levels"
    }


# --- The caller picks the file name -------------------------------------------------------------


@needs_nix_fixture
def test_the_caller_names_the_file_in_every_error(tmp_path: Path):
    # R38: another module calls the parser for its own file, for example `basix.yaml`.
    assert parse_text(tmp_path, "a: [x]\n", name="basix.yaml") == {"err": "basix.yaml:1:4: flow style is not accepted"}
    assert parse_text(tmp_path, nested_maps(LIMIT + 1), name="basix.yaml")["err"].startswith("basix.yaml:65:129: ")


# --- Positions (VMT-035) ------------------------------------------------------------------------

SAMPLE = """\
# a comment
programs:
  - ripgrep
  - key: z
    other: q
languages:
  python:
    version: "3.12"
"""


@needs_nix_fixture
def test_the_side_table_gives_line_and_column_of_keys_and_values(tmp_path: Path):

    def pos(path: list[str]):
        quoted = " ".join(json.dumps(seg) for seg in path)
        got = parse_file(tmp_path / "case.yaml", select=f".at [ {quoted} ]")
        return {k: v for k, v in got["ok"].items() if k in ("key", "value")} if got["ok"] else None

    (tmp_path / "case.yaml").write_text(SAMPLE)
    # Lines count from 1 and columns count characters from 1.
    assert pos(["programs"]) == {"key": "2:1", "value": "2:1"}  # a block value starts at its key
    assert pos(["programs", "[0]"]) == {"key": "3:3", "value": "3:5"}  # an item: the dash, then its text
    assert pos(["programs", "[1]", "key"]) == {"key": "4:5", "value": "4:10"}  # a compact item map
    assert pos(["programs", "[1]", "other"]) == {"key": "5:5", "value": "5:12"}
    assert pos(["languages", "python", "version"]) == {"key": "8:5", "value": "8:14"}  # the quote starts the value
    assert pos(["languages", "python", "missing"]) is None
    assert pos(["nothing"]) is None


@needs_nix_fixture
def test_a_column_counts_characters_not_bytes(tmp_path: Path):
    (tmp_path / "case.yaml").write_text('"é ü": x\nlast: y\n')
    got = parse_file(tmp_path / "case.yaml", select='.at [ "é ü" ]')
    # The quoted key takes 5 characters (7 bytes), then a colon and a space: the value is at column 8, not 10.
    assert got["ok"]["key"] == "1:1" and got["ok"]["value"] == "1:8"


@needs_nix_fixture
def test_positions_leave_the_value_unchanged(tmp_path: Path):
    # The value is the same tree as the corpus expects, and an empty file has an empty table.
    assert parse_text(tmp_path, "") == {"ok": {}}
    assert parse_text(tmp_path, "", select=".positions") == {"ok": {}}
    assert parse_text(tmp_path, "a: 1\n", select=".positions.a.key") == {"ok": "1:1"}


NO_VALUE = 'no value; write "" for an empty text'


@needs_nix_fixture
def test_a_key_with_no_value_fails_by_default(tmp_path: Path):
    # VMT-012: the plain call keeps the strict grammar, also for a machine entry.
    assert parse_text(tmp_path, "machines:\n  laptop:\n") == {"err": f"vendomat.yaml:2:10: {NO_VALUE}"}


@needs_nix_fixture
def test_the_caller_names_the_paths_where_no_value_is_an_empty_map(tmp_path: Path):
    # R51, VMT-170. `emptyMapAt` makes `machines.NAME` with no value an empty map.
    text = "machines:\n  laptop:\n  box: # all defaults\n  server:\n    serve: false\nenv:\n  A: b\n"
    got = parse_text(tmp_path, text, expr=EVAL_EMPTY_MACHINES)
    assert got == {"ok": {"machines": {"laptop": {}, "box": {}, "server": {"serve": "false"}}, "env": {"A": "b"}}}
    # An empty map has its value position at its key, like any map.
    pos = parse_text(tmp_path, text, expr=EVAL_EMPTY_MACHINES, select='.at [ "machines" "laptop" ]')
    assert pos == {"ok": {"key": "2:3", "value": "2:3", "sub": {}}}


@pytest.mark.parametrize(
    ("text", "where"),
    [
        ("machines:\n", "1:10"),  # the `machines` key itself
        ("env:\n  A:\n", "2:5"),  # a key outside `machines`
        ("machines:\n  laptop:\n    serve:\n", "3:11"),  # a key inside a machine entry
        ("machines:\n  -\n", "2:3"),  # a list item never takes the exception
    ],
    ids=["machines", "env", "machine-key", "list-item"],
)
@needs_nix_fixture
def test_no_value_still_fails_outside_a_machine_entry(tmp_path: Path, text: str, where: str):
    assert parse_text(tmp_path, text, expr=EVAL_EMPTY_MACHINES) == {"err": f"vendomat.yaml:{where}: {NO_VALUE}"}


def test_error_text_helper_reads_the_line_after_the_last_error():
    assert error_text("warning: x\nerror: vendomat.yaml:1:1: boom\n") == "vendomat.yaml:1:1: boom"
    several = "error:\n       vendomat.yaml:3:5: bad\n       vendomat.yaml:4:5: worse\n"
    assert error_text(several) == "vendomat.yaml:3:5: bad"
    assert re.match(r"^NO-ERROR-TEXT", error_text(""))

"""The generation record: its line format and the choice of a rollback target (R43, `VMT-098`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vendomat.record import Entry, RecordError, choose, now, parse_line, read_entries

TOP_A, TOP_B, TOP_C = "/nix/store/aaa-system", "/nix/store/bbb-system", "/nix/store/ccc-system"


def entry(generation: int, top: str, commit: str = "c" * 40, dirty: bool = False) -> Entry:
    return Entry(generation, top, commit, dirty, "2026-10-14T12:00:00Z")


def test_a_line_holds_the_five_keys_of_r43():
    line = entry(3, TOP_A, "a" * 40).line()
    assert "\n" not in line
    assert json.loads(line) == {
        "generation": 3,
        "toplevel": TOP_A,
        "commit": "a" * 40,
        "dirty": False,
        "time": "2026-10-14T12:00:00Z",
    }


def test_a_line_reads_back_to_the_same_entry():
    original = entry(7, TOP_B, "b" * 40, dirty=True)
    assert parse_line(original.line()) == original


def test_the_time_is_utc_to_the_second():
    stamp = now()
    assert len(stamp) == 20 and stamp.endswith("Z") and stamp[10] == "T"


@pytest.mark.parametrize(
    "text, message",
    [
        ("not json", "not JSON"),
        ("[1]", "not a JSON object"),
        ('{"generation": "1", "toplevel": "t", "commit": "c", "dirty": false, "time": "x"}', "'generation'"),
        ('{"generation": true, "toplevel": "t", "commit": "c", "dirty": false, "time": "x"}', "'generation'"),
        ('{"generation": 1, "toplevel": "", "commit": "c", "dirty": false, "time": "x"}', "'toplevel'"),
        ('{"generation": 1, "toplevel": "t", "commit": 5, "dirty": false, "time": "x"}', "'commit'"),
        ('{"generation": 1, "toplevel": "t", "commit": "c", "dirty": "no", "time": "x"}', "'dirty'"),
        ('{"generation": 1, "toplevel": "t", "commit": "c", "dirty": false}', "'time'"),
    ],
)
def test_a_bad_line_is_a_fault(text: str, message: str):
    with pytest.raises(RecordError, match=message) as info:
        parse_line(text)
    assert info.value.code == 2


def test_a_missing_file_is_an_empty_record(tmp_path: Path):
    assert read_entries(tmp_path / "none.jsonl") == []


def test_the_reader_skips_blank_lines_and_names_the_bad_line(tmp_path: Path):
    path = tmp_path / "generations.jsonl"
    path.write_text(entry(1, TOP_A).line() + "\n\n" + entry(2, TOP_B).line() + "\n")
    assert [e.generation for e in read_entries(path)] == [1, 2]
    path.write_text(entry(1, TOP_A).line() + "\n{bad\n")
    with pytest.raises(RecordError, match=r"generations.jsonl:2: not JSON"):
        read_entries(path)


def test_the_default_target_is_the_newest_entry_with_another_system_path():
    entries = [entry(1, TOP_A), entry(2, TOP_B), entry(3, TOP_B)]
    chosen = choose(entries, TOP_B)
    assert chosen.entry.generation == 1 and chosen.skipped_dirty == []


def test_the_default_target_skips_dirty_entries_and_reports_them():
    entries = [entry(1, TOP_A), entry(2, TOP_C, dirty=True), entry(3, TOP_B)]
    chosen = choose(entries, TOP_B)
    assert chosen.entry.generation == 1
    assert [e.generation for e in chosen.skipped_dirty] == [2]


def test_the_default_target_needs_a_clean_earlier_entry():
    with pytest.raises(RecordError, match="every earlier entry was applied with uncommitted changes"):
        choose([entry(1, TOP_C, dirty=True), entry(2, TOP_B)], TOP_B)
    with pytest.raises(RecordError, match="no earlier entry"):
        choose([entry(1, TOP_B), entry(2, TOP_B)], TOP_B)
    with pytest.raises(RecordError, match="no earlier entry"):
        choose([], TOP_B)


def test_a_generation_is_chosen_by_number_and_the_last_line_wins():
    entries = [entry(1, TOP_A, "1" * 40), entry(2, TOP_B), entry(1, TOP_A, "9" * 40)]
    assert choose(entries, TOP_B, generation=1).entry.commit == "9" * 40


def test_a_dirty_generation_is_refused_by_number():
    with pytest.raises(RecordError, match="uncommitted changes"):
        choose([entry(1, TOP_A, dirty=True), entry(2, TOP_B)], TOP_B, generation=1)


def test_an_unknown_generation_and_the_running_system_are_refused():
    with pytest.raises(RecordError, match="no entry for generation 9"):
        choose([entry(1, TOP_A)], TOP_B, generation=9)
    with pytest.raises(RecordError, match="running system"):
        choose([entry(1, TOP_A)], TOP_A, generation=1)


def test_a_commit_is_chosen_by_its_newest_clean_entry():
    entries = [entry(1, TOP_A, "a" * 40), entry(2, TOP_C, "a" * 40, dirty=True), entry(3, TOP_B, "b" * 40)]
    assert choose(entries, TOP_B, commit="a" * 40).entry.generation == 1
    with pytest.raises(RecordError, match="no clean entry for commit"):
        choose(entries, TOP_B, commit="d" * 40)

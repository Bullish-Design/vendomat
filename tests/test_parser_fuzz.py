"""The Nix YAML parser (`devenv/parse.nix`) on the large generated corpora of the project 21 parser spike.

The curated corpus in `tests/fixtures/yaml/` holds the hand cases. This module checks the generated corpora, which
are too large for the repository: about 38 000 files. The generators live in `tests/tools/yamlgen_*.py`. They are
deterministic: each corpus has a fixed seed, and the files are byte for byte the files of the spike
(`tests/fixtures/yaml/corpus-digests.json`). Each test writes its corpora to a temporary directory and deletes
them at the end. The temporary directory comes from `VENDOMAT_PARSER_FUZZ_TMP` (default: the system default).

The check is opt in. Run `testee verify parser-fuzz`.

The oracle for each corpus. The spike compared the parser with the old Rust primop (`vendomatFromYAML`) and with
PyYAML (BaseLoader). This module has neither tool. It uses the expected result that the generator produces, or
else properties and a digest.

- `p2` (3200 documents, seed 20261101): the tree of the generator, `pNNNN.tree.json`. The spike agreed with
  PyYAML on every one.
- `p2n` (1500 documents, seed 20261103): the tree of the generator. Lists in lists, and maps in nested lists.
- `p2tab` (400 documents, seed 20261102): the tree of the generator. Tabs inside plain values, which PyYAML rejects.
- `p2-valid` and `p2n-valid` (9416 and 6200 files, seeds 20261201 and 20261202): a tab variant has the tree of its
  source document. Tabs in the indentation (R9), also in the tab form of a compact item (R8).
- `p2-invalid` and `p2n-invalid` (4552 and 3482 files, same seeds): one indentation fault per file. The error must
  name the position that the generator computed. A document without a tab must say "unexpected indentation".
- `fuzz` and `fuzz3` (2500 files each, seeds 20261012 and 20261014 with `tame`): no expected result. A result is a
  tree or one error line. Properties, a round trip, and a digest check them (see below). The spike compared these
  with the primop.
- `mut1` and `mut2` (4000 and 5000 files, seeds 20261301 and 20261302): the same as `fuzz`. They are mutants of the
  `p2` and `p2n` documents. The spike compared these with PyYAML.

For the corpora without an expected result:

1. Properties. A file gives a tree, or an error line `vendomat.yaml:LINE:COL: reason`. A Nix error with another
   shape (a stack overflow, a `builtins` error, a missing file name) is a failure. The position lies inside the file.
2. Round trip. A tree is written again as YAML in a plain canonical form (every key and value double quoted). The
   parser must give the same tree back. This checks that the parser reads its own result consistently.
3. Digest. The results of a corpus are reduced to a count of trees, a count of errors, and a sha256 over all
   results. `tests/fixtures/yaml/fuzz-golden.json` holds them. A parser change that changes a result changes the
   digest. The change needs a review. Then update the file.

The one-time comparison of the digest with the spike (old primop and parser v3) is in
`.scratch/projects/24-vendomat-catalog-and-machines/evidence/S3-CATALOG.md`.

The differences from the old primop and PyYAML are on purpose:

- R9: a tab may indent a block. The primop rejected tabs.
- R8: a list item may start a map or a list on its own row (`- key: v`, `- - x`).
- R10: a plain map value that starts with `- ` or equals `-` is an error.
- VMT-013: a file may nest at most 64 levels. No generated document goes that deep.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from nixfixture import needs_nix_fixture
from tools import yamlgen_fuzz, yamlgen_mutants, yamlgen_valid, yamlgen_variants

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "devenv" / "parse.nix"
FIXTURES = ROOT / "tests" / "fixtures" / "yaml"

#: The seeds of the spike corpora, and the number of documents.
SEED_P2, COUNT_P2 = 20261101, 3200
SEED_P2N, COUNT_P2N = 20261103, 1500
SEED_P2TAB, COUNT_P2TAB = 20261102, 400
SEED_V2, SEED_V2N = 20261201, 20261202
SEED_FUZZ, SEED_FUZZ3, COUNT_FUZZ = 20261012, 20261014, 2500
SEED_MUT1, COUNT_MUT1 = 20261301, 4000
SEED_MUT2, COUNT_MUT2 = 20261302, 5000
PREFIX = 100

WORKERS = os.cpu_count() or 4
BATCH = 250
ERROR_LINE = re.compile(r"^\s*(?:error: )?(vendomat\.yaml:(\d+):(\d+): (.+))$", re.MULTILINE)

#: One evaluation for many files. A file that fails to parse gives `failed`; the caller runs it alone.
BATCH_NIX = """\
{ parser, list }:
let
  parse = import parser;
  one = f:
    let
      v = (parse "vendomat.yaml" (builtins.readFile f)).value;
      r = builtins.tryEval (builtins.deepSeq v v);
    in
    if r.success then { ok = r.value; } else { failed = true; };
in
map one (builtins.fromJSON (builtins.readFile list))
"""
SINGLE_NIX = '{ parser, f }: (import parser "vendomat.yaml" (builtins.readFile f)).value\n'

Result = dict[str, Any]


# --- Digests ------------------------------------------------------------------------------------


def corpus_digest(directory: Path, documents: int | None = None) -> tuple[int, str]:
    """The count and the sha256 of the sorted `*.yaml` files. `documents` keeps the first N source documents."""
    h = hashlib.sha256()
    count = 0
    for f in sorted(directory.glob("*.yaml")):
        if documents is not None and int(f.name[1:5]) >= documents:
            continue
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
        count += 1
    return count, h.hexdigest()


def spike_digests() -> dict[str, dict[str, Any]]:
    return json.loads((FIXTURES / "corpus-digests.json").read_text())["digests"]


def golden() -> dict[str, dict[str, Any]]:
    path = FIXTURES / "fuzz-golden.json"
    return json.loads(path.read_text())["results"] if path.exists() else {}


def results_digest(names: list[str], results: list[Result]) -> str:
    h = hashlib.sha256()
    for name, result in zip(names, results, strict=True):
        h.update(json.dumps([name, result], sort_keys=True).encode() + b"\n")
    return h.hexdigest()


# --- Generated corpora --------------------------------------------------------------------------


class Corpora:
    """The corpora of one test run, each generated once under `base`."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.made: dict[str, Path] = {}

    def get(self, name: str) -> Path:
        if name not in self.made:
            self.made[name] = self.make(name)
        return self.made[name]

    def make(self, name: str) -> Path:
        out = self.base / name
        match name:
            case "p2":
                yamlgen_valid.generate(out, COUNT_P2, SEED_P2)
            case "p2n":
                yamlgen_valid.generate(out, COUNT_P2N, SEED_P2N, nest=True)
            case "p2tab":
                yamlgen_valid.generate(out, COUNT_P2TAB, SEED_P2TAB, tabtext=True)
            case "p2-variants":
                yamlgen_variants.generate(self.get("p2"), out, SEED_V2)
            case "p2n-variants":
                yamlgen_variants.generate(self.get("p2n"), out, SEED_V2N)
            case "fuzz":
                yamlgen_fuzz.generate(out, COUNT_FUZZ, SEED_FUZZ)
            case "fuzz3":
                yamlgen_fuzz.generate(out, COUNT_FUZZ, SEED_FUZZ3, tame=True)
            case "mut1":
                yamlgen_mutants.generate(out, COUNT_MUT1, SEED_MUT1, [self.get("p2"), self.get("p2n")])
            case "mut2":
                yamlgen_mutants.generate(out, COUNT_MUT2, SEED_MUT2, [self.get("p2"), self.get("p2n")])
            case _:
                raise KeyError(name)
        return out


@pytest.fixture(scope="module")
def corpora() -> Iterator[Corpora]:
    base = Path(tempfile.mkdtemp(prefix="parser-fuzz-", dir=os.environ.get("VENDOMAT_PARSER_FUZZ_TMP") or None))
    try:
        yield Corpora(base)
    finally:
        if os.environ.get("VENDOMAT_PARSER_FUZZ_KEEP") != "1":
            shutil.rmtree(base, ignore_errors=True)


def log(name: str, record: dict[str, Any]) -> None:
    """Keep a summary of a corpus outside the repository, when `VENDOMAT_PARSER_FUZZ_LOGS` names a directory."""
    directory = os.environ.get("VENDOMAT_PARSER_FUZZ_LOGS")
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        (Path(directory) / f"{name}.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")


# --- Running the parser -------------------------------------------------------------------------


def nix_eval(args: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    argv = ["nix-instantiate", "--eval", "--strict", "--json", *args]
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, errors="replace")


def error_line(stderr: str) -> str:
    found = ERROR_LINE.findall(stderr)
    return found[-1][0] if found else "NO-ERROR-LINE: " + stderr.strip()[-300:]


def parse_one(nix_file: Path, path: Path) -> Result:
    done = nix_eval([str(nix_file), "--arg", "parser", str(PARSER), "--argstr", "f", str(path)])
    if done.returncode == 0:
        return {"ok": json.loads(done.stdout)}
    return {"err": error_line(done.stderr)}


def parse_many(work: Path, paths: list[Path]) -> list[Result]:
    """Parse every file. A batch handles the files that parse; a file that fails runs alone for its message."""
    batch_nix = work / "batch.nix"
    single_nix = work / "single.nix"
    batch_nix.write_text(BATCH_NIX)
    single_nix.write_text(SINGLE_NIX)
    results: list[Result | None] = [None] * len(paths)
    chunks = [range(i, min(i + BATCH, len(paths))) for i in range(0, len(paths), BATCH)]

    def run_chunk(chunk: range) -> list[int]:
        """Fill the results of a chunk. Return the indices that still need a run of their own."""
        listing = work / f"list-{chunk.start}.json"
        listing.write_text(json.dumps([str(paths[i]) for i in chunk]))
        done = nix_eval([str(batch_nix), "--arg", "parser", str(PARSER), "--arg", "list", str(listing)])
        listing.unlink()
        if done.returncode != 0:
            return list(chunk)
        pending = []
        for i, item in zip(chunk, json.loads(done.stdout), strict=True):
            if "ok" in item:
                results[i] = item
            else:
                pending.append(i)
        return pending

    with ThreadPoolExecutor(WORKERS) as pool:
        pending = [i for part in pool.map(run_chunk, chunks) for i in part]
        for i, result in zip(pending, pool.map(lambda i: parse_one(single_nix, paths[i]), pending), strict=True):
            results[i] = result
    return [r if r is not None else {"err": "NO-RESULT"} for r in results]


def yaml_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.yaml"))


# --- The generators reproduce the spike ---------------------------------------------------------


def test_the_generators_reproduce_the_first_documents_of_the_spike_corpora(tmp_path: Path):
    """No Nix. The first 100 documents of each corpus equal the spike files byte for byte."""
    expected = spike_digests()
    yamlgen_valid.generate(tmp_path / "p2", PREFIX, SEED_P2)
    yamlgen_valid.generate(tmp_path / "p2n", PREFIX, SEED_P2N, nest=True)
    yamlgen_valid.generate(tmp_path / "p2tab", PREFIX, SEED_P2TAB, tabtext=True)
    yamlgen_variants.generate(tmp_path / "p2", tmp_path / "p2-v", SEED_V2)
    yamlgen_variants.generate(tmp_path / "p2n", tmp_path / "p2n-v", SEED_V2N)
    yamlgen_fuzz.generate(tmp_path / "fuzz", PREFIX, SEED_FUZZ)
    yamlgen_fuzz.generate(tmp_path / "fuzz3", PREFIX, SEED_FUZZ3, tame=True)
    made = {
        "p2@100": tmp_path / "p2",
        "p2n@100": tmp_path / "p2n",
        "p2tab@100": tmp_path / "p2tab",
        "p2-valid@100": tmp_path / "p2-v" / "valid",
        "p2-invalid@100": tmp_path / "p2-v" / "invalid",
        "p2n-valid@100": tmp_path / "p2n-v" / "valid",
        "p2n-invalid@100": tmp_path / "p2n-v" / "invalid",
        "fuzz@100": tmp_path / "fuzz",
        "fuzz3@100": tmp_path / "fuzz3",
    }
    for key, directory in made.items():
        count, digest = corpus_digest(directory, PREFIX)
        assert (count, digest) == (expected[key]["files"], expected[key]["sha256"]), key


def test_the_generators_are_deterministic(tmp_path: Path):
    for run in ("one", "two"):
        yamlgen_valid.generate(tmp_path / run, 30, 7, nest=True)
        yamlgen_fuzz.generate(tmp_path / f"{run}-fuzz", 30, 7)
    assert corpus_digest(tmp_path / "one") == corpus_digest(tmp_path / "two")
    assert corpus_digest(tmp_path / "one-fuzz") == corpus_digest(tmp_path / "two-fuzz")


# --- Corpora with a tree ------------------------------------------------------------------------


def check_trees(work: Path, key: str, paths: list[Path], trees: list[Any]) -> None:
    started = time.monotonic()
    results = parse_many(work, paths)
    wrong = [
        f"{p.name}: want {json.dumps(t)[:150]} got {json.dumps(r)[:150]}"
        for p, t, r in zip(paths, trees, results, strict=True)
        if r != {"ok": t}
    ]
    log(key, {"files": len(paths), "wrong": len(wrong), "seconds": round(time.monotonic() - started, 1)})
    assert not wrong, f"{len(wrong)} of {len(paths)} wrong:\n" + "\n".join(wrong[:20])


@needs_nix_fixture
@pytest.mark.parametrize("name", ["p2", "p2n", "p2tab"])
def test_the_parser_returns_the_tree_of_the_generator(corpora: Corpora, name: str):
    directory = corpora.get(name)
    count, digest = corpus_digest(directory)
    assert (count, digest) == (spike_digests()[name]["files"], spike_digests()[name]["sha256"])
    paths = yaml_files(directory)
    trees = [json.loads(p.with_suffix(".tree.json").read_text()) for p in paths]
    check_trees(corpora.base, name, paths, trees)


@needs_nix_fixture
@pytest.mark.parametrize(("name", "source"), [("p2-valid", "p2"), ("p2n-valid", "p2n")])
def test_tab_variants_return_the_tree_of_their_source(corpora: Corpora, name: str, source: str):
    """R8 and R9: tabs in the indentation, and the tab form of a compact item, change nothing in the tree."""
    directory = corpora.get(f"{source}-variants") / "valid"
    assert corpus_digest(directory)[1] == spike_digests()[name]["sha256"]
    paths = yaml_files(directory)
    trees = [json.loads((corpora.get(source) / (p.name.split(".")[0] + ".tree.json")).read_text()) for p in paths]
    assert sum("\t" in p.read_text() for p in paths) > len(paths) // 2
    check_trees(corpora.base, name, paths, trees)


@needs_nix_fixture
@pytest.mark.parametrize(("name", "source"), [("p2-invalid", "p2"), ("p2n-invalid", "p2n")])
def test_indentation_faults_fail_at_the_computed_position(corpora: Corpora, name: str, source: str):
    """R9: a fault in mixed indentation names `inconsistent tabs and spaces`, or `unexpected indentation` for spaces."""
    variants = corpora.get(f"{source}-variants")
    assert corpus_digest(variants / "invalid")[1] == spike_digests()[name]["sha256"]
    expect = json.loads((variants / "invalid.json").read_text())
    paths = yaml_files(variants / "invalid")
    results = parse_many(corpora.base, paths)
    wrong = []
    reasons: dict[str, int] = {}
    for path, result in zip(paths, results, strict=True):
        want = expect[path.stem]
        found = ERROR_LINE.fullmatch(result.get("err", ""))
        if not found:
            wrong.append(f"{path.name}: not an error line: {str(result)[:150]}")
            continue
        line, col, reason = int(found.group(2)), int(found.group(3)), found.group(4)
        reasons[reason] = reasons.get(reason, 0) + 1
        want_line, want_col = want["line"], want["col"]
        if (line, col) != (want_line, want_col):
            wrong.append(f"{path.name}: want {want_line}:{want_col} got {line}:{col} {reason}")
        elif reason not in ("inconsistent tabs and spaces", "unexpected indentation"):
            wrong.append(f"{path.name}: reason {reason!r}")
        elif not want["tabs"] and reason != "unexpected indentation":
            wrong.append(f"{path.name}: a document without a tab says {reason!r}")
    log(name, {"files": len(paths), "wrong": len(wrong), "reasons": reasons})
    assert not wrong, f"{len(wrong)} of {len(paths)} wrong:\n" + "\n".join(wrong[:20])


# --- Corpora without a tree ---------------------------------------------------------------------

#: A string that a double-quoted scalar can hold without a special case: no control character but tab and newline,
#: no unusual white space (the parser trims white space with the Rust set, which a quoted value still keeps).
SAFE_CHAR = re.compile(r"[^\x00-\x08\x0b-\x1f\x7f-\x9f\u00a0\u1680\u2000-\u200f\u2028-\u202f\u205f-\u2064\u3000\ufeff]")


def quote(s: str) -> str | None:
    if not all(SAFE_CHAR.fullmatch(c) for c in s):
        return None
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def dump(tree: Any, indent: int = 0) -> str | None:
    """A tree as YAML in the canonical form, or None when the tree needs a case that the form leaves out."""
    pad = " " * indent
    out = []
    items: list[tuple[str | None, Any]] = []
    if isinstance(tree, dict):
        items = [(str(k), v) for k, v in tree.items()]
    else:
        items = [(None, v) for v in tree]
    if not items:
        return None
    for key, value in items:
        if key is None:
            head = pad + "-"
        else:
            quoted_key = quote(key)
            if quoted_key is None:
                return None
            head = f"{pad}{quoted_key}:"
        if isinstance(value, str):
            text = quote(value)
            if text is None:
                return None
            out.append(f"{head} {text}\n")
        else:
            inner = dump(value, indent + 2)
            if inner is None:
                return None
            out.append(head + "\n" + inner)
    return "".join(out)


def check_properties(path: Path, result: Result) -> str | None:
    """None when the result has the right shape, else the reason it does not."""
    if "ok" in result:
        return None if isinstance(result["ok"], dict) else "the tree is not a map"
    found = ERROR_LINE.fullmatch(result["err"])
    if not found:
        return "not an error line: " + result["err"][:200]
    line, col = int(found.group(2)), int(found.group(3))
    rows = path.read_bytes().decode("utf-8", errors="replace").split("\n")
    if not (1 <= line <= len(rows) + 1 and 1 <= col <= max(map(len, rows)) + 2):
        return f"position {line}:{col} lies outside the file ({len(rows)} rows)"
    if "overflow" in found.group(4) or "builtins" in found.group(4):
        return f"internal error: {found.group(4)[:100]}"
    return None


def check_unlabelled(corpora: Corpora, name: str, directory: Path, key: str | None = None) -> None:
    key = key or name
    count, digest = corpus_digest(directory)
    assert (count, digest) == (spike_digests()[name]["files"], spike_digests()[name]["sha256"])
    started = time.monotonic()
    paths = yaml_files(directory)
    results = parse_many(corpora.base, paths)

    bad = [f"{p.name}: {why}" for p, r in zip(paths, results, strict=True) if (why := check_properties(p, r))]
    assert not bad, f"{len(bad)} files break a property:\n" + "\n".join(bad[:20])

    # The round trip: write each tree again in the canonical form and parse it.
    again = corpora.base / f"{name}-again"
    again.mkdir()
    texts = {}
    for p, r in zip(paths, results, strict=True):
        if "ok" in r and (text := dump(r["ok"])) is not None:
            texts[p.name] = (text, r["ok"])
    for fname, (text, _) in texts.items():
        (again / fname).write_text(text, encoding="utf-8")
    again_paths = [again / n for n in texts]
    round_wrong = [
        f"{p.name}: {json.dumps(r)[:150]}"
        for p, r, (_, tree) in zip(again_paths, parse_many(corpora.base, again_paths), texts.values(), strict=True)
        if r != {"ok": tree}
    ]
    assert not round_wrong, f"{len(round_wrong)} trees changed on the round trip:\n" + "\n".join(round_wrong[:20])

    names = [p.name for p in paths]
    summary = {
        "files": len(paths),
        "ok": sum("ok" in r for r in results),
        "err": sum("err" in r for r in results),
        "round_trip": len(texts),
        "sha256": results_digest(names, results),
    }
    log(key, {**summary, "seconds": round(time.monotonic() - started, 1)})
    directory_log = os.environ.get("VENDOMAT_PARSER_FUZZ_LOGS")
    if directory_log:
        (Path(directory_log) / f"{key}.results.json").write_text(json.dumps(dict(zip(names, results, strict=True))))
    want = golden().get(key)
    assert want is not None, f"no golden entry; add to fuzz-golden.json: {json.dumps({key: summary})}"
    got = {k: summary[k] for k in ("files", "ok", "err", "sha256")}
    advice = f"the results changed; review them, then update: {json.dumps({key: summary})}"
    assert got == {k: want[k] for k in got}, advice


@needs_nix_fixture
@pytest.mark.parametrize("name", ["fuzz", "fuzz3", "mut1", "mut2"])
def test_fuzz_corpora_give_a_tree_or_one_error_line(corpora: Corpora, name: str):
    check_unlabelled(corpora, name, corpora.get(name))


# --- The helpers --------------------------------------------------------------------------------


def test_dump_writes_the_canonical_form():
    assert dump({"a": "x y", "l": ["1", {"k": "v"}, ["z"]]}) == (
        '"a": "x y"\n"l":\n  - "1"\n  -\n    "k": "v"\n  -\n    - "z"\n'
    )
    assert dump({"a": {}}) is None
    assert dump({"a": "\u00a0"}) is None
    assert quote('say "hi"\t\\') == r'"say \"hi\"\t\\"'


def test_error_line_reads_the_last_position_line():
    assert error_line("error:\n       vendomat.yaml:3:5: bad\n") == "vendomat.yaml:3:5: bad"
    assert error_line("error: vendomat.yaml:1:1: boom\n") == "vendomat.yaml:1:1: boom"
    assert error_line("error: stack overflow").startswith("NO-ERROR-LINE")


def test_the_golden_file_lists_every_unlabelled_corpus():
    path = FIXTURES / "fuzz-golden.json"
    assert path.exists()
    assert set(golden()) == {"fuzz", "fuzz3", "mut1", "mut2"}

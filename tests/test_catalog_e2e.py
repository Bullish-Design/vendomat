"""The catalog on a real devenv: fixtures F1 to F14 and F4b of the project 21 spike W4, plus the template.

Each fixture builds a workspace on disk and runs the real `devenv` in it. The workspace has the topology of
a Vendomat workspace:

- `vendomat`: a scratch flake with the inputs `nixpkgs` and `devenv`, and the catalog module files in `devenv/`. It
  stands in for the Vendomat flake (decision R41). The workspace `devenv.yaml` is
  the template `templates/workspace/devenv.yaml`. Only the `vendomat` URL changes: a `path:` input replaces
  `git://server/vendomat?ref=release`. So the template lines `nixpkgs: follows: vendomat/nixpkgs` and
  `devenv: follows: vendomat/devenv` run as written.
- `nixpkgs`: the revision of `flake.lock` of this repository (NixOS/nixpkgs e7439b6b14ad, guide Section 2.5). The spike
  W4 used `cachix/devenv-nixpkgs` 256551e4.
- `devenv`: the module-only fork. The default is the input that `flake.lock` pins (the published S1 tag). Set
  `VENDOMAT_E2E_S1_MODULES` to a `src/modules` directory to use a `path:` tree instead.
- the host `devenv` 2.4.0 on `PATH` (or `VENDOMAT_E2E_DEVENV`).

The catalog under test is `devenv/` of this checkout (or `VENDOMAT_E2E_CATALOG`).

The check is opt in. Run `testee verify opt:catalog-e2e`. It needs the network once (nixpkgs, nixpkgs-python,
rust-overlay, and the Rust toolchain of fixture F5) and a warm Nix store. The first run builds nothing large: the
fixtures use `nixpkgs` Python. Fixture F5 downloads one Rust toolchain.

The fixtures keep every command, exit status, and output under `VENDOMAT_E2E_LOGS` (default:
`~/.local/state/vendomat/p24/catalog-e2e/TIME`). A file `trees.txt` there records the tree each fixture used.

Rows of the ledger that these fixtures prove: VMT-020 (parser inside the catalog, F1, F2), VMT-021 (F2), VMT-022
(`test_edit_create_delete_of_vendomat_yaml_show_in_the_next_shell`), VMT-030 to VMT-032 (F3), VMT-036
(`test_the_catalog_costs_only_noise_on_shell_entry`), VMT-041 (F4), VMT-042 (F4b), VMT-043 (the template
shell), VMT-044 (F5), VMT-050 (F6), VMT-054 to VMT-056 and VMT-093 (F11), VMT-057 (F12), VMT-060 to VMT-063 (F9, F10,
F14), VMT-091 (F7, F8).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import tempfile
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from nixfixture import s1_devenv_input
from tools import yamlgen_valid

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace"
FIXTURES = ROOT / "tests" / "fixtures" / "yaml"
HARNESS = ROOT / "tests" / "nix" / "catalog_parsed.nix"

DISKO = "github:nix-community/disko/de5708739256238fb912c62f03988815db89ec9a"
FACTER = "github:nix-community/nixos-facter-modules/139dcef4dfc97009629c445806f197883351ab4a"
#: Extra inputs of the fixtures that evaluate a machine: `machines.nix` of the devenv fork needs both.
MACHINE_INPUTS = f"""\
  disko:
    url: {DISKO}
    inputs:
      nixpkgs:
        follows: nixpkgs
  nixos-facter-modules:
    url: {FACTER}
"""
ANSI = re.compile(r"\x1b\[[0-9;]*m")
FAULT_LINE = re.compile(r"^\s*(?:error: )?(vendomat\.yaml:\d+:\d+: .*)$", re.MULTILINE)

pytestmark = pytest.mark.skipif(
    os.environ.get("VENDOMAT_E2E") != "1",
    reason="real devenv fixtures; set VENDOMAT_E2E=1 to opt in (testee verify opt:catalog-e2e)",
)


# --- The site -----------------------------------------------------------------------------------


@dataclass
class Run:
    argv: list[str]
    returncode: int
    out: str
    err: str

    @property
    def text(self) -> str:
        return self.out + self.err

    @property
    def faults(self) -> list[str]:
        """The `vendomat.yaml:` lines of the error, in the order devenv prints them."""
        return FAULT_LINE.findall(self.text)


@dataclass
class Site:
    base: Path
    devenv: str
    s1: str
    catalog: Path
    nixpkgs: str
    logs: Path
    locks: dict[str, Path] = field(default_factory=dict)
    flake: Path | None = None
    count: int = 0

    # --- Building ---

    def scratch_flake(self) -> Path:
        """A flake that holds the catalog files and exports `nixpkgs` and `devenv` for `follows`."""
        if self.flake is None:
            flake = self.base / "vendomat"
            (flake / "devenv").mkdir(parents=True)
            for f in self.catalog.glob("*.nix"):
                shutil.copy(f, flake / "devenv" / f.name)
            (flake / "flake.nix").write_text(
                "{\n"
                f'  inputs.nixpkgs.url = "github:NixOS/nixpkgs/{self.nixpkgs}";\n'
                f'  inputs.devenv.url = "{self.s1}";\n'
                "  outputs = _: { };\n"
                "}\n"
            )
            self.flake = flake
        return self.flake

    def devenv_yaml(self, *, machines: bool = False) -> str:
        """The template `devenv.yaml`, with the `vendomat` URL pointed at the scratch flake."""
        text = (TEMPLATE / "devenv.yaml").read_text()
        url = "url: git://server/vendomat?ref=release"
        assert text.count(url) == 1
        text = text.replace(url, f"url: path:{self.scratch_flake()}")
        if machines:
            assert text.count("\nimports:") == 1
            text = text.replace("\nimports:", "\n" + MACHINE_INPUTS.rstrip("\n") + "\nimports:")
        return text

    def lock(self, kind: str) -> Path:
        """A lock file for all workspaces of one kind (`plain` or `machines`). It is made once by `devenv update`."""
        if kind not in self.locks:
            ws = self.base / f"lock-{kind}"
            ws.mkdir()
            self.write(ws, kind == "machines")
            result = self.run(ws, "update", timeout=1800)
            assert result.returncode == 0, result.text[-2000:]
            self.locks[kind] = ws / "devenv.lock"
        return self.locks[kind]

    def write(self, ws: Path, machines: bool) -> None:
        for f in TEMPLATE.iterdir():
            shutil.copy(f, ws / f.name)
        (ws / "devenv.yaml").write_text(self.devenv_yaml(machines=machines))

    def workspace(
        self,
        name: str,
        yaml: str | None = "",
        nix: str | None = None,
        files: dict[str, str] | None = None,
        *,
        machines: bool = False,
    ) -> Path:
        """A fresh workspace made from the template. `yaml=None` leaves no `vendomat.yaml`."""
        kind = "machines" if machines else "plain"
        lock = self.lock(kind)
        ws = self.base / name
        ws.mkdir()
        self.write(ws, machines)
        shutil.copy(lock, ws / "devenv.lock")
        if yaml is None:
            (ws / "vendomat.yaml").unlink()
        else:
            (ws / "vendomat.yaml").write_text(yaml)
        if nix is not None:
            (ws / "devenv.nix").write_text(nix)
        for fname, content in (files or {}).items():
            (ws / fname).write_text(content)
        return ws

    # --- Running ---

    def run(
        self, ws: Path, *args: str, timeout: int = 1200, tag: str | None = None, env_extra: dict[str, str] | None = None
    ) -> Run:
        env = {k: v for k, v in os.environ.items() if k not in ("UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV")}
        env["NO_COLOR"] = "1"
        env.update(env_extra or {})
        argv = [self.devenv, *args]
        done = subprocess.run(argv, cwd=ws, capture_output=True, text=True, env=env, timeout=timeout, errors="replace")
        result = Run(argv, done.returncode, ANSI.sub("", done.stdout), ANSI.sub("", done.stderr))
        self.count += 1
        record = f"$ (cd {ws.name} && {' '.join(args)})\n{result.text}rc={result.returncode}\n\n"
        with (self.logs / f"{tag or ws.name}.log").open("a") as log:
            log.write(record)
        return result

    def shell(self, ws: Path, command: str, **kwargs: Any) -> Run:
        return self.run(ws, "shell", "--", "sh", "-c", command, **kwargs)

    def eval(self, ws: Path, *attrs: str) -> dict[str, Any]:
        result = self.run(ws, "eval", *attrs)
        assert result.returncode == 0, result.text[-3000:]
        return json.loads(result.out)


def nixpkgs_rev() -> str:
    lock = json.loads((ROOT / "flake.lock").read_text())
    return lock["nodes"]["nixpkgs"]["locked"]["rev"]


@pytest.fixture(scope="module")
def site() -> Iterator[Site]:
    devenv = os.environ.get("VENDOMAT_E2E_DEVENV") or shutil.which("devenv")
    assert devenv, "no devenv on PATH; set VENDOMAT_E2E_DEVENV"
    s1, s1_label = s1_devenv_input(os.environ.get("VENDOMAT_E2E_S1_MODULES"))
    catalog = Path(os.environ.get("VENDOMAT_E2E_CATALOG") or ROOT / "devenv")
    assert (catalog / "devenv.nix").exists(), catalog
    default_logs = Path.home() / ".local/state/vendomat/p24/catalog-e2e" / time.strftime("%Y%m%dT%H%M%S")
    logs = Path(os.environ.get("VENDOMAT_E2E_LOGS") or default_logs)
    logs.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="catalog-e2e-", dir=os.environ.get("VENDOMAT_E2E_TMP") or None))
    version = subprocess.run([devenv, "--version"], capture_output=True, text=True).stdout.strip()
    (logs / "trees.txt").write_text(
        f"devenv binary: {Path(devenv).resolve()} ({version})\n"
        f"devenv input (S1 tree): {s1_label}\n"
        f"vendomat module (catalog): {catalog.resolve()}\n"
        f"nixpkgs: NixOS/nixpkgs {nixpkgs_rev()}\n"
        f"template: {TEMPLATE}\n"
    )
    try:
        yield Site(base, devenv, s1, catalog, nixpkgs_rev(), logs)
    finally:
        if os.environ.get("VENDOMAT_E2E_KEEP") != "1":
            shutil.rmtree(base, ignore_errors=True)


def has_catalog_file(site: Site, name: str) -> bool:
    return (site.catalog / name).exists()


# --- F1: the parser corpus inside the catalog ---------------------------------------------------


def catalog_parse(site: Site, text: str | bytes, base: Path) -> dict[str, Any]:
    """The tree that the catalog module reads from a `vendomat.yaml`, or `{"err": FAULT_LINE}`."""
    ws = Path(tempfile.mkdtemp(prefix="f1-", dir=base))
    try:
        (ws / "vendomat.yaml").write_bytes(text if isinstance(text, bytes) else text.encode())
        argv = ["nix-instantiate", "--extra-experimental-features", "flakes", "--eval", "--strict", "--json"]
        argv += [str(HARNESS), "--argstr", "dir", str(ws), "--arg", "catalog", str(site.catalog)]
        argv += ["--argstr", "nixpkgs", site.nixpkgs]
        done = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=300)
        if done.returncode == 0:
            return {"ok": json.loads(done.stdout)}
        found = FAULT_LINE.findall(done.stderr)
        return {"err": found[-1] if found else "NO-ERROR-LINE: " + done.stderr[-300:]}
    finally:
        shutil.rmtree(ws)


def test_f1_the_curated_parser_corpus_reads_the_same_inside_the_catalog(site: Site):
    """The 321 hand cases of `tests/fixtures/yaml`: the catalog gives the result that the corpus expects."""
    cases = []
    for group in ("p4", "edge", "deep", "rust"):
        table = json.loads((FIXTURES / group / "expected.json").read_text())
        for name, case in table.items():
            want = {k: v for k, v in case.items() if k in ("ok", "err")}
            cases.append((f"{group}/{name}", (FIXTURES / group / f"{name}.yaml").read_bytes(), want))
    with ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        got = list(pool.map(lambda c: catalog_parse(site, c[1], site.base), cases))
    wrong = [f"{c[0]}: want {str(c[2])[:120]} got {str(g)[:120]}" for c, g in zip(cases, got, strict=True) if c[2] != g]
    assert len(cases) == 321
    assert not wrong, f"{len(wrong)} of {len(cases)}:\n" + "\n".join(wrong[:15])


def test_f1_generated_documents_read_the_same_inside_the_catalog(site: Site):
    """Generated trees (the first 300 `p2`, 150 `p2n`, and 150 `p2tab` documents of the parser-fuzz seeds)."""
    corpora = []
    specs: list[tuple[str, int, int, dict[str, bool]]] = [
        ("p2", 300, 20261101, {}),
        ("p2n", 150, 20261103, {"nest": True}),
        ("p2tab", 150, 20261102, {"tabtext": True}),
    ]
    for name, count, seed, flags in specs:
        out = site.base / f"f1-{name}"
        yamlgen_valid.generate(out, count, seed, **flags)
        for p in sorted(out.glob("*.yaml")):
            corpora.append((f"{name}/{p.stem}", p, json.loads(p.with_suffix(".tree.json").read_text())))
    with ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        got = list(pool.map(lambda c: catalog_parse(site, c[1].read_bytes(), site.base), corpora))
    wrong = [f"{c[0]}: got {str(g)[:150]}" for c, g in zip(corpora, got, strict=True) if g != {"ok": c[2]}]
    assert len(corpora) == 600
    assert not wrong, f"{len(wrong)} of {len(corpora)}:\n" + "\n".join(wrong[:15])


# --- F2: a file enters a shell; VMT-022 ---------------------------------------------------------


def test_f2_no_file_an_empty_file_and_a_one_key_file_enter_a_shell(site: Site):
    ws = site.workspace("f2", None)
    assert site.shell(ws, "echo ok").out.strip().endswith("ok")
    (ws / "vendomat.yaml").write_text("")
    assert site.shell(ws, "echo ok").out.strip().endswith("ok")
    (ws / "vendomat.yaml").write_text("env:\n  A: b\nprograms:\n  - hello\n")
    done = site.shell(ws, "printenv A; hello")
    assert done.returncode == 0, done.text[-1500:]
    assert done.out.strip().splitlines()[-2:] == ["b", "Hello, world!"]


def test_edit_create_delete_of_vendomat_yaml_show_in_the_next_shell(site: Site):
    """VMT-022. One workspace, one change at a time. Each next shell shows it with no other step."""
    ws = site.workspace("f2-sequence", None)

    def value() -> str:
        done = site.shell(ws, 'echo "A=${A-unset}"')
        assert done.returncode == 0, done.text[-1500:]
        return done.out.strip().splitlines()[-1]

    assert value() == "A=unset"  # no file
    (ws / "vendomat.yaml").write_text("")
    assert value() == "A=unset"  # create: empty
    (ws / "vendomat.yaml").write_text("env:\n  A: one\n")
    assert value() == "A=one"  # edit: a key appears
    (ws / "vendomat.yaml").write_text("env:\n  A: two\n")
    assert value() == "A=two"  # edit: the value changes
    (ws / "vendomat.yaml").unlink()
    assert value() == "A=unset"  # delete
    (ws / "vendomat.yaml").write_text("env:\n  A: three\n")
    assert value() == "A=three"  # create again


def test_the_template_files_enter_a_shell(site: Site):
    """The template as shipped (only the `vendomat` URL differs) enters a shell, with and without keys."""
    template_yaml = (TEMPLATE / "vendomat.yaml").read_text()
    ws = site.workspace("template", yaml=template_yaml, nix=(TEMPLATE / "devenv.nix").read_text())
    shipped = (TEMPLATE / "devenv.yaml").read_text().splitlines()
    used = (ws / "devenv.yaml").read_text().splitlines()
    changed = [(a, b) for a, b in zip(shipped, used, strict=True) if a != b]
    assert changed == [("    url: git://server/vendomat?ref=release", f"    url: path:{site.scratch_flake()}")]
    assert (ws / ".gitignore").read_text() == (TEMPLATE / ".gitignore").read_text()
    first = site.shell(ws, "echo ok")
    assert first.returncode == 0, first.text[-2000:]
    # The sample keys of the template, with the programs and env lines turned on.
    text = (TEMPLATE / "vendomat.yaml").read_text().splitlines()
    sample = [line.removeprefix("# ").removeprefix("#") for line in text[text.index("#") + 1 :]]
    keep = [line for line in sample if line.startswith(("programs:", "  - ripgrep", "env:", "  GREETING"))]
    (ws / "vendomat.yaml").write_text("\n".join(keep) + "\n")
    done = site.shell(ws, "echo $GREETING; rg --version | head -1")
    assert done.returncode == 0, done.text[-2000:]
    assert done.out.strip().splitlines()[-2] == "hello"
    assert done.out.strip().splitlines()[-1].startswith("ripgrep ")


# --- VMT-036: the cost of the catalog -----------------------------------------------------------

PROGRAMS_ENV_PYTHON = 'programs:\n  - hello\nenv:\n  A: b\nlanguages:\n  python:\n    enable: "true"\n'


def median_entry_seconds(site: Site, ws: Path, runs: int = 7) -> float:
    site.shell(ws, "true")  # warm the evaluation cache
    times = []
    for _ in range(runs):
        start = time.monotonic()
        assert site.shell(ws, "true").returncode == 0
        times.append(time.monotonic() - start)
    return statistics.median(times)


def test_the_catalog_costs_only_noise_on_shell_entry(site: Site):
    """VMT-036. A warm shell entry with a catalog costs no more than noise over a workspace without the catalog."""
    bare = site.workspace("cost-bare", None)
    (bare / "devenv.yaml").write_text(site.devenv_yaml().split("\nimports:")[0] + "\n")
    with_catalog = site.workspace("cost-catalog", PROGRAMS_ENV_PYTHON)
    t_bare = median_entry_seconds(site, bare)
    t_catalog = median_entry_seconds(site, with_catalog)
    summary = f"warm shell entry, median of 7: bare {t_bare:.2f} s, catalog {t_catalog:.2f} s\n"
    (site.logs / "cost.txt").write_text(summary)
    # W4 measured 1.5 s to 1.9 s for every workspace. Allow 0.5 s or 30 %, whichever is larger.
    assert t_catalog <= t_bare + max(0.5, 0.3 * t_bare), (t_bare, t_catalog)


# --- F3: one error lists every fault ------------------------------------------------------------

F3 = """\
programs:
  - hello
languages:
  python:
    version: "three"
  golang:
    enable: "true"
env:
  BAD:
    - a
"""
F3B = """\
programs:
  - hello
  - no-such-program-xyz
languages:
  python:
    version: "three"
  golang:
    enable: "true"
env:
  GOOD: "1"
  BAD:
    - a
machines:
  Box_1:
    host: ""
"""


EXPECT_F3 = [
    'vendomat.yaml:5:14: languages.python.version must be a version such as "3.12", found "three"',
    "vendomat.yaml:6:3: languages.golang: unknown key (known: javascript, python, rust)",
    'vendomat.yaml:9:3: env.BAD must be text, found a list ["a"]',
]
EXPECT_F3B = [
    'vendomat.yaml:3:5: programs[1]: unknown program "no-such-program-xyz" (nixpkgs has no package with this name)',
    'vendomat.yaml:6:14: languages.python.version must be a version such as "3.12", found "three"',
    "vendomat.yaml:7:3: languages.golang: unknown key (known: javascript, python, rust)",
    'vendomat.yaml:11:3: env.BAD must be text, found a list ["a"]',
    "vendomat.yaml:14:3: machines.Box_1: the name is not a host name (lower case letters, digits, '-')",
    'vendomat.yaml:15:11: machines.Box_1.host must be a host name or address, found ""',
]


def test_f3_three_bad_fields_give_one_error_with_three_lines(site: Site):
    ws = site.workspace("f3", F3)
    done = site.shell(ws, "true")
    assert done.returncode != 0
    assert done.faults == EXPECT_F3, done.text[-2500:]
    # The module system stops every command, not only a shell (VMT-031).
    assert site.run(ws, "eval", "env").returncode != 0


def test_f3b_six_faults_come_in_file_order_with_the_position_first(site: Site):
    ws = site.workspace("f3b", F3B)
    done = site.shell(ws, "true")
    assert done.returncode != 0
    assert done.faults == EXPECT_F3B, done.text[-2500:]
    positions = [tuple(map(int, f.split(":")[1:3])) for f in done.faults]
    assert positions == sorted(positions)


# --- F4 and F4b: Python and pyproject.toml -----------------------------------------------------

PYTHON_ON = 'languages:\n  python:\n    enable: "true"\n'
PYPROJECT = '[project]\nname = "e2e"\nversion = "0.1"\n'


def test_f4_python_turns_uv_sync_on_only_with_a_pyproject(site: Site):
    ws = site.workspace("f4", PYTHON_ON)
    assert site.eval(ws, "languages.python.uv.enable", "languages.python.uv.sync.enable") == {
        "languages.python.uv.enable": True,
        "languages.python.uv.sync.enable": False,
    }
    first = site.shell(ws, "python --version")
    assert first.returncode == 0, first.text[-1500:]
    assert "pyproject" not in first.text.lower()  # no warning without the file (VMT-041)
    assert "Running devenv:python:uv" not in first.text
    (ws / "pyproject.toml").write_text(PYPROJECT)
    assert site.eval(ws, "languages.python.uv.sync.enable") == {"languages.python.uv.sync.enable": True}
    with_file = site.shell(ws, "python --version")
    assert with_file.returncode == 0, with_file.text[-1500:]
    assert "Running devenv:python:uv" in with_file.text
    (ws / "pyproject.toml").unlink()
    assert site.eval(ws, "languages.python.uv.sync.enable") == {"languages.python.uv.sync.enable": False}
    assert "Running devenv:python:uv" not in site.shell(ws, "python --version").text


def test_f4c_control_a_forced_sync_without_a_pyproject_fails_the_task(site: Site):
    ws = site.workspace("f4c", PYTHON_ON, nix="{ ... }: { languages.python.uv.sync.enable = true; }\n")
    done = site.shell(ws, "true")
    assert "No pyproject.toml found" in done.text
    assert "Running devenv:python:uv in" in done.text
    assert "(failed)" in done.text


def uncached_evaluation(run: Run) -> bool:
    """True when the run evaluated the shell instead of reading the evaluation cache."""
    lines = [ln for ln in run.text.splitlines() if ln.startswith("✓ Evaluating shell in")]
    assert lines, run.text[-1500:]
    return not any(ln.endswith("(cached)") for ln in lines)


def test_f4b_the_evaluation_cache_follows_pyproject_toml(site: Site):
    """VMT-042. Six shells: file absent, absent, created, created, deleted, deleted. No stale result."""
    ws = site.workspace("f4b", PYTHON_ON)
    steps: list[tuple[str, bool, bool, bool]] = []  # name, uncached evaluation, uv task ran, sync flag

    def step(name: str) -> None:
        done = site.run(ws, "--verbose", "shell", "--", "true")
        assert done.returncode == 0, done.text[-1500:]
        sync = site.eval(ws, "languages.python.uv.sync.enable")["languages.python.uv.sync.enable"]
        steps.append((name, uncached_evaluation(done), "Running devenv:python:uv in" in done.text, sync))

    step("absent-1")  # the first shell may evaluate
    step("absent-2")
    (ws / "pyproject.toml").write_text(PYPROJECT)
    step("created-1")
    step("created-2")
    (ws / "pyproject.toml").unlink()
    step("deleted-1")
    step("deleted-2")
    (site.logs / "f4b-steps.txt").write_text("\n".join(map(str, steps)) + "\n")
    by_name = {s[0]: s for s in steps}
    assert by_name["absent-2"] == ("absent-2", False, False, False)
    assert by_name["created-1"] == ("created-1", True, True, True)
    assert by_name["created-2"] == ("created-2", False, True, True)
    assert by_name["deleted-1"] == ("deleted-1", True, False, False)
    assert by_name["deleted-2"] == ("deleted-2", False, False, False)


# --- F5: Rust through the template input --------------------------------------------------------


def test_f5_rust_without_a_version_uses_nixpkgs_and_a_version_uses_rust_overlay(site: Site):
    ws = site.workspace("f5", 'languages:\n  rust:\n    enable: "true"\n')
    assert site.eval(ws, "languages.rust.channel", "languages.rust.version") == {
        "languages.rust.channel": "nixpkgs",
        "languages.rust.version": "latest",
    }
    plain = site.shell(ws, "rustc --version")
    assert plain.returncode == 0, plain.text[-1500:]
    assert plain.out.strip().splitlines()[-1].startswith("rustc ")
    (ws / "vendomat.yaml").write_text('languages:\n  rust:\n    version: "1.81.0"\n')
    values = site.eval(ws, "languages.rust.enable", "languages.rust.channel", "languages.rust.version")
    assert values == {
        "languages.rust.enable": True,
        "languages.rust.channel": "stable",
        "languages.rust.version": "1.81.0",
    }
    pinned = site.shell(ws, "rustc --version", timeout=3000)
    assert pinned.returncode == 0, pinned.text[-1500:]
    assert pinned.out.strip().splitlines()[-1].startswith("rustc 1.81.0 ")


# --- F6 to F8: YAML and devenv.nix --------------------------------------------------------------


def test_f6_a_scalar_set_in_both_files_names_both(site: Site):
    ws = site.workspace(
        "f6",
        'languages:\n  python:\n    version: "3.13"\nenv:\n  GREETING: yaml\n',
        nix='{ ... }: {\n  languages.python.version = "3.12";\n}\n',
    )
    done = site.run(ws, "eval", "languages.python.version")
    assert done.returncode != 0
    assert "`languages.python.version' has conflicting definition values" in done.text
    assert "In `vendomat.yaml'" in done.text and f"In `{ws}/devenv.nix'" in done.text
    ws2 = site.workspace("f6-env", "env:\n  GREETING: yaml\n", nix='{ ... }: {\n  env.GREETING = "nix";\n}\n')
    done = site.shell(ws2, "true")
    assert done.returncode != 0
    assert "`env.GREETING' has conflicting definition values" in done.text
    assert "In `vendomat.yaml'" in done.text and f"In `{ws2}/devenv.nix'" in done.text


def test_f7_mkforce_in_devenv_nix_wins(site: Site):
    ws = site.workspace(
        "f7", "env:\n  GREETING: yaml\n", nix='{ lib, ... }: {\n  env.GREETING = lib.mkForce "nix";\n}\n'
    )
    assert site.eval(ws, "env.GREETING") == {"env.GREETING": "nix"}
    done = site.shell(ws, "printenv GREETING")
    assert done.returncode == 0, done.text[-1500:]
    assert done.out.strip().splitlines()[-1] == "nix"


def test_f8_lists_and_maps_merge(site: Site):
    ws = site.workspace(
        "f8",
        "programs:\n  - hello\nenv:\n  FROM_YAML: y\n",
        nix='{ pkgs, ... }: {\n  packages = [ pkgs.jq ];\n  env.FROM_NIX = "n";\n}\n',
    )
    done = site.shell(ws, "hello; jq --version; printenv FROM_YAML FROM_NIX")
    assert done.returncode == 0, done.text[-1500:]
    tail = done.out.strip().splitlines()[-4:]
    assert tail[0] == "Hello, world!" and tail[1].startswith("jq-") and tail[2:] == ["y", "n"]


# --- F9, F10, F13, F14: machines ----------------------------------------------------------------

MACHINE_YAML = 'machines:\n  box:\n    host: "192.0.2.10"\n    virtual: "true"\n'
HOST_NAME = "machines.box._nixosEval.config.networking.hostName"


F9_DEVENV_NIX = """\
{ ... }: {
  imports = [ ./extra.nix ];
  machines.box.nixos = {
    environment.variables.W4_A = "from devenv.nix, attrset";
    system.stateVersion = "26.11";
  };
}
"""
F9_EXTRA_NIX = """\
{ ... }: {
  machines.box.nixos = { pkgs, ... }: {
    environment.variables.W4_B = "from extra.nix, function";
  };
}
"""


def test_f9_machines_nixos_merges_yaml_attribute_sets_and_functions(site: Site):
    ws = site.workspace(
        "f9",
        MACHINE_YAML,
        nix=F9_DEVENV_NIX,
        files={"extra.nix": F9_EXTRA_NIX},
        machines=True,
    )
    values = site.eval(
        ws,
        HOST_NAME,
        "machines.box._nixosEval.config.environment.variables.W4_A",
        "machines.box._nixosEval.config.environment.variables.W4_B",
        "machines.box.target.host",
        "machines.box.hardware.facter",
    )
    assert values == {
        HOST_NAME: "box",
        "machines.box._nixosEval.config.environment.variables.W4_A": "from devenv.nix, attrset",
        "machines.box._nixosEval.config.environment.variables.W4_B": "from extra.nix, function",
        "machines.box.target.host": "192.0.2.10",
        "machines.box.hardware.facter": None,
    }
    assert site.shell(ws, "true").returncode == 0


def test_f10_the_host_name_is_the_machine_name_and_another_value_needs_mkforce(site: Site):
    other = 'machines.box.nixos.networking.hostName = "other";'
    ws = site.workspace("f10", MACHINE_YAML, nix=f"{{ ... }}: {{ {other} }}\n", machines=True)
    done = site.run(ws, "eval", HOST_NAME)
    assert done.returncode != 0
    assert "`networking.hostName' has conflicting definition values" in done.text
    assert "vendomat.yaml" in done.text and "devenv.nix" in done.text
    forced = site.workspace(
        "f10-force",
        MACHINE_YAML,
        nix='{ lib, ... }: { machines.box.nixos.networking.hostName = lib.mkForce "other"; }\n',
        machines=True,
    )
    assert site.eval(forced, HOST_NAME) == {HOST_NAME: "other"}
    plain = site.workspace("f10-plain", MACHINE_YAML, machines=True)
    assert site.eval(plain, HOST_NAME) == {HOST_NAME: "box"}


def test_f14_a_machine_without_virtual_needs_its_hardware_report(site: Site):
    ws = site.workspace("f14", 'machines:\n  box:\n    host: "192.0.2.10"\n', machines=True)
    done = site.run(ws, "eval", HOST_NAME)
    assert done.returncode != 0
    assert ".machines/box/facter.json' does not exist" in done.text
    (ws / "vendomat.yaml").write_text(MACHINE_YAML)
    assert site.eval(ws, HOST_NAME) == {HOST_NAME: "box"}


# --- F13: tabs end to end -----------------------------------------------------------------------

TABBED = """\
programs:
\t- hello
\t- jq
languages:
\tpython:
\t\tenable: "true"
env:
\tTABBED: yes
machines:
\tbox:
\t\thost: "192.0.2.10"
\t\tvirtual: "true"
"""


def test_f13_a_tab_indented_file_enters_a_shell_and_a_mix_fails_with_its_position(site: Site):
    ws = site.workspace("f13", TABBED, machines=True)
    done = site.shell(ws, "hello; printenv TABBED; python --version")
    assert done.returncode == 0, done.text[-1500:]
    lines = done.out.strip().splitlines()
    assert lines[-3:-1] == ["Hello, world!", "yes"] and lines[-1].startswith("Python 3.")
    assert site.eval(ws, HOST_NAME) == {HOST_NAME: "box"}
    (ws / "vendomat.yaml").write_text('env:\n\tA: "1"\n  B: "2"\n')
    done = site.shell(ws, "true")
    assert done.returncode != 0
    assert done.faults == ["vendomat.yaml:3:3: inconsistent tabs and spaces"]


# --- F11 and F12: the hatch line and explain (catalog part 2) -----------------------------------

F11_DEVENV_NIX = """\
{ pkgs, ... }: {
  packages = [ pkgs.jq ];
  env.A = "a";
  env.B = "b";
  services.redis.enable = true;
}
"""


def test_f11_the_advanced_line_counts_the_settings_of_the_hatch_files(site: Site):
    if not has_catalog_file(site, "hatch.nix"):
        pytest.skip("this catalog has no hatch.nix yet (S3 part 2)")
    ws = site.workspace(
        "f11",
        "programs:\n  - hello\n",
        nix=F11_DEVENV_NIX,
        files={"devenv.local.nix": '{ ... }: { env.LOCAL_ONLY = "yes"; }\n'},
    )
    done = site.shell(ws, "printenv LOCAL_ONLY")
    assert done.returncode == 0, done.text[-1500:]
    assert "advanced: devenv.nix sets 4 settings; devenv.local.nix sets 1 setting (this checkout only)" in done.out
    # R45: the variable hides the line. The shell reads it, so the evaluation does not change.
    hidden = site.run(ws, "shell", "--", "true", env_extra={"VENDOMAT_HIDE_ADVANCED": "1"})
    assert hidden.returncode == 0 and "advanced:" not in hidden.text
    (ws / "devenv.local.nix").write_text("{ }\n")
    (ws / "devenv.nix").write_text("{ }\n")
    assert "advanced:" not in site.shell(ws, "true").text


def test_f12_explain_names_the_files_that_set_an_option(site: Site):
    if not has_catalog_file(site, "explain.nix"):
        pytest.skip("this catalog has no explain.nix yet (S3 part 2)")
    ws = site.workspace(
        "f12",
        'env:\n  FROM_YAML: y\n  BOTH: yaml\nmachines:\n  box:\n    host: "192.0.2.10"\n    virtual: "true"\n',
        nix='{ lib, ... }: {\n  env.FROM_NIX = "n";\n  env.BOTH = lib.mkForce "nix";\n}\n',
        machines=True,
    )
    report = site.eval(ws, "vendomat.explain")["vendomat.explain"]
    (site.logs / "f12-explain.json").write_text(json.dumps(report, indent=1))
    yaml = {entry["key"]: entry for entry in report["yaml"]}
    assert (yaml["env.FROM_YAML"]["value"], yaml["env.FROM_YAML"]["files"]) == ("y", ["vendomat.yaml"])
    # `mkForce` in devenv.nix replaces the value of the YAML, so the winning file is devenv.nix.
    assert (yaml["env.BOTH"]["value"], yaml["env.BOTH"]["files"]) == ("nix", ["devenv.nix"])
    assert yaml["machines.box.host"]["option"] == "machines.box.target.host"
    assert (yaml["env.FROM_YAML"]["line"], yaml["env.FROM_YAML"]["column"]) == (2, 3)
    only_nix = {entry["option"]: entry["files"] for entry in report["nix"]}
    assert only_nix == {"env.FROM_NIX": ["devenv.nix"]}

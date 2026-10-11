# Step 11 record: the readers

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`, in two parts.
**Raw reports:** `~/.local/state/devenv-py/step-11/REPORT.md` (syntax reader) and
`~/.local/state/devenv-py/step-11-eval/REPORT.md` (eval reader). Fleet counts:
`~/.local/state/devenv-py/step-11/fleet-counts.txt`.

## Inputs

| Item | Syntax reader | Eval reader |
| --- | --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` | same |
| Commit | `549e25ba517e` (change `pzrpnszz`) on `ce250ec0` | `5684ace508ea` (change `utzzrmnq`) on `7579a9e1` |
| Workspace | `gitman-workspaces/dpy-syntax` | `gitman-workspaces/dpy-evalread` |
| Testee | run `20261011T051218Z-bfc9fa816cb4` PASS; 83 tests in the run, 70 new | run `20261011T052547Z-b66d27705b13` PASS; 33 new tests, 4 marked `nix` |

## Syntax reader

Files: `src/devenv_py/read_syntax.py` (entry `read_syntax(source) -> SyntaxResult`),
`syntax_stats.py` (`python -m devenv_py.syntax_stats` prints counts only),
`grammar/node-schema.json` and `PROVENANCE.md` (tree-sitter-nix v0.3.0 schema, pydantree `c0ccabc`,
sha256 `d34e9bdf...`; the reader checks the hash at load), `tests/test_read_syntax.py`,
`test_read_syntax_nix.py` (marker `nix`), `test_syntax_stats.py`, and five synthetic samples under
`tests/fixtures/syntax/`.

Decisions applied:

1. The reader uses the real node kinds from the prototype report. A test lists the kinds it needs.
2. Root `let`: `let_prefix` holds the header verbatim (`let ... in`, trailing space trimmed). The
   reader also keeps `head_text`. `assemble_module(...)` and `SyntaxResult.assemble(bindings)` emit
   head, prefix, and extra bindings unchanged.
3. `extra_bindings` is a list of `{"$nix": <binding span>}` for `inherit`, `inherit (x)`, dynamic
   names, and collisions. The key `$nix-binding` is gone.
4. A string with `${...}` stays one `$nix`.
5. Priority: `mkDefault` reads as `"default"`, `mkForce` as `"force"`, `mkOverride n v` as the
   integer `n`. `mkOverride 1000` stays 1000. `mkOverride 50` stays 50. Only `lib.`-qualified
   calls are read.
6. A name that the head or a `let` binds is not a package under `with pkgs;`. A `let` that rebinds
   `pkgs`, `lib`, `null`, `true`, or `false` blocks the matching forms.
7. A parse error raises `SyntaxParseError` (a subclass of `SyntaxReadError` and `ValueError`) with
   the byte offset. The message never echoes source.
8. The node module has no `from __future__ import annotations`. A test checks this.
9. Spans use byte offsets only.
10. Rule from the orchestrator, added mid-task: a `$nix` never carries outer parentheses.
    `x = (a b);` reads as `a b`. Tests cover nesting, the root expression, and a read, render with
    `(src)`, read cycle.

Findings:

- A top-level list cannot hold a nested `inherit` or collision in place. The reader makes that whole
  nested set one `$nix` (reason `nested-extra-binding`). The fleet run shows 0 values with this
  reason.
- A `let` followed by a function or a non-attrset body makes the whole post-head expression one
  `$nix`, and `let_prefix` stays empty.
- The prototype name `read_syntax_full` is now `read_syntax`. The tree-only prototype `read_syntax`
  and the shadow read are gone.
- `pydantree-sitter` 0.4.0 works with the prototype code unchanged. The vendored schema loads with
  PyPI `tree_sitter_nix` 0.1.0.
- `ty` types `Grammar.nodes` as `SimpleNamespace | None`. The module annotates `N: Any` and
  `ExprUnion: Any`.
- Environment: the agent's first `uv sync` ran against Vendomat's venv and swapped the editable
  `devenv-py` install. The classifier denied two repair commands. The agent then worked through
  `devenv shell -- ...` in the workspace. See [step-2-3.md](./step-2-3.md).

### Fleet counts

Scope: 60 `devenv.nix` files under `~/Documents/Projects/*/`, excluding `.devenv`,
`gitman-workspaces`, `.archive`, and `.worktrees`, and never `devenv.local.nix`. The 60 include the
`devenv-py` scaffold, which the prototype skipped (it ran on 59). 59 files parse. 1 fails (conflict
markers). 29 have a root `let`.

| Rule | Leaves | Typed | Partial | Nix | Typed ratio |
| --- | --- | --- | --- | --- | --- |
| Before: root `let` is one `$nix` | 424 | 358 | 6 | 60 | 84.4 percent |
| After: `let_prefix` plus body | 1152 | 903 | 118 | 131 | 78.4 percent |

Typed plus partial after: 1021 of 1152 (88.6 percent). The "before" ratio counts 29 whole files as
one leaf each, so it overstates typing. After the change, 264 `$nix` values remain. Interpolation
causes 159 of them (60.2 percent: 104 string, 55 indented). Other reasons: non-`pkgs` select 40,
variable 23, other apply 17, `lib.mkOption` 8, path 7, `++` 4, `lib.mkIf` 3, `+` 2,
`lib.optional` 1. Extra bindings count as `nix` leaves.

Later change (`9a541b4bd8ed`, see [step-15.md](./step-15.md)): a plain relative path literal now
reads as typed `{"$path": ...}`. The fleet ratios were not re-measured.

## Eval reader

File: `src/devenv_py/read_eval.py`; tests: `tests/test_read_eval.py`. API:
`read_eval(truth, subtree, *, model=None, resolver=None, package_sets=None, root=None, pin=None,
pin_dir=None) -> (OptionModel, list[Miss])`.

The reader selects the truth keys equal to the subtree or under it. It nests by `loc`. It loads the
model with `generator.load_module` and `load_narrowed`, and it uses the most derived narrowed class.
On a `ValidationError` it maps each error to its option, drops that option, records a `Miss`, and
retries. `Miss(option, kind, reason, value)` has the kinds `unreadable` (`$error`, `$multi-def`),
`invalid`, `not-in-model`, `package`, `conflict`, and `model`. A `NixExpr` field that gets a
non-source truth value gives a miss that says truth cannot carry source.

### `$pkg` resolution (as built)

1. Candidates per (`pname`, output): the `pname` itself, and `<set>.<pname>` when the subtree hints
   at a language (`languages.python` gives `python3Packages`; table `LANGUAGE_PACKAGE_SETS`).
2. The reader writes one small module per pair into a run directory. It sets `packages` to
   `[ pkgs.<attr>, pkgs.<attr>.<output> ]`. A `tryEval` guard maps a missing attribute, removed
   alias, throw, or non-derivation to null.
3. The existing `truth` request kind serializes the result. All pairs go through one `run_batch`
   call.
4. Match: the truth `pname` equals the candidate `pname`, and either the default output equals the
   truth output (then `PkgRef(attr, output=None)`) or `pkgs.<attr>.<output>` exists (then
   `output=<o>`).
5. Exactly one match gives a `PkgRef`. Zero or several matches give a miss that lists the attributes
   tried.

Truth keeps no `outPath`, so the check uses `pname` and output name only. Cost (observation): one
`devenv eval` start of about 1.0 s plus a small amount per pair. A batch of 30 pairs took 1.4 s.
The resolver is injectable, so unit tests need no Nix.

### Results

- Golden truths read: `a-probe` and `d-priority` give `languages.python {enable: True}` and
  `services.postgres {enable: True}` or `{enable: True, port: 5434}`. Fixtures `b`, `c`, and `e`
  have no option in those subtrees and give empty instances.
- Synthetic invalid truth (port 70000, bool as string, element type error, unknown option, `$error`,
  `$multi-def`, `$fn`) gives misses with reasons. The rest is read.
- Nix tests: `jq/bin` gives `PkgRef(attr="jq", output=None)`; `git/out` gives `git`; `jq/dev` gives
  `jq` with output `dev`; `requests` gives `python3Packages.requests` with the Python hint and a
  miss without it; a missing attribute is a miss and does not spoil the batch.

### Departures and findings

- `PkgRef.output` is `None` when the truth output is the default output of `pkgs.<attr>`.
  `pkgs.jq` and `pkgs.jq.bin` give the same truth, so truth cannot tell them apart.
- The guide says to keep the candidate "whose `outPath` matches". Truth has no `outPath`, so the
  reader matches on `pname` and output.
- A `pname` that differs from the attribute name (`gcc` gives `gcc-wrapper`) is a miss. A package
  index per pin would fix it; it is not built.
- Ambiguity is a miss, even when plain `ruff` and `python3Packages.ruff` both fit.
- Generated model files for `packages`, `env`, and other top-level options do not exist. The golden
  tests that need them use a synthetic `packages` export.
- No `introspect.nix` hook was needed.

These `pname` limits led to the package identity problem. See [step-15.md](./step-15.md), the
section on open items.

## Gate GM7

Met for the code and tests of both readers.

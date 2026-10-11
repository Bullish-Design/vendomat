# Step 4 record: the options export

**Date:** 2026-10-11. **Status:** Observed. Done in `devenv-py`.
**Source quality:** no report file exists for this step (`~/.local/state/devenv-py/step-4/` is
absent). The facts below come from the orchestrator's summary and from the repository source. The
Testee run identifier is not recorded.

## Inputs

| Item | Value |
| --- | --- |
| Pin | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| Commit | `4052991b1b8a`: feat: add the options export, the completeness check, the census, and export-driven merge rules |
| Request | `{"kind": "options", "maxDepth": 8}` |
| Commands | `python -m devenv_py.options export`, `python -m devenv_py.options check`, `python -m devenv_py.options census` |

The guide proposed `dpy export`. The code ships `python -m devenv_py.options` with the
subcommands `export`, `check`, and `census`. Exit codes: 0 ok, 1 findings, 2 the tool could not
run. `dpy` has no `export` subcommand.

## Results (observation)

| Item | Expected | Actual |
| --- | --- | --- |
| Export hash | equals phase A | SHA-256 `a1126c7deb218be41121dc672fdb7b4b0ca58fafc482c787c9fd7ad66a07fc4e`, byte-identical to the phase-A export |
| Records | 1330 | 1330 |
| Records outside any submodule | 845 | 845 |
| `optionsDoc` keys against the doc rule | 1144 keys, 0 differences | 1144 keys, 0 differences |
| `depthCut` nodes | 0 | 0 (the export fails when any node has `depthCut`) |

The export files are `exports/devenv-2.4.0-b904dcb5-c2f38fe7/options.json` (canonical JSON,
833,807 bytes) and the sidecar `options.meta.json`. The sidecar holds the pin, the hash, and the
record counts. The file hash equals the hash in the sidecar. Step 8 committed the files (see
[step-8.md](./step-8.md)).

## Decisions applied

1. The completeness check uses the doc rule from the guide: list an option when `visible` is
   `true` or `"shallow"` and it is not `internal`; walk its sub-options when `visible` is `true` or
   `"transparent"`.
2. The normalizer reads its merge rules from the export (`normalize.default_rules`). The hard-coded
   table of Step 6 stays only as a test oracle. A `nullOr X` option takes the merge rule of `X`.
   Truth files from Step 7 use these rules.
3. The type census counts options per `type.name`, including nested names.

## Inference

- I1. The export is stable over repeated runs, because the hash equals the phase-A hash. The
  four-call stability test of the guide (two uncached, one refreshed, one cached, one from another
  directory) is a phase-A result. This record has no separate run of it.

## Gate GM2

Met, on the evidence above. The record lacks a report file and a Testee run identifier. Treat the
gap as a record defect, not a test failure.

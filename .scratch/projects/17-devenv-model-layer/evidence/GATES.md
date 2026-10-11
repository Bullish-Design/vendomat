# Gate records for project 17 (typed models for devenv modules)

**Updated:** 2026-10-11. **Pin:** `devenv-2.4.0-b904dcb5-c2f38fe7`. **`devenv-py` `main`:**
`0dd939d802d2`. Statuses: PASS, IN PROGRESS, BLOCKED. A gate passes only on recorded evidence. The
concept lists what each gate proves ([CONCEPT.md](../CONCEPT.md), Gates). The guide lists the steps
([GUIDE-HARNESS.md](../GUIDE-HARNESS.md)).

| Gate | Status | Evidence | Open item |
| --- | --- | --- | --- |
| GM0 | PASS at the probe pin | [step-0-probe.md](./step-0-probe.md); [phase-a.md](./phase-a.md), section 7 | The probe commands O1 to O12 were not rerun one by one on `b904dcb5`. Every later step used the same surfaces on that pin and worked. |
| GM1 | PASS | [step-2-3.md](./step-2-3.md); Testee run `20261011T051232Z-101a43914d5c` | None. The timing table is in the record. |
| GM2 | PASS | [step-4.md](./step-4.md); commit `4052991b1b8a` | The record has no report file and no Testee run identifier. |
| GM3 | PASS | [step-5-6.md](./step-5-6.md); Testee run `20261011T051232Z-101a43914d5c` | None. |
| GM4 | PASS | [step-7.md](./step-7.md); Testee run `20261011T130620Z-b33822909882` | None. 0 unstable fixtures. |
| GM5 | PASS | [step-8.md](./step-8.md); Testee run `20261011T051752Z-5a6f9bd2a573` | The 56 records that the field count does not explain. |
| GM6 | PASS for the suite; tag part open | [step-9.md](./step-9.md) and its addendum | No Templateer tag on `main`. The harness pins the revision `ac02b48c015d`. The owner decides the tag. |
| GM7 | PASS | [step-10.md](./step-10.md) (run `20261011T121708Z-3fd530e67e44`); [step-11.md](./step-11.md) (runs `20261011T051218Z-bfc9fa816cb4`, `20261011T052547Z-b66d27705b13`) | The eval reader resolves a package by `pname`. See GM9. |
| GM8 | PASS | [step-12-14.md](./step-12-14.md); Testee run `20261011T125749Z-5cc9d147cc4f`; strict RT5 run `20261011T131425Z-638700540816` | None. |
| GM9 | IN PROGRESS | [step-15.md](./step-15.md); pilot report `~/.local/state/devenv-py/rt/20261011T140324Z-rt-pilot/report.md` (gate FAIL, before the widening) | See below. |
| GM10 | IN PROGRESS | [step-16.md](./step-16.md) | The skills exist. The `services.redis` trial has not finished. |

## GM9 detail

The last complete pilot report is FAIL. The widening in `0dd939d802d2` fixed three RT1 misses and
the generated cases (RT7 and RT8 pass for both subtrees on seeds 1 and 2; see
[step-15.md](./step-15.md)). The gate stays open for these reasons.

1. Package identity breaks RT2 and RT6 for three `languages.python` fixtures, RT1 for
   `python-uv-sync`, and RT4 for `postgres-timescale`. In progress.
2. `postgres-customdbuser` fails RT4 on the `$path` `.` against `./.`. Not examined.
3. `services.postgres` has 3 of 10 fixtures excluded as `has-fn` (30 percent; the limit is 20).
4. `services.postgres` has a typed ratio of 86.8 percent (the limit is 90) at the last measure.
5. The run time needs a warm cache. Case directories carry the run id today. In progress.
6. The final gate run (`testee check rt-pilot`) has not run after these fixes.

Items 3 and 4 were measured before the latest changes. Nobody has re-measured them.

## What is in progress (no result claimed)

- Package identity by the full `$name` with attribute resolution (RT2, RT6).
- RT7 forcing of the `config.packages` names and of `enterShell`.
- Content-addressed case directories.
- The final GM9 gate run, then the GM10 skills trial on `services.redis`.

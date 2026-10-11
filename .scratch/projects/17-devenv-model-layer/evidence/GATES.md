# Gate records for project 17 (typed models for devenv modules)

**Updated:** 2026-10-11 (final record). **Pin:** `devenv-2.4.0-b904dcb5-c2f38fe7`.
**`devenv-py` `main`:** `4f3033bdaa9c`. Statuses: PASS, IN PROGRESS, BLOCKED. A gate passes only on
recorded evidence. The concept lists what each gate proves ([CONCEPT.md](../CONCEPT.md), Gates). The guide lists the steps
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
| GM7 | PASS | [step-10.md](./step-10.md) (run `20261011T121708Z-3fd530e67e44`); [step-11.md](./step-11.md) (runs `20261011T051218Z-bfc9fa816cb4`, `20261011T052547Z-b66d27705b13`) | The `pname` limit is gone: package identity uses the full `$name` (`4af72fe743ba`, MDL-036). See GM9. |
| GM8 | PASS | [step-12-14.md](./step-12-14.md); Testee run `20261011T125749Z-5cc9d147cc4f`; strict RT5 run `20261011T131425Z-638700540816` | None. |
| GM9 | PASS | [step-15-final.md](./step-15-final.md); report `~/.local/state/devenv-py/rt/regate-1/report.md` (four subtrees, gate PASS, cold 103.4 s); run `regate-2` (warm, 13.2 s, same 4780 result rows); report `~/.local/state/devenv-py/rt/rust-rebased-1/report.md` (`languages.rust`, gate PASS) | The `testee check rt-pilot` check covers the two pilot subtrees only. See the open items below. |
| GM10 | PASS | [step-16-final.md](./step-16-final.md); `languages.javascript` trial record `~/.local/state/devenv-py/devenv-py-author/languages.javascript/js-final.md`; commit `4a3e45feef51` (no harness file); Testee run `20261011T190830Z-9dc98b5f2868` | One fresh-agent pass on one subtree. The trials on `services.redis` and `languages.rust` came before it. |

## GM9 detail

**The supported set** (run `regate-1` and run `rust-rebased-1`, seeds 1 and 2; RT7 cases are the sum
of both seeds):

| Subtree | Status | Real fixtures | RT7 | RT8 |
| --- | --- | --- | --- | --- |
| `languages.python` | supported | 24 | 1099 pass, 0 fail | 95 of 95 |
| `services.postgres` | supported | 10 | 1103 pass, 0 fail | 32 of 32 |
| `services.redis` | supported (generated-only) | 1 | 1059 pass, 0 fail | 11 of 11 |
| `languages.javascript` | supported | 7 | 1061 pass, 0 fail | 38 of 38 |
| `languages.rust` | supported | 10 | 1109 pass, 0 fail | 47 of 47 |

The rules behind the table are MDL-030 (two tiers) and MDL-031 (path-limit exceptions). RT6 skips
`has-fn` for three `services.postgres` fixtures and `pkg-unresolved` for two `languages.python` and
three `languages.rust` fixtures. They are path-limit exceptions: the report lists them and the share
does not count them. The record lists every skip.

**The six open items of the 2026-10-11 draft of this file, and their result.**

1. Package identity: fixed (`4af72fe743ba`, MDL-036). One fixture, `python-with-packages`, stays
   `pkg-unresolved` for RT1 (1 of 24, 4 percent).
2. `postgres-customdbuser` RT4: fixed (`canonical_path`, `./.` is `.`). RT4 is 11 of 11.
3. `services.postgres` `has-fn` share: now a path-limit exception. The counted share is 0 of 10.
4. `services.postgres` typed ratio: 32 of 35 (91.4 percent; the limit is 90).
5. Run time: content-addressed case directories (MDL-037). Cold 103.4 s, warm 13.2 s.
6. The final gate run: done (`regate-1`, `regate-2`, `rust-rebased-1`).

**Open items after GM9 (named, not gate blockers).**

1. Templateer `main` has no release tag. The harness pins `ac02b48c015d`. The owner decides the tag.
   This is also the open part of GM6.
2. The `pytest-focus` targets file lives in XDG state and is shared by every checkout.
3. The end-to-end check default `VENDOMAT_TEMPLATEER` is specific to one machine.
4. The Devman push hook resolves `testee` from the session `PATH`. A session that started from an old
   Vendomat shell carries Testee 0.5.1 and gives wrong verdicts.
5. `testee check rt-pilot` runs `languages.python` and `services.postgres` only. The other three
   subtrees have a gate run (`regate-1`, `rust-rebased-1`) and no Testee check.
6. The report has no row for "every enum value and both integer bounds occur" (author skill step 9).
   An author computes it by hand.

## Earlier state (superseded)

The draft of this file at `0dd939d802d2` listed GM9 and GM10 as IN PROGRESS, with six open items
and a trial on `services.redis` that had not finished. The text above replaces it. The history is in
[step-15.md](./step-15.md) and [step-16.md](./step-16.md).

# Issue: Vendomat CI gate fails on a tag pin mismatch

**Status:** Open. One CI test fails.

**Disposition:** No waiver for landing was granted. This report records the
captured result. It does not mean the gate passed. Do not rerun Testee in Phase A.

## Summary

The Testee CI gate failed on 2026-09-29. Ruff, Ruff format, and ty passed.
Pytest failed one test. The test found a mismatch between a locked revision and
the revision for its tag. The cause is not established.

This test protects the pin invariant that Phase D must preserve when it bumps
flake inputs.

## Run record

| Field | Value |
|---|---|
| Gate | devenv shell testee verify --mode ci |
| Gitman timeout | 1,800 seconds |
| Testee run | 2026-09-29T14-32-47Z-909072 |
| Result | Failed; pytest exit code 1 |
| Duration | 35,954 ms |
| Checks | ruff, ruff-format, and ty passed; pytest failed one test |
| Testee mode | CI |

The report is in the ignored local run directory:

    .testee/runs/2026-09-29T14-32-47Z-909072/testee-report.json

## Observed failure

The failing test is
tests/test_fleet_shape.py::test_every_first_party_input_is_pinned_to_a_tag
at tests/test_fleet_shape.py:58.

The lock revision is 4870686dbddf26653d9e9db13bc1babcf73271a6. The tag revision
is a35859e4d32964ce6cf2c05a4093e0b5b2e67c17. They differ. The report shows
the failed assertion, but it does not establish why the pin and tag disagree.

## Reproduction

No reproduction run was made in Phase A. Do not rerun Testee.

## Resolution

Do not claim this gate is green. Any waiver or landing decision requires the
user's approval. Establish the cause before changing the pin check or release
logic.

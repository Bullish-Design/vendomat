# Vendomat contract verification investigation — 2026-10-14

## Question

Do the `vendomat apply` configuration-commit and rollback contracts pass their planned VM fixture,
including VR3 policy, and are failures caused by the product behavior or the VM test harness?

## Inputs and method

The machine fixture ran on source trees that Testee recorded for each run (`source_tree_start` in
`run.json`; the table names them). The earlier text of this record gave these inputs for the VM runs: Nix 2.34.7,
devenv 2.4.0, QEMU 11.1.1, module input revision `061c2184cfcc2e84d2013b5f5a0b57b003ccc7a9`, and
Nixpkgs revision `e7439b6b14ad3cc35d05608ebca9bce01a25f5f8`. The exact reproducible gate command was
`testee verify opt:machines-vm`, run from the Vendomat workspace root. VM disk, state, scratch, and
serial logs were kept under `/mnt/shared/vendomat-p21/` and
`~/.local/state/vendomat/p21/`.

The passing `opt:machines-vm` run ran on tree `af4016c8`. The other `opt:` runs of this change
(`opt:sharing-vm`, `opt:catalog-eval`, `opt:catalog-devenv`, `opt:catalog-e2e`, and
`opt:front-door-e2e`) ran on tree `25bd25c7`, which the earlier text of this record named as the
snapshot of all runs. That was wrong for the machine runs.

## Observations and fixes

Each count is the number of the 12 test cases that failed or passed, as pytest printed it.

| Run | Tree | Result | Failure classification and repair |
| --- | --- | --- | --- |
| `20261015T004333Z-1fdf9f4a2076` | `0c07163b` | 11 of 12 failed | Harness status parsing used `.strip()`, which removed meaningful leading porcelain status spaces. Preserve the prefix and trim only trailing whitespace. |
| `20261015T004959Z-a561708a5360` | `91517caa` | 8 of 12 failed | Harness expected status did not account for the trusted `.machines/` path. Corrected the trust-key and status expectations. |
| `20261015T005326Z-dd535d97fed0` | `79bf052d` | 6 of 12 failed | Harness cleanup used `git rm notes.txt` and deleted unrelated staged work. Adjusted cleanup to preserve the unrelated staged file. |
| `20261015T005825Z-c324aa10b6ec` | `9714fe60` | 6 of 12 failed | Harness cleanup assertion still modeled the staged-file state incorrectly. Corrected the status assertion against the retained staged change. |
| `20261015T010228Z-3f4b60c85684` | `cc2741e3` | 1 of 12 failed | The ignored-config refusal case expected a clean status even though unrelated `A  notes.txt` was intentionally staged. Updated the expected result to preserve that change. |
| `20261015T010946Z-a99af20c00cc` | `af4016c8` | 12 of 12 passed | Fresh complete rerun after the harness fixes. No test cases were skipped. |

The failing attempts were classified as fixture defects from the observed status/cleanup mismatches;
they did not establish a product defect. The final independent VM observations include successful
clean apply and lasting rollback, ignored-config refusal without machine change, dirty apply recorded
as dirty, dirty generation skipped on rollback, fast and exact rollback paths, and a boot-only
rollback. The final run also preserved unrelated staged work. Exact evidence is in
`/home/andrew/.local/state/vendomat/p21/2026-10-15/s4/machines-vm/run-010947Z/results.log` and
`commands.log`; serial output is in the adjacent `serial.log`.

## Conclusion and limits

The final VM fixture proves the R49 behavior on the tested disposable NixOS machine. The earlier
red attempts remain part of the record; only the fresh 12/12 rerun is a pass. This does not prove a
host activation, real hardware, S7, or physical-disk behavior. The R49 owner ruling is recorded in
`DECISIONS.md` and its contract result in [VR-CONTRACT-RESOLUTIONS-2026-10-14](VR-CONTRACT-RESOLUTIONS-2026-10-14.md).

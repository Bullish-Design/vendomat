# V6 gate records

**Updated:** 2026-10-09. Each gate is `PASS`, `FAIL`, `BLOCKED`, or `OPEN` (not yet run). `OPEN`
is a work state, not a result. A document, a unit test, a synthetic policy result, or a project 15
VM is not new V6 runtime proof. Raw logs sit under `~/.local/state/vendomat/v6/2026-10-09/<step>/`.

| Gate | Step | Status | Evidence | Note |
| --- | --- | --- | --- | --- |
| G0 | Authority ledger | PASS | [LEDGER-V6.md](../LEDGER-V6.md), [step-0.md](step-0.md) | Ledger check passes in `testee verify --full` (run 20261009T235155Z-480906abf076); log `00-ledger/testee-full-step0.log`. The external proof inventory is in step-0.md |
| G1 | Pinned devenv distribution | OPEN | | Lane running |
| G2 | `vendomat sync` for devenv workspaces | PASS | [step-2.md](step-2.md) | Stock devenv 2.4.0. The patched CLI is G1. Offline shell entry is G1 |
| G3 | Vendomat module and library faces | OPEN | | |
| G4 | Command and launcher | OPEN | | |
| G5 | Source, cache, builder | OPEN | | PV-09 may stay a named blocker |
| G6 | `nix-systems` bootable core | OPEN | | |
| G7 | Fresh server disk route in VMs | OPEN | | |
| G8 | Legacy dependency removal | OPEN | | |
| G9 | Cutover review package | OPEN | | Read-only facts and NOT RUN commands only |

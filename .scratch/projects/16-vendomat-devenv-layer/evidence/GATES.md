# V6 gate records

**Updated:** 2026-10-09. Each gate is `PASS`, `FAIL`, `BLOCKED`, or `OPEN` (not yet run). `OPEN`
is a work state, not a result. A document, a unit test, a synthetic policy result, or a project 15
VM is not new V6 runtime proof. Raw logs sit under `~/.local/state/vendomat/v6/2026-10-09/<step>/`.

| Gate | Step | Status | Evidence | Note |
| --- | --- | --- | --- | --- |
| G0 | Authority ledger | PASS | [LEDGER-V6.md](../LEDGER-V6.md), [step-0.md](step-0.md) | Ledger check passes in `testee verify --full` (run 20261009T235155Z-480906abf076); log `00-ledger/testee-full-step0.log`. The external proof inventory is in step-0.md |
| G1 | Pinned devenv distribution | BLOCKED | [01-devenv-distribution.md](01-devenv-distribution.md) | Every item passes except the build on `server`, the Attic push, and the cold substitution (`DVN-006`), and the kexec phase |
| G2 | `vendomat sync` for devenv workspaces | PASS | [step-2.md](step-2.md) | Stock devenv 2.4.0. The patched CLI is G1. Offline shell entry is G1 |
| G3 | Vendomat module and library faces | PASS | [step-3.md](step-3.md) | Mode metadata for the patched CLI waits for G1 |
| G4 | Command and launcher | BLOCKED | [step-4.md](step-4.md) | Every item passes except the real Attic push, which G5 owns. The gate stays BLOCKED until G5 |
| G5 | Source, cache, builder | BLOCKED | [step-5.md](step-5.md) | VM fixtures PASS: collection, `STORE-010`, cache push, cold substitution, builder, both substitution directions. BLOCKED: PV-09 (owner decision), the live Attic push (not permitted in this session), and the opt-in e2e wrapper (disk) |
| G6 | `nix-systems` bootable core | PASS | [step-6.md](step-6.md) | Core, Machines flow, library face, Home Manager role, and the framework denial pass in QEMU. The tests use a minimal delta, so the real services need their own VM checks (G8) |
| G7 | Fresh server disk route in VMs | BLOCKED | [step-7.md](step-7.md) | The refusal matrix ran (a to n, direct CLI) and found defects D1 to D5, W1 to W3, G1, C1, C2. Fixes are in `main` except C1 and C2 (fork `.2`). The success path, the boot of the new disk alone, and the firmware test are not run |
| G8 | Legacy dependency removal | BLOCKED | [step-8.md](step-8.md), [step-8a.md](step-8a.md), [step-8-services.md](step-8-services.md) | Closure, tool flakes, and the role-services VM (8 checks) PASS. BLOCKED: the V4 removal in repositories that hold open work, and `agentman` (deferred) |
| G9 | Cutover review package | OPEN | | Read-only facts and NOT RUN commands only |

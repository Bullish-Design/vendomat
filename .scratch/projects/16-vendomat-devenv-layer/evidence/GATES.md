# V6 gate records

**Updated:** 2026-10-10. Each gate is `PASS`, `FAIL`, `BLOCKED`, or `OPEN` (not yet run). `OPEN`
is a work state, not a result. A document, a unit test, a synthetic policy result, or a project 15
VM is not new V6 runtime proof. Raw logs sit under `~/.local/state/vendomat/v6/2026-10-09/<step>/`.

| Gate | Step | Status | Evidence | Note |
| --- | --- | --- | --- | --- |
| G0 | Authority ledger | PASS | [LEDGER-V6.md](../LEDGER-V6.md), [step-0.md](step-0.md) | Ledger check passes in `testee verify --full` (run 20261009T235155Z-480906abf076); log `00-ledger/testee-full-step0.log`. The external proof inventory is in step-0.md |
| G1 | Pinned devenv distribution | BLOCKED | [01-devenv-distribution.md](01-devenv-distribution.md) | Fork `v2.4.0-vendomat.2` (commit `e2acb5b0`). Every item passes except `DVN-006` (the fork build in the live Attic and a cold dry run) and the `kexec` phase, which the server route does not use |
| G2 | `vendomat sync` for devenv workspaces | PASS | [step-2.md](step-2.md) | Stock devenv 2.4.0. The patched CLI is G1. Offline shell entry is G1 |
| G3 | Vendomat module and library faces | PASS | [step-3.md](step-3.md) | Mode metadata for the patched CLI waits for G1 |
| G4 | Command and launcher | PASS | [step-4.md](step-4.md), [step-5.md](step-5.md) | Launcher, `path`, `check`, `push`, `bump`, `machine install` pass. The push shape (`attic push <cache> --stdin`) ran against a real `atticd` in a VM (`testee check e2e` run `20261010T125007Z-a0ca995fce8e`). The owner's live Attic was not pushed to (not permitted in this session) |
| G5 | Source, cache, builder | BLOCKED | [step-5.md](step-5.md) | Collection, `STORE-010`, cache push, cold substitution, builder, and both substitution directions PASS in VMs and in the green e2e. BLOCKED only on PV-09 (the installer's pull credential: an owner decision) |
| G6 | `nix-systems` bootable core | PASS | [step-6.md](step-6.md) | Core, Machines flow, library face, Home Manager role, and the framework denial pass in QEMU. The tests use a minimal delta, so the real services need their own VM checks (G8) |
| G7 | Fresh server disk route in VMs | PASS | [step-7.md](step-7.md) | In QEMU: 25 of 25 injection cases and 10 of 10 direct-CLI cases refuse with no write; the install succeeds; the old disk, ESP hashes and firmware entries equal the baseline; the new disk boots alone; BootNext boots it once and the next reboot returns the old system. One failed unit (`tailscaled-autoconnect`, no age key in the VM) is explained in N1. The real firmware and the real drive are not proven: G9 |
| G8 | Legacy dependency removal | BLOCKED | [step-8.md](step-8.md), [step-8a.md](step-8a.md), [step-8-services.md](step-8-services.md) | Closure, tool flakes, and the role-services VM (8 checks) PASS. BLOCKED: the V4 removal in repositories that hold open work, and `agentman` (deferred) |
| G9 | Cutover review package | BLOCKED | [CUTOVER-REVIEW.md](../CUTOVER-REVIEW.md) | The package is drafted. BLOCKED: the privileged scan (PV-02) and the `nixos-facter` report need root; the success path of G7 has not run; the owner has not reviewed |

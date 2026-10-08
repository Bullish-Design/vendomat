# V5 preliminary verification

**State:** verification complete on 2026-10-08. V5 implementation is **not ready**. No
implementation step has run. The detailed row-by-row result is in [RESULTS.md](RESULTS.md).

This directory records the checks that ran before implementation. It does not amend the authority
by itself. Current design authority remains:

1. [`../CONCEPT-V5.md`](../CONCEPT-V5.md) — design and examples.
2. [`../SPEC-V5.md`](../SPEC-V5.md) — normative requirements and Verify commands.
3. [`../GUIDE-V5.md`](../GUIDE-V5.md) — proposed steps, blocked at Step 0 and private-cache installer access.
4. [`../REFINEMENT-2026-10-08.md`](../REFINEMENT-2026-10-08.md) — drive identity and storage plan.
5. [`../../CURRENT.md`](../../CURRENT.md) — active state and blockers.
6. [`../KICKOFF-V5.md`](../KICKOFF-V5.md) — implementation status and conditions before work starts.

## Readiness

PV-02 blocks Step 0 because the physical target's partition-table and signature state is unknown.
PV-09 blocks a fresh installer because the private cache route, trust key, pull credential, and
source are unavailable before first boot. Source generation and several integration contracts also
need tracked fixtures. Do not treat a passing disposable fixture as a passed implementation
requirement.

The evidence supports a remote source URL as the fleet default, explicit local Nix input overrides,
a one-node `nixpkgs` goal only for controlled graphs, native option-type merging, optional module faces, a Gitman commit between `diff` and
`apply`, and a Nix-only machine core without the CLI. These interfaces remain proposed until the
tracked implementation fixtures pass.

**Update 2026-10-08:** the `--impure` shell is no longer a Vendomat contract. Vendomat generates no
shell (see [DECISIONS.md](DECISIONS.md)). PV-13 and PV-14 pass the project-output interface and the
generator in isolation. PV-15 records that no private source host exists.

## Evidence locations

Keep raw command output outside the repository under
`~/.local/state/vendomat/v5/prelim-verification/<date>/`. Each result links the exact raw logs and
states any missing command transcript. Do not put credentials or tokens in this directory.

Use Gitman for version control. Use Testee for repository verification. Keep every requirement ID;
add a fresh ID when a claim changes.

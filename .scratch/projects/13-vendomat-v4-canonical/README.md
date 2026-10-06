# Vendomat V4 — canonical contract

**Date:** 2026-10-06. **Status:** Canonical. This directory supersedes the project-09 and
project-10 V4 documents as the V4 contract.

The owner accepted the [project-12 independent review](../12-vendomat-v4-independent-review/REVIEW.md)
in full on 2026-10-06. These documents apply its recommendations.

## Read in this order

1. [CONCEPT-V4.md](./CONCEPT-V4.md) — owner goals and the system boundary. One page.
2. [V4-SPEC.md](./V4-SPEC.md) — the **only** normative contract. Every rule appears here once.
3. [V4-REQUIREMENTS.md](./V4-REQUIREMENTS.md) — 60 active requirement IDs and the full ID history.

## Supporting records

| File | Role |
| --- | --- |
| [NATIVE-BASELINE.md](./NATIVE-BASELINE.md) | 24 upstream facts the design assumes. Observed once on the pin. No gate. |
| [LATER-APPLICATION.md](./LATER-APPLICATION.md) | The Jujutsu–btrfs–bubblewrap case and `V4-APP-001`–`031`. Outside V4. |
| [FUTURE-WORK.md](./FUTURE-WORK.md) | Reviewed upgrades, release helpers, and three deferred capabilities, each with its trigger. |
| [PUB-FORM-SPIKE.md](./PUB-FORM-SPIKE.md) | Throwaway spike on the flake output form for publishable selections (`V4-SEL-010`). Observations only. No gate. |
| [docs/V4_PIN_RECORD.md](../../../docs/V4_PIN_RECORD.md) | Pin record: tool versions, hosts, state classes, cache policy, and named blockers per phase. Incomplete by design. No gate. |

## History, retained unchanged

| File | Role |
| --- | --- |
| [project-10 adversarial review](../10-vendomat-v4-adversarial-review/V4-REVIEW.md) | The 13 findings that shaped the contract. |
| [project-10 requirement audit](../10-vendomat-v4-adversarial-review/V4-REQUIREMENT-AUDIT.md) | One disposition for each of the 172 baseline IDs. |
| [project-11 simplification review](../11-vendomat-v4-simplification-review/REVIEW.md) | First simplification pass. |
| [project-12 independent review](../12-vendomat-v4-independent-review/REVIEW.md) | The accepted recommendations and their evidence. |
| [docs/V4_P0_PROOF.md](../../../docs/V4_P0_PROOF.md) | Observed host and tool evidence from 2026-10-06. Its gate framing is superseded by the pin record; its observations remain valid. |

The project-09 and project-10 concept, specification, and requirements files do not define V4. Do
not follow them for V4 work.

## Repository files aligned to this contract

| File | State |
| --- | --- |
| [docs/V4_IMPLEMENTATION_GUIDE.md](../../../docs/V4_IMPLEMENTATION_GUIDE.md) | Rebuilt 2026-10-06. A pin record plus P1–P7, with 4 common steps and 29 phase steps. No P0 and no combined preflight gate. P8–P10 are gone as phases. |
| [AGENTS.md](../../../AGENTS.md) | Updated 2026-10-06. Its authority list and gate order point here. Pre-V4 consumer migration is a separate project that starts after P6 passes. |

No V4 phase has passed. Do not claim a gate.

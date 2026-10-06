# Vendomat V4 simplification review

**Date:** 2026-10-06. **Status:** Proposal for owner review. No V4 document or product code changed for this review.

## Decision in brief

Keep the first Neovim application proof and the separate machine proof. Make the [specification](../10-vendomat-v4-adversarial-review/V4-SPEC.md) the one normative contract. Keep the [concept](../10-vendomat-v4-adversarial-review/CONCEPT-V4.md) for goals, the [requirements](../10-vendomat-v4-adversarial-review/V4-REQUIREMENTS.md) for stable IDs, and the [guide](../../../docs/V4_IMPLEMENTATION_GUIDE.md) for fixtures. Each fact should have one full explanation.

The largest change is to separate the application preflight from machine and consumer cutover. The current P0 gate requires a remote Machines plan and consumer transitions. Those operations serve P7 and release cutover. They do not establish the P1–P6 application proof. Keep the current P0 gate blocked until the owner approves a revised gate. Do not start P1 under the current contract.

## Inventory

The counts use the repository files as read on 2026-10-06. A requirement ID stays in the historical record when its active gate ends.

| Document | Lines now | Proposed line budget | Role after edit |
| --- | ---: | ---: | --- |
| [Concept](../10-vendomat-v4-adversarial-review/CONCEPT-V4.md) | 1,031 | 220 | Owner goals and system boundary. |
| [Specification](../10-vendomat-v4-adversarial-review/V4-SPEC.md) | 330 | 230 | One normative V4 contract. |
| [Requirements](../10-vendomat-v4-adversarial-review/V4-REQUIREMENTS.md) | 331 | 200 | Active ID ledger and compact ID history. |
| [Implementation guide](../../../docs/V4_IMPLEMENTATION_GUIDE.md) | 383 | 230 | Ordered fixtures and gates. |
| **Active contract total** | **2,075** | **880** | **Budget: 1,195 fewer lines.** |
| [Adversarial review](../10-vendomat-v4-adversarial-review/V4-REVIEW.md) | 163 | 163 | Historical review; retain. |
| [Requirement audit](../10-vendomat-v4-adversarial-review/V4-REQUIREMENT-AUDIT.md) | 260 | 260 | Historical audit; retain. |
| [P0 evidence](../../../docs/V4_P0_PROOF.md) | 226 | 226 | Observed record; retain and append new evidence later. |

The line budgets are edit targets, not measured results. Moving the later application into its own note adds a separate document. It does not add to the core V4 contract.

| Requirement group | IDs now | Proposed active core IDs | Disposition |
| --- | ---: | ---: | --- |
| OWN | 13 | 9 | Merge repeated ownership rules. |
| MOD | 14 | 12 | Use native module failures. |
| SEL | 9 | 7 | Keep frozen selection and byte identity. |
| CHK | 16 | 11 | Keep required check outcomes; merge duplicate set rules. |
| SRC | 25 | 13 | Keep selected source and provenance; drop the initial graph policy. |
| CACHE | 15 | 13 | Keep closure, Attic only use, and NAR comparison. |
| EVD | 11 | 8 | Keep a small receipt and log links. |
| REC | 13 | 5 | Keep first proof restore and state separation. |
| MACH | 15 | 10 | Keep native plan, activation, and recovery limits. |
| PROOF | 9 | 0 | Put the seven live scenarios in guide gates; two IDs are already retired. |
| UPG and OPT | 13 | 0 | Move to a short future work note. |
| APP | 31 | 0 | Move to a separate later module note. |
| **Total** | **184** | **88** | **96 IDs leave the active core ledger.** |

Of the 96, 44 move to later work (31 APP and 13 UPG/OPT). Nine PROOF IDs become guide scenarios. The other 43 merge, retire, or move to a future feature. Preserve all 184 old strings in the ID history. Never reuse an ID. The 172 baseline IDs and 12 added IDs remain traceable through the old audit.

The guide names P0–P10. P9 and P10 share one section. It has 63 numbered steps: five common steps, 55 phase steps, and three release steps. The proposed guide has P0–P7 and about 36 numbered steps. P8–P10 become future work triggers, so three phase labels leave the execution sequence. Keep each P0–P7 gate distinct. Check, Attic use, restore, and machine activation have different native owners.

The contract records nine `D-*` decisions. It names three proposed `review.*` options, two proposed review target options, and six proposed later application names or settings. It fixes no new Vendomat command spelling. Native commands such as `devenv machines plan`, Nix queries, and `attic push` are not Vendomat interfaces. The first fixture needs zero fixed new option or command names.

The receipt description lists selection identity, lock identity, output and closure paths, NAR hashes, checks and inputs, source coverage, Attic target, upload result, verification time, and an optional machine plan ID. The report also lists seven claims: retained source, correspondence, archive backed rebuild, check pass, cache availability, acceptance, and activation. P4 names three check outcomes: failed required, missing required, and a documented nonrequired gap. A build failure is a separate native failure.

## Ranked findings

Savings below are estimates for the four active contract documents. They overlap. Do not add them to derive the 1,195 line budget. Risk means the risk of the proposed cut to the first workflow or Neovim proof. Each change needs owner approval because the prior decisions are open in this review.

| Rank and area | Location | Why it is too large; native owner | Proposed simplification | IDs and cost | Risk |
| --- | --- | --- | --- | --- | --- |
| **1. Repeated contract text** | Concept §§2–3, 8–25; Spec §§1–8, 10; Requirements traceability and decision tables; guide P0–P10 | Four documents state the same selection, check, source, and phase rules. The audit repeats many ID reasons. Native tools still own execution. | Put normative behavior in the spec once. Let the concept state goals. Let each ID row point to the rule and one observable check. Let guide steps cite IDs. Keep the old review and audit as history. | About 600–800 lines. No behavior loss. All 184 IDs stay traceable. | Low. Cross links must stay valid. |
| **2. P0 mixes the application with machine cutover** | [Guide P0](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L42), [P7](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L280), [cutover](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L311); Concept §§10, 21–22 | A remote NixOS plan and 21 overlay transitions are real work, but they serve machine readiness and release cutover. [Machines](https://devenv.sh/machines/) already owns plan and apply. P1–P6 need a tested local composition pin and application hosts. | Make P0 an application preflight. Move the remote Machines pin and plan to P7 entry. Move active consumer transition tests to cutover. Preserve each old path until its before and after fixture passes. | Move `V4-MACH-001` and `V4-OWN-012` gates; keep IDs. About two P0 steps move. No phase gate is lost. | Medium. A first proof on an isolated consumer cannot claim fleet cutover. |
| **3. Later application inside V4** | [Spec §9](../10-vendomat-v4-adversarial-review/V4-SPEC.md#L228), [APP table](../10-vendomat-v4-adversarial-review/V4-REQUIREMENTS.md#L219), Concept §§22–23, guide P9–P10 | The Jujutsu, btrfs, and bubblewrap module has its own admission, image, runtime, and state design. Native Jujutsu, btrfs, bubblewrap, Nix, and systemd own those operations. No observed first proof failure forces its design now. | Move the case and `V4-APP-001–031` to one later module note. Leave one sentence in the core boundary. Keep original IDs and a move map. | 31 IDs and about 120–170 core lines. | Low for V4; later module needs its own review. |
| **4. Two capture graphs and automatic source policy** | Concept §§11–12, Spec §5, [guide P3](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L135), SRC table | The first proof needs one owned module and one selected third party source. The current policy adds a maintained list, two graph resolvers, stale entry reports, and broad discovery. Nix locks and source paths already identify selected inputs. Nix output closures do not map all package paths to source. | Capture the owned module and one named selected native input for the first proof. Retain a Git object, archive, or rooted Nix source path with one manifest. Add package dependency mapping only after a real inspection need and a native mapping fixture. | `V4-SRC-001`, `019–023` leave P3; `003` becomes one explicit source. About 70–110 lines and three P3 steps. | Medium. The first proof no longer claims both direct graphs. |
| **5. P8–P10 form an unneeded sequence** | Concept §§16–18, 22; Spec §8 and §10; [guide P8–P10](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L326) | A native update command, isolated checkout, task, and timer can serve these needs. No two consumer failures yet require a Vendomat proposal or release engine. | Replace P8–P10 with a short trigger note. Keep native reviewed changes as a normal workflow. Open a new design when repeated use proves a helper is needed. | `V4-UPG-001–009`, `V4-OPT-001–004` move to future work. Three phase labels and eight guide steps leave the sequence. About 90–130 lines. | Low for the first proof. Upgrade automation remains undefined. |
| **6. Extra proof IDs and repeated checks** | [Requirements CHK, EVD, PROOF](../10-vendomat-v4-adversarial-review/V4-REQUIREMENTS.md#L52), guide P1–P6 | PROOF scenarios restate feature IDs. CHK rows split one required set into owner, consumer, union, provenance, and missing declaration tests. [devenv tasks](https://devenv.sh/tasks/) already supplies order and check exit status. | Keep the union of declared module and consumer checks. Keep failed required, missing declared required, and documented nonrequired gap distinct. Use guide scenarios for combined proof. Do not infer undeclared tests. | Merge `V4-CHK-005`, `008–009`, `015–016`, `V4-EVD-004`, and `V4-PROOF-001–009`. Keep `CHK-010–014` as applicable. About 60–90 lines. | Medium. A missing check must mean a declared check that cannot run. |
| **7. Receipt and claim matrix** | Concept §§14–15, Spec §§4, 6, 8; guide P4–P6 | One report appears to own current source, cache, acceptance, and activation facts. Native locks, Nix, Attic, and Machines already own current facts. A large receipt becomes stale. | Store one immutable run manifest: frozen input digest, output path and NAR hash, required check IDs and log links, upload result, closure verification artifact, and time. Query current availability from Attic. Link source and machine evidence only when those fixtures exist. | Merge `V4-SEL-004`, `008`, `V4-EVD-008`, `010`, `V4-REC-010–011`, `V4-MACH-004`, `015`. About 40–70 lines. | Medium. Keep enough inputs to explain a failed or successful check later. |
| **8. Recovery and machine status matrix** | Concept §§10, 19; Spec §7; [guide P6–P7](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L244) | P7 repeats P6 source and cache status after machine failures. Machines and Home Manager already report their activation results. P6 already proves source and evidence restore. | Keep P6 source, output rebuild, and evidence restore. Make P7 one native plan/apply fixture with a service health result and one user activation failure. Report native system and user results, plus application data observation. Do not repeat P6 domains in P7. | Merge `V4-REC-003–004`, `008`, `013`, `V4-MACH-007`, `010`, `013`. About 45–75 lines and four guide steps. | Medium. Driver specific user recovery still needs a real fixture. |
| **9. Storage report as first proof gate** | Concept §§19, 25; Spec §10 `P-STORAGE`; [guide P6 step 5](../../../docs/V4_IMPLEMENTATION_GUIDE.md#L266) | Nix can report closure size and filesystem tools can report source bytes. Neither number proves the first command, source lookup, check, or cold consumer. | Record native measurements as optional evidence. Require them only before broader retention or machine generation caching. | Move `V4-REC-006` and `P-STORAGE` from P6. One guide step and about 10–20 lines. | Low. Capacity planning moves later. |
| **10. Names before fixtures** | Spec §3 examples and §9 case; Concept §25 | Eleven illustrative option names compete with the rule that names remain unproved. devenv and Nix already supply real import and output forms. | Use one schematic first consumer example or a fixture link. Fix a V4 name only after its pinned fixture passes. | `D-NAMES` remains. About 30–50 lines. Zero fixed new names before P1. | Low. Readers get less copyable syntax until proof. |

### Need, native form, and evidence

| Area | Concrete owner need | Plain native form | Failure basis |
| --- | --- | --- | --- |
| Document overlap | Find one rule and one test for it. | One spec rule and one ID link. | Observed repeated text and 2,075 active contract lines. |
| P0 gate | Finish the application proof without claiming machine readiness. | Local devenv fixture now; Machines plan at P7. | P0 records a failed remote plan and unfinished consumer transition. |
| Later application | Run several pinned revisions with isolated state. | A separate module using Jujutsu, btrfs, bubblewrap, Nix, and systemd. | No later application fixture or first proof failure exists. |
| Source capture | Read the selected source later with honest provenance. | Native lock and source path plus retained bytes and one manifest. | Source mapping across both graphs remains an unrun P3 experiment. |
| Later phases | Review updates or automate repeated tasks when useful. | Native update, isolated checkout, task, and timer. | No repeated consumer failure is recorded. |
| Check outcomes | Know which declared checks passed for this output. | Native check commands plus one frozen result manifest. | The earlier review found a rule conflict; no P4 fixture has run. |
| Receipt claims | Explain historical checks and query current availability. | Nix and Attic queries plus immutable log links. | No V4 receipt exists yet. Current state changes after a run. |
| Recovery status | See which native activation or restore operation worked. | Machines and Home Manager status; separate P6 restore records. | Upstream recovery limits are known; no P7 fixture has run. |
| Storage report | Decide when wider retention is affordable. | `nix path-info` and filesystem size queries. | No source growth result supports a first proof threshold. |
| Proposed names | Configure the first module on the selected pin. | Native import and typed Nix options proved by P1. | No V4 name has a passing fixture. |

## What the smaller contract must still prove

| First workflow stage | Keep this observable result | Native owner and smallest Vendomat addition |
| --- | --- | --- |
| Compose and develop | A focused module works in plain and flake backed consumers. A local override stays visible and reversible. | devenv inputs, imports, profiles, and locks select it. Vendomat may report effective selection. [devenv documents that imported `devenv.yaml` is not evaluated](https://devenv.sh/guides/polyrepo/). |
| Inspect | The owner reads the selected module and one third party source with an honest identity and relationship. A gap stays visible. | Git, native lock entries, and Nix source paths supply identity. A small retained object and manifest supply durable inspection. [Nix separates output and derivation queries](https://nix.dev/manual/nix/2.35/command-ref/nix-store/query). |
| Check and build | The declared command and editor checks pass for one frozen selected output. A failed or missing required check blocks publication. | Native checks and Nix build supply results. The run manifest binds checks to input and output identity. |
| Publish | Attic serves every selected runtime closure path in an isolated fixture. The selected output's NAR hash matches the checked bytes. | Nix lists paths and metadata. Attic pushes closures. [Attic can skip upstream signed paths by default](https://docs.attic.rs/reference/attic-cli.html). |
| Consume | A cold laptop substitutes and runs the command and editor without building. | Nix substitution and the application prove use. No Vendomat runtime is needed. |
| Recover | Retained source reads after restore. A rebuilt selected output passes the existing consumer trust check. Preserved evidence explains the old check. | Native source, Nix, Attic, and recorded logs supply these results. Attic objects are rebuilt from selected source. |
| Machine claim | A separate native plan, transfer trace, service result, and user result pass on a tested pin. | Machines, NixOS, and Home Manager own activation. Vendomat links checked application output identity only. |

The normal and dedicated Neovim forms must use one packaged command. A conflicting `PATH` entry must not select another command. Both forms must display a representative result. The dedicated form must keep its settings apart from the normal editor. These checks remain in P1 and P4.

## Decisions for the owner

| Decision | Recommendation | Why and remaining risk |
| --- | --- | --- |
| `D-APP-SCOPE` | Move the full later application case out of core V4. | Its 31 IDs do not help the first proof. Preserve its design and IDs in a separate note. |
| `D-NAMES` | Keep every new name provisional until a fixture proves it. | Remove unproved examples from the normative contract. |
| `D-CHECK-OWNER` | Keep module default required checks and consumer added checks as one declared set. | This protects the first editor proof. One declaration must identify each required check. |
| `D-CHECK-GAP` | Keep a short, explicit coverage note for a documented nonrequired check. | Do not add a general missing test detector. The three P4 outcomes stay distinct. |
| `D-CAPTURE` | Keep owned source plus one named selected third party source for the first proof. | Make capture explicit. Add automatic list policy only after repeated work. |
| `D-CAPTURE-GRAPH` | Remove the two graph gate from P3. | The first source can use a native input identity. A package to source map remains a later experiment. |
| `D-PROOF-GATE` | Keep separate application and machine claims. Move machine preflight out of P0. | P1–P6 can then finish without a remote machine. P7 still gates machine readiness. |
| `D-OFFLINE-SOURCE` | Keep unavailable lookup and independent local execution. | A disconnected client may lack source access. It must not change retained status. |
| `D-REPO-BACKUP` | Keep GitHub repository copies outside Vendomat. Remove this decision from normative V4 text. | The boundary belongs in project policy or review history. It creates no Vendomat feature. |
| Source and receipt shape | Use retained native source plus one manifest, and one run manifest with log links. | A fixture must still prove byte identity and honest source correspondence. |
| Guide scope | Keep P0–P7. Move P8–P10 to future notes. | No first proof gate is removed. |

Each row needs owner approval before the V4 documents change. Approval can cover this plan as one change, or can name exceptions.

## ID edit map

These are proposed dispositions. The target ID keeps the observable result. The ID history keeps every retired or moved ID and its reason.

| Group | Retire, merge, or move | Keep or destination |
| --- | --- | --- |
| OWN | `002`, `005`, `007`, `010` | Native authority in `001`; lookup in `SRC-012`; selection report in `SEL-001`; native task use in guide. Move `012` to cutover. |
| MOD | `007`, `013` | Native missing export under `001`; plain delivery limit under `011`. |
| SEL | `004`, `008` | Frozen input and output identity under `003`, `005–007`, `009`. |
| CHK | `005`, `008–009`, `015–016` | Check set under `010`, failed check under `004`, missing declared check under `011`, documented gap under `012`, check origin under `014`. |
| SRC | `001`, `010`, `013–014`, `016–023` | Exact first source under `002–009`, `011–012`, `015`, `024–025`. Native build mismatch belongs in `CHK-006`. Later indexing, remote reads, and graph policy need their own trigger. |
| CACHE | `007–008` | Local independence under `OWN-004/013`; unchanged selection under `SEL-003`. Keep `001–006`, `009–015`. |
| EVD | `004`, `008`, `010` | Source gap under `SRC-008`; acceptance and activation under native owners; rebuild claim only after its own proof. |
| REC | `003–004`, `006–008`, `010–011`, `013` | Keep `001–002`, `005`, `009`, `012`. Move storage and deletion features to future work. Keep machine status under MACH. |
| MACH | `004`, `007`, `010`, `013`, `015` | Native plan and checked paths under `003`; check reuse under `CHK-007`; system and user results under `009`, `011`, `014`. Move `001` to P7 entry. |
| PROOF | `001–009` | Put combined acceptance scenarios in guide P1–P7. `007–008` were already retired. |
| UPG, OPT | `UPG-001–009`, `OPT-001–004` | Move to future work note. No V4 phase gate. |
| APP | `APP-001–031` | Move to later module note. No V4 phase gate. |

This map gives 88 active core IDs. It does not authorize deleting historical IDs. It changes `SRC-003` from an automatic two graph policy to one selected third party source. It also changes the P3 gate and the first proof text in the same edit.

## Edit plan after approval

1. Add one later application note. Move Spec §9 and `APP-001–031` there. Retain an ID move map.
2. Shorten Concept §§2–25 to the owner goals, native boundary, first proof, and open experiments. Remove repeated procedure and later feature details.
3. Make Spec §§1–8 the sole normative contract. Apply the decisions above. Replace long proposed examples with fixture links or schematic input.
4. Rework Requirements into the 88 active ID ledger and compact historical map. Keep the old audit unchanged as provenance. Record every merge target and moved ID.
5. Rework the guide in phase order. Keep P0–P7 gates. Move remote Machines entry to P7 and active consumer transitions to cutover. Reduce P3 and P6 steps. Put later work in one short note.
6. Update AGENTS.md only to point to the new authority and gate order. Do not rewrite the preserved pre V4 README or implementation.
7. Check links, ID counts, phase labels, and decision text together. Run `devenv shell -- testee verify --mode quick`. Review the complete change through Gitman, then commit and push it as one reviewable change.

Do not start P0 work during these edits. Do not claim a new gate passed. The first fixture after approval will still determine exact names, commands, and file formats.

## Current host audit

I checked only host claims used in this review. On 2026-10-06, `devenv --version` reported `2.4.0+b904dcb` and `nix --version` reported `2.34.7`. `systemctl show atticd.service` reported active and running. `ss` showed `127.0.0.1:8089`. `tailscale serve status --json` showed `/attic` routed to that port. These observations update the older preactivation rows in the [P0 record](../../../docs/V4_P0_PROOF.md). They do not prove a client, a cache object, a full closure, or cold use. Current Nix settings still list only public substituters, `fallback=false`, and `require-sigs=true`. The P0 gate remains blocked under the current guide.

Gitman reports the working copy as canonical and `main` in sync with origin. `devenv shell -- gitman status` works here, even though the task context said Gitman was not in this devenv. The current status lists only this review file as changed.

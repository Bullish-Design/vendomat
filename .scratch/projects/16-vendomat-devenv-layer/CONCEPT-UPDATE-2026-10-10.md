# V6 concept update: workspace users first

**Date:** 2026-10-10. **Status:** Draft concept decision and session record.
**Authority:** V5 remains authoritative until the owner accepts the updated V6 specification.
Read this record with [the concept](./CONCEPT-V6.md), [specification](./SPEC-V6.md),
[guide](./GUIDE-V6.md), and [gate record](./evidence/GATES.md).

## Goal and scope

The owner wants the smallest maintainable Vendomat system that uses native devenv behavior.
Vendomat must support many personalized, composable modules. A module declares its required inputs
in its own `devenv.yaml`. A consumer inherits those inputs. Vendomat also bundles a template
generator library, so it can create files for users and module authors.

The first user goal is a workspace user who can create and update a workspace without editing Nix.
The owner would also like machine operators to avoid Nix for routine work. Machine coverage follows
the workspace flow. This sequence must leave a clean path for machine coverage without a core
rewrite. Module authors may write Nix.

The full V6 machine plan still covers the new `server` system and Framework adoption. This update
changes the order and the authoring contract. It does not authorize a disk write, deployment,
firmware change, or secret transfer.

## Clarifications from the review session

| Question | Owner direction |
| --- | --- |
| Which V6 choices may change? | Challenge any choice. Use native devenv functionality where reasonable. |
| Primary design measure | Choose the smallest maintainable system. |
| May already built features be removed? | Yes. Recommend cuts when ongoing cost exceeds value. |
| How do reusable modules declare inputs? | Each module has a `devenv.yaml`; consumers inherit those inputs. |
| Who should avoid Nix? | Workspace users and, ideally, machine operators. Module authors may write Nix. |
| Can Vendomat generate files? | Yes. Vendomat will bundle a template generator library. |
| Delivery order | Prove the no-Nix workspace flow first. Add machine coverage later without a major architecture change. |

## Research and observations

The [project 15 alignment research](../15-devenv-alignment/) and V6 fixtures studied native
devenv imports, input locks, module evaluation, Machines, and offline shell entry. The present
pre-resolver exists because an input-style import does not inherit its source's `devenv.yaml`.
The [Step 2 evidence](./evidence/step-2.md) records a passing three-level input fixture.
The fixture uses one consumer lock and top-level inputs with one-level `follows`. This is evidence
for input inheritance, not for the new user interface.

The [Step 3 evidence](./evidence/step-3.md) records passing fixtures for a central description
builder and hand-written faces. Those fixtures show that the mechanism can work. They do not
show that its shared description format is the smallest durable authoring contract. The current
code still implements this builder. This concept update does not change implementation code.

The V6 [gate record](./evidence/GATES.md) reports G2 and the original G3 as passed. It reports
G6 and G7 as passed in virtual machines. G1 and G5 still have named infrastructure blockers.
No gate has yet shown a workspace user selecting two authored modules and changing a supported
value without editing Nix. The new G3A gate is open.

The V6 concept currently places `vendomat.libs.<name>` values in hand-written workspace Nix.
It also requires one library description to produce devenv, NixOS, and Home Manager modules.
The machine sketch asks an author to write inventory, imports, and disk roles in Nix. These
examples reveal the gap between the proposed user goal and the original authoring interface.

## Adversarial assessment

The pre-resolver has a concrete reason to exist. Reusable modules bring `devenv.yaml` inputs,
but native input-style imports do not inherit those declarations. Removing the pre-resolver would
make consumers copy input declarations or change the promised composition model. Keep it narrow:
read pinned declarations, prepare the consumer's native lock inputs, and report conflicts.

The central description builder has a weaker reason to exist. It defines packages, options,
services, an `extra` escape hatch, a marker, three target outputs, and shared option paths.
Module authors may already write Nix. Native devenv, NixOS, and Home Manager modules can express
each target directly. The description format therefore adds a second module language and a
central compatibility duty. It also asks each library to fit targets it may never use.

Generating a Nix file once does not by itself satisfy the workspace goal. Users must also make
later routine changes without Nix edits. That calls for a small, user-owned configuration surface
and deterministic Vendomat-owned wiring. The interface should pass only supported values. It
must not become a general TOML encoding of Nix expressions or the full devenv option tree.

A no-Nix machine operator goal is feasible for known roles and bounded host facts. New services,
unusual disk layouts, and new policy still need an author to write Nix. A universal machine
configuration schema would duplicate NixOS and disko. Machine templates can create a role and
collect explicit facts, but disk identity and installation changes still need review.

## Decisions in the revised draft

1. Make no-Nix workspace creation and routine updates the first user acceptance goal.
2. Keep `vendomat.toml` as the workspace user's source of module selections and supported values.
3. Keep the pre-resolver so selected modules can bring their own `devenv.yaml` inputs.
4. Use the bundled template generator for initial workspace files and optional author scaffolds.
5. Let module authors write native devenv, NixOS, and Home Manager modules.
6. Retire the required library description, central three-target builder, and marker as the
   proposed authoring contract. Preserve their passing fixtures as historical mechanism evidence.
7. Require only the module targets a source actually needs. Do not require one option path,
   `enable` switch, or service model across all targets.
8. Keep workspace selection and input resolution separate from generated workspace wiring.
   A later machine adapter can reuse sources without changing the workspace user contract.
9. Keep the existing machine safety research and planned cutovers. Treat no-Nix machine operation
   as a later interface decision, after the workspace flow passes.

These decisions revise the draft concept. They do not mark the new interface as implemented or
prove the proposed registry syntax on pinned tools.

## Proposed workspace path

The template generator creates a stable `devenv.nix`, `devenv.yaml`, and `vendomat.toml`.
The workspace user selects modules and sets supported values in `vendomat.toml`. Vendomat resolves
the selected modules' inputs, then writes its own input fragment and Nix wiring. Native devenv
locks and composes the project. An unselected source remains inert.

The registry's current `[imports]` mapping may carry the module selection. A new values table
may hold supported values. The exact table name, value types, and generated file path are
proposals. A consumer fixture must settle them. The generated files must be reviewable and under
version control. `vendomat sync` must preserve template-owned and user-owned files.

A module author may put `devenv.nix` beside `devenv.yaml`. The module may instead export a native
flake module where that fits. The author defines supported settings in native Nix. A setting that
needs a Nix package or function stays in that authored module. The workspace user supplies only
the values that the tested user format supports.

## Machine path and its limits

The current machine plan may use authored Nix in `nix-systems`. It can keep native devenv Machines
for plan, apply, status, and rollback. It can keep the direct install guard and target preflight.
This phase does not require a no-Nix operator format before workspace adoption.

Later machine coverage can select authored roles and modules from the same sources. A separate
machine adapter can accept bounded host facts and generate wiring for those roles. The operator
must review the target, disk identity, generated diff, and native machine plan. A new machine
capability still goes to a module author. The machine adapter must not turn `vendomat.toml` into
a general NixOS language.

If the owner later limits the no-Nix goal to workspace users, the workspace architecture stays
the same. Machine operators can maintain `nix-systems` in ordinary Nix. That removes the machine
values interface and its upgrade burden, but it requires Nix skill for routine host changes.

## Required document and implementation follow-up

The [specification](./SPEC-V6.md) preserves the old requirement IDs and marks the changed claims
as superseded. Proposed successors cover the workspace user flow, registry choices, generated
wiring, native module authorship, and target-specific faces. The [guide](./GUIDE-V6.md) adds
Step 3A as the new user gate. The [gate record](./evidence/GATES.md) leaves that gate open.

Implementation still needs a tested registry format, generated workspace adapter, module
selection behavior, and a real consumer. The old description builder remains in the code until
the selected native-module route passes and its removal is safe. Do not count the original G3
pass as a pass for G3A. Update the implementation, spec, and guide together if the fixture
disproves an interface.

## Open questions for fixtures

- Which registry table carries supported values, and which value types does it allow?
- Does an `[imports]` entry alone select a module, or does selection need another field?
- Which generated Nix file carries settings while the template-owned root file stays stable?
- How does a module author expose settings without forcing an option path on machine targets?
- Which existing workspaces need a migration from hand-written settings to the new user format?
- After the workspace gate, which machine operator tasks recur often enough to justify templates
  and a values interface?

## Evidence level of this update

This record is a concept decision based on the cited local research and fixtures. It adds no
new runtime observation. The stated new registry format, generated wiring, and no-Nix user flow
remain proposals until a pinned real-consumer fixture passes.

## Document validation on 2026-10-10

The local tools were Testee 0.5.1 and Python 3.13.13. The command
`python3 -I .scratch/projects/16-vendomat-devenv-layer/ledger/build_ledger.py` was expected to
write a ledger with no ID error. It wrote `LEDGER-V6.md` and reported zero errors. The command
with `--check` was expected to leave the ledger unchanged and exit zero. It did so.

The command `testee verify --full` was expected to pass the repository's required checks.
Run `20261010T153231Z-a584dca3f271` exited zero and passed pytest, ruff, ruff-format, and ty.
Its saved report is at `.testee/runs/20261010T153231Z-a584dca3f271/report.json`.
The report marks the run as a full gate with a stable source tree. It does not prove G3A or any
real machine operation.

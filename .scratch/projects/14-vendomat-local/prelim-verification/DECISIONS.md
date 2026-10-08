# Decisions to make from evidence

**State:** Open. These are design choices, not passed checks. Record the selected option, date,
evidence link, and affected requirement IDs after each decision.

| Question | Options to test | Required evidence |
| --- | --- | --- |
| Where do checked-in flakes fetch personal inputs? | One fixed `~/vendor` path on every host; remote URLs with explicit local overrides | PV-03 portability and restore runs |
| How much `nixpkgs` sharing is required? | One node for the controlled graph; allow justified transitive nodes | PV-04 graph and closure measurements |
| Which host settings belong in TOML? | A small typed set; all scalar settings with explicit package lists; native Nix only | PV-06 type and conflict results |
| How does `set → diff → apply` cross the commit boundary? | Require a commit before `apply`; allow an explicit reviewed working-tree apply; make `set` create a commit | PV-08 state trace and failure cases |
| How does an installer reach a private cache? | Join the tailnet; copy a prebuilt closure; use a temporary trusted route | PV-09 cold installer proof |
| What does “build once” promise? | Cache hit while retained; rebuild after eviction; explicit pin or retention for selected outputs | PV-10 publication and collection results |
| Must an input export all three module faces? | Required three faces; only the faces the input uses | PV-07 real input census and evaluation |
| Does the Vendomat command belong in the shared machine core? | Core package; optional host package after Nix-only bootstrap | PV-11 boot and package failure fixture |

Do not settle a choice by changing a requirement in place. Supersede its ID, then update the
concept, specification, guide, and kickoff together. Search for the old claim in every active
document and fixture.

## Decision record template

```markdown
### YYYY-MM-DD — short question

**Selected:** option and exact scope.
**Evidence:** links to result files and raw logs.
**Reason:** why this option meets the current goal.
**Limit:** what the option does not guarantee.
**Requirements:** IDs kept, superseded, or added.
**Documents changed:** paths.
```

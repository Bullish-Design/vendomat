# Step 1 record: the `devenv-py` repository, the toolchain, and the first pin

**Date:** 2026-10-11. **Status:** Observed. Done. No report file exists for this step. The facts
below come from the orchestrator's run summary.

## Result

| Item | Value |
| --- | --- |
| Local repository | `~/Documents/Projects/devenv-py` |
| Remote | GitHub, private, `Bullish-Design/devenv-py` |
| Branch and commit | `main` at `ce250ec0`, pushed |
| Pin identifier | `devenv-2.4.0-b904dcb5-c2f38fe7` |
| `devenv` input | `b904dcb5…` (full revision `b904dcb51fe48c30db250038241507f60752f222`) |
| `nixpkgs` input | `c2f38fe7…` (full revision `c2f38fe7f9e04d9aadd354d380f2bd40531d9737`) |
| `nixpkgs-python` input | `5821ac5267b0dc89e48705407206e3c88ee3e0ad` |
| Testee | `v0.5.1` |
| Testee run | `20261011T044545Z-8570615c953a`, PASS |

The Step 0 probe used `devenv` input `a73c5b84`. That revision was not pinned then. The first pin
uses `b904dcb5`, the revision of the CLI build `2.4.0+b904dcb`. The probe counts (for example 1144
options) belong to `a73c5b84`. The Step 4 export at `b904dcb5` gives the same counts (1144 listed
options, 45 top-level names). Nobody diffed the two sets (see [phase-a.md](./phase-a.md), section 1).

## Dependencies

Each dependency comes from an HTTPS git tag or from PyPI.

| Dependency | Source | Note |
| --- | --- | --- |
| `pydantree-sitter` | tag `v0.4.0` | subdirectory `src/pydantree_sitter` |
| `templateer` | tag `v0.4.2` | the tag is on the `v6-flake` branch of `templateer_v2`, not on `main` |
| `loci-core` | tag `v0.4.5` | with `mancore` `v0.1.0` source |
| `tree-sitter-nix` | PyPI `0.1.0` | wheel `cp310-abi3` |

The `templateer` tag is not an ancestor of `main`. Step 9 adds the `nix` language on `main`. A new
tag must follow (see [step-9.md](./step-9.md)).

## Observations

1. The `devenv.lock` root maps `nixpkgs` to the node `nixpkgs_2`. A node named `nixpkgs` also
   exists. It holds another revision. Code that reads the lock must follow `nodes.root.inputs`.
2. The shell Python is 3.14.7. The repository sets no Python version pin. The dependencies import in
   that version.
3. The pytest check appends the host `PATH`, so tools outside the pure shell stay reachable.
4. The host profile lacks `repoman` and `copyroom`. `devenv.nix` pins the CLIs `repoman` `v0.13.0`
   and `copyroom` `v0.8.1` in `packages`.
5. `copyroom new` with `template-py` does not work under copyroom `0.8.x`. The orchestrator built
   the repository by hand, with `talkee` and `agentman` as the models.

## Inferences

- I1. The guide text "Python 3.13" is not a requirement. Nothing found needs a pin yet. Revisit if
  a dependency drops 3.14 support.
- I2. The `copyroom new` failure may be a template defect or a version mismatch. The cause was not
  isolated.

## Gate

The shell imports `pydantree_sitter`, `templateer`, and `tree_sitter_nix`, and `pin.py` accepts the
pin. The Testee run above passed. Gate for Step 1: met.

GM0 on the new pin is only partly repeated. See [phase-a.md](./phase-a.md), section 7.

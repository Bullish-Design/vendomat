# S9: native `follows` on the pinned fork replaces the shared-child pass (PRE-005)

Date: 2026-10-11. Host `server`, x86_64-linux, Nix 2.34.7. Status: fixture proof on the pinned fork. No repository changed.

## Question and hypotheses

Question: can `follows` in a devenv.yaml, as the pinned fork reads it, replace the shared-child
`follows` pass in `src/vendomat/devenvgen.py` (`_Discovery.follows`, PRE-005)? If it can, the `inputs`
key of `vendomat.yaml` can carry `follows` with devenv's own meaning, and Vendomat needs no transitive
resolver.

| ID | Hypothesis |
| --- | --- |
| H1 | Without `follows`, the lock holds one node per declaring flake (duplicates). |
| H2 | The consumer-wins rule dedupes the inherited top-level `shared`, but not the flake children. |
| H3 | Nested `inputs.<n>.inputs.<m>.follows` in the consumer devenv.yaml reaches the lock and gives one node. |
| H4 | The top-level `follows: <other>` form works. |
| H5 | A flake input with its own `nixpkgs` follows the consumer's `nixpkgs`. |
| H6 | Two sources that declare `shared` differently fail with a clear error. |
| H7 (from the PRE-005 text) | Native `follows` does not detect a child, and does not report a child whose source differs. |

## Tools and inputs

| Item | Value |
| --- | --- |
| Patched CLI | `/nix/store/mmmrsi96mgab54ccgs6l8cpkvh5lh2xm-devenv-wrapped-2.4.0/bin/devenv`; `devenv version` prints `devenv 2.4.0+fb5d382 (x86_64-linux)` |
| Stock CLI (control) | `/nix/store/axhrys71dyh0l7gynicv8mfy9y9mjc4i-devenv-wrapped-2.4.0/bin/devenv`; `devenv 2.4.0+b904dcb` (host PATH devenv is stock) |
| nixpkgs | `github:cachix/devenv-nixpkgs/256551e45f6303e142ab4a98be1bf243feb77dc0` (rev in `devenv.lock` of this repo) |
| devenv modules | `github:cachix/devenv/fe20b5cba7ab5e93ae73f956a8d3efc50e1753f4?dir=src/modules` (same lock) |
| Sources | loopback `git daemon`, tag-pinned `git://127.0.0.1:<port>/<repo>?ref=refs/tags/<tag>` (the fork-3 pattern; `git+file` does not lock a rev on 2.4.0) |
| Fixture | `.scratch/projects/20-vendomat-front-door/evidence/fixtures/s9-follows/s9-follows` (non-production) |
| Logs | `~/.local/state/vendomat/p20/2026-10-11/S9/logs/` (`results.json`, `<case>-1.log`, `<case>-2.log`), run output `run2.out`; first run (19 cases, same results) in `logs-run1/` |

Command (disk check first: unallocated 4.09 GiB, metadata 85.6 percent; no builds beyond the shell
entry; no garbage collection):

```
python3 -I .../s9-follows $PATCHED $STOCK $L/work $L/logs
```

Each case writes a consumer `devenv.yaml` and runs `devenv --no-eval-cache shell -- sh -c 'echo A=$SHARED_A B=$SHARED_B'`,
then a second `shell -- true`, then reads `devenv.lock`.

Fixture shape:

- `shared`: data only (`marker.txt`), tags `v1`, `v2`.
- `lib-a`, `lib-b`: each is a flake (`flake.nix` with inputs `nixpkgs` and `shared`, `flake = false`) and a module
  source (`devenv/devenv.yaml` declares `shared` and `nixpkgs`; `devenv/devenv.nix` sets `SHARED_A` or `SHARED_B` from `inputs.shared`).
  The consumer imports `lib-a/devenv` and `lib-b/devenv`.
  `lib-a` `v2` also declares `tool` with nested `nixpkgs.follows` in its devenv.yaml.
  `lib-b` `v2`: yaml and flake use `shared` `v2`. `lib-b` `v3`: yaml uses `v1`, flake.nix uses `v2`.
- `tool`: a flake with `nixpkgs` and `sub`. `sub`: a flake with `nixpkgs`.

"Nodes" below count lock nodes except `root`. Each `nixpkgs` node has its own `nixpkgs-src` child, so the total is larger than the sum.
"shared" and "nixpkgs" count the nodes for `shared` and for `devenv-nixpkgs`.

## Fork source (read-only)

- `Input` in `devenv-core/src/config.rs:175-200` has `url`, `flake`, `follows`, and `inputs: BTreeMap<String, Input>`. `inputs` is recursive.
- Patch 0007 (`create_flake_input` in `devenv-nix-backend/src/lib.rs`) builds nested overrides at any depth.
  An entry with `inputs` and neither `url` nor `follows` fails: "sets nested inputs but has neither url nor follows".
- Patch 0007 (`InheritedInputs`) copies the whole `Input` of a source entry, including its nested `inputs`/`follows`.
  A consumer input wins by name. `nixpkgs` and `devenv` count as consumer inputs.
- Upstream docs `https://devenv.sh/inputs/` ("Following inputs", fetched 2026-10-11) and the fork's `docs/src/content/docs/inputs.md:131-163` give the syntax:
  top-level `nixpkgs: {follows: base-project/nixpkgs}` and `git-hooks: {url: ..., inputs: {nixpkgs: {follows: nixpkgs}}}`.
  The docs show one nesting level. This is upstream evidence about the tool, not a gate.

## Expected and actual

| Case | Inputs (consumer devenv.yaml) | Expected | Actual |
| --- | --- | --- | --- |
| c0 | `nixpkgs`, `devenv` only | baseline | exit 0; 3 nodes; 1 nixpkgs |
| c1 | + `lib-a`, `lib-b`, imports; no `follows` (H1) | duplicates | exit 0; 12 nodes; **3 shared** (`shared`, `shared_2`, `shared_3`, same rev); **3 nixpkgs**; root `shared` is the inherited one (`shared_3`) |
| c2a | + `shared` `v1` declared (H2) | inherited top-level deduped; children stay | exit 0; same lock shape as c1 (12 nodes, 3 shared, 3 nixpkgs). The consumer entry only replaces the inherited yaml entry; each flake keeps its own child. |
| c2b | + `shared` `v2` declared | consumer wins in modules | exit 0; modules print `shared-v2` for both libs; the flake children stay on `v1`: 3 shared nodes, 2 revs. No message. |
| c3a | `lib-a`, `lib-b` each `inputs: {nixpkgs: {follows: nixpkgs}, shared: {follows: shared}}`; `shared` declared (H3) | one node each | exit 0; **6 nodes; 1 shared; 1 nixpkgs**; `lib-a`/`lib-b` inputs are `nixpkgs: [nixpkgs]`, `shared: [shared]`; modules enter |
| c3b | same as c3a, `shared` not declared (only inherited) | works | **exit 1, no lock:** `Failed to lock inputs for import inheritance: input 'lib-a/shared' follows a non-existent input 'shared'` |
| c4a | `nixpkgs: {follows: lib-a/nixpkgs}` (H4, docs path form) | works | exit 0; root `nixpkgs` is `[lib-a, nixpkgs]`; 10 nodes; 2 nixpkgs |
| c4b | `shared-alias: {follows: shared}`, `nixpkgs-alias: {follows: nixpkgs}` | works | exit 0; root aliases are `[shared]`, `[nixpkgs]`; children not deduped (12 nodes) |
| c4c | `lib-b.inputs.shared.follows: lib-a/shared` | works | exit 0; `lib-b.shared` is `[lib-a, shared]`; 11 nodes; 2 shared |
| c5a | flake `tool` (own `nixpkgs`, child `sub`), no `follows` | duplicates | exit 0; 9 nodes; 3 nixpkgs |
| c5b | `tool.inputs.nixpkgs.follows: nixpkgs` (H5) | `tool` points to root | exit 0; `tool.nixpkgs` is `[nixpkgs]`; 7 nodes; 2 nixpkgs (`sub` keeps its own). Stock gives the same lock bytes (`31b285f8`) when given c5c, because stock drops the depth-2 entry. |
| c5c | + `tool.inputs.sub: {url: <sub>, inputs: {nixpkgs: {follows: nixpkgs}}}` (depth 2, `sub` has a URL) | fork follows | patched: exit 0; `sub.nixpkgs` is `[nixpkgs]`; 5 nodes; 1 nixpkgs. Stock: exit 0, `sub.nixpkgs` stays `nixpkgs_2` (7 nodes), silent. |
| c5d | `tool.inputs.sub: {inputs: {nixpkgs: {follows: nixpkgs}}}` (depth 2, no URL) | fails or follows | patched: **exit 1**, `Failed to create flake inputs: input 'tool/sub' sets nested inputs but has neither url nor follows. Give it a url or follows, or Nix drops its nested inputs.` Stock: exit 0, silent drop (9 nodes). |
| c6a | `lib-a` `v1` and `lib-b` `v2` declare `shared` differently in devenv.yaml (H6) | error | **exit 1:** `input 'shared' has two different sources: one from import 'lib-a/devenv' and one from import 'lib-b/devenv'. Declare 'shared' in your devenv.yaml to choose.` Same text as fork-3. |
| c6b | `lib-b` `v3`: yaml agrees, flake.nix child differs; no `follows` (H7) | silent | exit 0; 12 nodes; 3 shared with **2 revs** (`v1` and `v2`); no warning in the log |
| c6c | `lib-b` `v3` + `lib-b.inputs.shared.follows: shared` | follows anyway | exit 0; `lib-b.shared` is `[shared]`; 11 nodes; 2 shared, 1 rev (`v1`). The different child source is replaced with no message. |
| c7 | `lib-a` `v2`: its devenv.yaml declares `tool` with `inputs.nixpkgs.follows: nixpkgs` | source-level `follows` inherited | exit 0; root gets `tool`; `tool.nixpkgs` is `[nixpkgs]`; `sub.nixpkgs` (depth 2) stays separate (`nixpkgs_4`); 16 nodes |
| c8a | `lib-a.inputs.bogus: {follows: shared}` (child does not exist) | error or warning | exit 0; no message; `bogus` is absent from the lock |
| c8b | `lib-a.inputs.shared: {follows: nope}` (target does not exist) | error | **exit 1:** `Failed to lock inputs for import inheritance: input 'lib-a/shared' follows a non-existent input 'nope'` |

Lock stability: for every case that exits 0, the second run keeps the lock bytes (`lock_stable: true` in `results.json`; 17 of 17).
Cases that exit 1 write no lock.

Per-case lock hashes (run 2): c1 `eab71233`, c3a `d5c1b7a8`, c4a `a418af5f`, c5b `31b285f8`, c5c `aa0dc75e`, c6b `3a8a4fd7`, c6c `2957d20c`, c7 `ac62ef1c`.
The hashes change between runs, because the random daemon port is part of each URL. The shape does not change (run 1 and run 2 agree on node counts).

## Proves

- The fork accepts nested `follows` at depth 1 and at depth 2 in the consumer devenv.yaml, and writes them to the lock as native `follows` edges (c3a, c5b, c5c).
  One shared node and one nixpkgs node result when the consumer lists every child (c3a: 6 nodes, against 12 in c1). This is the lock shape that the V6 fixture asks for.
- The `follows` target must be a top-level input of the consumer devenv.yaml. An input that only inheritance would add is not enough (c3b).
- The path form `follows: lib-a/shared` and the top-level `follows: <other>` form work (c4a, c4b, c4c).
- Stock devenv drops a depth-2 entry without a message. The fork follows it, if the intermediate input has a URL (c5c).
  The fork fails on a depth-2 entry whose intermediate input has no URL (c5d).
- A `follows` that the source's devenv.yaml declares passes to the consumer lock (c7).
- The lock stays byte-stable on a second run.
- The conflict error for two source declarations is unchanged from the fork-3 record (c6a).
- Native `follows` does not compare sources. It replaces a child with a different source silently (c6c). A differing flake child with no `follows` also gives no message (c6b).
- A `follows` that names a child that does not exist is accepted silently (c8a). A `follows` that names a target that does not exist fails (c8b).

## Inference (not proved by a fixture)

- Because `follows` for a missing child is silent (c8a), a fixed policy list (for example `nixpkgs` for every flake input) is safe to write without knowing the child set.
  Not tested for a real flake that has no such child and a `flake = false` target together.
- A `vendomat.yaml` `inputs` key that Vendomat copies to devenv.yaml unchanged gives these same results. The copy step is not built or tested here.
- The `nixpkgs` entry in a source devenv.yaml is ignored (consumer input wins; patch text). The lock shows no extra root input for it.
  The `nixpkgs` duplicates in c1 come from the flake children, not from the yaml.
- A post-lock check could count `devenv.lock` nodes that share one `original` and report duplicates. This needs no resolver and no Nix call. It is not built.

## Unproved

- GitHub, GitLab, and `dir=` sources with nested `follows`; `flake = false` with nested `follows` as the follower.
- `devenv update` and `devenv inputs add --follows` with the nested form on the fork.
- Cold-store and offline entry (DVN-008, DVN-012) with `follows` in the lock. Fixture sources were fetched through the loopback daemon and the network.
- The real collection (`vendomat-demo`): the demo's `vendomat.inputs.nixpkgs.follows` has the same shape as c5b/c3a (depth 1), but it was not run here.
- Depth 3 and deeper, and a child that a flake declares only under some conditions.

## Verdict on PRE-005

Native `follows` replaces the "add the edge" half of PRE-005 (`sync` MUST add `<input>.inputs.<name>.follows = <name>`).
`vendomat.yaml` `inputs`, with devenv's own meaning, can carry `follows` at depth 1 and at depth 2 (with a URL for the intermediate input).
The fork passes it to the lock, and the lock holds one node per source (c3a). Vendomat then needs no transitive resolver, no `nix flake metadata` per input, and no Nix call before the lock.

Three parts of PRE-005 and the old pass do not carry over, and the owner must accept the change:

1. **No detection.** The author must name each shared child (`nixpkgs`, `shared`). Vendomat no longer finds them. A fixed `nixpkgs` policy is safe (c8a).
2. **No "report a differing child".** PRE-005 says to report instead of follow. Native `follows` replaces a different source silently (c6c), and an unlisted differing child stays silent (c6b).
   Only the yaml-level conflict reports (c6a). A lock-only duplicate check (see Inference) can cover the gap later.
3. **Target and depth limits.** The target must be a consumer input (c3b). A depth-2 child needs the intermediate input's URL in the consumer file (c5d), which repeats a transitive fact.

Recommendation: supersede PRE-005 and drop `_Discovery.follows` and `NixResolver` (R3 option 1, R2 open question 12 option 1, plus the lock check as a later option).
Keep the conflict rule of PRE-003's successor (c6a).

## NEW claims (no ID allocated)

NEW: The `inputs` key of `vendomat.yaml` MUST accept the devenv.yaml input keys `url`, `flake`, `follows`, and `inputs` (recursive), with devenv's meaning, and Vendomat MUST write them to `devenv.yaml` unchanged.

NEW: Vendomat MUST NOT add a `follows` edge that the user did not write, and MUST NOT read the inputs of an input to decide one. Evidence: `follows` is native (S9 c3a, c5b, c5c).

NEW: A `follows` target in `vendomat.yaml` MUST name an input that the same file declares. Vendomat SHOULD report a target that it does not find before it calls devenv, because the devenv error comes late (S9 c3b, c8b).

NEW: Vendomat SHOULD report duplicate nodes in `devenv.lock` (two or more nodes with an equal `original`) after the lock step, without a Nix call. It cannot report a differing child that a `follows` already replaced (S9 c6b, c6c).

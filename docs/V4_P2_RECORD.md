# V4 P2 record

**Runs:** 2026-10-06 to 2026-10-07. **Result:** The P2 gate passes on the pinned tools, with the gaps listed
below. No phase after P2 passed.

P2 adds the publication form, delivery checks, override checks, and a fresh realization. Vendomat added no
code for P2. The module repository is `nvim-review`. The raw logs are in
`~/.local/state/vendomat/v4-proof/2026-10-06/p2/`.

## Choice: publication form

**Chosen:** a flake output attribute. `V4-SEL-010` resolves to a flake attribute. `devenv build outputs.<name>`
is recorded as a different handle, not a `nix build` route. It returns a JSON map with a store path and no
`drvPath`. The P1 flake form expresses all three outputs. So P1 did not need rework.

The P2 gate also requires the specification to replace every proposed name with the tested syntax. That edit
is not done yet. It must land before P3.

## Inputs and versions

| Item | Value |
| --- | --- |
| Nix | 2.34.7 |
| devenv | 2.4.0+b904dcb |
| Module repository | `nvim-review` at `215f02d85f4a066b4f54c30ab86ac8a8dcf321a9` |
| Module lock | `nixpkgs` `151fa4e8…`, `home-manager` (follows nixpkgs) |
| Plain consumers | `plain-a`, `plain-b`, `plain-missing`, `fresh`. Each imports `nvim-review` by path |
| Flake consumer | `flake`. Its own nixpkgs is `ac62194…`, which differs from the module lock |
| Override source | A copy of `nvim-review` with the module default `maxLength` changed to 60 |

## Checks

| Step | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| 1 Build JSON | `nix build --json` gives `drvPath` and output path per attribute | Confirmed for `review`, `plugin`, `editor` | `publication/01-build.json` |
| 1 Lock graph | `nix flake metadata --json` `.locks` holds every lock node | `home-manager`, `nixpkgs`, `root` in both sets | `publication/02-metadata.json` |
| 1 Archive | `nix flake archive` lists one path per locked input | Dry run lists 2 inputs plus the root source. A real archive was not run | `publication/03-archive-dryrun.json` |
| 1 Multi-output | `nix build --json` lists every output | Default lists `bin`, `man`. With `^*` it lists all six. Default is not complete | `publication/04c-openssl-all.json` |
| 1 devenv handle | `devenv build outputs.review` gives a handle | JSON map `{"outputs.review": <out path>}`. No `drvPath`. Same path as the Nix route | `publication/05-devenv-build.stdout` |
| 2 Missing input | Removing the required input gives a diagnostic naming it | `attribute 'nvim-review' missing` | `consumers/missing-input.log` |
| 2 Author-only tool | Consumer does not get the author tool | `shellcheck` absent in `plain-a` | `consumers/plain-a-shell.log` |
| 2 Remote author input | Author's extra input is not merged | Observed under `V4-MOD-013`, same method. Not repeated for this module | `baseline/V4-MOD-013-*` |
| 2 Transitive input | Module uses its locked nixpkgs. Lock entry alone enables nothing | Consumer nixpkgs `ac62194…` differs. Review path equals the module's own build. Quiet configuration has 0 `nvim-review` packages | `consumers/flake-review-path.txt` |
| 3 Override | Override changes path and output. Revert restores | Override: path and `max_length` 60. Reverted: original path and 80 | `consumers/a-*.txt` |
| 3 Second consumer | Consumer B's lock and path are unchanged | Lock hash and path identical before and after | `consumers/b-lock-*.sha`, `b-path-*.txt` |
| 4 Fresh realization | Fresh consumer realizes and runs with no Vendomat process | Command ran. 2 findings. Substituters: `cache.nixos.org`, `devenv.cachix.org` | `consumers/fresh-run.log`, `fresh-sources.txt` |

## Requirement IDs observed

| ID | Observation |
| --- | --- |
| `V4-SEL-010` | Flake attribute gives drvPath and outputs. Metadata gives the full lock graph. `devenv build` gives a different handle. |
| `V4-MOD-011` | Missing input diagnostic names it. Author-only tool absent. Remote author input not merged (observed under MOD-013). |
| `V4-MOD-012` | Locked transitive nixpkgs is used. A lock entry alone enables nothing. |
| `V4-SEL-002` | Consumer B's lock hash and path are unchanged after consumer A's override and revert. |
| `V4-OWN-013` | A fresh consumer realizes and runs with no Vendomat process and no Attic. |
| `V4-SEL-001` | Partly observed. The override appears in the native lock and output path. No Vendomat selection report exists yet. |

## Gaps

- `V4-PROOF-003` names a scenario with no text in the guide. This record cites the P2 steps as its evidence.
- `V4-SEL-001` is a Vendomat requirement. The evidence is native. Vendomat has no report command yet.
- The archive check used `--dry-run`. A real archive run is not observed.
- Nix `nix build` against the devenv project itself was not run. Only the flake route and the devenv handle were compared.
- The Attic denial is a configuration fact. This machine has no Attic substituter. The fresh run did not test a failing substituter.
- The override first looked ineffective. The marker was a library default, and the module passes its own value.
  The second run used the module default. This was a test error, not a product failure. Both runs are kept.
- The module repository had a git ref lag. `gitman repair` fixed it. Its tree is clean.

## Gate

Passed on 2026-10-07. The gate needs three things, and each one is in place:

- One publication form is chosen and proved. It is the flake output attribute.
- Both delivery forms pass. The plain devenv consumer and the flake-backed consumer both realize the command.
- A fresh local realization passes with no Vendomat process and no Attic.

The specification now uses the tested names for the publication form and delivery. The edits are in
`V4-SPEC.md`, section 3, and the question table. The gate makes no machine claim and no Attic claim.
P3 needs a writable store. The pin record says the daemon accepts writes. P3 entry still needs its own check.

# V4 P5 record

**Run:** 2026-10-07. **Result:** Steps 1 to 4 pass on the pinned tools. Step 5, the cold machine,
is blocked. No phase after P4 passed.

P5 publishes to the real Attic server and proves cache consumption. Unlike P1 to P4, this phase
touches real, persistent infrastructure: the cache `vendomat` on `atticd.service` now holds real
data. It is not a throwaway fixture. Vendomat added no code. Raw logs are in
`~/.local/state/vendomat/v4-proof/2026-10-07/p5/`. Two credentials were minted outside this
session, by the owner, and are not in any log: a publisher token (push, pull, create-cache,
configure-cache, configure-cache-retention) and a separate pull-only token.

## Inputs and versions

| Item | Value |
| --- | --- |
| Nix | 2.34.7 |
| Attic | server 0.1.0, client 0.1.0, both `attic-0-unstable-2026-06-26` |
| Cache | `vendomat`, private, priority 20, retention 0, public key `vendomat:SRJCMEnuScYDRmGId+o9nkXn+MaLpQvDTHs5AfnRQgA=` |
| Selection pushed | `nvim-review`'s `editor` output, `/nix/store/l6imh86vz9ic4cmyikisxszrrfvs7ab8-nvim-review-editor`, 121-path closure |
| Cold consumer | `framework` — still unreachable. Worse than the earlier SSH timeout: `ping` now gets 100% loss |

## Correction: `atticadm make-token --help` has two more flags than first reported

My first reading of `--help` was truncated. `--create-cache <PATTERN>` and `--delete <PATTERN>`
exist and were missing from my earlier report to the owner. The owner had to re-mint the publisher
token once I found this by reading the Attic source directly
(`server/src/adm/command/make_token.rs`). The corrected full flag list is in that source file.

## Checks

| Step | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| 1 Cache and tokens | Cache, push token, separate pull-only token, trusted public key all exist | All 4 exist. See table above | `cache-create.log`, `cache-info.log` |
| 1 Pull cannot push | The pull-only token is refused on push | `AccessError: ... does not have permission` | `pull-token-push-attempt.log` |
| 1 Retention zero | The cache's retention period is 0 | `Retention Period: 0` | `cache-retention.log`, `cache-info-after.log` |
| 2 Upstream filter cleared | A path first obtained from a public cache is not silently dropped | `cache create --upstream-cache-key-name` set to a non-matching value. Push reports `0 in upstream` for all 121 paths, several of which came from `cache.nixos.org` | `cache-info.log`, `push-editor.log` |
| 2 Push | The seeded path and its closure appear in the cache | 121 paths pushed, including public-cache-sourced dependencies (e.g. `perl-5.42.3`, `neovim-unwrapped`) | `push-editor.log` |
| 3 Query every path | Every closure path is present when queried from the cache alone | `nix path-info --store <cache>` returns all 121 names, exact match with the local closure | `path-info-cache-full.json`, `cache-present-names.txt` |
| 3 NAR hash | The served hash equals the checked hash | Both equal `sha256-sNmrFKjY…` | `narhash-compare.txt` |
| Adapted CACHE-005 | A never-pushed path reports absent, not a false success | `{"wic6…-cowsay-3.8.4": null}` | `absent-path-check.json` |
| Adapted CACHE-006 | Retrying a push is safe and reports no false failure | `121 already cached, 0 in upstream`, nothing re-uploaded | `push-retry.log` |
| 4 Isolated substitution | Every path substitutes from the cache alone, with other substituters and local builds off | All 121 paths copied from `http://127.0.0.1:8089/vendomat`. `max-jobs 0`. No other substituter configured | `isolated-build.log` |
| CACHE-013 secret scan | No push credential or signing secret in any tracked file, store path, or log | None found. A `netrc` file holding a token was created, used, and securely removed after each use | this record, section above |

## Requirement IDs observed

| ID | Observation |
| --- | --- |
| `V4-CACHE-001` | The pushed path, the queried path, and the checked path are the same store path throughout. |
| `V4-CACHE-002` | All 121 closure paths, enumerated with `nix-store -qR`, are present in the cache. |
| `V4-CACHE-003` | Dependencies first substituted from `cache.nixos.org` during the build are present in the cache, with `0 in upstream` confirming the filter did not drop them. |
| `V4-CACHE-005` | Adapted: a path that was never pushed reports `null`, not a false success. A true remove-after-push test needs storage access this run does not have. |
| `V4-CACHE-006` | Adapted: retrying an already-complete push is a safe no-op. A true mid-transfer interrupt was not tested. |
| `V4-CACHE-009` | The isolated-store build substitutes the full closure with builds disabled and runs the editor afterward. The literal second-machine case (`V4-MACH`-style cold consumer) is still open; see the gap below. |
| `V4-CACHE-013` | The pull token cannot push. No secret appears in any tracked file or log. |
| `V4-CACHE-015` | NAR hash of the cache-served output equals the checked hash, recorded in an isolated store with other substituters and local builds disabled. |

## Gaps

- **`BLK-P5-04` is not cleared.** The cold consumer `framework` is still unreachable. Step 5 of the
  guide — a second physical machine starting without the output, obtaining it from the cache, and
  running both editor forms — did not run. The isolated-store substitution test is the closest
  local proxy, and it is not the same claim.
- **`V4-CACHE-014` is not tested.** Removing one cached path needs either filesystem access to
  `/mnt/wd_green1/attic` (root-only, `andrew` has none) or a per-path delete API. This Attic
  version's client has no path-delete subcommand, and the server exposes no delete route beyond
  destroying a whole cache. This is a new blocker: `BLK-P5-08`.
- Running the isolated-store build's output directly executed a binary whose symlinks resolve to
  absolute `/nix/store/…` paths. The real `/nix/store` already held those paths from the earlier,
  non-isolated build. So that specific "it runs" check does not, by itself, prove the isolated
  store was the source of what actually executed. The substitution log and the NAR hash comparison
  do not have this problem; they are the reliable evidence for this step.
- `V4-EVD-003` (the receipt records the cache target and availability) is not tested here, because
  no receipt was assembled for this push. P4's receipt harness did not include a real upload; this
  run did the upload but did not re-run the receipt harness against it.
- `V4-PROOF-006`, P5's scenario, has no text in the guide, the same gap pattern as P1 to P4.

## Gate

Not passed. The guide's P5 gate needs the cold machine to run the application from the cache with
no build. That did not happen. Steps 1 to 4 pass individually and are recorded above. P6 needs P5
to pass, so P6 has not started.

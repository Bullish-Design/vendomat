# V4 P3 record

**Run:** 2026-10-07. **Result:** The P3 gate passes on the pinned tools, with the gaps listed below.
No phase after P3 passed.

P3 proves source retention. Vendomat added no code for P3. Every check uses native Nix commands
against the `nvim-review` selection from P1 and P2. Raw logs are in
`~/.local/state/vendomat/v4-proof/2026-10-07/p3/`.

## Inputs and versions

| Item | Value |
| --- | --- |
| Nix | 2.34.7 |
| Selection | `nvim-review` flake at `215f02d85f4a066b4f54c30ab86ac8a8dcf321a9` |
| Locked inputs | `nixpkgs` `151fa4e8…`, `home-manager` `fae6e9e4…` |
| Store | daemon, trusted, writable (`nix store info`, a test `nix store add` write) |

## Checks

| Step | Expected | Actual | Evidence |
| --- | --- | --- | --- |
| Archive | One store path per locked input, plus the root source | 3 paths: `nixpkgs`, `home-manager`, root | `archive.json` |
| GC roots | A root per archived path | 3 roots under `gcroots/` | `gcroot-1.log` to `gcroot-3.log` |
| Survival | Every archived path survives a real GC | All 3 survived `nix-collect-garbage` | `survival-check.txt` |
| Size | Total archived bytes recorded | 217,954,480 bytes (about 208 MiB) | `archived-sizes.txt` |
| Identity, exact | Locked input identity matches `nix flake metadata --json` | `nixpkgs` and `home-manager` revisions and NAR hashes match | `identity-records.md`, `metadata.json` |
| Identity, upstream reference | A retained, non-locked object gets a weaker correspondence claim | `gawk`'s source is rooted but not a lock node | `upstream-ref-src.txt`, `upstream-ref-root.log` |
| Identity, unresolved | A built package left uncaptured reports a coverage gap, not a failure | `neovim-unwrapped`'s source has no root. `nix flake check` still passes | `flake-check.log` |
| Corruption | A changed retained object loses its exact-correspondence claim | A copy's hash matches the recorded NAR hash, then differs after one byte changes | `corrupt-hash-before.txt`, `corrupt-hash-after.txt` |
| Dirty capture | `nix store add` on a dirty tree gives an immutable, content-addressed identity | The captured path keeps `maxLength = 60` after the working tree changes to `99` | `dirty-ca-path.txt` |
| Read | Reading a retained file changes no lock and no output path | `plain-a`'s lock hash and the `review` output path are unchanged before and after | `lock-before-read.sha`, `lock-after-read.sha` |
| Write denial | The store refuses a direct write | `permission denied` | `write-denied.txt` |

## Requirement IDs observed

| ID | Observation |
| --- | --- |
| `V4-SRC-002` | All 3 archived paths survived a real `nix-collect-garbage` run, each behind its own root. |
| `V4-SRC-003` | The archived path set (`nixpkgs`, `home-manager`, root) matches the lock's complete input set. |
| `V4-SRC-004` | Each retained input has a record naming its locator, locked revision, NAR hash, store path, and the consumer selection. |
| `V4-SRC-006` | Three states observed: exact (locked input, matching NAR hash), upstream reference (`gawk`, retained but not a lock node), unresolved (`neovim-unwrapped`, not retained). |
| `V4-SRC-008` | `neovim-unwrapped`'s source is uncaptured. `nix flake check` passes regardless. |
| `V4-SRC-009` | A corrupted copy's hash no longer matches the recorded NAR hash. The exact-correspondence claim would be withdrawn. |
| `V4-SRC-011` | Reading a retained file changes no lock, no output path. A direct write is denied. |
| `V4-SRC-024` | `nix store add` on a dirty tree gives a content-addressed path. Later edits to the working tree do not change it. |

## Gaps

- `V4-SRC-015` is not tested. Vendomat has no receipt format yet, so there is no rebuild field or
  cache-signature field to inspect. This needs the receipt format from P4.
- `V4-PROOF-004`, P3's scenario, has no text in the guide. This record cites the P3 steps as its
  evidence.
- The GC roots in this record live under the proof directory, not under a Vendomat-owned path.
  Vendomat's own GC-root location is still proposed, not implemented.
- The corruption and dirty-capture checks used copies outside the Nix store. They did not alter
  the real store, which the store itself refuses to let happen.

## Gate

Passed on 2026-10-07. Every locked input is retained, rooted, identified, and readable. The
built package reports `unresolved`, not a guess. Source retention changed no selection: the lock
hash and the output path were the same before and after every read. P4 needs the receipt format.
That format does not exist yet.

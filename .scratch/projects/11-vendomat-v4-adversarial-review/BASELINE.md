# V4 review baseline

Review project: `11-vendomat-v4-adversarial-review`
Source of record: `.scratch/projects/09-vendomat-nixos-devenv-rewrite` (unchanged by this review)
Copied at: 2026-10-04 (local), from trunk commit `38f9005ed287f6a1ef176faca10ac1c18054c93f`
Review workspace: gitman lane `v4-adversarial-review-11` in `.worktrees/v4-adversarial-review-11`

## Why prefix 11

`.scratch/projects/10-vendomat-v4-adversarial-review` already existed in the working copy when
this review started, on gitman lane `vendomat-v4-adversarial-review`. This review did not
overwrite it. `11` is the next free prefix.

## Inherited baseline (SHA-256 before any review edit)

| File | SHA-256 | Bytes | Lines |
|---|---|---|---|
| `CONCEPT-V4.md` | `2382b9f2bf0dae39b6a287fbe73bd63c10fe9c3f570a2d0d488d112403f74d2e` | 51027 | 975 |
| `V4-SPEC.md` | `c87726f8f8ec97fae78e9999adba65cafc1a4f8884ee77201a3f47b91d255bd9` | 33045 | 309 |
| `V4-REQUIREMENTS.md` | `c2e11464efd42184c869884902b254ef8d481fc20d9f8193a41b876fe3908bf4` | 45964 | 307 |

Any text in these three files that does not match the above hashes is a revision from this
review. To separate inherited text from revisions:

```bash
diff -u .scratch/projects/09-vendomat-nixos-devenv-rewrite/CONCEPT-V4.md \
        .scratch/projects/11-vendomat-v4-adversarial-review/CONCEPT-V4.md
```

## Scope of the copy

The source directory holds eleven markdown files. Only three carry `V4` in the name, and those
three are also the three newest files in the source directory:

- `CONCEPT-V4.md` (2026-10-04 19:05)
- `V4-REQUIREMENTS.md` (2026-10-04 21:31)
- `V4-SPEC.md` (2026-10-04 21:32)

No other source file names V4. The source directory gained no newer V4-specific file.
`CONCEPT.md`, `CONCEPT-CODEX.md`, `CONCEPT-CLAUDE.md`, `CONCEPT-V2-C.md`, `CONCEPT-V2-CC.md`,
`CONCEPT-V3-C.md`, `CONCEPT-V3-CC.md` and `IMPLEMENTATION_GUIDE.md` are earlier work. This
review does not treat them as V4 authority.

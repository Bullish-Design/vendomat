# W9: why devenv's evaluation cache misses some imports — 2026-10-13

<!-- Provenance: a subagent read devenv's source and ran fixtures on 2026-10-13. Raw report,
scripts, fixtures, and the doctor prototype: ~/.local/state/vendomat/p22/eval-cache-mechanism/
(REPORT.md, setup.sh, setup2.sh, mkproj.sh, q.py, doctor_check.py, fx/). The orchestrator wrote this
record from REPORT.md and checked that the record and the report agree. The orchestrator did not
rerun the fixtures. -->

This is the gate of owner ruling R11 (`ESTATE-034`). It explains W1's two results from source code.

## Inputs

- devenv 2.4.0+b904dcb. Source: `cachix/devenv` tag v2.4.0, HEAD `b904dcb51fe4`, the same build.
- Nix 2.34.7. Nix-side source: `cachix/nix` rev `bd10d7f5`, the pin in devenv's `flake.lock`.
- Cache: `.devenv/nix-eval-cache.db` (SQLite), read with `python3 -I` in read-only mode.
- One scratch devenv project per case. Each overlay-style `devenv.local.nix` imports an absolute
  path under `fx/share/<case>/`; the module sets `env.SPIKE_VAR`.

## Mechanism (from source)

Paths are relative to `cachix/devenv` at v2.4.0, except the first item.

1. **Nix reports a resolved path for an evaluated file.** `EvalState::evalFile`
   (`cachix/nix` `eval.cc:1148-1169`) reports the path from `resolveExprPath` (`eval.cc:3194-3208`).
   That function follows a symlink in the final path component only. A final component that is a
   real file keeps the path as written, with any directory symlinks above it. A final component
   that is a symlink becomes its target, which for a module file is a `/nix/store` path.
2. **devenv drops store paths.** `ops_to_identities`
   (`devenv-eval-cache/src/ffi_cache.rs:348-349`) skips every path that starts with `/nix/store`.
   Such an import gets no `file_input` row and is never checked again.
3. **devenv stores the path as given.** `FileInputDesc::new` (`eval_inputs.rs:108-135`) stores the
   path without canonicalizing it, a blake3 content hash, and the `stat` modification time (which
   follows symlinks).
4. **A cache hit passes two checks.**
   - `get_cached` (`caching_eval.rs:107-160`) runs `check_file_state` (`eval_inputs.rs:223-295`). It
     skips hashing when the modification time is unchanged (`:256-263`). Every store file has
     modification time 1, so this check cannot see a change from one store file to another.
   - `try_restore_cached_state` (`caching_eval.rs:473-503`) calls `inputs_changed`
     (`ffi_cache.rs:198-216`). It re-hashes every tracked path from disk, with no time shortcut.

**Rule:** devenv re-checks an import only when the final component of its path is not a symlink.

W1 explained:

- A changed **file symlink** is missed because the import has no row at all (item 2). W1's "row
  recorded once" was left over from W1 Q1, when the same path was a plain file.
- A changed **directory symlink** is caught because the final component is a real file, so the
  path as written has a row. Check 1 passes (time 1 equals 1). Check 2 re-hashes through the new
  links and forces a new evaluation. A debug trace shows `cache hit`, then `evaluation inputs
  changed while restoring a cache hit`.

## Fixtures

| Case | Final component | Row? | After the change |
| --- | --- | --- | --- |
| File symlink into the store | symlink | no | Stale |
| Directory symlink, real module file | real file | yes | Caught |
| Home Manager tree over a `linkFarm` whose entries link to files | symlink | no | Stale; `--refresh-eval-cache` fixes it |
| Home Manager tree over a store directory of real files | real file | yes | Caught |
| `linkFarm` entry that links to a directory holding a real file | real file | yes | Caught |
| System-profile form (`/run/current-system/sw/share/devman/link-module.nix`) | symlink | no | Stale; refresh fixes it |
| Profile, `share/<dir>` owned by one package (a directory link) | real file | yes | Caught |
| Profile, `share/<dir>` shared by several packages (file links) | symlink | no | Stale; refresh fixes it |

`builtins.readFile` and `builtins.hashFile` on a symlinked file add no row either.

## The production import (read-only)

The devman repository's real cache has no row for
`/run/current-system/sw/share/devman/link-module.nix`. That path is a file symlink into
`devman-link-0.6.0`. A new devman-link store path is therefore not seen by an existing cache until
`--refresh-eval-cache` runs or another tracked input changes. The overlay file
`~/.config/devman/projects/devman/devenv.local.nix` has a row, because its target is not in the
store. **Inference:** the same holds for every repository that imports the system path (62 overlay
files).

## Verdicts

- The directory behaviour is **incidental**. No code comment, test, document, or issue promises
  it. It rests on two accidents: Nix keeps directory symlinks in the path as written, and
  `inputs_changed` re-hashes with no time shortcut. Open issue cachix/devenv#3154 asks to make a
  hit cost only `stat` calls. A time shortcut in `inputs_changed` would break the directory case,
  because store files always have time 1. `main` had the same code on 2026-10-13.
- The layout planned under R11 (a Home Manager directory over a `linkFarm` of file links) is
  **stale**.
- A design that changes the content and the time of a real file outside the store does not depend
  on either accident. **Inference, not yet run:** a pointer file that Home Manager activation
  rewrites, holding the layer's store path, is caught by both checks.

## The fleet doctor check

An untracked import leaves no row, so the doctor checks that each import can be tracked:

1. For each absolute import path as written in the repository's `devenv.local.nix`: if the final
   component is a symlink, fail ("untracked import").
2. Otherwise open `.devenv/nix-eval-cache.db` read-only and require a `file_input` row whose path
   equals the import as written. A missing row fails. No database: skip.

The prototype (`doctor_check.py`) fails exactly the stale fixtures and the real system-path import.
Pair it with a pin fixture in CI: change a directory symlink and require the new value with no
flag. The fixture fails if devenv changes `inputs_changed`.

## Unproved

The pointer file; a real Home Manager generation; the exact Nix binary (source read at the
`flake.lock` pin; traces and fixtures agree with it).

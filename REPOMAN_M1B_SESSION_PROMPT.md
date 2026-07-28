# Repoman M1b kickoff prompt

```text
Work in the repoman repository to implement Milestone M1b from vendomat’s implementation plan: add the `wheel:` source kind end-to-end, with a Rust-toolchain opt-out.

Context

Vendomat is the vendor layer for the `*man` family. Its Nix module already exposes a wheelhouse through `UV_FIND_LINKS` and protects personal native packages with `UV_NO_BUILD_PACKAGE`. The missing piece is repoman: `repoman-sync` does not understand `wheel:` entries in `repoman.lock`, so it cannot install a prebuilt personal wheel without falling back to editable/native compilation.

The vendomat repo has already completed M1a and Face B milestones through M4. Do not reimplement those. This session is specifically the focused repoman M1b change.

Read these first, in full:

- `docs/IMPLEMENTATION_PLAN.md` in the vendomat repo, especially M1b and design issues 1 and 6.
- `docs/DESIGN.md` in the vendomat repo, especially the wheel/source-kind sections.
- In repoman, inspect:
  - `modules/scripts/repoman-sync.sh`
  - `modules/managers/gitman.nix`
  - `repoman.lock`
  - `tests/consumer-example/repoman.lock`
  - existing tests for the sync script, lock parsing, manager modules, and consumer examples.
- Inspect vendomat’s `modules/devenv.nix` to understand the existing `UV_FIND_LINKS` / `UV_NO_BUILD_PACKAGE` contract. Treat it as the provider-side contract; this task is consumer-side repoman work.

Required implementation

1. Add open-vocabulary `wheel:` source support in `modules/scripts/repoman-sync.sh`.

   The script’s embedded Python target resolver currently handles existing source kinds. Extend it so:

   ```python
   wheel:pyjutsu>=0.8
   ```

   resolves to the bare requirement:

   ```python
   pyjutsu>=0.8
   ```

   Do not hard-code pyjutsu. Keep the source-kind handling as an extensible prefix-to-handler seam, while preserving behavior for existing `path:` and `git+...` sources.

2. Add the safety guard.

   A `wheel:` source only works if vendomat’s module has exported `UV_FIND_LINKS`; otherwise uv will search PyPI and produce a confusing failure for personal packages.

   If any resolved target originated from a `wheel:` source and `UV_FIND_LINKS` is unset or empty, fail before invoking uv. The message must clearly tell the user to import and enable vendomat’s devenv module. It should identify the missing integration rather than imply that the package is on PyPI.

   Keep the guard generic for every `wheel:` source, not pyjutsu-specific.

3. Add Rust native-build opt-in to `modules/managers/gitman.nix`.

   Add:

   ```nix
   options.repoman.nativeBuild = lib.mkOption {
     type = lib.types.bool;
     default = false;
     description = "...";
   };
   ```

   Gate Rust provisioning and `pkgs.maturin` on both the manager being enabled and `cfg.nativeBuild`.

   Expected behavior:

   - A consumer using `wheel:` leaves `repoman.nativeBuild = false`; no Rust toolchain or maturin is contributed.
   - A repo that builds native packages locally sets `repoman.nativeBuild = true`.
   - Do not accidentally gate unrelated gitman functionality.

4. Update lock documentation and consumer fixture.

   Update the source-kind documentation/comment in:

   - `repoman.lock`
   - `tests/consumer-example/repoman.lock`

   Document all supported forms, including `wheel:`.

   Change the `git-pyjutsu` manager source to:

   ```toml
   source = "wheel:pyjutsu>=0.8"
   ```

   Preserve the project’s existing lock-file style and package/version arrangement.

5. Tests and proof.

   Add focused tests that prove:

   - `wheel:pyjutsu>=0.8` resolves exactly to `pyjutsu>=0.8`.
   - Existing source kinds keep their current behavior.
   - A wheel target with `UV_FIND_LINKS` absent fails with the intended actionable message.
   - The gitman module does not contribute Rust tooling when `nativeBuild = false`.
   - The gitman module does contribute the native build requirements when `nativeBuild = true`.

   If the consumer example can be run in this environment, prove the integration:

   - vendomat module enabled;
   - `nativeBuild = false`;
   - `repoman-sync` installs pyjutsu from the wheelhouse;
   - no Cargo/Rust compilation occurs;
   - `python -c "import pyjutsu"` succeeds.

   If a full integration test cannot run due to environment constraints, still implement unit/Nix-eval coverage and report the exact blocker.

Working rules

- Use `rg` to inspect first; preserve unrelated worktree changes.
- Do not modify vendomat unless a genuine cross-repo contract mismatch is discovered. If one is discovered, stop and report it rather than silently broadening scope.
- Use `apply_patch` for edits.
- Run the repository’s standard verification command(s), plus targeted tests.
- Do not commit unless explicitly asked.
- At the end, summarize modified files, test results, and any remaining integration limitation.

Definition of done

A repoman consumer can express a personal native dependency as `wheel:<requirement>` in `repoman.lock`; repoman passes a bare requirement to uv only when vendomat’s wheelhouse is configured; consumers no longer provision Rust by default; and the behavior is covered by focused tests.
```
